# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Body regions and locks on the head (docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md): which part of
the body each vertex of the Body and Clothing parts belongs to, the loose pieces attached to the head and the locks
they group into."""

import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import parts as rig_parts, regions, skeleton  # noqa: E402

ANGLE = math.radians(50.0)
ARM_START = Vector((0.12, 0.0, 1.42))
ARM_END = ARM_START + Vector((math.cos(ANGLE), 0.0, -math.sin(ANGLE))) * 0.62


def merged(name, pieces):
    verts, faces = [], []
    for piece_verts, piece_faces in pieces:
        faces += [tuple(i + len(verts) for i in face) for face in piece_faces]
        verts += piece_verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mirrored(point):
    return Vector((-point.x, point.y, point.z))


def character(reset=True):
    """A chibi 2 tall in A-pose: one Body mesh of loose pieces (torso, a big head, arms 50 degrees down, legs, a rabbit
    ear beside each side of the head hanging down to the shoulders, a hair lock in front of the right shoulder); a
    Shirt with a strap on the chest (a loose piece of the shirt); Boots wider than the legs, not touching. The skeleton
    is fitted to them. Returns (rig, {name: object}, parts). `reset` starts from an empty file (not in a window: the
    screenshot tool clears the scene itself)."""
    if reset:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    tube = st.tube
    body = [tube((0, 0, 0.88), (0, 0, 1.46), 0.18), tube((0, 0, 1.46), (0, 0, 2.0), 0.3)]
    for s in (1.0, -1.0):
        body.append(tube(tuple(ARM_START * Vector((s, 1, 1))), tuple(ARM_END * Vector((s, 1, 1))), 0.05))
        body.append(tube((0.08 * s, 0, 0.95), (0.09 * s, 0, 0.0), 0.07))
        body.append(tube((0.34 * s, 0.08, 1.85), (0.35 * s, 0.12, 1.42), 0.04))  # rabbit ear
    body.append(tube((-0.2, -0.25, 1.75), (-0.22, -0.2, 1.35), 0.03))  # hair lock
    shirt_tube = st.tube((0, 0, 1.40), (0, 0, 0.9), 0.2)
    strap = tube((0.1, -0.215, 1.38), (0.1, -0.215, 1.0), 0.012)
    objs = {"Body": merged("Body", body), "Shirt": merged("Shirt", [shirt_tube, strap]),
            "Boots": merged("Boots", [tube((s * 0.09, 0, 0.0), (s * 0.09, 0, 0.25), 0.085) for s in (1.0, -1.0)])}
    rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
    meshes = list(objs.values())
    skeleton.fit(bpy.context, rig, meshes, body=meshes)
    parts = [rig_parts.Part("Body", objs["Body"], 'BODY'), rig_parts.Part("Shirt", objs["Shirt"], 'CLOTHING'),
             rig_parts.Part("Boots", objs["Boots"], 'CLOTHING')]
    return rig, objs, parts


def nearest(obj, point):
    world, _edges = rig_parts.mesh_arrays(obj)
    return int(np.argmin(np.linalg.norm(world - np.array(point), axis=1)))


class RecognizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.parts = character()
        cls.found = regions.analyse(bpy.context, cls.rig, cls.parts)

    def region_at(self, name, point):
        obj = self.objs[name]
        vertices, labels = self.found.objects[obj]
        index = nearest(obj, point)
        return regions.REGIONS[labels[list(vertices).index(index)]]

    def test_regions_of_the_body_and_clothing(self):
        middle_arm = ARM_START + (ARM_END - ARM_START) * 0.5
        expected = [
            ("Body", ARM_END, 'ARM_L'), ("Body", middle_arm, 'ARM_L'), ("Body", mirrored(middle_arm), 'ARM_R'),
            ("Body", (0, -0.18, 1.15), 'TORSO'), ("Body", (0, -0.3, 1.75), 'HEAD'),
            ("Body", (0.085, 0, 0.5), 'LEG_L'), ("Body", (-0.085, 0, 0.5), 'LEG_R'),
            ("Body", (0.38, 0.1, 1.6), 'HEAD'), ("Body", (-0.38, 0.1, 1.6), 'HEAD'),  # the ears
            ("Body", (-0.21, -0.25, 1.4), 'HEAD'),  # the hair lock, in front of the right arm
            ("Shirt", (0.1, -0.227, 1.2), 'TORSO'), ("Shirt", (0.2, 0.0, 1.1), 'TORSO'),  # the strap, the side
            ("Boots", (0.175, 0.0, 0.1), 'LEG_L'), ("Boots", (-0.175, 0.0, 0.1), 'LEG_R'),
        ]
        for name, point, region in expected:
            self.assertEqual(self.region_at(name, point), region, (name, tuple(point)))

    def test_the_head_does_not_reach_down_over_the_chest(self):
        """Measured from a head as wide as itself all the way down, the chibi's big head took the top of its chest,
        its collar and the strap on it."""
        for name, point in (("Body", (0, -0.18, 1.42)), ("Shirt", (0, -0.2, 1.39)), ("Shirt", (0.1, -0.227, 1.37))):
            self.assertEqual(self.region_at(name, point), 'TORSO', (name, point))

    def test_locks_are_the_pieces_hanging_from_the_head(self):
        locks = {name: (obj.name, len(vertices)) for name, obj, vertices in self.found.locks}
        ear, hair = len(st.tube((0, 0, 0), (0, 0, 1), 0.04)[0]), len(st.tube((0, 0, 0), (0, 0, 1), 0.03)[0])
        # Top to bottom on each side: the right ear (top 1.85) before the hair lock (top 1.75).
        self.assertEqual(locks, {"Lock L1": ("Body", ear), "Lock R1": ("Body", ear), "Lock R2": ("Body", hair)})

    def test_half_widths_from_the_front(self):
        half = self.found.half
        self.assertAlmostEqual(half["LeftUpperArm"], 0.05, delta=0.015)
        self.assertAlmostEqual(half["RightHand"], half["LeftUpperArm"], delta=1e-6)
        self.assertAlmostEqual(half["Chest"], 0.2, delta=0.03)
        self.assertLessEqual(half["UpperChest"], max(half["Hips"], half["Spine"], half["Chest"]) + 1e-6)
        self.assertGreater(half["Head"], 0.25)

    def test_pieces_close_together_make_one_lock(self):
        world = np.array([(0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.004, 0.0, 1.0), (0.5, 0.0, 0.5)])
        pieces = [np.array([0, 1]), np.array([2]), np.array([3])]  # 2 is 4 mm from 1; the gap is 0.005 x 2
        found = regions.locks(pieces, world, 2.0, 0.0)
        self.assertEqual({name: sorted(v.tolist()) for name, v in found}, {"Lock M1": [0, 1, 2], "Lock L1": [3]})


def rigged(reset=True):
    """The character with its parts in the rig (as the interface adds them)."""
    from bl_ui import dasktoon_rig as ui
    rig, objs, _parts = character(reset)
    ui.add_part(rig, objs["Body"], 'BODY')
    ui.add_part(rig, objs["Shirt"], 'CLOTHING')
    ui.add_part(rig, objs["Boots"], 'CLOTHING')
    return rig, objs


class LayerTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.obj = st.box("Box", (0, 0, 0), (1, 1, 1))

    def test_write_then_read(self):
        head, torso, arm, leg = (regions.REGIONS.index(r) for r in ('HEAD', 'TORSO', 'ARM_L', 'LEG_R'))
        regions.write(self.obj, np.array([0, 1, 2, 3]), np.array([head, torso, arm, leg]))
        self.assertEqual(regions.read(self.obj).tolist(), [head, torso, arm, leg] + [regions.AUTO] * 4)
        layers = self.obj.data.color_attributes
        self.assertEqual((layers.active_color_name, layers.default_color_name), ("", ""))

    def test_the_mesh_keeps_its_own_colors(self):
        layers = self.obj.data.color_attributes
        layers.new("Col", 'BYTE_COLOR', 'CORNER')
        regions.write(self.obj, np.array([0]), np.array([0]))
        self.assertEqual((layers.active_color_name, layers.default_color_name), ("Col", "Col"))

    def test_painted_colors_snap_to_the_nearest_region(self):
        regions.write(self.obj, np.arange(8), np.zeros(8, np.int64))
        layer = self.obj.data.color_attributes[regions.LAYER]
        blue = regions.COLORS['TORSO']
        layer.data[0].color_srgb = (0.4, 0.6, 0.85, 1.0)  # a soft brush between head yellow and torso blue, near blue
        layer.data[1].color_srgb = (0.97, 0.98, 0.95, 1.0)  # unpainted: white
        layer.data[2].color_srgb = (0.02, 0.0, 0.03, 1.0)  # black
        layer.data[3].color_srgb = (*blue, 1.0)
        found = regions.read(self.obj)
        torso = regions.REGIONS.index('TORSO')
        self.assertEqual(found[:4].tolist(), [torso, regions.AUTO, regions.AUTO, torso])

    def test_no_layer_is_all_automatic(self):
        self.assertEqual(set(regions.read(self.obj).tolist()), {regions.AUTO})


class RecognizePartsTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs = rigged()

    def locks(self):
        return {part.name: part for part in self.rig.data.dasktoon_rig.parts if part.made_by_recognize}

    def test_regions_are_written_and_locks_are_parts(self):
        regions.recognize(bpy.context, self.rig)
        body = self.objs["Body"]
        found = regions.read(body)
        self.assertEqual(regions.REGIONS[found[nearest(body, ARM_END)]], 'ARM_L')
        self.assertEqual(regions.REGIONS[found[nearest(body, (0.38, 0.1, 1.6))]], 'HEAD')
        locks = self.locks()
        self.assertEqual(sorted(locks), ["Lock L1", "Lock R1", "Lock R2"])
        ear = locks["Lock L1"]
        self.assertEqual((ear.object, ear.scope, ear.vertex_group, ear.role, ear.bone),
                         (body, 'VERTEX_GROUP', "DT_Lock L1", 'ACCESSORY', "Head"))
        vertices = rig_parts.part_vertices(ear)
        self.assertEqual(nearest(body, (0.38, 0.1, 1.6)) in set(vertices.tolist()), True)

    def test_recognize_again_keeps_what_you_chose(self):
        regions.recognize(bpy.context, self.rig)
        hair = self.locks()["Lock R2"]
        hair.role, hair.stiffness = 'HAIR', 2.5
        regions.recognize(bpy.context, self.rig)
        locks = self.locks()
        self.assertEqual(sorted(locks), ["Lock L1", "Lock R1", "Lock R2"])
        self.assertEqual((locks["Lock R2"].role, locks["Lock R2"].stiffness), ('HAIR', 2.5))
        self.assertEqual(locks["Lock R1"].role, 'ACCESSORY')
        groups = sorted(g.name for g in self.objs["Body"].vertex_groups if g.name.startswith("DT_Lock"))
        self.assertEqual(groups, ["DT_Lock L1", "DT_Lock R1", "DT_Lock R2"])

    def test_recognize_again_with_locks_on_two_meshes(self):
        """Locks on the Body and on a Clothing mesh (a lock of hair hanging behind the head): recognized again, each is
        made again once."""
        from bl_ui import dasktoon_rig as ui
        hair = merged("Hair", [st.tube((0, 0.32, 1.95), (0, 0.36, 1.2), 0.05)])
        ui.add_part(self.rig, hair, 'CLOTHING')
        regions.recognize(bpy.context, self.rig)
        first = sorted((part.name, part.object.name) for part in self.locks().values())
        self.assertIn("Hair", [obj for _name, obj in first])
        regions.recognize(bpy.context, self.rig)
        self.assertEqual(sorted((part.name, part.object.name) for part in self.locks().values()), first)

    def test_parts_you_made_are_left_alone(self):
        from bl_ui import dasktoon_rig as ui
        body = self.objs["Body"]
        world, edges = rig_parts.mesh_arrays(body)
        ear = [p for p in rig_parts.pieces(edges, np.arange(len(world))) if nearest(body, (-0.38, 0.1, 1.6)) in p][0]
        group = body.vertex_groups.new(name="My Ear")
        group.add(ear.tolist(), 1.0, 'REPLACE')
        ui.add_part(self.rig, body, 'HAIR', name="My Ear", scope='VERTEX_GROUP', vertex_group="My Ear")
        regions.recognize(bpy.context, self.rig)
        self.assertEqual(sorted(self.locks()), ["Lock L1", "Lock R1"])  # the right side has only the hair lock now
        self.assertIn("My Ear", [part.name for part in self.rig.data.dasktoon_rig.parts])


def piece_at(obj, point):
    """The loose piece of obj's mesh that has the vertex nearest `point`."""
    world, edges = rig_parts.mesh_arrays(obj)
    index = nearest(obj, point)
    return next(p for p in rig_parts.pieces(edges, np.arange(len(world))) if index in p)


