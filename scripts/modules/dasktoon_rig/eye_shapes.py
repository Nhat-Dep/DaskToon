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

Eye whites painted on the face (pl1) would stay open, so the skin under each eye moves with it: the vertices of the
Body parts' meshes in front of the head inside the eye's outline (across and up) move as the eye does, fading back to
rest MARGIN of the eye's size out of it. Hair and clothes never move.

A mouth drawn on the face (pl1) makes joy smile: the Body's face texture is read through its UVs below the eyes, the
largest patch unlike the skin near the middle that is a wide line is the mouth (read on the mesh as shown, the rig
at rest: pl1's Subdivision moves the drawing away from where its cage puts it; only what shows from the front: pl1
has a pink inside of the mouth behind its face), and the skin at its corners lifts
(SMILE of its width at the corners, nothing in the middle). Stretching a drawn line cannot open it, so there is no "a".

Keys, on each mesh holding eye pieces or skin under them: blink (both eyes onto the close line, a third of the way up,
keeping KEEP of their height), blink_L and blink_R, joy (closed as an arc, its middle raised by ARCH of the eye's
height) and surprised (WIDEN times bigger about the eye's centre, across and up). A key of the same expression
(expressions.SLOTS) that moves is kept, an empty one filled, a missing one added under its VRM 0.x name."""

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
MARGIN = 0.3  # of the eye's size: the skin under an eye fades back to rest this far out of it
UNLIKE = 0.12  # how far from the skin's colour (RGB) the drawing of a mouth is
SMILE = 0.18  # of the mouth's width: how far its corners lift for joy
BIN = 0.02  # of the head: the cells grouping the drawn points into patches
STEPS = 8  # texture samples along each side of a face triangle
SHOWN = 0.02  # of the head: a sample this far behind the frontmost one across and up from it does not show
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


def _skin(rig, eyes, meshes):
    """{Body mesh: {side: (vertex indices, fade)}}: the face skin under each eye (module docstring)."""
    head = _head(rig)
    data = getattr(rig.data, "dasktoon_rig", None)
    bodies = {part.object for part in (data.parts if data is not None else ())
              if part.role == 'BODY' and part.object is not None}
    pieces = {}
    for eye in eyes.values():
        for obj, piece in eye.pieces:
            pieces.setdefault(obj, set()).update(piece.tolist())
    out = {}
    for obj in meshes:
        if obj not in bodies or not _is_mesh_of(rig, obj):
            continue
        rest = _rest(rig, obj)
        free = np.ones(len(rest), dtype=bool)
        free[list(pieces.get(obj, ()))] = False
        for side, eye in eyes.items():
            pad = np.maximum(MARGIN * (eye.high - eye.low), 1e-9)
            out_x = np.maximum(np.maximum(eye.low[0] - rest[:, 0], rest[:, 0] - eye.high[0]), 0.0) / pad[0]
            out_z = np.maximum(np.maximum(eye.low[2] - rest[:, 2], rest[:, 2] - eye.high[2]), 0.0) / pad[2]
            fade = np.clip(1.0 - np.maximum(out_x, out_z), 0.0, 1.0)
            near = np.nonzero(free & (fade > 0.0) & (rest[:, 1] < head[0][1]))[0]
            if len(near):
                out.setdefault(obj, {})[side] = (near, fade[near])
    return out


def _bodies(rig, meshes):
    data = getattr(rig.data, "dasktoon_rig", None)
    parts = {part.object for part in (data.parts if data is not None else ())
             if part.role == 'BODY' and part.object is not None}
    return [obj for obj in meshes if obj in parts and _is_mesh_of(rig, obj)]


def _image_of(material, cache):
    """(height x width x 4 pixels) of the first image texture of `material`, or None."""
    nodes = material.node_tree.nodes if material is not None and material.node_tree is not None else ()
    image = next((n.image for n in nodes if n.type == 'TEX_IMAGE' and n.image is not None and n.image.size[0] > 0),
                 None)
    if image is None:
        return None
    if image.name not in cache:
        width, height = image.size
        pixels = np.empty(width * height * 4, np.float32)
        image.pixels.foreach_get(pixels)
        cache[image.name] = pixels.reshape(height, width, 4)
    return cache[image.name]


def _samples(rig, obj, low, high, front, cache):
    """(points, colours) read from the face texture over the triangles of `obj` as shown (its modifiers on, the rig at
    rest) whose middle lies in the box."""
    import bpy
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return _read(rig, obj, mesh, low, high, front, cache)
    finally:
        evaluated.to_mesh_clear()


def _read(rig, obj, mesh, low, high, front, cache):
    layer = next((uv for uv in mesh.uv_layers if uv.active_render), None)
    if layer is None:
        return np.zeros((0, 3)), np.zeros((0, 3))
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    to_arm = rig.matrix_world.inverted() @ obj.matrix_world
    rest = co.reshape(-1, 3) @ np.array(to_arm.to_3x3()).T + np.array(to_arm.translation)
    a, b = np.meshgrid(np.arange(STEPS + 1), np.arange(STEPS + 1))
    keep = a + b <= STEPS
    weights = np.stack([a[keep], b[keep], STEPS - a[keep] - b[keep]], axis=1) / STEPS
    points, colours = [], []
    for tri in mesh.loop_triangles:
        corners = rest[list(tri.vertices)]
        middle = corners.mean(axis=0)
        if not (low[0] < middle[0] < high[0] and low[2] < middle[2] < high[2] and middle[1] < front):
            continue
        slot = obj.material_slots[tri.material_index] if tri.material_index < len(obj.material_slots) else None
        pixels = _image_of(slot.material if slot is not None else None, cache)
        if pixels is None:
            continue
        at = weights @ np.array([layer.data[i].uv for i in tri.loops])
        height, width = pixels.shape[:2]
        rows = np.floor(at[:, 1] * height).astype(int) % height
        cols = np.floor(at[:, 0] * width).astype(int) % width
        points.append(weights @ corners)
        colours.append(pixels[rows, cols, :3])
    if not points:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.concatenate(points), np.concatenate(colours)


def drawn_mouth(rig, meshes, eyes):
    """(middle, half width) in armature space of a mouth drawn on the Body's face below the eyes, or None."""
    head = _head(rig)
    if head is None or not eyes:
        return None
    centre, size = head
    middle_x = (eyes["LEFT"].low[0] + eyes["LEFT"].high[0] + eyes["RIGHT"].low[0] + eyes["RIGHT"].high[0]) / 4.0
    top = min(eye.low[2] for eye in eyes.values()) - 0.03 * size
    low = np.array((middle_x - 0.25 * size, 0.0, top - 0.6 * size))
    high = np.array((middle_x + 0.25 * size, 0.0, top))
    cache = {}
    import bpy
    pose_position, rig.data.pose_position = rig.data.pose_position, 'REST'
    bpy.context.view_layer.update()
    try:
        found = [_samples(rig, obj, low, high, centre[1], cache) for obj in _bodies(rig, meshes)]
    finally:
        rig.data.pose_position = pose_position
        bpy.context.view_layer.update()
    points = np.concatenate([p for p, _c in found]) if found else np.zeros((0, 3))
    colours = np.concatenate([c for _p, c in found]) if found else np.zeros((0, 3))
    if len(points) < 10:
        return None
    cells = [tuple(cell) for cell in np.floor(points[:, [0, 2]] / (0.5 * BIN * size)).astype(int)]
    nearest = {}
    for cell, depth in zip(cells, points[:, 1]):
        nearest[cell] = min(nearest.get(cell, np.inf), depth)
    shown = np.array([depth <= nearest[cell] + SHOWN * size for cell, depth in zip(cells, points[:, 1])])
    points, colours = points[shown], colours[shown]
    skin = np.median(colours, axis=0)
    drawn = points[np.linalg.norm(colours - skin, axis=1) > UNLIKE]
    if len(drawn) < 5:
        return None
    cells = {}
    for i, cell in enumerate(map(tuple, np.floor(drawn[:, [0, 2]] / (BIN * size)).astype(int))):
        cells.setdefault(cell, []).append(i)
    best, seen = None, set()
    for start in cells:
        if start in seen:
            continue
        group, stack = [], [start]
        seen.add(start)
        while stack:
            cell = stack.pop()
            group += cells[cell]
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    other = (cell[0] + dx, cell[1] + dz)
                    if other in cells and other not in seen:
                        seen.add(other)
                        stack.append(other)
        patch = drawn[group]
        if abs(patch[:, 0].mean() - middle_x) < 0.1 * size and (best is None or len(patch) > len(best)):
            best = patch
    if best is None:
        return None
    width, height = np.ptp(best[:, 0]), np.ptp(best[:, 2])
    if width < 0.05 * size or width < 2.5 * height:
        return None
    return (best.min(axis=0) + best.max(axis=0)) / 2.0, width / 2.0


def _smile(rest, mouth, front):
    """Offsets lifting the skin at the corners of `mouth` (middle, half width)."""
    middle, half = mouth
    across = (rest[:, 0] - middle[0]) / half
    up = (rest[:, 2] - middle[2]) / half
    lift = (SMILE * 2.0 * half * np.clip(across ** 2, 0.0, 1.0) * np.clip(1.6 - np.abs(across), 0.0, 1.0)
            * np.clip(1.0 - np.abs(up), 0.0, 1.0))
    out = np.zeros_like(rest)
    out[:, 2] = lift * (rest[:, 1] < front)
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
    skin = _skin(rig, eyes, meshes)
    mouth = drawn_mouth(rig, meshes, eyes)
    smiling = _bodies(rig, meshes) if mouth is not None else []
    holders = []
    for eye in eyes.values():
        for obj, _piece in eye.pieces:
            if obj not in holders:
                holders.append(obj)
    holders += [obj for obj in list(skin) + smiling if obj not in holders]
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
                near, fade = skin.get(obj, {}).get(side, ((), None))
                if len(near):
                    moved[near] = (_moved(eyes[side], rest[near], how) - rest[near]) * fade[:, None]
            if how == 'ARC' and obj in smiling:
                moved += _smile(rest, mouth, _head(rig)[0][1])
            to_arm = np.array((rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
            block.data.foreach_set("co", (base + moved @ np.linalg.inv(to_arm).T).ravel())
            made.setdefault(block.name, []).append(obj.name)
    return list(made.items())
