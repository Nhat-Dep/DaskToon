# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Pictures for the Guide's feature pages (docs/guide-writing/rules.md, section 5), made from test
characters in tests/python (never a user model), without text.

DaskToon.exe -b --factory-startup --python tools/dasktoon_feature_pictures.py [-- <name>]

Writes to scripts/modules/dasktoon_guide/pages/pictures/:
- outline.png: without outline, then with outline.
- face-shading.png: head with bumpy cel shadows, then with egg-shaped face shading.
"""
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import dasktoon_guide_checks_test as gt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
from bl_ui import dasktoon_outline as ot  # noqa: E402

OUT = os.path.join(REPO, "scripts", "modules", "dasktoon_guide", "pages", "pictures")
WORK = tempfile.mkdtemp(prefix="dt_feature_pictures_")
PANEL = (300, 400)
SKIN_COLOR = (0.95, 0.80, 0.72, 1.0)
INK_COLOR = (0.10, 0.05, 0.05, 1.0)
FLOOR_COLOR = (0.6, 0.6, 0.6, 1.0)
THREE_QUARTER = (-0.55, -1.0, 0.35)


def box(name, centre, half, color):
    mesh = bpy.data.meshes.new(name)
    x, y, z = half
    verts = [(centre[0] + sx * x, centre[1] + sy * y, centre[2] + sz * z)
             for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    mesh.from_pydata(verts, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                                 (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    obj = bpy.data.objects.new(name, mesh)
    mat = bpy.data.materials.new(name + "_Mat")
    mat.diffuse_color = color
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def stage_floor():
    box("Floor", (0, 0, -0.005), (1.6, 1.6, 0.005), FLOOR_COLOR)
    box("X", (0, 0, 0.002), (1.6, 0.006, 0.002), (0.85, 0.2, 0.2, 1.0))
    box("Y", (0, 0, 0.002), (0.006, 1.6, 0.002), (0.4, 0.75, 0.2, 1.0))


def shoot_workbench(target, direction, scale):
    scene = bpy.context.scene
    cam = scene.camera
    direction = Vector(direction).normalized()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = scale
    cam.location = Vector(target) + direction * 10
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    path = os.path.join(WORK, "panel.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def write_image(panels, name):
    h = panels[0].shape[0]
    gap = np.ones((h, 8, 4), np.float32)
    rows = [panels[0]]
    for panel in panels[1:]:
        rows += [gap, panel]
    px = np.concatenate(rows, axis=1)
    img = bpy.data.images.new(name, px.shape[1], h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    target_path = os.path.join(OUT, name + ".png")
    img.filepath_raw = target_path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    size_kb = os.path.getsize(target_path) / 1024
    print("Saved %s.png: %dx%d (%.1f KB)" % (name, px.shape[1], h, size_kb))


def eevee_scene(world, sun_strength, sun_rotation):
    """A scene rendered with EEVEE (Workbench draws neither the anime shader nor the outline hull), a Sun and a camera."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = PANEL
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.eevee.taa_render_samples = 16
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    tu.set_world_color(world)
    sun = tu.add_sun(sun_strength)
    sun.rotation_euler = sun_rotation
    sun.data.use_shadow = False
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.type = 'ORTHO'
    cam.data.clip_start, cam.data.clip_end = 0.01, 100.0
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def shoot(scene, name):
    path = os.path.join(WORK, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    px = np.empty(PANEL[0] * PANEL[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(PANEL[1], PANEL[0], 4)


def outline_picture():
    """The test character with the Anime BSDF, without the outline, then with a thick one."""
    body = gt.good()
    scene, cam = eevee_scene((0.55, 0.58, 0.65), 2.5, (math.radians(55.0), 0.0, math.radians(-35.0)))
    cam.data.ortho_scale = 2.4
    direction = Vector(THREE_QUARTER).normalized()
    target = Vector((0.0, 0.0, 0.95))
    cam.location = target + direction * 10.0
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    mat = body.material_slots[0].material
    node = mat.node_tree.nodes['Anime BSDF']
    node.inputs["Base Color"].default_value = SKIN_COLOR
    node.use_outline = True
    node.inputs["Outline Width"].default_value = 0.012
    node.use_outline = False
    ot.sync_all(scene)
    before = shoot(scene, "outline_before")
    node.use_outline = True
    ot.sync_all(scene)
    after = shoot(scene, "outline_after")
    write_image([before, after], "outline")


BUMPS = ((0.0, 0.3, 0.45, 0.12, 0.05),
         (-0.45, -0.05, 0.2, 0.15, 0.06),
         (0.45, -0.05, 0.2, 0.15, 0.06),
         (0.0, -0.42, 0.2, 0.08, 0.04),
         (0.0, -0.72, 0.25, 0.15, 0.05))


def face_shading_picture():
    scene = tu.reset_scene(PANEL[0])
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = PANEL
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.eevee.taa_render_samples = 16

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.8
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    cam.location = (0.0, -10.0, 0.0)
    scene.collection.objects.link(cam)
    scene.camera = cam

    tu.set_world_color((0.05, 0.06, 0.08))
    sun = tu.add_sun(3.0)
    sun.rotation_euler = (math.radians(60.0), 0.0, math.radians(-40.0))
    sun.data.use_shadow = False

    head, _rig = tu.add_test_head(radius=1.0, centre=(0.0, 0.0, 0.0))
    rng = np.random.default_rng(7)
    for v in head.data.vertices[:head['dt_skin_vertices']]:
        d = v.co.normalized()
        if d.y < 0.0:
            lump = sum(h * max(0.0, 1.0 - ((d.x - x) / w) ** 2 - ((d.z - z) / t) ** 2)
                       for x, z, w, t, h in BUMPS)
            v.co += d * (lump + 0.012 * -d.y * rng.standard_normal())

    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.inputs["Base Color"].default_value = SKIN_COLOR
    tu.assign(head, mat)
    fs.setup(head)

    modifier = fsn.get_modifier(head)

    # Panel 1: before (lumpy cel shadows)
    modifier.show_viewport = modifier.show_render = False
    path_before = os.path.join(WORK, "fs_before.png")
    scene.render.filepath = path_before
    bpy.ops.render.render(write_still=True)
    img_b = bpy.data.images.load(path_before, check_existing=False)
    px_b = np.empty(PANEL[0] * PANEL[1] * 4, dtype=np.float32)
    img_b.pixels.foreach_get(px_b)
    bpy.data.images.remove(img_b)

    # Panel 2: after (smooth egg proxy shadows)
    modifier.show_viewport = modifier.show_render = True
    path_after = os.path.join(WORK, "fs_after.png")
    scene.render.filepath = path_after
    bpy.ops.render.render(write_still=True)
    img_a = bpy.data.images.load(path_after, check_existing=False)
    px_a = np.empty(PANEL[0] * PANEL[1] * 4, dtype=np.float32)
    img_a.pixels.foreach_get(px_a)
    bpy.data.images.remove(img_a)

    write_image([px_b.reshape(PANEL[1], PANEL[0], 4), px_a.reshape(PANEL[1], PANEL[0], 4)], "face-shading")


def shader_picture():
    """Three spheres with the Anime BSDF: Simple shading, the Anime 3-Tone ramp, the Soft Painted ramp."""
    from bl_ui import dasktoon_shading_styles as styles
    scene = tu.reset_scene(PANEL[0])
    scene, cam = eevee_scene((0.12, 0.13, 0.16), 3.0, (math.radians(55.0), 0.0, math.radians(-35.0)))
    cam.data.ortho_scale = 2.6
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    panels = []
    for style in (None, "Anime 3-Tone", "Soft Painted"):
        for obj in [o for o in scene.objects if o.type == 'MESH']:
            bpy.data.objects.remove(obj)
        sphere = tu.add_sphere(radius=0.9)
        mat, node = tu.node_material("Ball", 'ShaderNodeAnimeCharacter')
        node.inputs["Base Color"].default_value = (0.9, 0.55, 0.55, 1.0)
        if style:
            node.shading_mode = 'RAMP'
            styles.apply_style(node.shading_ramp, styles.BUILTIN_STYLES[style])
        tu.assign(sphere, mat)
        cam.location = (0.0, -10.0, 0.0)
        panels.append(shoot(scene, "shader_%s" % style))
    write_image(panels, "shader")


def finish_picture():
    """The test character as rendered, then with the Illustration Finish on in the Sunset style."""
    from dasktoon_finish import styles as finish_styles
    body = gt.good()
    scene, cam = eevee_scene((0.10, 0.11, 0.16), 2.5, (math.radians(55.0), 0.0, math.radians(-35.0)))
    cam.data.ortho_scale = 2.4
    direction = Vector(THREE_QUARTER).normalized()
    cam.location = Vector((0.0, 0.0, 0.95)) + direction * 10.0
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    mat = body.material_slots[0].material
    mat.node_tree.nodes['Anime BSDF'].inputs["Base Color"].default_value = (0.85, 0.55, 0.5, 1.0)
    scene.render.use_compositing = True
    before = shoot(scene, "finish_before")
    finish = scene.dasktoon_finish
    finish.enabled = True
    for key, value in finish_styles.style_values("Sunset").items():
        setattr(finish, key, value)
    after = shoot(scene, "finish_after")
    write_image([before, after], "finish")


PICTURES = {
    "outline": outline_picture,
    "face-shading": face_shading_picture,
    "shader": shader_picture,
    "finish": finish_picture,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    targets = [a for a in args if a in PICTURES] or list(PICTURES.keys())
    for name in targets:
        PICTURES[name]()


if __name__ == "__main__":
    main()
