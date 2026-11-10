# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""An imported character's expressions under DaskToon's names (docs/superpowers/specs/2026-11-10-dasktoon-import-adopt-
design.md, section 5), so Auto Expressions, the face tools and Engine Export find them.

The mouth shapes and the blink are renamed (MikuMikuDance's あ い う え お まばたき, Unreal's E_Close); the winks become
Blink_L and Blink_R by the side their vertices are on, not by their names. Joy, Angry, Sorrow, Fun and Surprised are
new shape keys adding a brow, an eye and a mouth shape of the model's own (two of the three at least), as MikuMikuDance
and game models keep them apart. A name DaskToon already has on the mesh, with a key that moves, is left alone."""

import numpy as np

RENAME = (
    ("A", ("あ",)), ("I", ("い",)), ("U", ("う",)), ("E", ("え",)), ("O", ("お",)),
    ("Blink", ("まばたき", "E_Close", "Eye_Close", "EyeClose")),
)
# pairs of winks, most telling first: MikuMikuDance's ウィンク２ closes an eye plainly, ウィンク smiling
WINKS = (("ウィンク２", "ｳｨﾝｸ２右", "ウィンク２右"), ("ウィンク", "ウィンク右"), ("E_Close_L", "E_Close_R"),
         ("Blink_L", "Blink_R"))
# new key: (brow, eyes, mouth), each a list of choices, a choice the keys added together
MADE = (
    ("Joy", ((("にこり",), ("B_Happy",)),
             (("笑い",), ("E_Smile_L", "E_Smile_R")),
             (("にっこり",), ("口角上げ",), ("M_Smile_L", "M_Smile_R"), ("にやり",)))),
    ("Angry", ((("怒り",), ("B_Anger",)),
               (("ｷﾘｯ",), ("キリッ",), ("E_Anger",), ("じと目",)),
               (("∧",), ("口角下げ",), ("M_Anger",)))),
    ("Sorrow", ((("困る",), ("B_Sad",)),
                (("悲しい目",), ("E_Sad",)),
                (("口角下げ",), ("∧",)))),
    ("Fun", ((("にこり",), ("B_Cheerful",), ("B_Happy",)),
             (("なごみ",), ("E_Smile_L", "E_Smile_R")),
             (("口角上げ",), ("にっこり",), ("ω",), ("M_Smile_L", "M_Smile_R")))),
    ("Surprised", ((("上",), ("B_Up_Add",)),
                   (("びっくり",), ("E_Stare",)),
                   (("お",), ("O",), ("□",), ("▲",), ("M_O",)))),
)
LEAST = 2  # parts of three a made key needs


def _arrays(key):
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    out = {}
    for block in key.key_blocks:
        if block != key.reference_key:
            co = np.empty_like(base)
            block.data.foreach_get("co", co)
            out[block.name] = (co - base).reshape(-1, 3)
    return base.reshape(-1, 3), out


def _moves(offsets):
    return offsets is not None and len(offsets) and float(np.abs(offsets).max()) > 1e-6


def _has_slot(obj, slot, offsets):
    from dasktoon_rig import expressions
    return any(expressions.slot_of(name) == slot and _moves(o) for name, o in offsets.items())


def _side(obj, rest, offsets):
    """+1 when the shape moves the character's left (+X of its rig), -1 its right, 0 when it does not move."""
    from dasktoon_rig import expressions
    amount = np.linalg.norm(offsets, axis=1)
    if amount.sum() <= 0.0:
        return 0
    across = expressions._across(obj, rest)
    return 1 if float((across * amount).sum() / amount.sum()) > 0.0 else -1


def _choice(offsets, choices):
    for choice in choices:
        if all(_moves(offsets.get(name)) for name in choice):
            return choice
    return None


def adopt(rig, meshes):
    """Rename and make the expression keys of `meshes` (module docstring); returns [(name, made from)]."""
    from dasktoon_rig import expressions
    done = []
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        rest, offsets = _arrays(key)
        for name, sources in RENAME:
            slot = expressions.slot_of(name)
            if _has_slot(obj, slot, offsets):
                continue
            found = next((s for s in sources if _moves(offsets.get(s))), None)
            if found is not None and key.key_blocks.get(name) is None:
                key.key_blocks[found].name = name
                offsets[name] = offsets.pop(found)
                done.append((name, found))
        if not (_has_slot(obj, "BLINK_L", offsets) or _has_slot(obj, "BLINK_R", offsets)):
            for pair in WINKS:
                sides = {}
                for name in pair:
                    if _moves(offsets.get(name)):
                        sides.setdefault(_side(obj, rest, offsets[name]), name)
                if 1 in sides and -1 in sides:
                    for side, new in ((1, "Blink_L"), (-1, "Blink_R")):
                        old = sides[side]
                        if old != new and key.key_blocks.get(new) is None:
                            key.key_blocks[old].name = new
                            offsets[new] = offsets.pop(old)
                            done.append((new, old))
                    break
        for name, parts in MADE:
            slot = expressions.slot_of(name)
            if _has_slot(obj, slot, offsets) or key.key_blocks.get(name) is not None:
                continue
            chosen = [c for c in (_choice(offsets, choices) for choices in parts) if c is not None]
            if len(chosen) < LEAST:
                continue
            total = sum(offsets[n] for choice in chosen for n in choice)
            block = obj.shape_key_add(name=name, from_mix=False)
            block.value = 0.0  # a new key starts on
            block.data.foreach_set("co", (rest + total).astype(np.float32).ravel())
            offsets[name] = total
            done.append((name, " + ".join(n for choice in chosen for n in choice)))
    return done
