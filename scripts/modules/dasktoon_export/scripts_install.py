# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Install DaskToon's Unity scripts for the anime rig (spring bones, colliders, the importer that reads
<Model>.rig.json) into an export root, as the shaders are: fixed GUIDs and a version file, so a project is only
rewritten by a newer DaskToon (anime rig spec 9.5)."""

import os

from . import assets, shaders_install, unity_yaml

SCRIPTS_VERSION = 1
SCRIPT_DIR = "Scripts"
VERSION_FILE = "DaskToonScripts.version"
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unity_scripts")
FOLDER_GUIDS = {"Scripts": "fc047532de7a491c96575985da296e3a", "Scripts/Editor": "b072af31e2654fc280b1fc5df8af8cf2"}
VERSION_GUID = "aa275e64a29745889c3af2e20285b967"
FILE_GUIDS = {
    "DaskToonSpringBone.cs": "447db0cdbda2403dbb15e084f25149cf",
    "DaskToonSpringCollider.cs": "f611202d6bd34f7fb27569a468d4789b",
    "Editor/DaskToonRigImporter.cs": "5e0acb864e5c435983c70bd57f042a01",
}


def installed_version(root):
    try:
        with open(os.path.join(root, SCRIPT_DIR, VERSION_FILE), encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def install_scripts(target, warnings, force=False):
    """Write the scripts with their fixed GUIDs, then the version file. PROJECT mode skips an install of this version
    or newer unless `force`. Returns True when the scripts were written."""
    if target.mode == 'PROJECT' and not force and installed_version(target.root) >= SCRIPTS_VERSION:
        return False
    shaders_install.ensure_root(target)
    for rel in sorted(FOLDER_GUIDS):
        parent, name = os.path.split(rel)
        assets.ensure_folder(os.path.join(target.root, parent) if parent else target.root, name, FOLDER_GUIDS[rel])
    for rel, guid in sorted(FILE_GUIDS.items()):
        with open(os.path.join(SOURCE_DIR, *rel.split("/")), "rb") as f:
            data = f.read()
        assets.write_asset(target.root, SCRIPT_DIR + "/" + rel, guid, unity_yaml.script_meta(guid), warnings,
                           data=data)
    assets.write_asset(target.root, SCRIPT_DIR + "/" + VERSION_FILE, VERSION_GUID, unity_yaml.default_meta(VERSION_GUID),
                       warnings, data=b"%d\n" % SCRIPTS_VERSION)
    return True
