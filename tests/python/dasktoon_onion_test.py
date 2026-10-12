# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Onion skin (anime timing spec 6): the ghosts are the character's meshes at the keyed frames before and after the
current one (of the clip it plays); they are copied by jumping to those frames and back, which keeps the frame and the
selection, and is not done while the pose has changes that are not keyed yet."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_animation_filter_test as ft  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_animation import clips, onion, timing  # noqa: E402


def character():
    """The filter test's character with a clip "Walk": bone Root keyed at frames 1, 7 and 12, shape key Smile (which
    lifts the Face's first vertex by 1) keyed 0 at frame 1 and 1 at frame 12. The Face sits at x = 1."""
    ft.scene()
    rig = bpy.data.objects["Rig"]
    face = bpy.data.objects["Face"]
    face.location.x = 1.0
    face.data.shape_keys.key_blocks["Smile"].data[0].co.z = 1.0
    walk = clips.new(rig, list(bpy.context.view_layer.objects), "Walk")
    root, smile = rig.pose.bones["Root"], face.data.shape_keys.key_blocks["Smile"]
    for frame in (1, 7, 12):
        root.location.x = float(frame)
        root.keyframe_insert("location", index=0, frame=frame)
    for frame, value in ((1, 0.0), (12, 1.0)):
        smile.value = value
        smile.keyframe_insert("value", frame=frame)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig
    return rig, face, walk


class GhostFramesTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.face, self.walk = character()

    def test_keyed_frames_nearest_first(self):
        self.assertEqual(onion.key_frames(self.walk), [1, 7, 12])
        self.assertEqual(onion.ghost_frames(self.walk, 8, 1, 1), ([7], [12]))
        self.assertEqual(onion.ghost_frames(self.walk, 8, 2, 2), ([7, 1], [12]))
        self.assertEqual(onion.ghost_frames(self.walk, 7, 1, 1), ([1], [12]))
        self.assertEqual(onion.ghost_frames(self.walk, 12, 1, 0), ([7], []))
        self.assertEqual(onion.ghost_frames(None, 8, 1, 1), ([], []))

    def test_on_twos_the_shown_drawing_is_no_ghost(self):
        timing.set_step(self.walk, 1, 2)
        # Frame 8 shows the drawing of frame 7: the ghost before it is frame 1.
        self.assertEqual(onion.ghost_frames(self.walk, 8, 1, 1), ([1], [12]))


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.face, self.walk = character()

    def test_meshes_at_other_frames_in_world_space(self):
        scene = bpy.context.scene
        scene.frame_set(5)
        smile = self.face.data.shape_keys.key_blocks["Smile"]
        at_five = smile.value
        shapes = onion.capture(bpy.context, [self.face], [1, 12])
        self.assertEqual(sorted(shapes), [1, 12])
        (name, first), = shapes[1]
        (_name, last), = shapes[12]
        self.assertEqual(name, "Face")
        self.assertEqual(first.shape, (3, 3))  # one triangle
        self.assertAlmostEqual(float(first[0][0]), 1.0, places=5)  # world space: the Face is at x = 1
        self.assertAlmostEqual(float(first[0][2]), 0.0, places=5)
        self.assertAlmostEqual(float(last[0][2]), 1.0, places=5)   # Smile at 1 lifts the first vertex
        self.assertEqual((scene.frame_current, scene.frame_subframe), (5, 0.0))
        self.assertEqual([obj.name for obj in bpy.context.selected_objects], ["Rig"])
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)
        self.assertAlmostEqual(smile.value, at_five, places=5)

    def test_unkeyed_changes(self):
        bpy.context.scene.frame_set(4)
        ids = clips.parts(self.rig, list(bpy.context.view_layer.objects))
        self.assertFalse(onion.unkeyed_changes(ids, 4))
        self.rig.pose.bones["Root"].location.x = 99.0
        self.assertTrue(onion.unkeyed_changes(ids, 4))
        bpy.context.scene.frame_set(4)
        self.assertFalse(onion.unkeyed_changes(ids, 4))


class OnionSkinTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.face, self.walk = character()
        self.settings = bpy.context.scene.dasktoon_onion
        self.settings.show = True

    def test_refresh_keeps_ghosts_of_the_character(self):
        from bl_ui import dasktoon_animation as ui
        self.assertEqual((self.settings.before, self.settings.after), (1, 1))
        bpy.context.scene.frame_set(8)
        self.assertTrue(ui.onion_refresh(bpy.context))
        ghosts = ui.onion_ghosts()
        self.assertEqual([(side, frame) for side, _rank, frame, _shapes in ghosts], [('BEFORE', 7), ('AFTER', 12)])
        self.assertEqual([name for name, _tris in ghosts[0][3]], ["Face"])
        self.assertEqual(bpy.context.scene.frame_current, 8)

    def test_not_while_the_pose_has_unkeyed_changes(self):
        from bl_ui import dasktoon_animation as ui
        bpy.context.scene.frame_set(8)
        ui.onion_refresh(bpy.context)
        before = ui.onion_ghosts()
        self.settings.before = 2
        self.rig.pose.bones["Root"].location.x = 99.0
        self.assertFalse(ui.onion_refresh(bpy.context))
        self.assertEqual(self.rig.pose.bones["Root"].location.x, 99.0)  # the change is kept
        self.assertIs(ui.onion_ghosts(), before)
        bpy.context.scene.frame_set(8)
        self.assertTrue(ui.onion_refresh(bpy.context))
        self.assertEqual([frame for _side, _rank, frame, _shapes in ui.onion_ghosts()], [7, 1, 12])

    def test_no_ghosts_without_animation(self):
        from bl_ui import dasktoon_animation as ui
        rig2 = bpy.data.objects["Rig2"]
        rig2.animation_data_clear()
        self.rig.select_set(False)
        rig2.select_set(True)
        bpy.context.view_layer.objects.active = rig2
        self.assertTrue(ui.onion_refresh(bpy.context))
        self.assertEqual(ui.onion_ghosts(), [])

    def test_off_no_ghosts(self):
        from bl_ui import dasktoon_animation as ui
        self.settings.show = False
        ui.onion_refresh(bpy.context)
        self.assertEqual(ui.onion_ghosts(), [])

    def test_popover(self):
        from bl_ui import dasktoon_animation as ui
        log = tu.draw(ui.DASKTOON_PT_onion_skin)
        self.assertEqual([entry[1] for entry in log if entry[0] == "prop"], ["before", "after", "opacity"])


if __name__ == "__main__":
    tu.run_tests()
