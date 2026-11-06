# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Repair Shape Keys: keys made before the mesh was edited pull the edited vertices back to where they were, every key
by the same offset, and keys add up (temp_2_1, a real model: 191 of 226 keys held such an offset on 213 vertices of the
hands and chest; with 11 keys on, the hands moved 25 mm); a single vertex a key throws far from its neighbours (a left
over of merging two models: "joy" threw one at the throat 11.5 mm) takes its neighbours' move. The Check lists both."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import expressions  # noqa: E402

GRID = 9  # a flat face of GRID x GRID vertices, x from -1 to 1, z from 0 to 2
TOP = np.array([z > 1.5 for z in np.repeat(np.linspace(0.0, 2.0, GRID), GRID)])
BOTTOM_ROW = np.arange(GRID)  # the "hand": edited after the keys were made


def face(n_keys=6):
    """A plane with a Basis and `n_keys` keys, each moving the top rows up by its own amount."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts = np.array([(x, 0.0, z) for z in np.linspace(0.0, 2.0, GRID) for x in np.linspace(-1.0, 1.0, GRID)])
    faces = [(r * GRID + c, r * GRID + c + 1, (r + 1) * GRID + c + 1, (r + 1) * GRID + c)
             for r in range(GRID - 1) for c in range(GRID - 1)]
    mesh = bpy.data.meshes.new("Face")
    mesh.from_pydata(verts.tolist(), [], faces)
    obj = bpy.data.objects.new("Face", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.shape_key_add(name="Basis", from_mix=False)
    for k in range(n_keys):
        block = obj.shape_key_add(name="Key%d" % k, from_mix=False)
        co = verts.copy()
        co[TOP, 2] += 0.01 * (k + 1)
        block.data.foreach_set("co", co.ravel())
    return obj


def edit_basis(obj, vertices, delta):
    """Move `vertices` in the Basis only, as editing the mesh with the Basis active does: the other keys keep them."""
    key = obj.data.shape_keys
    co = np.empty(len(obj.data.vertices) * 3)
    key.reference_key.data.foreach_get("co", co)
    co = co.reshape(-1, 3)
    co[vertices] += delta
    key.reference_key.data.foreach_set("co", co.ravel())
    obj.data.vertices.foreach_set("co", co.ravel())


def rigged(obj):
    """An armature Chest > Neck > Head deforming obj: the top rows follow Head, the rest Chest."""
    arm = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    parent = None
    for name, z0, z1 in (("Chest", 0.0, 1.0), ("Neck", 1.0, 1.4), ("Head", 1.4, 2.0)):
        bone = arm.data.edit_bones.new(name)
        bone.head, bone.tail, bone.parent = (0, -0.2, z0), (0, -0.2, z1), parent
        parent = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.modifiers.new("Armature", 'ARMATURE').object = arm
    obj.vertex_groups.new(name="Head").add(np.nonzero(TOP)[0].tolist(), 1.0, 'REPLACE')
    obj.vertex_groups.new(name="Chest").add(np.nonzero(~TOP)[0].tolist(), 1.0, 'REPLACE')
    return arm


def offsets(obj, name):
    key = obj.data.shape_keys
    base = np.empty(len(obj.data.vertices) * 3)
    key.reference_key.data.foreach_get("co", base)
    co = np.empty_like(base)
    key.key_blocks[name].data.foreach_get("co", co)
    return (co - base).reshape(-1, 3)


class RepairTest(unittest.TestCase):
    def test_keys_made_before_an_edit_pull_the_old_shape_back(self):
        obj = face()
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.02))
        stale, _offset = expressions.stale_vertices(obj)
        self.assertEqual(sorted(np.nonzero(stale)[0].tolist()), BOTTOM_ROW.tolist())
        before_top = offsets(obj, "Key3")[TOP].copy()
        stale_count, thrown = expressions.repair_keys(obj)
        self.assertEqual((stale_count, thrown), (GRID, {}))
        for k in range(6):
            np.testing.assert_allclose(offsets(obj, "Key%d" % k)[BOTTOM_ROW], 0.0, atol=1e-7)
        np.testing.assert_allclose(offsets(obj, "Key3")[TOP], before_top, atol=1e-7)  # the expression stays
        self.assertFalse(expressions.stale_vertices(obj)[0].any())

    def test_a_key_added_up_from_old_keys_holds_the_offset_several_times(self):
        """Keys built by adding others ("joy" from eyes, brows and mouth; Fill Empty Expressions makes "e" from "a" and
        "i") hold the old offset as often as they add keys: temp_2_1's "joy" still moved the hands 17 mm."""
        obj = face()
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.02))
        added = obj.shape_key_add(name="Joy", from_mix=False)
        co = np.empty(len(obj.data.vertices) * 3)
        obj.data.shape_keys.reference_key.data.foreach_get("co", co)
        co = co.reshape(-1, 3) + offsets(obj, "Key0") + offsets(obj, "Key1") + offsets(obj, "Key2")
        added.data.foreach_set("co", co.ravel())
        top = offsets(obj, "Joy")[TOP].copy()
        expressions.repair_keys(obj)
        np.testing.assert_allclose(offsets(obj, "Joy")[BOTTOM_ROW], 0.0, atol=1e-7)
        np.testing.assert_allclose(offsets(obj, "Joy")[TOP], top, atol=1e-7)

    def test_a_vertex_thrown_far_by_one_key(self):
        obj = face()
        block = obj.data.shape_keys.key_blocks["Key2"]
        thrown_vertex = GRID * 3 + 4  # mid face, its neighbours still
        block.data[thrown_vertex].co.y -= 0.4
        self.assertEqual(expressions.spikes(obj), {"Key2": [thrown_vertex]})
        _stale, thrown = expressions.repair_keys(obj)
        self.assertEqual(thrown, {"Key2": 1})
        np.testing.assert_allclose(offsets(obj, "Key2")[thrown_vertex], 0.0, atol=1e-7)
        self.assertEqual(expressions.spikes(obj), {})

    def test_the_top_rows_moving_together_are_no_spike(self):
        obj = face()
        self.assertEqual(expressions.spikes(obj), {})
        self.assertFalse(expressions.stale_vertices(obj)[0].any())  # each key moves them by its own amount

    def test_two_keys_agreeing_are_not_enough(self):
        obj = face(n_keys=2)
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.0))
        self.assertFalse(expressions.stale_vertices(obj)[0].any())

    def test_a_bend_fix_made_after_the_edit_is_left_alone(self):
        obj = face()
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.0))
        fix = obj.shape_key_add(name="DT_Fix_LeftKnee", from_mix=False)  # made from the edited Basis
        co = np.empty(len(obj.data.vertices) * 3)
        obj.data.shape_keys.reference_key.data.foreach_get("co", co)
        co = co.reshape(-1, 3)
        co[BOTTOM_ROW, 1] += 0.03
        fix.data.foreach_set("co", co.ravel())
        expressions.repair_keys(obj)
        np.testing.assert_allclose(offsets(obj, "DT_Fix_LeftKnee")[BOTTOM_ROW], [(0.0, 0.03, 0.0)] * GRID, atol=1e-6)

    def test_a_face_key_moving_what_follows_the_chest(self):
        """A face key that also moves skin following the chest (temp_2_1, merged from two models: "Eyes Sharp 2 R"
        moved 195 vertices of the upper chest up to 38 mm) leaves it; a key of the body is left alone."""
        obj = face()
        rig = rigged(obj)
        face_key = obj.data.shape_keys.key_blocks["Key0"]
        face_key.data[0].co.y -= 0.03  # bottom row: follows the chest
        face_key.data[1].co.y -= 0.03
        body_key = obj.shape_key_add(name="Breathe", from_mix=False)
        for v in BOTTOM_ROW.tolist():
            body_key.data[v].co.y -= 0.02
        self.assertEqual(expressions.off_region(obj, rig), {"Key0": [0, 1]})
        expressions.repair_keys(obj, rig)
        np.testing.assert_allclose(offsets(obj, "Key0")[[0, 1]], 0.0, atol=1e-7)
        self.assertGreater(np.abs(offsets(obj, "Key0")[TOP]).max(), 0.005)  # the face still moves
        np.testing.assert_allclose(offsets(obj, "Breathe")[BOTTOM_ROW, 1], -0.02, atol=1e-6)
        self.assertEqual(expressions.off_region(obj, rig), {})

    def test_repair_leaves_nothing_for_the_check(self):
        """Old offsets joined a stray group to the face, so it passed for face; once they were taken out it stood alone
        (temp_2_1: the back of the neck in "Eyes Sharp 2 R"), and the Check found it again after Repair."""
        from dasktoon_rig import check
        obj = face()
        rig = rigged(obj)
        row = lambda r: list(range(GRID * r, GRID * (r + 1)))
        edit_basis(obj, row(6), (0.0, 0.0, 0.02))  # every key now holds row 6, joining row 5 to the top rows
        key = obj.data.shape_keys.key_blocks["Key0"]
        for v in row(5):
            key.data[v].co.y -= 0.002  # a stray move, following the chest
        expressions.repair_keys(obj, rig)
        self.assertEqual(check.key_issues([obj], rig), [])
        np.testing.assert_allclose(offsets(obj, "Key0")[row(5)], 0.0, atol=1e-7)

    def test_the_button(self):
        obj = face()
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.0))
        obj.data.shape_keys.key_blocks["Key1"].data[GRID * 4 + 4].co.y += 0.5
        bpy.context.view_layer.objects.active = obj
        with bpy.context.temp_override(object=obj, active_object=obj):
            self.assertEqual(bpy.ops.dasktoon.repair_shape_keys(), {'FINISHED'})
        self.assertFalse(expressions.stale_vertices(obj)[0].any())
        self.assertEqual(expressions.spikes(obj), {})

    def test_the_check_lists_them(self):
        from dasktoon_rig import check
        obj = face()
        edit_basis(obj, BOTTOM_ROW, (0.05, 0.0, 0.0))
        self.assertEqual(check.key_issues([obj]), [(obj, GRID, 0)])
        expressions.repair_keys(obj)
        self.assertEqual(check.key_issues([obj]), [])


if __name__ == "__main__":
    tu.run_tests()
