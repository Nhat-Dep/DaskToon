# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Materials DaskToon's exporter cannot read (a toon shader of another maker, a group node): the model would reach a
player with glTF's plain white. Meanwhile the .dlive export, each such material is baked as it shines (an emission bake
of its whole surface, over the UV map of the meshes using it) and stands in as a DaskToon material wearing that picture,
named as the original; a material that gives no light of its own (a Principled one: glTF carries it) is left alone. The
file's materials are given back afterwards."""

import contextlib
import os
import tempfile

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
import numpy as np

DARK = 0.01  # a bake whose brightest pixel is below this shines nothing: the material is not an emitter


def _surface_linked(mat):
    return bool(mat is not None and mat.use_nodes and mat.node_tree is not None and any(
        n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output and n.inputs["Surface"].is_linked
        for n in mat.node_tree.nodes))


def _bake_whole(objs, material, size):
    """Float RGBA pixels (size x size, rows bottom-up) of what `material` emits over the UVs of `objs` using it."""
    from dasktoon_export import bake
    scene, view_layer = bpy.context.scene, bpy.context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    engine, samples, device = scene.render.engine, scene.cycles.samples, scene.cycles.device
    image = copy = mesh = temp = None
    try:
        for obj in objs:
            if not obj.data.uv_layers:
                raise RuntimeError(rpt_("Mesh %s has no UV map to bake") % obj.name)
        image = bpy.data.images.new("DT_Fallback", size, size, alpha=True, float_buffer=True, is_data=True)
        copy = material.copy()
        bake._strip_outline(copy)
        tex = copy.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        for node in copy.node_tree.nodes:
            node.select = False
        tex.select = True
        copy.node_tree.nodes.active = tex
        mesh = bake._users_mesh(objs, material)
        mesh.materials.clear()
        mesh.materials.append(copy)
        for poly in mesh.polygons:
            poly.material_index = 0
        mesh.uv_layers.active_index = 0
        temp = bpy.data.objects.new("DT_FallbackObject", mesh)
        scene.collection.objects.link(temp)
        for o in selected:
            o.select_set(False)
        temp.select_set(True)
        view_layer.objects.active = temp
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 1
        scene.cycles.device = 'CPU'
        bpy.ops.object.bake(type='EMIT', margin=bake.MARGIN, margin_type='EXTEND', use_clear=True,
                            target='IMAGE_TEXTURES')
        pixels = np.empty(size * size * 4, np.float32)
        image.pixels.foreach_get(pixels)
        return pixels
    finally:
        if temp is not None:
            bpy.data.objects.remove(temp)
        if mesh is not None:
            bpy.data.meshes.remove(mesh)
        if copy is not None:
            bpy.data.materials.remove(copy)
        if image is not None:
            bpy.data.images.remove(image)
        scene.render.engine = engine
        scene.cycles.samples = samples
        scene.cycles.device = device
        for o in view_layer.objects:
            try:
                o.select_set(o in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active


def _stand_in(name, pixels, size, folder):
    """A DaskToon material `name` whose colour is the baked picture (a packed PNG), and the picture."""
    from dasktoon_export import textures
    path = os.path.join(folder, "fallback_%d.png" % len(os.listdir(folder)))
    with open(path, "wb") as f:
        f.write(textures.float_to_png(pixels, size, size, True))
    image = bpy.data.images.load(path)
    image.pack()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    node = tree.nodes.new('ShaderNodeAnimeCharacter')
    node.use_outline = False
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
    tree.links.new(tex.outputs["Color"], node.inputs["Shadow Color"])  # a baked look carries its own shading
    tree.links.new(next(s for s in node.outputs if s.enabled), out.inputs["Surface"])
    return mat, image


@contextlib.contextmanager
def baked(objects, size, warnings):
    """Swaps each material the exporter cannot read for a DaskToon one wearing its baked look while the block runs;
    yields the names of the materials swapped. `warnings` gets a line for a bake that failed."""
    from dasktoon_export import graph, _materials
    swapped = []  # (mesh, slot, original material, original's name)
    made = []  # (material, image)
    folder = tempfile.mkdtemp(prefix="dlive_fb_")
    try:
        meshes = [o for o in objects if o.type == 'MESH']
        for mat, users in _materials(meshes).items():
            if mat is None or not _surface_linked(mat) or graph.analyze_material(mat, list({o.data: o for o in users}))[0]:
                continue
            try:
                pixels = _bake_whole(users, mat, size)
            except Exception as ex:
                warnings.append(rpt_("Material %s: bake failed (%s)") % (mat.name, ex))
                continue
            if float(pixels.reshape(-1, 4)[:, :3].max()) < DARK:
                continue
            original = mat.name
            mat.name = original + " (original)"
            stand, image = _stand_in(original, pixels, size, folder)
            made.append((stand, image))
            for obj in {o.data: o for o in users}.values():
                for index, slot_material in enumerate(obj.data.materials):
                    if slot_material == mat:
                        obj.data.materials[index] = stand
                        swapped.append((obj.data, index, mat, original))
        yield [name for _m, _i, _mat, name in swapped]
    finally:
        for mesh, index, mat, _original in swapped:
            mesh.materials[index] = mat
        for stand, image in made:
            bpy.data.materials.remove(stand)
            bpy.data.images.remove(image)
        for _mesh, _index, mat, original in swapped:
            mat.name = original
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