def limb_weight(rig, obj, vertices, region):
    from dasktoon_rig import weights
    names = regions.region_bones(rig)[region]
    return weights.read(obj, names)[vertices].sum(axis=1)


class LockFromSelectionTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs = rigged()
        regions.recognize(bpy.context, self.rig)
        self.body = self.objs["Body"]
        self.ear = piece_at(self.body, (-0.38, 0.1, 1.6))
        self.hair = piece_at(self.body, (-0.21, -0.25, 1.4))

    def locks(self):
        """{name: (made by Recognize, vertex set)} of the locks."""
        return {part.name: (part.made_by_recognize, set(rig_parts.part_vertices(part).tolist()))
                for part in self.rig.data.dasktoon_rig.parts if part.vertex_group.startswith("DT_Lock")}

    def test_merge_then_split(self):
        # One vertex of the right ear and one of the hair lock: both whole pieces become one lock of yours.
        part = regions.lock_from_selection(self.rig, self.body, [int(self.ear[0]), int(self.hair[3])])
        self.assertEqual(part.name, "Lock R1")
        locks = self.locks()
        self.assertEqual(sorted(locks), ["Lock L1", "Lock R1"])  # the two locks it emptied are gone
        self.assertEqual(locks["Lock R1"], (False, set(self.ear.tolist()) | set(self.hair.tolist())))
        self.assertEqual(sorted(g.name for g in self.body.vertex_groups if g.name.startswith("DT_Lock")),
                         ["DT_Lock L1", "DT_Lock R1"])
        # Then the hair lock alone: split off.
        regions.lock_from_selection(self.rig, self.body, [int(self.hair[0])])
        locks = self.locks()
        self.assertEqual(locks["Lock R1"][1], set(self.ear.tolist()))
        self.assertEqual(locks["Lock R2"], (False, set(self.hair.tolist())))
        # Recognize again leaves your locks alone and makes no lock of their pieces.
        regions.recognize(bpy.context, self.rig)
        self.assertEqual(sorted(self.locks()), ["Lock L1", "Lock R1", "Lock R2"])
        self.assertEqual(regions.REGIONS[regions.read(self.body)[self.hair[0]]], 'HEAD')

    def test_recognized_locks_take_free_names(self):
        """A lock you made before Recognize ever ran keeps its name; the locks Recognize makes take other names."""
        rig, objs = rigged()
        body = objs["Body"]
        mine = regions.lock_from_selection(rig, body, [int(piece_at(body, (-0.21, -0.25, 1.4))[0])])
        self.assertEqual(mine.name, "Lock R1")
        regions.recognize(bpy.context, rig)
        names = [part.name for part in rig.data.dasktoon_rig.parts]
        self.assertEqual(len(names), len(set(names)), names)
        self.assertEqual(sorted(n for n in names if n.startswith("Lock")), ["Lock L1", "Lock R1", "Lock R2"])

    def test_nothing_selected(self):
        with self.assertRaises(rig_parts.PartError):
            regions.lock_from_selection(self.rig, self.body, [])


