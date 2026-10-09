# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export of a character with clips (clips spec 6): the model FBX without animation, one <Model>@<Clip>.fbx per
clip whose meta cuts that clip from the file's take with its name, range and Loop and copies the model's avatar; the
clip in use, the scene range and the frame come back afterwards; without clips nothing changes."""

import os
import re
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_export_rig_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_animation import clips  # noqa: E402


def character_with_clips():
    """The rig's test character with a Smile shape key and two clips: Walk (loop, frames 1-12, hips and smile), Wave
    (frames 5-20, hips)."""
    rig, objs = rt.built()
    body = objs["Body"]
    body.shape_key_add(name="Basis")
    body.shape_key_add(name="Smile")
    everything = list(bpy.context.view_layer.objects)
    hips = rig.pose.bones["Hips"]
    walk = clips.new(rig, everything, "Walk")
    for frame, x in ((1, 0.0), (12, 0.2)):
        hips.location = (x, 0.0, 0.0)
        hips.keyframe_insert("location", frame=frame)
    smile = body.data.shape_keys.key_blocks["Smile"]
    smile.value = 1.0
    smile.keyframe_insert("value", frame=12)
    walk.use_cyclic = True
    wave = clips.new(rig, everything, "Wave")
    for frame, z in ((5, 0.0), (20, 0.1)):
        hips.location = (0.0, 0.0, z)
        hips.keyframe_insert("location", frame=frame)
    return rig, objs, walk, wave


def export(rig, objs, include_animation=True):
    import dasktoon_export
    from dasktoon_export import targets
    target = targets.make_target(tempfile.mkdtemp(prefix="dt_clips_export_"), "Hero")
    options = dasktoon_export.ExportOptions(include_animation=include_animation, bake_size=32, bake_samples=2)
    return target, dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)


def meta(target, rel):
    with open(os.path.join(target.root, rel + ".meta"), encoding="utf-8") as f:
        return f.read()


def clip_files(target):
    return sorted(name for name in os.listdir(os.path.join(target.root, "Hero", "Model"))
                  if "@" in name and name.endswith(".fbx"))


class ExportClipsTest(unittest.TestCase):
    def test_each_clip_is_a_file_with_its_meta(self):
        rig, objs, walk, wave = character_with_clips()
        scene = bpy.context.scene
        scene.frame_set(3)
        before = (clips.current(rig), scene.frame_start, scene.frame_end, scene.frame_current)
        target, rep = export(rig, objs)
        model = meta(target, "Hero/Model/Hero.fbx")
        model_guid = re.search(r"guid: (\w+)", model).group(1)
        self.assertIn("importAnimation: 0", model)
        self.assertEqual(clip_files(target), ["Hero@Walk.fbx", "Hero@Wave.fbx"])
        for clip, first, last, loop in ((walk, 1, 12, 1), (wave, 5, 20, 0)):
            text = meta(target, "Hero/Model/Hero@%s.fbx" % clip.name)
            for line in ("importAnimation: 1", "      name: %s" % clip.name, "      takeName: %s" % scene.name,
                         "      firstFrame: %d" % first, "      lastFrame: %d" % last, "      loopTime: %d" % loop,
                         "avatarSetup: 2", "guid: %s, type: 3}" % model_guid, "materialImportMode: 0",
                         "animationType: 3"):
                self.assertIn(line, text, (clip.name, line))
        self.assertEqual(rep.clips, [("Walk", True), ("Wave", False)])
        self.assertIn("Clips: Walk (loop), Wave", rep.lines())
        self.assertEqual((clips.current(rig), scene.frame_start, scene.frame_end, scene.frame_current), before)

    def test_without_clips_nothing_changes(self):
        rig, objs = rt.built()
        target, rep = export(rig, objs)
        self.assertEqual((rep.clips, clip_files(target)), ([], []))
        self.assertIn("importAnimation: 1", meta(target, "Hero/Model/Hero.fbx"))

    def test_without_animation_no_clip_files(self):
        rig, objs, _walk, _wave = character_with_clips()
        target, rep = export(rig, objs, include_animation=False)
        self.assertEqual((rep.clips, clip_files(target)), ([], []))


if __name__ == "__main__":
    tu.run_tests()
