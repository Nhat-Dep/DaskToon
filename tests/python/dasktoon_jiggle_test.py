# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Jiggle modifier ("Rung mềm", docs/superpowers/specs/2026-11-10-dasktoon-jiggle-design.md, section 9): a ball
dropped on a pudding dents it, it springs back past where it was and settles; the cache gives the same frame again;
the rig's capsules push, but not the vertices their own bone moves; Add Jiggle and the presets."""

import os
import sys
import tempfile
import unittest

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402
from dasktoon_rig import jiggle  # noqa: E402

TOP = 0.5


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 250
    scene.render.fps = 24
    return scene


def pudding(cuts=7, name="Pudding"):
    """A closed 1 m box from z -0.5 to 0.5 with `cuts` cuts on every edge."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def ball(radius=0.3, name="Ball"):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Collision", 'COLLISION')
    return obj


def key_location(obj, keys):
    for frame, location in keys:
        obj.location = location
        obj.keyframe_insert("location", frame=frame)
    for fcurve in obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = 'LINEAR'


def positions(obj, frame=None):
    """World positions of the evaluated mesh at `frame` (the current one when None)."""
    if frame is not None:
        bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    co = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(ev.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def rest(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def volume(obj, co):
    total = 0.0
    for poly in obj.data.polygons:
        v = list(poly.vertices)
        for k in range(1, len(v) - 1):
            total += float(np.dot(co[v[0]], np.cross(co[v[k]], co[v[k + 1]]))) / 6.0
    return total


def top_centre(obj):
    co = rest(obj)
    return int(np.argmin(np.linalg.norm(co - np.array((0.0, 0.0, TOP)), axis=1)))


def dropped_ball_scene(volume_keep=0.8):
    """A pudding with the Pudding preset; a ball 15 cm into its top on frames 10-20, gone from frame 25."""
    empty_scene()
    obj = pudding()
    md = obj.modifiers.new("Jiggle", 'JIGGLE')
    jiggle.apply_preset(md, 'PUDDING')
    md.volume = volume_keep
    b = ball()
    key_location(b, [(1, (0, 0, 1.5)), (10, (0, 0, TOP + 0.3 - 0.15)), (20, (0, 0, TOP + 0.3 - 0.15)),
                     (25, (0, 0, 3.0))])
    return obj, md, b


class TypeTest(unittest.TestCase):
    def test_modifier_and_defaults(self):
        empty_scene()
        obj = pudding()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        self.assertEqual(md.type, 'JIGGLE')
        self.assertAlmostEqual(md.frequency, 3.0)
        self.assertEqual(md.substeps, 4)
        self.assertFalse(md.use_pin_bottom)
        self.assertEqual(len(md.colliders), 0)

    def test_save_and_load_keep_settings_and_colliders(self):
        empty_scene()
        obj = pudding()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        md.frequency, md.use_pin_bottom = 4.5, True
        md.collider_add("Hand", "Tip", 0.04)
        md.collider_add("Spine", "", 0.1)
        path = os.path.join(tempfile.mkdtemp(), "jiggle.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        md = bpy.data.objects["Pudding"].modifiers["Jiggle"]
        self.assertAlmostEqual(md.frequency, 4.5, places=5)
        self.assertTrue(md.use_pin_bottom)
        self.assertEqual([(c.bone, c.bone_end, round(c.radius, 5)) for c in md.colliders],
                         [("Hand", "Tip", 0.04), ("Spine", "", 0.1)])
        md.colliders_clear()
        self.assertEqual(len(md.colliders), 0)

    def test_copied_object_keeps_its_colliders(self):
        empty_scene()
        obj = pudding()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        md.collider_add("Hand", "", 0.04)
        copy = obj.copy()
        bpy.context.scene.collection.objects.link(copy)
        self.assertEqual([c.bone for c in copy.modifiers["Jiggle"].colliders], ["Hand"])
        md.colliders_clear()
        self.assertEqual([c.bone for c in copy.modifiers["Jiggle"].colliders], ["Hand"])

    def test_interface_is_translated(self):
        strings = {bpy.types.JiggleModifier.bl_rna.name, "Jiggle"}
        for struct in (bpy.types.JiggleModifier, bpy.types.JiggleModifierCollider):
            for prop in struct.bl_rna.properties:
                if prop.identifier in bpy.types.Modifier.bl_rna.properties or prop.identifier == "rna_type":
                    continue
                strings.update(s for s in (prop.name, prop.description) if s)
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])


class PuddingTest(unittest.TestCase):
    def test_nothing_touches_nothing_moves(self):
        empty_scene()
        obj = pudding()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'PUDDING')
        start = rest(obj)
        for frame in range(1, 31):
            np.testing.assert_allclose(positions(obj, frame), start, atol=1e-5, err_msg=str(frame))

    def test_ball_dents_bounces_and_settles(self):
        obj, md, _b = dropped_ball_scene()
        top = top_centre(obj)
        start = rest(obj)
        bottom = start[:, 2] < -0.5 + 1e-6
        heights = {}
        for frame in range(1, 130):
            co = positions(obj, frame)
            heights[frame] = co[top, 2]
            # The bottom stands still (Pin Bottom).
            np.testing.assert_allclose(co[bottom], start[bottom], atol=1e-6, err_msg=str(frame))
        # Dented by more than 30% of the 15 cm the ball goes in.
        self.assertLess(heights[15], TOP - 0.3 * 0.15)
        # Springs back past where it was after the ball goes...
        self.assertGreater(max(heights[f] for f in range(21, 60)), TOP + 0.002)
        # ...and settles within 4 seconds.
        self.assertLess(abs(heights[129] - TOP), 0.01)

    def test_dent_spreads(self):
        obj, md, _b = dropped_ball_scene(volume_keep=0.0)
        start = rest(obj)
        top = top_centre(obj)
        # Beside the ball (it is 30 cm wide, this is 37.5 cm out): it goes down too, less than the middle.
        side = int(np.argmin(np.linalg.norm(start - np.array((0.375, 0.0, TOP)), axis=1)))
        for frame in range(1, 16):
            co = positions(obj, frame)
        self.assertLess(co[side, 2], TOP - 0.002)
        self.assertGreater(co[side, 2], co[top, 2])
        md.spread = 0.0
        for frame in range(1, 16):
            co = positions(obj, frame)
        self.assertGreater(co[side, 2], TOP - 0.002)

    def test_volume_is_kept_while_pressed(self):
        obj, md, _b = dropped_ball_scene(volume_keep=1.0)
        for frame in range(1, 16):
            co = positions(obj, frame)
        v0 = volume(obj, rest(obj))
        self.assertLess(abs(volume(obj, co) - v0) / v0, 0.10)
        # Without keeping the volume it loses more.
        md.volume = 0.0
        for frame in range(1, 16):
            co_free = positions(obj, frame)
        self.assertGreater(abs(volume(obj, co_free) - v0), abs(volume(obj, co) - v0))

    def test_scrubbing_back_gives_the_same_frame(self):
        obj, _md, _b = dropped_ball_scene()
        played = {frame: positions(obj, frame) for frame in range(1, 41)}
        for frame in (15, 33, 7, 40):
            np.testing.assert_allclose(positions(obj, frame), played[frame], atol=1e-6, err_msg=str(frame))

    def test_jump_then_playing_matches_playing(self):
        obj, _md, _b = dropped_ball_scene()
        played = {frame: positions(obj, frame) for frame in range(1, 41)}
        positions(obj, 1)  # the start frame starts again
        positions(obj, 40)  # caught up over the jump: only close
        for frame in range(2, 41):
            co = positions(obj, frame)
        np.testing.assert_allclose(co, played[40], atol=1e-6)

    def test_settings_change_starts_again(self):
        obj, md, _b = dropped_ball_scene()
        for frame in range(1, 16):
            dented = positions(obj, frame)
        md.frequency = 5.0
        changed = positions(obj)
        self.assertFalse(np.allclose(changed, dented, atol=1e-6))


class MotionTest(unittest.TestCase):
    def test_zero_weight_follows_and_the_top_lags_then_wobbles(self):
        empty_scene()
        obj = pudding()
        group = obj.vertex_groups.new(name="Soft")
        start = rest(obj)
        free = [i for i in range(len(start)) if start[i, 2] > 0.0]
        group.add(free, 1.0, 'REPLACE')
        group.add([i for i in range(len(start)) if start[i, 2] <= 0.0], 0.0, 'REPLACE')
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'PUDDING')
        md.vertex_group = "Soft"
        md.use_pin_bottom = False
        key_location(obj, [(1, (0, 0, 0)), (6, (0.5, 0, 0))])
        top = top_centre(obj)
        fixed = [i for i in range(len(start)) if start[i, 2] <= 0.0]
        xs = {}
        for frame in range(1, 80):
            co = positions(obj, frame)
            offset = np.array(obj.matrix_world.translation)
            np.testing.assert_allclose(co[fixed], start[fixed] + offset, atol=1e-5, err_msg=str(frame))
            xs[frame] = co[top, 0] - offset[0]
        self.assertLess(min(xs[f] for f in range(2, 5)), -0.01)  # lags behind when it starts moving
        self.assertGreater(max(abs(xs[f]) for f in range(7, 40)), 0.005)  # wobbles on when it stops
        self.assertLess(abs(xs[79]), 0.01)

    def test_soft_edge_moves_with_the_middle(self):
        """The edge of a soft region shows a share of the same wobble as its middle, in step with it: a stiffer edge
        wobbling at its own pace tore a real character's breast into a cone."""
        empty_scene()
        obj = pudding()
        start = rest(obj)
        weights = jiggle.soft_weights(obj, [i for i in range(len(start)) if start[i, 2] > 0.2])
        group = obj.vertex_groups.new(name="Soft")
        for i, w in weights.items():
            group.add([i], w, 'REPLACE')
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'PUDDING')
        md.vertex_group, md.use_pin_bottom, md.spread, md.volume = "Soft", False, 0.0, 0.0
        key_location(obj, [(1, (0, 0, 0)), (4, (0, 0, 0.15)), (7, (0, 0, 0)), (60, (0, 0, 0))])
        core = [i for i, w in weights.items() if w > 0.999]
        edge = [i for i, w in weights.items() if 0.2 < w < 0.8]
        self.assertTrue(core and edge)
        checked = 0
        for frame in range(1, 41):
            d = positions(obj, frame) - start - np.array(obj.matrix_world.translation)
            middle = d[core].mean(axis=0)
            if frame < 8 or np.linalg.norm(middle) < 0.002:
                continue
            for i in edge:
                expected = weights[i] * middle
                self.assertLess(np.linalg.norm(d[i] - expected), 0.25 * np.linalg.norm(expected) + 1e-4,
                                (frame, i, weights[i]))
            checked += 1
        self.assertGreater(checked, 5)

    def test_sharp_edge_does_not_fold(self):
        """A group going from 1 to 0 between neighbours, shaken hard: the surface may stretch but never folds over (a
        breast's narrow edge folded into a crumpled ridge)."""
        empty_scene()
        obj = pudding(cuts=15)
        start = rest(obj)
        group = obj.vertex_groups.new(name="Soft")
        group.add([i for i in range(len(start)) if start[i, 2] > 0.2], 1.0, 'REPLACE')
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'PUDDING')
        md.vertex_group, md.use_pin_bottom = "Soft", False
        key_location(obj, [(1, (0, 0, 0)), (3, (0.3, 0, 0.3)), (5, (0, 0, 0)), (40, (0, 0, 0))])
        normals = np.empty(len(obj.data.polygons) * 3)
        obj.data.polygons.foreach_get("normal", normals)
        normals = normals.reshape(-1, 3)
        moved = 0.0
        for frame in range(1, 41):
            bpy.context.scene.frame_set(frame)
            ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            now = np.empty(len(ev.data.polygons) * 3)
            ev.data.polygons.foreach_get("normal", now)
            now = now.reshape(-1, 3)
            self.assertGreater(float((now * normals).sum(axis=1).min()), 0.0, frame)
            moved = max(moved, float(np.abs(positions(obj) - start - np.array(obj.matrix_world.translation)).max()))
        self.assertGreater(moved, 0.02)  # it did jiggle

    def test_follow_motion_one_does_not_lag(self):
        empty_scene()
        obj = pudding()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'PUDDING')
        md.follow = 1.0
        key_location(obj, [(1, (0, 0, 0)), (6, (0.5, 0, 0))])
        for frame in range(1, 12):
            co = positions(obj, frame)
            np.testing.assert_allclose(co, rest(obj), atol=1e-4, err_msg=str(frame))


