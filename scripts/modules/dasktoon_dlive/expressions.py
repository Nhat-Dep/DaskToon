# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Expressions of a .dlive (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md; format: D:/DaskLive/docs/dlive-format.md,
expressions.json). `make` runs Auto Expressions and the ARKit 52 synthesis on the (temporary) meshes it is given;
`describe` writes what moves: shape keys by ARKit and VRM 1.0 names, humanoid bones, and a report."""

import numpy as np
from mathutils import Vector

from dasktoon_rig import auto_expressions, expressions, eye_shapes, face_frame, face_shapes

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


def _left_of(obj, frame):
    """The direction of the character's left in the space of mesh `obj` (the frame's +X), None without a frame."""
    if frame is None:
        return None
    left = obj.matrix_world.to_3x3().inverted() @ (frame.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0)))
    return tuple(left) if left.length > 1e-9 else None


def make(meshes, rig):
    """Auto Expressions, the ARKit 52 from them and, for the face keys still empty, ARKit keys sculpted from the face's
    own shape (dasktoon_rig.face_shapes) on `meshes` (copies: they are changed). A character without a DaskToon rig is
    read through a temporary armature on the head found (face_frame). Returns the report dict {"sculpted": [...],
    "filled": [...], "how": {name: how}}."""
    import bpy
    from bl_ui import dasktoon_shape_key_manager as manager
    context = bpy.context
    face_frame.apply_mirrors(context, meshes)
    before = {obj: set(_moving(obj)) for obj in meshes}
    how, sculpted, filled = {}, [], []
    try:
        with face_frame.located(context, meshes, rig) as frame:
            result = auto_expressions.run(frame, meshes)
            sculpted = [name for name, _meshes in result.sculpted]
            filled = [name for name, _how in result.filled]
            for name, why in result.filled:
                how[name] = "filled from " + why
            for obj in meshes:
                key = obj.data.shape_keys
                if key is None or not any(expressions.slot_of(b.name) for b in key.key_blocks):
                    continue
                manager.synthesize_arkit52(obj, left=_left_of(obj, frame))
                for name in _moving(obj):
                    if name in ARKIT and name not in before[obj] and name not in filled:
                        filled.append(name)
                        how[name] = "built from the expression keys"
            face = face_shapes.read(frame, meshes)
            new = face_shapes.sculpt(face, confined=filled) + face_shapes.sculpt_presets(face) if face is not None else []
            for name, why, _names in new:
                if name not in sculpted:
                    sculpted.append(name)
                how[name] = why
            filled = [name for name in filled if name not in sculpted]  # a stand-in made again is sculpted
    except Exception as error:  # a face that cannot be read keeps the keys it has: the export goes on
        how["error"] = "%s: %s" % (type(error).__name__, error)
    return {"sculpted": sculpted, "filled": filled, "how": how}


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


def drop_unused(meshes, renamed, described):
    """Remove from `meshes` (copies) the shape keys no expression plays, that rest at 0 and that no kept key is
    relative to: a model with hundreds of keys sends only what moves in a game."""
    used = {(e["mesh"], e["key"]) for entries in described["keys"].values() for e in entries}
    dropped = 0
    for obj in meshes:
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is None:
            continue
        mesh_name = renamed.get(obj.name, obj.name)
        keep = {b.name for b in key.key_blocks if (mesh_name, b.name) in used or abs(b.value) > 1e-6}
        keep |= {b.relative_key.name for b in key.key_blocks if b.name in keep}
        for block in [b for b in key.key_blocks if b != key.reference_key and b.name not in keep]:
            obj.shape_key_remove(block)
            dropped += 1
    return dropped
