# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The shoulders lift with the arms (docs/superpowers/specs/2026-10-14-dasktoon-shoulder-follow-design.md): raised past
30 degrees below horizontal, an arm lifts its shoulder bone, up to 35 degrees with the arm straight up; keys on the
shoulder still count; the exported clip carries the lift."""

import math
import os
import shutil
import sys
import tempfile
import unittest

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, check, shoulders  # noqa: E402

RATIO = 35.0 / 120.0  # degrees of lift for each degree the arm rises


def direction(rig, name, posed):
    bone = rig.pose.bones[name] if posed else rig.data.bones[name]
    head, tail = (bone.head, bone.tail) if posed else (bone.head_local, bone.tail_local)
    return (rig.matrix_world.to_3x3() @ (tail - head)).normalized()


def lift(rig, side):
    """Degrees the shoulder bone is turned from rest by its pose (whatever way the bone points: an FBX import makes
    its own tails), positive when its tip rises."""
    name = side + "Shoulder"
    turned = rig.data.bones[name].matrix_local.inverted() @ rig.pose.bones[name].matrix
    angle = math.degrees(turned.to_quaternion().angle)
    rest, posed = direction(rig, name, False), direction(rig, name, True)
    return angle if posed.z >= rest.z - 1e-9 else -angle


def tip_rise(rig, side):
    """Degrees the shoulder bone's tip turns up, seen from the front (a lift, not a twist about the bone itself)."""
    rest, posed = direction(rig, side + "Shoulder", False), direction(rig, side + "Shoulder", True)
    return math.degrees(math.asin(max(-1.0, min(1.0, posed.z))) - math.asin(max(-1.0, min(1.0, rest.z))))


def rest_elevation(rig, side):
    return math.degrees(math.asin(direction(rig, side + "UpperArm", False).z))


def expected(rig, side, raise_degrees):
    """The lift spec 1 gives an arm raised by `raise_degrees` from rest."""
    rest = rest_elevation(rig, side)
    start = max(rest, -30.0)
    return max(0.0, min(RATIO * (90.0 - start), RATIO * (rest + raise_degrees - start)))


def turn(rig, name, axis, degrees):
    """Turn a bone about a world axis through its head (as the Check's test poses do)."""
    bone = rig.pose.bones[name]
    world = rig.matrix_world @ bone.matrix
    pivot = world.translation.copy()
    spin = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-pivot)
    bone.matrix = rig.matrix_world.inverted() @ spin @ world
    bpy.context.view_layer.update()


class ShoulderTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs = rt.rigged()
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))

    def tearDown(self):
        check.apply_pose(bpy.context, self.rig, 'REST')

    def test_raising_the_arms_lifts_the_shoulders(self):
        self.assertLess(rest_elevation(self.rig, "Left"), -30.0)  # an A-pose: the lift starts after a while
        check.apply_pose(bpy.context, self.rig, 'ARMS_UP')  # each upper arm raised 110 degrees
        for side in ("Left", "Right"):
            self.assertGreater(expected(self.rig, side, 110.0), 15.0)
            self.assertAlmostEqual(lift(self.rig, side), expected(self.rig, side, 110.0), delta=2.0, msg=side)
            # Its tip goes up by that much: the shoulder is lifted, not twisted about itself (which turned the arm
            # backwards on tdt).
            self.assertAlmostEqual(tip_rise(self.rig, side), expected(self.rig, side, 110.0), delta=2.0, msg=side)
        check.apply_pose(bpy.context, self.rig, 'REST')
        for side in ("Left", "Right"):
            self.assertAlmostEqual(lift(self.rig, side), 0.0, places=3)

    def test_wave_lifts_only_the_waving_side(self):
        check.apply_pose(bpy.context, self.rig, 'WAVE')  # the right arm raised 100 degrees
        self.assertAlmostEqual(lift(self.rig, "Right"), expected(self.rig, "Right", 100.0), delta=2.0)
        self.assertAlmostEqual(lift(self.rig, "Left"), 0.0, places=3)

    def test_the_slider(self):
        data = self.rig.data.dasktoon_rig
        self.assertEqual(data.shoulder_follow, 1.0)
        full = expected(self.rig, "Left", 110.0)
        data.shoulder_follow = 0.5
        check.apply_pose(bpy.context, self.rig, 'ARMS_UP')
        self.assertAlmostEqual(lift(self.rig, "Left"), full / 2.0, delta=1.5)
        data.shoulder_follow = 0.0
        bpy.context.view_layer.update()
        self.assertAlmostEqual(lift(self.rig, "Left"), 0.0, places=3)

    def test_keys_on_the_shoulder_still_count(self):
        """A shrug keyed on the shoulder bone, the arm down: the shoulder turns as keyed (the lift adds to keys, it
        does not replace them)."""
        bone = self.rig.pose.bones["LeftShoulder"]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (math.radians(10.0), 0.0, 0.0)
        bpy.context.view_layer.update()
        self.assertAlmostEqual(abs(lift(self.rig, "Left")), 10.0, delta=0.5)

    def test_a_t_pose_is_not_lifted_at_rest(self):
        """Arms level at rest: nothing at rest, the lift from the first degree up."""
        self.rig.data.use_mirror_x = False
        from dasktoon_rig import skeleton
        with skeleton.editing(bpy.context, self.rig) as edit:
            for side, s in (("Left", 1.0), ("Right", -1.0)):
                arm = edit[side + "UpperArm"]
                length = (arm.tail - arm.head).length
                arm.tail = arm.head + Matrix.Identity(3).col[0] * (s * length)  # level, straight out
        shoulders.apply(bpy.context, self.rig)
        self.assertAlmostEqual(rest_elevation(self.rig, "Left"), 0.0, places=3)
        self.assertAlmostEqual(lift(self.rig, "Left"), 0.0, places=3)
        turn(self.rig, "LeftUpperArm", 'Y', -45.0)  # the left arm up 45 degrees (as Arms Up turns it)
        self.assertAlmostEqual(lift(self.rig, "Left"), RATIO * 45.0, delta=1.5)
        self.assertAlmostEqual(tip_rise(self.rig, "Left"), RATIO * 45.0, delta=1.5)

    def test_one_of_each_after_building_again(self):
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))
        names = [bone.name for bone in self.rig.data.bones]
        drivers = self.rig.animation_data.drivers
        for side in ("Left", "Right"):
            helper = side + "ShoulderLift"
            self.assertEqual(names.count(helper), 1)
            self.assertFalse(self.rig.data.bones[helper].use_deform)
            self.assertTrue(self.rig.data.bones[helper].hide)
            self.assertNotIn(helper + ".001", names)
            constraints = [c for c in self.rig.pose.bones[side + "Shoulder"].constraints if c.name == shoulders.NAME]
            self.assertEqual(len(constraints), 1)
            ours = [d for d in drivers if d.data_path.startswith('pose.bones["%s"]' % helper)]
            self.assertEqual(len(ours), 1)
            self.assertEqual((ours[0].data_path, ours[0].array_index), ('pose.bones["%s"].rotation_euler' % helper, 0))
            self.assertTrue(ours[0].driver.is_simple_expression, ours[0].driver.expression)

    def test_the_exported_clip_carries_the_lift(self):
        """The clip FBX bakes the evaluated pose: the shoulder is lifted there, and the helper bone is not in it."""
        from dasktoon_export import model_fbx
        rig = self.rig
        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 5
        arm = rig.pose.bones["LeftUpperArm"]
        scene.frame_set(1)
        arm.keyframe_insert("rotation_quaternion", frame=1)
        check.apply_pose(bpy.context, rig, 'ARMS_UP')
        arm.keyframe_insert("rotation_quaternion", frame=5)
        want = expected(rig, "Left", 110.0)
        folder = tempfile.mkdtemp(prefix="dt_shoulder_")
        try:
            path = os.path.join(folder, "Lift.fbx")
            model_fbx.write_fbx(bpy.context, [rig] + list(self.objs.values()), path, True, single_take=True)
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=path)
            imported = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
            self.assertIsNone(imported.data.bones.get("LeftShoulderLift"))
            # The import puts the take one frame later (frames 2 to 6): its last frame is the arm up.
            bpy.context.scene.frame_set(int(imported.animation_data.action.frame_range[1]))
            self.assertAlmostEqual(abs(lift(imported, "Left")), want, delta=2.0)
        finally:
            shutil.rmtree(folder, ignore_errors=True)
            self.rig, self.objs = rt.rigged()  # the file was emptied: tearDown rests this new one


if __name__ == "__main__":
    tu.run_tests()
