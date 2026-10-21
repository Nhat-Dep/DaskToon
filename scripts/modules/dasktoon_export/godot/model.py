# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The model for Godot as binary glTF, and the import settings that make Godot run DaskToon's import script on it
(Godot spec 3). Modifiers are not applied, so shape keys survive and the Geometry Nodes outline hull stays out of the
file; Godot draws the outline in the shader from DT_OutlineN/W."""

import json
import os
import re
import shutil

import bpy

from . import files

GLTF_SETTINGS = dict(
    export_format='GLB',
    use_selection=True,
    export_apply=False,
    export_yup=True,
    export_texcoords=True,
    export_tangents=True,         # the outline reads DT_OutlineN in the tangent frame
    export_materials='EXPORT',    # for their names: the import script puts the DaskToon materials on them by name
    export_image_format='NONE',   # the textures go beside the materials, not into the model
    export_vertex_color='NONE',   # DaskToon's region layers are for painting in DaskToon
    export_skins=True,
    export_def_bones=True,
    export_morph=True,
    export_anim_slide_to_zero=True,  # a clip starts at 0 s in Godot, whatever frame it starts on in DaskToon
)
IMPORT_TEMPLATE = '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\n%s\n'
SCRIPT_LINE = 'import_script/path="%s"' % files.IMPORT_SCRIPT


def write_glb(context, objects, filepath, include_animation, animation_mode='ACTIVE_ACTIONS', morph_normals=True):
    """Export `objects` to `filepath`; the user's selection and active object are restored. Returns the names of
    objects left out because they cannot be selected (e.g. in an excluded collection). The file is written in a
    folder Godot skips (.gdignore) and moved into place, so the editor never imports half a file. `animation_mode`:
    NLA_TRACKS for clips (clips.baked), ACTIVE_ACTIONS for the animation playing now. `morph_normals` False keeps
    shape keys from changing normals (face shading writes the face's normals, face spec 6)."""
    view_layer = context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    left_out = []
    scratch = os.path.join(os.path.dirname(filepath), ".dasktoon_export")
    os.makedirs(scratch, exist_ok=True)
    open(os.path.join(scratch, ".gdignore"), "w").close()
    try:
        for obj in selected:
            obj.select_set(False)
        for obj in objects:
            try:
                obj.select_set(True)
            except RuntimeError:
                left_out.append(obj.name)
        tmp = os.path.join(scratch, os.path.basename(filepath))
        bpy.ops.export_scene.gltf(filepath=tmp, export_animations=include_animation,
                                  export_animation_mode=animation_mode, export_morph_normal=morph_normals,
                                  **GLTF_SETTINGS)
        os.replace(tmp, filepath)
        return left_out
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        for obj in view_layer.objects:
            try:
                obj.select_set(obj in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active


def _set_param(text, line):
    """`text` with the [params] line of the same name set to `line`."""
    name = line.split("=", 1)[0]
    pattern = r"^%s=.*$" % re.escape(name)
    if re.search(pattern, text, re.M):
        return re.sub(pattern, lambda _m: line, text, count=1, flags=re.M)
    if re.search(r"^\[params\]\s*$", text, re.M):
        return re.sub(r"^\[params\]\s*$", lambda _m: "[params]\n\n" + line, text, count=1, flags=re.M)
    return text.rstrip("\n") + "\n\n[params]\n\n" + line + "\n"


_SUBRESOURCES = re.compile(r"^_subresources=(.*?)(?=^[A-Za-z_][\w/]*=|\Z)", re.M | re.S)


PLAYER = "PATH:AnimationPlayer"  # the AnimationPlayer the glTF import makes, in Godot's per-node import settings


def _unoptimized(text):
    """`text` with the optimizer of the model's AnimationPlayer off (it drops keys whose change keeps its direction,
    such as a mouth cell going 1, 3, 4), or None when the per-node settings hold more than plain values and cannot be
    read."""
    found = _SUBRESOURCES.search(text)
    try:
        data = json.loads(found.group(1).strip()) if found else {}
    except ValueError:
        return None
    data.setdefault("nodes", {}).setdefault(PLAYER, {})["optimizer/enabled"] = False
    line = "_subresources=%s" % json.dumps(data, ensure_ascii=False)
    if found:
        return text[:found.start()] + line + "\n" + text[found.end():]
    return _set_param(text, line)


def import_settings(existing, fps, animated=False):
    """(The .glb.import text, True when the animation optimizer could be turned off): Godot's own settings (its uid, the
    user's choices) kept, the import script set, the animations read at the scene's frame rate (Godot resamples them at
    this rate: anime timing must land on frames) and kept as they are."""
    text = existing or IMPORT_TEMPLATE % SCRIPT_LINE
    text = _set_param(text, SCRIPT_LINE)
    text = _set_param(text, "animation/fps=%s" % ("%g" % round(fps, 3)))
    if not animated:
        return text, True
    unoptimized = _unoptimized(text)
    return (text, False) if unoptimized is None else (unoptimized, True)


def write_import_settings(path, fps, animated=False):
    """Returns False when the animation optimizer could not be turned off."""
    try:
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    except OSError:
        existing = ""
    text, ok = import_settings(existing, fps, animated)
    files.write_bytes(path, text.encode("utf-8"))
    return ok
