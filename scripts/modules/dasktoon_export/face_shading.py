# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading for game engines (docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md, section 6):
the ellipsoid normals at rest are written as the mesh's custom normals for the FBX, then the mesh is given back as it
was (custom_normal and sharp_edge, which normals_split_custom_set may change)."""

from contextlib import contextmanager

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
import numpy as np

# Attribute data type -> (foreach key, values per element, numpy type)
_LAYOUTS = {
    'INT16_2D': ("value", 2, np.int32),
    'FLOAT_VECTOR': ("vector", 3, np.float32),
    'BOOLEAN': ("value", 1, bool),
}
_SAVED = ("custom_normal", "sharp_edge")


def face_shaded(objects):
    """Mesh objects whose Face Shading modifier is shown in the viewport, one per mesh data."""
    from bl_ui import dasktoon_face_shading_nodes as fsn
    found, seen = [], set()
    for obj in objects:
        modifier = fsn.get_modifier(obj) if obj.type == 'MESH' else None
        if modifier is None or not modifier.show_viewport or obj.data in seen:
            continue
        seen.add(obj.data)
        found.append(obj)
    return found


def _snapshot(mesh):
    saved = {}
    for name in _SAVED:
        attr = mesh.attributes.get(name)
        if attr is None:
            saved[name] = None
            continue
        key, width, dtype = _LAYOUTS[attr.data_type]
        values = np.empty(len(attr.data) * width, dtype=dtype)
        attr.data.foreach_get(key, values)
        saved[name] = (attr.domain, attr.data_type, values)
    return saved


def _supported(mesh):
    return all(mesh.attributes.get(name) is None or mesh.attributes[name].data_type in _LAYOUTS for name in _SAVED)


def _restore(mesh, saved):
    for name, value in saved.items():
        attr = mesh.attributes.get(name)
        if attr is not None:
            mesh.attributes.remove(attr)
        if value is not None:
            domain, data_type, values = value
            mesh.attributes.new(name, data_type, domain).data.foreach_set(_LAYOUTS[data_type][0], values)
    mesh.update()


def _armatures(objects):
    from bl_ui import dasktoon_face_shading as fs
    rigs = []
    for obj in objects:
        rigs.append(fs.find_armature(obj))
        proxy = fs.proxy_of(obj)
        if proxy is not None and proxy.parent is not None and proxy.parent.type == 'ARMATURE':
            rigs.append(proxy.parent)
    return [rig for rig in dict.fromkeys(rigs) if rig is not None]


@contextmanager
def _rest_state(objects):
    """Rest Position, the Basis shape only and nothing after Face Shading (face spec 6.2); restored even on error."""
    from bl_ui import dasktoon_face_shading as fs
    from bl_ui import dasktoon_face_shading_nodes as fsn
    keys = [(o, o.show_only_shape_key, o.active_shape_key_index) for o in objects if o.data.shape_keys is not None]
    hidden = []
    for obj in objects:
        index = obj.modifiers.find(fsn.MODIFIER_NAME)
        hidden += [m for m in list(obj.modifiers)[index + 1:] if m.show_viewport]
    try:
        for obj, _only, _index in keys:
            obj.show_only_shape_key = True
            obj.active_shape_key_index = 0
        for modifier in hidden:
            modifier.show_viewport = False
        with fs.rest_pose(_armatures(objects)):
            yield
    finally:
        for modifier in hidden:
            modifier.show_viewport = True
        for obj, only, index in keys:
            obj.show_only_shape_key = only
            obj.active_shape_key_index = index
        bpy.context.view_layer.update()


def _before_face_shading(obj):
    from bl_ui import dasktoon_face_shading_nodes as fsn
    names = []
    for modifier in obj.modifiers:
        if modifier.name == fsn.MODIFIER_NAME:
            break
        if modifier.type != 'ARMATURE':
            names.append(modifier.name)
    return names


def bake_rest_normals(context, objects):
    """Face spec 6.1-6.4: write the rest-pose face shading normals as custom normals of each face-shaded mesh.
    Returns (snapshots, names, warnings); always hand the snapshots to restore_normals() after the FBX."""
    targets, warnings = [], []
    for obj in face_shaded(objects):
        if obj.data.library is not None:
            warnings.append(rpt_("%s: mesh linked from a library, face shading not written") % obj.name)
        elif not _supported(obj.data):
            warnings.append(rpt_("%s: unusual custom normals, face shading not written") % obj.name)
        else:
            targets.append(obj)
    if not targets:
        return [], [], warnings
    normals = {}
    with _rest_state(targets):
        depsgraph = context.evaluated_depsgraph_get()
        for obj in targets:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            if len(mesh.loops) == len(obj.data.loops):
                values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
                mesh.corner_normals.foreach_get("vector", values)
                normals[obj] = values.reshape(-1, 3)
            else:
                warnings.append(rpt_("%s: modifier %s changes the vertex count before Face Shading; apply it before "
                                     "exporting. Face shading not written")
                                % (obj.name, ", ".join(_before_face_shading(obj)) or "?"))
            evaluated.to_mesh_clear()
    snapshots, names = [], []
    try:
        for obj, values in normals.items():
            snapshots.append((obj.data, _snapshot(obj.data)))
            obj.data.normals_split_custom_set(values)
            names.append(obj.name)
    except Exception:  # The caller gets no snapshots: give back what was already written, then report the error.
        restore_normals(snapshots)
        raise
    return snapshots, names, warnings


def restore_normals(snapshots):
    for mesh, saved in snapshots:
        _restore(mesh, saved)
