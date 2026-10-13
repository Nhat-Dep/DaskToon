# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Eyes and mouth of the anime rig, R3 (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md, section 10):
the new part roles, the eyes looking at LookTarget within limits, the jaw, flat eyes and the 2D mouth that Build Rig
makes."""

import math
import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_rig import build, eyes, look, parts, skeleton  # noqa: E402


def built(roles=(("Body", 'BODY'),)):
    """The test character with `roles` as parts, built."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    for name, role in roles:
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    return rig, objs


def tail(rig, name):
    bpy.context.view_layer.update()
    return rig.matrix_world @ rig.pose.bones[name].tail


def look_angle(rig, name):
    """Angle in degrees between the eye's pose direction and its rest direction."""
    bpy.context.view_layer.update()
    pose = rig.pose.bones[name]
    rest = (pose.bone.tail_local - pose.bone.head_local).normalized()
    now = (pose.tail - pose.head).normalized()
    return math.degrees(rest.angle(now))


class LookTest(unittest.TestCase):
    def test_new_roles(self):
        roles = [item[0] for item in ui.ROLE_ITEMS]
        for role in ('JAW', 'FLAT_EYE', 'MOUTH_2D'):
            self.assertIn(role, roles)
            self.assertIn(role, parts.ROLES)
        self.assertEqual(parts.guess_role("Iris_L"), 'FLAT_EYE')
        self.assertEqual(parts.guess_role("Pupil"), 'FLAT_EYE')
        # A later role wins a vertex: a Jaw part over the Body, the Body over a flat eye or 2D mouth on it.
        self.assertLess(parts.ROLES.index('FLAT_EYE'), parts.ROLES.index('BODY'))
        self.assertLess(parts.ROLES.index('MOUTH_2D'), parts.ROLES.index('BODY'))
        self.assertGreater(parts.ROLES.index('JAW'), parts.ROLES.index('BODY'))

    def test_look_target(self):
        rig, _objs = built()
        bones = rig.data.bones
        target = bones[look.TARGET]
        self.assertFalse(target.use_deform)
        self.assertEqual(target.parent.name, "Head")
        eyes = (bones["LeftEye"].head_local + bones["RightEye"].head_local) / 2.0
        self.assertLess(target.head_local.y, eyes.y - 0.3)  # in front of the face (the character faces -Y)
        for eye in ("LeftEye", "RightEye"):
            constraints = rig.pose.bones[eye].constraints
            track = constraints[look.TRACK]
            self.assertEqual((track.type, track.subtarget, track.track_axis), ('DAMPED_TRACK', look.TARGET, 'TRACK_Y'))
            self.assertIs(track.target, rig)
            self.assertEqual(constraints[look.LIMIT].type, 'LIMIT_ROTATION')

    def test_eyes_follow_within_limits(self):
        rig, _objs = built()
        target = rig.pose.bones[look.TARGET]
        rest = tail(rig, "LeftEye").copy()
        # Move LookTarget to the character's left (+X in the world) a little.
        world = rig.matrix_world @ target.matrix
        world.translation += Vector((0.05, 0.0, 0.0))
        target.matrix = rig.matrix_world.inverted() @ world
        self.assertGreater(tail(rig, "LeftEye").x, rest.x + 1e-4)
        world.translation += Vector((5.0, 0.0, 0.0))  # far to the side: the eye stops at the limit
        target.matrix = rig.matrix_world.inverted() @ world
        limit = math.degrees(rig.data.dasktoon_rig.look_yaw_limit)
        self.assertLessEqual(look_angle(rig, "LeftEye"), limit + 0.5)
        self.assertGreater(look_angle(rig, "LeftEye"), limit - 5.0)

    def test_build_twice(self):
        rig, _objs = built()
        moved = Vector((0.0, -0.2, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            bone = edit[look.TARGET]
            bone.head += moved
            bone.tail += moved
        where = rig.data.bones[look.TARGET].head_local.copy()
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        self.assertEqual([b.name for b in rig.data.bones].count(look.TARGET), 1)
        self.assertLess((rig.data.bones[look.TARGET].head_local - where).length, 1e-5)  # the user's place stays
        for eye in ("LeftEye", "RightEye"):
            names = [c.name for c in rig.pose.bones[eye].constraints]
            self.assertEqual(sorted(names), sorted([look.TRACK, look.LIMIT]))


def chin(body):
    """A vertex group "Chin" on the front of the top two rings of the Body tube, by the Jaw bone's tip."""
    top = max(v.co.z for v in body.data.vertices)
    chosen = [v.index for v in body.data.vertices if v.co.z > top - 0.06 and v.co.y < -0.02]
    group = body.vertex_groups.new(name="Chin")
    group.add(chosen, 1.0, 'REPLACE')
    return chosen


def jaw_weight(obj, index):
    group = obj.vertex_groups.get("Jaw")
    if group is None:
        return 0.0
    return next((g.weight for g in obj.data.vertices[index].groups if g.group == group.index), 0.0)


class JawTest(unittest.TestCase):
    def test_rings(self):
        import numpy as np
        # A strip of 5 vertices in a row: 0-1-2-3-4.
        edges = np.array([(0, 1), (1, 2), (2, 3), (3, 4)])
        first, second = parts.rings(edges, np.array([0]), 2)
        self.assertEqual((first.tolist(), second.tolist()), ([1], [2]))

    def test_jaw(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        body = objs["Body"]
        chosen = chin(body)
        ui.add_part(rig, body, 'BODY')
        ui.add_part(rig, body, 'JAW', name="Chin", scope='VERTEX_GROUP', vertex_group="Chin")
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        for index in chosen:
            self.assertAlmostEqual(jaw_weight(body, index), 1.0, places=3)
        import numpy as np
        _world, edges = parts.mesh_arrays(body)
        first, second = parts.rings(edges, np.array(chosen), 2)
        # 2/3 and 1/3 of the Jaw bone in the rings; tidying for Unity (at most 4 bones a vertex, summing to 1) raises
        # its share a little where the face had more bones.
        ring1 = [jaw_weight(body, index) for index in first]
        ring2 = [jaw_weight(body, index) for index in second]
        self.assertTrue(all(0.6 < w < 0.8 for w in ring1), ring1)
        self.assertTrue(all(0.28 < w < 0.45 for w in ring2), ring2)
        for vertex in body.data.vertices:
            self.assertAlmostEqual(sum(g.weight for g in vertex.groups if body.vertex_groups[g.group].name in
                                       rig.data.bones), 1.0, places=2)
        low = min(body.data.vertices, key=lambda v: v.co.z).index
        self.assertEqual(jaw_weight(body, low), 0.0)
        # Opening the jaw moves the chin down and leaves the legs where they are.
        def where(index):
            bpy.context.view_layer.update()
            mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            return body.matrix_world @ mesh.vertices[index].co
        before_chin, before_low = where(chosen[0]), where(low)
        pose = rig.pose.bones["Jaw"]
        pose.rotation_mode = 'XYZ'
        pose.rotation_euler = (math.radians(20.0), 0.0, 0.0)
        moved = where(chosen[0]) - before_chin
        self.assertGreater(moved.length, 0.005)
        self.assertLess((where(low) - before_low).length, 1e-6)


def iris(rig):
    """A small plane with UVs just in front of the left eye, facing forward (-Y)."""
    head = rig.matrix_world @ rig.data.bones["LeftEye"].head_local
    bpy.ops.mesh.primitive_plane_add(size=0.02, location=head + Vector((0.0, -0.02, 0.0)),
                                     rotation=(math.radians(90.0), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = "Iris"
    return obj


def mean_uv(obj):
    bpy.context.view_layer.update()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    uvs = [loop.uv for loop in mesh.uv_layers.active.data]
    return Vector((sum(u.x for u in uvs) / len(uvs), sum(u.y for u in uvs) / len(uvs)))


def aim(rig, yaw, pitch):
    """LookTarget straight in front of the left eye, turned `yaw` degrees to the character's left (+X) and `pitch`
    degrees up."""
    eye = rig.matrix_world @ rig.data.bones["LeftEye"].head_local
    direction = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
                        -math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), math.sin(math.radians(pitch))))
    target = rig.pose.bones[look.TARGET]
    world = rig.matrix_world @ target.bone.matrix_local
    world.translation = eye + direction * 0.5
    target.matrix = rig.matrix_world.inverted() @ world
    bpy.context.view_layer.update()


class FlatEyeTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        self.iris = iris(self.rig)
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        self.part = ui.add_part(self.rig, self.iris, 'FLAT_EYE')
        self.part.eye_range = 0.1
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))

    def modifier(self):
        return self.iris.modifiers.get("%s %s" % (eyes.MODIFIER_PREFIX, self.part.name))

    def test_modifier_and_drivers(self):
        modifier = self.modifier()
        self.assertIsNotNone(modifier)
        self.assertEqual(modifier.type, 'UV_WARP')
        self.assertTrue(modifier.vertex_group)
        self.assertEqual(eyes.side_of(self.rig, self.part, parts.part_vertices(self.part)), 'LEFT')
        found = [d for d in self.iris.animation_data.drivers if d.data_path.endswith(".offset")]
        self.assertEqual(len(found), 2)
        self.assertTrue(all(d.driver.is_simple_expression for d in found))  # no Python, no Auto Run
        # The iris follows the head, not the eye that turns.
        self.assertEqual({g.name for g in self.iris.vertex_groups if g.name in self.rig.data.bones}, {"Head"})

    def test_iris_slides_with_the_gaze(self):
        aim(self.rig, 0.0, 0.0)
        rest = mean_uv(self.iris)
        aim(self.rig, 20.0, 0.0)  # to the character's left: the drawing moves left, so its UVs move right
        moved = mean_uv(self.iris) - rest
        self.assertAlmostEqual(moved.x, -0.1 * math.sin(math.radians(20.0)), delta=2e-3)
        self.assertAlmostEqual(moved.y, 0.0, delta=2e-3)
        aim(self.rig, 0.0, 10.0)  # up
        moved = mean_uv(self.iris) - rest
        self.assertAlmostEqual(moved.x, 0.0, delta=2e-3)
        self.assertAlmostEqual(moved.y, -0.1 * math.sin(math.radians(10.0)), delta=2e-3)

    def test_build_again_and_change_role(self):
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))
        self.assertEqual(len([m for m in self.iris.modifiers if m.name.startswith(eyes.MODIFIER_PREFIX)]), 1)
        self.assertEqual(len([d for d in self.iris.animation_data.drivers if d.data_path.endswith(".offset")]), 2)
        self.part.role = 'ACCESSORY'
        build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts))
        self.assertIsNone(self.modifier())
        self.assertEqual(len([d for d in self.iris.animation_data.drivers if d.data_path.endswith(".offset")]), 0)


if __name__ == "__main__":
    tu.run_tests()
