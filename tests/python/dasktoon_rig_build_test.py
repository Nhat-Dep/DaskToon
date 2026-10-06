# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build Rig on test characters, as separate objects and as one mesh by material (anime rig spec 6)."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, parts, weights  # noqa: E402

HAIR = ["Hair_%d" % k for k in range(1, 5)]
SKIRT = ["Skirt%d_%d" % (c, k) for c in range(1, 9) for k in range(1, 4)]


def deform_names(rig):
    return [b.name for b in rig.data.bones if b.use_deform]


def dominant(obj, rig, vertex):
    names = deform_names(rig)
    row = weights.read(obj, names)[vertex]
    return names[int(np.argmax(row))], float(row.max())


def separate_parts(objs):
    return [
        parts.Part("Body", objs["Body"], 'BODY'),
        parts.Part("Shirt", objs["Shirt"], 'CLOTHING'),
        parts.Part("Hair", objs["Hair"], 'HAIR'),
        parts.Part("Skirt", objs["Skirt"], 'SKIRT'),
        parts.Part("Ribbon", objs["Ribbon"], 'ACCESSORY'),
        parts.Part("Eye", objs["Eye"], 'ACCESSORY'),
    ]


class CheckedWeightsMixin:
    def assert_unity_weights(self, obj, rig):
        matrix = weights.read(obj, deform_names(rig))
        counts = (matrix > 0).sum(axis=1)
        self.assertTrue(np.all(counts >= 1), obj.name)
        self.assertTrue(np.all(counts <= 4), obj.name)
        np.testing.assert_allclose(matrix.sum(axis=1), 1.0, atol=1e-5, err_msg=obj.name)
        self.assertTrue(np.all(matrix[matrix > 0] >= 0.01 - 1e-9), obj.name)


