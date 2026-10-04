# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Expression tools under Properties › Object Data › Shape Keys (UI spec 3.2): VRM and ARKit expression sets, split and
bake tools, reference cards with a test on the model, and controllers that drive shape keys from a 2D joystick, an
AIUEO star, an emotion wheel or a slider bank, with an interactive HUD in the 3D Viewport."""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import blf
import math
import re
import textwrap
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList,
)
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
)


# =============================================================================
# Global HUD State
# =============================================================================

class DaskHUDState:
    draw_handler = None
    is_active = False
    is_dragging = False
    active_slider_index = -1
    drag_start_x = 0
    drag_start_y = 0
    session = 0  # bumped by every HUD start; an older HUD operator still running ends itself


# =============================================================================
# Data Models: Mappings & Groups
# =============================================================================

def _update_slider_value(self, context):
    """Callback when a 1D mapping slider value changes."""
    obj = context.object
    if not obj or not obj.data or not obj.data.shape_keys:
        return
    kb = obj.data.shape_keys.key_blocks.get(self.shape_key_name)
    if kb and self.enabled:
        kb.value = max(self.min_value, min(self.slider_value, self.max_value))


class DaskShapeMappingItem(PropertyGroup):
    """A shape key placed on a controller: a point on the pad, or a slider of a slider bank"""
    shape_key_name: StringProperty(
        name="Shape Key",
        description="Shape key this mapping drives",
        default="",
    )
    # 2D Coordinates
    target_x: FloatProperty(
        name="Target X",
        description="Position of the shape key on the pad, from left (-1) to right (1)",
        default=0.0,
        min=-1.0,
        max=1.0,
    )
    target_y: FloatProperty(
        name="Target Y",
        description="Position of the shape key on the pad, from bottom (-1) to top (1)",
        default=0.0,
        min=-1.0,
        max=1.0,
    )
    # 1D Multi-Slider Channel Value
    slider_value: FloatProperty(
        name="Value",
        description="Value of this slider",
        default=0.0,
        min=0.0,
        max=1.0,
        update=_update_slider_value,
    )
    radius: FloatProperty(
        name="Influence Radius",
        description="Distance from the point at which the shape key fades out",
        default=0.90,
        min=0.01,
        max=3.0,
    )
    min_value: FloatProperty(
        name="Minimum",
        description="Lowest value given to the shape key",
        default=0.0,
    )
    max_value: FloatProperty(
        name="Maximum",
        description="Highest value given to the shape key",
        default=1.0,
    )
    exponent: FloatProperty(
        name="Falloff",
        description="Exponent of the falloff curve: 1 is linear, 2 smooth, 0.5 sharp",
        default=1.0,
        min=0.1,
        max=5.0,
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Use this mapping",
        default=True,
    )


def _update_handle_position(self, context):
    """Callback when Handle X or Y changes to drive shape keys in real-time."""
    self.evaluate_mappings(context)


class DaskShapeGroupItem(PropertyGroup):
    """A controller: a pad or a slider bank that drives a set of shape keys"""
    name: StringProperty(
        name="Name",
        description="Name of the controller",
        default="New Controller",
    )
    controller_category: EnumProperty(
        name="Category",
        description="What the controller animates",
        items=[
            ('FACE', "Face", "Expressions, eyes and brows"),
            ('LIP_SYNC', "Lip Sync", "Visemes and speech shapes"),
            ('BODY', "Body", "Breathing, muscles and proportions"),
            ('HAIR_EARS', "Hair & Ears", "Animal ears, tails and hair"),
            ('CLOTH', "Cloth", "Skirt and cape sway, wrinkles"),
            ('PROPS', "Props", "Weapons, mechanical parts and customizer shapes"),
            ('CUSTOM', "Custom", "Anything else"),
        ],
        default='FACE',
    )
    controller_type: EnumProperty(
        name="Type",
        description="Shape of the controller",
        items=[
            ('JOYSTICK_2D', "2D Joystick", "A pad with each shape key at a point"),
            ('VISEME_STAR', "AIUEO Star", "A five-point star for the vowels A, I, U, E, O"),
            ('COMPASS_WHEEL', "Emotion Wheel", "A wheel with an emotion in each direction"),
            ('SLIDER_1D', "Slider Bank", "One slider per shape key"),
        ],
        default='JOYSTICK_2D',
    )

    # Current Handle (Drivable Coordinates for 2D Types)
    handle_x: FloatProperty(
        name="Handle X",
        description="Horizontal position of the handle",
        default=0.0,
        min=-1.0,
        max=1.0,
        update=_update_handle_position,
    )
    handle_y: FloatProperty(
        name="Handle Y",
        description="Vertical position of the handle",
        default=0.0,
        min=-1.0,
        max=1.0,
        update=_update_handle_position,
    )

    # Multi-Point Shape Key Mappings Collection
    mappings: CollectionProperty(type=DaskShapeMappingItem)
    active_mapping_index: IntProperty(name="Active Mapping Index", default=0)

    # Group Settings
    use_rbf_blend: BoolProperty(
        name="Smooth Blending",
        description="Blend smoothly where the influence of two points overlaps",
        default=True,
    )
    lock_x: BoolProperty(name="Lock X", default=False)
    lock_y: BoolProperty(name="Lock Y", default=False)

    def evaluate_mappings(self, context):
        """Calculates and updates all Shape Key values on the active mesh."""
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
            return

        key_blocks = obj.data.shape_keys.key_blocks

        if self.controller_type == 'SLIDER_1D':
            # Multi-Slider Mode: Each mapping drives its own shape key directly by slider_value
            for mapping in self.mappings:
                if not mapping.enabled or not mapping.shape_key_name:
                    continue
                kb = key_blocks.get(mapping.shape_key_name)
                if kb:
                    kb.value = max(mapping.min_value, min(mapping.slider_value, mapping.max_value))
            return

        # 2D Planar / Star / Compass RBF Evaluation
        hx, hy = self.handle_x, self.handle_y

        for mapping in self.mappings:
            if not mapping.enabled or not mapping.shape_key_name:
                continue
            kb = key_blocks.get(mapping.shape_key_name)
            if not kb:
                continue

            dx = hx - mapping.target_x
            dy = hy - mapping.target_y
            dist = math.sqrt(dx * dx + dy * dy)
            rad = max(mapping.radius, 0.001)

            if dist < rad:
                norm = 1.0 - (dist / rad)
                weight = math.pow(norm, max(mapping.exponent, 0.01))
                val = mapping.min_value + weight * (mapping.max_value - mapping.min_value)
            else:
                val = mapping.min_value

            kb.value = max(0.0, min(val, 1.0))


class DaskShapeControllerRoot(PropertyGroup):
    """The controllers of a mesh object"""
    groups: CollectionProperty(type=DaskShapeGroupItem)
    active_group_index: IntProperty(name="Active Controller Index", default=0)

    # HUD Viewport Settings
    hud_enabled: BoolProperty(
        name="Show HUD",
        description="Show the controller HUD in the 3D Viewport",
        default=False,
    )
    hud_pos_x: IntProperty(name="HUD X", default=80, min=10, max=4000)
    hud_pos_y: IntProperty(name="HUD Y", default=80, min=10, max=4000)
    hud_size: IntProperty(name="HUD Size", default=240, min=150, max=600)


# =============================================================================
# GPU 2D Viewport HUD Drawing Engine (Supports Multi-Slider 1D Bank!)
# =============================================================================

def draw_shape_axis_hud_2d(self, context):
    """Draws the on-screen 2D Joystick HUD in 3D Viewport with dedicated visuals per Type."""
    obj = context.object
    if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
        return
    root = getattr(obj, "dask_shape_controllers", None)
    if not root or not root.groups:
        return
    if not root.hud_enabled and not DaskHUDState.is_active:
        return

    if root.active_group_index >= len(root.groups):
        return
    grp = root.groups[root.active_group_index]

    # Layout geometry
    hud_x = root.hud_pos_x
    hud_y = root.hud_pos_y
    hud_w = root.hud_size

    # Expand width slightly for multi-slider banks with 3+ sliders
    if grp.controller_type == 'SLIDER_1D' and len(grp.mappings) > 2:
        hud_w = max(hud_w, len(grp.mappings) * 80 + 40)

    pad_h = root.hud_size
    hud_h = pad_h + 85

    pad_cx = hud_x + hud_w / 2
    pad_cy = hud_y + 60 + pad_h / 2
    pad_half = (pad_h - 40) / 2

    # Enable Alpha Blending
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    def fill_rect(x1, y1, x2, y2, color):
        vertices = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        indices = [(0, 1, 2), (0, 2, 3)]
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def wire_rect(x1, y1, x2, y2, color):
        vertices = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def wire_line(x1, y1, x2, y2, color):
        vertices = [(x1, y1), (x2, y2)]
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def wire_circle(cx, cy, r, color, segments=36):
        vertices = []
        for i in range(segments + 1):
            theta = 2.0 * math.pi * i / segments
            vertices.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    def draw_str(text, x, y, size=11, color=(1, 1, 1, 1)):
        font_id = 0
        blf.size(font_id, size)
        blf.position(font_id, x, y, 0)
        blf.color(font_id, color[0], color[1], color[2], color[3])
        blf.draw(font_id, text)

    # 1. Main Background Box (Dark Sleek Glassmorphism)
    fill_rect(hud_x, hud_y, hud_x + hud_w, hud_y + hud_h, (0.08, 0.09, 0.12, 0.90))
    wire_rect(hud_x, hud_y, hud_x + hud_w, hud_y + hud_h, (0.28, 0.32, 0.40, 0.90))

    # 2. Header Bar with Type Badge
    fill_rect(hud_x, hud_y + hud_h - 26, hud_x + hud_w, hud_y + hud_h, (0.12, 0.15, 0.24, 0.95))
    wire_line(hud_x, hud_y + hud_h - 26, hud_x + hud_w, hud_y + hud_h - 26, (0.35, 0.42, 0.55, 0.80))

    type_names = {
        'JOYSTICK_2D': n_("2D Joystick"),
        'VISEME_STAR': n_("AIUEO Star"),
        'COMPASS_WHEEL': n_("Emotion Wheel"),
        'SLIDER_1D': n_("Slider Bank"),
    }
    badge = iface_(type_names.get(grp.controller_type, type_names['JOYSTICK_2D']))
    draw_str("%s: %s" % (badge, grp.name), hud_x + 8, hud_y + hud_h - 18, size=11, color=(0.95, 0.96, 1.0, 1.0))
    draw_str("×", hud_x + hud_w - 18, hud_y + hud_h - 18, size=12, color=(0.7, 0.7, 0.8, 1.0))

    # 3. Inner Pad Area Background
    pad_left = hud_x + 15
    pad_right = hud_x + hud_w - 15
    pad_top = pad_cy + pad_half
    pad_bottom = pad_cy - pad_half

    fill_rect(pad_left, pad_bottom, pad_right, pad_top, (0.04, 0.05, 0.07, 0.92))
    wire_rect(pad_left, pad_bottom, pad_right, pad_top, (0.22, 0.26, 0.35, 0.80))

    # =========================================================================
    # DEDICATED VISUALS PER CONTROLLER TYPE
    # =========================================================================

    if grp.controller_type == 'SLIDER_1D':
        # ── TYPE 4: MULTI-SLIDER 1D FADER BANK (e.g. 3 Sliders: Blink Both / Left / Right) ──
        num_sliders = max(1, len(grp.mappings))
        col_width = (pad_right - pad_left) / num_sliders
        track_w = 8

        for i, mp in enumerate(grp.mappings):
            cx = pad_left + (i + 0.5) * col_width

            # Draw channel track groove
            fill_rect(cx - track_w / 2, pad_bottom + 25, cx + track_w / 2, pad_top - 20, (0.02, 0.03, 0.04, 0.95))
            wire_rect(cx - track_w / 2, pad_bottom + 25, cx + track_w / 2, pad_top - 20, (0.35, 0.42, 0.55, 0.85))

            # Tick marks
            for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
                ty = (pad_bottom + 25) + t * (pad_top - pad_bottom - 45)
                tw = 6 if t in {0.0, 1.0} else 4
                wire_line(cx - track_w / 2 - tw, ty, cx - track_w / 2, ty, (0.35, 0.45, 0.60, 0.60))
                wire_line(cx + track_w / 2, ty, cx + track_w / 2 + tw, ty, (0.35, 0.45, 0.60, 0.60))

            # Channel Label at top
            label_text = mp.shape_key_name
            # Shorten label if long (e.g. Fcl_EYE_Close_L -> Close_L)
            if "_" in label_text:
                label_text = label_text.split("_")[-1]
            draw_str(label_text[:8], cx - 18, pad_top - 14, size=10, color=(0.90, 0.92, 1.0, 0.95))

            # Fader Knob Handle
            val = mp.slider_value
            knob_y = (pad_bottom + 25) + val * (pad_top - pad_bottom - 45)
            kw, kh = 20, 9
            fill_rect(cx - kw, knob_y - kh, cx + kw, knob_y + kh, (0.20, 0.55, 0.95, 0.95))
            wire_rect(cx - kw, knob_y - kh, cx + kw, knob_y + kh, (1.0, 1.0, 1.0, 1.0))
            wire_line(cx - kw + 3, knob_y, cx + kw - 3, knob_y, (1.0, 1.0, 1.0, 1.0))

            # Readout value at bottom
            draw_str(f"{val:.2f}", cx - 10, pad_bottom + 8, size=9, color=(0.75, 0.85, 1.0, 0.85))

    elif grp.controller_type == 'VISEME_STAR':
        # ── TYPE 2: 5-POINT AIUEO STAR / PENTAGON ──
        star_angles = [
            math.pi / 2,                    # Top (A)
            math.pi / 2 + 2 * math.pi / 5,  # Top-Left (I)
            math.pi / 2 + 4 * math.pi / 5,  # Bottom-Left (U)
            math.pi / 2 + 6 * math.pi / 5,  # Bottom-Right (E)
            math.pi / 2 + 8 * math.pi / 5,  # Top-Right (O)
        ]
        star_pts = [(pad_cx + pad_half * math.cos(a), pad_cy + pad_half * math.sin(a)) for a in star_angles]

        for i in range(5):
            p1, p2 = star_pts[i], star_pts[(i + 1) % 5]
            wire_line(p1[0], p1[1], p2[0], p2[1], (0.35, 0.55, 0.85, 0.70))
            wire_line(pad_cx, pad_cy, p1[0], p1[1], (0.20, 0.30, 0.45, 0.50))
            p_star = star_pts[(i + 2) % 5]
            wire_line(p1[0], p1[1], p_star[0], p_star[1], (0.25, 0.40, 0.65, 0.35))

        wire_circle(pad_cx, pad_cy, pad_half * 0.4, (0.20, 0.35, 0.55, 0.40))

    elif grp.controller_type == 'COMPASS_WHEEL':
        # ── TYPE 3: EMOTION 360° COMPASS WHEEL ──
        wire_circle(pad_cx, pad_cy, pad_half * 0.25, (0.18, 0.24, 0.35, 0.40))
        wire_circle(pad_cx, pad_cy, pad_half * 0.50, (0.22, 0.30, 0.45, 0.50))
        wire_circle(pad_cx, pad_cy, pad_half * 0.75, (0.25, 0.35, 0.52, 0.60))
        wire_circle(pad_cx, pad_cy, pad_half * 1.00, (0.35, 0.50, 0.75, 0.80))

        for d in range(8):
            ang = d * math.pi / 4
            x2 = pad_cx + pad_half * math.cos(ang)
            y2 = pad_cy + pad_half * math.sin(ang)
            wire_line(pad_cx, pad_cy, x2, y2, (0.22, 0.30, 0.42, 0.60))

        draw_str(iface_("Joy"), pad_cx - 20, pad_cy + pad_half - 12, size=9, color=(1.0, 0.85, 0.30, 0.90))
        draw_str(iface_("Sorrow"), pad_cx - 28, pad_cy - pad_half + 4, size=9, color=(0.40, 0.70, 1.0, 0.90))
        draw_str(iface_("Angry"), pad_cx - pad_half + 2, pad_cy + 2, size=9, color=(1.0, 0.35, 0.35, 0.90))
        draw_str(iface_("Surprised"), pad_cx + pad_half - 52, pad_cy + 2, size=9, color=(0.50, 0.95, 0.60, 0.90))

    else:
        # ── TYPE 1: 2D PLANAR XY JOYSTICK ──
        wire_line(pad_cx - pad_half, pad_cy, pad_cx + pad_half, pad_cy, (0.22, 0.28, 0.38, 0.70))
        wire_line(pad_cx, pad_cy - pad_half, pad_cx, pad_cy + pad_half, (0.22, 0.28, 0.38, 0.70))
        wire_circle(pad_cx, pad_cy, pad_half, (0.22, 0.28, 0.38, 0.50))

    # 4. Target Points & Influence Circles (For 2D types)
    if grp.controller_type != 'SLIDER_1D':
        for mp in grp.mappings:
            if not mp.enabled or not mp.shape_key_name:
                continue
            tx = pad_cx + mp.target_x * pad_half
            ty = pad_cy + mp.target_y * pad_half
            rad_px = mp.radius * pad_half

            circle_col = (0.95, 0.30, 0.30, 0.45) if grp.controller_type != 'VISEME_STAR' else (0.30, 0.75, 1.0, 0.40)
            wire_circle(tx, ty, rad_px, circle_col)
            fill_rect(tx - 3, ty - 3, tx + 3, ty + 3, (0.95, 0.95, 0.95, 0.90))
            lbl = mp.shape_key_name
            draw_str(lbl, tx - len(lbl) * 3, ty + 5, size=10, color=(0.92, 0.94, 1.0, 0.92))

        # Interactive 2D Handle Puck
        hx_scr = pad_cx + grp.handle_x * pad_half
        hy_scr = pad_cy + grp.handle_y * pad_half

        fill_rect(hx_scr - 8, hy_scr - 8, hx_scr + 8, hy_scr + 8, (0.20, 0.60, 1.0, 0.95))
        wire_rect(hx_scr - 8, hy_scr - 8, hx_scr + 8, hy_scr + 8, (1.0, 1.0, 1.0, 1.0))
        fill_rect(hx_scr - 2, hy_scr - 2, hx_scr + 2, hy_scr + 2, (1.0, 1.0, 1.0, 1.0))

    # 5. Bottom Bar: Reset Button, Readout & Group Switcher
    btn_y = hud_y + 32
    fill_rect(hud_x + 10, btn_y, hud_x + hud_w - 10, btn_y + 20, (0.16, 0.20, 0.28, 0.90))
    wire_rect(hud_x + 10, btn_y, hud_x + hud_w - 10, btn_y + 20, (0.30, 0.36, 0.48, 0.80))
    draw_str(iface_("Reset Group"), hud_x + hud_w / 2 - 44, btn_y + 5, size=11, color=(0.90, 0.92, 1.0, 1.0))

    bar_y = hud_y + 8
    if grp.controller_type != 'SLIDER_1D':
        draw_str("X: %+.3f  Y: %+.3f" % (grp.handle_x, grp.handle_y), hud_x + 12, bar_y + 16, size=10, color=(0.75, 0.80, 0.90, 0.90))
    else:
        draw_str(iface_("%d sliders") % len(grp.mappings), hud_x + 12, bar_y + 16, size=10, color=(0.75, 0.80, 0.90, 0.90))

    fill_rect(hud_x + 10, bar_y, hud_x + 30, bar_y + 14, (0.14, 0.17, 0.24, 0.90))
    wire_rect(hud_x + 10, bar_y, hud_x + 30, bar_y + 14, (0.28, 0.34, 0.44, 0.80))
    draw_str("<", hud_x + 18, bar_y + 2, size=11, color=(1, 1, 1, 1))

    fill_rect(hud_x + 34, bar_y, hud_x + hud_w - 34, bar_y + 14, (0.12, 0.14, 0.20, 0.90))
    draw_str(grp.name[:22], hud_x + 40, bar_y + 2, size=10, color=(0.85, 0.90, 1.0, 1.0))

    fill_rect(hud_x + hud_w - 30, bar_y, hud_x + hud_w - 10, bar_y + 14, (0.14, 0.17, 0.24, 0.90))
    wire_rect(hud_x + hud_w - 30, bar_y, hud_x + hud_w - 10, bar_y + 14, (0.28, 0.34, 0.44, 0.80))
    draw_str(">", hud_x + hud_w - 22, bar_y + 2, size=11, color=(1, 1, 1, 1))


# =============================================================================
# Interactive Modal Operator for Viewport 2D HUD
# =============================================================================

def _view3d_region(screen):
    """(area, region) of the first 3D Viewport of the screen, or (None, None)."""
    for area in (screen.areas if screen is not None else ()):
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    return area, region
    return None, None


def _close_hud(context):
    """Hide the HUD. A HUD operator still running ends at its next event."""
    DaskHUDState.is_active = False
    DaskHUDState.is_dragging = False
    DaskHUDState.active_slider_index = -1
    if DaskHUDState.draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DaskHUDState.draw_handler, 'WINDOW')
        DaskHUDState.draw_handler = None
    obj = context.object
    if obj is not None and hasattr(obj, "dask_shape_controllers"):
        obj.dask_shape_controllers.hud_enabled = False
    if context.screen is not None:
        for area in context.screen.areas:
            area.tag_redraw()


class DASKTOON_OT_shape_axis_toggle_hud(Operator):
    """Show the active controller in the 3D Viewport: drag the handle or the sliders, I inserts a keyframe, Esc closes"""
    bl_idname = "dasktoon.shape_axis_toggle_hud"
    bl_label = "Viewport HUD"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        if not DaskHUDState.is_active or getattr(self, "_session", -1) != DaskHUDState.session:
            # Closed from the Controllers panel, or a newer HUD took over.
            return {'CANCELLED'}
        context.area.tag_redraw()
        obj = context.object
        if not obj or not hasattr(obj, "dask_shape_controllers"):
            self.cancel(context)
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        if not root.groups or root.active_group_index >= len(root.groups):
            self.cancel(context)
            return {'CANCELLED'}

        grp = root.groups[root.active_group_index]

        hud_x = root.hud_pos_x
        hud_y = root.hud_pos_y
        hud_w = root.hud_size
        if grp.controller_type == 'SLIDER_1D' and len(grp.mappings) > 2:
            hud_w = max(hud_w, len(grp.mappings) * 80 + 40)

        pad_h = root.hud_size
        hud_h = pad_h + 85

        pad_cx = hud_x + hud_w / 2
        pad_cy = hud_y + 60 + pad_h / 2
        pad_half = (pad_h - 40) / 2

        pad_left = hud_x + 15
        pad_right = hud_x + hud_w - 15
        pad_top = pad_cy + pad_half
        pad_bottom = pad_cy - pad_half

        mx, my = event.mouse_region_x, event.mouse_region_y

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                # Check Close button [X]
                if (hud_x + hud_w - 24 <= mx <= hud_x + hud_w) and (hud_y + hud_h - 26 <= my <= hud_y + hud_h):
                    self.cancel(context)
                    return {'FINISHED'}

                # Check Reset Button click
                btn_y = hud_y + 32
                if (hud_x + 10 <= mx <= hud_x + hud_w - 10) and (btn_y <= my <= btn_y + 20):
                    grp.handle_x = 0.0
                    grp.handle_y = 0.0
                    for mp in grp.mappings:
                        mp.slider_value = 0.0
                    grp.evaluate_mappings(context)
                    return {'RUNNING_MODAL'}

                # Check Prev Group Arrow [<]
                bar_y = hud_y + 8
                if (hud_x + 10 <= mx <= hud_x + 30) and (bar_y <= my <= bar_y + 14):
                    root.active_group_index = (root.active_group_index - 1) % len(root.groups)
                    return {'RUNNING_MODAL'}

                # Check Next Group Arrow [>]
                if (hud_x + hud_w - 30 <= mx <= hud_x + hud_w - 10) and (bar_y <= my <= bar_y + 14):
                    root.active_group_index = (root.active_group_index + 1) % len(root.groups)
                    return {'RUNNING_MODAL'}

                # Check Click inside Multi-Slider 1D Bank
                if grp.controller_type == 'SLIDER_1D' and grp.mappings:
                    num_sliders = len(grp.mappings)
                    col_width = (pad_right - pad_left) / num_sliders
                    if (pad_left <= mx <= pad_right) and (pad_bottom <= my <= pad_top):
                        col_idx = int((mx - pad_left) / col_width)
                        col_idx = max(0, min(col_idx, num_sliders - 1))
                        DaskHUDState.active_slider_index = col_idx
                        DaskHUDState.is_dragging = True

                        val = (my - (pad_bottom + 25)) / max(1.0, (pad_top - pad_bottom - 45))
                        grp.mappings[col_idx].slider_value = max(0.0, min(val, 1.0))
                        grp.evaluate_mappings(context)
                        return {'RUNNING_MODAL'}

                # Check Click inside 2D Pad Area
                elif (pad_cx - pad_half - 10 <= mx <= pad_cx + pad_half + 10) and (pad_cy - pad_half - 10 <= my <= pad_cy + pad_half + 10):
                    DaskHUDState.is_dragging = True
                    nx = (mx - pad_cx) / pad_half
                    ny = (my - pad_cy) / pad_half
                    grp.handle_x = max(-1.0, min(nx, 1.0))
                    grp.handle_y = max(-1.0, min(ny, 1.0))
                    grp.evaluate_mappings(context)
                    return {'RUNNING_MODAL'}

            elif event.value == 'RELEASE':
                DaskHUDState.is_dragging = False
                DaskHUDState.active_slider_index = -1

        elif event.type == 'MOUSEMOVE':
            if DaskHUDState.is_dragging:
                if grp.controller_type == 'SLIDER_1D' and 0 <= DaskHUDState.active_slider_index < len(grp.mappings):
                    col_idx = DaskHUDState.active_slider_index
                    val = (my - (pad_bottom + 25)) / max(1.0, (pad_top - pad_bottom - 45))
                    grp.mappings[col_idx].slider_value = max(0.0, min(val, 1.0))
                    grp.evaluate_mappings(context)
                else:
                    nx = (mx - pad_cx) / pad_half
                    ny = (my - pad_cy) / pad_half
                    grp.handle_x = max(-1.0, min(nx, 1.0))
                    grp.handle_y = max(-1.0, min(ny, 1.0))
                    grp.evaluate_mappings(context)
                return {'RUNNING_MODAL'}

        elif event.type == 'I' and event.value == 'PRESS':
            bpy.ops.dasktoon.shape_axis_keyframe_handle()
            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.cancel(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if DaskHUDState.is_active:
            _close_hud(context)
            return {'FINISHED'}

        obj = context.object
        if obj is None or obj.type != 'MESH' or obj.data.shape_keys is None:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        # The button sits in Properties › Object Data: the HUD runs in a 3D Viewport of the same window.
        area, region = context.area, context.region
        if area is None or area.type != 'VIEW_3D' or region is None or region.type != 'WINDOW':
            area, region = _view3d_region(context.screen)
        if area is None:
            self.report({'WARNING'}, rpt_("Open a 3D Viewport to show the HUD"))
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        if not root.groups:
            bpy.ops.dasktoon.shape_axis_auto_setup(preset_type='VRM_STANDARD')

        root.hud_enabled = True
        DaskHUDState.is_active = True
        DaskHUDState.session += 1
        self._session = DaskHUDState.session

        if DaskHUDState.draw_handler is None:
            DaskHUDState.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_shape_axis_hud_2d, (self, context), 'WINDOW', 'POST_PIXEL'
            )

        # Mouse positions reach modal() relative to the region the handler was added in.
        with context.temp_override(area=area, region=region):
            context.window_manager.modal_handler_add(self)
        area.tag_redraw()
        self.report({'INFO'}, rpt_("HUD open: drag the handle or the sliders, I inserts a keyframe, Esc closes"))
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        _close_hud(context)


# =============================================================================
# Operators: Quick Actions, Auto-Setup & Rig Board
# =============================================================================

class DASKTOON_OT_shape_axis_reset_handle(Operator):
    """Move the handle of the active controller back to the middle and set its sliders to 0"""
    bl_idname = "dasktoon.shape_axis_reset_handle"
    bl_label = "Reset Group"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj and hasattr(obj, "dask_shape_controllers"):
            root = obj.dask_shape_controllers
            if root.groups and 0 <= root.active_group_index < len(root.groups):
                grp = root.groups[root.active_group_index]
                grp.handle_x = 0.0
                grp.handle_y = 0.0
                for mp in grp.mappings:
                    mp.slider_value = 0.0
                grp.evaluate_mappings(context)
                self.report({'INFO'}, rpt_("Reset %s") % grp.name)
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_reset_all(Operator):
    """Reset every controller and set all shape keys to 0"""
    bl_idname = "dasktoon.shape_axis_reset_all"
    bl_label = "Reset All Controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj and hasattr(obj, "dask_shape_controllers"):
            root = obj.dask_shape_controllers
            for grp in root.groups:
                grp.handle_x = 0.0
                grp.handle_y = 0.0
                for mp in grp.mappings:
                    mp.slider_value = 0.0
                grp.evaluate_mappings(context)

        # Zero all mesh shape keys directly
        if obj and obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            for kb in obj.data.shape_keys.key_blocks:
                if kb != obj.data.shape_keys.reference_key:
                    kb.value = 0.0

        self.report({'INFO'}, rpt_("All controllers and shape keys reset"))
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_keyframe_handle(Operator):
    """Insert a keyframe on the handle of the active controller and on its shape keys"""
    bl_idname = "dasktoon.shape_axis_keyframe_handle"
    bl_label = "Insert Keyframe"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj and hasattr(obj, "dask_shape_controllers"):
            root = obj.dask_shape_controllers
            if root.groups and 0 <= root.active_group_index < len(root.groups):
                idx = root.active_group_index
                grp = root.groups[idx]
                obj.keyframe_insert(data_path=f'dask_shape_controllers.groups[{idx}].handle_x')
                obj.keyframe_insert(data_path=f'dask_shape_controllers.groups[{idx}].handle_y')

                if obj.data and obj.data.shape_keys:
                    for mp in grp.mappings:
                        if mp.shape_key_name:
                            kb = obj.data.shape_keys.key_blocks.get(mp.shape_key_name)
                            if kb:
                                kb.keyframe_insert(data_path="value")

                self.report({'INFO'}, rpt_("Keyframed %s at frame %d") % (grp.name, context.scene.frame_current))
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_add_group(Operator):
    """Add a controller"""
    bl_idname = "dasktoon.shape_axis_add_group"
    bl_label = "Add Controller"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="New Controller")
    category: EnumProperty(
        name="Category",
        items=[
            ('FACE', "Face", ""),
            ('LIP_SYNC', "Lip Sync", ""),
            ('BODY', "Body", ""),
            ('HAIR_EARS', "Hair & Ears", ""),
            ('CLOTH', "Cloth", ""),
            ('PROPS', "Props", ""),
        ],
        default='FACE',
    )
    ctrl_type: EnumProperty(
        name="Type",
        items=[
            ('JOYSTICK_2D', "2D Joystick", ""),
            ('VISEME_STAR', "AIUEO Star", ""),
            ('COMPASS_WHEEL', "Emotion Wheel", ""),
            ('SLIDER_1D', "Slider Bank", ""),
        ],
        default='JOYSTICK_2D',
    )

    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        root = obj.dask_shape_controllers
        grp = root.groups.add()
        grp.name = self.name
        grp.controller_category = self.category
        grp.controller_type = self.ctrl_type
        root.active_group_index = len(root.groups) - 1
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_remove_group(Operator):
    """Remove the active controller"""
    bl_idname = "dasktoon.shape_axis_remove_group"
    bl_label = "Remove Controller"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        root = obj.dask_shape_controllers
        if root.groups and 0 <= root.active_group_index < len(root.groups):
            root.groups.remove(root.active_group_index)
            root.active_group_index = max(0, root.active_group_index - 1)
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_add_mapping(Operator):
    """Add a shape key to the active controller"""
    bl_idname = "dasktoon.shape_axis_add_mapping"
    bl_label = "Add Mapping"
    bl_options = {'REGISTER', 'UNDO'}

    shape_name: StringProperty(name="Shape Key", default="")
    x: FloatProperty(name="Target X", default=0.0)
    y: FloatProperty(name="Target Y", default=0.0)
    radius: FloatProperty(name="Radius", default=0.90)

    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        root = obj.dask_shape_controllers
        if root.groups and 0 <= root.active_group_index < len(root.groups):
            grp = root.groups[root.active_group_index]
            mp = grp.mappings.add()
            mp.shape_key_name = self.shape_name
            mp.target_x = self.x
            mp.target_y = self.y
            mp.radius = self.radius
            grp.active_mapping_index = len(grp.mappings) - 1
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_remove_mapping(Operator):
    """Remove the active shape key from the controller"""
    bl_idname = "dasktoon.shape_axis_remove_mapping"
    bl_label = "Remove Mapping"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        root = obj.dask_shape_controllers
        if root.groups and 0 <= root.active_group_index < len(root.groups):
            grp = root.groups[root.active_group_index]
            if grp.mappings and 0 <= grp.active_mapping_index < len(grp.mappings):
                grp.mappings.remove(grp.active_mapping_index)
                grp.active_mapping_index = max(0, grp.active_mapping_index - 1)
        return {'FINISHED'}


# =============================================================================
# 1-Click Multi-Purpose & VRM Auto Setup Engine
# =============================================================================

class DASKTOON_OT_shape_axis_auto_setup(Operator):
    """Find the character's shape keys (VRM, VRoid, MMD and other common names) and add controllers for them"""
    bl_idname = "dasktoon.shape_axis_auto_setup"
    bl_label = "Auto Setup"
    bl_options = {'REGISTER', 'UNDO'}

    preset_type: EnumProperty(
        name="Preset",
        items=[
            ('VRM_STANDARD', "Auto Detect VRM / VRoid",
             "Emotion wheel, AIUEO star, gaze joystick and blink sliders for VRM 0.x, VRM 1.0 and VRoid shape keys"),
            ('ALL_SUITE', "Everything", "Every controller below that finds matching shape keys"),
            ('VRM_EMOTIONS', "VRM Emotions", "An emotion wheel: joy, angry, sorrow, surprised, relaxed"),
            ('AIUEO_VISEMES', "AIUEO Visemes", "A five-point star for the vowels"),
            ('BLINK_HUB', "Blink Sliders", "Sliders to blink both eyes, the left eye and the right eye"),
            ('EARS_TAIL', "Ears & Tail", "A joystick for animal ear shape keys"),
            ('BODY_MUSCLE', "Body", "A joystick for breathing, muscle and weight shape keys"),
            ('CLOTH_WIND', "Cloth Wind", "A joystick for skirt and cape sway in four directions"),
        ],
        default='VRM_STANDARD',
    )

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        before = len(root.groups)
        existing_names = [kb.name for kb in obj.data.shape_keys.key_blocks]

        def find_shape(patterns):
            for pat in patterns:
                for name in existing_names:
                    if re.search(pat, name, re.IGNORECASE):
                        return name
            return None

        # ── 1. VRM 0.x / 1.0 & ANIME EMOTION COMPASS WHEEL ──
        if self.preset_type in {'VRM_STANDARD', 'VRM_EMOTIONS', 'ALL_SUITE'}:
            joy = find_shape([r'Fcl_ALL_Joy', r'Fcl_MTH_Joy', r'^happy$', r'^joy$', r'喜', r'笑い', r'smile'])
            angry = find_shape([r'Fcl_ALL_Angry', r'Fcl_MTH_Angry', r'^angry$', r'怒', r'怒り'])
            sorrow = find_shape([r'Fcl_ALL_Sorrow', r'Fcl_MTH_Sorrow', r'^sad$', r'^sorrow$', r'哀', r'困る'])
            surprised = find_shape([r'Fcl_ALL_Surprised', r'Fcl_MTH_Surprised', r'^surprised$', r'驚', r'驚き'])
            relax = find_shape([r'Fcl_ALL_Relaxed', r'^relaxed$', r'楽', r'にこり'])

            if any([joy, angry, sorrow, surprised, relax]):
                grp = root.groups.add()
                grp.name = "expression_wheel"
                grp.controller_category = 'FACE'
                grp.controller_type = 'COMPASS_WHEEL'
                if joy: m = grp.mappings.add(); m.shape_key_name = joy; m.target_y = 1.0; m.target_x = 0.0
                if surprised: m = grp.mappings.add(); m.shape_key_name = surprised; m.target_x = 1.0; m.target_y = 0.0
                if sorrow: m = grp.mappings.add(); m.shape_key_name = sorrow; m.target_y = -1.0; m.target_x = 0.0
                if angry: m = grp.mappings.add(); m.shape_key_name = angry; m.target_x = -1.0; m.target_y = 0.0
                if relax: m = grp.mappings.add(); m.shape_key_name = relax; m.target_x = 0.707; m.target_y = 0.707

        # ── 2. VRM & ANIME 5-POINT AIUEO VISEME STAR ──
        if self.preset_type in {'VRM_STANDARD', 'AIUEO_VISEMES', 'ALL_SUITE'}:
            a_k = find_shape([r'Fcl_MTH_A', r'^aa$', r'^a$', r'v_a', r'viseme_a', r'あ', r'mouth_a'])
            i_k = find_shape([r'Fcl_MTH_I', r'^ih$', r'^i$', r'v_i', r'viseme_i', r'い', r'mouth_i'])
            u_k = find_shape([r'Fcl_MTH_U', r'^ou$', r'^u$', r'v_u', r'viseme_u', r'う', r'mouth_u'])
            e_k = find_shape([r'Fcl_MTH_E', r'^ee$', r'^e$', r'v_e', r'viseme_e', r'え', r'mouth_e'])
            o_k = find_shape([r'Fcl_MTH_O', r'^oh$', r'^o$', r'v_o', r'viseme_o', r'お', r'mouth_o'])

            if any([a_k, i_k, u_k, e_k, o_k]):
                grp = root.groups.add()
                grp.name = "aiueo_star"
                grp.controller_category = 'LIP_SYNC'
                grp.controller_type = 'VISEME_STAR'
                angles = [
                    math.pi / 2,                    # A
                    math.pi / 2 + 2 * math.pi / 5,  # I
                    math.pi / 2 + 4 * math.pi / 5,  # U
                    math.pi / 2 + 6 * math.pi / 5,  # E
                    math.pi / 2 + 8 * math.pi / 5,  # O
                ]
                keys = [a_k, i_k, u_k, e_k, o_k]
                for k, ang in zip(keys, angles):
                    if k:
                        m = grp.mappings.add()
                        m.shape_key_name = k
                        m.target_x = math.cos(ang)
                        m.target_y = math.sin(ang)
                        m.radius = 0.88

        # ── 3. VRM & ANIME EYE LOOK / GAZE JOYSTICK ──
        if self.preset_type in {'VRM_STANDARD', 'ALL_SUITE'}:
            up = find_shape([r'lookUp', r'Eye_U', r'look.*up', r'eye.*up', r'目.*上', r'look_u'])
            down = find_shape([r'lookDown', r'Eye_D', r'look.*down', r'eye.*down', r'目.*下', r'look_d'])
            left = find_shape([r'lookLeft', r'Eye_L', r'look.*left', r'eye.*left', r'目.*左', r'look_l'])
            right = find_shape([r'lookRight', r'Eye_R', r'look.*right', r'eye.*right', r'目.*右', r'look_r'])

            if any([up, down, left, right]):
                grp = root.groups.add()
                grp.name = "look_gaze"
                grp.controller_category = 'FACE'
                grp.controller_type = 'JOYSTICK_2D'
                if up: grp.mappings.add().shape_key_name = up; grp.mappings[-1].target_y = 1.0
                if down: grp.mappings.add().shape_key_name = down; grp.mappings[-1].target_y = -1.0
                if left: grp.mappings.add().shape_key_name = left; grp.mappings[-1].target_x = -1.0
                if right: grp.mappings.add().shape_key_name = right; grp.mappings[-1].target_x = 1.0

        # ── 4. MULTI-SLIDER 1D EYE BLINK HUB (3 Sliders: Blink Both, Blink L, Blink R in 1 Hub!) ──
        if self.preset_type in {'VRM_STANDARD', 'BLINK_HUB', 'ALL_SUITE'}:
            blink_both = find_shape([r'Fcl_EYE_Close$', r'^blink$', r'まばたき'])
            blink_l = find_shape([r'Fcl_EYE_Close_L', r'^blinkLeft$', r'ウィンク$', r'blink_l'])
            blink_r = find_shape([r'Fcl_EYE_Close_R', r'^blinkRight$', r'ウィンク右', r'blink_r'])

            if blink_both or blink_l or blink_r:
                grp = root.groups.add()
                grp.name = "eye_blink_hub"
                grp.controller_category = 'FACE'
                grp.controller_type = 'SLIDER_1D'
                if blink_both: m = grp.mappings.add(); m.shape_key_name = blink_both
                if blink_l: m = grp.mappings.add(); m.shape_key_name = blink_l
                if blink_r: m = grp.mappings.add(); m.shape_key_name = blink_r

        # ── 5. Kemonomimi Animal Ears & Tail ──
        if self.preset_type in {'ALL_SUITE', 'EARS_TAIL'}:
            ear_up = find_shape([r'ear.*up', r'ear.*erect', r'耳.*上', r'ear_u'])
            ear_down = find_shape([r'ear.*down', r'ear.*droop', r'耳.*下', r'ear_d'])
            ear_flat = find_shape([r'ear.*flat', r'ear.*back', r'耳.*伏'])
            ear_twitch = find_shape([r'ear.*twitch', r'ear.*wiggle'])

            if any([ear_up, ear_down, ear_flat, ear_twitch]):
                grp = root.groups.add()
                grp.name = "ears_motion"
                grp.controller_category = 'HAIR_EARS'
                grp.controller_type = 'JOYSTICK_2D'
                if ear_up: grp.mappings.add().shape_key_name = ear_up; grp.mappings[-1].target_y = 1.0
                if ear_down: grp.mappings.add().shape_key_name = ear_down; grp.mappings[-1].target_y = -1.0
                if ear_flat: grp.mappings.add().shape_key_name = ear_flat; grp.mappings[-1].target_x = -1.0
                if ear_twitch: grp.mappings.add().shape_key_name = ear_twitch; grp.mappings[-1].target_x = 1.0

        # ── 6. Cloth & Skirt Wind Controller ──
        if self.preset_type in {'ALL_SUITE', 'CLOTH_WIND'}:
            skirt_f = find_shape([r'skirt.*fwd', r'skirt.*front', r'cloth.*front', r'wind.*fwd'])
            skirt_b = find_shape([r'skirt.*back', r'cloth.*back', r'wind.*back'])
            skirt_l = find_shape([r'skirt.*left', r'cloth.*left', r'wind.*left'])
            skirt_r = find_shape([r'skirt.*right', r'cloth.*right', r'wind.*right'])

            if any([skirt_f, skirt_b, skirt_l, skirt_r]):
                grp = root.groups.add()
                grp.name = "cloth_wind_sway"
                grp.controller_category = 'CLOTH'
                grp.controller_type = 'JOYSTICK_2D'
                if skirt_f: grp.mappings.add().shape_key_name = skirt_f; grp.mappings[-1].target_y = 1.0
                if skirt_b: grp.mappings.add().shape_key_name = skirt_b; grp.mappings[-1].target_y = -1.0
                if skirt_l: grp.mappings.add().shape_key_name = skirt_l; grp.mappings[-1].target_x = -1.0
                if skirt_r: grp.mappings.add().shape_key_name = skirt_r; grp.mappings[-1].target_x = 1.0

        # ── 7. Body Breathing & Muscle Morphs ──
        if self.preset_type in {'ALL_SUITE', 'BODY_MUSCLE'}:
            breathe = find_shape([r'breath', r'chest', r'inhale', r'息'])
            flex = find_shape([r'flex', r'muscle', r'bicep', r'fit'])
            fat = find_shape([r'fat', r'heavy', r'chubby'])

            if any([breathe, flex, fat]):
                grp = root.groups.add()
                grp.name = "body_dynamics"
                grp.controller_category = 'BODY'
                grp.controller_type = 'JOYSTICK_2D'
                if breathe: grp.mappings.add().shape_key_name = breathe; grp.mappings[-1].target_y = 1.0
                if flex: grp.mappings.add().shape_key_name = flex; grp.mappings[-1].target_x = 1.0
                if fat: grp.mappings.add().shape_key_name = fat; grp.mappings[-1].target_x = -1.0

        root.active_group_index = 0
        self.report({'INFO'}, rpt_("Auto Setup added %d controllers") % (len(root.groups) - before))
        return {'FINISHED'}


