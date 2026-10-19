# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the automatic shape keys in a real window
(docs/superpowers/reports/2026-10-20-dasktoon-auto-shape-keys-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_auto_shape_keys_screenshots.py -- <out_dir> <lang>

<lang> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself, and saves:

- 100_bend_fixes_a, _b: the test chibi built, its left knee and hip bent: Anime Rig > Joints with Bend Fixes (two
  scroll positions), the knee's fix shown by its driver in the 3D view;
- 101_expression_sets: eye pieces in front of the chibi's head, Sculpt Eye Expressions pressed: Shape Keys and
  Expression Sets with Fill Empty Expressions and Sculpt Eye Expressions, joy shown in the 3D view.
"""
import datetime
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Matrix

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python", "ui_simulate", "modules"))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import easy_keys  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_shape_key_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
WORK = tempfile.mkdtemp(prefix="dt_shape_key_shots_")
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


def areas():
    screen = window().screen
    view = max((a for a in screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    properties = next(a for a in screen.areas if a.type == 'PROPERTIES')
    return view, properties


def select(objects, active):
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def look(win, view, objects, axis):
    select(objects, objects[0])
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type=axis)
        bpy.ops.view3d.view_selected()


def turn(rig, name, axis, angle):
    frame = rig.data.bones[name].matrix_local.to_3x3()
    pose_bone = rig.pose.bones[name]
    pose_bone.rotation_mode = 'QUATERNION'
    pose_bone.rotation_quaternion = (frame.inverted() @ Matrix.Rotation(angle, 3, axis) @ frame).to_quaternion()


def steps():
    import dasktoon_rig_regions_test as rt
    import dasktoon_expressions_eyes_test as et
    from dasktoon_rig import correctives
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    e.cursor_position_set(win.width // 2, 8, move=True)  # the status bar, away from tooltips

    # 100. The chibi built; its left knee and hip bent; Anime Rig > Joints with Bend Fixes.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    rig, objs = rt.rigged(reset=False)
    view, properties = areas()
    select([rig], rig)
    yield datetime.timedelta(seconds=0.5)
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("build", bpy.ops.dasktoon.rig_build())
    fixes = {fix.name: fix for fix in correctives.fixes(rig)}
    log("fixes", sorted(fixes), "keys", [b.name for b in objs["Body"].data.shape_keys.key_blocks])
    turn(rig, "LeftLowerLeg", fixes["LeftKnee"].axis, fixes["LeftKnee"].angle)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    shown = objs["Body"].evaluated_get(depsgraph).data.shape_keys.key_blocks["DT_Fix_LeftKnee"].value
    log("knee fix value", round(shown, 3))
    look(win, view, [objs["Body"]], 'RIGHT')
    select([rig], rig)
    yield datetime.timedelta(seconds=1.5)
    for name, times in (("100_bend_fixes_a", 4), ("100_bend_fixes_b", 4)):
        scroll(win, properties, times)
        yield datetime.timedelta(seconds=1.0)
        px = grab()
        write(side_by_side(area_shot(px, properties), area_shot(px, view)), name)

    # 101. Eye pieces in front of the head; Sculpt Eye Expressions; Expression Sets.
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    eyes = et.eyes_object(rig)
    select([eyes], eyes)
    yield datetime.timedelta(seconds=0.5)
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("sculpt", bpy.ops.dasktoon.sculpt_eye_expressions())
    log("eye keys", [b.name for b in eyes.data.shape_keys.key_blocks])
    eyes.data.shape_keys.key_blocks["joy"].value = 1.0
    eyes.active_shape_key_index = list(eyes.data.shape_keys.key_blocks).index(eyes.data.shape_keys.key_blocks["joy"])
    look(win, view, [eyes], 'FRONT')
    select([eyes], eyes)
    scroll(win, properties, -20)
    yield datetime.timedelta(seconds=1.5)
    scroll(win, properties, 3)
    yield datetime.timedelta(seconds=1.0)
    # Open Expression Sets (closed by default): its header sat 437 px below the top of the Properties editor here.
    e.cursor_position_set(properties.x + 105, properties.y + properties.height - 437, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse.tap()
    yield datetime.timedelta(seconds=0.5)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "101_expression_sets")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
