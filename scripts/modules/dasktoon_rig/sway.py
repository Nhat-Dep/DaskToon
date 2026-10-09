# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sway of the generated chains (anime rig spec 9.4). Before the animation of a frame is evaluated, the chain
bones go back to their rest rotation (frame_change_pre), so a key the user set is the chain's pose and an unkeyed bone
is at rest; after it (frame_change_post) the spring solver steps from the previous frame and the bones get the swayed
rotations. States are cached per frame, so going back to a frame shows it again; the first frame of the scene starts
over. Bake Sway keys the result. No drivers: these are DaskToon's own handlers."""

from contextlib import contextmanager

import bpy
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Matrix

from . import build, spring

MAX_CATCH_UP = 300
ROTATION_PATHS = ("rotation_quaternion", "rotation_euler", "rotation_axis_angle")
_cache = {}  # session_uid of the rig → {frame: [spring.State per chain]}
_suppressed = {}  # session_uid of the rig → part names whose chains do not sway (Engine Export, spec 9.5)


def clear_cache(rig=None):
    if rig is None:
        _cache.clear()
    else:
        _cache.pop(rig.session_uid, None)


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
    """The chain as animated, without sway (spring.Pose), from the current pose of `rig`."""
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


def _set_rotation(pb, matrix):
    q = matrix.to_quaternion()
    if pb.rotation_mode == 'QUATERNION':
        pb.rotation_quaternion = q
    elif pb.rotation_mode == 'AXIS_ANGLE':
        axis, angle = q.to_axis_angle()
        pb.rotation_axis_angle = (angle, axis.x, axis.y, axis.z)
    else:
        pb.rotation_euler = q.to_euler(pb.rotation_mode)


def apply(rig, names, world_rotations):
    """Give the chain bones the rotations that make their world rotations `world_rotations` (3x3 each)."""
    to_rig = _rotation(rig.matrix_world).T
    bones = [rig.pose.bones[name] for name in names]
    parent = bones[0].parent
    parent_pose = _rotation(parent.matrix) if parent is not None else np.eye(3)
    for pb, world_rotation in zip(bones, world_rotations):
        pose = to_rig @ world_rotation
        rest = np.array(pb.bone.matrix_local.to_3x3())
        parent_rest = np.array(pb.parent.bone.matrix_local.to_3x3()) if pb.parent is not None else np.eye(3)
        basis = rest.T @ parent_rest @ parent_pose.T @ pose
        _set_rotation(pb, Matrix(basis.tolist()))
        parent_pose = pose


def world_colliders(rig):
    """[(head, tail, radius)] world capsules of the rig's colliders in its current pose."""
    world = rig.matrix_world
    out = []
    for collider in rig.data.dasktoon_rig.colliders:
        pb = rig.pose.bones.get(collider.bone)
        if pb is not None:
            out.append((np.array(world @ pb.head), np.array(world @ pb.tail), collider.radius))
    return out


def _params(rig, part_name):
    part = rig.data.dasktoon_rig.parts.get(part_name)
    if part is None:
        return spring.Params()
    return spring.Params(part.stiffness, part.gravity, part.drag, part.radius)


def _live(rig):
    data = getattr(rig.data, "dasktoon_rig", None)
    return data is not None and data.live_sway


def sway(rig, scene):
    """Sway the chains of `rig` for the scene's current frame."""
    skipped = _suppressed.get(rig.session_uid, set())
    found = [(part, names) for part, names in chains(rig) if part not in skipped]
    if not found:
        return
    frame = scene.frame_current
    dt = scene.render.fps_base / scene.render.fps
    store = _cache.setdefault(rig.session_uid, {})
    poses = [chain_pose(rig, names) for _part, names in found]
    shape = [len(names) for _part, names in found]
    if store and [len(s.current) for s in next(iter(store.values()))] != shape:
        store.clear()
    colliders = world_colliders(rig)
    if frame in store and frame != scene.frame_start:
        states = [s.copy() for s in store[frame]]
        results = [spring.rotations(state, pose) for state, pose in zip(states, poses)]
    else:
        earlier = [f for f in store if f < frame]
        if frame == scene.frame_start or not earlier or frame - max(earlier) > MAX_CATCH_UP:
            store.clear()
            states = [spring.reset(pose) for pose in poses]
            results = [spring.rotations(state, pose) for state, pose in zip(states, poses)]
        else:
            start = max(earlier)
            states = [s.copy() for s in store[start]]
            for _ in range(frame - start):
                results = [spring.step(state, pose, _params(rig, part), colliders, dt)
                           for state, pose, (part, _names) in zip(states, poses, found)]
        store[frame] = [s.copy() for s in states]
    for (_part, names), rotations in zip(found, results):
        apply(rig, names, rotations)


def _live_rigs(scene):
    return [obj for obj in scene.objects if obj.type == 'ARMATURE' and _live(obj)]


@persistent
def frame_pre(scene, _depsgraph=None):
    identity = Matrix.Identity(3)
    for rig in _live_rigs(scene):
        for _part, names in chains(rig):
            for name in names:
                _set_rotation(rig.pose.bones[name], identity)


@persistent
def frame_post(scene, _depsgraph=None):
    for rig in _live_rigs(scene):
        sway(rig, scene)


@persistent
def depsgraph_post(_scene, depsgraph):
    """Keys edited (an Action updated): the cached sway no longer matches the animation."""
    if any(isinstance(update.id, bpy.types.Action) for update in depsgraph.updates):
        clear_cache()


@contextmanager
def suppressed(rig, part_names):
    """Meanwhile the chains of `part_names` rest and do not sway on a frame change; afterwards their rotations come
    back and the rig's cache is cleared (Engine Export writes the FBX in between, spec 9.5)."""
    names = [name for part, chain in chains(rig) if part in part_names for name in chain]
    saved = {name: tuple(getattr(rig.pose.bones[name], _rotation_path(rig.pose.bones[name]))) for name in names}
    _suppressed[rig.session_uid] = set(part_names)
    identity = Matrix.Identity(3)
    try:
        for name in names:
            _set_rotation(rig.pose.bones[name], identity)
        yield
    finally:
        _suppressed.pop(rig.session_uid, None)
        for name, value in saved.items():
            pb = rig.pose.bones[name]
            setattr(pb, _rotation_path(pb), value)
        clear_cache(rig)


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


def bake(context, rig, frame_start, frame_end):
    """Key the sway of every chain bone on every frame of the range (spec 9.4): their rotation curves are replaced and
    Live Sway turns off, so the keys play as they are. Returns (frames, bones)."""
    scene = context.scene
    names = [name for _part, chain in chains(rig) for name in chain]
    data = rig.data.dasktoon_rig
    saved = scene.frame_current
    remove_rotation_keys(rig, names)
    data.live_sway = True
    clear_cache(rig)
    values = {}
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        values[frame] = {name: tuple(getattr(rig.pose.bones[name], _rotation_path(rig.pose.bones[name])))
                         for name in names}
    data.live_sway = False
    for frame, rotations in values.items():
        for name, value in rotations.items():
            pb = rig.pose.bones[name]
            path = _rotation_path(pb)
            setattr(pb, path, value)
            pb.keyframe_insert(path, frame=frame, group=name)
    scene.frame_set(saved)
    return frame_end - frame_start + 1, len(names)
