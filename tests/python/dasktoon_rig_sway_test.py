# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sway and Bake Sway on the test character (anime rig spec 9.4)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_rig import build, parts, sway  # noqa: E402

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


def quat(rig, name):
    return np.array(rig.pose.bones[name].rotation_quaternion)


def play(rig, last):
    out = {}
    for frame in range(1, last + 1):
        bpy.context.scene.frame_set(frame)
        out[frame] = quat(rig, BONE)
    return out


class SwayTest(unittest.TestCase):
    def setUp(self):
        self.rig = character()

    def test_chains(self):
        found = dict((names[0], (part, names)) for part, names in sway.chains(self.rig))
        self.assertEqual(found["Hair_1"], ("Hair", ["Hair_1", "Hair_2", "Hair_3", "Hair_4"]))
        self.assertEqual(found["Skirt1_1"], ("Skirt", ["Skirt1_1", "Skirt1_2", "Skirt1_3"]))
        self.assertEqual(len(found), 9)

    def test_moving_hips_sway_the_skirt(self):
        played = play(self.rig, 12)
        self.assertAlmostEqual(abs(played[1][0]), 1.0, places=6)  # no sway on the first frame
        self.assertLess(abs(played[8][0]), 0.999)

    def test_back_to_start_resets(self):
        play(self.rig, 8)
        bpy.context.scene.frame_set(1)
        self.assertAlmostEqual(abs(quat(self.rig, BONE)[0]), 1.0, places=6)

    def test_revisiting_a_frame_gives_the_same_pose(self):
        played = play(self.rig, 12)
        bpy.context.scene.frame_set(7)
        np.testing.assert_allclose(quat(self.rig, BONE), played[7], atol=1e-6)  # float32 storage
        again = play(self.rig, 12)
        np.testing.assert_allclose(again[12], played[12], atol=1e-6)

    def test_tails_follow_the_simulation(self):
        play(self.rig, 9)
        bpy.context.view_layer.update()
        state = sway._cache[self.rig.session_uid][9]
        names = dict(sway.chains(self.rig))["Skirt"]
        index = [n for _p, n in sway.chains(self.rig)].index(names)
        world = self.rig.matrix_world
        for i, name in enumerate(names):
            tail = np.array(world @ self.rig.pose.bones[name].tail)
            np.testing.assert_allclose(tail, state[index].current[i], atol=1e-4)

    def test_live_sway_off_leaves_bones(self):
        self.rig.data.dasktoon_rig.live_sway = False
        pb = self.rig.pose.bones[BONE]
        pb.rotation_quaternion = (0.9, 0.1, 0.0, 0.0)
        play(self.rig, 6)
        np.testing.assert_allclose(quat(self.rig, BONE), (0.9, 0.1, 0.0, 0.0), atol=1e-6)

    def test_keyed_chain_bone_is_the_rest_direction(self):
        pb = self.rig.pose.bones["Hair_1"]
        pb.rotation_quaternion = (0.96592583, 0.25881905, 0.0, 0.0)  # 30 degrees, keyed on every frame
        pb.keyframe_insert("rotation_quaternion", frame=1)
        still = dict(sway.chains(self.rig))
        self.rig.data.dasktoon_rig.parts["Hair"].stiffness = 4.0
        self.rig.data.dasktoon_rig.parts["Hair"].gravity = 0.0
        played = {}
        for frame in range(1, 30):
            bpy.context.scene.frame_set(frame)
            played[frame] = quat(self.rig, "Hair_1")
        # With strong stiffness and no gravity the lock settles on its keyed pose instead of drifting each frame.
        np.testing.assert_allclose(played[29], (0.96592583, 0.25881905, 0.0, 0.0), atol=0.05)
        self.assertIn("Hair", still)

    def test_parameter_change_clears_the_cache(self):
        play(self.rig, 4)
        self.assertTrue(sway._cache.get(self.rig.session_uid))
        self.rig.data.dasktoon_rig.parts["Skirt"].drag = 0.9
        self.assertFalse(sway._cache.get(self.rig.session_uid))

    def test_bake_matches_live(self):
        live = play(self.rig, 12)
        frames, bones = sway.bake(bpy.context, self.rig, 1, 12)
        self.assertEqual((frames, bones), (12, 4 + 8 * 3))
        self.assertFalse(self.rig.data.dasktoon_rig.live_sway)
        for frame in (5, 9, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(quat(self.rig, BONE), live[frame], atol=1e-5)

    def test_bake_twice_does_not_stack(self):
        sway.bake(bpy.context, self.rig, 1, 12)
        first = {}
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            first[frame] = quat(self.rig, BONE)
        sway.bake(bpy.context, self.rig, 1, 12)
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(quat(self.rig, BONE), first[frame], atol=1e-5)


if __name__ == "__main__":
    tu.run_tests()
