# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fingers fitted to the hand of the Body (docs/superpowers/specs/2026-10-19-dasktoon-rig-fingers-design.md): the tips
and the knuckles of five fingers found on the hand laid flat, the thumb in front."""

import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402

LEVEL = [(0.12, 0.0, 1.4), (0.36, 0.0, 1.4), (0.62, 0.0, 1.4)]  # T-pose arms, the wrist at x 0.62
PALM = ((0.6, 0.0, 1.4), (0.72, 0.0, 1.4), 0.045)
# (finger, knuckle, tip), left hand, relative to the middle of the character; the palm faces down, the thumb in front.
FINGERS = (("Thumb", (0.65, -0.04, 1.4), (0.7, -0.095, 1.4)),
           ("Index", (0.72, -0.03, 1.4), (0.795, -0.034, 1.4)),
           ("Middle", (0.72, -0.01, 1.4), (0.805, -0.01, 1.4)),
           ("Ring", (0.72, 0.01, 1.4), (0.795, 0.014, 1.4)),
           ("Little", (0.72, 0.03, 1.4), (0.78, 0.04, 1.4)))
FINGER_RADIUS = 0.008
MIDDLE = Vector((3.0, 0.5, 0.0))


def world(point, sign=1.0):
    return MIDDLE + Vector(point) * Vector((sign, 1.0, 1.0))


def fitted(fingers=True):
    """A chibi Body with a flat-ish palm and, with `fingers`, five fingers apart on each hand, fitted."""
    extra = [PALM]
    if fingers:
        extra += [(knuckle, tip, FINGER_RADIUS) for _name, knuckle, tip in FINGERS]
    body = st.polyline_chibi(LEVEL, st.CentreLineTest.LEG, extra=extra)
    rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
    skeleton.fit(bpy.context, rig, [body], body=[body], skin=[body])
    return rig


def head(rig, name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def tail(rig, name):
    return rig.matrix_world @ rig.data.bones[name].tail_local


class FingersTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_five_fingers_apart(self):
        rig = fitted()
        for side, sign in (("Left", 1.0), ("Right", -1.0)):
            for name, knuckle, tip in FINGERS:
                where = "%s %s" % (side, name)
                self.assertLess((tail(rig, side + name + "Distal") - world(tip, sign)).length, 0.015, where)
                self.assertLess((head(rig, side + name + "Proximal") - world(knuckle, sign)).length, 0.025, where)
                self.assertLess((tail(rig, side + name + "Proximal") - head(rig, side + name + "Intermediate")).length,
                                1e-5, where)  # one chain

    def test_a_hand_without_fingers_apart_keeps_the_template(self):
        """A mitten hand (a chibi's round hand, a glove of one piece): no five tips, the fingers stay as fitted."""
        rig = fitted(fingers=False)
        thumb, middle = head(rig, "LeftThumbProximal"), head(rig, "LeftMiddleProximal")
        self.assertLess(thumb.y, middle.y)  # the template's: the thumb in front, as before
        self.assertGreater(tail(rig, "LeftMiddleDistal").x, world(PALM[1]).x - 0.03)


if __name__ == "__main__":
    tu.run_tests()