def tube_mesh(a, b, radius, rings, segments=12):
    """(world vertices, edges) of a tube from a to b."""
    verts, faces = st.tube(a, b, radius, rings=rings, segments=segments)
    edges = set()
    for face in faces:
        for i in range(len(face)):
            edge = (face[i], face[(i + 1) % len(face)])
            edges.add((min(edge), max(edge)))
    return np.array(verts, float), np.array(sorted(edges))


class SideTest(unittest.TestCase):
    def test_a_piece_on_one_leg_crossing_the_middle_is_that_leg_only(self):
        """lr_shape's leg warmer, modelled for the left leg and mirrored, reaches 8 mm past the middle on its inner
        side: that vertex was the right leg's, and the warmer tore 35 to 47 cm whenever the legs parted."""
        rig, objs, parts = character()
        warmer = merged("Warmer", [st.tube((0.09, 0.0, 0.1), (0.09, 0.0, 0.35), 0.095, rings=6, segments=16)])
        found = regions.analyse(bpy.context, rig, parts + [rig_parts.Part("Warmer", warmer, 'CLOTHING')])
        world, _edges = rig_parts.mesh_arrays(warmer)
        self.assertTrue((world[:, 0] < 0.0).any())  # it does cross the middle
        _vertices, labels = found.objects[warmer]
        self.assertEqual({regions.REGIONS[k] for k in labels.tolist()}, {"LEG_L"})

    def test_twin_tails_of_one_piece_with_the_hair_stay_on_the_head(self):
        """RG2 and RGforGame (real models, T-pose): the hair, the ears and the twin tails are one piece; the tips of
        the twin tails hung near the hands and went to the arms, so lifting an arm dragged them along. A piece lying
        wholly above the shoulders with only a few vertices of an arm is the head's."""
        bpy.ops.wm.read_factory_settings(use_empty=True)
        level = [(0.12, 0.0, 1.4), (0.36, 0.0, 1.4), (0.62, 0.0, 1.4)]
        body = st.polyline_chibi(level, st.CentreLineTest.LEG)
        pieces = [st.tube((3.0, 0.5, 1.5), (3.0, 0.5, 2.05), 0.32)]  # the cap, round the head
        pieces += [st.tube((3.0 + s * 0.33, 0.55, 1.95), (3.0 + s * 0.5, 0.55, 1.5), 0.04) for s in (1.0, -1.0)]
        verts, faces, firsts = [], [], []
        for piece_verts, piece_faces in pieces:
            firsts.append(len(verts))
            faces += [tuple(i + len(verts) for i in face) for face in piece_faces]
            verts += piece_verts
        mesh = bpy.data.meshes.new("Hair")
        mesh.from_pydata(verts, [(firsts[0], firsts[1]), (firsts[0], firsts[2])], faces)  # one piece
        hair = bpy.data.objects.new("Hair", mesh)
        bpy.context.scene.collection.objects.link(hair)
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        skeleton.fit(bpy.context, rig, [body, hair], body=[body, hair], skin=[body])
        found = regions.analyse(bpy.context, rig, [rig_parts.Part("Body", body, 'BODY'),
                                                   rig_parts.Part("Hair", hair, 'CLOTHING')])
        _vertices, labels = found.objects[hair]
        self.assertEqual({regions.REGIONS[k] for k in labels.tolist()}, {"HEAD"})
        _vertices, labels = found.objects[body]
        self.assertIn(regions.REGIONS.index('ARM_L'), labels)  # the arms stay arms

    def test_a_piece_on_both_legs_keeps_both(self):
        _vertices, labels = regions.analyse(bpy.context, *character()[::2]).objects[bpy.data.objects["Body"]]
        self.assertIn(regions.REGIONS.index('LEG_L'), labels)
        self.assertIn(regions.REGIONS.index('LEG_R'), labels)


