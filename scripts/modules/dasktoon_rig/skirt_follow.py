# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A skirt spreads with the thighs, played or not (the user's choice, 2026-10-19). The Spring constraints of a skirt's
strips push them out of the legs only as frames are played: on a frame not played through (the Check's Sit pose, the
first frame) the thighs stood through RG2's skirt, a real model.

The first bone of each strip of a Skirt part copies the turn of the thigh on its side, as much as FRONT for a strip at
the front, SIDE at the sides and BACK at the back, before its Spring constraint, so the skirt drapes over the thighs and
sways about that. The turn is copied in the thigh's local space turned to the strip's orientation, before the strip's
own keys, as the shoulders copy their lift (shoulders.py). Clips bake the result into the exported animation; in Unity
the strips' springs sway about it."""

from mathutils import Vector

NAME = "DaskToon Skirt Follow"
FRONT, SIDE, BACK = 0.8, 0.45, 0.1  # how much of its thigh's turn a strip at the front, a side and the back copies


def influence(front):
    """How much of its thigh's turn a strip copies, `front` being how far it lies to the front (1) or back (-1)."""
    return SIDE + (FRONT - SIDE) * front if front >= 0.0 else SIDE + (SIDE - BACK) * front


def apply(rig, parts):
    """Give the first bone of each strip of the Skirt parts among `parts` its follow, first in its constraints (Build
    Rig calls it on the bones it has just made). Returns the bones."""
    from . import sway
    bones = rig.data.bones
    legs = [bones.get(side + "UpperLeg") for side in ("Left", "Right")]
    if None in legs:
        return []
    centre = (legs[0].head_local + legs[1].head_local) / 2.0
    skirts = {part.name for part in parts if part.role == 'SKIRT'}
    done = []
    for part_name, names in sway.chains(rig):
        if part_name not in skirts:
            continue
        offset = bones[names[0]].head_local - centre
        across = Vector((offset.x, offset.y, 0.0))
        if across.length < 1e-6:
            continue
        across.normalize()
        pose_bone = rig.pose.bones[names[0]]
        found = pose_bone.constraints.get(NAME)
        if found is None:
            found = pose_bone.constraints.new('COPY_ROTATION')
            found.name = NAME
        index = list(pose_bone.constraints).index(found)
        if index:
            pose_bone.constraints.move(index, 0)
        found.target = rig
        found.subtarget = ("Left" if across.x >= 0.0 else "Right") + "UpperLeg"  # the character's left is +X
        found.owner_space, found.target_space = 'LOCAL', 'LOCAL_OWNER_ORIENT'
        found.mix_mode = 'BEFORE'
        found.use_x = found.use_y = found.use_z = True
        found.influence = influence(-across.y)  # the character faces -Y
        done.append(names[0])
    return done
