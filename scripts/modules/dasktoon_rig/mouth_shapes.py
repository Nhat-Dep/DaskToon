# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sculpt A I U E O (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part D) for a mouth that opens:
a slit in the skin (eye_shapes.lips) with a mouth built behind it, as characters from games have. The rest have nothing to
open: stretching a drawn line hides it, and a key cannot make a hole.

The lips part round the slit's two paths, most at the middle and not at all at the corners; the skin above and below goes
with them, fading ABOVE and BELOW of half the mouth's width away, across the mouth by as much as a vowel widens it. Of what
lies behind, the tallest pieces are the inside of the mouth: they stay, and the lips part no further than ROOM of the way
to their edge, up and down, and no wider than they reach across, or the mouth would show what lies behind the head.
Nothing behind the slit, no vowels. What else lies behind narrows with the lips: a line of the mouth may be a piece of its
own, and it stood out beside pursed lips. Of that, what lies below the slit, lower teeth and tongue, goes down JAW as far
as the lower lip and never past it, or it comes through the skin under the lip.

The anime shader darkens what is closed in (AO), and nothing is more closed in than the inside of a mouth: Encore's, painted
red, opened black. What lies behind the lips gets a copy of its material without that (INSIDE on its name), in a slot of its
own where it shares a mesh with the skin; the skin keeps its own. This comes with the slit, whether the vowels are made here
or not.

A key of the same vowel that moves is kept, an empty one filled, a missing one added under its VRM 0.x name."""

import bpy
import numpy as np

from . import eye_shapes

# (key, its slot, how far the upper lip rises and the lower lip falls, of half the mouth's width, how wide the mouth gets)
VOWELS = (("a", "A", 0.2, 1.1, 1.0), ("i", "I", 0.06, 0.18, 1.12), ("u", "U", 0.15, 0.26, 0.72),
          ("e", "E", 0.12, 0.45, 1.06), ("o", "O", 0.3, 0.7, 0.78))
ABOVE = 0.7
BELOW = 1.4
SIDES = 1.6  # of half the mouth's width: how far out to the side the skin moves
ROOM = 0.9
JAW = 0.7
TALL = 0.5  # of the tallest piece behind the slit: a piece this tall is the inside of the mouth
NEAR = 6.0  # of half the mouth's width: how far behind the lips, and how big, what belongs to the mouth is
INSIDE = ".Mouth"  # on the name of a material without the darkening of closed-in places


def _smooth(share):
    return share * share * (3.0 - 2.0 * share)


def _paths(mesh, ring, rest):
    """The vertices of `ring` along the upper lip and along the lower one, each from corner to corner."""
    inside = set(ring.tolist())
    next_to = {}
    for a, b in eye_shapes._boundary_points(mesh).tolist():
        if a in inside and b in inside:
            next_to.setdefault(a, []).append(b)
            next_to.setdefault(b, []).append(a)
    corner = int(ring[rest[ring, 0].argmin()])
    other = int(ring[rest[ring, 0].argmax()])
    paths = []
    for first in next_to[corner]:
        path, last = [corner, first], corner
        while path[-1] != other:
            step = next((v for v in next_to[path[-1]] if v != path[-2]), None)
            if step is None or step in path:
                return None
            path.append(step)
        paths.append(path)
    if len(paths) != 2:
        return None
    upper, lower = sorted(paths, key=lambda path: -rest[path, 2].mean())
    return np.array(upper), np.array(lower)


class _Mouth:
    """A mouth that opens: where its lips are, and what lies behind them."""

    def __init__(self, obj, rest, upper, lower, inside, others, behind):
        self.obj, self.rest = obj, rest
        self.middle = (rest[upper, 0].min() + rest[upper, 0].max()) / 2.0
        self.half = (rest[upper, 0].max() - rest[upper, 0].min()) / 2.0
        self.upper = self._along(rest[upper])
        self.lower = self._along(rest[lower])
        self.line = (rest[upper, 2].mean() + rest[lower, 2].mean()) / 2.0
        self.down = self.line - inside[0]  # room under the lips, over them, and to each side
        self.up = inside[1] - self.line
        self.across = min(self.middle - inside[2], inside[3] - self.middle, self.half)
        self.others = others  # [(object, piece, how far below the slit it reaches, None for what lies above it)]
        self.behind = behind  # [(object, piece)]: all that lies behind the lips

    @staticmethod
    def _along(points):
        order = points[:, 0].argsort()
        return points[order, 0], points[order, 2]

    def skin(self):
        """Mask of the vertices of the skin that may move."""
        rest = self.rest
        pieces = eye_shapes._pieces(self.obj.data)
        main = np.zeros(len(rest), dtype=bool)
        main[max(pieces, key=len)] = True
        return main & (np.abs(rest[:, 0] - self.middle) < SIDES * self.half)

    def moved(self, rise, fall, wide):
        """Offsets of the skin for a vowel."""
        rest = self.rest
        out = np.zeros_like(rest)
        free = self.skin()
        across = (rest[:, 0] - self.middle) / self.half
        bulge = np.sqrt(np.clip(1.0 - ((rest[:, 0] - self.middle) / self.across) ** 2, 0.0, 1.0))
        over = rest[:, 2] - np.interp(rest[:, 0], *self.upper)
        under = np.interp(rest[:, 0], *self.lower) - rest[:, 2]
        above = over >= under  # nearer the upper lip's side
        reach_up = _smooth(np.clip(1.0 - np.maximum(over, 0.0) / (ABOVE * self.half), 0.0, 1.0))
        reach_down = _smooth(np.clip(1.0 - np.maximum(under, 0.0) / (BELOW * self.half), 0.0, 1.0))
        rise, fall = self._limited(rise, fall)
        out[:, 2] = np.where(above, rise * reach_up, -fall * reach_down) * bulge
        side = np.clip((SIDES - np.abs(across)) / (SIDES - 1.0), 0.0, 1.0)
        out[:, 0] = (rest[:, 0] - self.middle) * (wide - 1.0) * np.where(above, reach_up, reach_down) * side
        out[~free] = 0.0
        return out

    def _limited(self, rise, fall):
        """How far the lips go, in armature space, for a vowel opening `rise` and `fall` of half the mouth's width."""
        return min(rise * self.half, ROOM * self.up), min(fall * self.half, ROOM * self.down)


