# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export for Godot 4 of a rigged character (Godot spec 5, wave 3): the rig data goes into <model>.dasktoon.json,
and Godot's import script gives the skeleton a SpringBoneSimulator3D for the hair and skirts that sway while the game
runs (with the colliders as capsules) and DaskToon's modifier, which sets the bend fixes' weights as DaskToon's drivers
do, slides the flat eye's iris and picks the 2D mouth's cell. Runs Godot on a throwaway project."""

import json
import math
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_export_rig_test as rt  # noqa: E402
import dasktoon_godot_harness as harness  # noqa: E402
import dasktoon_rig_correctives_test as ct  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_correctives_test as unity_fixes  # noqa: E402  (the poses of the Unity check)
import dasktoon_export  # noqa: E402
from dasktoon_animation import clips  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_rig import correctives, mouth  # noqa: E402


def export(objects, folder=None, **options):
    target = targets.make_target(folder or tempfile.mkdtemp(prefix="dt_godot_rig_"), "Hero", 'GODOT_4')
    settings = dict(include_animation=False, bake_size=32, bake_samples=2)
    settings.update(options)
    return target, dasktoon_export.export_model(bpy.context, target, objects,
                                                dasktoon_export.ExportOptions(**settings))


def rig_of(target):
    with open(os.path.join(target.root, "Hero", "Hero.dasktoon.json"), encoding="utf-8") as f:
        return json.load(f)["rig"]


class RigDataTest(unittest.TestCase):
    def test_the_rig_data_names_the_merged_mesh(self):
        rig, objs, iris, card = rt.face_built()
        target, rep = export([rig, iris, card] + list(objs.values()))
        data = rig_of(target)
        self.assertEqual(rep.rig, "Hero/Hero.dasktoon.json")
        self.assertTrue(any("Godot gets the swaying hair" in line for line in rep.lines()), rep.lines())
        self.assertEqual([e["object"] for e in data["flatEyes"]], ["Body"])
        self.assertEqual([m["object"] for m in data["mouths"]], ["Body"])

    def test_a_chain_growing_inside_a_collider_leaves_it_out(self):
        """luna's hair locks start at the top of the head, inside its capsule: Godot's spring bone threw them 35 cm
        off where DaskToon's sway leaves them hanging, so a chain does not collide with a capsule its root is in."""
        rig, objs = rt.built()
        head = next(c for c in rig.data.dasktoon_rig.colliders if c.bone == "Head")
        head.radius = 10.0  # the whole character inside it
        target, _rep = export([rig] + list(objs.values()), export_materials=False)
        chains = rig_of(target)["chains"]
        self.assertTrue(chains and all("Head" in c["exclude"] for c in chains), chains)
        head.radius = 0.0001
        target, _rep = export([rig] + list(objs.values()), export_materials=False)
        self.assertTrue(all("Head" not in c["exclude"] for c in rig_of(target)["chains"]))

    def test_no_rig_no_rig_data(self):
        tu.reset_scene()
        body = tu.add_sphere(segments=8, rings=4)
        target, rep = export([body])
        self.assertIsNone(rig_of(target))
        self.assertEqual(rep.rig, "")


