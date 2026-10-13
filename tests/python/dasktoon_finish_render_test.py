# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The illustration finish changes a render as each layer should (illustration finish spec 9): rendered with EEVEE,
each layer on alone, against the same scene with every layer off."""

import math
import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from dasktoon_finish import settings  # noqa: E402

WIDTH, HEIGHT = 160, 90


def material(name, color, emit=0.0):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color + (1.0,)
    if emit:
        bsdf.inputs["Emission Color"].default_value = color + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit
    tree.links.new(bsdf.outputs[0], tree.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    return mat


def add(name, primitive, location, size, color, emit=0.0):
    primitive(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size, size, size)
    obj.data.materials.append(material(name, color, emit))
    return obj


def scene():
    """A camera at y = -8 looking along +y over a ground; two like gray cubes, near (depth 10) and far (depth 58); a
    warm sphere at depth 7; a bright emitting ball; a Sun from the upper right, ahead."""
    tu.reset_scene()
    scn = bpy.context.scene
    scn.render.resolution_x, scn.render.resolution_y = WIDTH, HEIGHT
    tu.set_world_color((0.30, 0.40, 0.60))
    camera = scn.camera
    camera.location, camera.rotation_euler = (0.0, -8.0, 1.5), (math.radians(88.0), 0.0, 0.0)
    add("Ground", bpy.ops.mesh.primitive_plane_add, (0.0, 40.0, 0.0), 80.0, (0.30, 0.40, 0.25))
    add("Near", bpy.ops.mesh.primitive_cube_add, (-3.0, 2.0, 1.0), 1.0, (0.45, 0.45, 0.45))
    add("Far", bpy.ops.mesh.primitive_cube_add, (-14.0, 50.0, 5.0), 5.0, (0.45, 0.45, 0.45))
    add("Sphere", bpy.ops.mesh.primitive_uv_sphere_add, (0.5, -1.0, 1.2), 1.0, (0.80, 0.45, 0.35))
    add("Ball", bpy.ops.mesh.primitive_uv_sphere_add, (4.0, 4.0, 3.0), 0.4, (1.0, 0.9, 0.6), emit=6.0)
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(-60.0), math.radians(20.0), 0.0))
    bpy.context.object.data.energy = 3.0
    bpy.context.view_layer.update()
    return scn


def render(name):
    pixels, size = tu.render_pixels(name)
    return np.array(pixels, dtype=np.float32).reshape(size[1], size[0], 4)[..., :3]


def pixel_of(obj):
    """(row, column) of `obj`'s origin in the render (rows from the bottom)."""
    scn = bpy.context.scene
    co = world_to_camera_view(scn, scn.camera, obj.matrix_world.translation)
    return int(co.y * HEIGHT), int(co.x * WIDTH)


def patch(image, where, size=2):
    row, col = where
    return image[row - size:row + size + 1, col - size:col + size + 1].reshape(-1, 3).mean(axis=0)


class FinishRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = scene()
        cls.finish = cls.scene.dasktoon_finish
        cls.finish.focus_auto = cls.finish.gradient_auto = False
        cls.finish.enabled = True
        cls.only()
        cls.base = render("finish_base")

    def setUp(self):
        self.finish.enabled, self.finish.amount = True, 1.0

    @classmethod
    def only(cls, *layers, **values):
        """Only `layers` on, with `values` set."""
        for key in settings.LAYER_KEYS:
            setattr(cls.finish, key, key in layers)
        for key, value in values.items():
            setattr(cls.finish, key, value)

    def test_no_layer_and_amount_0_are_the_picture(self):
        self.finish.enabled = False
        plain = render("finish_off")
        self.finish.enabled = True
        # Every layer off is the picture as shown: Standard shows nothing above 1, and the finish keeps within 0 to 1.
        self.assertLess(np.abs(np.clip(plain, 0.0, 1.0) - self.base).max(), 0.02)
        self.only(*settings.LAYER_KEYS, amount=0.0)
        self.assertLess(np.abs(render("finish_amount0") - plain).max(), 0.002)

    def test_air(self):
        self.only("haze", haze_start=5.0, haze_end=60.0, haze_strength=1.0, haze_color=(1.0, 1.0, 1.0))
        image = render("finish_haze")
        near, far = (pixel_of(bpy.data.objects[name]) for name in ("Near", "Far"))
        near_gain = (patch(image, near) - patch(self.base, near)).mean()
        far_gain = (patch(image, far) - patch(self.base, far)).mean()
        self.assertGreater(far_gain, near_gain + 0.05)  # the far cube fades into the white air much more

    def test_glow(self):
        self.only("glow", glow_threshold=0.5, glow_size=0.05, glow_strength=1.0)
        image = render("finish_glow")
        row, col = pixel_of(bpy.data.objects["Ball"])
        ring = image[row - 8:row + 9, col + 5:col + 9]  # beside the ball
        self.assertGreater((ring - self.base[row - 8:row + 9, col + 5:col + 9]).mean(), 0.01)

    def test_vignette(self):
        self.only("vignette", vignette_strength=1.0, vignette_size=0.5)
        image = render("finish_vignette")
        corner, middle = (2, 2), (HEIGHT // 2, WIDTH // 2)
        self.assertLess(patch(image, corner, 1).mean(), 0.8 * patch(self.base, corner, 1).mean())
        self.assertLess(np.abs(patch(image, middle) - patch(self.base, middle)).max(), 0.01)

    def test_gradient_from_the_top(self):
        self.only("gradient", gradient_angle=math.radians(90.0), gradient_strength=1.0)
        image = render("finish_gradient")
        warm = image[..., 0] - image[..., 2]
        base = self.base[..., 0] - self.base[..., 2]
        top, bottom = (warm - base)[-10:].mean(), (warm - base)[:10].mean()
        self.assertGreater(top, bottom + 0.02)  # warmer at the top, where the light comes from

    def test_shadow_tint(self):
        self.only("grade", shadow_tint=(0.2, 0.3, 1.0), grade_strength=1.0)
        image = render("finish_grade")
        dark = self.base.mean(axis=2) < np.percentile(self.base.mean(axis=2), 30)
        blue = lambda img: (img[..., 2] - img[..., 0])[dark].mean()  # noqa: E731
        self.assertGreater(blue(image), blue(self.base) + 0.005)

    def test_brush_strokes(self):
        self.only("strokes", stroke_size=0.03)
        self.assertGreater(np.abs(render("finish_strokes") - self.base).mean(), 0.001)

    def test_soft_background(self):
        self.only("soft", focus_distance=7.0, soft_size=0.03, soft_range=0.5)
        image = render("finish_soft")
        sphere, far = pixel_of(bpy.data.objects["Sphere"]), pixel_of(bpy.data.objects["Far"])
        self.assertLess(np.abs(patch(image, sphere) - patch(self.base, sphere)).max(), 0.01)  # in focus
        # The far cube's edge blurs: the pixels just beside its outline change.
        row, col = far
        edge = (slice(row - 6, row + 7), slice(col - 12, col + 13))
        self.assertGreater(np.abs(image[edge] - self.base[edge]).max(), 0.02)


if __name__ == "__main__":
    tu.run_tests()
