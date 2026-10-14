# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the anime rig's eyes and mouth (R3) in a real window
(docs/superpowers/reports/2026-10-13-dasktoon-anime-rig-r3-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_rig_r3_screenshots.py -- <out_dir> <lang>

<lang> is en_US or vi_VN. A DaskToon window opens for about half a minute and closes itself. It builds the rig's test
character with a flat eye (a plane with a UV grid in front of the left eye) and a 2D mouth (a card with a 2 x 2 atlas
of colored cells), then saves:

- 50_face_parts: Properties › Object Data of the rig, the Flat Eye part selected: its Side and Range;
- 51_gaze: the face in Material Preview (bones hidden), LookTarget in front, then moved to the character's left: the
  iris grid slides;
- 52_mouth_2d: the mouth card with dt_mouth 0, then 1: another cell of the atlas;
- 53_lip_sync: the Lip Sync from Audio dialog.
"""
import datetime
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python", "ui_simulate", "modules"))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import easy_keys  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_rig_r3_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
WORK = tempfile.mkdtemp(prefix="dt_rig_r3_shots_")
COLORS = ((0.95, 0.35, 0.40), (0.40, 0.80, 0.45), (0.35, 0.50, 0.95), (0.95, 0.85, 0.35))
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


def side_by_side(a, b):
    h = min(a.shape[0], b.shape[0])
    gap = np.ones((h, 8, 4), np.float32)
    return np.concatenate([a[:h], gap, b[:h]], axis=1)


def emission_material(name, image):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs[0], tree.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    return mat


def atlas_image():
    size = 64
    image = bpy.data.images.new("MouthAtlas", size, size)
    pixels = []
    for y in range(size):
        row = 0 if y >= size // 2 else 1
        for x in range(size):
            pixels += list(COLORS[row * 2 + (0 if x < size // 2 else 1)]) + [1.0]
    image.pixels.foreach_set(pixels)
    image.update()
    return image


def plane(name, location, size):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location, rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    return obj


def build_character():
    from bl_ui import dasktoon_rig as ui
    from dasktoon_rig import build
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    objs = fx.character()
    rig = fx.rig_for()
    eye = rig.matrix_world @ rig.data.bones["LeftEye"].head_local
    iris = plane("Iris", eye + Vector((0.0, -0.02, 0.0)), 0.03)
    grid = bpy.data.images.new("IrisGrid", 256, 256)
    grid.generated_type = 'COLOR_GRID'
    iris.data.materials.append(emission_material("Iris", grid))
    jaw = rig.matrix_world @ rig.data.bones["Jaw"].tail_local
    card = plane("MouthCard", jaw + Vector((0.0, -0.02, 0.0)), 0.04)
    card.data.materials.append(emission_material("Mouth", atlas_image()))
    ui.add_part(rig, objs["Body"], 'BODY')
    flat = ui.add_part(rig, iris, 'FLAT_EYE')
    flat.eye_range = 0.3
    mouth = ui.add_part(rig, card, 'MOUTH_2D')
    mouth.mouth_rows, mouth.mouth_columns = 2, 2
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    rig.data.dasktoon_rig.active_part_index = 1
    return rig, objs, iris, card


def aim(rig, sideways):
    from dasktoon_rig import look
    target = rig.pose.bones[look.TARGET]
    world = rig.matrix_world @ target.bone.matrix_local
    world.translation += Vector((sideways, 0.0, 0.0))
    target.matrix = rig.matrix_world.inverted() @ world
    bpy.context.view_layer.update()


def steps():
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    rig, objs, iris, card = build_character()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == rig)
    bpy.context.view_layer.objects.active = rig

    # 50: the rig's Object Data, scrolled down to the Anime Rig panel and the Flat Eye part.
    properties = next(a for a in win.screen.areas if a.type == 'PROPERTIES')
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=1.0)
    region = next(r for r in properties.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=properties, region=region):
        for _ in range(40):
            bpy.ops.view2d.scroll_down(deltax=0, deltay=200)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    px = grab()
    write(crop(px, properties.x, properties.y, properties.x + properties.width, properties.y + properties.height),
          "50_face_parts")

    # 51 and 52: the head in Material Preview, from the front.
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    view.spaces.active.shading.type = 'MATERIAL'
    view.spaces.active.overlay.show_bones = False  # the bones would cover the iris
    objs["Eye"].hide_set(True)  # the test character's eyeball cube sits in front of the iris
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in (iris, card))
    with bpy.context.temp_override(window=win, area=view, region=next(r for r in view.regions if r.type == 'WINDOW')):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()
        bpy.ops.view3d.zoom(delta=-1)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    cx = view.x + view.width // 2
    rect = (cx - 420, view.y + 40, cx + 420, view.y + view.height - 60)
    yield datetime.timedelta(seconds=2.0)
    ahead = crop(grab(), *rect)
    aim(rig, 0.25)
    yield datetime.timedelta(seconds=1.5)
    left = crop(grab(), *rect)
    write(side_by_side(ahead, left), "51_gaze")
    aim(rig, -0.25)
    from dasktoon_rig import mouth
    card[mouth.PROP] = 0
    card.update_tag()
    yield datetime.timedelta(seconds=1.5)
    closed = crop(grab(), *rect)
    card[mouth.PROP] = 1
    card.update_tag()
    yield datetime.timedelta(seconds=1.5)
    write(side_by_side(closed, crop(grab(), *rect)), "52_mouth_2d")

    # 53: the Lip Sync from Audio dialog, from the Body.
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == objs["Body"])
    bpy.context.view_layer.objects.active = objs["Body"]
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=view, region=next(r for r in view.regions if r.type == 'WINDOW')):
        bpy.ops.dasktoon.lip_sync_from_audio('INVOKE_DEFAULT')
    yield datetime.timedelta(seconds=1.0)
    cx, cy = view.x + view.width // 2, view.y + view.height // 2
    write(crop(grab(), cx - 320, cy - 200, cx + 320, cy + 120), "53_lip_sync")
    e.esc()
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