def body_rig():
    """A rig with a Spine, a Chest above it and a LeftHand (finger LeftMiddleDistal), and a ball "Belly" moved by
    Spine."""
    empty_scene()
    data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    spine = data.edit_bones.new("Spine")
    spine.head, spine.tail = (0.0, 0.0, -0.4), (0.0, 0.0, 0.4)
    chest = data.edit_bones.new("Chest")
    chest.head, chest.tail = (0.0, 0.0, 0.6), (0.0, 0.0, 1.0)
    hand = data.edit_bones.new("LeftHand")
    hand.head, hand.tail = (1.0, 0.0, 0.0), (0.8, 0.0, 0.0)
    finger = data.edit_bones.new("LeftMiddleDistal")
    finger.head, finger.tail = (0.8, 0.0, 0.0), (0.7, 0.0, 0.0)
    finger.parent = hand
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = bpy.data.meshes.new("Belly")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.4)
    bm.to_mesh(mesh)
    bm.free()
    belly = bpy.data.objects.new("Belly", mesh)
    bpy.context.scene.collection.objects.link(belly)
    belly.vertex_groups.new(name="Spine").add(range(len(mesh.vertices)), 1.0, 'REPLACE')
    arm = belly.modifiers.new("Armature", 'ARMATURE')
    arm.object = rig
    belly.parent = rig
    return rig, belly


