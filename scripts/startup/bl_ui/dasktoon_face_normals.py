# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
import mathutils
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    EnumProperty,
)


# =============================================================================
# Core Algorithm: Anime Spherical Normal Projection & Custom Split Normal Set
# =============================================================================

def apply_anime_spherized_normals(
    obj,
    blend_factor=1.0,
    center_offset=(0.0, -0.2, 0.0),
    radius_scale=1.0,
    preserve_nose=0.2,
    symmetry_x=True,
    selected_only=True
):
    """Calculates and applies spherized anime face normals to the mesh."""
    if not obj or obj.type != 'MESH':
        return False, "Selected object is not a Mesh."

    me = obj.data
    is_editmode = (obj.mode == 'EDIT')

    if is_editmode:
        bm = bmesh.from_edit_mesh(me)
    else:
        bm = bmesh.new()
        bm.from_mesh(me)

    bm.verts.ensure_lookup_table()
    total_verts = len(bm.verts)
    if total_verts == 0:
        if not is_editmode:
            bm.free()
        return False, "Mesh has no vertices."

    # 1. Determine target vertices (selected or all)
    selected_indices = [v.index for v in bm.verts if v.select]
    if selected_only and selected_indices:
        target_indices = set(selected_indices)
    else:
        target_indices = set(range(total_verts))

    if not target_indices:
        if not is_editmode:
            bm.free()
        return False, "No target vertices selected."

    # 2. Compute Bounding Box / Geometric Center of target vertices
    target_coords = [bm.verts[i].co for i in target_indices]
    geom_center = sum(target_coords, mathutils.Vector((0.0, 0.0, 0.0))) / len(target_coords)

    # Apply user-defined offset
    offset_vec = mathutils.Vector(center_offset)
    sphere_center = geom_center + offset_vec

    # 3. Calculate max bounding distance and nose protrusion reference
    min_y = min(co.y for co in target_coords)  # Front-most in Blender coordinate convention
    max_y = max(co.y for co in target_coords)
    y_range = max(abs(max_y - min_y), 0.001)

    # 4. Compute Spherized Normals per vertex
    final_normals = []
    for v in bm.verts:
        orig_normal = v.normal.copy().normalized()
        if v.index not in target_indices:
            final_normals.append(orig_normal)
            continue

        # Direction from sphere center
        co = v.co
        if symmetry_x:
            # Symmetrize calculation across X=0 plane
            rel_x = co.x
            rel_y = co.y - sphere_center.y
            rel_z = co.z - sphere_center.z
            sphere_dir = mathutils.Vector((rel_x, rel_y, rel_z)).normalized()
        else:
            sphere_dir = (co - sphere_center).normalized()

        if sphere_dir.length < 0.0001:
            sphere_dir = mathutils.Vector((0.0, -1.0, 0.0))

        # Preserve Nose tip heuristic (protrusion factor)
        local_blend = blend_factor
        if preserve_nose > 0.001:
            # Vertices protruding most forward along -Y retain more original angle
            protrusion = clamp_val((sphere_center.y - co.y) / y_range, 0.0, 1.0)
            local_blend *= (1.0 - preserve_nose * protrusion)

        # Lerp and re-normalize
        new_normal = orig_normal.lerp(sphere_dir, local_blend).normalized()
        final_normals.append(new_normal)

    # 5. Commit Custom Split Normals to Mesh
    if is_editmode:
        bmesh.update_edit_mesh(me)
        bpy.ops.object.mode_set(mode='OBJECT')

    me.normals_split_custom_set_from_vertices(final_normals)
    me.update()

    if is_editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    if not is_editmode:
        bm.free()

    return True, f"Successfully spherized normals on {len(target_indices)} vertices."


def clamp_val(val, min_v, max_v):
    return max(min_v, min(max_v, val))


# =============================================================================
# Operators
# =============================================================================

