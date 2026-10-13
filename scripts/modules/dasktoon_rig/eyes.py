# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Flat eyes (anime rig spec 10.2): an iris drawn on the face slides on its UVs as its eye bone turns. A UV Warp
modifier, limited to the part's vertices, gets its offset from two drivers on the eye bone's turn:

    u = -range * cos(rx) * sin(rz),  v = -range * sin(rx)

rx and rz are the eye's local X and Z turn (up-down and side), constraints included; with the eye looking along f
(x: the character's left, z: up) that is (-range * f.x, -range * f.z), the offset DaskToon's Unity script uses too.
Looking to the character's left, the UVs go down in u, so the drawing moves to that side with the gaze.

The drivers are simple expressions, which Blender works out without Python (no Auto Run needed). A UV Warp between two
bones was tried first: it moves U with +X but V against +Z, so U and V could not both follow the gaze."""

import numpy as np
from mathutils import Vector

from . import parts as rig_parts

MODIFIER_PREFIX = "DaskToon Flat Eye"
GROUP_PREFIX = "DT_FlatEye_"


def side_of(rig, part, vertices):
    """'LEFT' or 'RIGHT': the part's setting, or (Automatic) the side of the rig its vertices lie on."""
    if part.eye_side != 'AUTO':
        return part.eye_side
    world, _edges = rig_parts.mesh_arrays(part.object)
    middle = rig.matrix_world.inverted() @ Vector(world[vertices].mean(axis=0))
    return 'LEFT' if middle.x > 0.0 else 'RIGHT'


def _group(part, vertices):
    """The vertex group the modifier works on: the part's own, or one made from its vertices."""
    obj = part.object
    if part.scope == 'VERTEX_GROUP':
        return part.vertex_group
    name = GROUP_PREFIX + part.name
    group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
    group.remove(list(range(len(obj.data.vertices))))
    group.add([int(v) for v in vertices], 1.0, 'REPLACE')
    return name


def _remove(obj, name):
    for index in (0, 1):
        obj.driver_remove('modifiers["%s"].offset' % name, index)
    modifier = obj.modifiers.get(name)
    if modifier is not None:
        obj.modifiers.remove(modifier)


def _drive(obj, name, index, expression, rig, eye):
    curve = obj.driver_add('modifiers["%s"].offset' % name, index)
    driver = curve.driver
    driver.type = 'SCRIPTED'
    while driver.variables:
        driver.variables.remove(driver.variables[0])
    for var_name, channel in (("rx", 'ROT_X'), ("rz", 'ROT_Z')):
        var = driver.variables.new()
        var.name, var.type = var_name, 'TRANSFORMS'
        target = var.targets[0]
        target.id, target.bone_target = rig, eye
        target.transform_type, target.transform_space, target.rotation_mode = channel, 'LOCAL_SPACE', 'XYZ'
    driver.expression = expression


def apply(rig, parts):
    """A UV Warp modifier with its drivers for every Flat Eye part; the flat eye modifiers no part needs any more go."""
    wanted = {}
    for part in parts:
        if part.role != 'FLAT_EYE' or part.object is None:
            continue
        vertices = np.asarray(rig_parts.part_vertices(part))
        eye = "LeftEye" if side_of(rig, part, vertices) == 'LEFT' else "RightEye"
        obj = part.object
        name = "%s %s" % (MODIFIER_PREFIX, part.name)
        wanted.setdefault(obj, set()).add(name)
        modifier = obj.modifiers.get(name) or obj.modifiers.new(name, 'UV_WARP')
        modifier.vertex_group = _group(part, vertices)
        modifier.object_from = modifier.object_to = None
        r = "%.6g" % part.eye_range
        _drive(obj, name, 0, "-%s * cos(rx) * sin(rz)" % r, rig, eye)
        _drive(obj, name, 1, "-%s * sin(rx)" % r, rig, eye)
    for part in parts:
        obj = part.object
        if obj is None:
            continue
        for modifier in list(obj.modifiers):
            if modifier.name.startswith(MODIFIER_PREFIX) and modifier.name not in wanted.get(obj, ()):
                _remove(obj, modifier.name)
