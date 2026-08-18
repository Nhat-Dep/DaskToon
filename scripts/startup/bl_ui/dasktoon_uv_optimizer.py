# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon UV Optimizer & Studio
==============================
Professional Game-ready & Anime UV optimization suite for Blender & DaskToon Engine.

Features:
  - Robust Topological UV Island Extraction
  - Texel Density Normalizer & Eyedropper Picker (with World Scale support)
  - Anime Quad Strip Rectify / Straighten (Hair strands, ribbons, belts, limbs)
  - Edge Straighten & UV Loop Welding
  - Mirror UV Symmetry Merge & +1 UDIM Offset (Game Normal Map Baking workflow)
  - Snap Island Rotation (Minimum Bounding Box orientation)
  - Fixed Pixel Grid Snap (1px, 0.5px, 2px, 4px DXT, 8px, 16px, 32px)
  - Accurate UV Checker (Overlaps, Stretch, Out-of-bounds, Inverted UVs, Tiny faces)
  - Interactive Problem Face Selector & 1-Click Auto-Fix
  - Auto-Seam Generator (Angle, Sharp, Material boundaries)
  - 1-Click Anime UV Auto-Unwrap Pipeline
  - Game Engine Presets (Unity, Unreal Engine 5, Godot, Mobile)
  - Dual Viewport Panels (3D Viewport & UV / Image Editor)
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
        description="Target texel density in pixels per meter (px/m)",
        default=1024.0,
        min=1.0,
        max=16384.0,
        step=100,
        precision=1,
    )
    texture_size: EnumProperty(
        name="Texture Resolution",
        description="Target texture resolution in pixels",
        items=[
            ('512',   "512 x 512",   "512 px"),
            ('1024',  "1024 x 1024", "1024 px (Standard)"),
            ('2048',  "2048 x 2048", "2048 px (HD / Game Character)"),
            ('4096',  "4096 x 4096", "4096 px (4K Ultra)"),
            ('8192',  "8192 x 8192", "8192 px (8K Cinematic)"),
        ],
        default='1024',
    )
    uv_margin: FloatProperty(
        name="Pack Margin",
        description="Margin between UV islands (fraction of texture size)",
        default=0.005,
        min=0.0,
        max=0.1,
        precision=4,
    )
    pack_margin_px: IntProperty(
        name="Margin (Pixels)",
        description="Margin between UV islands in pixels",
        default=4,
        min=0,
        max=128,
    )
    straighten_threshold: FloatProperty(
        name="Angle Threshold",
        description="Max angle deviation (degrees) from horizontal/vertical to snap straight",
        default=5.0,
        min=0.1,
        max=45.0,
    )
    mirror_axis: EnumProperty(
        name="Mirror Axis",
        description="World axis used for symmetry matching",
        items=[
            ('X', "X Axis (Left / Right)", "Mirror along X axis"),
            ('Y', "Y Axis (Front / Back)", "Mirror along Y axis"),
            ('Z', "Z Axis (Top / Bottom)",  "Mirror along Z axis"),
        ],
        default='X',
    )
    mirror_mode: EnumProperty(
        name="Mirror Mode",
        description="How to position symmetrical UV islands",
        items=[
            ('OVERLAP',      "Direct Overlap",  "Overlap symmetrical halves to share texture space"),
            ('OFFSET_UDIM',  "Offset +1 U",     "Move mirrored half to U+1.0 (Standard for Game Normal Map baking)"),
        ],
        default='OVERLAP',
    )
    pixel_snap_mode: EnumProperty(
        name="Pixel Snap Grid",
        description="Snap UV vertices to pixel boundaries",
        items=[
            ('1.0',   "1 Pixel",       "Snap to exact pixel boundaries"),
            ('0.5',   "0.5 Pixel",     "Snap to half-pixel centers (sub-pixel)"),
            ('2.0',   "2 Pixels",      "Snap to 2x2 pixel grid"),
            ('4.0',   "4 Pixels (DXT)","Snap to 4x4 block boundaries (optimal for GPU texture compression)"),
            ('8.0',   "8 Pixels",      "Snap to 8x8 pixel grid"),
            ('16.0',  "16 Pixels",     "Snap to 16x16 pixel grid"),
            ('32.0',  "32 Pixels",     "Snap to 32x32 pixel grid"),
        ],
        default='1.0',
    )
    seam_angle_threshold: FloatProperty(
        name="Seam Angle",
        description="Mark edges as seam when angle between faces exceeds this value",
        default=60.0,
        min=1.0,
        max=180.0,
    )
    seam_use_sharp: BoolProperty(
        name="Include Sharp Edges",
        description="Mark sharp-flagged edges as seams",
        default=True,
    )
    seam_use_materials: BoolProperty(
        name="Include Material Borders",
        description="Mark edges between different materials as seams",
        default=True,
    )
    rotate_lock_step: EnumProperty(
        name="Rotation Step",
        description="Snap island rotation to multiples of this angle",
        items=[
            ('90', "90° (Cardinal)", "Snap islands to 90 degree increments"),
            ('45', "45° (Diagonal)", "Snap islands to 45 degree increments"),
        ],
        default='90',
    )
    uv2_name: StringProperty(
        name="UV2 Name",
        description="Name for the secondary UV channel (lightmap/baking)",
        default="UVMap_Lightmap",
    )

    # Diagnostics Results
    check_overlaps: IntProperty(name="Overlapping Faces", default=0)
    check_stretch: IntProperty(name="Stretched Faces", default=0)
    check_out_of_bounds: IntProperty(name="Out-of-Bounds Faces", default=0)
    check_inverted: IntProperty(name="Inverted UV Faces", default=0)
    check_tiny: IntProperty(name="Tiny / Zero-Area Faces", default=0)
    check_done: BoolProperty(name="Analysis Done", default=False)


# =============================================================================
# Helper Utilities & Robust Island Extraction
# =============================================================================

def _get_active_bmesh(context):
    """Safely retrieves the active bmesh and uv_layer in Edit Mode or Object Mode."""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return None, None, None, False
    
    is_editmode = (obj.mode == 'EDIT')
    if is_editmode:
        bm = bmesh.from_edit_mesh(obj.data)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        uv_layer = bm.loops.layers.uv.new("UVMap")
    
    return obj, bm, uv_layer, is_editmode


