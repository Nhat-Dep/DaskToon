# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""FBX model for Unity (spec 4). Modifiers are not applied, so shape keys survive and the Geometry Nodes outline
hull stays out of the file; Unity draws the outline in the shader from DT_OutlineN/W."""

import bpy

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
            errors.append("%s: mesh link từ thư viện, không ghi được dữ liệu outline" % obj.name)
            continue
        try:
            ok, message = gamedata.write_outline_uvs(obj)
        except Exception as ex:  # e.g. the mesh already has Blender's maximum of 8 UV maps
            ok, message = False, "%s: không ghi được dữ liệu outline (%s)" % (obj.name, ex)
        if ok:
            done.append(obj.name)
        else:
            errors.append(message)
    return done, errors


def modifier_notes(objects):
    """Modifiers other than Armature and the DaskToon outline are not in the FBX (Apply Modifiers is off)."""
    from bl_ui import dasktoon_outline_nodes as gn
    notes = []
    for obj in objects:
        extra = [m.name for m in getattr(obj, "modifiers", ()) if m.type != 'ARMATURE' and m.name != gn.MODIFIER_NAME]
        if obj.type == 'MESH' and extra:
            notes.append("%s: modifier %s không được áp dụng vào FBX; hãy Apply trước khi export nếu cần"
                         % (obj.name, ", ".join(extra)))
    return notes


def write_fbx(context, objects, filepath, include_animation):
    """Export `objects` with the fixed settings of spec 4; the user's selection and active object are restored.
    Returns the names of objects left out because they cannot be selected (e.g. in an excluded collection)."""
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
        bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True, bake_anim=include_animation, **FBX_SETTINGS)
        return left_out
    finally:
        for obj in view_layer.objects:
            try:
                obj.select_set(obj in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active
