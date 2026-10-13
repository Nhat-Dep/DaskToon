# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The 2D mouth (anime rig spec 10.3): the part's material shows one cell of an atlas texture, rows x columns of drawn
mouths, the cell the object's dt_mouth property picks (animate it, or let lip sync key it). Each Image Texture of the
material gets the node group "DaskToon Mouth Atlas" before its Vector input, its Cell read by an Attribute node.

The FBX exporter does not carry custom property animation, so the bone MouthCell (deform, so it is exported; without
weights) carries the cell to Unity: a driver sets its Y scale to dt_mouth + 1, a simple expression (no Auto Run).

Cells run from the top left, row by row; by DaskToon's convention cell 0 is the closed mouth, then A, I, U, E, O."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import look, parts as rig_parts, skeleton

GROUP = "DaskToon Mouth Atlas"
PROP = "dt_mouth"
CELL_BONE = "MouthCell"
NODE_MARK = "dt_mouth_atlas"
CELLS = {"CLOSED": 0, "A": 1, "I": 2, "U": 3, "E": 4, "O": 5}


def cell_uv(uv, cell, rows, columns):
    """`uv` (0 to 1 over one mouth) placed in the atlas cell `cell` (rounded, kept within the atlas); the node group
    and DaskToon's Unity script use the same formula."""
    count = rows * columns
    c = min(max(int(cell + 0.5), 0), count - 1)
    col, row = c % columns, c // columns
    return (uv[0] + col) / columns, (uv[1] + rows - 1 - row) / rows


def _new_socket(tree, name, in_out, socket_type):
    socket = tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    socket.name = name  # a new socket's name is translated when the interface translates new data; keep it
    return socket


def atlas_group():
    """The node group: UV, Cell, Rows, Columns in, the UV in the atlas out (cell_uv)."""
    tree = bpy.data.node_groups.get(GROUP)
    if tree is not None and tree.get("dasktoon_version") == 1:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(GROUP, 'ShaderNodeTree')
    tree.nodes.clear()
    tree.interface.clear()
    _new_socket(tree, "UV", 'INPUT', 'NodeSocketVector')
    for name in ("Cell", "Rows", "Columns"):
        _new_socket(tree, name, 'INPUT', 'NodeSocketFloat')
    _new_socket(tree, "UV", 'OUTPUT', 'NodeSocketVector')
    nodes, links = tree.nodes, tree.links
    group_in = nodes.new("NodeGroupInput").outputs
    rows, columns = group_in["Rows"], group_in["Columns"]

    def math(operation, a, b=None):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, bpy.types.NodeSocket):
                links.new(value, node.inputs[i])
            else:
                node.inputs[i].default_value = value
        return node.outputs[0]

    last = math('SUBTRACT', math('MULTIPLY', rows, columns), 1.0)
    cell = math('MINIMUM', math('MAXIMUM', math('FLOOR', math('ADD', group_in["Cell"], 0.5)), 0.0), last)
    col = math('FLOORED_MODULO', cell, columns)
    row = math('FLOOR', math('DIVIDE', cell, columns))
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(group_in["UV"], split.inputs[0])
    u = math('DIVIDE', math('ADD', split.outputs["X"], col), columns)
    v = math('DIVIDE', math('ADD', split.outputs["Y"], math('SUBTRACT', math('SUBTRACT', rows, 1.0), row)), rows)
    join = nodes.new("ShaderNodeCombineXYZ")
    links.new(u, join.inputs["X"])
    links.new(v, join.inputs["Y"])
    links.new(join.outputs[0], nodes.new("NodeGroupOutput").inputs[0])
    tree["dasktoon_version"] = 1
    return tree


def _remove_atlas(mat):
    """Take out the atlas nodes of an earlier build, linking each texture back to its own UV source."""
    tree = mat.node_tree
    for group in [n for n in tree.nodes if n.get(NODE_MARK) == "group"]:
        source = next((link.from_socket for link in tree.links if link.to_socket == group.inputs["UV"]), None)
        targets = [link.to_socket for link in tree.links if link.from_node == group]
        if source is not None and source.node.get(NODE_MARK) != "uv":
            for socket in targets:
                tree.links.new(source, socket)
    for node in [n for n in tree.nodes if n.get(NODE_MARK)]:
        tree.nodes.remove(node)


