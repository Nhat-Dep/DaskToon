# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of Auto Expressions and of the Accessories group in a real window
(docs/superpowers/reports/2026-10-31-dasktoon-detailed-characters-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_auto_expressions_screenshots.py -- <out_dir> [<lang>]

<lang> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself, and saves, of the test
character of tests/python/dasktoon_detailed_character_test.py:

- 110_auto_expressions: the mesh tab after Auto Expressions, blink tried.
- 111_rig_expressions: the same buttons in Anime Rig.
- 112_accessories: Anime Rig > Accessories.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_auto_expression_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
WORK = tempfile.mkdtemp(prefix="dt_auto_expression_shots_")
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


def side_by_side(a, b):
    h = min(a.shape[0], b.shape[0])
    return np.concatenate([a[-h:], np.ones((h, 8, 4), np.float32), b[-h:]], axis=1)


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


def scroll(win, area, times):
    with bpy.context.temp_override(window=win, area=area, region=region(area)):
        for _ in range(abs(times)):
            if times > 0:
                bpy.ops.view2d.scroll_down(deltax=0, deltay=200)
            else:
                bpy.ops.view2d.scroll_up(deltax=0, deltay=200)


def select(objects, active):
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def steps():
    import dasktoon_detailed_character_test as dt
    import dasktoon_expressions_eyes_test as et
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    e.cursor_position_set(win.width // 2, 8, move=True)  # the status bar, away from tooltips

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    meshes = dt.dressed(2)
    screen = win.screen
    view = max((a for a in screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    properties = next(a for a in screen.areas if a.type == 'PROPERTIES')
    first = dt.rigged(meshes)
    eyes = et.eyes_object(first, name="Circle.006")
    brows = et.eyes_object(first, name="Circle.007", pieces=et.BROW)
    meshes += [eyes, brows]
    bpy.data.objects.remove(first)
    dt.clean(meshes)
    rig = dt.rigged(meshes)
    log("parts", [(p.name, p.role) for p in rig.data.dasktoon_rig.parts])
    yield datetime.timedelta(seconds=1.0)

    select([eyes], eyes)
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("auto", bpy.ops.dasktoon.auto_expressions())
        log("try", bpy.ops.dasktoon.expression_try(slot="BLINK"))
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()
    yield datetime.timedelta(seconds=1.5)
    scroll(win, properties, -20)
    yield datetime.timedelta(seconds=0.5)
    scroll(win, properties, 2)
    yield datetime.timedelta(seconds=1.0)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "110_auto_expressions")

    select([rig], rig)
    rig.data.dasktoon_rig.issues.clear()  # the test character's spots would fill the editor
    yield datetime.timedelta(seconds=1.0)
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=1.0)
    scroll(win, properties, -40)
    yield datetime.timedelta(seconds=0.5)
    for times, name in ((5, "112_accessories"), (7, "111_rig_expressions")):
        scroll(win, properties, times)
        yield datetime.timedelta(seconds=1.0)
        px = grab()
        write(area_shot(px, properties), name)
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