class KeepTest(unittest.TestCase):
    """How much of its weight each bone of a limb keeps on a vertex (rig regions spec 5, made more accurate after the
    tears the real models showed in the test poses): all of it on the limb, fading along the mesh into the region next
    to it over BAND of the height, none on the head or on a piece apart."""

    @classmethod
    def setUpClass(cls):
        cls.rig, cls.objs, cls.parts = character()

    def test_the_torso_next_to_a_leg_fades(self):
        world, edges = tube_mesh((0.09, 0.0, 0.6), (0.09, 0.0, 1.4), 0.07, rings=160)  # rings 5 mm apart
        torso, leg = regions.REGIONS.index('TORSO'), regions.REGIONS.index('LEG_L')
        labelled = np.where(world[:, 2] < 0.9975, leg, torso).astype(np.int8)
        band = 0.1
        keep = regions.keep_factors(self.rig, world, labelled, edges, band)["LeftUpperLeg"]
        z = world[:, 2]
        self.assertTrue(np.all(keep[labelled == leg] == 1.0))
        rings = sorted(set(np.round(z[labelled == torso], 6)))
        values = [keep[np.isclose(z, ring)].mean() for ring in rings]
        self.assertGreater(values[0], 0.9)  # next to the leg: hardly anything taken
        self.assertLess(keep[z > rings[0] + band + 0.006].max(), 1e-6)  # past the band: nothing
        self.assertTrue(all(b <= a + 1e-9 for a, b in zip(values, values[1:])))  # fading, never coming back
        self.assertLess(np.abs(np.diff([1.0] + values)).max(), 0.1)  # no ring takes a big step: no tear

    def test_nothing_on_the_head_or_a_piece_apart(self):
        world, edges = tube_mesh((0.09, 0.0, 0.6), (0.09, 0.0, 1.4), 0.07, rings=80)
        apart, apart_edges = tube_mesh((0.3, 0.0, 1.0), (0.3, 0.0, 1.2), 0.05, rings=10)
        joined = np.concatenate([world, apart])
        edges = np.concatenate([edges, apart_edges + len(world)])
        head, leg = regions.REGIONS.index('HEAD'), regions.REGIONS.index('LEG_L')
        labelled = np.concatenate([np.where(world[:, 2] < 1.0, leg, head),
                                   np.full(len(apart), regions.REGIONS.index('TORSO'))]).astype(np.int8)
        keep = regions.keep_factors(self.rig, joined, labelled, edges, 0.1)["LeftUpperLeg"]
        self.assertEqual(keep[len(world):].max(), 0.0)  # the piece apart
        self.assertEqual(keep[:len(world)][world[:, 2] > 1.0].max(), 0.0)  # the head

    def test_the_shoulder_keeps_its_weight_about_its_own_length(self):
        """The shoulder bone's reach comes from its own length, not from how wide the arm looks from the front (thin on
        lr_shape, whose sleeves are meshes of their own: the shoulder lost its weight 7 cm away)."""
        from dasktoon_rig import chains
        head, tail = rig_parts.bone_segment(self.rig, "LeftShoulder")
        length = float(np.linalg.norm(tail - head))
        world, edges = tube_mesh((0.0, 0.0, 0.9), (0.0, 0.0, 1.45), 0.18, rings=40)
        labelled = np.full(len(world), regions.REGIONS.index('TORSO'), np.int8)
        keep = regions.keep_factors(self.rig, world, labelled, edges, 0.1)["LeftShoulder"]
        near = chains.segment_distance(world, head, tail)
        self.assertGreater(keep[near < 0.6 * length].min(), 0.99)
        self.assertLess(keep[near > 1.3 * length].max(), 1e-6)

    def test_the_head_keeps_its_weight_on_the_head_fading_into_the_torso(self):
        """As a limb's bones do: a strap on the chest, a piece of the shirt, saw the head bone alone through the
        collar and Bone Heat gave it the head's weight; it turned with the head."""
        world, edges = tube_mesh((0.0, 0.0, 1.0), (0.0, 0.0, 1.8), 0.07, rings=160)
        strap, strap_edges = tube_mesh((0.0, -0.25, 1.0), (0.0, -0.25, 1.3), 0.02, rings=10)
        joined, edges = np.concatenate([world, strap]), np.concatenate([edges, strap_edges + len(world)])
        head, torso = regions.REGIONS.index('HEAD'), regions.REGIONS.index('TORSO')
        labelled = np.concatenate([np.where(world[:, 2] > 1.4025, head, torso),
                                   np.full(len(strap), torso)]).astype(np.int8)
        band = 0.1
        keep = regions.keep_factors(self.rig, joined, labelled, edges, band)["Head"]
        z = joined[:, 2]
        self.assertTrue(np.all(keep[labelled == head] == 1.0))
        below = keep[:len(world)][(z[:len(world)] < 1.4025) & (z[:len(world)] > 1.39)]
        self.assertGreater(below.min(), 0.9)  # next to the head: hardly anything taken
        self.assertLess(keep[:len(world)][z[:len(world)] < 1.4 - band - 0.006].max(), 1e-6)
        self.assertEqual(keep[len(world):].max(), 0.0)  # the strap


