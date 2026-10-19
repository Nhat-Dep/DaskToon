# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sculpt Eye Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part B): the eyes of a
character are the loose pieces in front of its head, one group a side; blink squashes both onto a line a third of the
way up, blink_L and blink_R one each, joy closes them as an arc, surprised makes them bigger. Keys that move are kept;
a face with eye sockets is left alone."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import eye_shapes  # noqa: E402

# One eye, in the head's frame (centre of the Head bone, its length as the unit; +x the character's left):
# (name, centre x, centre z, half width, half height); every piece is a flat grid facing -Y at y = -0.7.
PIECES = (("white", 0.25, -0.15, 0.09, 0.07), ("iris", 0.25, -0.15, 0.04, 0.06),
          ("upper lash", 0.25, -0.07, 0.1, 0.012), ("lower lash", 0.25, -0.22, 0.08, 0.008))


def grid(cx, cz, hw, hh, y, n=4):
    verts = [(cx + hw * u, y, cz + hh * v) for v in np.linspace(-1, 1, n) for u in np.linspace(-1, 1, n)]
    faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(n - 1)
             for c in range(n - 1)]
    return verts, faces


def head_frame(rig):
    head = rig.data.bones["Head"]
    return (head.head_local + head.tail_local) / 2.0, head.length


def eyes_object(rig, name="Eyes", sides=(1.0, -1.0), pieces=PIECES, socket=False):
    """A mesh of the eye pieces of both sides (head frame mapped to the rig's space), deformed by the rig."""
    centre, size = head_frame(rig)
    verts, faces = [], []
    for s in sides:
        for _name, x, z, hw, hh in pieces:
            v, f = grid(centre.x + s * x * size, centre.z + z * size, hw * size, hh * size, centre.y - 0.7 * size)
            faces += [tuple(i + len(verts) for i in face) for face in f]
            verts += v
    if socket:  # a face sheet in front with a hole where each eye is
        n = 12
        sheet = [(centre.x + size * u, centre.y - 0.65 * size, centre.z + size * (v - 0.15))
                 for v in np.linspace(-0.4, 0.4, n) for u in np.linspace(-0.6, 0.6, n)]
        base = len(verts)
        verts += sheet
        for r in range(n - 1):
            for c in range(n - 1):
                quad = [r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c]
                middle = np.mean([sheet[i] for i in quad], axis=0)
                rel_x, rel_z = (middle[0] - centre.x) / size, (middle[2] - centre.z) / size
                if abs(abs(rel_x) - 0.25) < 0.11 and abs(rel_z + 0.15) < 0.09:
                    continue  # the hole
                faces.append(tuple(base + i for i in quad))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Armature", 'ARMATURE').object = rig
    return obj


def character(**kwargs):
    rig, objs = rt.rigged()
    return rig, objs, eyes_object(rig, **kwargs)


def offsets(obj, name):
    key = obj.data.shape_keys
    base = np.array([p.co for p in key.reference_key.data])
    return np.array([p.co for p in key.key_blocks[name].data]) - base


def rest(obj):
    return np.array([v.co for v in obj.data.vertices])


def side_mask(rig, obj, sign):
    centre, _size = head_frame(rig)
    return (rest(obj)[:, 0] - centre.x) * sign > 0


class SculptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.eyes = character()
        cls.made = eye_shapes.sculpt(cls.rig, [cls.eyes] + list(cls.objs.values()))

    def test_the_keys_made(self):
        self.assertEqual(sorted(name for name, _meshes in self.made),
                         ["blink", "blink_L", "blink_R", "joy", "surprised"])
        self.assertEqual({tuple(meshes) for _name, meshes in self.made}, {("Eyes",)})
        self.assertIsNone(self.objs["Body"].data.shape_keys)  # no eye piece there

    def test_blink_closes_each_eye_on_a_line(self):
        co = rest(self.eyes) + offsets(self.eyes, "blink")
        _centre, size = head_frame(self.rig)
        for sign in (1.0, -1.0):
            mask = side_mask(self.rig, self.eyes, sign)
            low, high = rest(self.eyes)[mask, 2].min(), rest(self.eyes)[mask, 2].max()
            line = low + (high - low) / 3.0
            self.assertLess(np.abs(co[mask, 2] - line).max(), 0.04 * (high - low) + 1e-6)
            np.testing.assert_allclose(co[mask][:, :2], rest(self.eyes)[mask][:, :2], atol=1e-6)  # only up and down
        self.assertGreater(size, 0.0)

    def test_one_eye_each_side(self):
        left = side_mask(self.rig, self.eyes, 1.0)
        moved_l = np.linalg.norm(offsets(self.eyes, "blink_L"), axis=1)
        moved_r = np.linalg.norm(offsets(self.eyes, "blink_R"), axis=1)
        self.assertLess(moved_l[~left].max(), 1e-7)  # the character's left is +x
        self.assertGreater(moved_l[left].max(), 1e-3)
        self.assertLess(moved_r[left].max(), 1e-7)
        np.testing.assert_allclose(offsets(self.eyes, "blink_L") + offsets(self.eyes, "blink_R"),
                                   offsets(self.eyes, "blink"), atol=1e-6)

    def test_joy_closes_as_an_arc(self):
        co = rest(self.eyes) + offsets(self.eyes, "joy")
        mask = side_mask(self.rig, self.eyes, 1.0)
        x = rest(self.eyes)[mask, 0]
        middle = np.abs(x - (x.min() + x.max()) / 2.0) < 0.15 * (x.max() - x.min())
        ends = np.abs(x - (x.min() + x.max()) / 2.0) > 0.4 * (x.max() - x.min())
        self.assertGreater(co[mask][middle, 2].mean(), co[mask][ends, 2].mean() + 1e-3)

    def test_surprised_is_bigger(self):
        co = rest(self.eyes) + offsets(self.eyes, "surprised")
        mask = side_mask(self.rig, self.eyes, 1.0)
        before = np.ptp(rest(self.eyes)[mask], axis=0)
        after = np.ptp(co[mask], axis=0)
        self.assertAlmostEqual(after[0] / before[0], 1.12, places=4)
        self.assertAlmostEqual(after[2] / before[2], 1.12, places=4)


class SkinTest(unittest.TestCase):
    """pl1 (a real model) paints its eye whites on the face: the skin under each eye closes with it, fading back to
    rest a margin out; only the Body part's skin, never the hair or clothes."""

    def test_the_skin_under_the_eyes_closes_with_them(self):
        rig, objs, eyes = character()
        body = objs["Body"]
        body.modifiers.new("Armature", 'ARMATURE').object = rig
        shirt = objs["Shirt"]
        shirt.modifiers.new("Armature", 'ARMATURE').object = rig
        made = dict(eye_shapes.sculpt(rig, [eyes, body, shirt]))
        self.assertEqual(sorted(made["blink"]), ["Body", "Eyes"])
        self.assertIsNone(shirt.data.shape_keys)
        found = eye_shapes.find_eyes(rig, [eyes])
        to_arm = rig.matrix_world.inverted() @ body.matrix_world
        rest_arm = np.array([to_arm @ v.co for v in body.data.vertices])
        centre, _size = head_frame(rig)
        closed = rest_arm + offsets(body, "blink")  # the body has no transform of its own here
        inside_any = np.zeros(len(rest_arm), dtype=bool)
        for eye in found.values():
            line = eye.low[2] + (eye.high[2] - eye.low[2]) / 3.0
            inside = ((rest_arm[:, 0] > eye.low[0]) & (rest_arm[:, 0] < eye.high[0]) & (rest_arm[:, 2] > eye.low[2])
                      & (rest_arm[:, 2] < eye.high[2]) & (rest_arm[:, 1] < centre.y))
            self.assertGreater(inside.sum(), 0)
            self.assertLess(np.abs(closed[inside, 2] - line).max(), 0.05 * (eye.high[2] - eye.low[2]))
            pad = eye_shapes.MARGIN * (eye.high - eye.low)
            inside_any |= ((rest_arm[:, 0] > eye.low[0] - pad[0]) & (rest_arm[:, 0] < eye.high[0] + pad[0])
                           & (rest_arm[:, 2] > eye.low[2] - pad[2]) & (rest_arm[:, 2] < eye.high[2] + pad[2]))
        far = ~inside_any | (rest_arm[:, 1] >= centre.y)
        self.assertLess(np.abs(offsets(body, "blink")[far]).max(), 1e-7)  # the back of the head, the body below


