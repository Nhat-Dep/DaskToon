# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fingers fitted to the hand of the Body (docs/superpowers/specs/2026-10-19-dasktoon-rig-fingers-design.md). Fit to
Parts put the template's fingers on the hand by the arm's turn and scale alone: on the real models filie and lr_shape
the thumb stuck out of the hand and the other fingers stopped short of their tips.

The vertices of the Body ahead of the wrist are laid flat on the palm (their two widest directions) and drawn on a grid,
as the front view of the body is (body_shape). Walking from the wrist, the tips of the fingers are the farthest pixels
round about; from each tip the walk back to where the band widens finds the knuckle (body_shape.Shape.limb). With five
tips, the one at the front of the character (-Y) is the thumb, then the index, middle, ring and little finger; each
finger's three bones lie on the line from knuckle to tip, in the middle of the hand's thickness there. A hand without
five fingers apart (a fist, a mitten, a chibi's round hand) keeps the template's fingers."""

import numpy as np

from . import body_shape

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
SEGMENTS = ("Proximal", "Intermediate", "Distal")
JOINTS = (0.0, 0.45, 0.75, 1.0)  # along a finger from knuckle to tip: the heads of its bones, then the last tail
REACH = 1.6  # (x the template hand's length, wrist to the middle finger's tip) the hand is this far ahead of the wrist
BEHIND = 0.15  # (x the same) and the walk starts this far behind it
GRID = 256  # pixels over the reach
TIP_WINDOW = 2  # a tip is the farthest pixel of the walk within this many pixels round it ...
TIP_GAP = 0.012  # ... and at least this far (x the reach) from a farther tip
SAME = 0.75  # two tips whose fingers end nearer than this (x the finger's width) are one finger
FINGER_LENGTH = (0.15, 0.85)  # (x the hand's length, wrist to the farthest tip) a finger is this long


class _Flat(body_shape.Shape):
    """The silhouette of points laid flat (2D), for the walks of body_shape.Shape."""

    def __init__(self, points, step):
        self.step, self.height = step, step * GRID
        self.origin = points.min(axis=0) - step
        size = tuple(((points.max(axis=0) - self.origin) / step).astype(int)[::-1] + 2)
        cells = ((points - self.origin) / step).astype(int)
        mask = np.zeros(size, bool)
        mask[cells[:, 1], cells[:, 0]] = True
        self.mask = body_shape._largest(mask)


def _hand(meshes, wrist, along, reach):
    """(vertices n x 3, triangles m x 3) of `meshes` [(world, tris)] from BEHIND the wrist to `reach` ahead of it,
    near the forearm's line."""
    verts, tris = [], []
    for world, triangles in meshes:
        rel = world - wrist
        ahead = rel @ along
        aside = np.linalg.norm(rel - np.outer(ahead, along), axis=1)
        keep = (ahead > -BEHIND * reach / REACH) & (ahead < reach) & (aside < 0.6 * reach)
        if not keep.any():
            continue
        index = np.full(len(world), -1)
        index[keep] = np.arange(keep.sum()) + sum(len(v) for v in verts)
        inside = triangles[keep[triangles].all(axis=1)]
        verts.append(world[keep])
        tris.append(index[inside])
    if not verts:
        return None
    return np.concatenate(verts), np.concatenate(tris) if tris else np.zeros((0, 3), int)


def _tips(steps, gap):
    """Pixels (row, col) of the fingertips: the farthest of the walk round about, apart, the farthest first."""
    reached = steps >= 0
    best = np.where(reached, steps, -1)
    padded = np.pad(best, TIP_WINDOW, constant_values=-1)
    local = np.full(best.shape, -1)
    for dr in range(2 * TIP_WINDOW + 1):
        for dc in range(2 * TIP_WINDOW + 1):
            local = np.maximum(local, padded[dr:dr + best.shape[0], dc:dc + best.shape[1]])
    rows, cols = np.nonzero(reached & (best == local) & (best >= 0.5 * best.max()))
    order = np.argsort(-best[rows, cols])
    out = []
    for k in order:
        here = np.array((rows[k], cols[k]))
        if all(np.linalg.norm(here - other) >= gap for other in out):
            out.append(here)
    return [tuple(tip) for tip in out]


def side(out, meshes, prefix):
    """{bone: (head, tail, z axis)} (numpy, world) of the fingers of the hand `prefix` ("Left" or "Right") of `out`
    fitted to `meshes` [(world, tris)], or None when the hand does not show five fingers apart."""
    wrist = np.array(out[prefix + "Hand"][0])
    along = wrist - np.array(out[prefix + "LowerArm"][0])
    along /= np.linalg.norm(along)
    template = np.linalg.norm(np.array(out[prefix + "MiddleDistal"][1]) - wrist)
    reach = REACH * template
    found = _hand(meshes, wrist, along, reach)
    if found is None or len(found[0]) < 10 or not len(found[1]):
        return None
    verts, tris = found
    ahead = verts[(verts - wrist) @ along > 0.0]
    if len(ahead) < 10:
        return None
    centred = ahead - ahead.mean(axis=0)
    thick = np.linalg.svd(centred, full_matrices=False)[2][2]  # the hand's thinnest direction
    a = along - (along @ thick) * thick
    a /= np.linalg.norm(a)
    b = np.cross(thick, a)
    local = np.stack([(verts - wrist) @ a, (verts - wrist) @ thick, (verts - wrist) @ b], axis=1)
    step = reach / GRID
    flat = _Flat(body_shape._surface(local, tris, step, np.random.default_rng(0)), step)
    rows, cols = np.nonzero(flat.mask)
    start = int(np.argmin(np.linalg.norm(flat.point(rows, cols), axis=1)))
    steps = body_shape.walk(flat.mask, (rows[start], cols[start]))
    limbs = [limb for limb in (flat.limb(tip) for tip in _tips(steps, TIP_GAP * GRID)) if limb is not None]
    if not limbs:
        return None
    length = max(np.linalg.norm(limb.end) for limb in limbs)
    fingers = []
    for limb in limbs:  # the farthest first; tips on one finger (a flat or broad end) give that finger again
        if (FINGER_LENGTH[0] <= np.linalg.norm(limb.end - limb.base) / length <= FINGER_LENGTH[1]
                and all(np.linalg.norm(limb.end - other.end) >= SAME * other.width for other in fingers)):
            fingers.append(limb)
    if len(fingers) != 5:
        return None

    def placed(point, radius):
        near = np.linalg.norm(local[:, [0, 2]] - point, axis=1) < radius
        depth = float(np.median(local[near, 1])) if near.sum() >= 3 else 0.0
        return wrist + a * point[0] + thick * depth + b * point[1]

    lines = []
    for limb in fingers:
        radius = max(limb.width / 2.0, 2.0 * step)
        lines.append([placed(limb.base + (limb.end - limb.base) * share, radius) for share in JOINTS])
    lines.sort(key=lambda line: line[-1][1])  # front (-Y) first: the thumb
    axis = thick if thick @ np.array(out[prefix + "MiddleProximal"][2]) > 0.0 else -thick
    result = {}
    for finger, points in zip(FINGERS, lines):
        for k, segment in enumerate(SEGMENTS):
            result[prefix + finger + segment] = (points[k], points[k + 1], axis)
    return result


def fit(out, meshes, middle):
    """Move the fingers of `out` ({bone: (head, tail, z axis)}, world) onto the fingers of the hands of `meshes` (the
    Body [(world, tris)]); both sides the same, mirrored about x = `middle`. Returns the sides fitted."""
    from mathutils import Vector
    found = {prefix: side(out, meshes, prefix) for prefix in ("Left", "Right")}
    if not any(found.values()):
        return []
    flip = np.array([-1.0, 1.0, 1.0])

    def mirrored(point):
        return np.array((2.0 * middle - point[0], point[1], point[2]))

    left, right = found["Left"], found["Right"]
    for name in list((left or right)):
        other = ("Right" + name[4:]) if name.startswith("Left") else ("Left" + name[5:])
        own, theirs = (left, right) if name.startswith("Left") else (right, left)
        head, tail, axis = own[name] if own else (mirrored(theirs[other][0]), mirrored(theirs[other][1]),
                                                     theirs[other][2] * flip)
        if own and theirs:
            head = (head + mirrored(theirs[other][0])) / 2.0
            tail = (tail + mirrored(theirs[other][1])) / 2.0
            axis = axis + theirs[other][2] * flip
            axis /= np.linalg.norm(axis)
        out[name] = (Vector(head), Vector(tail), Vector(axis))
        out[other] = (Vector(mirrored(head)), Vector(mirrored(tail)), Vector(axis * flip))
    return [prefix for prefix, value in found.items() if value]
