# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Check of the one-button auto rig (docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md): test poses, the
mesh moved through its weights, joints outside the body, stretched spots and roles that look wrong."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, check  # noqa: E402


def world_head(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def world_tail(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].tail


class PoseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.parts = rt.character()
        build.build(bpy.context, cls.rig, cls.parts)

    def tearDown(self):
        check.apply_pose(bpy.context, self.rig, 'REST')

    def test_arms_up(self):
        check.apply_pose(bpy.context, self.rig, 'ARMS_UP')
        for side in ("Left", "Right"):
            self.assertGreater(world_head(self.rig, side + "Hand").z, world_head(self.rig, side + "UpperArm").z + 0.2)
        self.assertIsNone(self.rig.animation_data)  # nothing keyed

    def test_sit_and_turn_head(self):
        check.apply_pose(bpy.context, self.rig, 'SIT')
        for side in ("Left", "Right"):
            knee, ankle = world_head(self.rig, side + "LowerLeg"), world_head(self.rig, side + "Foot")
            self.assertLess(knee.y, world_head(self.rig, side + "UpperLeg").y - 0.2)  # the thigh points forward
            self.assertLess((ankle - knee).normalized().z, -0.9)  # the shin hangs down again
        eye = world_head(self.rig, "LeftEye").x
        check.apply_pose(bpy.context, self.rig, 'TURN_HEAD')
        self.assertGreater(world_head(self.rig, "LeftEye").x, eye + 0.02)  # the face turns to the character's left

    def test_rest_and_animation_come_back(self):
        check.apply_pose(bpy.context, self.rig, 'WAVE')
        check.apply_pose(bpy.context, self.rig, 'REST')
        self.assertTrue(all(bone.matrix_basis == bone.matrix_basis.Identity(4) for bone in self.rig.pose.bones))
        arm = self.rig.pose.bones["LeftLowerArm"]
        arm.rotation_mode = 'XYZ'
        arm.rotation_euler = (0.3, 0.0, 0.0)
        arm.keyframe_insert("rotation_euler", frame=1)
        try:
            check.apply_pose(bpy.context, self.rig, 'ARMS_UP')
            bpy.context.scene.frame_set(1)
            self.assertAlmostEqual(arm.rotation_euler.x, 0.3, places=5)  # the animation is back on a frame change
            self.assertEqual(len(self.rig.animation_data.action.layers[0].strips[0].channelbags[0].fcurves), 3)
        finally:
            self.rig.animation_data_clear()
            arm.rotation_euler = (0.0, 0.0, 0.0)

    def test_mesh_moved_through_its_weights(self):
        body = self.objs["Body"]
        rest = check.deformed(self.rig, body)
        tip = rt.nearest(body, rt.ARM_END)
        check.apply_pose(bpy.context, self.rig, 'ARMS_UP')
        moved = check.deformed(self.rig, body)
        self.assertGreater(moved[tip, 2], rest[tip, 2] + 0.5)
        foot = rt.nearest(body, (0.09, 0.0, 0.0))
        self.assertLess(np.linalg.norm(moved[foot] - rest[foot]), 1e-5)


if __name__ == "__main__":
    tu.run_tests()
