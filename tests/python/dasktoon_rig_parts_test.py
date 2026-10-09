# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Parts of the anime rig: role from a name, the vertices of a part, loose pieces, nearest bone (spec 5)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import parts  # noqa: E402


class NameTest(unittest.TestCase):
    def test_words(self):
        self.assertEqual(parts.words("TwinTails_01"), ["twin", "tails"])
        self.assertEqual(parts.words("HairBack.001"), ["hair", "back"])
        self.assertEqual(parts.words("T\u00f3c m\u00e1i"), ["toc", "mai"])
        self.assertEqual(parts.ascii_name("T\u00f3c m\u00e1i 2"), "Tocmai2")
        self.assertEqual(parts.ascii_name("!!"), "Part")

    def test_guess_role(self):
        cases = {
            "Hair.001": 'HAIR', "T\u00f3c": 'HAIR', "Ponytail": 'HAIR', "\u9aea": 'HAIR', "CatTail": 'HAIR',
            "Skirt": 'SKIRT', "V\u00e1y": 'SKIRT', "Eye_L": 'ACCESSORY', "Hat": 'ACCESSORY', "Shirt": 'CLOTHING',
            "Body": 'BODY', "Face": 'BODY', "Chatty": None, "Mesh": None,
        }
        for name, role in cases.items():
            self.assertEqual(parts.guess_role(name), role, name)

    def test_initial_roles(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        tall = fx.mesh_object("A", *fx.tube(0.9, 0.0, 0.1, 0.1))
        short = fx.mesh_object("B", *fx.tube(0.5, 0.4, 0.1, 0.1))
        hair = fx.mesh_object("Hair", *fx.strip((0, 0, 1), (0, 0, 0.5), 0.04))
        self.assertEqual(parts.initial_roles([short, tall, hair]), {tall: 'BODY', short: 'CLOTHING', hair: 'HAIR'})
        self.assertEqual(parts.initial_roles([short, tall], has_body=True), {tall: 'CLOTHING', short: 'CLOTHING'})

    def test_part_defaults(self):
        self.assertEqual(parts.Part("S", None, role='SKIRT').bone_count, 3)
        self.assertEqual(parts.Part("H", None, role='HAIR').bone_count, 4)


class VerticesTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.obj = fx.character(merged=True)["Character"]
        self.counts = {name: len(make()[0]) for name, make in fx.PIECES}

    def test_whole_object(self):
        found = parts.part_vertices(parts.Part("All", self.obj))
        self.assertEqual(len(found), len(self.obj.data.vertices))

    def test_by_material(self):
        found = parts.part_vertices(parts.Part("Hair", self.obj, scope='MATERIAL', material="Hair"))
        start = self.counts["Body"] + self.counts["Shirt"]
        np.testing.assert_array_equal(found, np.arange(start, start + self.counts["Hair"]))

    def test_by_vertex_group(self):
        group = self.obj.vertex_groups.new(name="DT_Some")
        group.add([3, 5, 7], 1.0, 'REPLACE')
        group.add([9], 0.0, 'REPLACE')
        found = parts.part_vertices(parts.Part("Some", self.obj, scope='VERTEX_GROUP', vertex_group="DT_Some"))
        self.assertEqual(found.tolist(), [3, 5, 7])

    def test_errors(self):
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='MATERIAL', material="Nope"))
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='VERTEX_GROUP', vertex_group="Nope"))
        self.obj.vertex_groups.new(name="Empty")
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='VERTEX_GROUP', vertex_group="Empty"))

    def test_pieces(self):
        world, edges = parts.mesh_arrays(self.obj)
        self.assertEqual(len(parts.pieces(edges, np.arange(len(world)))), len(fx.PIECES))
        hair = parts.part_vertices(parts.Part("Hair", self.obj, scope='MATERIAL', material="Hair"))
        found = parts.pieces(edges, hair)
        self.assertEqual(len(found), 1)
        np.testing.assert_array_equal(found[0], hair)

    def test_mesh_arrays_are_world(self):
        self.obj.location = (1.0, 0.0, 0.0)
        self.obj.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        world, _edges = parts.mesh_arrays(self.obj)
        local = np.array(self.obj.data.vertices[0].co)
        np.testing.assert_allclose(world[0], local * 2.0 + (1.0, 0.0, 0.0), atol=1e-6)


class BoneTest(unittest.TestCase):
    def test_nearest_bone(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        rig = fx.rig_for()
        eye = np.array([0.03, -0.06, 0.915]) * fx.HEIGHT
        self.assertEqual(parts.nearest_bone(rig, eye, ["Head", "LeftEye", "RightEye"]), "LeftEye")
        head, tail = parts.bone_segment(rig, "Head")
        np.testing.assert_allclose(tail, np.array([0.0, -0.005, 0.99]) * fx.HEIGHT, atol=1e-6)


if __name__ == "__main__":
    tu.run_tests()
