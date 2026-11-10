# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Controls (rig controls spec 6): a Rigify control layer on the DaskToon joints. The DaskToon skeleton does not move
at rest and is the only one that deforms; the IK and FK controls move it; Remove leaves the rig as it was; Build Rig
keeps the controls; the panel shows the IK/FK switches."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, controls, parts  # noqa: E402


def character():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    build.build(bpy.context, rig, [
        parts.Part("Body", objs["Body"], 'BODY'),
        parts.Part("Shirt", objs["Shirt"], 'CLOTHING'),
        parts.Part("Hair", objs["Hair"], 'HAIR'),
        parts.Part("Skirt", objs["Skirt"], 'SKIRT'),
    ])
    for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
        item = rig.data.dasktoon_rig.parts.add()
        item.name, item.object, item.role = name, objs[name], role
    return rig, objs


def bone_matrices(rig, names):
    bpy.context.view_layer.update()
    return {n: np.array(rig.matrix_world @ rig.pose.bones[n].matrix) for n in names}


def body_points(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


class ControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs = character()
        cls.dask = [b.name for b in cls.rig.data.bones]
        cls.deform = sorted(b.name for b in cls.rig.data.bones if b.use_deform)
        cls.rest = bone_matrices(cls.rig, cls.dask)
        cls.body = body_points(cls.objs["Body"])
        cls.count = controls.add(bpy.context, cls.rig)

    def setUp(self):
        for pb in self.rig.pose.bones:
            pb.matrix_basis = Matrix()
        for pb, _label in controls.limb_switches(self.rig):
            pb["IK_FK"] = 0.0
        self.rig.update_tag()
        bpy.context.view_layer.update()

    def test_control_bones_are_added_and_only_dasktoon_deforms(self):
        self.assertGreater(self.count, 100)
        self.assertTrue(controls.has_controls(self.rig))
        for name in ("ORG-spine", "hand_ik.L", "foot_ik.R", "upper_arm_fk.L", "torso", "root"):
            self.assertIn(name, self.rig.data.bones, name)
        self.assertFalse([c.name for c in self.rig.data.collections_all if c.name.startswith("Face")])
        self.assertEqual(sorted(b.name for b in self.rig.data.bones if b.use_deform), self.deform)
        con = self.rig.pose.bones["LeftUpperArm"].constraints[controls.FOLLOW]
        self.assertEqual(con.subtarget, "DTH-LeftUpperArm")
        self.assertFalse(any(t.name.startswith("rig_ui") for t in bpy.data.texts))
        self.assertNotIn("metarig", [o.name for o in bpy.data.objects])

    def test_nothing_moves_at_rest(self):
        now = bone_matrices(self.rig, self.dask)
        for name in self.dask:
            np.testing.assert_allclose(now[name][:3, 3], self.rest[name][:3, 3], atol=1e-4, err_msg=name)
            np.testing.assert_allclose(now[name][:3, :3], self.rest[name][:3, :3], atol=1e-3, err_msg=name)
        np.testing.assert_allclose(body_points(self.objs["Body"]), self.body, atol=1e-4)

    def test_ik_hand_moves_the_arm(self):
        hand = self.rig.pose.bones["hand_ik.L"]
        before = np.array(self.rig.matrix_world @ self.rig.pose.bones["LeftHand"].head)
        hand.location = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        target = np.array(self.rig.matrix_world @ hand.head) + np.array((0.0, -0.1, 0.15))
        hand.matrix = self.rig.matrix_world.inverted() @ Matrix.Translation(target) @ \
            (self.rig.matrix_world @ hand.matrix).to_3x3().to_4x4()
        bpy.context.view_layer.update()
        after = np.array(self.rig.matrix_world @ self.rig.pose.bones["LeftHand"].head)
        np.testing.assert_allclose(after, target, atol=2e-3)
        self.assertGreater(np.linalg.norm(after - before), 0.1)

    def test_fk_upper_arm_turns_the_arm(self):
        for pb, label in controls.limb_switches(self.rig):
            if label == "Left Arm":
                pb["IK_FK"] = 1.0
        self.rig.update_tag()
        fk = self.rig.pose.bones["upper_arm_fk.L"]
        fk.rotation_mode = 'XYZ'
        fk.rotation_euler = (0.0, 0.0, 0.8)
        bpy.context.view_layer.update()
        a = np.array(self.rig.matrix_world @ self.rig.pose.bones["LeftLowerArm"].head)
        b = self.rest["LeftLowerArm"][:3, 3]
        self.assertGreater(np.linalg.norm(a - b), 0.05)
        fk.rotation_euler = (0.0, 0.0, 0.0)

    def _limb_points(self, label):
        """The joints of the limb (each bone's head and tail) and the axes of its end bone (0.001 is 0.06 degree), which
        the snaps keep within 1 mm."""
        bones = controls.limb(self.rig, label)
        bpy.context.view_layer.update()
        world = self.rig.matrix_world
        points = [world @ self.rig.pose.bones[n].head for n in bones["org"]] +             [world @ self.rig.pose.bones[n].tail for n in bones["org"]]
        end = (world @ self.rig.pose.bones[bones["org"][2]].matrix).to_3x3().normalized()
        return np.array([p[:] for p in points] + [tuple(end.col[k]) for k in range(3)])


    def test_snaps_do_not_move_the_limb(self):
        from mathutils import Euler
        for label in ("Left Arm", "Right Leg"):
            bones = controls.limb(self.rig, label)
            switch = self.rig.pose.bones[bones["switch"]]
            switch["IK_FK"] = 1.0  # posed with FK
            for name, angles in zip(bones["fk"], ((0.0, 0.0, 0.6), (0.9, 0.0, 0.0), (0.0, 0.4, 0.3))):
                pb = self.rig.pose.bones[name]
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = Euler(angles)
            self.rig.update_tag()
            posed = self._limb_points(label)
            controls.snap(bpy.context, self.rig, label, 'IK')
            self.assertEqual(switch["IK_FK"], 0.0)
            np.testing.assert_allclose(self._limb_points(label), posed, atol=1e-3, err_msg=label + " to IK")
            for name in bones["fk"]:  # the FK controls go elsewhere: the IK controls hold the limb now
                self.rig.pose.bones[name].matrix_basis = Matrix()
            self.rig.update_tag()
            np.testing.assert_allclose(self._limb_points(label), posed, atol=1e-3, err_msg=label + " held by IK")
            controls.snap(bpy.context, self.rig, label, 'FK')
            self.assertEqual(switch["IK_FK"], 1.0)
            np.testing.assert_allclose(self._limb_points(label), posed, atol=1e-3, err_msg=label + " back to FK")

    def test_controls_section_draws(self):
        from bl_ui import dasktoon_rig as ui

        class Layout:  # records what the section draws
            def __init__(self, log):
                self.log = log

            def __getattr__(self, name):
                def call(*args, **kwargs):
                    self.log.append((name, args, kwargs))
                    return Layout(self.log) if name in {"row", "column", "grid_flow"} else Op()
                return call

        class Op:
            pass
        log = []
        ui.draw_controls(Layout(log), self.rig)
        snaps = [c for c in log if c[0] == "operator" and c[1] == ("dasktoon.rig_controls_snap",)]
        self.assertEqual(len(snaps), 8)  # To IK and To FK for each arm and leg
        self.assertIn(("operator", ("dasktoon.rig_controls_remove",), {"icon": 'X'}), log)
        self.assertGreaterEqual(len([c for c in log if c[0] == "prop" and c[1][1] == "is_visible"]), 10)

    def test_switches_for_four_limbs(self):
        self.assertEqual(sorted(label for _pb, label in controls.limb_switches(self.rig)),
                         ["Left Arm", "Left Leg", "Right Arm", "Right Leg"])


class RemoveTest(unittest.TestCase):
    def test_remove_leaves_the_rig_as_it_was(self):
        rig, objs = character()
        names = sorted(b.name for b in rig.data.bones)
        collections = sorted(c.name for c in rig.data.collections_all)
        objects = sorted(o.name for o in bpy.data.objects)
        rest = bone_matrices(rig, names)
        controls.add(bpy.context, rig)
        self.assertTrue(controls.remove(bpy.context, rig))
        self.assertFalse(controls.has_controls(rig))
        self.assertEqual(sorted(b.name for b in rig.data.bones), names)
        self.assertEqual(sorted(c.name for c in rig.data.collections_all), collections)
        self.assertEqual(sorted(o.name for o in bpy.data.objects), objects)
        self.assertFalse(any(c.name == controls.FOLLOW for pb in rig.pose.bones for c in pb.constraints))
        now = bone_matrices(rig, names)
        for name in names:
            np.testing.assert_allclose(now[name], rest[name], atol=1e-4, err_msg=name)
        self.assertFalse(controls.remove(bpy.context, rig))

    def test_build_rig_keeps_the_controls(self):
        rig, objs = character()
        controls.add(bpy.context, rig)
        # the chains are made again from the part list, whose skirt has 4 bones a chain to the fixture's 3
        fixed = lambda: sorted(b.name for b in rig.data.bones if build.MARK not in b)
        before = fixed()
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        self.assertTrue(controls.has_controls(rig))
        self.assertEqual(fixed(), before)
        self.assertEqual(rig.pose.bones["LeftHand"].constraints[controls.FOLLOW].subtarget, "DTH-LeftHand")

    def test_missing_joint_is_reported(self):
        rig, objs = character()
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        rig.data.edit_bones.remove(rig.data.edit_bones["LeftToes"])
        bpy.ops.object.mode_set(mode='OBJECT')
        with self.assertRaises(controls.ControlsError):
            controls.add(bpy.context, rig)
        self.assertFalse(controls.has_controls(rig))


if __name__ == "__main__":
    tu.run_tests()
