# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    FloatVectorProperty,
    PointerProperty,
)


# =============================================================================
# DaskToon Engine Scene Properties Group
# =============================================================================

class DaskToonEngineSettings(PropertyGroup):
    # Shading Mode
    shading_style: EnumProperty(
        name="Shading Style",
        description="Anime Cel-Shading Style",
        items=[
            ('TWO_TONE', "2-Tone Cel", "Classic Anime 2-tone shading (Base + Shadow)"),
            ('THREE_TONE', "3-Tone Cel", "Modern Anime 3-tone shading (Base + Half-Tone + Deep Shadow)"),
            ('GRADIENT_CEL', "Soft Cel", "Soft-edged Japanese illustration look"),
            ('MANGA_INK', "Manga & Screentone", "Monochrome comic screentone and ink lines"),
        ],
        default='TWO_TONE',
    )
    cel_steps: IntProperty(
        name="Cel Steps",
        description="Number of lighting quantization steps",
        default=2,
        min=1,
        max=8,
    )
    shadow_threshold: FloatProperty(
        name="Shadow Threshold",
        description="Global shadow boundary threshold",
        default=0.48,
        min=0.0,
        max=1.0,
    )
    shadow_softness: FloatProperty(
        name="Shadow Softness",
        description="Feathering / smoothness at the shadow boundary",
        default=0.02,
        min=0.001,
        max=0.5,
    )
    penumbra_sat_boost: FloatProperty(
        name="Penumbra Saturation Boost",
        description="Increases color vibrancy at the light-to-shadow terminator (characteristic of Japanese anime)",
        default=1.35,
        min=1.0,
        max=3.0,
    )

    # Outline & Ink Line Art
    enable_outlines: BoolProperty(
        name="Enable Outlines",
        description="Render real-time anime ink outlines and silhouettes",
        default=True,
    )
    outline_thickness: FloatProperty(
        name="Outline Thickness",
        description="Thickness of anime ink line art in pixels",
        default=1.8,
        min=0.1,
        max=15.0,
    )
    outline_color: FloatVectorProperty(
        name="Outline Color",
        description="Ink outline color",
        subtype='COLOR',
        default=(0.04, 0.04, 0.06, 1.0),
        size=4,
    )
    outline_silhouette: BoolProperty(
        name="Silhouette Lines",
        description="Draw outer contour outline",
        default=True,
    )
    outline_crease: BoolProperty(
        name="Crease & Interior Lines",
        description="Draw interior surface crease lines",
        default=True,
    )
    crease_angle: FloatProperty(
        name="Crease Angle",
        description="Angle threshold for interior creases",
        default=140.0,
        min=0.0,
        max=180.0,
    )

    # Lighting & Shadows
    hard_shadows: BoolProperty(
        name="Crisp Anime Shadows",
        description="Enforce sharp, non-blurred shadow map boundaries",
        default=True,
    )
    face_shadow_smoothing: BoolProperty(
        name="Face Shadow Fix",
        description="Smooth out faceted mesh normal artifacts on anime character faces",
        default=True,
    )
    ambient_sky_tint: FloatVectorProperty(
        name="Ambient Sky Tint",
        description="Color tint added into shadowed areas from the sky/environment",
        subtype='COLOR',
        default=(0.60, 0.65, 0.85, 1.0),
        size=4,
    )

    # Manga Screentone
    screentone_density: FloatProperty(
        name="Screen Dot Density",
        description="Frequency of manga halftone screen dots",
        default=45.0,
        min=5.0,
        max=200.0,
    )
    screentone_angle: FloatProperty(
        name="Screen Angle",
        description="Rotation angle for the manga halftone screen matrix",
        default=45.0,
        min=0.0,
        max=90.0,
    )

    # Animation Stepping
    anim_stepping: EnumProperty(
        name="Anime Stepping",
        description="Limit animation playback rate for traditional hand-drawn anime timing",
        items=[
            ('ONES', "On 1s (Full Frame Rate)", "Standard 24 / 30 / 60 FPS smooth motion"),
            ('TWOS', "On 2s (12 FPS Anime Timing)", "Classic anime frame-holding every 2 frames"),
            ('THREES', "On 3s (8 FPS Anime Timing)", "High-impact stylized frame-holding every 3 frames"),
        ],
        default='ONES',
    )


# =============================================================================
# Render Properties Panels for DaskToon Anime Engine
# =============================================================================

class DaskToonRenderPanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    @classmethod
    def poll(cls, context):
        return context.engine == "DASKTOON_ANIME"


class DASKTOON_RENDER_PT_header(DaskToonRenderPanel):
    bl_label = "DaskToon Anime Engine"
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row(align=True)
        row.label(text="DaskToon Real-Time Anime Engine", icon='RESTRICT_RENDER_OFF')
        row.label(text="v5.2 Core", icon='FILE_SCRIPT')
        
        box.label(
            text="Specialized Japanese Cel-Shading & Non-Photorealistic Animation Pipeline",
            icon='INFO',
        )


class DASKTOON_RENDER_PT_cel_shading(DaskToonRenderPanel):
    bl_label = "Anime Cel-Shading & Quantization"
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dasktoon = getattr(scene, "dasktoon_engine", None)
        if not dasktoon:
            return

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(dasktoon, "shading_style")
        col.prop(dasktoon, "cel_steps")

        layout.separator()

        col = layout.column(align=True)
        col.prop(dasktoon, "shadow_threshold")
        col.prop(dasktoon, "shadow_softness")
        col.prop(dasktoon, "penumbra_sat_boost")


