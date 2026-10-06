# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects on disk (unity export spec 7; project workflow spec 3, 4, 11, 12): creation with or without Unity,
Models/ and Textures/, older projects, the model list, names, recent projects and models, settings, linking Unity later."""

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

SHADER = os.path.join("Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_proj_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


def touch(path, data=b""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ProjectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_proj_config_")
        tu.reset_scene()
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_proj_"), "MyProject")

    def test_create_without_unity_makes_models_and_textures(self):
        project = dtp.create_project("Dự án của tôi", self.folder)
        self.assertEqual(read_json(os.path.join(self.folder, dtp.PROJECT_FILE)),
                         {"version": 1, "name": "Dự án của tôi", "engines": []})
        self.assertTrue(os.path.isdir(os.path.join(self.folder, "Models")))
        self.assertTrue(os.path.isdir(os.path.join(self.folder, "Textures")))
        self.assertEqual((project.engine, project.engine_path), ("", ""))
        self.assertEqual(dtp.recent_projects(), [project.file])

    def test_create_with_unity_links_it_and_installs_the_shaders(self):
        dtp.create_project("P", self.folder, self.unity)
        self.assertEqual(read_json(os.path.join(self.folder, dtp.PROJECT_FILE))["engines"],
                         [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}])
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))

    def test_a_bad_unity_path_creates_nothing(self):
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, tempfile.mkdtemp(prefix="dt_not_unity_"))
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, self.unity, 'GODOT_4')
        self.assertFalse(os.path.exists(self.folder))

    def test_existing_project_is_not_overwritten(self):
        dtp.create_project("P", self.folder)
        with self.assertRaises(ValueError):
            dtp.create_project("Q", self.folder)
        self.assertEqual(dtp.load(self.folder).name, "P")

    def test_a_folder_with_files_becomes_a_project_and_its_blend_files_models(self):
        touch(os.path.join(self.folder, "Hero.blend"))
        touch(os.path.join(self.folder, "notes.txt"))
        project = dtp.create_project("P", self.folder)
        self.assertEqual(dtp.project_models(project), [os.path.join(self.folder, "Hero.blend")])

    def test_model_list_puts_models_first_and_skips_backups_textures_and_hidden_folders(self):
        project = dtp.create_project("P", self.folder)
        for rel in ("Models/b.blend", "Models/A.blend", "Models/A.blend1", "Root.blend", "sub/x.blend",
                    "Textures/t.blend", ".hidden/h.blend"):
            touch(os.path.join(self.folder, *rel.split("/")))
        models = dtp.project_models(project)
        self.assertEqual([dtp.model_label(project, path) for path in models], ["A", "b", "Root.blend", "sub/x.blend"])

    def test_model_scan_skips_unity_library_folders(self):
        project = dtp.create_project("P", self.folder)
        for rel in ("Game/Assets/model.blend", "Game/Library/cache.blend", "Game/Temp/t.blend"):
            touch(os.path.join(self.folder, *rel.split("/")))
        touch(os.path.join(self.folder, *["d%d" % i for i in range(dtp.MAX_SCAN_DEPTH + 2)], "deep.blend"))
        self.assertEqual(dtp.project_models(project), [os.path.join(self.folder, "Game", "Assets", "model.blend")])

    def test_older_project_keeps_its_blend_files_at_the_root(self):
        os.makedirs(self.folder)
        dtp.save(dtp.Project(self.folder, "Old", [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}]))
        hero = touch(os.path.join(self.folder, "Hero.blend"), b"old model")
        project = dtp.find_project(hero)
        self.assertEqual((project.name, project.engine), ("Old", 'UNITY_URP'))
        self.assertFalse(os.path.exists(project.models_folder))
        self.assertEqual(dtp.project_models(project), [hero])
        self.assertEqual(dtp.new_model_path(project, "Sword"), os.path.join(self.folder, "Models", "Sword.blend"))
        self.assertTrue(os.path.isdir(project.models_folder))
        with open(hero, "rb") as f:
            self.assertEqual(f.read(), b"old model")

    def test_names_lose_the_characters_windows_refuses(self):
        self.assertEqual(dtp.clean_name(' Hero: "Boss"? '), "Hero_ _Boss__")
        self.assertEqual(dtp.clean_name("a/b\\c"), "a_b_c")
        self.assertEqual(dtp.clean_name("Hero."), "Hero")
        self.assertEqual(dtp.clean_name("Nhân vật"), "Nhân vật")
        for empty in ("", "   ", "..."):
            with self.assertRaises(ValueError):
                dtp.clean_name(empty)

    def test_model_names_are_unique_whatever_the_case(self):
        project = dtp.create_project("P", self.folder)
        mine = touch(os.path.join(project.models_folder, "Hero.blend"), b"mine")
        with self.assertRaises(ValueError):
            dtp.new_model_path(project, "hero")
        self.assertTrue(dtp.model_exists(project, "HERO"))
        self.assertEqual(dtp.free_model_name(project, "Hero"), "Hero_1")
        self.assertEqual(dtp.free_model_name(project, "Sword"), "Sword")
        self.assertEqual(dtp.free_model_name(project, "  "), "Untitled")
        self.assertEqual(dtp.new_model_path(project, "A/B"), os.path.join(project.models_folder, "A_B.blend"))
        with open(mine, "rb") as f:
            self.assertEqual(f.read(), b"mine")

    def test_incremental_names(self):
        folder = tempfile.mkdtemp(prefix="dt_proj_inc_")
        hero = touch(os.path.join(folder, "Hero.blend"))
        self.assertEqual(os.path.basename(dtp.incremental_path(hero)), "Hero_001.blend")
        touch(os.path.join(folder, "Hero_001.blend"))
        self.assertEqual(os.path.basename(dtp.incremental_path(hero)), "Hero_002.blend")
        self.assertEqual(os.path.basename(dtp.incremental_path(os.path.join(folder, "Hero_001.blend"))),
                         "Hero_002.blend")
        self.assertEqual(os.path.basename(dtp.incremental_path(os.path.join(folder, "Take9.blend"))), "Take10.blend")

    def test_project_is_found_from_a_subfolder(self):
        dtp.create_project("P", self.folder)
        self.assertEqual(dtp.find_project(os.path.join(self.folder, "characters", "hero", "hero.blend")).name, "P")
        self.assertIsNone(dtp.find_project(os.path.join(tempfile.mkdtemp(), "loose.blend")))
        self.assertIsNone(dtp.find_project(""))
        self.assertTrue(dtp.is_inside(os.path.join(self.folder, "Models", "a.blend"), self.folder))
        self.assertFalse(dtp.is_inside(self.folder + "2", self.folder))

    def test_recent_projects_keep_the_eight_newest(self):
        files = []
        for i in range(10):
            project = dtp.Project(os.path.join(tempfile.mkdtemp(prefix="dt_recent_"), "P%d" % i), "P%d" % i, [])
            dtp.save(project)
            dtp.add_recent(project.file)
            files.append(project.file)
        dtp.add_recent(files[5])
        recent = dtp.recent_projects()
        self.assertEqual(len(recent), dtp.MAX_RECENT)
        self.assertEqual(recent[:2], [files[5], files[9]])

    def test_recent_models_keep_the_ten_newest_existing_files(self):
        folder = tempfile.mkdtemp(prefix="dt_recent_models_")
        paths = [touch(os.path.join(folder, "m%d.blend" % i)) for i in range(12)]
        for path in paths:
            dtp.add_recent_model(path)
        dtp.add_recent_model(paths[3])
        os.remove(paths[11])
        recent = dtp.recent_models()
        self.assertEqual(recent[0], paths[3])
        self.assertNotIn(paths[11], recent)
        self.assertEqual(len(recent), dtp.MAX_RECENT_MODELS - 1)

    def test_settings_remember_where_projects_go(self):
        self.assertEqual(dtp.project_location(), dtp.default_location())
        self.assertEqual(os.path.basename(dtp.default_location()), "DaskToon Projects")
        place = tempfile.mkdtemp(prefix="dt_proj_place_")
        dtp.set_project_location(place)
        self.assertEqual(dtp.project_location(), place)
        self.assertEqual(read_json(os.path.join(dtp.config_dir(), dtp.SETTINGS_FILE)), {"project_location": place})
        os.rmdir(place)
        self.assertEqual(dtp.project_location(), dtp.default_location())

    def test_unity_can_be_linked_later(self):
        project = dtp.create_project("P", self.folder)
        dtp.link_engine(project, 'UNITY_URP', self.unity)
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))
        self.assertEqual(dtp.load(self.folder).engine_path, self.unity.replace("\\", "/"))
        os.remove(os.path.join(self.unity, SHADER))
        dtp.link_engine(project, 'UNITY_URP', self.unity)  # same project: nothing is installed again
        self.assertFalse(os.path.isfile(os.path.join(self.unity, SHADER)))
        other = fake_unity()
        dtp.link_engine(project, 'UNITY_URP', other)
        self.assertTrue(os.path.isfile(os.path.join(other, SHADER)))
        with self.assertRaises(ValueError):
            dtp.link_engine(project, 'UNITY_URP', tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertEqual(dtp.load(self.folder).engine_path, other.replace("\\", "/"))
        dtp.link_engine(project, 'UNITY_URP', "")
        self.assertEqual(dtp.load(self.folder).engines, [])

    def test_project_target_writes_into_the_unity_project(self):
        project = dtp.create_project("P", self.folder, self.unity)
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
