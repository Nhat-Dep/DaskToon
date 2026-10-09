# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Light Vector inputs follow the scene Sun without a button or drivers (UI spec 5)."""

import math
import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_sun_sync as ss  # noqa: E402


def face_shadow_material(name="Face"):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeFaceShadow')
    return mat, node


def close(a, b):
    return (Vector(a) - Vector(b)).length < 1e-5


class SunSyncTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.sun = tu.add_sun(rotation=(math.radians(40.0), 0.0, math.radians(30.0)))
        bpy.context.view_layer.update()

    def test_sync_writes_the_sun_direction_once(self):
        mat, node = face_shadow_material()
        vector = ss.sun_vector(self.sun)
        self.assertEqual(ss.sync_materials([mat], vector), 1)
        self.assertTrue(close(node.inputs["Light Vector"].default_value, vector))
        self.assertEqual(ss.sync_materials([mat], vector), 0)

    def test_linked_input_is_left_alone(self):
        mat, node = face_shadow_material()
        combine = mat.node_tree.nodes.new('ShaderNodeCombineXYZ')
        mat.node_tree.links.new(combine.outputs[0], node.inputs["Light Vector"])
        before = tuple(node.inputs["Light Vector"].default_value)
        self.assertEqual(ss.sync_materials([mat], ss.sun_vector(self.sun)), 0)
        self.assertEqual(tuple(node.inputs["Light Vector"].default_value), before)

    def test_node_inside_a_group_follows_too(self):
        group = bpy.data.node_groups.new("FaceGroup", 'ShaderNodeTree')
        inner = group.nodes.new('ShaderNodeAnimeFaceShadow')
        mat = tu.new_material("Grouped")
        holder = mat.node_tree.nodes.new('ShaderNodeGroup')
        holder.node_tree = group
        self.assertEqual(ss.sync_materials([mat], ss.sun_vector(self.sun)), 1)
        self.assertTrue(close(inner.inputs["Light Vector"].default_value, ss.sun_vector(self.sun)))

    def test_old_sync_sun_driver_is_removed(self):
        mat, node = face_shadow_material()
        node.inputs["Light Vector"].driver_add("default_value", 0)
        ss.sync_materials([mat], ss.sun_vector(self.sun))
        drivers = mat.node_tree.animation_data.drivers if mat.node_tree.animation_data else []
        self.assertEqual(len(drivers), 0)

    def test_rotating_the_sun_updates_materials_through_the_handler(self):
        mat, node = face_shadow_material()
        bpy.context.view_layer.update()
        self.sun.rotation_euler = (math.radians(70.0), 0.0, math.radians(-60.0))
        bpy.context.view_layer.update()
        self.assertTrue(close(node.inputs["Light Vector"].default_value, ss.sun_vector(self.sun)))

    def test_animated_sun_turns_materials_on_frame_change(self):
        # Frame changes run frame_change_post, not depsgraph_update_post: the old Sync Sun driver followed every frame.
        mat, node = face_shadow_material()
        bpy.context.view_layer.update()
        scene = bpy.context.scene
        self.sun.keyframe_insert("rotation_euler", frame=1)
        self.sun.rotation_euler = (math.radians(80.0), 0.0, math.radians(-50.0))
        self.sun.keyframe_insert("rotation_euler", frame=20)
        scene.frame_set(1)
        at_one = tuple(node.inputs["Light Vector"].default_value)
        scene.frame_set(20)
        self.assertTrue(close(node.inputs["Light Vector"].default_value, ss.sun_vector(self.sun)))
        self.assertFalse(close(node.inputs["Light Vector"].default_value, at_one))

    def test_no_sun_changes_nothing(self):
        bpy.data.objects.remove(self.sun)
        mat, node = face_shadow_material()
        before = tuple(node.inputs["Light Vector"].default_value)
        bpy.context.view_layer.update()
        self.assertEqual(tuple(node.inputs["Light Vector"].default_value), before)
        self.assertIsNone(ss.find_sun(bpy.context.scene))


if __name__ == "__main__":
    tu.run_tests()
