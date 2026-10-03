# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reading DaskToon materials into MaterialSpec (spec 5): nodes, hair pattern, Reroute, texture sources, render
state, outline and its UV channels."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gamedata  # noqa: E402
from dasktoon_export import graph  # noqa: E402

TMP = tempfile.mkdtemp(prefix="dt_graph_")


def png_image(name, rgba=(0.5, 0.25, 0.75, 1.0), non_color=False):
    img = bpy.data.images.new(name, 4, 4)
    img.pixels = list(rgba) * 16
    path = os.path.join(TMP, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    loaded = bpy.data.images.load(path)
    if non_color:
        loaded.colorspace_settings.name = 'Non-Color'
    return loaded


def sphere_with(mat):
    obj = tu.add_sphere(segments=12, rings=6)
    tu.assign(obj, mat)
    return obj


def analyze(mat, obj):
    return graph.analyze_material(mat, [obj.data])


class NodeTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_anime_bsdf_values_enums_and_modules(self):
        mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        node.use_ambient = True
        node.use_rim = True
        node.ambient_mode = 'HUE'
        node.light_blend_mode = 'MULTIPLY'
        node.inputs["Base Color"].default_value = (0.5, 0.2, 0.1, 1.0)
        node.inputs["Shadow Threshold"].default_value = 0.3
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.shader, "AnimeBSDF")
        for got, want in zip(spec.colors["_BaseColor"], (0.5, 0.2, 0.1, 1.0)):
            self.assertAlmostEqual(got, want, places=5)
        self.assertAlmostEqual(spec.floats["_DT_ShadowThreshold"], 0.3, places=5)
        self.assertEqual(spec.floats["_DT_AmbientMode"], 1.0)
        self.assertEqual(spec.floats["_DT_LightMode"], 2.0)
        self.assertTrue({"_DT_AMBIENT", "_DT_RIM"} <= spec.keywords)
        self.assertNotIn("_DT_LIGHT", spec.keywords)
        self.assertEqual(spec.floats["_DT_UseAmbient"], 1.0)
        self.assertEqual(spec.floats["_DT_UseLight"], 0.0)
        self.assertNotIn("_DT_UseAngelRing", spec.floats)

    def test_ramp_mode(self):
        mat, node = tu.node_material("Ramp", 'ShaderNodeDaskCel')
        node.shading_mode = 'RAMP'
        node.shading_ramp.interpolation = 'CONSTANT'
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertIn("_DT_RAMP", spec.keywords)
        self.assertEqual(spec.ramp, node.shading_ramp)
        self.assertEqual(spec.floats["_DT_RampConstant"], 1.0)
        self.assertEqual(spec.floats["_DT_UseRamp"], 1.0)

    def test_each_node_has_its_shader(self):
        for idname, shader in (('ShaderNodeAnimeCel', "AnimeCel"), ('ShaderNodeAnimeEye', "AnimeEye"),
                               ('ShaderNodeDaskCel', "DaskCel")):
            mat, _node = tu.node_material(idname, idname)
            spec, _ = analyze(mat, sphere_with(mat))
            self.assertEqual(spec.shader, shader)
        cel_mat, _ = tu.node_material("Cel", 'ShaderNodeAnimeCel')
        spec, _ = analyze(cel_mat, sphere_with(cel_mat))
        self.assertEqual(spec.floats["_DT_EmissionStrength"], 1.0)

    def test_eye_uv_input(self):
        mat, node = tu.node_material("Eye", 'ShaderNodeAnimeEye')
        obj = sphere_with(mat)
        spec, _ = analyze(mat, obj)
        self.assertEqual(spec.floats["_DT_EyeUseUV"], 0.0)
        coords = mat.node_tree.nodes.new('ShaderNodeTexCoord')
        mat.node_tree.links.new(coords.outputs["UV"], node.inputs["UV Vector"])
        spec, _ = analyze(mat, obj)
        self.assertEqual(spec.floats["_DT_EyeUseUV"], 1.0)
        self.assertEqual(spec.warnings, [])

    def test_hair_pattern(self):
        mat = tu.new_material("Hair")
        nt = mat.node_tree
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        emission = nt.nodes.new('ShaderNodeEmission')
        emission.inputs["Strength"].default_value = 2.0
        cel = nt.nodes.new('ShaderNodeAnimeCel')
        ring = nt.nodes.new('ShaderNodeAnimeAngelRing')
        ring.inputs["Intensity"].default_value = 0.8
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'ADD'
        sockets = {s.identifier: s for s in mix.inputs}
        nt.links.new(cel.outputs["Color"], sockets["A_Color"])
        nt.links.new(ring.outputs["Color"], sockets["B_Color"])
        nt.links.new(ring.outputs["Fac"], sockets["Factor_Float"])
        nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), emission.inputs["Color"])
        nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.shader, "AnimeCel")
        self.assertIn("_DT_ANGEL_RING", spec.keywords)
        self.assertEqual(spec.floats["_DT_EmissionStrength"], 2.0)
        self.assertAlmostEqual(spec.floats["_DT_RingIntensity"], 0.8, places=5)
        self.assertEqual(spec.floats["_DT_RingClampFactor"], 1.0)
        self.assertEqual(spec.floats["_DT_UseAngelRing"], 1.0)

    def test_reroutes_are_followed(self):
        mat, node = tu.node_material("Rerouted", 'ShaderNodeAnimeCharacter')
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        r1, r2 = nt.nodes.new('NodeReroute'), nt.nodes.new('NodeReroute')
        nt.links.new(node.outputs["BSDF"], r1.inputs[0])
        nt.links.new(r1.outputs[0], r2.inputs[0])
        nt.links.new(r2.outputs[0], out.inputs["Surface"])
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("reroute_tex")
        r3 = nt.nodes.new('NodeReroute')
        nt.links.new(tex.outputs["Color"], r3.inputs[0])
        nt.links.new(r3.outputs[0], node.inputs["Base Color"])
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.textures["_BaseMap"].kind, 'IMAGE')

    def test_unsupported_material(self):
        # DaskToon's default new material uses Anime BSDF, so build a Principled one explicitly.
        mat, _node = tu.node_material("Principled", 'ShaderNodeBsdfPrincipled')
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertIsNone(spec)
        self.assertIn("ShaderNodeBsdfPrincipled", reason)
        self.assertEqual(graph.analyze_material(None, []), (None, "slot trống"))


class SourceTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.mat, self.node = tu.node_material("Src", 'ShaderNodeAnimeCharacter')
        self.nt = self.mat.node_tree
        self.obj = sphere_with(self.mat)

    def test_direct_image_is_copied(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("direct")
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        spec, _ = analyze(self.mat, self.obj)
        src = spec.textures["_BaseMap"]
        self.assertEqual(src.kind, 'IMAGE')
        self.assertTrue(src.color)
        self.assertEqual(src.image, tex.image)
        self.assertEqual(spec.floats["_DT_BaseMapOn"], 1.0)
        self.assertEqual(spec.colors["_BaseColor"], (1.0, 1.0, 1.0, 1.0))

    def test_non_color_image_is_data(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("mask", non_color=True)
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Shadow Threshold"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertFalse(spec.textures["_DT_ShadowThresholdMap"].color)
        self.assertEqual(spec.floats["_DT_ShadowThreshold"], 1.0)

    def test_mapping_branch_is_baked(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("mapped")
        mapping = self.nt.nodes.new('ShaderNodeMapping')
        coords = self.nt.nodes.new('ShaderNodeTexCoord')
        self.nt.links.new(coords.outputs["UV"], mapping.inputs["Vector"])
        self.nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        spec, _ = analyze(self.mat, self.obj)
        src = spec.textures["_BaseMap"]
        self.assertEqual(src.kind, 'BAKE')
        self.assertEqual((src.node, src.socket, src.tree_owner), (self.node.name, "Base Color", self.mat))

    def test_light_dependent_branch_warns_and_keeps_value(self):
        self.node.inputs["Shadow Color"].default_value = (0.3, 0.2, 0.1, 1.0)
        mix = self.nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        fresnel = self.nt.nodes.new('ShaderNodeFresnel')
        self.nt.links.new(fresnel.outputs["Fac"], next(s for s in mix.inputs if s.identifier == "Factor_Float"))
        self.nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), self.node.inputs["Shadow Color"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertNotIn("_DT_ShadowColorMap", spec.textures)
        self.assertAlmostEqual(spec.colors["_DT_ShadowColor"][0], 0.3, places=5)
        self.assertTrue(any("Shadow Color" in w and "Fresnel" in w for w in spec.warnings), spec.warnings)

    def test_linked_input_without_texture_slot_warns(self):
        self.node.use_rim = True
        self.node.inputs["Rim Fresnel Power"].default_value = 3.0
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], self.node.inputs["Rim Fresnel Power"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertEqual(spec.floats["_DT_RimPower"], 3.0)
        self.assertTrue(any("Rim Fresnel Power" in w for w in spec.warnings))

    def test_hidden_module_inputs_are_not_read_for_links(self):
        power = next(s for s in self.node.inputs if s.name == "Rim Fresnel Power")
        power.default_value = 2.5
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], power)
        spec, _ = analyze(self.mat, self.obj)
        self.assertFalse(any("Rim Fresnel Power" in w for w in spec.warnings))
        self.assertEqual(spec.floats["_DT_RimPower"], 2.5)

    def test_normal_map(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("normal", (0.5, 0.5, 1.0, 1.0), non_color=True)
        normal_map = self.nt.nodes.new('ShaderNodeNormalMap')
        normal_map.inputs["Strength"].default_value = 0.6
        self.nt.links.new(tex.outputs["Color"], normal_map.inputs["Color"])
        self.nt.links.new(normal_map.outputs["Normal"], self.node.inputs["Normal"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertEqual(spec.textures["_DT_NormalMap"].kind, 'NORMAL')
        self.assertIn("_DT_NORMALMAP", spec.keywords)
        self.assertAlmostEqual(spec.floats["_DT_NormalStrength"], 0.6, places=5)
        self.assertEqual(spec.floats["_DT_UseNormalMap"], 1.0)


class RenderStateTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_blended_is_transparent(self):
        mat, _node = tu.node_material("Glass", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'BLENDED'
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual((spec.queue, spec.render_type), (3000, "Transparent"))
        self.assertEqual((spec.floats["_SrcBlend"], spec.floats["_DstBlend"], spec.floats["_ZWrite"]), (5.0, 10.0, 0.0))

    def test_dithered_alpha_below_one_clips(self):
        mat, node = tu.node_material("Lash", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'DITHERED'
        node.inputs["Alpha"].default_value = 0.5
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertIn("_DT_ALPHATEST_ON", spec.keywords)
        self.assertEqual(spec.floats["_AlphaClip"], 1.0)
        self.assertEqual(spec.queue, -1)
        opaque, _ = analyze(*(lambda m: (m, sphere_with(m)))(tu.node_material("Opaque", 'ShaderNodeAnimeCharacter')[0]))
        self.assertNotIn("_DT_ALPHATEST_ON", opaque.keywords)
        self.assertEqual(opaque.floats["_SrcBlend"], 1.0)

    def test_backface_culling_sets_cull(self):
        mat, _node = tu.node_material("Cull", 'ShaderNodeDaskCel')
        mat.use_backface_culling = True
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_Cull"], 2.0)
        mat.use_backface_culling = False
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_Cull"], 0.0)


class OutlineTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_no_outline_disables_the_pass(self):
        mat, _node = tu.node_material("Plain", 'ShaderNodeAnimeCharacter')
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.disabled_passes, ["SRPDefaultUnlit"])
        self.assertEqual(spec.floats["_DT_UseOutline"], 0.0)
        self.assertFalse(spec.outline)

    def test_outline_parameters_and_uv_channels(self):
        mat, node = tu.node_material("Lined", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        node.inputs["Outline Width"].default_value = 0.004
        node.outline_tint_mode = 'HARMONIC_KYOTO'
        obj = sphere_with(mat)
        outline.sync_material(mat)
        companion = outline.outline_material_for(mat)
        outline.outline_node(companion).inputs["Light Bleed"].default_value = 0.3
        ok, _msg = gamedata.write_outline_uvs(obj)
        self.assertTrue(ok)
        spec, _ = analyze(mat, obj)
        self.assertIn("_DT_OUTLINE", spec.keywords)
        self.assertEqual(spec.disabled_passes, [])
        self.assertAlmostEqual(spec.floats["_DT_OutlineWidth"], 0.004, places=6)
        self.assertAlmostEqual(spec.floats["_DT_OutlineLightBleed"], 0.3, places=5)
        self.assertEqual(spec.floats["_DT_OutlineTintMode"], 1.0)
        self.assertEqual(spec.floats["_DT_OutlineUV"], float(obj.data.uv_layers.find("DT_OutlineN")))
        self.assertEqual(spec.floats["_DT_OutlineWUV"], float(obj.data.uv_layers.find("DT_OutlineW")))
        self.assertEqual(spec.floats["_DT_OutlineUV"], 1.0)

    def test_missing_outline_data_falls_back_to_mesh_normal(self):
        mat, node = tu.node_material("NoData", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_DT_OutlineUV"], -1.0)
        self.assertTrue(any("DT_OutlineN" in w for w in spec.warnings))

    def test_meshes_with_different_uv_order_warn(self):
        mat, node = tu.node_material("Shared", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        a = sphere_with(mat)
        b = sphere_with(mat)
        b.data.uv_layers.new(name="Extra")
        for obj in (a, b):
            gamedata.write_outline_uvs(obj)
        spec, _ = graph.analyze_material(mat, [a.data, b.data])
        self.assertTrue(any("thứ tự UV" in w for w in spec.warnings), spec.warnings)

    def test_companion_is_recognised(self):
        mat, node = tu.node_material("Owner", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        outline.sync_material(mat)
        self.assertTrue(graph.is_outline_companion(outline.outline_material_for(mat)))
        self.assertFalse(graph.is_outline_companion(mat))


if __name__ == "__main__":
    tu.run_tests()
