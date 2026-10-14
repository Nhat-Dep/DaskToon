# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Lip sync from a voice file (anime rig spec 10.3), with what the install has: aud reads the samples, numpy does the
rest.

For each frame: the loudness of a window around it (silence closes the mouth), and the two lowest formants F1 and F2
of the voice there, from a linear prediction (LPC) model; each vowel A I U E O scores by how near its formants are.
The keys go to the vowel shape keys, the Jaw bone when the character has a Jaw part, and dt_mouth of its 2D mouths,
in whatever clip the character plays."""

import math
import re

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from bpy_extras import anim_utils

VOWELS = ("A", "I", "U", "E", "O")
FORMANTS = {"A": (800, 1200), "I": (300, 2300), "U": (350, 1300), "E": (500, 1900), "O": (500, 800)}  # Hz
SPREAD = (250.0, 450.0)  # how far F1 and F2 may be from a vowel's and still sound like it, in Hz
ANALYSIS_RATE = 10000.0
ORDER = 10
SILENCE = 0.1  # loudness below this share of the loud parts closes the mouth
JAW_OPEN = math.radians(20.0)
# Shape key names of each vowel: VRM, VRoid, plain letters, Japanese.
NAMES = {
    "A": (r"^aa$", r"^Fcl_MTH_A$", r"^a$", r"^vrc\.v_aa$", "あ"),
    "I": (r"^ih$", r"^Fcl_MTH_I$", r"^i$", r"^vrc\.v_ih$", "い"),
    "U": (r"^ou$", r"^Fcl_MTH_U$", r"^u$", r"^vrc\.v_ou$", "う"),
    "E": (r"^ee$", r"^Fcl_MTH_E$", r"^e$", r"^vrc\.v_e$", "え"),
    "O": (r"^oh$", r"^Fcl_MTH_O$", r"^o$", r"^vrc\.v_oh$", "お"),
}


class LipSyncError(Exception):
    """Why lip sync cannot run, worded for the user."""


def read(path):
    """(mono samples as float32, sample rate) of a sound file."""
    import aud
    sound = aud.Sound(path)
    data = np.asarray(sound.data(), dtype=np.float32)
    rate = float(sound.specs[0])
    return (data.mean(axis=1) if data.ndim == 2 else data).astype(np.float32), rate


def _resampled(samples, rate):
    """`samples` at ANALYSIS_RATE, a box filter first against aliasing."""
    if rate > ANALYSIS_RATE:
        width = int(rate // ANALYSIS_RATE)
        if width > 1:
            samples = np.convolve(samples, np.ones(width) / width, mode='same')
    times = np.arange(0.0, len(samples) / rate, 1.0 / ANALYSIS_RATE)
    return np.interp(times, np.arange(len(samples)) / rate, samples)


def _lpc(x):
    """Prediction polynomial (1, a1 … aORDER) of `x` by Levinson-Durbin on its autocorrelation; None when silent."""
    r = np.array([np.dot(x[:len(x) - k], x[k:]) for k in range(ORDER + 1)])
    if r[0] <= 1e-12:
        return None
    a = np.zeros(ORDER + 1)
    a[0], error = 1.0, r[0]
    for i in range(1, ORDER + 1):
        k = -(r[i] + np.dot(a[1:i], r[i - 1:0:-1])) / error
        a[1:i] = a[1:i] + k * a[i - 1:0:-1]
        a[i] = k
        error *= 1.0 - k * k
        if error <= 0.0:
            break
    return a


def _formants(a):
    """The formant frequencies of the polynomial `a`, lowest first."""
    roots = np.roots(a)
    roots = roots[roots.imag > 0.0]
    frequencies = np.angle(roots) * ANALYSIS_RATE / (2.0 * math.pi)
    bandwidths = -ANALYSIS_RATE / math.pi * np.log(np.abs(roots))
    return np.sort(frequencies[(frequencies > 90.0) & (bandwidths < 400.0)])


def _scores(f1, f2):
    out = np.array([math.exp(-((f1 - FORMANTS[v][0]) / SPREAD[0]) ** 2 - ((f2 - FORMANTS[v][1]) / SPREAD[1]) ** 2)
                    for v in VOWELS])
    total = out.sum()
    return out / total if total > 1e-9 else np.full(len(VOWELS), 1.0 / len(VOWELS))


def analyse(samples, rate, fps):
    """Per frame (frame 0 at the start of the sound): {"open": 0 to 1, "A" … "O": share of open}."""
    x = _resampled(np.asarray(samples, dtype=float), rate)
    count = int(len(samples) / rate * fps)
    half = int(ANALYSIS_RATE / fps)  # the window spans a frame on each side
    window = np.hanning(2 * half)
    loud = np.zeros(count)
    vowels = np.zeros((count, len(VOWELS)))
    for i in range(count):
        centre = int(i / fps * ANALYSIS_RATE)
        part = x[max(centre - half, 0):centre + half]
        if len(part) < 2 * half:
            part = np.pad(part, (0, 2 * half - len(part)))
        loud[i] = math.sqrt(float(np.mean(part * part)))
        emphasised = np.append(part[0], part[1:] - 0.97 * part[:-1]) * window
        a = _lpc(emphasised)
        found = _formants(a) if a is not None else []
        if len(found) >= 2:
            vowels[i] = _scores(found[0], found[1])
        else:
            vowels[i] = 1.0 / len(VOWELS)
    peak = np.percentile(loud[loud > 0.0], 95) if (loud > 0.0).any() else 0.0
    opening = np.clip(loud / peak, 0.0, 1.0) if peak > 0.0 else loud
    opening[opening < SILENCE] = 0.0
    weights = vowels * opening[:, None]
    kernel = np.ones(3) / 3.0
    opening = np.convolve(opening, kernel, mode='same')
    weights = np.stack([np.convolve(weights[:, j], kernel, mode='same') for j in range(len(VOWELS))], axis=1)
    frames = []
    for i in range(count):
        frame = {"open": float(opening[i])}
        frame.update({v: float(weights[i, j]) for j, v in enumerate(VOWELS)})
        frames.append(frame)
    return frames


def vowel_keys(key):
    """{vowel: shape key} of the vowels `key` has, by their usual names."""
    out = {}
    if key is None:
        return out
    blocks = [b for b in key.key_blocks if b != key.reference_key]
    for vowel, patterns in NAMES.items():
        for pattern in patterns:
            found = next((b for b in blocks if re.search(pattern, b.name, re.IGNORECASE)), None)
            if found is not None:
                out[vowel] = found
                break
    return out


def _curve(id_block, data_path, index, frame):
    """The F-curve of `data_path` in the action `id_block` plays, made by keying it once at `frame` (in the right
    slot; the keys written over that frame replace that key)."""
    id_block.keyframe_insert(data_path=data_path, index=index, frame=frame)
    anim = id_block.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    return next(fc for fc in bag.fcurves if fc.data_path == data_path and fc.array_index == max(index, 0))


def _write(id_block, data_path, index, frames, values, interpolation='LINEAR'):
    """Keys at `frames` with `values` on one F-curve (`index` -1 for a property that is not an array), replacing its
    keys in that range."""
    first, last = float(frames[0]), float(frames[-1])
    curve = _curve(id_block, data_path, index, first)
    for point in reversed(list(curve.keyframe_points)):
        if first - 0.5 <= point.co.x <= last + 0.5:
            curve.keyframe_points.remove(point, fast=True)
    start = len(curve.keyframe_points)
    curve.keyframe_points.add(len(frames))
    co = np.empty(len(curve.keyframe_points) * 2, np.float32)
    curve.keyframe_points.foreach_get("co", co)
    co[start * 2::2] = frames
    co[start * 2 + 1::2] = values
    curve.keyframe_points.foreach_set("co", co)
    for point in curve.keyframe_points[start:]:
        point.interpolation = interpolation
    curve.keyframe_points.sort()
    curve.update()


def apply(obj, rig, frames, start_frame, strength=1.0):
    """Key `frames` (analyse) from `start_frame`: the vowel shape keys of `obj`, the Jaw bone of `rig` when it has a
    Jaw part, dt_mouth of its 2D mouths. Returns what was keyed; LipSyncError when there is nothing to key."""
    from . import mouth
    keys = vowel_keys(obj.data.shape_keys if obj.type == 'MESH' else None)
    parts = list(rig.data.dasktoon_rig.parts) if rig is not None and hasattr(rig.data, "dasktoon_rig") else []
    jaw = rig is not None and rig.pose.bones.get("Jaw") is not None and any(p.role == 'JAW' for p in parts)
    mouths = [p.object for p in parts if p.role == 'MOUTH_2D' and p.object is not None]
    if not keys and not jaw and not mouths:
        raise LipSyncError(rpt_("%s has no vowel shape keys (A I U E O, aa ih ou ee oh…), Jaw part or 2D mouth to "
                                "key") % obj.name)
    times = np.arange(len(frames), dtype=np.float32) + start_frame
    for vowel, block in keys.items():
        _write(obj.data.shape_keys, 'key_blocks["%s"].value' % block.name, -1, times,
               np.array([f[vowel] * strength for f in frames], np.float32))
    if jaw:
        pose = rig.pose.bones["Jaw"]
        # The jaw opens turning down about its X axis: its tip goes down.
        angles = np.array([-f["open"] * strength * JAW_OPEN for f in frames])
        if pose.rotation_mode == 'QUATERNION':
            values = (np.cos(angles / 2.0), np.sin(angles / 2.0), np.zeros(len(frames)), np.zeros(len(frames)))
            path = "rotation_quaternion"
        else:
            values = (angles, np.zeros(len(frames)), np.zeros(len(frames)))
            path = "rotation_euler"
        for index, column in enumerate(values):
            _write(rig, 'pose.bones["Jaw"].%s' % path, index, times, column.astype(np.float32))
    if mouths:
        cells = [mouth.CELLS["CLOSED"] if f["open"] < 0.15 else mouth.CELLS[max(VOWELS, key=lambda v: f[v])]
                 for f in frames]
        for card in mouths:
            _write(card, '["%s"]' % mouth.PROP, -1, times, np.array(cells, np.float32), 'CONSTANT')
    return {"shape_keys": len(keys), "jaw": jaw, "mouth": bool(mouths)}
