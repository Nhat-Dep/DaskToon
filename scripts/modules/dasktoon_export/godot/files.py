# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The files every Godot export shares (shaders, import script) and how the Godot export writes files (Godot spec 2,
4). Everything goes under res://DaskToon, which is DaskToon's own: files there are overwritten."""

import os

SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
RES_ROOT = "res://DaskToon"
SHADERS = "Shaders"
IMPORT_SCRIPT = RES_ROOT + "/Scripts/dasktoon_import.gd"
VERSION = 1
VERSION_FILE = SHADERS + "/dasktoon_shaders.version"
ALPHA_SUFFIX = {'OPAQUE': "", 'CLIP': "_clip", 'BLEND': "_blend"}
ALPHA_DEFINE = {'CLIP': "DT_ALPHA_CLIP", 'BLEND': "DT_ALPHA_BLEND"}
# Base shader -> (render modes, culling modes it comes in, alpha modes it comes in). The outline is a hull drawn from
# inside, so it always culls its front faces.
VARIANTS = {
    "anime_bsdf": (("ambient_light_disabled",), ("cull_disabled", "cull_back"), ('OPAQUE', 'CLIP', 'BLEND')),
    "anime_outline": (("ambient_light_disabled", "world_vertex_coords"), ("cull_front",), ('OPAQUE', 'CLIP')),
}


def res(rel):
    return RES_ROOT + "/" + rel.replace("\\", "/")


def write_bytes(path, data):
    """Write through a temporary file Godot does not import, so the editor never reads half a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".dttmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def write_if_changed(path, data):
    """True when the file was written (it was missing or different)."""
    try:
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    except OSError:
        pass
    write_bytes(path, data)
    return True


def shader_file(base, cull_back=False, alpha='OPAQUE'):
    """File name of a shader variant: anime_bsdf[_cull][_clip|_blend].gdshader."""
    return base + ("_cull" if cull_back else "") + ALPHA_SUFFIX[alpha] + ".gdshader"


def variant_text(base, cull, alpha):
    modes, _culls, _alphas = VARIANTS[base]
    lines = ["// Written by DaskToon Engine Export: %s.gdshaderinc with %s and %s alpha." % (base, cull, alpha.lower()),
             "shader_type spatial;",
             "render_mode %s;" % ", ".join((cull,) + modes)]
    if alpha in ALPHA_DEFINE:
        lines.append("#define " + ALPHA_DEFINE[alpha])
    lines.append('#include "%s/%s/%s.gdshaderinc"' % (RES_ROOT, SHADERS, base))
    return "\n".join(lines) + "\n"


def _variants():
    for base, (_modes, culls, alphas) in VARIANTS.items():
        for cull in culls:
            for alpha in alphas:
                yield SHADERS + "/" + shader_file(base, cull == "cull_back", alpha), variant_text(base, cull, alpha)


def installed_version(root):
    try:
        with open(os.path.join(root, VERSION_FILE), encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def install(root, force=False):
    """The shaders, their variants and the import script under `root` (res://DaskToon). A project holding a newer
    version is left alone unless `force`. Returns True when a file was written."""
    if not force and installed_version(root) > VERSION:
        return False
    written = False
    for base, _dirs, names in os.walk(SOURCE_DIR):
        for name in names:
            source = os.path.join(base, name)
            with open(source, "rb") as f:
                data = f.read()
            written |= write_if_changed(os.path.join(root, os.path.relpath(source, SOURCE_DIR)), data)
    for rel, text in _variants():
        written |= write_if_changed(os.path.join(root, rel), text.encode("utf-8"))
    written |= write_if_changed(os.path.join(root, VERSION_FILE), b"%d\n" % VERSION)
    return written
