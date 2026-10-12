# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The compositor node group of the illustration finish (spec section 4). Its inputs are the picture, its Depth pass,
every setting that is not a layer switch or a Python option (named by its key) and the values Python computes
(`COMPUTED`). Only the layers that are on are built, in the order of `settings.LAYERS`, so a layer that is off costs
nothing; switching one rebuilds the group, moving a slider only changes an input. Sizes are shares of the picture
height, made pixels by Relative To Pixel, so a small viewport and a large render look alike."""

import bpy

from . import settings

GROUP_NAME = "DaskToon Illustration Finish"
VERSION = 1
SKY_DEPTH = 1.0e5  # the world behind everything has a depth far beyond this
SUN_THRESHOLD = 0.85  # brightness from which the sun's rays start: only the brightest parts send rays
LINEAR, SRGB = 'Linear Rec.709', 'sRGB'
# Computed by Python (sun.py): where the sun is on the picture (0 to 1 across), 1 when it is in front of the camera,
# the direction on the picture the light comes from, the distance kept sharp.
COMPUTED = {
    "sun_position": ('NodeSocketVector', (0.5, 1.2, 0.0)),
    "sun_visible": ('NodeSocketFloat', 0.0),
    "light_direction": ('NodeSocketVector', (0.0, 1.0, 0.0)),
    "focus": ('NodeSocketFloat', 5.0),
}
_SOCKETS = {'FACTOR': 'NodeSocketFloat', 'FLOAT': 'NodeSocketFloat', 'DISTANCE': 'NodeSocketFloat',
            'ANGLE': 'NodeSocketFloat', 'SWITCH': 'NodeSocketFloat', 'COLOR': 'NodeSocketColor'}
_BLACK = (0.0, 0.0, 0.0, 1.0)


def _socket_value(setting_kind, value):
    if setting_kind == 'COLOR':
        return tuple(value)[:3] + (1.0,)
    if setting_kind == 'SWITCH':
        return 1.0 if value else 0.0
    return value


def _new_socket(tree, name, in_out, socket_type):
    socket = tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    socket.name = name  # a new socket's name is translated when the interface translates new data; keep it
    return socket


def _interface(tree):
    tree.interface.clear()
    _new_socket(tree, "Image", 'INPUT', 'NodeSocketColor').default_value = _BLACK
    _new_socket(tree, "Depth", 'INPUT', 'NodeSocketFloat')
    for setting in settings.SETTINGS:
        if setting.is_input:
            socket = _new_socket(tree, setting.key, 'INPUT', _SOCKETS[setting.kind])
            socket.default_value = _socket_value(setting.kind, setting.default)
    for key, (socket_type, default) in COMPUTED.items():
        _new_socket(tree, key, 'INPUT', socket_type).default_value = default
    _new_socket(tree, "Image", 'OUTPUT', 'NodeSocketColor')


class _Tree:
    """Adds nodes to the group, each marked with the layer it belongs to."""

    def __init__(self, tree):
        self.tree = tree
        self.layer = None

    def node(self, idname, inputs=None, **props):
        node = self.tree.nodes.new(idname)
        if self.layer is not None:
            node["dasktoon_layer"] = self.layer
        for name, value in props.items():
            setattr(node, name, value)
        for key, value in (inputs or {}).items():
            socket = node.inputs[key]
            if isinstance(value, bpy.types.NodeSocket):
                self.tree.links.new(value, socket)
            else:
                socket.default_value = value
        return node

    def mix(self, blend, factor, a, b):
        """`a` with `b` blended over it (Mix, Screen, Soft Light…) by `factor`, kept within 0 to 1."""
        return self.node("ShaderNodeMix", {0: factor, 6: a, 7: b}, data_type='RGBA', blend_type=blend,
                         clamp_result=True).outputs[2]

    def math(self, operation, a, b=None, c=None, **props):
        inputs = {0: a}
        if b is not None:
            inputs[1] = b
        if c is not None:
            inputs[2] = c
        return self.node("ShaderNodeMath", inputs, operation=operation, **props).outputs[0]

    def vector(self, operation, a, b=None, scale=None):
        inputs = {0: a}
        if b is not None:
            inputs[1] = b
        if scale is not None:
            inputs[3] = scale
        node = self.node("ShaderNodeVectorMath", inputs, operation=operation)
        return node.outputs["Value" if operation in {'LENGTH', 'DOT_PRODUCT'} else "Vector"]

    def map_range(self, value, low, high, to_low=0.0, to_high=1.0):
        """`value` from `low`..`high` to `to_low`..`to_high`, eased and clamped."""
        return self.node("ShaderNodeMapRange", {0: value, 1: low, 2: high, 3: to_low, 4: to_high},
                         interpolation_type='SMOOTHSTEP', clamp=True).outputs[0]

    def pixels(self, share, image):
        """`share` of the picture height, in pixels."""
        return self.node("CompositorNodeRelativeToPixel", {1: share, "Image": image}, data_type='FLOAT',
                         reference_dimension='Y').outputs[0]

    def blur(self, image, size):
        size = self.node("ShaderNodeCombineXYZ", {"X": size, "Y": size}).outputs[0]
        return self.node("CompositorNodeBlur", {"Image": image, "Size": size}).outputs[0]

    def color_space(self, image, source, target):
        return self.node("CompositorNodeConvertColorSpace", {"Image": image}, from_color_space=source,
                         to_color_space=target).outputs[0]

    def gray(self, value):
        """A gray color of `value`."""
        return self.node("ShaderNodeCombineXYZ", {"X": value, "Y": value, "Z": value}).outputs[0]

    def hue_only(self, color):
        """`color` moved to mid brightness: Soft Light with it changes hue, not lightness."""
        lum = self.luminance(color)
        return self.vector('ADD', self.vector('SUBTRACT', color, self.gray(lum)), (0.5, 0.5, 0.5))

    def luminance(self, image):
        return self.node("CompositorNodeRGBToBW", {"Image": image}).outputs[0]

    def coordinates(self, image, kind):
        return self.node("CompositorNodeImageCoordinates", {"Image": image}).outputs[kind]


def _grade(t, img, gi):
    """Multiply the dark areas by the shadow tint (they deepen); soft-light the light areas with the light tint moved
    to mid brightness, so they change hue without getting lighter."""
    lum = t.luminance(img)
    dark = t.map_range(lum, 0.05, 0.55, 1.0, 0.0)
    light = t.map_range(lum, 0.45, 0.95)
    img = t.mix('MULTIPLY', t.math('MULTIPLY', dark, gi["grade_strength"]), img, gi["shadow_tint"])
    return t.mix('SOFT_LIGHT', t.math('MULTIPLY', light, gi["grade_strength"]), img, t.hue_only(gi["light_tint"]))


def _color(t, img, gi):
    """Saturation, then contrast around mid gray: (1 + contrast) x color - contrast x 0.5, as a Mix toward gray by
    -contrast. (Brightness/Contrast is not used: on the GPU it turned a dark color black at contrast 8.)"""
    img = t.node("CompositorNodeHueSat", {"Image": img, "Saturation": gi["saturation"]}).outputs[0]
    return t.node("ShaderNodeMix", {0: t.math('MULTIPLY', gi["contrast"], -1.0), 6: img, 7: (0.5, 0.5, 0.5, 1.0)},
                  data_type='RGBA', blend_type='MIX', clamp_factor=False, clamp_result=True).outputs[2]


def _strokes(t, img, gi):
    painted = t.node("CompositorNodeKuwahara", {"Image": img, "Size": t.pixels(gi["stroke_size"], img),
                                                 "Sharpness": gi["stroke_sharpness"]}).outputs[0]
    return t.mix('MIX', gi["stroke_strength"], img, painted)


def _haze(t, img, gi):
    """Far things fade into the air color from Start to End; the sky (no surface) fades by Sky."""
    depth = gi["Depth"]
    far = t.map_range(depth, gi["haze_start"], gi["haze_end"])
    sky = t.math('GREATER_THAN', depth, SKY_DEPTH)
    amount = t.math('MULTIPLY_ADD', t.math('SUBTRACT', gi["haze_sky"], far), sky, far)
    return t.mix('MIX', t.math('MULTIPLY', amount, gi["haze_strength"]), img, gi["haze_color"])


def _soft(t, img, gi):
    """Beyond the focus the picture blends into a blurred copy, fully at focus x (1 + Transition)."""
    blurred = t.blur(img, t.pixels(gi["soft_size"], img))
    focus = gi["focus"]
    end = t.math('MULTIPLY', focus, t.math('ADD', gi["soft_range"], 1.0))
    return t.mix('MIX', t.map_range(gi["Depth"], focus, end), img, blurred)


def _glow(t, img, gi):
    """Bloom: what lies above the threshold (scaled back to 0 to 1), blurred, screened over the picture. Parts
    below it do not glow, so a bright scene does not turn milky."""
    threshold = gi["glow_threshold"]
    above = t.node("ShaderNodeMix", {0: 1.0, 6: img, 7: t.gray(threshold)}, data_type='RGBA',
                   blend_type='SUBTRACT', clamp_result=True).outputs[2]
    scale = t.math('DIVIDE', 1.0, t.math('MAXIMUM', t.math('SUBTRACT', 1.0, threshold), 0.05))
    bright = t.node("ShaderNodeMix", {0: 1.0, 6: above, 7: t.gray(scale)}, data_type='RGBA',
                    blend_type='MULTIPLY', clamp_result=True).outputs[2]
    spread = t.blur(bright, t.pixels(gi["glow_size"], img))
    return t.mix('SCREEN', gi["glow_strength"], img, spread)


def _rays(t, img, gi):
    glare = t.node("CompositorNodeGlare", {"Image": img, "Type": 'Sun Beams', "Sun Position": gi["sun_position"],
                                           "Size": gi["rays_length"], "Threshold": SUN_THRESHOLD})
    amount = t.math('MULTIPLY', gi["rays_strength"], gi["sun_visible"])
    return t.mix('SCREEN', amount, img, glare.outputs["Glare"])


def _wrap(t, img, gi):
    """Where the depth around a pixel is farther than its own, it is on a subject's outline: light from around
    (the blurred picture) is screened over it."""
    depth = t.math('MINIMUM', gi["Depth"], 1000.0)
    width = t.pixels(gi["wrap_width"], img)
    around = t.luminance(t.blur(depth, width))
    edge = t.math('DIVIDE', t.math('SUBTRACT', around, depth), t.math('MULTIPLY_ADD', depth, 0.25, 0.01),
                  use_clamp=True)
    light = t.blur(img, t.math('MULTIPLY', width, 2.0))
    return t.mix('SCREEN', t.math('MULTIPLY', edge, gi["wrap_strength"]), img, light)


def _gradient(t, img, gi):
    """A wash from the dark side color to the light side color along the light direction, soft-lit over."""
    centered = t.vector('SUBTRACT', t.coordinates(img, "Normalized"), (0.5, 0.5, 0.0))
    side = t.map_range(t.vector('DOT_PRODUCT', centered, gi["light_direction"]), -0.5, 0.5)
    color = t.mix('MIX', side, gi["gradient_dark"], gi["gradient_light"])
    return t.mix('SOFT_LIGHT', gi["gradient_strength"], img, color)


def _vignette(t, img, gi):
    centered = t.vector('SCALE', t.vector('SUBTRACT', t.coordinates(img, "Normalized"), (0.5, 0.5, 0.0)), scale=2.0)
    size = gi["vignette_size"]
    mask = t.map_range(t.vector('LENGTH', centered), size, t.math('ADD', size, gi["vignette_softness"]))
    return t.mix('MULTIPLY', t.math('MULTIPLY', mask, gi["vignette_strength"]), img, gi["vignette_color"])


def _aberration(t, img, gi):
    return t.node("CompositorNodeLensdist", {"Image": img, "Dispersion": t.math('MULTIPLY', gi["aberration_strength"],
                                                                                  0.04)}).outputs[0]


def _paper(t, img, gi):
    """4D noise over the picture; its 4th coordinate is the frame when the grain changes each frame."""
    w = t.math('MULTIPLY', t.node("CompositorNodeSceneTime").outputs["Frame"], gi["paper_animated"])
    where = t.vector('SCALE', t.coordinates(img, "Uniform"), scale=t.math('MULTIPLY', gi["paper_scale"], 300.0))
    noise = t.node("ShaderNodeTexNoise", {"Vector": where, "W": w, "Detail": 6.0, "Roughness": 0.65},
                   noise_dimensions='4D')
    return t.mix('SOFT_LIGHT', gi["paper_strength"], img, noise.outputs["Factor"])


_BUILDERS = {"grade": _grade, "color": _color, "strokes": _strokes, "haze": _haze, "soft": _soft, "glow": _glow,
             "rays": _rays, "wrap": _wrap, "gradient": _gradient, "vignette": _vignette, "aberration": _aberration,
             "paper": _paper}
assert set(_BUILDERS) == set(settings.LAYER_KEYS)


def build(tree, layers):
    """Build `tree` with the layers in `layers`, then Amount: the result over the picture as rendered."""
    tree.nodes.clear()
    t = _Tree(tree)
    gi = t.node("NodeGroupInput").outputs
    # The layers work on the colors as seen, as a painter does: sRGB within 0 to 1 (Soft Light, Screen and contrast
    # around mid gray are meant for those; in linear values they crush the darks). With DaskToon's Standard view
    # transform these are the colors on screen. The setting colors are colors as seen too.
    img = t.mix('MIX', 0.0, t.color_space(gi["Image"], LINEAR, SRGB), gi["Image"])
    for key in settings.LAYER_KEYS:
        if key in layers:
            t.layer = key
            img = _BUILDERS[key](t, img, gi)
    t.layer = "amount"
    # Not kept within 0 to 1: at Amount 0 the picture comes out exactly as rendered.
    img = t.node("ShaderNodeMix", {0: gi["amount"], 6: gi["Image"], 7: t.color_space(img, SRGB, LINEAR)},
                 data_type='RGBA', blend_type='MIX').outputs[2]
    t.layer = None
    tree.links.new(img, t.node("NodeGroupOutput").inputs[0])
    tree["dasktoon_layers"] = ",".join(sorted(layers))


def layers_of(tree):
    """The layers `tree` was built with, or None."""
    found = tree.get("dasktoon_layers")
    return None if found is None else set(found.split(",")) - {""}


def ensure(tree, layers, name=GROUP_NAME):
    """`tree` (a new group when None) built with `layers`; left as it is when it already is."""
    layers = set(layers)
    if tree is None:
        tree = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    if tree.get("dasktoon_version") != VERSION:
        _interface(tree)
        tree["dasktoon_version"] = VERSION
    elif layers_of(tree) == layers:
        return tree
    build(tree, layers)
    return tree


def input_values(values, computed):
    """{input name: value} for a group node: the settings that are inputs, then `computed`."""
    out = {setting.key: _socket_value(setting.kind, values[setting.key])
           for setting in settings.SETTINGS if setting.is_input}
    out.update(computed)
    return out


def _same(a, b):
    try:
        return all(abs(x - y) < 1e-6 for x, y in zip(a, b))
    except TypeError:
        return abs(a - b) < 1e-6


def set_inputs(node, values):
    """Write `values` into the group node's inputs; True when one changed."""
    changed = False
    for name, value in values.items():
        socket = node.inputs.get(name)
        if socket is None or socket.is_linked:
            continue
        current = socket.default_value
        if not _same(tuple(current) if hasattr(current, "__len__") else current, value):
            socket.default_value = value
            changed = True
    return changed