class GiveUpTest(unittest.TestCase):
    def test_a_torso_vertex_gives_what_it_loses_to_the_trunk(self):
        """The back of tdt's collar: Bone Heat gave it the shoulder and the arm, the limit took them, and the head, the
        one other bone it had, got all of it: the collar turned with the head."""
        from dasktoon_rig import build, weights
        rig, objs, parts = character()
        build.build(bpy.context, rig, parts)
        body = objs["Body"]
        torso = piece_at(body, (0, -0.18, 1.15))
        world, _edges = rig_parts.mesh_arrays(body)
        vertex = int(torso[np.argmin(np.linalg.norm(world[torso] - np.array((0.0, 0.18, 1.2)), axis=1))])  # the back
        names = ["RightLowerArm", "Head"]
        weights.clear(body, [vertex], [b.name for b in rig.data.bones if b.use_deform])
        weights.write(body, [vertex], names, np.array([[0.7, 0.3]]))
        regions.restrict(bpy.context, rig, parts, build.ownership(parts))
        after = weights.read(body, ["Head", "RightLowerArm"] + list(regions.TRUNK))[vertex]
        self.assertLessEqual(after[0], 0.3 + 1e-6)  # the head gets nothing more (far from it, it keeps nothing)
        self.assertAlmostEqual(after[1], 0.0, places=6)
        self.assertAlmostEqual(after[0] + after[2:].sum(), 1.0, places=3)  # the rest went to the trunk


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dasktoon_rig import build
        cls.rig, cls.objs, cls.parts = character()
        cls.result = build.build(bpy.context, cls.rig, cls.parts)

    def test_lifting_an_arm_leaves_the_ears_locks_and_straps(self):
        body, shirt = self.objs["Body"], self.objs["Shirt"]
        for region, obj, point in (('ARM_L', body, (0.38, 0.1, 1.6)), ('ARM_R', body, (-0.38, 0.1, 1.6)),
                                   ('ARM_R', body, (-0.21, -0.25, 1.4)), ('ARM_L', shirt, (0.1, -0.227, 1.2))):
            piece = piece_at(obj, point)
            self.assertEqual(limb_weight(self.rig, obj, piece, region).max(), 0.0, (region, obj.name, point))
            from dasktoon_rig import weights
            shoulder = ("Left" if region == 'ARM_L' else "Right") + "Shoulder"
            self.assertEqual(weights.read(obj, [shoulder])[piece].max(), 0.0, (shoulder, obj.name, point))

    def test_a_strap_on_the_chest_does_not_follow_the_head(self):
        from dasktoon_rig import weights
        shirt = self.objs["Shirt"]
        strap = piece_at(shirt, (0.1, -0.227, 1.2))
        self.assertLess(weights.read(shirt, ["Head"])[strap].max(), 1e-6)

    def test_arms_and_boots_keep_their_limbs(self):
        body, boots = self.objs["Body"], self.objs["Boots"]
        arm = piece_at(body, ARM_END)
        world, _edges = rig_parts.mesh_arrays(body)
        axis = np.array(ARM_END - ARM_START)
        along = (world[arm] - np.array(ARM_START)) @ axis / (axis @ axis)
        outer = arm[along > 0.5]  # the start of the tube is inside the torso
        self.assertGreater(limb_weight(self.rig, body, outer, 'ARM_L').mean(), 0.9)
        boot = piece_at(boots, (-0.175, 0.0, 0.1))
        self.assertGreater(limb_weight(self.rig, boots, boot, 'LEG_R').mean(), 0.9)

    def test_what_an_arm_gives_up_goes_to_the_torso(self):
        """Bone Heat gives the slim waist of the chibi to the forearm hanging beside it (nearer than the spine): keeping
        the arm to its region takes that weight away, and the torso gets it; making what is left add up to 1 would give
        it back to the arm (the Check of the auto rig found the waist torn when the arms go up)."""
        body = self.objs["Body"]
        torso = piece_at(body, (0, -0.18, 1.15))
        world, _edges = rig_parts.mesh_arrays(body)
        waist = torso[world[torso, 2] < 1.2]  # well below the shoulders
        for region in ('ARM_L', 'ARM_R'):
            self.assertLess(limb_weight(self.rig, body, waist, region).max(), 0.1, region)

    def test_painted_regions_win(self):
        from dasktoon_rig import build
        body = self.objs["Body"]
        arm = piece_at(body, ARM_END)
        regions.write(body, arm, np.full(len(arm), regions.REGIONS.index('TORSO')))
        try:
            build.build(bpy.context, self.rig, self.parts)
            tip = nearest(body, ARM_END)
            self.assertEqual(limb_weight(self.rig, body, [tip], 'ARM_L')[0], 0.0)
        finally:
            body.data.color_attributes.remove(body.data.color_attributes[regions.LAYER])
            build.build(bpy.context, self.rig, self.parts)