class RigColliderTest(unittest.TestCase):
    def test_hand_dents_but_its_own_bone_does_not_push(self):
        rig, belly = body_rig()
        md = belly.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'FLESH')
        md.rig = rig
        md.collider_add("Chest", "", 0.1)
        md.collider_add("LeftHand", "LeftMiddleDistal", 0.05)
        start = rest(belly)
        # The top of the belly follows Chest a little: Chest's capsule must not push it.
        top_half = [i for i in range(len(start)) if start[i, 2] > 0.2]
        belly.vertex_groups.new(name="Chest").add(top_half, 0.1, 'REPLACE')
        hand, chest = rig.pose.bones["LeftHand"], rig.pose.bones["Chest"]
        # The fingertip goes 8 cm into the belly by frame 10 and stays; Chest comes down into it.
        for frame, x in ((1, 0.0), (10, -0.38)):
            hand.location = (0.0, -x, 0.0)  # the bone's Y points along -X in the world
            hand.keyframe_insert("location", frame=frame)
            chest.location = (0.0, -0.45 if frame == 10 else 0.0, 0.0)  # down into the belly
            chest.keyframe_insert("location", frame=frame)
        side = int(np.argmax(start[:, 0]))
        for frame in range(1, 21):
            co = positions(belly, frame)
            if frame >= 10:
                hand_tip = np.array(rig.matrix_world @ rig.pose.bones["LeftMiddleDistal"].tail)
                self.assertLess(hand_tip[0], 0.4 - 0.05)  # the hand is in the belly's rest shape
                # Pushed in front of the fingertip, and it stays there (it does not slide off the round tip).
                self.assertLess(co[side, 0], hand_tip[0] - 0.04, frame)
        a, b = np.array(rig.matrix_world @ chest.head), np.array(rig.matrix_world @ chest.tail)
        self.assertLess(a[2], 0.4)  # Chest's capsule reaches into the belly...

        def gap(p):
            t = min(max(float((p - a) @ (b - a)) / float((b - a) @ (b - a)), 0.0), 1.0)
            return float(np.linalg.norm(p - (a + (b - a) * t)))
        # ...but leaves the vertices it moves where they are, inside it (pushed, none would be closer than 0.1).
        self.assertLess(min(gap(co[i]) for i in top_half), 0.09)


    def test_skin_resting_near_a_collider_stays_still(self):
        """Skin at the soft edge that rests closer to a body capsule than the collision distance is not pushed: the
        push, scaled up by the edge's small share of the wobble, threw spikes out of a real character's breast."""
        rig, belly = body_rig()
        start = rest(belly)
        weights = jiggle.soft_weights(belly, [i for i in range(len(start)) if start[i, 0] > 0.3])
        group = belly.vertex_groups.new(name="Soft")
        for i, w in weights.items():
            group.add([i], w, 'REPLACE')
        edge = min((i for i, w in weights.items() if 0.1 < w < 0.4), key=lambda i: weights[i])
        out = start[edge] / np.linalg.norm(start[edge])
        along = np.cross(out, (0.0, 0.0, 1.0))
        along /= np.linalg.norm(along)
        radius = 0.03
        centre = start[edge] + out * (radius + 0.003)  # 3 mm from the skin, inside the 5 mm distance
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        probe = rig.data.edit_bones.new("Probe")
        probe.head, probe.tail = centre - along * 0.05, centre + along * 0.05
        bpy.ops.object.mode_set(mode='OBJECT')
        md = belly.modifiers.new("Jiggle", 'JIGGLE')
        jiggle.apply_preset(md, 'FLESH')
        md.vertex_group, md.distance, md.rig = "Soft", 0.005, rig
        md.collider_add("Probe", "", radius)
        for frame in range(1, 11):
            np.testing.assert_allclose(positions(belly, frame), start, atol=1e-4, err_msg=str(frame))


    def test_capsule_just_under_the_skin_does_not_push_it(self):
        """A body capsule lying just under the soft skin (the ribcage under a breast) is the inside of that body: the
        skin lagging into it is not thrown back out (it threw spikes out of a real character's breast)."""
        def run(with_inner):
            rig, belly = body_rig()
            bpy.context.view_layer.objects.active = rig
            bpy.ops.object.mode_set(mode='EDIT')
            inner = rig.data.edit_bones.new("Inner")
            inner.head, inner.tail = (0.3, 0.0, -0.1), (0.3, 0.0, 0.1)
            bpy.ops.object.mode_set(mode='OBJECT')
            start = rest(belly)
            group = belly.vertex_groups.new(name="Soft")
            group.add([i for i in range(len(start)) if start[i, 0] > 0.25], 1.0, 'REPLACE')
            md = belly.modifiers.new("Jiggle", 'JIGGLE')
            jiggle.apply_preset(md, 'FLESH')
            md.vertex_group, md.rig, md.follow = "Soft", rig, 0.0
            if with_inner:
                md.collider_add("Inner", "", 0.09)  # its surface 1 cm under the skin at x = 0.4
            key_location(rig, [(1, (0, 0, 0)), (4, (0.15, 0, 0)), (7, (0, 0, 0)), (30, (0, 0, 0))])
            return [positions(belly, frame) for frame in range(1, 21)]
        plain, inner = run(False), run(True)
        for frame, (a, b) in enumerate(zip(plain, inner), start=1):
            self.assertLess(float(np.abs(a - b).max()), 0.002, frame)
        self.assertGreater(max(float(np.abs(p - plain[0]).max()) for p in plain), 0.01)  # the skin did lag in


