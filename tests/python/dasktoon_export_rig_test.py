# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""<Model>.rig.json and the Unity scripts of the anime rig (spec 9.5), and how Engine Export writes them."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_export import rig_json  # noqa: E402
from dasktoon_rig import build  # noqa: E402


def built(roles=(("Body", 'BODY'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT'))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    for name, role in roles:
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    return rig, objs


class RigJsonTest(unittest.TestCase):
    def test_rig_data(self):
        rig, objs = built()
        rig.data.dasktoon_rig.parts["Skirt"].sway_in_unity = 'BAKED'
        rig.data.dasktoon_rig.parts["Hair"].stiffness = 2.5
        data = rig_json.rig_data(rig)
        self.assertEqual(data["version"], 1)
        hair = next(c for c in data["chains"] if c["part"] == "Hair")
        self.assertEqual(hair["bones"], ["Hair_1", "Hair_2", "Hair_3", "Hair_4"])
        self.assertEqual(hair["unity"], "runtime")
        self.assertAlmostEqual(hair["stiffness"], 2.5, places=5)
        self.assertAlmostEqual(hair["lengths"][1], rig.data.bones["Hair_2"].length, places=5)
        skirts = [c for c in data["chains"] if c["part"] == "Skirt"]
        self.assertEqual(len(skirts), 8)
        self.assertEqual({c["unity"] for c in skirts}, {"baked"})
        self.assertEqual([c["bone"] for c in data["colliders"]], list(build.COLLIDER_BONES))
        head = next(c for c in data["colliders"] if c["bone"] == "Head")
        self.assertAlmostEqual(head["length"], rig.data.bones["Head"].length, places=5)
        self.assertEqual(json.loads(rig_json.text(data)), data)
        self.assertEqual(rig_json.runtime_parts(rig), {"Hair"})
        self.assertIs(rig_json.find_rig([objs["Body"], rig]), rig)

    def test_scaled_rig_gives_world_lengths(self):
        rig, _objs = built()
        rig.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        hair = next(c for c in rig_json.rig_data(rig)["chains"] if c["part"] == "Hair")
        self.assertAlmostEqual(hair["lengths"][0], 2.0 * rig.data.bones["Hair_1"].length, places=5)

    def test_no_chains(self):
        rig, objs = built(roles=(("Body", 'BODY'),))
        self.assertIsNone(rig_json.rig_data(rig))
        self.assertIsNone(rig_json.find_rig([rig, objs["Body"]]))


if __name__ == "__main__":
    tu.run_tests()
