# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Lip sync from a voice file (anime rig spec 10.3): the vowels A I U E O and the mouth's opening per frame, found in
a synthetic voice (pulses through two resonators at each vowel's formants), keyed into the clip the character plays on
its vowel shape keys, its Jaw bone and its 2D mouth."""

import math
import os
import sys
import tempfile
import time
import unittest
import wave

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_face_test as face  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from bpy_extras import anim_utils  # noqa: E402
from dasktoon_animation import clips  # noqa: E402
from dasktoon_rig import build, lipsync, mouth  # noqa: E402

RATE = 22050
FPS = 24
VOWEL_SECONDS, GAP_SECONDS = 0.4, 0.2


def resonate(signal, frequency, bandwidth, rate):
    r = math.exp(-math.pi * bandwidth / rate)
    a1, a2 = -2.0 * r * math.cos(2.0 * math.pi * frequency / rate), r * r
    out = np.zeros(len(signal))
    for i in range(len(signal)):
        out[i] = signal[i] - a1 * out[i - 1] - a2 * out[i - 2] if i >= 2 else signal[i]
    return out


def vowel(name, seconds, rate=RATE):
    pulses = np.zeros(int(seconds * rate))
    pulses[::int(rate / 120.0)] = 1.0
    f1, f2 = lipsync.FORMANTS[name]
    out = resonate(resonate(pulses, f1, 80.0, rate), f2, 100.0, rate)
    return out / np.abs(out).max() * 0.5


def voice(rate=RATE):
    """(samples, [(vowel or None, start second, end second)]): silence, then each vowel after a gap."""
    parts, plan, t = [], [], 0.0
    for name in lipsync.VOWELS:
        parts += [np.zeros(int(GAP_SECONDS * rate)), vowel(name, VOWEL_SECONDS, rate)]
        plan += [(None, t, t + GAP_SECONDS), (name, t + GAP_SECONDS, t + GAP_SECONDS + VOWEL_SECONDS)]
        t += GAP_SECONDS + VOWEL_SECONDS
    parts.append(np.zeros(int(GAP_SECONDS * rate)))
    plan.append((None, t, t + GAP_SECONDS))
    return np.concatenate(parts).astype(np.float32), plan


def write_wav(samples, rate, channels=1):
    path = os.path.join(tempfile.mkdtemp(prefix="dt_lipsync_"), "voice.wav")
    data = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    if channels == 2:
        data = np.repeat(data[:, None], 2, axis=1)
    with wave.open(path, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(data.tobytes())
    return path


def frames_inside(plan, name):
    """Frames whose whole window lies in the segments of `name`, away from their edges."""
    out = []
    for segment, start, end in plan:
        if segment == name:
            out += list(range(int(math.ceil((start + 2.0 / FPS) * FPS)), int((end - 2.0 / FPS) * FPS) + 1))
    return out


class AnalyseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples, cls.plan = voice()
        cls.frames = lipsync.analyse(cls.samples, RATE, FPS)

    def test_vowels_from_a_synthetic_voice(self):
        for name in lipsync.VOWELS:
            inside = frames_inside(self.plan, name)
            right = [f for f in inside if max(lipsync.VOWELS, key=lambda v: self.frames[f][v]) == name]
            self.assertGreaterEqual(len(right), 0.8 * len(inside), (name, len(right), len(inside)))
        for frame in frames_inside(self.plan, None):
            self.assertLess(self.frames[frame]["open"], 0.05, frame)
        for frame in self.frames:
            self.assertAlmostEqual(sum(frame[v] for v in lipsync.VOWELS), frame["open"], places=5)

    def test_stereo_48k_long(self):
        one, _plan = voice(48000)
        long = np.tile(one, int(math.ceil(180.0 / (len(one) / 48000.0))))[:180 * 48000]
        path = write_wav(long, 48000, channels=2)
        start = time.perf_counter()
        samples, rate = lipsync.read(path)
        frames = lipsync.analyse(samples, rate, FPS)
        self.assertLess(time.perf_counter() - start, 10.0)
        self.assertEqual(rate, 48000)
        self.assertEqual(len(samples.shape), 1)
        self.assertEqual(len(frames), 180 * FPS)


def talking_character(jaw=False, mouth_2d=False, vowel_keys=("aa", "ih", "ou", "ee", "oh")):
    """The rig's test character with vowel shape keys on its Body, built, playing a clip "Talk"."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    body = objs["Body"]
    body.shape_key_add(name="Basis")
    for name in vowel_keys:
        body.shape_key_add(name=name)
    ui.add_part(rig, body, 'BODY')
    if jaw:
        face.chin(body)
        ui.add_part(rig, body, 'JAW', name="Chin", scope='VERTEX_GROUP', vertex_group="Chin")
    card = None
    if mouth_2d:
        card, _mat = face.mouth_card(rig)
        ui.add_part(rig, card, 'MOUTH_2D')
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    clips.new(rig, list(bpy.context.view_layer.objects), "Talk", scene=bpy.context.scene)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    bpy.context.view_layer.objects.active = body
    return rig, body, card


def paths_in(clip, idb):
    anim = idb.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(clip, anim.action_slot) if anim and anim.action == clip else None
    return {fc.data_path for fc in bag.fcurves} if bag is not None else set()


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.samples, self.plan = voice()
        self.path = write_wav(self.samples, RATE)

    def test_keys_go_into_the_clip(self):
        rig, body, card = talking_character(jaw=True, mouth_2d=True)
        talk = bpy.data.actions["Talk"]
        frames = lipsync.analyse(*lipsync.read(self.path), FPS)
        done = lipsync.apply(body, rig, frames, start_frame=1)
        self.assertEqual(done, {"shape_keys": 5, "jaw": True, "mouth": True})
        keys = paths_in(talk, body.data.shape_keys)
        for name in ("aa", "ih", "ou", "ee", "oh"):
            self.assertIn('key_blocks["%s"].value' % name, keys)
        self.assertTrue(any("Jaw" in p for p in paths_in(talk, rig)))
        self.assertIn('["%s"]' % mouth.PROP, paths_in(talk, card))
        # In the middle of the A, the mouth is open: the jaw down, the A cell shown.
        frame = 1 + frames_inside(self.plan, "A")[3]
        bpy.context.scene.frame_set(frame)
        self.assertGreater(body.data.shape_keys.key_blocks["aa"].value, 0.3)
        self.assertEqual(card[mouth.PROP], mouth.CELLS["A"])
        bpy.context.view_layer.update()
        rest = rig.data.bones["Jaw"].tail_local
        self.assertLess((rig.pose.bones["Jaw"].tail).z, rest.z - 1e-4)
        bpy.context.scene.frame_set(1 + frames_inside(self.plan, None)[1])
        self.assertEqual(card[mouth.PROP], mouth.CELLS["CLOSED"])

    def test_vowel_names(self):
        for names in (("A", "I", "U", "E", "O"), ("Fcl_MTH_A", "Fcl_MTH_I", "Fcl_MTH_U", "Fcl_MTH_E", "Fcl_MTH_O")):
            _rig, body, _card = talking_character(vowel_keys=names)
            found = lipsync.vowel_keys(body.data.shape_keys)
            self.assertEqual([found[v].name for v in lipsync.VOWELS], list(names))

    def test_nothing_to_key(self):
        _rig, body, _card = talking_character(vowel_keys=("Smile",))
        with self.assertRaisesRegex(RuntimeError, "vowel"):
            bpy.ops.dasktoon.lip_sync_from_audio(filepath=self.path)

    def test_operator_takes_the_first_sound_strip(self):
        _rig, body, _card = talking_character()
        editor = bpy.context.scene.sequence_editor_create()
        editor.strips.new_sound("Voice", self.path, 1, 10)
        self.assertEqual(bpy.ops.dasktoon.lip_sync_from_audio(), {'FINISHED'})
        talk = bpy.data.actions["Talk"]
        anim = body.data.shape_keys.animation_data
        bag = anim_utils.action_get_channelbag_for_slot(talk, anim.action_slot)
        curve = next(fc for fc in bag.fcurves if fc.data_path == 'key_blocks["aa"].value')
        self.assertEqual(int(curve.keyframe_points[0].co.x), 10)


if __name__ == "__main__":
    tu.run_tests()