# =============================================================================
# 3D Viewport Face Rig Board Generator (Drivers & Bone/Empty Controls)
# =============================================================================

class DASKTOON_OT_shape_axis_generate_rig_board(Operator):
    """Add a board next to the mesh with a frame and an empty handle per controller, as a start for a rig"""
    bl_idname = "dasktoon.shape_axis_generate_rig_board"
    bl_label = "Generate 3D Rig Board"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        if not root.groups:
            self.report({'WARNING'}, rpt_("No controllers yet: run Auto Setup first"))
            return {'CANCELLED'}

        col_name = f"{obj.name}_ShapeRigBoard"
        rig_col = bpy.data.collections.get(col_name)
        if not rig_col:
            rig_col = bpy.data.collections.new(col_name)
            context.scene.collection.children.link(rig_col)

        base_x = obj.location.x + 1.5
        base_z = obj.location.z + 1.2

        for i, grp in enumerate(root.groups):
            slot_x = base_x + (i % 3) * 0.9
            slot_z = base_z - (i // 3) * 0.9

            # Background Frame Object
            bpy.ops.mesh.primitive_plane_add(size=0.6, location=(slot_x, obj.location.y, slot_z), rotation=(math.radians(90), 0, 0))
            frame = context.active_object
            frame.name = f"RigFrame_{grp.name}"
            for col in list(frame.users_collection):
                col.objects.unlink(frame)
            rig_col.objects.link(frame)

            # Interactive Handle Controller (Empty)
            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.08, location=(slot_x, obj.location.y, slot_z))
            handle = context.active_object
            handle.name = f"CTRL_{grp.name}"
            for col in list(handle.users_collection):
                col.objects.unlink(handle)
            rig_col.objects.link(handle)

            # Limit movement to frame bounds
            con = handle.constraints.new(type='LIMIT_LOCATION')
            con.use_min_x = True; con.min_x = slot_x - 0.25
            con.use_max_x = True; con.max_x = slot_x + 0.25
            con.use_min_z = True; con.min_z = slot_z - 0.25
            con.use_max_z = True; con.max_z = slot_z + 0.25
            con.use_min_y = True; con.min_y = obj.location.y
            con.use_max_y = True; con.max_y = obj.location.y
            con.owner_space = 'WORLD'

        self.report({'INFO'}, rpt_("Rig board with %d controllers added to collection %s") % (len(root.groups), col_name))
        return {'FINISHED'}


