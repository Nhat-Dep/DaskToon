# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon standard skeleton: Unity's 55 human bones, T-pose, mirrored sides, fitted to meshes (anime rig spec 4)."""

import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402

UNITY_HUMAN_BONES = {
    "Hips", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot", "Spine",
    "Chest", "UpperChest", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm",
    "LeftLowerArm", "RightLowerArm", "LeftHand", "RightHand", "LeftToes", "RightToes", "LeftEye", "RightEye", "Jaw",
} | {side + finger + segment for side in ("Left", "Right")
     for finger in ("Thumb", "Index", "Middle", "Ring", "Little")
     for segment in ("Proximal", "Intermediate", "Distal")}


def box(name, low, high):
    """A mesh object filling the box low-high (world)."""
    mesh = bpy.data.meshes.new(name)
    (x0, y0, z0), (x1, y1, z1) = low, high
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def world_head(rig, name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def world_tail(rig, name):
    return rig.matrix_world @ rig.data.bones[name].tail_local


class TemplateTest(unittest.TestCase):
    def test_bones_are_unity_human_bones(self):
        names = [b[0] for b in skeleton.bones()]
        self.assertEqual(len(names), 55)
        self.assertEqual(set(names), UNITY_HUMAN_BONES)
        self.assertEqual(tuple(names), skeleton.BONE_NAMES)

    def test_parents_come_first(self):
        seen = set()
        for name, parent, _head, _tail, _z in skeleton.bones():
            self.assertTrue(parent is None or parent in seen, name)
            seen.add(name)

    def test_sides_mirror(self):
        table = {b[0]: b for b in skeleton.bones()}
        for name, (_n, parent, head, tail, _z) in table.items():
            if not name.startswith("Left"):
                continue
            right = table["Right" + name[4:]]
            self.assertEqual(right[1], parent if parent is None or not parent.startswith("Left")
                             else "Right" + parent[4:])
            self.assertEqual(right[2], (-head[0], head[1], head[2]))
            self.assertEqual(right[3], (-tail[0], tail[1], tail[2]))
            self.assertGreater(head[0], 0.0, name)

    def test_required_bones_are_in_the_template(self):
        self.assertEqual(len(skeleton.REQUIRED), 15)
        self.assertTrue(set(skeleton.REQUIRED) <= set(skeleton.BONE_NAMES))
        self.assertTrue(set(skeleton.FACE_BONES) <= set(skeleton.BONE_NAMES))


class CreateTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_create_humanoid(self):
        rig = skeleton.create_humanoid(bpy.context, 1.6, (1.0, 2.0, 0.0))
        self.assertEqual(len(rig.data.bones), 55)
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertTrue(rig.data.use_mirror_x)
        self.assertTrue(rig.show_in_front)
        self.assertEqual(rig.mode, 'OBJECT')
        self.assertAlmostEqual((rig.matrix_world.translation - Vector((1.0, 2.0, 0.0))).length, 0.0, places=6)
        self.assertAlmostEqual(world_tail(rig, "Head").z, 0.99 * 1.6, places=5)
        self.assertGreater(world_head(rig, "LeftHand").x, 1.0)
        self.assertLess(world_head(rig, "RightHand").x, 1.0)
        self.assertEqual(rig.data.bones["LeftUpperArm"].parent.name, "LeftShoulder")
        self.assertTrue(rig.data.bones["LeftLowerArm"].use_connect)
        self.assertFalse(rig.data.bones["LeftShoulder"].use_connect)
        self.assertIsNone(rig.data.bones["Hips"].parent)

    def test_create_keeps_the_active_object(self):
        other = box("Other", (0, 0, 0), (1, 1, 1))
        bpy.context.view_layer.objects.active = other
        skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        self.assertEqual(bpy.context.view_layer.objects.active, other)

    def test_missing_bones(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["Spine"])
            edit.remove(edit["LeftIndexDistal"])
        self.assertEqual(skeleton.missing_bones(rig.data), ["Spine"])
        self.assertFalse(skeleton.is_humanoid(rig))
        self.assertFalse(skeleton.is_humanoid(None))
        self.assertFalse(skeleton.is_humanoid(box("Mesh", (0, 0, 0), (1, 1, 1))))

    def test_placement(self):
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        height, location = skeleton.placement([mesh], (0.0, 0.0, 0.0))
        self.assertAlmostEqual(height, 2.0, places=6)
        self.assertAlmostEqual((location - Vector((5.0, 0.0, 1.0))).length, 0.0, places=6)
        height, location = skeleton.placement([], (7.0, 0.0, 0.0))
        self.assertEqual(height, skeleton.DEFAULT_HEIGHT)
        self.assertEqual(tuple(location), (7.0, 0.0, 0.0))

    def test_fit_moves_joints_not_the_object(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["LeftLittleDistal"])
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        self.assertAlmostEqual(skeleton.fit(bpy.context, rig, [mesh]), 2.0, places=6)
        self.assertEqual(tuple(rig.matrix_world.translation), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(world_tail(rig, "Head").z, 1.0 + 0.99 * 2.0, places=5)
        self.assertAlmostEqual(world_head(rig, "Hips").x, 5.0, places=5)
        self.assertNotIn("LeftLittleDistal", rig.data.bones)
        self.assertEqual(len(rig.data.bones), 54)


if __name__ == "__main__":
    tu.run_tests()
