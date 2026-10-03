# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Geometry Nodes builders for the DaskToon outline (spec section 4.3). Builders only, no syncing."""

import math
from dataclasses import dataclass

import bpy

CORE_GROUP = "DaskToon_OutlineCore"
CORE_VERSION = 1
OBJECT_GROUP_PREFIX = "DT_Outline::"
MODIFIER_NAME = "DaskToon Outline"
WOBBLE_SCALE = 12.0
_FALLBACK = (0.5, 0.8, 0.6)
FALLBACK_LIGHT = tuple(c / math.sqrt(sum(x * x for x in _FALLBACK)) for c in _FALLBACK)


@dataclass(frozen=True)
class SlotParams:
    enabled: bool
    width: float
    bleed: float
    wobble: float
    outline_material: object  # bpy.types.Material or None


def _new_socket(tree, name, in_out, socket_type, default=None):
    socket = tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    if default is not None:
        socket.default_value = default
    return socket


def _feed(tree, socket, value):
    if isinstance(value, bpy.types.NodeSocket):
        tree.links.new(value, socket)
    elif value is not None:
        socket.default_value = value


def _math(tree, operation, a=None, b=None, c=None, clamp=False):
    node = tree.nodes.new('ShaderNodeMath')
    node.operation = operation
    node.use_clamp = clamp
    for socket, value in zip(node.inputs, (a, b, c)):
        _feed(tree, socket, value)
    return node.outputs[0]


def _vector_math(tree, operation, a=None, b=None, scale=None):
    node = tree.nodes.new('ShaderNodeVectorMath')
    node.operation = operation
    _feed(tree, node.inputs[0], a)
    _feed(tree, node.inputs[1], b)
    if scale is not None:
        _feed(tree, node.inputs["Scale"], scale)
    if operation in {'DOT_PRODUCT', 'LENGTH', 'DISTANCE'}:
        return node.outputs["Value"]
    return node.outputs["Vector"]


def _on_domain(tree, value, domain, data_type):
    node = tree.nodes.new('GeometryNodeFieldOnDomain')
    node.domain = domain
    node.data_type = data_type
    tree.links.new(value, node.inputs["Value"])
    return node.outputs["Value"]


