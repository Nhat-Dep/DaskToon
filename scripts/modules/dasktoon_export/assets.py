# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Exported files and their .meta. DaskToon only overwrites what it wrote itself (same GUID) and never deletes
anything (spec 4, 9)."""

import os

from bpy.app.translations import pgettext_rpt as rpt_

from . import unity_yaml


def read_meta_guid(meta_path):
    try:
        with open(meta_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("guid:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def is_ours(path, guid):
    """True when `path` is free or holds a file DaskToon wrote earlier (its .meta carries `guid`)."""
    if not os.path.exists(path) and not os.path.exists(path + ".meta"):
        return True
    return read_meta_guid(path + ".meta") == guid


def _replace(path, writer):
    # Unity ignores *.tmp files, so a half-written file is never imported.
    tmp = path + ".tmp"
    writer(tmp)
    os.replace(tmp, path)


def _write_bytes(path, data):
    def writer(tmp):
        with open(tmp, "wb") as f:
            f.write(data)
    _replace(path, writer)


def write_asset(root, relpath, guid, meta, warnings, data=None, writer=None):
    """Write <root>/<relpath> and its .meta (meta first, so a file is never left without its GUID)."""
    path = os.path.join(root, relpath)
    if not is_ours(path, guid):
        warnings.append(rpt_("Skipped %s: the file already exists and was not made by DaskToon")
                        % relpath.replace("\\", "/"))
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_bytes(path + ".meta", meta.encode("utf-8"))
    if writer is None:
        _write_bytes(path, data)
    else:
        _replace(path, writer)
    return True


def ensure_folder(root, relpath, guid):
    """Create a folder with its folder .meta; an existing .meta is left alone."""
    path = os.path.join(root, relpath)
    os.makedirs(path, exist_ok=True)
    if not os.path.exists(path + ".meta"):
        _write_bytes(path + ".meta", unity_yaml.folder_meta(guid).encode("utf-8"))
