# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Copy the images a model uses from outside its project into <project>/Textures/ before a person saves
(docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 10). Saves made by scripts and auto-save
do not call this."""

import filecmp
import os
import shutil
from dataclasses import dataclass, field

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

from . import project as dtp

TILE_TOKENS = ("<UDIM>", "<UVTILE>")
COPIED_SOURCES = {'FILE', 'MOVIE', 'TILED'}


@dataclass
class Collected:
    copied: int = 0                               # images whose files were copied into Textures/
    images: list = field(default_factory=list)    # images that now point into Textures/
    warnings: list = field(default_factory=list)  # one translated line each

    def summary(self):
        if self.copied == 1:
            return rpt_("Copied 1 texture into Textures/")
        if self.copied:
            return rpt_("Copied %d textures into Textures/") % self.copied
        return ""


def _tile_path(pattern, token, number):
    if token == "<UDIM>":
        return pattern.replace(token, str(number))
    return pattern.replace(token, "u%d_v%d" % ((number - 1001) % 10 + 1, (number - 1001) // 10 + 1))


def suffixed(name, number, token):
    """`name` with _<number> before its extension, or before the tile token (skin.<UDIM>.png gives skin_1.<UDIM>.png)."""
    if number == 0:
        return name
    if token:
        head, _token, tail = name.partition(token)
        stem = head.rstrip("._-")
        return "%s_%d%s%s%s" % (stem, number, head[len(stem):], token, tail)
    stem, extension = os.path.splitext(name)
    return "%s_%d%s" % (stem, number, extension)


def _place(folder, name, sources, token):
    """(destination path or tile pattern, [(source, destination)] still to copy): the first name in `folder` whose files
    are missing or identical to `sources`, trying name, name_1, name_2…"""
    number = 0
    while True:
        target = os.path.join(folder, suffixed(name, number, token))
        pending, clash = [], False
        for tile, source in sources:
            destination = target if token is None else _tile_path(target, token, tile)
            if not os.path.exists(destination):
                pending.append((source, destination))
            elif not os.path.isfile(destination) or not filecmp.cmp(source, destination, shallow=False):
                clash = True
                break
        if not clash:
            return target, pending
        number += 1


def _blend_path(path):
    """`path` as the open .blend file should store it: relative ("//...") when the file is saved and a relative path
    exists, absolute otherwise. Saving into another folder then rebases the relative path (Blender's relative remap)."""
    if bpy.data.filepath:
        try:
            return "//" + os.path.relpath(path, os.path.dirname(bpy.data.filepath)).replace(os.sep, "/")
        except ValueError:  # another drive
            pass
    return path


def collect(project, images=None):
    """Copy into the project's Textures/ the files of the images that live outside `project`, and point the images at
    the copies through filepath_raw (no reload, so paint not saved yet stays). Packed, generated and linked images and
    images already in the project are left alone; image sequences and missing files only get a warning."""
    result = Collected()
    for image in bpy.data.images if images is None else images:
        if image.users == 0 or image.library is not None or image.packed_file is not None:
            continue
        if image.source not in COPIED_SOURCES | {'SEQUENCE'} or not image.filepath_raw:
            continue
        path = os.path.normpath(bpy.path.abspath(image.filepath_raw))
        if dtp.is_inside(path, project.folder):
            continue
        if image.source == 'SEQUENCE':
            result.warnings.append(rpt_("%s: image sequences are not copied into the project") % image.name)
            continue
        token = next((t for t in TILE_TOKENS if t in path), None) if image.source == 'TILED' else None
        if token is None:
            sources = [(None, path)]
        else:
            sources = [(tile.number, _tile_path(path, token, tile.number)) for tile in image.tiles]
        missing = [source for _tile, source in sources if not os.path.isfile(source)]
        if missing:
            result.warnings.append(rpt_("%s: file not found: %s") % (image.name, missing[0]))
            continue
        os.makedirs(project.textures_folder, exist_ok=True)
        target, pending = _place(project.textures_folder, os.path.basename(path), sources, token)
        for source, destination in pending:
            shutil.copy2(source, destination)
        if pending:
            result.copied += 1
        image.filepath_raw = _blend_path(target)
        result.images.append(image)
    return result


def relink_absolute(images):
    """After the open file was saved under a new path: make relative the copied images whose path stayed absolute
    (the file used to be on another drive). Returns how many changed; the caller saves again when there are any."""
    changed = 0
    for image in images:
        if image.filepath_raw.startswith("//"):
            continue
        relative = _blend_path(image.filepath_raw)
        if relative != image.filepath_raw:
            image.filepath_raw = relative
            changed += 1
    return changed


def unsaved_images():
    """Names of images with paint changes that saving the .blend file does not keep (workflow spec 12)."""
    return sorted(image.name for image in bpy.data.images if image.users and image.is_dirty)
