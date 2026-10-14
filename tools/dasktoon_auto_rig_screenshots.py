# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A screenshot of the one-button auto rig and its Check panel in a real window
(docs/superpowers/reports/2026-10-14-dasktoon-auto-rig-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_auto_rig_screenshots.py -- <out_dir> <lang>     [<scroll>]

<lang> is en_US or vi_VN; <scroll> is how many steps the Properties editor scrolls down to the Check panel (7 for the
report's picture in the factory window). A DaskToon window opens for about half a minute and closes itself. It makes the regions test
character's meshes (a chibi with rabbit ears and a hair lock on its Body, a shirt, boots) with a flared skirt and a
lock of hair hanging behind the head added as meshes of their own, selects them and presses Add › Armature › Anime
Humanoid. To show every kind of spot it then moves the left wrist out of the arm and presses Check Again, and Show on
the first torn spot. It saves 70_check: the Check panel beside the 3D view.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_auto_rig_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
SCROLL = int(ARGS[2]) if len(ARGS) > 2 else 0
WORK = tempfile.mkdtemp(prefix="dt_auto_rig_shots_")
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


def scroll_down(win, area, times):
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
    from dasktoon_rig import skeleton
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    old, objs, _parts = rt.character(reset=False)
    bpy.data.objects.remove(old)
    skirt = rt.merged("Circle.007", [rt.st.tube((0, 0, 0.92), (0, 0, 0.62), 0.22)])
    for v in skirt.data.vertices:  # wider at the hem
        if v.co.z < 0.8:
            v.co.x *= 1.4
            v.co.y *= 1.4
    hair = rt.merged("Circle.008", [rt.st.tube((0, 0.32, 1.95), (0, 0.36, 1.2), 0.05)])
    meshes = list(objs.values()) + [skirt, hair]
    bpy.context.view_layer.update()  # the removed skeleton leaves the view layer's list
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in meshes)
    bpy.context.view_layer.objects.active = objs["Body"]
    log("add", bpy.ops.dasktoon.rig_add_humanoid())
    rig = bpy.context.view_layer.objects.active
    data = rig.data.dasktoon_rig
    log("found", [(item.kind, item.bone, item.part, item.pose, item.region, item.role) for item in data.issues])
    rig.data.use_mirror_x = False
    with skeleton.editing(bpy.context, rig) as edit:  # a joint placed by hand outside the arm
        edit["LeftHand"].head.x += 0.2
        edit["LeftHand"].tail.x += 0.2
    log("check", bpy.ops.dasktoon.rig_check())
    index = next(i for i, item in enumerate(data.issues) if item.kind == 'STRETCH')
    log("show", bpy.ops.dasktoon.rig_show_spot(index=index))
    log("listed", [(item.kind, item.bone, item.part, item.pose, item.region, item.role) for item in data.issues])

    view = max((a for a in window().screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    view.spaces.active.overlay.show_bones = False
    front_view(window(), view, meshes)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig
    properties = next(a for a in window().screen.areas if a.type == 'PROPERTIES')
    log("properties tab", properties.spaces.active.context)
    yield datetime.timedelta(seconds=1.5)  # drawn once, so the panel knows how tall it is
    if SCROLL:
        scroll_down(window(), properties, SCROLL)
    yield datetime.timedelta(seconds=1.5)
    write(side_by_side(area_shot(properties), area_shot(view)), "70_check")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