def atlas_material(mat, rows, columns):
    """Put the atlas group before the Vector input of every Image Texture of `mat`; returns how many."""
    if mat is None or mat.node_tree is None:
        return 0
    _remove_atlas(mat)
    tree = mat.node_tree
    group_tree = atlas_group()
    textures = [n for n in tree.nodes if n.bl_idname == "ShaderNodeTexImage"]
    for texture in textures:
        vector = texture.inputs["Vector"]
        source = vector.links[0].from_socket if vector.is_linked else None
        if source is None:
            uv_map = tree.nodes.new("ShaderNodeUVMap")
            uv_map[NODE_MARK] = "uv"
            uv_map.location = texture.location + Vector((-500.0, -200.0))
            source = uv_map.outputs["UV"]
        group = tree.nodes.new("ShaderNodeGroup")
        group.node_tree = group_tree
        group[NODE_MARK] = "group"
        group.location = texture.location + Vector((-250.0, -200.0))
        group.inputs["Rows"].default_value = rows
        group.inputs["Columns"].default_value = columns
        cell = tree.nodes.new("ShaderNodeAttribute")
        cell.attribute_type, cell.attribute_name = 'OBJECT', PROP
        cell[NODE_MARK] = "cell"
        cell.location = texture.location + Vector((-500.0, -400.0))
        tree.links.new(source, group.inputs["UV"])
        tree.links.new(cell.outputs["Fac"], group.inputs["Cell"])
        tree.links.new(group.outputs["UV"], vector)
    return len(textures)


def ensure_property(obj, count):
    """The object's dt_mouth, an animatable whole number from 0 to `count` - 1."""
    if PROP not in obj:
        obj[PROP] = 0
    obj.id_properties_ui(PROP).update(min=0, max=max(count - 1, 0), description="Cell of the mouth atlas to show")


def _materials(part, vertices):
    """The materials the part's faces use."""
    obj = part.object
    if part.scope == 'MATERIAL':
        found = obj.data.materials.get(part.material)
        return [found] if found is not None else []
    inside = set(int(v) for v in vertices)
    slots = {p.material_index for p in obj.data.polygons if all(v in inside for v in p.vertices)}
    return [obj.material_slots[i].material for i in sorted(slots) if i < len(obj.material_slots)]


def _cell_bone(context, rig, wanted):
    """MouthCell under the Head, near the mouth, when a 2D Mouth part needs it; gone otherwise."""
    bones = rig.data.bones
    if (bones.get(CELL_BONE) is not None) == wanted:
        return
    with skeleton.editing(context, rig) as edit:
        if not wanted:
            edit.remove(edit[CELL_BONE])
            return
        bone = edit.new(CELL_BONE)
        jaw = edit.get("Jaw")
        bone.head = jaw.tail.copy() if jaw is not None else edit["Head"].head.copy()
        bone.tail = bone.head + Vector((0.0, -0.02, 0.0))
        bone.parent = edit["Head"]
        bone.use_deform = True  # exported in the FBX (deform bones only); it has no weights
        bone[look.FACE_MARK] = "mouth"


def _drive(rig, obj):
    path = 'pose.bones["%s"].scale' % CELL_BONE
    rig.driver_remove(path, 1)
    if obj is None:
        return
    driver = rig.driver_add(path, 1).driver
    driver.type = 'SCRIPTED'
    var = driver.variables.new()
    var.name, var.type = "cell", 'SINGLE_PROP'
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = obj
    var.targets[0].data_path = '["%s"]' % PROP
    driver.expression = "cell + 1"


def apply(context, rig, parts, result):
    """The atlas in the materials of every 2D Mouth part, its dt_mouth, MouthCell and its driver (from the first)."""
    mouths = [part for part in parts if part.role == 'MOUTH_2D' and part.object is not None]
    _cell_bone(context, rig, bool(mouths))
    if rig.animation_data is not None or mouths:
        _drive(rig, mouths[0].object if mouths else None)
    for part in mouths:
        vertices = rig_parts.part_vertices(part)
        count = 0
        for mat in _materials(part, vertices):
            count += atlas_material(mat, part.mouth_rows, part.mouth_columns)
        if count == 0:
            result.warnings.append(rpt_("%s: its material has no image texture to show mouth cells from") % part.name)
        ensure_property(part.object, part.mouth_rows * part.mouth_columns)
