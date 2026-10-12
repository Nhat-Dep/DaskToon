# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The clips of a character in Unity 6000.5 (clips spec 6): each <Model>@<Clip>.fbx imports as one AnimationClip with
the clip's name, Loop and length, a Humanoid motion, and the blend shape curve of the face. Runs Unity in batchmode on
the harness's throwaway project."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_export_clips_test as ct  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityClipsTest(unittest.TestCase):
    def test_clips_import_as_animation_clips(self):
        root = harness.ensure_project()
        rig, objs, _walk, _wave = ct.character_with_clips()
        fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        target = targets.make_target(root, "DTClips")
        options = dasktoon_export.ExportOptions(include_animation=True, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)
        self.assertEqual(rep.clips, [("Walk", True), ("Wave", False)])
        files = ["Assets/DaskToon/DTClips/Model/DTClips@%s.fbx" % name for name in ("Walk", "Wave")]
        result = harness.run_method("DaskToonClipTests.CheckClips",
                                    {"model": "Assets/DaskToon/DTClips/Model/DTClips.fbx", "files": files})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["modelHuman"])
        for name, loop, frames in (("Walk", True, 11), ("Wave", False, 15)):
            key = "DTClips@" + name
            self.assertEqual(result[key + ".count"], 1, name)
            self.assertEqual(result[key + ".name"], name)
            self.assertEqual(result[key + ".loop"], loop, name)
            self.assertAlmostEqual(result[key + ".length"], frames / fps, places=2)
            self.assertTrue(result[key + ".human"], name)
        self.assertTrue(result["DTClips@Walk.blendShape"])
        # Walk runs on twos (anime timing spec 5): constant keys, held between drawn frames; Wave is left smooth.
        self.assertTrue(result["DTClips@Walk.constant"])
        self.assertLess(result["DTClips@Walk.hold"], 1e-4)
        self.assertFalse(result["DTClips@Wave.constant"])


if __name__ == "__main__":
    tu.run_tests()
