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
        
        box.operator("dasktoon.setup_anime_material", text="Apply Basic Toon Material", icon='MATERIAL')
        box.operator("dasktoon.link_sun_direction", text="Sync Sun Light to Shaders", icon='ORIENTATION_GIMBAL')
        box.operator("dasktoon.setup_lineart", text="Add Ink Line Art", icon='GREASEPENCIL')


class VIEW3D_PT_dasktoon_shader_nodes(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_label = "Anime Shader Nodes"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # 1-Click Anime Material Presets
        box_presets = layout.box()
        box_presets.label(text="1-Click Anime Presets:", icon='NODE_MATERIAL')
        grid = box_presets.grid_flow(columns=2, align=True)
        
        p1 = grid.operator("dasktoon.setup_anime_preset", text="Anime Character", icon='ARMATURE_DATA')
        p1.preset_type = 'CHARACTER'
        
        p2 = grid.operator("dasktoon.setup_anime_preset", text="Anime Hair Ring", icon='STRANDS')
        p2.preset_type = 'HAIR'
        
        p3 = grid.operator("dasktoon.setup_anime_preset", text="Anime Eyes", icon='HIDE_OFF')
        p3.preset_type = 'EYES'
        
        p4 = grid.operator("dasktoon.setup_anime_preset", text="Manga Comic Tone", icon='TEXTURE')
        p4.preset_type = 'MANGA'
        
        p5 = grid.operator("dasktoon.setup_anime_preset", text="🎨 Artist Outline", icon='MOD_LINEART')
        p5.preset_type = 'OUTLINE'
        
        p6 = grid.operator("dasktoon.setup_anime_preset", text="Dask Cel Shader", icon='MATERIAL')
        p6.preset_type = 'CEL'

        box_presets.separator()
        box_presets.operator("dasktoon.link_sun_direction", text="☀️ Sync Sun Light to Shaders", icon='LIGHT_SUN')

        layout.separator()

        # Dedicated Native Anime Shader Nodes
        box_nodes = layout.box()
        box_nodes.label(text="Insert Native Anime Shader:", icon='NODETREE')

        try:
            from bl_ui.dasktoon_anime_nodes import ANIME_NATIVE_NODES
            col = box_nodes.column(align=True)
            for node_key, (name, _type, icon_name) in ANIME_NATIVE_NODES.items():
                op = col.operator("node.dasktoon_add_anime_node", text=name, icon=icon_name)
                op.node_type = node_key
        except ImportError:
            box_nodes.label(text="Anime nodes library loading...", icon='INFO')


classes = (
    DASKTOON_OT_activate_engine,
    VIEW3D_PT_dasktoon_main,
    VIEW3D_PT_dasktoon_shader_nodes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