def _found(rig, meshes, eyes):
    """The _Mouth of the character, or None without a mouth that opens."""
    found = eye_shapes.lips(rig, meshes, eyes)
    if found is None:
        return None
    obj, ring = found
    rest = eye_shapes._rest(rig, obj)
    paths = _paths(obj.data, ring, rest)
    if paths is None:
        return None
    upper, lower = paths
    points = rest[ring]
    middle, half = (points[:, 0].min() + points[:, 0].max()) / 2.0, np.ptp(points[:, 0]) / 2.0
    line, front = points[:, 2].mean(), points[:, 1].mean()
    behind = []
    for other in meshes:
        if not eye_shapes._is_mesh_of(rig, other) or not len(other.data.vertices):
            continue
        at = eye_shapes._rest(rig, other)
        skin = len(max(eye_shapes._pieces(other.data), key=len))
        for piece in eye_shapes._pieces(other.data):
            p = at[piece]
            low, high = p.min(axis=0), p.max(axis=0)
            deep = (low[1] + high[1]) / 2.0 - front
            if (other != obj or len(piece) != skin) and len(piece) >= eye_shapes.FEWEST and 0.0 < deep < NEAR * half \
                    and abs((low[0] + high[0]) / 2.0 - middle) < 2.0 * half and low[2] < line + 2.0 * half \
                    and high[2] > line - 2.0 * half and np.ptp(p, axis=0).max() < NEAR * half:
                behind.append((other, piece, low, high))
    if not behind:
        return None
    tallest = max(high[2] - low[2] for _obj, _piece, low, high in behind)
    inside = [entry for entry in behind if entry[3][2] - entry[2][2] >= TALL * tallest]
    bottom, top = min(low[2] for _o, _p, low, _h in inside), max(high[2] for _o, _p, _l, high in inside)
    left, right = min(low[0] for _o, _p, low, _h in inside), max(high[0] for _o, _p, _l, high in inside)
    if bottom >= line or top <= line or left >= middle or right <= middle:
        return None
    others = [(other, piece, line - low[2] if (low[2] + high[2]) / 2.0 < line else None)
              for other, piece, low, high in behind if high[2] - low[2] < TALL * tallest]
    return _Mouth(obj, rest, upper, lower, (bottom, top, left, right), others, [entry[:2] for entry in behind])


