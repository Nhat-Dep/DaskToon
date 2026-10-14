# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The fast action filter (docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md, section 7): the Geometry
Nodes group "DaskToon Fast Action", the last modifier of each mesh of a character. A Simulation Zone keeps where each
vertex was (in world space) at the 3 frames before; where a vertex moves faster than the threshold, the mesh's trailing
side is smeared back, afterimages of the frames before show (only their fast parts) and speed lines trail it. Held
poses (anime timing) do not move, so the effects show on the frames where the drawing changes. Engine Export does not
apply modifiers, so none of this reaches the FBX."""

import bpy

from . import character

GROUP = "DaskToon Fast Action"
MODIFIER = "DaskToon Fast Action"
VERSION = 1
FADE = "dasktoon_fade"  # afterimage opacity along the copies: 1, 2/3, 1/3; the afterimage material reads it
_TEMP = ("dasktoon_tmp_p1", "dasktoon_tmp_p2", "dasktoon_tmp_p3", "dasktoon_tmp_f1", "dasktoon_tmp_f2",
         "dasktoon_tmp_f3", "dasktoon_tmp_line")

# The threshold (a speed) and the line width are set for a character this tall and scale with the character's height
# (real model test: a character 2.95 m tall was covered in lines). The line length is a time: it scales by itself.
REFERENCE_HEIGHT = 1.6
LINE_WIDTH = 0.004

# (name, socket type, default, min, max): the group's inputs after Geometry, set from the character's settings.
INPUTS = (
    ("Threshold", 'NodeSocketFloat', 3.0, 0.0, 1000.0),
    ("Smear", 'NodeSocketFloat', 0.6, 0.0, 1.0),
    ("Afterimages", 'NodeSocketInt', 2, 0, 3),
    ("Afterimage Material", 'NodeSocketMaterial', None, None, None),
    ("Line Density", 'NodeSocketFloat', 0.08, 0.0, 1.0),
    ("Line Length", 'NodeSocketFloat', 0.04, 0.0, 10.0),
    ("Line Width", 'NodeSocketFloat', LINE_WIDTH, 0.0, 1.0),
    ("Line Material", 'NodeSocketMaterial', None, None, None),
)


class _Tree:
    """Adds nodes to a node tree: node(idname, {input name or index: value or socket}, **properties)."""

    def __init__(self, tree):
        self.tree = tree

    def node(self, idname, inputs=None, **props):
        node = self.tree.nodes.new(idname)
        for name, value in props.items():
            setattr(node, name, value)
        for key, value in (inputs or {}).items():
            socket = node.inputs[key]
            if isinstance(value, bpy.types.NodeSocket):
                self.tree.links.new(value, socket)
            else:
                socket.default_value = value
        return node

    def math(self, operation, a, b=None, **props):
        inputs = {0: a} if b is None else {0: a, 1: b}
        return self.node("ShaderNodeMath", inputs, operation=operation, **props).outputs[0]

    def vector(self, operation, a, b=None, scale=None):
        inputs = {0: a}
        if b is not None:
            inputs[1] = b
        if scale is not None:
            inputs["Scale"] = scale
        node = self.node("ShaderNodeVectorMath", inputs, operation=operation)
        return node.outputs["Value" if operation in {'LENGTH', 'DOT_PRODUCT'} else "Vector"]

    def attribute(self, name, data_type='FLOAT_VECTOR'):
        return self.node("GeometryNodeInputNamedAttribute", {"Name": name}, data_type=data_type).outputs["Attribute"]

    def store(self, geometry, name, value, data_type='FLOAT_VECTOR'):
        return self.node("GeometryNodeStoreNamedAttribute", {"Geometry": geometry, "Name": name, "Value": value},
                         data_type=data_type, domain='POINT').outputs["Geometry"]

    def sample(self, geometry, value, index):
        return self.node("GeometryNodeSampleIndex", {"Geometry": geometry, "Value": value, "Index": index},
                         data_type='FLOAT_VECTOR', domain='POINT').outputs["Value"]


def _new_socket(tree, name, in_out, socket_type):
    socket = tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    socket.name = name  # a new socket's name is translated when the interface translates new data; keep it English
    return socket


def _interface(tree):
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    for name, socket_type, default, low, high in INPUTS:
        socket = _new_socket(tree, name, 'INPUT', socket_type)
        if default is not None:
            socket.default_value, socket.min_value, socket.max_value = default, low, high
    _new_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')


def _build(tree):
    t = _Tree(tree)
    group_in = t.node("NodeGroupInput").outputs
    mesh = group_in["Geometry"]
    index = t.node("GeometryNodeInputIndex").outputs[0]
    position = t.node("GeometryNodeInputPosition").outputs[0]
    normal = t.node("GeometryNodeInputNormal").outputs["Normal"]
    me = t.node("GeometryNodeSelfObject").outputs[0]
    matrix = t.node("GeometryNodeObjectInfo", {"Object": me}).outputs["Transform"]
    inverse = t.node("FunctionNodeInvertMatrix", {"Matrix": matrix}).outputs["Matrix"]
    world = t.node("FunctionNodeTransformPoint", {"Vector": position, "Transform": matrix}).outputs[0]

    # The state: one point per vertex at its world position now, with where it was 1, 2 and 3 frames before.
    def points():
        return t.node("GeometryNodeMeshToPoints", {"Mesh": mesh, "Position": world}).outputs["Points"]

    start = points()
    for name in _TEMP[:3]:
        start = t.store(start, name, position)
    sim_in = t.node("GeometryNodeSimulationInput")
    sim_out = t.node("GeometryNodeSimulationOutput")
    sim_in.pair_with_output(sim_out)
    sim_out.state_items[0].name = "Geometry"  # made with a translated name when the interface translates new data
    sim_out.state_items.new('FLOAT', "Step").name = "Step"
    tree.links.new(start, sim_in.inputs["Geometry"])
    before = sim_in.outputs["Geometry"]
    state = points()
    state = t.store(state, _TEMP[0], t.sample(before, position, index))
    state = t.store(state, _TEMP[1], t.sample(before, t.attribute(_TEMP[0]), index))
    state = t.store(state, _TEMP[2], t.sample(before, t.attribute(_TEMP[1]), index))
    tree.links.new(state, sim_out.inputs["Geometry"])
    tree.links.new(sim_in.outputs["Delta Time"], sim_out.inputs["Step"])
    now = sim_out.outputs["Geometry"]
    step = sim_out.outputs["Step"]

    # On the mesh: where each vertex was (local), whether it moved fast into each of the last 3 frames, and its line.
    was = [world] + [t.sample(now, t.attribute(name), index) for name in _TEMP[:3]]
    limit = t.math('MULTIPLY', group_in["Threshold"], step)
    base = mesh
    for k in (1, 2, 3):
        local = t.node("FunctionNodeTransformPoint", {"Vector": was[k], "Transform": inverse}).outputs[0]
        base = t.store(base, _TEMP[2 + k], t.math('GREATER_THAN', t.vector('LENGTH', t.vector('SUBTRACT', was[k - 1],
                                                                                              was[k])), limit),
                       'BOOLEAN')
        base = t.store(base, _TEMP[k - 1], local)
    back = t.vector('SUBTRACT', t.attribute(_TEMP[0]), position)  # toward where it was a frame before
    line_scale = t.math('DIVIDE', group_in["Line Length"], step)
    base = t.store(base, _TEMP[6], t.vector('SCALE', back, scale=line_scale))
    fast = t.attribute(_TEMP[3], 'BOOLEAN')

    # Smear: the trailing side (normals facing back) is pulled back by Smear.
    trailing = t.vector('DOT_PRODUCT', normal, t.vector('NORMALIZE', back))
    pull = t.math('MULTIPLY', trailing, group_in["Smear"], use_clamp=True)
    smeared = t.node("GeometryNodeSetPosition", {"Geometry": base, "Selection": fast,
                                                 "Offset": t.vector('SCALE', back, scale=pull)}).outputs[0]
    join = t.node("GeometryNodeJoinGeometry")
    tree.links.new(smeared, join.inputs[0])

    # Afterimages: the fast part of the mesh where it was k frames before, fading with k.
    for k in (1, 2, 3):
        moved = t.node("GeometryNodeSetPosition", {"Geometry": base, "Position": t.attribute(_TEMP[k - 1])}).outputs[0]
        slow = t.node("FunctionNodeBooleanMath", {0: t.attribute(_TEMP[2 + k], 'BOOLEAN')}, operation='NOT').outputs[0]
        kept = t.node("GeometryNodeDeleteGeometry", {"Geometry": moved, "Selection": slow}, domain='POINT',
                      mode='ALL').outputs[0]
        kept = t.store(kept, FADE, 1.0 - (k - 1) / 3.0, 'FLOAT')
        kept = t.node("GeometryNodeSetMaterial", {"Geometry": kept,
                                                  "Material": group_in["Afterimage Material"]}).outputs[0]
        shown = t.node("FunctionNodeCompare", {"A": group_in["Afterimages"], "B": k}, data_type='INT',
                       operation='GREATER_EQUAL').outputs[0]
        switch = t.node("GeometryNodeSwitch", {"Switch": shown, "True": kept}, input_type='GEOMETRY')
        tree.links.new(switch.outputs[0], join.inputs[0])

    # Speed lines: from a share (Line Density) of the fast vertices, back along the motion, speed x Line Length long.
    chosen = t.node("FunctionNodeRandomValue", {"Probability": group_in["Line Density"], "ID": index},
                    data_type='BOOLEAN').outputs[0]
    pick = t.node("FunctionNodeBooleanMath", {0: fast, 1: chosen}, operation='AND').outputs[0]
    dots = t.node("GeometryNodeMeshToPoints", {"Mesh": base, "Selection": pick}).outputs["Points"]
    loose = t.node("GeometryNodePointsToVertices", {"Points": dots}).outputs["Mesh"]
    lines = t.node("GeometryNodeExtrudeMesh", {"Mesh": loose, "Offset": t.attribute(_TEMP[6])},
                   mode='VERTICES').outputs["Mesh"]
    curves = t.node("GeometryNodeMeshToCurve", {"Mesh": lines}).outputs["Curve"]
    profile = t.node("GeometryNodeCurvePrimitiveCircle", {"Resolution": 4, "Radius": group_in["Line Width"]},
                     mode='RADIUS').outputs["Curve"]
    tubes = t.node("GeometryNodeCurveToMesh", {"Curve": curves, "Profile Curve": profile}).outputs["Mesh"]
    tubes = t.node("GeometryNodeSetMaterial", {"Geometry": tubes, "Material": group_in["Line Material"]}).outputs[0]
    tree.links.new(tubes, join.inputs[0])

    out = join.outputs[0]
    for name in _TEMP:
        out = t.node("GeometryNodeRemoveAttribute", {"Geometry": out, "Name": name}).outputs[0]
    tree.links.new(out, t.node("NodeGroupOutput").inputs[0])


def node_group():
    """The "DaskToon Fast Action" group, built (again) when missing or older."""
    tree = bpy.data.node_groups.get(GROUP)
    if tree is not None and tree.get("dasktoon_version") == VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    tree.nodes.clear()
    tree.interface.clear()
    _interface(tree)
    _build(tree)
    tree["dasktoon_version"] = VERSION
    return tree


def material_name(armature, kind):
    """"DaskToon Afterimage (Rig)" or "DaskToon Lines (Rig)": a character's effect materials."""
    return "DaskToon %s (%s)" % (kind, armature.name)


