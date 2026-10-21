# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export for Godot 4 of a character with clips (Godot spec 3, wave 2): one animation per clip in the model,
baked frame by frame with its anime timing, its Loop and its shape keys, nothing of one clip in another; the clip in use,
the scene range and the frame come back afterwards. With Godot installed, a throwaway project imports it and the import
script makes Walk loop and step."""

import json
import math
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_export_clips_test as ct  # noqa: E402
import dasktoon_godot_harness as harness  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_animation import clips  # noqa: E402
from dasktoon_export import targets  # noqa: E402


def export(rig, objs, folder=None, include_animation=True, merge_meshes=False):
    target = targets.make_target(folder or tempfile.mkdtemp(prefix="dt_godot_clips_"), "Hero", 'GODOT_4')
    options = dasktoon_export.ExportOptions(include_animation=include_animation, bake_size=32, bake_samples=2,
                                            merge_meshes=merge_meshes)
    return target, dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ClipsTest(unittest.TestCase):
    def test_clips_are_listed_and_everything_comes_back(self):
        rig, objs, _walk, _wave = ct.character_with_clips()
        scene = bpy.context.scene
        scene.frame_set(3)
        before = (clips.current(rig), scene.frame_start, scene.frame_end, scene.frame_current)
        actions = set(bpy.data.actions)
        target, rep = export(rig, objs)
        self.assertEqual(rep.clips, [("Walk", True), ("Wave", False)])
        self.assertIn("Clips: Walk (loop), Wave", rep.lines())
        data = read_json(os.path.join(target.root, "Hero", "Hero.dasktoon.json"))
        self.assertEqual(data["clips"], [{"name": "Walk", "loop": True, "stepped": True},
                                         {"name": "Wave", "loop": False, "stepped": False}])
        with open(os.path.join(target.root, "Hero", "Hero.glb.import"), encoding="utf-8") as f:
            self.assertIn("animation/fps=%g" % scene.render.fps, f.read())
        self.assertEqual((clips.current(rig), scene.frame_start, scene.frame_end, scene.frame_current), before)
        self.assertEqual(set(bpy.data.actions), actions)
        for idb in clips.parts(rig, list(bpy.context.view_layer.objects)):
            anim = idb.animation_data
            self.assertTrue(anim is None or not len(anim.nla_tracks), idb.name)
        self.assertTrue(all(not c.mute for bone in rig.pose.bones for c in bone.constraints))

    def test_the_glb_has_one_animation_per_clip(self):
        rig, objs, _walk, _wave = ct.character_with_clips()
        target, _rep = export(rig, objs)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(target.root, "Hero", "Hero.glb"))
        self.assertTrue({"Walk", "Wave"} <= {action.name for action in bpy.data.actions}, list(bpy.data.actions))

    def test_without_animation_there_are_no_clips(self):
        rig, objs, _walk, _wave = ct.character_with_clips()
        target, rep = export(rig, objs, include_animation=False)
        self.assertEqual(rep.clips, [])
        self.assertEqual(read_json(os.path.join(target.root, "Hero", "Hero.dasktoon.json"))["clips"], [])


@unittest.skipUnless(harness.godot_exe(), harness.SKIP_REASON)
class GodotClipsTest(unittest.TestCase):
    def check(self, merge_meshes):
        root = harness.new_project("dasktoon_godot_clips")
        rig, objs, _walk, _wave = ct.character_with_clips()
        export(rig, objs, root, merge_meshes=merge_meshes)
        harness.import_project(root)
        result, output = harness.run_script(root, "dasktoon_clips", {
            "model": "res://DaskToon/Hero/Hero.glb", "bone": "Hips", "shape": "Smile",
            "fps": bpy.context.scene.render.fps})
        self.assertTrue(result["ok"], result.get("error"))
        clips_found = result["clips"]
        self.assertEqual(set(clips_found), {"Walk", "Wave"}, output[-2000:])
        walk, wave = clips_found["Walk"], clips_found["Wave"]
        fps = bpy.context.scene.render.fps
        self.assertEqual((walk["loop"], wave["loop"]), (1, 0))  # Animation.LOOP_LINEAR, LOOP_NONE
        self.assertEqual(walk["interpolation"], [0])  # every track Animation.INTERPOLATION_NEAREST
        self.assertEqual(wave["bone_interpolation"], 1)  # INTERPOLATION_LINEAR (tracks of one key come as NEAREST)
        self.assertAlmostEqual(walk["length"], 11.0 / fps, places=3)
        self.assertAlmostEqual(wave["length"], 15.0 / fps, places=3)
        # Walk is on twos: the hips hold each drawing for two frames, and go 0.2 in all.
        hips = [math.dist(p, walk["bone"][0]) for p in walk["bone"]]
        self.assertEqual(len(hips), 12)
        for k in range(0, 12, 2):
            self.assertAlmostEqual(hips[k], hips[k + 1], places=4, msg=hips)
        self.assertGreater(hips[-1], 0.15)
        # The smile opens in Walk, on twos too (frame 12 holds frame 11's drawing), and stays shut in Wave.
        smile = walk["shape"]
        self.assertAlmostEqual(smile[0], 0.0, places=3)
        for k in range(0, 12, 2):
            self.assertAlmostEqual(smile[k], smile[k + 1], places=4, msg=smile)
        self.assertGreater(smile[-1], 0.95)
        self.assertTrue(all(abs(v) < 1e-3 for v in wave["shape"]), wave["shape"])

    def test_godot_plays_the_clips(self):
        self.check(merge_meshes=False)

    def test_godot_plays_the_clips_of_merged_meshes(self):
        self.check(merge_meshes=True)


if __name__ == "__main__":
    tu.run_tests()