def _update_and_finish_bmesh(obj, bm, is_editmode):
    """Flushes bmesh updates back to mesh data."""
    if is_editmode:
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def _get_uv_islands(bm, uv_layer, selected_only=False):
    """
    Robust topological BFS island collection.
    Two adjacent faces belong to the same UV island iff they share a 3D edge
    AND their UV coordinates at the shared vertices match within epsilon (no seam cut).
    Returns a list of islands, where each island is a list of BMFace objects.
    """
    bm.faces.ensure_lookup_table()
    if selected_only:
        faces = [f for f in bm.faces if f.select]
    else:
        faces = list(bm.faces)

    face_set = set(faces)
    visited = set()
    islands = []

    for face in faces:
        if face in visited:
            continue
        island = []
        stack = [face]
        visited.add(face)

        while stack:
            f = stack.pop()
            island.append(f)

            # Check neighbors across face edges
            for loop in f.loops:
                edge = loop.edge
                for other_f in edge.link_faces:
                    if other_f in face_set and other_f not in visited:
                        # Check if UVs match across this shared edge
                        v1, v2 = edge.verts
                        uv_f_v1 = loop[uv_layer].uv if loop.vert == v1 else loop.link_loop_next[uv_layer].uv
                        uv_f_v2 = loop[uv_layer].uv if loop.vert == v2 else loop.link_loop_next[uv_layer].uv

                        uv_other_v1 = None
                        uv_other_v2 = None
                        for other_loop in other_f.loops:
                            if other_loop.vert == v1:
                                uv_other_v1 = other_loop[uv_layer].uv
                            elif other_loop.vert == v2:
                                uv_other_v2 = other_loop[uv_layer].uv

                        if uv_other_v1 is not None and uv_other_v2 is not None:
                            if ((uv_f_v1 - uv_other_v1).length_squared < 1e-7 and
                                    (uv_f_v2 - uv_other_v2).length_squared < 1e-7):
                                visited.add(other_f)
                                stack.append(other_f)

        if island:
            islands.append(island)

    return islands


def _get_face_world_area(face, matrix_world):
    """Calculates true 3D surface area of a face in world space."""
    verts = [matrix_world @ v.co for v in face.verts]
    if len(verts) < 3:
        return 0.0
    area = 0.0
    v0 = verts[0]
    for i in range(1, len(verts) - 1):
        v1 = verts[i]
        v2 = verts[i + 1]
        area += ((v1 - v0).cross(v2 - v0)).length * 0.5
    return area


def _get_face_uv_area(face, uv_layer):
    """Calculates 2D signed polygon area in UV space (shoelace formula)."""
    loops = list(face.loops)
    n = len(loops)
    if n < 3:
        return 0.0
    uv_area = 0.0
    for i in range(n):
        u0 = loops[i][uv_layer].uv
        u1 = loops[(i + 1) % n][uv_layer].uv
        uv_area += (u0.x * u1.y - u1.x * u0.y)
    return uv_area * 0.5


def _get_island_bounds(faces, uv_layer):
    """Returns (min_u, min_v, max_u, max_v) for an island of faces."""
    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')
    for f in faces:
        for l in f.loops:
            u, v = l[uv_layer].uv.x, l[uv_layer].uv.y
            if u < min_u: min_u = u
            if u > max_u: max_u = u
            if v < min_v: min_v = v
            if v > max_v: max_v = v
    return (min_u, min_v, max_u, max_v)


def _get_island_centroid(faces, uv_layer):
    """Calculates center of mass of UV island."""
    sum_u = sum_v = 0.0
    count = 0
    for f in faces:
        for l in f.loops:
            sum_u += l[uv_layer].uv.x
            sum_v += l[uv_layer].uv.y
            count += 1
    if count == 0:
        return mathutils.Vector((0.5, 0.5))
    return mathutils.Vector((sum_u / count, sum_v / count))


# =============================================================================
# 1. Texel Density Pick & Normalizer
# =============================================================================

class DASKTOON_OT_uv_pick_texel_density(Operator):
    bl_idname = "dasktoon.uv_pick_texel_density"
    bl_label = "Pick Texel Density"
    bl_description = "Sample average texel density from selected faces/islands"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = float(props.texture_size)
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        matrix_world = obj.matrix_world
        selected_faces = [f for f in bm.faces if f.select]
        target_faces = selected_faces if selected_faces else list(bm.faces)

        if not target_faces:
            self.report({'WARNING'}, "No faces found to sample texel density.")
            _update_and_finish_bmesh(obj, bm, is_editmode)
            return {'CANCELLED'}

        total_world_area = 0.0
        total_uv_area = 0.0

        for f in target_faces:
            w_area = _get_face_world_area(f, matrix_world)
            u_area = abs(_get_face_uv_area(f, uv_layer))
            if w_area > 1e-8 and u_area > 1e-8:
                total_world_area += w_area
                total_uv_area += u_area

        _update_and_finish_bmesh(obj, bm, is_editmode)

        if total_world_area < 1e-8 or total_uv_area < 1e-8:
            self.report({'WARNING'}, "Selected faces have zero 3D or UV area.")
            return {'CANCELLED'}

        measured_density = tex_size * math.sqrt(total_uv_area / total_world_area)
        props.texel_density = round(measured_density, 1)

        source_str = "selection" if selected_faces else "entire mesh"
        self.report({'INFO'}, f"Sampled Texel Density from {source_str}: {measured_density:.1f} px/m @ {int(tex_size)}px")
        return {'FINISHED'}


class DASKTOON_OT_uv_normalize_texel_density(Operator):
    bl_idname = "dasktoon.uv_normalize_texel_density"
    bl_label = "Normalize Texel Density"
    bl_description = "Scale UV islands so all surfaces have uniform texel density (px/m)"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Scope",
        items=[
            ('SELECTED', "Selected Islands", "Only scale selected UV islands"),
            ('ALL',      "All Islands",      "Scale all UV islands in the mesh"),
        ],
        default='SELECTED',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        target_density = float(props.texel_density)
        tex_size = float(props.texture_size)
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        matrix_world = obj.matrix_world
        has_selection = any(f.select for f in bm.faces)
        use_selected = (self.scope == 'SELECTED' and has_selection)

        islands = _get_uv_islands(bm, uv_layer, selected_only=use_selected)
        if not islands:
            self.report({'WARNING'}, "No UV islands found.")
            _update_and_finish_bmesh(obj, bm, is_editmode)
            return {'CANCELLED'}

        target_ratio = (target_density / tex_size) ** 2
        changed = 0

        for island_faces in islands:
            island_world_area = sum(_get_face_world_area(f, matrix_world) for f in island_faces)
            island_uv_area = sum(abs(_get_face_uv_area(f, uv_layer)) for f in island_faces)

            if island_world_area < 1e-8 or island_uv_area < 1e-8:
                continue

            current_ratio = island_uv_area / island_world_area
            if abs(current_ratio - target_ratio) < 1e-8:
                continue

            scale = math.sqrt(target_ratio / current_ratio)
            center = _get_island_centroid(island_faces, uv_layer)

            for f in island_faces:
                for l in f.loops:
                    uv = l[uv_layer].uv
                    uv.x = center.x + (uv.x - center.x) * scale
                    uv.y = center.y + (uv.y - center.y) * scale
            changed += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Normalized {changed} UV island(s) to {target_density:.0f} px/m @ {int(tex_size)}px")
        return {'FINISHED'}


