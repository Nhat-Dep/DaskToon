# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Simple mode must keep today's look (spec 3.2).

Capture BEFORE the refactor:  DaskToon.exe -b --factory-startup --python dasktoon_shading_baseline.py -- --capture
Check (normal test run):      same command without --capture.
"""

import json
import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

BASELINE = os.path.join(tu.DATA_DIR, "shading_baseline.json")
GRID = 5


def cases():
    result = []
    for node in ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'):
        for sun in (0.4, 1.0, 1.6, 3.0):
            for thr in (0.3, 0.46, 0.7):
                result.append({"node": node, "sun": sun, "thr": thr, "soft": 0.035})
        result.append({"node": node, "sun": 1.0, "thr": 0.46, "soft": 0.3})
    for mode in ('OVERLAY', 'HUE', 'HUE_SAT', 'SAT', 'VAL', 'MULTIPLY', 'MIX'):
        result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.0, "thr": 0.46, "soft": 0.035,
                       "use_ambient": True, "ambient_mode": mode, "world": [0.2, 0.3, 0.6]})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 2.0, "thr": 0.46, "soft": 0.035,
                   "use_light": True, "sun_color": [1.0, 0.6, 0.4]})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_rim": True})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_grade": True})
    result.append({"node": 'ShaderNodeDaskCel', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_outline": True})
    return result


def case_key(case):
    return json.dumps(case, sort_keys=True)


def render_case(case):
    tu.reset_scene()
    tu.set_world_color(case.get("world", (0.0, 0.0, 0.0)))
    tu.add_sun(case["sun"], rotation=(0.6, 0.3, 0.0), color=case.get("sun_color", (1.0, 1.0, 1.0)))
    obj = tu.add_sphere()
    mat, node = tu.node_material("Case", case["node"])
    tu.assign(obj, mat)
    node.inputs["Shadow Threshold"].default_value = case["thr"]
    node.inputs["Shadow Softness"].default_value = case["soft"]
    for flag in ("use_ambient", "use_light", "use_rim", "use_grade"):
        if case.get(flag):
            setattr(node, flag, True)
    if "ambient_mode" in case:
        node.ambient_mode = case["ambient_mode"]
        node.inputs["Use Custom Color"].default_value = False
    if "Use Outline" in node.inputs:
        node.inputs["Use Outline"].default_value = bool(case.get("use_outline"))
        node.inputs["Outline Width"].default_value = 0.004
    bpy.app.handlers.depsgraph_update_post.clear()  # isolate shading from any outline handler
    pixels, (w, h) = tu.render_pixels("baseline")
    samples = []
    for gy in range(GRID):
        for gx in range(GRID):
            x = int((gx + 0.5) * w / GRID)
            y = int((gy + 0.5) * h / GRID)
            i = (y * w + x) * 4
            samples.extend(round(v, 6) for v in pixels[i:i + 3])
    return samples


class SimpleModeBaseline(unittest.TestCase):
    def test_simple_mode_matches_baseline(self):
        with open(BASELINE, encoding="utf-8") as f:
            stored = json.load(f)
        for case in cases():
            with self.subTest(case=case_key(case)):
                got = render_case(case)
                want = stored[case_key(case)]
                worst = max(abs(a - b) for a, b in zip(got, want))
                self.assertLess(worst, 1e-3)


def capture():
    data = {case_key(case): render_case(case) for case in cases()}
    os.makedirs(tu.DATA_DIR, exist_ok=True)
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=0, sort_keys=True)
    print("captured", len(data), "cases into", BASELINE)


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture()
    else:
        tu.run_tests()