def ensure_core_group():
    tree = bpy.data.node_groups.get(CORE_GROUP)
    if tree is not None and tree.get("dasktoon_version") == CORE_VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(CORE_GROUP, 'GeometryNodeTree')
    else:
        tree.nodes.clear()
        tree.interface.clear()
    tree["dasktoon_version"] = CORE_VERSION
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Enabled", 'INPUT', 'NodeSocketBool', False)
    _new_socket(tree, "Width", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Bleed", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Wobble", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Sun", 'INPUT', 'NodeSocketObject')
    _new_socket(tree, "Has Sun", 'INPUT', 'NodeSocketBool', False)
    _new_socket(tree, "Mask Name", 'INPUT', 'NodeSocketString', "")
    _new_socket(tree, "UV Name", 'INPUT', 'NodeSocketString', "")
    _new_socket(tree, "Original", 'OUTPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Hull", 'OUTPUT', 'NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    inp = group_in.outputs

    # Faces whose material has outline enabled are the hull source.
    separate = nodes.new('GeometryNodeSeparateGeometry')
    separate.domain = 'FACE'
    links.new(inp["Geometry"], separate.inputs["Geometry"])
    links.new(inp["Enabled"], separate.inputs["Selection"])

    # Smoothed normal: merge coincident vertices, then sample their normal back (no cracks on split seams).
    merge = nodes.new('GeometryNodeMergeByDistance')
    merge.inputs["Distance"].default_value = 1e-5
    links.new(inp["Geometry"], merge.inputs["Geometry"])
    nearest = nodes.new('GeometryNodeSampleNearest')
    nearest.domain = 'POINT'
    links.new(merge.outputs[0], nearest.inputs["Geometry"])
    links.new(nodes.new('GeometryNodeInputPosition').outputs[0], nearest.inputs["Sample Position"])
    smooth = nodes.new('GeometryNodeSampleIndex')
    smooth.data_type = 'FLOAT_VECTOR'
    smooth.domain = 'POINT'
    links.new(merge.outputs[0], smooth.inputs["Geometry"])
    links.new(nodes.new('GeometryNodeInputNormal').outputs[0], smooth.inputs["Value"])
    links.new(nearest.outputs["Index"], smooth.inputs["Index"])

    # World-space normal and direction towards the Sun.
    self_info = nodes.new('GeometryNodeObjectInfo')
    self_info.transform_space = 'ORIGINAL'
    links.new(nodes.new('GeometryNodeSelfObject').outputs[0], self_info.inputs["Object"])
    to_world = nodes.new('FunctionNodeTransformDirection')
    links.new(smooth.outputs[0], to_world.inputs["Direction"])
    links.new(self_info.outputs["Transform"], to_world.inputs["Transform"])
    normal_world = _vector_math(tree, 'NORMALIZE', to_world.outputs[0])
    sun_info = nodes.new('GeometryNodeObjectInfo')
    sun_info.transform_space = 'ORIGINAL'
    links.new(inp["Sun"], sun_info.inputs["Object"])
    sun_up = nodes.new('FunctionNodeRotateVector')
    sun_up.inputs["Vector"].default_value = (0.0, 0.0, 1.0)
    links.new(sun_info.outputs["Rotation"], sun_up.inputs["Rotation"])
    light_dir = nodes.new('GeometryNodeSwitch')
    light_dir.input_type = 'VECTOR'
    light_dir.inputs["False"].default_value = FALLBACK_LIGHT
    links.new(inp["Has Sun"], light_dir.inputs["Switch"])
    links.new(sun_up.outputs[0], light_dir.inputs["True"])

    # light_thin = 1 - clamp((hl - 0.55) / 0.45) * bleed * 0.75, with hl = dot(N, L) * 0.5 + 0.5
    n_dot_l = _vector_math(tree, 'DOT_PRODUCT', normal_world, light_dir.outputs[0])
    half_lambert = _math(tree, 'MULTIPLY_ADD', n_dot_l, 0.5, 0.5)
    lit_amount = _math(tree, 'DIVIDE', _math(tree, 'SUBTRACT', half_lambert, 0.55), 0.45, clamp=True)
    bleed = _on_domain(tree, inp["Bleed"], 'FACE', 'FLOAT')
    light_thin = _math(tree, 'SUBTRACT', 1.0,
                       _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', lit_amount, bleed), 0.75))

    # Wobble: f(u, v) = sin(2u) cos(3v) + 0.5 sin(6.28v), (u, v) = first UV map * WOBBLE_SCALE
    uv_attr = nodes.new('GeometryNodeInputNamedAttribute')
    uv_attr.data_type = 'FLOAT_VECTOR'
    links.new(inp["UV Name"], uv_attr.inputs["Name"])
    uv = _on_domain(tree, uv_attr.outputs["Attribute"], 'CORNER', 'FLOAT_VECTOR')
    split_uv = nodes.new('ShaderNodeSeparateXYZ')
    links.new(uv, split_uv.inputs[0])
    u = _math(tree, 'MULTIPLY', split_uv.outputs["X"], WOBBLE_SCALE)
    v = _math(tree, 'MULTIPLY', split_uv.outputs["Y"], WOBBLE_SCALE)
    f = _math(tree, 'ADD',
              _math(tree, 'MULTIPLY', _math(tree, 'SINE', _math(tree, 'MULTIPLY', u, 2.0)),
                    _math(tree, 'COSINE', _math(tree, 'MULTIPLY', v, 3.0))),
              _math(tree, 'MULTIPLY', _math(tree, 'SINE', _math(tree, 'MULTIPLY', v, 6.28)), 0.5))
    wobble = _on_domain(tree, inp["Wobble"], 'FACE', 'FLOAT')
    wobble_term = _math(tree, 'ADD', 1.0, _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', wobble, 0.25), f))

    # Optional painted mask (vertex group); 1 when the attribute does not exist.
    mask_attr = nodes.new('GeometryNodeInputNamedAttribute')
    mask_attr.data_type = 'FLOAT'
    links.new(inp["Mask Name"], mask_attr.inputs["Name"])
    mask = nodes.new('GeometryNodeSwitch')
    mask.input_type = 'FLOAT'
    mask.inputs["False"].default_value = 1.0
    links.new(mask_attr.outputs["Exists"], mask.inputs["Switch"])
    links.new(mask_attr.outputs["Attribute"], mask.inputs["True"])

    width = _on_domain(tree, inp["Width"], 'FACE', 'FLOAT')
    width = _math(tree, 'MULTIPLY',
                  _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', width, light_thin), wobble_term),
                  mask.outputs[0])
    offset_world = _vector_math(tree, 'SCALE', normal_world, scale=width)
    invert = nodes.new('FunctionNodeInvertMatrix')
    links.new(self_info.outputs["Transform"], invert.inputs["Matrix"])
    to_local = nodes.new('FunctionNodeTransformDirection')
    links.new(offset_world, to_local.inputs["Direction"])
    links.new(invert.outputs["Matrix"], to_local.inputs["Transform"])
    set_position = nodes.new('GeometryNodeSetPosition')
    links.new(separate.outputs["Selection"], set_position.inputs["Geometry"])
    links.new(to_local.outputs[0], set_position.inputs["Offset"])
    flip = nodes.new('GeometryNodeFlipFaces')
    links.new(set_position.outputs[0], flip.inputs["Mesh"])

    links.new(inp["Geometry"], group_out.inputs["Original"])
    links.new(flip.outputs[0], group_out.inputs["Hull"])
    return tree


def build_object_group(obj, slots, sun, mask_name, uv_name):
    name = OBJECT_GROUP_PREFIX + obj.name
    tree = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, 'GeometryNodeTree')
    tree.nodes.clear()
    tree.interface.clear()
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    material_index = nodes.new('GeometryNodeInputMaterialIndex').outputs[0]

    def table(data_type, values):
        switch = nodes.new('GeometryNodeIndexSwitch')
        switch.data_type = data_type
        switch.index_switch_items.clear()
        for _value in values:
            switch.index_switch_items.new()
        links.new(material_index, switch.inputs["Index"])
        for i, value in enumerate(values):
            switch.inputs[i + 1].default_value = value
        return switch.outputs[0]

    core = nodes.new('GeometryNodeGroup')
    core.node_tree = ensure_core_group()
    links.new(group_in.outputs[0], core.inputs["Geometry"])
    links.new(table('BOOLEAN', [s.enabled for s in slots]), core.inputs["Enabled"])
    links.new(table('FLOAT', [s.width for s in slots]), core.inputs["Width"])
    links.new(table('FLOAT', [s.bleed for s in slots]), core.inputs["Bleed"])
    links.new(table('FLOAT', [s.wobble for s in slots]), core.inputs["Wobble"])
    core.inputs["Sun"].default_value = sun
    core.inputs["Has Sun"].default_value = sun is not None
    core.inputs["Mask Name"].default_value = mask_name
    core.inputs["UV Name"].default_value = uv_name

    hull = core.outputs["Hull"]
    for i, slot in enumerate(slots):
        if not slot.enabled or slot.outline_material is None:
            continue
        compare = nodes.new('FunctionNodeCompare')
        compare.data_type = 'INT'
        compare.operation = 'EQUAL'
        links.new(material_index, compare.inputs["A"])
        compare.inputs["B"].default_value = i
        set_material = nodes.new('GeometryNodeSetMaterial')
        set_material.inputs["Material"].default_value = slot.outline_material
        links.new(hull, set_material.inputs["Geometry"])
        links.new(compare.outputs[0], set_material.inputs["Selection"])
        hull = set_material.outputs[0]
    join = nodes.new('GeometryNodeJoinGeometry')
    # A multi-input socket evaluates the newest link first: link the hull first so the original
    # mesh keeps the first (unchanged) vertex and face indices of the evaluated mesh.
    links.new(hull, join.inputs[0])
    links.new(core.outputs["Original"], join.inputs[0])
    links.new(join.outputs[0], group_out.inputs[0])
    return tree


def _move_last(obj, modifier):
    index = obj.modifiers.find(modifier.name)
    last = len(obj.modifiers) - 1
    if index == last:
        return
    if hasattr(obj.modifiers, "move"):
        obj.modifiers.move(index, last)
    else:
        with bpy.context.temp_override(object=obj):
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=last)


def ensure_modifier(obj, tree):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None:
        modifier = obj.modifiers.new(MODIFIER_NAME, 'NODES')
    if modifier.node_group != tree:
        modifier.node_group = tree
    _move_last(obj, modifier)
    return modifier


def remove_modifier(obj):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is not None:
        obj.modifiers.remove(modifier)
    tree = bpy.data.node_groups.get(OBJECT_GROUP_PREFIX + obj.name)
    if tree is not None and tree.users == 0:
        bpy.data.node_groups.remove(tree)
