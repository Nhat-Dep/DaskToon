# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The `dasktoon` block of a materials.json entry (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md): what
DaskToon needs to rebuild a material on import - the node, its settings, its input values and its textures. DaskLive
ignores it. The shader values of the entry itself come from the Godot export's writer."""

import os

import bpy

from dasktoon_export import graph
from dasktoon_export.godot import materials as godot_materials

_NODE_BASE = {p.identifier for p in bpy.types.Node.bl_rna.properties}
_SIMPLE = {'BOOLEAN', 'INT', 'FLOAT', 'ENUM', 'STRING'}


def _plain(value):
    if isinstance(value, (bool, int, float, str)):
        return value
    return [float(v) for v in value]


def _settings(node):
    """The node's own settings (not its inputs): use_outline, shading_mode and the like."""
    out = {}
    for prop in node.bl_rna.properties:
        if prop.identifier in _NODE_BASE or prop.is_readonly or prop.type not in _SIMPLE:
            continue
        if prop.type == 'ENUM' and prop.is_enum_flag:
            continue
        value = getattr(node, prop.identifier)
        out[prop.identifier] = _plain(value) if not hasattr(value, "__len__") or isinstance(value, str) else list(value)
    return out


def block(spec, textures):
    """The `dasktoon` block of `spec` (graph.MaterialSpec); `textures` {Godot uniform: archive path} of what was
    written."""
    source = graph._surface(spec.material)
    node = source.node
    inputs = {}
    for sock in node.inputs:
        if hasattr(sock, "default_value") and sock.type != 'SHADER':
            inputs[sock.identifier] = _plain(sock.default_value)
    out = {"node": node.bl_idname, "settings": _settings(node), "inputs": inputs, "textures": []}
    for prop, src in sorted(spec.textures.items()):
        path = textures.get(godot_materials.godot_name(prop))
        if path is None:
            continue
        entry = {"socket": src.socket, "kind": src.kind, "color": bool(src.color), "path": path}
        if src.kind == 'NORMAL':
            entry["strength"] = float(spec.floats.get("_DT_NormalStrength", 1.0))
        out["textures"].append(entry)
    ramp = getattr(node, "shading_ramp", None)
    if ramp is not None and getattr(node, "shading_mode", "") == 'RAMP':
        out["ramp"] = {"interpolation": ramp.interpolation,
                       "elements": [[e.position, [float(c) for c in e.color]] for e in ramp.elements]}
    return out


def rebuild(mat, data, folder):
    """Make `mat`'s node tree from a `dasktoon` block; images are loaded from `folder` (archive paths under it) and
    packed. Returns the node."""
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    node = tree.nodes.new(data["node"])
    for name, value in data.get("settings", {}).items():
        try:
            setattr(node, name, value)
        except (AttributeError, TypeError, ValueError):
            pass
    for sock in node.inputs:
        if sock.identifier in data.get("inputs", {}) and hasattr(sock, "default_value"):
            try:
                sock.default_value = data["inputs"][sock.identifier]
            except (TypeError, ValueError):
                pass
    out_socket = node.outputs.get("BSDF") or node.outputs[0]
    tree.links.new(out_socket, output.inputs["Surface"])
    ramp = data.get("ramp")
    if ramp is not None and getattr(node, "shading_ramp", None) is not None:
        target = node.shading_ramp
        target.interpolation = ramp["interpolation"]
        while len(target.elements) > len(ramp["elements"]):
            target.elements.remove(target.elements[-1])
        while len(target.elements) < len(ramp["elements"]):
            target.elements.new(1.0)
        for element, (position, color) in zip(target.elements, ramp["elements"]):
            element.position, element.color = position, color
    for tex in data.get("textures", []):
        path = os.path.join(folder, *tex["path"].split("/"))
        if not os.path.isfile(path):
            continue
        image = bpy.data.images.load(path, check_existing=False)
        image.colorspace_settings.name = 'sRGB' if tex.get("color") else 'Non-Color'
        image.pack()
        image_node = tree.nodes.new('ShaderNodeTexImage')
        image_node.image = image
        socket = next((s for s in node.inputs if s.identifier == tex["socket"]), None)
        if tex["kind"] == 'NORMAL':
            normal = tree.nodes.new('ShaderNodeNormalMap')
            normal.inputs["Strength"].default_value = tex.get("strength", 1.0)
            tree.links.new(image_node.outputs["Color"], normal.inputs["Color"])
            socket = node.inputs.get("Normal")
            if socket is not None:
                tree.links.new(normal.outputs["Normal"], socket)
        elif socket is not None:
            tree.links.new(image_node.outputs["Color"], socket)
    return node
