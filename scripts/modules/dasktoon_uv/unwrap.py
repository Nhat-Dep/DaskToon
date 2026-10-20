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
# Packing by the islands' exact shapes is the tightest but slow (20 to 80 s on the real characters); by their boxes
# takes seconds and leaves a few % more empty (pl1 89 -> 86 %, tdt 78 -> 71 %).
SHAPES = {True: 'CONCAVE', False: 'AABB'}
MIRROR_TOLERANCE = 0.001  # of the character's height: a vertex and its mirror
OLD = " Old"
HEAD = seams_.LABELS.index('HEAD')
MIRRORS = {seams_.LABELS.index(right): seams_.LABELS.index(left) for right, left in (
    ('ARM_R', 'ARM_L'), ('LEG_R', 'LEG_L'), ('HAND_R', 'HAND_L'), ('FOOT_R', 'FOOT_L'))}  # the right on the left
TOO_SMALL = 0.02  # an island whose pixels per area fall under this share of the usual one failed to unwrap


class Result(NamedTuple):
    labels: dict  # {obj: label of every face}
    mirrored: dict  # {(obj, right face): (obj, left face)}
    old: dict  # {obj: name of the old UV map, or None}
    sets: dict = {}  # {obj: set (index in sets.NAMES) of every face}, game texture sets only
    sizes: dict = {}  # {set name: image size}
    density: float = 0.0  # the Body and Hair sets' pixels per metre (the Face's is twice that)


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


def _area3(obj, faces):
    mesh = obj.data
    world = [obj.matrix_world @ v.co for v in mesh.vertices]
    total = 0.0
    for f in faces:
        corners = list(mesh.polygons[f].vertices)
        for k in range(1, len(corners) - 1):
            total += ((world[corners[k]] - world[corners[0]]).cross(world[corners[k + 1]] - world[corners[0]])).length / 2
    return total


def too_small(ratios):
    """The keys of {key: UV area over surface area} whose ratio is under TOO_SMALL of the median one."""
    usual = float(np.median(list(ratios.values()))) if ratios else 0.0
    return [key for key, ratio in ratios.items() if ratio <= TOO_SMALL * usual]


def failed_islands(meshes, labels, faces_of):
    """{obj: faces} of the groups Minimum Stretch could not solve: laid flat to nothing, or a speck beside the others
    (lr's thighs)."""
    ratios, faces = {}, {}
    for obj in meshes:
        uv = get_uv(obj)
        for k, group in enumerate(seams_.groups(obj.data, labels[obj], faces_of[obj])):
            surface = _area3(obj, group)
            if surface > 0:
                ratios[(obj, k)] = _area(uv, obj.data, group) / surface
                faces[(obj, k)] = group
    out = {obj: [] for obj in meshes}
    for obj, k in too_small(ratios):
        out[obj] += faces[(obj, k)]
    return out


