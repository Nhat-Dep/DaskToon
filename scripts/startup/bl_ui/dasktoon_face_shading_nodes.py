# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Geometry Nodes of DaskToon face shading (docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md,
section 4): the corner normals of the face lean towards the normals of an ellipsoid proxy. Builders and modifier
helpers only."""

import bpy

from .dasktoon_outline_nodes import MODIFIER_NAME as OUTLINE_MODIFIER
from .dasktoon_outline_nodes import _feed, _math, _new_socket, _vector_math

GROUP = "DaskToon_FaceShading"
VERSION = 1
MODIFIER_NAME = "DaskToon Face Shading"
MASK_NAME = "DT_Face"
# Group inputs after Geometry: (name, socket type, default, min, max). Falloff stays above 0 because Map Range divides
# by From Max - From Min.
INPUTS = (
    ("Proxy", 'NodeSocketObject', None, None, None),
    ("Coverage", 'NodeSocketFloat', 1.0, 0.0, 1.0),
    ("Falloff", 'NodeSocketFloat', 0.3, 0.01, 2.0),
    ("Nose Keep", 'NodeSocketFloat', 0.6, 0.0, 1.0),
    ("Chin Keep", 'NodeSocketFloat', 0.8, 0.0, 1.0),
    ("Mask Name", 'NodeSocketString', MASK_NAME, None, None),
)


def _smoothstep(tree, edge0, edge1, x):
    """Clamped smoothstep: Map Range in Smooth Step mode."""
    node = tree.nodes.new('ShaderNodeMapRange')
    node.interpolation_type = 'SMOOTHSTEP'
    _feed(tree, node.inputs["Value"], x)
    _feed(tree, node.inputs["From Min"], edge0)
    _feed(tree, node.inputs["From Max"], edge1)
    return node.outputs["Result"]


def ensure_group():
    tree = bpy.data.node_groups.get(GROUP)
    if tree is not None and tree.get("dasktoon_version") == VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    else:
        tree.nodes.clear()
        tree.interface.clear()
    tree["dasktoon_version"] = VERSION
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    for name, socket_type, default, low, high in INPUTS:
        socket = _new_socket(tree, name, 'INPUT', socket_type, default)
        if low is not None:
            socket.min_value = low
            socket.max_value = high
    _new_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    inp = group_in.outputs

    # M: the proxy relative to this object. In the proxy's own space the proxy is the unit sphere.
    info = nodes.new('GeometryNodeObjectInfo')
    info.transform_space = 'RELATIVE'
    links.new(inp["Proxy"], info.inputs["Object"])
    invert = nodes.new('FunctionNodeInvertMatrix')
    links.new(info.outputs["Transform"], invert.inputs["Matrix"])
    to_proxy = nodes.new('FunctionNodeTransformPoint')
    links.new(nodes.new('GeometryNodeInputPosition').outputs[0], to_proxy.inputs["Vector"])
    links.new(invert.outputs["Matrix"], to_proxy.inputs["Transform"])
    q = to_proxy.outputs[0]
    r = _vector_math(tree, 'LENGTH', q)
    d = _vector_math(tree, 'NORMALIZE', q)

    # n_e = normalize((L^-1)^T d), the ellipsoid normal through the point; down = normalize(L (0, 0, -1)).
    transpose = nodes.new('FunctionNodeTransposeMatrix')
    links.new(invert.outputs["Matrix"], transpose.inputs["Matrix"])
    ellipsoid = nodes.new('FunctionNodeTransformDirection')
    links.new(d, ellipsoid.inputs["Direction"])
    links.new(transpose.outputs["Matrix"], ellipsoid.inputs["Transform"])
    n_e = _vector_math(tree, 'NORMALIZE', ellipsoid.outputs[0])
    down_dir = nodes.new('FunctionNodeTransformDirection')
    down_dir.inputs["Direction"].default_value = (0.0, 0.0, -1.0)
    links.new(info.outputs["Transform"], down_dir.inputs["Transform"])
    down = _vector_math(tree, 'NORMALIZE', down_dir.outputs[0])

    # N0: the corner normal as it is, custom normals included.
    n0 = nodes.new('GeometryNodeInputNormal').outputs["Normal"]
    split = nodes.new('ShaderNodeSeparateXYZ')
    links.new(d, split.inputs[0])
    mask = nodes.new('GeometryNodeInputNamedAttribute')
    mask.data_type = 'FLOAT'
    links.new(inp["Mask Name"], mask.inputs["Name"])

    outer = _smoothstep(tree, 1.0, _math(tree, 'ADD', inp["Falloff"], 1.0), r)
    region = _math(tree, 'MULTIPLY', mask.outputs["Attribute"], _math(tree, 'SUBTRACT', 1.0, outer))
    nose = _math(tree, 'MULTIPLY',
                 _smoothstep(tree, 0.80, 0.95, _math(tree, 'MULTIPLY', split.outputs["Y"], -1.0)),
                 _smoothstep(tree, 0.02, 0.08, _math(tree, 'SUBTRACT', r, 1.0)))
    chin = _math(tree, 'MULTIPLY',
                 _smoothstep(tree, 0.25, 0.55, _math(tree, 'MULTIPLY', split.outputs["Z"], -1.0)),
                 _smoothstep(tree, 0.35, 0.70, _vector_math(tree, 'DOT_PRODUCT', n0, down)))
    keep_nose = _math(tree, 'SUBTRACT', 1.0, _math(tree, 'MULTIPLY', inp["Nose Keep"], nose))
    keep_chin = _math(tree, 'SUBTRACT', 1.0, _math(tree, 'MULTIPLY', inp["Chin Keep"], chin))
    weight = _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', inp["Coverage"], region),
                   _math(tree, 'MULTIPLY', keep_nose, keep_chin))
    lean = _vector_math(tree, 'SCALE', _vector_math(tree, 'SUBTRACT', n_e, n0), scale=weight)
    normal = _vector_math(tree, 'NORMALIZE', _vector_math(tree, 'ADD', n0, lean))

    set_normal = nodes.new('GeometryNodeSetMeshNormal')
    set_normal.mode = 'FREE'
    set_normal.domain = 'CORNER'
    links.new(inp["Geometry"], set_normal.inputs["Mesh"])
    links.new(normal, set_normal.inputs["Custom Normal"])
    links.new(set_normal.outputs[0], group_out.inputs["Geometry"])
    return tree


def get_modifier(obj):
    """obj's Face Shading modifier when it runs DaskToon's node group, else None."""
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'NODES' or modifier.node_group is None:
        return None
    return modifier if modifier.node_group.name == GROUP else None


def input_socket(modifier, name):
    """The modifier's input `name`; its `.value` is what the panel's slider shows."""
    identifier = modifier.node_group.interface.items_tree[name].identifier
    return getattr(modifier.properties.inputs, identifier)


def set_inputs(modifier, values):
    """Python writes to modifier inputs neither re-evaluate the object nor rebuild the depsgraph relations (the proxy is
    read through Object Info); assigning the node group again does both."""
    for name, value in values.items():
        input_socket(modifier, name).value = value
    modifier.node_group = modifier.node_group


def ensure_modifier(obj):
    """obj's Face Shading modifier, after the deforming modifiers and right before the outline (face spec 4)."""
    tree = ensure_group()
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'NODES':
        modifier = obj.modifiers.new(MODIFIER_NAME, 'NODES')
    if modifier.node_group != tree:
        modifier.node_group = tree
    outline = obj.modifiers.find(OUTLINE_MODIFIER)
    index = obj.modifiers.find(modifier.name)
    if 0 <= outline < index:
        obj.modifiers.move(index, outline)
    return modifier


def remove_modifier(obj):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is not None:
        obj.modifiers.remove(modifier)
