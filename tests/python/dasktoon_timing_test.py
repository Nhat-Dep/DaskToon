# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime timing (anime timing spec 3, 4): a clip's timing table makes it run on 2s, 3s, 4s or hold, changes along the
clip, and applies to the bones and shape keys of the clip alike; a clip without a table is evaluated as before."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_animation_filter_test as ft  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_animation import clips, timing  # noqa: E402


def character():
    """The filter test's character with a clip "Walk": bone Root at x = frame and shape key Smile at frame / 12, keyed
    on every frame 1 to 12."""
    ft.scene()
    rig = bpy.data.objects["Rig"]
    key = bpy.data.objects["Face"].data.shape_keys
    walk = clips.new(rig, list(bpy.context.view_layer.objects), "Walk")
    root, smile = rig.pose.bones["Root"], key.key_blocks["Smile"]
    for frame in range(1, 13):
        root.location = (float(frame), 0.0, 0.0)
        root.keyframe_insert("location", index=0, frame=frame)
        smile.value = frame / 12.0
        smile.keyframe_insert("value", frame=frame)
    return rig, key, walk


def values(rig, key, frame, subframe=0.0):
    bpy.context.scene.frame_set(frame, subframe=subframe)
    return rig.pose.bones["Root"].location.x, key.key_blocks["Smile"].value


class TimingTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.key, self.walk = character()

    def at(self, frame, subframe=0.0):
        return values(self.rig, self.key, frame, subframe)

    def assertHeld(self, frame, drawn, subframe=0.0):
        x, smile = self.at(frame, subframe)
        self.assertAlmostEqual(x, drawn, places=4, msg=(frame, subframe))
        self.assertAlmostEqual(smile, drawn / 12.0, places=4, msg=(frame, subframe))

    def test_no_table_is_blender(self):
        self.assertFalse(timing.has_steps(self.walk))
        for frame in (1, 2, 5, 12):
            self.assertHeld(frame, frame)
        x, _smile = self.at(2, 0.5)
        self.assertTrue(2.0 < x < 3.0, x)

    def test_on_twos(self):
        timing.set_step(self.walk, 1, 2)
        for frame, drawn in ((1, 1), (2, 1), (3, 3), (4, 3), (12, 11)):
            self.assertHeld(frame, drawn)
        self.assertHeld(2, 1, subframe=0.5)  # motion blur samples hold too

    def test_on_threes_and_fours(self):
        timing.set_step(self.walk, 1, 3)
        for frame, drawn in ((3, 1), (4, 4), (6, 4), (7, 7)):
            self.assertHeld(frame, drawn)
        timing.set_step(self.walk, 1, 4)
        for frame, drawn in ((4, 1), (5, 5), (8, 5), (9, 9)):
            self.assertHeld(frame, drawn)

    def test_timing_changes_along_the_clip(self):
        timing.set_step(self.walk, 1, 2)
        timing.set_step(self.walk, 7, 1)
        for frame, drawn in ((6, 5), (7, 7), (8, 8), (9, 9)):
            self.assertHeld(frame, drawn)
        self.assertEqual([(s.frame, s.step) for s in self.walk.dasktoon_timing], [(1, 2), (7, 1)])

    def test_hold(self):
        timing.set_step(self.walk, 3, 0)
        timing.set_step(self.walk, 8, 1)
        for frame, drawn in ((2, 2), (3, 3), (5, 3), (7, 3), (8, 8)):
            self.assertHeld(frame, drawn)

    def test_helpers(self):
        timing.set_step(self.walk, 1, 2)
        timing.set_step(self.walk, 9, 0)
        self.assertTrue(timing.has_steps(self.walk))
        self.assertEqual([timing.step_at(self.walk, f) for f in (0, 1, 8, 9, 20)], [1, 2, 2, 0, 0])
        self.assertEqual([timing.drawn_frame(self.walk, f) for f in (0, 2, 4, 9, 15)], [0, 1, 3, 9, 9])
        timing.set_step(self.walk, 9, 3)  # an existing frame is changed, not added
        self.assertEqual([(s.frame, s.step) for s in self.walk.dasktoon_timing], [(1, 2), (9, 3)])
        timing.remove(self.walk, 1)
        self.assertEqual([(s.frame, s.step) for s in self.walk.dasktoon_timing], [(9, 3)])
        timing.set_step(self.walk, 9, 1)
        self.assertFalse(timing.has_steps(self.walk))


if __name__ == "__main__":
    tu.run_tests()
