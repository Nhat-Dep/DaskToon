# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The jaw bone of a character, under whatever name its skeleton gives it (expressions.json `bones.jaw`: DaskLive turns
it for jawOpen when the character has it)."""


def jaw_bone(rig):
    """The name of the deforming bone of `rig` that is its jaw: DaskToon's own "Jaw", else a bone whose name the importers
    read as a jaw (J_Bip_C_Jaw, jaw, Jaw_01 ...); None when there is none."""
    if rig is None or rig.type != 'ARMATURE':
        return None
    from dasktoon_import import bones as known
    bone = rig.data.bones.get("Jaw")
    if bone is not None and bone.use_deform:
        return bone.name
    for bone in rig.data.bones:
        if not bone.use_deform:
            continue
        kind = known.classify(bone.name)
        if kind is not None and kind[0] == "Jaw":
            return bone.name
    return None


def add_to(expressions, rig):
    """Put the jaw into `expressions["bones"]` when the rig has one and the humanoid bones lack it."""
    bones = expressions.setdefault("bones", {})
    if "jaw" not in bones:
        name = jaw_bone(rig)
        if name is not None:
            bones["jaw"] = name
    return expressions
