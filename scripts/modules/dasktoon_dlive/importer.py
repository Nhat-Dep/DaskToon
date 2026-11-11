# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File > Import > DaskLive (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md): the glTF model, its DaskToon
materials rebuilt from materials.json's `dasktoon` blocks, shape key values, and the sway chains and colliders of
rig.json put back on the rig where DaskToon has the matching settings."""

import json
import os
import shutil
import tempfile
import zipfile

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

KNOWN_VERSION = 1


class DliveError(Exception):
    pass


def read_manifest(archive):
    """The manifest of an open ZipFile; raises DliveError for a file that is not a .dlive or is of a newer version."""
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    except (KeyError, ValueError):
        raise DliveError(rpt_("This is not a DaskLive file (no manifest)"))
    if manifest.get("format") != "dlive":
        raise DliveError(rpt_("This is not a DaskLive file"))
    version = manifest.get("version")
    if not isinstance(version, int) or version > KNOWN_VERSION:
        raise DliveError(rpt_("This DaskLive file is version %s; this DaskToon reads up to version %d. Update "
                              "DaskToon") % (version, KNOWN_VERSION))
    return manifest


def _restore_rig(rig, data):
    """Chains and colliders of rig.json onto `rig` (its `dasktoon_rig` parts and the bones' chain marks)."""
    from dasktoon_rig import build, sway
    if rig is None or not data:
        return
    settings = rig.data.dasktoon_rig
    scale = sway.rig_scale(rig) or 1.0
    for chain in data.get("chains", []):
        bones = [rig.data.bones.get(n) for n in chain["bones"]]
        if any(b is None for b in bones) or settings.parts.get(chain["part"]) is not None:
            continue
        part = settings.parts.add()
        part.name = chain["part"]
        part.role = 'HAIR'
        part.stiffness, part.gravity, part.drag = chain["stiffness"], chain["gravity"], chain["drag"]
        part.radius = chain["radius"] / scale
        part.sway_in_unity = 'BAKED' if chain.get("unity") == "baked" else 'RUNTIME'
        for bone in bones:
            bone[build.MARK] = chain["part"]
    for collider in data.get("colliders", []):
        if rig.data.bones.get(collider["bone"]) is not None:
            item = settings.colliders.add()
            item.bone = collider["bone"]
            item.radius = collider["radius"] / scale


def import_dlive(context, filepath):
    """Import `filepath`; returns the list of new objects. Raises DliveError for a file DaskToon cannot read."""
    from . import materials
    folder = tempfile.mkdtemp(prefix="dlive_import_")
    try:
        with zipfile.ZipFile(filepath) as archive:
            manifest = read_manifest(archive)
            for entry in archive.namelist():
                if entry.startswith("/") or ".." in entry.split("/"):
                    raise DliveError(rpt_("This DaskLive file holds an unsafe path"))
            archive.extractall(folder)
        before = set(bpy.data.objects)
        glb = os.path.join(folder, manifest["model"])
        bpy.ops.import_scene.gltf(filepath=glb)
        new = [o for o in bpy.data.objects if o not in before]
        with open(os.path.join(folder, manifest["materials"]), encoding="utf-8") as f:
            entries = json.load(f)["materials"]
        used = {slot.material for o in new if o.type == 'MESH' for slot in o.material_slots if slot.material}
        for entry in entries:
            data = entry.get("dasktoon")
            mat = next((m for m in used if m.name == entry["name"]), None) or bpy.data.materials.get(entry["name"])
            if data and mat is not None:
                materials.rebuild(mat, data, folder)
        with open(os.path.join(folder, manifest["rig"]), encoding="utf-8") as f:
            rig_data = json.load(f)
        rig = next((o for o in new if o.type == 'ARMATURE'), None)
        _restore_rig(rig, rig_data.get("rig"))
        for mesh_name, values in (rig_data.get("shapes") or {}).items():
            obj = next((o for o in new if o.type == 'MESH' and o.name == mesh_name), None)
            key = obj.data.shape_keys if obj is not None else None
            for name, value in values.items():
                if key is not None and name in key.key_blocks:
                    key.key_blocks[name].value = value
        try:
            from bl_ui import dasktoon_outline
            dasktoon_outline.sync_all(context.scene)
        except Exception:
            pass
        return new
    finally:
        shutil.rmtree(folder, ignore_errors=True)
