# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Use DaskToon Shader (docs/superpowers/specs/2026-10-19-dasktoon-model-import-fixes-design.md, section 2): a material
on Principled, Emission, Diffuse or a node group of its own gets an Anime BSDF with its outline, fed the colour or
texture its old shader had; the old nodes stay, only unhooked."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_material_convert as convert  # noqa: E402


def surface(mat):
    out = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    return out.inputs["Surface"].links[0].from_node


def feeder(socket):
    return socket.links[0].from_node if socket.is_linked else None


class ConvertTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def principled(self, name, texture=False, alpha=False):
        mat = tu.new_material(name)
        nt = mat.node_tree
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs["Base Color"].default_value = (0.2, 0.4, 0.6, 1.0)
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        if texture:
            tex = nt.nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.new(name + " image", 4, 4)
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            if alpha:
                nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        return mat

    def test_a_textured_principled_material(self):
        mat = self.principled("Skin", texture=True, alpha=True)
        self.assertTrue(convert.convert(mat))
        anime = surface(mat)
        self.assertEqual(anime.bl_idname, 'ShaderNodeAnimeCharacter')
        self.assertTrue(anime.use_outline)
        self.assertEqual(feeder(anime.inputs["Base Color"]).bl_idname, 'ShaderNodeTexImage')
        self.assertEqual(feeder(anime.inputs["Alpha"]).bl_idname, 'ShaderNodeTexImage')
        shadow = feeder(anime.inputs["Shadow Color"])  # the texture, darker and cooler
        self.assertEqual(feeder(shadow.inputs["A"]).bl_idname, 'ShaderNodeTexImage')
        self.assertTrue(any(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in mat.node_tree.nodes))  # kept

    def test_a_plain_colour(self):
        mat = tu.emission_material("Glow", (0.5, 0.25, 1.0, 1.0))
        self.assertTrue(convert.convert(mat))
        anime = surface(mat)
        self.assertEqual(tuple(anime.inputs["Base Color"].default_value), (0.5, 0.25, 1.0, 1.0))
        shadow = feeder(anime.inputs["Shadow Color"])
        self.assertEqual(tuple(shadow.inputs["A"].default_value), (0.5, 0.25, 1.0, 1.0))

    def test_a_node_group_of_its_own(self):
        """Models made with another toon setup (the five models of the game folder used one called ND_toon): the
        group's first colour input is the colour."""
        group = bpy.data.node_groups.new("My Toon", 'ShaderNodeTree')
        group.interface.new_socket("Strength", in_out='INPUT', socket_type='NodeSocketFloat')
        group.interface.new_socket("skin_color", in_out='INPUT', socket_type='NodeSocketColor')
        group.interface.new_socket("Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
        mat = tu.new_material("Toon")
        nt = mat.node_tree
        node = nt.nodes.new('ShaderNodeGroup')
        node.node_tree = group
        node.inputs["skin_color"].default_value = (0.9, 0.1, 0.1, 1.0)
        nt.links.new(node.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs["Surface"])
        self.assertTrue(convert.convert(mat))
        self.assertEqual([round(c, 5) for c in surface(mat).inputs["Base Color"].default_value], [0.9, 0.1, 0.1, 1.0])

    def test_an_anime_material_is_left_alone(self):
        mat = self.principled("Skin")
        self.assertTrue(convert.convert(mat))
        count = len(mat.node_tree.nodes)
        self.assertFalse(convert.convert(mat))
        self.assertEqual(len(mat.node_tree.nodes), count)

    def test_the_menu_converts_every_material_of_the_selected_objects(self):
        obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(obj, self.principled("A"))
        obj.data.materials.append(tu.emission_material("B", (0, 0, 1, 1)))
        obj.data.materials.append(self.principled("A2"))
        obj.data.materials[2] = obj.data.materials[0]  # the same material twice: once
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        self.assertEqual(bpy.ops.dasktoon.material_to_anime(scope='OBJECTS'), {'FINISHED'})
        self.assertTrue(all(surface(mat).bl_idname == 'ShaderNodeAnimeCharacter' for mat in obj.data.materials))
        funcs = bpy.types.MATERIAL_MT_context_menu.draw._draw_funcs
        self.assertIn(convert.menu_func.__name__, [f.__name__ for f in funcs if f.__module__ == convert.__name__])

    def test_the_active_material_only(self):
        obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(obj, self.principled("A"))
        obj.data.materials.append(tu.emission_material("B", (0, 0, 1, 1)))
        obj.active_material_index = 1
        bpy.context.view_layer.objects.active = obj
        self.assertEqual(bpy.ops.dasktoon.material_to_anime(scope='ACTIVE'), {'FINISHED'})
        self.assertEqual(surface(obj.data.materials[1]).bl_idname, 'ShaderNodeAnimeCharacter')
        self.assertEqual(surface(obj.data.materials[0]).bl_idname, 'ShaderNodeBsdfPrincipled')


if __name__ == "__main__":
    tu.run_tests()