# =============================================================================
# Lists of the Controllers panel
# =============================================================================

class DASKTOON_UL_shape_groups(UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        grp = item
        type_icons = {
            'JOYSTICK_2D': 'TRACKING',
            'VISEME_STAR': 'OUTLINER_OB_FONT',
            'COMPASS_WHEEL': 'ORIENTATION_GIMBAL',
            'SLIDER_1D': 'DRIVER_DISTANCE',
        }
        ic = type_icons.get(grp.controller_type, 'SETTINGS')
        layout.prop(grp, "name", text="", emboss=False, icon=ic)
        layout.label(text=iface_("%d shapes") % len(grp.mappings), translate=False)


class DASKTOON_UL_shape_mappings(UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        mp = item
        layout.prop(mp, "enabled", text="")
        layout.label(text=mp.shape_key_name or iface_("(Empty)"), icon='SHAPEKEY_DATA', translate=False)
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="X:%.2f Y:%.2f" % (mp.target_x, mp.target_y), translate=False)


# =============================================================================
# VRM ShapeKey Toolset (ARKit & VRM Standard Blendshape Suite)
# =============================================================================

class DASKTOON_OT_vrm_init_standard(Operator):
    """Add the VRM expression shape keys the mesh does not have yet, empty, ready to sculpt"""
    bl_idname = "dasktoon.vrm_init_standard"
    bl_label = "Add VRM Expression Set"
    bl_options = {'REGISTER', 'UNDO'}

    standard_type: EnumProperty(
        name="Version",
        items=[
            ('VRM_0', "VRM 0.x", "The 18 VRM 0.x shape keys: joy, angry, a, i, u, blink…"),
            ('VRM_1', "VRM 1.0", "The 18 VRM 1.0 shape keys: happy, sad, aa, ih, blinkLeft…"),
        ],
        default='VRM_0',
    )

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, rpt_("Select a mesh object"))
            return {'CANCELLED'}

        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis", from_mix=False)

        sk = obj.data.shape_keys

        vrm0_names = [
            "joy", "angry", "sorrow", "fun", "surprised", "neutral",
            "a", "i", "u", "e", "o",
            "blink", "blink_l", "blink_r",
            "lookup", "lookdown", "lookleft", "lookright",
        ]
        vrm1_names = [
            "happy", "angry", "sad", "relaxed", "surprised", "neutral",
            "aa", "ih", "ou", "ee", "oh",
            "blink", "blinkLeft", "blinkRight",
            "lookUp", "lookDown", "lookLeft", "lookRight",
        ]

        target_names = vrm0_names if self.standard_type == 'VRM_0' else vrm1_names
        added = 0
        for name in target_names:
            if name not in sk.key_blocks:
                obj.shape_key_add(name=name, from_mix=False)
                added += 1

        self.report({'INFO'}, rpt_("Added %d VRM shape keys") % added)
        return {'FINISHED'}


