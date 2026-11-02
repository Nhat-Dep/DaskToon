# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Auto Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part C): one button for the
whole character. The eyes, the skin round them and the mouth are often meshes of their own, so everything here works on
all the meshes of the character's rig; a mesh without a rig is on its own.

run fills the empty keys from those that move, sculpts what is still missing of the eye keys, and fills again: a blink
made by hand stays and gets its two sides from it, and a key under another name (happy) comes from what was sculpted
(joy). states tells, for each expression of LISTED, what the character has."""

from typing import NamedTuple

import bpy
import numpy as np

from . import expressions, eye_shapes

LISTED = ("BLINK", "BLINK_L", "BLINK_R", "JOY", "ANGRY", "SORROW", "FUN", "SURPRISED", "A", "I", "U", "E", "O")


class Result(NamedTuple):
    sculpted: list  # [(key name, [mesh names])]
    filled: list  # [(key name, how)]
    left: list  # the slots of LISTED nothing moves yet


def rig_of(obj):
    """The humanoid rig of `obj`: itself, or the armature an Armature modifier of the mesh uses; None without one."""
    if obj is None:
        return None
    if obj.type == 'ARMATURE':
        return obj if obj.data.bones.get("Head") is not None else None
    for modifier in obj.modifiers if obj.type == 'MESH' else ():
        if modifier.type == 'ARMATURE' and modifier.object is not None and modifier.object.data.bones.get("Head"):
            return modifier.object
    return None


def meshes_of(obj):
    """Every mesh of the character of `obj`, the rig's own if it has one; `obj` alone otherwise."""
    rig = rig_of(obj)
    if rig is None:
        return [obj] if obj is not None and obj.type == 'MESH' else []
    return [child for child in bpy.data.objects if eye_shapes._is_mesh_of(rig, child)]


def states(meshes):
    """{slot of LISTED: 'READY' a key of it moves on some mesh, 'EMPTY' keys of it move nothing, 'MISSING' it has none}."""
    found = dict.fromkeys(LISTED, 'MISSING')
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        base = np.empty(len(key.reference_key.data) * 3, np.float32)
        key.reference_key.data.foreach_get("co", base)
        for block in key.key_blocks:
            slot = expressions.slot_of(block.name)
            if slot in found and block != key.reference_key and found[slot] != 'READY':
                found[slot] = 'READY' if expressions.key_moves(block, base) else 'EMPTY'
    return found


def slot_keys(obj, slot):
    """The keys showing `slot` on `obj`: one, the first that moves, since the keys of one expression hold one shape (joy
    and happy) and would add up. A blink with no key of its own is its two sides."""
    key = obj.data.shape_keys
    if key is None:
        return []
    blocks = [b for b in key.key_blocks if b != key.reference_key and expressions.slot_of(b.name) == slot]
    if not blocks:
        return slot_keys(obj, "BLINK_L") + slot_keys(obj, "BLINK_R") if slot == "BLINK" else []
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    return [next((b for b in blocks if expressions.key_moves(b, base)), blocks[0])]


def _add_sides(obj):
    """Empty keys for the sides of a blink of `obj` that moves, for fill to make from it. A mesh modelled in half has none:
    a key there moves both sides."""
    key = obj.data.shape_keys
    if key is None or eye_shapes.has_mirror(obj):
        return
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    slots = {expressions.slot_of(block.name) for block in key.key_blocks}
    if any(expressions.slot_of(b.name) == "BLINK" and expressions.key_moves(b, base) for b in key.key_blocks):
        for name, slot in (("blink_L", "BLINK_L"), ("blink_R", "BLINK_R")):
            if slot not in slots:
                obj.shape_key_add(name=name, from_mix=False).value = 0.0


def run(rig, meshes, replace=False):
    """Auto Expressions on `meshes` of `rig` (None: no eyes to sculpt). `replace`: the eye keys are written again."""
    if not replace:
        for obj in meshes:
            _add_sides(obj)
    filled = [] if replace else [pair for obj in meshes for pair in expressions.fill(obj)]
    sculpted = eye_shapes.sculpt(rig, meshes, replace) if rig is not None else []
    filled += [pair for obj in meshes for pair in expressions.fill(obj)]
    return Result(sculpted, filled, [slot for slot, state in states(meshes).items() if state != 'READY'])
