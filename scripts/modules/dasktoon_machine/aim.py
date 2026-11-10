# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Aiming (machine rig spec 5): a barrel, an eye or a turret turns towards a target bone "Aim <bone>". The muzzle is the
middle of the far end of the joint's pieces; the joint and up to two joints above it (hinges or ball joints, each
holding only the next one) are turned at rest so their Y axis points at it across their axis. A hinge follows the
target with a Locked Track about its axis, a ball joint with a Damped Track; the limits still apply after them. The
target's Aim property (0..1) drives them."""

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import EditSession, MachineError, drive, joints, pieces, root_name, shapes

PREFIX = "Aim "
SWITCH = "Aim"
AIM = "dt_aim"
TRACK = "DT Aim"
LONGEST = 3
FAR = 0.98  # the muzzle: the middle of the points at least this share of the farthest distance away
REACH = 4.0  # the target starts this many muzzle lengths from the joint


def aims(rig):
    """[(joint, target)] of the machine's aims."""
    return [(pb[AIM], pb.name) for pb in rig.pose.bones if AIM in pb and pb[AIM] in rig.pose.bones]


def target_of(rig, name):
    return next((t for b, t in aims(rig) if b == name), None)


def chain(rig, name):
    root = root_name(rig)
    bone = rig.data.bones[name]
    if bone.dasktoon_joint.kind not in ('HINGE', 'BALL'):
        raise MachineError(rpt_("Only a hinge or a ball joint can aim"))
    names, b = [name], bone
    while len(names) < LONGEST:
        p = b.parent
        if (p is None or p.name == root or p.parent is None or p.parent.name == root or len(p.children) != 1 or
                p.dasktoon_joint.kind not in ('HINGE', 'BALL')):
            break
        names.append(p.name)
        b = p
    return names


def muzzle(rig, binding, name):
    """The muzzle of joint `name` in armature space."""
    points = binding.points(binding.pieces_of(name))
    if not len(points):
        raise MachineError(rpt_("The joint holds no piece"))
    m = np.array(rig.matrix_world.inverted())
    points = points @ m[:3, :3].T + m[:3, 3]
    head = np.array(rig.data.bones[name].head_local)
    d = np.linalg.norm(points - head, axis=1)
    return points[d >= FAR * d.max()].mean(axis=0)


def tracked(rig, target):
    return [pb.name for pb in rig.pose.bones if any(c.name == TRACK and c.subtarget == target for c in pb.constraints)]


def add(context, rig, name):
    """Joint `name` and the joints above it aim at a new target; returns the target's name."""
    if target_of(rig, name) is not None:
        raise MachineError(rpt_("This joint already aims"))
    names = chain(rig, name)
    binding = pieces.Binding(rig)
    point = muzzle(rig, binding, name)
    for n in names:
        data = rig.data.bones[n].dasktoon_joint
        data.aim = True
        data.aim_point = point
    joints.reorient(context, binding, names)
    head = np.array(rig.data.bones[name].head_local)
    reach = point - head
    length = float(np.linalg.norm(reach)) or 0.1
    target = PREFIX + name
    k = 1
    while target in rig.data.bones:
        target = "%s%s.%03d" % (PREFIX, name, k)
        k += 1
    with EditSession(context, rig) as edit_bones:
        eb = edit_bones.new(target)
        eb.head = head + REACH * reach
        eb.tail = head + (REACH + 0.5) * reach
        eb.parent = edit_bones[root_name(rig)]
        eb.use_deform = False
    pb = rig.pose.bones[target]
    pb[AIM] = name
    pb[SWITCH] = 1.0
    pb.id_properties_ui(SWITCH).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
                                      description=rpt_("How much the joints turn towards the target"))
    shapes.style_target(rig, target, 'AIM', 0.25 * length)
    for n in names:
        owner = rig.pose.bones[n]
        hinge = rig.data.bones[n].dasktoon_joint.kind == 'HINGE'
        con = owner.constraints.new('LOCKED_TRACK' if hinge else 'DAMPED_TRACK')
        con.name = TRACK
        con.target, con.subtarget = rig, target
        con.track_axis = 'TRACK_Y'
        if hinge:
            con.lock_axis = 'LOCK_X'
        owner.constraints.move(len(owner.constraints) - 1, 0)
        drive(rig, con, target, SWITCH, "v")
    rig.update_tag()
    return target


def remove(context, rig, target):
    names = tracked(rig, target)
    for n in names:
        pb = rig.pose.bones[n]
        for con in [c for c in pb.constraints if c.name == TRACK and c.subtarget == target]:
            con.driver_remove("influence")
            pb.constraints.remove(con)
        rig.data.bones[n].dasktoon_joint.aim = False
    with EditSession(context, rig) as edit_bones:
        edit_bones.remove(edit_bones[target])
    rig.update_tag()
    return names


def remove_for(context, rig, name):
    for _joint, target in aims(rig):
        if target == name or name in tracked(rig, target):
            remove(context, rig, target)