class DASKTOON_RENDER_PT_lineart(DaskToonRenderPanel):
    bl_label = "Ink & Outline Line Art"
    bl_order = 20

    def draw_header(self, context):
        dasktoon = getattr(context.scene, "dasktoon_engine", None)
        if dasktoon:
            self.layout.prop(dasktoon, "enable_outlines", text="")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dasktoon = getattr(scene, "dasktoon_engine", None)
        if not dasktoon:
            return

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = dasktoon.enable_outlines

        col = layout.column(align=True)
        col.prop(dasktoon, "outline_thickness")
        col.prop(dasktoon, "outline_color")

        layout.separator()

        col = layout.column(align=True)
        col.prop(dasktoon, "outline_silhouette")
        col.prop(dasktoon, "outline_crease")
        if dasktoon.outline_crease:
            col.prop(dasktoon, "crease_angle")

        layout.separator()
        row = layout.row(align=True)
        row.operator("dasktoon.setup_lineart", text="Generate Grease Pencil LineArt Layer", icon='OUTLINER_OB_GREASEPENCIL')


class DASKTOON_RENDER_PT_shadows(DaskToonRenderPanel):
    bl_label = "Anime Lighting & Hard Shadows"
    bl_order = 30
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dasktoon = getattr(scene, "dasktoon_engine", None)
        if not dasktoon:
            return

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(dasktoon, "hard_shadows")
        col.prop(dasktoon, "face_shadow_smoothing")
        col.prop(dasktoon, "ambient_sky_tint")
        col.separator()
        row = col.row(align=True)
        row.operator("dasktoon.setup_lighting", text="Add Anime Sun Light", icon='LIGHT_SUN')
        row.operator("dasktoon.link_sun_direction", text="Sync Sun to Materials", icon='ORIENTATION_GIMBAL')


class DASKTOON_RENDER_PT_manga(DaskToonRenderPanel):
    bl_label = "Manga Screen-tones & Halftones"
    bl_order = 40
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dasktoon = getattr(scene, "dasktoon_engine", None)
        if not dasktoon:
            return

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(dasktoon, "screentone_density")
        col.prop(dasktoon, "screentone_angle")


class DASKTOON_RENDER_PT_animation(DaskToonRenderPanel):
    bl_label = "Anime Timing & Animation Stepping"
    bl_order = 50
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dasktoon = getattr(scene, "dasktoon_engine", None)
        if not dasktoon:
            return

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(dasktoon, "anim_stepping")
        col.prop(scene.render, "use_motion_blur", text="Anime Motion Blur")


class DASKTOON_RENDER_PT_presets(DaskToonRenderPanel):
    bl_label = "1-Click Anime Material Presets"
    bl_order = 60

    def draw(self, context):
        layout = self.layout

        grid = layout.grid_flow(columns=2, align=True)
        
        p1 = grid.operator("dasktoon.setup_anime_preset", text="Anime Character", icon='ARMATURE_DATA')
        p1.preset_type = 'CHARACTER'
        
        p2 = grid.operator("dasktoon.setup_anime_preset", text="Anime Hair Ring", icon='STRANDS')
        p2.preset_type = 'HAIR'
        
        p3 = grid.operator("dasktoon.setup_anime_preset", text="Anime Eyes", icon='HIDE_OFF')
        p3.preset_type = 'EYES'
        
        p4 = grid.operator("dasktoon.setup_anime_preset", text="Manga Tone", icon='TEXTURE')
        p4.preset_type = 'MANGA'


# =============================================================================
# Operators
# =============================================================================

class DASKTOON_OT_setup_anime_lighting(Operator):
    """Add an Anime Sun Light and configure Viewport for Realtime Cel-Shading"""
    bl_idname = "dasktoon.setup_lighting"
    bl_label = "Setup Anime Sun Light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sun_ob = None
        for ob in context.scene.objects:
            if ob.type == 'LIGHT' and ob.data.type == 'SUN':
                sun_ob = ob
                break

        if not sun_ob:
            light_data = bpy.data.lights.new(name="Anime_Sun_Light", type='SUN')
            light_data.energy = 2.5
            light_data.color = (1.0, 0.98, 0.95)
            sun_ob = bpy.data.objects.new(name="Anime_Sun_Light", object_data=light_data)
            context.collection.objects.link(sun_ob)
            sun_ob.location = (4.0, -4.0, 6.0)
            sun_ob.rotation_euler = (0.785, 0.523, -0.610)

        # Set viewport to Rendered if available
        if hasattr(context, "area") and context.area:
            for space in context.area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'

        self.report({'INFO'}, "Configured Anime Sun Light and Realtime Viewport!")
        return {'FINISHED'}


class DASKTOON_OT_setup_lineart(Operator):
    """Add a real-time Line Art outline layer to the active scene"""
    bl_idname = "dasktoon.setup_lineart"
    bl_label = "Add Anime Line Art"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            bpy.ops.object.gpencil_add(type='LINEART_SCENE')
            self.report({'INFO'}, "Created Anime Line Art Outline layer!")
        except Exception as e:
            self.report({'WARNING'}, f"LineArt operation: {e}")
        return {'FINISHED'}


# =============================================================================
# Registration
# =============================================================================

classes = (
    DaskToonEngineSettings,
    DASKTOON_RENDER_PT_header,
    DASKTOON_RENDER_PT_cel_shading,
    DASKTOON_RENDER_PT_lineart,
    DASKTOON_RENDER_PT_shadows,
    DASKTOON_RENDER_PT_manga,
    DASKTOON_RENDER_PT_animation,
    DASKTOON_RENDER_PT_presets,
    DASKTOON_OT_setup_anime_lighting,
    DASKTOON_OT_setup_lineart,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dasktoon_engine = PointerProperty(type=DaskToonEngineSettings)


def unregister():
    if hasattr(bpy.types.Scene, "dasktoon_engine"):
        del bpy.types.Scene.dasktoon_engine
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
