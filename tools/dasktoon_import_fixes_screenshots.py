# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Screenshots of the model import fixes in a real window
(docs/superpowers/reports/2026-10-19-dasktoon-model-import-fixes-report.md).

DaskToon.exe --enable-event-simulate --factory-startup --python tools/dasktoon_import_fixes_screenshots.py -- <out_dir> <lang> [<scroll>]

<lang> is en_US or vi_VN; <scroll> is how many steps the Properties editor scrolls down to the Check panel (7 by
default). A DaskToon window opens for about a minute and closes itself, and saves:

- 90_facing: a chibi modelled facing a side, its feet telling nothing, rigged by Add › Armature › Anime Humanoid: the
  Check asks to turn it, with Turn 90° Left and Turn 90° Right;
- 91_turned: after Turn 90° Right: the Check again, and the character facing the front;
- 92_material_menu: the material slot menu (⌄) with Use DaskToon Shader and its All Selected form;
- 93_material_after: the material after Use DaskToon Shader: the Anime BSDF fed the old colour;
- 94_fast_action: the Fast Action popover of a character moving fast, not baked: Render bakes it first;
- 95_render: what Render (as F12 runs it) rendered, after baking first (capture_log.txt says what was baked);
- 96_fast_action_baked: the popover again: baked for the scene's frames;
- 97_skirt_check: a dress rigged by hand (parts added, Build Rig, Check): its part below the waist looks like a skirt,
  with Make That Part a Skirt;
- 98_skirt_made: after the button: the dress's lower part is a Skirt part, the Check has no such spot.
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
import dasktoon_rig_regions_test as rt  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(tempfile.gettempdir(), "dt_import_fixes_shots")
LANGUAGE = ARGS[1] if len(ARGS) > 1 else "vi_VN"
SCROLL = int(ARGS[2]) if len(ARGS) > 2 else 7
WORK = tempfile.mkdtemp(prefix="dt_import_fixes_shots_")
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


def area_shot(px, area):
    return crop(px, area.x, area.y, area.x + area.width, area.y + area.height)


def side_by_side(a, b):
    h = min(a.shape[0], b.shape[0])
    gap = np.ones((h, 8, 4), np.float32)
    return np.concatenate([a[-h:], gap, b[-h:]], axis=1)


def region(area, kind='WINDOW'):
    return next(r for r in area.regions if r.type == kind)


def scroll_down(win, area, times):
    with bpy.context.temp_override(window=win, area=area, region=region(area)):
        for _ in range(times):
            bpy.ops.view2d.scroll_down(deltax=0, deltay=200)


def front_view(win, view, objects):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    with bpy.context.temp_override(window=win, area=view, region=region(view)):
        bpy.ops.view3d.view_axis(type='FRONT')
        bpy.ops.view3d.view_selected()


def clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    bpy.context.view_layer.update()


def select(objects, active):
    bpy.context.view_layer.update()  # objects just made join the view layer's list
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def issues(rig):
    return [(item.kind, item.part, item.role, item.below_waist) for item in rig.data.dasktoon_rig.issues]


