# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Which way a character faces, and turning it round to face the front (-Y), where the standard skeleton and Unity's
front are (lr_shape, one of the real models, faced +Y: the auto rig put its left on its right and bent its knees
forward).

Its feet tell: a foot reaches forward past the lower leg above it, or at least its toes reach farther than its heel. The
lower legs are found just above the floor, split across the way they spread; each foot is the soles nearest its leg, all
of them near it (the hem of a long dress or a stand under the feet is no foot)."""

import math

import numpy as np
from mathutils import Matrix

SOLES = 0.03  # (x height) the soles: this near the floor
LEGS = (0.06, 0.12)  # (x height) the lower legs: this high
REACH = 0.01  # (x height) a foot reaching less far past its leg tells nothing
TOE = 0.015  # (x height) or its toes reach this much farther forward than its heel back (RGforGame's boots: soles
#              under the shins on the whole, the toes 2.9% farther than the heels)
FOOT = 0.16  # (x height) a foot lies this near its leg (pl1's chunky boots reach 0.124; a long dress's hem is farther)
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
        reach = _reach(mine - centres[k], height)
        if reach is None:
            return None
        reaches.append(reach)
    if reaches[0] @ reaches[1] < math.cos(AGREE):
        return None
    direction = reaches[0] + reaches[1]
    return centres.mean(axis=0), direction / np.linalg.norm(direction)


def _reach(sole, height):
    """The horizontal unit direction a foot of soles `sole` (n x 2, from its leg) reaches; None when it does not
    tell."""
    reach = sole.mean(axis=0)
    if np.linalg.norm(reach) >= REACH * height:
        return reach / np.linalg.norm(reach)
    if len(sole) < 2:
        return None
    length = np.linalg.svd(sole - reach, full_matrices=False)[2][0]  # the way the foot lies
    along = sole @ length
    ahead = along.max() + along.min()  # how much farther one end reaches than the other
    if abs(ahead) < TOE * height:
        return None
    return length if ahead > 0.0 else -length


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


def _shown(context, objects):
    """(world vertices of the meshes among `objects` as shown, the floor, the height); None without any."""
    from .body_shape import evaluated
    shown = [evaluated(context, obj)[0] for obj in objects if obj.type == 'MESH']
    world = np.concatenate(shown) if shown else np.zeros((0, 3))
    if len(world) == 0 or np.ptp(world[:, 2]) <= 0.0:
        return None
    return world, world[:, 2].min(), np.ptp(world[:, 2])


def _lower_legs(world, height, floor):
    z = (world[:, 2] - floor) / height
    return world[(z > LEGS[0]) & (z < LEGS[1]), :2]


def sideways(context, objects):
    """True when the character made of the meshes among `objects` faces a side (+X or -X) and its feet do not tell
    which: its lower legs stand side by side along Y. It is not turned (left or right is not known); the Check asks."""
    found = _shown(context, objects)
    if found is None:
        return False
    world, floor, height = found
    if feet(world, height, floor) is not None:
        return False
    legs = _lower_legs(world, height, floor)
    if len(legs) < 2:
        return False
    across = np.linalg.svd(legs - legs.mean(axis=0), full_matrices=False)[2][0]
    return abs(across[1]) >= math.cos(AXIS)


def _turn(context, objects, angle, about):
    rotation = (Matrix.Translation((about[0], about[1], 0.0)) @ Matrix.Rotation(angle, 4, 'Z')
                @ Matrix.Translation((-about[0], -about[1], 0.0)))
    moving = set(objects)
    for obj in objects:
        if not any(parent in moving for parent in _ancestors(obj)):
            obj.matrix_world = rotation @ obj.matrix_world
    context.view_layer.update()


def turn(context, objects, angle, body=None):
    """Turn `objects` (and what hangs from them) by `angle` (radians about +Z) round the vertical through where the
    character of `body` (meshes; default `objects`) stands: between its lower legs."""
    found = _shown(context, body or objects)
    if found is None:
        return
    world, floor, height = found
    legs = _lower_legs(world, height, floor)
    about = legs.mean(axis=0) if len(legs) else world[:, :2].mean(axis=0)
    _turn(context, objects, angle, about)


def face_front(context, objects, body=None):
    """Turn `objects` (and what hangs from them) round the vertical through where the character stands, to face -Y,
    when the feet of `body` (meshes; default `objects`) tell it faces another way. Returns the turn (radians about +Z;
    0 when none)."""
    found = _shown(context, body or objects)
    if found is None:
        return 0.0
    world, floor, height = found
    standing = feet(world, height, floor)
    if standing is None:
        return 0.0
    about, direction = standing
    angle = turn_to_front(direction)
    if angle != 0.0:
        _turn(context, objects, angle, about)
    return angle
