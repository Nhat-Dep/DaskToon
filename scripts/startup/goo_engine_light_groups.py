# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel, PropertyGroup, Operator
from bpy.props import IntProperty, StringProperty, CollectionProperty


class DASKTOON_LightGroupItem(PropertyGroup):
    name: StringProperty(name="Name", default="LightGroup")
    group_id: IntProperty(name="Group ID", default=1, min=0, max=128)


class DASKTOON_PT_light_groups(Panel):
    """Panel for managing NPR Light Groups in EEVEE-Next"""
    bl_label = "Goo NPR Light Groups"
    bl_idname = "DASKTOON_PT_light_groups"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.label(text="EEVEE-Next NPR Light Groups", icon='LIGHT_SUN')

        box = layout.box()
        box.label(text="Assign lights to Light Groups for Shader Info filtering:", icon='INFO')
        
        # Display lights in the scene with their group ID
        lights = [ob for ob in scene.objects if ob.type == 'LIGHT']
        if not lights:
            box.label(text="No lights in scene", icon='DOT')
        else:
            for ob in lights:
                r = box.row(align=True)
                r.label(text=ob.name, icon='LIGHT_' + ob.data.type)
                r.prop(ob.data, "color", text="")


classes = (
    DASKTOON_LightGroupItem,
    DASKTOON_PT_light_groups,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
