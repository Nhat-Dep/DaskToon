# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Outline data for game engines: smoothed normals (tangent space, octahedral) in DT_OutlineN
and the painted width mask in DT_OutlineW (spec section 5)."""

import bpy
import numpy as np
from bpy.types import Operator

from .dasktoon_outline import MASK_NAMES
from .dasktoon_outline_nodes import MODIFIER_NAME

UV_NORMAL = "DT_OutlineN"
UV_MASK = "DT_OutlineW"
SIG_PROP = "dt_outline_sig"
QUANT = 1e-5


def oct_encode(v):
    v = v / np.abs(v).sum(axis=1, keepdims=True)
    xy = v[:, :2].copy()
    neg = v[:, 2] < 0.0
    sign = np.where(xy[neg] >= 0.0, 1.0, -1.0)
    xy[neg] = (1.0 - np.abs(v[neg][:, [1, 0]])) * sign
    return xy


def oct_decode(e):
    n = np.column_stack([e[:, 0], e[:, 1], 1.0 - np.abs(e[:, 0]) - np.abs(e[:, 1])])
    t = np.clip(-n[:, 2], 0.0, None)
    n[:, 0] += np.where(n[:, 0] >= 0.0, -t, t)
    n[:, 1] += np.where(n[:, 1] >= 0.0, -t, t)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def _array(collection, attr, count, width, dtype=np.float64):
    raw_type = np.int32 if dtype in (np.int64, np.int32) else np.float32
    out = np.empty(count * width, dtype=raw_type)
    collection.foreach_get(attr, out)
    out = out.astype(dtype)
    return out.reshape(count, width) if width > 1 else out


def smoothed_vertex_normals(mesh):
    """Angle-weighted face normals summed over vertices that share a position (merges split seams)."""
    v_count, l_count, p_count = len(mesh.vertices), len(mesh.loops), len(mesh.polygons)
    co = _array(mesh.vertices, "co", v_count, 3)
    corner_vert = _array(mesh.loops, "vertex_index", l_count, 1, np.int64)
    loop_start = _array(mesh.polygons, "loop_start", p_count, 1, np.int64)
    loop_total = _array(mesh.polygons, "loop_total", p_count, 1, np.int64)
    poly_normal = _array(mesh.polygons, "normal", p_count, 3)
    corner_poly = np.repeat(np.arange(p_count), loop_total)
    k = np.arange(l_count) - loop_start[corner_poly]
    total = loop_total[corner_poly]
    prev_corner = loop_start[corner_poly] + (k - 1) % total
    next_corner = loop_start[corner_poly] + (k + 1) % total
    here = co[corner_vert]
    e1 = co[corner_vert[prev_corner]] - here
    e2 = co[corner_vert[next_corner]] - here
    angle = np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), (e1 * e2).sum(axis=1))
    keys = np.round(co / QUANT).astype(np.int64)
    _unique, group = np.unique(keys, axis=0, return_inverse=True)
    group = group.reshape(-1)
    acc = np.zeros((group.max() + 1, 3))
    np.add.at(acc, group[corner_vert], poly_normal[corner_poly] * angle[:, None])
    acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    return acc[group]


def _mask_per_vertex(obj):
    name = next((n for n in MASK_NAMES if n in obj.vertex_groups), None)
    weights = np.ones(len(obj.data.vertices))
    if name is None:
        return weights
    index = obj.vertex_groups[name].index
    weights[:] = 0.0
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == index:
                weights[v.index] = g.weight
    return weights


def _ensure_layer(mesh, name):
    layer = mesh.uv_layers.get(name)
    return layer if layer is not None else mesh.uv_layers.new(name=name, do_init=False)


def write_outline_uvs(obj):
    mesh = obj.data
    if not mesh.uv_layers:
        return False, "%s: cần ít nhất một UV map" % obj.name
    if any(p.loop_total > 4 for p in mesh.polygons):
        return False, "%s: có mặt nhiều hơn 4 cạnh (ngon); hãy Triangulate hoặc chia lại trước" % obj.name
    uv0 = mesh.uv_layers[0].name
    active_name = mesh.uv_layers.active.name
    render_name = next(uv.name for uv in mesh.uv_layers if uv.active_render)
    l_count = len(mesh.loops)
    mesh.calc_tangents(uvmap=uv0)
    tangent = _array(mesh.loops, "tangent", l_count, 3)
    sign = _array(mesh.loops, "bitangent_sign", l_count, 1)
    normal = np.array([c.vector for c in mesh.corner_normals], dtype=np.float64)
    mesh.free_tangents()
    bitangent = sign[:, None] * np.cross(normal, tangent)
    corner_vert = _array(mesh.loops, "vertex_index", l_count, 1, np.int64)
    smooth = smoothed_vertex_normals(mesh)[corner_vert]
    n_ts = np.column_stack([(smooth * tangent).sum(1), (smooth * bitangent).sum(1), (smooth * normal).sum(1)])
    n_ts /= np.maximum(np.linalg.norm(n_ts, axis=1, keepdims=True), 1e-12)
    encoded = oct_encode(n_ts).astype(np.float32)
    mask = np.zeros((l_count, 2), dtype=np.float32)
    mask[:, 0] = _mask_per_vertex(obj)[corner_vert]
    _ensure_layer(mesh, UV_NORMAL).uv.foreach_set("vector", encoded.ravel())
    _ensure_layer(mesh, UV_MASK).uv.foreach_set("vector", mask.ravel())
    mesh.uv_layers.active = mesh.uv_layers[active_name]
    mesh.uv_layers[render_name].active_render = True
    mesh[SIG_PROP] = _signature(mesh)
    return True, "%s: đã ghi %s và %s" % (obj.name, UV_NORMAL, UV_MASK)


def _signature(mesh):
    # ID property arrays cannot hold strings, so the signature is a small dict.
    return {"vertices": len(mesh.vertices), "corners": len(mesh.loops), "uv0": mesh.uv_layers[0].name}


def is_outline_data_stale(mesh):
    sig = mesh.get(SIG_PROP)
    if sig is None or not mesh.uv_layers:
        return True
    return sig.to_dict() != _signature(mesh)


class DASKTOON_OT_outline_prepare_game_data(Operator):
    """Write smoothed outline normals and the width mask into real UV maps for game export"""
    bl_idname = "dasktoon.outline_prepare_game_data"
    bl_label = "Chuẩn bị outline cho game"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objects = [o for o in context.selected_objects if o.type == 'MESH']
        if not objects:
            objects = [o for o in context.scene.objects if o.type == 'MESH' and o.modifiers.get(MODIFIER_NAME)]
        done, errors, seen = 0, [], set()
        for obj in objects:
            if obj.data in seen or obj.data.library is not None:
                continue
            seen.add(obj.data)
            ok, msg = write_outline_uvs(obj)
            if ok:
                done += 1
            else:
                errors.append(msg)
        for msg in errors:
            self.report({'WARNING'}, msg)
        self.report({'INFO'}, "Đã chuẩn bị %d mesh, %d lỗi" % (done, len(errors)))
        return {'FINISHED'} if done else {'CANCELLED'}


classes = (DASKTOON_OT_outline_prepare_game_data,)
