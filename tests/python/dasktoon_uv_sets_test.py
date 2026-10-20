# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Game texture sets (docs/superpowers/specs/2026-10-20-dasktoon-game-texture-sets-design.md) on the regions chibi with a
hair lock (role Hair) and a material of its own colour on each part: every face in its set (Hair, Body, Face), each set
in its own square without overlaps but the mirrored limbs, islands standing upright, the face twice as sharp, sizes in
powers of two, one colour picture per set holding each material's colour, Base Color reading it, the face's own
material."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Color

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_uv_unwrap_test as ut  # noqa: E402
from bl_ui import dasktoon_rig as rig_ui  # noqa: E402
from dasktoon_paint import start  # noqa: E402
from dasktoon_rig import regions  # noqa: E402
from dasktoon_uv import sets, transfer, unwrap  # noqa: E402

COLOURS = {"Body": (0.9, 0.6, 0.5), "Shirt": (0.1, 0.25, 0.8), "Boots": (0.05, 0.05, 0.05), "Hair": (0.6, 0.1, 0.3)}
BYTE = 2.0 / 255


def character():
    rig, objs = rt.rigged()
    head = rig.matrix_world @ rig.data.bones["Head"].tail_local
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.03, depth=0.3,
                                       location=(head.x + 0.06, head.y + 0.06, head.z - 0.12))
    hair = bpy.context.active_object
    hair.name = "Hair"
    rig_ui.add_part(rig, hair, 'HAIR')
    meshes = [objs["Body"], objs["Shirt"], objs["Boots"], hair]
    for obj in meshes:
        mat = bpy.data.materials.new(obj.name)
        start.anime_node(mat).inputs["Base Color"].default_value = (*COLOURS[obj.name], 1.0)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return rig, meshes


def skin_faces(obj, labels):
    """The head faces of the loose piece that also has faces below the head (the skin reaching the neck)."""
    from dasktoon_uv import seams
    mesh = obj.data
    pieces = seams.loose_pieces(mesh)[[p.vertices[0] for p in mesh.polygons]]
    head = labels == regions.REGIONS.index('HEAD')
    reaching = {piece for piece in np.unique(pieces[head]) if (~head[pieces == piece]).any()}
    return np.nonzero(head & np.isin(pieces, list(reaching)))[0]


def srgb(rgb):
    return np.array(Color(rgb).from_scene_linear_to_srgb())


class SetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.meshes = character()
        cls.body, cls.shirt, cls.boots, cls.hair = cls.meshes
        cls.result = unwrap.unwrap(bpy.context, cls.meshes, cls.rig, tight=False, sets=True)
        cls.atlases = sets.make_atlases(cls.meshes, cls.rig, cls.result)
        transfer.transfer(cls.meshes, cls.result.old, cls.result.mirrored, exclude=set(cls.atlases.values()))

    def set_of(self, obj):
        return self.result.sets[obj]

    def test_every_face_is_in_its_set(self):
        hair, body, face = (sets.NAMES.index(name) for name in ('HAIR', 'BODY', 'FACE'))
        self.assertTrue((self.set_of(self.hair) == hair).all())
        self.assertTrue((self.set_of(self.shirt) == body).all())
        labels = self.result.labels[self.body]
        head = labels == regions.REGIONS.index('HEAD')
        skin = skin_faces(self.body, labels)
        self.assertTrue(len(skin))
        self.assertTrue((self.set_of(self.body)[skin] == face).all())  # the head's skin
        self.assertTrue(np.isin(self.set_of(self.body)[head], [face, hair]).all())  # its locks and ears: hair
        self.assertTrue((self.set_of(self.body)[~head] == body).all())

    def test_each_set_lies_in_its_square_without_overlaps(self):
        for index in range(len(sets.NAMES)):
            tris = []
            for obj in self.meshes:
                mirrored = {f for (o, f) in self.result.mirrored if o == obj}
                chosen = [f for f in np.nonzero(self.set_of(obj) == index)[0].tolist() if f not in mirrored]
                tris += ut.triangles(obj, chosen)
            if not tris:
                continue
            uv = np.concatenate([t[0] for t in tris])
            self.assertTrue((uv >= -1e-4).all() and (uv <= 1 + 1e-4).all(), sets.NAMES[index])
            counts = ut.coverage(tris)
            self.assertLess((counts > 1).sum() / max((counts > 0).sum(), 1), 0.01, sets.NAMES[index])

    def test_the_islands_stand_upright(self):
        upright = total = 0
        for gradient in sets.island_up_gradients(self.body, self.result.labels[self.body], self.rig):
            if np.linalg.norm(gradient) < 1e-6:
                continue
            total += 1
            upright += gradient[1] > abs(gradient[0])
        self.assertGreater(total, 3)
        self.assertGreaterEqual(upright / total, 0.8)

    def test_the_face_is_twice_as_sharp_as_the_body(self):
        def density(name):
            index = sets.NAMES.index(name)
            uv_area = world_area = 0.0
            for obj in self.meshes:
                for uv, world in ut.triangles(obj, np.nonzero(self.set_of(obj) == index)[0].tolist()):
                    uv_area += ut.area2(uv)
                    world_area += ut.area3(world)
            return (uv_area / world_area) ** 0.5 * self.result.sizes[name]
        self.assertGreaterEqual(density('FACE'), 1.9 * self.result.density)
        self.assertGreaterEqual(density('BODY'), 0.95 * self.result.density)
        self.assertGreaterEqual(density('HAIR'), 0.95 * self.result.density)

    def test_the_sizes_are_powers_of_two_up_to_2048(self):
        sizes = list(self.result.sizes.values())
        self.assertTrue(all(size in (256, 512, 1024, 2048) for size in sizes), sizes)
        self.assertIn(2048, sizes)

    def test_each_set_has_one_colour_picture_with_its_materials_colours(self):
        self.assertEqual(set(self.atlases), {'HAIR', 'BODY', 'FACE'})
        for name, image in self.atlases.items():
            self.assertEqual(tuple(image.size), (self.result.sizes[name],) * 2)
        for obj in (self.shirt, self.hair):
            image = self.atlases['HAIR' if obj is self.hair else 'BODY']
            size = image.size[0]
            px = np.empty(size * size * 4, np.float32)
            image.pixels.foreach_get(px)
            px = px.reshape(size, size, 4)
            uv = ut.uvs(obj)
            poly = obj.data.polygons[len(obj.data.polygons) // 2]
            centre = uv[list(poly.loop_indices)].mean(axis=0)
            np.testing.assert_allclose(transfer._sample(px, centre[None])[0][:3], srgb(COLOURS[obj.name]),
                                       atol=BYTE, err_msg=obj.name)

    def test_base_color_reads_the_set_picture(self):
        for obj in self.meshes:
            for slot in obj.material_slots:
                socket = start.anime_node(slot.material).inputs["Base Color"]
                self.assertTrue(socket.is_linked, slot.material.name)
                self.assertIn(socket.links[0].from_node.image, set(self.atlases.values()), slot.material.name)

    def test_the_face_has_a_material_of_its_own(self):
        names = [slot.material.name for slot in self.body.material_slots]
        self.assertIn("Body Face", names)
        face = sets.NAMES.index('FACE')
        for poly in self.body.data.polygons:
            material = self.body.material_slots[poly.material_index].material.name
            self.assertEqual(material == "Body Face", self.set_of(self.body)[poly.index] == face)


class HeadPiecesTest(unittest.TestCase):
    def test_hair_in_the_body_mesh_goes_to_hair_and_eye_pieces_to_the_face(self):
        # tdt's hair is modelled in its body mesh (its locks Recognize made rigid accessories): it filled the face set.
        import bmesh
        import dasktoon_expressions_eyes_test as et
        rig, objs, eyes = et.character()
        body = objs["Body"]
        centre, size = et.head_frame(rig)
        bm = bmesh.new()
        bm.from_mesh(body.data)
        cap = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=size * 0.7,
                                        matrix=__import__("mathutils").Matrix.Translation(
                                            centre + __import__("mathutils").Vector((0, size * 0.1, size * 0.45))))
        cap_verts = {v.index for v in cap["verts"]}
        bm.to_mesh(body.data)
        bm.free()
        body.data.update()
        from dasktoon_uv import seams
        labels = seams.face_labels(bpy.context, body, rig)
        found = sets.face_sets(body, rig, labels)
        cap_faces = [p.index for p in body.data.polygons if set(p.vertices) <= cap_verts]
        self.assertTrue(cap_faces)
        self.assertTrue((found[cap_faces] == sets.NAMES.index('HAIR')).all())
        skin = skin_faces(body, labels)
        self.assertTrue(len(skin))
        self.assertTrue((found[skin] == sets.NAMES.index('FACE')).all())
        eye_labels = seams.face_labels(bpy.context, eyes, rig)
        self.assertTrue((sets.face_sets(eyes, rig, eye_labels) == sets.NAMES.index('FACE')).all())


if __name__ == "__main__":
    tu.run_tests()
