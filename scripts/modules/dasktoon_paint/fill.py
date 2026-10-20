# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fill Part (spec section 4): the loose part under the cursor, faces of the same material only, filled by Blender's
own Fill on the model through the face mask, so the fill goes to the active layer, bleeds over the seams and undoes
like any stroke. With the face mask already on, the selected faces are filled."""

import contextlib

import numpy as np
from mathutils.bvhtree import BVHTree


def face_under(obj, origin, direction):
    """Index of the mesh face the ray (world space) hits first, or None."""
    mesh = obj.data
    matrix = obj.matrix_world
    verts = [matrix @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in mesh.polygons])
    _location, _normal, index, _distance = tree.ray_cast(origin, direction)
    return index


def part_faces(mesh, face):
    """The faces of the loose part holding `face` that use its material."""
    count = len(mesh.polygons)
    starts = np.empty(count, dtype=np.int32)
    totals = np.empty(count, dtype=np.int32)
    materials = np.empty(count, dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", totals)
    mesh.polygons.foreach_get("material_index", materials)
    loops = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    owner = np.repeat(np.arange(count), totals)  # the face of each loop
    by_vertex = {}
    for vertex, f in zip(loops.tolist(), owner.tolist()):
        by_vertex.setdefault(vertex, []).append(f)
    material = materials[face]
    seen = {face}
    todo = [face]
    while todo:
        f = todo.pop()
        for vertex in loops[starts[f]:starts[f] + totals[f]].tolist():
            for other in by_vertex[vertex]:
                if other not in seen and materials[other] == material:
                    seen.add(other)
                    todo.append(other)
    return sorted(seen)


@contextlib.contextmanager
def only_faces(obj, faces):
    """Let painting reach `faces` only (the face mask), then put the selection and the mask back."""
    mesh = obj.data
    selection = np.empty(len(mesh.polygons), dtype=bool)
    mesh.polygons.foreach_get("select", selection)
    mask = mesh.use_paint_mask
    chosen = np.zeros(len(mesh.polygons), dtype=bool)
    chosen[list(faces)] = True
    try:
        mesh.polygons.foreach_set("select", chosen)
        mesh.use_paint_mask = True
        mesh.update()
        yield
    finally:
        mesh.polygons.foreach_set("select", selection)
        mesh.use_paint_mask = mask
        mesh.update()