class DASKTOON_OT_vrm_split_shape_key(Operator):
    """Split a symmetric shape key into a left and a right shape key, blended across the middle of the mesh"""
    bl_idname = "dasktoon.vrm_split_shape_key"
    bl_label = "Split Left / Right"
    bl_options = {'REGISTER', 'UNDO'}

    source_shape: StringProperty(name="Source", default="")
    falloff: FloatProperty(name="Falloff", default=0.015, min=0.0, max=0.2,
                           description="Width of the blend across the middle of the mesh (X = 0)")
    suffix_style: EnumProperty(
        name="Suffix",
        items=[
            ('_L_R', "_L / _R", "Names like blink_L and blink_R"),
            ('Left_Right', "Left / Right", "Names like blinkLeft and blinkRight"),
            ('_l_r', "_l / _r", "Names like blink_l and blink_r"),
        ],
        default='_L_R',
    )

    def invoke(self, context, _event):
        obj = context.object
        if obj and obj.data and obj.data.shape_keys:
            active_kb = obj.active_shape_key
            if active_kb and active_kb.name != "Basis":
                self.source_shape = active_kb.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        if not self.source_shape or self.source_shape not in sk.key_blocks:
            self.report({'ERROR'}, rpt_("Shape key %s not found") % self.source_shape)
            return {'CANCELLED'}

        basis_kb = sk.key_blocks[0]
        src_kb = sk.key_blocks[self.source_shape]

        if self.suffix_style == '_L_R':
            l_name = f"{self.source_shape}_L"
            r_name = f"{self.source_shape}_R"
        elif self.suffix_style == 'Left_Right':
            l_name = f"{self.source_shape}Left"
            r_name = f"{self.source_shape}Right"
        else:
            l_name = f"{self.source_shape}_l"
            r_name = f"{self.source_shape}_r"

        left_kb = sk.key_blocks.get(l_name) or obj.shape_key_add(name=l_name, from_mix=False)
        right_kb = sk.key_blocks.get(r_name) or obj.shape_key_add(name=r_name, from_mix=False)

        fall = max(1e-5, self.falloff)
        for i, v in enumerate(obj.data.vertices):
            b_co = basis_kb.data[i].co
            s_co = src_kb.data[i].co
            delta = s_co - b_co

            x = b_co.x
            # Smoothstep between -fall and +fall
            t = (x + fall) / (2.0 * fall)
            t = max(0.0, min(1.0, t))
            fac_l = t * t * (3.0 - 2.0 * t)
            fac_r = 1.0 - fac_l

            left_kb.data[i].co = b_co + delta * fac_l
            right_kb.data[i].co = b_co + delta * fac_r

        self.report({'INFO'}, rpt_("Split %s into %s and %s") % (self.source_shape, l_name, r_name))
        return {'FINISHED'}


