# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bend fixes (docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md): Build Rig makes a shape key for each
knee, elbow, hip and shoulder; at the fix's pose a vertex blended across the joint lands where turning it by its share
of the bend puts it, instead of where linear blending does; a driver (no Python) shows the key as the joint bends."""

import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, correctives  # noqa: E402

JOINTS = ("Knee", "KneeDeep", "Elbow", "ElbowDeep", "Hip", "Shoulder", "ShoulderUp")


def built():
    """The chibi of the regions test (arms 50 degrees below horizontal), built."""
    rig, objs = rt.rigged()
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    return rig, objs


def fix_of(rig, name):
    return next(fix for fix in correctives.fixes(rig) if fix.name == name)


def at_rest(rig):
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.rotation_quaternion = Quaternion()
        pose_bone.location = (0.0, 0.0, 0.0)


def turn(rig, child, axis, angle):
    """The pose bone `child` turned by `angle` about `axis` (armature space), the rest of the rig at rest."""
    at_rest(rig)
    bone = rig.data.bones[child]
    frame = bone.matrix_local.to_3x3()
    turned = frame.inverted() @ Matrix.Rotation(angle, 3, axis) @ frame
    rig.pose.bones[child].rotation_quaternion = turned.to_quaternion()
    bpy.context.view_layer.update()


def value(obj, name):
    """The key's value as the depsgraph works it out (its driver)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    key = obj.evaluated_get(depsgraph).data.shape_keys
    return key.key_blocks[name].value


