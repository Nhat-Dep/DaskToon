# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Create legacy .blend fixtures with the PRE-CHANGE DaskToon build (run once, then commit the files).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_make_legacy_fixtures.py
"""

import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dasktoon_data")


def _node(mat, idname):
    return next(n for n in mat.node_tree.nodes if n.bl_idname == idname)


def nodes_fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for idname in ('ShaderNodeAnimeCharacter', 'ShaderNodeAnimeCel', 'ShaderNodeDaskCel'):
        mat = bpy.data.materials.new("Legacy_" + idname[len("ShaderNode"):])
        mat.use_fake_user = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        node = nt.nodes.new(idname)
        nt.links.new(node.outputs[0], out.inputs["Surface"])
    bsdf = _node(bpy.data.materials["Legacy_AnimeCharacter"], 'ShaderNodeAnimeCharacter')
    bsdf.use_ambient = True
    bsdf.use_rim = True
    bsdf.ambient_mode = 'HUE'
    bsdf.outline_tint_mode = 'LIGHT_REACTIVE'
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "dasktoon_legacy_nodes.blend"), compress=True)


def outline_fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_uv_sphere_add()
    hero = bpy.context.active_object
    hero.name = "Hero"
    mat = bpy.data.materials.new("Skin")
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new('ShaderNodeAnimeCharacter')
    node.use_outline = True
    node.inputs["Outline Width"].default_value = 0.004
    node.inputs["Outline Color"].default_value = (0.3, 0.1, 0.05, 1.0)
    nt.links.new(node.outputs[0], out.inputs["Surface"])
    hero.data.materials.append(mat)
    bpy.context.view_layer.update()  # legacy handler: Solidify + Hero_DaskOutline slot
    for i in range(20):
        dup = hero.copy()  # linked duplicate: shares the mesh (bug #3 slot explosion)
        dup.name = "HeroDup%02d" % i
        scene.collection.objects.link(dup)
    bpy.context.view_layer.update()
    print("legacy slots:", len(hero.data.materials), "modifiers:", [m.name for m in hero.modifiers])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "dasktoon_legacy_outline.blend"), compress=True)


os.makedirs(OUT, exist_ok=True)
nodes_fixture()
outline_fixture()
