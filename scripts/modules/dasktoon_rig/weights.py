# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Vertex weights of the anime rig (spec 5.2, 6.2): vertex groups read and written as matrices, the clean-up for Unity,
binding a mesh to the rig, Blender's automatic weights for the body, and weights copied from the body surface."""

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from . import chains, parts

LIMIT = 4
MINIMUM = 0.01
# A Clothing point up to this far from the Body (x the Body's height) copies the Body; twice as far or more it takes
# automatic weights of its own; in between, a blend (real model test: a dress over no skin copied shoulders 30 cm away).
CLOTH_GAP = 0.02


def read(obj, names):
    """Weights (vertices x len(names)) of obj in the vertex groups `names`; 0 where a vertex or group is missing."""
    columns = {}
    for j, name in enumerate(names):
        group = obj.vertex_groups.get(name)
        if group is not None:
            columns[group.index] = j
    out = np.zeros((len(obj.data.vertices), len(names)))
    if columns:
        for vertex in obj.data.vertices:
            for element in vertex.groups:
                j = columns.get(element.group)
                if j is not None:
                    out[vertex.index, j] = element.weight
    return out


def clear(obj, vertices, names):
    """Take `vertices` out of the vertex groups `names`."""
    indices = [int(i) for i in vertices]
    for name in names:
        group = obj.vertex_groups.get(name)
        if group is not None:
            group.remove(indices)


def write(obj, vertices, names, matrix):
    """Give vertices[i] the weight matrix[i, j] in the group names[j] (created on its first weight); zeros are left
    out. Weights the vertices had in other groups stay: clear them first."""
    vertices = np.asarray(vertices)
    for j, name in enumerate(names):
        column = matrix[:, j]
        rows = np.nonzero(column > 0.0)[0]
        if len(rows) == 0:
            continue
        group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        values = column[rows]
        if np.all(values == values[0]):
            group.add([int(i) for i in vertices[rows]], float(values[0]), 'REPLACE')
        else:
            for index, value in zip(vertices[rows].tolist(), values.tolist()):
                group.add([index], value, 'REPLACE')


def tidy(matrix, limit=LIMIT, minimum=MINIMUM):
    """Rows of `matrix` for Unity (spec 6.2 step 5): weights under `minimum` dropped, at most `limit` per row, summing
    to 1. A row whose weights are all under `minimum` keeps its largest one; an empty row stays empty."""
    out = np.where(matrix >= minimum, matrix, 0.0)
    if out.shape[1] > limit:
        drop = np.argsort(-out, axis=1, kind="stable")[:, limit:]
        np.put_along_axis(out, drop, 0.0, axis=1)
    lost = (out.sum(axis=1) <= 0.0) & (matrix.max(axis=1, initial=0.0) > 0.0)
    rows = np.nonzero(lost)[0]
    out[rows, matrix[rows].argmax(axis=1)] = 1.0
    sums = out.sum(axis=1)
    full = sums > 0.0
    out[full] /= sums[full, None]
    return out


def bind(rig, obj):
    """An Armature modifier on obj pointing at rig, right after the last Mirror modifier (so a half-modelled mesh is
    mirrored before it deforms) or else first; obj a child of rig where it is now (spec 6.2 step 3, 12)."""
    modifier = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
    if modifier is None:
        modifier = obj.modifiers.new("Armature", 'ARMATURE')
    modifier.object = rig
    stack = list(obj.modifiers)
    current = stack.index(modifier)
    mirrors = [i for i, m in enumerate(stack) if m.type == 'MIRROR']
    target = mirrors[-1] + 1 if mirrors else 0
    if target > current:
        target -= 1
    if target != current:
        obj.modifiers.move(current, target)
    if obj.parent != rig:
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = 'OBJECT'
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = world


def body_heat(context, rig, obj, body_bones):
    """Blender's automatic weights (bone heat, Object › Parent › With Automatic Weights) of obj from `body_bones`
    only: the other bones of rig have Deform off meanwhile. Selection, active object and Deform flags come back."""
    bones = rig.data.bones
    deform = {bone.name: bone.use_deform for bone in bones}
    view_layer = context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    try:
        for bone in bones:
            bone.use_deform = deform[bone.name] and bone.name in body_bones
        for o in selected:
            o.select_set(False)
        obj.select_set(True)
        rig.select_set(True)
        view_layer.objects.active = rig
        bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)
    finally:
        for bone in bones:
            bone.use_deform = deform[bone.name]
        for o in view_layer.objects:
            o.select_set(o in selected)
        view_layer.objects.active = active


