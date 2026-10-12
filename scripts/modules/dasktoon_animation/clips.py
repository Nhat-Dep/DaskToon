# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Clips of a character (docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md, sections 3 to 5): a clip is one
Action with a slot for every part it animates (the armature, the objects of the character, the Keys of its meshes), so
body and face move together. Action.dasktoon_character points to the armature the clip belongs to; Action.use_cyclic is
its Loop. Assigning a clip to every part is switching to it; Blender picks each part's slot by name and makes a slot
when a part is keyed for the first time."""

import bpy
from bpy_extras import anim_utils

from . import character

OWNER = "dasktoon_character"  # Action property, registered by bl_ui.dasktoon_animation


def parts(armature, objects):
    """The IDs a clip of `armature` animates: every object of its character among `objects`, and the Key of each
    mesh."""
    out = []
    for obj in character.members(armature, objects):
        out.append(obj)
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is not None:
            out.append(key)
    return out


def clips_of(armature):
    """The clips of the character of `armature`, by name."""
    return sorted((action for action in bpy.data.actions if getattr(action, OWNER, None) == armature),
                  key=lambda action: action.name)


def current(armature):
    """The clip the armature plays now, or None."""
    anim = armature.animation_data
    action = anim.action if anim is not None else None
    return action if action is not None and getattr(action, OWNER, None) == armature else None


def frame_range(clip):
    """(first, last) frame of `clip`: its manual range when set, else its keys."""
    start, end = clip.frame_range
    return int(round(start)), int(round(end))


def has_keys(clip):
    return any(len(bag.fcurves) for layer in clip.layers for strip in layer.strips for bag in strip.channelbags)


def use(armature, objects, clip, scene=None):
    """Every part of the character plays `clip` (None: no action); with `scene`, its preview range shows the clip."""
    for idb in parts(armature, objects):
        anim = idb.animation_data or idb.animation_data_create()
        if anim.action != clip:
            anim.action = clip
    if scene is not None and clip is not None and has_keys(clip):
        scene.use_preview_range = True
        scene.frame_preview_start, scene.frame_preview_end = frame_range(clip)


def _make(armature, name):
    clip = bpy.data.actions.new(name)
    setattr(clip, OWNER, armature)
    clip.use_fake_user = True  # a clip not in use has no other user, and would not be saved
    return clip


def _copy(action, slot, clip, idb):
    """The curves `idb` gets from `action` (its slot), copied into a slot of `clip` named after `idb`."""
    source = anim_utils.action_get_channelbag_for_slot(action, slot)
    if source is None or not len(source.fcurves):
        return
    layer = clip.layers[0] if len(clip.layers) else clip.layers.new("Layer")
    strip = layer.strips[0] if len(layer.strips) else layer.strips.new(type='KEYFRAME')
    bag = strip.channelbag(clip.slots.new(id_type=idb.id_type, name=idb.name), ensure=True)
    for curve in source.fcurves:
        copy = bag.fcurves.new(curve.data_path, index=curve.array_index,
                               group_name=curve.group.name if curve.group is not None else "")
        copy.extrapolation = curve.extrapolation
        copy.keyframe_points.add(len(curve.keyframe_points))
        for old, new in zip(curve.keyframe_points, copy.keyframe_points):
            new.co, new.handle_left, new.handle_right = old.co, old.handle_left, old.handle_right
            new.interpolation, new.easing = old.interpolation, old.easing
            new.handle_left_type, new.handle_right_type = old.handle_left_type, old.handle_right_type
        copy.update()


def adopt(armature, objects):
    """When the character has no clip yet but its parts are animated (each with its own action, as Key Pose made
    them), gather that animation into a first clip "Clip" and play it. The old actions stay. Returns the clip, or
    None."""
    if clips_of(armature):
        return None
    animated = [idb for idb in parts(armature, objects)
                if idb.animation_data is not None and idb.animation_data.action is not None]
    if not animated:
        return None
    clip = _make(armature, "Clip")
    for idb in animated:
        _copy(idb.animation_data.action, idb.animation_data.action_slot, clip, idb)
    use(armature, objects, clip)
    return clip


def new(armature, objects, name="Clip", scene=None):
    """A new, empty clip that the character plays from now on (its existing animation becomes a clip first)."""
    adopt(armature, objects)
    clip = _make(armature, name)
    use(armature, objects, clip, scene)
    return clip


def delete(armature, objects, clip, scene=None):
    """Delete `clip`; the character plays the first clip left, or nothing."""
    left = [other for other in clips_of(armature) if other != clip]
    use(armature, objects, left[0] if left else None, scene)
    bpy.data.actions.remove(clip)
