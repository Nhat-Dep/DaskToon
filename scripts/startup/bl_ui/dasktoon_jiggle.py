# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Jiggle buttons (docs/superpowers/specs/2026-11-10-dasktoon-jiggle-design.md, section 1): Add Jiggle and Make
Colliders in the object and mesh context menus, and the presets of the Jiggle modifier's panel. The work is done by
dasktoon_rig.jiggle."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from dasktoon_rig.jiggle import PRESET_ITEMS


class OBJECT_OT_dasktoon_jiggle_add(Operator):
    """Make the selected part (Edit Mode) or the whole object jiggle and dent like a pudding"""
    bl_idname = "object.dasktoon_jiggle_add"
    bl_label = "Add Jiggle"
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(
        name="Preset",
        items=(('AUTO', "Automatic", "Soft Flesh on a rigged character, Pudding on anything else"),) + PRESET_ITEMS,
        default='AUTO',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        from dasktoon_rig import jiggle
        obj = context.active_object
        selected = None
        mode = obj.mode
        if mode == 'EDIT':
            obj.update_from_editmode()
            selected = [v.index for v in obj.data.vertices if v.select]
            if not selected:
                self.report({'ERROR'}, rpt_("Select the part that should jiggle"))
                return {'CANCELLED'}
            bpy.ops.object.mode_set(mode='OBJECT')
        elif jiggle.find_rig(obj) is not None:
            self.report({'ERROR'}, rpt_("Select the part that should jiggle in Edit Mode"))
            return {'CANCELLED'}
        try:
            md = jiggle.add(obj, selected, self.preset)
        finally:
            if mode == 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, rpt_("Added %s: it jiggles when played") % md.name)
        return {'FINISHED'}


class OBJECT_OT_dasktoon_jiggle_preset(Operator):
    """Set the Jiggle modifier's settings from a preset"""
    bl_idname = "object.dasktoon_jiggle_preset"
    bl_label = "Jiggle Preset"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    modifier: StringProperty(name="Modifier", options={'SKIP_SAVE'})
    preset: EnumProperty(name="Preset", items=PRESET_ITEMS)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        from dasktoon_rig import jiggle
        obj = context.active_object
        md = obj.modifiers.get(self.modifier) if self.modifier else None
        if md is None:
            md = next((m for m in obj.modifiers if m.type == 'JIGGLE'), None)
        if md is None or md.type != 'JIGGLE':
            self.report({'ERROR'}, rpt_("No Jiggle modifier"))
            return {'CANCELLED'}
        jiggle.apply_preset(md, self.preset)
        if md.vertex_group:
            md.use_pin_bottom = False
        return {'FINISHED'}


class OBJECT_OT_dasktoon_make_collider(Operator):
    """Let the selected objects push jiggles in (Physics › Collision)"""
    bl_idname = "object.dasktoon_make_collider"
    bl_label = "Make Colliders"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        from dasktoon_rig import jiggle
        made = [obj.name for obj in context.selected_objects if obj.type == 'MESH' and jiggle.make_collider(obj)]
        self.report({'INFO'}, rpt_("Colliders now: %s") % (", ".join(made) or rpt_("none new")))
        return {'FINISHED'}


def object_menu(self, _context):
    layout = self.layout
    layout.separator()
    layout.operator(OBJECT_OT_dasktoon_jiggle_add.bl_idname, icon='MOD_SOFT')
    layout.operator(OBJECT_OT_dasktoon_make_collider.bl_idname, icon='MOD_PHYSICS')


def edit_menu(self, _context):
    layout = self.layout
    layout.separator()
    layout.operator(OBJECT_OT_dasktoon_jiggle_add.bl_idname, icon='MOD_SOFT')


classes = (OBJECT_OT_dasktoon_jiggle_add, OBJECT_OT_dasktoon_jiggle_preset, OBJECT_OT_dasktoon_make_collider)


# bl_ui registers `classes`; register() only adds the menu entries (space_view3d registers after this module).
def register():
    from .space_view3d import VIEW3D_MT_object_context_menu, VIEW3D_MT_edit_mesh_context_menu
    VIEW3D_MT_object_context_menu.append(object_menu)
    VIEW3D_MT_edit_mesh_context_menu.append(edit_menu)


def unregister():
    from .space_view3d import VIEW3D_MT_object_context_menu, VIEW3D_MT_edit_mesh_context_menu
    VIEW3D_MT_object_context_menu.remove(object_menu)
    VIEW3D_MT_edit_mesh_context_menu.remove(edit_menu)