class AddTest(unittest.TestCase):
    def test_add_on_an_object_is_a_pudding_at_the_top_of_the_stack(self):
        empty_scene()
        obj = pudding()
        obj.modifiers.new("Subdivision", 'SUBSURF')
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        self.assertEqual(bpy.ops.object.dasktoon_jiggle_add(), {'FINISHED'})
        md = obj.modifiers[0]
        self.assertEqual(md.type, 'JIGGLE')
        self.assertTrue(md.use_pin_bottom)
        self.assertAlmostEqual(md.volume, jiggle.PRESETS['PUDDING'][3])

    def test_add_on_a_rigged_body_needs_a_selection(self):
        rig, belly = body_rig()
        rig.data.dasktoon_rig.colliders.add().bone = "Spine"
        rig.data.dasktoon_rig.colliders[0].radius = 0.3
        bpy.context.view_layer.objects.active = belly
        belly.select_set(True)
        with self.assertRaises(RuntimeError):
            bpy.ops.object.dasktoon_jiggle_add()
        mesh = belly.data
        co = rest(belly)
        chosen = [i for i in range(len(co)) if co[i, 0] > 0.3]
        for v in mesh.vertices:
            v.select = v.index in chosen
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.object.dasktoon_jiggle_add(), {'FINISHED'})
        bpy.ops.object.mode_set(mode='OBJECT')
        md = belly.modifiers[1]
        self.assertEqual([m.type for m in belly.modifiers], ['ARMATURE', 'JIGGLE'])
        self.assertAlmostEqual(md.frequency, jiggle.PRESETS['FLESH'][0])
        group = belly.vertex_groups[md.vertex_group]
        weights = {}
        for v in mesh.vertices:
            for g in v.groups:
                if g.group == group.index:
                    weights[v.index] = g.weight
        self.assertTrue(all(abs(weights[i] - 1.0) < 1e-6 for i in chosen))
        edge = [w for i, w in weights.items() if i not in chosen]
        self.assertTrue(edge and all(0.0 < w < 1.0 for w in edge))
        self.assertNotIn(int(np.argmin(co[:, 0])), weights)  # the far side is not touched
        self.assertEqual(md.rig, rig)
        names = [(c.bone, c.bone_end) for c in md.colliders]
        self.assertEqual(names, [("Spine", ""), ("LeftHand", "LeftMiddleDistal")])
        self.assertGreater(md.colliders[1].radius, 0.0)

    def test_presets_and_make_collider(self):
        empty_scene()
        obj = pudding()
        other = ball()
        other.modifiers.clear()
        md = obj.modifiers.new("Jiggle", 'JIGGLE')
        bpy.context.view_layer.objects.active = obj
        for preset, values in jiggle.PRESETS.items():
            self.assertEqual(bpy.ops.object.dasktoon_jiggle_preset(modifier=md.name, preset=preset), {'FINISHED'})
            self.assertAlmostEqual(md.frequency, values[0])
            self.assertAlmostEqual(md.follow, values[4])
        for o in bpy.context.scene.objects:
            o.select_set(o == other)
        bpy.ops.object.dasktoon_make_collider()
        self.assertEqual([m.type for m in other.modifiers], ['COLLISION'])
        bpy.ops.object.dasktoon_make_collider()
        self.assertEqual([m.type for m in other.modifiers], ['COLLISION'])

    def test_menus_show_the_buttons(self):
        empty_scene()
        obj = pudding()
        bpy.context.view_layer.objects.active = obj
        log = [o[0] for o in tu.operators(tu.draw(bpy.types.VIEW3D_MT_object_context_menu))]
        self.assertIn("object.dasktoon_jiggle_add", log)
        self.assertIn("object.dasktoon_make_collider", log)


if __name__ == "__main__":
    tu.run_tests()
