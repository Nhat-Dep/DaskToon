# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The eyes and mouth of a character in Unity 6000.5 (anime rig spec 10, R3): Engine Export writes the flat eye and
2D mouth into the rig file, DaskToon's importer adds DaskToonFlatEye and DaskToonMouthAtlas, the iris slides as in
DaskToon, the MouthCell bone picks the cell, and the clip carries MouthCell's scale. Runs Unity in batchmode on the
harness's throwaway project."""

import math
import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_export_rig_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_animation import clips  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_rig import mouth  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityFaceTest(unittest.TestCase):
    def test_flat_eye_and_mouth_in_unity(self):
        root = harness.ensure_project()
        rig, objs, iris, card = rt.face_built()
        scene = bpy.context.scene
        talk = clips.new(rig, list(bpy.context.view_layer.objects), "Talk", scene=scene)
        for frame, cell in ((1, 0), (3, 3), (6, 1)):
            card[mouth.PROP] = cell
            card.keyframe_insert('["%s"]' % mouth.PROP, frame=frame)
        rig.pose.bones["Hips"].keyframe_insert("location", frame=1)
        rig.pose.bones["Hips"].keyframe_insert("location", frame=6)
        talk.use_cyclic = False
        fps = scene.render.fps / scene.render.fps_base
        target = targets.make_target(root, "DTFace")
        options = dasktoon_export.ExportOptions(include_animation=True, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [rig, iris, card] + list(objs.values()), options)
        self.assertEqual(rep.clips, [("Talk", False)])
        result = harness.run_method("DaskToonFaceTests.CheckFace", {
            "model": "Assets/DaskToon/DTFace/Model/DTFace.fbx",
            "clip": "Assets/DaskToon/DTFace/Model/DTFace@Talk.fbx",
            "cellTime": 2.0 / fps})  # frame 3 of a clip starting at frame 1
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["flatEye"])
        self.assertEqual((result["flatEye.eye"], result["flatEye.target"]), ("LeftEye", "Iris"))
        self.assertAlmostEqual(result["flatEye.range"], 0.1, places=5)
        self.assertLess(result["flatEye.rest"], 1e-4)
        self.assertAlmostEqual(result["flatEye.left"], -0.1 * math.sin(math.radians(20.0)), delta=2e-3)
        self.assertAlmostEqual(result["flatEye.leftY"], 0.0, delta=2e-3)
        self.assertAlmostEqual(result["flatEye.up"], -0.1 * math.sin(math.radians(10.0)), delta=2e-3)
        self.assertAlmostEqual(result["flatEye.upX"], 0.0, delta=2e-3)
        self.assertTrue(result["mouth"])
        self.assertEqual((result["mouth.bone"], result["mouth.target"]), (mouth.CELL_BONE, "MouthCard"))
        self.assertEqual((result["mouth.rows"], result["mouth.columns"]), (2, 4))
        self.assertEqual((result["mouth.rest"], result["mouth.cell"]), (0, 3))
        for got, expected in zip(result["mouth.uv"], (0.25, 0.5, 0.75, 0.5)):
            self.assertAlmostEqual(got, expected, places=5)
        self.assertTrue(result["clip"])
        self.assertTrue(result.get("clip.cellCurve"), result)  # MouthCell's scale reaches the Humanoid clip
        self.assertAlmostEqual(result["clip.cellValue"], 4.0, delta=0.01)


if __name__ == "__main__":
    tu.run_tests()
