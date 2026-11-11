# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face keys sculpted from nothing (docs/superpowers/specs/2026-11-11-dasktoon-dlive-face-sculpt-design.md): a character
with no face shape keys, with or without a DaskToon rig, gets the ARKit keys a face's own shape can make. The head here is a
sphere one unit tall with eye pieces in front of it (its radius 0.5, the eyes 0.25 to each side, at 0.15 under its middle);
what differs is where the brows are (none, loose pieces of the head's own mesh, meshes of their own), which way it faces, how
the character is skeletoned (none, a skeleton of Japanese bone names) and whether it is modelled in half.

No vertex moves more than a share of the face's height, no brow key moves anything under the eyes, no jaw key anything over
them or behind the head's middle, and the two sides of a pair are each other's mirror."""

import math
import os
import sys
import unittest

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_dlive import expressions as dlive  # noqa: E402
from dasktoon_rig import face_frame, face_shapes  # noqa: E402

RADIUS = 0.5
EYE_Z = -0.15
EYE_X = 0.25
FACE_HEIGHT = 1.0
MOST = 0.15  # of the face's height: the furthest a vertex of any key moves
BROWS = ("browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight")
JAWS = ("jawForward", "jawLeft", "jawRight", "jawOpen")
PAIRS = (("browDownLeft", "browDownRight"), ("browOuterUpLeft", "browOuterUpRight"), ("cheekSquintLeft", "cheekSquintRight"),
         ("noseSneerLeft", "noseSneerRight"), ("mouthPressLeft", "mouthPressRight"), ("mouthStretchLeft", "mouthStretchRight"),
         ("mouthDimpleLeft", "mouthDimpleRight"), ("mouthSmileLeft", "mouthSmileRight"), ("mouthFrownLeft", "mouthFrownRight"),
         ("mouthLowerDownLeft", "mouthLowerDownRight"), ("mouthUpperUpLeft", "mouthUpperUpRight"),
         ("mouthLeft", "mouthRight"), ("jawLeft", "jawRight"), ("eyeWideLeft", "eyeWideRight"),
         ("eyeSquintLeft", "eyeSquintRight"))
CANNOT = {n for n in dlive.ARKIT if n.startswith("eyeLook")} | {"tongueOut"}  # no iris to turn in a ball, no tongue


def link(name, verts, faces, scale=1.0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def sphere_mesh(name, half=False):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=RADIUS)
    if half:  # modelled in half: x <= 0 only, a Mirror modifier makes the rest
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                               clear_outer=True)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def skin_y(x, z):
    return -math.sqrt(max(RADIUS ** 2 - x * x - z * z, 0.0))


def eye_pieces(name="Eyes", half=False):
    """The eye pieces of et.PIECES (the head's frame is the scene's: the head's size is 1) in front of the sphere."""
    verts, faces = [], []
    for s in ((1.0,) if half else (1.0, -1.0)):
        for _n, x, z, hw, hh in et.PIECES:
            v, f = et.grid(s * x * (-1.0 if half else 1.0), EYE_Z + (z + 0.15), hw, hh, skin_y(x, z + EYE_Z + 0.15) - 0.04)
            faces += [tuple(i + len(verts) for i in face) for face in f]
            verts += v
    return link(name, verts, faces)


def brow_grid(side, verts, faces):
    x, z = 0.25 * side, 0.07
    v, f = et.grid(x, z, 0.1, 0.015, skin_y(abs(x), z) - 0.02)
    faces += [tuple(i + len(verts) for i in face) for face in f]
    verts += v


def joined(head, extra_verts, extra_faces):
    """`head` with the pieces added to its own mesh."""
    mesh = head.data
    base = len(mesh.vertices)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    new = [bm.verts.new(v) for v in extra_verts]
    for face in extra_faces:
        bm.faces.new([new[i] for i in face])
    bm.to_mesh(mesh)
    bm.free()
    return base


def hair_mesh():
    """A cap over the top of the head: it never moves."""
    obj = sphere_mesh("Hair")
    obj.scale = (1.06, 1.06, 1.06)
    bpy.context.view_layer.update()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0.1], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def head(brows=None, half=False, facing=1.0, with_hair=True):
    """(meshes by name) of a one-unit head; brows None (none), 'pieces' (loose pieces of the head's mesh), 'meshes' (a
    mesh of their own); `facing` -1 turns the whole character to face +Y."""
    tu.reset_scene()
    objs = {"Head": sphere_mesh("Head", half), "Eyes": eye_pieces("Eyes", half)}
    if brows:
        verts, faces = [], []
        for side in ((-1.0,) if half else (1.0, -1.0)):
            brow_grid(side, verts, faces)
        if brows == 'pieces':
            joined(objs["Head"], verts, faces)
        else:
            objs["Brows"] = link("Brows", verts, faces)
    if with_hair:
        objs["Hair"] = hair_mesh()
    for obj in objs.values():
        if half:
            modifier = obj.modifiers.new("Mirror", 'MIRROR')
            modifier.use_axis[0] = True
        if facing < 0:
            obj.rotation_euler.z = math.pi
    bpy.context.view_layer.update()
    return objs


def world_offsets(obj, name):
    """The offsets of key `name` of `obj` in the scene, and the rest positions in the scene."""
    key = obj.data.shape_keys
    base = np.array([p.co for p in key.reference_key.data])
    moved = np.array([p.co for p in key.key_blocks[name].data]) - base
    r = np.array(obj.matrix_world.to_3x3())
    return moved @ r.T, base @ r.T + np.array(obj.matrix_world.translation)


def has(obj, name):
    key = obj.data.shape_keys
    return key is not None and name in key.key_blocks


def moves(obj, name, least=1e-6):
    return has(obj, name) and float(np.abs(world_offsets(obj, name)[0]).max()) > least


def moving_objects(objs, name):
    return [o for o in objs.values() if moves(o, name)]


def made(objs, rig=None):
    return dlive.make(list(objs.values()), rig)


def described(objs, rig=None):
    report = made(objs, rig)
    return report, dlive.describe(list(objs.values()), {}, rig, report)


class RiglessHeadTest(unittest.TestCase):
    """No armature, no keys: the eyes tell where the face is."""

    def test_all_the_keys_a_face_can_make_are_made(self):
        objs = head()
        _report, data = described(objs)
        self.assertLessEqual(set(data["made"]["missing"]), CANNOT, data["made"])
        for name in ("browDownLeft", "browInnerUp", "eyeWideLeft", "cheekPuff", "mouthPucker", "jawLeft", "mouthRollUpper"):
            self.assertIn(name, data["keys"])
        for vrm in ("aa", "ih", "ou", "ee", "oh", "angry", "sad", "relaxed", "blink", "happy", "surprised"):
            self.assertIn(vrm, data["keys"])

    def test_the_report_says_how_each_was_made(self):
        report, data = described(head())
        self.assertIn("browInnerUp", report["how"])
        self.assertTrue(all(report["how"][n] for n in report["sculpted"] if n[0].islower() and n in dlive.ARKIT), report)

    def test_nothing_is_left_behind(self):
        objs = head()
        before = {name: len(getattr(bpy.data, name)) for name in ("objects", "armatures")}
        made(objs)
        self.assertEqual({name: len(getattr(bpy.data, name)) for name in ("objects", "armatures")}, before)
        for obj in objs.values():
            self.assertEqual([m.type for m in obj.modifiers], [])

    def test_a_head_that_faces_back_has_its_left_and_right_the_right_way(self):
        objs = head(facing=-1.0)
        made(objs)
        moved, rest = world_offsets(objs["Eyes"], "eyeWideLeft")
        near = np.abs(moved).max(axis=1) > 1e-6
        self.assertTrue(near.any())
        self.assertTrue((rest[near, 0] < 0.0).all(), "the character's left is the scene's -X when it faces +Y")
        moved, rest = world_offsets(objs["Eyes"], "eyeBlinkLeft")
        self.assertTrue((rest[np.abs(moved).max(axis=1) > 1e-6, 0] < 0.0).all())

    def test_the_hair_never_moves(self):
        objs = head()
        made(objs)
        key = objs["Hair"].data.shape_keys
        for block in key.key_blocks if key is not None else ():
            if block != key.reference_key:
                self.assertEqual(float(np.abs(world_offsets(objs["Hair"], block.name)[0]).max()), 0.0, block.name)

    def test_no_vertex_moves_far_and_each_key_stays_in_its_place(self):
        objs = head()
        made(objs)
        everything = [(o, b.name) for o in objs.values() if o.data.shape_keys for b in o.data.shape_keys.key_blocks
                      if b != o.data.shape_keys.reference_key]
        for obj, name in everything:
            moved, rest = world_offsets(obj, name)
            self.assertLessEqual(float(np.linalg.norm(moved, axis=1).max()), MOST * FACE_HEIGHT, (obj.name, name))
            if name in BROWS:
                self.assertEqual(float(np.abs(moved[rest[:, 2] < EYE_Z]).max(initial=0.0)), 0.0, (obj.name, name))
            if name in JAWS:
                self.assertEqual(float(np.abs(moved[(rest[:, 2] > 0.0) | (rest[:, 1] > 0.02)]).max(initial=0.0)), 0.0,
                                 (obj.name, name))

    def test_pairs_are_mirrors(self):
        objs = head()
        made(objs)
        body = objs["Head"]
        for left, right in PAIRS:
            if not (has(body, left) and has(body, right)):
                continue
            a, rest_a = world_offsets(body, left)
            b, rest_b = world_offsets(body, right)
            lookup = {tuple(np.round(r * np.array((-1.0, 1.0, 1.0)), 4)): i for i, r in enumerate(rest_b)}
            for i in np.nonzero(np.abs(a).max(axis=1) > 1e-6)[0]:
                j = lookup.get(tuple(np.round(rest_a[i], 4)))
                if j is not None:
                    self.assertTrue(np.allclose(a[i] * np.array((-1.0, 1.0, 1.0)), b[j], atol=2e-4), (left, right, i))

    def test_the_left_keys_move_the_left_of_the_face(self):
        objs = head()
        made(objs)
        for name in ("browDownLeft", "cheekSquintLeft", "mouthStretchLeft", "noseSneerLeft"):
            moved, rest = world_offsets(objs["Head"], name)
            moving = np.abs(moved).max(axis=1) > 1e-6
            self.assertTrue(moving.any(), name)
            self.assertGreater(float(rest[moving, 0].mean()), 0.0, name)
            self.assertLess(float(rest[moving, 0].min()), 0.1, name)


class BrowsTest(unittest.TestCase):
    def test_skin_above_the_eyes_when_there_are_no_brows(self):
        objs = head()
        made(objs)
        for name in BROWS:
            self.assertEqual([o.name for o in moving_objects(objs, name)], ["Head"], name)
            moved, rest = world_offsets(objs["Head"], name)
            moving = np.abs(moved).max(axis=1) > 1e-6
            self.assertGreater(float(rest[moving, 2].min()), EYE_Z + 0.05, name)
        moved, _rest = world_offsets(objs["Head"], "browInnerUp")
        self.assertGreater(float(moved[:, 2].max()), 0.01)
        moved, _rest = world_offsets(objs["Head"], "browDownLeft")
        self.assertLess(float(moved[:, 2].min()), -0.01)

    def test_brows_that_are_pieces_of_the_heads_mesh_move_as_they_are(self):
        objs = head(brows='pieces')
        base = len(sphere_mesh("Counter").data.vertices)
        bpy.data.objects.remove(bpy.data.objects["Counter"])
        made(objs)
        for name in BROWS:
            moved, rest = world_offsets(objs["Head"], name)
            moving = np.nonzero(np.abs(moved).max(axis=1) > 1e-6)[0]
            self.assertTrue(len(moving), name)
            self.assertTrue((moving >= base).all(), "only the brow pieces move, not the skin: " + name)
        moved, rest = world_offsets(objs["Head"], "browInnerUp")
        inner = moved[rest[:, 0] * np.sign(rest[:, 0] + 1e-9) > 0.0]
        pieces = np.arange(len(rest)) >= base
        near = pieces & (np.abs(rest[:, 0]) < 0.2)
        far = pieces & (np.abs(rest[:, 0]) > 0.3)
        self.assertGreater(float(moved[near, 2].max()), float(moved[far, 2].max()) + 0.005, "the inner end rises most")
        self.assertEqual(len(inner) > 0, True)

    def test_brows_that_are_meshes_of_their_own_move_as_they_are(self):
        objs = head(brows='meshes')
        made(objs)
        for name in BROWS:
            self.assertEqual([o.name for o in moving_objects(objs, name)], ["Brows"], name)
        moved, rest = world_offsets(objs["Brows"], "browDownRight")
        moving = np.abs(moved).max(axis=1) > 1e-6
        self.assertTrue((rest[moving, 0] < 0.0).all(), "the right brow only")
        self.assertLess(float(moved[:, 2].min()), -0.01)
        moved, rest = world_offsets(objs["Brows"], "browOuterUpLeft")
        left_outer = moved[(rest[:, 0] > 0.3), 2].max()
        left_inner = moved[(rest[:, 0] > 0.0) & (rest[:, 0] < 0.2), 2].max()
        self.assertGreater(float(left_outer), float(left_inner))


class SkeletonTest(unittest.TestCase):
    def test_a_skeleton_of_japanese_bone_names_gives_the_same_keys(self):
        objs = head(brows='meshes')
        rig = bpy.data.objects.new("MMD", bpy.data.armatures.new("MMD"))
        bpy.context.scene.collection.objects.link(rig)
        from dasktoon_rig import skeleton
        with skeleton.editing(bpy.context, rig) as edit:
            for name, head_at, tail_at in (("センター", (0, 0, -3), (0, 0, -2)),
                                           ("首", (0, 0, -0.6), (0, 0, -0.5)), ("頭", (0, 0, -0.5), (0, 0, 0.55))):
                bone = edit.new(name)
                bone.head, bone.tail = head_at, tail_at
        for obj in objs.values():
            obj.modifiers.new("Armature", 'ARMATURE').object = rig
        before = len(bpy.data.armatures), len(bpy.data.objects)
        report, data = described(objs, rig)
        self.assertEqual((len(bpy.data.armatures), len(bpy.data.objects)), before)
        self.assertLessEqual(set(data["made"]["missing"]), CANNOT, data["made"])
        self.assertEqual([o.name for o in moving_objects(objs, "browInnerUp")], ["Brows"])
        self.assertEqual([b.name for b in rig.data.bones], ["センター", "首", "頭"])
        self.assertEqual(len(rig.modifiers), 0)


class HalfHeadTest(unittest.TestCase):
    def test_a_head_modelled_in_half_gets_keys_of_each_side(self):
        objs = head(half=True)
        _report, data = described(objs)
        self.assertLessEqual(set(data["made"]["missing"]), CANNOT, data["made"])
        body = objs["Head"]
        self.assertEqual([m.type for m in body.modifiers], [], "the copy holds both sides: its Mirror is applied")
        moved_left, rest = world_offsets(body, "mouthStretchLeft")
        moved_right, _ = world_offsets(body, "mouthStretchRight")
        self.assertTrue(np.abs(moved_left).max() > 1e-6 and np.abs(moved_right).max() > 1e-6)
        self.assertTrue(float(rest[np.abs(moved_left).max(axis=1) > 1e-6, 0].mean()) > 0.0)
        self.assertTrue(float(rest[np.abs(moved_right).max(axis=1) > 1e-6, 0].mean()) < 0.0)


class StandInTest(unittest.TestCase):
    def test_a_cheek_key_made_from_joy_does_not_close_the_eye(self):
        objs = head()
        made(objs)
        for name in ("cheekSquintLeft", "cheekSquintRight"):
            self.assertEqual(moves(objs["Eyes"], name, 1e-5), False, name)
            self.assertTrue(moves(objs["Head"], name), name)


class FrameTest(unittest.TestCase):
    def test_no_eyes_no_frame(self):
        objs = head()
        bpy.data.objects.remove(objs["Eyes"])
        with face_frame.located(bpy.context, [objs["Head"]], None) as rig:
            self.assertIsNone(rig)
        self.assertEqual([m.type for m in objs["Head"].modifiers], [])

    def test_the_frame_is_on_the_head(self):
        objs = head()
        with face_frame.located(bpy.context, list(objs.values()), None) as rig:
            self.assertIsNotNone(rig)
            centre = rig.matrix_world.translation
            size = rig.matrix_world.to_scale().x
        self.assertLess(Vector((centre.x, centre.y, centre.z)).length, 0.25)
        self.assertGreater(size, 0.5)
        self.assertLess(size, 2.0)


if __name__ == "__main__":
    tu.run_tests()
