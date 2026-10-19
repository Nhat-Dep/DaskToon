# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sculpt Eye Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part B). Many anime
characters build each eye from loose pieces in front of the face (eye white, iris, lashes) rather than a socket with
lids; closing such an eye is squashing its pieces onto a line.

The head's frame: the centre of the Head bone, its length as the unit, the character facing -Y with its left at +X
(the standard skeleton, armature space). A loose piece (vertices joined by edges) of a mesh the rig deforms is part of
an eye when its centre is in front, to the side, at eye height and it is small; the pieces of one side make that eye,
and both eyes are needed. Hair parts are left out (a lock hanging in front of an eye). Open edges of other pieces all
around an eye (an eye in a socket) leave the face alone; the edge of the hair crossing it is no socket.

Keys, on each mesh holding eye pieces: blink (both eyes onto the close line, a third of the way up, keeping KEEP of
their height), blink_L and blink_R, joy (closed as an arc, its middle raised by ARCH of the eye's height) and surprised
(WIDEN times bigger about the eye's centre, across and up). A key of the same expression (expressions.SLOTS) that moves
is kept, an empty one filled, a missing one added under its VRM 0.x name."""

from typing import NamedTuple

import numpy as np

from . import expressions

FRONT = -0.15  # the piece's centre at most this far forward of the head's centre (facing -Y)
SIDE = (0.06, 0.5)  # how far from the middle
HEIGHT = (-0.5, 0.2)  # how high, from the head's centre
WIDEST = 0.45  # a piece wider, taller or deeper than this is not part of an eye (a bang, a face)
CLOSE_AT = 1.0 / 3.0
KEEP = 0.04
ARCH = 0.35
WIDEN = 1.12
FEWEST = 3  # vertices of a piece (a loose vertex is no eye)
SOCKET_GAP = 1.5  # radians: open edges around an eye leaving no wider gap make it a socket
# (key, its slot, the eyes it closes or widens, how)
KEYS = (("blink", "BLINK", ("LEFT", "RIGHT"), 'CLOSE'), ("blink_L", "BLINK_L", ("LEFT",), 'CLOSE'),
        ("blink_R", "BLINK_R", ("RIGHT",), 'CLOSE'), ("joy", "JOY", ("LEFT", "RIGHT"), 'ARC'),
        ("surprised", "SURPRISED", ("LEFT", "RIGHT"), 'WIDEN'))


class Eye(NamedTuple):
    side: str
    pieces: list  # [(object, vertex indices)]
    low: np.ndarray  # (x, y, z) smallest, armature space
    high: np.ndarray  # largest


def _head(rig):
    head = rig.data.bones.get("Head")
    if head is None or head.length <= 0.0:
        return None
    return np.array((head.head_local + head.tail_local) / 2.0), head.length


def _rest(rig, obj):
    """The rest coordinates of `obj` (its reference key's, else its vertices') in the rig's armature space."""
    key = obj.data.shape_keys
    points = key.reference_key.data if key is not None else obj.data.vertices
    co = np.empty(len(points) * 3)
    points.foreach_get("co", co)
    to_arm = rig.matrix_world.inverted() @ obj.matrix_world
    return co.reshape(-1, 3) @ np.array(to_arm.to_3x3()).T + np.array(to_arm.translation)


def _pieces(mesh):
    """Vertex indices of each loose piece (vertices joined by edges)."""
    count = len(mesh.vertices)
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    parent = np.arange(count)

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in edges.reshape(-1, 2):
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([root(i) for i in range(count)])
    return [np.nonzero(roots == r)[0] for r in np.unique(roots)]


def _boundary_points(mesh):
    """The middle of each edge used by one face, as vertex index pairs."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    used = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("edge_index", used)
    faces = np.bincount(used, minlength=len(mesh.edges))
    return edges.reshape(-1, 2)[faces == 1]


def _is_mesh_of(rig, obj):
    return obj.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)


def find_eyes(rig, meshes):
    """{"LEFT": Eye, "RIGHT": Eye} of the character, or {} without both eyes or with eye sockets."""
    head = _head(rig)
    if head is None:
        return {}
    centre, size = head
    found = {"LEFT": [], "RIGHT": []}
    others = []  # (object, rest, the pieces that are not eyes)
    data = getattr(rig.data, "dasktoon_rig", None)
    hair = {part.object for part in (data.parts if data is not None else ()) if part.role == 'HAIR'}
    for obj in meshes:
        if not _is_mesh_of(rig, obj) or not len(obj.data.vertices):
            continue
        if obj in hair:
            others.append((obj, _rest(rig, obj), np.ones(len(obj.data.vertices), dtype=bool)))
            continue
        rest = _rest(rig, obj)
        rel = (rest - centre) / size
        not_eyes = np.ones(len(rest), dtype=bool)
        for piece in _pieces(obj.data):
            p = rel[piece]
            middle = (p.min(axis=0) + p.max(axis=0)) / 2.0
            if (len(piece) >= FEWEST and middle[1] < FRONT and SIDE[0] < abs(middle[0]) < SIDE[1]
                    and HEIGHT[0] < middle[2] < HEIGHT[1] and np.ptp(p, axis=0).max() < WIDEST):
                found["LEFT" if middle[0] > 0.0 else "RIGHT"].append((obj, piece))
                not_eyes[piece] = False
        others.append((obj, rest, not_eyes))
    if not found["LEFT"] or not found["RIGHT"]:
        return {}
    eyes = {}
    for side, pieces in found.items():
        points = np.concatenate([_rest(rig, obj)[piece] for obj, piece in pieces])
        eyes[side] = Eye(side, pieces, points.min(axis=0), points.max(axis=0))
    for obj, rest, not_eyes in others:  # a socket: another piece's open edges around an eye
        pairs = _boundary_points(obj.data)
        pairs = pairs[not_eyes[pairs[:, 0]] & not_eyes[pairs[:, 1]]]
        if not len(pairs):
            continue
        middles = (rest[pairs[:, 0]] + rest[pairs[:, 1]]) / 2.0
        for eye in eyes.values():
            pad = 0.25 * (eye.high - eye.low)
            inside = ((middles[:, 0] > eye.low[0] - pad[0]) & (middles[:, 0] < eye.high[0] + pad[0])
                      & (middles[:, 2] > eye.low[2] - pad[2]) & (middles[:, 2] < eye.high[2] + pad[2])
                      & (middles[:, 1] < centre[1]))
            if inside.sum() < 3:
                continue
            middle = (eye.low + eye.high) / 2.0
            turns = np.sort(np.arctan2(middles[inside, 2] - middle[2], middles[inside, 0] - middle[0]))
            gaps = np.diff(np.append(turns, turns[0] + 2.0 * np.pi))
            if gaps.max() < SOCKET_GAP:  # open edges all around the eye
                return {}
    return eyes


def _moved(eye, points, how):
    """`points` (armature space) of `eye` after `how`."""
    out = points.copy()
    low, high = eye.low, eye.high
    line = low[2] + CLOSE_AT * (high[2] - low[2])
    if how == 'CLOSE':
        out[:, 2] = line + (points[:, 2] - line) * KEEP
    elif how == 'ARC':
        middle, half = (low[0] + high[0]) / 2.0, max((high[0] - low[0]) / 2.0, 1e-9)
        lift = ARCH * (high[2] - low[2]) * np.clip(1.0 - ((points[:, 0] - middle) / half) ** 2, 0.0, 1.0)
        out[:, 2] = line + lift + (points[:, 2] - line) * KEEP
    else:
        middle = (low + high) / 2.0
        for axis in (0, 2):
            out[:, axis] = middle[axis] + (points[:, axis] - middle[axis]) * WIDEN
    return out


def _target(obj, slot, name):
    """The key to write `name`'s shape into: a key of its slot that moves nothing, or None when one moves; a new key
    under `name` when the slot has none."""
    key = obj.data.shape_keys
    if key is None:
        obj.shape_key_add(name="Basis", from_mix=False)
        key = obj.data.shape_keys
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    empty = None
    for block in key.key_blocks:
        if block == key.reference_key or expressions.slot_of(block.name) != slot:
            continue
        co = np.empty_like(base)
        block.data.foreach_get("co", co)
        if np.abs(co - base).max() > expressions.NOTHING:
            return None
        empty = empty or block
    return empty or obj.shape_key_add(name=name, from_mix=False)


def sculpt(rig, meshes):
    """Make the eye keys on the meshes holding eye pieces; returns [(key name, [mesh names])], nothing without eyes."""
    eyes = find_eyes(rig, meshes)
    if not eyes:
        return []
    holders = []
    for eye in eyes.values():
        for obj, _piece in eye.pieces:
            if obj not in holders:
                holders.append(obj)
    made = {}
    for name, slot, sides, how in KEYS:
        for obj in holders:
            block = _target(obj, slot, name)
            if block is None:
                continue
            key = obj.data.shape_keys
            base = np.empty(len(key.reference_key.data) * 3)
            key.reference_key.data.foreach_get("co", base)
            base = base.reshape(-1, 3)
            rest = _rest(rig, obj)
            moved = np.zeros_like(rest)
            for side in sides:
                for owner, piece in eyes[side].pieces:
                    if owner == obj:
                        moved[piece] = _moved(eyes[side], rest[piece], how) - rest[piece]
            to_arm = np.array((rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
            block.data.foreach_set("co", (base + moved @ np.linalg.inv(to_arm).T).ravel())
            made.setdefault(block.name, []).append(obj.name)
    return list(made.items())
