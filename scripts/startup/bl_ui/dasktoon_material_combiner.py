# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
import numpy as np
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    IntProperty,
    EnumProperty,
    BoolProperty,
    StringProperty,
)


# =============================================================================
# Helper: Material Color & Texture Extraction
# =============================================================================

def extract_material_base_color(mat):
    """Extracts representative RGBA color by tracing the active Surface output node or viewport color."""
    if not mat:
        return (0.8, 0.8, 0.8, 1.0)

    if mat.node_tree:
        # Find active Output Material node
        out_node = None
        for n in mat.node_tree.nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and getattr(n, 'is_active_output', False):
                out_node = n
                break
        if not out_node:
            for n in mat.node_tree.nodes:
                if n.bl_idname == 'ShaderNodeOutputMaterial':
                    out_node = n
                    break

        if out_node and out_node.inputs['Surface'].is_linked:
            from_node = out_node.inputs['Surface'].links[0].from_node
            if from_node.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel', 'ShaderNodeBsdfPrincipled'} and 'Base Color' in from_node.inputs:
                return tuple(from_node.inputs['Base Color'].default_value)
            elif from_node.bl_idname in {'ShaderNodeBsdfDiffuse', 'ShaderNodeEmission'} and 'Color' in from_node.inputs:
                return tuple(from_node.inputs['Color'].default_value)

        # Secondary search across all nodes
        for node in mat.node_tree.nodes:
            if node.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'} and 'Base Color' in node.inputs:
                return tuple(node.inputs['Base Color'].default_value)
            elif node.bl_idname == 'ShaderNodeBsdfPrincipled' and 'Base Color' in node.inputs:
                return tuple(node.inputs['Base Color'].default_value)
            elif node.bl_idname in {'ShaderNodeBsdfDiffuse', 'ShaderNodeEmission'} and 'Color' in node.inputs:
                return tuple(node.inputs['Color'].default_value)

    # Viewport color fallback
    if hasattr(mat, 'diffuse_color'):
        return tuple(mat.diffuse_color)

    return (0.8, 0.8, 0.8, 1.0)


# =============================================================================
# Core Algorithm: Ultra-Fast Vectorized UV Atlas Rasterization & Dilation
# =============================================================================

def rasterize_triangle_to_buffer(img_array, uv0, uv1, uv2, color, width, height):
    """Rasterizes a 2D UV triangle into the pixel buffer."""
    p0 = np.array([uv0[0] * (width - 1), uv0[1] * (height - 1)])
    p1 = np.array([uv1[0] * (width - 1), uv1[1] * (height - 1)])
    p2 = np.array([uv2[0] * (width - 1), uv2[1] * (height - 1)])

    min_x = max(0, int(np.floor(min(p0[0], p1[0], p2[0]))))
    max_x = min(width - 1, int(np.ceil(max(p0[0], p1[0], p2[0]))))
    min_y = max(0, int(np.floor(min(p0[1], p1[1], p2[1]))))
    max_y = min(height - 1, int(np.ceil(max(p0[1], p1[1], p2[1]))))

    if min_x > max_x or min_y > max_y:
        return

    xv, yv = np.meshgrid(np.arange(min_x, max_x + 1), np.arange(min_y, max_y + 1))
    pts = np.stack([xv, yv], axis=-1)

    def edge_fun(a, b, c):
        return (b[0] - a[0]) * (c[..., 1] - a[1]) - (b[1] - a[1]) * (c[..., 0] - a[0])

    area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
    w0 = edge_fun(p0, p1, pts)
    w1 = edge_fun(p1, p2, pts)
    w2 = edge_fun(p2, p0, pts)

    if area >= 0:
        mask = (w0 >= -0.5) & (w1 >= -0.5) & (w2 >= -0.5)
    else:
        mask = (w0 <= 0.5) & (w1 <= 0.5) & (w2 <= 0.5)

    if np.any(mask):
        img_array[yv[mask], xv[mask]] = color


def dilate_atlas(img_array, passes=8):
    """Expands colored pixels outward into transparent border areas to eliminate UV seams."""
    h, w, c = img_array.shape
    valid = img_array[..., 3] > 0.001

    for _ in range(passes):
        unpainted = ~valid
        up = np.roll(valid, -1, axis=0)
        down = np.roll(valid, 1, axis=0)
        left = np.roll(valid, -1, axis=1)
        right = np.roll(valid, 1, axis=1)
        neighbor_valid = up | down | left | right
        to_fill = unpainted & neighbor_valid
        if not np.any(to_fill):
            break
        new_colors = np.zeros_like(img_array)
        counts = np.zeros((h, w, 1), dtype=np.float32)
        for shift_arr, mask_dir in [
            (np.roll(img_array, -1, axis=0), up),
            (np.roll(img_array, 1, axis=0), down),
            (np.roll(img_array, -1, axis=1), left),
            (np.roll(img_array, 1, axis=1), right),
        ]:
            m = to_fill & mask_dir
            new_colors[m] += shift_arr[m]
            counts[m] += 1.0
        counts = np.maximum(counts, 1.0)
        img_array[to_fill] = new_colors[to_fill] / counts[to_fill]
        valid = valid | to_fill


