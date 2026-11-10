# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Machine rig (machine rig spec 9) on a test machine: pieces, guessed joints, joints that move their pieces rigidly,
joint kinds and limits, the click tool, IK legs, aiming and making an imported model's pieces rigid."""

import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_machine_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_machine as machine  # noqa: E402
from dasktoon_machine import aim, joints, legs, pieces, tool  # noqa: E402


def new_machine():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs, parts = fx.machine()
    rig = machine.create(bpy.context, list(objs.values()), "Mech")
    return rig, objs, {name: pieces.piece_of_vertex(o, i) for name, (o, i) in parts.items()}


def evaluated_points(obj):
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def rest_points(obj):
    return pieces.world_points(obj)


def angle(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    c = abs(a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return math.degrees(math.acos(min(1.0, c)))


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()


class PiecesTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.p = new_machine()
        self.b = pieces.Binding(self.rig)

    def test_create_makes_a_root_holding_every_piece(self):
        self.assertTrue(machine.is_machine(self.rig))
        self.assertEqual([b.name for b in self.rig.data.bones], [machine.ROOT])
        root = self.rig.data.bones[machine.ROOT]
        self.assertAlmostEqual(root.head_local.z, 0.1, places=5)  # the bottom of the foot
        for obj in self.objs.values():
            self.assertEqual(obj.modifiers[0].type, 'ARMATURE')
            self.assertEqual(obj.modifiers[0].object, self.rig)
            self.assertIs(machine.rig_of_mesh(obj), self.rig)
        self.assertEqual(len(self.b.pieces()), len(fx.PARTS))
        self.assertEqual(len(self.b.unbound()), len(fx.PARTS))

    def test_pieces_are_loose_parts(self):
        self.assertEqual(len(set(self.p.values())), len(fx.PARTS))
        barrel = self.b.verts(self.p["Barrel"])
        self.assertEqual(len(barrel), 5 * fx.SEGMENTS)

    def test_piece_from_selection_splits_a_part(self):
        obj, number = self.p["Barrel"]
        polys = [p for p in obj.data.polygons if all(self.b.ids[obj][v] == number for v in p.vertices)]
        tip = [p for p in polys if p.center.x > 0.45]
        for p in obj.data.polygons:
            p.select = p in tip
        new = pieces.from_selection(obj)
        b = pieces.Binding(self.rig)
        self.assertIn((obj, new), b.pieces())
        self.assertIn((obj, number), b.pieces())
        self.assertTrue(np.all(b.world[obj][b.verts((obj, new))][:, 0] > 0.4))

    def test_a_ray_finds_the_piece_under_it(self):
        piece, loc = self.b.hit((0.0, 0.0, 2.0), (0.0, 0.0, -1.0))
        self.assertEqual(piece, self.p["Turret"])
        self.assertAlmostEqual(loc[2], 0.8, places=4)
        piece, _loc = self.b.hit((-0.2, 2.0, 0.63), (0.0, -1.0, 0.0))  # beside the hole, where the axle is
        self.assertEqual(piece, self.p["Wheel"])
        self.assertEqual(self.b.hit((5.0, 5.0, 5.0), (0.0, 0.0, 1.0)), (None, None))


class GuessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.p = new_machine()
        cls.b = pieces.Binding(cls.rig)

    def guess(self, child, parent):
        return joints.guess(self.b, [self.p[n] for n in child], [self.p[n] for n in parent])

    def test_turret_turns_about_the_vertical_at_its_foot(self):
        j = self.guess(["Turret", "EarL", "EarR"], ["Body"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 0, 1)), 1.0)
        np.testing.assert_allclose(j.pivot, (0.0, 0.0, 0.7), atol=1e-4)

    def test_gun_turns_about_its_trunnion(self):
        j = self.guess(["Trunnion", "Barrel"], ["Turret", "EarL", "EarR"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 1, 0)), 1.0)
        np.testing.assert_allclose(j.pivot, (0.1, 0.0, 0.84), atol=1e-3)

    def test_wheel_turns_on_its_axle(self):
        j = self.guess(["Wheel"], ["Axle"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 1, 0)), 1.0)
        np.testing.assert_allclose(j.pivot, (-0.2, 0.3, 0.55), atol=1e-3)

    def test_hatch_turns_about_the_edge_it_stands_on(self):
        j = self.guess(["Hatch"], ["Body"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (1, 0, 0)), 1.0)
        np.testing.assert_allclose(j.pivot, (-0.15, 0.105, 0.7), atol=1e-3)

    def test_a_head_wider_than_its_mast_turns_about_the_mast(self):
        # no vertex of the lamp touches the mast: the mast's top corners touch the lamp's bottom face
        j = self.guess(["Lamp"], ["Mast"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 0, 1)), 1.0)
        np.testing.assert_allclose(j.pivot, (-0.25, -0.15, 0.85), atol=1e-3)

    def test_a_round_piece_off_its_parent_turns_about_its_own_axis(self):
        j = self.guess(["Drill"], ["Body"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 0, 1)), 1.0)
        np.testing.assert_allclose(j.pivot[:2], (0.0, 0.0), atol=1e-3)
        self.assertTrue(0.47 < j.pivot[2] < 0.51, j.pivot)

    def test_a_fan_turns_about_its_round_hub(self):
        # the hub and its blades together are not round: the hub, nearest the body, is
        j = self.guess(["Hub", "Blade", "Blade2"], ["Body"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (1, 0, 0)), 1.0)
        np.testing.assert_allclose(j.pivot[1:], (-0.1, 0.6), atol=1e-3)
        self.assertTrue(-0.33 < j.pivot[0] < -0.3, j.pivot)

    def test_crossed_rings_spin_about_the_round_plinth_under_them(self):
        # neither touching nor round together (each ring alone is, about its own tilted normal): they turn about the
        # axis of the round piece they float over, which goes through their middle
        j = self.guess(["RingA", "RingB"], ["Plinth"])
        self.assertEqual(j.kind, 'HINGE')
        self.assertLess(angle(j.axis, (0, 0, 1)), 1.0)
        np.testing.assert_allclose(j.pivot[:2], (0.22, 0.12), atol=1e-3)
        # also when the plinth is one of several parent pieces, round in different ways
        j = self.guess(["RingA", "RingB"], ["Plinth", "Hub"])
        self.assertLess(angle(j.axis, (0, 0, 1)), 1.0)

    def test_a_piece_away_from_its_parent_gets_a_ball_joint_in_the_gap(self):
        j = self.guess(["Foot"], ["Body"])
        self.assertEqual(j.kind, 'BALL')
        self.assertTrue(0.15 < j.pivot[2] < 0.5, j.pivot)

    def test_without_a_parent_the_joint_is_in_the_middle(self):
        j = self.guess(["Body"], [])
        self.assertEqual(j.kind, 'BALL')
        np.testing.assert_allclose(j.pivot, (0.0, 0.0, 0.6), atol=1e-4)


