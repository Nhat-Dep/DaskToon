# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Every setting of the illustration finish (spec section 4), in one table: the scene's properties, the node group's
inputs and the styles are all made from it.

A LAYER setting switches a layer on or off: the group is built with the layers that are on. OPTION settings, and the
focus distance and gradient angle, are used by Python only: it writes the group's computed inputs (`focus`,
`light_direction`) from them. Every other setting is an input of the group, named by its key."""

import math
from collections import namedtuple

from bpy.app.translations import pgettext_n as n_

PYTHON_ONLY = {"focus_distance", "gradient_angle"}
Setting = namedtuple("Setting", "key label kind default low high layer description")
Setting.is_input = property(lambda self: self.kind not in {'LAYER', 'OPTION'} and self.key not in PYTHON_ONLY)

# (key, label, group): the layers in the order they are applied, like a painter's layers from the bottom up.
LAYERS = (
    ("grade", n_("Shadow and Light Tint"), 'COLOR'),
    ("color", n_("Saturation and Contrast"), 'COLOR'),
    ("strokes", n_("Brush Strokes"), 'TEXTURE'),
    ("haze", n_("Air"), 'DEPTH'),
    ("soft", n_("Soft Background"), 'DEPTH'),
    ("glow", n_("Soft Glow"), 'LIGHT'),
    ("rays", n_("Light Rays"), 'LIGHT'),
    ("wrap", n_("Back Light Wrap"), 'LIGHT'),
    ("gradient", n_("Light Gradient"), 'COLOR'),
    ("vignette", n_("Vignette"), 'DEPTH'),
    ("aberration", n_("Chromatic Aberration"), 'TEXTURE'),
    ("paper", n_("Paper"), 'TEXTURE'),
)
LAYER_KEYS = tuple(key for key, _label, _group in LAYERS)
# (key, label): the panel's groups.
GROUPS = (
    ('COLOR', n_("Painting Colors")),
    ('DEPTH', n_("Depth")),
    ('LIGHT', n_("Painting Light")),
    ('TEXTURE', n_("Strokes and Texture")),
)

S = Setting
SETTINGS = (
    S("amount", n_("Amount"), 'FACTOR', 1.0, 0.0, 1.0, None,
      n_("How much of the finish shows: 0 is the picture as rendered")),
    S("grade", n_("Shadow and Light Tint"), 'LAYER', True, None, None, "grade",
      n_("Dark areas lean to a shadow color, light areas to a light color")),
    S("shadow_tint", n_("Shadow Tint"), 'COLOR', (0.60, 0.55, 0.90), 0.0, 1.0, "grade",
      n_("Color the dark areas lean to")),
    S("light_tint", n_("Light Tint"), 'COLOR', (1.0, 0.86, 0.66), 0.0, 1.0, "grade",
      n_("Color the light areas lean to")),
    S("grade_strength", n_("Tint Strength"), 'FACTOR', 0.45, 0.0, 1.0, "grade", n_("How strongly the areas lean")),
    S("color", n_("Saturation and Contrast"), 'LAYER', True, None, None, "color",
      n_("Livelier colors and clearer forms")),
    S("saturation", n_("Saturation"), 'FLOAT', 1.12, 0.0, 2.0, "color", n_("1 keeps the colors")),
    S("contrast", n_("Contrast"), 'FLOAT', 0.08, -0.5, 0.5, "color", n_("0 keeps the contrast")),
    S("strokes", n_("Brush Strokes"), 'LAYER', False, None, None, "strokes",
      n_("Small details become patches of color along the strokes, as if painted with a brush")),
    S("stroke_size", n_("Brush Size"), 'FLOAT', 0.004, 0.0, 0.05, "strokes",
      n_("Brush size, as a share of the picture height")),
    S("stroke_sharpness", n_("Sharpness"), 'FACTOR', 0.5, 0.0, 1.0, "strokes",
      n_("How crisp the edges of the strokes are")),
    S("stroke_strength", n_("Strokes Strength"), 'FACTOR', 1.0, 0.0, 1.0, "strokes",
      n_("How much of the strokes shows")),
    S("haze", n_("Air"), 'LAYER', True, None, None, "haze",
      n_("The farther, the more things fade into the color of the air")),
    S("haze_start", n_("Start"), 'DISTANCE', 8.0, 0.0, 10000.0, "haze", n_("Distance where the air starts to show")),
    S("haze_end", n_("End"), 'DISTANCE', 80.0, 0.0, 10000.0, "haze", n_("Distance where the air is at full strength")),
    S("haze_color", n_("Air Color"), 'COLOR', (0.70, 0.78, 0.92), 0.0, 1.0, "haze", n_("Color far things fade into")),
    S("haze_strength", n_("Air Strength"), 'FACTOR', 0.55, 0.0, 1.0, "haze", n_("How much far things fade")),
    S("haze_sky", n_("Sky"), 'FACTOR', 0.15, 0.0, 1.0, "haze", n_("How much the sky behind everything fades")),
    S("soft", n_("Soft Background"), 'LAYER', True, None, None, "soft",
      n_("What lies beyond the focus is softened, so the subject stands out")),
    S("focus_auto", n_("Auto Focus"), 'OPTION', True, None, None, "soft",
      n_("Focus where the camera focuses, or else on the selected object")),
    S("focus_distance", n_("Focus Distance"), 'DISTANCE', 5.0, 0.0, 10000.0, "soft", n_("Distance kept sharp")),
    S("soft_size", n_("Softness"), 'FLOAT', 0.006, 0.0, 0.05, "soft",
      n_("Blur size, as a share of the picture height")),
    S("soft_range", n_("Transition"), 'FLOAT', 1.0, 0.05, 10.0, "soft",
      n_("How far beyond the focus, as a multiple of it, the background is fully soft")),
    S("glow", n_("Soft Glow"), 'LAYER', True, None, None, "glow",
      n_("A blurred copy of the picture lightens it, so light spreads softly as in an anime film")),
    S("glow_threshold", n_("Threshold"), 'FACTOR', 0.55, 0.0, 1.0, "glow",
      n_("0 glows the whole picture, 1 only the brightest")),
    S("glow_size", n_("Spread"), 'FLOAT', 0.03, 0.0, 0.2, "glow",
      n_("How far the glow spreads, as a share of the picture height")),
    S("glow_strength", n_("Glow Strength"), 'FACTOR', 0.35, 0.0, 1.0, "glow", n_("How bright the glow is")),
    S("rays", n_("Light Rays"), 'LAYER', True, None, None, "rays",
      n_("Rays from where the sun is in the picture; none when the sun is behind the camera")),
    S("rays_length", n_("Length"), 'FACTOR', 0.25, 0.0, 1.0, "rays", n_("How long the rays are")),
    S("rays_strength", n_("Rays Strength"), 'FACTOR', 0.35, 0.0, 1.0, "rays", n_("How bright the rays are")),
    S("wrap", n_("Back Light Wrap"), 'LAYER', True, None, None, "wrap",
      n_("Light behind a subject spills a little over its outline")),
    S("wrap_width", n_("Width"), 'FLOAT', 0.008, 0.0, 0.05, "wrap",
      n_("How far the light spills, as a share of the picture height")),
    S("wrap_strength", n_("Wrap Strength"), 'FACTOR', 0.4, 0.0, 1.0, "wrap", n_("How bright the spill is")),
    S("gradient", n_("Light Gradient"), 'LAYER', True, None, None, "gradient",
      n_("A warm to cool wash across the picture, from the side the light comes from")),
    S("gradient_light", n_("Light Side"), 'COLOR', (1.0, 0.82, 0.62), 0.0, 1.0, "gradient",
      n_("Color on the side of the light")),
    S("gradient_dark", n_("Dark Side"), 'COLOR', (0.42, 0.48, 0.80), 0.0, 1.0, "gradient",
      n_("Color on the other side")),
    S("gradient_auto", n_("Follow Sun"), 'OPTION', True, None, None, "gradient",
      n_("The light side is where the scene's sun shines from")),
    S("gradient_angle", n_("Angle"), 'ANGLE', math.radians(90.0), -math.pi, math.pi, "gradient",
      n_("Side the light comes from in the picture: at 90 degrees it comes from the top")),
    S("gradient_strength", n_("Gradient Strength"), 'FACTOR', 0.3, 0.0, 1.0, "gradient", n_("How strong the wash is")),
    S("vignette", n_("Vignette"), 'LAYER', True, None, None, "vignette",
      n_("The corners darken a little, leading the eye in")),
    S("vignette_size", n_("Size"), 'FACTOR', 0.8, 0.0, 1.5, "vignette",
      n_("Where the darkening starts, from the middle")),
    S("vignette_softness", n_("Edge Softness"), 'FACTOR', 0.5, 0.01, 1.5, "vignette", n_("How gradually it darkens")),
    S("vignette_color", n_("Vignette Color"), 'COLOR', (0.12, 0.10, 0.20), 0.0, 1.0, "vignette",
      n_("Color of the corners")),
    S("vignette_strength", n_("Vignette Strength"), 'FACTOR', 0.3, 0.0, 1.0, "vignette",
      n_("How dark the corners get")),
    S("aberration", n_("Chromatic Aberration"), 'LAYER', True, None, None, "aberration",
      n_("Colors split very slightly toward the edges, as through a lens")),
    S("aberration_strength", n_("Aberration"), 'FACTOR', 0.2, 0.0, 1.0, "aberration", n_("How far the colors split")),
    S("paper", n_("Paper"), 'LAYER', True, None, None, "paper", n_("A very light grain of paper over the picture")),
    S("paper_scale", n_("Paper Scale"), 'FLOAT', 1.0, 0.1, 10.0, "paper", n_("Size of the grain")),
    S("paper_strength", n_("Paper Strength"), 'FACTOR', 0.12, 0.0, 1.0, "paper", n_("How much the grain shows")),
    S("paper_animated", n_("Changes Each Frame"), 'SWITCH', False, None, None, "paper",
      n_("The grain changes every frame, like film; off, it stays like paper")),
)
del S
BY_KEY = {setting.key: setting for setting in SETTINGS}
assert {s.key for s in SETTINGS if s.kind == 'LAYER'} == set(LAYER_KEYS)


def defaults():
    """{key: default} of every setting."""
    return {setting.key: setting.default for setting in SETTINGS}


def layer_group(layer):
    return next(group for key, _label, group in LAYERS if key == layer)
