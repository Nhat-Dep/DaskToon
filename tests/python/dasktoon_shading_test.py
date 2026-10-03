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


if __name__ == "__main__":
    tu.run_tests()
