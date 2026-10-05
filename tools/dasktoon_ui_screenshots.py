# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of where each DaskToon feature lives (docs/superpowers/reports/2026-10-04-dasktoon-ui-reorganization-report.md,
section "Ảnh chụp").

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_ui_screenshots.py -- <out_dir> <language>

<language> is en_US or vi_VN. A DaskToon window opens for about a minute and closes itself.

Event simulation drives the real UI (menus open through the header buttons and arrow keys); real mouse and keyboard
input is ignored meanwhile. Everything is made in temporary folders: the project, its fake Unity folder and the
DaskToon config folder (so the user's recent projects stay untouched).
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
OUT = ARGS[0] if ARGS else os.path.join(tempfile.gettempdir(), "dt_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else 'en_US'
os.makedirs(OUT, exist_ok=True)
os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_shots_config_")
WORK = tempfile.mkdtemp(prefix="dt_shots_work_")

easy_keys.setup_default_preferences(bpy.context.preferences)
bpy.context.preferences.view.show_tooltips = False
bpy.context.preferences.view.language = LANGUAGE

# The Shape Keys subpanels are closed by default; open them for the pictures.
from bl_ui import dasktoon_shape_key_manager as skm  # noqa: E402
for cls in (skm.DATA_PT_dasktoon_expression_sets, skm.DATA_PT_dasktoon_expression_tools,
            skm.DATA_PT_dasktoon_expression_preview, skm.DATA_PT_dasktoon_expression_controllers):
    bpy.utils.unregister_class(cls)
    cls.bl_options = set()
    bpy.utils.register_class(cls)

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
    """Bounding rect of the pixels that changed inside `limit` (x0, y0, x1, y1), in window coordinates."""
    x0, y0, x1, y1 = limit
    # Menus differ strongly from what they cover; the viewport's anti-aliasing settling over time does not.
    diff = np.abs(after[y0:y1, x0:x1, :3] - before[y0:y1, x0:x1, :3]).max(axis=2) > 0.2
    ys, xs = np.nonzero(diff)
    if len(xs) == 0:
        return None
    return (int(x0 + xs.min() - margin), int(y0 + ys.min() - margin), int(x0 + xs.max() + 1 + margin),
            int(y0 + ys.max() + 1 + margin))


def union(a, b):
    if a is None:
        return b
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def build_scene():
    import dasktoon_test_utils as tu
    from dasktoon_project import project as dtp

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    head, _rig = tu.add_test_head(radius=1.0, centre=(0.0, 0.0, 1.0))
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    skin, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    tu.assign(head, skin)
    eyes, _node = tu.node_material("Eyes", 'ShaderNodeAnimeCharacter')
    head.data.materials.append(eyes)
    tu.add_sun(rotation=(0.8, 0.0, 0.6))
    bpy.ops.dasktoon.face_shading_setup()
    bpy.ops.dasktoon.vrm_init_standard(standard_type='VRM_0')
    bpy.ops.dasktoon.shape_axis_auto_setup(preset_type='VRM_STANDARD')
    head.active_shape_key_index = 1

    unity = os.path.join(WORK, "MyGame")
    for sub in ("Assets", "ProjectSettings"):
        os.makedirs(os.path.join(unity, sub), exist_ok=True)
    dtp.create_project("Hero", os.path.join(WORK, "Hero"), 'UNITY_URP', unity, save_current=True)
    log("scene ready", bpy.data.filepath)
    return head


def select(obj):
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def steps():
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    head = build_scene()
    proxy = next(o for o in bpy.data.objects if o.type == 'EMPTY')
    yield datetime.timedelta(seconds=1.0)

    # Make the Properties editor wider and taller by dragging its borders, as a user would.
    def drag(x0, y0, x1, y1):
        e.cursor_position_set(x0, y0, move=True)
        yield datetime.timedelta(seconds=0.3)
        e.leftmouse.press()
        yield datetime.timedelta(seconds=0.2)
        for t in (0.25, 0.5, 0.75, 1.0):
            e.cursor_position_set(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), move=True)
            yield datetime.timedelta(seconds=0.1)
        e.leftmouse.release()
        yield datetime.timedelta(seconds=0.5)

    props = area_of('PROPERTIES')
    yield from drag(props.x - 2, props.y + props.height // 2, props.x - 432, props.y + props.height // 2)
    props = area_of('PROPERTIES')
    yield from drag(props.x + props.width // 2, props.y + props.height + 1,
                    props.x + props.width // 2, props.y + props.height + 131)
    props = area_of('PROPERTIES')
    log("properties", area_rect(props))
    space = props.spaces.active
    centre = (props.x + props.width // 2, props.y + props.height // 2)

    def scroll(direction, count):
        e.cursor_position_set(*centre, move=True)
        for _ in range(count):
            getattr(e, "wheel%smouse" % direction)()
        e.cursor_position_set(props.x + 12, props.y + 20, move=True)  # park on the empty foot of the tab column

    def props_top(height):
        return props.x, props.y + props.height - height, props.x + props.width, props.y + props.height

    # 1. Face Shading in Properties › Object Data of the mesh (end of the tab).
    space.context = 'DATA'
    yield datetime.timedelta(seconds=0.5)
    scroll("down", 80)
    yield datetime.timedelta(seconds=1.0)
    save(grab(), area_rect(props), "01_face_shading")

    # 2. The same panel on the egg-shaped proxy.
    select(proxy)
    yield datetime.timedelta(seconds=0.5)
    scroll("up", 80)
    yield datetime.timedelta(seconds=1.0)
    save(grab(), props_top(380), "02_face_shading_proxy")

    # 3-5. Shape Keys and its four subpanels, page by page.
    select(head)
    yield datetime.timedelta(seconds=0.5)
    scroll("up", 80)
    yield datetime.timedelta(seconds=1.0)
    save(grab(), area_rect(props), "03_shape_keys_sets_tools")
    scroll("down", 12)
    yield datetime.timedelta(seconds=1.0)
    save(grab(), area_rect(props), "04_shape_keys_preview")
    scroll("down", 12)
    yield datetime.timedelta(seconds=1.0)
    save(grab(), area_rect(props), "05_shape_keys_controllers")

    # 6. Blender's own Shape Key Specials menu (Flip = Mirror Shape Key); Clear Shape Keys is the X of the Relative row.
    scroll("up", 80)
    yield datetime.timedelta(seconds=1.0)
    before = grab()
    e.cursor_position_set(props.x + props.width - 330, props.y + props.height - 300, move=True)  # keeps the X visible
    yield datetime.timedelta(seconds=0.3)
    with bpy.context.temp_override(window=win, area=props, region=region_of(props)):
        bpy.ops.wm.call_menu(name="MESH_MT_shape_key_context_menu")
    yield datetime.timedelta(seconds=1.0)
    after = grab()
    save(after, union(changed_rect(before, after, area_rect(props)), props_top(600)), "06_shape_key_specials")
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    # 7. Shader Editor: outline and shading style live on the Anime BSDF node.
    skin = bpy.data.materials["Skin"]
    main = next(n for n in skin.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
    main.use_outline = True
    main.shading_mode = 'RAMP'
    view = area_of('VIEW_3D')
    view.type = 'NODE_EDITOR'
    node_space = view.spaces.active
    node_space.tree_type = 'ShaderNodeTree'
    node_space.shader_type = 'OBJECT'
    head.active_material_index = 0
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=view, region=region_of(view)):
        bpy.ops.node.view_all()
    yield datetime.timedelta(seconds=1.0)
    save(grab(), area_rect(view), "07_outline_on_node")
    view.type = 'VIEW_3D'
    yield datetime.timedelta(seconds=0.5)

    # 8. 3D Viewport › Add (Shift+A) › Anime Effect: last item, open it. Shift+A works whatever the header language.
    view = area_of('VIEW_3D')
    before = grab()
    e.cursor_position_set(view.x + 330, view.y + view.height - 160, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.shift.a()
    yield datetime.timedelta(seconds=0.8)
    e.up_arrow()
    yield datetime.timedelta(seconds=0.5)
    e.right_arrow()
    yield datetime.timedelta(seconds=1.0)
    after = grab()
    menus = changed_rect(before, after, area_rect(view))
    save(after, menus, "08_add_anime_effect")
    e.esc()
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    # 9. File › DaskToon Project (click File, last item, open it).
    before = grab()
    e.cursor_position_set(40, win.height - 12, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse()
    yield datetime.timedelta(seconds=0.8)
    e.up_arrow()
    yield datetime.timedelta(seconds=0.5)
    e.right_arrow()
    yield datetime.timedelta(seconds=1.0)
    after = grab()
    menus = changed_rect(before, after, (0, view.y, props.x - 4, win.height))  # not the status bar hints
    save(after, union(menus, (0, win.height - 26, 260, win.height)), "09_file_dasktoon_project")
    e.esc()
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    # 10. Properties › Material › slot menu: Combine Materials, Restore Original Slots (after a combine).
    select(head)
    with bpy.context.temp_override(window=win, area=view, region=region_of(view)):
        bpy.ops.dasktoon.combine_materials(resolution='1024')
    space.context = 'MATERIAL'
    yield datetime.timedelta(seconds=0.5)
    scroll("up", 80)
    yield datetime.timedelta(seconds=1.0)
    before = grab()
    e.cursor_position_set(props.x + props.width - 60, props.y + props.height - 150, move=True)
    yield datetime.timedelta(seconds=0.3)
    with bpy.context.temp_override(window=win, area=props, region=region_of(props)):
        bpy.ops.wm.call_menu(name="MATERIAL_MT_context_menu")
    yield datetime.timedelta(seconds=1.0)
    after = grab()
    save(after, union(changed_rect(before, after, area_rect(props)), props_top(380)), "10_material_slot_menu")
    e.esc()
    yield datetime.timedelta(seconds=0.5)

    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
