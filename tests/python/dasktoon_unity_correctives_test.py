# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The bend fixes in Unity 6000.5 (docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md): Engine Export
writes them into the rig file and the FBX, DaskToon's importer adds a DaskToonCorrective, each fix's target points the
same way as in DaskToon (the knee back, the hip and elbow forward, the shoulder down), and the child bone turned to the
direction it has in a DaskToon pose gives the weight DaskToon's driver gives. Runs Unity in batchmode on the harness's
throwaway project."""

import math
import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_correctives_test as ct  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_rig import correctives  # noqa: E402


def poses(rig, body):
    """[(fix name, axis, angle)] to try: along the arc, past it, off it, mixed."""
    fixes = {fix.name: fix for fix in correctives.fixes(rig)}
    knee, hip, elbow, shoulder = fixes["LeftKnee"], fixes["RightHip"], fixes["RightElbow"], fixes["LeftShoulder"]
    left_hip = fixes["LeftHip"]
    across = left_hip.rest.cross(left_hip.axis)
    return [("LeftKnee", knee.axis, 0.5 * knee.angle), ("LeftKnee", knee.axis, knee.angle),
            ("LeftKnee", knee.axis, 1.3 * knee.angle), ("RightHip", hip.axis, 0.6 * hip.angle),
            ("LeftHip", across, math.radians(60.0)), ("LeftHip", (left_hip.axis + 0.5 * across).normalized(),
                                                       math.radians(70.0)),
            ("RightElbow", elbow.axis, 0.8 * elbow.angle), ("LeftShoulder", shoulder.axis, 0.5 * shoulder.angle),
            ("LeftKnee", knee.axis, math.radians(120.0)), ("LeftKneeDeep", knee.axis, math.radians(120.0)),
            ("LeftKneeDeep", knee.axis, math.radians(165.0))]


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityCorrectivesTest(unittest.TestCase):
    def test_bend_fixes_in_unity(self):
        root = harness.ensure_project()
        rig, objs = ct.built()
        body = objs["Body"]
        frame = correctives.body_frame(rig)
        fixes = {fix.name: fix for fix in correctives.fixes(rig)}
        sent, expected = [], []
        for name, axis, angle in poses(rig, body):
            fix = fixes[name]
            ct.turn(rig, fix.child, axis, angle)
            expected.append(ct.value(body, correctives.PREFIX + name))
            pose_bone = rig.pose.bones[fix.child]
            direction = (pose_bone.tail - pose_bone.head).normalized()
            sent.append({"shape": correctives.PREFIX + name, "child": fix.child,
                         "direction": [direction.dot(axis_) for axis_ in frame]})
        ct.at_rest(rig)
        bpy.context.view_layer.update()
        target = targets.make_target(root, "DTFix")
        options = dasktoon_export.ExportOptions(include_animation=False, export_materials=False)
        rep = dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)
        self.assertTrue(rep.rig, rep.lines())
        result = harness.run_method("DaskToonCorrectiveTests.Check", {
            "model": "Assets/DaskToon/DTFix/Model/DTFix.fbx", "poses": sent})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["component"])
        self.assertGreater(result["frontAlongToes"], 0.99)  # the character's frame matches its own feet
        self.assertEqual(sorted(result["shapes"]), sorted(correctives.PREFIX + name for name in fixes))
        for name, fix in fixes.items():
            shape = correctives.PREFIX + name
            self.assertEqual(result[shape + ".renderers"], "Body")  # Engine Export merges the meshes
            self.assertAlmostEqual(result[shape + ".angle"], fix.angle, delta=2e-3, msg=name)
            self.assertLess(abs(result[shape + ".atRest"]), 1e-4, name)
        self.assertLess(result["DT_Fix_LeftKnee.front"], -0.99)  # the lower leg goes back
        self.assertGreater(result["DT_Fix_RightHip.front"], 0.99)  # the thigh comes forward
        self.assertGreater(result["DT_Fix_LeftElbow.front"], 0.99)  # the forearm comes forward
        self.assertGreater(result["DT_Fix_RightShoulder.down"], 0.99)  # the arm down
        self.assertLess(result["DT_Fix_LeftKneeDeep.down"], -0.8)  # 150 degrees: the lower leg folded up
        self.assertEqual(len(result["weights"]), len(expected))
        for got, want, pose in zip(result["weights"], expected, sent):
            self.assertAlmostEqual(got, want, delta=0.01, msg=pose)
        self.assertGreater(max(expected), 0.99)
        self.assertLess(min(expected), 0.01)


if __name__ == "__main__":
    tu.run_tests()
