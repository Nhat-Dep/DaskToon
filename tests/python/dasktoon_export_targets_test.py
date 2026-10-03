# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Export destinations (PROJECT / FOLDER) and safe writing next to .meta files (spec 4)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import assets, targets, unity_yaml  # noqa: E402


def fake_unity_project(parent, name="Game"):
    root = os.path.join(parent, name)
    os.makedirs(os.path.join(root, "Assets", "Characters"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class TargetsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dt_targets_")

    def test_unity_project_is_found_from_a_subfolder(self):
        project = fake_unity_project(self.tmp)
        self.assertEqual(targets.find_unity_project(os.path.join(project, "Assets", "Characters")), project)
        self.assertTrue(targets.is_unity_project(project))
        self.assertIsNone(targets.find_unity_project(self.tmp))

    def test_project_mode_writes_into_assets_dasktoon(self):
        project = fake_unity_project(self.tmp)
        target = targets.make_target(os.path.join(project, "Assets", "Characters"), "Hero")
        self.assertEqual(target.mode, 'PROJECT')
        self.assertEqual(target.root, os.path.join(project, "Assets", "DaskToon"))
        self.assertEqual(target.project, project)
        self.assertEqual(target.name, "Hero")

    def test_folder_mode_makes_name_unity_folder(self):
        target = targets.make_target(self.tmp, "Hero")
        self.assertEqual(target.mode, 'FOLDER')
        self.assertEqual(target.root, os.path.join(self.tmp, "Hero_Unity"))

    def test_blend_name(self):
        self.assertEqual(targets.blend_name(""), "Untitled")
        self.assertEqual(targets.blend_name("C:/work/Hero.blend"), "Hero")

    def test_target_is_remembered_per_blend_file(self):
        tu.reset_scene()
        scene = bpy.context.scene
        self.assertIsNone(targets.remembered_target(scene))
        targets.remember_target(scene, self.tmp, 'UNITY_URP')
        self.assertEqual(targets.remembered_target(scene), (self.tmp, 'UNITY_URP'))


class AssetsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="dt_assets_")
        self.guid = unity_yaml.guid_for("Hero", "Hero/Materials/Skin.mat")

    def read(self, relpath):
        with open(os.path.join(self.root, relpath), "rb") as f:
            return f.read()

    def test_writes_file_and_meta_and_overwrites_its_own_file(self):
        warnings = []
        meta = unity_yaml.material_meta(self.guid)
        self.assertTrue(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, meta, warnings, data=b"one"))
        self.assertTrue(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, meta, warnings, data=b"two"))
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"two")
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero/Materials/Skin.mat.meta")), self.guid)
        self.assertEqual(warnings, [])
        self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(os.path.join(self.root, "Hero/Materials"))))

    def test_never_overwrites_a_user_file(self):
        os.makedirs(os.path.join(self.root, "Hero/Materials"))
        with open(os.path.join(self.root, "Hero/Materials/Skin.mat"), "wb") as f:
            f.write(b"user")
        warnings = []
        ok = assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, unity_yaml.material_meta(self.guid),
                                warnings, data=b"dasktoon")
        self.assertFalse(ok)
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"user")
        self.assertFalse(os.path.exists(os.path.join(self.root, "Hero/Materials/Skin.mat.meta")))
        self.assertEqual(len(warnings), 1)
        other = unity_yaml.material_meta("f" * 32)
        with open(os.path.join(self.root, "Hero/Materials/Skin.mat.meta"), "w", encoding="utf-8") as f:
            f.write(other)
        self.assertFalse(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid,
                                            unity_yaml.material_meta(self.guid), warnings, data=b"dasktoon"))
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"user")

    def test_writer_callback(self):
        def writer(path):
            with open(path, "wb") as f:
                f.write(b"fbx")
        self.assertTrue(assets.write_asset(self.root, "Hero/Model/Hero.fbx", self.guid, unity_yaml.default_meta(self.guid),
                                           [], writer=writer))
        self.assertEqual(self.read("Hero/Model/Hero.fbx"), b"fbx")

    def test_folder_meta_is_written_once(self):
        assets.ensure_folder(self.root, "Hero", "a" * 32)
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero.meta")), "a" * 32)
        assets.ensure_folder(self.root, "Hero", "b" * 32)
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero.meta")), "a" * 32)
        self.assertIn("folderAsset: yes", self.read("Hero.meta").decode("utf-8"))


if __name__ == "__main__":
    tu.run_tests()
