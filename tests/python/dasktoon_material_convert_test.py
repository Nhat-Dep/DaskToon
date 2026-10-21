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


def flat_texture(nt, value):
    """An image texture of one colour, read as it is stored (Non-Color)."""
    image = bpy.data.images.new("Flat %g" % value, 4, 4)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set([value, value, value, 1.0] * 16)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = image
    return tex


def multiply(nt, a, b):
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(a, mix.inputs["A"])
    nt.links.new(b, mix.inputs["B"])
    return next(s for s in mix.outputs if s.identifier == "Result_Color")


def toon_group():
    """luna's kind of toon group: Diffuse -> Shader to RGB -> a two-step ramp (dark blue below 0.3, white above), times
    the colour."""
    group = bpy.data.node_groups.new("Own Toon", 'ShaderNodeTree')
    group.interface.new_socket("Color", in_out='INPUT', socket_type='NodeSocketColor')
    group.interface.new_socket("Result", in_out='OUTPUT', socket_type='NodeSocketColor')
    gn = group.nodes
    inp, out = gn.new('NodeGroupInput'), gn.new('NodeGroupOutput')
    diffuse, to_rgb, ramp = gn.new('ShaderNodeBsdfDiffuse'), gn.new('ShaderNodeShaderToRGB'), gn.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = (0.1, 0.1, 0.2, 1.0)
    ramp.color_ramp.elements[1].position = 0.3
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    group.links.new(inp.outputs["Color"], diffuse.inputs["Color"])
    group.links.new(diffuse.outputs["BSDF"], to_rgb.inputs["Shader"])
    group.links.new(to_rgb.outputs["Color"], ramp.inputs["Fac"])
    group.links.new(multiply(group, ramp.outputs["Color"], inp.outputs["Color"]), out.inputs["Result"])
    return group


class OwnLookTest(unittest.TestCase):
    """A model shaded by a node setup of its own that shows a colour (luna: two toon groups, each multiplying the
    texture by itself): the Anime BSDF gets that colour as it looks lit (Base Color) and in shadow (Shadow Color), the
    light the setup reads replaced by the scene's Sun and World; the texture alone made luna's black dress grey."""

    def setUp(self):
        tu.reset_scene()
        tu.add_sun(3.0)  # straight down: lights the plane with 3 / pi
        bpy.ops.mesh.primitive_plane_add(size=4.0)
        self.plane = bpy.context.active_object

    def shown(self, mat, socket):
        """The linear colour `socket` gives, rendered as emission on the plane facing the camera."""
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        before = out.inputs["Surface"].links[0].from_socket
        emission = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(socket, emission.inputs["Color"])
        nt.links.new(emission.outputs[0], out.inputs["Surface"])
        try:
            return tu.render_center("own_look_%s" % mat.name)[:3]
        finally:
            nt.links.new(before, out.inputs["Surface"])
            nt.nodes.remove(emission)

    def own(self, name, build):
        mat = tu.new_material(name)
        nt = mat.node_tree
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(build(nt), out.inputs["Surface"])
        tu.assign(self.plane, mat)
        return mat

    def assert_colour(self, got, want, places=2):
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=places, msg=(got, want))

    def test_colour_times_itself_stays_dark(self):
        def build(nt):
            tex = flat_texture(nt, 0.6)
            return multiply(nt, tex.outputs["Color"], tex.outputs["Color"])
        mat = self.own("Squared", build)
        self.assertTrue(convert.convert(mat))
        anime = surface(mat)
        base = anime.inputs["Base Color"].links[0].from_socket
        self.assert_colour(self.shown(mat, base), (0.36, 0.36, 0.36))
        shadow = anime.inputs["Shadow Color"].links[0].from_socket
        self.assert_colour(self.shown(mat, shadow), tuple(0.36 * c for c in convert.SHADOW))

    def test_an_own_toon_group_gives_its_lit_and_shadow_colours(self):
        group = toon_group()

        def build(nt):
            node = nt.nodes.new('ShaderNodeGroup')
            node.node_tree = group
            nt.links.new(flat_texture(nt, 0.6).outputs["Color"], node.inputs["Color"])
            return node.outputs["Result"]
        mat = self.own("Toon Look", build)
        self.assertTrue(convert.convert(mat))
        anime = surface(mat)
        base = anime.inputs["Base Color"].links[0].from_socket
        shadow = anime.inputs["Shadow Color"].links[0].from_socket
        self.assert_colour(self.shown(mat, base), (0.6, 0.6, 0.6))  # lit: 0.6 x 3/pi reads above 0.3
        self.assert_colour(self.shown(mat, shadow), (0.06, 0.06, 0.12))  # no light: the dark blue step
        from dasktoon_export import graph
        self.assertIsNone(graph.light_dependency(base))  # an export can bake it
        self.assertIsNone(graph.light_dependency(shadow))
        self.assertTrue(any(n.bl_idname == 'ShaderNodeShaderToRGB' for n in group.nodes))  # the group as it was


if __name__ == "__main__":
    tu.run_tests()
