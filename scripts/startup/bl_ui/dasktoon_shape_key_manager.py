# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon ShapeKey Axis & Morph Controller Suite
Interactive 2D Viewport HUD & Multi-Purpose Blendshape Rigging System.
Supports 4 specialized visual HUD controller types:
  1. 🕹️ 2D Joystick (XY Planar Pad)
  2. ⭐ 5-Point AIUEO Star (Japanese/Anime Lip-Sync Pentagon)
  3. 🧭 Emotion Compass Wheel (360-degree Radial Expression Wheel)
  4. 🎚️ 1D Multi-Slider Hub (Multi-Channel Vertical Fader Mixer Bank, e.g. Blink Both / Left / Right)
With 1-Click VRM (VRoid / VRM 0.x / VRM 1.0), MMD, ARKit 52, Ears, Cloth & Body Auto-Detection.
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import blf
import math
import json
import os
import re
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList,
    Menu,
)
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    FloatVectorProperty,
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
    """Represents a single Shape Key mapped onto 2D coordinates or 1D multi-slider bank."""
    shape_key_name: StringProperty(
        name="Shape Key",
        description="Target mesh Shape Key name",
        default="",
    )
    # 2D Coordinates
    target_x: FloatProperty(
        name="Target X",
        description="X coordinate on the 2D plane (-1.0 to 1.0)",
        default=0.0,
        min=-1.0,
        max=1.0,
    )
    target_y: FloatProperty(
        name="Target Y",
        description="Y coordinate on the 2D plane (-1.0 to 1.0)",
        default=0.0,
        min=-1.0,
        max=1.0,
    )
    # 1D Multi-Slider Channel Value
    slider_value: FloatProperty(
        name="Slider Value",
        description="Independent channel fader value (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=_update_slider_value,
    )
    radius: FloatProperty(
        name="Radius / Influence",
        description="Radial influence falloff distance",
        default=0.90,
        min=0.01,
        max=3.0,
    )
    min_value: FloatProperty(
        name="Min Value",
        description="Minimum output value",
        default=0.0,
    )
    max_value: FloatProperty(
        name="Max Value",
        description="Maximum output value",
        default=1.0,
    )
    exponent: FloatProperty(
        name="Curve Falloff",
        description="Falloff curve exponent (1.0 = Linear, 2.0 = Smooth, 0.5 = Sharp)",
        default=1.0,
        min=0.1,
        max=5.0,
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Enable/Disable this mapping",
        default=True,
    )


def _update_handle_position(self, context):
    """Callback when Handle X or Y changes to drive shape keys in real-time."""
    self.evaluate_mappings(context)


class DaskShapeGroupItem(PropertyGroup):
    """A logical controller group (e.g. Look, Mouth, Hair Sway, Breast Physics, Cloth Wind)."""
    name: StringProperty(
        name="Group Name",
        description="Name of this controller group",
        default="New Controller",
    )
    controller_category: EnumProperty(
        name="Category",
        description="Intended animation and morph category",
        items=[
            ('FACE', "🎭 Face & Expression", "Facial blendshapes, emotions, eyes, brows"),
            ('LIP_SYNC', "👄 Lip-Sync & Visemes", "Phonemes, AIUEO, speech shapes"),
            ('BODY', "🦾 Body & Muscle Morphs", "Anatomy, muscle flex, breathing, body scale"),
            ('HAIR_EARS', "🦊 Hair, Ears & Tails", "Kemonomimi animal ears, tail wag, ponytail sway"),
            ('CLOTH', "👗 Cloth & Dynamics", "Skirt wind sway, cape folds, wrinkles"),
            ('PROPS', "⚔️ Props & Mechanics", "Weapons, mechanical transforms, character customizer"),
            ('CUSTOM', "⚙️ Custom", "General-purpose morph group"),
        ],
        default='FACE',
    )
    controller_type: EnumProperty(
        name="Type",
        description="Controller layout and interaction geometry",
        items=[
            ('JOYSTICK_2D', "🕹️ 2D Joystick (XY Pad)", "Free 2D XY planar joystick controller"),
            ('VISEME_STAR', "⭐ 5-Point AIUEO Star", "5-Point radial star pad for Japanese/Anime speech"),
            ('COMPASS_WHEEL', "🧭 Emotion Compass Wheel", "360-degree radial emotion/direction wheel"),
            ('SLIDER_1D', "🎚️ 1D Multi-Slider Hub", "Multi-channel linear fader mixer bank"),
        ],
        default='JOYSTICK_2D',
    )

    # Current Handle (Drivable Coordinates for 2D Types)
    handle_x: FloatProperty(
        name="Handle X",
        description="Horizontal driver coordinate",
        default=0.0,
        min=-1.0,
        max=1.0,
        update=_update_handle_position,
    )
    handle_y: FloatProperty(
        name="Handle Y",
        description="Vertical driver coordinate",
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
        name="Smooth RBF Blending",
        description="Smoothly blend between overlapping target influence zones",
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
    """Root data container attached to Scene or Object."""
    groups: CollectionProperty(type=DaskShapeGroupItem)
    active_group_index: IntProperty(name="Active Group Index", default=0)
    filter_category: EnumProperty(
        name="Filter Category",
        items=[
            ('ALL', "All Categories", "Show all controllers"),
            ('FACE', "Face", "Facial and Expression controllers"),
            ('LIP_SYNC', "Lip-Sync", "Visemes and phoneme controllers"),
            ('BODY', "Body", "Anatomy and body morphs"),
            ('HAIR_EARS', "Hair/Ears", "Hair, ears, tails controllers"),
            ('CLOTH', "Cloth", "Cloth and wind controllers"),
            ('PROPS', "Props", "Props and customizer morphs"),
        ],
        default='ALL',
    )
    search_query: StringProperty(
        name="Search",
        description="Filter controllers by name",
        default="",
    )

    # HUD Viewport Settings
    hud_enabled: BoolProperty(
        name="Show Viewport HUD",
        description="Display interactive 2D on-screen Joystick HUD in the 3D Viewport",
        default=False,
    )
    hud_pos_x: IntProperty(name="HUD Pos X", default=80, min=10, max=4000)
    hud_pos_y: IntProperty(name="HUD Pos Y", default=80, min=10, max=4000)
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

    type_badges = {
        'JOYSTICK_2D': "🕹️ 2D Joystick",
        'VISEME_STAR': "⭐ AIUEO Star",
        'COMPASS_WHEEL': "🧭 Emotion Wheel",
        'SLIDER_1D': f"🎚️ Multi-Slider Hub ({len(grp.mappings)} Sliders)",
    }
    badge = type_badges.get(grp.controller_type, "🕹️")
    draw_str(f"{badge}: {grp.name}", hud_x + 8, hud_y + hud_h - 18, size=11, color=(0.95, 0.96, 1.0, 1.0))
    draw_str("✕", hud_x + hud_w - 18, hud_y + hud_h - 18, size=12, color=(0.7, 0.7, 0.8, 1.0))

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

        draw_str("JOY (喜)", pad_cx - 20, pad_cy + pad_half - 12, size=9, color=(1.0, 0.85, 0.30, 0.90))
        draw_str("SORROW (哀)", pad_cx - 28, pad_cy - pad_half + 4, size=9, color=(0.40, 0.70, 1.0, 0.90))
        draw_str("ANGRY (怒)", pad_cx - pad_half + 2, pad_cy + 2, size=9, color=(1.0, 0.35, 0.35, 0.90))
        draw_str("SURPRISE (驚)", pad_cx + pad_half - 52, pad_cy + 2, size=9, color=(0.50, 0.95, 0.60, 0.90))

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
    draw_str("Reset All in Group", hud_x + hud_w / 2 - 44, btn_y + 5, size=11, color=(0.90, 0.92, 1.0, 1.0))

    bar_y = hud_y + 8
    if grp.controller_type != 'SLIDER_1D':
        draw_str(f"X: {grp.handle_x:+.3f}  Y: {grp.handle_y:+.3f}", hud_x + 12, bar_y + 16, size=10, color=(0.75, 0.80, 0.90, 0.90))
    else:
        draw_str(f"{len(grp.mappings)} Channels Active", hud_x + 12, bar_y + 16, size=10, color=(0.75, 0.80, 0.90, 0.90))

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

class DASKTOON_OT_shape_axis_toggle_hud(Operator):
    """Open interactive 2D on-screen Joystick HUD in 3D Viewport (Click & drag handles to deform character!)"""
    bl_idname = "dasktoon.shape_axis_toggle_hud"
    bl_label = "Interactive Viewport HUD"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
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
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "View3D not found")
            return {'CANCELLED'}

        obj = context.object
        if not obj or not hasattr(obj, "dask_shape_controllers"):
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        if not root.groups:
            bpy.ops.dasktoon.shape_axis_auto_setup(preset_type='VRM_STANDARD')

        root.hud_enabled = True
        DaskHUDState.is_active = True

        if DaskHUDState.draw_handler is None:
            DaskHUDState.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_shape_axis_hud_2d, (self, context), 'WINDOW', 'POST_PIXEL'
            )

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Interactive Viewport HUD Active! (Drag Sliders/Handles | Press I to Keyframe | ESC to Close)")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        DaskHUDState.is_active = False
        DaskHUDState.is_dragging = False
        DaskHUDState.active_slider_index = -1
        if DaskHUDState.draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(DaskHUDState.draw_handler, 'WINDOW')
            DaskHUDState.draw_handler = None
        if context.object and hasattr(context.object, "dask_shape_controllers"):
            context.object.dask_shape_controllers.hud_enabled = False
        if context.area:
            context.area.tag_redraw()