def areas():
    screen = window().screen
    view = max((a for a in screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    properties = next(a for a in screen.areas if a.type == 'PROPERTIES')
    return view, properties


def steps():
    import dasktoon_rig_skeleton_test as st
    from dasktoon_animation import fast_action
    win = window()
    e = easy_keys.EventGenerate(win)
    yield datetime.timedelta(seconds=2.0)
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    bpy.context.preferences.view.language = LANGUAGE
    e.cursor_position_set(win.width // 2, 8, move=True)  # the status bar, away from tooltips

    # 90, 91. A chibi facing +X whose shins end flat: the Check asks which way to turn it.
    clear()
    body = st.polyline_chibi(st.CentreLineTest.ARM, st.CentreLineTest.LEG)
    body.matrix_world = st.turned(math.pi / 2.0, st.FacingTest.MIDDLE)
    select([body], body)
    log("add", bpy.ops.dasktoon.rig_add_humanoid())
    rig = bpy.context.view_layer.objects.active
    log("90 found", issues(rig))
    view, properties = areas()
    view.spaces.active.overlay.show_bones = True
    front_view(win, view, [body])
    select([rig], rig)
    yield datetime.timedelta(seconds=1.5)
    scroll_down(win, properties, SCROLL)
    yield datetime.timedelta(seconds=1.5)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "90_facing")
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("turn", bpy.ops.dasktoon.rig_turn_character(degrees=-90))
    log("91 found", issues(rig))
    front_view(win, view, [body])
    select([rig], rig)
    yield datetime.timedelta(seconds=1.5)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "91_turned")

    # 92, 93. Use DaskToon Shader from the material slot menu.
    clear()
    objs = fx.character()
    body = objs["Body"]
    material = bpy.data.materials.new("Skin")
    material.use_nodes = True
    tree = material.node_tree  # as a model brought in from elsewhere has it: Principled into the output
    tree.nodes.clear()
    principled = tree.nodes.new('ShaderNodeBsdfPrincipled')
    principled.inputs["Base Color"].default_value = (0.9, 0.62, 0.5, 1.0)
    tree.links.new(principled.outputs[0], tree.nodes.new('ShaderNodeOutputMaterial').inputs["Surface"])
    body.data.materials.append(material)
    select([body], body)
    yield datetime.timedelta(seconds=0.5)  # drawn once for the mesh, so it has a Material tab
    properties.spaces.active.context = 'MATERIAL'
    yield datetime.timedelta(seconds=1.0)
    e.cursor_position_set(properties.x + properties.width - 30, properties.y + properties.height - 120, move=True)
    yield datetime.timedelta(seconds=0.3)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        bpy.ops.wm.call_menu(name="MATERIAL_MT_context_menu")
    yield datetime.timedelta(seconds=0.7)
    px = grab()
    write(crop(px, properties.x - 260, properties.y, properties.x + properties.width, properties.y + properties.height),
          "92_material_menu")
    e.esc()
    yield datetime.timedelta(seconds=0.3)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("shader", bpy.ops.dasktoon.material_to_anime(scope='OBJECTS'))
    output = next(n for n in material.node_tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    log("93 surface", output.inputs["Surface"].links[0].from_node.bl_idname)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.0)
    write(area_shot(grab(), properties), "93_material_after")

    # 94 to 96. A character moving fast: the Fast Action popover, then Render (as F12 runs it), then the popover.
    clear()
    objs = fx.character()
    rig = fx.rig_for()
    from bl_ui import dasktoon_rig as ui
    from dasktoon_rig import build
    for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 12
    for frame, x in ((1, 0.0), (6, 3.0)):
        rig.location.x = x
        rig.keyframe_insert("location", index=0, frame=frame)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    camera.location = (1.5, -9.0, 0.55 * fx.HEIGHT)
    camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_percentage = 25
    rig.data.dasktoon_fast_action.enabled = True
    scene.frame_set(4)
    win.workspace = bpy.data.workspaces["Animation"]
    yield datetime.timedelta(seconds=1.0)
    select([objs["Body"]], objs["Body"])
    dopesheet = next(a for a in win.screen.areas if a.type == 'DOPESHEET_EDITOR')
    top = dopesheet.y + dopesheet.height
    e.cursor_position_set(dopesheet.x + dopesheet.width // 2, top - 14, move=True)
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=dopesheet, region=region(dopesheet, 'HEADER')):
        bpy.ops.wm.call_panel(name="DASKTOON_PT_fast_action", keep_open=False)
    yield datetime.timedelta(seconds=0.7)
    write(crop(grab(), dopesheet.x, top - 520, dopesheet.x + dopesheet.width, top), "94_fast_action")
    e.esc()
    yield datetime.timedelta(seconds=0.3)
    log("94 baked", fast_action.baked(rig))
    main = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width)
    with bpy.context.temp_override(window=win, area=main, region=region(main)):
        log("render", bpy.ops.dasktoon.render('INVOKE_DEFAULT', use_viewport=True))
    yield datetime.timedelta(seconds=4.0)
    log("95 baked", fast_action.baked(rig),
        "needs", fast_action.needs_bake(bpy.context, rig, list(bpy.context.view_layer.objects)))
    result = bpy.data.images.get("Render Result")
    log("95 render result", result is not None)
    if result is not None:
        path = os.path.join(OUT, "95_render.png")
        result.save_render(path)
        log("saved", "95_render")
    for other in list(bpy.context.window_manager.windows)[1:]:  # the render window
        with bpy.context.temp_override(window=other):
            bpy.ops.wm.window_close()
    yield datetime.timedelta(seconds=0.5)
    e.cursor_position_set(dopesheet.x + dopesheet.width // 2, top - 14, move=True)
    yield datetime.timedelta(seconds=0.3)
    with bpy.context.temp_override(window=win, area=dopesheet, region=region(dopesheet, 'HEADER')):
        bpy.ops.wm.call_panel(name="DASKTOON_PT_fast_action", keep_open=False)
    yield datetime.timedelta(seconds=0.7)
    write(crop(grab(), dopesheet.x, top - 520, dopesheet.x + dopesheet.width, top), "96_fast_action_baked")
    e.esc()
    yield datetime.timedelta(seconds=0.3)

    # 97, 98. A dress rigged by hand: the Check finds its part below the waist looks like a skirt.
    win.workspace = bpy.data.workspaces["Layout"]
    yield datetime.timedelta(seconds=1.0)
    clear()
    rig, objs, _parts = rt.character(reset=False)
    dress = rt.merged("Circle.011", [rt.st.tube((0, 0, 1.4), (0, 0, 1.0), 0.21),
                                     rt.st.tube((0, 0, 1.0), (0, 0, 0.62), 0.22)])
    for v in dress.data.vertices:
        if v.co.z < 0.8:
            v.co.x *= 1.4
            v.co.y *= 1.4
    for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Boots", 'CLOTHING')):
        ui.add_part(rig, objs[name], role)
    ui.add_part(rig, dress, 'CLOTHING')
    select([rig], rig)
    view, properties = areas()
    yield datetime.timedelta(seconds=0.5)  # drawn once for the rig
    properties.spaces.active.context = 'DATA'
    yield datetime.timedelta(seconds=0.5)
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("build", bpy.ops.dasktoon.rig_build())
        log("check", bpy.ops.dasktoon.rig_check())
    log("97 found", issues(rig))
    front_view(win, view, list(objs.values()) + [dress])
    select([rig], rig)
    e.cursor_position_set(win.width // 2, 8, move=True)
    yield datetime.timedelta(seconds=1.5)
    scroll_down(win, properties, SCROLL)
    yield datetime.timedelta(seconds=1.5)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "97_skirt_check")
    with bpy.context.temp_override(window=win, area=properties, region=region(properties)):
        log("skirt", bpy.ops.dasktoon.rig_skirt_below_waist(part="Circle.011"))
    log("98 found", issues(rig), [(p.name, p.role, p.scope) for p in rig.data.dasktoon_rig.parts])
    yield datetime.timedelta(seconds=1.5)
    px = grab()
    write(side_by_side(area_shot(px, properties), area_shot(px, view)), "98_skirt_made")
    log("done")
    LOG.close()
    bpy.ops.wm.quit_blender()


def on_error():
    log("ERROR, see the console")
    LOG.close()
    bpy.ops.wm.quit_blender()


easy_keys.run(steps(), on_error=on_error)
