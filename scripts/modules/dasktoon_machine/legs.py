# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""IK legs of a machine (machine rig spec 5): the foot follows a target bone "IK <foot>" placed on it; an IK constraint
on the joint above the foot bends the chain up to the body (the hinges' IK locks keep each joint turning about its own
axis, so no pole is needed); the foot copies the target's rotation and stays flat on the ground. The target's IK_FK
property (0 IK, 1 FK) drives both constraints. Snaps switch over without moving the leg."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

from . import EditSession, MachineError, drive, root_name, shapes

PREFIX = "IK "
SWITCH = "IK_FK"
LEG = "dt_leg"
IK = "DT IK"
FOOT = "DT IK Foot"
LONGEST = 4


def chain(rig, foot):
    """The joints the IK bends, from the one above the foot upwards, stopping below a joint that hangs from the root
    (the body) or holds more than one joint."""
    root = root_name(rig)
    bone = rig.data.bones[foot]
    if bone.parent is None or bone.parent.name == root:
        raise MachineError(rpt_("A foot needs a joint above it"))
    names, b = [bone.parent.name], bone.parent
    while len(names) < LONGEST:
        p = b.parent
        if (p is None or p.name == root or p.parent is None or p.parent.name == root or len(p.children) != 1 or
                p.dasktoon_joint.kind == 'FIXED'):
            break
        names.append(p.name)
        b = p
    return names


def legs(rig):
    """[(foot, target)] of the machine's IK legs."""
    return [(pb[LEG], pb.name) for pb in rig.pose.bones if LEG in pb and pb[LEG] in rig.pose.bones]


def target_of(rig, foot):
    return next((t for f, t in legs(rig) if f == foot), None)


def leg_chain(rig, target):
    """The bones the IK of `target` bends, from the top down, then the foot."""
    foot = rig.pose.bones[target][LEG]
    for pb in rig.pose.bones:
        con = pb.constraints.get(IK)
        if con is not None and con.subtarget == target:
            names, b = [], rig.data.bones[pb.name]
            for _k in range(con.chain_count):
                names.append(b.name)
                b = b.parent
            return list(reversed(names)) + [foot]
    return [foot]


def add(context, rig, foot):
    """An IK leg ending at joint `foot`; returns the target's name."""
    if target_of(rig, foot) is not None:
        raise MachineError(rpt_("This foot already has an IK target"))
    names = chain(rig, foot)
    target = PREFIX + foot
    k = 1
    while target in rig.data.bones:
        target = "%s%s.%03d" % (PREFIX, foot, k)
        k += 1
    with EditSession(context, rig) as edit_bones:
        src = edit_bones[foot]
        eb = edit_bones.new(target)
        eb.head, eb.tail, eb.roll = src.head.copy(), src.tail.copy(), src.roll
        eb.parent = edit_bones[root_name(rig)]
        eb.use_deform = False
    pb = rig.pose.bones[target]
    pb[LEG] = foot
    pb[SWITCH] = 0.0
    pb.id_properties_ui(SWITCH).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
                                      description=rpt_("0: the IK target moves the leg, 1: its joints do"))
    pb.rotation_mode = 'QUATERNION'
    shapes.style_target(rig, target, 'TARGET', max(rig.data.bones[foot].length, 0.02))
    con = rig.pose.bones[names[0]].constraints.new('IK')
    con.name = IK
    con.target, con.subtarget = rig, target
    con.chain_count = len(names)
    con.use_tail, con.use_stretch = True, False
    drive(rig, con, target, SWITCH, "1 - v")
    con = rig.pose.bones[foot].constraints.new('COPY_ROTATION')
    con.name = FOOT
    con.target, con.subtarget = rig, target
    con.target_space = con.owner_space = 'WORLD'
    rig.pose.bones[foot].constraints.move(len(rig.pose.bones[foot].constraints) - 1, 0)
    drive(rig, con, target, SWITCH, "1 - v")
    rig.update_tag()
    return target


def remove(context, rig, target):
    foot = rig.pose.bones[target][LEG] if LEG in rig.pose.bones[target] else None
    for pb in rig.pose.bones:
        for con in [c for c in pb.constraints if c.name in (IK, FOOT) and c.subtarget == target]:
            con.driver_remove("influence")
            pb.constraints.remove(con)
    with EditSession(context, rig) as edit_bones:
        edit_bones.remove(edit_bones[target])
    rig.update_tag()
    return foot


def remove_for(context, rig, name):
    """Take away the legs that use joint `name` (as the foot, in the chain or as the target)."""
    for _foot, target in legs(rig):
        if target == name or name in leg_chain(rig, target):
            remove(context, rig, target)


def snap(context, rig, target, to):
    """Switch the leg of `target` to 'IK' or 'FK' keeping its pose."""
    pb_target = rig.pose.bones[target]
    names = leg_chain(rig, target)
    context.view_layer.update()
    if to == 'FK':
        matrices = [rig.pose.bones[n].matrix.copy() for n in names]
        pb_target[SWITCH] = 1.0
        rig.update_tag()
        context.view_layer.update()
        for n, m in zip(names, matrices):
            rig.pose.bones[n].matrix = m
            context.view_layer.update()
    else:
        pb_target.matrix = rig.pose.bones[names[-1]].matrix.copy()
        pb_target[SWITCH] = 0.0
        rig.update_tag()
        context.view_layer.update()
