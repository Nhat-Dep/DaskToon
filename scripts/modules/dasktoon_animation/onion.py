# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Onion skin (docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md, section 6): faint copies of the
character's meshes at the keyed frames before and after the current one. They are copied by jumping to those frames
and back; bl_ui.dasktoon_animation decides when and draws them."""

import numpy as np
from bpy_extras import anim_utils

from . import timing


def key_frames(action):
    """The frames that have a key in `action` (any slot, any curve), sorted."""
    frames = set()
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    frames.update(int(round(point.co.x)) for point in curve.keyframe_points)
    return sorted(frames)


def ghost_frames(action, frame, before, after):
    """([frames before], [frames after]) `frame`: up to `before` and `after` keyed frames of `action`, nearest first.
    With anime timing the drawing shown at `frame` is its drawn frame's, so that one is no ghost."""
    if action is None:
        return [], []
    frames = key_frames(action)
    shown = timing.drawn_frame(action, frame)
    earlier = [f for f in reversed(frames) if f < shown][:before]
    later = [f for f in frames if f > frame][:after]
    return earlier, later


def triangles(obj, depsgraph):
    """The triangles of the evaluated mesh of `obj` in world space: an (n * 3, 3) float32 array, three corners a
    triangle."""
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        corners = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", corners)
        matrix = np.array(evaluated.matrix_world, dtype=np.float32)
        world = co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
        return np.ascontiguousarray(world[corners], dtype=np.float32)
    finally:
        evaluated.to_mesh_clear()


def capture(context, objects, frames):
    """{frame: [(object name, triangles)]}: the meshes of `objects` as evaluated at each of `frames`. The scene goes
    back to its frame afterwards."""
    scene = context.scene
    current, subframe = scene.frame_current, scene.frame_subframe
    meshes = [obj for obj in objects if obj.type == 'MESH']
    out = {}
    try:
        for frame in frames:
            scene.frame_set(frame)
            depsgraph = context.evaluated_depsgraph_get()
            out[frame] = [(obj.name, triangles(obj, depsgraph)) for obj in meshes]
    finally:
        scene.frame_set(current, subframe=subframe)
    return out


def _value(idb, curve):
    """The value the animated property of `curve` has now, or None when it is not a number."""
    try:
        value = idb.path_resolve(curve.data_path)
        if not isinstance(value, (bool, int, float)):
            value = value[curve.array_index]
        return float(value)
    except (ValueError, TypeError, IndexError):
        return None


def animated_ids(objects):
    """`objects`, their data and the Keys of their meshes: what a jump to another frame evaluates again."""
    out = []
    for obj in objects:
        out.append(obj)
        data = obj.data
        if data is not None and hasattr(data, "animation_data"):
            out.append(data)
        key = data.shape_keys if obj.type == 'MESH' else None
        if key is not None:
            out.append(key)
    return out


def unkeyed_changes(ids, frame):
    """True when a property that the action of one of `ids` animates no longer has its keyed value at `frame`: the
    user changed the pose without keying it, and jumping to another frame would lose that. Driven properties do not
    count: their drivers set them."""
    for idb in ids:
        anim = idb.animation_data
        if anim is None or anim.action is None:
            continue
        bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
        if bag is None:
            continue
        time = timing.drawn_frame(anim.action, frame)
        driven = {(driver.data_path, driver.array_index) for driver in anim.drivers}
        for curve in bag.fcurves:
            if curve.mute or (curve.data_path, curve.array_index) in driven:
                continue
            value = _value(idb, curve)
            if value is not None and abs(value - curve.evaluate(time)) > 1e-4:
                return True
    return False
