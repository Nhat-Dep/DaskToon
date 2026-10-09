# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the anime rig R1 in a real DaskToon window
(docs/superpowers/reports/2026-10-06-dasktoon-anime-rig-r1-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_rig_screenshots.py -- <out_dir> <language>

<language> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself. It builds the test
character of tests/python/dasktoon_rig_fixtures.py, adds the standard skeleton with Add › Armature › Anime Humanoid,
presses Build Rig, poses the spine, head, hair and skirt, and saves:

- 21_add_armature_menu: the Add › Armature menu with Anime Humanoid;
- 22_rest, 23_posed: the character from the side before and after posing (the hair and skirt chains bend);
- 25_sway: R2, the hips dash sideways from frame 1 to 6; on frame 8 the skirt and hair lag behind (Live Sway);
- 24_rig_panel: the Anime Rig panel in Properties › Object Data of the armature, the skirt part active (Sway shows its
  settings and the colliders).
"""
import datetime
import math
import os
import sys
import tempfile

import bpy
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python", "ui_simulate", "modules"))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import easy_keys  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_rig_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
WORK = tempfile.mkdtemp(prefix="dt_rig_shots_")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "capture_log.txt"), "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def window():
    return bpy.context.window_manager.windows[0]


def area_of(kind):
    return next(a for a in window().screen.areas if a.type == kind)


def region_of(area, kind='WINDOW'):
    return next(r for r in area.regions if r.type == kind)


def grab():
    """Full window pixels, rows from the bottom (window coordinates)."""
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


def save(px, rect, name):
    """Save the window coordinates rect (x0, y0, x1, y1) of px as <OUT>/<name>.png."""
    h, w = px.shape[:2]
    x0, y0, x1, y1 = max(0, rect[0]), max(0, rect[1]), min(w, rect[2]), min(h, rect[3])
    sub = np.ascontiguousarray(px[y0:y1, x0:x1])
    img = bpy.data.images.new(name, x1 - x0, y1 - y0, alpha=False)
    img.pixels.foreach_set(sub.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    log("saved", name, (x0, y0, x1, y1))


def area_rect(area):
    return area.x, area.y, area.x + area.width, area.y + area.height


def changed_rect(before, after, limit, margin=12):
    x0, y0, x1, y1 = limit
    diff = np.abs(after[y0:y1, x0:x1, :3] - before[y0:y1, x0:x1, :3]).max(axis=2) > 0.2
    ys, xs = np.nonzero(diff)
    if len(xs) == 0:
        return limit
    return (int(x0 + xs.min() - margin), int(y0 + ys.min() - margin), int(x0 + xs.max() + 1 + margin),
            int(y0 + ys.max() + 1 + margin))


def pose(rig):
    bones = rig.pose.bones
    turns = {"Spine": (0.0, 0.0, 12.0), "Head": (0.0, 0.0, 25.0), "LeftUpperArm": (-50.0, 0.0, 0.0),
             "RightUpperArm": (-50.0, 0.0, 0.0)}
    turns.update({"Hair_%d" % k: (25.0, 0.0, 0.0) for k in range(1, 5)})
    turns.update({"Skirt1_%d" % k: (20.0, 0.0, 0.0) for k in range(1, 4)})
    turns.update({"Skirt5_%d" % k: (20.0, 0.0, 0.0) for k in range(1, 4)})
    for name, angles in turns.items():
        bone = bones.get(name)
        if bone is None:
            log("no bone", name)
            continue
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = [math.radians(a) for a in angles]


def steps():
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    view = area_of('VIEW_3D')
    region = region_of(view)
    space = view.spaces.active
    space.shading.type = 'SOLID'
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)

    # 21. Add › Armature with Anime Humanoid.
    yield datetime.timedelta(seconds=1.0)
    before = grab()
    with bpy.context.temp_override(window=win, area=view, region=region):
        bpy.ops.wm.call_menu(name="VIEW3D_MT_armature_add")
    yield datetime.timedelta(seconds=0.3)  # before the tooltip of the item under the cursor shows
    after = grab()
    status_bar = int(30 * bpy.context.preferences.view.ui_scale)
    save(after, changed_rect(before, after, (0, status_bar, win.width, win.height)), "21_add_armature_menu")
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    # The test character, then the skeleton and Build Rig through the operators, as a user would.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    objs = fx.character()
    bpy.context.view_layer.update()
    for obj in objs.values():
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs["Body"]
    with bpy.context.temp_override(window=win, area=view, region=region):
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        log("parts", [(p.name, p.role) for p in rig.data.dasktoon_rig.parts])
        bpy.ops.dasktoon.rig_build()
        log("bones", len(rig.data.bones))
        bpy.ops.view3d.view_axis(type='RIGHT')
        bpy.ops.view3d.view_all(center=False)
    yield datetime.timedelta(seconds=1.5)
    save(grab(), area_rect(view), "22_rest")

    with bpy.context.temp_override(window=win, area=view, region=region):
        bpy.ops.object.mode_set(mode='POSE')
    pose(rig)
    yield datetime.timedelta(seconds=1.5)
    save(grab(), area_rect(view), "23_posed")
    with bpy.context.temp_override(window=win, area=view, region=region):
        bpy.ops.object.mode_set(mode='OBJECT')
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)

    # 25. Live Sway: the hips dash sideways, the skirt and hair lag behind.
    hips = rig.pose.bones["Hips"]
    for frame, x in ((1, 0.0), (6, 0.35), (14, 0.35)):
        hips.location = (x, 0.0, 0.0)
        hips.keyframe_insert("location", frame=frame)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 14
    with bpy.context.temp_override(window=win, area=view, region=region):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_all(center=False)
    for frame in range(1, 9):
        scene.frame_set(frame)
    log("sway frame", scene.frame_current, tuple(round(v, 3) for v in rig.pose.bones["Skirt1_3"].rotation_quaternion))
    yield datetime.timedelta(seconds=1.5)
    save(grab(), area_rect(view), "25_sway")
    data = rig.data.dasktoon_rig
    data.active_part_index = next(i for i, p in enumerate(data.parts) if p.role == 'SKIRT')

    # 24. The Anime Rig panel: the big area becomes a Properties editor on the armature's Object Data tab.
    view.type = 'PROPERTIES'
    yield datetime.timedelta(seconds=0.5)
    props = view.spaces.active
    props.context = 'DATA'
    yield datetime.timedelta(seconds=1.0)
    # Build Rig again from the panel's own editor, as the button does (automatic weights need the selection there).
    with bpy.context.temp_override(window=win, area=view, region=region_of(view)):
        log("build from Properties", bpy.ops.dasktoon.rig_build(), len(rig.data.bones),
            len(objs["Body"].vertex_groups))
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)
    for _ in range(40):
        e.wheeldownmouse()
    e.cursor_position_set(view.x + 12, view.y + 20, move=True)  # park on the tab column, away from tooltips
    yield datetime.timedelta(seconds=1.5)
    save(grab(), area_rect(view), "24_rig_panel")
    view.type = 'VIEW_3D'

    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
