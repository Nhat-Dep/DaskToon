# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The anime unwrap (spec section 2, steps 3 to 7): seams from seams.py, Blender's Minimum Stretch unwrap on a new UV
map (the old one kept as "<name> Old"), even pixels then the head's islands 1.5 times larger, the right arm, leg and
their clothes laid on the left ones when the mesh mirrors, every material's faces packed together by their shape."""

import contextlib
from typing import NamedTuple

import bpy
import numpy as np
from mathutils import Matrix
from mathutils.kdtree import KDTree

from dasktoon_rig import regions

from . import seams as seams_

HEAD_SCALE = 1.5  # the face gets 1.5 times the pixels across (spec, ruling 3)
MARGIN = 0.004  # about 8 pixels at 2048: room for a game's mipmaps, still tight
MIRROR_TOLERANCE = 0.001  # of the character's height: a vertex and its mirror
OLD = " Old"
HEAD = regions.REGIONS.index('HEAD')
MIRRORS = {regions.REGIONS.index('ARM_R'): regions.REGIONS.index('ARM_L'),
           regions.REGIONS.index('LEG_R'): regions.REGIONS.index('LEG_L')}  # the character's right on its left


class Result(NamedTuple):
    labels: dict  # {obj: label of every face}
    mirrored: dict  # {(obj, right face): (obj, left face)}
    old: dict  # {obj: name of the old UV map, or None}


def get_uv(obj):
    data = obj.data.uv_layers.active.data
    out = np.empty(len(data) * 2, dtype=np.float32)
    data.foreach_get("uv", out)
    return out.reshape(-1, 2)


def set_uv(obj, uv):
    obj.data.uv_layers.active.data.foreach_set("uv", np.asarray(uv, dtype=np.float32).ravel())


@contextlib.contextmanager
def editing(context, meshes):
    """Edit Mode on `meshes` together (UV selection following the faces), then back as it was."""
    view_layer = context.view_layer
    active = view_layer.objects.active
    selected = [obj for obj in view_layer.objects if obj.select_get()]
    modes = {obj: obj.mode for obj in meshes}
    settings = context.scene.tool_settings
    sync = settings.use_uv_select_sync
    for obj in view_layer.objects:
        obj.select_set(obj in meshes)
    view_layer.objects.active = meshes[0]
    if meshes[0].mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    settings.use_uv_select_sync = True
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        yield
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        settings.use_uv_select_sync = sync
        for obj in view_layer.objects:
            obj.select_set(obj in selected)
        view_layer.objects.active = active
        if active is not None and modes.get(active, 'OBJECT') not in ('OBJECT', 'EDIT'):
            bpy.ops.object.mode_set(mode=modes[active])


def select_faces(obj, chosen):
    mesh = obj.data
    flags = np.zeros(len(mesh.polygons), dtype=bool)
    flags[list(chosen)] = True
    mesh.polygons.foreach_set("select", flags)
    verts = np.zeros(len(mesh.vertices), dtype=bool)
    for f in np.nonzero(flags)[0].tolist():
        verts[list(mesh.polygons[f].vertices)] = True
    mesh.vertices.foreach_set("select", verts)
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    mesh.edges.foreach_set("select", verts[edges[:, 0]] & verts[edges[:, 1]])


def new_uv_map(obj):
    """A new UV map, active and rendered; the old one (if any) renamed "<name> Old". Returns the old name or None."""
    layers = obj.data.uv_layers
    if not len(layers):
        layer = layers.new(name="UVMap")
        old = None
    else:
        previous = layers.active
        name = previous.name
        previous.name = name + OLD
        old = previous.name
        layer = layers.new(name=name)
    layers.active = layer
    layer.active_render = True
    return old


def scale_head(obj, labels, faces_of):
    """The head's islands HEAD_SCALE times larger, each about its own middle."""
    uv = get_uv(obj)
    mesh = obj.data
    for group in seams_.groups(mesh, labels, faces_of):
        if labels[group[0]] != HEAD:
            continue
        loops = [loop for f in group for loop in mesh.polygons[f].loop_indices]
        middle = uv[loops].mean(axis=0)
        uv[loops] = middle + (uv[loops] - middle) * HEAD_SCALE
    set_uv(obj, uv)


