# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_upgrade as up  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402


def open_fixture(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(tu.DATA_DIR, name))


class UpgradeTest(unittest.TestCase):
    def test_legacy_outline_is_upgraded(self):
        open_fixture("dasktoon_legacy_outline.blend")
        hero = bpy.data.objects["Hero"]
        self.assertFalse(any(m.type == 'SOLIDIFY' for o in bpy.data.objects for m in o.modifiers))
        self.assertFalse(any(m and m.name.endswith("_DaskOutline") for m in hero.data.materials))
        self.assertEqual(len(hero.data.materials), 1)
        self.assertIsNone(bpy.data.materials.get("Hero_DaskOutline"))
        self.assertIsNotNone(hero.modifiers.get(gn.MODIFIER_NAME))
        skin = bpy.data.materials["Skin"]
        node = next(n for n in skin.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(node.use_outline)
        self.assertAlmostEqual(node.inputs["Outline Width"].default_value, 0.004, places=6)
        self.assertIn(up.REPORT_TEXT, bpy.data.texts)
        for scene in bpy.data.scenes:
            self.assertEqual(scene.get("dasktoon_data_version"), up.DATA_VERSION)

    def test_legacy_anime_cel_modes(self):
        open_fixture("dasktoon_legacy_nodes.blend")
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        self.assertEqual(cel.ambient_mode, 'HUE_SAT')
        self.assertEqual(cel.light_blend_mode, 'MULTIPLY')
        bsdf = next(n for n in bpy.data.materials["Legacy_AnimeCharacter"].node_tree.nodes
                    if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(bsdf.use_ambient)
        self.assertTrue(bsdf.use_rim)
        self.assertEqual(bsdf.shading_mode, 'SIMPLE')

    def test_legacy_thickness_becomes_outline_width(self):
        """The Solidify thickness is what the user saw: it must survive, also for a node left at its default
        width and for a material without an Anime BSDF / Dask Cel node."""
        tu.reset_scene()
        obj = tu.add_sphere(segments=8, rings=4)
        body, node = tu.node_material("Body", 'ShaderNodeAnimeCharacter')
        cloth = tu.emission_material("Cloth", (1.0, 1.0, 1.0, 1.0))
        obj.data.materials.append(body)
        obj.data.materials.append(cloth)
        obj.data.materials.append(tu.emission_material(obj.name + "_DaskOutline", (0.0, 0.0, 0.0, 1.0)))
        obj.modifiers.new("DaskToon_Outline", 'SOLIDIFY').thickness = 0.006
        up.upgrade_legacy_outline([])
        self.assertAlmostEqual(node.inputs["Outline Width"].default_value, 0.006, places=6)
        dask = outline.outline_node(outline.outline_material_for(cloth, create=False))
        self.assertAlmostEqual(dask.inputs["Outline Width"].default_value, 0.006, places=6)

    def test_upgrade_runs_once(self):
        open_fixture("dasktoon_legacy_nodes.blend")
        path = os.path.join(tempfile.mkdtemp(prefix="dasktoon_up_"), "saved.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        cel.ambient_mode = 'OVERLAY'  # the user's later choice must survive reopening
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        self.assertEqual(cel.ambient_mode, 'OVERLAY')


if __name__ == "__main__":
    tu.run_tests()