def _barycentric(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-18:
        return np.array([1.0, 0.0, 0.0])
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    out = np.clip(np.array([1.0 - v - w, v, w]), 0.0, None)
    return out / out.sum()


def heat_of_copy(context, rig, obj, body_bones):
    """Automatic weights (vertices x len(body_bones)) of obj from `body_bones`, worked out on a copy so obj keeps its
    weights; a row is empty where bone heat finds no solution."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    context.scene.collection.objects.link(copy)
    try:
        clear(copy, range(len(copy.data.vertices)), body_bones)
        body_heat(context, rig, copy, set(body_bones))
        return read(copy, body_bones)
    finally:
        mesh = copy.data
        bpy.data.objects.remove(copy)
        bpy.data.meshes.remove(mesh)


def clothing_weights(context, rig, sources, names, obj, vertices):
    """Weights (len(vertices) x len(names)) of Clothing vertices of obj (spec 5.2): copied from the Body surface where
    it is near (CLOTH_GAP), automatic weights of the clothing itself where it is far, a blend in between."""
    world, _edges = parts.mesh_arrays(obj)
    matrix, distance = surface_weights(sources, names, world[vertices], distances=True)
    body = [parts.mesh_arrays(source)[0][mask] for source, mask in sources]
    body = np.concatenate(body) if body else np.zeros((0, 3))
    gap = CLOTH_GAP * float(np.ptp(body[:, 2])) if len(body) else 0.0
    far = np.clip(distance / gap - 1.0, 0.0, 1.0) if gap > 0.0 else np.ones(len(vertices))
    if far.any():
        heat = heat_of_copy(context, rig, obj, names)[vertices]
        empty = heat.sum(axis=1) <= 0.0
        if empty.any():
            heat[empty] = nearest_bone_weights(rig, names, world[vertices[empty]])
        matrix = matrix * (1.0 - far[:, None]) + heat * far[:, None]
    return matrix


def surface_weights(sources, names, points, distances=False):
    """Weights (len(points) x len(names)) at world `points` copied from the nearest point of the source surfaces and
    interpolated between the corners of that triangle (spec 5.2, Clothing). `sources` is a list of (object, vertex
    mask); only triangles with every corner in the mask are used. With `distances`, also how far each point is from
    the surface (inf where there is none)."""
    verts, tris, table, offset = [], [], [], 0
    for obj, mask in sources:
        mesh = obj.data
        mesh.calc_loop_triangles()
        corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
        mesh.loop_triangles.foreach_get("vertices", corners)
        corners = corners.reshape(-1, 3).astype(np.int64)
        corners = corners[mask[corners].all(axis=1)]
        world, _edges = parts.mesh_arrays(obj)
        verts.append(world)
        tris.append(corners + offset)
        table.append(read(obj, names))
        offset += len(world)
    out = np.zeros((len(points), len(names)))
    away = np.full(len(points), np.inf)
    if not tris or sum(len(t) for t in tris) == 0:
        return (out, away) if distances else out
    verts, tris, table = np.concatenate(verts), np.concatenate(tris), np.concatenate(table)
    tree = BVHTree.FromPolygons(verts.tolist(), tris.tolist(), all_triangles=True)
    for i, point in enumerate(np.asarray(points, float).tolist()):
        location, _normal, index, distance = tree.find_nearest(point)
        if index is None:
            continue
        a, b, c = tris[index]
        bary = _barycentric(np.array(location), verts[a], verts[b], verts[c])
        out[i] = bary[0] * table[a] + bary[1] * table[b] + bary[2] * table[c]
        away[i] = distance
    return (out, away) if distances else out


def nearest_bone_weights(rig, names, points):
    """Weight 1 for the bone in `names` nearest to each world point (len(points) x len(names))."""
    points = np.asarray(points, float)
    distance = np.stack([chains.segment_distance(points, *parts.bone_segment(rig, name)) for name in names], axis=1)
    out = np.zeros_like(distance)
    out[np.arange(len(points)), distance.argmin(axis=1)] = 1.0
    return out
