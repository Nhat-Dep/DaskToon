# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Machine parts built on joints (machine parts spec, docs/superpowers/specs/2026-11-10-dasktoon-machine-parts-design.md).

A piston: a barrel joint and a rod joint, hanging from two different joints, always look at each other's pin, so the
rod slides in and out of the barrel as those joints move. Each tracks a helper bone that hangs from the other side's
parent at the other pin (no dependency loop).

A linked joint: a follower hinge or slide takes a driver joint's angle or distance times a ratio (a driver with a
simple expression and the ratio as a property of the follower). Meshing gears turn the other way by the ratio of
their radii, gears on a chain or wheels of one vehicle the same way."""

import math

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import EditSession, MachineError, joints, pieces, root_name

PISTON = "dt_piston"
TRACK = "DT Piston"
HELPER = "MCH-"
HELPERS = "Machine Helpers"
LINK = "dt_link"
RATIO = "dt_link_ratio"
PARALLEL = math.radians(10.0)  # axes this near parallel (or perpendicular) are read as such
MESHING = 1.1  # axes nearer than this times the sum of the radii: the gears mesh


# Pistons


def pistons(rig):
    """[(barrel, rod)] of the machine's pistons."""
    return [(pb.name, pb[PISTON]) for pb in rig.pose.bones if PISTON in pb and pb[PISTON] in rig.pose.bones]


def _helpers(rig):
    arm = rig.data
    collection = arm.collections.get(HELPERS)
    if collection is None:
        collection = arm.collections.new(HELPERS)
        collection.is_visible = False
    return collection


def _face(eb, target):
    """Turn edit bone `eb` about its head so its Y axis points at `target`, keeping its X axis across as well as
    possible."""
    head = np.array(eb.head)
    y = np.asarray(target) - head
    length = float(np.linalg.norm(y))
    if length < 1e-6:
        raise MachineError(rpt_("The barrel and the rod have their pins in the same place"))
    y /= length
    x = np.array(eb.x_axis)
    x = x - (x @ y) * y
    if np.linalg.norm(x) < 1e-4:
        x = np.cross(y, (0.0, 0.0, 1.0)) if abs(y[2]) < 0.9 else np.cross(y, (1.0, 0.0, 0.0))
    x /= np.linalg.norm(x)
    eb.tail = Vector(head + y * length * 0.5)
    eb.align_roll(Vector(np.cross(x, y)))


def piston_add(context, rig, barrel, rod):
    """Make the joints `barrel` and `rod` a piston; returns (barrel, rod)."""
    bones = rig.data.bones
    root = root_name(rig)
    for name in (barrel, rod):
        if name not in bones or name == root:
            raise MachineError(rpt_("Select two joints: the rod, then the barrel"))
    if barrel == rod:
        raise MachineError(rpt_("Select two joints: the rod, then the barrel"))
    taken = {n for pair in pistons(rig) for n in pair}
    if barrel in taken or rod in taken:
        raise MachineError(rpt_("One of these joints is in a piston already"))
    a, b = bones[barrel].parent, bones[rod].parent
    if a is None or b is None or a.name == b.name:
        raise MachineError(rpt_("The barrel and the rod must hang from two different joints"))
    a, b = a.name, b.name
    with EditSession(context, rig) as edit_bones:
        x, r = edit_bones[barrel], edit_bones[rod]
        x_head, r_head = np.array(x.head), np.array(r.head)
        _face(x, r_head)
        _face(r, x_head)
        for name, head, parent, towards in ((HELPER + barrel, r_head, b, x_head), (HELPER + rod, x_head, a, r_head)):
            eb = edit_bones.get(name) or edit_bones.new(name)
            eb.head = Vector(head)
            d = head - towards
            eb.tail = Vector(head + d / np.linalg.norm(d) * 0.1 * np.linalg.norm(d))
            eb.parent = edit_bones[parent]
            eb.use_deform = False
    collection = _helpers(rig)
    for name in (HELPER + barrel, HELPER + rod):
        bone = rig.data.bones[name]
        for c in list(bone.collections):
            c.unassign(bone)
        collection.assign(bone)
    for name in (barrel, rod):
        rig.data.bones[name].dasktoon_joint.kind = 'FIXED'
        joints.apply_kind(rig, name)
        pb = rig.pose.bones[name]
        for con in [c for c in pb.constraints if c.name == TRACK]:
            pb.constraints.remove(con)
        con = pb.constraints.new('DAMPED_TRACK')
        con.name = TRACK
        con.target, con.subtarget = rig, HELPER + name
        con.track_axis = 'TRACK_Y'
        pb.constraints.move(len(pb.constraints) - 1, 0)
    rig.pose.bones[barrel][PISTON] = rod
    rig.update_tag()
    return barrel, rod


