# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Pieces of a machine (machine rig spec 3): the integer vertex attribute `dt_piece` numbers them. 0 means not numbered
yet: such vertices are split by loose part (edge-connected) and numbered when the machine is read. Make a Piece from
Selection numbers the vertices of the selected faces anew.

A piece is (mesh object, number). Binding reads which bone each vertex is weighted to and moves pieces between bones;
it also casts rays at the rest shape of the meshes to find the piece under the mouse."""

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import MachineError, meshes, root_name

ATTR = "dt_piece"


def _edges(mesh):
    e = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", e)
    return e.reshape(-1, 2)


def components(count, edges):
    """A label per vertex: the smallest vertex index of its loose part."""
    labels = np.arange(count)
    if not len(edges):
        return labels
    a, b = edges[:, 0], edges[:, 1]
    while True:
        m = np.minimum(labels[a], labels[b])
        new = labels.copy()
        np.minimum.at(new, a, m)
        np.minimum.at(new, b, m)
        new = new[new]
        while True:
            jumped = new[new]
            if np.array_equal(jumped, new):
                break
            new = jumped
        if np.array_equal(new, labels):
            return labels
        labels = new


def read(obj):
    mesh = obj.data
    attr = mesh.attributes.get(ATTR)
    ids = np.zeros(len(mesh.vertices), dtype=np.int64)
    if attr is not None and attr.domain == 'POINT' and attr.data_type == 'INT':
        buf = np.empty(len(mesh.vertices), dtype=np.int32)
        attr.data.foreach_get("value", buf)
        ids[:] = buf
    return ids


def write(obj, ids):
    mesh = obj.data
    attr = mesh.attributes.get(ATTR)
    if attr is not None and (attr.domain != 'POINT' or attr.data_type != 'INT'):
        mesh.attributes.remove(attr)
        attr = None
    if attr is None:
        attr = mesh.attributes.new(ATTR, 'INT', 'POINT')
    attr.data.foreach_set("value", np.asarray(ids, dtype=np.int32))
    mesh.update()


def ensure(obj):
    """The piece number of each vertex of `obj`, numbering the vertices that have none by loose part."""
    ids = read(obj)
    free = ids == 0
    if free.any():
        edges = _edges(obj.data)
        edges = edges[free[edges[:, 0]] & free[edges[:, 1]]]
        labels = components(len(ids), edges)
        start = int(ids.max()) + 1
        _unique, inverse = np.unique(labels[free], return_inverse=True)
        ids[free] = start + inverse
        write(obj, ids)
    return ids


def piece_of_vertex(obj, index):
    return (obj, int(ensure(obj)[index]))


def from_selection(obj):
    """The selected faces of `obj` (Object Mode data) become a piece of their own; returns its number."""
    sel = np.empty(len(obj.data.polygons), dtype=bool)
    obj.data.polygons.foreach_get("select", sel)
    if not sel.any():
        raise MachineError(rpt_("Select the faces of the piece in Edit Mode first"))
    ids = ensure(obj)
    verts = set()
    for poly in np.nonzero(sel)[0]:
        verts.update(obj.data.polygons[int(poly)].vertices)
    new = int(ids.max()) + 1
    ids[list(verts)] = new
    write(obj, ids)
    return new


def world_points(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


class Binding:
    """Which bone holds each piece of a machine's meshes, read from their vertex groups (the strongest bone of the
    machine wins a vertex). Kept up to date by bind(); read again with a new Binding after other changes."""

    def __init__(self, rig, objects=None):
        self.rig = rig
        self.root = root_name(rig)
        self.objects = list(objects) if objects is not None else meshes(rig)
        self.names = [b.name for b in rig.data.bones]
        self._index = {n: i for i, n in enumerate(self.names)}
        self.ids, self.owner, self.world = {}, {}, {}
        self._bvh = {}
        for obj in self.objects:
            self.ids[obj] = ensure(obj)
            self.world[obj] = world_points(obj)
            self.owner[obj] = self._read_owner(obj)

    def _name_index(self, name):
        if name not in self._index:
            self._index[name] = len(self.names)
            self.names.append(name)
        return self._index[name]

    def _read_owner(self, obj):
        owner = np.full(len(obj.data.vertices), -1, dtype=np.int64)
        groups = {g.index: self._index[g.name] for g in obj.vertex_groups if g.name in self._index}
        if not groups:
            return owner
        for v in obj.data.vertices:
            best, weight = -1, 0.0
            for g in v.groups:
                bone = groups.get(g.group)
                if bone is not None and g.weight > weight:
                    best, weight = bone, g.weight
            owner[v.index] = best
        return owner

    # Pieces

    def pieces(self):
        return [(obj, int(i)) for obj in self.objects for i in np.unique(self.ids[obj])]

    def verts(self, piece):
        obj, number = piece
        return np.nonzero(self.ids[obj] == number)[0]

    def bone_of(self, piece):
        obj, _number = piece
        owners = self.owner[obj][self.verts(piece)]
        owners = owners[owners >= 0]
        if not len(owners):
            return None
        return self.names[int(np.bincount(owners).argmax())]

    def pieces_of(self, bone):
        return [p for p in self.pieces() if self.bone_of(p) == bone]

    def unbound(self):
        return [p for p in self.pieces() if self.bone_of(p) in (None, self.root)]

    def points(self, pieces):
        """World rest positions of the vertices of `pieces`."""
        parts = [self.world[obj][self.verts((obj, n))] for obj, n in pieces]
        return np.concatenate(parts) if parts else np.zeros((0, 3))

    def whole_object(self, pieces):
        """The object `pieces` cover entirely, or None."""
        objs = {obj for obj, _n in pieces}
        if len(objs) != 1:
            return None
        obj = objs.pop()
        numbers = {n for _o, n in pieces}
        return obj if set(np.unique(self.ids[obj]).tolist()) <= numbers else None

    def faces(self, pieces):
        """{object: [polygon indices]} of the faces lying wholly in `pieces`."""
        out = {}
        for obj in {o for o, _n in pieces}:
            numbers = np.array(sorted(n for o, n in pieces if o == obj))
            inside = np.isin(self.ids[obj], numbers)
            loop_verts = np.empty(len(obj.data.loops), dtype=np.int64)
            obj.data.loops.foreach_get("vertex_index", loop_verts)
            starts = np.empty(len(obj.data.polygons), dtype=np.int64)
            obj.data.polygons.foreach_get("loop_start", starts)
            ok = np.logical_and.reduceat(inside[loop_verts], starts) if len(starts) else np.zeros(0, dtype=bool)
            out[obj] = np.nonzero(ok)[0]
        return out

    def surface(self, pieces):
        """A BVH tree of the world rest faces of `pieces`, or None when they have no face."""
        verts, polys = [], []
        for obj, indices in self.faces(pieces).items():
            if not len(indices):
                continue
            offset = len(verts)
            verts += [Vector(p) for p in self.world[obj]]
            polys += [[offset + v for v in obj.data.polygons[int(i)].vertices] for i in indices]
        return BVHTree.FromPolygons(verts, polys) if polys else None

    # Moving pieces

    def bind(self, pieces, bone):
        """Weight `pieces` 100% to `bone`, taking them from every other bone of the machine."""
        index = self._name_index(bone)
        bones = set(self.names)
        for obj in {o for o, _n in pieces}:
            verts = np.concatenate([self.verts(p) for p in pieces if p[0] == obj]).tolist()
            for group in obj.vertex_groups:
                if group.name in bones and group.name != bone:
                    group.remove(verts)
            group = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
            group.add(verts, 1.0, 'REPLACE')
            self.owner[obj][verts] = index

    def rename(self, old, new):
        if old in self._index:
            i = self._index.pop(old)
            self.names[i] = new
            self._index[new] = i

    # Picking

    def hit(self, origin, direction):
        """(piece, world location) of the first rest face along the ray, or (None, None)."""
        best = (None, None, float("inf"))
        origin, direction = Vector(origin), Vector(direction).normalized()
        for obj in self.objects:
            tree = self._bvh.get(obj)
            if tree is None:
                tree = BVHTree.FromPolygons([Vector(p) for p in self.world[obj]],
                                            [list(p.vertices) for p in obj.data.polygons])
                self._bvh[obj] = tree
            loc, _normal, index, dist = tree.ray_cast(origin, direction)
            if loc is not None and dist < best[2]:
                poly = obj.data.polygons[index]
                verts = list(poly.vertices)
                near = min(verts, key=lambda v: (Vector(self.world[obj][v]) - loc).length)
                best = ((obj, int(self.ids[obj][near])), loc, dist)
        return best[0], best[1]
