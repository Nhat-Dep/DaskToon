# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

os.environ["DASKTOON_STYLES_DIR"] = tempfile.mkdtemp(prefix="dasktoon_styles_")
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402


class StylesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.mat, self.node = tu.node_material("S", 'ShaderNodeAnimeCharacter')
        self.node.shading_mode = 'RAMP'

    def test_builtin_style_applies_exactly(self):
        style = styles.BUILTIN_STYLES["Anime 3-Tone"]
        styles.apply_style(self.node.shading_ramp, style)
        ramp = self.node.shading_ramp
        self.assertEqual(ramp.interpolation, 'CONSTANT')
        self.assertEqual(len(ramp.elements), 3)
        for element, (pos, col) in zip(ramp.elements, style["stops"]):
            self.assertAlmostEqual(element.position, pos, places=4)
            for a, b in zip(element.color, col):
                self.assertAlmostEqual(a, b, places=4)

    def test_save_load_delete_user_style(self):
        styles.apply_style(self.node.shading_ramp, styles.BUILTIN_STYLES["Manga"])
        path = styles.save_user_style("Style của tôi", self.node.shading_ramp)
        self.assertTrue(os.path.isfile(path))
        self.assertIn("Style của tôi", styles.list_user_styles())
        styles.apply_style(self.node.shading_ramp, styles.BUILTIN_STYLES["Anime 2-Tone"])
        styles.apply_style(self.node.shading_ramp, styles.get_style("Style của tôi"))
        self.assertAlmostEqual(self.node.shading_ramp.elements[0].color[0], 0.10, places=4)
        self.assertTrue(styles.delete_user_style("Style của tôi"))
        self.assertNotIn("Style của tôi", styles.list_user_styles())

    def test_operator_by_material_and_node_name(self):
        result = bpy.ops.dasktoon.shading_style_apply(name="Manga", material=self.mat.name, node=self.node.name)
        self.assertEqual(result, {'FINISHED'})
        self.assertAlmostEqual(self.node.shading_ramp.elements[0].color[0], 0.10, places=4)

    def test_ramp_from_simple_keeps_boundary(self):
        plane = tu.add_plane()
        sun = tu.add_sun(1.0)
        tu.assign(plane, self.mat)
        node = self.node
        node.shading_mode = 'SIMPLE'
        node.inputs["Shadow Threshold"].default_value = 0.46
        node.inputs["Shadow Softness"].default_value = 0.05
        renders = {}
        for label, light in (("below", 0.36), ("above", 0.56)):
            sun.data.energy = light * math.pi
            renders[("simple", label)] = tu.render_center("simple_" + label)
        styles.ramp_from_simple(node)
        self.assertEqual(node.shading_mode, 'RAMP')
        for label, light in (("below", 0.36), ("above", 0.56)):
            sun.data.energy = light * math.pi
            renders[("ramp", label)] = tu.render_center("ramp_" + label)
        for label in ("below", "above"):
            for a, b in zip(renders[("simple", label)][:3], renders[("ramp", label)][:3]):
                self.assertAlmostEqual(a, b, delta=0.08)


if __name__ == "__main__":
    tu.run_tests()