def build_leg(rig, b, p):
    """Body, thigh, shin and foot joints of the test machine; returns their names."""
    ctx = bpy.context
    body = joints.add(ctx, b, [p["Body"]], None, joints.guess(b, [p["Body"]], []))
    hip = joints.add(ctx, b, [p["Thigh"]], body, joints.Joint(np.array(fx.HIP[0]), np.array(fx.HIP[1]), 'HINGE'))
    knee = joints.add(ctx, b, [p["Shin"]], hip, joints.Joint(np.array(fx.KNEE[0]), np.array(fx.KNEE[1]), 'HINGE'))
    ankle = joints.add(ctx, b, [p["Foot"]], knee,
                       joints.Joint(np.array(fx.ANKLE[0]), np.array(fx.ANKLE[1]), 'HINGE'))
    return body, hip, knee, ankle


class JointTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.p = new_machine()
        self.b = pieces.Binding(self.rig)
        self.mech = self.objs["Mech"]

    def test_a_joint_holds_its_pieces_fully(self):
        body, hip, knee, ankle = build_leg(self.rig, self.b, self.p)
        self.assertEqual(body, "Body")  # the material of its faces
        self.assertEqual(self.rig.data.bones[hip].parent.name, body)
        self.assertEqual(self.rig.data.bones[body].parent.name, machine.ROOT)
        b = pieces.Binding(self.rig)
        self.assertEqual(b.bone_of(self.p["Shin"]), knee)
        group = self.mech.vertex_groups[knee]
        for v in b.verts(self.p["Shin"]):
            weights = {self.mech.vertex_groups[g.group].name: g.weight for g in self.mech.data.vertices[v].groups}
            self.assertEqual(weights, {knee: 1.0})
        self.assertEqual(group.name, knee)
        self.assertEqual(len(b.unbound()), len(fx.PARTS) - 4)

    def test_hinge_axis_is_the_bone_x_axis_and_y_points_at_the_child(self):
        _body, hip, knee, ankle = build_leg(self.rig, self.b, self.p)
        bones = self.rig.data.bones
        for name, (pivot, axis) in ((hip, fx.HIP), (knee, fx.KNEE), (ankle, fx.ANKLE)):
            np.testing.assert_allclose(bones[name].head_local, pivot, atol=1e-5)
            self.assertLess(angle(bones[name].matrix_local.col[0][:3], axis), 0.01, name)
        np.testing.assert_allclose(bones[hip].tail_local, fx.KNEE[0], atol=1e-5)
        np.testing.assert_allclose(bones[knee].tail_local, fx.ANKLE[0], atol=1e-5)

    def test_rest_pose_does_not_move_anything(self):
        build_leg(self.rig, self.b, self.p)
        for obj in self.objs.values():
            np.testing.assert_allclose(evaluated_points(obj), rest_points(obj), atol=1e-6)

    def test_turning_a_hinge_moves_its_pieces_rigidly_and_nothing_else(self):
        _body, hip, knee, _ankle = build_leg(self.rig, self.b, self.p)
        self.rig.pose.bones[knee].rotation_euler = (0.6, 0.0, 0.0)
        moved = evaluated_points(self.mech)
        rest = rest_points(self.mech)
        b = pieces.Binding(self.rig)
        for name in ("Shin", "Foot"):
            v = b.verts(self.p[name])
            d_rest = np.linalg.norm(rest[v][:, None] - rest[v][None], axis=2)
            d_moved = np.linalg.norm(moved[v][:, None] - moved[v][None], axis=2)
            np.testing.assert_allclose(d_moved, d_rest, atol=1e-5)
            self.assertGreater(np.abs(moved[v] - rest[v]).max(), 0.05, name)
        for name in ("Thigh", "Body", "Turret"):
            v = b.verts(self.p[name])
            np.testing.assert_allclose(moved[v], rest[v], atol=1e-6)
        # the knee turns about the world Y axis through its pivot: the shin stays in the XZ plane
        v = b.verts(self.p["Shin"])
        np.testing.assert_allclose(moved[v][:, 1], rest[v][:, 1], atol=1e-5)

    def test_kinds_set_locks_and_limits_clamp(self):
        _body, hip, knee, _ankle = build_leg(self.rig, self.b, self.p)
        pb = self.rig.pose.bones[knee]
        data = self.rig.data.bones[knee].dasktoon_joint
        self.assertEqual(tuple(pb.lock_rotation), (False, True, True))
        self.assertTrue(pb.lock_ik_y and pb.lock_ik_z)
        data.use_limit = True
        data.angle_min, data.angle_max = math.radians(-10), math.radians(40)
        pb.rotation_euler = (math.radians(80), 0.0, 0.0)
        bpy.context.view_layer.update()
        visual = (self.rig.data.bones[knee].matrix_local.inverted() @ pb.matrix).to_euler()
        self.assertAlmostEqual(math.degrees(visual.x), 40.0, places=2)
        self.assertAlmostEqual(math.degrees(pb.ik_max_x), 40.0, places=3)
        data.kind = 'SLIDE'
        self.assertEqual(tuple(pb.lock_location), (False, True, True))
        self.assertEqual(tuple(pb.lock_rotation), (True, True, True))
        data.distance_min, data.distance_max = 0.0, 0.05
        pb.location = (0.2, 0.0, 0.0)
        bpy.context.view_layer.update()
        self.assertAlmostEqual((self.rig.data.bones[knee].matrix_local.inverted() @ pb.matrix).translation.x, 0.05,
                               places=5)
        data.kind = 'FIXED'
        self.assertTrue(all(pb.lock_location) and all(pb.lock_rotation))
        data.kind = 'BALL'
        self.assertEqual(pb.rotation_mode, 'QUATERNION')
        self.assertFalse([c for c in pb.constraints if c.name == joints.LIMIT])

    def test_the_kind_survives_edit_mode(self):
        _body, hip, _knee, _ankle = build_leg(self.rig, self.b, self.p)
        self.rig.data.bones[hip].dasktoon_joint.use_limit = True
        with machine.EditSession(bpy.context, self.rig):
            pass
        self.assertEqual(self.rig.data.bones[hip].dasktoon_joint.kind, 'HINGE')
        self.assertTrue(self.rig.data.bones[hip].dasktoon_joint.use_limit)

    def test_remove_gives_the_pieces_back_and_keeps_the_children(self):
        body, hip, knee, ankle = build_leg(self.rig, self.b, self.p)
        parent = joints.remove(bpy.context, self.b, knee)
        self.assertEqual(parent, hip)
        self.assertNotIn(knee, self.rig.data.bones)
        self.assertEqual(self.rig.data.bones[ankle].parent.name, hip)
        b = pieces.Binding(self.rig)
        self.assertIn(self.p["Shin"], b.unbound())
        self.assertNotIn(knee, self.mech.vertex_groups)
        # the hip, now with the ankle as its one child, points at it
        np.testing.assert_allclose(self.rig.data.bones[hip].tail_local, fx.ANKLE[0], atol=1e-5)
        with self.assertRaises(machine.MachineError):
            joints.remove(bpy.context, b, machine.ROOT)

    def test_set_parent_and_move(self):
        body, hip, knee, ankle = build_leg(self.rig, self.b, self.p)
        joints.set_parent(bpy.context, self.b, ankle, body)
        self.assertEqual(self.rig.data.bones[ankle].parent.name, body)
        with self.assertRaises(machine.MachineError):
            joints.set_parent(bpy.context, self.b, body, ankle)
        joints.move(bpy.context, self.b, knee, joints.Joint(np.array((0.5, 0.0, 0.5)), np.array((1.0, 0, 0)), 'HINGE'))
        bone = self.rig.data.bones[knee]
        np.testing.assert_allclose(bone.head_local, (0.5, 0.0, 0.5), atol=1e-5)
        self.assertLess(angle(bone.matrix_local.col[0][:3], (1, 0, 0)), 0.01)
        j = joints.joint_of(self.rig, knee)
        self.assertEqual(j.kind, 'HINGE')
        np.testing.assert_allclose(j.pivot, (0.5, 0.0, 0.5), atol=1e-5)

    def test_controls_have_shapes_sized_to_their_pieces(self):
        _body, hip, knee, _ankle = build_leg(self.rig, self.b, self.p)
        pb = self.rig.pose.bones[knee]
        self.assertEqual(pb.custom_shape.name, "DT Machine Hinge")
        self.assertGreater(pb.custom_shape_scale_xyz[0], 0.03)
        self.assertEqual(self.rig.pose.bones[machine.ROOT].custom_shape.name, "DT Machine Root")
        self.assertIn(knee, [b.name for b in self.rig.data.collections["Joints"].bones])


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.p = new_machine()
        self.t = tool.ToolState(bpy.context, self.rig)

    def test_a_leg_by_clicks(self):
        t, p = self.t, self.p
        t.click(p["Body"])
        self.assertEqual(t.state, tool.PARENT)
        t.click(None)
        self.assertEqual(t.state, tool.ADJUST)
        body = t.confirm()
        self.assertEqual(self.rig.data.bones[body].parent.name, machine.ROOT)
        for name, (pivot, axis) in (("Thigh", fx.HIP), ("Shin", fx.KNEE), ("Foot", fx.ANKLE)):
            t.click(p[name])
            self.assertEqual(t.state, tool.ADJUST)  # the last joint is the parent
            t.move_pivot(pivot)
            t.set_axis(axis)
            while t.joint.kind != 'HINGE':
                t.cycle_kind()
            t.confirm()
        bones = self.rig.data.bones
        self.assertEqual([bones["Foot"].parent.name, bones["Shin"].parent.name, bones["Thigh"].parent.name],
                         ["Shin", "Thigh", "Body"])
        np.testing.assert_allclose(bones["Shin"].head_local, fx.KNEE[0], atol=1e-5)
        self.assertEqual(t.undo_last(), "Foot")
        self.assertNotIn("Foot", bones)
        self.assertEqual(t.default_parent, "Shin")
        # a click on a piece with a joint opens it
        t.click(p["Shin"])
        self.assertEqual(t.editing, "Shin")
        t.cycle_kind()
        t.confirm()
        self.assertEqual(bones["Shin"].dasktoon_joint.kind, 'BALL')

    def test_shift_click_gathers_pieces_and_parent_gets_its_own_joint(self):
        t, p = self.t, self.p
        t.click(p["Turret"])
        t.click(p["EarL"], shift=True)
        t.click(p["EarR"], shift=True)
        t.click(p["Body"])  # no joint yet: it gets a free one under the root
        self.assertIn("Body", self.rig.data.bones)
        self.assertEqual(t.joint.kind, 'HINGE')
        self.assertLess(angle(t.joint.axis, (0, 0, 1)), 1.0)
        turret = t.confirm()
        b = pieces.Binding(self.rig)
        self.assertEqual(sorted(b.pieces_of(turret), key=lambda x: x[1]),
                         sorted([p["Turret"], p["EarL"], p["EarR"]], key=lambda x: x[1]))
        self.assertEqual(self.rig.data.bones[turret].parent.name, "Body")
        t.default_parent = None
        t.click(p["Wheel"])
        t.click(p["Axle"])
        self.assertLess(angle(t.joint.axis, (0, 1, 0)), 1.0)
        wheel = t.confirm()
        self.assertEqual(self.rig.data.bones[wheel].parent.name, "Axle")
        self.assertEqual(wheel, "Wheel")  # the whole mesh

    def test_a_joint_cannot_hang_from_its_own_child(self):
        t, p = self.t, self.p
        body, _hip, _knee, _ankle = build_leg(self.rig, t.binding, p)
        t.click(p["Thigh"])
        t.click(p["Shin"])
        self.assertTrue(t.message)
        self.assertEqual(t.parent, body)


class LegTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.p = new_machine()
        self.b = pieces.Binding(self.rig)
        self.body, self.hip, self.knee, self.ankle = build_leg(self.rig, self.b, self.p)
        self.target = legs.add(bpy.context, self.rig, self.ankle)

    def head(self, name):
        bpy.context.view_layer.update()
        return np.array(self.rig.matrix_world @ self.rig.pose.bones[name].head)

    def move_target(self, goal):
        bone = self.rig.data.bones[self.target]
        self.rig.pose.bones[self.target].location = \
            bone.matrix_local.to_3x3().inverted() @ Vector(np.asarray(goal) - np.array(bone.head_local))

    def test_the_leg_follows_its_target(self):
        self.assertEqual(legs.chain(self.rig, self.ankle), [self.knee, self.hip])
        self.assertEqual(legs.legs(self.rig), [(self.ankle, self.target)])
        np.testing.assert_allclose(self.head(self.ankle), fx.ANKLE[0], atol=1e-5)
        rest = rest_points(self.objs["Mech"])
        np.testing.assert_allclose(evaluated_points(self.objs["Mech"]), rest, atol=1e-5)
        goal = np.array((0.4, 0.0, 0.3))
        self.move_target(goal)
        np.testing.assert_allclose(self.head(self.ankle), goal, atol=1e-3)
        moved = evaluated_points(self.objs["Mech"])
        b = pieces.Binding(self.rig)
        for name in ("Thigh", "Shin", "Foot"):  # the leg stays in its plane: the hinges turn about Y only
            v = b.verts(self.p[name])
            np.testing.assert_allclose(moved[v][:, 1], rest[v][:, 1], atol=1e-4, err_msg=name)
        foot = self.rig.pose.bones[self.ankle].matrix.to_quaternion()
        target = self.rig.pose.bones[self.target].matrix.to_quaternion()
        self.assertLess(foot.rotation_difference(target).angle, 1e-3)
        self.rig.pose.bones[self.target][legs.SWITCH] = 1.0
        self.rig.update_tag()
        np.testing.assert_allclose(self.head(self.ankle), fx.ANKLE[0], atol=1e-5)

    def test_snaps_keep_the_pose(self):
        tgt = self.rig.pose.bones[self.target]
        self.move_target((0.4, 0.0, 0.3))
        before = self.head(self.ankle)
        legs.snap(bpy.context, self.rig, self.target, 'FK')
        self.assertEqual(tgt[legs.SWITCH], 1.0)
        np.testing.assert_allclose(self.head(self.ankle), before, atol=1e-4)
        self.rig.pose.bones[self.knee].rotation_euler.x += 0.3
        before = self.head(self.ankle)
        legs.snap(bpy.context, self.rig, self.target, 'IK')
        self.assertEqual(tgt[legs.SWITCH], 0.0)
        np.testing.assert_allclose(self.head(self.ankle), before, atol=1e-3)

    def test_removing_the_leg_or_its_joints(self):
        legs.remove(bpy.context, self.rig, self.target)
        self.assertNotIn(self.target, self.rig.data.bones)
        self.assertFalse([c for pb in self.rig.pose.bones for c in pb.constraints if c.name.startswith("DT IK")])
        target = legs.add(bpy.context, self.rig, self.ankle)
        joints.remove(bpy.context, pieces.Binding(self.rig), self.knee)
        self.assertNotIn(target, self.rig.data.bones)
        with self.assertRaises(machine.MachineError):
            legs.add(bpy.context, self.rig, self.body)


class AimTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.p = new_machine()
        t = tool.ToolState(bpy.context, self.rig)
        p = self.p
        for child, parent in ((["Turret", "EarL", "EarR"], "Body"), (["Trunnion", "Barrel"], "Turret")):
            t.default_parent = None
            t.click(p[child[0]])
            for name in child[1:]:
                t.click(p[name], shift=True)
            t.click(p[parent])
            self.assertEqual(t.joint.kind, 'HINGE')
            t.confirm()
        b = pieces.Binding(self.rig)
        self.gun, self.turret = b.bone_of(p["Trunnion"]), b.bone_of(p["Turret"])
        self.target = aim.add(bpy.context, self.rig, self.gun)

    def gun_direction(self):
        bpy.context.view_layer.update()
        m = self.rig.matrix_world @ self.rig.pose.bones[self.gun].matrix
        return np.array(m.translation), np.array(m.to_3x3().col[1].normalized())

    def aim_at(self, goal):
        bone = self.rig.data.bones[self.target]
        self.rig.pose.bones[self.target].location = \
            bone.matrix_local.to_3x3().inverted() @ Vector(np.asarray(goal) - np.array(bone.head_local))

    def test_the_chain_points_at_the_muzzle_at_rest(self):
        self.assertEqual(aim.chain(self.rig, self.gun), [self.gun, self.turret])
        bones = self.rig.data.bones
        self.assertLess(angle(bones[self.gun].matrix_local.col[1][:3], (1, 0, 0)), 0.5)
        self.assertLess(angle(bones[self.turret].matrix_local.col[1][:3], (1, 0, 0)), 0.5)
        np.testing.assert_allclose(bones[self.target].head_local, (0.1 + 4 * 0.4, 0.0, 0.84), atol=1e-3)
        for obj in self.objs.values():
            np.testing.assert_allclose(evaluated_points(obj), rest_points(obj), atol=1e-5)

    def test_the_gun_points_at_the_target(self):
        for goal in ((1.0, 1.0, 1.5), (-0.5, 0.8, 0.9), (0.3, -1.2, 0.4)):
            self.aim_at(goal)
            head, y = self.gun_direction()
            self.assertLess(angle(y, np.array(goal) - head), 2.0, goal)
            turret = self.rig.matrix_world @ self.rig.pose.bones[self.turret].matrix
            self.assertLess(angle(turret.to_3x3().col[0][:3], (0, 0, 1)), 0.1)  # the turret only turns about Z

    def test_limits_hold_while_aiming(self):
        data = self.rig.data.bones[self.gun].dasktoon_joint
        data.use_limit = True
        data.angle_min, data.angle_max = math.radians(-30), math.radians(10)
        self.aim_at((0.3, 0.0, 5.0))
        _head, y = self.gun_direction()
        self.assertAlmostEqual(math.degrees(math.asin(y[2])), 30.0, delta=0.5)

    def test_aim_off_and_remove(self):
        self.aim_at((1.0, 1.0, 1.5))
        self.rig.pose.bones[self.target][aim.SWITCH] = 0.0
        self.rig.update_tag()
        _head, y = self.gun_direction()
        self.assertLess(angle(y, (1, 0, 0)), 0.5)
        aim.remove(bpy.context, self.rig, self.target)
        self.assertNotIn(self.target, self.rig.data.bones)
        self.assertFalse(self.rig.data.bones[self.gun].dasktoon_joint.aim)
        self.assertFalse([c for pb in self.rig.pose.bones for c in pb.constraints if c.name == aim.TRACK])


