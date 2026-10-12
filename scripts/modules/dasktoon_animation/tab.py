# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Animation tab replaces Blender's when a file opens (Animation tab spec 6). The tab lives in a template
.blend that tools/dasktoon_build_animation_tab.py builds from Blender's own tab; it carries a version, so a newer
DaskToon replaces an older DaskToon tab once, and a tab the user resized is left alone."""

import os

import bpy

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "startup",
                        "bl_ui", "dasktoon_animation.blend")
NAME = "Animation"
MARK = "dasktoon_animation_template"
VERSION = 1


def ensure_animation_tab():
    """Replace the file's Animation tab by DaskToon's when it is Blender's or an older DaskToon one; a file without an
    Animation tab keeps it that way. True when the tab was replaced."""
    old = bpy.data.workspaces.get(NAME)
    if old is None or old.get(MARK, 0) >= VERSION or not os.path.isfile(TEMPLATE):
        return False
    with bpy.data.libraries.load(TEMPLATE, link=False) as (_src, dst):
        dst.workspaces = [NAME]
    new = dst.workspaces[0]
    new.use_fake_user = False
    bpy.data.workspaces.replace(old, new)
    return True


def show_render_in_camera_view():
    """Blender opens every 3D Viewport in Solid when it reads a file (render can be heavy); the camera view of
    DaskToon's tab goes back to Rendered, as it was made to show the anime look (spec 3). Other shading the user chose
    there stays."""
    workspace = bpy.data.workspaces.get(NAME)
    if workspace is None or workspace.get(MARK) is None:
        return
    for screen in workspace.screens:
        for area in screen.areas:
            space = area.spaces.active
            if area.type != 'VIEW_3D' or space.region_3d.view_perspective != 'CAMERA':
                continue
            if space.shading.type == 'SOLID':
                space.shading.type = 'RENDERED'