def painted_face(rig, mouth=True):
    """A Body part: a face sheet in front of the head, UV-mapped over its whole image, the image skin-coloured with a
    dark mouth line (pl1, a real model, paints its mouth) 0.4 head below the head's centre, 0.2 head wide."""
    from bl_ui import dasktoon_rig as ui
    centre, size = head_frame(rig)
    n = 25
    us = np.linspace(0.0, 1.0, n)
    verts = [(centre.x + size * (u - 0.5) * 0.8, centre.y - 0.6 * size, centre.z + size * (-0.7 + 0.6 * v))
             for v in us for u in us]
    faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(n - 1)
             for c in range(n - 1)]
    mesh = bpy.data.meshes.new("Face")
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        i = loop.vertex_index
        layer.data[loop.index].uv = (us[i % n], us[i // n])
    res = 128
    image = bpy.data.images.new("FaceTex", res, res)
    px = np.empty((res, res, 4), np.float32)
    px[:] = (0.98, 0.9, 0.83, 1.0)
    if mouth:  # z = -0.4 head: v = 0.5; x within 0.2 head: u from 0.375 to 0.625
        px[62:66, 48:80] = (0.85, 0.35, 0.5, 1.0)  # rows are v, from the bottom
    image.pixels.foreach_set(px.ravel())
    mat = bpy.data.materials.new("Skin")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    mesh.materials.append(mat)
    obj = bpy.data.objects.new("Face", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Armature", 'ARMATURE').object = rig
    ui.add_part(rig, obj, 'BODY')
    return obj


class DrawnMouthTest(unittest.TestCase):
    """joy smiles with a mouth drawn on the face: the skin at its corners lifts, its middle stays."""

    def test_joy_lifts_the_corners(self):
        rig, _objs, eyes = character()
        face = painted_face(rig)
        mouth = eye_shapes.drawn_mouth(rig, [face, eyes], eye_shapes.find_eyes(rig, [eyes]))
        centre, size = head_frame(rig)
        self.assertIsNotNone(mouth)
        middle, half = mouth
        self.assertAlmostEqual(middle[0], centre.x, delta=0.03 * size)
        self.assertAlmostEqual(middle[2], centre.z - 0.4 * size, delta=0.03 * size)
        self.assertAlmostEqual(half, 0.1 * size, delta=0.03 * size)
        eye_shapes.sculpt(rig, [eyes, face])
        rest_arm = np.array([v.co for v in face.data.vertices])  # no transforms here
        moved = offsets(face, "joy")
        rel_x = (rest_arm[:, 0] - middle[0]) / half
        on_line = np.abs(rest_arm[:, 2] - middle[2]) < 0.03 * size
        corners = on_line & (np.abs(np.abs(rel_x) - 1.0) < 0.2)
        centre_line = on_line & (np.abs(rel_x) < 0.1)
        self.assertGreater(moved[corners, 2].min(), 0.02 * half)
        self.assertLess(np.abs(moved[centre_line, 2]).max(), 0.02 * half + 1e-7)
        np.testing.assert_allclose(moved[:, :2], 0.0, atol=1e-7)  # only up
        self.assertLess(np.abs(offsets(face, "blink")[corners]).max(), 1e-7)  # the blink leaves the mouth

    def test_a_hidden_mouth_inside_is_not_the_drawing(self):
        """pl1 (a real model) has a pink inside of the mouth behind its face: only what shows from the front counts."""
        rig, _objs, eyes = character()
        face = painted_face(rig)
        centre, size = head_frame(rig)
        n = 6
        us = np.linspace(-0.3, 0.3, n)
        verts = [(centre.x + size * u, centre.y - 0.5 * size, centre.z + size * (-0.4 + 0.2 * v))
                 for v in us for u in us]
        faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(n - 1)
                 for c in range(n - 1)]
        inside = bpy.data.meshes.new("Inside")
        inside.from_pydata(verts, [], faces)
        inside.uv_layers.new(name="UVMap")  # every UV at 0: a pink corner of its own image
        pink = bpy.data.images.new("Pink", 4, 4)
        pink.pixels.foreach_set(np.tile((0.85, 0.35, 0.5, 1.0), 16).astype(np.float32))
        mat = bpy.data.materials.new("Inside")
        mat.use_nodes = True
        mat.node_tree.nodes.new('ShaderNodeTexImage').image = pink
        inside.materials.append(mat)
        face.data.update()
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(face.data)
        bm.from_mesh(inside)  # in the Body's mesh, behind its face
        bm.to_mesh(face.data)
        bm.free()
        face.data.materials.append(mat)
        for poly in face.data.polygons[-len(faces):]:
            poly.material_index = 1
        mouth = eye_shapes.drawn_mouth(rig, [face, eyes], eye_shapes.find_eyes(rig, [eyes]))
        self.assertIsNotNone(mouth)
        self.assertAlmostEqual(mouth[1], 0.1 * size, delta=0.03 * size)

    def test_no_drawing_no_smile(self):
        rig, _objs, eyes = character()
        face = painted_face(rig, mouth=False)
        self.assertIsNone(eye_shapes.drawn_mouth(rig, [face, eyes], eye_shapes.find_eyes(rig, [eyes])))


class ExistingKeysTest(unittest.TestCase):
    def test_keys_that_move_are_kept_and_empty_ones_filled(self):
        rig, objs, eyes = character()
        eyes.shape_key_add(name="Basis", from_mix=False)
        mine = eyes.shape_key_add(name="blink", from_mix=False)
        mine.data[0].co.z += 0.01
        eyes.shape_key_add(name="happy", from_mix=False)  # empty: joy's VRM 1.0 name
        made = dict(eye_shapes.sculpt(rig, [eyes]))
        self.assertNotIn("blink", made)
        self.assertIn("happy", made)
        self.assertNotIn("joy", eyes.data.shape_keys.key_blocks)
        self.assertAlmostEqual(offsets(eyes, "blink")[0, 2], 0.01, places=6)
        self.assertGreater(np.abs(offsets(eyes, "happy")).max(), 1e-3)

    def test_sculpting_again_makes_no_second_key(self):
        rig, objs, eyes = character()
        eye_shapes.sculpt(rig, [eyes])
        eye_shapes.sculpt(rig, [eyes])
        names = [b.name for b in eyes.data.shape_keys.key_blocks]
        self.assertEqual(len(names), len(set(names)))


class NoEyesTest(unittest.TestCase):
    def test_eye_sockets_are_left_alone(self):
        rig, _objs, eyes = character(socket=True)
        self.assertEqual(eye_shapes.find_eyes(rig, [eyes]), {})
        self.assertEqual(eye_shapes.sculpt(rig, [eyes]), [])

    def test_one_eye_is_not_enough(self):
        rig, _objs, eyes = character(sides=(1.0,))
        self.assertEqual(eye_shapes.sculpt(rig, [eyes]), [])

    def test_a_bang_over_the_eyes_is_no_socket(self):
        """pl1 (a real model): the edge of the hair along the forehead crosses the eyes' outlines; only open edges
        all around an eye make a socket."""
        rig, objs, eyes = character()
        centre, size = head_frame(rig)
        n = 40
        verts = [(centre.x + size * u, centre.y - 0.75 * size, centre.z + size * (-0.1 + 0.4 * v))
                 for v in np.linspace(0, 1, n) for u in np.linspace(-0.6, 0.6, n)]
        faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(n - 1)
                 for c in range(n - 1)]
        mesh = bpy.data.meshes.new("Hair")
        mesh.from_pydata(verts, [], faces)  # its lower edge runs through both eyes
        hair = bpy.data.objects.new("Hair", mesh)
        bpy.context.scene.collection.objects.link(hair)
        hair.modifiers.new("Armature", 'ARMATURE').object = rig
        self.assertEqual(sorted(eye_shapes.find_eyes(rig, [eyes, hair])), ["LEFT", "RIGHT"])

    def test_hair_parts_and_loose_points_are_not_eyes(self):
        """filie (a real model): a lock of her hair hangs in front of an eye, and a loose vertex sits there."""
        from bl_ui import dasktoon_rig as ui
        rig, objs, eyes = character()
        lock = eyes_object(rig, name="Lock", sides=(1.0,), pieces=(("lock", 0.2, -0.1, 0.05, 0.15),))
        ui.add_part(rig, lock, 'HAIR')
        with_point = eyes_object(rig, name="Point", sides=(1.0,), pieces=())
        with_point.data.vertices.add(1)
        centre, size = head_frame(rig)
        with_point.data.vertices[0].co = (centre.x + 0.3 * size, centre.y - 0.6 * size, centre.z - 0.3 * size)
        found = eye_shapes.find_eyes(rig, [eyes, lock, with_point])
        self.assertEqual({obj.name for obj, _piece in found["LEFT"].pieces}, {"Eyes"})

    def test_hair_behind_or_big_pieces_are_not_eyes(self):
        rig, objs = rt.rigged()
        # a bang across the whole face: too wide to be an eye
        bang = eyes_object(rig, name="Bang", sides=(1.0,), pieces=(("bang", 0.0, -0.1, 0.4, 0.05),))
        self.assertEqual(eye_shapes.find_eyes(rig, [bang] + list(objs.values())), {})

    def test_the_button(self):
        rig, objs, eyes = character()
        bpy.context.view_layer.objects.active = eyes
        self.assertEqual(bpy.ops.dasktoon.sculpt_eye_expressions(), {'FINISHED'})
        self.assertIn("blink", eyes.data.shape_keys.key_blocks)
        objs["Body"].modifiers.new("Armature", 'ARMATURE').object = rig  # as Build Rig binds it
        bpy.context.view_layer.objects.active = objs["Body"]
        self.assertEqual(bpy.ops.dasktoon.sculpt_eye_expressions(), {'FINISHED'})  # any mesh of the character
        bpy.context.view_layer.objects.active = objs["Shirt"]  # not bound: no character
        self.assertFalse(bpy.ops.dasktoon.sculpt_eye_expressions.poll())


if __name__ == "__main__":
    tu.run_tests()
