# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

WEIGHT_NODES = (
    'ShaderNodeAnimeCharacter', 'ShaderNodeArtistLineModulation', 'ShaderNodeDaskAmbient',
    'ShaderNodeDaskAO', 'ShaderNodeDaskCel', 'ShaderNodeDaskGrade', 'ShaderNodeDaskLight',
    'ShaderNodeDaskOutline',
)


class MixShaderWeightTest(unittest.TestCase):
    def test_factor_one_hides_dasktoon_node(self):
        for node_type in WEIGHT_NODES:
            with self.subTest(node=node_type):
                tu.reset_scene()
                plane = tu.add_plane()
                tu.add_sun(3.0)
                tu.set_world_color((0.2, 0.2, 0.2))
                alone_mat, _node = tu.node_material("Alone", node_type)
                tu.assign(plane, alone_mat)
                alone = tu.render_center("weight_alone_" + node_type)
                self.assertFalse(tu.is_shader_error(alone), "shader failed to compile (magenta)")
                self.assertGreater(max(alone[:3]), 0.02, "renders black on its own; weight cannot be judged")
                mixed_mat, _node = tu.mix_with_black_material("Mixed", node_type)
                tu.assign(plane, mixed_mat)
                mixed = tu.render_center("weight_mixed_" + node_type)
                self.assertLess(max(mixed[:3]), 0.01)


