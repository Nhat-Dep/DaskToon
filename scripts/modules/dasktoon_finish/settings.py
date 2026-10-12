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

PYTHON_ONLY = {"focus_distance", "gradient_angle"}
Setting = namedtuple("Setting", "key label kind default low high layer description")
Setting.is_input = property(lambda self: self.kind not in {'LAYER', 'OPTION'} and self.key not in PYTHON_ONLY)

# (key, label, group): the layers in the order they are applied, like a painter's layers from the bottom up.
LAYERS = (
    ("grade", "Shadow and Light Tint", 'COLOR'),
    ("color", "Saturation and Contrast", 'COLOR'),
    ("strokes", "Brush Strokes", 'TEXTURE'),
    ("haze", "Air", 'DEPTH'),
    ("soft", "Soft Background", 'DEPTH'),
    ("glow", "Soft Glow", 'LIGHT'),
    ("rays", "Light Rays", 'LIGHT'),
    ("wrap", "Back Light Wrap", 'LIGHT'),
    ("gradient", "Light Gradient", 'COLOR'),
    ("vignette", "Vignette", 'DEPTH'),
    ("aberration", "Chromatic Aberration", 'TEXTURE'),
    ("paper", "Paper", 'TEXTURE'),
)
LAYER_KEYS = tuple(key for key, _label, _group in LAYERS)
# (key, label): the panel's groups.
GROUPS = (
    ('COLOR', "Painting Colors"),
    ('DEPTH', "Depth"),
    ('LIGHT', "Painting Light"),
    ('TEXTURE', "Strokes and Texture"),
)

