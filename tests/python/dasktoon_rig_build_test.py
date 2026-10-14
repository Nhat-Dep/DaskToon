# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build Rig on test characters, as separate objects and as one mesh by material (anime rig spec 6)."""

import os
import sys
import unittest

import bmesh
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
        # The 55 of the skeleton, LookTarget (R3, spec 10.1) and the chains.
        self.assertEqual(len(self.rig.data.bones), 55 + 1 + len(HAIR) + len(SKIRT))
        for obj in self.objs.values():
            self.assertEqual(len([m for m in obj.modifiers if m.type == 'ARMATURE']), 1)
            self.assert_unity_weights(obj, self.rig)

    def test_stale_generated_groups_are_removed(self):
        self.parts[3].chain_count = 4
        build.build(bpy.context, self.rig, self.parts)
        skirt_groups = {g.name for g in self.objs["Skirt"].vertex_groups if g.name.startswith("Skirt")}
        self.assertEqual(skirt_groups, {"Skirt%d_%d" % (c, k) for c in range(1, 5) for k in range(1, 4)})
        self.assertNotIn("Skirt8_1", self.rig.data.bones)


class FarClothingTest(unittest.TestCase):
    def test_dress_over_no_skin_takes_its_own_weights(self):
        """A dress over a Body that has no torso under it (real model test: the dress copied the weights of the
        shoulders 30 cm away and followed the arms) takes automatic weights of its own: the front of its middle
        follows the spine."""
        import dasktoon_rig_skeleton_test as st
        bpy.ops.wm.read_factory_settings(use_empty=True)
        h = fx.HEIGHT
        pieces = [fx.tube(0.99, 0.80, 0.06, 0.06, rings=6)]  # head and neck
        for s in (1.0, -1.0):
            pieces.append(st.tube((0.05 * s * h, 0.0, 0.47 * h), (0.06 * s * h, 0.0, 0.05 * h), 0.04 * h))
        verts, faces = [], []
        for piece_verts, piece_faces in pieces:
            faces += [tuple(i + len(verts) for i in f) for f in piece_faces]
            verts += piece_verts
        body = fx.mesh_object("Body", verts, faces)
        dress = fx.mesh_object("Dress", *fx.tube(0.74, 0.5, 0.12, 0.12, rings=6))
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, [parts.Part("Body", body, 'BODY'), parts.Part("Dress", dress, 'CLOTHING')])
        front_middle = 3 * 16 + 12  # ring 3 of 6 (0.62 of the height), the vertex at -Y
        self.assertIn(dominant(dress, rig, front_middle)[0], {"Hips", "Spine", "Chest", "UpperChest"})
        CheckedWeightsMixin.assert_unity_weights(self, dress, rig)
        self.assertFalse([w for w in result.warnings if "Dress" in w], result.warnings)

    def test_shirt_on_the_skin_still_copies_it(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        build.build(bpy.context, rig, [parts.Part("Body", objs["Body"], 'BODY'),
                                       parts.Part("Shirt", objs["Shirt"], 'CLOTHING')])
        names = deform_names(rig)
        shirt, body = weights.read(objs["Shirt"], names), weights.read(objs["Body"], names)
        # The Shirt (radius 0.08 of the height) is 0.01 out from the Body (0.07): it copies the Body, so it uses only
        # bones the Body uses.
        self.assertGreater(shirt.sum(), 0.0)
        self.assertEqual({names[j] for j in np.nonzero(shirt.sum(axis=0))[0]} - {names[j] for j in np.nonzero(body.sum(axis=0))[0]}, set())


def merged_parts(obj):
    return [
        parts.Part("Body", obj, 'BODY'),
        parts.Part("Shirt", obj, 'CLOTHING', scope='MATERIAL', material="Shirt"),
        parts.Part("Hair", obj, 'HAIR', scope='MATERIAL', material="Hair"),
        parts.Part("Skirt", obj, 'SKIRT', scope='MATERIAL', material="Skirt"),
        parts.Part("Ribbon", obj, 'ACCESSORY', scope='MATERIAL', material="Ribbon"),
        parts.Part("Eye", obj, 'ACCESSORY', scope='MATERIAL', material="Eye"),
    ]


class MergedTest(CheckedWeightsMixin, unittest.TestCase):
    def test_merged_mesh_by_material(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = fx.character(merged=True)["Character"]
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, merged_parts(obj))
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

    def test_attach_bone_must_not_be_generated(self):
        build.build(bpy.context, self.rig, separate_parts(self.objs))
        before = sorted(b.name for b in self.rig.data.bones)
        hanging = separate_parts(self.objs)
        hanging[2].bone = "Skirt1_1"  # hair hanging from a bone the next build removes and makes again
        with self.assertRaises(build.BuildError) as caught:
            build.build(bpy.context, self.rig, hanging)
        self.assertIn("Skirt1_1", str(caught.exception))
        self.assertEqual(sorted(b.name for b in self.rig.data.bones), before)

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


class ColliderTest(unittest.TestCase):
    def test_build_makes_body_colliders(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, separate_parts(objs))
        colliders = {c.bone: c.radius for c in rig.data.dasktoon_rig.colliders}
        self.assertEqual(set(colliders), set(build.COLLIDER_BONES))
        self.assertEqual([name for name, _radius in result.colliders], list(colliders))
        np.testing.assert_allclose([radius for _name, radius in result.colliders], list(colliders.values()), rtol=1e-6)
        body_radius = 0.07 * fx.HEIGHT
        self.assertTrue(0.3 * body_radius < colliders["Chest"] < body_radius, colliders["Chest"])
        self.assertTrue(all(r > 0.0 for r in colliders.values()))
        build.build(bpy.context, rig, separate_parts(objs))
        self.assertEqual(len(rig.data.dasktoon_rig.colliders), len(build.COLLIDER_BONES))

    def test_colliders_are_in_armature_units(self):
        found = {}
        for scale in (1.0, 2.0):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            objs = fx.character()
            rig = fx.rig_for()
            for obj in (rig, *objs.values()):
                obj.scale = (scale, scale, scale)
            bpy.context.view_layer.update()
            result = build.build(bpy.context, rig, separate_parts(objs))
            found[scale] = ({c.bone: c.radius for c in rig.data.dasktoon_rig.colliders}, dict(result.colliders))
        (local, world), (local2, world2) = found[1.0], found[2.0]
        for name in build.COLLIDER_BONES:
            self.assertAlmostEqual(local2[name], local[name], delta=1e-3 * local[name], msg=name)
            self.assertAlmostEqual(world2[name], 2.0 * world[name], delta=2e-3 * world[name], msg=name)

    def test_part_sway_defaults(self):
        part = parts.Part("Hair", None, 'HAIR')
        self.assertEqual((part.stiffness, part.gravity, part.drag, part.radius), (1.0, 0.2, 0.4, 0.03))


def flip(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def mesh_warnings(result):
    return [w for w in result.warnings if "inward" in w or "scale" in w]


class MeshWarningTest(unittest.TestCase):
    def test_the_test_character_has_none(self):
        for merged in (False, True):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            objs = fx.character(merged=merged)
            found = build.build(bpy.context, fx.rig_for(),
                                merged_parts(objs["Character"]) if merged else separate_parts(objs))
            self.assertEqual(mesh_warnings(found), [], merged)

    def test_inward_body_faces(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        flip(objs["Body"])
        found = mesh_warnings(build.build(bpy.context, fx.rig_for(), separate_parts(objs)))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("Body: "), found)
        self.assertIn("inward", found[0])

    def test_negative_or_uneven_scale(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        objs["Skirt"].scale = (1.0, 1.0, 1.2)
        objs["Ribbon"].scale = (-1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        found = mesh_warnings(build.build(bpy.context, fx.rig_for(), separate_parts(objs)))
        self.assertEqual(sorted(w.split(" ")[0] for w in found), ["Ribbon", "Skirt"])


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
            self.assertIn("  userData: DaskToonHumanoid\n", f.read())  # its importer makes it Humanoid


def evaluated(obj):
    """World positions of obj's vertices as shown (modifiers on)."""
    shown = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = shown.to_mesh()
    try:
        co = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", co)
    finally:
        shown.to_mesh_clear()
    matrix = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


class MirrorTest(unittest.TestCase):
    def test_a_mirrored_half_follows_its_own_side(self):
        """A sleeve modelled on the right arm only, the left one made by a Mirror modifier (as on lr_shape). Blender
        gives the mirrored half the Left groups only where the object has them, with the modifier's Vertex Groups on:
        Build sees to both. Before, the left sleeve followed the right arm and flew across the body in Wave."""
        import dasktoon_rig_regions_test as rt
        from bl_ui import dasktoon_rig as ui
        from dasktoon_rig import check
        rig, _objs = rt.rigged()
        start, end = rt.mirrored(rt.ARM_START), rt.mirrored(rt.ARM_END)  # the right arm
        sleeve = rt.merged("Sleeve", [rt.st.tube(tuple(start + (end - start) * 0.3), tuple(start + (end - start) * 0.9),
                                                 0.07)])
        mirror = sleeve.modifiers.new("Mirror", 'MIRROR')
        mirror.use_mirror_vertex_groups = False
        ui.add_part(rig, sleeve, 'CLOTHING')
        result = build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        self.assertTrue(mirror.use_mirror_vertex_groups)
        self.assertIn("Sleeve: the Mirror modifier now flips the vertex groups, so the mirrored half follows its own "
                      "side", result.warnings)
        self.assertIsNotNone(sleeve.vertex_groups.get("LeftLowerArm"))
        rest = evaluated(sleeve)
        check.apply_pose(bpy.context, rig, 'WAVE')
        try:
            moved = evaluated(sleeve)
        finally:
            check.apply_pose(bpy.context, rig, 'REST')
        left, right = rest[:, 0] > 0.05, rest[:, 0] < -0.05
        self.assertTrue(left.any())
        self.assertLess(np.linalg.norm(moved[left] - rest[left], axis=1).max(), 1e-3)  # the left arm stays down
        self.assertGreater(np.linalg.norm(moved[right] - rest[right], axis=1).max(), 0.3)  # the right one waves


if __name__ == "__main__":
    tu.run_tests()
