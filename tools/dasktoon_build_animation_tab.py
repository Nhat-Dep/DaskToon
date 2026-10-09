# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build scripts/startup/bl_ui/dasktoon_animation.blend, DaskToon's Animation tab
(docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md, section 3), from Blender's own Animation tab.

DaskToon.exe --factory-startup --python tools/dasktoon_build_animation_tab.py [-- <out.blend>]

A DaskToon window opens for a few seconds (closing an area needs one) and closes itself. The tab keeps Blender's camera
view, main viewport, Dope Sheet and Properties; the Outliner goes, so Properties takes the right column; the camera view
shows Rendered, the main viewport its toolbar, Properties the Object Data tab, the Dope Sheet Whole Character. The areas
are printed so a rebuild can be compared."""

import os
import sys

import bpy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(REPO, "scripts", "startup", "bl_ui",
                                                         "dasktoon_animation.blend")


def blender_tab():
    """Blender's own Animation tab: the factory settings read again without DaskToon's replacement."""
    from bl_ui import dasktoon_animation as ui
    if ui.load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(ui.load_post)
    bpy.ops.wm.read_factory_settings()
    return 0.5


def show_tab():
    window = bpy.context.window_manager.windows[0]
    window.workspace = bpy.data.workspaces["Animation"]
    return 0.5


def build():
    from dasktoon_animation import tab
    window = bpy.context.window_manager.windows[0]
    workspace = bpy.data.workspaces["Animation"]
    screen = window.screen
    assert workspace.screens[0] == screen, "the window does not show the Animation tab"
    outliner = next(area for area in screen.areas if area.type == 'OUTLINER')
    with bpy.context.temp_override(window=window, screen=screen, area=outliner):
        bpy.ops.screen.area_close()
    views = sorted((area for area in screen.areas if area.type == 'VIEW_3D'), key=lambda area: area.x)
    camera, main = views[0].spaces.active, views[1].spaces.active
    assert camera.region_3d.view_perspective == 'CAMERA'
    # Showing or hiding a region updates the area, which needs the window in the context (a timer has none).
    with bpy.context.temp_override(window=window, screen=screen):
        camera.shading.type = 'RENDERED'
        camera.show_region_toolbar = False
        camera.show_gizmo = False
        main.show_region_toolbar = True
        properties = next(area for area in screen.areas if area.type == 'PROPERTIES').spaces.active
        properties.context = 'DATA'
        dopesheet = next(area for area in screen.areas if area.type == 'DOPESHEET_EDITOR').spaces.active
        dopesheet.mode = 'DOPESHEET'
        dopesheet.show_region_footer = True
        dopesheet.dopesheet.show_whole_character = True
    workspace[tab.MARK] = tab.VERSION
    return 1.0  # the areas get their new sizes when the window redraws


def write():
    workspace = bpy.data.workspaces["Animation"]
    screen = workspace.screens[0]
    bpy.data.libraries.write(OUT, {workspace}, fake_user=True)
    for area in screen.areas:
        print("area", area.type, area.x, area.y, area.width, area.height)
    print("wrote", OUT)
    bpy.ops.wm.quit_blender()


def steps():
    yield blender_tab
    yield show_tab
    yield build
    yield write


_steps = steps()


def tick():
    step = next(_steps, None)
    if step is None:
        return None
    try:
        delay = step()
    except Exception:
        import traceback
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None
    return delay if delay is not None else 0.5


bpy.app.timers.register(tick, first_interval=2.0, persistent=True)  # reading the factory settings keeps it
