# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of Anime Unwrap in a real window (docs/superpowers/reports/2026-10-20-dasktoon-anime-unwrap-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_uv_screenshots.py -- <out_dir> <lang>

A DaskToon window opens for about twenty seconds and closes itself, and saves (the rigged regions chibi):

- 120_uv_menu: Edit Mode's UV menu with Anime Unwrap;
- 121_anime_unwrap: after Anime Unwrap, the UV Editor (all faces) beside the 3D view with the seams.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_uv_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
WORK = tempfile.mkdtemp(prefix="dt_uv_shots_")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "capture_log.txt"), "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def grab(win):
    path = os.path.join(WORK, "grab.png")
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=path)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


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
    import dasktoon_rig_regions_test as rt
    win = bpy.context.window_manager.windows[0]
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    rig, objs = rt.rigged(reset=False)
    body = objs["Body"]
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in (objs["Body"], objs["Shirt"], objs["Boots"]))
    bpy.context.view_layer.objects.active = body
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='BACK')
        bpy.ops.view3d.view_selected()
        bpy.ops.object.mode_set(mode='EDIT')
    yield datetime.timedelta(seconds=1.0)
    reg = region(view)
    e.cursor_position_set(reg.x + reg.width // 2, reg.y + reg.height // 2, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.u.tap()  # the UV menu
    yield datetime.timedelta(seconds=1.0)
    write(grab(win), "120_uv_menu")
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        log("unwrap", bpy.ops.dasktoon.uv_unwrap_anime())
        bpy.ops.mesh.select_all(action='SELECT')
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    yield datetime.timedelta(seconds=0.5)
    # The UV Editor on the left half of the 3D view.
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
    yield datetime.timedelta(seconds=0.5)
    left = min((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.x)
    left.ui_type = 'UV'
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=left, region=region(left)):
        bpy.ops.image.view_all(fit_view=True)
    yield datetime.timedelta(seconds=1.5)
    write(grab(win), "121_anime_unwrap")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    import traceback
    log("ERROR", traceback.format_exc())
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