def mirror_pairs(obj, labels, faces_of, frame, height):
    """{right face: left face} for the right arm and leg groups whose every face has a mirrored face on the left, and
    {vertex: its mirror} for their vertices."""
    mesh = obj.data
    to_frame = frame.inverted() @ obj.matrix_world
    local = np.array([to_frame @ v.co for v in mesh.vertices])
    tree = KDTree(len(local))
    for i, co in enumerate(local):
        tree.insert(co, i)
    tree.balance()
    tolerance = MIRROR_TOLERANCE * height
    by_vertices = {frozenset(p.vertices): p.index for p in mesh.polygons if labels[p.index] in MIRRORS.values()}
    pairs, vertex_mirror = {}, {}
    for group in seams_.groups(mesh, labels, faces_of):
        side = labels[group[0]]
        if side not in MIRRORS:
            continue
        found, mirror = {}, {}
        for f in group:
            mapped = []
            for v in mesh.polygons[f].vertices:
                x, y, z = local[v]
                _co, index, distance = tree.find((-x, y, z))
                if index is None or distance > tolerance:
                    break
                mapped.append(index)
                mirror[v] = index
            other = by_vertices.get(frozenset(mapped)) if len(mapped) == len(mesh.polygons[f].vertices) else None
            if other is None or labels[other] != MIRRORS[side]:
                break
            found[f] = other
        else:
            pairs.update(found)
            vertex_mirror.update(mirror)
    return pairs, vertex_mirror


def copy_mirrored(obj, pairs, vertex_mirror):
    """The right faces' UVs from their left faces, corner by corner."""
    mesh = obj.data
    uv = get_uv(obj)
    for face, other in pairs.items():
        corner = {mesh.loops[loop].vertex_index: loop for loop in mesh.polygons[other].loop_indices}
        for loop in mesh.polygons[face].loop_indices:
            uv[loop] = uv[corner[vertex_mirror[mesh.loops[loop].vertex_index]]]
    set_uv(obj, uv)


def _area(uv, mesh, faces):
    total = 0.0
    for f in faces:
        loops = list(mesh.polygons[f].loop_indices)
        a = uv[loops[0]]
        for k in range(1, len(loops) - 1):
            b, c = uv[loops[k]], uv[loops[k + 1]]
            total += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
    return total


def failed_islands(obj, labels, faces_of):
    """Faces of the groups Minimum Stretch could not solve (laid flat to nothing)."""
    uv = get_uv(obj)
    out = []
    for group in seams_.groups(obj.data, labels, faces_of):
        if _area(uv, obj.data, group) < 1e-9:
            out += group
    return out


def _material_keys(obj):
    indices = np.empty(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", indices)
    slots = [slot.material for slot in obj.material_slots]
    return [slots[i] if i < len(slots) else None for i in indices.tolist()]


def unwrap(context, meshes, rig=None):
    """The anime unwrap of `meshes` (mesh objects) into new UV maps; see the module."""
    meshes = [obj for obj in meshes if obj.type == 'MESH' and len(obj.data.polygons)]
    if not meshes:
        return Result({}, {}, {})
    analysis = None
    if rig is not None and not all((regions.read(obj) >= 0).any() for obj in meshes):
        analysis = regions.analyse(context, rig, list(rig.data.dasktoon_rig.parts))
    labels, faces_of, old = {}, {}, {}
    for obj in meshes:
        cut, labels[obj] = seams_.seams(context, obj, rig, analysis)
        mesh = obj.data
        flags = np.zeros(len(mesh.edges), dtype=bool)
        flags[list(cut)] = True
        mesh.edges.foreach_set("use_seam", flags)
        faces_of[obj] = seams_._edge_faces(mesh)
        old[obj] = new_uv_map(obj)
    with editing(context, meshes):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', fill_holes=True, margin=0.0)
    failed = {obj: failed_islands(obj, labels[obj], faces_of[obj]) for obj in meshes}
    if any(failed.values()):  # Minimum Stretch gives up on some shapes: Angle Based for those
        for obj in meshes:
            select_faces(obj, failed[obj])
        with editing(context, meshes):
            bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, margin=0.0)
    for obj in meshes:
        select_faces(obj, range(len(obj.data.polygons)))
    with editing(context, meshes):
        bpy.ops.uv.average_islands_scale()
    for obj in meshes:
        scale_head(obj, labels[obj], faces_of[obj])

    frame = rig.matrix_world if rig is not None else Matrix.Identity(4)
    zs = np.concatenate([[(obj.matrix_world @ v.co).z for v in obj.data.vertices] for obj in meshes])
    height = float(zs.max() - zs.min()) or 1.0
    mirrored, mirrors = {}, {}
    for obj in meshes:
        pairs, vertex_mirror = mirror_pairs(obj, labels[obj], faces_of[obj], frame, height)
        mirrors[obj] = (pairs, vertex_mirror)
        mirrored.update({(obj, face): (obj, other) for face, other in pairs.items()})

    keys = {obj: _material_keys(obj) for obj in meshes}
    for material in {key for obj in meshes for key in keys[obj]}:
        for obj in meshes:
            right = mirrors[obj][0]
            select_faces(obj, [f for f, key in enumerate(keys[obj]) if key == material and f not in right])
        with editing(context, meshes):
            bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=MARGIN,
                                    shape_method='CONCAVE')
    for obj in meshes:
        copy_mirrored(obj, *mirrors[obj])
        select_faces(obj, [])
    return Result(labels, mirrored, old)
