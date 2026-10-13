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


def character():
    """A chibi 2 tall in A-pose: one Body mesh of loose pieces (torso, a big head, arms 50 degrees down, legs, a rabbit
    ear beside each side of the head hanging down to the shoulders, a hair lock in front of the right shoulder); a
    Shirt with a strap on the chest (a loose piece of the shirt); Boots wider than the legs, not touching. The skeleton is fitted to them. Returns
    (rig, {name: object}, parts)."""
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


def rigged():
    """The character with its parts in the rig (as the interface adds them)."""
    from bl_ui import dasktoon_rig as ui
    rig, objs, _parts = character()
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
