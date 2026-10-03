# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity imports the exported FBX with the exported materials, blend shapes, Blender axes converted, and
DT_OutlineN decoding to DaskToon's smoothed normals in Unity's tangent frame (spec 8, Unity steps 2 and 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gamedata  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402


def to_unity(v):
    return [-v[0], v[2], -v[1]]


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityModelTest(unittest.TestCase):
    def test_fbx_import_materials_shapes_axes_and_outline_normals(self):
        root = harness.ensure_project()
        tu.reset_scene()
        outline.reset_cache()
        body = tu.add_sphere(segments=24, rings=12)
        body.name = "Body"
        body.data.uv_layers.new(name="Second")
        mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        tu.assign(body, mat)
        body.shape_key_add(name="Basis")
        body.shape_key_add(name="Smile").data[0].co.z += 0.1
        outline.sync_all(bpy.context.scene)
        target = targets.make_target(root, "DTModel")
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [body], options)
        self.assertEqual(rep.materials, ["Skin"])
        mesh = body.data
        smooth = gamedata.smoothed_vertex_normals(mesh)
        normals = [{"p": to_unity(v.co), "n": to_unity(s)} for v, s in zip(mesh.vertices, smooth)]
        uv_index = mesh.uv_layers.find("DT_OutlineN")
        self.assertEqual(uv_index, 2)
        result = harness.run_method("DaskToonModelTests.CheckModel", {
            "model": "Assets/DaskToon/DTModel/Model/DTModel.fbx", "mesh": "Body",
            "outlineUV": uv_index, "normals": normals})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["imported"])
        self.assertEqual(result["materials"], {"Skin": "Assets/DaskToon/DTModel/Materials/Skin.mat"})
        self.assertTrue(result["meshFound"])
        self.assertGreaterEqual(result["blendShapes"], 1)
        self.assertIn(uv_index, result["uvChannels"])
        self.assertGreater(result["matched"], 0.9 * result["vertices"])
        self.assertLess(result["maxNormalAngle"], 2.0)
        self.assertAlmostEqual(result["top"], max(v.co.z for v in mesh.vertices), places=3)


if __name__ == "__main__":
    tu.run_tests()