S = Setting
SETTINGS = (
    S("amount", "Amount", 'FACTOR', 1.0, 0.0, 1.0, None, "How much of the finish shows: 0 is the picture as rendered"),
    S("grade", "Shadow and Light Tint", 'LAYER', True, None, None, "grade",
      "Dark areas lean to a shadow color, light areas to a light color"),
    S("shadow_tint", "Shadow Tint", 'COLOR', (0.60, 0.55, 0.90), 0.0, 1.0, "grade", "Color the dark areas lean to"),
    S("light_tint", "Light Tint", 'COLOR', (1.0, 0.86, 0.66), 0.0, 1.0, "grade", "Color the light areas lean to"),
    S("grade_strength", "Tint Strength", 'FACTOR', 0.45, 0.0, 1.0, "grade", "How strongly the areas lean"),
    S("color", "Saturation and Contrast", 'LAYER', True, None, None, "color", "Livelier colors and clearer forms"),
    S("saturation", "Saturation", 'FLOAT', 1.12, 0.0, 2.0, "color", "1 keeps the colors"),
    S("contrast", "Contrast", 'FLOAT', 0.08, -0.5, 0.5, "color", "0 keeps the contrast"),
    S("strokes", "Brush Strokes", 'LAYER', False, None, None, "strokes",
      "Small details become patches of color along the strokes, as if painted with a brush"),
    S("stroke_size", "Brush Size", 'FLOAT', 0.004, 0.0, 0.05, "strokes",
      "Brush size, as a share of the picture height"),
    S("stroke_sharpness", "Sharpness", 'FACTOR', 0.5, 0.0, 1.0, "strokes", "How crisp the edges of the strokes are"),
    S("stroke_strength", "Strokes Strength", 'FACTOR', 1.0, 0.0, 1.0, "strokes", "How much of the strokes shows"),
    S("haze", "Air", 'LAYER', True, None, None, "haze", "The farther, the more things fade into the color of the air"),
    S("haze_start", "Start", 'DISTANCE', 8.0, 0.0, 10000.0, "haze", "Distance where the air starts to show"),
    S("haze_end", "End", 'DISTANCE', 80.0, 0.0, 10000.0, "haze", "Distance where the air is at full strength"),
    S("haze_color", "Air Color", 'COLOR', (0.70, 0.78, 0.92), 0.0, 1.0, "haze", "Color far things fade into"),
    S("haze_strength", "Air Strength", 'FACTOR', 0.55, 0.0, 1.0, "haze", "How much far things fade"),
    S("haze_sky", "Sky", 'FACTOR', 0.15, 0.0, 1.0, "haze", "How much the sky behind everything fades"),
    S("soft", "Soft Background", 'LAYER', True, None, None, "soft",
      "What lies beyond the focus is softened, so the subject stands out"),
    S("focus_auto", "Auto Focus", 'OPTION', True, None, None, "soft",
      "Focus where the camera focuses, or else on the selected object"),
    S("focus_distance", "Focus Distance", 'DISTANCE', 5.0, 0.0, 10000.0, "soft", "Distance kept sharp"),
    S("soft_size", "Softness", 'FLOAT', 0.006, 0.0, 0.05, "soft", "Blur size, as a share of the picture height"),
    S("soft_range", "Transition", 'FLOAT', 1.0, 0.05, 10.0, "soft",
      "How far beyond the focus, as a multiple of it, the background is fully soft"),
    S("glow", "Soft Glow", 'LAYER', True, None, None, "glow",
      "A blurred copy of the picture lightens it, so light spreads softly as in an anime film"),
    S("glow_threshold", "Threshold", 'FACTOR', 0.55, 0.0, 1.0, "glow",
      "0 glows the whole picture, 1 only the brightest"),
    S("glow_size", "Spread", 'FLOAT', 0.03, 0.0, 0.2, "glow",
      "How far the glow spreads, as a share of the picture height"),
    S("glow_strength", "Glow Strength", 'FACTOR', 0.35, 0.0, 1.0, "glow", "How bright the glow is"),
    S("rays", "Light Rays", 'LAYER', True, None, None, "rays",
      "Rays from where the sun is in the picture; none when the sun is behind the camera"),
    S("rays_length", "Length", 'FACTOR', 0.25, 0.0, 1.0, "rays", "How long the rays are"),
    S("rays_strength", "Rays Strength", 'FACTOR', 0.35, 0.0, 1.0, "rays", "How bright the rays are"),
    S("wrap", "Back Light Wrap", 'LAYER', True, None, None, "wrap",
      "Light behind a subject spills a little over its outline"),
    S("wrap_width", "Width", 'FLOAT', 0.008, 0.0, 0.05, "wrap",
      "How far the light spills, as a share of the picture height"),
    S("wrap_strength", "Wrap Strength", 'FACTOR', 0.4, 0.0, 1.0, "wrap", "How bright the spill is"),
    S("gradient", "Light Gradient", 'LAYER', True, None, None, "gradient",
      "A warm to cool wash across the picture, from the side the light comes from"),
    S("gradient_light", "Light Side", 'COLOR', (1.0, 0.82, 0.62), 0.0, 1.0, "gradient",
      "Color on the side of the light"),
    S("gradient_dark", "Dark Side", 'COLOR', (0.42, 0.48, 0.80), 0.0, 1.0, "gradient", "Color on the other side"),
    S("gradient_auto", "Follow Sun", 'OPTION', True, None, None, "gradient",
      "The light side is where the scene's sun shines from"),
    S("gradient_angle", "Angle", 'ANGLE', math.radians(90.0), -math.pi, math.pi, "gradient",
      "Side the light comes from in the picture: 90° is from the top"),
    S("gradient_strength", "Gradient Strength", 'FACTOR', 0.3, 0.0, 1.0, "gradient", "How strong the wash is"),
    S("vignette", "Vignette", 'LAYER', True, None, None, "vignette", "The corners darken a little, leading the eye in"),
    S("vignette_size", "Size", 'FACTOR', 0.8, 0.0, 1.5, "vignette", "Where the darkening starts, from the middle"),
    S("vignette_softness", "Edge Softness", 'FACTOR', 0.5, 0.01, 1.5, "vignette", "How gradually it darkens"),
    S("vignette_color", "Vignette Color", 'COLOR', (0.12, 0.10, 0.20), 0.0, 1.0, "vignette", "Color of the corners"),
    S("vignette_strength", "Vignette Strength", 'FACTOR', 0.3, 0.0, 1.0, "vignette", "How dark the corners get"),
    S("aberration", "Chromatic Aberration", 'LAYER', True, None, None, "aberration",
      "Colors split very slightly toward the edges, as through a lens"),
    S("aberration_strength", "Aberration", 'FACTOR', 0.2, 0.0, 1.0, "aberration", "How far the colors split"),
    S("paper", "Paper", 'LAYER', True, None, None, "paper", "A very light grain of paper over the picture"),
    S("paper_scale", "Paper Scale", 'FLOAT', 1.0, 0.1, 10.0, "paper", "Size of the grain"),
    S("paper_strength", "Paper Strength", 'FACTOR', 0.12, 0.0, 1.0, "paper", "How much the grain shows"),
    S("paper_animated", "Changes Each Frame", 'SWITCH', False, None, None, "paper",
      "The grain changes every frame, like film; off, it stays like paper"),
)
del S
BY_KEY = {setting.key: setting for setting in SETTINGS}
assert {s.key for s in SETTINGS if s.kind == 'LAYER'} == set(LAYER_KEYS)


def defaults():
    """{key: default} of every setting."""
    return {setting.key: setting.default for setting in SETTINGS}


def layer_group(layer):
    return next(group for key, _label, group in LAYERS if key == layer)
