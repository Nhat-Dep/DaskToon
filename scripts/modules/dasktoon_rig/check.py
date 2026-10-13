# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Check of the one-button auto rig (docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md): test poses
someone new to rigging can try with one button, the mesh moved through its weights as the Armature modifier moves it,
and the spots worth a look: joints outside the body, stretched spots, roles that look wrong."""

import math

import numpy as np
from mathutils import Matrix

from . import parts as rig_parts, weights

POSES = ('ARMS_UP', 'SIT', 'TURN_HEAD', 'WAVE', 'REST')
# (bone, world axis, degrees): each bone turned about its head, in order, from the rest pose (spec §3). The character
# faces -Y with its left at +X: about +Y a positive angle lifts the right arm, about X a negative one swings a thigh
# forward, about Z a positive one turns the face to the character's left.
TURNS = {
    'ARMS_UP': (("LeftUpperArm", 'Y', -110.0), ("RightUpperArm", 'Y', 110.0)),
    'SIT': (("LeftUpperLeg", 'X', -90.0), ("RightUpperLeg", 'X', -90.0),
            ("LeftLowerLeg", 'X', 90.0), ("RightLowerLeg", 'X', 90.0)),
    'TURN_HEAD': (("Head", 'Z', 45.0),),
    'WAVE': (("RightUpperArm", 'Y', 100.0), ("RightLowerArm", 'Y', 30.0)),
}


def apply_pose(context, rig, pose):
    """Put `rig` in a test pose: every bone back at rest, then the pose's turns. Nothing is keyed; on the next frame
    change the animation of the rig shows again. REST leaves every bone at rest."""
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    context.view_layer.update()
    to_rig = rig.matrix_world.inverted()
    for name, axis, degrees in TURNS.get(pose, ()):
        bone = rig.pose.bones.get(name)
        if bone is None:
            continue
        world = rig.matrix_world @ bone.matrix
        pivot = world.translation.copy()
        turn = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-pivot)
        bone.matrix = to_rig @ turn @ world
        context.view_layer.update()


def deformed(rig, obj):
    """World positions of the vertices of obj's mesh (no shape keys or modifiers) moved by the rig's current pose through
    their weights, blended as the Armature modifier blends them; a vertex without weight stays."""
    world, _edges = rig_parts.mesh_arrays(obj)
    names = [bone.name for bone in rig.data.bones if bone.use_deform]
    matrix = weights.read(obj, names)
    total = matrix.sum(axis=1)
    moved = np.zeros_like(world)
    to_rig = rig.matrix_world.inverted()
    for j, name in enumerate(names):
        share = matrix[:, j]
        if not share.any():
            continue
        bone = rig.pose.bones[name]
        move = np.array(rig.matrix_world @ bone.matrix @ rig.data.bones[name].matrix_local.inverted() @ to_rig)
        moved += share[:, None] * (world @ move[:3, :3].T + move[:3, 3])
    out = world.copy()
    have = total > 0.0
    out[have] = moved[have] / total[have, None]
    return out