def evaluated(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = obj.evaluated_get(depsgraph).data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def child_share(rig, obj, child):
    """Per vertex, the part of its weight on `child` and the bones below it (deform bones only)."""
    side = {child} | {bone.name for bone in rig.data.bones[child].children_recursive}
    deform = {bone.name for bone in rig.data.bones if bone.use_deform}
    total = np.zeros(len(obj.data.vertices))
    share = np.zeros(len(obj.data.vertices))
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            name = obj.vertex_groups[element.group].name
            if name in deform:
                total[vertex.index] += element.weight
                if name in side:
                    share[vertex.index] += element.weight
    return np.divide(share, total, out=np.zeros_like(share), where=total > 0)


class FixesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs = built()

    def setUp(self):
        at_rest(self.rig)
        bpy.context.view_layer.update()

    def test_a_fix_for_each_joint_and_side(self):
        names = sorted(fix.name for fix in correctives.fixes(self.rig))
        self.assertEqual(names, sorted(side + joint for side in ("Left", "Right") for joint in JOINTS))
        keys = self.objs["Body"].data.shape_keys.key_blocks
        for name in names:
            self.assertIn(correctives.PREFIX + name, keys)

    def test_the_bend_of_each_joint(self):
        for name, degrees in (("LeftKnee", 90.0), ("LeftKneeDeep", 150.0), ("LeftElbow", 90.0),
                              ("LeftElbowDeep", 140.0), ("LeftHip", 90.0), ("LeftShoulder", 40.0),
                              ("LeftShoulderUp", 140.0)):
            fix = fix_of(self.rig, name)
            self.assertAlmostEqual(math.degrees(fix.angle), degrees, delta=2.0, msg=name)
        self.assertGreater(fix_of(self.rig, "LeftShoulderUp").target.z, 0.99)  # the arm straight up
        deep = fix_of(self.rig, "LeftKneeDeep")
        self.assertGreater(deep.target.z, 0.8)  # 150 degrees from hanging down, back towards up
        self.assertGreater(deep.target.y, 0.45)
        self.assertEqual((deep.axis - fix_of(self.rig, "LeftKnee").axis).length < 1e-6, True)  # the same arc
        self.assertGreater(fix_of(self.rig, "LeftKnee").target.y, 0.9)  # the lower leg goes back
        self.assertLess(fix_of(self.rig, "LeftHip").target.y, -0.9)  # the thigh comes forward
        self.assertLess(fix_of(self.rig, "LeftElbow").target.y, -0.9)  # the forearm comes forward
        self.assertLess(fix_of(self.rig, "LeftShoulder").target.z, -0.99)  # the arm down

    def test_the_driver_follows_the_bend(self):
        body = self.objs["Body"]
        for name in ("RightHip", "RightShoulder", "LeftShoulderUp", "LeftKneeDeep", "RightElbowDeep"):
            fix = fix_of(self.rig, name)
            key = correctives.PREFIX + name
            self.assertTrue(body.data.shape_keys.animation_data.drivers.find(
                'key_blocks["%s"].value' % key).driver.is_simple_expression, name)  # no Python needed
            self.assertAlmostEqual(value(body, key), 0.0, places=3, msg=name)
            for fraction in (0.5, 1.0):
                bend = fix.start + fraction * (fix.angle - fix.start)
                turn(self.rig, fix.child, fix.axis, bend)
                self.assertAlmostEqual(value(body, key), fraction, delta=0.01, msg=name)
            turn(self.rig, fix.child, fix.axis, min(fix.angle + math.radians(20.0), math.radians(175.0)))
            self.assertAlmostEqual(value(body, key), 1.0, delta=0.01, msg=name)  # past the pose: kept at full

    def test_a_deeper_bend_hands_over_to_the_deep_fix(self):
        """Kneeling or a forearm folded right up: the 90 degree fix fades out as the deep one takes over."""
        body = self.objs["Body"]
        for name in ("LeftKnee", "RightElbow"):
            first, deep = fix_of(self.rig, name), fix_of(self.rig, name + "Deep")
            self.assertAlmostEqual(first.end, deep.angle, places=6)
            self.assertAlmostEqual(deep.start, first.angle, places=6)
            middle = (first.angle + deep.angle) / 2.0
            for bend, want_first, want_deep in ((0.5 * first.angle, 0.5, 0.0), (first.angle, 1.0, 0.0),
                                                (middle, 0.5, 0.5), (deep.angle, 0.0, 1.0)):
                turn(self.rig, first.child, first.axis, bend)
                self.assertAlmostEqual(value(body, correctives.PREFIX + first.name), want_first, delta=0.01,
                                       msg=(name, math.degrees(bend)))
                self.assertAlmostEqual(value(body, correctives.PREFIX + deep.name), want_deep, delta=0.01,
                                       msg=(name, math.degrees(bend)))

    def test_a_limb_moving_elsewhere_leaves_the_fix(self):
        body = self.objs["Body"]
        fix = fix_of(self.rig, "LeftHip")
        for axis, angle, what in ((fix.axis, -0.5, "swung back"),
                                  (fix.rest.cross(fix.axis), math.radians(90.0), "raised to the side"),
                                  (fix.rest, math.radians(90.0), "twisted about itself")):
            turn(self.rig, fix.child, axis, angle)
            self.assertLess(value(body, correctives.PREFIX + "LeftHip"), 1e-3, what)

    def test_the_shape_is_the_rotation_blend(self):
        """At the fix's pose with the key on, each vertex is where turning it about the joint by its share of the bend
        puts it."""
        body = self.objs["Body"]
        for name in ("LeftKnee", "LeftHip", "LeftElbow", "LeftKneeDeep", "LeftShoulderUp"):
            fix = fix_of(self.rig, name)
            turn(self.rig, fix.child, fix.axis, fix.angle)
            share = child_share(self.rig, body, fix.child)
            blended = np.nonzero((share > 0.01) & (share < 0.99))[0]
            self.assertGreater(len(blended), 10, name)
            got = evaluated(body)
            to_arm = self.rig.matrix_world.inverted() @ body.matrix_world
            rest = [to_arm @ v.co for v in body.data.vertices]
            worst = 0.0
            for i in blended:  # the other fixes stay at 0: their joints are not bent
                want = fix.joint + Matrix.Rotation(share[i] * fix.angle, 3, fix.axis) @ (rest[i] - fix.joint)
                worst = max(worst, (to_arm @ Vector(got[i]) - want).length)
            self.assertLess(worst, 1e-4, name)

    def test_vertices_on_one_side_do_not_move(self):
        body = self.objs["Body"]
        keys = body.data.shape_keys
        base = np.array([v.co for v in keys.reference_key.data])
        for fix in correctives.fixes(self.rig):
            share = child_share(self.rig, body, fix.child)
            moved = np.linalg.norm(np.array([v.co for v in keys.key_blocks[correctives.PREFIX + fix.name].data]) - base,
                                   axis=1)
            rigid = (share < 1e-6) | (share > 1 - 1e-6)
            self.assertLess(moved[rigid].max(), 1e-7, fix.name)
            self.assertGreater(moved.max(), 1e-3, fix.name)


class RebuildTest(unittest.TestCase):
    def test_building_again_replaces_the_fixes(self):
        rig, objs = built()
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        names = [block.name for block in objs["Body"].data.shape_keys.key_blocks]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len([name for name in names if name.startswith(correctives.PREFIX)]), 14)

    def test_no_fixes_on_a_mirrored_half(self):
        """A shape key sits under the Mirror modifier: a fix made on one half would show on the other half too, whose
        arm is not bent (a sleeve flew 0.48 m in Wave). lr_shape, a real model, has such halves."""
        import dasktoon_rig_regions_test as rt
        from bl_ui import dasktoon_rig as ui
        rig, _objs = rt.rigged()
        start, end = rt.mirrored(rt.ARM_START), rt.mirrored(rt.ARM_END)  # the right arm
        sleeve = rt.merged("Sleeve", [rt.st.tube(tuple(start + (end - start) * 0.3),
                                                 tuple(start + (end - start) * 0.9), 0.07)])
        sleeve.modifiers.new("Mirror", 'MIRROR')
        ui.add_part(rig, sleeve, 'CLOTHING')
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        key = sleeve.data.shape_keys
        self.assertFalse(key is not None and any(b.name.startswith(correctives.PREFIX) for b in key.key_blocks))

    def test_off_removes_them(self):
        rig, objs = built()
        rig.data.dasktoon_rig.bend_fixes = False
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        key = objs["Body"].data.shape_keys
        self.assertFalse(key is not None and any(b.name.startswith(correctives.PREFIX) for b in key.key_blocks))
        self.assertFalse(key is not None and key.animation_data is not None and len(key.animation_data.drivers))

    def test_a_t_pose_shoulder_turns_a_right_angle_and_a_hanging_arm_has_none(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        from dasktoon_rig import skeleton
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        self.assertAlmostEqual(math.degrees(fix_of(rig, "LeftShoulder").angle), 90.0, delta=1.0)
        rig.data.use_mirror_x = False  # only the left arm hangs
        with skeleton.editing(bpy.context, rig) as edit:
            for name in ("LeftUpperArm", "LeftLowerArm", "LeftHand"):
                bone = edit[name]
                top = edit["LeftUpperArm"].head.copy()
                length_from_top = ((bone.head - top).length, (bone.tail - top).length)
                bone.head = top + Vector((0.02, 0.0, -length_from_top[0]))
                bone.tail = top + Vector((0.02, 0.0, -length_from_top[1]))
        self.assertNotIn("LeftShoulder", [fix.name for fix in correctives.fixes(rig)])
        self.assertIn("RightShoulder", [fix.name for fix in correctives.fixes(rig)])


if __name__ == "__main__":
    tu.run_tests()
