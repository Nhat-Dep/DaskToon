# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The anime rig in Unity 6000.5 (spec 9.5): the importer adds the spring bones and colliders from <model>.rig.json, and
20 steps of the C# spring bone match dasktoon_rig/spring.py. Runs Unity in batchmode on the harness's throwaway project."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
import dasktoon_export  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_rig import build, spring, sway  # noqa: E402

STEPS = 20
DT = 1.0 / 30.0


def to_unity(v):
    return [-float(v[0]), float(v[2]), -float(v[1])]


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityRigTest(unittest.TestCase):
    def test_spring_bones_match_dasktoon(self):
        root = harness.ensure_project()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        for name, role in (("Body", 'BODY'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
            ui.add_part(rig, objs[name], role)
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        target = targets.make_target(root, "DTRig")
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [rig, objs["Body"], objs["Hair"], objs["Skirt"]],
                                           options)
        self.assertEqual(rep.rig, "DTRig/Model/DTRig.rig.json")
        names = dict(sway.chains(rig))["Hair"]
        pose = sway.chain_pose(rig, names)
        part = rig.data.dasktoon_rig.parts["Hair"]
        params = spring.Params(part.stiffness, part.gravity, part.drag, part.radius)
        state = spring.reset(pose)
        colliders = sway.world_colliders(rig)
        for _ in range(STEPS):
            spring.step(state, pose, params, colliders, DT)
        expected = [c for tail in state.current for c in to_unity(tail)]
        result = harness.run_method("DaskToonRigTests.CheckRig", {
            "model": "Assets/DaskToon/DTRig/Model/DTRig.fbx", "chainRoot": names[0], "steps": STEPS, "dt": DT,
            "expected": expected})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["scripts"])
        self.assertTrue(result["imported"])
        self.assertEqual(result["springs"], 9)
        self.assertEqual(result["colliders"], len(build.COLLIDER_BONES))
        self.assertTrue(result["chainFound"])
        self.assertLess(result["offAxis"], 1e-3)
        self.assertLess(result["maxError"], 2e-3)


if __name__ == "__main__":
    tu.run_tests()
