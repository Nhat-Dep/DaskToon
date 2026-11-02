# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A mouth that opens (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part D): a thin slit in the
skin with a mouth built behind it. No test had one, so A I U E O were never made, and joy read the mouth from whatever
loose pieces lay near the middle of the face: on a real character a piece of the collar joined them, and joy dented the
jaw."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_rig_regions_test as rt  # noqa: E402
from dasktoon_rig import auto_expressions, eye_shapes, mouth_shapes  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402

MOUTH_Z = -0.4
HALF = 0.06
INSIDE = (("cavity", 0.0, MOUTH_Z, 0.08, 0.06),)
TEETH = (("upper teeth", 0.0, MOUTH_Z + 0.015, 0.05, 0.008), ("lower teeth", 0.0, MOUTH_Z - 0.015, 0.05, 0.008))


def face_with_slit(rig, half=HALF, gap=0.001, tall=False):
    """A Body part: a face sheet with a slit `half` wide each way at the mouth's place, its lips a little apart. `tall`
    turns the slit on end: a seam, no mouth."""
    centre, size = et.head_frame(rig)
    us = np.linspace(-0.6, 0.6, 49)
    vs = np.linspace(-0.6, 0.25, 35)
    row = int(np.abs(vs - MOUTH_Z).argmin())
    col_low, col_high = int(np.abs(us + half).argmin()), int(np.abs(us - half).argmin())
    n, m = len(us), len(vs)
    verts = [(centre.x + size * u, centre.y - 0.6 * size, centre.z + size * v) for v in vs for u in us]
    doubled = {}
    for c in range(col_low + 1, col_high):
        doubled[c] = len(verts)
        x, y, z = verts[row * n + c]
        verts[row * n + c] = (x, y, z + gap * size)
        verts.append((x, y, z - gap * size))
    faces = []
    for r in range(m - 1):
        for c in range(n - 1):
            below = [r * n + c, r * n + c + 1]
            if r + 1 == row:  # the row under the lips closes on the lower lip's own vertices
                top = [doubled.get(c + 1, (r + 1) * n + c + 1), doubled.get(c, (r + 1) * n + c)]
            else:
                top = [(r + 1) * n + c + 1, (r + 1) * n + c]
            faces.append(tuple(below + top))
    mesh = bpy.data.meshes.new("Face")
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new("Face", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Armature", 'ARMATURE').object = rig
    ui.add_part(rig, obj, 'BODY')
    if tall:
        co = np.array([v.co for v in mesh.vertices])
        xz = co[:, [0, 2]].copy()
        co[:, 0], co[:, 2] = centre.x + (xz[:, 1] - centre.z - MOUTH_Z * size), centre.z + MOUTH_Z * size + (xz[:, 0] - centre.x)
        mesh.vertices.foreach_set("co", co.ravel())
    return obj


class Lipped(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, _objs = rt.rigged()
        cls.eyes = et.eyes_object(cls.rig)
        cls.face = face_with_slit(cls.rig)
        cls.cavity = et.eyes_object(cls.rig, name="Cavity", sides=(1.0,), pieces=INSIDE, depth=-0.5)
        cls.teeth = et.eyes_object(cls.rig, name="Teeth", sides=(1.0,), pieces=TEETH, depth=-0.55)
        cls.meshes = [cls.eyes, cls.face, cls.cavity, cls.teeth]
        cls.found = eye_shapes.find_eyes(cls.rig, cls.meshes)
        cls.centre, cls.size = et.head_frame(cls.rig)


class LipsTest(Lipped):
    def test_the_slit_is_the_mouth(self):
        middle, half = eye_shapes.slit_mouth(self.rig, self.meshes, self.found)
        self.assertAlmostEqual(middle[0], self.centre.x, delta=1e-4)
        self.assertAlmostEqual(middle[2], self.centre.z + MOUTH_Z * self.size, delta=0.03 * self.size)
        self.assertAlmostEqual(half, HALF * self.size, delta=0.03 * self.size)

    def test_a_ring_of_loose_teeth_is_no_slit(self):
        self.assertIsNone(eye_shapes.slit_mouth(self.rig, [self.eyes, self.teeth, self.cavity], self.found))


class OtherFacesTest(unittest.TestCase):
    def test_a_seam_on_end_is_no_slit(self):
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig, tall=True)
        self.assertIsNone(eye_shapes.slit_mouth(rig, [eyes, face], eye_shapes.find_eyes(rig, [eyes])))

    def test_joy_smiles_at_the_slit_whatever_lies_below(self):
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        collar = et.eyes_object(rig, name="Collar", sides=(1.0,), pieces=(("collar", 0.0, -0.62, 0.08, 0.03),), depth=-0.3)
        meshes = [eyes, face, collar]
        eye_shapes.sculpt(rig, meshes)
        centre, size = et.head_frame(rig)
        rest_z = et.rest(face)[:, 2]
        moved = np.abs(et.offsets(face, "joy")[:, 2])
        moved[rest_z > centre.z - 0.3 * size] = 0.0  # the skin under the eyes closes too
        self.assertAlmostEqual(rest_z[moved.argmax()], centre.z + MOUTH_Z * size, delta=0.08 * size)
        self.assertLess(moved[rest_z < centre.z + (MOUTH_Z - 0.12) * size].max(), 1e-7)  # the jaw


class PiecesOfAMouthTest(unittest.TestCase):
    """No slit: the mouth is the row most loose pieces lie in. All of them together made a mouth halfway down the chin."""

    def test_a_piece_further_down_is_no_part_of_the_mouth(self):
        rig, _objs, eyes = et.character()
        lips = et.eyes_object(rig, name="Lips", sides=(1.0,), pieces=(
            ("upper", 0.0, -0.38, 0.05, 0.01), ("lower", 0.0, -0.42, 0.05, 0.01), ("tongue", 0.0, -0.4, 0.03, 0.01)))
        collar = et.eyes_object(rig, name="Collar", sides=(1.0,), pieces=(("collar", 0.0, -0.62, 0.05, 0.02),))
        found = eye_shapes.find_eyes(rig, [eyes])
        centre, size = et.head_frame(rig)
        middle, _half = eye_shapes.piece_mouth(rig, [eyes, lips, collar], found)
        self.assertAlmostEqual(middle[2], centre.z - 0.4 * size, delta=0.02 * size)


class VowelsTest(Lipped):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.made = dict(mouth_shapes.sculpt(cls.rig, cls.meshes))

    def lip(self, key):
        """(top of the gap, bottom of the gap, the mouth's width) in `key`, measured at the middle of the slit."""
        co = et.rest(self.face) + et.offsets(self.face, key)
        ring = max(eye_shapes._rings(self.face.data), key=lambda r: -np.ptp(et.rest(self.face)[r, 2]))
        points = et.rest(self.face)[ring]
        middle = np.abs(points[:, 0] - self.centre.x) < 0.2 * HALF * self.size
        z = co[ring][middle, 2]
        return float(z.max()), float(z.min()), float(np.ptp(co[ring, 0]))

    def opening(self, key):
        top, bottom, _width = self.lip(key)
        return top - bottom

    def test_the_keys_made(self):
        self.assertEqual(sorted(self.made), ["a", "e", "i", "o", "u"])
        for meshes in self.made.values():
            self.assertIn("Face", meshes)
        key = self.face.data.shape_keys
        self.assertEqual({b.value for b in key.key_blocks if b != key.reference_key}, {0.0})

    def test_a_opens_the_mouth(self):
        self.assertGreater(self.opening("a"), 0.8 * HALF * self.size)

    def test_the_vowels_open_as_far_as_they_should(self):
        self.assertGreater(self.opening("a"), self.opening("o"))
        self.assertGreater(self.opening("o"), self.opening("e"))
        self.assertGreater(self.opening("e"), self.opening("u"))
        self.assertGreater(self.opening("u"), self.opening("i"))

    def test_they_are_as_wide_as_they_should_be(self):
        width = {key: self.lip(key)[2] for key in ("a", "i", "u", "o")}
        self.assertGreater(width["i"], width["a"])
        self.assertLess(width["u"], width["a"])
        self.assertLess(width["o"], width["a"])

    def test_the_corners_stay_shut(self):
        co = et.rest(self.face) + et.offsets(self.face, "a")
        ring = max(eye_shapes._rings(self.face.data), key=lambda r: -np.ptp(et.rest(self.face)[r, 2]))
        points = et.rest(self.face)[ring]
        out = np.abs(points[:, 0] - self.centre.x)
        corner = out >= 0.85 * out.max()
        self.assertLess(float(np.ptp(co[ring][corner, 2])), 0.3 * self.opening("a"))

    def test_the_skin_far_from_it_stays(self):
        rest = et.rest(self.face)
        moved = np.linalg.norm(et.offsets(self.face, "a"), axis=1)
        far = np.abs(rest[:, 2] - (self.centre.z + MOUTH_Z * self.size)) > 0.25 * self.size
        self.assertLess(moved[far].max(), 1e-7)

    def test_the_lower_teeth_go_with_the_jaw(self):
        moved = et.offsets(self.teeth, "a")[:, 2]
        low = et.rest(self.teeth)[:, 2] < self.centre.z + MOUTH_Z * self.size
        self.assertLess(moved[low].max(), -1e-4)
        self.assertLess(np.abs(moved[~low]).max(), 1e-7)

    def test_what_lies_behind_narrows_with_the_lips(self):
        """A line of the mouth is a piece of its own on some characters: left as wide as it was, it stood out on each side
        of pursed lips."""
        for key, wide in (("u", 0.72), ("o", 0.78)):
            before = et.rest(self.teeth)[:, 0] - self.centre.x
            after = before + et.offsets(self.teeth, key)[:, 0]
            np.testing.assert_allclose(after, before * wide, atol=1e-5)

    def test_it_stays_as_wide_for_a_wide_mouth(self):
        self.assertLess(np.abs(et.offsets(self.teeth, "i")[:, 0]).max(), 1e-7)

    def test_the_inside_of_the_mouth_stays(self):
        key = self.cavity.data.shape_keys
        self.assertTrue(key is None or "a" not in key.key_blocks)


class RoomTest(unittest.TestCase):
    """The lips go no further than what lies behind them, or the mouth shows through to the back of the head."""

    def test_it_opens_no_further_than_the_inside(self):
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        small = et.eyes_object(rig, name="Cavity", sides=(1.0,), pieces=(("cavity", 0.0, MOUTH_Z, 0.08, 0.02),), depth=-0.5)
        mouth_shapes.sculpt(rig, [eyes, face, small])
        centre, size = et.head_frame(rig)
        low = (et.rest(face) + et.offsets(face, "a"))[:, 2].min()
        lowest = (et.rest(face)[np.abs(et.rest(face)[:, 2] - (centre.z + MOUTH_Z * size)) < 0.01 * size, 2]).min()
        moved = lowest - (et.rest(face) + et.offsets(face, "a"))[
            np.abs(et.rest(face)[:, 2] - lowest) < 1e-6 * size, 2].min()
        self.assertLessEqual(moved, 0.02 * size + 1e-4)
        self.assertGreater(moved, 0.0)
        self.assertLess(low, et.rest(face)[:, 2].min() + 1e-6)

    def test_the_lips_part_only_in_front_of_the_inside(self):
        """The inside narrower than the slit: past its edge an open mouth looked through to the hair behind the head."""
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        narrow = et.eyes_object(rig, name="Cavity", sides=(1.0,), pieces=(("cavity", 0.0, MOUTH_Z, 0.015, 0.06),), depth=-0.5)
        mouth_shapes.sculpt(rig, [eyes, face, narrow])
        centre, size = et.head_frame(rig)
        ring = max(eye_shapes._rings(face.data), key=lambda r: -np.ptp(et.rest(face)[r, 2]))
        past = np.abs(et.rest(face)[ring, 0] - centre.x) > 0.017 * size
        self.assertLess(np.abs(et.offsets(face, "a")[ring][past, 2]).max(), 1e-6)
        self.assertGreater(np.abs(et.offsets(face, "a")[ring, 2]).max(), 0.01 * size)

    def test_the_teeth_stay_behind_the_lip(self):
        """They went down further than the lip, and came through the skin under it."""
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        cavity = et.eyes_object(rig, name="Cavity", sides=(1.0,), pieces=INSIDE, depth=-0.5)
        low = et.eyes_object(rig, name="Teeth", sides=(1.0,), pieces=(("teeth", 0.0, MOUTH_Z - 0.03, 0.05, 0.012),), depth=-0.55)
        mouth_shapes.sculpt(rig, [eyes, face, cavity, low])
        ring = max(eye_shapes._rings(face.data), key=lambda r: -np.ptp(et.rest(face)[r, 2]))
        lip = float((et.rest(face) + et.offsets(face, "a"))[ring, 2].min())
        self.assertGreater(float((et.rest(low) + et.offsets(low, "a"))[:, 2].min()), lip - 1e-5)

    def test_with_nothing_behind_it_there_are_no_vowels(self):
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        self.assertEqual(mouth_shapes.sculpt(rig, [eyes, face]), [])


class WithAutoExpressionsTest(unittest.TestCase):
    def character(self):
        rig, _objs = rt.rigged()
        eyes = et.eyes_object(rig)
        face = face_with_slit(rig)
        cavity = et.eyes_object(rig, name="Cavity", sides=(1.0,), pieces=INSIDE, depth=-0.5)
        return rig, eyes, face, [eyes, face, cavity]

    def test_the_button_makes_them(self):
        rig, _eyes, _face, meshes = self.character()
        result = auto_expressions.run(rig, meshes)
        for slot in "AIUEO":
            self.assertNotIn(slot, result.left)
        self.assertEqual(auto_expressions.states(meshes)["A"], 'READY')

    def test_a_vowel_made_by_hand_stays(self):
        rig, _eyes, face, meshes = self.character()
        face.shape_key_add(name="Basis", from_mix=False)
        mine = face.shape_key_add(name="a", from_mix=False)
        mine.data[0].co.z += 0.01
        mine.value = 0.0
        hand = et.offsets(face, "a").copy()
        made = dict(mouth_shapes.sculpt(rig, meshes))
        self.assertNotIn("a", made)
        np.testing.assert_allclose(et.offsets(face, "a"), hand, atol=1e-7)
        self.assertIn("o", made)

    def test_an_empty_vowel_is_filled_and_not_doubled(self):
        rig, _eyes, face, meshes = self.character()
        face.shape_key_add(name="Basis", from_mix=False)
        face.shape_key_add(name="aa", from_mix=False).value = 0.0
        made = dict(mouth_shapes.sculpt(rig, meshes))
        self.assertIn("aa", made)
        self.assertNotIn("a", face.data.shape_keys.key_blocks)


if __name__ == "__main__":
    tu.run_tests()
