# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon start-up: the colour management DaskToon's shading is tuned for (Standard view, no look)."""

import bpy


def dasktoon_enforce_color_management(scene=None):
    if scene is None:
        scene = getattr(bpy.context, "scene", None)
    if scene and hasattr(scene, "view_settings"):
        try:
            if scene.view_settings.view_transform != 'Standard':
                scene.view_settings.view_transform = 'Standard'
            if scene.view_settings.look != 'None':
                scene.view_settings.look = 'None'
        except Exception:
            pass


def register():
    dasktoon_enforce_color_management()


def unregister():
    pass
