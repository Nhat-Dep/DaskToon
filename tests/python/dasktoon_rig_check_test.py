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


def issues(rig):
    return [(item.kind, item.bone, item.part, item.pose, item.region, item.role) for item in rig.data.dasktoon_rig.issues]


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs = rt.rigged()
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))

    def probe(self, name, start, end, bones):
        """A tube from `start` to `end`, a part of the rig, whose vertices follow `bones` (one bone each, in order along
        the tube, a share each): weights set by hand, so the test is about the Check, not the automatic weights."""
        from bl_ui import dasktoon_rig as ui
        from dasktoon_rig import weights
        obj = rt.merged(name, [rt.st.tube(start, end, 0.03, rings=12)])
        world, _edges = rt.rig_parts.mesh_arrays(obj)
        axis = np.array(end) - np.array(start)
        along = (world - np.array(start)) @ axis / (axis @ axis)
        which = np.minimum((np.clip(along, 0.0, 1.0) * len(bones)).astype(int), len(bones) - 1)
        matrix = np.zeros((len(world), len(bones)))
        matrix[np.arange(len(world)), which] = 1.0
        weights.bind(self.rig, obj)
        weights.write(obj, np.arange(len(world)), bones, matrix)
        return ui.add_part(self.rig, obj, 'ACCESSORY')

    def test_bending_between_bones_next_to_each_other_is_fine(self):
        """Sitting bends the knee 90 degrees: the skin round it stretches, but between the thigh and the shin, bones next
        to each other: a joint bending, not a tear."""
        part = self.probe("Stocking", tuple(world_head(self.rig, "LeftUpperLeg")), tuple(world_head(self.rig, "LeftFoot")),
                          ["LeftUpperLeg", "LeftLowerLeg"])
        self.assertEqual(check.stretch_issues(bpy.context, self.rig, [part]), [])
        check.STRETCH, saved = 1.2, check.STRETCH  # it does stretch: only the bones being neighbours keep it off the list
        try:
            check.FAR_BONES, far = 1, check.FAR_BONES
            try:
                self.assertTrue(check.stretch_issues(bpy.context, self.rig, [part]))
            finally:
                check.FAR_BONES = far
        finally:
            check.STRETCH = saved

    def test_a_piece_torn_between_far_bones(self):
        """A rabbit ear half on the head, half on the left arm: raising the arms tears it."""
        part = self.probe("Ear", (0.33, 0.12, 1.85), (0.34, 0.15, 1.42), ["Head", "LeftUpperArm"])
        found = check.stretch_issues(bpy.context, self.rig, [part])
        self.assertEqual([(obj.name, pose) for obj, pose, _region, _spot in found], [("Ear", 'ARMS_UP')])
        self.assertTrue(all(bone.matrix_basis == bone.matrix_basis.Identity(4) for bone in self.rig.pose.bones))

    def test_a_wrist_outside_the_arm(self):
        from dasktoon_rig import skeleton
        parts = list(self.rig.data.dasktoon_rig.parts)
        self.assertEqual(check.joint_issues(self.rig, parts), [])
        self.rig.data.use_mirror_x = False  # the right wrist stays
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit["LeftHand"].head.x += 0.2  # the elbow-to-wrist bone follows: it is connected
            edit["LeftHand"].tail.x += 0.2
        self.assertEqual(check.joint_issues(self.rig, parts), ["LeftHand"])

    def test_run_keeps_what_it_found_on_the_rig(self):
        self.probe("Ear", (0.33, 0.12, 1.85), (0.34, 0.15, 1.42), ["Head", "LeftUpperArm"])
        count = check.run(bpy.context, self.rig)
        data = self.rig.data.dasktoon_rig
        self.assertEqual(count, len(data.issues))
        self.assertTrue(data.checked)
        ear = [item for item in data.issues if item.kind == 'STRETCH' and item.part == "Ear"]
        self.assertEqual([(item.pose, item.region) for item in ear], [('ARMS_UP', 'HEAD')])
        self.assertTrue(len(ear[0]["vertices"]) >= 3)
        self.assertTrue(all(bone.matrix_basis == bone.matrix_basis.Identity(4) for bone in self.rig.pose.bones))

    def test_roles_that_look_wrong(self):
        from bl_ui import dasktoon_rig as ui
        st = rt.st
        skirt = rt.merged("Circle.007", [st.tube((0, 0, 0.92), (0, 0, 0.62), 0.22)])
        flare = skirt.data.vertices
        for v in flare:  # wider at the hem
            if v.co.z < 0.8:
                v.co.x *= 1.4
                v.co.y *= 1.4
        hair = rt.merged("Circle.008", [st.tube((0, 0.32, 1.95), (0, 0.36, 1.2), 0.05)])  # hangs behind the head
        pants = rt.merged("Circle.009", [st.tube((s * 0.09, 0, 0.92), (s * 0.09, 0, 0.5), 0.09) for s in (1.0, -1.0)])
        hat = rt.merged("Circle.010", [st.tube((0, 0, 2.0), (0, 0, 2.15), 0.25)])
        for obj in (skirt, hair, pants, hat):
            ui.add_part(self.rig, obj, 'CLOTHING')
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))
        check.run(bpy.context, self.rig)
        roles = sorted((entry[2], entry[5]) for entry in issues(self.rig) if entry[0] == 'ROLE')
        self.assertEqual(roles, [("Circle.007", 'SKIRT'), ("Circle.008", 'HAIR')])  # not the pants, not the hat


if __name__ == "__main__":
    tu.run_tests()
