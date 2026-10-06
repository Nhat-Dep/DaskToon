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


class ScriptsInstallTest(unittest.TestCase):
    def target(self, root, mode='PROJECT'):
        from dasktoon_export import targets
        return targets.ExportTarget('UNITY_URP', mode, root, "Hero", None)

    def test_install_writes_scripts_with_fixed_guids(self):
        from dasktoon_export import scripts_install as si
        root = os.path.join(tempfile.mkdtemp(prefix="dt_scripts_"), "Assets", "DaskToon")
        warnings = []
        self.assertTrue(si.install_scripts(self.target(root), warnings))
        self.assertEqual(warnings, [])
        for rel, guid in si.FILE_GUIDS.items():
            path = os.path.join(root, si.SCRIPT_DIR, *rel.split("/"))
            self.assertTrue(os.path.isfile(path), rel)
            with open(path + ".meta", encoding="utf-8") as f:
                meta = f.read()
            self.assertIn("guid: %s" % guid, meta)
            self.assertIn("MonoImporter:", meta)
        self.assertTrue(os.path.isfile(os.path.join(root, si.SCRIPT_DIR, "Editor.meta")))
        self.assertEqual(si.installed_version(root), si.SCRIPTS_VERSION)
        with open(os.path.join(root, si.SCRIPT_DIR, "DaskToonSpringBone.cs"), encoding="utf-8") as f:
            code = f.read()
        self.assertIn("public void Step(float dt)", code)
        self.assertIn("Vector3.down", code)

    def test_newer_scripts_are_kept(self):
        from dasktoon_export import scripts_install as si
        root = os.path.join(tempfile.mkdtemp(prefix="dt_scripts_"), "Assets", "DaskToon")
        self.assertTrue(si.install_scripts(self.target(root), []))
        with open(os.path.join(root, si.SCRIPT_DIR, si.VERSION_FILE), "w", encoding="utf-8") as f:
            f.write("%d\n" % (si.SCRIPTS_VERSION + 1))
        self.assertFalse(si.install_scripts(self.target(root), []))
        self.assertTrue(si.install_scripts(self.target(root), [], force=True))


def export(rig, objs, folder=None):
    import dasktoon_export
    from dasktoon_export import targets
    target = targets.make_target(folder or tempfile.mkdtemp(prefix="dt_rig_export_"), "Hero")
    options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
    return target, dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)


class ExportRigTest(unittest.TestCase):
    def test_export_writes_rig_json_and_scripts(self):
        from dasktoon_export import scripts_install as si
        rig, objs = built()
        target, rep = export(rig, objs)
        self.assertEqual(rep.rig, "Hero/Model/Hero.rig.json")
        self.assertEqual(rep.scripts, 'INSTALLED')
        path = os.path.join(target.root, "Hero", "Model", "Hero.rig.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["chains"]), 9)
        self.assertTrue(os.path.isfile(path + ".meta"))
        self.assertTrue(os.path.isfile(os.path.join(target.root, si.SCRIPT_DIR, "DaskToonSpringBone.cs")))
        self.assertIn("Hero/Model/Hero.rig.json", "\n".join(rep.lines()))

    def test_no_chains_no_rig_files(self):
        rig, objs = built(roles=(("Body", 'BODY'),))
        target, rep = export(rig, {"Body": objs["Body"]})
        self.assertEqual(rep.rig, "")
        self.assertEqual(rep.scripts, 'SKIPPED')
        self.assertFalse(os.path.exists(os.path.join(target.root, "Hero", "Model", "Hero.rig.json")))
        self.assertFalse(os.path.exists(os.path.join(target.root, "Scripts")))

    def test_runtime_chains_rest_while_the_fbx_is_written(self):
        import dasktoon_export
        from dasktoon_export import model_fbx
        rig, objs = built()
        rig.data.dasktoon_rig.parts["Hair"].sway_in_unity = 'BAKED'
        scene = bpy.context.scene
        hips = rig.pose.bones["Hips"]
        for frame, x in ((1, 0.0), (6, 0.3)):
            hips.location = (x, 0.0, 0.0)
            hips.keyframe_insert("location", frame=frame)
        for frame in range(1, 9):
            scene.frame_set(frame)
        seen = {}
        original = model_fbx.write_fbx

        def spy(context, objects, filepath, include_animation):
            seen["skirt"] = tuple(rig.pose.bones["Skirt1_3"].rotation_quaternion)
            seen["hair"] = tuple(rig.pose.bones["Hair_4"].rotation_quaternion)
            return original(context, objects, filepath, include_animation)

        model_fbx.write_fbx = spy
        try:
            export(rig, objs)
        finally:
            model_fbx.write_fbx = original
        self.assertAlmostEqual(abs(seen["skirt"][0]), 1.0, places=6)   # Runtime: at rest in the FBX
        self.assertLess(abs(seen["hair"][0]), 0.9999)                  # Baked: keeps its sway
        self.assertLess(abs(rig.pose.bones["Skirt1_3"].rotation_quaternion[0]), 0.9999)  # back afterwards

    def test_runtime_chain_with_keys_warns(self):
        from dasktoon_rig import sway
        rig, objs = built()
        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 3
        sway.bake(bpy.context, rig, 1, 3)
        _target, rep = export(rig, objs)
        self.assertTrue(any("Skirt" in w and "twice" in w for w in rep.warnings), rep.warnings)
        self.assertTrue(any("Hair" in w and "twice" in w for w in rep.warnings), rep.warnings)


if __name__ == "__main__":
    tu.run_tests()
