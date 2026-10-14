# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where the eyes look (anime rig spec 10.1): the bone LookTarget in front of the face, and on LeftEye and RightEye a
Damped Track to it, then a Limit Rotation (the rig's side and up-down limits). The animator moves LookTarget, or turns
the eye bones themselves; the exported animation bakes the turned eyes, so Unity needs no constraint.

LookTarget and the other face helper bones carry FACE_MARK, not Build Rig's mark: building again keeps them where the
animator put them."""

from contextlib import contextmanager

from mathutils import Vector

from . import skeleton

TARGET = "LookTarget"
FACE_MARK = "dt_face"
TRACK = "DaskToon Look"
LIMIT = "DaskToon Look Limit"
EYES = ("LeftEye", "RightEye")
DISTANCE = 0.5 / skeleton.DEFAULT_HEIGHT  # in front of the eyes, as a share of the skeleton's height
SIZE = 0.05 / skeleton.DEFAULT_HEIGHT


def _height(edit):
    zs = [z for bone in edit for z in (bone.head.z, bone.tail.z)]
    return max(zs) - min(zs)


def _constraint(pose_bone, name, kind):
    found = pose_bone.constraints.get(name)
    if found is not None and found.type != kind:
        pose_bone.constraints.remove(found)
        found = None
    if found is None:
        found = pose_bone.constraints.new(kind)
        found.name = name
    return found


def sync_limits(rig):
    """The eyes' Limit Rotation follows the rig's side and up-down limits."""
    data = rig.data.dasktoon_rig
    for eye in EYES:
        pose_bone = rig.pose.bones.get(eye)
        limit = pose_bone.constraints.get(LIMIT) if pose_bone is not None else None
        if limit is None:
            continue
        limit.min_x, limit.max_x = -data.look_pitch_limit, data.look_pitch_limit
        limit.min_z, limit.max_z = -data.look_yaw_limit, data.look_yaw_limit


@contextmanager
def resting(rig):
    """Meanwhile the eyes' look constraints are muted, so the eyes are at rest (Engine Export writes the model FBX
    this way: Unity measures a flat eye's turn from the pose it imports); afterwards each is as it was."""
    saved = []
    pose = rig.pose  # None for an armature outside the view layer
    for eye in EYES:
        pose_bone = pose.bones.get(eye) if pose is not None else None
        for name in (TRACK, LIMIT):
            con = pose_bone.constraints.get(name) if pose_bone is not None else None
            if con is not None:
                saved.append((con, con.mute))
    try:
        for con, _mute in saved:
            con.mute = True
        yield
    finally:
        for con, mute in saved:
            con.mute = mute


def ensure(context, rig):
    """LookTarget (made once, in front of the eyes) and the eyes' constraints; False when the skeleton has no eyes."""
    bones = rig.data.bones
    if any(bones.get(eye) is None for eye in EYES):
        return False
    if bones.get(TARGET) is None:
        with skeleton.editing(context, rig) as edit:
            middle = (edit["LeftEye"].head + edit["RightEye"].head) / 2.0
            height = _height(edit)
            target = edit.new(TARGET)
            target.head = middle + Vector((0.0, -DISTANCE * height, 0.0))
            target.tail = target.head + Vector((0.0, -SIZE * height, 0.0))
            target.parent = edit["Head"]
            target.use_deform = False
            target[FACE_MARK] = "look"
    for eye in EYES:
        pose_bone = rig.pose.bones[eye]
        track = _constraint(pose_bone, TRACK, 'DAMPED_TRACK')
        track.target, track.subtarget, track.track_axis = rig, TARGET, 'TRACK_Y'
        limit = _constraint(pose_bone, LIMIT, 'LIMIT_ROTATION')
        limit.owner_space = 'LOCAL'
        limit.use_limit_x = limit.use_limit_z = True
        limit.use_limit_y = False
        names = [c.name for c in pose_bone.constraints]
        if names.index(LIMIT) < names.index(TRACK):
            pose_bone.constraints.move(names.index(LIMIT), names.index(TRACK))
    sync_limits(rig)
    return True
