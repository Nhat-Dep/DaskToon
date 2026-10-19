# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Spring constraint (anime rig spec 9.4): the constraint type, its colliders and settings, and how it sways
a bone like dasktoon_rig/spring.py."""

import math
import os
import sys
import tempfile
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402


def chain_rig(count=3):
    """An armature with a body bone "Spine" (up) and a horizontal chain "Tail_1".."Tail_<count>" along +Y from its top."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    spine = data.edit_bones.new("Spine")
    spine.head, spine.tail = (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    parent = spine
    for k in range(1, count + 1):
        bone = data.edit_bones.new("Tail_%d" % k)
        bone.head = (0.0, 0.1 * (k - 1), 1.0)
        bone.tail = (0.0, 0.1 * k, 1.0)
        bone.parent = parent
        bone.use_connect = k > 1
        parent = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def add_springs(rig, count=3, colliders=()):
    for k in range(1, count + 1):
        con = rig.pose.bones["Tail_%d" % k].constraints.new('SPRING')
        for bone, radius in colliders:
            item = con.colliders.new()
            item.target = rig
            item.subtarget = bone
            item.radius = radius
    return [rig.pose.bones["Tail_%d" % k].constraints[0] for k in range(1, count + 1)]


class TypeTest(unittest.TestCase):
    def test_new_spring_constraint(self):
        rig = chain_rig()
        con = rig.pose.bones["Tail_1"].constraints.new('SPRING')
        self.assertEqual(con.type, 'SPRING')
        self.assertEqual(con.bl_rna.identifier, "SpringConstraint")
        np.testing.assert_allclose((con.stiffness, con.gravity, con.drag), (1.0, 0.2, 0.4), rtol=1e-6)
        self.assertAlmostEqual(con.radius, 0.03, places=6)
        self.assertEqual(len(con.colliders), 0)
        item = con.colliders.new()
        self.assertEqual(item.target, rig)
        item.subtarget = "Spine"
        item.radius = 0.25
        self.assertEqual((con.colliders[0].subtarget, round(con.colliders[0].radius, 6)), ("Spine", 0.25))
        self.assertEqual(con.colliders[0].path_from_id(), 'pose.bones["Tail_1"].constraints["Spring"].colliders[0]')
        con.colliders.clear()
        self.assertEqual(len(con.colliders), 0)

    def test_save_and_reload_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        rig.pose.bones["Tail_1"].constraints[0].stiffness = 2.5
        path = os.path.join(tempfile.mkdtemp(prefix="dt_spring_"), "spring.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        con = bpy.data.objects["Rig"].pose.bones["Tail_1"].constraints[0]
        self.assertEqual(con.type, 'SPRING')
        self.assertAlmostEqual(con.stiffness, 2.5, places=6)
        self.assertEqual([(c.target.name, c.subtarget) for c in con.colliders], [("Rig", "Spine")])
        self.assertAlmostEqual(con.colliders[0].radius, 0.2, places=6)

    def test_copy_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        copy = rig.copy()
        bpy.context.scene.collection.objects.link(copy)
        con = copy.pose.bones["Tail_1"].constraints[0]
        self.assertEqual([c.subtarget for c in con.colliders], ["Spine"])

    def test_panels_and_texts(self):
        from bl_ui import properties_constraint as pc
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint"))
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint_colliders"))
        item = next(i for i in bpy.types.Constraint.bl_rna.properties["type"].enum_items if i.identifier == 'SPRING')
        strings = {item.name, item.description, bpy.types.SpringConstraint.bl_rna.description}
        for struct in (bpy.types.SpringConstraint, bpy.types.SpringConstraintCollider):
            for prop in struct.bl_rna.properties:
                if prop.identifier in bpy.types.Constraint.bl_rna.properties or prop.identifier == "rna_type":
                    continue
                strings.update((prop.name, prop.description))
        strings.discard("")
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])


