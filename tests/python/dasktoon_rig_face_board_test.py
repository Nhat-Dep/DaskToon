# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The face board (rig controls spec 8): knobs beside the head drive the expression shape keys the character has (none
for those it lacks), with simple-expression drivers; the tools set and key expressions through the knobs; the board
stays when the controls come off and leaves nothing behind when it goes."""

import json
import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, face_board, lipsync, parts  # noqa: E402

KEYS = ("Blink", "Blink_L", "Blink_R", "A", "Joy", "lookUp", "Lashes_only")


def character():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    build.build(bpy.context, rig, [parts.Part("Body", objs["Body"], 'BODY'), parts.Part("Hair", objs["Hair"], 'HAIR')])
    body = objs["Body"]
    body.shape_key_add(name="Basis")
    for k, name in enumerate(KEYS):
        block = body.shape_key_add(name=name, from_mix=False)
        block.value = 0.0
        block.data[k].co.z += 0.01
    hair = objs["Hair"]  # a second mesh with the same blink (lashes apart): one knob drives both
    hair.shape_key_add(name="Basis")
    hair.shape_key_add(name="blink", from_mix=False).value = 0.0
    return rig, body, hair


def evaluated_value(obj, name):
    bpy.context.view_layer.update()
    return obj.data.shape_keys.key_blocks[name].value


class FaceBoardTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.body, self.hair = character()
        self.count = face_board.build(bpy.context, self.rig)
        self.reach = json.loads(self.rig.data[face_board.RECORD])["reach"]

    def knob(self, name, x=0.0, y=0.0):
        self.rig.pose.bones[face_board.PREFIX + name].location = (x, y, 0.0)

    def test_knobs_for_the_keys_there_are(self):
        bones = self.rig.data.bones
        for name in ("Eyes", "Wink", "Gaze", "A", "Joy"):
            self.assertIn(face_board.PREFIX + name, bones, name)
            self.assertIn(face_board.FRAME_PREFIX + name, bones, name)
        for name in ("Brows", "Mouth", "I", "Grin", "Tongue"):
            self.assertNotIn(face_board.PREFIX + name, bones, name)
        self.assertEqual(self.count, 5)
        self.assertFalse(any(b.use_deform for b in bones if b.name.startswith(("FB", face_board.BOARD))))
        self.assertEqual(bones[face_board.BOARD].parent.name, "Head")
        self.assertTrue(bones[face_board.FRAME_PREFIX + "Eyes"].hide_select)

    def test_knobs_drive_their_keys(self):
        self.knob("Eyes", y=-self.reach)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 1.0, places=4)
        self.assertAlmostEqual(evaluated_value(self.hair, "blink"), 1.0, places=4)
        self.knob("Eyes", y=-self.reach / 2)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 0.5, places=4)
        self.knob("Eyes", y=self.reach)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 0.0, places=4)
        self.knob("Wink", x=self.reach)  # out, the character's left
        self.assertAlmostEqual(evaluated_value(self.body, "Blink_L"), 1.0, places=4)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink_R"), 0.0, places=4)
        self.knob("A", y=self.reach)
        self.assertAlmostEqual(evaluated_value(self.body, "A"), 1.0, places=4)
        self.knob("Gaze", y=self.reach)
        self.assertAlmostEqual(evaluated_value(self.body, "lookUp"), 1.0, places=4)
        drivers = self.body.data.shape_keys.animation_data.drivers
        self.assertTrue(all(d.driver.is_simple_expression for d in drivers))  # no script needed

    def test_knobs_are_held_on_the_board(self):
        pb = self.rig.pose.bones[face_board.PREFIX + "A"]
        pb.location = (0.05, -0.05, 0.05)
        bpy.context.view_layer.update()
        local = self.rig.data.bones[pb.name].matrix_local.inverted() @ pb.matrix
        np.testing.assert_allclose(local.to_translation(), (0.0, 0.0, 0.0), atol=1e-6)  # a slider only goes up
        self.assertTrue(pb.lock_rotation[0] and pb.lock_location[2])

    def test_tools_go_through_the_knobs(self):
        blink = self.body.data.shape_keys.key_blocks["Blink"]
        face_board.set_value(self.body, blink, 0.7)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 0.7, places=4)
        lashes = self.body.data.shape_keys.key_blocks["Lashes_only"]  # no knob: its own value
        face_board.set_value(self.body, lashes, 0.4)
        self.assertAlmostEqual(lashes.value, 0.4, places=6)
        owner, path, index, scale = face_board.knob_path(self.body, "A")
        self.assertEqual((owner, path, index), (self.rig, 'pose.bones["FB_A"].location', 1))
        frames = [dict({v: 0.0 for v in lipsync.VOWELS}, open=0.0) for _ in range(3)]
        frames[1]["A"] = frames[1]["open"] = 1.0
        lipsync.apply(self.body, self.rig, frames, 10)
        bpy.context.scene.frame_set(11)
        self.assertAlmostEqual(evaluated_value(self.body, "A"), 1.0, places=4)
        bpy.context.scene.frame_set(10)
        self.assertAlmostEqual(evaluated_value(self.body, "A"), 0.0, places=4)

    def test_remove_leaves_nothing(self):
        objects = {o.name for o in bpy.data.objects}
        self.assertTrue(face_board.remove(bpy.context, self.rig))
        self.assertFalse([b.name for b in self.rig.data.bones if b.name.startswith("FB")])
        anim = self.body.data.shape_keys.animation_data  # the bend fixes keep their own drivers
        self.assertFalse([d.data_path for d in (anim.drivers if anim else ()) for v in d.driver.variables
                          for t in v.targets if (t.bone_target or "").startswith(face_board.PREFIX)])
        self.assertFalse([n for n in {o.name for o in bpy.data.objects} - objects])
        self.assertFalse([o for o in bpy.data.objects if o.name.startswith(face_board.TEXT_PREFIX)])
        self.assertIsNone(self.rig.data.collections.get(face_board.COLLECTION))
        self.assertFalse(face_board.has_board(self.rig))
        blink = self.body.data.shape_keys.key_blocks["Blink"]
        blink.value = 0.3
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 0.3, places=6)

    def test_board_stays_when_the_controls_go(self):
        from dasktoon_rig import controls
        controls.add(bpy.context, self.rig)
        face_board.build(bpy.context, self.rig)
        controls.remove(bpy.context, self.rig)
        self.assertTrue(face_board.has_board(self.rig))
        self.assertIn(face_board.PREFIX + "Eyes", self.rig.data.bones)
        self.assertIsNotNone(self.rig.data.collections.get(face_board.COLLECTION))
        self.knob("Eyes", y=-self.reach)
        self.assertAlmostEqual(evaluated_value(self.body, "Blink"), 1.0, places=4)


if __name__ == "__main__":
    tu.run_tests()
