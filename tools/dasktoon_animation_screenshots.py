# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of DaskToon's Animation tab in a real window
(docs/superpowers/reports/2026-10-10-dasktoon-animation-tab-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_animation_screenshots.py -- <out_dir> <language>

<language> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself. It builds the anime rig's
test character (tests/python/dasktoon_rig_fixtures.py) with a "Smile" shape key on the body and a camera, opens the
Animation tab with only the body selected, presses Key Pose on frame 1 and, with another pose and the smile, on frame
12, then saves:

- 30_animation_tab: the whole window on frame 6: camera view, main viewport, Properties, the character timeline;
- 31_character_timeline: the Dope Sheet: Key Pose and Whole Character in its header, the rig's bones and the body's
  shape key as rows although only the body is selected;
- 32_clips: the clip menu of the character timeline: Walk (Loop on) and Wave, New Clip, Delete Clip;
- 33_timing: the Timing popover: Walk on 2s from frame 1 and on 3s from frame 7
  (docs/superpowers/reports/2026-10-13-dasktoon-anime-timing-report.md);
- 34_onion_skin: a clip "Swing" (the upper body swings to the side from frame 1 to 5), the main viewport on frame 3
  with the ghosts of the poses keyed on frames 1 and 5;
- 35_fast_action: the camera view (Rendered) on frame 4 of Swing: smears, afterimages and speed lines on the upper body.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_animation_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
WORK = tempfile.mkdtemp(prefix="dt_animation_shots_")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "capture_log.txt"), "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def window():
    return bpy.context.window_manager.windows[0]


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


def character():
    """The rig's test character, built, with a Smile shape key on the body and a camera looking at it."""
    from bl_ui import dasktoon_rig as ui
    from dasktoon_rig import build
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    objs = fx.character()
    rig = fx.rig_for()
    for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    body = objs["Body"]
    body.shape_key_add(name="Basis")
    smile = body.shape_key_add(name="Smile")
    for point in smile.data:
        if point.co.z > 0.85 * fx.HEIGHT:
            point.co.x *= 1.15
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -4.5, 0.55 * fx.HEIGHT)
    camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    bpy.context.scene.camera = camera
    return rig, body