class DASKTOON_OT_fix_face_normals(Operator):
    """Spherize and smooth custom vertex normals for Anime 2D cel-shading look (Arc System Works / Genshin Impact style)"""
    bl_idname = "dasktoon.fix_face_normals"
    bl_label = "Fix Anime Face Normals"
    bl_options = {'REGISTER', 'UNDO'}

    blend_factor: FloatProperty(
        name="Blend Strength",
        description="Strength of spherized normal blending (1.0 = completely smooth spherical shading)",
        default=0.85,
        min=0.0,
        max=1.0,
    )
    center_offset: FloatVectorProperty(
        name="Sphere Center Offset",
        description="Offset of the virtual projection sphere (push backward on Y to flatten face front)",
        default=(0.0, 0.15, -0.05),
        subtype='TRANSLATION',
        size=3,
    )
    preserve_nose: FloatProperty(
        name="Preserve Nose Tip",
        description="Retain original sharp definition at the nose tip",
        default=0.25,
        min=0.0,
        max=1.0,
    )
    symmetry_x: BoolProperty(
        name="Symmetry X",
        description="Enforce exact bilateral symmetry across the X axis",
        default=True,
    )
    selected_only: BoolProperty(
        name="Selected Vertices Only",
        description="Apply only to selected vertices in Edit Mode, or all if none selected",
        default=True,
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        success, msg = apply_anime_spherized_normals(
            obj=obj,
            blend_factor=self.blend_factor,
            center_offset=self.center_offset,
            preserve_nose=self.preserve_nose,
            symmetry_x=self.symmetry_x,
            selected_only=self.selected_only
        )

        if success:
            self.report({'INFO'}, f"✨ DaskToon: {msg}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"DaskToon: {msg}")
            return {'CANCELLED'}


class DASKTOON_OT_reset_face_normals(Operator):
    """Clear custom split normals and reset mesh to default geometry normals"""
    bl_idname = "dasktoon.reset_face_normals"
    bl_label = "Reset to Default Normals"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        was_editmode = (obj.mode == 'EDIT')
        if was_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception:
            pass

        obj.data.update()

        if was_editmode:
            bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, f"Reset custom normals on '{obj.name}' to default.")
        return {'FINISHED'}


class DASKTOON_OT_toggle_face_normals_display(Operator):
    """Toggle Viewport display of Custom Split Normal vectors"""
    bl_idname = "dasktoon.toggle_face_normals_display"
    bl_label = "Toggle Normal Lines Display"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        space = context.space_data
        if space and space.type == 'VIEW_3D' and hasattr(space, 'overlay'):
            overlay = space.overlay
            if hasattr(overlay, 'show_split_normals'):
                overlay.show_split_normals = not overlay.show_split_normals
                state = "ON" if overlay.show_split_normals else "OFF"
                self.report({'INFO'}, f"Split Normals Display: {state}")
                return {'FINISHED'}

        self.report({'INFO'}, "Toggled Normal Display overlay.")
        return {'FINISHED'}


# =============================================================================
# Sidebar N-Panel: Anime Face Normal Studio
# =============================================================================

class DASKTOON_PT_face_normals(Panel):
    """Anime Face Normal Studio panel in 3D Viewport Sidebar"""
    bl_label = "🎭 Anime Face Normal Studio"
    bl_idname = "DASKTOON_PT_face_normals"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_order = 15

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        box = layout.box()
        box.label(text="Arc System Works / Hoyo Face Shading", icon='SHADING_RENDERED')

        if not obj or obj.type != 'MESH':
            box.label(text="Select a character Mesh to edit normals", icon='INFO')
            return

        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator("dasktoon.fix_face_normals", text="✨ Fix Face Normals (1-Click)", icon='SPHERE')

        box.separator()
        row = box.row(align=True)
        row.operator("dasktoon.reset_face_normals", text="Reset Normals", icon='LOOP_BACK')
        row.operator("dasktoon.toggle_face_normals_display", text="Normal Lines", icon='HIDE_OFF')


# =============================================================================
# Registration
# =============================================================================

classes = (
    DASKTOON_OT_fix_face_normals,
    DASKTOON_OT_reset_face_normals,
    DASKTOON_OT_toggle_face_normals_display,
    DASKTOON_PT_face_normals,
)


def register():
    for cls in classes:
        if not hasattr(cls, 'is_registered') or not cls.is_registered:
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
