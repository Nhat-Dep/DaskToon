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

# slot: the names (whole, any case) of its keys; the Japanese ones are MMD's usual morph names (a, i, u, e, o, blink,
# the wink of the character's left and right, smile, angry, troubled, surprised)
SLOTS = {
    "A": ("a", "aa", "fcl_mth_a", "mth_a", "jawopen", "あ"),
    "I": ("i", "ih", "fcl_mth_i", "mth_i", "い"),
    "U": ("u", "ou", "fcl_mth_u", "mth_u", "う"),
    "E": ("e", "ee", "fcl_mth_e", "mth_e", "え"),
    "O": ("o", "oh", "fcl_mth_o", "mth_o", "お"),
    "BLINK": ("blink", "eyeblink", "fcl_eye_close", "まばたき"),
    "BLINK_L": ("blink_l", "blinkleft", "eyeblinkleft", "eyeblink_l", "fcl_eye_close_l", "ウィンク"),
    "BLINK_R": ("blink_r", "blinkright", "eyeblinkright", "eyeblink_r", "fcl_eye_close_r", "ウィンク右"),
    "JOY": ("joy", "happy", "fcl_all_joy", "笑い"),
    "ANGRY": ("angry", "fcl_all_angry", "怒り"),
    "SORROW": ("sorrow", "sad", "fcl_all_sorrow", "困る"),
    "FUN": ("fun", "relaxed", "fcl_all_fun"),
    "SURPRISED": ("surprised", "fcl_all_surprised", "びっくり"),
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


def key_moves(block, base):
    """True when the shape key `block` moves a vertex off `base` (the reference key's "co", float32)."""
    co = np.empty_like(base)
    block.data.foreach_get("co", co)
    return bool(np.abs(co - base).max() > NOTHING) if len(co) else False


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
            key.key_blocks[name].value = 0.0  # it was empty, so off until used (a new shape key starts at 1)
            offsets[name] = made
            moves.add(name)
            filled.append((name, how))
    return filled


# Repair Shape Keys: editing the mesh with the Basis active moves only the Basis; every other key keeps the vertices
# where they were, so each key pulls them back by the same offset, and keys add up (temp_2_1, a real model: 191 of 226
# keys did on 213 vertices of the hands and chest; with 11 keys on, the hands moved 25 mm). A single vertex a key throws
# far from its neighbours is a left over too (merging two models: "joy" threw one at the throat 11.5 mm).
STALE_KEYS = 4  # a vertex is stale when at least this many keys move it by the very same offset ...
STALE_SHARE = 0.8  # ... and they are this share of the keys that move anything
STALE_LEAST = 1e-4  # (x the mesh's size) an offset this small is nothing
SAME = 1e-5  # (x the mesh's size) offsets this near are the same
SPIKE = 4.0  # a key moving a vertex this many times further than any of its neighbours ...
SPIKE_LEAST = 0.0015  # ... and further than this (x the mesh's size) has thrown it
GENERATED = "DT_Fix_"  # DaskToon's bend fixes, made from the Basis as it is: not counted


def _key_offsets(obj):
    """(names, offsets keys x vertices x 3, the mesh's size) of obj's shape keys but the Basis."""
    key = obj.data.shape_keys
    if key is None or len(key.key_blocks) < 2:
        return [], np.zeros((0, len(obj.data.vertices), 3)), 1.0
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    blocks = [b for b in key.key_blocks if b != key.reference_key]
    out = np.empty((len(blocks), len(base) // 3, 3))
    for k, block in enumerate(blocks):
        out[k] = _offsets(key, block)
    rest = base.reshape(-1, 3)
    size = float(np.linalg.norm(np.ptp(rest, axis=0))) if len(rest) else 1.0
    return [b.name for b in blocks], out, max(size, 1e-9)


def stale_vertices(obj):
    """(mask over the vertices, offset n x 3) of the vertices most keys move by one same offset, and that offset."""
    names, offsets, size = _key_offsets(obj)
    counted = [k for k, name in enumerate(names) if not name.startswith(GENERATED)]
    mask = np.zeros(offsets.shape[1], bool)
    if len(counted) < STALE_KEYS:
        return mask, np.zeros((offsets.shape[1], 3))
    sub = offsets[counted]
    moving = (np.abs(sub).max(axis=2) > STALE_LEAST * size).any(axis=1).sum()  # keys moving anything
    median = np.median(sub, axis=0)
    agree = (np.abs(sub - median[None]).max(axis=2) < SAME * size).sum(axis=0)
    mask = (np.linalg.norm(median, axis=1) > STALE_LEAST * size) & (agree >= STALE_KEYS) & \
        (agree >= STALE_SHARE * max(moving, 1))
    return mask, np.where(mask[:, None], median, 0.0)


def _neighbours(obj):
    edges = np.empty(len(obj.data.edges) * 2, np.int64)
    obj.data.edges.foreach_get("vertices", edges)
    out = [[] for _ in range(len(obj.data.vertices))]
    for a, b in edges.reshape(-1, 2).tolist():
        out[a].append(b)
        out[b].append(a)
    return out


def spikes(obj, neighbours=None):
    """{key name: [vertices]} each key throws far from all their neighbours."""
    names, offsets, size = _key_offsets(obj)
    neighbours = neighbours if neighbours is not None else _neighbours(obj)
    out = {}
    for k, name in enumerate(names):
        if name.startswith(GENERATED):
            continue
        d = np.linalg.norm(offsets[k], axis=1)
        found = [v for v in np.nonzero(d > SPIKE_LEAST * size)[0].tolist()
                 if neighbours[v] and d[v] > SPIKE * max(d[neighbours[v]].max(), 1e-12)]
        if found:
            out[name] = found
    return out


def _head_share(obj, rig):
    """Per vertex, the share of its deforming weight on the rig's Neck, Head and the bones below them; None without a
    Head. The Neck counts: Build weights the chin of some characters to it (tdt, Luna: real models)."""
    from . import weights
    head = rig.data.bones.get("Head") if rig is not None else None
    if head is None:
        return None
    deform = [b.name for b in rig.data.bones if b.use_deform]
    neck = rig.data.bones.get("Neck")
    top = neck if neck is not None and head in neck.children_recursive else head
    below = {top.name} | {b.name for b in top.children_recursive}
    matrix = weights.read(obj, deform)
    total = matrix.sum(axis=1)
    on_head = matrix[:, [j for j, n in enumerate(deform) if n in below]].sum(axis=1)
    return np.where(total > 0.0, on_head / np.maximum(total, 1e-12), np.nan)


def off_region(obj, rig):
    """{key name: [vertices]} a face key moves that follow the trunk or limbs: a key is a face key when most of the
    vertices it moves follow the neck or head, and of its moved vertices, a joined group that mostly does not is no
    part of the face (temp_2_1, merged from two models: "Eyes Sharp 2 R" moved 195 vertices of the upper chest up to
    38 mm, more than the eyes). Skin joined to the face that moves with it stays."""
    from . import parts
    share = _head_share(obj, rig)
    if share is None:
        return {}
    names, offsets, size = _key_offsets(obj)
    edges = np.empty(len(obj.data.edges) * 2, np.int64)
    obj.data.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    follows = share >= 0.5
    other = share < 0.5  # nan (no weight) is neither
    out = {}
    for k, name in enumerate(names):
        if name.startswith(GENERATED):
            continue
        moved = np.linalg.norm(offsets[k], axis=1) > STALE_LEAST * size
        if not (moved & other).any() or (moved & follows).sum() < (moved & other).sum():
            continue
        found = []
        for group in parts.pieces(edges, np.nonzero(moved)[0]):
            if follows[group].sum() < other[group].sum():
                found += group[other[group]].tolist()
        if found:
            out[name] = sorted(found)
    return out


def repair_keys(obj, rig=None):
    """Take the stale offset out of every key that holds it, give each thrown vertex its neighbours' mean move and,
    with the rig, stop face keys moving what does not follow the head. Returns (how many vertices were stale, {key
    name: other vertices mended})."""
    key = obj.data.shape_keys
    if key is None:
        return 0, {}
    stale, offset = stale_vertices(obj)
    names, offsets, size = _key_offsets(obj)
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    base = base.reshape(-1, 3)
    changed = np.zeros(len(names), bool)
    squared = np.maximum((offset * offset).sum(axis=1), 1e-30)
    for k in range(len(names)):
        off = offsets[k]
        # the old offset once, or several times in a key added up from others ("joy" from eyes, brows and mouth)
        times = (off * offset).sum(axis=1) / squared
        holds = stale & (times > 0.5) & (np.abs(off - times[:, None] * offset).max(axis=1) < SAME * size)
        off[holds] = 0.0
        changed[k] |= holds.any()

    def write():
        for k, name in enumerate(names):
            if changed[k]:
                key.key_blocks[name].data.foreach_set("co", (base + offsets[k]).ravel())
        changed[:] = False

    write()
    mended = {}
    # stray groups only once the old offsets are out (they joined some to the face), until none is left: taking one
    # out can leave a smaller one standing alone
    for _round in range(8):
        reach = off_region(obj, rig)
        if not reach:
            break
        for name, found in reach.items():
            k = names.index(name)
            offsets[k][found] = 0.0
            changed[k] = True
            mended[name] = mended.get(name, 0) + len(found)
        write()
    neighbours = _neighbours(obj)
    for k, name in enumerate(names):
        if name.startswith(GENERATED):
            continue
        off = offsets[k]
        d = np.linalg.norm(off, axis=1)
        for v in np.nonzero(d > SPIKE_LEAST * size)[0].tolist():
            if neighbours[v] and d[v] > SPIKE * max(d[neighbours[v]].max(), 1e-12):
                off[v] = off[neighbours[v]].mean(axis=0)
                changed[k] = True
                mended[name] = mended.get(name, 0) + 1
    write()
    obj.data.update()
    return int(stale.sum()), mended
