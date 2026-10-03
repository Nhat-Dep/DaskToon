# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon (EEVEE) vs Unity URP renders of the same spheres (spec 8): cel and diffuse within 0.03 on sRGB values,
specular and AO reported only. Writes a side-by-side sheet for the user to review."""

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
import dasktoon_unity_harness as harness  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import shaders_install, targets, textures  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(REPO, "docs", "superpowers", "reports", "2026-10-03-unity-compare.png")
RES = 128
SPACING = 3.0
ORTHO_SCALE = 1.4
SUN_STRENGTH = 3.0
SUN_COLOR = (1.0, 0.9, 0.8)
SUN_ROTATION = (math.radians(50.0), 0.0, math.radians(30.0))
WORLD = (0.05, 0.06, 0.08)
TOLERANCE = 0.03
EDGE = 0.05
OUTLINE_WIDTH_TOLERANCE = 1.5   # px; EEVEE's film filter softens the line edges, Unity renders without AA
OUTLINE_COLOUR_TOLERANCE = 0.08
MODEL_NAME = "DTCompare"


def to_unity(v):
    return [-v[0], v[2], -v[1]]


def srgb(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def bsdf(name, **props):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeCharacter')
    for key, value in props.items():
        setattr(node, key, value)
    return mat, node


def with_style(mat_node, style):
    mat, node = mat_node
    node.shading_mode = 'RAMP'
    styles.apply_style(node.shading_ramp, styles.BUILTIN_STYLES[style])
    return mat


def anime_cel(name, spec_size=0.0, style=None):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeCel')
    node.inputs["Specular Size"].default_value = spec_size
    if style:
        with_style((mat, node), style)
    return mat


def ambient_world():
    mat, node = bsdf("bsdf_ambient_world", use_ambient=True, ambient_mode='HUE_SAT')
    node.inputs["Use Custom Color"].default_value = False
    node.inputs["Ambient Factor"].default_value = 0.6
    return mat


def hair():
    mat = tu.new_material("hair")
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emission = nt.nodes.new('ShaderNodeEmission')
    cel = nt.nodes.new('ShaderNodeAnimeCel')
    cel.inputs["Specular Size"].default_value = 0.0
    ring = nt.nodes.new('ShaderNodeAnimeAngelRing')
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'ADD'
    sockets = {s.identifier: s for s in mix.inputs}
    nt.links.new(cel.outputs["Color"], sockets["A_Color"])
    nt.links.new(ring.outputs["Color"], sockets["B_Color"])
    nt.links.new(ring.outputs["Fac"], sockets["Factor_Float"])
    nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), emission.inputs["Color"])
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat


def eye():
    mat, node = tu.node_material("eye", 'ShaderNodeAnimeEye')
    coords = mat.node_tree.nodes.new('ShaderNodeTexCoord')
    mat.node_tree.links.new(coords.outputs["UV"], node.inputs["UV Vector"])
    return mat


def outlined(name, tint_mode='CUSTOM', bleed=0.0, wobble=0.0):
    """Anime BSDF with the thickest outline, so its width can be measured in pixels."""
    mat, node = bsdf(name, use_outline=True, outline_tint_mode=tint_mode)
    node.inputs["Outline Width"].default_value = 0.05
    node.inputs["Outline Color"].default_value = (0.0, 0.0, 0.5, 1.0)
    node.inputs["Outline Lighting Mix"].default_value = 0.0
    outline.sync_material(mat)
    dask = outline.outline_node(outline.outline_material_for(mat))
    dask.inputs["Light Bleed"].default_value = bleed
    dask.inputs["Hand Wobble"].default_value = wobble
    return mat


def dask_cel(name, style=None):
    mat, node = tu.node_material(name, 'ShaderNodeDaskCel')
    if style:
        with_style((mat, node), style)
    return mat


# (case, material builder, graded)
CASES = [
    ("bsdf_simple", lambda: bsdf("bsdf_simple")[0], True),
    ("bsdf_ambient_custom", lambda: bsdf("bsdf_ambient_custom", use_ambient=True)[0], True),
    ("bsdf_ambient_world", ambient_world, True),
    ("bsdf_light_overlay", lambda: bsdf("bsdf_light_overlay", use_light=True)[0], True),
    ("bsdf_light_multiply", lambda: bsdf("bsdf_light_multiply", use_light=True, light_blend_mode='MULTIPLY')[0], True),
    ("bsdf_rim", lambda: bsdf("bsdf_rim", use_rim=True)[0], True),
    ("bsdf_grade", lambda: bsdf("bsdf_grade", use_grade=True)[0], True),
    ("bsdf_ramp_3tone", lambda: with_style(bsdf("bsdf_ramp_3tone"), "Anime 3 tông"), True),
    ("bsdf_ramp_soft", lambda: with_style(bsdf("bsdf_ramp_soft"), "Mềm như vẽ"), True),
    ("bsdf_ao", lambda: bsdf("bsdf_ao", use_ao=True)[0], False),
    ("cel_simple", lambda: anime_cel("cel_simple"), True),
    ("cel_ramp", lambda: anime_cel("cel_ramp", style="Anime 2 tông"), True),
    ("cel_spec", lambda: anime_cel("cel_spec", spec_size=0.08), False),
    ("hair", hair, True),
    ("eye", eye, True),
    ("daskcel_simple", lambda: dask_cel("daskcel_simple"), True),
    ("daskcel_manga", lambda: dask_cel("daskcel_manga", style="Manga"), True),
    ("outline_custom", lambda: outlined("outline_custom"), True),
    ("outline_harmonic", lambda: outlined("outline_harmonic", 'HARMONIC_KYOTO', 0.7, 0.15), True),
]


def build_scene():
    tu.reset_scene(RES)
    outline.reset_cache()
    scene = bpy.context.scene
    scene.eevee.taa_render_samples = 16
    tu.set_world_color(WORLD)
    sun = tu.add_sun(SUN_STRENGTH, SUN_ROTATION, SUN_COLOR)
    sun.data.use_shadow = False
    cam = scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ORTHO_SCALE
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    spheres = []
    for i, (name, builder, _graded) in enumerate(CASES):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=48, ring_count=24, location=(i * SPACING, 0.0, 0.0))
        obj = bpy.context.active_object
        obj.data.shade_smooth()
        obj.name = "Case_" + name
        tu.assign(obj, builder())
        spheres.append(obj)
    outline.sync_all(scene)  # Geometry Nodes outline hulls for the outline cases
    return scene, sun, cam, spheres


def render_blender(scene, cam, spheres):
    images = {}
    for i, obj in enumerate(spheres):
        for other in spheres:
            other.hide_render = other is not obj
        cam.location = (i * SPACING, -5.0, 0.0)
        pixels, size = tu.render_pixels("blender_" + obj.name)
        images[obj.name[len("Case_"):]] = np.array(pixels).reshape(size[1], size[0], 4)
    for obj in spheres:
        obj.hide_render = False
    return images


def load_exr(path):
    img = bpy.data.images.load(path, check_existing=False)
    pixels = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return pixels


def sample_points():
    centre = RES / 2.0
    radius = 0.5 / ORTHO_SCALE * RES * 0.85
    points = []
    for gy in np.linspace(0.2, 0.8, 9):
        for gx in np.linspace(0.2, 0.8, 9):
            x, y = int(gx * RES), int(gy * RES)
            if (x + 0.5 - centre) ** 2 + (y + 0.5 - centre) ** 2 < radius ** 2:
                points.append((x, y))
    return points


def local_range(img, x, y, radius=2):
    """Largest channel range in the (2 radius + 1)^2 window: high on shading boundaries."""
    patch = img[max(y - radius, 0):y + radius + 1, max(x - radius, 0):x + radius + 1]
    return float((patch.max(axis=(0, 1)) - patch.min(axis=(0, 1))).max())


def compare(blender, unity):
    """Max sRGB difference over the sample points that sit away from shading boundaries in both images: a sub-pixel
    shift of a sharp cel boundary is not a colour difference."""
    b, u = srgb(blender[..., :3]), srgb(unity[..., :3])
    worst, used, skipped = 0.0, 0, 0
    for x, y in sample_points():
        if local_range(b, x, y) > EDGE or local_range(u, x, y) > EDGE:
            skipped += 1
            continue
        worst = max(worst, float(np.abs(b[y, x] - u[y, x]).max()))
        used += 1
    return worst, used, skipped


def outline_profile(img, background):
    """(thickness in px, sRGB colour at the middle of the line) along 8 directions outside the sphere's disc."""
    image = srgb(img[..., :3])
    bg = srgb(np.array(background))
    centre = RES / 2.0
    radius = 0.5 / ORTHO_SCALE * RES
    profile = []
    for k in range(8):
        angle = k * math.pi / 4.0
        hits = []
        for step in range(30):
            r = radius + 0.75 + step * 0.5
            x, y = int(centre + r * math.cos(angle)), int(centre + r * math.sin(angle))
            if np.abs(image[y, x] - bg).max() > 0.08:
                hits.append(image[y, x])
        profile.append((len(hits) * 0.5, hits[len(hits) // 2] if hits else None))
    return profile


def compare_outline(blender, unity):
    """Largest thickness difference (px) and colour difference over the 8 directions, and the thinnest line."""
    worst_width, worst_colour, thinnest = 0.0, 0.0, 99.0
    for (tb, cb), (tu_, cu) in zip(outline_profile(blender, WORLD), outline_profile(unity, (0.0, 0.0, 0.0))):
        worst_width = max(worst_width, abs(tb - tu_))
        thinnest = min(thinnest, tb, tu_)
        if cb is not None and cu is not None:
            worst_colour = max(worst_colour, float(np.abs(cb - cu).max()))
    return worst_width, worst_colour, thinnest


def write_sheet(rows):
    """One row per case: DaskToon | Unity | |difference| x 5, top to bottom in CASES order."""
    height = RES * len(rows)
    sheet = np.zeros((height, RES * 3, 4))
    for i, (blender, unity) in enumerate(rows):
        y0 = height - (i + 1) * RES
        sheet[y0:y0 + RES, 0:RES] = blender
        sheet[y0:y0 + RES, RES:2 * RES] = unity
        sheet[y0:y0 + RES, 2 * RES:3 * RES, :3] = np.abs(srgb(blender[..., :3]) - srgb(unity[..., :3])) * 5.0
        sheet[y0:y0 + RES, 2 * RES:3 * RES, 3] = 1.0
    sheet[..., :3] = np.where(np.arange(3 * RES)[None, :, None] < 2 * RES, srgb(sheet[..., :3]), sheet[..., :3])
    data = (np.clip(sheet, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    with open(SHEET, "wb") as f:
        f.write(textures.png_bytes(RES * 3, height, data))


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityRenderTest(unittest.TestCase):
    def test_unity_matches_dasktoon(self):
        root = harness.ensure_project()
        scene, sun, cam, spheres = build_scene()
        blender = render_blender(scene, cam, spheres)
        target = targets.make_target(root, MODEL_NAME)
        shaders_install.install_shaders(target, [], force=True)  # the throwaway project may hold older test shaders
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=64, bake_samples=4)
        rep = dasktoon_export.export_model(bpy.context, target, spheres, options)
        self.assertEqual(len(rep.materials), len(CASES), rep.lines())
        light_dir = sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        out_dir = os.path.join(tu.OUT_DIR, "unity_renders")
        args = {
            "model": "Assets/DaskToon/%s/Model/%s.fbx" % (MODEL_NAME, MODEL_NAME),
            "cases": [{"name": name, "obj": "Case_" + name, "camPos": to_unity((i * SPACING, -5.0, 0.0))}
                      for i, (name, _builder, _graded) in enumerate(CASES)],
            "resolution": RES,
            "orthoSize": ORTHO_SCALE / 2.0,
            "camForward": to_unity((0.0, 1.0, 0.0)),
            "camUp": to_unity((0.0, 0.0, 1.0)),
            "lightDir": to_unity(light_dir.normalized()),
            "lightIntensity": SUN_STRENGTH / math.pi,
            "lightColor": list(SUN_COLOR),
            "ambient": list(WORLD),
            "outDir": out_dir,
        }
        result = harness.run_method("DaskToonRenderTests.RenderCases", args)
        self.assertTrue(result["ok"], result.get("error"))
        table, failures, rows = {}, [], []
        for name, _builder, graded in CASES:
            unity = load_exr(result["outputs"][name])
            worst, used, skipped = compare(blender[name], unity)
            table[name] = {"max_diff": round(worst, 4), "points": used, "edge_points": skipped, "graded": graded}
            rows.append((blender[name], unity))
            if graded and (worst > TOLERANCE or used < 0.6 * (used + skipped)):
                failures.append(name)
            if name.startswith("outline_"):
                width_diff, colour_diff, thinnest = compare_outline(blender[name], unity)
                table[name].update(outline_width_diff_px=width_diff, outline_colour_diff=round(colour_diff, 4),
                                   outline_thinnest_px=thinnest)
                if width_diff > OUTLINE_WIDTH_TOLERANCE or colour_diff > OUTLINE_COLOUR_TOLERANCE or thinnest < 1.0:
                    failures.append(name + " (outline)")
        write_sheet(rows)
        with open(os.path.join(tu.OUT_DIR, "unity_compare.json"), "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)
        print(json.dumps(table, indent=2))
        self.assertEqual(failures, [], json.dumps(table, indent=2))


if __name__ == "__main__":
    tu.run_tests()
