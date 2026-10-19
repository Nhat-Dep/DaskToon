# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fill Empty Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md): an expression shape
key that moves nothing, or barely moves next to the mesh's other expressions, is built from the ones that do.

Keys are known by their usual names (VRM 0.x, VRM 1.0, VRoid, ARKit), case aside, gathered in slots: a key of a slot
is filled from another key of the same slot first ("happy" from "joy"), else by the slot's recipes, the first whose
sources all move. A recipe adds sources times weights, each limited to a part: the character's left or right half,
blended across the middle as Split Left / Right does, or the vertices a source moves up (or down). The character's left
is +X of the armature of a humanoid rig deforming the mesh, its middle at the Hips (filie faces +Y in the scene, so her
mesh's own +X is her right); a mesh without one uses its own X. Slots fill in order,
so a key filled early can feed a later one. The rest face ("neutral") is never filled: VRM keeps it empty."""

import re

import numpy as np

EMPTY_SHARE = 0.15  # a key moving less than this share of the mesh's usual expression (median largest move) is empty
NOTHING = 1e-5
MIDDLE = 0.015  # the blend across X = 0 of a side, as Split Left / Right

# slot: the names (whole, any case) of its keys
SLOTS = {
    "A": ("a", "aa", "fcl_mth_a", "mth_a", "jawopen"),
    "I": ("i", "ih", "fcl_mth_i", "mth_i"),
    "U": ("u", "ou", "fcl_mth_u", "mth_u"),
    "E": ("e", "ee", "fcl_mth_e", "mth_e"),
    "O": ("o", "oh", "fcl_mth_o", "mth_o"),
    "BLINK": ("blink", "eyeblink", "fcl_eye_close"),
    "BLINK_L": ("blink_l", "blinkleft", "eyeblinkleft", "eyeblink_l", "fcl_eye_close_l"),
    "BLINK_R": ("blink_r", "blinkright", "eyeblinkright", "eyeblink_r", "fcl_eye_close_r"),
    "JOY": ("joy", "happy", "fcl_all_joy"),
    "ANGRY": ("angry", "fcl_all_angry"),
    "SORROW": ("sorrow", "sad", "fcl_all_sorrow"),
    "FUN": ("fun", "relaxed", "fcl_all_fun"),
    "SURPRISED": ("surprised", "fcl_all_surprised"),
    "UPPER_UP": ("mouthupperup",),
    "UPPER_UP_L": ("mouthupperupleft", "mouthupperup_l"),
    "UPPER_UP_R": ("mouthupperupright", "mouthupperup_r"),
    "LOWER_DOWN": ("mouthlowerdown",),
    "LOWER_DOWN_L": ("mouthlowerdownleft", "mouthlowerdown_l"),
    "LOWER_DOWN_R": ("mouthlowerdownright", "mouthlowerdown_r"),
}
# slot: recipes, tried in turn; a recipe is ((source slot, weight, part), ...)
RECIPES = {
    "E": ((("A", 0.5, 'ALL'), ("I", 0.5, 'ALL')),),
    "BLINK_L": ((("BLINK", 1.0, 'LEFT'),),),
    "BLINK_R": ((("BLINK", 1.0, 'RIGHT'),),),
    "BLINK": ((("BLINK_L", 1.0, 'ALL'), ("BLINK_R", 1.0, 'ALL')),),  # each side already holds only its half
    "UPPER_UP": ((("I", 1.0, 'UP'),), (("E", 1.0, 'UP'),), (("A", 1.0, 'UP'),)),
    "LOWER_DOWN": ((("A", 1.0, 'DOWN'),),),
    "UPPER_UP_L": ((("UPPER_UP", 1.0, 'LEFT'),),),
    "UPPER_UP_R": ((("UPPER_UP", 1.0, 'RIGHT'),),),
    "LOWER_DOWN_L": ((("LOWER_DOWN", 1.0, 'LEFT'),),),
    "LOWER_DOWN_R": ((("LOWER_DOWN", 1.0, 'RIGHT'),),),
}
ORDER = ("A", "I", "U", "O", "JOY", "ANGRY", "SORROW", "FUN", "SURPRISED", "E", "BLINK_L", "BLINK_R", "BLINK",
         "UPPER_UP", "LOWER_DOWN", "UPPER_UP_L", "UPPER_UP_R", "LOWER_DOWN_L", "LOWER_DOWN_R")


def slot_of(name):
    low = name.lower()
    return next((slot for slot, names in SLOTS.items() if low in names), None)


def _offsets(key, block):
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    co = np.empty_like(base)
    block.data.foreach_get("co", co)
    return (co - base).reshape(-1, 3)


def _across(obj, rest):
    """Per vertex, how far it is to the character's left of the middle (module docstring)."""
    for modifier in obj.modifiers:
        rig = modifier.object if modifier.type == 'ARMATURE' else None
        hips = rig.data.bones.get("Hips") if rig is not None and rig.type == 'ARMATURE' else None
        if hips is not None:
            to_arm = rig.matrix_world.inverted() @ obj.matrix_world
            return rest @ np.array(to_arm.to_3x3())[0] + to_arm.translation.x - hips.head_local.x
    return rest[:, 0]


def _part(offsets, across, part):
    if part == 'ALL':
        return offsets
    if part in ('UP', 'DOWN'):
        keep = offsets[:, 2] > NOTHING if part == 'UP' else offsets[:, 2] < -NOTHING
        return offsets * keep[:, None]
    t = np.clip((across + MIDDLE) / (2.0 * MIDDLE), 0.0, 1.0)
    left = t * t * (3.0 - 2.0 * t)
    return offsets * (left if part == 'LEFT' else 1.0 - left)[:, None]


def fill(obj):
    """Fill the empty expression keys of `obj` that can be built; returns [(key name, how)] in the order filled."""
    key = obj.data.shape_keys if obj.type == 'MESH' else None
    if key is None:
        return []
    rest = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", rest)
    rest = rest.reshape(-1, 3)
    across = _across(obj, rest)
    offsets = {b.name: _offsets(key, b) for b in key.key_blocks if b != key.reference_key}
    largest = {name: float(np.linalg.norm(o, axis=1).max()) if len(o) else 0.0 for name, o in offsets.items()}
    usual = [value for value in largest.values() if value > NOTHING]
    floor = max(NOTHING, EMPTY_SHARE * float(np.median(usual))) if usual else NOTHING
    by_slot = {}
    for name in offsets:
        slot = slot_of(name)
        if slot is not None:
            by_slot.setdefault(slot, []).append(name)
    moves = {name for name, value in largest.items() if value >= floor}

    def source(slot):
        return next((name for name in by_slot.get(slot, ()) if name in moves), None)

    filled = []
    for slot in ORDER:
        for name in by_slot.get(slot, ()):
            if name in moves:
                continue
            same = source(slot)
            if same is not None:
                made, how = offsets[same].copy(), same
            else:
                made = how = None
                for recipe in RECIPES.get(slot, ()):
                    names = [source(part_slot) for part_slot, _weight, _part_name in recipe]
                    if None in names:
                        continue
                    made = sum(weight * _part(offsets[n], across, part) for n, (_s, weight, part) in zip(names, recipe))
                    how = " + ".join("%g %s%s" % (weight, n, "" if part == 'ALL' else " (%s)" % part.lower())
                                     for n, (_s, weight, part) in zip(names, recipe))
                    if np.linalg.norm(made, axis=1).max() >= floor:
                        break
                    made = None
                if made is None:
                    continue
            key.key_blocks[name].data.foreach_set("co", (rest + made).ravel())
            offsets[name] = made
            moves.add(name)
            filled.append((name, how))
    return filled
