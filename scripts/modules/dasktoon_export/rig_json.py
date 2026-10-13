# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""<Model>.rig.json beside the FBX (anime rig spec 9.5): the chains and colliders DaskToon's Unity spring bone needs,
by bone name. Unity keeps a bone's tail along its local +Y, as Blender does, so only lengths and radii travel, in world
units (meters): the rig keeps its radii in armature units. Version 2 (R3, spec 10) adds the flat eyes and 2D mouths:
the mesh, the material (name and slot), the eye's side and range, the atlas's rows and columns and its cell bone."""

import json

VERSION = 2


def _length(rig, bone):
    world = rig.matrix_world
    return (world @ bone.tail_local - world @ bone.head_local).length


def _face(rig):
    """(flat eyes, mouths) of the rig file."""
    from dasktoon_rig import eyes, mouth, parts as rig_parts
    flat_eyes, mouths = [], []
    data = getattr(rig.data, "dasktoon_rig", None)
    for part in data.parts if data is not None else ():
        if part.object is None or part.role not in rig_parts.FACE_ROLES:
            continue
        vertices = rig_parts.part_vertices(part)
        slot, mat = (rig_parts.part_materials(part, vertices) or [(0, None)])[0]
        entry = {"object": part.object.name, "material": mat.name if mat is not None else "", "slot": slot}
        if part.role == 'FLAT_EYE':
            entry.update(side=eyes.side_of(rig, part, vertices), range=round(part.eye_range, 6))
            flat_eyes.append(entry)
        else:
            entry.update(rows=part.mouth_rows, columns=part.mouth_columns, bone=mouth.CELL_BONE)
            mouths.append(entry)
    return flat_eyes, mouths


def rig_data(rig):
    """The json-ready dict of an armature with chains Build Rig made, flat eyes or 2D mouths; None without any."""
    from dasktoon_rig import spring, sway
    found = sway.chains(rig)
    flat_eyes, mouths = _face(rig)
    if not found and not flat_eyes and not mouths:
        return None
    data = rig.data.dasktoon_rig
    bones = rig.data.bones
    scale = sway.rig_scale(rig)
    chains = []
    for part_name, names in found:
        part = data.parts.get(part_name)
        defaults = spring.Params()
        chains.append({
            "part": part_name,
            "bones": names,
            "lengths": [round(_length(rig, bones[name]), 6) for name in names],
            "stiffness": round(part.stiffness if part else defaults.stiffness, 6),
            "gravity": round(part.gravity if part else defaults.gravity, 6),
            "drag": round(part.drag if part else defaults.drag, 6),
            "radius": round((part.radius if part else defaults.radius) * scale, 6),
            "unity": "baked" if part is not None and part.sway_in_unity == 'BAKED' else "runtime",
        })
    colliders = [{"bone": c.bone, "radius": round(c.radius * scale, 6), "length": round(_length(rig, bones[c.bone]), 6)}
                 for c in data.colliders if bones.get(c.bone) is not None]
    return {"version": VERSION, "chains": chains, "colliders": colliders, "flatEyes": flat_eyes, "mouths": mouths}


def text(data):
    return json.dumps(data, indent=2) + "\n"


def find_rig(objects):
    """The first armature of `objects` with something for the rig file (chains, flat eyes, 2D mouths), or None."""
    return next((obj for obj in objects if obj.type == 'ARMATURE' and rig_data(obj) is not None), None)


def runtime_parts(rig):
    """Names of the hair and skirt parts whose chains Unity sways itself."""
    from dasktoon_rig import parts
    return {part.name for part in rig.data.dasktoon_rig.parts
            if part.role in parts.CHAIN_ROLES and part.sway_in_unity == 'RUNTIME'}
