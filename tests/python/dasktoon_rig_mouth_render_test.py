# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A 2D mouth shows the cell of its atlas that the object's dt_mouth picks (anime rig spec 10.3), rendered with
EEVEE: a plane facing the camera, its material an emitting 2 x 2 atlas of four colors."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import mouth  # noqa: E402

# Cells from the top left, row by row; image rows run from the bottom.
COLORS = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0, 1.0))


def atlas_image():
    size = 16
    image = bpy.data.images.new("Atlas", size, size)
    image.colorspace_settings.name = 'Non-Color'  # before the pixels: a generated image is made again on this
    pixels = []
    for y in range(size):
        row = 0 if y >= size // 2 else 1
        for x in range(size):
            col = 0 if x < size // 2 else 1
            pixels += list(COLORS[row * 2 + col]) + [1.0]
    image.pixels.foreach_set(pixels)
    image.update()
    return image


def scene():
    """The plane under the default test camera (it looks down at it), its material the atlas as emission."""
    tu.reset_scene(resolution=16)
    bpy.ops.mesh.primitive_plane_add(size=2.0)
    plane = bpy.context.object
    mat = bpy.data.materials.new("Mouth")
    if mat.node_tree is None:
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = atlas_image()
    texture.interpolation = 'Closest'
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs[0], tree.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    plane.data.materials.append(mat)
    return plane, mat


class MouthRenderTest(unittest.TestCase):
    def test_dt_mouth_picks_the_cell(self):
        plane, mat = scene()
        self.assertEqual(mouth.atlas_material(mat, 2, 2), 1)
        mouth.ensure_property(plane, 4)
        for cell, color in enumerate(COLORS):
            plane[mouth.PROP] = cell
            plane.update_tag()
            rgba = tu.render_center("mouth_cell_%d" % cell)
            self.assertEqual(tuple(round(c) for c in rgba[:3]), color, cell)


if __name__ == "__main__":
    tu.run_tests()
