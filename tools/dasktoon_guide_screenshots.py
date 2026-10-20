# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the Guide tab in a real window (docs/superpowers/reports/2026-10-20-dasktoon-model-guide-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_guide_screenshots.py -- <out_dir> <lang>

<lang> is en_US or vi_VN. A DaskToon window opens for about twenty seconds and closes itself, and saves (the test
chibi, floating a little above the floor):

- 102_model_check: the 3D view with the Guide tab, Check Model pressed;
- 103_step_by_step: On the floor fixed, the Model Check closed: Step by Step with the Rigging step open.
"""
import datetime
import os
import sys
import tempfile

import bpy
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python", "ui_simulate", "modules"))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import easy_keys  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_guide_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
WORK = tempfile.mkdtemp(prefix="dt_guide_shots_")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "capture_log.txt"), "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def window():
    return bpy.context.window_manager.windows[0]


def grab():
    win = window()
    path = os.path.join(WORK, "grab.png")
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=path)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def area_shot(px, area):
    return np.ascontiguousarray(px[area.y:area.y + area.height, area.x:area.x + area.width])


def write(px, name):
    h, w = px.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    log("saved", name, (w, h))


def region(area, kind='WINDOW'):
    return next(r for r in area.regions if r.type == kind)


def steps():
    import dasktoon_guide_checks_test as gt
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    e.cursor_position_set(win.width // 2, 8, move=True)  # the status bar, away from tooltips

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    body = gt.good(reset=False)
    body.location.z = 0.3  # floating: the Model Check finds it
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    bpy.context.view_layer.objects.active = body
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    space = view.spaces.active
    space.show_region_ui = True
    yield datetime.timedelta(seconds=0.5)
    sidebar = region(view, 'UI')
    try:
        sidebar.active_panel_category = "Guide"
    except (AttributeError, TypeError) as ex:
        log("category", ex)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()
    with bpy.context.temp_override(window=win, area=view, region=sidebar):
        log("check", bpy.ops.dasktoon.guide_check())
    yield datetime.timedelta(seconds=1.5)
    write(area_shot(grab(), view), "102_model_check")

    with bpy.context.temp_override(window=win, area=view, region=sidebar):
        log("fix", bpy.ops.dasktoon.guide_fix(check="floor"))
    # Close the Model Check panel so Step by Step shows: click its header at the top of the sidebar.
    e.cursor_position_set(sidebar.x + 40, sidebar.y + sidebar.height - 14, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse.tap()
    yield datetime.timedelta(seconds=0.5)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    write(area_shot(grab(), view), "103_step_by_step")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
