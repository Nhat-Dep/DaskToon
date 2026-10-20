# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The model for Godot as binary glTF, and the import settings that make Godot run DaskToon's import script on it
(Godot spec 3). Modifiers are not applied, so shape keys survive and the Geometry Nodes outline hull stays out of the
file; Godot draws the outline in the shader from DT_OutlineN/W."""

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
    export_morph_normal=True,
)
IMPORT_TEMPLATE = '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\n%s\n'
SCRIPT_LINE = 'import_script/path="%s"' % files.IMPORT_SCRIPT


def write_glb(context, objects, filepath, include_animation):
    """Export `objects` to `filepath`; the user's selection and active object are restored. Returns the names of
    objects left out because they cannot be selected (e.g. in an excluded collection). The file is written in a
    folder Godot skips (.gdignore) and moved into place, so the editor never imports half a file."""
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
        bpy.ops.export_scene.gltf(filepath=tmp, export_animations=include_animation, **GLTF_SETTINGS)
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


def import_settings(existing):
    """The .glb.import text: Godot's own settings (its uid, the user's choices) kept, the import script set."""
    if not existing:
        return IMPORT_TEMPLATE % SCRIPT_LINE
    if re.search(r"^import_script/path=.*$", existing, re.M):
        return re.sub(r"^import_script/path=.*$", SCRIPT_LINE.replace("\\", "\\\\"), existing, count=1, flags=re.M)
    if re.search(r"^\[params\]\s*$", existing, re.M):
        return re.sub(r"^\[params\]\s*$", "[params]\n\n" + SCRIPT_LINE, existing, count=1, flags=re.M)
    return existing.rstrip("\n") + "\n\n[params]\n\n" + SCRIPT_LINE + "\n"


def write_import_settings(path):
    try:
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    except OSError:
        existing = ""
    files.write_bytes(path, import_settings(existing).encode("utf-8"))
