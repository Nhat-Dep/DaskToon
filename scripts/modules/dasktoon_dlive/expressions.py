# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Expressions of a .dlive (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md; format: D:/DaskLive/docs/dlive-format.md,
expressions.json). `make` runs Auto Expressions and the ARKit 52 synthesis on the (temporary) meshes it is given;
`describe` writes what moves: shape keys by ARKit and VRM 1.0 names, humanoid bones, and a report."""

import numpy as np

from dasktoon_rig import auto_expressions, expressions, eye_shapes

ARKIT = (
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft", "eyeSquintLeft",
    "eyeWideLeft", "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight", "eyeLookOutRight", "eyeLookUpRight",
    "eyeSquintRight", "eyeWideRight", "jawForward", "jawLeft", "jawRight", "jawOpen", "mouthClose", "mouthFunnel",
    "mouthPucker", "mouthLeft", "mouthRight", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthPressLeft", "mouthPressRight",
    "mouthLowerDownLeft", "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "browDownLeft",
    "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff", "cheekSquintLeft",
    "cheekSquintRight", "noseSneerLeft", "noseSneerRight", "tongueOut",
)
VRM_OF_SLOT = {"A": "aa", "I": "ih", "U": "ou", "E": "ee", "O": "oh", "BLINK": "blink", "BLINK_L": "blinkLeft",
               "BLINK_R": "blinkRight", "JOY": "happy", "ANGRY": "angry", "SORROW": "sad", "FUN": "relaxed",
               "SURPRISED": "surprised"}
VRM_OTHER = ("lookUp", "lookDown", "lookLeft", "lookRight", "neutral")
THUMB = {"ThumbProximal": "ThumbMetacarpal", "ThumbIntermediate": "ThumbProximal"}  # Unity's names -> VRM 1.0's


def _base(key):
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    return base


def _moving(obj):
    """Names of the shape keys of mesh `obj` that move a vertex."""
    key = obj.data.shape_keys
    if key is None:
        return []
    base = _base(key)
    return [b.name for b in key.key_blocks if b != key.reference_key and expressions.key_moves(b, base)]


def make(meshes, rig):
    """Auto Expressions then the ARKit 52 on `meshes` (copies: they are changed). Returns the report dict
    {"sculpted": [...], "filled": [...]}."""
    from bl_ui import dasktoon_shape_key_manager as manager
    before = {obj: set(_moving(obj)) for obj in meshes}
    result = auto_expressions.run(rig, meshes)
    sculpted = [name for name, _meshes in result.sculpted]
    filled = [name for name, _how in result.filled]
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None or not any(expressions.slot_of(b.name) for b in key.key_blocks):
            continue
        manager.synthesize_arkit52(obj)
        for name in _moving(obj):
            if name in ARKIT and name not in before[obj] and name not in filled:
                filled.append(name)
    return {"sculpted": sculpted, "filled": filled}


def humanoid_bones(rig):
    """{VRM 1.0 role: bone name} of the standard skeleton's bones that `rig` has and deforms."""
    from dasktoon_rig import skeleton
    out = {}
    if rig is None:
        return out
    for name in skeleton.BONE_NAMES:
        bone = rig.data.bones.get(name)
        if bone is None or not bone.use_deform:
            continue
        side = next((s for s in ("Left", "Right") if name.startswith(s)), "")
        rest = name[len(side):]
        for old, new in THUMB.items():
            if rest == old or rest.startswith(old):
                rest = new + rest[len(old):]
                break
        role = side.lower() + rest if side else rest[0].lower() + rest[1:]
        out[role] = name
    return out


def describe(meshes, renamed, rig, made):
    """expressions.json's content. `meshes` are the objects of the model, `renamed` {name: name in the model}."""
    keys, entries, moving = {}, {}, {}
    lower_arkit = {n.lower(): n for n in ARKIT}
    for obj in meshes:
        if obj.type != 'MESH':
            continue
        mesh_name = renamed.get(obj.name, obj.name)
        moving[obj] = _moving(obj)
        for name in moving[obj]:
            arkit = lower_arkit.get(name.lower())
            if arkit is not None:
                entries.setdefault(arkit, []).append((mesh_name, name))
            if name.lower() in {v.lower() for v in VRM_OTHER}:
                vrm = next(v for v in VRM_OTHER if v.lower() == name.lower())
                entries.setdefault(vrm, []).append((mesh_name, name))
        for slot, vrm in VRM_OF_SLOT.items():
            for block in auto_expressions.slot_keys(obj, slot):
                if block.name in moving[obj]:
                    entries.setdefault(vrm, []).append((mesh_name, block.name))
    for expression, pairs in entries.items():
        keys[expression] = [{"mesh": m, "key": k, "weight": 1.0} for m, k in dict.fromkeys(pairs)]
    made = dict(made)
    made["missing"] = [name for name in ARKIT if name not in keys]
    return {"keys": keys, "bones": humanoid_bones(rig), "made": made}
