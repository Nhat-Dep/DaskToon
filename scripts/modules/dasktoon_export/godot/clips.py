# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The clips of a character as glTF animations (Godot spec 3, wave 2). Each clip is played by every part of the
character over its own frame range and baked frame by frame from what Blender shows (the anime timing, which Blender
applies while it plays a clip, and the bone constraints are in the keys; the parts Godot sways itself are held still,
as for Unity). The baked keys become NLA tracks named after the clip on every part, which the glTF exporter turns into
one animation per clip, each clip at a time of its own (the exporter reads a mesh whose shape keys the armature drives
while it plays the armature's track, with every shape key track playing: clips side by side do not mix; the animations
start at 0 s all the same); the bone constraints and the drivers of the baked shape keys (a merged mesh's keys follow the
originals by drivers) are muted meanwhile, so the exporter reads the baked keys. Everything is given back afterwards. The import script makes the looping clips loop and the clips with anime timing
step from frame to frame."""

import contextlib

import bpy

BAKE_PREFIX = "DT_GodotBake"
GAP = 10  # frames between two clips' times
TRANSFORMS = ("location", "rotation_quaternion", "rotation_euler", "rotation_axis_angle", "scale")


def _rotation(mode, matrix_rotation, previous):
    """The rotation channels of `mode` for a rotation quaternion; an Euler stays close to the previous frame's."""
    if mode == 'QUATERNION':
        if previous is not None and matrix_rotation.dot(previous) < 0.0:
            matrix_rotation = -matrix_rotation  # the shorter way, so linear keys do not spin round
        return "rotation_quaternion", matrix_rotation
    if mode == 'AXIS_ANGLE':
        axis, angle = matrix_rotation.to_axis_angle()
        return "rotation_axis_angle", (angle, axis.x, axis.y, axis.z)
    return "rotation_euler", matrix_rotation.to_euler(mode, previous) if previous is not None else \
        matrix_rotation.to_euler(mode)


def _keyed_shapes(clips_list, keys):
    """Names of the shape keys that any clip animates on any of `keys`."""
    from dasktoon_animation import clips
    names = set()
    for clip in clips_list:
        for key in keys:
            for path, _index in clips._keyed(clip, key):
                if path.startswith('key_blocks["') and path.endswith('"].value'):
                    names.add(path[len('key_blocks["'):-len('"].value')])
    return names


def _keyed_objects(clips_list, objects):
    """The objects whose own transform any clip animates."""
    from dasktoon_animation import clips
    return [obj for obj in objects
            if any(path in TRANSFORMS for clip in clips_list for path, _index in clips._keyed(clip, obj))]


def _sample(context, armature, keys, objects, previous):
    """{(id, data path): values} of this frame, from the evaluated scene."""
    depsgraph = context.evaluated_depsgraph_get()
    out = {}
    rig_eval = armature.evaluated_get(depsgraph)
    for bone in armature.pose.bones:
        local = armature.convert_space(pose_bone=bone, matrix=rig_eval.pose.bones[bone.name].matrix,
                                       from_space='POSE', to_space='LOCAL')
        loc, rot, scale = local.decompose()
        prefix = 'pose.bones["%s"].' % bpy.utils.escape_identifier(bone.name)
        name, value = _rotation(bone.rotation_mode, rot, previous.get((armature, prefix + "rotation")))
        previous[(armature, prefix + "rotation")] = value if name != "rotation_axis_angle" else None
        out[(armature, prefix + "location")] = tuple(loc)
        out[(armature, prefix + name)] = tuple(value)
        out[(armature, prefix + "scale")] = tuple(scale)
    for key, names in keys.items():
        blocks = key.evaluated_get(depsgraph).key_blocks
        for name in names:
            out[(key, 'key_blocks["%s"].value' % bpy.utils.escape_identifier(name))] = (blocks[name].value,)
    for obj in objects:
        loc, rot, scale = obj.evaluated_get(depsgraph).matrix_basis.decompose()
        name, value = _rotation(obj.rotation_mode, rot, previous.get((obj, "rotation")))
        previous[(obj, "rotation")] = value if name != "rotation_axis_angle" else None
        out[(obj, "location")] = tuple(loc)
        out[(obj, name)] = tuple(value)
        out[(obj, "scale")] = tuple(scale)
    return out


