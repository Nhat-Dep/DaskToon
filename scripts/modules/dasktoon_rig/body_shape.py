# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The shape of a character seen from the front, for Fit to Parts (anime rig spec 4.3). Added after the real model
test, where fitting the template to the bounding box gave T-pose arms 0.7 m from the hands of an A-pose chibi and a
spine behind the body (the box held the ears).

The front silhouette of the Body and Clothing meshes is drawn on a grid of GRID pixels over the character's height;
only its largest piece counts (a blade or a loose strand is not a limb). Walking from a hand tip (the pixel farthest out
on that side) or a sole (the lowest pixel on that side) over the silhouette, the band of pixels at each walked distance
stays as wide as the limb until the walk reaches the body, where it keeps widening: there the limb starts. The limb's
pixels give its line (principal axis); depth comes from the vertices near a point. The template's arms and legs are then
turned and scaled onto the limbs found, and its spine stretched between the hips and shoulders found. Last, the joints
of the arms and legs move onto the middle lines of the limbs, from their cross-sections (sections.py): real models bend
their elbows and knees, and depth read from the front view took in hair behind the hips and the heels of shoes."""

from collections import namedtuple

import numpy as np
from mathutils import Matrix, Vector

GRID = 256  # pixels over the character's height
ARM_REACH = 0.15  # a hand tip is at least this far (x height) out from the middle
LIMB_LENGTH = (0.08, 0.7)  # a limb is this long (x height)
WIDEN = 1.6  # where a limb meets the body, the band is this many times the limb's width ...
SPREAD = 3.0  # ... and this many times wider SPREAD_AT (x height) further on: the body, not a wider sleeve
SPREAD_AT = 0.06
SLEEVE = (1.5, 0.2)  # past where an arm widens, a band keeping within this ratio over a limb's least length, and
#                     narrower than this (x height), is a wide sleeve round the arm (RGforGame's slim hands out of wide
#                     sleeves); the band through the body spreads wider (only for arms: walking up from the legs, a
#                     torso standing straight keeps the width of a sleeve)
HIP_ABOVE = 0.1  # the hip joint is this part of the leg's length above where the leg meets the body
ARM_UP = 0.57  # an arm is modelled hanging or level: a limb pointing up more than this (sine, 35 deg) is an ear or a
#                twin tail reaching out wider than the hand (RGforGame), and the hand is looked for lower down
ARM_TRIES = 3
# Template heights (x height) of the hip and shoulder joints: the spine is stretched between the heights found.
HIP_Z, SHOULDER_Z = 0.52, 0.78

Limb = namedtuple("Limb", "base end axis width")  # front view (x, z): where it meets the body, its tip or sole


def evaluated(context, obj):
    """(world vertices n x 3, triangles m x 3) of `obj` as shown, modifiers on (a mirrored half is whole)."""
    depsgraph = context.evaluated_depsgraph_get()
    shown = obj.evaluated_get(depsgraph)
    mesh = shown.to_mesh()
    try:
        co = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get("co", co)
        mesh.calc_loop_triangles()
        triangles = np.empty(len(mesh.loop_triangles) * 3, np.int32)
        mesh.loop_triangles.foreach_get("vertices", triangles)
    finally:
        shown.to_mesh_clear()
    matrix = np.array(obj.matrix_world)
    return co.reshape(-1, 3).astype(float) @ matrix[:3, :3].T + matrix[:3, 3], triangles.reshape(-1, 3)


def _surface(vertices, triangles, step, rng):
    """Front (x, z) of points spread over the triangles, about three in a pixel `step` wide, and of the vertices."""
    flat = vertices[:, [0, 2]]
    a, b, c = (vertices[triangles[:, k]] for k in range(3))
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    count = np.minimum(np.ceil(area / (step * step) * 3.0).astype(int), 300) + 1
    which = np.repeat(np.arange(len(triangles)), count)
    u, v = rng.random(len(which)), rng.random(len(which))
    outside = u + v > 1.0
    u[outside], v[outside] = 1.0 - u[outside], 1.0 - v[outside]
    a, b, c = (flat[triangles[which, k]] for k in range(3))
    return np.concatenate([a + (b - a) * u[:, None] + (c - a) * v[:, None], flat])


def _grow(front):
    """`front` and its 8 neighbours."""
    out = front.copy()
    out[1:] |= front[:-1]
    out[:-1] |= front[1:]
    out[:, 1:] |= front[:, :-1]
    out[:, :-1] |= front[:, 1:]
    out[1:, 1:] |= front[:-1, :-1]
    out[1:, :-1] |= front[:-1, 1:]
    out[:-1, 1:] |= front[1:, :-1]
    out[:-1, :-1] |= front[1:, 1:]
    return out


def walk(mask, start):
    """Steps (to one of 8 neighbours) from pixel `start` to every pixel of `mask`; -1 where the walk does not reach."""
    steps = np.full(mask.shape, -1, np.int32)
    front = np.zeros(mask.shape, bool)
    front[start] = True
    steps[start] = 0
    step = 0
    while front.any():
        step += 1
        front = _grow(front) & mask & (steps < 0)
        steps[front] = step
    return steps


def _largest(mask):
    """The largest connected piece of `mask`."""
    left, best, size = mask.copy(), mask, -1
    while left.any():
        piece = walk(left, tuple(np.argwhere(left)[0])) >= 0
        left &= ~piece
        if piece.sum() > size:
            best, size = piece, piece.sum()
    return best


def _line(points):
    """(centre, unit axis) of the principal axis through 2D `points`."""
    centre = points.mean(axis=0)
    _values, vectors = np.linalg.eigh(np.cov((points - centre).T))
    return centre, vectors[:, -1]


class Shape:
    """The front silhouette of `objects` (meshes) on a grid over a character `height` tall standing at `feet`."""

    def __init__(self, context, objects, feet, height):
        self.height, self.step = height, height / GRID
        meshes = [evaluated(context, obj) for obj in objects if obj.type == 'MESH']
        meshes = [(v, t) for v, t in meshes if len(t)]
        self.mask = None
        if not meshes:
            return
        self.vertices = np.concatenate([v for v, _t in meshes])
        self.lowest = [float(v[:, 2].min()) for v, _t in meshes]
        rng = np.random.default_rng(0)  # the same fit every time
        self.points = [_surface(v, t, self.step, rng) for v, t in meshes]
        points = np.concatenate(self.points)
        self.origin = np.array([points[:, 0].min(), min(points[:, 1].min(), feet.z)]) - self.step
        self.size = tuple(((points.max(axis=0) - self.origin) / self.step).astype(int)[::-1] + 2)
        self.mask = self._silhouette(range(len(meshes)))

    def _silhouette(self, which):
        """The largest piece of the silhouette of the meshes numbered `which`."""
        mask = np.zeros(self.size, bool)
        for k in which:
            cells = ((self.points[k] - self.origin) / self.step).astype(int)
            mask[cells[:, 1], cells[:, 0]] = True
        return _largest(mask)

    def point(self, rows, cols):
        """Front (x, z) of the middle of pixels."""
        return self.origin + (np.stack([cols, rows], axis=-1) + 0.5) * self.step

    def pixel(self, xz):
        col, row = ((np.asarray(xz) - self.origin) / self.step).astype(int)
        return min(max(row, 0), self.mask.shape[0] - 1), min(max(col, 0), self.mask.shape[1] - 1)

    def depth(self, xz, radius, fallback):
        """Median y of the vertices within `radius` of front point `xz`, or `fallback`."""
        near = np.hypot(self.vertices[:, 0] - xz[0], self.vertices[:, 2] - xz[1]) < radius
        return float(np.median(self.vertices[near, 1])) if near.sum() >= 3 else fallback

    def limb(self, start, mask=None, sleeves=False):
        """The limb walked from pixel `start` (a hand tip or a sole) over `mask` (default the silhouette) up to where it
        meets the body, or None; with `sleeves`, past wide sleeves round it."""
        steps = walk(self.mask if mask is None else mask, start)
        band = np.bincount(steps[steps >= 0].ravel())
        ahead = max(int(round(SPREAD_AT * GRID)), 3)
        first = max(int(round(LIMB_LENGTH[0] * GRID)), 4)
        for meet in range(first, len(band) - ahead):
            width = np.median(band[meet // 2:meet])
            if all(band[meet + k] > WIDEN * width for k in range(3)) and band[meet + ahead] > SPREAD * width:
                sleeve = band[meet + ahead:meet + ahead + first]
                if (sleeves and len(sleeve) == first and sleeve.max() <= SLEEVE[0] * sleeve.min()
                        and sleeve.max() * self.step < SLEEVE[1] * self.height):
                    continue
                return self._limb_to(steps, start, meet)
        return None

    def _limb_to(self, steps, start, meet):
        """The limb of the pixels walked from `start` in fewer than `meet` steps."""
        points = self.point(*np.nonzero((steps >= 0) & (steps < meet)))
        centre, axis = _line(points)
        if (self.point(*start) - centre) @ axis < 0.0:
            axis = -axis  # towards the tip
        along = (points - centre) @ axis
        across = np.abs((points - centre) @ np.array([-axis[1], axis[0]]))
        edge = self.point(*np.nonzero(steps == meet)).mean(axis=0)
        return Limb(centre + axis * ((edge - centre) @ axis), centre + axis * np.percentile(along, 99.5), axis,
                    4.0 * float(np.median(across)))  # the median distance from the axis is a quarter of the width

    def _length_ok(self, limb):
        length = np.linalg.norm(limb.end - limb.base) / self.height
        return LIMB_LENGTH[0] <= length <= LIMB_LENGTH[1]

    def arm(self, side, middle):
        """The arm on `side` (1: the character's left, +X; -1: right) of the middle x, or None. The hand tip is the
        pixel farthest out on that side; a limb from there pointing up (an ear, a twin tail) is passed over and the
        tip looked for below it."""
        rows, cols = np.nonzero(self.mask)
        xz = self.point(rows, cols)
        below = np.inf
        for _try in range(ARM_TRIES):
            low_enough = (xz[:, 1] > self.origin[1] + 0.2 * self.height) & (xz[:, 1] < below)
            out = np.where(low_enough, side * (xz[:, 0] - middle), -np.inf)
            tip = int(np.argmax(out))
            if out[tip] < ARM_REACH * self.height:
                return None
            limb = self.limb((rows[tip], cols[tip]), self._reaching_down_to(xz[tip, 1], (rows[tip], cols[tip])),
                             sleeves=True)
            if limb is not None and limb.axis[1] > ARM_UP:
                below = min(limb.base[1], limb.end[1])  # up and out: not the arm
                continue
            if limb is None or side * limb.axis[0] <= 0.0 or not self._length_ok(limb):
                return None
            return limb
        return None

    def _reaching_down_to(self, z, tip):
        """The silhouette without the meshes lying wholly above height `z` (twin tails hanging onto the arm: no part of
        it), when pixel `tip` stays in it; else the whole silhouette."""
        below = [k for k, lowest in enumerate(self.lowest) if lowest <= z]
        if len(below) == len(self.lowest):
            return self.mask
        mask = self._silhouette(below)
        return mask if mask[tip] else self.mask

    def leg(self, side, middle):
        """The leg on `side` of the middle x, or None: a limb that stands, apart from the other leg."""
        rows, cols = np.nonzero(self.mask)
        out = side * (self.point(rows, cols)[:, 0] - middle) > 0.01 * self.height
        if not out.any():
            return None
        sole = int(np.argmin(np.where(out, rows, self.mask.shape[0])))
        limb = self.limb((rows[sole], cols[sole]))
        if limb is None or abs(limb.axis[1]) < 0.8 or not self._length_ok(limb):
            return None
        halfway = (limb.base + limb.end) / 2.0
        return None if self.mask[self.pixel((middle, halfway[1]))] else limb


def _mirrored(found, middle):
    """{side: limb}: a side not found mirrors the other one."""
    def mirror(limb):
        flip = np.array([-1.0, 1.0])
        return Limb(limb.base * flip + (2.0 * middle, 0.0), limb.end * flip + (2.0 * middle, 0.0), limb.axis * flip,
                    limb.width)
    return {side: limb or (mirror(found[-side]) if found[-side] is not None else None) for side, limb in found.items()}


def _flip(point, middle):
    """`point` mirrored across the plane x = middle."""
    return Vector((2.0 * middle - point.x, point.y, point.z))


def _similar(a_from, b_from, a_to, b_to):
    """(point map, rotation) turning and scaling segment a_from-b_from onto a_to-b_to."""
    rotation = (b_from - a_from).rotation_difference(b_to - a_to).to_matrix()
    scale = (b_to - a_to).length / (b_from - a_from).length
    return (lambda p: a_to + rotation @ ((p - a_from) * scale)), rotation


def joints(context, objects, feet, height, skin=None):
    """{bone: (head, tail, z axis)} in world space of the standard skeleton fitted to the silhouette of `objects`, for
    a character `height` tall with its feet at `feet`; None when they have no faces. What is not found (arms, legs)
    stays as in the template, at the heights found. The joints of the arms and legs then lie on the middle lines of the
    limbs of `skin` (the Body meshes) where it has them, else of `objects`; the spine and neck in the middle of the
    body, front to back."""
    from . import skeleton
    shape = Shape(context, objects, feet, height)
    if shape.mask is None:
        return None
    middle = float(np.median(shape.vertices[:, 0]))
    arms = _mirrored({side: shape.arm(side, middle) for side in (1, -1)}, middle)
    legs = _mirrored({side: shape.leg(side, middle) for side in (1, -1)}, middle)
    top = feet.z + height
    hip_z, shoulder_z = feet.z + HIP_Z * height, feet.z + SHOULDER_Z * height
    shoulders = {side: arm.base - arm.axis * arm.width / 2.0 for side, arm in arms.items() if arm is not None}
    hips = {side: leg.base[1] + HIP_ABOVE * (leg.base[1] - feet.z) for side, leg in legs.items() if leg is not None}
    if hips:
        hip_z = float(np.mean(list(hips.values())))
    if shoulders:
        shoulder_z = float(np.mean([point[1] for point in shoulders.values()]))
    if not feet.z < hip_z < shoulder_z < top:  # a shape this method misreads: the template's heights
        arms = legs = {1: None, -1: None}
        hip_z, shoulder_z = feet.z + HIP_Z * height, feet.z + SHOULDER_Z * height
    z = shape.vertices[:, 2]
    torso = (z >= hip_z) & (z <= hip_z + 0.75 * (shoulder_z - hip_z))  # below the hair that may hang behind
    middle_y = float(np.median(shape.vertices[torso if torso.any() else slice(None), 1]))
    knots = ((0.0, HIP_Z, SHOULDER_Z, 1.0), (feet.z, hip_z, shoulder_z, top))

    def spine(p):
        return Vector((middle + p.x * height, middle_y + p.y * height, float(np.interp(p.z, *knots))))

    template = {name: (Vector(head), Vector(tail), Vector(axis), parent)
                for name, parent, head, tail, axis in skeleton.bones()}
    ends = {}  # (limb, side): (start, end) in world space
    for side in (1, -1):
        arm, leg = arms[side], legs[side]
        if arm is not None:
            radius = max(arm.width / 2.0, 2.0 * shape.step)
            ends["Arm", side] = (Vector((shoulders[side][0], middle_y, shoulders[side][1])),
                                 Vector((arm.end[0], shape.depth(arm.end, radius, middle_y), arm.end[1])))
        if leg is not None:
            radius = max(leg.width / 2.0, 2.0 * shape.step)
            ankle_z = feet.z + (hip_z - feet.z) * template["LeftFoot"][0].z / HIP_Z
            points = [leg.base + leg.axis * (z - leg.base[1]) / leg.axis[1] for z in (hip_z, ankle_z)]
            ends["Leg", side] = tuple(Vector((point[0], shape.depth(point, radius, middle_y), point[1]))
                                      for point in points)
    for limb in ("Arm", "Leg"):  # both sides found: the average of each and the other mirrored, so the rig mirrors
        if (limb, 1) in ends and (limb, -1) in ends:
            left = tuple((a + _flip(b, middle)) / 2.0 for a, b in zip(ends[limb, 1], ends[limb, -1]))
            ends[limb, 1], ends[limb, -1] = left, tuple(_flip(point, middle) for point in left)
    maps = {}
    for (limb, side), (start, end) in ends.items():
        prefix = "Left" if side == 1 else "Right"
        first, last = (((prefix + "UpperArm", 0), (prefix + "MiddleDistal", 1)) if limb == "Arm"
                       else ((prefix + "UpperLeg", 0), (prefix + "Foot", 0)))
        maps[prefix + limb] = _similar(template[first[0]][first[1]], template[last[0]][last[1]], start, end)
    still = (spine, Matrix.Identity(3))

    def region(name):
        side = next((side for side in ("Left", "Right") if name.startswith(side)), None)
        for limb, members in (("Arm", _arm_bones), ("Leg", _leg_bones)):
            if side is not None and side + limb in maps and name in members(side):
                return maps[side + limb]
        return still

    out = {}
    for name, (head, tail, axis, _parent) in template.items():
        place, rotation = region(name)
        child = next((other for other, (h, _t, _a, parent) in template.items()
                      if parent == name and (h - tail).length < 1e-9), None)
        out[name] = (place(head), (region(child)[0] if child else place)(tail), rotation @ axis)
    from . import sections
    groups = [[evaluated(context, obj) for obj in group if obj.type == 'MESH'] for group in (skin or [], objects)]
    sections.centre_limbs(out, [group for group in groups if group], height)
    sections.centre_trunk(out, [group for group in groups if group], height)
    return out


def _arm_bones(side):
    return {side + name for name in ("UpperArm", "LowerArm", "Hand")} | {
        side + finger + segment for finger in ("Thumb", "Index", "Middle", "Ring", "Little")
        for segment in ("Proximal", "Intermediate", "Distal")}


def _leg_bones(side):
    return {side + name for name in ("UpperLeg", "LowerLeg", "Foot", "Toes")}

