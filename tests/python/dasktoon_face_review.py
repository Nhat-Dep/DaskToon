# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Before / after sheet of DaskToon face shading for human review (not an automated test, face spec 8).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_face_review.py [-- <character.blend>]

Rows, top to bottom: the test head without / with face shading, then (when a .blend is given) the character's head
without / with. Columns: three Sun angles. The .blend is opened read-only and never saved.
Writes docs/superpowers/reports/2026-10-04-face-shading-review.png."""

import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
from dasktoon_export import textures  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(REPO, "docs", "superpowers", "reports", "2026-10-04-face-shading-review.png")
SIZE = 256
# Sun rotations: key light from the front left and above, front right and lower, then a side light.
SUNS = ((math.radians(60.0), 0.0, math.radians(-40.0)),
        (math.radians(75.0), 0.0, math.radians(30.0)),
        (math.radians(40.0), 0.0, math.radians(-100.0)))


def srgb(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def prepare_render(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.eevee.taa_render_samples = 16
    if scene.camera is None:
        cam = bpy.data.objects.new("ReviewCamera", bpy.data.cameras.new("ReviewCamera"))
        scene.collection.objects.link(cam)
        scene.camera = cam


def front_camera(scene, centre, scale):
    cam = scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = scale
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100.0
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)  # looks along +Y, at the face
    cam.location = (centre.x, centre.y - 10.0, centre.z)


def render(name):
    pixels, (w, h) = tu.render_pixels(name)
    return np.array(pixels).reshape(h, w, 4)


def before_after(faced, sun, tag):
    """[[tiles without face shading], [tiles with]] over the Sun angles."""
    rows = []
    for on in (False, True):
        for obj in faced:
            modifier = fsn.get_modifier(obj)
            modifier.show_viewport = modifier.show_render = on
        tiles = []
        for i, rotation in enumerate(SUNS):
            sun.rotation_euler = rotation
            tiles.append(render("%s_%d_%d" % (tag, on, i)))
        rows.append(tiles)
    return rows


# Bumps on the front of the review head: (direction x, direction z, half width, half height, height).
BUMPS = ((0.0, 0.3, 0.45, 0.12, 0.05),        # brow ridge
         (-0.45, -0.05, 0.2, 0.15, 0.06),     # cheekbones
         (0.45, -0.05, 0.2, 0.15, 0.06),
         (0.0, -0.42, 0.2, 0.08, 0.04),       # lips
         (0.0, -0.72, 0.25, 0.15, 0.05))      # chin


def roughen(head):
    """A lumpy face on the test head (unit radius, centred at the origin): the messy cel shadows face shading fixes."""
    rng = np.random.default_rng(7)
    for v in head.data.vertices[:head["dt_skin_vertices"]]:
        d = v.co.normalized()
        if d.y < 0.0:
            lump = sum(h * max(0.0, 1.0 - ((d.x - x) / w) ** 2 - ((d.z - z) / t) ** 2) for x, z, w, t, h in BUMPS)
            v.co += d * (lump + 0.012 * -d.y * rng.standard_normal())


def test_head_rows():
    scene = tu.reset_scene(SIZE)
    prepare_render(scene)
    tu.set_world_color((0.05, 0.06, 0.08))
    sun = tu.add_sun(3.0)
    sun.data.use_shadow = False
    head, _rig = tu.add_test_head(radius=1.0, centre=(0.0, 0.0, 0.0))
    roughen(head)
    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.inputs["Base Color"].default_value = (0.95, 0.80, 0.72, 1.0)
    tu.assign(head, mat)
    fs.setup(head)
    front_camera(scene, Vector((0.0, 0.0, 0.0)), 2.8)
    return before_after([head], sun, "head")


def face_mesh(scene):
    """(mesh, armature): among meshes weighted to a head bone, the one with the most forward vertex in the middle strip
    of its head (the face skin, face spec 5.3)."""
    best = None
    for obj in scene.objects:
        if obj.type != 'MESH' or not obj.visible_get():
            continue
        armature = fs.find_armature(obj)
        bone = fs.find_head_bone(armature) if armature is not None else None
        if bone is None:
            continue
        try:
            head = fs.head_vertices(obj, bone)
        except fs.FaceShadingError:
            continue
        with fs.rest_pose([armature]):
            world = np.array([tuple(obj.matrix_world @ obj.data.vertices[i].co) for i in head])
        low, high = world[:, 0].min(), world[:, 0].max()
        middle = world[np.abs(world[:, 0] - (low + high) / 2.0) <= 0.25 * (high - low)]
        front = middle[:, 1].min()
        if best is None or front < best[0]:
            best = (front, obj, armature)
    return (best[1], best[2]) if best else (None, None)


def face_from_shape_keys(scene):
    """Without a head bone (a character without a rig): the mesh with the most shape keys and, as its head, every
    vertex at or above the lowest vertex its expressions move, which is what a user would select in Edit Mode."""
    meshes = [o for o in scene.objects if o.type == 'MESH' and o.visible_get() and o.data.shape_keys is not None]
    if not meshes:
        return None, None
    obj = max(meshes, key=lambda o: len(o.data.shape_keys.key_blocks))
    keys = obj.data.shape_keys.key_blocks
    basis = np.array([tuple(p.co) for p in keys[0].data])
    moved = np.zeros(len(basis), dtype=bool)
    for key in keys[1:]:
        moved |= np.linalg.norm(np.array([tuple(p.co) for p in key.data]) - basis, axis=1) > 1e-5
    if not moved.any():
        return None, None
    world = np.array([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices])
    lowest, highest = world[moved, 2].min(), world[moved, 2].max()
    return obj, np.flatnonzero(world[:, 2] >= lowest - 0.15 * (highest - lowest))


def character_rows(path):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    scene = bpy.context.scene
    face, armature = face_mesh(scene)
    selected = None
    if face is None:
        face, selected = face_from_shape_keys(scene)
    if face is None:
        print("REVIEW: no face mesh found in", path)
        return []
    print("REVIEW: face mesh", face.name, "armature", armature.name if armature else None,
          "selected", None if selected is None else len(selected))
    proxy = fs.setup(face, selected=selected)
    print("REVIEW: proxy", proxy.name, "at", tuple(round(c, 3) for c in proxy.matrix_world.translation),
          "radii", tuple(round(c, 3) for c in proxy.matrix_world.to_scale()))
    prepare_render(scene)
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            obj.hide_render = True
    sun = tu.add_sun(3.0)
    sun.data.use_shadow = False
    bpy.context.view_layer.update()
    centre = proxy.matrix_world.translation
    front_camera(scene, centre, 3.2 * max(proxy.matrix_world.to_scale()))
    return before_after([face], sun, "character")


def write_sheet(rows):
    height, width = SIZE * len(rows), SIZE * len(SUNS)
    sheet = np.zeros((height, width, 4))
    for r, tiles in enumerate(rows):
        y0 = height - (r + 1) * SIZE
        for c, tile in enumerate(tiles):
            sheet[y0:y0 + SIZE, c * SIZE:(c + 1) * SIZE] = tile
    sheet[..., :3] = srgb(sheet[..., :3])
    sheet[..., 3] = 1.0
    data = (np.clip(sheet, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    with open(SHEET, "wb") as f:
        f.write(textures.png_bytes(width, height, data))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rows = test_head_rows()
    if argv:
        rows += character_rows(argv[0])
    write_sheet(rows)
    print("REVIEW SHEET", SHEET)


main()