def _bake_action(name, idb, start, samples):
    """An action of `idb` with a key on every frame from `start` for each of its sampled channels."""
    action = bpy.data.actions.new(name)
    channels = [(owner, path) for owner, path in samples[0] if owner == idb]
    if not channels:
        return action
    slot = action.slots.new(idb.id_type, idb.name)
    bag = action.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for owner, path in channels:
        for index in range(len(samples[0][(owner, path)])):
            curve = bag.fcurves.new(path, index=index)
            curve.keyframe_points.add(len(samples))
            co = []
            for k, sample in enumerate(samples):
                co += (float(start + k), float(sample[(owner, path)][index]))
            curve.keyframe_points.foreach_set("co", co)
            curve.keyframe_points.foreach_set("interpolation", [1] * len(samples))  # LINEAR
            curve.update()
    return action


@contextlib.contextmanager
def _muted(armature, keys):
    """The armature's bone constraints and the drivers of `keys` muted meanwhile."""
    saved = [(c, c.mute) for bone in armature.pose.bones for c in bone.constraints]
    saved += [(d, d.mute) for key in keys if key.animation_data is not None for d in key.animation_data.drivers]
    for item, _mute in saved:
        item.mute = True
    try:
        yield
    finally:
        for item, mute in saved:
            item.mute = mute


@contextlib.contextmanager
def baked(context, armature, objects):
    """While inside, `armature` and the meshes and objects of `objects` that the clips move carry an NLA track per clip
    with the clip baked, and the character's parts no action; yields [(clip name, loop, stepped)]. `objects` are the
    objects exported (the character's meshes merged, when they are). Without clips nothing changes and it yields []."""
    from dasktoon_animation import clips, timing
    from dasktoon_rig import sway
    from .. import _set_frame_range, rig_json
    all_clips = [clip for clip in clips.clips_of(armature) if clips.has_keys(clip)] if armature is not None else []
    if not all_clips:
        yield []
        return
    scene = context.scene
    everything = list(context.view_layer.objects)
    parts = clips.parts(armature, everything)
    saved = clips.current(armature), scene.frame_start, scene.frame_end, scene.frame_current
    shapes = _keyed_shapes(all_clips, [p for p in parts if isinstance(p, bpy.types.Key)])
    keys = {}
    for obj in objects:
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        names = sorted(name for name in shapes if key is not None and name in key.key_blocks)
        if names:
            keys[key] = names
    moved = [obj for obj in _keyed_objects(all_clips, [p for p in parts if isinstance(p, bpy.types.Object)])
             if obj in objects]
    quiet = sway.suppressed(armature, rig_json.runtime_parts(armature)) if rig_json.find_rig([armature]) else \
        contextlib.nullcontext()
    made, tracks, out = [], [], []
    try:
        baked_clips = []
        with quiet:
            for clip in all_clips:
                first, last = clips.frame_range(clip)
                clips.use(armature, everything, clip)
                _set_frame_range(scene, first, last)
                frames = list(range(first, last + 1))
                previous, samples = {}, []
                for frame in frames:
                    scene.frame_set(frame)
                    samples.append(_sample(context, armature, keys, moved, previous))
                baked_clips.append((clip, frames, samples))
        # The tracks go on once every clip is baked: a track plays under the clip baked after it.
        start = 1
        for clip, frames, samples in baked_clips:
            for idb in [armature] + list(keys) + [obj for obj in moved if obj != armature]:
                action = _bake_action("%s_%s_%s" % (BAKE_PREFIX, clip.name, idb.name), idb, start, samples)
                made.append(action)
                if not action.slots:
                    continue
                anim = idb.animation_data or idb.animation_data_create()
                track = anim.nla_tracks.new()
                track.name = clip.name
                strip = track.strips.new(clip.name, start, action)
                strip.action_slot = action.slots[0]
                strip.extrapolation = 'NOTHING'  # nothing outside its own time
                tracks.append((anim, track))
            out.append((clip.name, clip.use_cyclic, timing.has_steps(clip)))
            start += len(frames) + GAP
        clips.use(armature, everything, None)
        for idb in parts:
            if idb.animation_data is not None:
                idb.animation_data.action = None
        with _muted(armature, keys):
            yield out
    finally:
        for anim, track in tracks:
            anim.nla_tracks.remove(track)
        for action in made:
            bpy.data.actions.remove(action)
        clips.use(armature, everything, saved[0])
        _set_frame_range(scene, saved[1], saved[2])
        scene.frame_set(saved[3])
