# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the illustration finish in a real window
(docs/superpowers/reports/2026-10-13-dasktoon-illustration-finish-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_finish_screenshots.py -- <out_dir> <language>

<language> is en_US or vi_VN. A DaskToon window opens for about a minute and closes itself. It builds the anime rig's
test character with DaskToon toon materials in a small set (ground, trees, a far building, a sky, a Sun), turns the
finish on and saves:

- 40_finish_panel: Properties › Scene with the Illustration Finish panel, Painting Colors open;
- 41_finish_before_after: the camera's render without the finish, then with the Default style;
- 42_finish_camera_view: the Animation tab, its camera view (Rendered) showing the finish;
- 43_finish_styles: renders with each built-in style, the first one without the finish.
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
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_finish_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "en_US"
WORK = tempfile.mkdtemp(prefix="dt_finish_shots_")
RENDER_W, RENDER_H = 480, 300
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "capture_log.txt"), "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def window():
    return bpy.context.window_manager.windows[0]


def load(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def grab():
    """Full window pixels, rows from the bottom (window coordinates)."""
    win = window()
    path = os.path.join(WORK, "grab.png")
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=path)
    return load(path)


def write(px, name):
    h, w = px.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(np.ascontiguousarray(px).ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    log("saved", name, (w, h))


def save_area(px, area, name):
    write(px[area.y:area.y + area.height, area.x:area.x + area.width], name)


def toon(name, color, outline=True):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    node = tree.nodes.new("ShaderNodeAnimeCharacter")
    node.inputs["Base Color"].default_value = color + (1.0,)
    node.use_outline = outline
    tree.links.new(node.outputs[0], tree.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    return mat


def give(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def build_set():
    """The test character in toon materials, a ground, trees from near to far, a far building, a sky and a Sun; a
    camera on the character."""
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    scene.render.resolution_x, scene.render.resolution_y = RENDER_W, RENDER_H
    scene.view_settings.view_transform = 'Standard'
    world = scene.world or bpy.data.worlds.new("Sky")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.62, 0.95, 1.0)
    objs = fx.character()
    colors = {"Body": (1.0, 0.82, 0.74), "Shirt": (0.95, 0.95, 1.0), "Hair": (0.35, 0.22, 0.45),
              "Skirt": (0.25, 0.35, 0.75)}
    for name, obj in objs.items():
        if obj.type == 'MESH':
            give(obj, toon(name, colors.get(name, (0.8, 0.8, 0.8))))

    def prop(op, loc, scale, color):
        op(location=loc)
        obj = bpy.context.object
        obj.scale = scale
        give(obj, toon("Set" + obj.name, color, outline=False))

    prop(bpy.ops.mesh.primitive_plane_add, (0, 30, 0), (60, 60, 1), (0.45, 0.68, 0.38))
    for x, y, s in ((-3, 6, 1.0), (4, 14, 1.4), (-9, 28, 2.2), (10, 45, 3.0), (-18, 70, 4.0)):
        prop(bpy.ops.mesh.primitive_cone_add, (x, y, s * 1.5), (s, s, s * 1.6), (0.18, 0.45, 0.25))
    prop(bpy.ops.mesh.primitive_cube_add, (14, 90, 8), (8, 4, 8), (0.85, 0.82, 0.78))
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(55), 0, math.radians(150)))
    bpy.context.object.data.energy = 3.5
    bpy.ops.object.camera_add(location=(0.9, -3.6, 1.2), rotation=(math.radians(84), 0, math.radians(14)))
    scene.camera = bpy.context.object
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == objs["Body"])
    bpy.context.view_layer.objects.active = objs["Body"]
    return objs


def render(name):
    scene = bpy.context.scene
    path = os.path.join(WORK, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return load(path)


def side_by_side(images, columns):
    rows = (len(images) + columns - 1) // columns
    h, w = images[0].shape[:2]
    sheet = np.ones((rows * h, columns * w, 4), np.float32)
    for i, img in enumerate(images):
        r, c = divmod(i, columns)
        sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = img
    return sheet


def steps():
    from bl_ui import dasktoon_finish as ui
    from dasktoon_finish import styles
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    build_set()
    scene = bpy.context.scene

    # 41 and 43: renders without the finish, then with each style (Default first).
    plain = render("off")
    finish = scene.dasktoon_finish
    finish.enabled = True
    shots = [plain]
    for name in styles.BUILT_IN:
        ui.apply_style(scene, name)
        shots.append(render(name.replace(" ", "_")))
    write(side_by_side(shots[:2], 2), "41_finish_before_after")
    write(side_by_side(shots, 2), "43_finish_styles")
    log("styles", list(styles.BUILT_IN))
    ui.apply_style(scene, "Default")

    # 40: Properties › Scene, scrolled down to the Illustration Finish panel.
    properties = next(a for a in win.screen.areas if a.type == 'PROPERTIES')
    properties.spaces.active.context = 'SCENE'
    yield datetime.timedelta(seconds=1.0)
    region = next(r for r in properties.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=properties, region=region):
        for _ in range(40):
            bpy.ops.view2d.scroll_down(deltax=0, deltay=200)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.5)
    save_area(grab(), properties, "40_finish_panel")

    # 42: the Animation tab; its camera view renders with the finish.
    win.workspace = bpy.data.workspaces["Animation"]
    yield datetime.timedelta(seconds=1.0)
    from dasktoon_animation import tab
    tab.show_render_in_camera_view()
    ui.sync(scene)
    yield datetime.timedelta(seconds=6.0)
    camera_view = next(a for a in win.screen.areas
                       if a.type == 'VIEW_3D' and a.spaces.active.region_3d.view_perspective == 'CAMERA')
    log("camera view compositor", camera_view.spaces.active.shading.use_compositor)
    save_area(grab(), camera_view, "42_finish_camera_view")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
