# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Window test of the paint layers (docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md, section 5).
Strokes need a 3D view and an Image Editor, so it is not in the CMake list. Run it with the bundled Python:

    "$PY" tests/python/dasktoon_paint_layers_window_test.py "$DT"

Inside DaskToon (event simulation) a plane with the anime shader gets Start Painting and a second layer, then:
1. a stroke in the 3D view goes to the active layer: the layer Base stays as it was, the image shows the stroke;
2. Undo takes the stroke out of the layer and out of the image;
3. a stroke in the Image Editor goes to the active layer too, and shows in the image;
4. Fill Part fills the plane's part on the active layer."""

import json
import os
import subprocess
import sys
import tempfile

try:
    import bpy
except ImportError:
    bpy = None

RESULT = "result.json"


def run_outside(exe):
    work = tempfile.mkdtemp(prefix="dt_paint_window_")
    env = dict(os.environ, DASKTOON_CONFIG_DIR=os.path.join(work, "config"), DASKTOON_WINDOW_TEST=work)
    subprocess.call([exe, "--enable-event-simulate", "--factory-startup", "--python", os.path.abspath(__file__)],
                    env=env, timeout=600)
    result_path = os.path.join(work, RESULT)
    if not os.path.isfile(result_path):
        print("FAIL: DaskToon wrote no result (see its console output)")
        return 1
    with open(result_path, encoding="utf-8") as f:
        result = json.load(f)
    for line in result.get("log", []):
        print("  ", line)
    for error in result["errors"]:
        print("FAIL:", error)
    print("OK" if not result["errors"] else "%d failure(s)" % len(result["errors"]))
    return 0 if not result["errors"] else 1