@unittest.skipUnless(harness.godot_exe(), harness.SKIP_REASON)
class GodotRigTest(unittest.TestCase):
    def run_godot(self, objects, args, **options):
        root = harness.new_project("dasktoon_godot_rig")
        export(objects, root, **options)
        harness.import_project(root)
        args = dict(args, model="res://DaskToon/Hero/Hero.glb")
        result, output = harness.run_script(root, "dasktoon_rig", args)
        self.assertTrue(result["ok"], result.get("error"))
        return result, output

    def test_hair_and_skirts_sway_in_godot(self):
        rig, objs = rt.built()
        rig.data.dasktoon_rig.parts["Hair"].stiffness = 2.5
        next(c for c in rig.data.dasktoon_rig.colliders if c.bone == "Head").radius = 10.0
        data = rt.rig_json.rig_data(rig)
        from dasktoon_export import godot as godot_export
        godot_export.leave_out_inner_colliders(rig, data)
        result, output = self.run_godot([rig] + list(objs.values()), {}, export_materials=False)
        self.assertTrue(result["sway"], output[-2000:])
        runtime = [c for c in data["chains"] if c["unity"] == "runtime"]
        settings = {s["root"]: s for s in result["settings"]}
        self.assertEqual(set(settings), {c["bones"][0] for c in runtime})
        hair = settings["Hair_1"]
        self.assertEqual(hair["end"], "Hair_4")
        self.assertAlmostEqual(hair["stiffness"], 2.5, places=4)
        chain = next(c for c in runtime if c["part"] == "Hair")
        for key in ("drag", "gravity", "radius"):
            self.assertAlmostEqual(hair[key], chain[key], places=4, msg=key)
        self.assertAlmostEqual(hair["length"], chain["lengths"][-1], places=4)
        self.assertTrue(all(s["collisions"] for s in result["settings"]))
        for chain in runtime:
            self.assertEqual(sorted(settings[chain["bones"][0]]["exclude"]), sorted(chain["exclude"]))
        self.assertEqual(sorted(c["bone"] for c in result["colliders"]), sorted(c["bone"] for c in data["colliders"]))
        for got in result["colliders"]:
            want = next(c for c in data["colliders"] if c["bone"] == got["bone"])
            self.assertAlmostEqual(got["radius"], want["radius"], places=4)
            self.assertAlmostEqual(got["length"], want["length"], places=4)
            # Along the bone, from its head to its tail (Godot does not save the offset: DaskToon's modifier sets it).
            self.assertAlmostEqual(got["offset"], want["length"] / 2.0, places=4)

    def test_baked_parts_do_not_sway_in_godot(self):
        rig, objs = rt.built()
        for part in rig.data.dasktoon_rig.parts:
            part.sway_in_unity = 'BAKED'
        result, _output = self.run_godot([rig] + list(objs.values()), {}, export_materials=False)
        self.assertFalse(result["sway"])

    def test_bend_fixes_in_godot(self):
        rig, objs = ct.built()
        body = objs["Body"]
        frame = correctives.body_frame(rig)
        fixes = {fix.name: fix for fix in correctives.fixes(rig)}
        sent, expected = [], []
        for name, axis, angle in unity_fixes.poses(rig, body):
            fix = fixes[name]
            ct.turn(rig, fix.child, axis, angle)
            expected.append(ct.value(body, correctives.PREFIX + name))
            pose_bone = rig.pose.bones[fix.child]
            direction = (pose_bone.tail - pose_bone.head).normalized()
            sent.append({"shape": correctives.PREFIX + name, "child": fix.child,
                         "direction": [direction.dot(axis_) for axis_ in frame]})
        ct.at_rest(rig)
        bpy.context.view_layer.update()
        result, output = self.run_godot([rig] + list(objs.values()), {"poses": sent}, export_materials=False)
        self.assertTrue(result["modifier"], output[-2000:])
        self.assertEqual(result["fixCount"], len(fixes))
        self.assertEqual(result["fixMesh"], "Body")
        self.assertEqual(len(result["weights"]), len(expected))
        for got, want, pose in zip(result["weights"], expected, sent):
            self.assertAlmostEqual(got, want, delta=0.01, msg=pose)
        self.assertGreater(max(expected), 0.99)
        self.assertLess(min(expected), 0.01)

    def test_flat_eye_and_mouth_in_godot(self):
        rig, objs, iris, card = rt.face_built()
        scene = bpy.context.scene
        talk = clips.new(rig, list(bpy.context.view_layer.objects), "Talk", scene=scene)
        for frame, cell in ((1, 0), (3, 3), (6, 1)):
            card[mouth.PROP] = cell
            card.keyframe_insert('["%s"]' % mouth.PROP, frame=frame)
        rig.pose.bones["Hips"].keyframe_insert("location", frame=1)
        rig.pose.bones["Hips"].keyframe_insert("location", frame=6)
        fps = scene.render.fps / scene.render.fps_base
        result, output = self.run_godot([rig, iris, card] + list(objs.values()),
                                        {"clip": "Talk", "cellTime": 2.0 / fps}, include_animation=True)
        self.assertTrue(result["modifier"], output[-2000:])
        # Engine Export merges the meshes by default: the iris and the mouth card are in the Body, found by material.
        self.assertEqual((result["eyeBone"], result["eyeMesh"]), ("LeftEye", "Body"))
        eye = result["eye"]
        self.assertLess(math.hypot(*eye["rest"]), 1e-4)
        self.assertAlmostEqual(eye["left"][0], -0.1 * math.sin(math.radians(20.0)), delta=2e-3)
        self.assertAlmostEqual(eye["left"][1], 0.0, delta=2e-3)
        self.assertAlmostEqual(eye["up"][1], -0.1 * math.sin(math.radians(10.0)), delta=2e-3)
        self.assertAlmostEqual(eye["up"][0], 0.0, delta=2e-3)
        self.assertEqual(result["mouthBone"], mouth.CELL_BONE)
        for got, want in zip(result["mouthRest"], (0.25, 0.5, 0.0, 0.5)):
            self.assertAlmostEqual(got, want, places=5)
        for got, want in zip(result["mouth"], (0.25, 0.5, 0.75, 0.5)):
            self.assertAlmostEqual(got, want, places=5)
        self.assertAlmostEqual(result["cellScale"], 4.0, delta=0.01)  # frame 3 of Talk shows cell 3


if __name__ == "__main__":
    tu.run_tests()