class AdoptTest(unittest.TestCase):
    """An imported machine: its own skeleton, smooth weights blending the pieces between bones."""

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs, parts = fx.machine()
        self.p = {name: pieces.piece_of_vertex(o, i) for name, (o, i) in parts.items()}
        arm = bpy.data.armatures.new("Imported")
        self.rig = bpy.data.objects.new("Imported", arm)
        bpy.context.scene.collection.objects.link(self.rig)
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode='EDIT')
        for name, head, tail, parent in (("center", (0, 0, 0), (0, 0.2, 0), None),
                                         ("hull", (0, 0, 0.6), (0, 0, 0.7), "center"),
                                         ("turret", (0, 0, 0.7), (0, 0, 0.8), "hull")):
            eb = arm.edit_bones.new(name)
            eb.head, eb.tail = head, tail
            if parent:
                eb.parent = arm.edit_bones[parent]
        bpy.ops.object.mode_set(mode='OBJECT')
        b = pieces.Binding(self.rig, list(self.objs.values()))
        for obj in self.objs.values():
            for name in ("hull", "turret"):
                obj.vertex_groups.new(name=name)
            mod = obj.modifiers.new("Armature", 'ARMATURE')
            mod.object = self.rig
        mech = self.objs["Mech"]
        for piece, weights in ((self.p["Body"], {"hull": 0.8, "turret": 0.2}),
                               (self.p["Turret"], {"hull": 0.5, "turret": 0.5}),
                               (self.p["Barrel"], {"turret": 1.0}),
                               (self.p["Wheel"], {"hull": 0.3, "turret": 0.7})):
            obj = piece[0]
            for name, w in weights.items():
                obj.vertex_groups[name].add(b.verts(piece).tolist(), w, 'REPLACE')
        self.mech = mech

    def weights(self, piece):
        obj = piece[0]
        b = pieces.Binding(self.rig, list(self.objs.values()))
        out = set()
        for v in b.verts(piece):
            out.add(tuple(sorted((obj.vertex_groups[g.group].name, round(g.weight, 6))
                                 for g in obj.data.vertices[v].groups if g.weight > 0)))
        return out

    def test_each_piece_goes_to_its_strongest_bone(self):
        count, split = machine.adopt(bpy.context, self.rig)
        self.assertTrue(machine.is_machine(self.rig))
        self.assertEqual(machine.root_name(self.rig), "center")
        self.assertEqual(count, len(fx.PARTS))
        self.assertEqual(self.weights(self.p["Body"]), {(("hull", 1.0),)})
        self.assertEqual(self.weights(self.p["Barrel"]), {(("turret", 1.0),)})
        self.assertEqual(self.weights(self.p["Wheel"]), {(("turret", 1.0),)})
        self.assertEqual(split, [self.p["Turret"]])
        self.assertEqual(len(self.weights(self.p["Turret"])), 1)
        self.assertEqual(self.rig.data.bones["hull"].dasktoon_joint.kind, 'BALL')
        self.assertEqual(self.rig.pose.bones["hull"].custom_shape.name, "DT Machine Ball")


if __name__ == "__main__":
    tu.run_tests()
