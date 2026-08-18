# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon UV Optimizer
=====================
Game-ready UV optimization tools for DaskToon Anime Engine.

Features:
  - Texel Density Normalizer
  - Straighten Near-Straight UV Edges
  - Smart UV Pack with margin control
  - Mirror UV Merge (overlap symmetric halves)
  - UV Checker & Report (overlap, stretch, bounds, tiny islands)
  - One-click Game Engine Presets (Unity / Godot / Unreal Engine)
"""

import bpy
import bmesh
import math
import mathutils
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    IntProperty,
    FloatProperty,
    EnumProperty,
    BoolProperty,
    StringProperty,
)


# =============================================================================
# Property Group
# =============================================================================

class DaskToonUVOptimizerProps(PropertyGroup):
    texel_density: FloatProperty(
        name="Texel Density",
        description="Target texel density in pixels per meter",
        default=1024.0,
        min=1.0,
        max=8192.0,
        step=100,
        precision=0,
    )
    texture_size: EnumProperty(
        name="Texture Size",
        description="Target texture resolution",
        items=[
            ('512',  "512 px",  "512 x 512"),
            ('1024', "1024 px", "1024 x 1024 (recommended)"),
            ('2048', "2048 px", "2048 x 2048"),
            ('4096', "4096 px", "4096 x 4096"),
        ],
        default='1024',
    )
    uv_margin: FloatProperty(
        name="UV Margin",
        description="Margin between UV islands (fraction of texture size)",
        default=0.005,
        min=0.0,
        max=0.05,
        precision=4,
    )
    straighten_threshold: FloatProperty(
        name="Straighten Threshold",
        description="Max angle deviation (degrees) to snap UV edges straight",
        default=2.0,
        min=0.1,
        max=15.0,
    )
    mirror_axis: EnumProperty(
        name="Mirror Axis",
        description="World axis used for symmetry detection",
        items=[
            ('X', "X Axis", "Mirror on X axis"),
            ('Y', "Y Axis", "Mirror on Y axis"),
            ('Z', "Z Axis", "Mirror on Z axis"),
        ],
        default='X',
    )
    check_overlaps: IntProperty(name="Overlapping Islands", default=0)
    check_stretch: IntProperty(name="Stretched Islands", default=0)
    check_out_of_bounds: IntProperty(name="Out-of-Bounds Islands", default=0)
    check_tiny: IntProperty(name="Tiny Islands", default=0)
    check_done: BoolProperty(name="Analysis Done", default=False)

    # Pixel Grid Snap
    pixel_grid_size: EnumProperty(
        name="Pixel Grid",
        description="Snap UV vertices to N×N pixel grid",
        items=[
            ('4',   "1/4 px",   "Snap to 4px subdivisions"),
            ('8',   "1/8 px",   "Snap to 8px subdivisions"),
            ('16',  "1/16 px",  "Snap to 16px subdivisions"),
            ('32',  "1/32 px",  "Snap to 32px subdivisions"),
            ('64',  "1/64 px",  "Snap to 64px subdivisions"),
        ],
        default='16',
    )

    # Auto-Seam
    seam_angle_threshold: FloatProperty(
        name="Seam Angle",
        description="Mark edges as seam when dihedral angle exceeds this value",
        default=60.0,
        min=1.0,
        max=180.0,
    )
    seam_use_sharp: BoolProperty(
        name="Include Sharp Edges",
        description="Also mark sharp-flagged edges as seams",
        default=True,
    )

    # UV2 / Lightmap channel
    uv2_name: StringProperty(
        name="UV2 Channel Name",
        description="Name for the secondary UV channel (lightmap)",
        default="UVMap_Lightmap",
    )

    # De-overlap
    deoverlap_margin: FloatProperty(
        name="De-overlap Margin",
        description="Extra gap between islands when separating overlaps",
        default=0.01,
        min=0.0,
        max=0.1,
        precision=4,
    )

    # Rotate lock
    rotate_lock_step: EnumProperty(
        name="Rotation Step",
        description="Snap island rotation to multiples of this angle",
        items=[
            ('90',  "90°",  "Multiples of 90 degrees"),
            ('45',  "45°",  "Multiples of 45 degrees"),
        ],
        default='90',
    )


# =============================================================================
# Helper Utilities
# =============================================================================

def _island_bounds(loops, uv_layer):
    uvs = [l[uv_layer].uv for l in loops]
    return (
        min(u.x for u in uvs),
        min(u.y for u in uvs),
        max(u.x for u in uvs),
        max(u.y for u in uvs),
    )


def _island_area_3d(loops):
    faces_seen = set()
    area = 0.0
    for loop in loops:
        f = loop.face
        if id(f) not in faces_seen:
            faces_seen.add(id(f))
            area += f.calc_area()
    return area


def _island_area_uv(loops, uv_layer):
    faces_seen = set()
    area = 0.0
    for loop in loops:
        f = loop.face
        if id(f) not in faces_seen:
            faces_seen.add(id(f))
            face_loops = list(f.loops)
            n = len(face_loops)
            uv_area = 0.0
            for i in range(n):
                u0 = face_loops[i][uv_layer].uv
                u1 = face_loops[(i + 1) % n][uv_layer].uv
                uv_area += (u0.x * u1.y - u1.x * u0.y)
            area += abs(uv_area) * 0.5
    return area


def _collect_islands(bm, uv_layer):
    """BFS to collect UV islands as lists of BMLoops."""
    visited = set()
    islands = []
    for face in bm.faces:
        for loop in face.loops:
            if id(loop) in visited:
                continue
            island_loops = []
            stack = [loop]
            while stack:
                cur = stack.pop()
                if id(cur) in visited:
                    continue
                visited.add(id(cur))
                island_loops.append(cur)
                cur_uv = cur[uv_layer].uv
                for link_loop in cur.vert.link_loops:
                    if id(link_loop) not in visited:
                        if (link_loop[uv_layer].uv - cur_uv).length < 1e-6:
                            stack.append(link_loop)
            if island_loops:
                islands.append(island_loops)
    return islands


# =============================================================================
# 1. Normalize Texel Density
# =============================================================================

class DASKTOON_OT_uv_normalize_texel_density(Operator):
    bl_idname = "dasktoon.uv_normalize_texel_density"
    bl_label = "Normalize Texel Density"
    bl_description = "Scale UV islands so every surface receives the same texel density"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        target_density = props.texel_density
        tex_size = int(props.texture_size)
        target_ratio = (target_density ** 2) / (tex_size ** 2)

        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        islands = _collect_islands(bm, uv_layer)
        changed = 0

        for island_loops in islands:
            area_3d = _island_area_3d(island_loops)
            area_uv = _island_area_uv(island_loops, uv_layer)
            if area_3d < 1e-10 or area_uv < 1e-10:
                continue
            current_ratio = area_uv / area_3d
            if abs(current_ratio - target_ratio) < 1e-8:
                continue
            scale = math.sqrt(target_ratio / current_ratio)
            uvs = [l[uv_layer].uv for l in island_loops]
            cx = sum(u.x for u in uvs) / len(uvs)
            cy = sum(u.y for u in uvs) / len(uvs)
            for l in island_loops:
                u = l[uv_layer].uv
                u.x = cx + (u.x - cx) * scale
                u.y = cy + (u.y - cy) * scale
            changed += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Normalized {changed} UV island(s) to {target_density:.0f} px/m @ {tex_size}px")
        return {'FINISHED'}


# =============================================================================
# 2. Straighten Near-Straight UV Edges
# =============================================================================

class DASKTOON_OT_uv_straighten_edges(Operator):
    bl_idname = "dasktoon.uv_straighten_edges"
    bl_label = "Straighten UV Edges"
    bl_description = "Snap nearly horizontal/vertical UV edges to be perfectly straight"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        threshold = math.radians(props.straighten_threshold)
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        snapped = 0

        for face in bm.faces:
            loops = list(face.loops)
            n = len(loops)
            for i in range(n):
                la = loops[i]
                lb = loops[(i + 1) % n]
                ua = la[uv_layer].uv
                ub = lb[uv_layer].uv
                dx = ub.x - ua.x
                dy = ub.y - ua.y
                length = math.sqrt(dx * dx + dy * dy)
                if length < 1e-10:
                    continue
                angle = math.atan2(abs(dy), abs(dx))
                if angle < threshold:
                    mid_v = (ua.y + ub.y) * 0.5
                    la[uv_layer].uv.y = mid_v
                    lb[uv_layer].uv.y = mid_v
                    snapped += 1
                elif abs(angle - math.pi * 0.5) < threshold:
                    mid_u = (ua.x + ub.x) * 0.5
                    la[uv_layer].uv.x = mid_u
                    lb[uv_layer].uv.x = mid_u
                    snapped += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Straightened {snapped} UV edge(s)")
        return {'FINISHED'}


# =============================================================================
# 3. Smart UV Pack
# =============================================================================

class DASKTOON_OT_uv_smart_pack(Operator):
    bl_idname = "dasktoon.uv_smart_pack"
    bl_label = "Smart UV Pack"
    bl_description = "Pack all UV islands into [0,1] space with game-optimized margin"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        margin = props.uv_margin
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=margin)
        tex_size = int(props.texture_size)
        self.report({'INFO'}, f"Packed UV with {int(margin * tex_size)}px margin at {tex_size}px")
        return {'FINISHED'}


# =============================================================================
# 4. Mirror UV Merge
# =============================================================================

class DASKTOON_OT_uv_mirror_merge(Operator):
    bl_idname = "dasktoon.uv_mirror_merge"
    bl_label = "Mirror UV Merge"
    bl_description = "Overlap mirrored face UVs to halve texture memory usage"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[props.mirror_axis]
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        TOLERANCE = 1e-4
        merged = 0

        for face_pos in bm.faces:
            center = face_pos.calc_center_median()
            if center[axis_idx] <= 0:
                continue
            mirror_center = mathutils.Vector(center)
            mirror_center[axis_idx] = -mirror_center[axis_idx]
            face_neg = None
            for f in bm.faces:
                if f == face_pos:
                    continue
                if (f.calc_center_median() - mirror_center).length < TOLERANCE:
                    face_neg = f
                    break
            if face_neg is None:
                continue
            lp = list(face_pos.loops)
            ln = list(face_neg.loops)
            if len(lp) != len(ln):
                continue
            for a, b in zip(lp, ln):
                b[uv_layer].uv = a[uv_layer].uv.copy()
            merged += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Merged {merged} mirrored face pair(s) on {props.mirror_axis} axis")
        return {'FINISHED'}


# =============================================================================
# 5. UV Checker & Report
# =============================================================================

class DASKTOON_OT_uv_analyze(Operator):
    bl_idname = "dasktoon.uv_analyze"
    bl_label = "Analyze UV"
    bl_description = "Scan UV and report: overlaps, stretch, out-of-bounds, tiny islands"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = int(props.texture_size)
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        islands = _collect_islands(bm, uv_layer)

        tiny_threshold = (1.0 / tex_size) ** 2
        out_of_bounds = stretched = tiny = overlaps = 0

        islands_data = []
        for isl in islands:
            mn_u, mn_v, mx_u, mx_v = _island_bounds(isl, uv_layer)
            area_uv = _island_area_uv(isl, uv_layer)
            area_3d = _island_area_3d(isl)
            islands_data.append({
                'min_u': mn_u, 'min_v': mn_v,
                'max_u': mx_u, 'max_v': mx_v,
                'area_uv': area_uv, 'area_3d': area_3d,
                'loops': isl,
            })

            if mn_u < -0.001 or mn_v < -0.001 or mx_u > 1.001 or mx_v > 1.001:
                out_of_bounds += 1
            if area_uv < tiny_threshold:
                tiny += 1
            if area_3d > 1e-10 and area_uv > 1e-10:
                ratio = area_uv / area_3d
                for loop in isl:
                    f = loop.face
                    f_uv = _island_area_uv(list(f.loops), uv_layer)
                    f_3d = f.calc_area()
                    if f_3d > 1e-10 and f_uv > 1e-10:
                        fr = f_uv / f_3d
                        if fr > ratio * 3.0 or fr < ratio * 0.333:
                            stretched += 1
                            break

        for i in range(len(islands_data)):
            for j in range(i + 1, len(islands_data)):
                a, b = islands_data[i], islands_data[j]
                if (a['max_u'] > b['min_u'] and b['max_u'] > a['min_u'] and
                        a['max_v'] > b['min_v'] and b['max_v'] > a['min_v']):
                    overlaps += 1

        props.check_overlaps = overlaps
        props.check_stretch = stretched
        props.check_out_of_bounds = out_of_bounds
        props.check_tiny = tiny
        props.check_done = True

        self.report({'INFO'},
            f"UV: {overlaps} overlaps | {stretched} stretched | "
            f"{out_of_bounds} out-of-bounds | {tiny} tiny")
        return {'FINISHED'}


# =============================================================================
# 6. Game Engine Preset
# =============================================================================

class DASKTOON_OT_uv_game_preset(Operator):
    bl_idname = "dasktoon.uv_game_preset"
    bl_label = "Apply Game Preset"
    bl_description = "Apply UV optimization for a game engine and pack"
    bl_options = {'REGISTER', 'UNDO'}

    engine: EnumProperty(
        name="Engine",
        items=[
            ('UNITY',  "Unity",         "Unity (2px margin, 1024px)"),
            ('GODOT',  "Godot",         "Godot (1px margin, 1024px)"),
            ('UNREAL', "Unreal Engine", "Unreal 5 (4px margin, 2048px)"),
        ],
        default='UNITY',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and
                obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        if self.engine == 'UNITY':
            props.texture_size = '1024'
            props.texel_density = 1024.0
            props.uv_margin = 2.0 / 1024.0
        elif self.engine == 'GODOT':
            props.texture_size = '1024'
            props.texel_density = 1024.0
            props.uv_margin = 1.0 / 1024.0
        elif self.engine == 'UNREAL':
            props.texture_size = '2048'
            props.texel_density = 2048.0
            props.uv_margin = 4.0 / 2048.0

        bpy.ops.dasktoon.uv_normalize_texel_density()
        bpy.ops.dasktoon.uv_smart_pack()
        self.report({'INFO'}, f"Applied {self.engine} UV preset!")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        self.layout.prop(self, "engine", expand=True)


# =============================================================================
# 7. Pixel Grid Snap
# =============================================================================

class DASKTOON_OT_uv_pixel_grid_snap(Operator):
    bl_idname = "dasktoon.uv_pixel_grid_snap"
    bl_label = "Pixel Grid Snap"
    bl_description = (
        "Snap all UV vertices to the nearest pixel grid position. "
        "Prevents sub-pixel UV jitter and keeps textures crisp for cel-shading"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = int(props.texture_size)
        grid = int(props.pixel_grid_size)
        step = 1.0 / (tex_size / grid)
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        snapped = 0
        for face in bm.faces:
            for loop in face.loops:
                u = loop[uv_layer].uv
                new_x = round(u.x / step) * step
                new_y = round(u.y / step) * step
                if abs(new_x - u.x) > 1e-8 or abs(new_y - u.y) > 1e-8:
                    u.x = new_x
                    u.y = new_y
                    snapped += 1
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Snapped {snapped} UV vertex/vertices to {grid}px grid at {tex_size}px")
        return {'FINISHED'}


# =============================================================================
# 8. Auto-Seam Generator
# =============================================================================

class DASKTOON_OT_uv_auto_seam(Operator):
    bl_idname = "dasktoon.uv_auto_seam"
    bl_label = "Auto-Generate Seams"
    bl_description = (
        "Mark seams on edges whose dihedral angle exceeds the threshold "
        "or are flagged as sharp. Ideal before UV unwrapping"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        angle_rad = math.radians(props.seam_angle_threshold)
        use_sharp = props.seam_use_sharp
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        marked = 0
        for edge in bm.edges:
            if len(edge.link_faces) < 2:
                # Boundary edge — always a seam
                edge.seam = True
                marked += 1
                continue
            f0, f1 = edge.link_faces[0], edge.link_faces[1]
            n0, n1 = f0.normal, f1.normal
            dot = max(-1.0, min(1.0, n0.dot(n1)))
            dihedral = math.acos(dot)
            if dihedral > angle_rad:
                edge.seam = True
                marked += 1
            elif use_sharp and edge.smooth is False:
                edge.seam = True
                marked += 1
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Marked {marked} seam edge(s) (angle > {props.seam_angle_threshold:.0f}°)")
        return {'FINISHED'}


# =============================================================================
# 9. UV Channel Manager (Add UV2 Lightmap Channel)
# =============================================================================

class DASKTOON_OT_uv_add_lightmap_channel(Operator):
    bl_idname = "dasktoon.uv_add_lightmap_channel"
    bl_label = "Add Lightmap UV (UV2)"
    bl_description = (
        "Add a second UV channel optimized for lightmapping. "
        "Unwraps with no overlaps, full [0,1] coverage, and game margin"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        uv2_name = props.uv2_name
        obj = context.active_object

        # Add UV layer if not present
        if uv2_name not in obj.data.uv_layers:
            obj.data.uv_layers.new(name=uv2_name)
            self.report({'INFO'}, f"Created UV channel '{uv2_name}'")
        else:
            self.report({'WARNING'}, f"UV channel '{uv2_name}' already exists — switching to it")

        # Activate the new layer
        obj.data.uv_layers[uv2_name].active = True
        obj.data.uv_layers[uv2_name].active_render = False

        # Smart UV Project with no overlaps for lightmap
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.smart_project(
            angle_limit=math.radians(66),
            margin_method='SCALED',
            island_margin=props.uv_margin,
            area_weight=0.0,
            correct_aspect=True,
            scale_to_bounds=True,
        )
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=props.uv_margin)

        self.report({'INFO'}, f"Lightmap UV '{uv2_name}' generated and packed!")
        return {'FINISHED'}


# =============================================================================
# 10. Island De-overlap
# =============================================================================

class DASKTOON_OT_uv_deoverlap(Operator):
    bl_idname = "dasktoon.uv_deoverlap"
    bl_label = "De-overlap Islands"
    bl_description = (
        "Detect and separate overlapping UV islands by moving them "
        "to a free position in the UV space"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        margin = props.deoverlap_margin
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        islands = _collect_islands(bm, uv_layer)

        placed = []  # (min_u, min_v, max_u, max_v)
        moved = 0

        for isl in islands:
            mn_u, mn_v, mx_u, mx_v = _island_bounds(isl, uv_layer)
            w = mx_u - mn_u + margin
            h = mx_v - mn_v + margin

            def overlaps_placed(nu, nv):
                for (pu, pv, qu, qv) in placed:
                    if (nu < qu + margin and nu + w > pu - margin and
                            nv < qv + margin and nv + h > pv - margin):
                        return True
                return False

            if not overlaps_placed(mn_u, mn_v):
                placed.append((mn_u, mn_v, mn_u + w, mn_v + h))
                continue

            # Find a free slot scanning left→right, bottom→top
            found = False
            for row in range(0, 10):
                for col in range(0, 10):
                    nu = col * w
                    nv = row * h
                    if not overlaps_placed(nu, nv):
                        # Move island
                        dx = nu - mn_u
                        dy = nv - mn_v
                        for l in isl:
                            l[uv_layer].uv.x += dx
                            l[uv_layer].uv.y += dy
                        placed.append((nu, nv, nu + w, nv + h))
                        moved += 1
                        found = True
                        break
                if found:
                    break

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Moved {moved} overlapping island(s) to free positions")
        return {'FINISHED'}


# =============================================================================
# 11. Rotate Islands to 90° Steps
# =============================================================================

class DASKTOON_OT_uv_rotate_lock(Operator):
    bl_idname = "dasktoon.uv_rotate_lock"
    bl_label = "Snap Island Rotation"
    bl_description = (
        "Rotate each UV island to the nearest 90° (or 45°) step. "
        "Improves atlas packing efficiency and avoids diagonal pixel bleed"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.mode == 'EDIT' and obj.data.uv_layers.active)

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        step_deg = int(props.rotate_lock_step)
        step_rad = math.radians(step_deg)
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        islands = _collect_islands(bm, uv_layer)
        rotated = 0

        for isl in islands:
            if len(isl) < 2:
                continue
            # Estimate dominant angle via PCA of UV positions
            uvs = [l[uv_layer].uv.copy() for l in isl]
            cx = sum(u.x for u in uvs) / len(uvs)
            cy = sum(u.y for u in uvs) / len(uvs)
            cov_xx = sum((u.x - cx) ** 2 for u in uvs)
            cov_xy = sum((u.x - cx) * (u.y - cy) for u in uvs)
            if abs(cov_xx) < 1e-10 and abs(cov_xy) < 1e-10:
                continue
            angle = math.atan2(cov_xy, cov_xx)
            # Snap angle to nearest step
            steps = round(angle / step_rad)
            snap_angle = steps * step_rad
            delta = snap_angle - angle
            if abs(delta) < 1e-6:
                continue
            cos_d = math.cos(delta)
            sin_d = math.sin(delta)
            for l in isl:
                u = l[uv_layer].uv
                rx = u.x - cx
                ry = u.y - cy
                u.x = cx + rx * cos_d - ry * sin_d
                u.y = cy + rx * sin_d + ry * cos_d
            rotated += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Snapped {rotated} island(s) to {step_deg}° rotation steps")
        return {'FINISHED'}


# =============================================================================
# N-Panel UI
# =============================================================================

class DASKTOON_PT_uv_optimizer(Panel):
    bl_label = "DaskToon UV"
    bl_idname = "DASKTOON_PT_uv_optimizer"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "DaskToon"

    def draw(self, context):
        layout = self.layout
        props = context.scene.dasktoon_uv_optimizer

        # --- Settings ---
        box = layout.box()
        box.label(text="Settings", icon='PREFERENCES')
        col = box.column(align=True)
        col.prop(props, "texture_size", text="Resolution")
        col.prop(props, "texel_density", text="Texel Density (px/m)")
        col.prop(props, "uv_margin", text="Pack Margin")

        layout.separator(factor=0.5)

        # --- Optimize ---
        box = layout.box()
        box.label(text="Optimize UV", icon='UV')
        col = box.column(align=True)
        col.operator("dasktoon.uv_normalize_texel_density",
                     text="Normalize Texel Density", icon='FULLSCREEN_ENTER')
        row = col.row(align=True)
        row.prop(props, "straighten_threshold", text="Angle Threshold")
        col.operator("dasktoon.uv_straighten_edges",
                     text="Straighten UV Edges", icon='MOD_EDGESPLIT')
        col.operator("dasktoon.uv_smart_pack",
                     text="Smart UV Pack", icon='PACKAGE')

        layout.separator(factor=0.5)

        # --- Mirror ---
        box = layout.box()
        box.label(text="Mirror UV Merge", icon='MOD_MIRROR')
        col = box.column(align=True)
        col.prop(props, "mirror_axis", text="Axis", expand=True)
        col.operator("dasktoon.uv_mirror_merge",
                     text="Merge Mirror UVs", icon='AUTOMERGE_ON')

        layout.separator(factor=0.5)

        # --- Pixel Grid Snap ---
        box = layout.box()
        box.label(text="Pixel Grid Snap", icon='SNAP_GRID')
        col = box.column(align=True)
        col.prop(props, "pixel_grid_size", text="Grid Size")
        col.operator("dasktoon.uv_pixel_grid_snap",
                     text="Snap to Pixel Grid", icon='SNAP_ON')

        layout.separator(factor=0.5)

        # --- Rotation Lock ---
        box = layout.box()
        box.label(text="Rotation Lock", icon='LOOP_FORWARDS')
        col = box.column(align=True)
        col.prop(props, "rotate_lock_step", text="Step", expand=True)
        col.operator("dasktoon.uv_rotate_lock",
                     text="Snap Island Rotation", icon='ORIENTATION_GIMBAL')

        layout.separator(factor=0.5)

        # --- De-overlap ---
        box = layout.box()
        box.label(text="De-overlap Islands", icon='FULLSCREEN_EXIT')
        col = box.column(align=True)
        col.prop(props, "deoverlap_margin", text="Gap Margin")
        col.operator("dasktoon.uv_deoverlap",
                     text="Separate Overlapping Islands", icon='MOD_EXPLODE')

        layout.separator(factor=0.5)

        # --- Auto Seam ---
        box = layout.box()
        box.label(text="Auto-Generate Seams", icon='MOD_EDGESPLIT')
        col = box.column(align=True)
        col.prop(props, "seam_angle_threshold", text="Seam Angle")
        col.prop(props, "seam_use_sharp", text="Include Sharp Edges")
        col.operator("dasktoon.uv_auto_seam",
                     text="Generate Seams", icon='KEYTYPE_JITTER_VEC')

        layout.separator(factor=0.5)

        # --- UV2 Lightmap ---
        box = layout.box()
        box.label(text="Lightmap UV (UV2)", icon='LIGHT')
        col = box.column(align=True)
        col.prop(props, "uv2_name", text="Channel Name")
        col.operator("dasktoon.uv_add_lightmap_channel",
                     text="Generate Lightmap UV", icon='LIGHTPROBE_PLANE')

        layout.separator(factor=0.5)

        # --- Game Presets ---
        box = layout.box()
        box.label(text="Game Engine Presets", icon='RESTRICT_INSTANCED_OFF')
        row = box.row(align=True)
        op = row.operator("dasktoon.uv_game_preset", text="Unity")
        op.engine = 'UNITY'
        op = row.operator("dasktoon.uv_game_preset", text="Godot")
        op.engine = 'GODOT'
        op = row.operator("dasktoon.uv_game_preset", text="Unreal")
        op.engine = 'UNREAL'

        layout.separator(factor=0.5)

        # --- UV Checker ---
        box = layout.box()
        box.label(text="UV Checker", icon='VIEWZOOM')
        box.operator("dasktoon.uv_analyze", text="Analyze UV", icon='ZOOM_ALL')

        if props.check_done:
            col = box.column(align=True)
            icon_fn = lambda n: 'ERROR' if n > 0 else 'CHECKMARK'
            col.label(text=f"Overlaps:      {props.check_overlaps}", icon=icon_fn(props.check_overlaps))
            col.label(text=f"Stretched:     {props.check_stretch}", icon=icon_fn(props.check_stretch))
            col.label(text=f"Out-of-Bounds: {props.check_out_of_bounds}", icon=icon_fn(props.check_out_of_bounds))
            col.label(text=f"Tiny Islands:  {props.check_tiny}", icon=icon_fn(props.check_tiny))

            total = sum([props.check_overlaps, props.check_stretch,
                         props.check_out_of_bounds, props.check_tiny])
            if total == 0:
                box.label(text="UV looks good for game!", icon='CHECKMARK')


# =============================================================================
# Registration
# =============================================================================

classes = (
    DaskToonUVOptimizerProps,
    DASKTOON_OT_uv_normalize_texel_density,
    DASKTOON_OT_uv_straighten_edges,
    DASKTOON_OT_uv_smart_pack,
    DASKTOON_OT_uv_mirror_merge,
    DASKTOON_OT_uv_analyze,
    DASKTOON_OT_uv_game_preset,
    DASKTOON_OT_uv_pixel_grid_snap,
    DASKTOON_OT_uv_auto_seam,
    DASKTOON_OT_uv_add_lightmap_channel,
    DASKTOON_OT_uv_deoverlap,
    DASKTOON_OT_uv_rotate_lock,
    DASKTOON_PT_uv_optimizer,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    if not hasattr(bpy.types.Scene, "dasktoon_uv_optimizer"):
        bpy.types.Scene.dasktoon_uv_optimizer = bpy.props.PointerProperty(
            type=DaskToonUVOptimizerProps
        )


def unregister():
    if hasattr(bpy.types.Scene, "dasktoon_uv_optimizer"):
        del bpy.types.Scene.dasktoon_uv_optimizer
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
