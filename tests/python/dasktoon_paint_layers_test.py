# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Paint layers inside the image (docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md): the image is the
composite of its layers (the C++ compositing, run through paint.dasktoon_layers_composite), the first layer keeps the
picture, merge down and flatten keep what shows; Add Texture Paint Slot connects to the anime shader. Strokes going to
the active layer need a window: dasktoon_paint_layers_window_test."""

import os
import sys
import tempfile
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_paint import brushes, fill as fill_part, layers, start  # noqa: E402
from mathutils import Color  # noqa: E402

W, H = 8, 4
BYTE = 1.0 / 255.0 + 1e-6


def pixels(image):
    px = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(px)
    return px.reshape(image.size[1], image.size[0], 4)


def fill(image, rgba):
    image.pixels.foreach_set(np.tile(np.array(rgba, dtype=np.float32), image.size[0] * image.size[1]))
    image.update()


def picture(name="Skin"):
    image = bpy.data.images.new(name, W, H, alpha=True)
    px = np.zeros((H, W, 4), dtype=np.float32)
    px[..., 0] = np.linspace(0, 1, W)[None, :]
    px[..., 1] = 0.5
    px[..., 2] = np.linspace(1, 0, H)[:, None]
    px[..., 3] = 1.0
    image.pixels.foreach_set(px.ravel())
    image.update()
    return image, px


def blend(mode, below, above):
    return {'NORMAL': above, 'MULTIPLY': below * above, 'ADD': below + above,
            'SCREEN': 1 - (1 - below) * (1 - above),
            'OVERLAY': np.where(below <= 0.5, 2 * below * above, 1 - 2 * (1 - below) * (1 - above))}[mode]


def over(below, above, mode, opacity):
    """The W3C separable blend of `above` (straight RGBA) on `below`, as the C++ compositing does it."""
    sa = above[..., 3:] * opacity
    ba = below[..., 3:]
    alpha = sa + ba * (1 - sa)
    mixed = (1 - ba) * above[..., :3] + ba * blend(mode, below[..., :3], above[..., :3])
    rgb = np.where(alpha > 0, (sa * mixed + (1 - sa) * ba * below[..., :3]) / np.maximum(alpha, 1e-9), 0)
    return np.concatenate([rgb, alpha], axis=-1)


class LayersTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.image, self.px = picture()

    def test_the_first_layer_keeps_the_picture(self):
        top = layers.add(self.image)
        self.assertEqual([item.name for item in self.image.dasktoon_layers], ["Base", "Layer 1"])
        self.assertEqual(self.image.dasktoon_layer_index, 1)
        base = self.image.dasktoon_layers[0].image
        self.assertTrue(base.name.startswith("."))  # hidden from the image lists
        self.assertEqual(tuple(base.size), (W, H))
        np.testing.assert_allclose(pixels(base), self.px, atol=BYTE)
        np.testing.assert_allclose(pixels(top.image)[..., 3], 0.0)  # the new layer is empty
        np.testing.assert_allclose(pixels(self.image), self.px, atol=BYTE)  # what shows is unchanged

    def test_each_blend_mode_and_opacity(self):
        top = layers.add(self.image)
        fill(top.image, (0.8, 0.3, 0.6, 0.5))
        layers.composite(self.image)
        for mode in ('NORMAL', 'MULTIPLY', 'ADD', 'SCREEN', 'OVERLAY'):
            for opacity in (1.0, 0.4):
                top.blend, top.opacity = mode, opacity
                expected = np.clip(over(self.px, pixels(top.image), mode, opacity), 0, 1)
                np.testing.assert_allclose(pixels(self.image), expected, atol=2 * BYTE, err_msg=(mode, opacity))

    def test_a_hidden_layer_does_not_show(self):
        top = layers.add(self.image)
        fill(top.image, (1, 0, 0, 1))
        layers.composite(self.image)
        self.assertGreater(abs(pixels(self.image) - self.px).max(), 0.5)
        top.hide = True
        np.testing.assert_allclose(pixels(self.image), self.px, atol=BYTE)

    def test_merge_down_and_flatten_keep_what_shows(self):
        top = layers.add(self.image)
        fill(top.image, (0.2, 0.9, 0.1, 0.6))
        layers.composite(self.image)
        top.opacity = 0.5
        shown = pixels(self.image)
        layers.merge_down(self.image, 1)
        self.assertEqual(len(self.image.dasktoon_layers), 1)
        np.testing.assert_allclose(pixels(self.image), shown, atol=2 * BYTE)
        np.testing.assert_allclose(pixels(self.image.dasktoon_layers[0].image), shown, atol=2 * BYTE)
        layers.add(self.image)
        layers.flatten(self.image)
        self.assertEqual(len(self.image.dasktoon_layers), 0)
        np.testing.assert_allclose(pixels(self.image), shown, atol=2 * BYTE)

    def test_move_remove_and_duplicate(self):
        red = layers.add(self.image).image  # items move in the list: keep their images, not the items
        fill(red, (1, 0, 0, 1))
        blue = layers.add(self.image).image
        fill(blue, (0, 0, 1, 1))
        layers.composite(self.image)
        np.testing.assert_allclose(pixels(self.image)[0, 0], (0, 0, 1, 1), atol=BYTE)
        layers.move(self.image, 2, -1)  # blue under red
        self.assertEqual(self.image.dasktoon_layers[2].image, red)
        np.testing.assert_allclose(pixels(self.image)[0, 0], (1, 0, 0, 1), atol=BYTE)
        copy = layers.duplicate(self.image, 2).image
        self.assertNotEqual(copy, red)
        np.testing.assert_allclose(pixels(copy), pixels(red))
        layers.remove(self.image, 3)
        layers.remove(self.image, 2)
        np.testing.assert_allclose(pixels(self.image)[0, 0], (0, 0, 1, 1), atol=BYTE)

    def test_a_float_image_keeps_float_layers(self):
        image = bpy.data.images.new("Linear", W, H, alpha=True, float_buffer=True)
        fill(image, (2.0, 0.5, 0.25, 1.0))
        top = layers.add(image)
        self.assertTrue(top.image.is_float)
        np.testing.assert_allclose(pixels(image)[0, 0], (2.0, 0.5, 0.25, 1.0), atol=1e-5)


class PaintSlotTest(unittest.TestCase):
    def test_add_texture_paint_slot_connects_to_the_anime_shader(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_plane_add()
        obj = bpy.context.active_object
        mat = bpy.data.materials.new("Skin")
        obj.data.materials.append(mat)
        anime = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertFalse(any(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in mat.node_tree.nodes))
        with bpy.context.temp_override(object=obj, active_object=obj):
            self.assertEqual(bpy.ops.paint.add_texture_paint_slot(type='BASE_COLOR', slot_type='IMAGE', name="Paint",
                                                                  width=16, height=16), {'FINISHED'})
        links = [link for link in mat.node_tree.links if link.to_node == anime and link.to_socket.name == "Base Color"]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].from_node.bl_idname, 'ShaderNodeTexImage')


def mesh_object(name, parts, materials=("Skin",)):
    """A mesh of `parts` quads side by side (no UV map), faces alternating over `materials`."""
    verts, faces = [], []
    for k in range(parts):
        base = len(verts)
        verts += [(3 * k, 0, 0), (3 * k + 1, 0, 0), (3 * k + 1, 1, 0), (3 * k, 1, 0), (3 * k + 2, 0, 0),
                  (3 * k + 2, 1, 0)]
        faces += [(base, base + 1, base + 2, base + 3), (base + 1, base + 4, base + 5, base + 2)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for mat_name in materials:
        mesh.materials.append(bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name))
    for i, poly in enumerate(mesh.polygons):
        poly.material_index = i % len(materials)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


class StartTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_start_painting_connects_a_picture_of_the_colour(self):
        obj = mesh_object("Doll", 1)
        mat = obj.data.materials[0]
        node = start.anime_node(mat)
        node.inputs["Base Color"].default_value = (0.2, 0.4, 0.8, 1.0)
        self.assertFalse(obj.data.uv_layers)
        made = start.start(bpy.context, obj, size=16)
        self.assertEqual(len(made), 1)
        self.assertTrue(obj.data.uv_layers)  # Smart UV Project
        link = node.inputs["Base Color"].links[0]
        self.assertEqual(link.from_node.image, made[0])
        self.assertEqual(mat.node_tree.nodes.active, link.from_node)  # the paint slot
        expected = (*Color((0.2, 0.4, 0.8)).from_scene_linear_to_srgb(), 1.0)
        np.testing.assert_allclose(pixels(made[0])[3, 5], expected, atol=BYTE)
        self.assertEqual(start.start(bpy.context, obj, size=16), [])  # nothing more to make

    def test_the_operator_leaves_the_mesh_in_texture_paint_with_the_anime_pen(self):
        obj = mesh_object("Doll", 1)
        self.assertEqual(bpy.ops.dasktoon.paint_start(), {'FINISHED'})
        self.assertEqual(obj.mode, 'TEXTURE_PAINT')
        found = {key: brushes.find(key) for key in brushes.BRUSHES}
        self.assertTrue(all(brush is not None and brush.asset_data is not None for brush in found.values()))
        self.assertEqual(bpy.context.tool_settings.image_paint.brush, found['PEN'])
        self.assertEqual(found['FILL'].image_brush_type, 'FILL')
        self.assertEqual(found['PEN'].curve_distance_falloff_preset, 'CONSTANT')
        self.assertTrue(bpy.ops.dasktoon.paint_start.poll())
        bpy.ops.dasktoon.paint_start()
        self.assertEqual(len([b for b in bpy.data.brushes if b.get(brushes.MARK)]), 3)  # not made twice


class SaveTest(unittest.TestCase):
    def test_saving_the_file_keeps_the_pictures_and_the_layers(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        image, _px = picture()
        top = layers.add(image).image
        fill(top, (0.0, 1.0, 0.0, 0.5))
        layers.composite(image)
        shown = pixels(image)
        plain = bpy.data.images.new("Painted", W, H)
        fill(plain, (0.3, 0.3, 0.9, 1.0))
        names = (image.name, top.name)
        # Something must use the images, or the file drops them.
        mat = bpy.data.materials.new("Skin")
        mat.node_tree.nodes.new("ShaderNodeTexImage").image = image
        mat.node_tree.nodes.new("ShaderNodeTexImage").image = plain
        mat.use_fake_user = True
        path = os.path.join(tempfile.mkdtemp(prefix="dt_paint_save_"), "doll.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        self.assertTrue(all(bpy.data.images[n].packed_file is not None for n in names + ("Painted",)))
        bpy.ops.wm.open_mainfile(filepath=path)
        image = bpy.data.images[names[0]]
        self.assertEqual(len(image.dasktoon_layers), 2)
        self.assertEqual(image.dasktoon_layers[1].image.name, names[1])
        np.testing.assert_allclose(pixels(image), shown, atol=2 * BYTE)
        np.testing.assert_allclose(pixels(bpy.data.images["Painted"])[0, 0], (0.3, 0.3, 0.9, 1.0), atol=2 * BYTE)


class FillPartTest(unittest.TestCase):
    def test_a_part_is_its_connected_faces_of_one_material(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = mesh_object("Doll", 3)
        self.assertEqual(fill_part.part_faces(obj.data, 2), [2, 3])  # the second part only
        two = mesh_object("Dress", 2, materials=("Cloth", "Lace"))
        self.assertEqual(fill_part.part_faces(two.data, 0), [0])  # its neighbour is Lace
        self.assertEqual(fill_part.face_under(obj, (3.5, 0.5, 5.0), (0.0, 0.0, -1.0)), 2)


if __name__ == "__main__":
    tu.run_tests()
