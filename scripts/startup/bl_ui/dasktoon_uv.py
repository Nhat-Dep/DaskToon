# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime Unwrap (docs/superpowers/specs/2026-10-20-dasktoon-anime-unwrap-design.md): the operator, in Edit Mode's UV
menu and the material slots' menu."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.types import Operator


def unwrap_meshes(context, meshes):
    """The anime unwrap of `meshes`, their pictures carried over; the unwrap's result."""
    from dasktoon_guide import checks
    from dasktoon_uv import transfer, unwrap
    rig = checks.humanoid_rig(meshes)
    result = unwrap.unwrap(context, meshes, rig)
    transfer.transfer(meshes, result.old, result.mirrored)
    return result


class DASKTOON_OT_uv_unwrap_anime(Operator):
    """Unwrap the selected meshes for anime painting: each body part whole, seams on the hidden side, the face larger, """ \
        """the right limbs on the left ones, packed tight; painted pictures move to the new UV map"""
    bl_idname = "dasktoon.uv_unwrap_anime"
    bl_label = "Anime Unwrap"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if context.active_object not in meshes:
            meshes.insert(0, context.active_object)
        else:
            meshes.remove(context.active_object)
            meshes.insert(0, context.active_object)
        mode = context.active_object.mode
        result = unwrap_meshes(context, meshes)
        if mode == 'EDIT' and context.active_object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        kept = [name for name in result.old.values() if name]
        self.report({'INFO'}, rpt_("Anime Unwrap: %d meshes, %d mirrored faces%s")
                    % (len(meshes), len(result.mirrored), rpt_(", the old UV maps kept") if kept else ""))
        return {'FINISHED'}


def draw_uv_menu(self, _context):
    self.layout.separator()
    self.layout.operator("dasktoon.uv_unwrap_anime", text="Anime Unwrap", icon='UV')


classes = (DASKTOON_OT_uv_unwrap_anime,)


def register():  # bl_ui registers the classes first
    from .properties_material import MATERIAL_MT_context_menu
    from .space_view3d import VIEW3D_MT_uv_map
    VIEW3D_MT_uv_map.append(draw_uv_menu)
    MATERIAL_MT_context_menu.append(draw_uv_menu)


def unregister():
    from .properties_material import MATERIAL_MT_context_menu
    from .space_view3d import VIEW3D_MT_uv_map
    MATERIAL_MT_context_menu.remove(draw_uv_menu)
    VIEW3D_MT_uv_map.remove(draw_uv_menu)
