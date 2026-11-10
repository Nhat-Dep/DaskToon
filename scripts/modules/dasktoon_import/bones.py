# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Which bone of an imported skeleton is which DaskToon bone (docs/superpowers/specs/2026-11-10-dasktoon-import-adopt-
design.md, section 3). Plain Python over SourceBone records, so it runs without Blender.

A bone's name tells its side and its kind in the naming of MikuMikuDance (Japanese, 左/右), 3ds Max Biped
("Bip001 L Thigh"), Unreal ("thigh_l"), Mixamo ("mixamorig:LeftUpLeg"), VRoid ("J_Bip_L_UpperLeg") and DaskToon itself.
The shape decides the rest: the spine is the bones of the spine kind on the way from the neck down, in the order they
hang; the fingers' joints are the first three of each finger in the order they hang; a side the names give the wrong
way round (the character's left is +X) is swapped back."""

import re
from typing import NamedTuple


class SourceBone(NamedTuple):
    name: str
    parent: str  # None at the root
    head: tuple
    tail: tuple
    aliases: tuple = ()  # other names of the bone (MikuMikuDance's Japanese name)


# kind: its names without side, separators or case
KINDS = {
    "Hips": ("hips", "pelvis", "下半身"),
    "Neck": ("neck", "neck01", "首"),
    "Head": ("head", "頭"),
    "Jaw": ("jaw",),
    "Eye": ("eye", "目"),
    "Shoulder": ("shoulder", "clavicle", "肩"),
    "UpperArm": ("upperarm", "arm", "腕"),
    "LowerArm": ("lowerarm", "forearm", "ひじ"),
    "Hand": ("hand", "手首"),
    "UpperLeg": ("upperleg", "upleg", "thigh", "足", "足d"),
    "LowerLeg": ("lowerleg", "leg", "calf", "ひざ", "ひざd"),
    "Foot": ("foot", "足首", "足首d"),
    "Toes": ("toes", "toebase", "toe", "toe0", "ball", "足先ex"),
}
SIDED = {"Eye", "Shoulder", "UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot", "Toes"}
SPINE_RE = re.compile(r"^(spine\d*|spine_?\d+|chest|upperchest|上半身\d*)$")
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
FINGER_WORDS = (("thumb", "親指"), ("index", "人指", "人差指"), ("middle", "中指"), ("ring", "薬指"),
                ("little", "pinky", "小指"))
SEGMENTS = ("Proximal", "Intermediate", "Distal")
SPINE_NAMES = ("Spine", "Chest", "UpperChest")
WIDE = str.maketrans("０１２３４５６７８９ＬＲ", "0123456789LR")
PREFIX_RE = re.compile(r"^(mixamorig\d*[:_]|bip0*1[ _]?|def[-_.]|j_bip_|j_)", re.IGNORECASE)


def _side_and_rest(name):
    """('L' / 'R' / '', the name without its side) of one name, original case kept."""
    s = name.translate(WIDE).strip()
    s = PREFIX_RE.sub("", s)
    if s and s[0] in "左右" and len(s) > 1:
        return ("L" if s[0] == "左" else "R"), s[1:]
    m = re.match(r"^([CLR])[_ .](.+)$", s)  # VRoid J_Bip_L_..., Biped "L Thigh"
    if m:
        return ("" if m.group(1) == "C" else m.group(1)), m.group(2)
    m = re.match(r"^(Left|Right)(?=[A-Z_ .])(.+)$", s)
    if m:
        return m.group(1)[0], m.group(2)
    m = re.match(r"^(.+?)[_ .\-]?(left|right)$", s, re.IGNORECASE)
    if m:
        return m.group(2)[0].upper(), m.group(1)
    m = re.match(r"^(.+?)[_ .\-]([lLrR])$", s)
    if m:
        return m.group(2).upper(), m.group(1)
    m = re.match(r"^([LR])(?=[A-Z0-9])(.+)$", s)  # Biped without spaces: "LThigh", "RFinger0"
    if m:
        return m.group(1), m.group(2)
    return "", s


def _key(text):
    return re.sub(r"[\s_.\-:]+", "", text).lower()


def classify(name):
    """(kind, side, number) of one bone name, or None: kind is a KINDS key, 'Spine' (number its level in the name, -1
    without one) or a finger of FINGERS (number its joint, 0 first)."""
    side, rest = _side_and_rest(name)
    key = _key(rest)
    if side and key.startswith("hand") and len(key) > 4 and not key.startswith("hand0"):
        key = key[4:]  # Mixamo LeftHandIndex1
    for kind, keys in KINDS.items():
        if key in keys:
            if (kind in SIDED) != bool(side):
                return None
            return kind, side, 0
    if not side and SPINE_RE.match(key):
        digits = re.sub(r"\D", "", key)
        return "Spine", "", (int(digits) if digits else (-1 if key.startswith(("spine", "上半身")) else 50))
    if side:
        m = re.match(r"^finger([0-4])(\d?)$", key)  # Biped: Finger0 Finger01 Finger02 is the thumb
        if m:
            return FINGERS[int(m.group(1))], side, int(m.group(2) or 0)
        for finger, words in zip(FINGERS, FINGER_WORDS):
            for word in words:
                m = re.match("^" + word + r"[_]?(\d+|proximal|intermediate|distal)$", key)
                if m:
                    joint = m.group(1)
                    return finger, side, int(joint) if joint.isdigit() else SEGMENTS.index(joint.capitalize())
    return None


class MapError(Exception):
    """The skeleton lacks bones DaskToon needs; `missing` names them."""

    def __init__(self, missing):
        super().__init__(", ".join(missing))
        self.missing = missing


def _depths(bones):
    parent = {b.name: b.parent for b in bones}
    out = {}
    for b in bones:
        depth, p = 0, b.parent
        while p is not None and depth < 10000:
            depth += 1
            p = parent.get(p)
        out[b.name] = depth
    return out


def ancestors(bones, name):
    """The names above `name`, nearest first."""
    parent = {b.name: b.parent for b in bones}
    out, p = [], parent.get(name)
    while p is not None and p not in out:
        out.append(p)
        p = parent.get(p)
    return out


def _all_names(bone):
    return (bone.name,) + tuple(a for a in bone.aliases if a)


def match(bones):
    """({DaskToon bone: the source bone giving its joint}, {source bone: DaskToon bone} of every source bone named as
    one, such as MikuMikuDance's leg and its D twin) of the skeleton `bones` (SourceBone). Raises MapError when one of
    the bones DaskToon cannot do without (dasktoon_rig.skeleton.REQUIRED) is not found."""
    from dasktoon_rig import skeleton
    depth = _depths(bones)
    found = {}  # DaskToon name -> [(order, source name)]
    spine = []
    fingers = {}
    for bone in bones:
        hit = None
        for name in _all_names(bone):
            hit = classify(name)
            if hit is not None:
                break
        if hit is None:
            continue
        kind, side, number = hit
        if kind == "Spine":
            spine.append(bone.name)
        elif kind in FINGERS:
            fingers.setdefault((side, kind), []).append(bone.name)
        else:
            target = (("Left" if side == "L" else "Right") + kind) if side else kind
            found.setdefault(target, []).append(bone.name)
    out, members = {}, {}
    for target, names in found.items():
        # Two bones of a kind (MikuMikuDance's leg and its D twin, which carries the weights) stand at one place:
        # the joint from the one nearest the root, the weights of both.
        out[target] = min(names, key=lambda n: depth[n])
        for name in names:
            members[name] = target
    for (side, finger), names in fingers.items():
        names.sort(key=lambda n: depth[n])
        prefix = "Left" if side == "L" else "Right"
        for segment, name in zip(SEGMENTS, names):
            out[prefix + finger + segment] = name
    neck = out.get("Neck") or out.get("Head")
    if neck is not None:
        above = ancestors(bones, neck)
        chain = [n for n in reversed(above) if n in spine]
        if not chain:
            chain = [n for n in spine]
            chain.sort(key=lambda n: depth[n])
        for name, target in zip(_spread(chain), SPINE_NAMES):
            if name is not None:
                out[target] = name
    if "Hips" not in out:
        hips = _common_parent(bones, out)
        if hips is not None:
            out["Hips"] = hips
    if _sides_swapped(bones, out):
        out = {_other_side(t): n for t, n in out.items()}
        members = {n: _other_side(t) for n, t in members.items()}
    for target, name in out.items():
        members[name] = target
    missing = [name for name in skeleton.REQUIRED if name not in out]
    if missing:
        raise MapError(missing)
    return out, members


def _spread(chain):
    """The spine's bones (lowest first) as (Spine, Chest, UpperChest): all three from three or more (first, middle,
    last), Spine and Chest from two, Spine from one."""
    n = len(chain)
    if n >= 3:
        return [chain[0], chain[n // 2] if n > 3 else chain[1], chain[-1]]
    return list(chain) + [None] * (3 - n)


def _common_parent(bones, out):
    """The nearest bone above both upper legs and the spine, for a skeleton without a bone named as the hips."""
    legs = [out.get("LeftUpperLeg"), out.get("RightUpperLeg"), out.get("Spine")]
    if any(n is None for n in legs):
        return None
    sets = [[n] + ancestors(bones, n) for n in legs]
    for name in sets[0]:
        if all(name in s for s in sets[1:]) and name not in legs:
            return name
    return None


def _sides_swapped(bones, out):
    """True when the upper arms' heads say the names are the wrong way round (the character's left is +X)."""
    head = {b.name: b.head for b in bones}
    left, right = out.get("LeftUpperArm"), out.get("RightUpperArm")
    return left is not None and right is not None and head[left][0] < head[right][0]


def _other_side(target):
    if target.startswith("Left"):
        return "Right" + target[4:]
    if target.startswith("Right"):
        return "Left" + target[5:]
    return target
