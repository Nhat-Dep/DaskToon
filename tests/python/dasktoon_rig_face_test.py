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
from dasktoon_rig import build, look, parts, skeleton  # noqa: E402


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


if __name__ == "__main__":
    tu.run_tests()