# =============================================================================
# Main Combiner Routine
# =============================================================================

def combine_object_materials(obj, resolution=2048, margin=8, mode='SINGLE'):
    """Bakes & consolidates all material slots into a single Dask Shader BSDF material."""
    if not obj or obj.type != 'MESH':
        return False, "Selected object is not a Mesh."

    me = obj.data
    slot_count = len(obj.material_slots)
    if slot_count <= 1:
        return False, f"Object only has {slot_count} material slot(s). No consolidation needed."

    was_editmode = (obj.mode == 'EDIT')

    # 1. Ensure UV Map exists (auto-generate Smart UV Project if none)
    if not me.uv_layers:
        if not was_editmode:
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
        if not was_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')
        me.update()
    if was_editmode:
        bpy.ops.object.mode_set(mode='OBJECT')

    # 2. Backup Original Material Names & Face Assignments
    orig_materials = [slot.material.name if slot.material else "" for slot in obj.material_slots]
    orig_face_indices = [poly.material_index for poly in me.polygons]
    obj["dasktoon_orig_materials"] = orig_materials
    obj["dasktoon_orig_face_indices"] = orig_face_indices

    # 3. Extract colors for each material slot
    slot_colors = [extract_material_base_color(slot.material) for slot in obj.material_slots]

    # 4. Prepare Atlas Image Buffer
    width = resolution
    height = resolution
    img_array = np.zeros((height, width, 4), dtype=np.float32)

    # 5. Extract UV loops and rasterize polygons
    uv_layer = me.uv_layers.active.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bm_uv = bm.loops.layers.uv.active

    for face in bm.faces:
        mat_idx = face.material_index
        if 0 <= mat_idx < len(slot_colors):
            color = slot_colors[mat_idx]
        else:
            color = (0.8, 0.8, 0.8, 1.0)

        loops = face.loops
        if len(loops) < 3:
            continue

        # Fan triangulation for n-gons
        uv0 = tuple(loops[0][bm_uv].uv)
        for i in range(1, len(loops) - 1):
            uv1 = tuple(loops[i][bm_uv].uv)
            uv2 = tuple(loops[i + 1][bm_uv].uv)
            rasterize_triangle_to_buffer(img_array, uv0, uv1, uv2, color, width, height)

    bm.free()

    # 6. Apply UV Dilation / Padding to prevent seam artifacts
    if margin > 0:
        dilate_atlas(img_array, passes=margin)

    # 7. Create or update Image Datablock
    atlas_name = f"{obj.name}_Atlas"
    img = bpy.data.images.get(atlas_name)
    if not img or img.size[0] != width or img.size[1] != height:
        img = bpy.data.images.new(name=atlas_name, width=width, height=height, alpha=True)
    img.pixels.foreach_set(img_array.ravel())
    img.update()

    # 8. Create Consolidated Dask Shader BSDF Material
    cons_mat_name = f"{obj.name}_Consolidated_DaskToon"
    cons_mat = bpy.data.materials.get(cons_mat_name)
    if not cons_mat:
        cons_mat = bpy.data.materials.new(name=cons_mat_name)
    cons_mat.use_nodes = True
    nt = cons_mat.node_tree
    nt.nodes.clear()

    out_node = nt.nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (550, 0)

    dask_node = nt.nodes.new('ShaderNodeAnimeCharacter')
    dask_node.location = (200, 0)

    # Shadow Tint Multiply node so shadow color dynamically matches atlas colors
    mix_node = nt.nodes.new('ShaderNodeMix')
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs['Factor'].default_value = 1.0
    mix_node.inputs[7].default_value = (0.65, 0.55, 0.65, 1.0)  # Anime cool shadow tint
    mix_node.location = (-50, -140)

    tex_node = nt.nodes.new('ShaderNodeTexImage')
    tex_node.image = img
    tex_node.location = (-300, 0)

    uv_node = nt.nodes.new('ShaderNodeUVMap')
    uv_node.location = (-520, 0)

    nt.links.new(uv_node.outputs['UV'], tex_node.inputs['Vector'])
    nt.links.new(tex_node.outputs['Color'], dask_node.inputs['Base Color'])
    nt.links.new(tex_node.outputs['Color'], mix_node.inputs[6])
    nt.links.new(mix_node.outputs['Result'], dask_node.inputs['Shadow Color'])
    nt.links.new(dask_node.outputs['BSDF'], out_node.inputs['Surface'])

    # 9. Clear all material slots and assign single consolidated material
    obj.data.materials.clear()
    obj.data.materials.append(cons_mat)

    for poly in me.polygons:
        poly.material_index = 0

    me.update()

    if was_editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    return True, f"Consolidated {slot_count} materials into 1 single Master Material using '{atlas_name}' ({width}x{height})!"


