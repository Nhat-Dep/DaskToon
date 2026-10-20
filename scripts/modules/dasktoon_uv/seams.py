# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where the anime unwrap cuts (spec section 2, steps 1 and 2). Every face gets a label: its body region from the rig
(head, torso, an arm, a leg) or, without one, its loose piece. Edges between labels are seams; a group of faces of one
label that is closed, or a tube between two openings, or a head or torso, is also cut once along its length, on the side
the character hides (the back, under the arms, the inside of the legs): the shortest path whose edges cost more the more
they face the front."""

import heapq

import numpy as np
from mathutils import Matrix, Vector

from dasktoon_rig import regions

PIECE = 100  # labels of loose pieces start here; regions are 0..5
EXPOSURE = 6.0  # how much more an edge facing away from the hidden side costs
FLAT = 0.2  # a group thinner than this (its least spread over its most) is a flat piece: an eye plate, a card
SHARP = 60.0  # degrees: a closed piece is also cut where its faces meet this sharply (a capped tube's rims)
TORSO = regions.REGIONS.index('TORSO')
LEGS = (regions.REGIONS.index('LEG_L'), regions.REGIONS.index('LEG_R'))
LABELS = regions.REGIONS + ('HAND_L', 'HAND_R', 'FOOT_L', 'FOOT_R')  # the hands and feet cut off their limbs
HIDDEN = {'HEAD': (0, 1, 0), 'TORSO': (0, 1, 0), 'ARM_L': (0, 0, -1), 'ARM_R': (0, 0, -1),
          'LEG_L': (-1, 0, 0), 'LEG_R': (1, 0, 0), 'HAND_L': (0, 0, -1), 'HAND_R': (0, 0, -1),
          'FOOT_L': (0, 0, -1), 'FOOT_R': (0, 0, -1)}  # in the character's frame: front -Y, its left +X
UPRIGHT = {'HEAD', 'TORSO'}  # cut along the body's up axis (a wide garment's longest axis runs across it)
ENDS = (('ARM_L', 'HAND_L', 'LeftLowerArm', 'LeftHand'), ('ARM_R', 'HAND_R', 'RightLowerArm', 'RightHand'),
        ('LEG_L', 'FOOT_L', 'LeftLowerLeg', 'LeftFoot'), ('LEG_R', 'FOOT_R', 'RightLowerLeg', 'RightFoot'))


def _find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent, a, b):
    a, b = _find(parent, a), _find(parent, b)
    if a != b:
        parent[b] = a


def loose_pieces(mesh):
    """The loose piece of every vertex (a number per piece)."""
    parent = list(range(len(mesh.vertices)))
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    for a, b in edges.reshape(-1, 2).tolist():
        _union(parent, a, b)
    return np.array([_find(parent, i) for i in range(len(parent))])


def vertex_regions(context, obj, rig, analysis=None):
    """Region (index in regions.REGIONS) of every vertex, -1 where unknown: as painted on the region layer, else as the
    rig's analysis finds it."""
    out = regions.read(obj).astype(np.int32)
    if (out >= 0).any() or rig is None:
        return out
    if analysis is None:
        analysis = regions.analyse(context, rig, list(rig.data.dasktoon_rig.parts))
    found = analysis.objects.get(obj)
    if found is not None:
        vertices, labelled = found
        out[np.asarray(vertices)] = np.asarray(labelled)
    return out


def clothing_vertices(obj, rig):
    """True for the vertices a Clothing part of the rig owns."""
    from dasktoon_rig import build
    parts = list(rig.data.dasktoon_rig.parts)
    owners = build.ownership(parts).get(obj)
    if owners is None:
        return np.zeros(len(obj.data.vertices), dtype=bool)
    roles = np.array([part.role == 'CLOTHING' for part in parts] + [False])  # -1 (no part) reads the last
    return roles[owners]


def merge_garments(labels, pieces, clothing):
    """A clothing piece holding torso faces and leg faces is one garment over the hips (shorts, a skirt, a dress): its
    leg faces take the torso's label, so it is not cut round the hips, in front. Socks and boots (legs only) and the
    body keep their labels; sleeves stay apart (cut at the armhole, like a sewn sleeve)."""
    out = labels.copy()
    for piece in np.unique(pieces[clothing]):
        mask = (pieces == piece) & clothing
        present = set(labels[mask].tolist())
        if TORSO in present and present & set(LEGS):
            out[mask & np.isin(labels, LEGS)] = TORSO
    return out