def piston_remove(context, rig, barrel):
    rod = rig.pose.bones[barrel].get(PISTON)
    names = [n for n in (barrel, rod) if n in rig.pose.bones]
    for name in names:
        pb = rig.pose.bones[name]
        for con in [c for c in pb.constraints if c.name == TRACK]:
            pb.constraints.remove(con)
        rig.data.bones[name].dasktoon_joint.kind = 'HINGE'
        joints.apply_kind(rig, name)
    if PISTON in rig.pose.bones[barrel]:
        del rig.pose.bones[barrel][PISTON]
    helpers = [HELPER + n for n in names if HELPER + n in rig.data.bones]
    if helpers:
        with EditSession(context, rig) as edit_bones:
            for name in helpers:
                edit_bones.remove(edit_bones[name])
    rig.update_tag()


# Linked joints


def links(rig):
    """[(driver, follower, ratio)] of the machine's linked joints."""
    return [(pb[LINK], pb.name, float(pb.get(RATIO, 1.0))) for pb in rig.pose.bones
            if LINK in pb and pb[LINK] in rig.pose.bones]


def _channel(rig, name):
    """(data path, index) of the value a joint moves by: a hinge's angle, a slide's distance."""
    kind = rig.data.bones[name].dasktoon_joint.kind
    if kind == 'HINGE':
        return "rotation_euler", 0
    if kind == 'SLIDE':
        return "location", 0
    raise MachineError(rpt_("Only hinges and slides can be linked"))


def _axis(rig, name):
    m = rig.matrix_world @ rig.data.bones[name].matrix_local
    return np.array(m.translation), np.array(m.to_3x3().col[0].normalized())


def _radius(binding, name, centre, axis):
    points = binding.points(binding.pieces_of(name))
    if not len(points):
        return 0.0
    d = points - centre
    return float(np.linalg.norm(d - np.outer(d @ axis, axis), axis=1).max())


def ratio(rig, driver, follower, binding=None):
    """The follower's turn per turn of the driver: for two hinges about parallel (or crossed) axes, minus the ratio
    of their radii when they mesh, plus it when they do not (a chain, wheels of one vehicle); 1 otherwise."""
    bones = rig.data.bones
    if bones[driver].dasktoon_joint.kind != 'HINGE' or bones[follower].dasktoon_joint.kind != 'HINGE':
        return 1.0
    binding = binding or pieces.Binding(rig)
    cd, ad = _axis(rig, driver)
    cf, af = _axis(rig, follower)
    rd, rf = _radius(binding, driver, cd, ad), _radius(binding, follower, cf, af)
    if rd <= 0.0 or rf <= 0.0:
        return 1.0
    cos = float(ad @ af)
    if abs(cos) >= math.cos(PARALLEL):
        d = cf - cd
        apart = float(np.linalg.norm(d - (d @ ad) * ad))
        sign = -1.0 if apart <= MESHING * (rd + rf) else 1.0
        return sign * math.copysign(1.0, cos) * rd / rf
    if abs(cos) <= math.sin(PARALLEL):
        return -rd / rf
    return 1.0


def _driven_by(rig, name):
    pb = rig.pose.bones.get(name)
    return pb.get(LINK) if pb is not None else None


def link_add(context, rig, driver, follower, value=None):
    """`follower` moves with `driver`, times `value` (the guessed ratio when None); returns the ratio."""
    if driver == follower:
        raise MachineError(rpt_("A joint cannot follow itself"))
    if _driven_by(rig, follower) is not None:
        raise MachineError(rpt_("%s follows another joint already") % follower)
    d = driver
    while d is not None:
        if d == follower:
            raise MachineError(rpt_("These joints would drive each other round in a loop"))
        d = _driven_by(rig, d)
    path_d, index_d = _channel(rig, driver)
    path_f, index_f = _channel(rig, follower)
    value = ratio(rig, driver, follower) if value is None else float(value)
    pb = rig.pose.bones[follower]
    pb[LINK] = driver
    pb[RATIO] = value
    pb.id_properties_ui(RATIO).update(soft_min=-10.0, soft_max=10.0,
                                      description=rpt_("How far this joint moves for each unit of its driver"))
    driver_ = pb.driver_add(path_f, index_f).driver
    driver_.type = 'SCRIPTED'
    for v in list(driver_.variables):
        driver_.variables.remove(v)
    for var_name, path in (("v", 'pose.bones["%s"].%s[%d]' % (driver.replace('"', '\\"'), path_d, index_d)),
                           ("r", 'pose.bones["%s"]["%s"]' % (follower.replace('"', '\\"'), RATIO))):
        var = driver_.variables.new()
        var.name, var.type = var_name, 'SINGLE_PROP'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = rig
        var.targets[0].data_path = path
    driver_.expression = "v * r"
    rig.update_tag()
    return value


def link_remove(rig, follower):
    pb = rig.pose.bones[follower]
    try:
        path, index = _channel(rig, follower)
        pb.driver_remove(path, index)
    except MachineError:
        for path in ("rotation_euler", "location"):
            pb.driver_remove(path, 0)
    for key in (LINK, RATIO):
        if key in pb:
            del pb[key]
    rig.update_tag()


def remove_for(context, rig, name):
    """Take away the pistons and links that use joint `name`."""
    for barrel, rod in pistons(rig):
        if name in (barrel, rod):
            piston_remove(context, rig, barrel)
    for driver, follower, _r in links(rig):
        if name in (driver, follower):
            link_remove(rig, follower)
