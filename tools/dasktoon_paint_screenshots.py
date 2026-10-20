# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of anime painting in a real window (docs/superpowers/reports/2026-10-20-dasktoon-paint-layers-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_paint_screenshots.py -- <out_dir> <lang>

<lang> is en_US or vi_VN. A DaskToon window opens for about twenty seconds and closes itself, and saves (the test
chibi):

- 110_texture_slots: Start Painting done (its own UV map), a layer Lines with a red stroke on the body: the 3D view in
  Texture Paint, the header's Texture Slots popover open with its Paint Layers;
- 111_fill_part: Fill Part clicked on the left leg in blue: the tool in the toolbar, its colour in the header;
- 112_image_editor: the same picture in the Image Editor, its Image tab with the Paint Layers.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_paint_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
WORK = tempfile.mkdtemp(prefix="dt_paint_shots_")
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


def stroke(win, area, points):
    elements = [{"name": "", "location": (0, 0, 0), "mouse": p, "mouse_event": p, "pressure": 1.0, "size": 12.0,
                 "time": float(i), "is_start": i == 0, "x_tilt": 0.0, "y_tilt": 0.0} for i, p in enumerate(points)]
    with bpy.context.temp_override(window=win, area=area, region=region(area)):
        return bpy.ops.paint.image_paint(stroke=elements)


def steps():
    import dasktoon_guide_checks_test as gt
    from dasktoon_paint import layers
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    e.cursor_position_set(win.width // 2, 8, move=True)

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    body = gt.good(reset=False)
    body.data.uv_layers.remove(body.data.uv_layers[0])  # the test's UV map lays every face on the whole picture
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    bpy.context.view_layer.objects.active = body
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()
        log("start", bpy.ops.dasktoon.paint_start())
    owner = bpy.context.tool_settings.image_paint
    mat = body.active_material
    image = mat.texture_paint_images[mat.paint_active_slot]
    layers.add(image, "Lines")
    view.spaces.active.shading.type = 'MATERIAL'
    view.spaces.active.show_region_ui = True
    yield datetime.timedelta(seconds=1.0)
    owner.unified_paint_settings.use_unified_color = True
    owner.unified_paint_settings.color = (0.9, 0.1, 0.1)
    reg = region(view)
    cx, cy = reg.width // 2, reg.height // 2
    brush = owner.brush
    log("brush", brush.name if brush else None, brush.image_brush_type if brush else None,
        brush.size if brush else None, tuple(owner.brush_asset_reference.relative_asset_identifier.split("/")))
    log("stroke", stroke(win, view, [(cx - 20 + k, cy + 20 + k // 3) for k in range(0, 40, 4)]))
    top = image.dasktoon_layers[image.dasktoon_layer_index].image
    px = np.empty(len(top.pixels), dtype=np.float32)
    top.pixels.foreach_get(px)
    log("painted share", float((px.reshape(-1, 4)[:, 3] > 0.5).mean()))
    view.spaces.active.show_region_ui = False
    yield datetime.timedelta(seconds=0.5)
    # The header's Texture Slots popover (named after the slot), 48% across the header here; it stays open under the
    # cursor.
    e.cursor_position_set(view.x + int(view.width * 0.481), view.y + view.height - 12, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse.tap()
    yield datetime.timedelta(seconds=0.3)
    e.cursor_position_set(view.x + int(view.width * 0.481), view.y + view.height - 60, move=True)
    yield datetime.timedelta(seconds=1.5)
    write(area_shot(grab(), view), "110_texture_slots")
    e.esc()
    yield datetime.timedelta(seconds=0.3)
    view.spaces.active.show_region_ui = True

    owner.unified_paint_settings.color = (0.1, 0.3, 0.9)
    with bpy.context.temp_override(window=win, area=view, region=reg):
        bpy.ops.wm.tool_set_by_id(name="dasktoon.fill_part")
    yield datetime.timedelta(seconds=0.5)
    e.cursor_position_set(reg.x + cx + 10, reg.y + int(reg.height * 0.2), move=True)  # the left leg
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse.tap()
    yield datetime.timedelta(seconds=1.0)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    write(area_shot(grab(), view), "111_fill_part")

    view.ui_type = 'IMAGE_EDITOR'
    yield datetime.timedelta(seconds=0.5)
    space = view.spaces.active
    space.image = image
    space.show_region_ui = True
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.image.view_all(fit_view=True)
    yield datetime.timedelta(seconds=0.5)
    sidebar = region(view, 'UI')
    # The Image Editor's Image tab: about 130 px under the top of its sidebar here.
    e.cursor_position_set(sidebar.x + sidebar.width - 8, sidebar.y + sidebar.height - 130, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse.tap()
    yield datetime.timedelta(seconds=0.3)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.5)
    write(area_shot(grab(), view), "112_image_editor")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    import traceback
    log("ERROR", traceback.format_exc())
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
