# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Key Pose and the "DaskToon Character" keying set (Animation tab spec 5): selecting any part of a character keys
every bone, every shape key but the Basis and every expression controller of it; another selected object gets its
location, rotation and scale. Scenes without an active keying set use it for I."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_animation_filter_test as ft  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_animation as ui  # noqa: E402
from dasktoon_animation import KEYING_SET, character  # noqa: E402

FRAME = 5


def select(names):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj.name in names)
    bpy.context.view_layer.objects.active = bpy.data.objects[sorted(names)[0]] if names else None


def keys_at(id_data, frame=FRAME):
    """"path[index]" of the curves of `id_data` with a key on `frame`."""
    return {"%s[%d]" % (fc.data_path, fc.array_index) for fc in ft.fcurves(id_data)
            if any(abs(key.co.x - frame) < 1e-6 for key in fc.keyframe_points)}


class CharacterTest(unittest.TestCase):
    def setUp(self):
        ft.scene()
        self.face = bpy.data.objects["Face"]
        self.face.dask_shape_controllers.groups.add()
        bpy.context.scene.frame_set(FRAME)

    def test_members(self):
        rig, rig2 = bpy.data.objects["Rig"], bpy.data.objects["Rig2"]
        objects = list(bpy.context.view_layer.objects)
        self.assertEqual({obj.name for obj in character.members(rig, objects)}, {"Rig", "Face", "Hat"})
        self.assertEqual(character.armatures_of(self.face), [rig])
        self.assertEqual(character.armatures_of(bpy.data.objects["Prop"]), [])
        self.face.modifiers.new("Second", 'ARMATURE').object = rig2
        self.assertEqual(character.armatures_of(self.face), [rig, rig2])
        select({"Face"})
        self.assertEqual([arm.name for arm in character.selected_characters(bpy.context)], ["Rig", "Rig2"])

    def test_key_pose_keys_the_whole_character(self):
        select({"Face"})
        self.assertEqual(bpy.ops.dasktoon.key_pose(), {'FINISHED'})
        rig_paths = {path.rsplit("[", 1)[0] for path in keys_at(bpy.data.objects["Rig"])}
        self.assertLessEqual({'pose.bones["Root"].location', 'pose.bones["Root"].rotation_quaternion',
                              'pose.bones["Root"].scale', 'pose.bones["Arm"].rotation_quaternion',
                              'pose.bones["Arm"].scale'}, rig_paths)
        self.assertNotIn('pose.bones["Arm"].location', rig_paths)  # connected to Root
        self.assertEqual(keys_at(self.face.data.shape_keys), {'key_blocks["Smile"].value[0]'})
        self.assertEqual(keys_at(self.face), {"dask_shape_controllers.groups[0].handle_x[0]",
                                              "dask_shape_controllers.groups[0].handle_y[0]"})
        self.assertEqual(keys_at(bpy.data.objects["Hat"]), set())
        self.assertEqual(keys_at(bpy.data.objects["Rig2"]), set())

    def test_the_keying_set_keys_through_blender(self):
        # I with this keying set active: Blender runs the registered keying set (here from a 3D Viewport).
        select({"Face"})
        screen = bpy.data.workspaces["Animation"].screens[0]
        area = next(a for a in screen.areas if a.type == 'VIEW_3D')
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(screen=screen, area=area, region=region):
            bpy.ops.anim.keyframe_insert_by_name(type=KEYING_SET)
        self.assertEqual(keys_at(self.face.data.shape_keys), {'key_blocks["Smile"].value[0]'})
        self.assertIn('pose.bones["Arm"].scale[0]', keys_at(bpy.data.objects["Rig"]))

    def test_other_objects_key_location_rotation_scale(self):
        select({"Prop"})
        bpy.ops.dasktoon.key_pose()
        self.assertEqual({path.split("[")[0] for path in keys_at(bpy.data.objects["Prop"])},
                         {"location", "rotation_euler", "scale"})

    def test_nothing_selected(self):
        select(set())
        with self.assertRaisesRegex(RuntimeError, "Select a part of a character"):
            bpy.ops.dasktoon.key_pose()

    def test_character_keying_set_is_used_when_the_scene_has_none(self):
        fresh = bpy.data.scenes.new("Fresh")
        self.assertIsNone(fresh.keying_sets_all.active)
        self.assertTrue(ui.use_character_keying_set(fresh))
        self.assertEqual(fresh.keying_sets_all.active.bl_idname, KEYING_SET)
        other = bpy.data.scenes.new("Other")
        other.keying_sets_all.active = next(ks for ks in other.keying_sets_all if ks.bl_idname == "Location")
        self.assertFalse(ui.use_character_keying_set(other))
        self.assertEqual(other.keying_sets_all.active.bl_idname, "Location")

    def test_header_shows_key_pose_with_whole_character(self):
        from bl_ui.space_dopesheet import DOPESHEET_HT_editor_buttons
        screen, area, _region = ft.dopesheet()
        header = next(r for r in area.regions if r.type == 'HEADER')
        space = area.spaces.active
        space.mode = 'DOPESHEET'
        for whole in (True, False):
            space.dopesheet.show_whole_character = whole
            layout = tu.RecordingLayout()
            with bpy.context.temp_override(screen=screen, area=area, region=header):
                DOPESHEET_HT_editor_buttons.draw_header(bpy.context, layout)
            self.assertEqual("dasktoon.key_pose" in [idname for idname, _text in tu.operators(layout.log)], whole)


if __name__ == "__main__":
    tu.run_tests()