class DASKTOON_OT_vrm_bake_expression(Operator):
    """Save the current mix of shape key values as a new shape key"""
    bl_idname = "dasktoon.vrm_bake_expression"
    bl_label = "Bake Expression to New Shape Key"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(name="Name", default="custom_expression_baked")
    reset_after: BoolProperty(name="Clear Values After Bake", default=True)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        basis_kb = sk.key_blocks[0]
        new_kb = sk.key_blocks.get(self.new_name) or obj.shape_key_add(name=self.new_name, from_mix=False)

        deltas = [mathutils.Vector((0.0, 0.0, 0.0)) for _ in obj.data.vertices] if 'mathutils' in globals() else [v.co.copy() * 0.0 for v in obj.data.vertices]

        active_count = 0
        for kb in sk.key_blocks:
            if kb == basis_kb or kb == new_kb or kb.value == 0.0:
                continue
            val = kb.value
            active_count += 1
            for i in range(len(obj.data.vertices)):
                deltas[i] += (kb.data[i].co - basis_kb.data[i].co) * val

        for i, v in enumerate(obj.data.vertices):
            new_kb.data[i].co = basis_kb.data[i].co + deltas[i]

        if self.reset_after:
            for kb in sk.key_blocks:
                if kb != basis_kb and kb != new_kb:
                    kb.value = 0.0

        self.report({'INFO'}, rpt_("Baked %d shape keys into %s") % (active_count, self.new_name))
        return {'FINISHED'}


class DASKTOON_OT_vrm_synthesize_arkit52(Operator):
    """Build the 52 ARKit face tracking shape keys from the VRM or VRoid shape keys of the mesh"""
    bl_idname = "dasktoon.vrm_synthesize_arkit52"
    bl_label = "Synthesize ARKit 52 from VRM"
    bl_options = {'REGISTER', 'UNDO'}

    overwrite_existing: BoolProperty(name="Overwrite Existing", default=False)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        existing_names = {kb.name: kb for kb in sk.key_blocks}
        basis_kb = sk.key_blocks[0]

        def get_kb(patterns):
            for pat in patterns:
                for name, kb in existing_names.items():
                    if re.search(pat, name, re.IGNORECASE):
                        return kb
            return None

        # Detect VRM base shapes
        joy_kb = get_kb([r'Fcl_ALL_Joy', r'happy', r'joy', r'笑い', r'smile'])
        angry_kb = get_kb([r'Fcl_ALL_Angry', r'angry', r'怒'])
        sad_kb = get_kb([r'Fcl_ALL_Sorrow', r'sad', r'sorrow', r'哀'])
        surprised_kb = get_kb([r'Fcl_ALL_Surprised', r'surprised', r'驚'])
        blink_both = get_kb([r'Fcl_EYE_Close$', r'^blink$', r'まばたき'])
        blink_l = get_kb([r'Fcl_EYE_Close_L', r'^blinkLeft$', r'ウィンク$', r'blink_l']) or blink_both
        blink_r = get_kb([r'Fcl_EYE_Close_R', r'^blinkRight$', r'ウィンク右', r'blink_r']) or blink_both
        a_kb = get_kb([r'Fcl_MTH_A', r'^aa$', r'^a$', r'あ'])
        i_kb = get_kb([r'Fcl_MTH_I', r'^ih$', r'^i$', r'い'])
        u_kb = get_kb([r'Fcl_MTH_U', r'^ou$', r'^u$', r'う'])
        e_kb = get_kb([r'Fcl_MTH_E', r'^ee$', r'^e$', r'え'])
        o_kb = get_kb([r'Fcl_MTH_O', r'^oh$', r'^o$', r'お'])
        look_u = get_kb([r'lookUp', r'Eye_U', r'eye.*up'])
        look_d = get_kb([r'lookDown', r'Eye_D', r'eye.*down'])
        look_l = get_kb([r'lookLeft', r'Eye_L', r'eye.*left'])
        look_r = get_kb([r'lookRight', r'Eye_R', r'eye.*right'])

        # 52 ARKit Blendshapes Recipe Table: (ARKit_Name, [(source_kb, weight, side_filter)])
        # side_filter: 'L' (X>0), 'R' (X<0), 'ALL'
        recipes = {
            # Eyes
            'eyeBlinkLeft': [(blink_l, 1.0, 'L')],
            'eyeBlinkRight': [(blink_r, 1.0, 'R')],
            'eyeLookDownLeft': [(look_d, 1.0, 'L')],
            'eyeLookDownRight': [(look_d, 1.0, 'R')],
            'eyeLookInLeft': [(look_r, 1.0, 'L')],
            'eyeLookInRight': [(look_l, 1.0, 'R')],
            'eyeLookOutLeft': [(look_l, 1.0, 'L')],
            'eyeLookOutRight': [(look_r, 1.0, 'R')],
            'eyeLookUpLeft': [(look_u, 1.0, 'L')],
            'eyeLookUpRight': [(look_u, 1.0, 'R')],
            'eyeSquintLeft': [(joy_kb, 0.5, 'L')],
            'eyeSquintRight': [(joy_kb, 0.5, 'R')],
            'eyeWideLeft': [(surprised_kb, 0.6, 'L')],
            'eyeWideRight': [(surprised_kb, 0.6, 'R')],
            # Jaw
            'jawOpen': [(a_kb, 1.0, 'ALL')],
            'jawForward': [(a_kb, 0.2, 'ALL')],
            'jawLeft': [(a_kb, 0.2, 'L')],
            'jawRight': [(a_kb, 0.2, 'R')],
            # Mouth
            'mouthClose': [(a_kb, -0.3, 'ALL')],
            'mouthFunnel': [(u_kb, 0.8, 'ALL')],
            'mouthPucker': [(o_kb, 0.9, 'ALL')],
            'mouthLeft': [(i_kb, 0.5, 'L')],
            'mouthRight': [(i_kb, 0.5, 'R')],
            'mouthSmileLeft': [(joy_kb, 0.7, 'L'), (blink_l, 0.25, 'L')],
            'mouthSmileRight': [(joy_kb, 0.7, 'R'), (blink_r, 0.25, 'R')],
            'mouthFrownLeft': [(sad_kb, 0.8, 'L')],
            'mouthFrownRight': [(sad_kb, 0.8, 'R')],
            'mouthDimpleLeft': [(joy_kb, 0.4, 'L')],
            'mouthDimpleRight': [(joy_kb, 0.4, 'R')],
            'mouthStretchLeft': [(i_kb, 0.8, 'L')],
            'mouthStretchRight': [(i_kb, 0.8, 'R')],
            'mouthRollLower': [(o_kb, 0.3, 'ALL')],
            'mouthRollUpper': [(u_kb, 0.3, 'ALL')],
            'mouthShrugLower': [(sad_kb, 0.4, 'ALL')],
            'mouthShrugUpper': [(sad_kb, 0.4, 'ALL')],
            'mouthPressLeft': [(i_kb, 0.3, 'L')],
            'mouthPressRight': [(i_kb, 0.3, 'R')],
            'mouthLowerDownLeft': [(a_kb, 0.5, 'L')],
            'mouthLowerDownRight': [(a_kb, 0.5, 'R')],
            'mouthUpperUpLeft': [(joy_kb, 0.5, 'L')],
            'mouthUpperUpRight': [(joy_kb, 0.5, 'R')],
            # Brows
            'browDownLeft': [(angry_kb, 0.85, 'L')],
            'browDownRight': [(angry_kb, 0.85, 'R')],
            'browInnerUp': [(surprised_kb, 0.75, 'ALL')],
            'browOuterUpLeft': [(surprised_kb, 0.6, 'L')],
            'browOuterUpRight': [(surprised_kb, 0.6, 'R')],
            # Cheeks & Nose
            'cheekPuff': [(u_kb, 0.5, 'ALL')],
            'cheekSquintLeft': [(joy_kb, 0.6, 'L')],
            'cheekSquintRight': [(joy_kb, 0.6, 'R')],
            'noseSneerLeft': [(angry_kb, 0.5, 'L')],
            'noseSneerRight': [(angry_kb, 0.5, 'R')],
            'tongueOut': [(a_kb, 0.25, 'ALL')],
        }

        generated_count = 0
        fall = 0.015
        for arkit_name, ingredients in recipes.items():
            if arkit_name in sk.key_blocks and not self.overwrite_existing:
                continue

            target_kb = sk.key_blocks.get(arkit_name) or obj.shape_key_add(name=arkit_name, from_mix=False)
            deltas = [v.co.copy() * 0.0 for v in obj.data.vertices]

            for src_kb, weight, side in ingredients:
                if not src_kb:
                    continue
                for i, v in enumerate(obj.data.vertices):
                    b_co = basis_kb.data[i].co
                    s_co = src_kb.data[i].co
                    d = (s_co - b_co) * weight

                    x = b_co.x
                    if side == 'L':
                        t = max(0.0, min(1.0, (x + fall) / (2.0 * fall)))
                        fac = t * t * (3.0 - 2.0 * t)
                    elif side == 'R':
                        t = max(0.0, min(1.0, (x + fall) / (2.0 * fall)))
                        fac = 1.0 - (t * t * (3.0 - 2.0 * t))
                    else:
                        fac = 1.0

                    deltas[i] += d * fac

            for i, v in enumerate(obj.data.vertices):
                target_kb.data[i].co = basis_kb.data[i].co + deltas[i]

            generated_count += 1

        self.report({'INFO'}, rpt_("Built %d of the 52 ARKit shape keys") % generated_count)
        return {'FINISHED'}