class BuildButtonTest(unittest.TestCase):
    def test_build_recognizes_first_when_it_never_did(self):
        rig, objs = rigged()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj == rig)
        bpy.context.view_layer.objects.active = rig
        self.assertEqual(bpy.ops.dasktoon.rig_build(), {'FINISHED'})
        self.assertIsNotNone(objs["Body"].data.color_attributes.get(regions.LAYER))
        locks = sorted(part.name for part in rig.data.dasktoon_rig.parts if part.made_by_recognize)
        self.assertEqual(locks, ["Lock L1", "Lock R1", "Lock R2"])
        from dasktoon_rig import weights
        ear = piece_at(objs["Body"], (0.38, 0.1, 1.6))
        self.assertEqual(set(weights.read(objs["Body"], ["Head"])[ear, 0].round(6).tolist()), {1.0})
        # A second Build keeps what is there (painted regions, the locks and their roles).
        hair = next(part for part in rig.data.dasktoon_rig.parts if part.name == "Lock R2")
        hair.role = 'HAIR'
        self.assertEqual(bpy.ops.dasktoon.rig_build(), {'FINISHED'})
        self.assertEqual(next(p for p in rig.data.dasktoon_rig.parts if p.name == "Lock R2").role, 'HAIR')
        self.assertIn("LockR2_1", rig.data.bones)  # chain bones are named after the part, without spaces


if __name__ == "__main__":
    tu.run_tests()
