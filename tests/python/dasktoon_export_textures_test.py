# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Ramp strips, PNG / EXR writing, copied images and Cycles baking (spec 4, 5)."""

import os
import sys
import tempfile
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import bake, graph, textures  # noqa: E402

TMP = tempfile.mkdtemp(prefix="dt_textures_")


def load_pixels(name, data):
    path = os.path.join(TMP, name)
    with open(path, "wb") as f:
        f.write(data)
    img = bpy.data.images.load(path, check_existing=False)
    pixels = np.array(img.pixels[:]).reshape(-1, 4)
    size = tuple(img.size)
    bpy.data.images.remove(img)
    return pixels, size


def data_counts():
    return {name: len(getattr(bpy.data, name)) for name in ("objects", "meshes", "materials", "images", "shape_keys")}


class TextureFileTest(unittest.TestCase):
    def test_png_rows_are_bottom_up_like_blender(self):
        rgba = bytes([255, 0, 0, 255, 0, 255, 0, 255,      # bottom row: red, green
                      0, 0, 255, 255, 255, 255, 255, 255])  # top row: blue, white
        pixels, size = load_pixels("rows.png", textures.png_bytes(2, 2, rgba))
        self.assertEqual(size, (2, 2))
        np.testing.assert_allclose(pixels[0], (1, 0, 0, 1), atol=1e-6)
        np.testing.assert_allclose(pixels[2], (0, 0, 1, 1), atol=1e-6)

    def test_float_png_encodes_colour_as_srgb_and_numbers_raw(self):
        half = np.full(4, 0.5, dtype=np.float32)
        half[3] = 1.0
        raw = textures.float_to_png(half, 1, 1, srgb=False)
        srgb = textures.float_to_png(half, 1, 1, srgb=True)
        self.assertEqual(raw, textures.png_bytes(1, 1, bytes([128, 128, 128, 255])))
        self.assertEqual(srgb, textures.png_bytes(1, 1, bytes([188, 188, 188, 255])))

    def test_needs_float(self):
        self.assertFalse(textures.needs_float(np.array([0.0, 0.5, 1.0, 1.0])))
        self.assertTrue(textures.needs_float(np.array([1.5, 0.5, 0.5, 1.0])))
        self.assertTrue(textures.needs_float(np.array([-0.2, 0.5, 0.5, 1.0])))

    def test_ramp_strip_samples_texel_centres(self):
        mat, node = tu.node_material("RampTest", 'ShaderNodeDaskCel')
        ramp = node.shading_ramp
        ramp.interpolation = 'CONSTANT'
        ramp.elements[0].position = 0.0
        ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.elements[1].position = 0.5
        ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        px = textures.ramp_pixels(ramp)
        self.assertEqual(len(px), textures.RAMP_WIDTH * 4)
        self.assertEqual(px[127 * 4], 0)
        self.assertEqual(px[128 * 4], 255)
        ramp.interpolation = 'LINEAR'
        ramp.elements[1].position = 1.0
        px = textures.ramp_pixels(ramp)
        t = 100.5 / 256.0
        want = round((1.055 * t ** (1 / 2.4) - 0.055) * 255)
        self.assertLessEqual(abs(px[100 * 4] - want), 1)
        self.assertEqual(px[100 * 4 + 3], 255)
        pixels, size = load_pixels("ramp.png", textures.ramp_png(ramp))
        self.assertEqual(size, (256, 1))

    def test_image_file_reads_disk_and_packed_images(self):
        path = os.path.join(TMP, "disk.png")
        with open(path, "wb") as f:
            f.write(textures.png_bytes(1, 1, bytes([10, 20, 30, 255])))
        img = bpy.data.images.load(path)
        ext, data = textures.image_file(img)
        self.assertEqual(ext, ".png")
        with open(path, "rb") as f:
            self.assertEqual(data, f.read())
        img.pack()
        os.remove(path)
        ext, packed = textures.image_file(img)
        self.assertEqual((ext, packed), (".png", data))
        img.unpack(method='REMOVE')
        self.assertIsNone(textures.image_file(img))

    def test_exr_keeps_values_above_one(self):
        px = np.array([2.0, 0.25, -0.5, 1.0] * 4, dtype=np.float32)
        pixels, size = load_pixels("hdr.exr", textures.exr_bytes(px, 2, 2))
        self.assertEqual(size, (2, 2))
        np.testing.assert_allclose(pixels[0], (2.0, 0.25, -0.5, 1.0), atol=1e-3)


class BakeTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        self.obj = bpy.context.active_object
        self.mat, self.node = tu.node_material("Baked", 'ShaderNodeAnimeCharacter')
        tu.assign(self.obj, self.mat)
        self.nt = self.mat.node_tree

    def source(self, socket, is_color=True):
        return graph.TexSource('BAKE', is_color, self.mat, self.node.name, socket, None)

    def test_constant_colour_branch(self):
        mix = self.nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        sockets = {s.identifier: s for s in mix.inputs}
        sockets["Factor_Float"].default_value = 0.25
        sockets["A_Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        sockets["B_Color"].default_value = (0.0, 0.0, 1.0, 1.0)
        self.nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), self.node.inputs["Base Color"])
        px = bake.bake_input(self.obj, self.mat, self.source("Base Color"), 16, 4).reshape(-1, 4)
        np.testing.assert_allclose(px[:, :3].mean(axis=0), (0.75, 0.0, 0.25), atol=0.01)

    def test_float_branch(self):
        value = self.nt.nodes.new('ShaderNodeValue')
        value.outputs[0].default_value = 0.3
        self.nt.links.new(value.outputs[0], self.node.inputs["Shadow Threshold"])
        px = bake.bake_input(self.obj, self.mat, self.source("Shadow Threshold", False), 16, 4).reshape(-1, 4)
        np.testing.assert_allclose(px[:, :3].mean(axis=0), (0.3, 0.3, 0.3), atol=0.01)

    def test_user_state_and_data_are_restored(self):
        other = tu.add_sphere(segments=8, rings=4)
        other.data = self.obj.data            # a linked duplicate shares the mesh
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        self.obj.select_set(False)
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE'
        scene.cycles.samples = 7
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], self.node.inputs["Shadow Threshold"])
        before = data_counts()
        bake.bake_input(self.obj, self.mat, self.source("Shadow Threshold", False), 8, 2)
        self.assertEqual(data_counts(), before)
        self.assertEqual(scene.render.engine, 'BLENDER_EEVEE')
        self.assertEqual(scene.cycles.samples, 7)
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertTrue(other.select_get())
        self.assertFalse(self.obj.select_get())
        self.assertEqual(self.obj.data.users, 2)

    def test_material_with_outline_bakes_its_branch(self):
        """The outline sync handler must not turn the temporary bake object into an outlined one (that baked black)."""
        self.node.use_outline = True
        mix = self.nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        sockets = {s.identifier: s for s in mix.inputs}
        sockets["Factor_Float"].default_value = 0.0
        sockets["A_Color"].default_value = (0.2, 0.4, 0.6, 1.0)
        self.nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), self.node.inputs["Shadow Color"])
        px = bake.bake_input(self.obj, self.mat, self.source("Shadow Color"), 16, 4).reshape(-1, 4)
        np.testing.assert_allclose(px[:, :3].mean(axis=0), (0.2, 0.4, 0.6), atol=0.01)
        self.assertFalse([g.name for g in bpy.data.node_groups if "DT_Bake" in g.name])

    def test_branch_size_is_the_largest_image(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.new("Big", 64, 32)
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        self.assertEqual(bake.branch_size(self.mat, self.node.name, "Base Color", 1024), 64)
        self.assertEqual(bake.branch_size(self.mat, self.node.name, "Shadow Color", 1024), 1024)


if __name__ == "__main__":
    tu.run_tests()