class DASKTOON_OT_vrm_remove_empty_shapes(Operator):
    """Remove the shape keys that move no vertex"""
    bl_idname = "dasktoon.vrm_remove_empty_shapes"
    bl_label = "Remove Empty Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        basis_kb = sk.key_blocks[0]
        to_remove = []

        for kb in sk.key_blocks:
            if kb == basis_kb:
                continue
            max_d = 0.0
            for i in range(len(obj.data.vertices)):
                d = (kb.data[i].co - basis_kb.data[i].co).length
                if d > max_d:
                    max_d = d
                    if max_d > 1e-4:
                        break
            if max_d < 1e-4:
                to_remove.append(kb.name)

        for name in to_remove:
            kb = sk.key_blocks.get(name)
            if kb:
                obj.shape_key_remove(kb)

        self.report({'INFO'}, rpt_("Removed %d empty shape keys") % len(to_remove))
        return {'FINISHED'}


class DASKTOON_OT_vrm_convert_naming(Operator):
    """Rename shape keys from one naming standard to another (VRoid, VRM 0.x, VRM 1.0)"""
    bl_idname = "dasktoon.vrm_convert_naming"
    bl_label = "Convert Naming"
    bl_options = {'REGISTER', 'UNDO'}

    conversion_mode: EnumProperty(
        name="Conversion",
        items=[
            ('VROID_TO_VRM0', "VRoid to VRM 0.x", "Rename VRoid shape keys (Fcl_ALL_Joy…) to VRM 0.x names (joy…)"),
            ('VRM0_TO_VRM1', "VRM 0.x to VRM 1.0",
             "Rename VRM 0.x shape keys (joy, blink_l…) to VRM 1.0 names (happy, blinkLeft…)"),
            ('VRM1_TO_VRM0', "VRM 1.0 to VRM 0.x",
             "Rename VRM 1.0 shape keys (happy, blinkLeft…) to VRM 0.x names (joy, blink_l…)"),
        ],
        default='VROID_TO_VRM0',
    )

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        rename_map = {}

        if self.conversion_mode == 'VROID_TO_VRM0':
            rename_map = {
                'Fcl_ALL_Joy': 'joy', 'Fcl_ALL_Angry': 'angry', 'Fcl_ALL_Sorrow': 'sorrow',
                'Fcl_ALL_Surprised': 'surprised', 'Fcl_ALL_Neutral': 'neutral',
                'Fcl_MTH_A': 'a', 'Fcl_MTH_I': 'i', 'Fcl_MTH_U': 'u', 'Fcl_MTH_E': 'e', 'Fcl_MTH_O': 'o',
                'Fcl_EYE_Close': 'blink', 'Fcl_EYE_Close_L': 'blink_l', 'Fcl_EYE_Close_R': 'blink_r',
                'Eye_U': 'lookup', 'Eye_D': 'lookdown', 'Eye_L': 'lookleft', 'Eye_R': 'lookright',
            }
        elif self.conversion_mode == 'VRM0_TO_VRM1':
            rename_map = {
                'joy': 'happy', 'sorrow': 'sad', 'fun': 'relaxed',
                'a': 'aa', 'i': 'ih', 'u': 'ou', 'e': 'ee', 'o': 'oh',
                'blink_l': 'blinkLeft', 'blink_r': 'blinkRight',
                'lookup': 'lookUp', 'lookdown': 'lookDown', 'lookleft': 'lookLeft', 'lookright': 'lookRight',
            }
        elif self.conversion_mode == 'VRM1_TO_VRM0':
            rename_map = {
                'happy': 'joy', 'sad': 'sorrow', 'relaxed': 'fun',
                'aa': 'a', 'ih': 'i', 'ou': 'u', 'ee': 'e', 'oh': 'o',
                'blinkLeft': 'blink_l', 'blinkRight': 'blink_r',
                'lookUp': 'lookup', 'lookDown': 'lookdown', 'lookLeft': 'lookleft', 'lookRight': 'lookright',
            }

        renamed = 0
        for old_n, new_n in rename_map.items():
            kb = sk.key_blocks.get(old_n)
            if kb and new_n not in sk.key_blocks:
                kb.name = new_n
                renamed += 1

        self.report({'INFO'}, rpt_("Renamed %d shape keys") % renamed)
        return {'FINISHED'}


class DASKTOON_OT_vrm_live_preview(Operator):
    """Play a blink, speech or emotion test on the mesh in a loop, until Esc or right click"""
    bl_idname = "dasktoon.vrm_live_preview"
    bl_label = "Live Preview"
    bl_options = {'REGISTER'}

    _timer = None
    _step = 0.0
    preview_mode: EnumProperty(
        name="Mode",
        items=[
            ('AUTO_BLINK', "Blink", "Blink every few seconds"),
            ('AIUEO_TALK', "Speech", "Say the vowels A, I, U, E, O in a loop"),
            ('EMOTIONS', "Emotions", "Go through joy, surprise, sorrow and anger in a loop"),
        ],
        default='AUTO_BLINK',
    )

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self._step += 0.08
            obj = context.object
            if not obj or not obj.data or not obj.data.shape_keys:
                return {'PASS_THROUGH'}

            sk = obj.data.shape_keys
            def set_val(pat, val):
                for name, kb in sk.key_blocks.items():
                    if re.search(pat, name, re.IGNORECASE):
                        kb.value = val

            if self.preview_mode == 'AUTO_BLINK':
                # Blink pulse every ~2.5 seconds
                cycle = self._step % 3.0
                blink_val = math.sin(cycle * math.pi / 0.25) if cycle < 0.25 else 0.0
                set_val(r'blink|Fcl_EYE_Close', max(0.0, blink_val))

            elif self.preview_mode == 'AIUEO_TALK':
                # 5 vowels sequentially
                phase = (self._step * 1.5) % 5.0
                idx = int(phase)
                frac = phase - idx
                vowels = [r'Fcl_MTH_A|^a$|^aa$', r'Fcl_MTH_I|^i$|^ih$', r'Fcl_MTH_U|^u$|^ou$', r'Fcl_MTH_E|^e$|^ee$', r'Fcl_MTH_O|^o$|^oh$']
                for j, pat in enumerate(vowels):
                    w = math.sin(frac * math.pi) if j == idx else 0.0
                    set_val(pat, max(0.0, w))

            elif self.preview_mode == 'EMOTIONS':
                # Smooth emotion waves
                e_phase = (self._step * 0.5) % 4.0
                e_idx = int(e_phase)
                e_frac = e_phase - e_idx
                emotes = [r'Joy|happy', r'Surprised', r'Sorrow|sad', r'Angry']
                for j, pat in enumerate(emotes):
                    w = math.sin(e_frac * math.pi) if j == e_idx else 0.0
                    set_val(pat, max(0.0, w))

            context.area.tag_redraw()

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.033, window=context.window)
        wm.modal_handler_add(self)
        self.report({'INFO'}, rpt_("Live preview running: press Esc or right click to stop"))
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        # Reset shapes
        obj = context.object
        if obj and obj.data and obj.data.shape_keys:
            for kb in obj.data.shape_keys.key_blocks:
                if kb != obj.data.shape_keys.key_blocks[0]:
                    kb.value = 0.0
        context.area.tag_redraw()
        self.report({'INFO'}, rpt_("Live preview stopped"))


# =============================================================================
# VRM Visual Reference Guide Database & Solo Preview
# =============================================================================

VRM_GUIDE_CARDS = {
    'JOY': {
        'name': n_("Joy"),
        'region': n_("Mouth Corners and Eyes"),
        'desc': n_("A bright smile: the mouth corners pull out and up, and the lower eyelids push up into smiling "
                   "half-moon eyes."),
        'targets': ['joy', 'happy', 'Fcl_ALL_Joy', 'mouthSmileLeft', 'mouthSmileRight'],
    },
    'ANGRY': {
        'name': n_("Angry"),
        'region': n_("Brows and Mouth Corners"),
        'desc': n_("Anger: the inner ends of the brows drop and press toward the nose, the eyes narrow hard and the "
                   "mouth corners turn down."),
        'targets': ['angry', 'Fcl_ALL_Angry', 'browDownLeft', 'browDownRight', 'mouthFrownLeft', 'mouthFrownRight'],
    },
    'SORROW': {
        'name': n_("Sorrow"),
        'region': n_("Brows and Lower Lip"),
        'desc': n_("Sadness: the inner ends of the brows rise into a slant, the mouth corners droop and the gaze "
                   "falls."),
        'targets': ['sorrow', 'sad', 'Fcl_ALL_Sorrow', 'browInnerUp', 'mouthFrownLeft', 'mouthFrownRight'],
    },
    'SURPRISED': {
        'name': n_("Surprised"),
        'region': n_("Wide Eyes and O Mouth"),
        'desc': n_("Surprise: the eyes open as wide as they go, the pupils shrink a little, the brows rise high and "
                   "the mouth opens into an O."),
        'targets': ['surprised', 'Fcl_ALL_Surprised', 'eyeWideLeft', 'eyeWideRight', 'browInnerUp', 'jawOpen'],
    },
    'RELAXED': {
        'name': n_("Relaxed"),
        'region': n_("Curved Closed Eyes and Soft Smile"),
        'desc': n_("Contentment: the eyes close into curves (^ ^) and the mouth corners smile softly."),
        'targets': ['fun', 'relaxed', 'Fcl_ALL_Relaxed', 'mouthDimpleLeft', 'mouthDimpleRight'],
    },
    'VISEME_A': {
        'name': n_("Viseme A"),
        'region': n_("Jaw Lowered, Mouth Open Tall"),
        'desc': n_("Mouth shape for 'A': the jaw drops and the mouth opens tall, showing the upper front teeth and "
                   "the tongue."),
        'targets': ['a', 'aa', 'Fcl_MTH_A', 'jawOpen'],
    },
    'VISEME_I': {
        'name': n_("Viseme I"),
        'region': n_("Lips Pulled Wide, Teeth Showing"),
        'desc': n_("Mouth shape for 'I': both mouth corners stretch sideways, showing both rows of teeth."),
        'targets': ['i', 'ih', 'Fcl_MTH_I', 'mouthStretchLeft', 'mouthStretchRight'],
    },
    'VISEME_U': {
        'name': n_("Viseme U"),
        'region': n_("Small Pursed Lips"),
        'desc': n_("Mouth shape for 'U': both lips purse forward into a small circle and the cheeks draw in a "
                   "little."),
        'targets': ['u', 'ou', 'Fcl_MTH_U', 'mouthFunnel', 'mouthPucker'],
    },
    'VISEME_E': {
        'name': n_("Viseme E"),
        'region': n_("Mouth Half Open"),
        'desc': n_("Mouth shape for 'E': the mouth corners open moderately and the upper lip arches a little."),
        'targets': ['e', 'ee', 'Fcl_MTH_E', 'mouthSmileLeft', 'mouthSmileRight'],
    },
    'VISEME_O': {
        'name': n_("Viseme O"),
        'region': n_("Round Mouth"),
        'desc': n_("Mouth shape for 'O': the mouth opens round like an egg and the lips push forward a little."),
        'targets': ['o', 'oh', 'Fcl_MTH_O', 'mouthPucker', 'jawOpen'],
    },
    'BLINK_BOTH': {
        'name': n_("Blink Both Eyes"),
        'region': n_("Upper Eyelids"),
        'desc': n_("A full blink: the upper eyelids close all the way onto the lower ones and the lashes fold "
                   "naturally."),
        'targets': ['blink', 'Fcl_EYE_Close', 'eyeBlinkLeft', 'eyeBlinkRight'],
    },
    'WINK_L': {
        'name': n_("Wink Left"),
        'region': n_("Left Eye"),
        'desc': n_("Only the left eye closes in a playful wink; the right eye stays wide open."),
        'targets': ['blink_l', 'blinkLeft', 'Fcl_EYE_Close_L', 'eyeBlinkLeft'],
    },
    'WINK_R': {
        'name': n_("Wink Right"),
        'region': n_("Right Eye"),
        'desc': n_("Only the right eye closes; the left eye stays open as usual."),
        'targets': ['blink_r', 'blinkRight', 'Fcl_EYE_Close_R', 'eyeBlinkRight'],
    },
    'CHEEK_PUFF': {
        'name': n_("Cheek Puff"),
        'region': n_("Both Cheeks"),
        'desc': n_("Both cheeks puff out, as if holding air or sulking."),
        'targets': ['cheekPuff', 'Fcl_MTH_U'],
    },
}