def _material_keys(obj):
    indices = np.empty(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", indices)
    slots = [slot.material for slot in obj.material_slots]
    return [slots[i] if i < len(slots) else None for i in indices.tolist()]


def _share(meshes, keys, key, skip):
    """UV units per metre of the faces whose key is `key` (the mirrored right faces left out)."""
    uv_area = world_area = 0.0
    for obj in meshes:
        uv = get_uv(obj)
        faces = [f for f, k in enumerate(keys[obj]) if k == key and f not in skip[obj]]
        uv_area += _area(uv, obj.data, faces)
        world_area += _area3(obj, faces)
    return (uv_area / world_area) ** 0.5 if world_area > 0 else 0.0


BIG_SHARE = 0.7  # the largest islands making up this share of a set's area stay upright and in place


def _pin(obj, faces):
    """Pin the UV corners of `faces` (and unpin the others)."""
    layer = obj.data.uv_layers.active
    layer.pin_ensure()
    flags = np.zeros(len(obj.data.loops), dtype=bool)
    for f in faces:
        flags[list(obj.data.polygons[f].loop_indices)] = True
    layer.pin.foreach_set("value", flags)


def _pack_upright(context, meshes, keys, key, skip, tight, margin, labels, faces_of):
    """Pack a set with its islands upright, then pack its small islands again round the large ones (locked), turned by
    quarter turns where that fits them better: the face, torso and limbs stay upright, the small pieces fill gaps."""
    _pack(context, meshes, keys, key, skip, tight, margin, rotate=False)
    islands = []
    for obj in meshes:
        uv = get_uv(obj)
        for group in seams_.groups(obj.data, labels[obj], faces_of[obj]):
            group = [f for f in group if keys[obj][f] == key and f not in skip[obj]]
            if group:
                islands.append((_area(uv, obj.data, group), obj, group))
    total = sum(area for area, _obj, _group in islands)
    if total <= 0 or len(islands) < 2:
        return
    big, running = {obj: [] for obj in meshes}, 0.0
    for area, obj, group in sorted(islands, key=lambda item: -item[0]):
        if running >= BIG_SHARE * total:
            break
        big[obj] += group
        running += area
    for obj in meshes:
        _pin(obj, big[obj])
    for obj in meshes:
        select_faces(obj, [f for f, k in enumerate(keys[obj]) if k == key and f not in skip[obj]])
    with editing(context, meshes):
        bpy.ops.uv.pack_islands(rotate=True, rotate_method='CARDINAL', scale=True, margin_method='FRACTION',
                                margin=margin, pin=True, pin_method='LOCKED', shape_method=SHAPES[tight])
    for obj in meshes:
        _pin(obj, [])


def _pack(context, meshes, keys, key, skip, tight, margin, rotate):
    for obj in meshes:
        select_faces(obj, [f for f, k in enumerate(keys[obj]) if k == key and f not in skip[obj]])
    with editing(context, meshes):
        bpy.ops.uv.pack_islands(rotate=rotate, scale=True, margin_method='FRACTION', margin=margin,
                                shape_method=SHAPES[tight])


def unwrap(context, meshes, rig=None, tight=True, sets=False):
    """The anime unwrap of `meshes` (mesh objects) into new UV maps; see the module. `tight`: pack by the islands'
    exact shapes (slow) rather than by their boxes. `sets` (with a rig): game texture sets (sets.py), one square per
    set, islands upright, sizes by one sharpness."""
    from . import sets as sets_
    if context.active_object is not None and context.active_object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')  # UV maps and seams are written to the mesh, not to Edit Mode's copy
    meshes = [obj for obj in meshes if obj.type == 'MESH' and len(obj.data.polygons)]
    if not meshes:
        return Result({}, {}, {})
    analysis = None
    if rig is not None and not all((regions.read(obj) >= 0).any() for obj in meshes):
        analysis = regions.analyse(context, rig, list(rig.data.dasktoon_rig.parts))
    sets = bool(sets and rig is not None)
    labels, faces_of, old, face_set = {}, {}, {}, {}
    for obj in meshes:
        cut, labels[obj] = seams_.seams(context, obj, rig, analysis)
        if sets:
            face_set[obj] = sets_.face_sets(obj, rig, labels[obj])
            sets_.split_materials(obj, face_set[obj])
        mesh = obj.data
        flags = np.zeros(len(mesh.edges), dtype=bool)
        flags[list(cut)] = True
        mesh.edges.foreach_set("use_seam", flags)
        faces_of[obj] = seams_._edge_faces(mesh)
        old[obj] = new_uv_map(obj)
    with editing(context, meshes):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', fill_holes=True, margin=0.0)
    failed = failed_islands(meshes, labels, faces_of)
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
        if sets:
            sets_.stand_upright(obj, labels[obj], faces_of[obj], rig)  # the sets' sizes give the face its pixels
        else:
            scale_head(obj, labels[obj], faces_of[obj])

    frame = rig.matrix_world if rig is not None else Matrix.Identity(4)
    zs = np.concatenate([[(obj.matrix_world @ v.co).z for v in obj.data.vertices] for obj in meshes])
    height = float(zs.max() - zs.min()) or 1.0
    mirrored, mirrors = {}, {}
    for obj in meshes:
        pairs, vertex_mirror = mirror_pairs(obj, labels[obj], faces_of[obj], frame, height)
        mirrors[obj] = (pairs, vertex_mirror)
        mirrored.update({(obj, face): (obj, other) for face, other in pairs.items()})

    skip = {obj: set(mirrors[obj][0]) for obj in meshes}
    sizes, density = {}, 0.0
    if sets:
        keys = {obj: face_set[obj].tolist() for obj in meshes}
        present = sorted({k for obj in meshes for k in keys[obj]})
        for key in present:  # upright islands; the small ones may turn to fill gaps
            _pack_upright(context, meshes, keys, key, skip, tight, MARGIN, labels, faces_of)
        shares = {sets_.NAMES[k]: _share(meshes, keys, k, skip) for k in present}
        wanted = {name: (sets_.FACE_SHARPNESS if name == 'FACE' else 1.0) for name in shares}
        # One sharpness for the character; the set that needs the most pixels for it gets the largest size.
        density = sets_.MAX_SIZE * min(share / wanted[name] for name, share in shares.items() if share > 0)
        for key in present:
            name = sets_.NAMES[key]
            sizes[name] = sets_.size_for(density * wanted[name], shares[name])
            if sizes[name] < sets_.MAX_SIZE:  # the gap between islands in pixels of the set's own size
                _pack_upright(context, meshes, keys, key, skip, tight, sets_.MARGIN_PIXELS / sizes[name], labels,
                              faces_of)
    else:
        keys = {obj: _material_keys(obj) for obj in meshes}
        for material in {key for obj in meshes for key in keys[obj]}:
            _pack(context, meshes, keys, material, skip, tight, MARGIN, rotate=True)
    for obj in meshes:
        copy_mirrored(obj, *mirrors[obj])
        select_faces(obj, [])
    return Result(labels, mirrored, old, face_set, sizes, density)