class AnimeBsdfAlphaTest(unittest.TestCase):
    def test_alpha_controls_transparency(self):
        tu.reset_scene()
        bpy.context.scene.render.film_transparent = True
        plane = tu.add_plane()
        tu.add_sun(3.0)
        mat, node = tu.node_material("Alpha", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'BLENDED'
        tu.assign(plane, mat)
        node.inputs["Alpha"].default_value = 0.0
        self.assertLess(tu.render_center("alpha_0")[3], 0.01)
        node.inputs["Alpha"].default_value = 1.0
        self.assertGreater(tu.render_center("alpha_1")[3], 0.99)


SHADING_NODES = ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel', 'ShaderNodeAnimeCel')


class ShadingModeTest(unittest.TestCase):
    def test_rna_and_socket_visibility(self):
        tu.reset_scene()
        for node_type in SHADING_NODES:
            with self.subTest(node=node_type):
                _mat, node = tu.node_material("M", node_type)
                self.assertEqual(node.shading_mode, 'SIMPLE')
                self.assertIsNotNone(node.shading_ramp)
                def socket(identifier):
                    # Name lookups skip unavailable sockets, so search all inputs by identifier.
                    return next(s for s in node.inputs if s.identifier == identifier)
                self.assertTrue(socket("Shadow Color").enabled)
                node.shading_mode = 'RAMP'
                self.assertFalse(socket("Shadow Color").enabled)
                self.assertFalse(socket("Shadow Softness").enabled)
                self.assertTrue(socket("Shadow Threshold").enabled)

    def test_ramp_mode_is_base_times_ramp(self):
        for node_type in SHADING_NODES:
            with self.subTest(node=node_type):
                tu.reset_scene()
                plane = tu.add_plane()
                sun = tu.add_sun(0.3 * math.pi)  # light = 0.3 at the plane centre (world is black)
                mat, node = tu.node_material("R", node_type)
                tu.assign(plane, mat)
                node.shading_mode = 'RAMP'
                ramp = node.shading_ramp
                ramp.interpolation = 'CONSTANT'
                ramp.elements[0].position = 0.0
                ramp.elements[0].color = (0.5, 0.25, 0.25, 1.0)
                ramp.elements[1].position = 0.5
                ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
                node.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
                node.inputs["Shadow Threshold"].default_value = 0.5
                if node_type == 'ShaderNodeAnimeCel':
                    node.inputs["Specular Color"].default_value = (0.0, 0.0, 0.0, 1.0)
                    node.light_blend_mode = 'PURE_CEL'
                dark = tu.render_center("ramp_dark_" + node_type)  # t = 0.3 -> first stop
                self.assertAlmostEqual(dark[0], 0.5, delta=0.01)
                self.assertAlmostEqual(dark[1], 0.25, delta=0.01)
                sun.data.energy = 0.8 * math.pi  # t = 0.8 -> white
                lit = tu.render_center("ramp_lit_" + node_type)
                self.assertAlmostEqual(lit[0], 1.0, delta=0.01)
                self.assertAlmostEqual(lit[1], 1.0, delta=0.01)


class LightModeTest(unittest.TestCase):
    def test_light_blend_mode_keeps_other_settings(self):
        tu.reset_scene()
        _mat, node = tu.node_material("L", 'ShaderNodeAnimeCharacter')
        node.use_ambient = True
        node.use_rim = True
        node.ambient_mode = 'HUE'
        node.outline_tint_mode = 'LIGHT_REACTIVE'
        for mode in ('HUE', 'MULTIPLY', 'ADD', 'PURE_CEL', 'OVERLAY', 'ADD'):
            node.light_blend_mode = mode
            self.assertEqual(node.light_blend_mode, mode)
            self.assertTrue(node.use_ambient)
            self.assertTrue(node.use_rim)
            self.assertFalse(node.use_light)
            self.assertEqual(node.ambient_mode, 'HUE')
            self.assertEqual(node.outline_tint_mode, 'LIGHT_REACTIVE')
        node.outline_tint_mode = 'CUSTOM'
        node.ambient_mode = 'MIX'
        self.assertEqual(node.light_blend_mode, 'ADD')

    def test_light_modes_change_color(self):
        tu.reset_scene()
        plane = tu.add_plane()
        tu.add_sun(2.0, color=(1.0, 0.4, 0.2))
        mat, node = tu.node_material("LM", 'ShaderNodeAnimeCharacter')
        tu.assign(plane, mat)
        node.inputs["Base Color"].default_value = (0.7, 0.5, 0.3, 1.0)  # HUE needs a chromatic base
        node.use_light = True
        results = {}
        for mode in ('OVERLAY', 'HUE', 'MULTIPLY', 'ADD', 'PURE_CEL'):
            node.light_blend_mode = mode
            results[mode] = tu.render_center("lightmode_" + mode)[:3]
        node.use_light = False
        off = tu.render_center("lightmode_off")[:3]
        for a, b in zip(results['PURE_CEL'], off):
            self.assertAlmostEqual(a, b, delta=1e-3)
        distinct = {tuple(round(c, 2) for c in rgb) for rgb in results.values()}
        self.assertEqual(len(distinct), 5)


class AnimeCelTest(unittest.TestCase):
    def _plane(self, sun_strength, sun_color=(1.0, 1.0, 1.0)):
        tu.reset_scene()
        plane = tu.add_plane()
        tu.add_sun(sun_strength, color=sun_color)
        mat, node = tu.node_material("Cel", 'ShaderNodeAnimeCel')
        tu.assign(plane, mat)
        node.inputs["Base Color"].default_value = (0.9, 0.6, 0.4, 1.0)  # chromatic, see LightModeTest
        node.inputs["Shadow Color"].default_value = (0.3, 0.2, 0.4, 1.0)
        node.inputs["Specular Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        return node

    def test_defaults(self):
        tu.reset_scene()
        _mat, node = tu.node_material("D", 'ShaderNodeAnimeCel')
        self.assertEqual(node.ambient_mode, 'HUE_SAT')
        self.assertEqual(node.light_blend_mode, 'OVERLAY')
        self.assertEqual(node.shading_mode, 'SIMPLE')

    def test_threshold_moves_boundary(self):
        node = self._plane(0.4 * math.pi)  # light = 0.4
        node.light_blend_mode = 'PURE_CEL'
        node.inputs["Shadow Threshold"].default_value = 0.3
        lit = tu.render_center("cel_lit")
        node.inputs["Shadow Threshold"].default_value = 0.5
        shade = tu.render_center("cel_shade")
        self.assertGreater(lit[0] - shade[0], 0.2)

    def test_specular_adds_color(self):
        node = self._plane(1.0)
        node.light_blend_mode = 'PURE_CEL'
        without = tu.render_center("spec_off")
        node.inputs["Specular Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        node.inputs["Specular Size"].default_value = 0.5
        with_spec = tu.render_center("spec_on")
        self.assertGreater(with_spec[0] - without[0], 0.05)

    def test_ambient_modes_differ(self):
        """SAT and HUE_SAT may coincide for a near-grey Shadow Color, so 6 distinct colors are enough."""
        node = self._plane(0.0)
        node.inputs["Ambient Color"].default_value = (0.2, 0.3, 0.9, 1.0)
        node.inputs["Ambient Blend"].default_value = 1.0
        colors = set()
        for mode in ('OVERLAY', 'HUE', 'HUE_SAT', 'SAT', 'VAL', 'MULTIPLY', 'MIX'):
            node.ambient_mode = mode
            colors.add(tuple(round(c, 2) for c in tu.render_center("cel_amb_" + mode)[:3]))
        self.assertGreaterEqual(len(colors), 6)

    def test_light_modes_differ(self):
        node = self._plane(2.0, sun_color=(1.0, 0.4, 0.2))
        colors = set()
        for mode in ('OVERLAY', 'HUE', 'MULTIPLY', 'ADD', 'PURE_CEL'):
            node.light_blend_mode = mode
            colors.add(tuple(round(c, 2) for c in tu.render_center("cel_light_" + mode)[:3]))
        self.assertEqual(len(colors), 5)


class LegacyNodesTest(unittest.TestCase):
    def test_legacy_nodes_without_storage(self):
        bpy.ops.wm.open_mainfile(filepath=os.path.join(tu.DATA_DIR, "dasktoon_legacy_nodes.blend"))
        tu._drop_legacy_outline_handler()
        mat = bpy.data.materials["Legacy_AnimeCharacter"]
        node = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(node.use_ambient)
        self.assertTrue(node.use_rim)
        self.assertEqual(node.ambient_mode, 'HUE')
        self.assertEqual(node.outline_tint_mode, 'LIGHT_REACTIVE')
        self.assertEqual(node.light_blend_mode, 'OVERLAY')
        self.assertEqual(node.shading_mode, 'SIMPLE')
        self.assertIsNone(node.shading_ramp)
        tu.setup_render_scene()
        plane = tu.add_plane()
        tu.add_sun(2.0)
        tu.assign(plane, mat)
        simple = tu.render_center("legacy_simple")
        self.assertGreater(max(simple[:3]), 0.05)
        node.shading_mode = 'RAMP'
        self.assertIsNotNone(node.shading_ramp)
        ramp = tu.render_center("legacy_ramp")
        self.assertGreater(max(ramp[:3]), 0.05)


if __name__ == "__main__":
    tu.run_tests()
