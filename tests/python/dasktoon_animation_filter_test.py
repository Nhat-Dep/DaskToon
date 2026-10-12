# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Dope Sheet's Whole Character filter (Animation tab spec 4): selecting any part of a character shows every channel
of it (all bones, the shape keys of its meshes, the objects parented to it); other objects only when selected. Which
channels are shown is read from the keys that Select All selects in the Dope Sheet of the Animation tab."""

import os
import sys
import unittest

import bpy
from bpy_extras import anim_utils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402


def armature(name, bones):
    """An armature object with `bones` [(name, parent, head, tail)], linked to the scene."""
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bone_name, parent, head, tail in bones:
        bone = data.edit_bones.new(bone_name)
        bone.head, bone.tail = head, tail
        if parent is not None:
            bone.parent = data.edit_bones[parent]
            bone.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in obj.pose.bones:
        pb.keyframe_insert("location", frame=1)
    return obj


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.keyframe_insert("location", frame=1)
    return obj


def face(name, rig):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Armature", 'ARMATURE').object = rig
    obj.shape_key_add(name="Basis")
    obj.shape_key_add(name="Smile")
    mesh.shape_keys.key_blocks["Smile"].keyframe_insert("value", frame=1)
    return obj


def scene():
    """Character Rig (bones Root, Arm; mesh Face with shape key Smile; Hat parented to Rig), character Rig2, Prop."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = armature("Rig", [("Root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
                           ("Arm", "Root", (0.0, 0.0, 1.0), (0.0, 0.0, 2.0))])
    face("Face", rig)
    empty("Hat", rig)
    armature("Rig2", [("Root", None, (2.0, 0.0, 0.0), (2.0, 0.0, 1.0))])
    empty("Prop")


def fcurves(id_data):
    anim = id_data.animation_data if id_data is not None else None
    if anim is None or anim.action is None:
        return []
    bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    return list(bag.fcurves) if bag is not None else []


def label(owner, fcurve):
    """"Rig:Root" for a bone's curve, "Face:Smile" for a shape key's, the object's name otherwise."""
    if fcurve.data_path.startswith(('pose.bones["', 'key_blocks["')):
        return "%s:%s" % (owner, fcurve.data_path.split('"')[1])
    return owner


def channels():
    out = []
    for obj in bpy.data.objects:
        out += [(label(obj.name, fc), fc) for fc in fcurves(obj)]
        if obj.type == 'MESH' and obj.data.shape_keys is not None:
            out += [(label(obj.name, fc), fc) for fc in fcurves(obj.data.shape_keys)]
    return out


def dopesheet():
    screen = bpy.data.workspaces["Animation"].screens[0]
    area = next(a for a in screen.areas if a.type == 'DOPESHEET_EDITOR')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return screen, area, region


def shown(selected, whole, only_selected=True):
    """Labels of the channels the Dope Sheet of the Animation tab shows with `selected` objects selected."""
    view_layer = bpy.context.view_layer
    for obj in view_layer.objects:
        obj.select_set(obj.name in selected)
    # The Animation tab works in Pose Mode: an active armature counts as a selected part, as in Blender's filter.
    view_layer.objects.active = bpy.data.objects[sorted(selected)[0]] if selected else None
    for _label, fc in channels():
        for key in fc.keyframe_points:
            key.select_control_point = False
    screen, area, region = dopesheet()
    space = area.spaces.active
    space.mode = 'DOPESHEET'
    space.dopesheet.show_only_selected = only_selected
    space.dopesheet.show_whole_character = whole
    with bpy.context.temp_override(screen=screen, area=area, region=region):
        bpy.ops.action.select_all(action='SELECT')
    return {lab for lab, fc in channels() if any(key.select_control_point for key in fc.keyframe_points)}


CHARACTER = {"Rig:Root", "Rig:Arm", "Face:Smile", "Hat"}


class WholeCharacterTest(unittest.TestCase):
    def setUp(self):
        scene()

    def test_property(self):
        ds = dopesheet()[1].spaces.active.dopesheet
        ds.show_whole_character = False
        self.assertFalse(ds.show_whole_character)
        ds.show_whole_character = True
        self.assertTrue(ds.show_whole_character)

    def test_texts(self):
        prop = bpy.types.DopeSheet.bl_rna.properties["show_whole_character"]
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated({prop.name, prop.description}, dt.KEEP), [])

    def test_header_has_the_switch_in_the_dope_sheet_only(self):
        screen, area, region = dopesheet()
        header = next(r for r in area.regions if r.type == 'HEADER')
        layout = tu.RecordingLayout()
        with bpy.context.temp_override(screen=screen, area=area, region=header):
            from bl_ui import space_dopesheet
            space_dopesheet.dopesheet_filter(layout, bpy.context)
        self.assertIn("show_whole_character", [entry[1] for entry in layout.log if entry[0] == "prop"])

    def test_off_is_blender(self):
        self.assertEqual(shown({"Face"}, whole=False), {"Face:Smile"})

    def test_a_selected_face_shows_the_whole_character(self):
        self.assertEqual(shown({"Face"}, whole=True), CHARACTER)

    def test_a_selected_armature_shows_its_meshes(self):
        self.assertEqual(shown({"Rig"}, whole=True), CHARACTER)

    def test_every_bone_not_only_selected_ones(self):
        rig = bpy.data.objects["Rig"]
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        rig.pose.bones["Root"].select = True
        rig.pose.bones["Arm"].select = False
        self.assertEqual({lab for lab in shown({"Rig"}, whole=False) if lab.startswith("Rig:")}, {"Rig:Root"})
        self.assertLessEqual({"Rig:Root", "Rig:Arm", "Face:Smile"}, shown({"Rig"}, whole=True))
        bpy.ops.object.mode_set(mode='OBJECT')

    def test_other_objects_only_when_selected(self):
        self.assertEqual(shown({"Prop"}, whole=True), {"Prop"})
        self.assertEqual(shown({"Prop", "Hat"}, whole=True), CHARACTER | {"Prop"})

    def test_two_characters(self):
        self.assertEqual(shown({"Face", "Rig2"}, whole=True), CHARACTER | {"Rig2:Root"})

    def test_nothing_selected_shows_nothing(self):
        self.assertEqual(shown(set(), whole=True), set())


if __name__ == "__main__":
    tu.run_tests()