def _emission(material):
    return next(node for node in material.node_tree.nodes if node.type == 'EMISSION')


def material_color(material):
    return _emission(material).inputs["Color"].default_value


def _material(armature, kind):
    """The character's afterimage material (emission, see-through by FADE x opacity) or lines material (emission),
    made when missing."""
    name = material_name(armature, kind)
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    if material.node_tree is None:
        material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    if kind == "Lines":
        links.new(emission.outputs[0], output.inputs["Surface"])
        return material
    material.surface_render_method = 'BLENDED'
    fade = nodes.new("ShaderNodeAttribute")
    fade.attribute_name = FADE
    opacity = nodes.new("ShaderNodeMath")
    opacity.operation = 'MULTIPLY'
    opacity.name = "Opacity"
    links.new(fade.outputs["Fac"], opacity.inputs[0])
    mix = nodes.new("ShaderNodeMixShader")
    links.new(opacity.outputs[0], mix.inputs["Fac"])
    links.new(nodes.new("ShaderNodeBsdfTransparent").outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    return material


def _input(modifier, name):
    """The modifier's input `name` (its `.value` is the value)."""
    return getattr(modifier.properties.inputs, modifier.node_group.interface.items_tree[name].identifier)


def input_value(modifier, name):
    return _input(modifier, name).value


def size(objects):
    """The character's height (its meshes at rest) over REFERENCE_HEIGHT; 1 when there is none."""
    from dasktoon_rig import skeleton
    box = skeleton.bounds(objects)
    height = box[1].z - box[0].z if box is not None else 0.0
    return height / REFERENCE_HEIGHT if height > 1e-6 else 1.0


def _settings_inputs(armature, objects):
    settings = armature.data.dasktoon_fast_action
    afterimage, lines = _material(armature, "Afterimage"), _material(armature, "Lines")
    material_color(afterimage)[:3] = settings.afterimage_color
    afterimage.node_tree.nodes["Opacity"].inputs[1].default_value = settings.afterimage_opacity
    material_color(lines)[:3] = settings.line_color
    scale = size(objects)
    return {"Threshold": settings.threshold * scale, "Smear": settings.smear, "Afterimages": settings.afterimages,
            "Afterimage Material": afterimage, "Line Density": settings.line_density,
            "Line Length": settings.line_length, "Line Width": LINE_WIDTH * scale, "Line Material": lines}


def meshes(armature, objects):
    return [obj for obj in character.members(armature, objects) if obj.type == 'MESH']


def sync(armature, objects):
    """The modifiers of the character's meshes follow its settings: on, each mesh has the modifier last, with the
    settings as inputs; off, the modifiers are off (and stay, with their settings)."""
    settings = armature.data.dasktoon_fast_action
    if not settings.enabled:
        for obj in meshes(armature, objects):
            modifier = obj.modifiers.get(MODIFIER)
            if modifier is not None:
                modifier.show_viewport = modifier.show_render = False
        return
    tree = node_group()
    inputs = _settings_inputs(armature, meshes(armature, objects))
    for obj in meshes(armature, objects):
        modifier = obj.modifiers.get(MODIFIER) or obj.modifiers.new(MODIFIER, 'NODES')
        if modifier.node_group != tree:
            modifier.node_group = tree
        index = list(obj.modifiers).index(modifier)
        if index != len(obj.modifiers) - 1:
            obj.modifiers.move(index, len(obj.modifiers) - 1)
        for name, value in inputs.items():
            _input(modifier, name).value = value
        modifier.show_viewport = modifier.show_render = True
        modifier.node_group = tree  # Python writes to the inputs do not evaluate the object again; this does