def steps():
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    rig, body = character()
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 24
    win.workspace = bpy.data.workspaces["Animation"]
    yield datetime.timedelta(seconds=1.0)
    log("tab", win.workspace.name, [a.type for a in win.screen.areas])
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    bpy.context.view_layer.objects.active = body
    scene.frame_set(1)
    log("key 1", bpy.ops.dasktoon.key_pose())
    scene.frame_set(12)
    for name, angle in (("Spine", 15.0), ("Head", -20.0), ("LeftUpperArm", -60.0), ("RightUpperArm", 40.0)):
        pb = rig.pose.bones[name]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, math.radians(angle), 0.0)
    body.data.shape_keys.key_blocks["Smile"].value = 1.0
    log("key 12", bpy.ops.dasktoon.key_pose())
    scene.frame_set(6)
    dopesheet = next(a for a in win.screen.areas if a.type == 'DOPESHEET_EDITOR')
    with bpy.context.temp_override(window=win, area=dopesheet, region=next(
            r for r in dopesheet.regions if r.type == 'WINDOW')):
        bpy.ops.action.view_all()
    main = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    with bpy.context.temp_override(window=win, area=main, region=next(r for r in main.regions if r.type == 'WINDOW')):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_all(center=False)
    e.cursor_position_set(win.width // 2, 8, move=True)  # the status bar, away from tooltips
    yield datetime.timedelta(seconds=3.0)
    px = grab()
    save(px, (0, 0, win.width, win.height), "30_animation_tab")
    save(px, (dopesheet.x, dopesheet.y, dopesheet.x + dopesheet.width, dopesheet.y + dopesheet.height),
         "31_character_timeline")

    # 32. Clips: the animation so far becomes a clip (renamed Walk, Loop on), a second clip Wave; the clip menu open.
    from dasktoon_animation import clips
    log("clip new", bpy.ops.dasktoon.clip_new())
    walk = bpy.data.actions["Clip"]
    walk.name, walk.use_cyclic = "Walk", True
    clips.current(rig).name = "Wave"
    clips.use(rig, list(bpy.context.view_layer.objects), walk, scene)
    header = next(r for r in dopesheet.regions if r.type == 'HEADER')
    top = dopesheet.y + dopesheet.height
    e.cursor_position_set(dopesheet.x + 330, top - 14, move=True)
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=dopesheet, region=header):
        bpy.ops.wm.call_menu(name="DASKTOON_MT_character_clips")
    yield datetime.timedelta(seconds=0.5)
    save(grab(), (dopesheet.x, top - 330, dopesheet.x + 1000, top), "32_clips")
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    # 33. Timing: Walk on 2s from frame 1 and on 3s from frame 7; the Timing popover open on frame 8.
    scene.frame_set(1)
    log("timing 2s", bpy.ops.dasktoon.timing_set(step=2))
    scene.frame_set(7)
    log("timing 3s", bpy.ops.dasktoon.timing_set(step=3))
    scene.frame_set(8)
    e.cursor_position_set(dopesheet.x + 620, top - 14, move=True)
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=dopesheet, region=header):
        bpy.ops.wm.call_panel(name="DASKTOON_PT_character_timing", keep_open=False)
    yield datetime.timedelta(seconds=0.5)
    save(grab(), (dopesheet.x, top - 300, dopesheet.x + 1100, top), "33_timing")
    e.esc()

    # 34 and 35 use a clip "Swing": the upper body swings to the side from frame 1 to frame 5.
    from bl_ui import dasktoon_animation as anim_ui
    from mathutils import Matrix
    clips.new(rig, list(bpy.context.view_layer.objects), "Swing", scene=scene)
    scene.frame_set(1)
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion, pb.rotation_euler, pb.scale = (0, 0, 0), (1, 0, 0, 0), (0, 0, 0), (1, 1, 1)
    body.data.shape_keys.key_blocks["Smile"].value = 0.0
    log("swing 1", bpy.ops.dasktoon.key_pose())
    scene.frame_set(5)
    for name, angle in (("Spine", 35.0),):
        pb = rig.pose.bones[name]
        head = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(angle), 4, 'Y') @ \
            Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()
    log("swing 5", bpy.ops.dasktoon.key_pose())

    # 34. Onion skin on frame 3: the poses keyed on frames 1 (red) and 5 (blue) around the character.
    scene.dasktoon_onion.show = True
    scene.frame_set(3)
    with bpy.context.temp_override(window=win, area=main, region=next(r for r in main.regions if r.type == 'WINDOW')):
        bpy.ops.view3d.view_selected()
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.5)  # the ghosts are copied once the frame stays
    log("ghosts", [(side, frame) for side, _rank, frame, _shapes in anim_ui.onion_ghosts()])
    save(grab(), (main.x, main.y, main.x + main.width, main.y + main.height), "34_onion_skin")
    scene.dasktoon_onion.show = False

    # 35. Fast action on frame 4, the swing at its fastest: the upper body smears and leaves afterimages and speed
    # lines; the camera view renders it.
    fast = rig.data.dasktoon_fast_action
    fast.threshold, fast.smear, fast.afterimages, fast.line_density = 1.0, 0.8, 3, 0.3
    fast.enabled = True
    for frame in range(1, 5):  # the simulation runs from the start
        scene.frame_set(frame)
    yield datetime.timedelta(seconds=4.0)
    camera_view = next(a for a in win.screen.areas
                       if a.type == 'VIEW_3D' and a.spaces.active.region_3d.view_perspective == 'CAMERA')
    save(grab(), (camera_view.x, camera_view.y, camera_view.x + camera_view.width,
                  camera_view.y + camera_view.height), "35_fast_action")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