def restore_object_materials(obj):
    """Restores original material slots and polygon assignments from backup."""
    if not obj or obj.type != 'MESH':
        return False, "Selected object is not a Mesh."

    if "dasktoon_orig_materials" not in obj or "dasktoon_orig_face_indices" not in obj:
        return False, "No backup of original materials found on this object."

    orig_mat_names = list(obj["dasktoon_orig_materials"])
    orig_face_indices = list(obj["dasktoon_orig_face_indices"])

    was_editmode = (obj.mode == 'EDIT')
    if was_editmode:
        bpy.ops.object.mode_set(mode='OBJECT')

    me = obj.data
    me.materials.clear()

    for mat_name in orig_mat_names:
        mat = bpy.data.materials.get(mat_name)
        if mat:
            me.materials.append(mat)
        else:
            # Fallback placeholder if material was deleted
            placeholder = bpy.data.materials.new(name=mat_name or "Restored_Material")
            me.materials.append(placeholder)

    for i, poly in enumerate(me.polygons):
        if i < len(orig_face_indices):
            poly.material_index = orig_face_indices[i]

    me.update()

    if was_editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    return True, f"Restored {len(orig_mat_names)} original material slots on '{obj.name}'!"


# =============================================================================
# Operators
# =============================================================================

class DASKTOON_OT_combine_materials(Operator):
    """Bake & consolidate all material slots into 1 single Master Dask Shader BSDF material (Ultra-Fast Viewport Optimization)"""
    bl_idname = "dasktoon.combine_materials"
    bl_label = "Combine & Optimize Materials"
    bl_options = {'REGISTER', 'UNDO'}

    resolution: EnumProperty(
        name="Resolution",
        description="Atlas Texture Resolution",
        items=[
            ('1024', "1024 x 1024", "Standard (Lightweight)"),
            ('2048', "2048 x 2048", "High Quality (Recommended for Anime)"),
            ('4096', "4096 x 4096", "Ultra High (Cinematic Crisp)"),
        ],
        default='2048',
    )
    margin: IntProperty(
        name="UV Margin Bleed",
        description="Expand pixel boundaries to eliminate UV seams",
        default=8,
        min=0,
        max=32,
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        res_val = int(self.resolution)
        success, msg = combine_object_materials(obj, resolution=res_val, margin=self.margin)

        if success:
            self.report({'INFO'}, f"✨ DaskToon: {msg}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"DaskToon: {msg}")
            return {'CANCELLED'}


class DASKTOON_OT_restore_materials(Operator):
    """Restore original multi-material slots from safe backup"""
    bl_idname = "dasktoon.restore_materials"
    bl_label = "Restore Original Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        success, msg = restore_object_materials(obj)
        if success:
            self.report({'INFO'}, f"✨ DaskToon: {msg}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"DaskToon: {msg}")
            return {'CANCELLED'}


# =============================================================================
# Sidebar N-Panel: Material Optimizer & Combiner
# =============================================================================

class DASKTOON_PT_material_combiner(Panel):
    """Material Optimizer & Combiner panel in 3D Viewport Sidebar"""
    bl_label = "🎨 Material Optimizer & Combiner"
    bl_idname = "DASKTOON_PT_material_combiner"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_order = 18

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        box = layout.box()
        box.label(text="Consolidate Multiple Slots to 1 Master Shader", icon='MATERIAL')

        if not obj or obj.type != 'MESH':
            box.label(text="Select a Mesh to optimize materials", icon='INFO')
            return

        slot_count = len(obj.material_slots)
        row = box.row()
        row.label(text=f"Current Slots: {slot_count}", icon='RESTRICT_VIEW_OFF')
        if slot_count > 1:
            row.label(text="➔ Target: 1 Slot", icon='CHECKMARK')

        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator("dasktoon.combine_materials", text="✨ Combine Materials (1-Click)", icon='IMAGE_ZDEPTH')

        if "dasktoon_orig_materials" in obj:
            box.separator()
            box.operator("dasktoon.restore_materials", text="🔄 Restore Original Slots", icon='LOOP_BACK')


# =============================================================================
# Registration
# =============================================================================

classes = (
    DASKTOON_OT_combine_materials,
    DASKTOON_OT_restore_materials,
    DASKTOON_PT_material_combiner,
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
