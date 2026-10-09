# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""<Model>.rig.json beside the FBX (anime rig spec 9.5): the chains and colliders DaskToon's Unity spring bone needs,
by bone name. Unity keeps a bone's tail along its local +Y, as Blender does, so only lengths (world, meters) travel."""

import json

VERSION = 1


def _length(rig, bone):
    world = rig.matrix_world
    return (world @ bone.tail_local - world @ bone.head_local).length


def rig_data(rig):
    """The json-ready dict of an armature whose chains Build Rig made, or None when it has none."""
    from dasktoon_rig import spring, sway
    found = sway.chains(rig)
    if not found:
        return None
    data = rig.data.dasktoon_rig
    bones = rig.data.bones
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
            "radius": round(part.radius if part else defaults.radius, 6),
            "unity": "baked" if part is not None and part.sway_in_unity == 'BAKED' else "runtime",
        })
    colliders = [{"bone": c.bone, "radius": round(c.radius, 6), "length": round(_length(rig, bones[c.bone]), 6)}
                 for c in data.colliders if bones.get(c.bone) is not None]
    return {"version": VERSION, "chains": chains, "colliders": colliders}


def text(data):
    return json.dumps(data, indent=2) + "\n"


def find_rig(objects):
    """The first armature of `objects` with chains made by Build Rig, or None."""
    from dasktoon_rig import sway
    return next((obj for obj in objects if obj.type == 'ARMATURE' and sway.chains(obj)), None)


def runtime_parts(rig):
    """Names of the hair and skirt parts whose chains Unity sways itself."""
    from dasktoon_rig import parts
    return {part.name for part in rig.data.dasktoon_rig.parts
            if part.role in parts.CHAIN_ROLES and part.sway_in_unity == 'RUNTIME'}
