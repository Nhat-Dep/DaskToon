# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Animation tab (docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md, sections 5 to 7): the
"DaskToon Character" keying set, Key Pose, the part of the Dope Sheet header that shows when Whole Character is on, and
the file-load handler that puts DaskToon's tab in place of Blender's. The header also holds the character's clips
(docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md, section 4)."""

import types

import bpy
import _keyingsets_utils as keyingsets_utils
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import PointerProperty, StringProperty
from bpy.types import KeyingSetInfo, Menu, Operator
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


def header_armature(context):
    """The armature whose clips the header shows: the active object's character, else the first character with a
    selected part; None without one."""
    from dasktoon_animation import character
    obj = context.active_object
    found = character.armatures_of(obj) if obj is not None else []
    if not found:
        found = character.selected_characters(context)
    return found[0] if found else None


class DASKTOON_MT_character_clips(Menu):
    bl_label = "Clips"

    def draw(self, context):
        from dasktoon_animation import clips
        layout = self.layout
        armature = header_armature(context)
        if armature is None:
            layout.label(text="Select a part of a character")
            return
        for clip in clips.clips_of(armature):
            props = layout.operator(DASKTOON_OT_clip_use.bl_idname, text=clip.name, icon='ACTION', translate=False)
            props.clip = clip.name
        layout.separator()
        layout.operator(DASKTOON_OT_clip_new.bl_idname, icon='ADD')
        layout.operator(DASKTOON_OT_clip_delete.bl_idname, icon='X')


def _clip_context(op, context):
    """(armature, objects) of the header's character, or None after reporting why."""
    armature = header_armature(context)
    if armature is None:
        op.report({'ERROR'}, rpt_("Select a part of a character"))
        return None
    return armature, list(context.view_layer.objects)


class DASKTOON_OT_clip_new(Operator):
    """Make a new, empty clip of the character and play it; its animation so far becomes a clip first"""
    bl_idname = "dasktoon.clip_new"
    bl_label = "New Clip"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from dasktoon_animation import clips
        found = _clip_context(self, context)
        if found is None:
            return {'CANCELLED'}
        clip = clips.new(*found, scene=context.scene)
        self.report({'INFO'}, rpt_("New clip %s") % clip.name)
        return {'FINISHED'}


class DASKTOON_OT_clip_use(Operator):
    """Play this clip on the whole character: body and face"""
    bl_idname = "dasktoon.clip_use"
    bl_label = "Use Clip"
    bl_options = {'REGISTER', 'UNDO'}

    clip: StringProperty(name="Clip")

    def execute(self, context):
        from dasktoon_animation import clips
        found = _clip_context(self, context)
        if found is None:
            return {'CANCELLED'}
        clip = next((c for c in clips.clips_of(found[0]) if c.name == self.clip), None)
        if clip is None:
            self.report({'ERROR'}, rpt_("No clip %s") % self.clip)
            return {'CANCELLED'}
        clips.use(*found, clip, context.scene)
        return {'FINISHED'}


class DASKTOON_OT_clip_delete(Operator):
    """Delete the clip the character plays; it plays the first clip left"""
    bl_idname = "dasktoon.clip_delete"
    bl_label = "Delete Clip"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        from dasktoon_animation import clips
        armature = header_armature(context)
        return armature is not None and clips.current(armature) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        from dasktoon_animation import clips
        armature, objects = header_armature(context), list(context.view_layer.objects)
        clip = clips.current(armature)
        name = clip.name
        clips.delete(armature, objects, clip, context.scene)
        self.report({'INFO'}, rpt_("Deleted clip %s") % name)
        return {'FINISHED'}


def draw_character_header(layout, context):
    """DaskToon's part of the Dope Sheet header while Whole Character is on: Key Pose and the character's clips (clips
    spec 4); timing comes here too (spec 7)."""
    from dasktoon_animation import clips
    layout.operator(DASKTOON_OT_key_pose.bl_idname, icon='KEY_HLT')
    armature = header_armature(context)
    if armature is None:
        return
    clip = clips.current(armature)
    row = layout.row(align=True)
    label = clip.name if clip is not None else iface_("No Clip")
    row.menu(DASKTOON_MT_character_clips.__name__, text=label, icon='ACTION', translate=False)
    if clip is not None:
        row.prop(clip, "name", text="")
        row.prop(clip, "use_cyclic", text="Loop", toggle=True)
    row.operator(DASKTOON_OT_clip_new.bl_idname, text="", icon='ADD')


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


@persistent
def load_post(_filepath):
    """A file was opened (the startup file and New too): DaskToon's Animation tab, and the character keying set for I
    in scenes without one (spec 5, 6)."""
    from dasktoon_animation import tab
    tab.ensure_animation_tab()
    tab.show_render_in_camera_view()
    for scene in bpy.data.scenes:
        use_character_keying_set(scene)


classes = (
    DASKTOON_KS_character,
    DASKTOON_OT_key_pose,
    DASKTOON_MT_character_clips,
    DASKTOON_OT_clip_new,
    DASKTOON_OT_clip_use,
    DASKTOON_OT_clip_delete,
)


def _is_armature(_action, obj):
    return obj.type == 'ARMATURE'


# bl_ui registers `classes`; register() adds the file-load handler and the clip's character.
def register():
    bpy.types.Action.dasktoon_character = PointerProperty(
        name="Character", description="Armature of the character this action is a clip of (DaskToon)",
        type=bpy.types.Object, poll=_is_armature)
    if load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post)


def unregister():
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
    del bpy.types.Action.dasktoon_character
