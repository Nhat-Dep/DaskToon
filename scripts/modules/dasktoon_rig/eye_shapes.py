# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sculpt Eye Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part B). Many anime
characters build each eye from loose pieces in front of the face (eye white, iris, lashes) rather than a socket with
lids; closing such an eye is squashing its pieces onto a line.

The head's frame: the centre of the Head bone, its length as the unit, the character facing -Y with its left at +X
(the standard skeleton, armature space). A loose piece (vertices joined by edges) of a mesh the rig deforms may be part
of an eye when it is in the front of the face, to the side, at eye height and small, and has a mirror twin on the other
side (the Head bone can sit off the face's middle, so the twins tell the middle: Encore). A piece of a mesh modelled in
half, with a Mirror modifier, is its own twin (filie); a key there moves both sides, so that mesh gets no key of one side.
Of those, the eye is where most pieces lie, of the pieces as deep as that place: the band up that they fill, at least
half as wide as there however many pieces make that width, then across among those in that band, and the pieces mostly
inside it. A brow lies above that band (Encore's brows, taken for the eye, put the close line above the real eye, and
blink opened it), many bits of lashes are no wider than the one lash they make (counted one by one, Evita's made a strip
of the eye), an ear lies behind it, a strand runs on past it (tdt). Where a ring of open edges of a Body goes round that
place, as deep, the face has a hole there, and the hole is the eye: what lies behind it says little, whites may reach far
past it under the skin. Both eyes are needed. Hair parts are left out (a lock hanging in front of an eye), and a piece
counts as far as it shows: Evita's ball lies in a dent, most of it under the skin; read whole, it made the eye twice as
tall as the opening, and closing dragged the brows down.

Open edges of a Body part all around an eye (Encore's face has a hole at each eye) are the eye's opening: the eye's
outline is then the hole's, and the lids close as the skin does below. Open edges all around an eye in anything else
leave the face alone; the edge of the hair crossing it is no socket.

A closed eye is its lash. A lash comes to the close line as it is, up to LINE thick. What lies over the eye's middle,
up, at its own middle across, comes to nothing behind the lash: the white and the iris, thick as the line, showed round
every thinner lash. That is no matter of outline: a lash curving down round the corners of the eye is as tall as the eye.
Where no piece is a lash (one piece holds the white and the lash drawn on it, Luna), the front one stays as thick as the
line, it is what the closed eye is.

Eye whites painted on the face (pl1) would stay open, so the skin under each eye moves with it: the vertices of the
Body parts' meshes in front of the head inside the eye's outline (across and up) move as the eye does, fading back to
rest MARGIN of the eye's size out of it. Hair and clothes never move.

A mouth drawn on the face (pl1) makes joy smile: the Body's face texture is read through its UVs at most MOUTH below the
eyes (Luna has a brooch further down, and joy lifted her chest round it; a Head bone's length says nothing here), the
largest patch unlike the skin near the middle that is a wide line is the mouth (read on the mesh as shown, the rig
at rest: pl1's Subdivision moves the drawing away from where its cage puts it; only what shows from the front: pl1
has a pink inside of the mouth behind its face), and the skin at its corners lifts
(SMILE of its width at the corners, nothing in the middle). Stretching a drawn line cannot open it, so there is no "a".
A mouth that opens, a thin ring of open edges on the skin, is the surest of all and is read first: mouth_shapes makes its
vowels.
A face without a drawing (filie) may hold the mouth as loose pieces in the middle below the eyes (plates inside the
crease of a closed face): the outline of the group of them lying together, the biggest and of two the higher, gives the
mouth instead. All of them together made a mouth halfway down the chin, with a piece of the collar among them.

Keys, on each mesh holding eye pieces or skin under them: blink (both eyes onto the close line, a third of the way
up), blink_L and blink_R, joy (closed as an arc, its middle raised by ARCH of the eye's
height) and surprised (WIDEN times bigger about the eye's centre, across and up). A key of the same expression
(expressions.SLOTS) that moves is kept, an empty one filled, a missing one added under its VRM 0.x name; asked to
replace, every key of the expression is written again, and those on meshes that are no longer part of it cleared."""

from typing import NamedTuple

import numpy as np

from . import expressions

FRONT = -0.15  # the piece's centre at most this far forward of the head's centre (facing -Y)
DEEP = 0.25  # or at most this far behind the front of the face: eyes set in holes (Encore)
SIDE = (0.06, 0.5)  # how far from the middle
HEIGHT = (-0.5, 0.2)  # how high, from the head's centre
WIDEST = 0.45  # a piece wider, taller or deeper than this is not part of an eye (a bang, a face)
TWIN_OFF = 0.05  # (of the head) how far apart in height and depth the two pieces of a pair lie, and their middles
TWIN_SIZE = 0.3  # how much the sizes of the two pieces of a pair differ
OFF_MIDDLE = 0.15  # (of the head) how far from the Head bone the face's middle may be
BAND_SHARE = 0.5  # the eye's band: at least this share as many pieces as cover its busiest place
INSIDE = 0.5  # a piece at least this much in the band, both ways, is part of the eye
AS_DEEP = 0.2  # (of the head) pieces and a hole this far in depth from where most pieces lie are at the eye
SPOTS = 9  # across and up a piece: where to look for what shows of it
UNDER = 0.01  # (of the head) skin this far in front of a piece covers it; a lash lying on the skin is not under it
CLOSE_AT = 1.0 / 3.0
KEEP = 0.04
LINE = 0.15  # of the eye's height: how thick a closed eye is, about a lash
ARCH = 0.35
WIDEN = 1.12
MARGIN = 0.3  # of the eye's size: the skin under an eye fades back to rest this far out of it
MOUTH = 1.0  # of the distance between the eyes: how far below them a mouth lies, whatever the Head bone's length
THIN = 0.25  # of a slit's width: how tall the lips of a mouth that opens are, shut
TOGETHER = 0.01  # of the head: pieces this far apart in height are of one mouth
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


def _joined(count, pairs):
    """Vertex indices of each group of the `count` vertices that the index `pairs` (n x 2) join."""
    parent = np.arange(count)

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in pairs:
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([root(i) for i in range(count)])
    return [np.nonzero(roots == r)[0] for r in np.unique(roots)]


def _triangles(mesh):
    """Vertex indices of the triangles of `mesh`, n x 3."""
    mesh.calc_loop_triangles()
    out = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get("vertices", out)
    return out.reshape(-1, 3)


def _depths(points, triangles, x, z):
    """How deep (y) each of `triangles` (n x 3 indices into `points`, armature space) lying over the place (x, z) is
    there, seen from the front."""
    a, b, c = (points[triangles[:, i]][:, [0, 2]] for i in range(3))

    def turn(p, q):
        return (q[:, 0] - p[:, 0]) * (z - p[:, 1]) - (q[:, 1] - p[:, 1]) * (x - p[:, 0])

    turns = np.stack([turn(b, c), turn(c, a), turn(a, b)])
    over = ((turns >= 0.0).all(axis=0) | (turns <= 0.0).all(axis=0)) & (turns.sum(axis=0) != 0.0)
    return (points[triangles[over], 1] * (turns[:, over] / turns[:, over].sum(axis=0)).T).sum(axis=1)


def _pieces(mesh):
    """Vertex indices of each loose piece (vertices joined by edges)."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    return _joined(len(mesh.vertices), edges.reshape(-1, 2))


def _boundary_points(mesh):
    """The middle of each edge used by one face, as vertex index pairs."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    used = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("edge_index", used)
    faces = np.bincount(used, minlength=len(mesh.edges))
    return edges.reshape(-1, 2)[faces == 1]


def _rings(mesh):
    """Vertex indices of each ring of open edges of `mesh`."""
    pairs = _boundary_points(mesh)
    if not len(pairs):
        return []
    used = np.unique(pairs)
    return [used[group] for group in _joined(len(used), np.searchsorted(used, pairs))]


def _is_mesh_of(rig, obj):
    return obj.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)


def has_mirror(obj):
    """True when `obj` is modelled in half: a Mirror modifier across its X makes the other side."""
    return any(modifier.type == 'MIRROR' and modifier.use_axis[0] and modifier.mirror_object is None
               and modifier.show_viewport for modifier in obj.modifiers)


def _mirror_plane(rig, obj):
    """x (armature space) of the plane the Mirror modifier of `obj` reflects it across; None without one, or one that
    does not mirror the character's sides."""
    to_arm = rig.matrix_world.inverted() @ obj.matrix_world
    if not has_mirror(obj) or abs(to_arm.to_3x3().col[0].normalized().x) < 0.99:
        return None
    return float(to_arm.translation.x)


def _reach(spans):
    """How much of a line the `spans` (n x 2) cover, those overlapping counted once."""
    total, end = 0.0, -np.inf
    for low, high in sorted(spans.tolist()):
        total += max(0.0, high - max(low, end))
        end = max(end, high)
    return total


def _band(spans, others):
    """(low, high, the place most cover) of the stretch of `spans` (n x 2) round that place, on both ways for as long as
    the pieces reach BAND_SHARE as wide the other way (`others`, n x 2) as they do there."""
    edges = np.unique(spans)
    if len(edges) < 2:
        return float(spans[:, 0].min()), float(spans[:, 1].max()), float(spans[:, 0].min())
    middles = (edges[:-1] + edges[1:]) / 2.0
    covering = (spans[:, 0, None] <= middles) & (middles <= spans[:, 1, None])
    cover = np.array([_reach(others[on]) for on in covering.T])
    begin = int(np.argmax(covering.sum(axis=0)))
    need = BAND_SHARE * cover[begin]
    low = high = begin
    while low > 0 and cover[low - 1] >= need:
        low -= 1
    while high < len(cover) - 1 and cover[high + 1] >= need:
        high += 1
    return float(edges[low]), float(edges[high + 1]), float(middles[begin])


def _inside(low, high, band):
    """True when at least INSIDE of the stretch low to high lies in `band`."""
    size = high - low
    return min(high, band[1]) - max(low, band[0]) >= INSIDE * size


def _twins(found):
    """(the face's middle, the pieces on its left, on its right) of `found` [(object, piece, low, high)] that have a
    mirror twin; head frame. (None, [], []) without one."""
    pairs = []
    for i, a in enumerate(found):
        mid_a, size_a = (a[2] + a[3]) / 2.0, a[3] - a[2]
        for b in found[i + 1:]:
            mid_b, size_b = (b[2] + b[3]) / 2.0, b[3] - b[2]
            middle = (mid_a[0] + mid_b[0]) / 2.0
            if (abs(middle) < OFF_MIDDLE and abs(mid_a[1] - mid_b[1]) < TWIN_OFF and abs(mid_a[2] - mid_b[2]) < TWIN_OFF
                    and np.all(np.abs(size_a - size_b) <= TWIN_SIZE * np.maximum(size_a, size_b) + 1e-9)):
                pairs.append((middle, a, b) if mid_a[0] > mid_b[0] else (middle, b, a))
    if not pairs:
        return None, [], []
    centre = float(np.median([middle for middle, _a, _b in pairs]))
    pairs = [pair for pair in pairs if abs(pair[0] - centre) < TWIN_OFF]
    left, right = {}, {}
    for _middle, a, b in pairs:
        left[id(a)], right[id(b)] = a, b
    return centre, list(left.values()), list(right.values())


def _eye_of(pieces, middle):
    """The pieces of one eye of `pieces` [(object, piece, low, high)], its band (low, high) up, and the place most of
    them lie (across, deep, up), head frame; ([], None, None) with none at the eye's distance from the middle."""
    pieces = [p for p in pieces if SIDE[0] < abs((p[2][0] + p[3][0]) / 2.0 - middle) < SIDE[1]]
    if not pieces:
        return [], None, None
    def spans(found, axis):
        return np.array([(p[2][axis], p[3][axis]) for p in found])

    at_x = _band(spans(pieces, 0), spans(pieces, 2))[2]
    at_z = _band(spans(pieces, 2), spans(pieces, 0))[2]
    here = [p for p in pieces if p[2][0] <= at_x <= p[3][0] and p[2][2] <= at_z <= p[3][2]] or pieces
    deep = float(np.median([(p[2][1] + p[3][1]) / 2.0 for p in here]))
    pieces = [p for p in pieces if abs((p[2][1] + p[3][1]) / 2.0 - deep) <= AS_DEEP]
    *up, at_z = _band(spans(pieces, 2), spans(pieces, 0))
    row = [p for p in pieces if _inside(p[2][2], p[3][2], up)] or pieces
    *across, at_x = _band(spans(row, 0), spans(row, 2))
    kept = [p for p in row if _inside(p[2][0], p[3][0], across)]
    return kept, up, (at_x, deep, at_z)


def _hole_at(place, rests, rings, centre, size):
    """(low, high) in armature space of the smallest ring of open edges of a Body round `place` (across, deep, up, head
    frame), as deep and no wider than a piece of an eye; None without one. `rings`: {object: [vertex indices]}."""
    x, y, z = np.array(place) * size + centre
    best = None
    for obj, found in rings.items():
        for ring in found:
            points = rests[obj][ring]
            low, high = points.min(axis=0), points.max(axis=0)
            if (low[0] < x < high[0] and low[2] < z < high[2] and abs(points[:, 1].mean() - y) <= AS_DEEP * size
                    and max(high[0] - low[0], high[2] - low[2]) < WIDEST * size
                    and (best is None or high[0] - low[0] < best[1][0] - best[0][0])):
                best = low, high
    return best


def _round_the_eye(eye, middles, centre_y):
    """The entries of `middles` (open edges' middles, armature space) that go all around `eye`, as a mask; None when
    they do not."""
    pad = 0.25 * (eye.high - eye.low)
    inside = ((middles[:, 0] > eye.low[0] - pad[0]) & (middles[:, 0] < eye.high[0] + pad[0])
              & (middles[:, 2] > eye.low[2] - pad[2]) & (middles[:, 2] < eye.high[2] + pad[2])
              & (middles[:, 1] < centre_y))
    if inside.sum() < 3:
        return None
    middle = (eye.low + eye.high) / 2.0
    turns = np.sort(np.arctan2(middles[inside, 2] - middle[2], middles[inside, 0] - middle[0]))
    gaps = np.diff(np.append(turns, turns[0] + 2.0 * np.pi))
    return inside if gaps.max() < SOCKET_GAP else None


def _face_front(rig, meshes, centre, size):
    """How far forward (head frame) the face of the Body parts comes; None without one near the head."""
    front = None
    for obj in _bodies(rig, meshes):
        rel = (_rest(rig, obj) - centre) / size
        near = rel[(np.abs(rel[:, 0]) < 1.0) & (np.abs(rel[:, 2]) < 1.0)]
        if len(near):
            front = min(front, near[:, 1].min()) if front is not None else near[:, 1].min()
    return front


def _shown(found, rests, triangles, skins, centre, size):
    """`found` (object, piece, low, high; head frame) with its low and high cut down to what shows of it, the skin of
    `skins` [(rest, triangles)] in front of the rest; None when nothing does. Of what a Mirror modifier makes, the whole.
    The spots are few: what shows all over keeps its outline, a lash thinner than they are far apart."""
    obj, piece, low, high = found
    if not len(piece):
        return found
    own = triangles[obj][np.isin(triangles[obj][:, 0], piece)]
    low_at, high_at = low * size + centre, high * size + centre
    near = []
    for rest, skin in skins:
        corners = rest[skin][:, :, [0, 2]]
        apart = (corners.min(axis=1) > high_at[[0, 2]]) | (corners.max(axis=1) < low_at[[0, 2]])
        near.append((rest, skin[~apart.any(axis=1)]))
    under, shown = 0, []
    for x in np.linspace(low_at[0], high_at[0], SPOTS):
        for z in np.linspace(low_at[2], high_at[2], SPOTS):
            depths = _depths(rests[obj], own, x, z)
            if len(depths):
                if any((_depths(rest, skin, x, z) < depths.min() - UNDER * size).any() for rest, skin in near):
                    under += 1
                else:
                    shown.append((x, z))
    if not under:
        return found
    if not shown:
        return None
    half = (high - low) / (SPOTS - 1) / 2.0
    seen = (np.array(shown) - centre[[0, 2]]) / size
    cut_low, cut_high = low.copy(), high.copy()
    cut_low[[0, 2]] = np.maximum(seen.min(axis=0) - half[[0, 2]], low[[0, 2]])
    cut_high[[0, 2]] = np.minimum(seen.max(axis=0) + half[[0, 2]], high[[0, 2]])
    return obj, piece, cut_low, cut_high


def find_eyes(rig, meshes):
    """{"LEFT": Eye, "RIGHT": Eye} of the character, or {} without both eyes or with eye sockets in no Body part."""
    head = _head(rig)
    if head is None:
        return {}
    centre, size = head
    data = getattr(rig.data, "dasktoon_rig", None)
    hair = {part.object for part in (data.parts if data is not None else ()) if part.role == 'HAIR'}
    front = _face_front(rig, meshes, centre, size)
    deepest = max(FRONT, front + DEEP) if front is not None else FRONT
    bound = [obj for obj in meshes if _is_mesh_of(rig, obj) and len(obj.data.vertices)]
    rests = {obj: _rest(rig, obj) for obj in bound}
    found = []
    for obj in bound:
        if obj in hair:
            continue
        rel = (rests[obj] - centre) / size
        plane = _mirror_plane(rig, obj)
        for piece in _pieces(obj.data):
            p = rel[piece]
            low, high = p.min(axis=0), p.max(axis=0)
            middle = (low + high) / 2.0
            if (len(piece) >= FEWEST and middle[1] < deepest and abs(middle[0]) < SIDE[1] + OFF_MIDDLE
                    and HEIGHT[0] < middle[2] < HEIGHT[1] and np.ptp(p, axis=0).max() < WIDEST):
                found.append((obj, piece, low, high))
                if plane is not None:  # its twin: what the modifier makes, no vertices of the mesh
                    at = (plane - centre[0]) / size
                    other_low, other_high = low.copy(), high.copy()
                    other_low[0], other_high[0] = 2.0 * at - high[0], 2.0 * at - low[0]
                    found.append((obj, np.empty(0, dtype=np.int64), other_low, other_high))
    bodies = set(_bodies(rig, meshes))
    loose = {obj: np.zeros(len(rests[obj]), dtype=bool) for obj in bound}
    for obj, piece, _low, _high in found:
        loose[obj][piece] = True  # the rings of what may be part of an eye are no holes in the face
    rings = {obj: [ring for ring in _rings(obj.data) if not loose[obj][ring].any()] for obj in bound if obj in bodies}
    triangles = {obj: _triangles(obj.data) for obj in bound}
    skins = [(rests[obj], triangles[obj][~loose[obj][triangles[obj]].any(axis=1)]) for obj in bound if obj in bodies]
    middle, left, right = _twins(found)
    if middle is None:
        return {}
    eyes = {}
    for side, pieces in (("LEFT", left), ("RIGHT", right)):
        shown = [_shown(piece, rests, triangles, skins, centre, size) for piece in pieces]
        kept, band, place = _eye_of([piece for piece in shown if piece is not None], middle)
        if not kept:
            return {}
        low = np.min([piece[2] for piece in kept], axis=0) * size + centre
        high = np.max([piece[3] for piece in kept], axis=0) * size + centre
        low[2], high[2] = (np.array(band) * size + centre[2])
        hole = _hole_at(place, rests, rings, centre, size)
        if hole is not None:  # with what lies on its rim: the lashes
            rel_low, rel_high = (hole[0] - centre) / size, (hole[1] - centre) / size
            pad = MARGIN * (rel_high - rel_low)
            across, up = (rel_low[0] - pad[0], rel_high[0] + pad[0]), (rel_low[2] - pad[2], rel_high[2] + pad[2])
            inside = [p for p in pieces if _inside(p[2][0], p[3][0], across) and _inside(p[2][2], p[3][2], up)]
            kept = inside or kept
            low[[0, 2]], high[[0, 2]] = hole[0][[0, 2]], hole[1][[0, 2]]
        eyes[side] = Eye(side, [(obj, piece) for obj, piece, _low, _high in kept if len(piece)], low, high)
    for obj in bound:  # a socket: open edges of something else around an eye (of a Body they are the hole above)
        if obj in hair or obj in bodies:
            continue
        pairs = _boundary_points(obj.data)
        pairs = pairs[~loose[obj][pairs[:, 0]] & ~loose[obj][pairs[:, 1]]]
        if len(pairs):
            middles = (rests[obj][pairs[:, 0]] + rests[obj][pairs[:, 1]]) / 2.0
            if any(_round_the_eye(eye, middles, centre[1]) is not None for eye in eyes.values()):
                return {}
    return eyes


def _over_the_middle(rig, eye):
    """For each piece of `eye`, True when it lies over the eye's middle, up, at its own middle across."""
    middle = (eye.low[2] + eye.high[2]) / 2.0
    held = {}
    out = []
    for obj, piece in eye.pieces:
        if obj not in held:
            held[obj] = _rest(rig, obj), _triangles(obj.data)
        rest, triangles = held[obj]
        x = (rest[piece, 0].min() + rest[piece, 0].max()) / 2.0
        out.append(bool(len(_depths(rest, triangles[np.isin(triangles[:, 0], piece)], x, middle))))
    return out


def _hidden(rig, eye):
    """Indices into the pieces of `eye` of those a closed eye does not show (module docstring)."""
    over = _over_the_middle(rig, eye)
    hidden = {i for i, on in enumerate(over) if on}
    if hidden and len(hidden) == len(over):
        hidden.remove(min(hidden, key=lambda i: _rest(rig, eye.pieces[i][0])[eye.pieces[i][1], 1].min()))
    return hidden


def _moved(eye, points, how, thick=None):
    """`points` (armature space) of `eye` after `how`. With `thick` they are one piece of the eye: closing, it comes to
    the line whole, no thicker than `thick` of the eye's height. Otherwise they are skin, whose every point goes to the
    line."""
    out = points.copy()
    low, high = eye.low, eye.high
    line = low[2] + CLOSE_AT * (high[2] - low[2])
    if how in ('CLOSE', 'ARC'):
        lift = 0.0
        if how == 'ARC':
            middle, half = (low[0] + high[0]) / 2.0, max((high[0] - low[0]) / 2.0, 1e-9)
            lift = ARCH * (high[2] - low[2]) * np.clip(1.0 - ((points[:, 0] - middle) / half) ** 2, 0.0, 1.0)
        if thick is not None:
            bottom, top = float(points[:, 2].min()), float(points[:, 2].max())
            height = max(top - bottom, 1e-9)
            out[:, 2] = line + lift + (points[:, 2] - (bottom + top) / 2.0) * min(1.0, thick * (high[2] - low[2]) / height)
        else:
            out[:, 2] = line + lift + (points[:, 2] - line) * KEEP
    else:
        middle = (low + high) / 2.0
        for axis in (0, 2):
            out[:, axis] = middle[axis] + (points[:, axis] - middle[axis]) * WIDEN
    return out


def _skin(rig, eyes, meshes):
    """{Body mesh: {side: (vertex indices, fade)}}: the face skin under each eye (module docstring)."""
    head = _head(rig)
    bodies = _bodies(rig, meshes)
    pieces = {}
    for eye in eyes.values():
        for obj, piece in eye.pieces:
            pieces.setdefault(obj, set()).update(piece.tolist())
    out = {}
    for obj in bodies:
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


def _mouth_band(eyes, size):
    """(bottom, top) heights in armature space a mouth lies between, below `eyes`."""
    apart = abs(eyes["LEFT"].low[0] + eyes["LEFT"].high[0] - eyes["RIGHT"].low[0] - eyes["RIGHT"].high[0]) / 2.0
    lowest = min(eye.low[2] for eye in eyes.values())
    return lowest - MOUTH * apart, lowest - 0.03 * size


def lips(rig, meshes, eyes):
    """(object, vertices) of the ring of open edges a mouth that opens leaves: thin and wide, on the skin of a Body and not
    round a loose piece of it (teeth behind the lips), where a mouth lies; the widest, or None."""
    head = _head(rig)
    if head is None or not eyes:
        return None
    centre, size = head
    middle_x = (eyes["LEFT"].low[0] + eyes["LEFT"].high[0] + eyes["RIGHT"].low[0] + eyes["RIGHT"].high[0]) / 4.0
    bottom, top = _mouth_band(eyes, size)
    best, widest = None, 0.0
    for obj in _bodies(rig, meshes):
        rest = _rest(rig, obj)
        skin = np.zeros(len(rest), dtype=bool)
        skin[max(_pieces(obj.data), key=len)] = True
        for ring in _rings(obj.data):
            low, high = rest[ring].min(axis=0), rest[ring].max(axis=0)
            middle, wide = (low + high) / 2.0, high[0] - low[0]
            if (skin[ring].all() and abs(middle[0] - middle_x) < 0.06 * size and bottom < middle[2] < top
                    and middle[1] < centre[1] and wide >= 0.05 * size and high[2] - low[2] <= THIN * wide
                    and wide > widest):
                best, widest = (obj, ring), wide
    return best


def slit_mouth(rig, meshes, eyes):
    """(middle, half width) in armature space of the lips of a mouth that opens, or None."""
    found = lips(rig, meshes, eyes)
    if found is None:
        return None
    points = _rest(rig, found[0])[found[1]]
    return (points.min(axis=0) + points.max(axis=0)) / 2.0, np.ptp(points[:, 0]) / 2.0


def drawn_mouth(rig, meshes, eyes):
    """(middle, half width) in armature space of a mouth drawn on the Body's face below the eyes, or None."""
    head = _head(rig)
    if head is None or not eyes:
        return None
    centre, size = head
    middle_x = (eyes["LEFT"].low[0] + eyes["LEFT"].high[0] + eyes["RIGHT"].low[0] + eyes["RIGHT"].high[0]) / 4.0
    bottom, top = _mouth_band(eyes, size)
    low = np.array((middle_x - 0.25 * size, 0.0, bottom))
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


def piece_mouth(rig, meshes, eyes):
    """(middle, half width) in armature space of the loose pieces in the middle of the face below the eyes (a mouth
    built of pieces), or None."""
    head = _head(rig)
    if head is None or not eyes:
        return None
    centre, size = head
    middle_x = (eyes["LEFT"].low[0] + eyes["LEFT"].high[0] + eyes["RIGHT"].low[0] + eyes["RIGHT"].high[0]) / 4.0
    bottom, top = _mouth_band(eyes, size)
    found = []
    for obj in meshes:
        if not _is_mesh_of(rig, obj) or not len(obj.data.vertices):
            continue
        rest = _rest(rig, obj)
        for piece in _pieces(obj.data):
            if len(piece) < FEWEST:
                continue
            p = rest[piece]
            middle = (p.min(axis=0) + p.max(axis=0)) / 2.0
            if (abs(middle[0] - middle_x) < 0.06 * size and middle[1] < centre[1] and bottom < middle[2] < top
                    and np.ptp(p, axis=0).max() < WIDEST * size and np.ptp(p[:, 0]) >= 0.05 * size):  # a nose is none
                found.append(p)
    if not found:
        return None
    groups = []
    for p in sorted(found, key=lambda p: -p[:, 2].max()):
        if groups and p[:, 2].max() >= groups[-1][1] - TOGETHER * size:
            groups[-1][1] = min(groups[-1][1], p[:, 2].min())
            groups[-1][0].append(p)
        else:
            groups.append([[p], p[:, 2].min()])
    points = np.concatenate(max(groups, key=lambda group: len(group[0]))[0])
    width = np.ptp(points[:, 0])
    if width < 0.05 * size:
        return None
    return (points.min(axis=0) + points.max(axis=0)) / 2.0, width / 2.0


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


def _targets(obj, slot, name, replace):
    """The keys to write `name`'s shape into. Asked to `replace`, every key of its slot. Otherwise a key of its slot
    that moves nothing, or none when one moves. A new key under `name` when the slot has none."""
    key = obj.data.shape_keys
    if key is None:
        obj.shape_key_add(name="Basis", from_mix=False)
        key = obj.data.shape_keys
    blocks = [b for b in key.key_blocks if b != key.reference_key and expressions.slot_of(b.name) == slot]
    if replace:
        return blocks or [obj.shape_key_add(name=name, from_mix=False)]
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    if any(expressions.key_moves(block, base) for block in blocks):
        return []
    return blocks[:1] or [obj.shape_key_add(name=name, from_mix=False)]


def _done(meshes):
    """The slots of KEYS a key moves on one of `meshes`."""
    out = set()
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        base = np.empty(len(key.reference_key.data) * 3, np.float32)
        key.reference_key.data.foreach_get("co", base)
        for block in key.key_blocks:
            if block != key.reference_key and expressions.slot_of(block.name) is not None \
                    and expressions.key_moves(block, base):
                out.add(expressions.slot_of(block.name))
    return out


def _clear(obj, slots):
    """The keys of `slots` on `obj` go back to moving nothing, and off."""
    key = obj.data.shape_keys
    if key is None:
        return
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    for block in key.key_blocks:
        if block != key.reference_key and expressions.slot_of(block.name) in slots:
            block.data.foreach_set("co", base)
            block.value = 0.0


def write_key(rig, obj, moved, slot, name, replace):
    """`moved` (offsets of `obj` in armature space) into the keys of `slot` of `obj` (_targets); returns their names."""
    blocks = _targets(obj, slot, name, replace)
    if not blocks:
        return []
    key = obj.data.shape_keys
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    base = base.reshape(-1, 3)
    to_arm = np.array((rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
    for block in blocks:
        block.data.foreach_set("co", (base + moved @ np.linalg.inv(to_arm).T).ravel())
        block.value = 0.0  # off until used: a new shape key starts at 1
    return [block.name for block in blocks]


def sculpt(rig, meshes, replace=False):
    """Make the eye keys on the meshes holding eye pieces; returns [(key name, [mesh names])], nothing without eyes. An
    expression moving on any mesh of the character is left to that key: the skin closing over the eyes by a key of its
    own would close them twice. With `replace` the keys of those expressions are written again, whatever they held
    (module docstring)."""
    eyes = find_eyes(rig, meshes)
    if not eyes:
        return []
    skin = _skin(rig, eyes, meshes)
    hidden = {side: _hidden(rig, eye) for side, eye in eyes.items()}
    mouth = slit_mouth(rig, meshes, eyes) or drawn_mouth(rig, meshes, eyes) or piece_mouth(rig, meshes, eyes)
    smiling = _bodies(rig, meshes) if mouth is not None else []
    holders = []
    for eye in eyes.values():
        for obj, _piece in eye.pieces:
            if obj not in holders:
                holders.append(obj)
    holders = list(dict.fromkeys(holders + list(skin) + smiling))
    if replace:
        for obj in meshes:
            if _is_mesh_of(rig, obj) and obj not in holders:
                _clear(obj, {slot for _name, slot, _sides, _how in KEYS})
    done = set() if replace else _done([obj for obj in meshes if _is_mesh_of(rig, obj)])
    made = {}
    for name, slot, sides, how in KEYS:
        if slot in done:
            continue
        for obj in holders:
            if len(sides) == 1 and has_mirror(obj):
                continue
            rest = _rest(rig, obj)
            moved = np.zeros_like(rest)
            for side in sides:
                for i, (owner, piece) in enumerate(eyes[side].pieces):
                    if owner == obj:
                        thick = KEEP if i in hidden[side] else LINE
                        moved[piece] = _moved(eyes[side], rest[piece], how, thick) - rest[piece]
                near, fade = skin.get(obj, {}).get(side, ((), None))
                if len(near):
                    moved[near] = (_moved(eyes[side], rest[near], how) - rest[near]) * fade[:, None]
            if how == 'ARC' and obj in smiling:
                moved += _smile(rest, mouth, _head(rig)[0][1])
            if not moved.any():  # the body under a face of its own: no key that moves nothing
                if replace:
                    _clear(obj, {slot})
                continue
            for block in write_key(rig, obj, moved, slot, name, replace):
                made.setdefault(block, []).append(obj.name)
    return list(made.items())
