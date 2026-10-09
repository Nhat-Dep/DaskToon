# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sway of the generated chains (anime rig spec 9.4). Every chain bone has DaskToon's C++ Spring constraint, which the
depsgraph evaluates with the rest of the pose, so scrubbing, rendering and exporting are right without baking. This
module keeps the constraints in step with the rig's parts and colliders, turns Live Sway on and off (mute), bakes the
sway into keys and mutes the runtime chains while Engine Export writes the FBX. spring.py stays the reference of the
maths the constraint and Unity's script share."""

from contextlib import contextmanager

import bpy
import numpy as np
from mathutils import Matrix

from . import build, spring

CONSTRAINT_NAME = "DaskToon Spring"
ROTATION_PATHS = ("rotation_quaternion", "rotation_euler", "rotation_axis_angle")


def chains(rig):
    """[(part name, [bone names from root to tip])] of the chains Build Rig generated in `rig`."""
    out = []
    for bone in rig.data.bones:
        part = bone.get(build.MARK)
        if part is None or (bone.parent is not None and bone.parent.get(build.MARK) == part):
            continue
        names, current = [bone.name], bone
        while True:
            children = [c for c in current.children if c.get(build.MARK) == part]
            if not children:
                break
            current = children[0]
            names.append(current.name)
        out.append((part, names))
    return out


def _rotation(matrix):
    return np.array(matrix.to_3x3().normalized())


def chain_pose(rig, names):
    """The chain as posed now (spring.Pose), from the current pose of `rig`, Spring constraints included."""
    world = rig.matrix_world
    bones = [rig.pose.bones[name] for name in names]
    parent = bones[0].parent
    parent_rotation = _rotation(world @ parent.matrix) if parent is not None else _rotation(world)
    rotations = [_rotation(world @ pb.matrix) for pb in bones]
    local, previous = [], parent_rotation
    for rotation in rotations:
        local.append(previous.T @ rotation)
        previous = rotation
    lengths = [(world @ pb.tail - world @ pb.head).length for pb in bones]
    return spring.Pose(np.array(world @ bones[0].head), parent_rotation, local, lengths)


def spring_constraint(pb):
    """The Spring constraint of a pose bone, or None."""
    return next((c for c in pb.constraints if c.type == 'SPRING'), None)


def _constraints(rig, part_names=None):
    out = []
    for part, names in chains(rig):
        if part_names is not None and part not in part_names:
            continue
        for name in names:
            con = spring_constraint(rig.pose.bones[name])
            if con is not None:
                out.append(con)
    return out


def rig_scale(rig):
    """The largest scale of the rig object: radii are in armature units and grow with it."""
    return max(rig.matrix_world.to_scale())


def world_colliders(rig):
    """[(head, tail, world radius)] capsules of the rig's colliders in its current pose."""
    world, scale = rig.matrix_world, rig_scale(rig)
    out = []
    for collider in rig.data.dasktoon_rig.colliders:
        pb = rig.pose.bones.get(collider.bone)
        if pb is not None:
            out.append((np.array(world @ pb.head), np.array(world @ pb.tail), collider.radius * scale))
    return out


def _sync_colliders(rig, con, colliders):
    """The constraint's colliders as `colliders` [(bone, radius)]; the list is only made again when the bones differ
    (every new collider rebuilds the depsgraph relations)."""
    if [(c.target, c.subtarget) for c in con.colliders] != [(rig, bone) for bone, _radius in colliders]:
        con.colliders.clear()
        for bone, _radius in colliders:
            item = con.colliders.new()
            item.target = rig
            item.subtarget = bone
    for item, (_bone, radius) in zip(con.colliders, colliders):
        if abs(item.radius - radius) > 1e-7:
            item.radius = radius


def sync(rig):
    """A Spring constraint on every chain bone with its part's settings, the rig's colliders and Live Sway (spec 9.4)."""
    data = rig.data.dasktoon_rig
    colliders = [(c.bone, c.radius) for c in data.colliders if rig.data.bones.get(c.bone) is not None]
    for part_name, names in chains(rig):
        part = data.parts.get(part_name)
        params = part if part is not None else spring.Params()
        for name in names:
            pb = rig.pose.bones[name]
            con = spring_constraint(pb)
            if con is None:
                con = pb.constraints.new('SPRING')
                con.name = CONSTRAINT_NAME
            for prop in ("stiffness", "gravity", "drag", "radius"):
                value = getattr(params, prop)
                if abs(getattr(con, prop) - value) > 1e-7:
                    setattr(con, prop, value)
            _sync_colliders(rig, con, colliders)
            if con.mute != (not data.live_sway):
                con.mute = not data.live_sway