class DASKTOON_OT_vrm_guide_solo_preview(Operator):
    """Show this expression on the mesh: its shape keys go to the intensity, all others to 0"""
    bl_idname = "dasktoon.vrm_guide_solo_preview"
    bl_label = "Test Expression on Model"
    bl_options = {'REGISTER', 'UNDO'}

    card_key: StringProperty(name="Expression", default="JOY")
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        for kb in sk.key_blocks:
            kb.value = 0.0

        card = VRM_GUIDE_CARDS.get(self.card_key)
        if not card:
            return {'CANCELLED'}

        applied = []
        for pat in card['targets']:
            for name, kb in sk.key_blocks.items():
                if name.lower() == pat.lower() or re.search(f'^{pat}$', name, re.IGNORECASE):
                    kb.value = self.intensity
                    applied.append(name)
                    break

        if applied:
            self.report({'INFO'}, rpt_("Showing %s: %s") % (iface_(card['name']), ", ".join(applied)))
        else:
            self.report({'WARNING'}, rpt_("No shape key of the mesh matches %s: add a VRM expression set first")
                        % iface_(card['name']))

        return {'FINISHED'}


# =============================================================================
# ARKit 52 Database & Visual Reference Guide
# =============================================================================

ARKIT_52_ALL_NAMES = [
    # Eye (14)
    'eyeBlinkLeft', 'eyeBlinkRight', 'eyeLookDownLeft', 'eyeLookDownRight',
    'eyeLookInLeft', 'eyeLookInRight', 'eyeLookOutLeft', 'eyeLookOutRight',
    'eyeLookUpLeft', 'eyeLookUpRight', 'eyeSquintLeft', 'eyeSquintRight',
    'eyeWideLeft', 'eyeWideRight',
    # Jaw (4)
    'jawOpen', 'jawForward', 'jawLeft', 'jawRight',
    # Mouth (23)
    'mouthClose', 'mouthFunnel', 'mouthPucker', 'mouthLeft', 'mouthRight',
    'mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft', 'mouthFrownRight',
    'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft', 'mouthStretchRight',
    'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower', 'mouthShrugUpper',
    'mouthPressLeft', 'mouthPressRight', 'mouthLowerDownLeft', 'mouthLowerDownRight',
    'mouthUpperUpLeft', 'mouthUpperUpRight',
    # Brows (5)
    'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
    # Cheeks, Nose & Tongue (6)
    'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft', 'noseSneerRight', 'tongueOut',
]

ARKIT_GUIDE_DB = {
    'eyeBlinkLeft': (n_("Left Eyelid"), n_("Closes the left upper eyelid fully onto the lower one.")),
    'eyeBlinkRight': (n_("Right Eyelid"), n_("Closes the right upper eyelid fully onto the lower one.")),
    'eyeLookUpLeft': (n_("Left Pupil"), n_("Turns the left eye up.")),
    'eyeLookUpRight': (n_("Right Pupil"), n_("Turns the right eye up.")),
    'eyeLookDownLeft': (n_("Left Pupil"), n_("Turns the left eye down.")),
    'eyeLookDownRight': (n_("Right Pupil"), n_("Turns the right eye down.")),
    'eyeLookInLeft': (n_("Left Pupil"), n_("Turns the left eye in, toward the nose.")),
    'eyeLookInRight': (n_("Right Pupil"), n_("Turns the right eye in, toward the nose.")),
    'eyeLookOutLeft': (n_("Left Pupil"), n_("Turns the left eye out, toward the temple.")),
    'eyeLookOutRight': (n_("Right Pupil"), n_("Turns the right eye out, toward the temple.")),
    'eyeSquintLeft': (n_("Left Eye Squint"), n_("Pushes the left lower eyelid up, as in a smiling squint.")),
    'eyeSquintRight': (n_("Right Eye Squint"), n_("Pushes the right lower eyelid up, as in a smiling squint.")),
    'eyeWideLeft': (n_("Left Eye Wide"), n_("Opens the left upper eyelid as wide as it goes.")),
    'eyeWideRight': (n_("Right Eye Wide"), n_("Opens the right upper eyelid as wide as it goes.")),
    'jawOpen': (n_("Jaw Open"), n_("Drops the jaw to open the mouth wide.")),
    'jawForward': (n_("Jaw Forward"), n_("Pushes the lower jaw forward.")),
    'jawLeft': (n_("Jaw Left"), n_("Slides the lower jaw to the left.")),
    'jawRight': (n_("Jaw Right"), n_("Slides the lower jaw to the right.")),
    'mouthClose': (n_("Lips Closed"), n_("Presses the lips together while the jaw is open.")),
    'mouthFunnel': (n_("Lip Funnel"), n_("Opens the lips into a round funnel, as in a loud 'U'.")),
    'mouthPucker': (n_("Lip Pucker"), n_("Puckers the lips forward into a small round shape, as for a kiss.")),
    'mouthLeft': (n_("Mouth Left"), n_("Slides the whole mouth to the left.")),
    'mouthRight': (n_("Mouth Right"), n_("Slides the whole mouth to the right.")),
    'mouthSmileLeft': (n_("Left Smile"), n_("Pulls the left mouth corner out and up.")),
    'mouthSmileRight': (n_("Right Smile"), n_("Pulls the right mouth corner out and up.")),
    'mouthFrownLeft': (n_("Left Frown"), n_("Pulls the left mouth corner down.")),
    'mouthFrownRight': (n_("Right Frown"), n_("Pulls the right mouth corner down.")),
    'mouthDimpleLeft': (n_("Left Dimple"), n_("Pulls the left mouth corner back into the cheek, making a dimple.")),
    'mouthDimpleRight': (n_("Right Dimple"), n_("Pulls the right mouth corner back into the cheek, making a dimple.")),
    'mouthStretchLeft': (n_("Left Stretch"), n_("Stretches the left mouth corner sideways, as for 'I'.")),
    'mouthStretchRight': (n_("Right Stretch"), n_("Stretches the right mouth corner sideways, as for 'I'.")),
    'mouthRollLower': (n_("Lower Lip Roll"), n_("Rolls the lower lip in over the teeth.")),
    'mouthRollUpper': (n_("Upper Lip Roll"), n_("Rolls the upper lip in over the teeth.")),
    'mouthShrugLower': (n_("Lower Lip Shrug"), n_("Pushes the lower lip up.")),
    'mouthShrugUpper': (n_("Upper Lip Shrug"), n_("Lifts the upper lip a little.")),
    'mouthPressLeft': (n_("Left Lip Press"), n_("Presses the left side of the lips flat together.")),
    'mouthPressRight': (n_("Right Lip Press"), n_("Presses the right side of the lips flat together.")),
    'mouthLowerDownLeft': (n_("Left Lower Lip Down"),
                           n_("Pulls the left side of the lower lip down, showing the lower teeth.")),
    'mouthLowerDownRight': (n_("Right Lower Lip Down"),
                            n_("Pulls the right side of the lower lip down, showing the lower teeth.")),
    'mouthUpperUpLeft': (n_("Left Upper Lip Up"), n_("Lifts the left side of the upper lip, showing the upper teeth.")),
    'mouthUpperUpRight': (n_("Right Upper Lip Up"),
                          n_("Lifts the right side of the upper lip, showing the upper teeth.")),
    'browDownLeft': (n_("Left Brow Down"), n_("Lowers the inner end of the left brow toward the nose.")),
    'browDownRight': (n_("Right Brow Down"), n_("Lowers the inner end of the right brow toward the nose.")),
    'browInnerUp': (n_("Inner Brows Up"), n_("Raises the inner ends of both brows, looking sad or surprised.")),
    'browOuterUpLeft': (n_("Left Outer Brow Up"), n_("Raises the outer end of the left brow.")),
    'browOuterUpRight': (n_("Right Outer Brow Up"), n_("Raises the outer end of the right brow.")),
    'cheekPuff': (n_("Cheek Puff"), n_("Puffs both cheeks out.")),
    'cheekSquintLeft': (n_("Left Cheek Raise"), n_("Raises the left cheek, pushing the lower eyelid up.")),
    'cheekSquintRight': (n_("Right Cheek Raise"), n_("Raises the right cheek, pushing the lower eyelid up.")),
    'noseSneerLeft': (n_("Left Nose Sneer"), n_("Wrinkles the left side of the nose up.")),
    'noseSneerRight': (n_("Right Nose Sneer"), n_("Wrinkles the right side of the nose up.")),
    'tongueOut': (n_("Tongue Out"), n_("Sticks the tip of the tongue out past the lips.")),
}


class DASKTOON_OT_arkit_init_placeholders(Operator):
    """Add the 52 ARKit shape keys the mesh does not have yet, empty, ready to sculpt"""
    bl_idname = "dasktoon.arkit_init_placeholders"
    bl_label = "Add ARKit 52 Placeholders"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, rpt_("Select a mesh object"))
            return {'CANCELLED'}

        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis", from_mix=False)

        sk = obj.data.shape_keys
        added = 0
        for name in ARKIT_52_ALL_NAMES:
            if name not in sk.key_blocks:
                obj.shape_key_add(name=name, from_mix=False)
                added += 1

        self.report({'INFO'}, rpt_("Added %d ARKit shape keys to %s") % (added, obj.name))
        return {'FINISHED'}


class DASKTOON_OT_arkit_solo_preview(Operator):
    """Show this ARKit shape key on the mesh: it goes to the intensity, all others to 0"""
    bl_idname = "dasktoon.arkit_solo_preview"
    bl_label = "Test ARKit Shape on Model"
    bl_options = {'REGISTER', 'UNDO'}

    shape_name: StringProperty(name="Shape Key", default="eyeBlinkLeft")
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, rpt_("Select a mesh with shape keys"))
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        for kb in sk.key_blocks:
            kb.value = 0.0

        kb = sk.key_blocks.get(self.shape_name)
        if kb:
            kb.value = self.intensity
            self.report({'INFO'}, rpt_("Showing %s") % self.shape_name)
        else:
            self.report({'WARNING'}, rpt_("Shape key %s not found: synthesize ARKit 52 first") % self.shape_name)

        return {'FINISHED'}


