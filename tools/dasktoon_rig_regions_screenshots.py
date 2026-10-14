# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the anime rig's body regions and locks in a real window
(docs/superpowers/reports/2026-10-14-dasktoon-rig-regions-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_rig_regions_screenshots.py -- <out_dir> <lang>

<lang> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself. It builds the regions test
character (a chibi whose rabbit ears and a hair lock are loose pieces of the Body, a shirt with a strap, boots), presses
Recognize, then saves:

- 60_regions_panel: Properties › Object Data of the rig: the Parts list with the locks and the Regions panel;
- 61_show_regions: the character in Show Regions, from the front;
- 62_highlight: the lock of the left ear chosen in the list, lit up in the 3D view;
- 63_paint_regions: painting the left arm in Vertex Paint: the mesh's Anime Rig panel with a button per region, and the
  3D view.
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
import dasktoon_rig_regions_test as rt  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_rig_regions_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
WORK = tempfile.mkdtemp(prefix="dt_rig_regions_shots_")
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


def crop(px, x0, y0, x1, y1):
    h, w = px.shape[:2]
    return np.ascontiguousarray(px[max(0, y0):min(h, y1), max(0, x0):min(w, x1)])


def write(px, name):
    h, w = px.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    log("saved", name, (w, h))


def area_shot(area):
    return crop(grab(), area.x, area.y, area.x + area.width, area.y + area.height)


def side_by_side(a, b):
    h = min(a.shape[0], b.shape[0])
    gap = np.ones((h, 8, 4), np.float32)
    return np.concatenate([a[-h:], gap, b[-h:]], axis=1)


def scroll_down(win, area, times=40):
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=area, region=region):
        for _ in range(times):
            bpy.ops.view2d.scroll_down(deltax=0, deltay=200)


def front_view(win, view, objects):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    with bpy.context.temp_override(window=win, area=view, region=next(r for r in view.regions if r.type == 'WINDOW')):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()


def steps():
    from bl_ui import dasktoon_rig as ui
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    rig, objs = rt.rigged(reset=False)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.dasktoon.rig_recognize()
    data = rig.data.dasktoon_rig
    log("locks", [part.name for part in data.parts if part.made_by_recognize])

    # 60: the rig's Object Data, the whole area, scrolled down to the Anime Rig panel.
    properties = next(a for a in win.screen.areas if a.type == 'PROPERTIES')
    properties.spaces.active.context = 'DATA'
    with bpy.context.temp_override(window=win, area=properties):
        bpy.ops.screen.screen_full_area()
    yield datetime.timedelta(seconds=1.0)
    full = next(a for a in window().screen.areas if a.type == 'PROPERTIES')
    scroll_down(window(), full)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    write(area_shot(full), "60_regions_panel")
    with bpy.context.temp_override(window=window(), area=full):
        bpy.ops.screen.back_to_previous()
    yield datetime.timedelta(seconds=1.0)

    # 61: Show Regions, from the front.
    view = max((a for a in window().screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    view.spaces.active.overlay.show_bones = False
    front_view(window(), view, list(objs.values()))
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig
    bpy.context.window_manager.dasktoon_show_regions = True
    yield datetime.timedelta(seconds=1.5)
    write(area_shot(view), "61_show_regions")
    bpy.context.window_manager.dasktoon_show_regions = False

    # 62: the left ear's lock chosen in the list: lit up.
    data.active_part_index = next(i for i, part in enumerate(data.parts) if part.name == "Lock L1")
    view.spaces.active.shading.type = 'SOLID'
    yield datetime.timedelta(seconds=1.5)
    write(area_shot(view), "62_highlight")

    # 63: painting the left arm: the mesh's Anime Rig panel (opened for the picture) and the 3D view.
    panel = ui.DATA_PT_dasktoon_rig_mesh
    bpy.utils.unregister_class(panel)
    panel.bl_options = set()
    bpy.utils.register_class(panel)
    bpy.ops.dasktoon.rig_paint_regions(region='ARM_L')
    properties = next(a for a in window().screen.areas if a.type == 'PROPERTIES')
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=1.0)
    scroll_down(window(), properties)
    yield datetime.timedelta(seconds=1.0)
    write(side_by_side(area_shot(properties), area_shot(view)), "63_paint_regions")
    bpy.ops.dasktoon.rig_paint_done()
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
