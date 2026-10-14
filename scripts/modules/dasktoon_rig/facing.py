# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Which way a character faces, and turning it round to face the front (-Y), where the standard skeleton and Unity's
front are (lr_shape, one of the real models, faced +Y: the auto rig put its left on its right and bent its knees
forward).

Its feet tell: a foot reaches forward past the lower leg above it. The lower legs are found just above the floor, split
across the way they spread; each foot is the soles nearest its leg, all of them near it (the hem of a long dress or a
stand under the feet is no foot)."""

import math

import numpy as np
from mathutils import Matrix

SOLES = 0.03  # (x height) the soles: this near the floor
LEGS = (0.06, 0.12)  # (x height) the lower legs: this high
REACH = 0.01  # (x height) a foot reaching less far past its leg tells nothing
FOOT = 0.12  # (x height) a foot lies this near its leg
AGREE = math.radians(45.0)  # the two feet reach the same way within this
AXIS = math.radians(30.0)  # a character facing within this of an axis faces it; between two, it is not turned


def feet(world, height, floor):
    """(where the character stands (x, y), the horizontal unit direction its feet reach (x, y)) of a character `height`
    tall standing on `floor`, made of the vertices `world` (n x 3); None when its feet do not tell."""
    z = (world[:, 2] - floor) / height
    soles = world[z < SOLES, :2]
    legs = world[(z > LEGS[0]) & (z < LEGS[1]), :2]
    if len(soles) == 0 or len(legs) < 2:
        return None
    middle = legs.mean(axis=0)
    across = np.linalg.svd(legs - middle, full_matrices=False)[2][0]
    side = (legs - middle) @ across > 0.0
    if side.all() or not side.any():
        return None
    centres = np.array([legs[side].mean(axis=0), legs[~side].mean(axis=0)])
    nearest = np.argmin(np.linalg.norm(soles[:, None, :] - centres[None], axis=2), axis=1)
    reaches = []
    for k in range(2):
        mine = soles[nearest == k]
        if len(mine) == 0 or np.linalg.norm(mine - centres[k], axis=1).max() > FOOT * height:
            return None
        reach = mine.mean(axis=0) - centres[k]
        if np.linalg.norm(reach) < REACH * height:
            return None
        reaches.append(reach / np.linalg.norm(reach))
    if reaches[0] @ reaches[1] < math.cos(AGREE):
        return None
    direction = reaches[0] + reaches[1]
    return centres.mean(axis=0), direction / np.linalg.norm(direction)


def _wrapped(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def turn_to_front(direction):
    """The turn (radians about +Z, a multiple of a quarter) bringing `direction` (x, y) to -Y; 0 when it is within
    AXIS of -Y, or of no axis."""
    angle = math.atan2(direction[1], direction[0])
    for axis in (-0.5 * math.pi, 0.0, 0.5 * math.pi, math.pi):
        if abs(_wrapped(angle - axis)) <= AXIS:
            return _wrapped(-0.5 * math.pi - axis)
    return 0.0


def _ancestors(obj):
    parent = obj.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def face_front(context, objects, body=None):
    """Turn `objects` (and what hangs from them) round the vertical through where the character stands, to face -Y,
    when the feet of `body` (meshes; default `objects`) tell it faces another way. Returns the turn (radians about +Z;
    0 when none)."""
    from .body_shape import evaluated
    shown = [evaluated(context, obj)[0] for obj in (body or objects) if obj.type == 'MESH']
    world = np.concatenate(shown) if shown else np.zeros((0, 3))
    if len(world) == 0:
        return 0.0
    floor, height = world[:, 2].min(), np.ptp(world[:, 2])
    found = feet(world, height, floor) if height > 0.0 else None
    if found is None:
        return 0.0
    (x, y), direction = found
    turn = turn_to_front(direction)
    if turn == 0.0:
        return 0.0
    rotation = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(turn, 4, 'Z') @ Matrix.Translation((-x, -y, 0.0))
    moving = set(objects)
    for obj in objects:
        if not any(parent in moving for parent in _ancestors(obj)):
            obj.matrix_world = rotation @ obj.matrix_world
    context.view_layer.update()
    return turn
