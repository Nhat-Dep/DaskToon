# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon Engine - Automatic Startup Initialization
Initializes Color Management defaults and registers Anime shader nodes cleanly on startup.
"""

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
    import bl_ui.dasktoon_anime_nodes as anime_nodes
    anime_nodes.register()

    try:
        import goo_engine_light_groups
        goo_engine_light_groups.register()
    except Exception:
        pass

    dasktoon_enforce_color_management()


def unregister():
    try:
        import goo_engine_light_groups
        goo_engine_light_groups.unregister()
    except Exception:
        pass

    import bl_ui.dasktoon_anime_nodes as anime_nodes
    anime_nodes.unregister()


if __name__ == "__main__":
    register()
