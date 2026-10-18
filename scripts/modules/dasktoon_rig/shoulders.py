# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The shoulders lift with the arms (docs/superpowers/specs/2026-10-14-dasktoon-shoulder-follow-design.md). Raised
past START below horizontal, an upper arm lifts its shoulder bone, RATIO of a degree for each degree it rises, up to
LIFT with the arm straight up: turning only the arm folded the top of the shoulder in.

A hidden helper bone on each shoulder (its head and tail, its parent; no deform, so not in the FBX) is rolled so its X
axis is the axis lifting the shoulder, and turned about it by a driver that reads how far the upper arm is raised
sideways from the arm's own quaternion (its rotation channels: a Transform variable would wait for the arm's final pose,
which waits for its parent, the shoulder: a cycle). An X axis of its own, not a fixed axis of an axis-angle rotation:
putting the bones at rest (the test poses, Clear Rotation) set that axis back to Y and twisted the shoulder instead. The
shoulder copies the helper's rotation in the helper's local space turned to the shoulder's orientation, before its own:
keys on the shoulder still count. The constraint's influence is the rig's Shoulder Follows Arm. Clips bake the result,
so Unity needs no constraint. An arm turned to an Euler rotation mode is not followed (the standard skeleton's bones use
quaternions)."""

import math

from mathutils import Vector

from . import skeleton

NAME = "DaskToon Shoulder Follow"
MARK = "dt_shoulder"
SIDES = ("Left", "Right")
START = math.radians(30.0)  # the arm this far below horizontal: its shoulder starts to lift
LIFT = math.radians(35.0)  # the lift with the arm straight up
RATIO = LIFT / (math.pi / 2.0 + START)


def helper_name(side):
    return side + "ShoulderLift"


def _raise_axis(direction, up):
    """The axis turning `direction` towards `up`, or None when they are parallel."""
    axis = direction.cross(up)
    return axis.normalized() if axis.length > 1e-6 else None


def _local(matrix_local, axis):
    """`axis` (armature space) in the bone's own frame, across the bone (no part along its Y), unit length."""
    local = matrix_local.to_3x3().inverted() @ axis
    local.y = 0.0
    return local.normalized()


def _helpers(context, rig, sides, up):
    """A helper bone for each side, made or moved onto its shoulder, its X axis the axis lifting the shoulder."""
    with skeleton.editing(context, rig) as edit:
        for side in sides:
            shoulder = edit[side + "Shoulder"]
            helper = edit.get(helper_name(side)) or edit.new(helper_name(side))
            helper.head, helper.tail = shoulder.head.copy(), shoulder.tail.copy()
            direction = (shoulder.tail - shoulder.head).normalized()
            lift = _raise_axis(direction, up)
            if lift is not None:
                helper.align_roll(lift.cross(direction))  # Z = X x Y, with X the lift axis and Y along the bone
            helper.parent = shoulder.parent
            helper.use_connect = False
            helper.use_deform = False
            helper.hide = True
            helper[MARK] = side


# How far a quaternion (w, x, y, z) turns a bone about the axis (ax, 0, az) across it: its swing (the turn of the
# bone's direction, the twist about its own Y left out) as a rotation vector, along that axis. Written tight: Blender
# keeps 255 characters of a driver's expression.
SWING_X, SWING_Z, KEEP = "(x*w+z*y)", "(z*w-x*y)", "(w*w+y*y)"
SWING = "sqrt(%s*%s+%s*%s)" % (SWING_X, SWING_X, SWING_Z, SWING_Z)
RAISE = "2*atan2(%s,%s)*(%%.4f*%s%%+.4f*%s)/max(%s,0.000001)" % (SWING, KEEP, SWING_X, SWING_Z, SWING)
LONGEST = 255


def _drive(rig, side, arm_axis, start, top):
    """The helper turns about its X axis `top` at most: RATIO of the upper arm's swing about `arm_axis` (the arm's
    frame) past `start`."""
    name = helper_name(side)
    pose_bone = rig.pose.bones[name]
    pose_bone.rotation_mode = 'XYZ'
    for path, count in (('pose.bones["%s"].rotation_euler' % name, 3),
                        ('pose.bones["%s"].rotation_axis_angle' % name, 4)):  # the latter: a lift made before
        for index in range(count):
            rig.driver_remove(path, index)
    pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    driver = rig.driver_add('pose.bones["%s"].rotation_euler' % name, 0).driver
    driver.type = 'SCRIPTED'
    for index, letter in enumerate("wxyz"):
        component = driver.variables.new()
        component.name = letter
        component.type = 'SINGLE_PROP'
        component.targets[0].id = rig
        component.targets[0].data_path = 'pose.bones["%sUpperArm"].rotation_quaternion[%d]' % (side, index)
    # Arithmetic, sqrt, atan2, min and max: a simple expression, which needs no Python (files not trusted to run
    # scripts).
    expression = "max(0,min(%.4f,(%s-%.4f)*%.4f))" % (top, RAISE % (arm_axis.x, arm_axis.z), start, RATIO)
    if len(expression) > LONGEST:
        raise ValueError("driver expression too long: %d characters" % len(expression))
    driver.expression = expression


def _constrain(rig, side):
    pose_bone = rig.pose.bones[side + "Shoulder"]
    found = pose_bone.constraints.get(NAME)
    if found is not None and found.type != 'COPY_ROTATION':
        pose_bone.constraints.remove(found)
        found = None
    if found is None:
        found = pose_bone.constraints.new('COPY_ROTATION')
        found.name = NAME
    found.target, found.subtarget = rig, helper_name(side)
    found.owner_space, found.target_space = 'LOCAL', 'LOCAL_OWNER_ORIENT'
    found.mix_mode = 'BEFORE'
    found.use_x = found.use_y = found.use_z = True


def sync(rig):
    """The lift's strength follows the rig's Shoulder Follows Arm."""
    follow = rig.data.dasktoon_rig.shoulder_follow
    for side in SIDES:
        pose_bone = rig.pose.bones.get(side + "Shoulder")
        found = pose_bone.constraints.get(NAME) if pose_bone is not None else None
        if found is not None:
            found.influence = follow


def apply(context, rig):
    """Make, or make again, the lift of each side that has a shoulder and an upper arm (Build Rig calls it); the axes
    and the start come from the rest pose. Returns the sides done."""
    bones = rig.data.bones
    sides = [side for side in SIDES if bones.get(side + "Shoulder") is not None
             and bones.get(side + "UpperArm") is not None]
    if not sides:
        return []
    up = (rig.matrix_world.inverted().to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    _helpers(context, rig, sides, up)
    done = []
    for side in sides:
        arm, shoulder = bones[side + "UpperArm"], bones[side + "Shoulder"]
        arm_direction = (arm.tail_local - arm.head_local).normalized()
        arm_axis = _raise_axis(arm_direction, up)
        shoulder_axis = _raise_axis((shoulder.tail_local - shoulder.head_local).normalized(), up)
        if arm_axis is None or shoulder_axis is None:
            continue
        rest = math.asin(max(-1.0, min(1.0, arm_direction.dot(up))))
        start = max(0.0, -START - rest)  # how far the arm rises from rest before its shoulder lifts
        top = RATIO * (math.pi / 2.0 - max(rest, -START))
        _drive(rig, side, _local(arm.matrix_local, arm_axis), start, top)
        _constrain(rig, side)
        done.append(side)
    sync(rig)
    return done
