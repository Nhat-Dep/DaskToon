# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The anime brushes (spec section 4): kept in the file as its own brush assets (ruling 8), found again by the mark
"dasktoon_brush" whatever their names became."""

import contextlib

import bpy
from bpy.app.translations import pgettext_data as data_

MARK = "dasktoon_brush"
BRUSHES = {
    # A hard, even line with no soft edge: outlines, eyes, flat shapes.
    'PEN': ("Anime Pen", dict(image_brush_type='DRAW', curve_distance_falloff_preset='CONSTANT', strength=1.0,
                              size=8, spacing=3, use_paint_antialiasing=False)),
    # A faint, soft spray that builds up: blush, soft shading.
    'BLUSH': ("Anime Blush", dict(image_brush_type='DRAW', curve_distance_falloff_preset='SMOOTHER', strength=0.12,
                                  size=60, spacing=8)),
    # Blender's Fill: on the model it fills the faces the mask lets through (Fill Part sets that mask).
    'FILL': ("Anime Fill", dict(image_brush_type='FILL', strength=1.0)),
}


def find(key):
    return next((brush for brush in bpy.data.brushes if brush.get(MARK) == key), None)


def ensure():
    """The anime brushes in this file, made when missing; {key: brush}."""
    made = {}
    for key, (name, settings) in BRUSHES.items():
        brush = find(key)
        if brush is None:
            brush = bpy.data.brushes.new(data_(name), mode='TEXTURE_PAINT')
            brush[MARK] = key
            for attr, value in settings.items():
                if hasattr(brush, attr):
                    setattr(brush, attr, value)
        if brush.asset_data is None:
            brush.asset_mark()
        made[key] = brush
    return made


def activate(context, key):
    """Make the anime brush `key` the Texture Paint brush."""
    brush = ensure()[key]
    bpy.ops.brush.asset_activate(asset_library_type='LOCAL', relative_asset_identifier="Brush/" + brush.name)
    return context.tool_settings.image_paint.brush == brush


@contextlib.contextmanager
def using(context, key):
    """Paint with the anime brush `key` for a moment, then go back to the brush in use."""
    settings = context.tool_settings.image_paint
    reference = settings.brush_asset_reference
    before = (reference.asset_library_type, reference.asset_library_identifier, reference.relative_asset_identifier)
    try:
        activate(context, key)
        yield settings.brush
    finally:
        if before[2]:
            bpy.ops.brush.asset_activate(asset_library_type=before[0], asset_library_identifier=before[1],
                                         relative_asset_identifier=before[2])
