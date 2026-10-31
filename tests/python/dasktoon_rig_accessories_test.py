# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""What richly detailed characters taught the auto rig (Encore, Evita and Violet, models from games, 2026-10-30): their
meshes are cut along the texture seams, their parts have Chinese names, and much of what they wear does not bend with
the skin (a bow, a bag, crystals floating round a cloak). Accessories are a group of their own: rigid on one bone each,
kept out of the skeleton's fit."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import accessories, build, parts as rig_parts, regions, skeleton, weights  # noqa: E402


def box(cx, cy, cz, half, ):
    """A closed box (vertices, faces) centred at (cx, cy, cz)."""
    verts = [(cx + sx * half[0], cy + sy * half[1], cz + sz * half[2])
             for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces


def mesh(name, pieces):
    obj = rt.merged(name, pieces)
    return obj


def parts_named(rig):
    return {part.name: part for part in rig.data.dasktoon_rig.parts}


class SeamTest(unittest.TestCase):
    """A model from a game has its vertices doubled along the texture seams: one surface, in pieces that only touch.
    Evita's arm is such a piece: the arm's bones lost their hold on the shoulder cap of the torso piece, so the arm rose
    out of it."""

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_pieces_cut_along_a_seam_are_one_piece(self):
        first = st.tube((0, 0, 0), (0, 0, 1), 0.1, rings=4)
        second = st.tube((0, 0, 1), (0, 0, 2), 0.1, rings=4)  # the same ring at z = 1
        apart = st.tube((1, 0, 0), (1, 0, 1), 0.1, rings=4)
        obj = rt.merged("Cut", [first, second, apart])
        world, edges = rig_parts.mesh_arrays(obj)
        self.assertEqual(len(rig_parts.pieces(edges, np.arange(len(world)))), 3)
        world, edges = rig_parts.welded_arrays(obj)
        self.assertEqual(len(rig_parts.pieces(edges, np.arange(len(world)))), 2)

    def test_the_two_sides_of_a_seam_keep_their_distance_along_the_mesh(self):
        world, edges = rig_parts.welded_arrays(rt.merged("Cut", [st.tube((0, 0, 0), (0, 0, 1), 0.1, rings=4),
                                                                 st.tube((0, 0, 1), (0, 0, 2), 0.1, rings=4)]))
        seeds = world[:, 2] < 1e-6
        self.assertTrue(np.isfinite(regions._along(world, edges, seeds, 10.0)).all())

    def test_a_seam_carries_the_arm_across(self):
        rig, _objs, _parts = rt.character()
        first, first_edges = rt.tube_mesh((0.09, 0.0, 0.6), (0.09, 0.0, 1.0), 0.07, rings=40)
        second, second_edges = rt.tube_mesh((0.09, 0.0, 1.0), (0.09, 0.0, 1.4), 0.07, rings=40)
        world = np.concatenate([first, second])
        edges = np.concatenate([first_edges, second_edges + len(first)])
        leg, torso = regions.REGIONS.index('LEG_L'), regions.REGIONS.index('TORSO')
        labelled = np.concatenate([np.full(len(first), leg), np.full(len(second), torso)]).astype(np.int8)
        cut = regions.keep_factors(rig, world, labelled, edges, 0.1)["LeftUpperLeg"]
        self.assertEqual(cut[len(first):].max(), 0.0)  # cut: the leg ends at the seam
        welded = rig_parts.welded_edges(world, edges)
        whole = regions.keep_factors(rig, world, labelled, welded, 0.1)["LeftUpperLeg"]
        near = len(first) + np.nonzero(second[:, 2] < 1.02)[0]
        self.assertGreater(whole[near].min(), 0.8)

    def test_the_two_sides_of_a_seam_weigh_the_same(self):
        rig, objs, _parts = rt.character()
        arm_a = rt.ARM_START + (rt.ARM_END - rt.ARM_START) * 0.5
        cut = rt.merged("Sleeve", [st.tube(tuple(rt.ARM_START), tuple(arm_a), 0.06, rings=6),
                                   st.tube(tuple(arm_a), tuple(rt.ARM_END), 0.06, rings=6)])
        parts = [rig_parts.Part("Body", objs["Body"], 'BODY'), rig_parts.Part("Sleeve", cut, 'BODY')]
        build.build(bpy.context, rig, parts)
        world, _edges = rig_parts.mesh_arrays(cut)
        names = [b.name for b in rig.data.bones if b.use_deform]
        matrix = weights.read(cut, names)
        groups = rig_parts.same_place(world)
        self.assertGreater(len(groups), 0)
        for group in groups:
            np.testing.assert_allclose(matrix[group], matrix[group[0]][None, :].repeat(len(group), axis=0), atol=1e-3)


class NameTest(unittest.TestCase):
    def test_chinese_names(self):
        cases = {
            "靴子": 'CLOTHING', "袜子": 'CLOTHING', "袖子": 'CLOTHING', "衣服": 'CLOTHING',
            "领子": 'CLOTHING', "短裤": 'CLOTHING', "裙子下": 'SKIRT',
            "身体": 'BODY', "头发": 'HAIR', "胸缎带": 'ACCESSORY',
            "后蝴蝶结2": 'ACCESSORY', "黑花": 'ACCESSORY', "星星": 'ACCESSORY',
            "腰结x2": 'ACCESSORY',
        }
        for name, role in cases.items():
            self.assertEqual(rig_parts.guess_role(name), role, name)

    def test_what_is_worn_in_the_hair_is_no_hair(self):
        for name in ("HairClip", "hair_ribbon", "HairOrnament"):
            self.assertEqual(rig_parts.guess_role(name), 'ACCESSORY', name)
        self.assertEqual(rig_parts.guess_role("Hair_Back"), 'HAIR')

    def test_things_carried_and_cloaks(self):
        for name in ("weapon01.001", "Sword", "Cloak", "Cape", "Crystal", "Wing_L"):
            self.assertEqual(rig_parts.guess_role(name), 'ACCESSORY', name)


class FarOrnamentTest(unittest.TestCase):
    """Evita's cloak holds crystals as long as she is tall, floating out to her sides: read as part of the body's shape,
    they became her arms, her shoulders level with her eyes."""

    def character(self):
        rig, objs, _parts = rt.character()
        from bl_ui import dasktoon_rig as ui
        wide = [st.tube((s * 0.5, 0.0, 1.5), (s * 1.3, 0.0, 1.5), 0.05) for s in (1.0, -1.0)]  # out at the shoulders
        cloak = rt.merged("Cloak2", wide + [st.tube((0, 0.3, 1.4), (0, 0.3, 0.8), 0.05)])
        for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Boots", 'CLOTHING')):
            ui.add_part(rig, objs[name], role)
        ui.add_part(rig, cloak, 'CLOTHING')
        return rig, objs, cloak

    def test_far_pieces_are_found_before_the_fit(self):
        rig, _objs, cloak = self.character()
        accessories.find_far(rig)
        part = parts_named(rig)[accessories.part_name(cloak)]
        self.assertEqual(part.role, 'ACCESSORY')
        vertices = rig_parts.part_vertices(part)
        world, _edges = rig_parts.mesh_arrays(cloak)
        self.assertGreater(np.abs(world[vertices, 0]).min(), 0.4)  # the two out at the sides, not the one behind

    def test_a_mesh_all_far_is_an_accessory_itself(self):
        rig, objs, _cloak = self.character()
        wings = rt.merged("Wings", [st.tube((s * 0.5, 0.0, 1.5), (s * 1.3, 0.0, 1.5), 0.05) for s in (1.0, -1.0)])
        from bl_ui import dasktoon_rig as ui
        ui.add_part(rig, wings, 'CLOTHING')
        accessories.find_far(rig)
        self.assertEqual(parts_named(rig)["Wings"].role, 'ACCESSORY')

    def test_a_skirt_round_the_body_is_no_ornament(self):
        rig, objs, _cloak = self.character()
        from bl_ui import dasktoon_rig as ui
        skirt = rt.merged("Dress", [st.tube((0, 0, 1.0), (0, 0, 0.3), 0.9, segments=24)])
        ui.add_part(rig, skirt, 'CLOTHING')
        accessories.find_far(rig)
        self.assertEqual(parts_named(rig)["Dress"].role, 'CLOTHING')

    def test_the_fit_does_not_see_them(self):
        from bl_ui import dasktoon_rig as ui
        rig, _objs, _cloak = self.character()
        accessories.find_far(rig)
        ui.fit_to_parts(bpy.context, rig)
        arm = rig.matrix_world @ rig.data.bones["LeftHand"].head_local
        self.assertLess(abs(arm.x - rt.ARM_END.x), 0.12)  # at the real hand, not out at the crystal's tip
        self.assertLess(abs(arm.z - rt.ARM_END.z), 0.12)


class SkinOnlyWhereItShowsTest(unittest.TestCase):
    """Skin is modelled where it shows: under socks, shoes and sleeves there is none, so what is worn there lies far from
    any skin without being off the body. Every fixture here had skin all the way down, under the boots: two real
    characters lost their shoes and socks to the accessories, and their legs stopped at the knee."""

    TORSO = st.tube((0, 0, 0.88), (0, 0, 1.46), 0.18)
    HEAD = st.tube((0, 0, 1.46), (0, 0, 2.0), 0.3)

    @staticmethod
    def along_arm(side, start, end):
        mirror = Vector((side, 1.0, 1.0))
        return st.tube(tuple((rt.ARM_START + (rt.ARM_END - rt.ARM_START) * start) * mirror),
                       tuple((rt.ARM_START + (rt.ARM_END - rt.ARM_START) * end) * mirror), 0.05)

    def rigged(self, skin, outfit):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        meshes = [rt.merged("Body", skin), rt.merged("Outfit", outfit)]
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        self.assertEqual(bpy.ops.dasktoon.rig_add_humanoid(), {'FINISHED'})
        return next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')

    def test_shoes_and_socks_below_the_skin_stay_on_the_legs(self):
        arms = [self.along_arm(s, 0.0, 1.0) for s in (1.0, -1.0)]
        thighs = [st.tube((s * 0.08, 0, 0.95), (s * 0.09, 0, 0.55), 0.07) for s in (1.0, -1.0)]
        socks = [st.tube((s * 0.09, 0, 0.56), (s * 0.09, 0, 0.2), 0.075) for s in (1.0, -1.0)]
        shoes = [st.tube((s * 0.09, 0, 0.2), (s * 0.09, -0.08, 0.02), 0.09) for s in (1.0, -1.0)]
        rig = self.rigged([self.TORSO, self.HEAD] + arms + thighs, socks + shoes)
        self.assertEqual(parts_named(rig)["Outfit"].role, 'CLOTHING')
        self.assertNotIn(accessories.part_name(bpy.data.objects["Outfit"]), parts_named(rig))
        foot = rig.matrix_world @ rig.data.bones["LeftFoot"].head_local
        self.assertLess(foot.z, 0.2)  # at the shoe, not at the knee where the skin stops
        knee = rig.matrix_world @ rig.data.bones["LeftLowerLeg"].head_local
        self.assertLess(abs(knee.z - 0.5), 0.15)

    def test_a_slim_trunk_keeps_its_shoulders_at_its_sides(self):
        """A trunk as narrow as a wide sleeve: the walk from the hand went on through it as if along a sleeve, the
        shoulders came to lie inside the chest, and arms raised met over the head. Every fixture had a trunk too wide for
        this."""
        slim = st.tube((0, 0, 0.88), (0, 0, 1.46), 0.1)
        arms = [self.along_arm(s, 0.0, 1.0) for s in (1.0, -1.0)]
        legs = [st.tube((s * 0.06, 0, 0.95), (s * 0.07, 0, 0.0), 0.05) for s in (1.0, -1.0)]
        shirt = st.tube((0, 0, 1.42), (0, 0, 0.9), 0.11)
        sleeves = [self.along_arm(s, 0.0, 0.5) for s in (1.0, -1.0)]
        rig = self.rigged([slim, self.HEAD] + arms + legs, [shirt] + sleeves)
        shoulder = rig.matrix_world @ rig.data.bones["LeftUpperArm"].head_local
        self.assertGreater(shoulder.x, 0.095)
        hand = rig.matrix_world @ rig.data.bones["LeftHand"].head_local
        self.assertLess((hand - rt.ARM_END).length, 0.2)  # still on the line of the arm

    def test_a_lock_of_hair_in_the_skin_is_no_arm(self):
        """The Body mesh holds the head and its hair, the arms are all sleeves: the skin's "arm" was a tuft at the
        temple, and the shoulders rose to it."""
        tufts = [st.tube((s * 0.26, 0, 1.72), (s * 0.44, 0, 1.66), 0.05) for s in (1.0, -1.0)]  # short of the hand
        legs = [st.tube((s * 0.08, 0, 0.95), (s * 0.09, 0, 0.0), 0.07) for s in (1.0, -1.0)]
        sleeves = [self.along_arm(s, 0.0, 1.0) for s in (1.0, -1.0)]
        rig = self.rigged([self.HEAD] + tufts + legs, [self.TORSO] + sleeves)
        hand = rig.matrix_world @ rig.data.bones["LeftHand"].head_local
        self.assertLess((hand - rt.ARM_END).length, 0.2)
        shoulder = rig.matrix_world @ rig.data.bones["LeftUpperArm"].head_local
        self.assertLess(shoulder.z, 1.55)

    def test_a_sleeve_with_no_arm_in_it_is_the_arm(self):
        hands = [self.along_arm(s, 0.8, 1.0) for s in (1.0, -1.0)]
        legs = [st.tube((s * 0.08, 0, 0.95), (s * 0.09, 0, 0.0), 0.07) for s in (1.0, -1.0)]
        sleeves = [self.along_arm(s, 0.0, 0.81) for s in (1.0, -1.0)]
        rig = self.rigged([self.HEAD] + hands + legs, [self.TORSO] + sleeves)
        self.assertEqual(parts_named(rig)["Outfit"].role, 'CLOTHING')
        self.assertNotIn(accessories.part_name(bpy.data.objects["Outfit"]), parts_named(rig))
        hand = rig.matrix_world @ rig.data.bones["LeftHand"].head_local
        self.assertLess((hand - rt.ARM_END).length, 0.2)


class HiddenArmsTest(unittest.TestCase):
    """A cloak spread wide hides the arms in the silhouette of the Body and Clothing together (Evita, a real model: the
    template's level arms stayed, her hands hanging far below them). The skin shows where they are."""

    def test_the_skin_tells_where_the_arms_are(self):
        from bl_ui import dasktoon_rig as ui
        rig, objs, _parts = rt.character()
        for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Boots", 'CLOTHING')):
            ui.add_part(rig, objs[name], role)
        verts = [(u * 0.75, 0.4, 0.9 + v * 0.65) for v in np.linspace(0, 1, 9) for u in np.linspace(-1, 1, 21)]
        faces = [(r * 21 + c, r * 21 + c + 1, (r + 1) * 21 + c + 1, (r + 1) * 21 + c) for r in range(8) for c in range(20)]
        cloak = rt.merged("Sheet", [(verts, faces)])  # behind her, close enough to stay Clothing, wider than her arms
        ui.add_part(rig, cloak, 'CLOTHING')
        ui.fit_to_parts(bpy.context, rig)
        hand = rig.matrix_world @ rig.data.bones["LeftHand"].head_local
        elbow = rig.matrix_world @ rig.data.bones["LeftLowerArm"].head_local
        shoulder = rig.matrix_world @ rig.data.bones["LeftUpperArm"].head_local
        direction = (rt.ARM_END - rt.ARM_START).normalized()
        self.assertGreater((hand - shoulder).normalized().dot(direction), 0.95)
        self.assertLess((hand - rt.ARM_END).length, 0.15)
        self.assertLess(elbow.z, shoulder.z - 0.1)


class WideClothesTest(unittest.TestCase):
    """A cloak as wide as the arms reach widens the trunk as the front view reads it: the regions took the arms for trunk,
    so the arm bones rose and the arms stayed behind, stretched from hip to hand (a real character, seen only in a render
    of the skin alone). Every fixture's clothes followed the body's width."""

    def setUp(self):
        from bl_ui import dasktoon_rig as ui
        self.rig, self.objs, _parts = rt.character()
        for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Boots", 'CLOTHING')):
            ui.add_part(self.rig, self.objs[name], role)
        verts = [(u * 0.8, 0.26, 0.5 + v * 1.0) for v in np.linspace(0, 1, 11) for u in np.linspace(-1, 1, 21)]
        faces = [(r * 21 + c, r * 21 + c + 1, (r + 1) * 21 + c + 1, (r + 1) * 21 + c) for r in range(10) for c in range(20)]
        ui.add_part(self.rig, rt.merged("Sheet", [(verts, faces)]), 'CLOTHING')  # close behind it, wider than the arms
        ui.fit_to_parts(bpy.context, self.rig)
        self.parts = list(self.rig.data.dasktoon_rig.parts)
        world = rig_parts.mesh_arrays(self.objs["Body"])[0]
        axis = np.array(rt.ARM_END - rt.ARM_START)
        self.along = (world - np.array(rt.ARM_START)) @ axis / (axis @ axis)
        off = np.linalg.norm(world - np.array(rt.ARM_START) - np.outer(self.along, axis), axis=1)
        self.arm = np.nonzero((self.along > 0.25) & (self.along < 1.0) & (off < 0.07))[0]  # beyond the shoulder

    def test_the_arms_stay_arms(self):
        vertices, labelled = regions.analyse(bpy.context, self.rig, self.parts).objects[self.objs["Body"]]
        by_vertex = dict(zip(vertices.tolist(), labelled.tolist()))
        found = {regions.REGIONS[by_vertex[i]] for i in self.arm.tolist()}
        self.assertEqual(found, {'ARM_L'})

    def test_and_follow_their_bones(self):
        build.build(bpy.context, self.rig, self.parts)
        outer = self.arm[self.along[self.arm] > 0.55]  # the start of the tube is inside the torso, then the elbow blends
        self.assertGreater(float(rt.limb_weight(self.rig, self.objs["Body"], outer, 'ARM_L').min()), 0.9)


class NoArmsTest(unittest.TestCase):
    def test_a_trunk_with_no_arms_to_read_is_as_wide_as_it_looks(self):
        """A bust in a coat: its shoulders are only the template's, which says nothing of how wide a trunk may be, and the
        coat is the trunk's shape."""
        from bl_ui import dasktoon_rig as ui
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bust = rt.merged("Bust", [st.tube((0, 0, 0.0), (0, 0, 1.4), 0.3, rings=40, segments=64),
                                  st.tube((0, 0, 1.4), (0, 0, 2.0), 0.3, rings=30, segments=64)])
        coat = rt.merged("Coat", [st.tube((0, 0, 0.0), (0, 0, 1.3), 0.6, rings=60, segments=96)])
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        ui.add_part(rig, bust, 'BODY')
        ui.add_part(rig, coat, 'CLOTHING')
        ui.fit_to_parts(bpy.context, rig)
        found = regions.analyse(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        self.assertGreater(found.half["Spine"], 0.5)


class WideHipsTest(unittest.TestCase):
    """The trunk's round end hung below the hips: with hips wide next to the thigh it took the top of the thigh, which stayed
    behind when the leg rose, a flap of skin below the hip (a real character, seen only in a render of the sitting pose;
    its thigh is 0.26 of its height, its hips 0.19 across from the middle). Fixture hips were narrow. Worn over the top
    of the legs, shorts lost the leg bones altogether."""

    def setUp(self):
        from bl_ui import dasktoon_rig as ui
        bpy.ops.wm.read_factory_settings(use_empty=True)
        legs = [st.tube((s * 0.17, 0, 1.0), (s * 0.17, 0, 0.0), 0.1, rings=20) for s in (1.0, -1.0)]
        arms = [st.tube(tuple(rt.ARM_START * Vector((s, 1, 1))), tuple(rt.ARM_END * Vector((s, 1, 1))), 0.05) for s in (1.0, -1.0)]
        trunk = [st.tube((0, 0, 0.95), (0, 0, 1.25), 0.32), st.tube((0, 0, 1.25), (0, 0, 1.46), 0.2),
                 st.tube((0, 0, 1.46), (0, 0, 2.0), 0.3)]
        self.body = rt.merged("Body", trunk + legs + arms)
        shorts = [st.tube((s * 0.17, 0, 0.98), (s * 0.17, 0, 0.72), 0.115, rings=10) for s in (1.0, -1.0)]
        self.shorts = rt.merged("Shorts", shorts)
        self.rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        ui.add_part(self.rig, self.body, 'BODY')
        ui.add_part(self.rig, self.shorts, 'CLOTHING')
        ui.fit_to_parts(bpy.context, self.rig)
        self.parts = list(self.rig.data.dasktoon_rig.parts)

    def thigh(self, obj, low, high):
        world = rig_parts.mesh_arrays(obj)[0]
        return np.nonzero((world[:, 0] > 0.1) & (world[:, 0] < 0.3) & (world[:, 2] > low) & (world[:, 2] < high))[0]

    def test_the_top_of_the_thigh_is_thigh(self):
        vertices, labelled = regions.analyse(bpy.context, self.rig, self.parts).objects[self.body]
        by_vertex = dict(zip(vertices.tolist(), labelled.tolist()))
        self.assertEqual({regions.REGIONS[by_vertex[i]] for i in self.thigh(self.body, 0.45, 0.8).tolist()}, {'LEG_L'})

    def test_it_follows_the_leg(self):
        build.build(bpy.context, self.rig, self.parts)
        self.assertGreater(float(rt.limb_weight(self.rig, self.body, self.thigh(self.body, 0.5, 0.8), 'LEG_L').min()), 0.9)

    def test_so_do_shorts_on_it(self):
        build.build(bpy.context, self.rig, self.parts)
        hem = self.thigh(self.shorts, 0.72, 0.76)
        self.assertGreater(float(rt.limb_weight(self.rig, self.shorts, hem, 'LEG_L').min()), 0.9)


class NamesInOtherScriptsTest(unittest.TestCase):
    """Bone names are ASCII, and a name in Chinese has no ASCII: two skirts so named made bones of one name, the first's
    bones then passing for bones of the body. Shorts near them took them on and stopped following the thighs."""

    def test_two_skirts_keep_their_own_bones(self):
        from bl_ui import dasktoon_rig as ui
        rig, objs, _parts = rt.character()
        for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Boots", 'CLOTHING')):
            ui.add_part(rig, objs[name], role)
        names = ("\u88d9\u5b50\u4e0a", "\u88d9\u5b50\u4e0b")
        upper = rt.merged(names[0], [st.tube((0, 0, 1.0), (0, 0, 0.8), 0.3, segments=24)])
        lower = rt.merged(names[1], [st.tube((0, 0, 0.8), (0, 0, 0.55), 0.36, segments=24)])
        ui.add_part(rig, upper, 'SKIRT')
        ui.add_part(rig, lower, 'SKIRT')
        ui.fit_to_parts(bpy.context, rig)
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        chain = [bone.name for bone in rig.data.bones if bone.name.startswith("Part")]
        self.assertEqual(len(chain), 2 * 8 * 3)
        self.assertEqual(float(weights.read(objs["Body"], chain).max()), 0.0)
        self.assertEqual(float(weights.read(objs["Shirt"], chain).max()), 0.0)
        own = {obj.name: {name for name in chain if float(weights.read(obj, [name]).max()) > 0.0} for obj in (upper, lower)}
        self.assertTrue(own[names[0]] and own[names[1]])
        self.assertEqual(own[names[0]] & own[names[1]], set())


class HeadPartsTest(unittest.TestCase):
    """Encore's brows, lashes, mouth and blush are meshes of their own, all on the head: they were Clothing, and each
    loose bit a lock (59 parts)."""

    def setUp(self):
        from bl_ui import dasktoon_rig as ui
        self.rig, self.objs = rt.rigged()
        head = self.rig.matrix_world @ self.rig.data.bones["Head"].head_local
        self.brows = rt.merged("mei", [box(s * 0.12, -0.28, head.z + 0.28, (0.05, 0.01, 0.01)) for s in (1.0, -1.0)])
        self.lining = rt.merged("hou", [box(0.0, 0.1, head.z + 0.2, (0.2, 0.1, 0.15))])
        ui.add_part(self.rig, self.brows, 'CLOTHING')
        ui.add_part(self.rig, self.lining, 'CLOTHING')

    def test_what_lies_on_the_head_goes_with_the_head(self):
        accessories.find(bpy.context, self.rig)
        for name in ("mei", "hou"):
            part = parts_named(self.rig)[name]
            self.assertEqual((part.role, part.bone), ('ACCESSORY', "Head"), name)

    def test_they_are_no_locks_any_more(self):
        accessories.find(bpy.context, self.rig)
        regions.recognize(bpy.context, self.rig)
        self.assertFalse([p.name for p in self.rig.data.dasktoon_rig.parts
                          if p.name.startswith("Lock") and p.object is self.brows])

    def test_the_body_itself_stays(self):
        accessories.find(bpy.context, self.rig)
        self.assertEqual(parts_named(self.rig)["Body"].role, 'BODY')

    def test_a_name_says_nothing_of_this(self):
        """The shape decides: a mesh on the head of any name goes with the head."""
        from bl_ui import dasktoon_rig as ui
        stud = rt.merged("Mesh.017", [box(0.2, -0.28, self.brows.location.z + 1.8, (0.02, 0.02, 0.02))])
        ui.add_part(self.rig, stud, 'CLOTHING')
        accessories.find(bpy.context, self.rig)
        self.assertEqual(parts_named(self.rig)["Mesh.017"].role, 'ACCESSORY')


class StandingOffTest(unittest.TestCase):
    """A bag at the hip, a bow on the chest: pieces of a Clothing mesh standing off the body."""

    def setUp(self):
        from bl_ui import dasktoon_rig as ui
        self.rig, self.objs = rt.rigged()
        self.coat = rt.merged("Coat", [st.tube((0, 0, 1.38), (0, 0, 0.9), 0.205),
                                       box(0.3, -0.05, 1.0, (0.08, 0.08, 0.08)),  # a bag at the hip
                                       box(0.0, -0.3, 1.3, (0.06, 0.06, 0.04))])  # a bow on the chest
        ui.add_part(self.rig, self.coat, 'CLOTHING')

    def test_they_become_an_accessory_part_of_the_mesh(self):
        accessories.find(bpy.context, self.rig)
        part = parts_named(self.rig)[accessories.part_name(self.coat)]
        self.assertEqual((part.role, part.scope), ('ACCESSORY', 'VERTEX_GROUP'))
        self.assertEqual(len(rig_parts.part_vertices(part)), 16)
        self.assertEqual(parts_named(self.rig)["Coat"].role, 'CLOTHING')

    def test_many_meshes_each_with_something_standing_off(self):
        """Each one adds a part, and adding a part moves the list in memory: what was held of the list from before is
        gone. That crashed on a real character. Where the list lands is luck, so this does not fail on demand on the old
        code; it holds what must come out, with more parts added than any other test here."""
        from bl_ui import dasktoon_rig as ui
        meshes = []
        for i in range(40):
            band = st.tube((0, 0, 1.38 - 0.01 * i), (0, 0, 1.36 - 0.01 * i), 0.205)
            meshes.append(rt.merged("Layer%d" % i, [band, box(0.32, 0.3, 0.95 + 0.01 * i, (0.03, 0.03, 0.03))]))
            ui.add_part(self.rig, meshes[-1], 'CLOTHING')
        accessories.find(bpy.context, self.rig)
        named = parts_named(self.rig)
        for obj in meshes:
            self.assertEqual(named[accessories.part_name(obj)].object, obj)
            self.assertEqual(named[obj.name].role, 'CLOTHING')

    def test_finding_again_makes_no_second_part(self):
        accessories.find(bpy.context, self.rig)
        accessories.find(bpy.context, self.rig)
        names = [p.name for p in self.rig.data.dasktoon_rig.parts]
        self.assertEqual(len(names), len(set(names)))

    def test_a_part_you_gave_a_bone_keeps_it(self):
        accessories.find(bpy.context, self.rig)
        parts_named(self.rig)[accessories.part_name(self.coat)].bone = "Hips"
        accessories.find(bpy.context, self.rig)
        self.assertEqual(parts_named(self.rig)[accessories.part_name(self.coat)].bone, "Hips")


class RigidTest(unittest.TestCase):
    """Each accessory follows one bone: the bone of the limb it sits on, else of the trunk, never an arm it only lies
    near (the crystals by Evita's shoulders)."""

    @classmethod
    def setUpClass(cls):
        from bl_ui import dasktoon_rig as ui
        cls.rig, cls.objs = rt.rigged()
        wrist = rt.ARM_START + (rt.ARM_END - rt.ARM_START) * 0.8
        cls.bracelet = tuple(wrist)
        cls.gems = rt.merged("Gems", [box(*cls.bracelet, (0.07, 0.07, 0.07)),  # round the wrist
                                      box(0.42, 0.0, 1.5, (0.03, 0.03, 0.03)),  # out by the shoulder, on nothing
                                      box(-0.3, -0.05, 1.0, (0.05, 0.05, 0.05))])  # at the hip
        ui.add_part(cls.rig, cls.gems, 'ACCESSORY')
        build.build(bpy.context, cls.rig, list(cls.rig.data.dasktoon_rig.parts))
        cls.names = [b.name for b in cls.rig.data.bones if b.use_deform]
        cls.matrix = weights.read(cls.gems, cls.names)

    def bones_of(self, first):
        rows = self.matrix[first:first + 8]
        return {self.names[j] for j in np.nonzero(rows.sum(axis=0))[0]}

    def test_on_a_limb_it_follows_the_limb(self):
        self.assertEqual(self.bones_of(0) & {"LeftLowerArm", "LeftHand"}, self.bones_of(0))
        self.assertEqual(len(self.bones_of(0)), 1)

    def test_near_a_shoulder_it_does_not_follow_the_arm(self):
        bones = self.bones_of(8)
        self.assertEqual(len(bones), 1)
        self.assertFalse(bones & {"LeftUpperArm", "LeftLowerArm", "LeftHand"})

    def test_at_the_hip_it_follows_the_trunk(self):
        bones = self.bones_of(16)
        self.assertEqual(len(bones), 1)
        self.assertTrue(bones & {"Hips", "Spine", "Chest"})

    def test_pieces_that_touch_go_together(self):
        from bl_ui import dasktoon_rig as ui
        rig, _objs = rt.rigged()
        bow = rt.merged("Bow", [box(0.3, -0.05, 1.0, (0.05, 0.05, 0.05)), box(0.3, -0.05, 1.1, (0.05, 0.05, 0.05))])
        ui.add_part(rig, bow, 'ACCESSORY')
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        names = [b.name for b in rig.data.bones if b.use_deform]
        self.assertEqual(len(np.nonzero(weights.read(bow, names).sum(axis=0))[0]), 1)


class HairTest(unittest.TestCase):
    """Evita's hair: 135 pieces, most of them cut along seams or too short to swing, made 116 chains (464 bones)."""

    def setUp(self):
        from bl_ui import dasktoon_rig as ui
        self.ui = ui
        self.rig, self.objs = rt.rigged()

    def chains_of(self, name, pieces):
        hair = rt.merged(name, pieces)
        self.ui.add_part(self.rig, hair, 'HAIR')
        return build.build(bpy.context, self.rig, list(self.rig.data.dasktoon_rig.parts)).chains

    def test_a_lock_cut_along_a_seam_is_one_chain(self):
        made = self.chains_of("HairA", [st.tube((0.3, -0.1, 1.9), (0.3, -0.1, 1.5), 0.02),
                                        st.tube((0.3, -0.1, 1.5), (0.3, -0.1, 1.1), 0.02)])
        self.assertEqual(made, 1)

    def test_a_short_piece_is_rigid_on_the_head(self):
        short = st.tube((0.3, -0.1, 1.9), (0.3, -0.1, 1.85), 0.004)  # long for its width, 2.5% of her height
        made = self.chains_of("HairB", [short, st.tube((-0.3, -0.1, 1.9), (-0.3, -0.1, 1.1), 0.02)])
        self.assertEqual(made, 1)


class PanelTest(unittest.TestCase):
    def test_the_accessories_are_listed_apart(self):
        from bl_ui import dasktoon_rig as ui
        rig, objs = rt.rigged()
        gem = rt.merged("Gem", [box(0.4, 0.0, 1.5, (0.03, 0.03, 0.03))])
        ui.add_part(rig, gem, 'ACCESSORY')
        shown = ui.DASKTOON_UL_rig_parts.shown(rig.data.dasktoon_rig.parts)
        apart = ui.DASKTOON_UL_rig_accessories.shown(rig.data.dasktoon_rig.parts)
        self.assertEqual([p.name for p in apart], ["Gem"])
        self.assertNotIn("Gem", [p.name for p in shown])
        self.assertIn("Body", [p.name for p in shown])


if __name__ == "__main__":
    tu.run_tests()