class SeparateTest(CheckedWeightsMixin, unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        self.parts = separate_parts(self.objs)
        self.result = build.build(bpy.context, self.rig, self.parts)

    def test_generated_bones(self):
        self.assertEqual(sorted(self.result.bones), sorted(HAIR + SKIRT))
        self.assertEqual(self.result.chains, 9)
        bones = self.rig.data.bones
        self.assertEqual(bones["Hair_1"].parent.name, "Head")
        self.assertEqual(bones["Hair_2"].parent.name, "Hair_1")
        self.assertTrue(bones["Hair_2"].use_connect)
        self.assertEqual(bones["Skirt1_1"].parent.name, "Hips")
        self.assertEqual(bones["Hair_3"]["dt_part"], "Hair")
        self.assertTrue(all(bones[n].use_deform for n in HAIR + SKIRT))
        self.assertIn("6 objects", self.result.summary())

    def test_every_object_is_bound_with_unity_weights(self):
        for obj in self.objs.values():
            self.assertEqual(obj.parent, self.rig)
            self.assertEqual([m.object for m in obj.modifiers if m.type == 'ARMATURE'], [self.rig])
            self.assert_unity_weights(obj, self.rig)

    def test_hair_root_follows_the_head_and_tip_the_last_bone(self):
        hair = self.objs["Hair"]
        self.assertEqual(dominant(hair, self.rig, 0), ("Head", 1.0))
        name, value = dominant(hair, self.rig, len(hair.data.vertices) - 1)
        self.assertEqual(name, "Hair_4")
        self.assertAlmostEqual(value, 1.0, places=5)

    def test_skirt_front_bottom_follows_the_front_strip(self):
        skirt = self.objs["Skirt"]
        front_bottom = 6 * 16 + 12  # last ring, the vertex at -Y
        self.assertEqual(dominant(skirt, self.rig, front_bottom), ("Skirt1_3", 1.0))
        self.assertEqual(dominant(skirt, self.rig, 12)[0], "Hips")

    def test_shirt_copies_the_body(self):
        shirt = self.objs["Shirt"]
        names = deform_names(self.rig)
        used = {names[j] for j in np.nonzero(weights.read(shirt, names).sum(axis=0))[0]}
        self.assertTrue(used & {"Spine", "Chest", "UpperChest"}, used)
        self.assertFalse(used & (set(HAIR + SKIRT) | {"LeftEye", "RightEye", "Jaw"}), used)

    def test_accessories_are_rigid_on_the_nearest_bone(self):
        self.assertEqual(set(dominant(self.objs["Ribbon"], self.rig, v) for v in range(8)), {("Head", 1.0)})
        self.assertEqual(set(dominant(self.objs["Eye"], self.rig, v) for v in range(8)), {("LeftEye", 1.0)})

    def test_second_build_replaces_generated_bones(self):
        again = build.build(bpy.context, self.rig, self.parts)
        self.assertEqual(sorted(again.bones), sorted(HAIR + SKIRT))
        self.assertEqual(len(self.rig.data.bones), 55 + len(HAIR) + len(SKIRT))
        for obj in self.objs.values():
            self.assertEqual(len([m for m in obj.modifiers if m.type == 'ARMATURE']), 1)
            self.assert_unity_weights(obj, self.rig)

    def test_stale_generated_groups_are_removed(self):
        self.parts[3].chain_count = 4
        build.build(bpy.context, self.rig, self.parts)
        skirt_groups = {g.name for g in self.objs["Skirt"].vertex_groups if g.name.startswith("Skirt")}
        self.assertEqual(skirt_groups, {"Skirt%d_%d" % (c, k) for c in range(1, 5) for k in range(1, 4)})
        self.assertNotIn("Skirt8_1", self.rig.data.bones)


class MergedTest(CheckedWeightsMixin, unittest.TestCase):
    def test_merged_mesh_by_material(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = fx.character(merged=True)["Character"]
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, [
            parts.Part("Body", obj, 'BODY'),
            parts.Part("Shirt", obj, 'CLOTHING', scope='MATERIAL', material="Shirt"),
            parts.Part("Hair", obj, 'HAIR', scope='MATERIAL', material="Hair"),
            parts.Part("Skirt", obj, 'SKIRT', scope='MATERIAL', material="Skirt"),
            parts.Part("Ribbon", obj, 'ACCESSORY', scope='MATERIAL', material="Ribbon"),
            parts.Part("Eye", obj, 'ACCESSORY', scope='MATERIAL', material="Eye"),
        ])
        self.assertEqual(sorted(result.bones), sorted(HAIR + SKIRT))
        self.assert_unity_weights(obj, rig)
        hair = parts.part_vertices(parts.Part("Hair", obj, scope='MATERIAL', material="Hair"))
        names = deform_names(rig)
        used = {names[j] for j in np.nonzero(weights.read(obj, names)[hair].sum(axis=0))[0]}
        self.assertTrue(used <= {"Head"} | set(HAIR), used)


class TransformTest(unittest.TestCase):
    def joints(self, scaled):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        hair = objs["Hair"]
        if scaled:
            offset = Vector((0.0, 0.0, 0.5 * fx.HEIGHT))
            for v in hair.data.vertices:
                v.co = (v.co - offset) / 2.0
            hair.scale = (2.0, 2.0, 2.0)
            hair.location = offset
        bpy.context.view_layer.update()
        before = hair.matrix_world.copy()
        rig = fx.rig_for()
        build.build(bpy.context, rig, separate_parts(objs))
        bpy.context.view_layer.update()
        for a, b in zip(before, hair.matrix_world):
            np.testing.assert_allclose(tuple(a), tuple(b), atol=1e-6)
        return [tuple(rig.matrix_world @ rig.data.bones[name].head_local) for name in HAIR]

    def test_scaled_hair_object_gets_world_joints(self):
        np.testing.assert_allclose(self.joints(True), self.joints(False), atol=1e-4)


class ModeAndErrorTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()

    def test_build_returns_to_pose_mode(self):
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode='POSE')
        build.build(bpy.context, self.rig, separate_parts(self.objs))
        self.assertEqual(self.rig.mode, 'POSE')
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)

    def test_errors_change_nothing(self):
        cases = [
            [],
            [parts.Part("Shirt", self.objs["Shirt"], 'CLOTHING')],
            [parts.Part("Body", self.objs["Body"], 'BODY', scope='MATERIAL', material="Nope")],
            [parts.Part("Body", self.objs["Body"], 'BODY'), parts.Part("Hair", self.objs["Hair"], 'HAIR', bone="Nope")],
            [parts.Part("Body", None, 'BODY')],
        ]
        for case in cases:
            with self.assertRaises(build.BuildError):
                build.build(bpy.context, self.rig, case)
        self.objs["Body"].hide_set(True)
        with self.assertRaises(build.BuildError):
            build.build(bpy.context, self.rig, [parts.Part("Body", self.objs["Body"], 'BODY')])
        self.assertEqual(len(self.rig.data.bones), 55)
        for obj in self.objs.values():
            self.assertEqual(len(obj.modifiers), 0)
            self.assertEqual(len(obj.vertex_groups), 0)
            self.assertIsNone(obj.parent)

    def test_not_a_standard_skeleton(self):
        from dasktoon_rig import skeleton
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Spine"])
        with self.assertRaises(build.BuildError) as caught:
            build.build(bpy.context, self.rig, separate_parts(self.objs))
        self.assertIn("Spine", str(caught.exception))

    def test_shared_mesh_is_refused(self):
        twin = bpy.data.objects.new("Twin", self.objs["Body"].data)
        bpy.context.scene.collection.objects.link(twin)
        with self.assertRaises(build.BuildError):
            build.build(bpy.context, self.rig, [parts.Part("Body", self.objs["Body"], 'BODY')])

    def test_later_role_wins_a_vertex(self):
        body = self.objs["Body"]
        group = body.vertex_groups.new(name="DT_Top")
        top = list(range(16))
        group.add(top, 1.0, 'REPLACE')
        build.build(bpy.context, self.rig, [
            parts.Part("Top", body, 'ACCESSORY', scope='VERTEX_GROUP', vertex_group="DT_Top", bone="Neck"),
            parts.Part("Body", body, 'BODY'),
        ])
        self.assertEqual({dominant(body, self.rig, v) for v in top}, {("Neck", 1.0)})


class HumanoidTest(unittest.TestCase):
    def test_export_is_humanoid_for_one_standard_skeleton(self):
        import dasktoon_export
        from dasktoon_rig import skeleton
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        self.assertTrue(dasktoon_export._humanoid([rig] + list(objs.values())))
        self.assertFalse(dasktoon_export._humanoid(list(objs.values())))
        second = fx.rig_for()
        self.assertFalse(dasktoon_export._humanoid([rig, second]))
        with skeleton.editing(bpy.context, second) as edit:
            edit.remove(edit["Head"])
        self.assertFalse(dasktoon_export._humanoid([second]))

    def test_exported_model_meta_is_humanoid(self):
        import tempfile
        import dasktoon_export
        from dasktoon_export import targets
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        build.build(bpy.context, rig, separate_parts(objs))
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_rig_"), "Hero")
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)
        self.assertEqual(rep.model, "Hero/Model/Hero.fbx")
        with open(os.path.join(target.root, "Hero", "Model", "Hero.fbx.meta"), encoding="utf-8") as f:
            self.assertIn("  animationType: 3\n", f.read())


if __name__ == "__main__":
    tu.run_tests()
