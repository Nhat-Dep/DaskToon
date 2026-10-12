# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sway of the test character with DaskToon's Spring constraint (anime rig spec 9.4): Build Rig sets the constraints up,
the hips dashing sideways sway the skirt, scrubbing and the start frame behave, Live Sway mutes, Bake Sway keys."""

import math
import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_rig import build, sway  # noqa: E402

BONE = "Skirt1_3"


def character():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    for obj, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
        ui.add_part(rig, objs[obj], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 20
    hips = rig.pose.bones["Hips"]
    for frame, x in ((1, 0.0), (6, 0.3), (12, 0.3)):  # the hips dash sideways, then stop
        hips.location = (x, 0.0, 0.0)
        hips.keyframe_insert("location", frame=frame)
    scene.frame_set(1)
    return rig


def angle(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b))))))


def play(rig, last, name=BONE):
    out = {}
    for frame in range(1, last + 1):
        bpy.context.scene.frame_set(frame)
        out[frame] = sway.direction(rig, name)
    return out


def unswayed(rig, frame, name=BONE):
    """The bone's direction on `frame` with every Spring constraint muted (the cache stays)."""
    sway.set_live(rig, False)
    bpy.context.scene.frame_set(frame)
    found = sway.direction(rig, name)
    sway.set_live(rig, True)
    bpy.context.scene.frame_set(frame)
    return found


class SwayTest(unittest.TestCase):
    def setUp(self):
        self.rig = character()

    def test_chains(self):
        found = dict((names[0], (part, names)) for part, names in sway.chains(self.rig))
        self.assertEqual(found["Hair_1"], ("Hair", ["Hair_1", "Hair_2", "Hair_3", "Hair_4"]))
        self.assertEqual(found["Skirt1_1"], ("Skirt", ["Skirt1_1", "Skirt1_2", "Skirt1_3"]))
        self.assertEqual(len(found), 9)

    def test_build_adds_spring_constraints(self):
        skirt = self.rig.data.dasktoon_rig.parts["Skirt"]
        for _part, names in sway.chains(self.rig):
            for name in names:
                cons = [c for c in self.rig.pose.bones[name].constraints if c.type == 'SPRING']
                self.assertEqual(len(cons), 1, name)
                self.assertEqual(cons[0].name, sway.CONSTRAINT_NAME)
                self.assertEqual(len(cons[0].colliders), len(build.COLLIDER_BONES))
                self.assertFalse(cons[0].mute)
        con = sway.spring_constraint(self.rig.pose.bones[BONE])
        self.assertEqual((con.stiffness, con.gravity, con.drag), (skirt.stiffness, skirt.gravity, skirt.drag))
        self.assertEqual({c.subtarget for c in con.colliders}, set(build.COLLIDER_BONES))
        self.assertEqual({c.target for c in con.colliders}, {self.rig})

    def test_python_frame_handlers_are_gone(self):
        names = {h.__name__ for h in bpy.app.handlers.frame_change_post + bpy.app.handlers.frame_change_pre}
        self.assertFalse(names & {"frame_post", "frame_pre"})

    def test_moving_hips_sway_the_skirt(self):
        played = play(self.rig, 12)
        self.assertLess(angle(played[1], unswayed(self.rig, 1)), 0.01)
        self.assertGreater(angle(played[8], unswayed(self.rig, 8)), 2.0)

    def test_back_to_start_resets(self):
        play(self.rig, 8)
        bpy.context.scene.frame_set(1)
        self.assertLess(angle(sway.direction(self.rig, BONE), unswayed(self.rig, 1)), 0.01)

    def test_revisiting_a_frame_gives_the_same_pose(self):
        played = play(self.rig, 12)
        bpy.context.scene.frame_set(7)
        np.testing.assert_allclose(sway.direction(self.rig, BONE), played[7], atol=1e-6)
        again = play(self.rig, 12)
        np.testing.assert_allclose(again[12], played[12], atol=1e-6)

    def test_live_sway_off_mutes(self):
        self.rig.data.dasktoon_rig.live_sway = False
        self.assertTrue(all(sway.spring_constraint(self.rig.pose.bones[n]).mute
                            for _p, names in sway.chains(self.rig) for n in names))
        played = play(self.rig, 8)
        self.assertLess(angle(played[8], unswayed(self.rig, 8)), 0.01)

    def test_settings_reach_the_constraints(self):
        data = self.rig.data.dasktoon_rig
        data.parts["Skirt"].stiffness = 2.5
        con = sway.spring_constraint(self.rig.pose.bones["Skirt1_1"])
        self.assertAlmostEqual(con.stiffness, 2.5, places=6)
        hips = next(c for c in data.colliders if c.bone == "Hips")
        hips.radius = 0.123
        con_hips = next(c for c in con.colliders if c.subtarget == "Hips")
        self.assertAlmostEqual(con_hips.radius, 0.123, places=6)

    def test_keyed_chain_bone_is_the_rest_direction(self):
        pb = self.rig.pose.bones["Hair_1"]
        pb.rotation_quaternion = (0.96592583, 0.25881905, 0.0, 0.0)  # 30 degrees, keyed
        pb.keyframe_insert("rotation_quaternion", frame=1)
        part = self.rig.data.dasktoon_rig.parts["Hair"]
        part.stiffness = 4.0
        part.gravity = 0.0
        played = play(self.rig, 30, "Hair_1")
        self.assertLess(angle(played[30], unswayed(self.rig, 30, "Hair_1")), 3.0)

    def test_bake_matches_live(self):
        live = play(self.rig, 12)
        self.assertEqual(sway.bake(bpy.context, self.rig, 1, 12), (12, 4 + 8 * 3))
        self.assertFalse(self.rig.data.dasktoon_rig.live_sway)
        self.assertTrue(sway.spring_constraint(self.rig.pose.bones[BONE]).mute)
        for frame in (5, 9, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(sway.direction(self.rig, BONE), live[frame], atol=1e-4)

    def test_bake_twice_does_not_stack(self):
        sway.bake(bpy.context, self.rig, 1, 12)
        first = {}
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            first[frame] = sway.direction(self.rig, BONE)
        sway.bake(bpy.context, self.rig, 1, 12)
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(sway.direction(self.rig, BONE), first[frame], atol=1e-4)


class SuppressTest(unittest.TestCase):
    def test_suppressed_chains_rest_and_come_back(self):
        rig = character()
        play(rig, 8)
        hair = sway.direction(rig, "Hair_4")
        skirt_rest = unswayed(rig, 8)
        with sway.suppressed(rig, {"Skirt"}):
            self.assertTrue(sway.spring_constraint(rig.pose.bones[BONE]).mute)
            self.assertFalse(sway.spring_constraint(rig.pose.bones["Hair_4"]).mute)
            bpy.context.view_layer.update()
            self.assertLess(angle(sway.direction(rig, BONE), skirt_rest), 0.01)
            np.testing.assert_allclose(sway.direction(rig, "Hair_4"), hair, atol=1e-6)
        self.assertFalse(sway.spring_constraint(rig.pose.bones[BONE]).mute)

    def test_world_colliders(self):
        rig = character()
        found = sway.world_colliders(rig)
        self.assertEqual(len(found), len(build.COLLIDER_BONES))
        head, tail, radius = found[0]
        self.assertGreater(np.linalg.norm(tail - head), 0.0)
        self.assertGreater(radius, 0.0)


if __name__ == "__main__":
    tu.run_tests()
