# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Weights of the anime rig: matrices in and out of vertex groups, the Unity clean-up, binding, bone heat, weights
copied from a surface (spec 5.2, 6.2, 12)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import weights  # noqa: E402


def plane(name, size=1.0, cuts=4):
    verts = [(x, y, 0.0) for y in np.linspace(-size, size, cuts + 1) for x in np.linspace(-size, size, cuts + 1)]
    n = cuts + 1
    faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(cuts) for c in range(cuts)]
    return fx.mesh_object(name, verts, faces)


class MatrixTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.obj = plane("P")

    def test_write_read_clear(self):
        vertices = np.array([0, 1, 2])
        matrix = np.array([[1.0, 0.0], [0.25, 0.75], [0.0, 0.5]])
        weights.write(self.obj, vertices, ["A", "B"], matrix)
        out = weights.read(self.obj, ["A", "B", "C"])
        np.testing.assert_allclose(out[:3, :2], matrix)
        self.assertEqual(out[:, 2].sum(), 0.0)
        self.assertEqual(out[3:].sum(), 0.0)
        self.assertNotIn(0, [g.group for g in self.obj.data.vertices[0].groups if g.group == self.obj.vertex_groups["B"].index])
        weights.clear(self.obj, np.array([1]), ["A", "B"])
        out = weights.read(self.obj, ["A", "B"])
        np.testing.assert_allclose(out[1], [0.0, 0.0])
        np.testing.assert_allclose(out[0], [1.0, 0.0])

    def test_tidy(self):
        matrix = np.array([
            [0.5, 0.2, 0.1, 0.1, 0.05, 0.05],     # six weights: the two smallest go
            [0.005, 0.0, 0.0, 0.0, 0.0, 0.0],     # only a tiny weight: it stays, as 1
            [0.0] * 6,                            # nothing stays nothing
            [0.3, 0.3, 0.0, 0.0, 0.0, 0.009],     # under 0.01 goes
        ])
        out = weights.tidy(matrix)
        np.testing.assert_allclose(out[0], np.array([0.5, 0.2, 0.1, 0.1, 0.0, 0.0]) / 0.9)
        np.testing.assert_allclose(out[1], [1, 0, 0, 0, 0, 0])
        np.testing.assert_allclose(out[2], 0.0)
        np.testing.assert_allclose(out[3], [0.5, 0.5, 0, 0, 0, 0])
        self.assertTrue(np.all((out > 0).sum(axis=1) <= 4))


class BindTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.rig = fx.rig_for()
        self.rig.location = (0.5, 0.0, 0.0)
        bpy.context.view_layer.update()

    def test_bind_puts_armature_after_mirror(self):
        obj = plane("Half")
        obj.modifiers.new("Mirror", 'MIRROR')
        obj.modifiers.new("Subdivision", 'SUBSURF')
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['MIRROR', 'ARMATURE', 'SUBSURF'])
        self.assertEqual(obj.modifiers[1].object, self.rig)
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['MIRROR', 'ARMATURE', 'SUBSURF'])

    def test_bind_without_mirror_goes_first(self):
        obj = plane("P")
        obj.modifiers.new("Subdivision", 'SUBSURF')
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['ARMATURE', 'SUBSURF'])

    def test_bind_keeps_world_matrix(self):
        obj = plane("P")
        other = bpy.data.objects.new("Other", None)
        bpy.context.scene.collection.objects.link(other)
        other.location = (0.0, 3.0, 0.0)
        obj.parent = other
        obj.location = (1.0, 0.0, 2.0)
        obj.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        before = obj.matrix_world.copy()
        weights.bind(self.rig, obj)
        bpy.context.view_layer.update()
        self.assertEqual(obj.parent, self.rig)
        for a, b in zip(before, obj.matrix_world):
            np.testing.assert_allclose(tuple(a), tuple(b), atol=1e-6)

    def test_body_heat_uses_only_the_given_bones_and_restores_state(self):
        body = fx.mesh_object("Body", *fx.tube(0.86, 0.05, 0.07, 0.07, rings=24))
        other = plane("Other")
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        weights.body_heat(bpy.context, self.rig, body, {"Hips", "Spine", "Chest"})
        groups = {g.name for g in body.vertex_groups}
        self.assertTrue({"Hips", "Spine", "Chest"} <= groups)
        self.assertFalse(groups & {"Head", "LeftUpperLeg"})
        self.assertTrue(all(b.use_deform for b in self.rig.data.bones))
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertTrue(other.select_get())
        self.assertFalse(body.select_get())
        self.assertFalse(self.rig.select_get())


class SurfaceTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_surface_weights_interpolate(self):
        source = plane("Body")
        world = np.array([tuple(v.co) for v in source.data.vertices])
        left = np.clip((1.0 - world[:, 0]) / 2.0, 0.0, 1.0)
        weights.write(source, np.arange(len(world)), ["A", "B"], np.stack([left, 1.0 - left], axis=1))
        mask = np.ones(len(world), bool)
        out = weights.surface_weights([(source, mask)], ["A", "B"], np.array([(0.0, 0.0, 0.1), (-1.0, 0.3, 0.2)]))
        np.testing.assert_allclose(out[0], [0.5, 0.5], atol=1e-6)
        np.testing.assert_allclose(out[1], [1.0, 0.0], atol=1e-6)

    def test_surface_weights_skip_masked_triangles(self):
        source = plane("Body")
        world = np.array([tuple(v.co) for v in source.data.vertices])
        weights.write(source, np.arange(len(world)), ["A"], np.ones((len(world), 1)))
        out = weights.surface_weights([(source, np.zeros(len(world), bool))], ["A"], np.array([(0.0, 0.0, 0.1)]))
        np.testing.assert_allclose(out, 0.0)

    def test_nearest_bone_weights(self):
        rig = fx.rig_for()
        points = np.array([[0.0, 0.0, 0.55], [0.0, -0.005, 0.95]]) * fx.HEIGHT
        out = weights.nearest_bone_weights(rig, ["Hips", "Head"], points)
        np.testing.assert_allclose(out, [[1.0, 0.0], [0.0, 1.0]])


if __name__ == "__main__":
    tu.run_tests()
