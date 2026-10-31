# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A new anime shader node is grey until it is given a colour. It was skin: a character whose pictures were not there yet
looked bare."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

NODES = {"ShaderNodeAnimeCharacter": ("Base Color", "Shadow Color"), "ShaderNodeAnimeCel": ("Base Color", "Shadow Color"),
         "ShaderNodeAnimeWarmCoolGrade": ("Base Color",)}


class DefaultsTest(unittest.TestCase):
    def setUp(self):
        self.mat = bpy.data.materials.new("Defaults")
        self.mat.use_nodes = True

    def colour(self, idname, name):
        return self.mat.node_tree.nodes.new(idname).inputs[name].default_value[:3]

    def test_their_colours_are_grey(self):
        for idname, names in NODES.items():
            for name in names:
                red, green, blue = self.colour(idname, name)
                self.assertAlmostEqual(red, green, places=5, msg=(idname, name))
                self.assertAlmostEqual(green, blue, places=5, msg=(idname, name))

    def test_the_shadow_is_darker(self):
        for idname in ("ShaderNodeAnimeCharacter", "ShaderNodeAnimeCel"):
            self.assertLess(self.colour(idname, "Shadow Color")[0], self.colour(idname, "Base Color")[0] - 0.1, idname)

    def test_a_converted_material_does_not_use_them(self):
        """Use DaskToon Shader takes the colour of the material: a skin stays a skin."""
        from bl_ui import dasktoon_material_convert as convert
        nodes = self.mat.node_tree.nodes
        nodes.clear()
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.inputs["Base Color"].default_value = (0.9, 0.7, 0.6, 1.0)
        self.mat.node_tree.links.new(principled.outputs["BSDF"], nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
        self.assertTrue(convert.convert(self.mat, bpy.context.scene))
        anime = next(node for node in self.mat.node_tree.nodes if node.bl_idname == "ShaderNodeAnimeCharacter")
        self.assertEqual(tuple(round(c, 3) for c in anime.inputs["Base Color"].default_value[:3]), (0.9, 0.7, 0.6))


if __name__ == "__main__":
    tu.run_tests()