# =============================================================================
# Operators: Quick Actions, Auto-Setup & Rig Board
# =============================================================================

class DASKTOON_OT_shape_axis_reset_handle(Operator):
    """Reset current controller handle to center (0, 0) or zero all sliders in group"""
    bl_idname = "dasktoon.shape_axis_reset_handle"
    bl_label = "Reset Handle"
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
                self.report({'INFO'}, f"Reset {grp.name} to 0.0")
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_reset_all(Operator):
    """Reset all controller handles and zero all shape keys"""
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

        self.report({'INFO'}, "All shape keys and controllers reset to 0.0!")
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_keyframe_handle(Operator):
    """Insert Keyframe for the active controller handle position and shape keys"""
    bl_idname = "dasktoon.shape_axis_keyframe_handle"
    bl_label = "Keyframe Handle"
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

                self.report({'INFO'}, f"Keyframed {grp.name} at frame {context.scene.frame_current}")
        return {'FINISHED'}


class DASKTOON_OT_shape_axis_add_group(Operator):
    """Add a new Shape Key controller group"""
    bl_idname = "dasktoon.shape_axis_add_group"
    bl_label = "Add Controller"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="New Controller")
    category: EnumProperty(
        name="Category",
        items=[
            ('FACE', "Face", ""),
            ('LIP_SYNC', "Lip-Sync", ""),
            ('BODY', "Body", ""),
            ('HAIR_EARS', "Hair/Ears", ""),
            ('CLOTH', "Cloth", ""),
            ('PROPS', "Props", ""),
        ],
        default='FACE',
    )
    ctrl_type: EnumProperty(
        name="Type",
        items=[
            ('JOYSTICK_2D', "2D Joystick", ""),
            ('VISEME_STAR', "5-Point Star", ""),
            ('COMPASS_WHEEL', "Compass Wheel", ""),
            ('SLIDER_1D', "1D Multi-Slider Hub", ""),
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
    """Remove the active controller group"""
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
    """Add a shape key target mapping to the active controller"""
    bl_idname = "dasktoon.shape_axis_add_mapping"
    bl_label = "Add Mapping"
    bl_options = {'REGISTER', 'UNDO'}

    shape_name: StringProperty(name="Shape Key Name", default="")
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
    """Remove active shape key target mapping"""
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
    """Automatically detect character Blendshapes (VRM 0.x/1.0, MMD, ARKit 52, Ears, Cloth, Body) and generate optimal HUD controllers"""
    bl_idname = "dasktoon.shape_axis_auto_setup"
    bl_label = "1-Click Auto Setup"
    bl_options = {'REGISTER', 'UNDO'}

    preset_type: EnumProperty(
        name="Auto Preset",
        items=[
            ('VRM_STANDARD', "🌟 Auto Detect VRM / VRoid Suite (Primary)", "1-Click Full Setup for VRM 0.x, VRM 1.0 & VRoid blendshapes"),
            ('ALL_SUITE', "✨ Complete Multi-Purpose Suite", "Auto setup Face, Visemes, Ears, Hair, Body & Cloth"),
            ('VRM_EMOTIONS', "🧭 VRM Emotion Compass Wheel", "Setup 360° Joy/Angry/Sad/Surprised emotion wheel"),
            ('AIUEO_VISEMES', "⭐ AIUEO 5-Point Star Pad", "Setup 5-point Japanese/Anime viseme pad"),
            ('BLINK_HUB', "🎚️ 3-Slider Eye Blink Hub", "Setup multi-slider 1D hub for Blink Both, Left & Right"),
            ('ARKIT_52', "📱 Apple ARKit 52 Face Suite", "Setup full 52 ARKit face tracking blendshapes"),
            ('EARS_TAIL', "🦊 Kemonomimi Animal Ears & Tail", "Setup ear wag & tail physics"),
            ('BODY_MUSCLE', "🦾 Body & Muscle Morphs", "Setup Breathing, Muscle Flex & Morphs"),
            ('CLOTH_WIND', "👗 Cloth & Wind Sway", "Setup 4-way skirt/cape wind sway"),
        ],
        default='VRM_STANDARD',
    )

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Selected object has no Shape Keys!")
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
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
        self.report({'INFO'}, f"Auto Setup completed! Generated {len(root.groups)} controllers for {self.preset_type}.")
        return {'FINISHED'}


# =============================================================================
# 3D Viewport Face Rig Board Generator (Drivers & Bone/Empty Controls)
# =============================================================================

class DASKTOON_OT_shape_axis_generate_rig_board(Operator):
    """Generate an interactive 3D Rig Board in Viewport with Bone/Empty handles driven by Blender Drivers"""
    bl_idname = "dasktoon.shape_axis_generate_rig_board"
    bl_label = "Generate 3D Rig Board"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
            return {'CANCELLED'}

        root = obj.dask_shape_controllers
        if not root.groups:
            self.report({'WARNING'}, "No controller groups to generate! Run Auto-Setup first.")
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

        self.report({'INFO'}, f"Generated 3D Rig Board with {len(root.groups)} controllers in collection '{col_name}'!")
        return {'FINISHED'}


# =============================================================================
# UI Panels: N-Panel Sidebar & Object Data Properties
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
        layout.label(text=f"({len(grp.mappings)} shapes)")


class DASKTOON_UL_shape_mappings(UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        mp = item
        layout.prop(mp, "enabled", text="")
        layout.label(text=mp.shape_key_name or "(Empty)", icon='SHAPEKEY_DATA')
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text=f"X:{mp.target_x:.2f} Y:{mp.target_y:.2f}")


class DASKTOON_PT_shape_axis_panel(Panel):
    """Master N-Panel in 3D Viewport under 'Shape Axis' and 'DaskToon' tabs"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Shape Axis"
    bl_label = "ShapeKey Axis Controller Suite"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.data and obj.data.shape_keys

    def draw(self, context):
        layout = self.layout
        obj = context.object
        root = getattr(obj, "dask_shape_controllers", None)
        if not root:
            return

        # 1. Big Interactive Viewport HUD Launcher
        box_hud = layout.box()
        b_hud_col = box_hud.column(align=True)
        btn_text = "🕹️ Close Viewport HUD" if DaskHUDState.is_active else "🕹️ Open Interactive Viewport HUD"
        btn_icon = 'CANCEL' if DaskHUDState.is_active else 'PLAY'
        b_hud_col.operator("dasktoon.shape_axis_toggle_hud", text=btn_text, icon=btn_icon)

        # 2. Quick Actions Toolbar
        row = layout.row(align=True)
        row.operator("dasktoon.shape_axis_reset_handle", text="Reset Group", icon='LOOP_BACK')
        row.operator("dasktoon.shape_axis_reset_all", text="Reset All", icon='X')
        row.operator("dasktoon.shape_axis_keyframe_handle", text="Key [I]", icon='KEY_HLT')

        # 3. 1-Click Multi-Purpose & VRM Auto Setup Wizard
        box = layout.box()
        box.label(text="1-Click Auto Setup Presets", icon='AUTO')
        # Primary VRM Button
        vrm_op = box.operator("dasktoon.shape_axis_auto_setup", text="🌟 Auto Detect VRM / VRoid Suite", icon='SOLO_ON')
        vrm_op.preset_type = 'VRM_STANDARD'

        grid = box.grid_flow(columns=2, align=True)
        g1 = grid.operator("dasktoon.shape_axis_auto_setup", text="🧭 VRM Emotions", icon='ORIENTATION_GIMBAL')
        g1.preset_type = 'VRM_EMOTIONS'
        g2 = grid.operator("dasktoon.shape_axis_auto_setup", text="⭐ AIUEO Star", icon='OUTLINER_OB_FONT')
        g2.preset_type = 'AIUEO_VISEMES'
        g3 = grid.operator("dasktoon.shape_axis_auto_setup", text="🎚️ 3-Slider Blink", icon='DRIVER_DISTANCE')
        g3.preset_type = 'BLINK_HUB'
        g4 = grid.operator("dasktoon.shape_axis_auto_setup", text="🦊 Ears & Tail", icon='STRANDS')
        g4.preset_type = 'EARS_TAIL'

        layout.separator()

        # 4. Groups List
        row = layout.row()
        row.label(text="Controller Groups:", icon='GROUP')
        row.prop(root, "filter_category", text="")

        row = layout.row()
        row.template_list("DASKTOON_UL_shape_groups", "", root, "groups", root, "active_group_index", rows=4)

        col = row.column(align=True)
        col.operator("dasktoon.shape_axis_add_group", icon='ADD', text="")
        col.operator("dasktoon.shape_axis_remove_group", icon='REMOVE', text="")

        if not root.groups or root.active_group_index >= len(root.groups):
            return

        grp = root.groups[root.active_group_index]

        # 5. Active Group Controls & Sliders
        box = layout.box()
        b_row = box.row()
        b_row.prop(grp, "name", text="Group")
        b_row.prop(grp, "controller_type", text="")

        if grp.controller_type == 'SLIDER_1D':
            # Multi-Slider Faders in N-Panel
            col = box.column(align=True)
            col.label(text=f"Fader Channels ({len(grp.mappings)} Sliders):", icon='DRIVER_DISTANCE')
            for mp in grp.mappings:
                if mp.shape_key_name:
                    row = col.row(align=True)
                    row.prop(mp, "slider_value", slider=True, text=mp.shape_key_name)
                    # Quick zero button for each channel
                    zero_op = row.operator("dasktoon.shape_axis_reset_handle", text="", icon='X')
        else:
            col = box.column(align=True)
            col.prop(grp, "handle_x", slider=True, text="X (Horizontal)")
            col.prop(grp, "handle_y", slider=True, text="Y (Vertical)")

        # 6. Mappings for this Group
        box.separator()
        b_row = box.row()
        b_row.label(text="Shape Key Mappings:", icon='SHAPEKEY_DATA')

        b_row = box.row()
        b_row.template_list("DASKTOON_UL_shape_mappings", "", grp, "mappings", grp, "active_mapping_index", rows=3)
        b_col = b_row.column(align=True)
        b_col.operator("dasktoon.shape_axis_add_mapping", icon='ADD', text="")
        b_col.operator("dasktoon.shape_axis_remove_mapping", icon='REMOVE', text="")

        if grp.mappings and 0 <= grp.active_mapping_index < len(grp.mappings):
            mp = grp.mappings[grp.active_mapping_index]
            sub = box.column(align=True)
            sub.prop_search(mp, "shape_key_name", obj.data.shape_keys, "key_blocks", text="Shape")
            if grp.controller_type != 'SLIDER_1D':
                coords = sub.row(align=True)
                coords.prop(mp, "target_x", text="Target X")
                coords.prop(mp, "target_y", text="Target Y")
                sub.prop(mp, "radius", text="Influence Radius", slider=True)

        # 7. 3D Rig Board Generator
        layout.separator()
        layout.operator("dasktoon.shape_axis_generate_rig_board", text="🎮 Generate 3D Rig Board", icon='ARMATURE_DATA')


# =============================================================================
# VRM ShapeKey Toolset (ARKit & VRM Standard Blendshape Suite)
# =============================================================================

class DASKTOON_OT_vrm_init_standard(Operator):
    """Initialize or generate missing VRM 0.x / VRM 1.0 standard blendshapes"""
    bl_idname = "dasktoon.vrm_init_standard"
    bl_label = "Initialize VRM Standard"
    bl_options = {'REGISTER', 'UNDO'}

    standard_type: EnumProperty(
        name="VRM Version",
        items=[
            ('VRM_0', "VRM 0.x Standard (joy, angry, a, i, u, blink...)", "18 VRM 0.x blendshapes"),
            ('VRM_1', "VRM 1.0 Standard (happy, sad, aa, ih, blinkLeft...)", "18 VRM 1.0 blendshapes"),
        ],
        default='VRM_0',
    )

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a Mesh Object!")
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

        self.report({'INFO'}, f"VRM Initializer: Added {added} missing shape keys for {self.standard_type}.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_split_shape_key(Operator):
    """Split a symmetrical Shape Key into Left (_L) and Right (_R) with seamless X-axis falloff"""
    bl_idname = "dasktoon.vrm_split_shape_key"
    bl_label = "Split Shape Key (L / R)"
    bl_options = {'REGISTER', 'UNDO'}

    source_shape: StringProperty(name="Source Shape Key", default="")
    falloff: FloatProperty(name="Center Seam Falloff", default=0.015, min=0.0, max=0.2, description="Smooth blending radius across the center line X=0")
    suffix_style: EnumProperty(
        name="Suffix Style",
        items=[
            ('_L_R', "_L / _R (Standard)", "e.g. blink_L, blink_R"),
            ('Left_Right', "Left / Right (CamelCase)", "e.g. blinkLeft, blinkRight"),
            ('_l_r', "_l / _r (Lowercase)", "e.g. blink_l, blink_r"),
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
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        if not self.source_shape or self.source_shape not in sk.key_blocks:
            self.report({'ERROR'}, f"Source Shape Key '{self.source_shape}' not found!")
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

        self.report({'INFO'}, f"Split '{self.source_shape}' -> '{l_name}' and '{r_name}' with falloff {self.falloff:.3f}m.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_mirror_shape_key(Operator):
    """Mirror a Shape Key across the X-axis (Left to Right or Right to Left)"""
    bl_idname = "dasktoon.vrm_mirror_shape_key"
    bl_label = "Mirror Shape Key (X-Axis)"
    bl_options = {'REGISTER', 'UNDO'}

    source_shape: StringProperty(name="Source Shape Key", default="")
    target_shape: StringProperty(name="Target Name (Empty for Auto)", default="")

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
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        if not self.source_shape or self.source_shape not in sk.key_blocks:
            self.report({'ERROR'}, f"Shape Key '{self.source_shape}' not found!")
            return {'CANCELLED'}

        basis_kb = sk.key_blocks[0]
        src_kb = sk.key_blocks[self.source_shape]

        target_name = self.target_shape
        if not target_name:
            if "_L" in self.source_shape: target_name = self.source_shape.replace("_L", "_R")
            elif "_R" in self.source_shape: target_name = self.source_shape.replace("_R", "_L")
            elif "Left" in self.source_shape: target_name = self.source_shape.replace("Left", "Right")
            elif "Right" in self.source_shape: target_name = self.source_shape.replace("Right", "Left")
            elif "_l" in self.source_shape: target_name = self.source_shape.replace("_l", "_r")
            elif "_r" in self.source_shape: target_name = self.source_shape.replace("_r", "_l")
            else: target_name = f"{self.source_shape}_Mirrored"

        target_kb = sk.key_blocks.get(target_name) or obj.shape_key_add(name=target_name, from_mix=False)

        # Build KD-Tree for spatial symmetry matching
        import mathutils
        kd = mathutils.kdtree.KDTree(len(obj.data.vertices))
        for i, v in enumerate(obj.data.vertices):
            kd.insert(v.co, i)
        kd.balance()

        for i, v in enumerate(obj.data.vertices):
            mirrored_pos = mathutils.Vector((-v.co.x, v.co.y, v.co.z))
            co, match_idx, dist = kd.find(mirrored_pos)

            if dist < 0.01:
                # Matched symmetric vertex
                src_delta = src_kb.data[match_idx].co - basis_kb.data[match_idx].co
                mirrored_delta = mathutils.Vector((-src_delta.x, src_delta.y, src_delta.z))
                target_kb.data[i].co = basis_kb.data[i].co + mirrored_delta
            else:
                target_kb.data[i].co = basis_kb.data[i].co

        self.report({'INFO'}, f"Mirrored '{self.source_shape}' -> '{target_name}'.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_bake_expression(Operator):
    """Bake current mixed Shape Key values into a new single Shape Key"""
    bl_idname = "dasktoon.vrm_bake_expression"
    bl_label = "Bake Current Expression to Shape Key"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(name="New Shape Key Name", default="custom_expression_baked")
    reset_after: BoolProperty(name="Reset Sliders After Bake", default=True)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
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

        self.report({'INFO'}, f"Baked {active_count} active shape keys into '{self.new_name}'.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_synthesize_arkit52(Operator):
    """Synthesize complete Apple ARKit 52 Face Tracking blendshapes from existing VRM/VRoid shape keys"""
    bl_idname = "dasktoon.vrm_synthesize_arkit52"
    bl_label = "Synthesize ARKit 52 Suite"
    bl_options = {'REGISTER', 'UNDO'}

    overwrite_existing: BoolProperty(name="Overwrite Existing ARKit Keys", default=False)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
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

        self.report({'INFO'}, f"Generated {generated_count} / 52 Apple ARKit blendshapes from VRM sources!")
        return {'FINISHED'}


class DASKTOON_OT_vrm_zero_all_shapes(Operator):
    """Reset all Shape Keys on the active mesh to 0.0"""
    bl_idname = "dasktoon.vrm_zero_all_shapes"
    bl_label = "Zero All Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            return {'CANCELLED'}
        for kb in obj.data.shape_keys.key_blocks:
            kb.value = 0.0
        self.report({'INFO'}, "Reset all Shape Keys to 0.0.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_remove_empty_shapes(Operator):
    """Clean up and remove shape keys with zero vertex displacement"""
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

        self.report({'INFO'}, f"Removed {len(to_remove)} empty/unused shape keys.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_convert_naming(Operator):
    """Convert Shape Key naming conventions (VRM 0.x <-> VRM 1.0 <-> VRoid <-> MMD)"""
    bl_idname = "dasktoon.vrm_convert_naming"
    bl_label = "Convert Naming Convention"
    bl_options = {'REGISTER', 'UNDO'}

    conversion_mode: EnumProperty(
        name="Conversion Standard",
        items=[
            ('VROID_TO_VRM0', "VRoid (Fcl_...) -> VRM 0.x (joy, blink...)", "Convert VRoid names to VRM 0.x standard"),
            ('VRM0_TO_VRM1', "VRM 0.x -> VRM 1.0 (happy, blinkLeft...)", "Convert VRM 0.x to VRM 1.0 standard"),
            ('VRM1_TO_VRM0', "VRM 1.0 -> VRM 0.x (joy, blink_l...)", "Convert VRM 1.0 to VRM 0.x standard"),
        ],
        default='VROID_TO_VRM0',
    )

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

        self.report({'INFO'}, f"Renamed {renamed} shape keys to {self.conversion_mode}.")
        return {'FINISHED'}


class DASKTOON_OT_vrm_live_preview(Operator):
    """Live interactive Auto-Blink and Lip-Sync previewer in 3D Viewport"""
    bl_idname = "dasktoon.vrm_live_preview"
    bl_label = "Live Expression Previewer"
    bl_options = {'REGISTER'}

    _timer = None
    _step = 0.0
    preview_mode: EnumProperty(
        name="Preview Mode",
        items=[
            ('AUTO_BLINK', "👁️ Auto Blink Cycle", "Natural random eye blink test"),
            ('AIUEO_TALK', "🗣️ AIUEO Lip-Sync Loop", "Continuous vowel speech cycle"),
            ('EMOTIONS', "🎭 Emotion Transition Loop", "Smooth emotion shifting"),
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
        self.report({'INFO'}, f"Live Preview Started: {self.preview_mode}. Press ESC or Right Click to stop.")
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
        self.report({'INFO'}, "Live Preview Stopped.")


# =============================================================================
# VRM Visual Reference Guide Database & Solo Preview
# =============================================================================

VRM_GUIDE_CARDS = {
    'JOY': {
        'name': "😊 Joy / Happy (Nụ cười tươi)",
        'region': "👄 Khóe Miệng + 👁️ Mắt",
        'desc': "Nụ cười tươi tắn. Khóe miệng kéo dẹt sang hai bên và chếch lên trên, mí mắt dưới đẩy nhẹ tạo mắt cười hình bán nguyệt.",
        'targets': ['joy', 'happy', 'Fcl_ALL_Joy', 'mouthSmileLeft', 'mouthSmileRight'],
    },
    'ANGRY': {
        'name': "😠 Angry (Tức giận)",
        'region': "🤨 Lông Mày + 👄 Khóe Môi",
        'desc': "Biểu cảm tức giận. Hai đầu lông mày hạ thấp và ép sát vào sống mũi, mí mắt nheo gắt, khóe môi chúc xuống.",
        'targets': ['angry', 'Fcl_ALL_Angry', 'browDownLeft', 'browDownRight', 'mouthFrownLeft', 'mouthFrownRight'],
    },
    'SORROW': {
        'name': "😢 Sorrow / Sad (Buồn bã)",
        'region': "🤨 Lông Mày + 👄 Môi Dưới",
        'desc': "Biểu cảm buồn bã / đau lòng. Hai đầu lông mày nâng cao chếch chữ bát (八), khóe miệng trễ xuống, ánh mắt rũ.",
        'targets': ['sorrow', 'sad', 'Fcl_ALL_Sorrow', 'browInnerUp', 'mouthFrownLeft', 'mouthFrownRight'],
    },
    'SURPRISED': {
        'name': "😲 Surprised (Kinh ngạc)",
        'region': "👁️ Mắt Mở To + 👄 Miệng Chữ O",
        'desc': "Biểu cảm sửng sốt / ngạc nhiên. Hai mắt mở to hết cỡ, đồng tử co nhẹ, lông mày nhướng cao, miệng há hình chữ O.",
        'targets': ['surprised', 'Fcl_ALL_Surprised', 'eyeWideLeft', 'eyeWideRight', 'browInnerUp', 'jawOpen'],
    },
    'RELAXED': {
        'name': "😌 Relaxed / Fun (Thư thái)",
        'region': "👁️ Mắt Cong Nhắm + 👄 Nụ Cười Nhẹ",
        'desc': "Biểu cảm an tâm / dễ chịu. Hai mắt nhắm cong hình chữ U (^ ^), khóe miệng mỉm cười nhẹ nhàng.",
        'targets': ['fun', 'relaxed', 'Fcl_ALL_Relaxed', 'mouthDimpleLeft', 'mouthDimpleRight'],
    },
    'VISEME_A': {
        'name': "🗣️ Viseme A (Khẩu hình A)",
        'region': "👄 Cằm Hạ Thấp (Há Miệng Dọc)",
        'desc': "Khẩu hình phát âm 'A'. Cằm hạ thấp xuống, miệng mở dọc tự nhiên để lộ răng cửa trên và lưỡi.",
        'targets': ['a', 'aa', 'Fcl_MTH_A', 'jawOpen'],
    },
    'VISEME_I': {
        'name': "🗣️ Viseme I (Khẩu hình I)",
        'region': "👄 Kéo Ngang Môi (Cười Răng)",
        'desc': "Khẩu hình phát âm 'I'. Hai khóe miệng kéo căng sang hai bên theo chiều ngang, để lộ hai hàm răng.",
        'targets': ['i', 'ih', 'Fcl_MTH_I', 'mouthStretchLeft', 'mouthStretchRight'],
    },
    'VISEME_U': {
        'name': "🗣️ Viseme U (Khẩu hình U)",
        'region': "👄 Chu Môi Nhỏ",
        'desc': "Khẩu hình phát âm 'U'. Môi trên và môi dưới chu tròn nhỏ về phía trước, hai má hơi hóp lại.",
        'targets': ['u', 'ou', 'Fcl_MTH_U', 'mouthFunnel', 'mouthPucker'],
    },
    'VISEME_E': {
        'name': "🗣️ Viseme E (Khẩu hình E)",
        'region': "👄 Miệng Mở Vừa Phải",
        'desc': "Khẩu hình phát âm 'E'. Khóe miệng mở rộng vừa phải, môi trên hơi cong lên tạo hình vòm cầu.",
        'targets': ['e', 'ee', 'Fcl_MTH_E', 'mouthSmileLeft', 'mouthSmileRight'],
    },
    'VISEME_O': {
        'name': "🗣️ Viseme O (Khẩu hình O)",
        'region': "👄 Miệng Tròn Vo",
        'desc': "Khẩu hình phát âm 'O'. Miệng mở tròn vo như quả trứng, môi hơi chìa ra phía trước.",
        'targets': ['o', 'oh', 'Fcl_MTH_O', 'mouthPucker', 'jawOpen'],
    },
    'BLINK_BOTH': {
        'name': "👁️ Eye Blink (Chớp cả hai mắt)",
        'region': "👁️ Mí Mắt Trên",
        'desc': "Chớp mắt hoàn toàn. Mí mắt trên hạ sát hoàn toàn xuống mí dưới, lông mi cụp tự nhiên.",
        'targets': ['blink', 'Fcl_EYE_Close', 'eyeBlinkLeft', 'eyeBlinkRight'],
    },
    'WINK_L': {
        'name': "😉 Wink Left (Nháy mắt Trái)",
        'region': "👁️ Mắt Bên Trái",
        'desc': "Chỉ có mắt bên Trái nhắm lại tạo dáng nháy mắt tinh nghịch, mắt bên Phải vẫn mở to.",
        'targets': ['blink_l', 'blinkLeft', 'Fcl_EYE_Close_L', 'eyeBlinkLeft'],
    },
    'WINK_R': {
        'name': "😉 Wink Right (Nháy mắt Phải)",
        'region': "👁️ Mắt Bên Phải",
        'desc': "Chỉ có mắt bên Phải nhắm lại, mắt bên Trái vẫn mở to bình thường.",
        'targets': ['blink_r', 'blinkRight', 'Fcl_EYE_Close_R', 'eyeBlinkRight'],
    },
    'CHEEK_PUFF': {
        'name': "🐡 Cheek Puff (Phồng má)",
        'region': "😼 Hai Bên Má",
        'desc': "Phồng căng hai bên má ra ngoài như đang ngậm hơi hoặc hờn dỗi Anime.",
        'targets': ['cheekPuff', 'Fcl_MTH_U'],
    },
}

class DASKTOON_OT_vrm_guide_solo_preview(Operator):
    """Solo preview the selected reference guide expression on the character model"""
    bl_idname = "dasktoon.vrm_guide_solo_preview"
    bl_label = "Solo Preview on Model"
    bl_options = {'REGISTER', 'UNDO'}

    card_key: StringProperty(name="Card Key", default="JOY")
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
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
            self.report({'INFO'}, f"Previewing '{card['name']}': Active shapes -> {', '.join(applied)}")
        else:
            self.report({'WARNING'}, f"No matching Shape Keys found on model for '{card['name']}'. Run VRM Initializer first!")

        return {'FINISHED'}


# =============================================================================
# VRM ShapeKey Toolset Dedicated N-Panel (Tab: "Shape Axis")
# =============================================================================

class DASKTOON_PT_vrm_toolset_panel(Panel):
    """Dedicated VRM ShapeKey Toolset Panel in 3D Viewport"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Shape Axis"
    bl_label = "VRM ShapeKey Toolset"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        sk = obj.data.shape_keys if obj and obj.data else None
        scene = context.scene

        # ── 0. Visual Reference Guide & Cards ──
        box_guide = layout.box()
        box_guide.label(text="📖 VRM Expression Guide Cards", icon='BOOKMARKS')
        
        if not hasattr(scene, "dask_guide_card_key"):
            scene.dask_guide_card_key = "JOY"

        box_guide.prop(scene, "dask_guide_card_key", text="Card")
        selected_key = scene.dask_guide_card_key
        card = VRM_GUIDE_CARDS.get(selected_key, VRM_GUIDE_CARDS['JOY'])

        card_box = box_guide.box()
        col = card_box.column(align=True)
        col.label(text=f"🎯 {card['name']}", icon='SOLO_ON')
        col.label(text=f"📍 {card['region']}", icon='RESTRICT_SELECT_OFF')
        col.separator()
        col.label(text=card['desc'])
        col.separator()

        row_btn = col.row(align=True)
        op_solo = row_btn.operator("dasktoon.vrm_guide_solo_preview", text="🔍 Solo Test on Model", icon='VIEWZOOM')
        op_solo.card_key = selected_key
        row_btn.operator("dasktoon.vrm_zero_all_shapes", text="Reset", icon='LOOP_BACK')

        # ── 1. VRM Standard Initializer ──
        box_init = layout.box()
        box_init.label(text="VRM Standard Initializer", icon='OUTLINER_OB_ARMATURE')
        row = box_init.row(align=True)
        op_vrm0 = row.operator("dasktoon.vrm_init_standard", text="🌟 VRM 0.x Suite", icon='ADD')
        op_vrm0.standard_type = 'VRM_0'
        op_vrm1 = row.operator("dasktoon.vrm_init_standard", text="✨ VRM 1.0 Suite", icon='FILE_REFRESH')
        op_vrm1.standard_type = 'VRM_1'

        if not sk:
            box_init.label(text="(Object has no Shape Keys yet)", icon='INFO')
            return

        # ── 2. Shape Key Split & Mirror Studio ──
        box_split = layout.box()
        box_split.label(text="Split & Mirror Studio", icon='MOD_MIRROR')
        row = box_split.row(align=True)
        row.operator("dasktoon.vrm_split_shape_key", text="✂️ Split Active (L / R)", icon='ARROW_LEFTRIGHT')
        row.operator("dasktoon.vrm_mirror_shape_key", text="🪞 Mirror (X-Axis)", icon='MOD_MIRROR')

        # ── 3. Expression Mixer & Baker ──
        box_mix = layout.box()
        box_mix.label(text="Expression Mixer & Bake", icon='COLORSET_01_VEC')
        box_mix.operator("dasktoon.vrm_bake_expression", text="🧪 Bake Current Expression to New Key", icon='EXPERIMENTAL')

        # ── 4. Clean-Up & Management Utilities ──
        box_util = layout.box()
        box_util.label(text="Clean-Up & Utilities", icon='TOOL_SETTINGS')
        col = box_util.column(align=True)
        col.operator("dasktoon.vrm_zero_all_shapes", text="Zero All Shape Keys", icon='LOOP_BACK')
        col.operator("dasktoon.vrm_remove_empty_shapes", text="Remove Empty / Zero-Delta Keys", icon='TRASH')
        col.operator("dasktoon.vrm_convert_naming", text="Convert Naming Standard...", icon='SYNTAX_OFF')

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
    # Mouth (24)
    'mouthClose', 'mouthFunnel', 'mouthPucker', 'mouthLeft', 'mouthRight',
    'mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft', 'mouthFrownRight',
    'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft', 'mouthStretchRight',
    'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower', 'mouthShrugUpper',
    'mouthPressLeft', 'mouthPressRight', 'mouthLowerDownLeft', 'mouthLowerDownRight',
    'mouthUpperUpLeft', 'mouthUpperUpRight',
    # Brows (5)
    'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
    # Cheeks, Nose & Tongue (5)
    'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft', 'noseSneerRight', 'tongueOut',
]

ARKIT_GUIDE_DB = {
    'eyeBlinkLeft': ("👁️ Mí Mắt Trái", "Nhắm mí mắt trên bên Trái hoàn toàn chạm mí dưới."),
    'eyeBlinkRight': ("👁️ Mí Mắt Phải", "Nhắm mí mắt trên bên Phải hoàn toàn chạm mí dưới."),
    'eyeLookUpLeft': ("👀 Đồng Tử Trái", "Đồng tử mắt trái liếc lên trên."),
    'eyeLookUpRight': ("👀 Đồng Tử Phải", "Đồng tử mắt phải liếc lên trên."),
    'eyeLookDownLeft': ("👀 Đồng Tử Trái", "Đồng tử mắt trái liếc cụp xuống dưới."),
    'eyeLookDownRight': ("👀 Đồng Tử Phải", "Đồng tử mắt phải liếc cụp xuống dưới."),
    'eyeLookInLeft': ("👀 Đồng Tử Trái", "Đồng tử mắt trái liếc vào trong sống mũi."),
    'eyeLookInRight': ("👀 Đồng Tử Phải", "Đồng tử mắt phải liếc vào trong sống mũi."),
    'eyeLookOutLeft': ("👀 Đồng Tử Trái", "Đồng tử mắt trái liếc ra ngoài thái dương."),
    'eyeLookOutRight': ("👀 Đồng Tử Phải", "Đồng tử mắt phải liếc ra ngoài thái dương."),
    'eyeSquintLeft': ("👁️ Nheo Mắt Trái", "Mí dưới mắt trái đẩy nhẹ lên trên như đang nheo mắt cười."),
    'eyeSquintRight': ("👁️ Nheo Mắt Phải", "Mí dưới mắt phải đẩy nhẹ lên trên như đang nheo mắt cười."),
    'eyeWideLeft': ("👁️ Trợn Mắt Trái", "Mí mắt trên bên trái mở to căng hết cỡ."),
    'eyeWideRight': ("👁️ Trợn Mắt Phải", "Mí mắt trên bên phải mở to căng hết cỡ."),
    'jawOpen': ("👄 Mở Cằm Dọc", "Cằm hạ thấp xuống phía dưới để há miệng lớn."),
    'jawForward': ("👄 Đưa Cằm Ra Trước", "Xương cằm dưới đẩy tịnh tiến ra phía trước."),
    'jawLeft': ("👄 Lệch Cằm Trái", "Cằm dưới trượt sang bên Trái."),
    'jawRight': ("👄 Lệch Cằm Phải", "Cằm dưới trượt sang bên Phải."),
    'mouthClose': ("👄 Khép Môi", "Hai môi ép chặt vào nhau khi cằm đang há."),
    'mouthFunnel': ("👄 Mở Phễu", "Môi mở tròn hình phễu như đang nói chữ 'U' to."),
    'mouthPucker': ("👄 Chu Môi", "Hai môi chu tròn nhỏ nhô về phía trước (chu mỏ/hôn)."),
    'mouthLeft': ("👄 Kéo Mép Trái", "Toàn bộ vòm môi trượt sang bên Trái."),
    'mouthRight': ("👄 Kéo Mép Phải", "Toàn bộ vòm môi trượt sang bên Phải."),
    'mouthSmileLeft': ("😊 Cười Mép Trái", "Khóe môi trái kéo sang bên và chếch lên trên."),
    'mouthSmileRight': ("😊 Cười Mép Phải", "Khóe môi phải kéo sang bên và chếch lên trên."),
    'mouthFrownLeft': ("😢 Mếu Mép Trái", "Khóe môi trái kéo chúc xuống dưới (mếu/buồn)."),
    'mouthFrownRight': ("😢 Mếu Mép Phải", "Khóe môi phải kéo chúc xuống dưới (mếu/buồn)."),
    'mouthDimpleLeft': ("😊 Lúm Đồng Tiền Trái", "Khóe môi trái kéo lùi nhẹ vào má tạo vết lúm."),
    'mouthDimpleRight': ("😊 Lúm Đồng Tiền Phải", "Khóe môi phải kéo lùi nhẹ vào má tạo vết lúm."),
    'mouthStretchLeft': ("👄 Kéo Căng Mép Trái", "Khóe miệng trái kéo căng ngang sang bên (phát âm 'I')."),
    'mouthStretchRight': ("👄 Kéo Căng Mép Phải", "Khóe miệng phải kéo căng ngang sang bên (phát âm 'I')."),
    'mouthRollLower': ("👄 Cuộn Môi Dưới", "Môi dưới cuộn tròn vào trong mép răng."),
    'mouthRollUpper': ("👄 Cuộn Môi Trên", "Môi trên cuộn tròn vào trong mép răng."),
    'mouthShrugLower': ("👄 Đẩy Môi Dưới", "Môi dưới đẩy nhếch lên trên."),
    'mouthShrugUpper': ("👄 Đẩy Môi Trên", "Môi trên nhếch nhẹ lên trên."),
    'mouthPressLeft': ("👄 Ép Mép Trái", "Môi trái ép dẹt chặt vào nhau."),
    'mouthPressRight': ("👄 Ép Mép Phải", "Môi phải ép dẹt chặt vào nhau."),
    'mouthLowerDownLeft': ("👄 Hạ Môi Dưới Trái", "Phần môi dưới bên trái kéo hạ xuống để lộ răng dưới."),
    'mouthLowerDownRight': ("👄 Hạ Môi Dưới Phải", "Phần môi dưới bên phải kéo hạ xuống để lộ răng dưới."),
    'mouthUpperUpLeft': ("👄 Nâng Môi Trên Trái", "Phần môi trên bên trái kéo nâng lên để lộ răng trên."),
    'mouthUpperUpRight': ("👄 Nâng Môi Trên Phải", "Phần môi trên bên phải kéo nâng lên để lộ răng trên."),
    'browDownLeft': ("🤨 Hạ Mày Trái", "Đầu lông mày trái hạ thấp và ép sát vào sống mũi."),
    'browDownRight': ("🤨 Hạ Mày Phải", "Đầu lông mày phải hạ thấp và ép sát vào sống mũi."),
    'browInnerUp': ("🤨 Nhướng Lông Mày Giữa", "Hai đầu lông mày giữa nhướng cao tạo vẻ buồn bã/ngạc nhiên."),
    'browOuterUpLeft': ("🤨 Nhướng Đuôi Mày Trái", "Đuôi ngoài lông mày trái nâng cao lên trên."),
    'browOuterUpRight': ("🤨 Nhướng Đuôi Mày Phải", "Đuôi ngoài lông mày phải nâng cao lên trên."),
    'cheekPuff': ("🐡 Phồng Hai Má", "Hai bên má phồng căng tròn ra ngoài."),
    'cheekSquintLeft': ("😼 Nâng Má Trái", "Khối cơ má trái nâng cao đẩy mí mắt dưới lên."),
    'cheekSquintRight': ("😼 Nâng Má Phải", "Khối cơ má phải nâng cao đẩy mí mắt dưới lên."),
    'noseSneerLeft': ("👃 Nhăn Mũi Trái", "Cánh mũi trái co nhăn lên trên."),
    'noseSneerRight': ("👃 Nhăn Mũi Phải", "Cánh mũi phải co nhăn lên trên."),
    'tongueOut': ("👅 Thè Lưỡi", "Đầu lưỡi thò ra ngoài môi."),
}


class DASKTOON_OT_arkit_init_placeholders(Operator):
    """Initialize all 52 Apple ARKit blendshapes as basis placeholders on the mesh"""
    bl_idname = "dasktoon.arkit_init_placeholders"
    bl_label = "Initialize 52 ARKit Placeholders"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a Mesh Object!")
            return {'CANCELLED'}

        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis", from_mix=False)

        sk = obj.data.shape_keys
        added = 0
        for name in ARKIT_52_ALL_NAMES:
            if name not in sk.key_blocks:
                obj.shape_key_add(name=name, from_mix=False)
                added += 1

        self.report({'INFO'}, f"Initialized {added} missing ARKit 52 blendshapes on '{obj.name}'.")
        return {'FINISHED'}


class DASKTOON_OT_arkit_solo_preview(Operator):
    """Solo preview the selected ARKit blendshape on the character model"""
    bl_idname = "dasktoon.arkit_solo_preview"
    bl_label = "Solo Preview ARKit Shape"
    bl_options = {'REGISTER', 'UNDO'}

    shape_name: StringProperty(name="Shape Name", default="eyeBlinkLeft")
    intensity: FloatProperty(name="Intensity", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        obj = context.object
        if not obj or not obj.data or not obj.data.shape_keys:
            self.report({'ERROR'}, "Select a Mesh with Shape Keys!")
            return {'CANCELLED'}

        sk = obj.data.shape_keys
        for kb in sk.key_blocks:
            kb.value = 0.0

        kb = sk.key_blocks.get(self.shape_name)
        if kb:
            kb.value = self.intensity
            self.report({'INFO'}, f"ARKit Solo: Active '{self.shape_name}' = {self.intensity:.2f}")
        else:
            self.report({'WARNING'}, f"Shape key '{self.shape_name}' not found on model. Synthesize ARKit first!")

        return {'FINISHED'}


# =============================================================================
# DEDICATED ARKit 52 N-PANEL TAB (Category: "ARKit")
# =============================================================================

class DASKTOON_PT_arkit_studio_panel(Panel):
    """Dedicated Apple ARKit 52 Face Tracking Studio in 3D Viewport Sidebar (Tab 'ARKit')"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARKit"
    bl_label = "Apple ARKit 52 Face Studio"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        sk = obj.data.shape_keys if obj and obj.data else None
        scene = context.scene

        # ── 1. ARKit Health & Status Inspector ──
        box_stat = layout.box()
        box_stat.label(text="ARKit 52 Blendshapes Status", icon='PHONE')
        
        if sk:
            present_count = sum(1 for name in ARKIT_52_ALL_NAMES if name in sk.key_blocks)
            perc = int((present_count / 52.0) * 100)
            
            row = box_stat.row(align=True)
            ic = 'CHECKMARK' if present_count == 52 else 'INFO'
            row.label(text=f"Progress: {present_count} / 52 Shapes ({perc}%)", icon=ic)
            
            # Sub-category badges
            eyes_c = sum(1 for n in ARKIT_52_ALL_NAMES[:14] if n in sk.key_blocks)
            jaw_mouth_c = sum(1 for n in ARKIT_52_ALL_NAMES[14:42] if n in sk.key_blocks)
            brow_c = sum(1 for n in ARKIT_52_ALL_NAMES[42:47] if n in sk.key_blocks)
            cheek_c = sum(1 for n in ARKIT_52_ALL_NAMES[47:] if n in sk.key_blocks)
            
            grid = box_stat.grid_flow(columns=2, align=True)
            grid.label(text=f"👁️ Eyes: {eyes_c}/14")
            grid.label(text=f"👄 Mouth: {jaw_mouth_c}/28")
            grid.label(text=f"🤨 Brows: {brow_c}/5")
            grid.label(text=f"😼 Cheeks: {cheek_c}/5")
        else:
            box_stat.label(text="(Object has no Shape Keys yet)", icon='INFO')

        # ── 2. 1-Click ARKit 52 Synthesizer & Generator ──
        box_gen = layout.box()
        box_gen.label(text="ARKit 52 Generators", icon='AUTO')
        box_gen.operator("dasktoon.vrm_synthesize_arkit52", text="📱 Synthesize 52 ARKit from VRM", icon='SOLO_ON')
        box_gen.operator("dasktoon.arkit_init_placeholders", text="➕ Initialize 52 Empty Placeholders", icon='ADD')

        if not sk:
            return

        # ── 3. ARKit 52 Visual Reference Cards & Inspector ──
        box_cards = layout.box()
        box_cards.label(text="📖 ARKit 52 Visual Reference & Test", icon='BOOKMARKS')

        if not hasattr(scene, "dask_arkit_selected_shape"):
            scene.dask_arkit_selected_shape = "eyeBlinkLeft"

        box_cards.prop(scene, "dask_arkit_selected_shape", text="Shape")
        sel_shape = scene.dask_arkit_selected_shape
        guide_info = ARKIT_GUIDE_DB.get(sel_shape, ("📍 Vùng mặt", "Mô tả cử động giải phẫu ARKit."))

        card_box = box_cards.box()
        col = card_box.column(align=True)
        col.label(text=f"🎯 {sel_shape}", icon='SHAPEKEY_DATA')
        col.label(text=f"📍 {guide_info[0]}", icon='RESTRICT_SELECT_OFF')
        col.separator()
        col.label(text=guide_info[1])
        col.separator()

        row_b = col.row(align=True)
        op_solo = row_b.operator("dasktoon.arkit_solo_preview", text="🔍 Solo Test on Model", icon='VIEWZOOM')
        op_solo.shape_name = sel_shape
        row_b.operator("dasktoon.vrm_zero_all_shapes", text="Reset", icon='LOOP_BACK')

        # ── 4. Live Motion Tester ──
        box_prev = layout.box()
        box_prev.label(text="Live Viewport Motion Tester", icon='PLAY')
        row = box_prev.row(align=True)
        op_b = row.operator("dasktoon.vrm_live_preview", text="👁️ Blink Test", icon='HIDE_OFF')
        op_b.preview_mode = 'AUTO_BLINK'
        op_t = row.operator("dasktoon.vrm_live_preview", text="🗣️ Speech Loop", icon='SPEAKER')
        op_t.preview_mode = 'AIUEO_TALK'
        op_e = row.operator("dasktoon.vrm_live_preview", text="🎭 Emotions", icon='SCENE')
        op_e.preview_mode = 'EMOTIONS'

        # ── 5. ARKit Utilities ──
        box_util = layout.box()
        box_util.label(text="ARKit Utilities", icon='TOOL_SETTINGS')
        row = box_util.row(align=True)
        row.operator("dasktoon.vrm_zero_all_shapes", text="Zero All 52", icon='LOOP_BACK')
        row.operator("dasktoon.vrm_remove_empty_shapes", text="Clean Empty", icon='TRASH')


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
    # VRM & ARKit ShapeKey Toolset Operators
    DASKTOON_OT_vrm_init_standard,
    DASKTOON_OT_vrm_split_shape_key,
    DASKTOON_OT_vrm_mirror_shape_key,
    DASKTOON_OT_vrm_bake_expression,
    DASKTOON_OT_vrm_synthesize_arkit52,
    DASKTOON_OT_vrm_zero_all_shapes,
    DASKTOON_OT_vrm_remove_empty_shapes,
    DASKTOON_OT_vrm_convert_naming,
    DASKTOON_OT_vrm_live_preview,
    DASKTOON_OT_vrm_guide_solo_preview,
    DASKTOON_OT_arkit_init_placeholders,
    DASKTOON_OT_arkit_solo_preview,
    DASKTOON_UL_shape_groups,
    DASKTOON_UL_shape_mappings,
    DASKTOON_PT_shape_axis_panel,
    DASKTOON_PT_vrm_toolset_panel,
    DASKTOON_PT_arkit_studio_panel,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    bpy.types.Object.dask_shape_controllers = PointerProperty(type=DaskShapeControllerRoot)
    bpy.types.Scene.dask_guide_card_key = EnumProperty(
        name="Expression Card",
        items=[
            ('JOY', "😊 Joy / Happy", "Open smile & eyes curved"),
            ('ANGRY', "😠 Angry", "Furrowed brows & lowered eyelids"),
            ('SORROW', "😢 Sorrow / Sad", "Raised inner brows & downturned mouth"),
            ('SURPRISED', "😲 Surprised", "Raised brows & wide open eyes"),
            ('RELAXED', "😌 Relaxed / Fun", "Curved eyes & soft smile"),
            ('VISEME_A', "🗣️ Viseme A (aa)", "Jaw open vertically"),
            ('VISEME_I', "🗣️ Viseme I (ih)", "Mouth stretched horizontally"),
            ('VISEME_U', "🗣️ Viseme U (ou)", "Mouth funnel & pucker"),
            ('VISEME_E', "🗣️ Viseme E (ee)", "Mouth open moderately"),
            ('VISEME_O', "🗣️ Viseme O (oh)", "Mouth open rounded O"),
            ('BLINK_BOTH', "👁️ Eye Blink Both", "Both upper eyelids closed"),
            ('WINK_L', "😉 Wink Left", "Left eye closed, right eye open"),
            ('WINK_R', "😉 Wink Right", "Right eye closed, left eye open"),
            ('CHEEK_PUFF', "🐡 Cheek Puff", "Both cheeks puffed outward"),
        ],
        default='JOY',
    )
    bpy.types.Scene.dask_arkit_selected_shape = EnumProperty(
        name="ARKit Blendshape",
        items=[(name, name, ARKIT_GUIDE_DB.get(name, ("", ""))[1]) for name in ARKIT_52_ALL_NAMES],
        default='eyeBlinkLeft',
    )


def unregister():
    if DaskHUDState.draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DaskHUDState.draw_handler, 'WINDOW')
        DaskHUDState.draw_handler = None
    if hasattr(bpy.types.Object, "dask_shape_controllers"):
        del bpy.types.Object.dask_shape_controllers
    if hasattr(bpy.types.Scene, "dask_guide_card_key"):
        del bpy.types.Scene.dask_guide_card_key
    if hasattr(bpy.types.Scene, "dask_arkit_selected_shape"):
        del bpy.types.Scene.dask_arkit_selected_shape
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()


if __name__ == "__main__":
    register()
