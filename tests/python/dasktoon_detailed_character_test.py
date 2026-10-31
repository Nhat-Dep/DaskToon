# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A character as detailed as a real one, end to end: Anime Humanoid, then Auto Expressions. Every other fixture is
clean: a few meshes with sensible names, skin all the way down, eyes alone on the face. What real models brought
(2026-10-30) is all here at once, under names that say nothing: surfaces cut along their texture seams, skin only where it
shows, shoes and socks below it, hair cut in pieces, studs, crystals out at the sides, a bag, a bow, and a face crowded
with brows, blush, shadow and lash bits. The checks ask what a person sees, not how it was found."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import auto_expressions, parts as rig_parts  # noqa: E402

JOINTS = ("Hips", "Chest", "Neck", "Head", "LeftUpperArm", "LeftLowerArm", "LeftHand", "LeftUpperLeg", "LeftLowerLeg",
          "LeftFoot")
# Across the eye's face: (name, centre x, centre z, half width, half height) in the head's frame.
CROWD = (("blush", 0.3, -0.33, 0.08, 0.03), ("shadow", 0.0, -0.05, 0.5, 0.25), ("lash bit", 0.36, -0.03, 0.015, 0.015))


def tube(a, b, radius, seams):
    """A tube from a to b, cut across `seams` times: pieces that only touch, its vertices doubled along the cuts."""
    a, b = Vector(a), Vector(b)
    if not seams:
        return [st.tube(tuple(a), tuple(b), radius)]
    steps = seams + 1
    return [st.tube(tuple(a.lerp(b, i / steps)), tuple(a.lerp(b, (i + 1) / steps)), radius, rings=3) for i in range(steps)]


def stud(x, y, z, half=0.012):
    return st.tube((x, y, z - half), (x, y, z + half), half, rings=1, segments=6)


def dressed(seams):
    """The meshes of the character, 2 tall in A-pose; `seams`: how many times each long surface is cut."""
    arms, thighs, socks, shoes, sleeves = [], [], [], [], []
    for s in (1.0, -1.0):
        mirror = Vector((s, 1.0, 1.0))
        elbow = rt.ARM_START + (rt.ARM_END - rt.ARM_START) * 0.5
        arms += tube(rt.ARM_START * mirror, rt.ARM_END * mirror, 0.05, seams)
        sleeves += tube(rt.ARM_START * mirror, elbow * mirror, 0.062, seams)
        thighs += tube((s * 0.08, 0, 0.95), (s * 0.09, 0, 0.55), 0.07, seams)
        socks += tube((s * 0.09, 0, 0.56), (s * 0.09, 0, 0.2), 0.075, seams)
        shoes.append(st.tube((s * 0.09, 0, 0.2), (s * 0.09, -0.08, 0.02), 0.09))
    skin = arms + thighs + tube((0, 0, 0.88), (0, 0, 1.46), 0.18, seams) + [st.tube((0, 0, 1.46), (0, 0, 2.0), 0.3)]
    studs = [stud(0.0, -0.2, 0.95 + i * 0.04) for i in range(12)]
    shirt = tube((0, 0, 1.4), (0, 0, 0.9), 0.2, seams) + sleeves + studs
    crystals = [st.tube((s * 0.55, 0.0, 1.5), (s * 1.2, 0.0, 1.5), 0.06) for s in (1.0, -1.0)]
    bag = [st.tube((0.25, 0.34, 0.8), (0.25, 0.34, 1.0), 0.09), st.tube((0.0, 0.42, 1.2), (0.0, 0.42, 1.3), 0.07)]
    bow = [st.tube((0.3, 0.1, 1.92), (0.3, 0.2, 1.92), 0.05)]
    locks = []
    for s in (1.0, -1.0):
        locks += tube((s * 0.3, 0.2, 1.95), (s * 0.33, 0.28, 1.0), 0.03, seams)
    hair = [st.tube((0, 0, 1.78), (0, 0, 2.06), 0.33)] + locks
    return [rt.merged(name, pieces) for name, pieces in (
        ("Circle", skin), ("Circle.001", shirt + socks + shoes), ("Circle.002", crystals), ("Circle.003", bag),
        ("Circle.004", bow), ("Circle.005", hair))]


def rigged(meshes):
    for obj in bpy.data.objects:
        obj.select_set(False)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    known = set(bpy.data.objects)
    assert bpy.ops.dasktoon.rig_add_humanoid() == {'FINISHED'}
    return next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and obj not in known)


def joints(rig):
    return {name: rig.matrix_world @ rig.data.bones[name].head_local for name in JOINTS}


def clean(meshes):
    """`meshes` as before a rig: what the last rig left on them goes."""
    for obj in meshes:
        obj.modifiers.clear()
        obj.vertex_groups.clear()
        for name in ("DaskToon Region",):
            attribute = obj.data.color_attributes.get(name)
            if attribute is not None:
                obj.data.color_attributes.remove(attribute)


