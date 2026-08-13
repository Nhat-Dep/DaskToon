# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel


class VIEW3D_PT_dasktoon_main(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_label = "DaskToon Suite"

    def draw(self, context):
        layout = self.layout
        
        # Header Box
        header_box = layout.box()
        header_box.label(text="DaskToon Animation Tools", icon='RESTRICT_RENDER_OFF')
        header_box.label(text="Version: 5.2 Modded", icon='CHECKMARK')

        # Quick Actions
        col = layout.column(align=True)
        col.label(text="Quick Controls:")
        col.operator("wm.splash", text="DaskToon Info", icon='INFO')
        
        layout.separator()

        # Shading & Line Art Box
        box = layout.box()
        box.label(text="Toon Shading & Line Art", icon='MATERIAL')
        scene = context.scene
        box.prop(scene.render, "engine", text="Render Engine")
        
        if scene.render.engine == 'BLENDER_EEVEE_NEXT' or scene.render.engine == 'BLENDER_EEVEE':
            box.label(text="EEVEE Toon Mode Active", icon='LIGHT')


classes = (
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