def tails(rig, count=3):
    world = rig.matrix_world
    return [np.array(world @ rig.pose.bones["Tail_%d" % k].tail) for k in range(1, count + 1)]


def python_tails(rig, frames, params, colliders, count=3):
    """Tails from dasktoon_rig/spring.py for the same chain, frame by frame, with the springs muted for the poses."""
    from dasktoon_rig import spring, sway
    cons = [rig.pose.bones["Tail_%d" % k].constraints[0] for k in range(1, count + 1)]
    for con in cons:
        con.mute = True
    names = ["Tail_%d" % k for k in range(1, count + 1)]
    out, state = {}, None
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        pose = sway.chain_pose(rig, names)
        caps = [(np.array(rig.matrix_world @ rig.pose.bones[b].head), np.array(rig.matrix_world @ rig.pose.bones[b].tail), r)
                for b, r in colliders]
        if state is None or frame == bpy.context.scene.frame_start:
            state = spring.reset(pose, params, caps)
        else:
            spring.step(state, pose, params, caps, 1.0 / bpy.context.scene.render.fps)
        out[frame] = [t.copy() for t in state.current]
    for con in cons:
        con.mute = False
    return out


def animate_spine(rig):
    spine = rig.pose.bones["Spine"]
    for frame, x in ((1, 0.0), (5, 0.4), (10, 0.4)):
        spine.location = (x, 0.0, 0.0)
        spine.keyframe_insert("location", frame=frame)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 20


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.rig = chain_rig()
        animate_spine(self.rig)
        self.cons = add_springs(self.rig, 3, [("Spine", 0.05)])

    def play(self, last):
        out = {}
        for frame in range(1, last + 1):
            bpy.context.scene.frame_set(frame)
            out[frame] = tails(self.rig)
        return out

    def test_matches_python(self):
        from dasktoon_rig import spring
        expected = python_tails(self.rig, range(1, 13), spring.Params(), [("Spine", 0.05)])
        self.cons[0].clear_cache()
        played = self.play(12)
        for frame in (1, 4, 8, 12):
            np.testing.assert_allclose(np.array(played[frame]), np.array(expected[frame]), atol=1e-4, err_msg=str(frame))
        self.assertGreater(np.linalg.norm(played[8][2] - played[1][2] - np.array((0.4, 0.0, 0.0))), 0.01)

    def test_start_frame_has_no_sway(self):
        self.play(8)
        bpy.context.scene.frame_set(1)
        np.testing.assert_allclose(np.array(tails(self.rig)),
                                   [(0.0, 0.1, 1.0), (0.0, 0.2, 1.0), (0.0, 0.3, 1.0)], atol=1e-5)

    def test_same_frame_twice_and_scrubbing(self):
        played = self.play(12)
        bpy.context.scene.frame_set(7)
        np.testing.assert_allclose(np.array(tails(self.rig)), np.array(played[7]), atol=1e-6)
        bpy.context.view_layer.update()
        np.testing.assert_allclose(np.array(tails(self.rig)), np.array(played[7]), atol=1e-6)
        again = self.play(12)
        np.testing.assert_allclose(np.array(again[12]), np.array(played[12]), atol=1e-6)

    def test_subframes_leave_the_cache_alone(self):
        played = self.play(4)
        self.cons[0].clear_cache()
        self.play(3)
        bpy.context.scene.frame_set(3, subframe=0.5)  # motion blur samples between frames
        between = tails(self.rig)
        bpy.context.scene.frame_set(4)
        np.testing.assert_allclose(np.array(tails(self.rig)), np.array(played[4]), atol=1e-6)
        mid = (played[3][2] + played[4][2]) / 2.0
        self.assertLess(np.linalg.norm(between[2] - mid), 0.25 * np.linalg.norm(played[4][2] - played[3][2]))

    def test_changed_input_starts_again(self):
        self.play(8)
        spine = self.rig.pose.bones["Spine"]
        spine.location = (0.4, 0.0, 0.3)
        spine.keyframe_insert("location", frame=8)
        bpy.context.scene.frame_set(8)
        head = np.array(self.rig.matrix_world @ self.rig.pose.bones["Tail_1"].head)
        np.testing.assert_allclose(tails(self.rig)[0], head + (0.0, 0.1, 0.0), atol=1e-5)  # at rest again

    def test_mute_and_settings(self):
        self.play(8)
        for con in self.cons:
            con.mute = True
        bpy.context.scene.frame_set(8)
        rest = tails(self.rig)
        for con in self.cons:
            con.mute = False
        bpy.context.scene.frame_set(8)
        swayed = tails(self.rig)
        self.assertGreater(np.linalg.norm(swayed[2] - rest[2]), 1e-3)
        self.cons[2].drag = 1.0   # clears the cache: frame 8 starts again
        bpy.context.scene.frame_set(8)
        np.testing.assert_allclose(tails(self.rig)[2], rest[2], atol=1e-5)

    def test_collider_pushes_out_and_follows_scale(self):
        for con in self.cons:
            con.stiffness, con.gravity = 0.0, 2.0
        self.play(15)
        tip = tails(self.rig)[2]
        head = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].head)
        tail = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].tail)
        t = np.clip((tip - head) @ (tail - head) / ((tail - head) @ (tail - head)), 0.0, 1.0)
        self.assertGreaterEqual(np.linalg.norm(tip - (head + t * (tail - head))), 0.05 + 0.03 - 1e-4)

    def test_radius_grows_with_the_rig_scale(self):
        self.rig.scale = (2.0, 2.0, 2.0)
        for con in self.cons:
            con.stiffness, con.gravity = 0.0, 2.0
        self.play(15)
        tip = tails(self.rig)[2]
        head = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].head)
        tail = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].tail)
        t = np.clip((tip - head) @ (tail - head) / ((tail - head) @ (tail - head)), 0.0, 1.0)
        self.assertGreaterEqual(np.linalg.norm(tip - (head + t * (tail - head))), 2.0 * (0.05 + 0.03) - 1e-4)

    def test_start_frame_is_out_of_the_colliders(self):
        """On the scene's first frame, and when the pose changes on a frame, the chain starts again out of the
        colliders, as a step leaves it: a skirt stood through the thighs in the Check's Sit pose (RG2, a real model)."""
        from dasktoon_rig import spring
        rig = self.rig
        bpy.ops.object.mode_set(mode='EDIT')
        block = rig.data.edit_bones.new("Block")  # across the chain, through Tail_2's tail
        block.head, block.tail = (-0.5, 0.2, 1.0), (0.5, 0.2, 1.0)
        bpy.ops.object.mode_set(mode='OBJECT')
        for con in self.cons:
            item = con.colliders.new()
            item.target, item.subtarget, item.radius = rig, "Block", 0.05
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        head = np.array(rig.matrix_world @ rig.pose.bones["Tail_1"].head)
        expected = python_tails(rig, [1], spring.Params(), [("Spine", 0.05), ("Block", 0.05)])[1]
        got = tails(rig)
        np.testing.assert_allclose(np.array(got), np.array(expected), atol=1e-4)
        for k, tail in enumerate(got):
            self.assertGreaterEqual(math.hypot(tail[1] - 0.2, tail[2] - 1.0), 0.05 + 0.03 - 1e-4, k)
        self.assertAlmostEqual(float(np.linalg.norm(got[0] - head)), 0.1, places=4)

    def test_python_handlers_are_gone(self):
        names = [h.__name__ for h in bpy.app.handlers.frame_change_post + bpy.app.handlers.frame_change_pre]
        self.assertNotIn("frame_post", names)
        self.assertNotIn("frame_pre", names)


if __name__ == "__main__":
    tu.run_tests()