def _darkens(material):
    """The nodes of `material` that darken what is closed in."""
    tree = material.node_tree if material is not None else None
    found = []
    for node in tree.nodes if tree is not None else ():
        if getattr(node, "use_ao", False):
            factor = next(socket for socket in node.inputs if socket.name == "AO Factor")
            if factor.is_linked or factor.default_value > 0.0:
                found.append(node)
    return found


def _without_darkening(material):
    """The copy of `material` for what lies behind the lips."""
    name = material.name + INSIDE
    copy = bpy.data.materials.get(name)
    if copy is None:
        copy = material.copy()
        copy.name = name
        for node in _darkens(copy):
            node.use_ao = False
    return copy


def _light_the_inside(behind):
    """What lies behind the lips, `behind` [(object, piece)], without the darkening of closed-in places (module docstring)."""
    held = {}
    for obj, piece in behind:
        held.setdefault(obj, set()).update(piece.tolist())
    for obj, vertices in held.items():
        faces = {}
        for polygon in obj.data.polygons:
            if polygon.vertices[0] in vertices:
                faces.setdefault(polygon.material_index, []).append(polygon)
        for index, polygons in faces.items():
            material = obj.material_slots[index].material if index < len(obj.material_slots) else None
            if not _darkens(material):
                continue
            copy = _without_darkening(material)
            if all(p.index in {q.index for q in polygons} for p in obj.data.polygons if p.material_index == index):
                obj.material_slots[index].material = copy  # nothing else uses this slot
                continue
            slot = next((i for i, s in enumerate(obj.material_slots) if s.material == copy), None)
            if slot is None:
                obj.data.materials.append(copy)
                slot = len(obj.material_slots) - 1
            for polygon in polygons:
                polygon.material_index = slot


def sculpt(rig, meshes, replace=False):
    """Make the vowel keys of a mouth that opens; returns [(key name, [mesh names])], nothing without one (module
    docstring). With `replace` the keys of the vowels are written again, whatever they held."""
    eyes = eye_shapes.find_eyes(rig, meshes)
    mouth = _found(rig, meshes, eyes) if eyes else None
    if mouth is None:
        return []
    _light_the_inside(mouth.behind)
    done = set() if replace else eye_shapes._done([obj for obj in meshes if eye_shapes._is_mesh_of(rig, obj)])
    made = {}
    for name, slot, rise, fall, wide in VOWELS:
        if slot in done:
            continue
        moved = {mouth.obj: mouth.moved(rise, fall, wide)}
        drop = mouth._limited(rise, fall)[1]
        for obj, piece, below in mouth.others:
            at = eye_shapes._rest(rig, obj)
            offsets = moved.setdefault(obj, np.zeros_like(at))
            offsets[piece, 0] += (at[piece, 0] - mouth.middle) * (min(wide, 1.0) - 1.0)
            if below is not None:
                offsets[piece, 2] -= min(JAW * drop, max(drop - below, 0.0))
        for obj, offsets in moved.items():
            for block in eye_shapes.write_key(rig, obj, offsets, slot, name, replace):
                made.setdefault(block, []).append(obj.name)
    return list(made.items())