def split_ends(labels, obj, rig):
    """The vertices of an arm past the wrist, of a leg past the ankle (along the forearm, the shin), become the hand,
    the foot: a limb with its foot and toes in one island came out stretched (filie)."""
    bones = rig.data.bones
    world = np.array([obj.matrix_world @ v.co for v in obj.data.vertices]).reshape(-1, 3)
    out = labels.copy()
    for limb, end, upper, joint in ENDS:
        if upper not in bones or joint not in bones:
            continue
        start = np.array(rig.matrix_world @ bones[upper].head_local)
        joint_at = np.array(rig.matrix_world @ bones[joint].head_local)
        direction = (joint_at - start) / max(np.linalg.norm(joint_at - start), 1e-9)
        out[(labels == LABELS.index(limb)) & ((world - joint_at) @ direction > 0)] = LABELS.index(end)
    return out


def face_labels(context, obj, rig, analysis=None):
    """A label for every face: the region most of its vertices have, else PIECE + its loose piece; a garment over the
    hips is one label (merge_garments)."""
    mesh = obj.data
    vertex = vertex_regions(context, obj, rig, analysis) if rig is not None else np.full(len(mesh.vertices), -1)
    if rig is not None:
        vertex = split_ends(vertex, obj, rig)
    pieces = loose_pieces(mesh)
    combined = np.where(vertex >= 0, vertex, PIECE + pieces)
    labels = np.empty(len(mesh.polygons), dtype=np.int64)
    first = np.empty(len(mesh.polygons), dtype=np.int64)
    for poly in mesh.polygons:
        values, counts = np.unique(combined[list(poly.vertices)], return_counts=True)
        labels[poly.index] = values[counts.argmax()]
        first[poly.index] = poly.vertices[0]
    if rig is not None:
        labels = merge_garments(labels, pieces[first], clothing_vertices(obj, rig)[first])
    return labels


def _edge_faces(mesh):
    faces_of = [[] for _ in mesh.edges]
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            faces_of[mesh.loops[loop].edge_index].append(poly.index)
    return faces_of


def groups(mesh, labels, faces_of):
    """Faces joined by edges inside one label: [[face indices]]."""
    parent = list(range(len(mesh.polygons)))
    for faces in faces_of:
        for a, b in zip(faces, faces[1:]):
            if labels[a] == labels[b]:
                _union(parent, a, b)
    out = {}
    for face in range(len(mesh.polygons)):
        out.setdefault(_find(parent, face), []).append(face)
    return list(out.values())


def _loops_of(mesh, edges):
    """The edge loops (as vertex sets) the `edges` (indices) make."""
    parent = {}
    for e in edges:
        a, b = mesh.edges[e].vertices
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        ra, rb = a, b
        while parent[ra] != ra:
            ra = parent[ra]
        while parent[rb] != rb:
            rb = parent[rb]
        if ra != rb:
            parent[rb] = ra
    out = {}
    for v in parent:
        r = v
        while parent[r] != r:
            r = parent[r]
        out.setdefault(r, set()).add(v)
    return list(out.values())


def _path(adjacency, start, ends, cost):
    """Dijkstra from `start` to the nearest of `ends`; the edges of the path."""
    best = {start: 0.0}
    back = {}
    heap = [(0.0, start)]
    while heap:
        d, v = heapq.heappop(heap)
        if v in ends:
            path = []
            while v in back:
                path.append(back[v][1])
                v = back[v][0]
            return path
        if d > best.get(v, float("inf")):
            continue
        for w, edge in adjacency.get(v, ()):
            nd = d + cost[edge]
            if nd < best.get(w, float("inf")):
                best[w] = nd
                back[w] = (v, edge)
                heapq.heappush(heap, (nd, w))
    return []


def _edge_counts(mesh, faces):
    counts = {}
    for f in faces:
        for key in mesh.polygons[f].edge_keys:
            counts[key] = counts.get(key, 0) + 1
    return counts


