# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskLive (.dlive) export and import (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md; the format is
D:\\DaskLive\\docs\\dlive-format.md): the Godot export's model, rig data, material values and finish packed into one ZIP,
with the expressions the character plays."""

import contextlib
import datetime
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

VERSION = 1
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass
class Options:
    make_expressions: bool = True
    texture_size: int = 2048
    thumbnail: bool = True
    merge_meshes: bool = True
    bake_samples: int = 1  # an emission bake has no noise: 1 sample gives the same pixels in 60% of the time
    morph_normals: bool = False  # the shape keys' normals: 80% of a face rig's size, little seen on a toon face
    drop_unused_keys: bool = True  # shape keys no expression plays (on the copies made for the expressions)


@dataclass
class Report:
    filepath: str = ""
    materials: list = field(default_factory=list)
    expressions: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    thumbnail: bool = False

    def summary(self):
        made = self.expressions.get("made", {})
        return rpt_("DaskLive: %d materials, %d expressions made, %d warnings") % (
            len(self.materials), len(made.get("sculpted", [])) + len(made.get("filled", [])), len(self.warnings))


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


JPEG_QUALITY = 90
DATA_MAPS = ("alpha", "normal", "mask", "height", "rough", "metal")  # kept as PNG, whatever they look like


def _opaque(image):
    """True when no pixel of `image` is see-through (a colour map of that is smaller as a JPEG)."""
    if image.channels < 4 or image.alpha_mode == 'NONE':
        return True
    pixels = np.empty(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    return bool(pixels[3::4].min() >= 0.999)


def _texture(source, dest_folder, rel_name, size, rep, colour=False):
    """Copy the image at `source` into dest_folder, scaled down to `size` (a PNG when it has to change, a JPEG when it
    is a colour map with nothing see-through: a third of the size); returns its path in the archive, or None."""
    stem, ext = os.path.splitext(rel_name)
    image = None
    try:
        image = bpy.data.images.load(source, check_existing=False)
        width, height = image.size
        biggest = max(width, height)
        if ext.lower() in TEXTURE_EXTENSIONS and biggest <= size and (ext.lower() != ".png" or not colour):
            shutil.copyfile(source, os.path.join(dest_folder, rel_name))
            return "textures/" + rel_name
        if biggest > size:
            factor = size / biggest
            image.scale(max(1, round(width * factor)), max(1, round(height * factor)))
        jpeg = colour and _opaque(image)
        image.file_format = 'JPEG' if jpeg else 'PNG'
        out = os.path.join(dest_folder, stem + (".jpg" if jpeg else ".png"))
        image.filepath_raw = out
        if jpeg:
            image.save(quality=JPEG_QUALITY)
        else:
            image.save()
        return "textures/" + os.path.basename(out)
    except Exception as ex:  # a texture that cannot be read leaves its material with the value
        rep.warnings.append(rpt_("Texture %s left out (%s)") % (rel_name, ex))
        return None
    finally:
        if image is not None:
            bpy.data.images.remove(image)


def _file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def export(context, filepath, objects, options=None):
    """Write `objects` as a .dlive at `filepath`; returns a Report. With options.make_expressions the expressions are
    made on temporary copies, so the file being worked on is unchanged (spec R4)."""
    from dasktoon_export import ExportOptions, godot, merge
    from dasktoon_export.godot import finish as godot_finish
    from dasktoon_export.targets import ExportTarget
    from dasktoon_rig import auto_expressions, eye_shapes
    from . import copies, expressions, materials as dlive_materials, slots, thumbnail

    options = options or Options()
    rep = Report(filepath=filepath)
    name = os.path.splitext(os.path.basename(filepath))[0] or "Character"
    work = tempfile.mkdtemp(prefix="dlive_")
    textures_dir = os.path.join(work, "textures")
    os.makedirs(textures_dir)
    entries, texture_map, by_hash = [], {}, {}

    def collect(spec, entry, textures):
        mapped = {}
        for uniform, res in textures.items():
            rel = res.split("/Textures/", 1)[-1]
            if rel not in texture_map:
                source = os.path.join(work, "godot", name, "Textures", rel)
                colour = not any(word in uniform.lower() for word in DATA_MAPS)
                made = _texture(source, textures_dir, rel, options.texture_size, rep, colour)
                if made is not None:  # the same picture under two names is kept once (a shadow colour like the base)
                    digest = _file_hash(os.path.join(work, made.replace("/", os.sep)))
                    if digest in by_hash and by_hash[digest] != made:
                        os.remove(os.path.join(work, made.replace("/", os.sep)))
                        made = by_hash[digest]
                    by_hash.setdefault(digest, made)
                texture_map[rel] = made
            mapped[uniform] = texture_map[rel]
        for part in (entry, entry.get("outline")):
            if part is None:
                continue
            part["params"] = {k: (mapped.get(k) if isinstance(v, str) else v) for k, v in part["params"].items()
                              if not (isinstance(v, str) and mapped.get(k) is None)}
        entry["dasktoon"] = dlive_materials.block(spec, {k: v for k, v in mapped.items() if v})
        entries.append(entry)
        rep.materials.append(entry["name"])

    try:
        copying = copies.temporary(context, objects) if options.make_expressions else contextlib.nullcontext(
            list(objects))
        with copying as objs:
            sources = merge.sources(objs) if options.merge_meshes else []
            renamed = {obj.name: sources[0].name for obj in sources}
            rigs = [o for o in objs if o.type == 'ARMATURE']
            rig = auto_expressions.rig_of(rigs[0]) if rigs else None
            made = {"sculpted": [], "filled": []}
            if options.make_expressions:
                meshes = [o for o in objs if o.type == 'MESH']
                meshes = [m for m in meshes if rig is None or eye_shapes._is_mesh_of(rig, m)] or meshes
                made = expressions.make(meshes, rig)
            target = ExportTarget('GODOT_4', 'FOLDER', os.path.join(work, "godot"), name)
            settings = ExportOptions(include_animation=False, bake_size=min(options.texture_size, 1024),
                                     bake_samples=options.bake_samples, merge_meshes=options.merge_meshes,
                                     morph_normals=options.morph_normals)
            rep.expressions = expressions.describe(objs, renamed, rig, made)
            if options.make_expressions and options.drop_unused_keys:
                expressions.drop_unused(objs, renamed, rep.expressions)
            with slots.filled(objs):
                grep = godot.export_model(context, target, objs, settings, collect)
            rep.warnings += list(grep.warnings)
            rep.warnings += [rpt_("Material %s: %s (DaskLive shows the model's own material)") % item for item in grep.skipped]
            thumb_path = os.path.join(work, "thumbnail.png")
            if options.thumbnail:
                try:
                    rep.thumbnail = thumbnail.render(objs, thumb_path)
                except Exception as ex:
                    rep.warnings.append(rpt_("No thumbnail (%s)") % ex)
        folder = os.path.join(work, "godot", name)
        with open(os.path.join(folder, name + ".dasktoon.json"), "rb") as f:
            rig_data = f.read()
        with open(os.path.join(folder, name + ".glb"), "rb") as f:
            glb = f.read()
        finish = godot_finish.layers_json(context.scene)
        manifest = {
            "format": "dlive", "version": VERSION, "name": name, "generator": "DaskToon " + bpy.app.version_string,
            "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": "model.glb", "rig": "rig.json", "materials": "materials.json",
            "expressions": "expressions.json", "finish": "finish.json" if finish is not None else None,
            "thumbnail": "thumbnail.png" if rep.thumbnail else None,
            "scene": {"light_direction": list(godot.light_direction(context.scene)),
                      "ambient": list(godot.world_ambient(context.scene))},
        }
        tmp_zip = filepath + ".dttmp"
        with zipfile.ZipFile(tmp_zip, "w") as z:
            z.writestr("manifest.json", _json(manifest), zipfile.ZIP_DEFLATED)
            z.writestr("model.glb", glb, zipfile.ZIP_STORED)
            z.writestr("rig.json", rig_data, zipfile.ZIP_DEFLATED)
            z.writestr("materials.json", _json({"materials": entries}), zipfile.ZIP_DEFLATED)
            z.writestr("expressions.json", _json(rep.expressions), zipfile.ZIP_DEFLATED)
            if finish is not None:
                z.writestr("finish.json", _json(finish), zipfile.ZIP_DEFLATED)
            for rel in sorted(set(v for v in texture_map.values() if v)):
                z.write(os.path.join(work, rel.replace("/", os.sep)), rel, zipfile.ZIP_STORED)
            if rep.thumbnail:
                z.write(thumb_path, "thumbnail.png", zipfile.ZIP_STORED)
        os.replace(tmp_zip, filepath)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return rep


def import_dlive(context, filepath):
    from .importer import import_dlive as run
    return run(context, filepath)
