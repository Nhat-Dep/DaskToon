# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel, Operator


class DASKTOON_RENDER_PT_anime_settings(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_label = "DaskToon Anime & Cel-Shading"

    @classmethod
    def poll(cls, context):
        return context.engine == "DASKTOON_ANIME"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Header info
        box = layout.box()
        box.label(text="Native C++ Anime & Toon Suite", icon='RESTRICT_RENDER_OFF')
        box.label(text="Realtime Cel-Shading Engine", icon='CHECKMARK')

        # Cel Shading Settings
        col = layout.column(align=True)
        col.label(text="Cel-Shading Controls:", icon='MATERIAL')
        
        box_cel = layout.box()
        box_cel.prop(scene.render, "use_motion_blur", text="Anime Motion Blur")
        box_cel.operator("dasktoon.setup_anime_material", text="Create Anime Toon Material", icon='ADD')

        layout.separator()

        # Ink & Outline Section
        col_line = layout.column(align=True)
        col_line.label(text="Ink & Line Art Outlines:", icon='GREASEPENCIL')
        
        box_line = layout.box()
        box_line.operator("dasktoon.setup_lineart", text="Add Anime Line Art Outline", icon='OUTLINER_OB_GREASEPENCIL')


class DASKTOON_OT_setup_anime_material(Operator):
    """Create a 2D/3D Anime Cel-Shading Material for the active object"""
    bl_idname = "dasktoon.setup_anime_material"
    bl_label = "Setup Anime Toon Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        # Create new toon material
        mat_name = "DaskToon_Anime_Shader"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            # Add nodes for Toon Shader
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (400, 0)

            diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')
            diffuse_node.location = (-400, 0)

            shader_to_rgb = nodes.new(type='ShaderNodeShaderToRgb')
            shader_to_rgb.location = (-200, 0)

            color_ramp = nodes.new(type='ShaderNodeValToRGB')
            color_ramp.location = (0, 0)
            color_ramp.color_ramp.interpolation = 'CONSTANT'
            color_ramp.color_ramp.elements[0].position = 0.5
            color_ramp.color_ramp.elements[0].color = (0.1, 0.1, 0.15, 1.0)
            color_ramp.color_ramp.elements[1].position = 0.51
            color_ramp.color_ramp.elements[1].color = (0.9, 0.85, 0.8, 1.0)

            emission_node = nodes.new(type='ShaderNodeEmission')
            emission_node.location = (200, 0)

            links.new(diffuse_node.outputs['BSDF'], shader_to_rgb.inputs['Shader'])
            links.new(shader_to_rgb.outputs['Color'], color_ramp.inputs['Facet'])
            links.new(color_ramp.outputs['Color'], emission_node.inputs['Color'])
            links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        self.report({'INFO'}, f"Applied Anime Toon Material to {obj.name}")
        return {'FINISHED'}


class DASKTOON_OT_setup_lineart(Operator):
    """Add Line Art Outline to the active object or scene"""
    bl_idname = "dasktoon.setup_lineart"
    bl_label = "Add Anime Line Art"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Add Grease Pencil Line Art object
        bpy.ops.object.gpencil_add(type='LINEART_SCENE')
        self.report({'INFO'}, "Created Anime Line Art Outline layer!")
        return {'FINISHED'}


classes = (
    DASKTOON_RENDER_PT_anime_settings,
    DASKTOON_OT_setup_anime_material,
    DASKTOON_OT_setup_lineart,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