def steps(work):
    import datetime
    import numpy as np
    from dasktoon_paint import layers, start

    def wait(seconds):
        return datetime.timedelta(seconds=seconds)

    errors, log = [], []
    result = {"errors": errors, "log": log}

    def write_result():
        with open(os.path.join(work, RESULT), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)

    def pixels(image):
        px = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(px)
        return px.reshape(image.size[1], image.size[0], 4)

    def check(condition, message):
        if not condition:
            errors.append(message)

    def region(area, kind='WINDOW'):
        return next(r for r in area.regions if r.type == kind)

    def stroke(win, area, points):
        reg = region(area)
        elements = [{"name": "", "location": (0, 0, 0), "mouse": p, "mouse_event": p, "pressure": 1.0, "size": 40.0,
                     "time": float(i), "is_start": i == 0, "x_tilt": 0.0, "y_tilt": 0.0} for i, p in enumerate(points)]
        with bpy.context.temp_override(window=win, area=area, region=reg):
            return bpy.ops.paint.image_paint(stroke=elements)

    yield wait(2.0)
    win = bpy.context.window_manager.windows[0]
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    bpy.ops.mesh.primitive_plane_add(size=2.0)
    plane = bpy.context.active_object
    plane.data.materials.append(bpy.data.materials.new("Skin"))
    made = start.start(bpy.context, plane, size=256)
    check(len(made) == 1, "Start Painting made %d images, not 1" % len(made))
    owner = made[0]
    top = layers.add(owner).image
    base = owner.dasktoon_layers[0].image
    base_before, owner_before = pixels(base).copy(), pixels(owner).copy()
    names = (owner.name, base.name, top.name)  # Undo can make new Python objects for the images: look them up again

    def images():
        return tuple(bpy.data.images[name] for name in names)
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='TOP')
        bpy.ops.view3d.view_selected()
        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
    settings = bpy.context.tool_settings.image_paint
    settings.mode = 'MATERIAL'
    settings.unified_paint_settings.color = (1.0, 0.0, 0.0)
    settings.unified_paint_settings.use_unified_color = True
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.ed.undo_push(message="Paint setup")  # as the operators of a real session would have
    yield wait(1.0)

    # 1. A stroke in the 3D view.
    reg = region(view)
    cx, cy = reg.width // 2, reg.height // 2
    log.append("3D stroke: %s" % stroke(win, view, [(cx - 60, cy), (cx, cy), (cx + 60, cy)]))
    yield wait(1.0)
    painted = pixels(top)
    check(painted[..., 3].max() > 0.5, "the 3D stroke did not reach the active layer")
    check(np.abs(pixels(base) - base_before).max() < 1e-6, "the 3D stroke changed the layer Base")
    shown = np.abs(pixels(owner) - owner_before).max()
    check(shown > 0.3, "the image does not show the 3D stroke (largest change %.3f)" % shown)
    composite_ok = np.abs(pixels(owner)[..., 0] - np.maximum(painted[..., 0] * painted[..., 3]
                                                             + owner_before[..., 0] * (1 - painted[..., 3]), 0))
    log.append("3D: layer alpha max %.3f, image change %.3f, composite red error %.4f"
               % (painted[..., 3].max(), shown, composite_ok.max()))
    check(composite_ok.max() < 0.02, "the image is not the composite after the 3D stroke")

    # 2. Undo.
    with bpy.context.temp_override(window=win, area=view, region=reg):
        bpy.ops.ed.undo()
    yield wait(1.0)
    owner, base, top = images()
    log.append("undo: layers %d, active %d" % (len(owner.dasktoon_layers), owner.dasktoon_layer_index))
    check(pixels(top)[..., 3].max() < 1e-6, "Undo left the 3D stroke in the layer")
    check(np.abs(pixels(owner) - owner_before).max() < 2.0 / 255, "Undo left the 3D stroke in the image")

    # 3. A stroke in the Image Editor.
    view.ui_type = 'IMAGE_EDITOR'
    yield wait(0.5)
    space = view.spaces.active
    space.image = owner
    space.mode = 'PAINT'
    yield wait(0.5)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.image.view_all(fit_view=True)
    yield wait(0.5)
    reg = region(view)
    cx, cy = reg.width // 2, reg.height // 2
    log.append("2D stroke: %s" % stroke(win, view, [(cx, cy - 40), (cx, cy), (cx, cy + 40)]))
    yield wait(1.0)
    check(pixels(top)[..., 3].max() > 0.5, "the 2D stroke did not reach the active layer")
    check(np.abs(pixels(base) - base_before).max() < 1e-6, "the 2D stroke changed the layer Base")
    check(np.abs(pixels(owner) - owner_before).max() > 0.3, "the image does not show the 2D stroke")
    view.ui_type = 'VIEW_3D'
    yield wait(0.5)

    # 4. The Fill Part tool, clicked on the plane: the whole part on the active layer, the brush in use kept.
    import easy_keys
    owner, base, top = images()
    top.pixels.foreach_set(np.zeros(len(top.pixels), dtype=np.float32))
    top.update()
    layers.composite(owner)
    settings.unified_paint_settings.color = (0.0, 0.0, 1.0)
    brush_before = settings.brush
    view = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    reg = region(view)
    with bpy.context.temp_override(window=win, area=view, region=reg):
        bpy.ops.ed.undo_push(message="Before Fill Part")
        bpy.ops.wm.tool_set_by_id(name="dasktoon.fill_part")
    yield wait(0.5)
    e = easy_keys.EventGenerate(win)
    e.cursor_position_set(reg.x + reg.width // 2, reg.y + reg.height // 2, move=True)
    yield wait(0.3)
    e.leftmouse.tap()
    yield wait(1.5)
    owner, base, top = images()
    alpha = pixels(top)[..., 3]
    log.append("fill part: covered %.3f, blue %.3f" % ((alpha > 0.9).mean(), pixels(owner)[..., 2].mean()))
    check((alpha > 0.9).mean() > 0.95, "Fill Part did not fill the plane on the active layer")
    check(np.abs(pixels(base) - base_before).max() < 1e-6, "Fill Part changed the layer Base")
    check(pixels(owner)[..., 2].mean() > 0.9, "the image does not show the fill")
    check(settings.brush == brush_before, "Fill Part did not give the brush in use back")
    check(not plane.data.use_paint_mask, "Fill Part left the face mask on")

    write_result()
    bpy.ops.wm.quit_blender()


def run_inside():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_simulate", "modules"))
    import easy_keys
    work = os.environ["DASKTOON_WINDOW_TEST"]
    easy_keys.setup_default_preferences(bpy.context.preferences)

    def on_error():
        import traceback
        with open(os.path.join(work, RESULT), "w", encoding="utf-8") as f:
            json.dump({"errors": ["a step raised an error: " + traceback.format_exc()]}, f)
        bpy.ops.wm.quit_blender()

    easy_keys.run(steps(work), on_error=on_error)


if bpy is None:
    if __name__ == "__main__":
        sys.exit(run_outside(sys.argv[1]))
else:
    run_inside()