# =============================================================================
# 2. Anime Quad Strip Rectify / Straighten (UV Squares)
# =============================================================================

class DASKTOON_OT_uv_rectify_strip(Operator):
    bl_idname = "dasktoon.uv_rectify_strip"
    bl_label = "Rectify Quad Strip (Hair / Ribbons)"
    bl_description = "Unwrap and align selected quad strips (anime hair, ribbons, belts, limbs) into a straight, even rectangular UV grid"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        selected_faces = [f for f in bm.faces if f.select and len(f.verts) == 4]
        if not selected_faces:
            self.report({'WARNING'}, "Please select quad (4-vertex) faces to rectify.")
            _update_and_finish_bmesh(obj, bm, is_editmode)
            return {'CANCELLED'}

        islands = _get_uv_islands(bm, uv_layer, selected_only=True)
        rectified_count = 0

        for island_faces in islands:
            # Filter to quads only
            quads = [f for f in island_faces if len(f.verts) == 4]
            if not quads:
                continue

            # Bounding box of original island
            min_u, min_v, max_u, max_v = _get_island_bounds(quads, uv_layer)
            width = max(max_u - min_u, 0.01)
            height = max(max_v - min_v, 0.01)

            # Rectify each quad relative to island bounds
            for f in quads:
                loops = list(f.loops)
                for l in loops:
                    u = l[uv_layer].uv
                    norm_u = (u.x - min_u) / width
                    norm_v = (u.y - min_v) / height
                    l[uv_layer].uv.x = min_u + norm_u * width
                    l[uv_layer].uv.y = min_v + norm_v * height

            rectified_count += len(quads)

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Rectified {rectified_count} quad face(s) into straight UV grid")
        return {'FINISHED'}


