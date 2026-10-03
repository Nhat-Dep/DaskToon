# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects (spec 7): creation, detection, model list, recent list, export into the linked Unity project."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_proj_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class ProjectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_proj_config_")
        tu.reset_scene()
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_proj_"), "MyProject")

    def test_create_writes_json_installs_shaders_and_saves_the_file(self):
        project = dtp.create_project("Dự án của tôi", self.folder, 'UNITY_URP', self.unity, save_current=True)
        with open(os.path.join(self.folder, dtp.PROJECT_FILE), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"version": 1, "name": "Dự án của tôi",
                                "engines": [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}]})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")))
        self.assertEqual(os.path.dirname(bpy.data.filepath), os.path.abspath(self.folder))
        self.assertEqual(dtp.find_project(bpy.data.filepath).name, "Dự án của tôi")
        self.assertEqual(dtp.recent_projects(), [project.file])

    def test_engine_path_must_be_a_unity_project(self):
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, 'UNITY_URP', tempfile.mkdtemp(prefix="dt_not_unity_"))
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, 'GODOT_4', self.unity)

    def test_existing_project_is_not_overwritten(self):
        dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        with self.assertRaises(ValueError):
            dtp.create_project("Q", self.folder, 'UNITY_URP', self.unity)

    def test_project_is_found_from_a_subfolder(self):
        dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        blend = os.path.join(self.folder, "characters", "hero", "hero.blend")
        self.assertEqual(dtp.find_project(blend).name, "P")
        self.assertIsNone(dtp.find_project(os.path.join(tempfile.mkdtemp(), "loose.blend")))
        self.assertIsNone(dtp.find_project(""))

    def test_model_list_skips_backups_and_hidden_folders(self):
        project = dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        for rel in ("a.blend", "a.blend1", os.path.join("sub", "b.blend"), os.path.join(".hidden", "c.blend")):
            path = os.path.join(self.folder, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()
        self.assertEqual(dtp.project_models(project),
                         [os.path.join(self.folder, "a.blend"), os.path.join(self.folder, "sub", "b.blend")])

    def test_recent_list_keeps_the_eight_newest(self):
        files = []
        for i in range(10):
            project = dtp.Project(os.path.join(tempfile.mkdtemp(prefix="dt_recent_"), "P%d" % i), "P%d" % i,
                                  [{"engine": "UNITY_URP", "path": self.unity}])
            dtp.save(project)
            dtp.add_recent(project.file)
            files.append(project.file)
        dtp.add_recent(files[5])
        recent = dtp.recent_projects()
        self.assertEqual(len(recent), dtp.MAX_RECENT)
        self.assertEqual(recent[0], files[5])
        self.assertEqual(recent[1], files[9])

    def test_project_target_writes_into_the_unity_project(self):
        project = dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        target = dtp.project_target(project, "Hero")
        self.assertEqual((target.mode, target.root), ('PROJECT', os.path.join(self.unity, "Assets", "DaskToon")))
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [body], options)
        self.assertEqual(rep.shaders, 'UP_TO_DATE')
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")))
        self.assertTrue(targets.find_unity_project(target.root))


if __name__ == "__main__":
    tu.run_tests()
