# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Render a contact sheet of shading styles and outlines for human review (not an automated test).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_visual_review.py

Rows (top to bottom): Simple mode, then every built-in ramp style; columns: three sun angles.
The last row shows the outline (fixed Light Bleed and Hand Wobble) at the three sun angles.
"""

import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402

SIZE = 256
OUT = os.path.join(tu.OUT_DIR, "review")
SUN_ANGLES = (0.3, 0.9, 1.4)


def render_tile(style_name, sun_angle, outline=False):
    tu.reset_scene(SIZE)
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    tu.set_world_color((0.05, 0.06, 0.08))
    tu.add_sun(3.0, rotation=(sun_angle, 0.4, 0.0))
    obj = tu.add_sphere(radius=1.2)
    mat, node = tu.node_material("Review", 'ShaderNodeAnimeCharacter')
    tu.assign(obj, mat)
    node.inputs["Base Color"].default_value = (0.95, 0.80, 0.72, 1.0)
    if style_name is not None:
        node.shading_mode = 'RAMP'
        styles.apply_style(node.shading_ramp, styles.BUILTIN_STYLES[style_name])
    if outline:
        node.use_outline = True
        node.inputs["Outline Width"].default_value = 0.1
        bpy.context.view_layer.update()
    path = os.path.join(OUT, "%s_%.1f_%s.png" % (style_name or "Simple", sun_angle, outline))
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = 'Non-Color'  # keep the encoded display values as they are
    tile = np.array(img.pixels[:]).reshape(SIZE, SIZE, 4)
    bpy.data.images.remove(img)
    return tile


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for style_name in [None] + list(styles.BUILTIN_STYLES):
        rows.append(np.concatenate([render_tile(style_name, a) for a in SUN_ANGLES], axis=1))
    rows.append(np.concatenate(
        [render_tile(None, a, outline=True) for a in SUN_ANGLES], axis=1))
    sheet = np.concatenate(rows[::-1], axis=0)  # Blender images start at the bottom row.
    h, w = sheet.shape[:2]
    image = bpy.data.images.new("review_sheet", w, h, alpha=True, is_data=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels = sheet.ravel()
    image.filepath_raw = os.path.join(OUT, "review_sheet.png")
    image.file_format = 'PNG'
    image.save()
    print("REVIEW SHEET:", image.filepath_raw)


main()
