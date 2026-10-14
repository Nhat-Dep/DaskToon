# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Cross-sections of a character's meshes and the middle lines of its arms and legs (the joint accuracy measured on
tdt and lr_shape: hips 4 to 7 cm behind the thighs, ankles 3 to 11 cm off the shins, wrists 1 to 2 cm off the
forearms; depth read from every vertex near a point in the front view took in hair hanging behind the hips and the
heels of shoes).

A plane across a limb cuts its surface in closed outlines. The limb is the innermost outline round the bone (a leg
inside a skirt, the skin inside a shell a few millimetres out for the anime outline), or the nearest one when the bone
is outside it; its centre by area is the middle of the limb there. The joints of each arm and leg move onto the line
through the middles of their limb, both sides alike; the spine and neck, front to back, onto the middles of the body
at their joints (the median depth of the torso's vertices put the waists of tdt and lr_shape 10 to 12 cm behind their
middles)."""

import numpy as np

from mathutils import Vector

UPPER_SAMPLES = (0.35, 0.5, 0.65, 0.8)  # along an upper arm or thigh: away from the shoulder or the crotch
LOWER_SAMPLES = (0.2, 0.35, 0.5, 0.65)  # along a forearm or shin: away from the hand or the foot
REACH = 0.1  # (x height) outlines this near the bone
TRUNK_REACH = 0.3  # (x height) the same for the spine: the body is wider than a limb (the neck is as a limb: wider,
# its cut takes in the head and hair round it)
WIDEST = 0.15  # (x height) a wider outline is no limb (the torso)
MOVE = 0.08  # (x height) a joint moves at most this far (farther, the outlines are not the limb)
LIMBS = (("UpperArm", "LowerArm", "Hand"), ("UpperLeg", "LowerLeg", "Foot"))
TRUNK = ("Hips", "Spine", "Chest", "UpperChest", "Neck")  # their middles (at their ends: the crotch, the chin)
LIMB_WORDS = ("UpperArm", "LowerArm", "Hand", "Thumb", "Index", "Middle", "Ring", "Little", "UpperLeg", "LowerLeg",
              "Foot", "Toes")


def outlines(world, tris, point, along, reach):
    """The closed outlines [(n x 3 world points)] where the plane through `point` across `along` cuts the triangles
    `tris` of `world` with a corner within `reach` of it (cut short there, an outline is not closed and is left out)."""
    near = np.linalg.norm(world - point, axis=1) < reach
    side = (world - point) @ along
    keep = near[tris].any(axis=1) & (side[tris].min(axis=1) < 0.0) & (side[tris].max(axis=1) > 0.0)
    links, spot = {}, {}
    for tri in tris[keep]:
        ends = []
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if (side[a] < 0.0) != (side[b] < 0.0):
                key = (min(a, b), max(a, b))
                spot[key] = world[a] + (world[b] - world[a]) * (side[a] / (side[a] - side[b]))
                ends.append(key)
        if len(ends) == 2:
            links.setdefault(ends[0], []).append(ends[1])
            links.setdefault(ends[1], []).append(ends[0])
    loops, seen = [], set()
    for first in links:
        if first in seen:
            continue
        loop, previous, current = [first], None, first
        seen.add(first)
        while True:
            following = [k for k in links[current] if k != previous and k not in seen]
            if not following:
                break
            previous, current = current, following[0]
            seen.add(current)
            loop.append(current)
        if len(loop) >= 3 and first in links[current]:
            loops.append(np.array([spot[k] for k in loop]))
    return loops


def _across(along):
    u = np.cross(along, [0.0, 0.0, 1.0] if abs(along[2]) < 0.9 else [1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    return u, np.cross(along, u)


def outline(loop, point, along):
    """(area, centre (world), whether `point` is inside) of an outline in the plane across `along`."""
    u, v = _across(along)
    x, y = (loop - point) @ u, (loop - point) @ v
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    area = cross.sum() / 2.0
    if abs(area) < 1e-12:
        return 0.0, loop.mean(axis=0), False
    cx, cy = ((x + x1) * cross).sum() / (6.0 * area), ((y + y1) * cross).sum() / (6.0 * area)
    inside = False
    for i in range(len(x)):  # even-odd rule from the point, the origin of the plane
        if (y[i] > 0.0) != (y1[i] > 0.0) and x[i] + (x1[i] - x[i]) * (-y[i]) / (y1[i] - y[i]) > 0.0:
            inside = not inside
    return abs(area), point + cx * u + cy * v, inside


def section(meshes, point, along, height, reach=REACH, round_only=False):
    """(centre, radius) of the limb round `point` across `along`: the innermost outline of `meshes` [(world, tris)]
    within `reach` (x height) round it, else (unless `round_only`) the nearest; None when there is none of a limb's
    size."""
    found = []
    for world, tris in meshes:
        for loop in outlines(world, tris, point, along, reach * height):
            area, centre, inside = outline(loop, point, along)
            radius = np.sqrt(area / np.pi)
            if 0.0 < radius < WIDEST * height and (inside or not round_only):
                found.append((not inside, area if inside else np.linalg.norm(centre - point), centre, radius))
    if not found:
        return None
    _outside, _key, centre, radius = min(found, key=lambda f: (f[0], f[1]))
    return centre, radius


def _line(meshes, start, end, samples, height):
    """(point, unit direction) of the middle line of the limb along start→end, through the middles of its sections at
    `samples` of the way; None when fewer than three are found."""
    along = (end - start) / np.linalg.norm(end - start)
    centres = []
    for share in samples:
        for group in meshes:  # the skin first, else the clothes on it as well
            found = section(group, start + (end - start) * share, along, height)
            if found is not None:
                centres.append(found[0])
                break
    if len(centres) < 3:
        return None
    centres = np.array(centres)
    middle = centres.mean(axis=0)
    direction = np.linalg.svd(centres - middle)[2][0]
    return middle, direction if direction @ along > 0.0 else -direction


def _onto(line, point):
    middle, direction = line
    return middle + direction * ((point - middle) @ direction)


def centre_limbs(out, meshes, height):
    """Move the shoulders, elbows, wrists, hips, knees and ankles of `out` ({bone: (head, tail, z axis)}, world) onto
    the middle lines of the limbs of `meshes` (groups of [(world vertices, triangles)], the skin first), both sides the
    same (the rig mirrors). A joint whose limb is not found, or which would move more than MOVE of the height, stays."""
    moves = {}
    for side in ("Left", "Right"):
        for upper, lower, end in LIMBS:
            names = [side + upper, side + lower, side + end]
            if any(name not in out for name in names):
                continue
            joints = [np.array(out[names[0]][0]), np.array(out[names[1]][0]), np.array(out[names[2]][0])]
            above = _line(meshes, joints[0], joints[1], UPPER_SAMPLES, height)
            below = _line(meshes, joints[1], joints[2], LOWER_SAMPLES, height)
            found = [_onto(above, joints[0]) if above else None,
                     np.mean([_onto(line, joints[1]) for line in (above, below) if line], axis=0)
                     if above or below else None,
                     _onto(below, joints[2]) if below else None]
            for k, place in enumerate(found):
                if place is not None and np.linalg.norm(place - joints[k]) < MOVE * height:
                    moves[(side, upper, k)] = place - joints[k]
    for upper, lower, end in LIMBS:  # mirrored: each side moves by the mean of its own move and the other's
        for k in range(3):
            left, right = moves.get(("Left", upper, k)), moves.get(("Right", upper, k))
            if left is None and right is None:
                continue
            if left is None:
                left = right * np.array([-1.0, 1.0, 1.0])
            if right is None:
                right = left * np.array([-1.0, 1.0, 1.0])
            shared = (left + right * np.array([-1.0, 1.0, 1.0])) / 2.0
            for side, move in (("Left", shared), ("Right", shared * np.array([-1.0, 1.0, 1.0]))):
                _move_joint(out, side, (upper, lower, end), k, Vector(move))


def centre_trunk(out, meshes, height):
    """Move the spine and neck of `out` ({bone: (head, tail, z axis)}, world) front to back onto the middles of the
    body's sections round the middles of the bones of TRUNK (`meshes` as in centre_limbs; cut at a joint, the neck's
    top took in the head and the hips' the thighs), and the bones hanging from them with them (the head, the face, the
    shoulders' roots): each point by the moves at the heights next to it, in proportion, above the neck's middle as it
    (a spine bending smoothly from the middle of the chest to the middle of the neck: moved whole, the neck stood
    straight on a bent spine and turning the head swung the hair behind it further, tearing it). A bone without a
    section round it (a hand hanging beside the waist is none), or which would move more than MOVE of the height,
    does not count; the arms and legs stay."""
    heights, moves = [], []
    for name in TRUNK:
        if name not in out:
            continue
        head, tail, _axis = out[name]
        middle, along = np.array((head + tail) / 2.0), np.array(tail - head)
        if np.linalg.norm(along) < 1e-9:
            continue
        for group in meshes:
            reach = REACH if name == "Neck" else TRUNK_REACH
            found = section(group, middle, along / np.linalg.norm(along), height, reach, round_only=True)
            if found is not None:
                if abs(found[0][1] - middle[1]) < MOVE * height:
                    heights.append(middle[2])
                    moves.append(found[0][1] - middle[1])
                break
    if not heights:
        return
    limbs = [name for name in out if any(word in name for word in LIMB_WORDS)]
    stay = [point for name in limbs for point in out[name][:2]]

    def moved(point):
        if any((point - other).length < 1e-6 for other in stay):
            return point
        return point + Vector((0.0, float(np.interp(point.z, heights, moves)), 0.0))

    for name, (head, tail, axis) in list(out.items()):
        if name not in limbs:
            out[name] = (moved(head), moved(tail), axis)


def _move_joint(out, side, chain, k, move):
    """Move joint k of the chain (0: its root, 1: its middle, 2: its end) in `out`: the heads of the bones starting
    there and the tails of the bones ending there."""
    upper, lower, end = (side + name for name in chain)
    joint = out[[upper, lower, end][k]][0].copy()
    for name, (head, tail, axis) in list(out.items()):
        new_head = head + move if (head - joint).length < 1e-6 else head
        new_tail = tail + move if (tail - joint).length < 1e-6 else tail
        if new_head is not head or new_tail is not tail:
            out[name] = (new_head, new_tail, axis)
