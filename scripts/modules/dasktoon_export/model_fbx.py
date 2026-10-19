# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""FBX model for Unity (spec 4). Modifiers are not applied, so shape keys survive and the Geometry Nodes outline
hull stays out of the file; Unity draws the outline in the shader from DT_OutlineN/W."""

from contextlib import contextmanager

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

EXPORT_TYPES = {'ARMATURE', 'MESH', 'EMPTY'}
FBX_SETTINGS = dict(
    use_mesh_modifiers=False,
    axis_forward='-Z',
    axis_up='Y',
    apply_scale_options='FBX_SCALE_ALL',
    add_leaf_bones=False,
    use_armature_deform_only=True,
    mesh_smooth_type='FACE',
    object_types=EXPORT_TYPES,
    path_mode='STRIP',
    embed_textures=False,
)


def export_objects(context, selected_only):
    """The selection (plus the armatures deforming it), or every visible armature, mesh and empty."""
    if not selected_only:
        return [o for o in context.scene.objects if o.type in EXPORT_TYPES and o.visible_get()]
    chosen = [o for o in context.selected_objects if o.type in EXPORT_TYPES]
    for obj in list(chosen):
        rigs = [m.object for m in getattr(obj, "modifiers", ()) if m.type == 'ARMATURE' and m.object is not None]
        if obj.parent is not None and obj.parent.type == 'ARMATURE':
            rigs.append(obj.parent)
        chosen += [rig for rig in rigs if rig not in chosen]
    return chosen


def outline_meshes(objects):
    from bl_ui import dasktoon_outline as outline
    return [o for o in objects if o.type == 'MESH'
            and any(outline.find_source(slot.material) is not None for slot in o.material_slots)]


def prepare_outline_data(objects):
    """DT_OutlineN/W on every outlined mesh (project 1, spec 5). Returns (names written, error messages)."""
    from bl_ui import dasktoon_outline_gamedata as gamedata
    done, errors, seen = [], [], set()
    for obj in outline_meshes(objects):
        if obj.data in seen:
            continue
        seen.add(obj.data)
        if obj.data.library is not None:
            errors.append(rpt_("%s: mesh linked from a library, outline data not written") % obj.name)
            continue
        try:
            ok, message = gamedata.write_outline_uvs(obj)
        except Exception as ex:  # e.g. the mesh already has Blender's maximum of 8 UV maps
            ok, message = False, rpt_("%s: outline data not written (%s)") % (obj.name, ex)
        if ok:
            done.append(obj.name)
        else:
            errors.append(message)
    return done, errors


def modifier_notes(objects):
    """Modifiers other than Armature, the DaskToon outline, face shading and the fast action are not in the FBX (Apply
    Modifiers is off; face shading is written as normals; the fast action is DaskToon's own, its popover says so)."""
    from bl_ui import dasktoon_face_shading_nodes as fsn
    from bl_ui import dasktoon_outline_nodes as gn
    from dasktoon_animation import fast_action
    notes = []
    for obj in objects:
        extra = [m.name for m in getattr(obj, "modifiers", ()) if m.type != 'ARMATURE'
                 and m.name not in (gn.MODIFIER_NAME, fsn.MODIFIER_NAME, fast_action.MODIFIER)]
        if obj.type == 'MESH' and extra:
            notes.append(rpt_("%s: modifiers %s are not applied in the FBX; apply them before exporting if needed")
                         % (obj.name, ", ".join(extra)))
    return notes


@contextmanager
def _without_region_layers(objects):
    """The anime rig's region layers (rig regions spec 7) out of the meshes of `objects` meanwhile, then back with their
    colors and the meshes' active and default colors: they are for painting in DaskToon, not Unity's vertex colors."""
    from dasktoon_rig import regions
    saved = []
    for obj in objects:
        mesh = obj.data if obj.type == 'MESH' else None
        layer = mesh.color_attributes.get(regions.LAYER) if mesh is not None else None
        if layer is None or any(mesh is other[0] for other in saved):
            continue
        colors = np.empty(len(layer.data) * 4, np.float32)
        layer.data.foreach_get("color", colors)
        layers = mesh.color_attributes
        saved.append((mesh, colors, layer.data_type, layer.domain, layers.active_color_name, layers.default_color_name))
        layers.remove(layer)
    try:
        yield
    finally:
        for mesh, colors, data_type, domain, active, default in saved:
            layer = mesh.color_attributes.new(regions.LAYER, data_type, domain)
            layer.data.foreach_set("color", colors)
            mesh.color_attributes.active_color_name = active
            mesh.color_attributes.default_color_name = default


def write_fbx(context, objects, filepath, include_animation, single_take=False):
    """Export `objects` with the fixed settings of spec 4; the user's selection and active object are restored.
    `single_take` bakes one take of the scene's frame range, named after the scene (a clip, clips spec 6), instead of a
    take per action. Returns the names of objects left out because they cannot be selected (e.g. in an excluded
    collection)."""
    view_layer = context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    left_out = []
    try:
        for obj in selected:
            obj.select_set(False)
        for obj in objects:
            try:
                obj.select_set(True)
            except RuntimeError:
                left_out.append(obj.name)
        takes = dict(bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False) if single_take else {}
        with _without_region_layers(objects):
            bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True, bake_anim=include_animation, **FBX_SETTINGS,
                                     **takes)
        return left_out
    finally:
        for obj in view_layer.objects:
            try:
                obj.select_set(obj in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active