class Detailed(unittest.TestCase):
    seams = 2

    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cls.meshes = dressed(cls.seams)
        first = rigged(cls.meshes)  # only to know where the head lands: the face goes on it, as it was there all along
        cls.eyes = et.eyes_object(first, name="Circle.006")
        cls.brows = et.eyes_object(first, name="Circle.007", pieces=et.BROW)
        cls.crowd = et.eyes_object(first, name="Circle.008", pieces=CROWD, depth=-0.72)
        cls.meshes += [cls.eyes, cls.brows, cls.crowd]
        bpy.data.objects.remove(first)
        clean(cls.meshes)
        cls.rig = rigged(cls.meshes)
        cls.parts = list(cls.rig.data.dasktoon_rig.parts)
        cls.result = auto_expressions.run(cls.rig, auto_expressions.meshes_of(cls.meshes[0]))


class SkeletonTest(Detailed):
    def test_it_stands_on_its_shoes(self):
        self.assertLess(joints(self.rig)["LeftFoot"].z, 0.25)

    def test_the_hips_and_the_knees(self):
        found = joints(self.rig)
        self.assertLess(abs(found["Hips"].z - 0.95), 0.2)
        self.assertLess(abs(found["LeftLowerLeg"].z - 0.5), 0.15)

    def test_the_shoulders_are_where_the_arms_start(self):
        self.assertLess((joints(self.rig)["LeftUpperArm"] - rt.ARM_START).length, 0.2)

    def test_the_hands_are_at_the_hands_not_the_crystals(self):
        self.assertLess((joints(self.rig)["LeftHand"] - rt.ARM_END).length, 0.2)

    def test_the_head_is_on_the_neck(self):
        found = joints(self.rig)
        self.assertLess(found["Neck"].z, found["Head"].z)
        self.assertLess(abs(found["Head"].z - 1.55), 0.25)


class PartsTest(Detailed):
    def part_at(self, obj, point):
        """The part holding the vertex of `obj` nearest `point`."""
        world, _edges = rig_parts.mesh_arrays(obj)
        nearest = int(np.argmin(np.linalg.norm(world - np.array(point), axis=1)))
        holding = [part for part in self.parts if part.object == obj and nearest in rig_parts.part_vertices(part)]
        return next((part for part in holding if part.role == 'ACCESSORY'), holding[0])

    def test_what_floats_is_an_accessory(self):
        by_name = {obj.name: obj for obj in self.meshes}
        self.assertEqual(self.part_at(by_name["Circle.002"], (1.2, 0, 1.5)).role, 'ACCESSORY')
        self.assertEqual(self.part_at(by_name["Circle.003"], (0.25, 0.34, 0.9)).role, 'ACCESSORY')
        self.assertEqual(self.part_at(by_name["Circle.004"], (0.3, 0.15, 1.92)).role, 'ACCESSORY')

    def test_what_is_worn_on_the_body_is_not(self):
        outfit = next(obj for obj in self.meshes if obj.name == "Circle.001")
        for point in ((0.2, 0, 1.2), (0.09, 0, 0.4), (0.09, -0.08, 0.02)):  # shirt, sock, shoe
            self.assertNotEqual(self.part_at(outfit, point).role, 'ACCESSORY', point)


class ExpressionsTest(Detailed):
    def test_the_eyes_are_ready(self):
        states = auto_expressions.states(auto_expressions.meshes_of(self.meshes[0]))
        for slot in ("BLINK", "BLINK_L", "BLINK_R", "JOY", "SURPRISED"):
            self.assertEqual(states[slot], 'READY', slot)

    def test_a_blink_closes_the_eyes_and_nothing_else(self):
        moved = et.offsets(self.eyes, "blink")
        self.assertLess(moved[:, 2].min(), -1e-3)  # the upper lid comes down ...
        self.assertGreater(moved[:, 2].max(), 1e-3)  # ... and the lower one up: they meet
        for obj in (self.brows, self.crowd):
            key = obj.data.shape_keys
            if key is not None and "blink" in key.key_blocks:
                self.assertLess(np.abs(et.offsets(obj, "blink")).max(), 1e-6, obj.name)

    def test_they_all_start_off(self):
        for obj in auto_expressions.meshes_of(self.meshes[0]):
            key = obj.data.shape_keys
            if key is not None:
                self.assertEqual({b.value for b in key.key_blocks if b != key.reference_key} - {0.0}, set(), obj.name)


class SeamsChangeNothingTest(unittest.TestCase):
    """A surface cut along its seams is the same surface: the rig must not tell the two apart."""

    def test_the_skeleton_is_the_same(self):
        found = []
        for seams in (0, 2):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            found.append(joints(rigged(dressed(seams))))
        for name in JOINTS:
            self.assertLess((found[0][name] - found[1][name]).length, 0.04, name)

    def test_so_are_the_parts_and_the_bones(self):
        counts = []
        for seams in (0, 2):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            rig = rigged(dressed(seams))
            data = rig.data.dasktoon_rig
            counts.append((len(rig.data.bones), sorted(part.role for part in data.parts)))
        self.assertEqual(counts[0], counts[1])


if __name__ == "__main__":
    tu.run_tests()
