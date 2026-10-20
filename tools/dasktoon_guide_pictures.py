# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The pictures of the Guide's pages (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md), made from the
test characters (never a user's), in the Solid look a newcomer sees while modelling, without text (the pages' captions
say what each panel shows, in both languages).

DaskToon.exe -b --factory-startup --python tools/dasktoon_guide_pictures.py

writes scripts/modules/dasktoon_guide/pages/pictures/:

- body.png: the test chibi as it should stand, then floating off the middle, turned to the back, its arms down;
- head.png: the eye pieces in front of the face, from the front and from the side;
- rig.png: after the auto rig, at rest, then its left knee and elbow bent (the bend fixes on);
- expressions.png: after Sculpt Eye Expressions: at rest, blink, joy.
"""
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "python"))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_guide_checks_test as gt  # noqa: E402
from dasktoon_guide import fixes  # noqa: E402
from dasktoon_rig import correctives, eye_shapes  # noqa: E402

OUT = os.path.join(REPO, "scripts", "modules", "dasktoon_guide", "pages", "pictures")
WORK = tempfile.mkdtemp(prefix="dt_guide_pictures_")
PANEL = (300, 400)
SKIN, CLOTH, EYE, FLOOR = (0.95, 0.8, 0.7, 1), (0.45, 0.55, 0.8, 1), (0.15, 0.2, 0.35, 1), (0.6, 0.6, 0.6, 1)


def stage(objects):
    """Solid look, a floor with the red X and green Y lines of the viewport's grid."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.show_shadows = False
    scene.view_settings.view_transform = 'Standard'
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.82, 0.84, 0.88)
    scene.render.resolution_x, scene.render.resolution_y = PANEL
    scene.render.resolution_percentage = 100
    for obj in objects:
        obj.color = SKIN if obj.type == 'MESH' else obj.color
    box("Floor", (0, 0, -0.005), (1.6, 1.6, 0.005), FLOOR)
    box("X", (0, 0, 0.002), (1.6, 0.006, 0.002), (0.85, 0.2, 0.2, 1))
    box("Y", (0, 0, 0.002), (0.006, 1.6, 0.002), (0.4, 0.75, 0.2, 1))
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.type = 'ORTHO'
    scene.collection.objects.link(cam)
    scene.camera = cam


def box(name, centre, half, color):
    mesh = bpy.data.meshes.new(name)
    x, y, z = half
    verts = [(centre[0] + sx * x, centre[1] + sy * y, centre[2] + sz * z)
             for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    mesh.from_pydata(verts, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    obj = bpy.data.objects.new(name, mesh)
    obj.color = color
    bpy.context.scene.collection.objects.link(obj)
    return obj


def shoot(target, direction, scale):
    """Render the camera looking at `target` from `direction`, `scale` metres across; the pixels."""
    scene = bpy.context.scene
    cam = scene.camera
    direction = Vector(direction).normalized()
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


def write(panels, name):
    h = panels[0].shape[0]
    gap = np.ones((h, 8, 4), np.float32)
    rows = [panels[0]]
    for panel in panels[1:]:
        rows += [gap, panel]
    px = np.concatenate(rows, axis=1)
    img = bpy.data.images.new(name, px.shape[1], h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    print("saved", name, px.shape[1], h)


THREE_QUARTER = (-0.55, -1.0, 0.35)  # from the front (-Y), the character's right, a little above


def body_picture():
    panels = []
    for variant in ("right", "floating", "turned", "arms down"):
        body = gt.good(arm=gt.HANGING if variant == "arms down" else gt.ARM)
        if variant == "floating":
            body.location = (0.45, 0.35, 0.3)
        if variant == "turned":
            body.rotation_euler.z = math.pi
        stage([body])
        panels.append(shoot((0, 0, 0.95), THREE_QUARTER, 2.6))
    write(panels, "body")


def head_view(rig):
    centre, size = et.head_frame(rig)
    return rig.matrix_world @ (centre + Vector((0, 0, -0.1 * size))), size


def colour_face(objs, eyes):
    for obj in objs.values():
        obj.color = CLOTH if obj.name in ("Shirt", "Boots") else SKIN
    eyes.color = EYE


def head_picture():
    rig, objs, eyes = et.character()
    stage(list(objs.values()))
    colour_face(objs, eyes)
    target, size = head_view(rig)
    write([shoot(target, (0, -1, 0.05), size * 2.6), shoot(target, (0.8, -0.6, 0.9), size * 2.6)], "head")


def rig_picture():
    body = gt.good()
    fixes.run(bpy.context, "rig", [body])
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
    stage([body])
    panels = [shoot((0, 0, 0.95), THREE_QUARTER, 2.6)]
    for fix in correctives.fixes(rig):
        if fix.name in ("LeftKnee", "LeftElbow"):
            bone = rig.pose.bones[fix.child]
            bone.rotation_mode = 'QUATERNION'
            frame = rig.data.bones[fix.child].matrix_local.to_3x3()
            turn = frame.inverted() @ Matrix.Rotation(fix.angle, 3, fix.axis) @ frame
            bone.rotation_quaternion = turn.to_quaternion()
    bpy.context.view_layer.update()
    panels.append(shoot((0, 0, 0.95), (0.9, -0.8, 0.3), 2.6))
    write(panels, "rig")


def expressions_picture():
    rig, objs, eyes = et.character()
    meshes = list(objs.values()) + [eyes]
    eye_shapes.sculpt(rig, meshes)
    stage(meshes)
    colour_face(objs, eyes)
    target, size = head_view(rig)
    panels = []
    for name in ("", "blink", "joy"):
        for obj in meshes:
            key = obj.data.shape_keys
            for block in key.key_blocks if key else ():
                if block != key.reference_key and not block.name.startswith(correctives.PREFIX):
                    block.value = 1.0 if block.name == name else 0.0
        bpy.context.view_layer.update()
        panels.append(shoot(target, (0, -1, 0.05), size * 2.2))
    write(panels, "expressions")


os.makedirs(OUT, exist_ok=True)
for make in (body_picture, head_picture, rig_picture, expressions_picture):
    make()
