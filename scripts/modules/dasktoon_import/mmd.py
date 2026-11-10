# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""MikuMikuDance models for DaskToon (docs/superpowers/specs/2026-11-10-dasktoon-import-adopt-design.md, section 2):
MMD Tools reads the model (mesh, skeleton, morphs; not its rigid bodies, which DaskToon's sway replaces), the model's
physics says which bones swing, adopt.py does the rest."""

import importlib
import logging
import os
import sys

import bpy


def _mmd(sub):
    """A module of the MMD Tools loaded now: DaskToon's own (addons_core) or an extension someone installed."""
    for name in list(sys.modules):
        if name.split(".")[-1] == "mmd_tools" and hasattr(sys.modules[name], "__path__"):
            return importlib.import_module(name + "." + sub)
    raise ImportError("MMD Tools")


def swinging_bones(path):
    """The Japanese names of the bones the model's physics moves (its dynamic rigid bodies); None when the file cannot
    tell."""
    level = logging.getLogger().level
    logging.getLogger().setLevel(logging.WARNING)  # the reader logs every section at INFO
    try:
        if path.lower().endswith(".pmd"):
            model = _mmd("core.pmd").load(path)
            rigids, bones = model.rigid_bodies, model.bones
        else:
            model = _mmd("core.pmx").load(path)
            rigids, bones = model.rigids, model.bones
    except Exception:  # an unreadable file was already reported by the import itself
        return None
    finally:
        logging.getLogger().setLevel(level)
    return {bones[r.bone].name for r in rigids
            if r.mode in (1, 2) and isinstance(r.bone, int) and 0 <= r.bone < len(bones)}


def import_file(context, path, scale=0.08):
    """Read the model with MMD Tools; returns the new objects."""
    before = set(bpy.data.objects)
    result = bpy.ops.mmd_tools.import_model(filepath=path, scale=scale, types={'MESH', 'ARMATURE', 'MORPHS'},
                                            log_level='WARNING')
    if 'FINISHED' not in result:
        raise RuntimeError(os.path.basename(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def bone_names_by_japanese(armature):
    """{Japanese name: bone name} of an armature MMD Tools made (it renames 左足 to 足.L)."""
    out = {}
    for pb in armature.pose.bones:
        mmd = getattr(pb, "mmd_bone", None)
        if mmd is not None and mmd.name_j:
            out[mmd.name_j] = pb.name
    return out


def adopt_file(context, path, scale=0.08):
    """Import and adopt one model; returns adopt.Result."""
    return adopt_imported(context, path, import_file(context, path, scale))


def adopt_imported(context, path, objects, controls=True):
    """Adopt the model MMD Tools just made of `path` (`objects`, the new objects); returns adopt.Result."""
    from . import adopt
    armature, meshes = adopt.source_of(objects)
    if armature is None:
        raise adopt.AdoptError(bpy.app.translations.pgettext_rpt("No skeleton in the model"))
    japanese = swinging_bones(path)
    swaying = None
    if japanese is not None:
        names = bone_names_by_japanese(armature)
        swaying = {names[j] for j in japanese if j in names}
    return adopt.adopt(context, armature, meshes, kind='MMD', swaying=swaying, controls=controls)