def cut_along(obj, faces, hidden, frame, index_of, upright=False):
    """Edges of one cut along the group `faces`, on the side facing `hidden` (character frame); along the body's up
    axis when `upright`, else along the group's longest axis."""
    mesh = obj.data
    matrix = obj.matrix_world
    hidden = np.array((frame.to_3x3() @ Vector(hidden)).normalized())
    edge_count = _edge_counts(mesh, faces)
    inner = [index_of[k] for k, n in edge_count.items() if n >= 2]
    border = [index_of[k] for k, n in edge_count.items() if n == 1]
    verts = sorted({v for f in faces for v in mesh.polygons[f].vertices})
    if len(verts) < 8:
        return []
    world = {v: np.array(matrix @ mesh.vertices[v].co) for v in verts}
    points = np.array([world[v] for v in verts])
    centre = points.mean(axis=0)
    axis = (np.array((frame.to_3x3() @ Vector((0, 0, 1))).normalized()) if upright
            else np.linalg.svd(points - centre, full_matrices=False)[2][0])
    along = {v: float((world[v] - centre) @ axis) for v in verts}
    # Which way a vertex faces, read from where it sits round the group's axis (not from the normals, which a newcomer's
    # mesh may have inward).
    facing = {}
    for v in verts:
        radial = world[v] - centre - along[v] * axis
        facing[v] = float(radial @ hidden / max(np.linalg.norm(radial), 1e-9))
    cost, adjacency = {}, {}
    for e in inner:
        a, b = mesh.edges[e].vertices
        exposure = 1.0 - (facing[a] + facing[b] + 2.0) / 4.0  # 0 facing the hidden side, 1 facing away
        cost[e] = float(np.linalg.norm(world[a] - world[b])) * (1.0 + EXPOSURE * exposure ** 2)
        adjacency.setdefault(a, []).append((b, e))
        adjacency.setdefault(b, []).append((a, e))
    hidden_side = [v for v in verts if facing[v] > 0.3] or verts
    loops = sorted(_loops_of(mesh, border), key=lambda loop: np.mean([along[v] for v in loop]))
    if len(loops) >= 2:  # a tube: from the first opening to the last
        start = max(loops[0], key=lambda v: facing[v])
        ends = set(loops[-1])
    elif len(loops) == 1:  # one opening (a head on its neck): from it to the far end
        start = max(loops[0], key=lambda v: facing[v])
        side = np.sign(np.mean([along[v] for v in loops[0]])) or -1.0
        far = min(hidden_side, key=lambda v: side * along[v])
        ends = {far}
    else:  # closed: end to end
        start = min(hidden_side, key=lambda v: along[v])
        ends = {max(hidden_side, key=lambda v: along[v])}
    return _path(adjacency, start, ends, cost)


def _flat(obj, faces):
    """True when the faces lie nearly in a plane (their least spread under FLAT of their most)."""
    mesh = obj.data
    verts = sorted({v for f in faces for v in mesh.polygons[f].vertices})
    if len(verts) < 4:
        return True
    points = np.array([mesh.vertices[v].co for v in verts])
    spread = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
    return spread[0] < 1e-9 or spread[-1] / spread[0] < FLAT


def seams(context, obj, rig, analysis=None):
    """The seam edges of obj and its face labels: (set of edge indices, labels)."""
    mesh = obj.data
    labels = face_labels(context, obj, rig, analysis)
    faces_of = _edge_faces(mesh)
    cut = {e for e, faces in enumerate(faces_of) if len({labels[f] for f in faces}) > 1}
    frame = rig.matrix_world if rig is not None else Matrix.Identity(4)  # without a rig: standing as the Guide asks
    index_of = {e.key: e.index for e in mesh.edges}
    for group in groups(mesh, labels, faces_of):
        label = int(labels[group[0]])
        name = LABELS[label] if 0 <= label < len(LABELS) else None
        openings = len(_loops_of(mesh, [index_of[k] for k, n in _edge_counts(mesh, group).items() if n == 1]))
        if openings == 1 and name not in ('HEAD', 'TORSO') and _flat(obj, group):
            continue  # a flat piece with one edge round it (an eye plate): it unwraps as it is
        cut.update(cut_along(obj, group, HIDDEN.get(name, (0, 1, 0)), frame, index_of, name in UPRIGHT))
        if openings == 0:  # closed: one cut along leaves its caps folded over it
            cut.update(_sharp_edges(mesh, group, faces_of, index_of))
    return cut, labels


def _sharp_edges(mesh, group, faces_of, index_of):
    """Edges inside the group where its two faces meet at more than SHARP degrees."""
    inside = set(group)
    limit = np.cos(np.radians(SHARP))
    out = []
    for key, count in _edge_counts(mesh, group).items():
        if count != 2:
            continue
        a, b = (f for f in faces_of[index_of[key]] if f in inside)
        if mesh.polygons[a].normal.dot(mesh.polygons[b].normal) < limit:
            out.append(index_of[key])
    return out
