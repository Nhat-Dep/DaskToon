# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Body regions and locks on the head (docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md): which part of
the body each vertex of the Body and Clothing parts belongs to, the loose pieces attached to the head and the locks
they group into."""

import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import parts as rig_parts, regions, skeleton  # noqa: E402

ANGLE = math.radians(50.0)
ARM_START = Vector((0.12, 0.0, 1.42))
ARM_END = ARM_START + Vector((math.cos(ANGLE), 0.0, -math.sin(ANGLE))) * 0.62


def merged(name, pieces):
    verts, faces = [], []
    for piece_verts, piece_faces in pieces:
        faces += [tuple(i + len(verts) for i in face) for face in piece_faces]
        verts += piece_verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mirrored(point):
    return Vector((-point.x, point.y, point.z))


def character():
    """A chibi 2 tall in A-pose: one Body mesh of loose pieces (torso, a big head, arms 50 degrees down, legs, a rabbit
    ear beside each side of the head hanging down to the shoulders, a hair lock in front of the right shoulder); a
    Shirt with a strap on the chest (a loose piece of the shirt); wide Boots. The skeleton is fitted to them. Returns
    (rig, {name: object}, parts)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tube = st.tube
    body = [tube((0, 0, 0.88), (0, 0, 1.46), 0.18), tube((0, 0, 1.46), (0, 0, 2.0), 0.3)]
    for s in (1.0, -1.0):
        body.append(tube(tuple(ARM_START * Vector((s, 1, 1))), tuple(ARM_END * Vector((s, 1, 1))), 0.05))
        body.append(tube((0.08 * s, 0, 0.95), (0.09 * s, 0, 0.0), 0.07))
        body.append(tube((0.34 * s, 0.08, 1.85), (0.35 * s, 0.12, 1.42), 0.04))  # rabbit ear
    body.append(tube((-0.2, -0.25, 1.75), (-0.22, -0.2, 1.35), 0.03))  # hair lock
    shirt_tube = st.tube((0, 0, 1.40), (0, 0, 0.9), 0.2)
    strap = tube((0.1, -0.215, 1.38), (0.1, -0.215, 1.0), 0.012)
    objs = {"Body": merged("Body", body), "Shirt": merged("Shirt", [shirt_tube, strap]),
            "Boots": merged("Boots", [tube((s * 0.09, 0, 0.0), (s * 0.09, 0, 0.25), 0.12) for s in (1.0, -1.0)])}
    rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
    meshes = list(objs.values())
    skeleton.fit(bpy.context, rig, meshes, body=meshes)
    parts = [rig_parts.Part("Body", objs["Body"], 'BODY'), rig_parts.Part("Shirt", objs["Shirt"], 'CLOTHING'),
             rig_parts.Part("Boots", objs["Boots"], 'CLOTHING')]
    return rig, objs, parts


def nearest(obj, point):
    world, _edges = rig_parts.mesh_arrays(obj)
    return int(np.argmin(np.linalg.norm(world - np.array(point), axis=1)))


class RecognizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.parts = character()
        cls.found = regions.analyse(bpy.context, cls.rig, cls.parts)

    def region_at(self, name, point):
        obj = self.objs[name]
        vertices, labels = self.found.objects[obj]
        index = nearest(obj, point)
        return regions.REGIONS[labels[list(vertices).index(index)]]

    def test_regions_of_the_body_and_clothing(self):
        middle_arm = ARM_START + (ARM_END - ARM_START) * 0.5
        expected = [
            ("Body", ARM_END, 'ARM_L'), ("Body", middle_arm, 'ARM_L'), ("Body", mirrored(middle_arm), 'ARM_R'),
            ("Body", (0, -0.18, 1.15), 'TORSO'), ("Body", (0, -0.3, 1.75), 'HEAD'),
            ("Body", (0.085, 0, 0.5), 'LEG_L'), ("Body", (-0.085, 0, 0.5), 'LEG_R'),
            ("Body", (0.38, 0.1, 1.6), 'HEAD'), ("Body", (-0.38, 0.1, 1.6), 'HEAD'),  # the ears
            ("Body", (-0.21, -0.25, 1.4), 'HEAD'),  # the hair lock, in front of the right arm
            ("Shirt", (0.1, -0.227, 1.2), 'TORSO'), ("Shirt", (0.2, 0.0, 1.1), 'TORSO'),  # the strap, the side
            ("Boots", (0.21, 0.0, 0.1), 'LEG_L'), ("Boots", (-0.21, 0.0, 0.1), 'LEG_R'),
        ]
        for name, point, region in expected:
            self.assertEqual(self.region_at(name, point), region, (name, tuple(point)))

    def test_locks_are_the_pieces_hanging_from_the_head(self):
        locks = {name: (obj.name, len(vertices)) for name, obj, vertices in self.found.locks}
        ear, hair = len(st.tube((0, 0, 0), (0, 0, 1), 0.04)[0]), len(st.tube((0, 0, 0), (0, 0, 1), 0.03)[0])
        # Top to bottom on each side: the right ear (top 1.85) before the hair lock (top 1.75).
        self.assertEqual(locks, {"Lock L1": ("Body", ear), "Lock R1": ("Body", ear), "Lock R2": ("Body", hair)})

    def test_half_widths_from_the_front(self):
        half = self.found.half
        self.assertAlmostEqual(half["LeftUpperArm"], 0.05, delta=0.015)
        self.assertAlmostEqual(half["RightHand"], half["LeftUpperArm"], delta=1e-6)
        self.assertAlmostEqual(half["Chest"], 0.2, delta=0.03)
        self.assertLessEqual(half["UpperChest"], max(half["Hips"], half["Spine"], half["Chest"]) + 1e-6)
        self.assertGreater(half["Head"], 0.25)

    def test_pieces_close_together_make_one_lock(self):
        world = np.array([(0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.004, 0.0, 1.0), (0.5, 0.0, 0.5)])
        pieces = [np.array([0, 1]), np.array([2]), np.array([3])]  # 2 is 4 mm from 1; the gap is 0.005 x 2
        found = regions.locks(pieces, world, 2.0, 0.0)
        self.assertEqual({name: sorted(v.tolist()) for name, v in found}, {"Lock M1": [0, 1, 2], "Lock L1": [3]})


if __name__ == "__main__":
    tu.run_tests()
