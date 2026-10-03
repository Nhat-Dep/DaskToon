# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Install the DaskToon Unity shaders into an export root: fixed GUIDs, so every export points at the same shader
assets, and a version file, so a project is only rewritten by a newer DaskToon (spec 4)."""

import os

from . import assets, unity_yaml

SHADER_VERSION = 1
SHADER_DIR = "Shaders"
VERSION_FILE = "DaskToonShaders.version"
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unity_urp")
SHADER_NAMES = ("AnimeBSDF", "AnimeCel", "AnimeEye", "DaskCel")
SHADERS_FOLDER_GUID = "44377c95f9c3c9c9d028aff6a66c6477"
ROOT_FOLDER_GUID = "3694ef82df330a6381e838d2da364f48"  # Assets/DaskToon in PROJECT mode
VERSION_GUID = "d5a71714275166c4ace3f09ff18fa067"
FILE_GUIDS = {
    "DaskToonCore.hlsl": "712e19c1031f534b059dd5ae3c069025",
    "DaskToonURP.hlsl": "f86e64c85feac9699df227c399051118",
    "DaskToonOutline.hlsl": "76ca2d70894695203cf8567f47ecafed",
    "AnimeBSDF.shader": "651389b857c37954216341111b253e67",
    "AnimeCel.shader": "ef4936d27bf797490dd8a472a561f02e",
    "AnimeEye.shader": "970c613c54e57029168ffc98ac73c832",
    "DaskCel.shader": "050189cde98f1c513deb3503682f01a1",
}


def shader_guid(shader):
    return FILE_GUIDS[shader + ".shader"]


def installed_version(root):
    try:
        with open(os.path.join(root, SHADER_DIR, VERSION_FILE), encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def _meta_for(file_name, guid):
    if file_name.endswith(".shader"):
        return unity_yaml.shader_meta(guid)
    if file_name.endswith(".hlsl"):
        return unity_yaml.include_meta(guid)
    return unity_yaml.default_meta(guid)


def ensure_root(target):
    """The export root; in PROJECT mode also the .meta of Assets/DaskToon."""
    if target.mode == 'PROJECT':
        assets.ensure_folder(os.path.dirname(target.root), os.path.basename(target.root), ROOT_FOLDER_GUID)
    else:
        os.makedirs(target.root, exist_ok=True)


def install_shaders(target, warnings, force=False):
    """Write the shader sources with their fixed GUIDs, then the version file. PROJECT mode skips an install of
    this version or newer unless `force`. Returns True when the shaders were written."""
    if target.mode == 'PROJECT' and not force and installed_version(target.root) >= SHADER_VERSION:
        return False
    ensure_root(target)
    assets.ensure_folder(target.root, SHADER_DIR, SHADERS_FOLDER_GUID)
    for file_name, guid in sorted(FILE_GUIDS.items()):
        with open(os.path.join(SOURCE_DIR, file_name), "rb") as f:
            data = f.read()
        assets.write_asset(target.root, SHADER_DIR + "/" + file_name, guid, _meta_for(file_name, guid), warnings,
                           data=data)
    assets.write_asset(target.root, SHADER_DIR + "/" + VERSION_FILE, VERSION_GUID,
                       unity_yaml.default_meta(VERSION_GUID), warnings, data=b"%d\n" % SHADER_VERSION)
    return True
