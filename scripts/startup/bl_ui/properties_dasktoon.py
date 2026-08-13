# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel, Operator


class DASKTOON_OT_activate_engine(Operator):
    """Switch active Render Engine to DaskToon Anime & Toon Engine"""
    bl_idname = "dasktoon.activate_engine"
    bl_label = "Activate DaskToon Anime Engine"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.render.engine = "DASKTOON_ANIME"
        self.report({'INFO'}, "Activated DaskToon Anime & Toon Engine!")
        return {'FINISHED'}


class VIEW3D_PT_dasktoon_main(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_label = "DaskToon Suite"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Header Box
        header_box = layout.box()
        header_box.label(text="DaskToon Animation Suite", icon='RESTRICT_RENDER_OFF')
        header_box.label(text="Engine: " + scene.render.engine, icon='RENDER_STILL')

        # Quick Actions
        col = layout.column(align=True)
        col.operator("dasktoon.activate_engine", text="Switch to Anime Engine", icon='NODE_COMPOSITING')
        col.operator("wm.splash", text="DaskToon Info", icon='INFO')

        layout.separator()

        # Shading & Line Art Box
        box = layout.box()
        box.label(text="Toon Shading & Line Art", icon='MATERIAL')
        
        box.operator("dasktoon.setup_anime_material", text="Apply Toon Material", icon='MATERIAL')
        box.operator("dasktoon.setup_lineart", text="Add Ink Line Art", icon='GREASEPENCIL')


classes = (
    DASKTOON_OT_activate_engine,
    VIEW3D_PT_dasktoon_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
