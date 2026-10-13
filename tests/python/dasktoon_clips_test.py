# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Clips of a character (clips spec 3-5): one Action each, assigned to every part of the character (the armature, the
objects of the character, the Keys of its meshes); new keys go into the clip in use; the animation the parts already
have becomes the first clip; the clip menu, name and Loop in the character timeline."""

import os
import sys
import unittest

import bpy
from bpy_extras import anim_utils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_animation_filter_test as ft  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_animation as ui  # noqa: E402
from dasktoon_animation import clips  # noqa: E402


def paths(action, idb):
    """Data paths `action` holds in the slot of `idb`."""
    prefix = "KE" if idb.id_type == 'KEY' else "OB"
    slot = next((s for s in action.slots if s.identifier == prefix + idb.name), None)
    bag = anim_utils.action_get_channelbag_for_slot(action, slot) if slot is not None else None
    return {fc.data_path for fc in bag.fcurves} if bag is not None else set()


class ClipTest(unittest.TestCase):
    def setUp(self):
        ft.scene()
        self.rig, self.face, self.hat = (bpy.data.objects[name] for name in ("Rig", "Face", "Hat"))
        self.key = self.face.data.shape_keys
        self.objects = list(bpy.context.view_layer.objects)

    def test_existing_animation_becomes_the_first_clip(self):
        walk = clips.new(self.rig, self.objects, "Walk")
        first = bpy.data.actions["Clip"]
        self.assertEqual([clip.name for clip in clips.clips_of(self.rig)], ["Clip", "Walk"])
        self.assertEqual(paths(first, self.rig), {'pose.bones["Root"].location', 'pose.bones["Arm"].location'})
        self.assertEqual(paths(first, self.key), {'key_blocks["Smile"].value'})
        self.assertEqual(paths(first, self.hat), {"location"})
        self.assertIs(clips.current(self.rig), walk)
        self.assertTrue(first.use_fake_user and walk.use_fake_user)  # a clip not in use is kept in the file

    def test_new_clip_is_assigned_to_every_part(self):
        walk = clips.new(self.rig, self.objects, "Walk")
        for idb in (self.rig, self.face, self.key, self.hat):
            self.assertEqual(idb.animation_data.action, walk, idb.name)
        self.assertNotEqual(bpy.data.objects["Rig2"].animation_data.action, walk)
        self.assertEqual(clips.clips_of(bpy.data.objects["Rig2"]), [])

    def test_switching_clips_rests_what_the_new_clip_does_not_key(self):
        """A clip shows only its own animation: what another clip keys and it does not goes back to rest (real model
        test: the clip Talk kept the arm Wave raised, in DaskToon and in the exported FBX)."""
        scene = bpy.context.scene
        wave = clips.new(self.rig, self.objects, "Wave")
        arm = self.rig.pose.bones["Arm"]
        arm.rotation_mode = 'XYZ'
        arm.rotation_euler = (0.5, 0.0, 0.0)
        arm.keyframe_insert("rotation_euler", frame=1)
        smile = self.key.key_blocks["Smile"]
        smile.value = 0.8
        smile.keyframe_insert("value", frame=1)
        talk = clips.new(self.rig, self.objects, "Talk")
        clips.use(self.rig, self.objects, wave)
        scene.frame_set(1)
        self.assertAlmostEqual(arm.rotation_euler.x, 0.5, places=5)
        arm.scale = (1.2, 1.2, 1.2)  # no clip keys it: it stays
        clips.use(self.rig, self.objects, talk)
        scene.frame_set(1)
        self.assertEqual(tuple(arm.rotation_euler), (0.0, 0.0, 0.0))
        self.assertEqual(smile.value, 0.0)
        self.assertAlmostEqual(arm.scale.x, 1.2, places=5)
        clips.use(self.rig, self.objects, wave)
        scene.frame_set(1)
        self.assertAlmostEqual(arm.rotation_euler.x, 0.5, places=5)

    def test_keys_go_into_the_clip(self):
        walk = clips.new(self.rig, self.objects, "Walk")
        self.rig.pose.bones["Root"].keyframe_insert("rotation_quaternion", frame=4)
        self.key.key_blocks["Smile"].keyframe_insert("value", frame=4)
        self.assertEqual(paths(walk, self.rig), {'pose.bones["Root"].rotation_quaternion'})
        self.assertEqual(paths(walk, self.key), {'key_blocks["Smile"].value'})

    def test_switching_and_the_preview_range(self):
        clips.new(self.rig, self.objects, "Walk")
        first = bpy.data.actions["Clip"]
        self.hat.location = (1.0, 0.0, 0.0)
        clips.use(self.rig, self.objects, first, bpy.context.scene)
        self.hat.keyframe_insert("location", frame=20)
        clips.use(self.rig, self.objects, first, bpy.context.scene)
        self.assertIs(clips.current(self.rig), first)
        self.assertEqual(self.key.animation_data.action_slot.identifier, "KE" + self.key.name)
        self.assertEqual(clips.frame_range(first), (1, 20))
        scene = bpy.context.scene
        self.assertTrue(scene.use_preview_range)
        self.assertEqual((scene.frame_preview_start, scene.frame_preview_end), (1, 20))

    def test_loop(self):
        walk = clips.new(self.rig, self.objects, "Walk")
        self.assertFalse(walk.use_cyclic)
        walk.use_cyclic = True
        self.assertTrue(walk.use_cyclic)

    def test_delete(self):
        walk = clips.new(self.rig, self.objects, "Walk")
        first = bpy.data.actions["Clip"]
        clips.delete(self.rig, self.objects, walk)
        self.assertNotIn("Walk", bpy.data.actions)
        self.assertIs(clips.current(self.rig), first)
        clips.delete(self.rig, self.objects, first)
        self.assertIsNone(self.rig.animation_data.action)
        self.assertIsNone(self.key.animation_data.action)

    def test_operators_and_header(self):
        for obj in self.objects:
            obj.select_set(obj == self.face)
        bpy.context.view_layer.objects.active = self.face
        self.assertEqual(bpy.ops.dasktoon.clip_new(), {'FINISHED'})
        current = clips.current(self.rig)
        self.assertEqual(current.name, "Clip.001")
        self.assertEqual(bpy.ops.dasktoon.clip_use(clip="Clip"), {'FINISHED'})
        self.assertEqual(clips.current(self.rig).name, "Clip")
        layout = tu.RecordingLayout()
        ui.draw_character_header(layout, bpy.context)
        self.assertIn(("menu", "DASKTOON_MT_character_clips", "Clip"), [entry[:3] for entry in layout.log])
        # The clip's name and Loop; then the Onion Skin and Fast Action switches (anime timing spec 6, 7).
        self.assertEqual([entry[1] for entry in layout.log if entry[0] == "prop"],
                         ["name", "use_cyclic", "show", "enabled"])
        self.assertIn("dasktoon.clip_new", [idname for idname, _text in tu.operators(layout.log)])
        menu = tu.draw(bpy.types.DASKTOON_MT_character_clips)
        self.assertEqual([text for idname, text in tu.operators(menu) if idname == "dasktoon.clip_use"],
                         ["Clip", "Clip.001"])

    def test_texts(self):
        import dasktoon_i18n_utils as iu
        from bl_ui import dasktoon_translations as dt
        prop = bpy.types.Action.bl_rna.properties["dasktoon_character"]
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated({prop.name, prop.description}, dt.KEEP), [])


if __name__ == "__main__":
    tu.run_tests()
