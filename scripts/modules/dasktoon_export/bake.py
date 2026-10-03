# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bake a node branch to pixels with Cycles Emit on throwaway data (spec 5). The user's selection, active object,
render engine and samples are restored and every temporary datablock is removed, also on error."""

import bmesh
import bpy
import numpy as np

from .graph import follow

MARGIN = 16


def _input(tree, node_name, socket_identifier):
    node = tree.nodes[node_name]
    return next(s for s in node.inputs if s.identifier == socket_identifier)


def branch_size(tree_owner, node_name, socket_identifier, default):
    """Bake resolution: the largest image in the branch, else `default` (spec 5)."""
    size = 0
    seen = set()
    stack = [follow(_input(tree_owner.node_tree, node_name, socket_identifier))]
    while stack:
        out = stack.pop()
        if out is None or out.node.as_pointer() in seen:
            continue
        seen.add(out.node.as_pointer())
        if out.node.bl_idname == 'ShaderNodeTexImage' and out.node.image is not None:
            size = max(size, *out.node.image.size)
        stack.extend(follow(s) for s in out.node.inputs if s.enabled)
    return size or default


def _faces_mesh(obj, material):
    """A copy of obj's mesh keeping only the faces that use `material`."""
    slot = next(i for i, s in enumerate(obj.material_slots) if s.material == material)
    mesh = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != slot], context='FACES')
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _bake_material(source, image):
    """A copy of the branch's material whose only output is Emission(branch) and whose active node is `image`."""
    mat = source.tree_owner.copy()
    tree = mat.node_tree
    upstream = follow(_input(tree, source.node, source.socket))
    for node in tree.nodes:
        if node.bl_idname == 'ShaderNodeOutputMaterial':
            node.is_active_output = False
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.target = 'ALL'
    output.is_active_output = True
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs["Strength"].default_value = 1.0
    tree.links.new(upstream, emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    for node in tree.nodes:
        node.select = False
    tex.select = True
    tree.nodes.active = tex
    return mat


def bake_input(obj, material, source, size, samples):
    """Float RGBA pixels (size x size, rows bottom-up) of the branch feeding source.node / source.socket in
    source.tree_owner's tree, baked on the faces of `obj` that use `material`, over the first UV map."""
    if not obj.data.uv_layers:
        raise RuntimeError("mesh %s không có UV map để bake" % obj.name)
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    engine, samples_before, device = scene.render.engine, scene.cycles.samples, scene.cycles.device
    temp_obj = mesh = mat = image = None
    try:
        image = bpy.data.images.new("DT_Bake", size, size, alpha=True, float_buffer=True, is_data=True)
        mat = _bake_material(source, image)
        mesh = _faces_mesh(obj, material)
        mesh.materials.clear()
        mesh.materials.append(mat)
        for poly in mesh.polygons:
            poly.material_index = 0
        mesh.uv_layers.active_index = 0
        temp_obj = bpy.data.objects.new("DT_BakeObject", mesh)
        temp_obj.matrix_world = obj.matrix_world
        scene.collection.objects.link(temp_obj)
        if mesh.shape_keys is not None:
            temp_obj.shape_key_clear()
        for o in selected:
            o.select_set(False)
        temp_obj.select_set(True)
        view_layer.objects.active = temp_obj
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.device = 'CPU'
        bpy.ops.object.bake(type='EMIT', margin=MARGIN, margin_type='EXTEND', use_clear=True,
                            target='IMAGE_TEXTURES')
        pixels = np.empty(size * size * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        return pixels
    finally:
        if temp_obj is not None:
            bpy.data.objects.remove(temp_obj)
        if mesh is not None:
            bpy.data.meshes.remove(mesh)
        if mat is not None:
            bpy.data.materials.remove(mat)
        if image is not None:
            bpy.data.images.remove(image)
        scene.render.engine = engine
        scene.cycles.samples = samples_before
        scene.cycles.device = device
        for o in view_layer.objects:
            try:
                o.select_set(o in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active
