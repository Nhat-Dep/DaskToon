# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Spring bones of the anime rig (spec 9.3) as plain numpy maths, so DaskToon and the Unity script share one algorithm
(VRM's spring bone): every bone keeps its tail's current and previous world position; a step adds the inertia, a pull
towards the posed direction and gravity, keeps the bone's length and pushes the tail out of capsule colliders. A bone's
tail is along its local +Y, as in Blender."""

import numpy as np

GRAVITY_DIR = np.array((0.0, 0.0, -1.0))


class Params:
    """How a chain sways: stiffness (pull back to the pose), gravity, drag (1 keeps no inertia) and the radius of each
    tail against colliders."""

    def __init__(self, stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03):
        self.stiffness = stiffness
        self.gravity = gravity
        self.drag = drag
        self.radius = radius


class Pose:
    """A chain as animated, without sway: world head of its first bone, world rotation (3x3) of the bone it hangs from,
    each bone's rotation relative to the one before (3x3) and each bone's length."""

    def __init__(self, root_head, parent_rotation, local_rotations, lengths):
        self.root_head = np.asarray(root_head, float)
        self.parent_rotation = np.asarray(parent_rotation, float)
        self.local_rotations = [np.asarray(r, float) for r in local_rotations]
        self.lengths = [float(length) for length in lengths]


class State:
    """Current and previous world position of every tail of a chain."""

    def __init__(self, current, previous=None):
        self.current = np.array(current, float)
        self.previous = np.array(current if previous is None else previous, float)

    def copy(self):
        return State(self.current.copy(), self.previous.copy())


def _unit(vector):
    length = float(np.linalg.norm(vector))
    return vector / length if length > 1e-12 else vector


def from_to(a, b):
    """The rotation (3x3) taking unit vector a to unit vector b along the shortest arc."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    cross = np.cross(a, b)
    cosine = float(a @ b)
    if cosine < -1.0 + 1e-9:
        axis = _unit(np.cross(a, (1.0, 0.0, 0.0)) if abs(a[0]) < 0.9 else np.cross(a, (0.0, 1.0, 0.0)))
        return 2.0 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0.0, -cross[2], cross[1]], [cross[2], 0.0, -cross[0]], [-cross[1], cross[0], 0.0]])
    return np.eye(3) + k + k @ k / (1.0 + cosine)


def reset(pose):
    """The state of a chain hanging in its pose, without sway."""
    tails = []
    head, parent = pose.root_head, pose.parent_rotation
    for local, length in zip(pose.local_rotations, pose.lengths):
        rotation = parent @ local
        head = head + rotation[:, 1] * length
        tails.append(head)
        parent = rotation
    return State(tails)


def rotations(state, pose):
    """World rotations (3x3) that point every bone of the chain at its tail in `state`, without a step."""
    out = []
    head, parent = pose.root_head, pose.parent_rotation
    for i, (local, length) in enumerate(zip(pose.local_rotations, pose.lengths)):
        posed = parent @ local
        rotation = from_to(posed[:, 1], _unit(state.current[i] - head)) @ posed
        out.append(rotation)
        head, parent = head + rotation[:, 1] * length, rotation
    return out


def _push_out(point, a, b, distance):
    """`point` moved out of the capsule of radius `distance` around the segment a-b, if it is inside."""
    axis = b - a
    length2 = float(axis @ axis)
    t = 0.0 if length2 < 1e-18 else min(1.0, max(0.0, float((point - a) @ axis) / length2))
    closest = a + axis * t
    away = point - closest
    gap = float(np.linalg.norm(away))
    if gap >= distance or gap < 1e-12:
        return point
    return closest + away / gap * distance


def step(state, pose, params, colliders, dt):
    """One step of `dt` seconds (spec 9.3): updates `state` and returns the bones' world rotations (3x3).
    `colliders` is a list of (head, tail, radius) capsules in world space."""
    out = []
    head, parent = pose.root_head, pose.parent_rotation
    for i, (local, length) in enumerate(zip(pose.local_rotations, pose.lengths)):
        posed = parent @ local
        rest = posed[:, 1]
        current = state.current[i].copy()
        tail = (current + (current - state.previous[i]) * (1.0 - params.drag) + rest * (params.stiffness * dt)
                + GRAVITY_DIR * (params.gravity * dt))
        tail = head + _unit(tail - head) * length
        for a, b, radius in colliders:
            tail = _push_out(tail, np.asarray(a, float), np.asarray(b, float), radius + params.radius)
            tail = head + _unit(tail - head) * length
        state.previous[i] = current
        state.current[i] = tail
        rotation = from_to(rest, _unit(tail - head)) @ posed
        out.append(rotation)
        head, parent = tail, rotation
    return out
