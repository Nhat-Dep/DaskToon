# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The character side of DaskToon's Animation tab (docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md,
sections 5 and 7): the "DaskToon Character" keying set, Key Pose, and the part of the Dope Sheet header that shows when
Whole Character is on."""

import types

import bpy
import _keyingsets_utils as keyingsets_utils
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import KeyingSetInfo, Operator
from keyingsets_builtins import WholeCharacterMixin


class CharacterKeying(WholeCharacterMixin):
    """What the "DaskToon Character" keying set keys (spec 5). Key Pose keys the same paths itself, so it works from any
    editor."""

    def iterator(self, context, ks):
        from dasktoon_animation import character
        objects = list(context.view_layer.objects)
        for armature in character.selected_characters(context):
            for bone in armature.pose.bones:
                self.generate(context, ks, bone)
            for obj in character.members(armature, objects):
                self.generate_face(ks, obj)
        for obj in context.selected_objects:
            if not character.armatures_of(obj):
                keyingsets_utils.RKS_GEN_location(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_rotation(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_scaling(self, context, ks, obj)

    def generate_face(self, ks, obj):
        """The shape keys (but the Basis) and the expression controllers of a mesh of the character."""
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is not None:
            for block in key.key_blocks:
                if block != key.reference_key:
                    ks.paths.add(key, 'key_blocks["%s"].value' % bpy.utils.escape_identifier(block.name),
                                 group_method='NAMED', group_name=obj.name)
        root = getattr(obj, "dask_shape_controllers", None)
        for i in range(len(root.groups) if root is not None else 0):
            for axis in ("handle_x", "handle_y"):
                ks.paths.add(obj, "dask_shape_controllers.groups[%d].%s" % (i, axis), group_method='NAMED',
                             group_name="Controllers")


class DASKTOON_KS_character(CharacterKeying, KeyingSetInfo):
    """Key the whole pose of the selected characters: every bone, every shape key of their meshes and every expression
    controller; other selected objects get location, rotation and scale"""
    bl_idname = "DASKTOON_KS_character"
    bl_label = "DaskToon Character"

    def poll(self, context):
        from dasktoon_animation import character
        return bool(context.selected_objects) or bool(character.selected_characters(context))


class _Paths(list):
    """Collects what a keying set iterator adds: (ID, data path, index, group)."""

    def add(self, id_block, path, index=-1, group_method='NAMED', group_name=""):
        self.append((id_block, path, index, group_name if group_method == 'NAMED' else ""))


def key_pose(context):
    """Key what the "DaskToon Character" keying set keys, on the current frame. Returns the number of paths keyed."""
    ks = types.SimpleNamespace(paths=_Paths())
    CharacterKeying().iterator(context, ks)
    frame = context.scene.frame_current
    for id_block, path, index, group in ks.paths:
        id_block.keyframe_insert(data_path=path, index=index, frame=frame, group=group)
    return len(ks.paths)


class DASKTOON_OT_key_pose(Operator):
    """Key the whole pose of the selected characters at the current frame: every bone, shape key and controller"""
    bl_idname = "dasktoon.key_pose"
    bl_label = "Key Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from dasktoon_animation import character
        characters = character.selected_characters(context)
        if not characters and not context.selected_objects:
            self.report({'ERROR'}, rpt_("Select a part of a character to key its pose"))
            return {'CANCELLED'}
        key_pose(context)
        names = [armature.name for armature in characters] or [obj.name for obj in context.selected_objects]
        self.report({'INFO'}, rpt_("Keyed the pose of %s") % ", ".join(names))
        return {'FINISHED'}


def draw_character_header(layout, _context):
    """DaskToon's part of the Dope Sheet header while Whole Character is on (spec 7: clips and timing come here)."""
    layout.operator(DASKTOON_OT_key_pose.bl_idname, icon='KEY_HLT')


def use_character_keying_set(scene):
    """A scene without an active keying set keys whole characters with I (spec 5). True when it was set."""
    from dasktoon_animation import KEYING_SET
    keying_sets = scene.keying_sets_all
    if keying_sets.active is not None:
        return False
    found = next((ks for ks in keying_sets if ks.bl_idname == KEYING_SET), None)
    if found is None:
        return False
    keying_sets.active = found
    return True


classes = (
    DASKTOON_KS_character,
    DASKTOON_OT_key_pose,
)