def set_live(rig, on):
    """Unmute (on) or mute the Spring constraints of the rig's chains."""
    for con in _constraints(rig):
        con.mute = not on


def clear_cache(rig):
    """Forget the rig's cached sway, so it starts again."""
    found = _constraints(rig)
    if found:
        found[0].clear_cache()


def direction(rig, name):
    """World direction (unit) of a pose bone, Spring constraints included."""
    pb = rig.pose.bones[name]
    world = rig.matrix_world
    v = np.array(world @ pb.tail) - np.array(world @ pb.head)
    return v / np.linalg.norm(v)


@contextmanager
def suppressed(rig, part_names):
    """Meanwhile the Spring constraints of `part_names` are muted (Engine Export writes the FBX, spec 9.5); afterwards
    each one is as it was."""
    cons = _constraints(rig, set(part_names))
    saved = [(con, con.mute) for con in cons]
    try:
        for con in cons:
            con.mute = True
        yield
    finally:
        for con, mute in saved:
            con.mute = mute


def remove_rotation_keys(rig, names):
    """Delete the rotation curves of `names` from the action of `rig` (its slot's channels)."""
    from bpy_extras import anim_utils
    anim = rig.animation_data
    if anim is None or anim.action is None:
        return
    channelbag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    if channelbag is None:
        return
    paths = {'pose.bones["%s"].%s' % (bpy.utils.escape_identifier(name), prop) for name in names
             for prop in ROTATION_PATHS}
    for curve in list(channelbag.fcurves):
        if curve.data_path in paths:
            channelbag.fcurves.remove(curve)


def _rotation_path(pb):
    if pb.rotation_mode == 'QUATERNION':
        return "rotation_quaternion"
    if pb.rotation_mode == 'AXIS_ANGLE':
        return "rotation_axis_angle"
    return "rotation_euler"


def _set_rotation(pb, matrix):
    q = matrix.to_quaternion()
    if pb.rotation_mode == 'QUATERNION':
        pb.rotation_quaternion = q
    elif pb.rotation_mode == 'AXIS_ANGLE':
        axis, angle = q.to_axis_angle()
        pb.rotation_axis_angle = (angle, axis.x, axis.y, axis.z)
    else:
        pb.rotation_euler = q.to_euler(pb.rotation_mode)


def _basis_rotation(pb):
    """The local rotation (3x3) that gives a pose bone its current pose rotation, with its parent as it is now."""
    pose = _rotation(pb.matrix)
    rest = np.array(pb.bone.matrix_local.to_3x3())
    if pb.parent is None:
        return rest.T @ pose
    parent_rest = np.array(pb.parent.bone.matrix_local.to_3x3())
    return rest.T @ parent_rest @ _rotation(pb.parent.matrix).T @ pose


def bake(context, rig, frame_start, frame_end):
    """Key the sway of every chain bone on every frame of the range (spec 9.4): their rotation curves are replaced and
    Live Sway turns off, so the keys play as the constraints did. Returns (frames, bones)."""
    scene = context.scene
    names = [name for _part, chain in chains(rig) for name in chain]
    data = rig.data.dasktoon_rig
    saved = scene.frame_current
    remove_rotation_keys(rig, names)
    identity = Matrix.Identity(3)
    for name in names:
        _set_rotation(rig.pose.bones[name], identity)
    data.live_sway = True
    set_live(rig, True)
    clear_cache(rig)
    values = {}
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        values[frame] = {name: Matrix(_basis_rotation(rig.pose.bones[name]).tolist()) for name in names}
    data.live_sway = False
    set_live(rig, False)
    for frame, rotations in values.items():
        for name, matrix in rotations.items():
            pb = rig.pose.bones[name]
            _set_rotation(pb, matrix)
            pb.keyframe_insert(_rotation_path(pb), frame=frame, group=name)
    scene.frame_set(saved)
    return frame_end - frame_start + 1, len(names)