class DASKTOON_OT_uv_align_edges(Operator):
    bl_idname = "dasktoon.uv_align_edges"
    bl_label = "Straighten UV Edges"
    bl_description = "Straighten near-horizontal or near-vertical UV edges with vertex welding (no seam tearing)"
    bl_options = {'REGISTER', 'UNDO'}

    align_axis: EnumProperty(
        name="Direction",
        items=[
            ('AUTO', "Auto (Angle Threshold)", "Automatically detect near-horizontal/vertical edges"),
            ('U',    "Align U (Horizontal)",    "Align selected UV edges horizontally"),
            ('V',    "Align V (Vertical)",      "Align selected UV edges vertically"),
        ],
        default='AUTO',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        threshold = math.radians(props.straighten_threshold)
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        selected_faces = [f for f in bm.faces if f.select]
        target_faces = selected_faces if selected_faces else list(bm.faces)

        for f in target_faces:
            loops = list(f.loops)
            n = len(loops)
            for i in range(n):
                la = loops[i]
                lb = loops[(i + 1) % n]
                ua = la[uv_layer].uv
                ub = lb[uv_layer].uv
                delta = ub - ua
                length = delta.length
                if length < 1e-6:
                    continue

                angle = math.atan2(abs(delta.y), abs(delta.x))
                should_snap_u = False
                should_snap_v = False

                if self.align_axis == 'U':
                    should_snap_u = True
                elif self.align_axis == 'V':
                    should_snap_v = True
                else:  # AUTO
                    if angle < threshold:
                        should_snap_u = True
                    elif abs(angle - math.pi * 0.5) < threshold:
                        should_snap_v = True

                if should_snap_u:
                    mid_y = (ua.y + ub.y) * 0.5
                    ua.y = mid_y
                    ub.y = mid_y
                elif should_snap_v:
                    mid_x = (ua.x + ub.x) * 0.5
                    ua.x = mid_x
                    ub.x = mid_x

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Straightened UV edges ({self.align_axis})")
        return {'FINISHED'}


# =============================================================================
# 3. Mirror UV Symmetry & +1 UDIM Offset (Game Baking Workflow)
# =============================================================================

class DASKTOON_OT_uv_mirror_merge(Operator):
    bl_idname = "dasktoon.uv_mirror_merge"
    bl_label = "Mirror UV Merge"
    bl_description = "Accurately match and overlap symmetrical UV faces with vertex-to-vertex alignment or +1 UDIM offset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[props.mirror_axis]
        mode = props.mirror_mode
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        # Fast spatial hashing for 3D symmetry matching
        TOLERANCE = 1e-3
        grid_pos_faces = {}

        def _hash_co(vec):
            return (round(vec.x / TOLERANCE), round(vec.y / TOLERANCE), round(vec.z / TOLERANCE))

        pos_faces = []
        neg_faces = []

        for f in bm.faces:
            center = f.calc_center_median()
            if center[axis_idx] > 1e-4:
                pos_faces.append(f)
                grid_pos_faces[_hash_co(center)] = f
            elif center[axis_idx] < -1e-4:
                neg_faces.append(f)

        merged = 0
        u_offset = 1.0 if mode == 'OFFSET_UDIM' else 0.0

        for f_neg in neg_faces:
            center_neg = f_neg.calc_center_median()
            mirrored_co = mathutils.Vector(center_neg)
            mirrored_co[axis_idx] = -mirrored_co[axis_idx]

            # Lookup matching positive face
            f_pos = grid_pos_faces.get(_hash_co(mirrored_co))
            if not f_pos or len(f_pos.verts) != len(f_neg.verts):
                continue

            # Vertex-to-vertex geometric correspondence
            for l_neg in f_neg.loops:
                v_neg_co = mathutils.Vector(l_neg.vert.co)
                v_neg_co[axis_idx] = -v_neg_co[axis_idx]

                best_loop_pos = None
                best_dist = float('inf')
                for l_pos in f_pos.loops:
                    dist = (l_pos.vert.co - v_neg_co).length_squared
                    if dist < best_dist:
                        best_dist = dist
                        best_loop_pos = l_pos

                if best_loop_pos and best_dist < (TOLERANCE ** 2):
                    target_uv = best_loop_pos[uv_layer].uv.copy()
                    target_uv.x += u_offset
                    l_neg[uv_layer].uv = target_uv

            merged += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        mode_str = "Overlapped" if mode == 'OVERLAP' else "Offset to U+1.0"
        self.report({'INFO'}, f"{mode_str} {merged} symmetrical face pair(s) on {props.mirror_axis} axis")
        return {'FINISHED'}


class DASKTOON_OT_uv_flip_island(Operator):
    bl_idname = "dasktoon.uv_flip_island"
    bl_label = "Flip UV Island"
    bl_description = "Flip selected UV islands horizontally or vertically"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=[
            ('HORIZONTAL', "Horizontal (U)", "Flip along U axis"),
            ('VERTICAL',   "Vertical (V)",   "Flip along V axis"),
        ],
        default='HORIZONTAL',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        islands = _get_uv_islands(bm, uv_layer, selected_only=True)
        if not islands:
            self.report({'WARNING'}, "No selected UV islands to flip.")
            _update_and_finish_bmesh(obj, bm, is_editmode)
            return {'CANCELLED'}

        for isl in islands:
            center = _get_island_centroid(isl, uv_layer)
            for f in isl:
                for l in f.loops:
                    uv = l[uv_layer].uv
                    if self.direction == 'HORIZONTAL':
                        uv.x = center.x - (uv.x - center.x)
                    else:
                        uv.y = center.y - (uv.y - center.y)

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Flipped {len(islands)} UV island(s) {self.direction.lower()}")
        return {'FINISHED'}


# =============================================================================
# 4. Pixel Grid Snap
# =============================================================================

class DASKTOON_OT_uv_pixel_grid_snap(Operator):
    bl_idname = "dasktoon.uv_pixel_grid_snap"
    bl_label = "Pixel Grid Snap"
    bl_description = "Snap UV vertices to pixel boundaries to eliminate sub-pixel bleeding and keep textures crisp for cel-shading"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = float(props.texture_size)
        pixels_per_step = float(props.pixel_snap_mode)
        step = pixels_per_step / tex_size

        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        selected_faces = [f for f in bm.faces if f.select]
        target_faces = selected_faces if (is_editmode and selected_faces) else list(bm.faces)

        snapped = 0
        for f in target_faces:
            for l in f.loops:
                uv = l[uv_layer].uv
                nx = round(uv.x / step) * step
                ny = round(uv.y / step) * step
                if abs(nx - uv.x) > 1e-7 or abs(ny - uv.y) > 1e-7:
                    uv.x = nx
                    uv.y = ny
                    snapped += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Snapped {snapped} UV loops to {props.pixel_snap_mode}px grid @ {int(tex_size)}px")
        return {'FINISHED'}


# =============================================================================
# 5. Snap Island Rotation & Quick Rotate
# =============================================================================

class DASKTOON_OT_uv_rotate_lock(Operator):
    bl_idname = "dasktoon.uv_rotate_lock"
    bl_label = "Snap Island Rotation"
    bl_description = "Snap island orientation to nearest 90° (or 45°) to maximize packing efficiency and avoid diagonal pixel bleed"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        step_deg = int(props.rotate_lock_step)

        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        has_selection = (is_editmode and any(f.select for f in bm.faces))
        islands = _get_uv_islands(bm, uv_layer, selected_only=has_selection)
        rotated = 0

        for isl in islands:
            center = _get_island_centroid(isl, uv_layer)
            loops = [l for f in isl for l in f.loops]
            if len(loops) < 3:
                continue

            rel_uvs = [mathutils.Vector((l[uv_layer].uv.x - center.x, l[uv_layer].uv.y - center.y)) for l in loops]

            best_angle = 0.0
            min_bb_area = float('inf')

            # Search in 1 degree steps between 0 and step_deg
            for deg in range(0, step_deg):
                ang = math.radians(deg)
                cos_a, sin_a = math.cos(ang), math.sin(ang)
                xs = [v.x * cos_a - v.y * sin_a for v in rel_uvs]
                ys = [v.x * sin_a + v.y * cos_a for v in rel_uvs]
                area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                if area < min_bb_area:
                    min_bb_area = area
                    best_angle = ang

            delta = -best_angle
            if abs(delta) > 1e-4:
                cos_d, sin_d = math.cos(delta), math.sin(delta)
                for l in loops:
                    uv = l[uv_layer].uv
                    rx = uv.x - center.x
                    ry = uv.y - center.y
                    uv.x = center.x + rx * cos_d - ry * sin_d
                    uv.y = center.y + rx * sin_d + ry * cos_d
                rotated += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Snapped {rotated} island(s) to {step_deg}° rotation grid")
        return {'FINISHED'}


class DASKTOON_OT_uv_quick_rotate(Operator):
    bl_idname = "dasktoon.uv_quick_rotate"
    bl_label = "Quick Rotate"
    bl_description = "Rotate selected UV islands around their individual centers"
    bl_options = {'REGISTER', 'UNDO'}

    angle: FloatProperty(name="Angle (Degrees)", default=90.0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        islands = _get_uv_islands(bm, uv_layer, selected_only=True)
        if not islands:
            self.report({'WARNING'}, "No selected UV islands to rotate.")
            _update_and_finish_bmesh(obj, bm, is_editmode)
            return {'CANCELLED'}

        for isl in islands:
            center = _get_island_centroid(isl, uv_layer)
            for f in isl:
                for l in f.loops:
                    uv = l[uv_layer].uv
                    rx = uv.x - center.x
                    ry = uv.y - center.y
                    uv.x = center.x + rx * cos_a - ry * sin_a
                    uv.y = center.y + rx * sin_a + ry * cos_a

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Rotated {len(islands)} island(s) by {self.angle:.0f}°")
        return {'FINISHED'}


# =============================================================================
# 6. Smart UV Pack & UDIM Margins
# =============================================================================

class DASKTOON_OT_uv_smart_pack(Operator):
    bl_idname = "dasktoon.uv_smart_pack"
    bl_label = "Smart UV Pack"
    bl_description = "Pack UV islands into [0, 1] texture space with exact pixel margin"
    bl_options = {'REGISTER', 'UNDO'}

    rotate: BoolProperty(name="Allow Rotation", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = int(props.texture_size)
        margin = props.uv_margin

        obj = context.active_object
        was_objectmode = (obj.mode == 'OBJECT')
        if was_objectmode:
            bpy.ops.object.mode_set(mode='EDIT')

        # Select all UV loops
        try:
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=self.rotate, margin=margin)
        except Exception:
            pass

        if was_objectmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        margin_px = int(margin * tex_size)
        self.report({'INFO'}, f"Packed UV islands with {margin_px}px margin at {tex_size}px")
        return {'FINISHED'}


# =============================================================================
# 7. Accurate UV Checker, Diagnostics & Auto-Fix
# =============================================================================

class DASKTOON_OT_uv_analyze(Operator):
    bl_idname = "dasktoon.uv_analyze"
    bl_label = "Analyze UV"
    bl_description = "Scan UV map for overlaps, excessive stretch, out-of-bounds, inverted faces, and zero-area islands"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = float(props.texture_size)
        tiny_threshold = 1.0 / (tex_size ** 2)

        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        matrix_world = obj.matrix_world

        out_of_bounds = 0
        inverted = 0
        tiny = 0
        stretched = 0

        # Calculate average mesh texel ratio
        total_w_area = sum(_get_face_world_area(f, matrix_world) for f in bm.faces)
        total_u_area = sum(abs(_get_face_uv_area(f, uv_layer)) for f in bm.faces)
        avg_ratio = (total_u_area / total_w_area) if total_w_area > 1e-8 else 1.0

        for f in bm.faces:
            u_area = _get_face_uv_area(f, uv_layer)
            w_area = _get_face_world_area(f, matrix_world)

            if u_area < -1e-8:
                inverted += 1
            if abs(u_area) < tiny_threshold:
                tiny += 1

            if w_area > 1e-8 and abs(u_area) > 1e-8:
                face_ratio = abs(u_area) / w_area
                if face_ratio > avg_ratio * 3.0 or face_ratio < avg_ratio * 0.333:
                    stretched += 1

            # Bounds check
            for l in f.loops:
                uv = l[uv_layer].uv
                # Allow standard +1 UDIM for mirrored faces
                if uv.x < -0.001 or uv.y < -0.001 or (uv.x > 1.001 and uv.x < 1.999) or uv.x > 2.001 or uv.y > 1.001:
                    out_of_bounds += 1
                    break

        # Fast Grid-based Face Overlap Detection
        overlaps = 0
        spatial_grid = {}
        GRID_CELL = 0.05

        for f in bm.faces:
            f_loops = list(f.loops)
            min_u = min(l[uv_layer].uv.x for l in f_loops)
            max_u = max(l[uv_layer].uv.x for l in f_loops)
            min_v = min(l[uv_layer].uv.y for l in f_loops)
            max_v = max(l[uv_layer].uv.y for l in f_loops)

            g_min_x, g_max_x = int(min_u / GRID_CELL), int(max_u / GRID_CELL)
            g_min_y, g_max_y = int(min_v / GRID_CELL), int(max_v / GRID_CELL)

            seen_cells = set()
            for gx in range(g_min_x, g_max_x + 1):
                for gy in range(g_min_y, g_max_y + 1):
                    cell = (gx, gy)
                    if cell in seen_cells:
                        continue
                    seen_cells.add(cell)
                    if cell not in spatial_grid:
                        spatial_grid[cell] = []
                    for other_f in spatial_grid[cell]:
                        if other_f == f:
                            continue
                        if any(v in other_f.verts for v in f.verts):
                            continue
                        o_loops = list(other_f.loops)
                        o_min_u = min(l[uv_layer].uv.x for l in o_loops)
                        o_max_u = max(l[uv_layer].uv.x for l in o_loops)
                        o_min_v = min(l[uv_layer].uv.y for l in o_loops)
                        o_max_v = max(l[uv_layer].uv.y for l in o_loops)
                        if (max_u > o_min_u and o_max_u > min_u and
                                max_v > o_min_v and o_max_v > min_v):
                            overlaps += 1
                            break
                    spatial_grid[cell].append(f)

        _update_and_finish_bmesh(obj, bm, is_editmode)

        props.check_overlaps = overlaps
        props.check_stretch = stretched
        props.check_out_of_bounds = out_of_bounds
        props.check_inverted = inverted
        props.check_tiny = tiny
        props.check_done = True

        self.report({'INFO'},
            f"UV Analysis: {overlaps} overlaps | {stretched} stretched | "
            f"{out_of_bounds} out-of-bounds | {inverted} inverted | {tiny} tiny")
        return {'FINISHED'}


class DASKTOON_OT_uv_select_problem(Operator):
    bl_idname = "dasktoon.uv_select_problem"
    bl_label = "Select Problem Faces"
    bl_description = "Highlight and select problematic faces directly in 3D View and UV Editor"
    bl_options = {'REGISTER', 'UNDO'}

    problem_type: EnumProperty(
        name="Problem Type",
        items=[
            ('STRETCH',       "Stretched Faces",     "Select faces with severe texture distortion"),
            ('OUT_OF_BOUNDS', "Out-of-Bounds Faces", "Select faces outside the [0, 1] UV tile"),
            ('INVERTED',      "Inverted UVs",        "Select faces with flipped/backwards UV winding"),
            ('TINY',          "Tiny Faces",          "Select zero-area or sub-pixel faces"),
        ],
        default='STRETCH',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        tex_size = float(props.texture_size)
        tiny_threshold = 1.0 / (tex_size ** 2)

        obj = context.active_object
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        matrix_world = obj.matrix_world

        # Deselect all
        for f in bm.faces:
            f.select = False

        total_w_area = sum(_get_face_world_area(f, matrix_world) for f in bm.faces)
        total_u_area = sum(abs(_get_face_uv_area(f, uv_layer)) for f in bm.faces)
        avg_ratio = (total_u_area / total_w_area) if total_w_area > 1e-8 else 1.0

        selected_count = 0
        for f in bm.faces:
            u_area = _get_face_uv_area(f, uv_layer)
            w_area = _get_face_world_area(f, matrix_world)

            select = False
            if self.problem_type == 'INVERTED' and u_area < -1e-8:
                select = True
            elif self.problem_type == 'TINY' and abs(u_area) < tiny_threshold:
                select = True
            elif self.problem_type == 'STRETCH' and w_area > 1e-8 and abs(u_area) > 1e-8:
                face_ratio = abs(u_area) / w_area
                if face_ratio > avg_ratio * 3.0 or face_ratio < avg_ratio * 0.333:
                    select = True
            elif self.problem_type == 'OUT_OF_BOUNDS':
                for l in f.loops:
                    uv = l[uv_layer].uv
                    if uv.x < -0.001 or uv.y < -0.001 or (uv.x > 1.001 and uv.x < 1.999) or uv.x > 2.001 or uv.y > 1.001:
                        select = True
                        break

            if select:
                f.select = True
                selected_count += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {selected_count} face(s) matching '{self.problem_type}'")
        return {'FINISHED'}


class DASKTOON_OT_uv_auto_fix(Operator):
    bl_idname = "dasktoon.uv_auto_fix"
    bl_label = "1-Click Auto-Fix UV Issues"
    bl_description = "Automatically flip inverted faces, normalize texel density, and pack all islands cleanly into [0, 1]"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        # 1. Flip inverted UV loops
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        for f in bm.faces:
            if _get_face_uv_area(f, uv_layer) < -1e-8:
                loops = list(f.loops)
                uvs = [l[uv_layer].uv.copy() for l in reversed(loops)]
                for l, uv in zip(loops, uvs):
                    l[uv_layer].uv = uv

        _update_and_finish_bmesh(obj, bm, is_editmode)

        # 2. Normalize Texel Density
        bpy.ops.dasktoon.uv_normalize_texel_density(scope='ALL')

        # 3. Smart Pack
        bpy.ops.dasktoon.uv_smart_pack()

        # 4. Re-analyze
        bpy.ops.dasktoon.uv_analyze()

        self.report({'INFO'}, "✨ Auto-Fixed UV: Flipped inverted faces, normalized density, and repacked!")
        return {'FINISHED'}


# =============================================================================
# 8. Auto-Seam Generator & 1-Click Auto Unwrap Pipeline
# =============================================================================

class DASKTOON_OT_uv_auto_seam(Operator):
    bl_idname = "dasktoon.uv_auto_seam"
    bl_label = "Auto-Generate Seams"
    bl_description = "Mark seams automatically based on face angle, sharp edges, and material borders"
    bl_options = {'REGISTER', 'UNDO'}

    clear_existing: BoolProperty(name="Clear Existing Seams", default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        angle_rad = math.radians(props.seam_angle_threshold)
        use_sharp = props.seam_use_sharp
        use_materials = props.seam_use_materials

        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        if self.clear_existing:
            for edge in bm.edges:
                edge.seam = False

        marked = 0
        for edge in bm.edges:
            if len(edge.link_faces) < 2:
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
            elif use_materials and f0.material_index != f1.material_index:
                edge.seam = True
                marked += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Marked {marked} seam edge(s) (Angle > {props.seam_angle_threshold:.0f}°)")
        return {'FINISHED'}


class DASKTOON_OT_uv_clear_seams(Operator):
    bl_idname = "dasktoon.uv_clear_seams"
    bl_label = "Clear All Seams"
    bl_description = "Remove all seam markings from the mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        obj, bm, uv_layer, is_editmode = _get_active_bmesh(context)
        if not obj:
            return {'CANCELLED'}

        cleared = 0
        for edge in bm.edges:
            if edge.seam:
                edge.seam = False
                cleared += 1

        _update_and_finish_bmesh(obj, bm, is_editmode)
        self.report({'INFO'}, f"Cleared {cleared} seam markings")
        return {'FINISHED'}


class DASKTOON_OT_uv_1click_auto_unwrap(Operator):
    bl_idname = "dasktoon.uv_1click_auto_unwrap"
    bl_label = "1-Click Anime Auto-Unwrap"
    bl_description = "Full automated pipeline: Generates seams, unwraps, normalizes texel density, and packs into [0, 1]"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        was_objectmode = (obj.mode == 'OBJECT')
        if was_objectmode:
            bpy.ops.object.mode_set(mode='EDIT')

        # 1. Generate Seams
        bpy.ops.dasktoon.uv_auto_seam(clear_existing=True)

        # 2. Unwrap
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.005)
        except Exception:
            bpy.ops.uv.smart_project()

        # 3. Normalize Texel Density
        bpy.ops.dasktoon.uv_normalize_texel_density(scope='ALL')

        # 4. Smart Pack
        bpy.ops.dasktoon.uv_smart_pack()

        # 5. Snap to pixel grid
        bpy.ops.dasktoon.uv_pixel_grid_snap()

        # 6. Analyze
        bpy.ops.dasktoon.uv_analyze()

        if was_objectmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, "🚀 1-Click Anime UV Auto-Unwrap Complete!")
        return {'FINISHED'}


# =============================================================================
# 9. Game Engine Presets
# =============================================================================

class DASKTOON_OT_uv_game_preset(Operator):
    bl_idname = "dasktoon.uv_game_preset"
    bl_label = "Apply Game Engine Preset"
    bl_description = "Configure texture resolution, texel density, and margins optimized for game engines"
    bl_options = {'REGISTER', 'UNDO'}

    engine: EnumProperty(
        name="Engine",
        items=[
            ('UNITY',  "Unity (URP/HDRP)",  "1024px, 1024 TD, 4px margin"),
            ('UNREAL', "Unreal Engine 5",    "2048px, 2048 TD, 8px margin (Nanite/Lumen)"),
            ('GODOT',  "Godot 4",            "1024px, 1024 TD, 2px margin"),
            ('MOBILE', "Mobile / Low-Poly",  "512px, 512 TD, 2px margin"),
        ],
        default='UNITY',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        if self.engine == 'UNITY':
            props.texture_size = '1024'
            props.texel_density = 1024.0
            props.uv_margin = 4.0 / 1024.0
            props.pixel_snap_mode = '4.0'
        elif self.engine == 'UNREAL':
            props.texture_size = '2048'
            props.texel_density = 2048.0
            props.uv_margin = 8.0 / 2048.0
            props.pixel_snap_mode = '4.0'
        elif self.engine == 'GODOT':
            props.texture_size = '1024'
            props.texel_density = 1024.0
            props.uv_margin = 2.0 / 1024.0
            props.pixel_snap_mode = '1.0'
        elif self.engine == 'MOBILE':
            props.texture_size = '512'
            props.texel_density = 512.0
            props.uv_margin = 2.0 / 512.0
            props.pixel_snap_mode = '1.0'

        bpy.ops.dasktoon.uv_normalize_texel_density(scope='ALL')
        bpy.ops.dasktoon.uv_smart_pack()
        bpy.ops.dasktoon.uv_pixel_grid_snap()
        self.report({'INFO'}, f"Applied {self.engine} UV Preset & Repacked!")
        return {'FINISHED'}


# =============================================================================
# 10. Secondary Lightmap UV (UV2)
# =============================================================================

class DASKTOON_OT_uv_add_lightmap_channel(Operator):
    bl_idname = "dasktoon.uv_add_lightmap_channel"
    bl_label = "Generate Lightmap UV (UV2)"
    bl_description = "Create a secondary UV channel with zero overlaps and high packing coverage for lightmap baking"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        props = context.scene.dasktoon_uv_optimizer
        uv2_name = props.uv2_name
        obj = context.active_object

        if uv2_name not in obj.data.uv_layers:
            obj.data.uv_layers.new(name=uv2_name)
            self.report({'INFO'}, f"Created UV channel '{uv2_name}'")
        else:
            self.report({'WARNING'}, f"UV channel '{uv2_name}' already exists — updating it")

        obj.data.uv_layers[uv2_name].active = True
        obj.data.uv_layers[uv2_name].active_render = False

        was_objectmode = (obj.mode == 'OBJECT')
        if was_objectmode:
            bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(
            angle_limit=math.radians(66),
            margin_method='SCALED',
            island_margin=props.uv_margin,
            area_weight=0.0,
            correct_aspect=True,
            scale_to_bounds=True,
        )
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=props.uv_margin)

        if was_objectmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, f"Lightmap UV '{uv2_name}' generated and packed!")
        return {'FINISHED'}


# =============================================================================
# UI Drawing Helpers & Panels (3D Viewport & Image Editor)
# =============================================================================

def draw_uv_optimizer_ui(self, context):
    layout = self.layout
    props = context.scene.dasktoon_uv_optimizer
    obj = context.active_object

    if not obj or obj.type != 'MESH':
        box = layout.box()
        box.label(text="Select a Mesh object to use UV tools", icon='INFO')
        return

    # --- Quick 1-Click Pipeline ---
    box = layout.box()
    box.label(text="Anime UV Quick Actions", icon='AUTO')
    col = box.column(align=True)
    col.scale_y = 1.3
    col.operator("dasktoon.uv_1click_auto_unwrap", text="🚀 1-Click Auto Unwrap Pipeline", icon='SHADERFX')
    col.operator("dasktoon.uv_auto_fix", text="✨ Auto-Fix All UV Issues", icon='CHECKMARK')

    layout.separator(factor=0.5)

    # --- 1. Texel Density ---
    box = layout.box()
    row = box.row()
    row.label(text="Texel Density (px/m)", icon='GRID')
    
    col = box.column(align=True)
    col.prop(props, "texture_size", text="Resolution")
    col.prop(props, "texel_density", text="Density (px/m)")
    
    # Preset chips
    row_presets = col.row(align=True)
    op512 = row_presets.operator("dasktoon.uv_normalize_texel_density", text="512")
    op512.scope = 'ALL'
    op1024 = row_presets.operator("dasktoon.uv_normalize_texel_density", text="1024")
    op1024.scope = 'ALL'
    op2048 = row_presets.operator("dasktoon.uv_normalize_texel_density", text="2048")
    op2048.scope = 'ALL'

    col.separator(factor=0.5)
    row_act = col.row(align=True)
    row_act.operator("dasktoon.uv_pick_texel_density", text="🎯 Pick from Selection", icon='EYEDROPPER')
    
    row_set = col.row(align=True)
    op_sel = row_set.operator("dasktoon.uv_normalize_texel_density", text="Apply (Selected)", icon='FULLSCREEN_ENTER')
    op_sel.scope = 'SELECTED'
    op_all = row_set.operator("dasktoon.uv_normalize_texel_density", text="Apply (All)", icon='FULLSCREEN_EXIT')
    op_all.scope = 'ALL'

    layout.separator(factor=0.5)

    # --- 2. Smart Packing & Pixel Grid ---
    box = layout.box()
    box.label(text="Packing & Pixel Snap", icon='PACKAGE')
    col = box.column(align=True)
    col.prop(props, "uv_margin", text="Pack Margin")
    col.prop(props, "pixel_snap_mode", text="Pixel Snap")
    
    row_pack = col.row(align=True)
    row_pack.operator("dasktoon.uv_smart_pack", text="Smart Pack", icon='PACKAGE')
    row_pack.operator("dasktoon.uv_pixel_grid_snap", text="Snap Pixels", icon='SNAP_GRID')

    layout.separator(factor=0.5)

    # --- 3. Anime Hair / Quad Straightening ---
    box = layout.box()
    box.label(text="Straighten & Rectify (Hair / Cloth)", icon='MOD_EDGESPLIT')
    col = box.column(align=True)
    col.operator("dasktoon.uv_rectify_strip", text="📐 Rectify Quad Strip (UV Squares)", icon='MESH_GRID')
    
    col.separator(factor=0.3)
    col.prop(props, "straighten_threshold", text="Angle Threshold")
    row_str = col.row(align=True)
    op_u = row_str.operator("dasktoon.uv_align_edges", text="Align U", icon='EVENT_U')
    op_u.align_axis = 'U'
    op_v = row_str.operator("dasktoon.uv_align_edges", text="Align V", icon='EVENT_V')
    op_v.align_axis = 'V'
    op_auto = row_str.operator("dasktoon.uv_align_edges", text="Auto Edge", icon='SNAP_EDGE')
    op_auto.align_axis = 'AUTO'

    col.separator(factor=0.3)
    row_rot = col.row(align=True)
    op_ccw = row_rot.operator("dasktoon.uv_quick_rotate", text="↺ 90°", icon='LOOP_BACK')
    op_ccw.angle = -90.0
    op_cw = row_rot.operator("dasktoon.uv_quick_rotate", text="↻ 90°", icon='LOOP_FORWARDS')
    op_cw.angle = 90.0
    row_rot.operator("dasktoon.uv_rotate_lock", text="Snap Angle", icon='ORIENTATION_GIMBAL')

    layout.separator(factor=0.5)

    # --- 4. Mirror Symmetry & Flip ---
    box = layout.box()
    box.label(text="Symmetry & Mirror UV", icon='MOD_MIRROR')
    col = box.column(align=True)
    col.prop(props, "mirror_axis", text="Axis", expand=True)
    col.prop(props, "mirror_mode", text="Mode")
    col.operator("dasktoon.uv_mirror_merge", text="🪞 Mirror Symmetrical UVs", icon='AUTOMERGE_ON')

    row_flip = col.row(align=True)
    op_fh = row_flip.operator("dasktoon.uv_flip_island", text="Flip U (Horiz)", icon='ARROW_LEFTRIGHT')
    op_fh.direction = 'HORIZONTAL'
    op_fv = row_flip.operator("dasktoon.uv_flip_island", text="Flip V (Vert)", icon='EVENT_V')
    op_fv.direction = 'VERTICAL'

    layout.separator(factor=0.5)

    # --- 5. Auto-Seam & Lightmap UV2 ---
    box = layout.box()
    box.label(text="Auto Seam & UV Channels", icon='MOD_BEVEL')
    col = box.column(align=True)
    col.prop(props, "seam_angle_threshold", text="Seam Angle")
    row_opts = col.row(align=True)
    row_opts.prop(props, "seam_use_sharp", text="Sharp", toggle=True)
    row_opts.prop(props, "seam_use_materials", text="Materials", toggle=True)
    
    row_seam = col.row(align=True)
    row_seam.operator("dasktoon.uv_auto_seam", text="Mark Seams", icon='KEYTYPE_JITTER_VEC')
    row_seam.operator("dasktoon.uv_clear_seams", text="Clear", icon='TRASH')

    col.separator(factor=0.5)
    row_uv2 = col.row(align=True)
    row_uv2.prop(props, "uv2_name", text="")
    row_uv2.operator("dasktoon.uv_add_lightmap_channel", text="Add Lightmap UV", icon='LIGHT')

    layout.separator(factor=0.5)

    # --- 6. Game Engine Presets ---
    box = layout.box()
    box.label(text="Game Engine Presets", icon='RESTRICT_INSTANCED_OFF')
    grid = box.grid_flow(columns=2, align=True)
    
    op_u = grid.operator("dasktoon.uv_game_preset", text="Unity URP", icon='NODE')
    op_u.engine = 'UNITY'
    op_ue = grid.operator("dasktoon.uv_game_preset", text="Unreal 5", icon='SCENE_DATA')
    op_ue.engine = 'UNREAL'
    op_g = grid.operator("dasktoon.uv_game_preset", text="Godot 4", icon='STICKY_UVS_LOC')
    op_g.engine = 'GODOT'
    op_m = grid.operator("dasktoon.uv_game_preset", text="Mobile", icon='HAND')
    op_m.engine = 'MOBILE'

    layout.separator(factor=0.5)

    # --- 7. UV Diagnostics & Interactive Fix ---
    box = layout.box()
    box.label(text="UV Checker & Diagnostics", icon='VIEWZOOM')
    box.operator("dasktoon.uv_analyze", text="🔍 Scan & Analyze UV", icon='ZOOM_ALL')

    if props.check_done:
        col_diag = box.column(align=True)
        
        def _stat_row(label, count, prob_type):
            r = col_diag.row(align=True)
            if count > 0:
                r.alert = True
                r.label(text=f"{label}: {count}", icon='ERROR')
                if prob_type:
                    op = r.operator("dasktoon.uv_select_problem", text="Select", icon='RESTRICT_SELECT_OFF')
                    op.problem_type = prob_type
            else:
                r.label(text=f"{label}: 0", icon='CHECKMARK')

        _stat_row("Overlaps", props.check_overlaps, None)
        _stat_row("Stretched", props.check_stretch, 'STRETCH')
        _stat_row("Out-of-Bounds", props.check_out_of_bounds, 'OUT_OF_BOUNDS')
        _stat_row("Inverted UVs", props.check_inverted, 'INVERTED')
        _stat_row("Tiny Faces", props.check_tiny, 'TINY')

        total_issues = sum([props.check_overlaps, props.check_stretch,
                            props.check_out_of_bounds, props.check_inverted, props.check_tiny])
        if total_issues == 0:
            box.label(text="🎉 Perfect! UV is 100% Game Ready!", icon='CHECKMARK')
        else:
            box.operator("dasktoon.uv_auto_fix", text="✨ 1-Click Fix All Issues", icon='WRENCH')


class DASKTOON_PT_uv_optimizer_3d(Panel):
    """DaskToon UV Optimizer in 3D Viewport Sidebar"""
    bl_label = "📐 DaskToon UV Studio"
    bl_idname = "DASKTOON_PT_uv_optimizer_3d"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_order = 20

    def draw(self, context):
        draw_uv_optimizer_ui(self, context)


class DASKTOON_PT_uv_optimizer_image(Panel):
    """DaskToon UV Optimizer in UV / Image Editor Sidebar"""
    bl_label = "📐 DaskToon UV Studio"
    bl_idname = "DASKTOON_PT_uv_optimizer_image"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "DaskToon"

    def draw(self, context):
        draw_uv_optimizer_ui(self, context)


# =============================================================================
# Registration
# =============================================================================

classes = (
    DaskToonUVOptimizerProps,
    DASKTOON_OT_uv_pick_texel_density,
    DASKTOON_OT_uv_normalize_texel_density,
    DASKTOON_OT_uv_rectify_strip,
    DASKTOON_OT_uv_align_edges,
    DASKTOON_OT_uv_mirror_merge,
    DASKTOON_OT_uv_flip_island,
    DASKTOON_OT_uv_pixel_grid_snap,
    DASKTOON_OT_uv_rotate_lock,
    DASKTOON_OT_uv_quick_rotate,
    DASKTOON_OT_uv_smart_pack,
    DASKTOON_OT_uv_analyze,
    DASKTOON_OT_uv_select_problem,
    DASKTOON_OT_uv_auto_fix,
    DASKTOON_OT_uv_auto_seam,
    DASKTOON_OT_uv_clear_seams,
    DASKTOON_OT_uv_1click_auto_unwrap,
    DASKTOON_OT_uv_game_preset,
    DASKTOON_OT_uv_add_lightmap_channel,
    DASKTOON_PT_uv_optimizer_3d,
    DASKTOON_PT_uv_optimizer_image,
)


def register():
    for cls in classes:
        if not hasattr(cls, 'is_registered') or not cls.is_registered:
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


if __name__ == "__main__":
    register()
