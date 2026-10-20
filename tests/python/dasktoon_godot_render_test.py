# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon (EEVEE) vs Godot 4 renders of the same spheres (Godot spec 5, wave 1: Anime BSDF and the outline), with the
cases and the measures of the Unity comparison: cel and diffuse within 0.03 on sRGB values, outline width and colour.
AO is reported only (Godot gives custom shading no ambient occlusion). Godot opens a small window to draw."""

import json
import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_godot_harness as harness  # noqa: E402
import dasktoon_unity_render_test as unity_render  # noqa: E402  (the cases and measures of the Unity comparison)
from bl_ui import dasktoon_outline as outline  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets, textures  # noqa: E402

MODEL_NAME = "DTCompare"
CASES = [case for case in unity_render.CASES
         if case[0].startswith(("bsdf_", "outline_")) or case[0] == unity_render.FACE_CASE]


def to_godot(v):
    return [v[0], v[2], -v[1]]


def linear(srgb):
    return np.where(srgb <= 0.04045, srgb / 12.92, np.power((srgb + 0.055) / 1.055, 2.4))


def build_scene():
    tu.reset_scene(unity_render.RES)
    outline.reset_cache()
    scene = bpy.context.scene
    scene.eevee.taa_render_samples = 16
    tu.set_world_color(unity_render.WORLD)
    sun = tu.add_sun(unity_render.SUN_STRENGTH, unity_render.SUN_ROTATION, unity_render.SUN_COLOR)
    sun.data.use_shadow = False
    cam = scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = unity_render.ORTHO_SCALE
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    spheres = []
    for i, (name, builder, _graded) in enumerate(CASES):
        location = (i * unity_render.SPACING, 0.0, 0.0)
        if name == unity_render.FACE_CASE:
            obj = unity_render.face_head(location)
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=48, ring_count=24, location=location)
            obj = bpy.context.active_object
            obj.data.shade_smooth()
        obj.name = "Case_" + name
        tu.assign(obj, builder())
        spheres.append(obj)
    outline.sync_all(scene)
    return scene, sun, cam, spheres


def load_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    pixels = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    pixels[..., :3] = linear(pixels[..., :3])  # Godot saves what it shows (sRGB); the measures take linear values
    return pixels


def write_sheet(rows, path):
    """One row per case: DaskToon | Godot | |difference| x 5."""
    res = unity_render.RES
    height = res * len(rows)
    sheet = np.zeros((height, res * 3, 4))
    for i, (blender, godot) in enumerate(rows):
        y0 = height - (i + 1) * res
        sheet[y0:y0 + res, 0:res] = blender
        sheet[y0:y0 + res, res:2 * res] = godot
        diff = np.abs(unity_render.srgb(blender[..., :3]) - unity_render.srgb(godot[..., :3])) * 5.0
        sheet[y0:y0 + res, 2 * res:3 * res, :3] = diff
        sheet[y0:y0 + res, 2 * res:3 * res, 3] = 1.0
    sheet[..., :3] = np.where(np.arange(3 * res)[None, :, None] < 2 * res, unity_render.srgb(sheet[..., :3]),
                              sheet[..., :3])
    data = (np.clip(sheet, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    with open(path, "wb") as f:
        f.write(textures.png_bytes(res * 3, height, data))


@unittest.skipUnless(harness.godot_exe(), harness.SKIP_REASON)
class GodotRenderTest(unittest.TestCase):
    def test_godot_matches_dasktoon(self):
        root = harness.new_project("dasktoon_godot_render")
        scene, sun, cam, spheres = build_scene()
        blender = unity_render.render_blender(scene, cam, spheres)
        target = targets.make_target(root, MODEL_NAME, 'GODOT_4')
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=64, bake_samples=4,
                                                merge_meshes=False)
        rep = dasktoon_export.export_model(bpy.context, target, spheres, options)
        self.assertEqual(len(rep.materials), len(CASES), rep.lines())
        harness.import_project(root)
        light_dir = sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        out_dir = os.path.join(tu.OUT_DIR, "godot_renders")
        os.makedirs(out_dir, exist_ok=True)
        result, output = harness.run_script(root, "dasktoon_render", {
            "model": "res://DaskToon/%s/%s.glb" % (MODEL_NAME, MODEL_NAME),
            "cases": [{"name": name, "obj": "Case_" + name, "camPos": to_godot((i * unity_render.SPACING, -5.0, 0.0))}
                      for i, (name, _builder, _graded) in enumerate(CASES)],
            "resolution": unity_render.RES,
            "orthoSize": unity_render.ORTHO_SCALE,
            "lightDir": to_godot(light_dir.normalized()),
            "lightEnergy": unity_render.SUN_STRENGTH / math.pi,
            "lightColor": [float(unity_render.srgb(c)) for c in unity_render.SUN_COLOR],
            "outDir": out_dir.replace("\\", "/"),
        }, headless=False)
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(harness.shader_errors(output), [], output[-4000:])
        table, failures, rows = {}, [], []
        for name, _builder, graded in CASES:
            godot = load_png(result["outputs"][name])
            worst, used, skipped = unity_render.compare(blender[name], godot)
            table[name] = {"max_diff": round(worst, 4), "points": used, "edge_points": skipped, "graded": graded}
            rows.append((blender[name], godot))
            if graded and (worst > unity_render.TOLERANCE or used < 0.6 * (used + skipped)):
                failures.append(name)
            if name.startswith("outline_"):
                width_diff, colour_diff, thinnest = unity_render.compare_outline(blender[name], godot)
                table[name].update(outline_width_diff_px=width_diff, outline_colour_diff=round(colour_diff, 4),
                                   outline_thinnest_px=thinnest)
                if (width_diff > unity_render.OUTLINE_WIDTH_TOLERANCE
                        or colour_diff > unity_render.OUTLINE_COLOUR_TOLERANCE or thinnest < 1.0):
                    failures.append(name + " (outline)")
        sheet = os.path.join(tu.OUT_DIR, "godot_compare.png")
        write_sheet(rows, sheet)
        print("Godot comparison sheet:", sheet)
        print(json.dumps(table, indent=2))
        self.assertEqual(failures, [], json.dumps(table, indent=2))


if __name__ == "__main__":
    tu.run_tests()