# =============================================================================
# Properties › Object Data › Shape Keys (UI spec 3.2)
# =============================================================================

ARKIT_GROUPS = ((n_("Eyes"), 0, 14), (n_("Jaw & Mouth"), 14, 41), (n_("Brows"), 41, 46),
                (n_("Cheeks, Nose & Tongue"), 46, 52))


class DaskExpressionPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_parent_id = "DATA_PT_shape_keys"
    bl_options = {'DEFAULT_CLOSED'}
    needs_shape_keys = True

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            return False
        return obj.data.shape_keys is not None or not cls.needs_shape_keys


def _card(layout, context, title, region, text, translate_title=True):
    """A reference card: the title, the face region and the description, wrapped to the width of the editor."""
    col = layout.box().column(align=True)
    col.label(text=iface_(title) if translate_title else title, icon='SOLO_ON', translate=False)
    col.label(text=iface_(region), icon='RESTRICT_SELECT_OFF', translate=False)
    col.separator()
    width = context.region.width if context.region is not None else 300
    scale = context.preferences.system.ui_scale or 1.0  # 0 without a window (background)
    chars = max(24, int(width / (7 * scale)))
    for line in textwrap.wrap(iface_(text), chars):
        col.label(text=line, translate=False)


class DATA_PT_dasktoon_expression_sets(DaskExpressionPanel, Panel):
    bl_label = "Expression Sets"
    needs_shape_keys = False

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_init_standard", text="VRM 0.x Set", icon='ADD').standard_type = 'VRM_0'
        row.operator("dasktoon.vrm_init_standard", text="VRM 1.0 Set", icon='ADD').standard_type = 'VRM_1'
        col = layout.column(align=True)
        col.operator("dasktoon.vrm_synthesize_arkit52", icon='SOLO_ON')
        col.operator("dasktoon.arkit_init_placeholders", icon='ADD')
        col.operator("dasktoon.vrm_convert_naming", icon='SYNTAX_OFF')
        keys = context.object.data.shape_keys
        if keys is None:
            return
        present = sum(1 for name in ARKIT_52_ALL_NAMES if name in keys.key_blocks)
        box = layout.box()
        box.label(text=iface_("ARKit 52: %d / 52 shapes") % present, translate=False,
                  icon='CHECKMARK' if present == 52 else 'INFO')
        grid = box.grid_flow(columns=2, align=True)
        for label, start, end in ARKIT_GROUPS:
            count = sum(1 for name in ARKIT_52_ALL_NAMES[start:end] if name in keys.key_blocks)
            grid.label(text="%s: %d/%d" % (iface_(label), count, end - start), translate=False)


class DATA_PT_dasktoon_expression_tools(DaskExpressionPanel, Panel):
    bl_label = "Expression Tools"

    def draw(self, _context):
        col = self.layout.column(align=True)
        col.operator("dasktoon.vrm_split_shape_key", icon='ARROW_LEFTRIGHT')
        col.operator("dasktoon.vrm_bake_expression", icon='EXPERIMENTAL')
        col.operator("dasktoon.vrm_remove_empty_shapes", icon='TRASH')


class DATA_PT_dasktoon_expression_preview(DaskExpressionPanel, Panel):
    bl_label = "Expression Preview"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "dask_guide_card_key", text="VRM")
        card = VRM_GUIDE_CARDS.get(scene.dask_guide_card_key, VRM_GUIDE_CARDS['JOY'])
        _card(layout, context, card['name'], card['region'], card['desc'])
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_guide_solo_preview", text="Test on Model", icon='VIEWZOOM').card_key = \
            scene.dask_guide_card_key
        row.operator("object.shape_key_clear", text="Clear Values", icon='LOOP_BACK')
        layout.separator()
        layout.prop(scene, "dask_arkit_selected_shape", text="ARKit")
        name = scene.dask_arkit_selected_shape
        region, text = ARKIT_GUIDE_DB.get(name, (n_("Face"), n_("An ARKit facial movement.")))
        _card(layout, context, name, region, text, translate_title=False)
        row = layout.row(align=True)
        row.operator("dasktoon.arkit_solo_preview", text="Test on Model", icon='VIEWZOOM').shape_name = name
        row.operator("object.shape_key_clear", text="Clear Values", icon='LOOP_BACK')
        layout.separator()
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_live_preview", text="Blink", icon='HIDE_OFF').preview_mode = 'AUTO_BLINK'
        row.operator("dasktoon.vrm_live_preview", text="Speech", icon='SPEAKER').preview_mode = 'AIUEO_TALK'
        row.operator("dasktoon.vrm_live_preview", text="Emotions", icon='SCENE').preview_mode = 'EMOTIONS'


class DATA_PT_dasktoon_expression_controllers(DaskExpressionPanel, Panel):
    bl_label = "Controllers"

    def draw(self, context):
        layout = self.layout
        obj = context.object
        root = getattr(obj, "dask_shape_controllers", None)
        if not root:
            return

        # 1. Viewport HUD
        if DaskHUDState.is_active:
            layout.operator("dasktoon.shape_axis_toggle_hud", text="Close Viewport HUD", icon='CANCEL')
        else:
            layout.operator("dasktoon.shape_axis_toggle_hud", text="Open Viewport HUD", icon='PLAY')

        # 2. Quick actions
        row = layout.row(align=True)
        row.operator("dasktoon.shape_axis_reset_handle", text="Reset Group", icon='LOOP_BACK')
        row.operator("dasktoon.shape_axis_reset_all", text="Reset All", icon='X')
        row.operator("dasktoon.shape_axis_keyframe_handle", text="Insert Keyframe", icon='KEY_HLT')

        # 3. Auto setup
        box = layout.box()
        box.label(text="Auto Setup", icon='AUTO')
        box.operator("dasktoon.shape_axis_auto_setup", text="Auto Detect VRM / VRoid",
                     icon='SOLO_ON').preset_type = 'VRM_STANDARD'
        grid = box.grid_flow(columns=2, align=True)
        grid.operator("dasktoon.shape_axis_auto_setup", text="VRM Emotions",
                      icon='ORIENTATION_GIMBAL').preset_type = 'VRM_EMOTIONS'
        grid.operator("dasktoon.shape_axis_auto_setup", text="AIUEO Visemes",
                      icon='OUTLINER_OB_FONT').preset_type = 'AIUEO_VISEMES'
        grid.operator("dasktoon.shape_axis_auto_setup", text="Blink Sliders",
                      icon='DRIVER_DISTANCE').preset_type = 'BLINK_HUB'
        grid.operator("dasktoon.shape_axis_auto_setup", text="Ears & Tail", icon='STRANDS').preset_type = 'EARS_TAIL'

        layout.separator()

        # 4. Controllers
        layout.label(text="Controller Groups", icon='GROUP')
        row = layout.row()
        row.template_list("DASKTOON_UL_shape_groups", "", root, "groups", root, "active_group_index", rows=4)
        col = row.column(align=True)
        col.operator("dasktoon.shape_axis_add_group", icon='ADD', text="")
        col.operator("dasktoon.shape_axis_remove_group", icon='REMOVE', text="")

        if not root.groups or root.active_group_index >= len(root.groups):
            return

        grp = root.groups[root.active_group_index]

        # 5. Active controller
        box = layout.box()
        row = box.row()
        row.prop(grp, "name", text="")
        row.prop(grp, "controller_type", text="")

        if grp.controller_type == 'SLIDER_1D':
            col = box.column(align=True)
            col.label(text=iface_("Fader Channels (%d sliders)") % len(grp.mappings), icon='DRIVER_DISTANCE',
                      translate=False)
            for mp in grp.mappings:
                if mp.shape_key_name:
                    col.prop(mp, "slider_value", slider=True, text=mp.shape_key_name, translate=False)
        else:
            col = box.column(align=True)
            col.prop(grp, "handle_x", slider=True)
            col.prop(grp, "handle_y", slider=True)

        # 6. Shape keys of the active controller
        box.separator()
        box.label(text="Shape Key Mappings", icon='SHAPEKEY_DATA')
        row = box.row()
        row.template_list("DASKTOON_UL_shape_mappings", "", grp, "mappings", grp, "active_mapping_index", rows=3)
        col = row.column(align=True)
        col.operator("dasktoon.shape_axis_add_mapping", icon='ADD', text="")
        col.operator("dasktoon.shape_axis_remove_mapping", icon='REMOVE', text="")

        if grp.mappings and 0 <= grp.active_mapping_index < len(grp.mappings):
            mp = grp.mappings[grp.active_mapping_index]
            sub = box.column(align=True)
            sub.prop_search(mp, "shape_key_name", obj.data.shape_keys, "key_blocks")
            if grp.controller_type != 'SLIDER_1D':
                coords = sub.row(align=True)
                coords.prop(mp, "target_x")
                coords.prop(mp, "target_y")
                sub.prop(mp, "radius", slider=True)

        # 7. 3D rig board
        layout.separator()
        layout.operator("dasktoon.shape_axis_generate_rig_board", icon='ARMATURE_DATA')


# =============================================================================
# Registration
# =============================================================================

classes = (
    DaskShapeMappingItem,
    DaskShapeGroupItem,
    DaskShapeControllerRoot,
    DASKTOON_OT_shape_axis_toggle_hud,
    DASKTOON_OT_shape_axis_reset_handle,
    DASKTOON_OT_shape_axis_reset_all,
    DASKTOON_OT_shape_axis_keyframe_handle,
    DASKTOON_OT_shape_axis_add_group,
    DASKTOON_OT_shape_axis_remove_group,
    DASKTOON_OT_shape_axis_add_mapping,
    DASKTOON_OT_shape_axis_remove_mapping,
    DASKTOON_OT_shape_axis_auto_setup,
    DASKTOON_OT_shape_axis_generate_rig_board,
    DASKTOON_OT_vrm_init_standard,
    DASKTOON_OT_vrm_split_shape_key,
    DASKTOON_OT_vrm_bake_expression,
    DASKTOON_OT_vrm_synthesize_arkit52,
    DASKTOON_OT_vrm_remove_empty_shapes,
    DASKTOON_OT_vrm_convert_naming,
    DASKTOON_OT_vrm_live_preview,
    DASKTOON_OT_vrm_guide_solo_preview,
    DASKTOON_OT_arkit_init_placeholders,
    DASKTOON_OT_arkit_solo_preview,
    DASKTOON_UL_shape_groups,
    DASKTOON_UL_shape_mappings,
    DATA_PT_dasktoon_expression_sets,
    DATA_PT_dasktoon_expression_tools,
    DATA_PT_dasktoon_expression_preview,
    DATA_PT_dasktoon_expression_controllers,
)


# bl_ui registers `classes`; register()/unregister() only manage the properties and the HUD.
def register():
    bpy.types.Object.dask_shape_controllers = PointerProperty(type=DaskShapeControllerRoot)
    bpy.types.Scene.dask_guide_card_key = EnumProperty(
        name="VRM Expression",
        description="Expression to look up",
        items=[(key, card['name'], card['region']) for key, card in VRM_GUIDE_CARDS.items()],
        default='JOY',
    )
    bpy.types.Scene.dask_arkit_selected_shape = EnumProperty(
        name="ARKit Shape Key",
        description="ARKit shape key to look up",
        items=[(name, name, ARKIT_GUIDE_DB.get(name, ("", ""))[1]) for name in ARKIT_52_ALL_NAMES],
        default='eyeBlinkLeft',
    )


def unregister():
    if DaskHUDState.draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DaskHUDState.draw_handler, 'WINDOW')
        DaskHUDState.draw_handler = None
    del bpy.types.Object.dask_shape_controllers
    del bpy.types.Scene.dask_guide_card_key
    del bpy.types.Scene.dask_arkit_selected_shape
