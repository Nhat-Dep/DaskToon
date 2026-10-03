# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon project operators and the Engine Export default target (spec 7). Panels are checked by hand."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_engine_export as export_ui  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_projui_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class ProjectUITest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_projui_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        body = tu.add_sphere(segments=8, rings=4)
        body.name = "Body"
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_projui_"), "Proj")

    def create(self):
        return bpy.ops.dasktoon.project_create(name="Proj", folder=self.folder, engine='UNITY_URP',
                                               engine_path=self.unity, save_current=True)

    def test_create_makes_the_saved_file_part_of_the_project(self):
        self.assertEqual(self.create(), {'FINISHED'})
        self.assertEqual(project_ui.active_project().name, "Proj")
        self.assertTrue(bpy.data.filepath.startswith(os.path.abspath(self.folder)))

    def test_create_reports_a_bad_unity_path(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_create(name="Proj", folder=self.folder, engine='UNITY_URP',
                                            engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))

    def test_open_sets_the_session_project_for_an_unsaved_file(self):
        project = dtp.create_project("Opened", self.folder, 'UNITY_URP', self.unity)
        self.assertIsNone(project_ui.active_project())
        self.assertEqual(bpy.ops.dasktoon.project_open(filepath=project.file), {'FINISHED'})
        self.assertEqual(project_ui.active_project().name, "Opened")
        self.assertEqual(dtp.recent_projects()[0], project.file)

    def test_export_this_model_writes_into_the_unity_project(self):
        self.create()
        self.assertEqual(bpy.ops.dasktoon.project_export(), {'FINISHED'})
        name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", name, "Materials", "Skin.mat")))
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", name, "Model", name + ".fbx")))

    def test_reinstall_shaders_rewrites_edited_files(self):
        self.create()
        shader = os.path.join(self.unity, "Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")
        with open(shader, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertEqual(bpy.ops.dasktoon.project_reinstall_shaders(), {'FINISHED'})
        with open(shader, encoding="utf-8") as f:
            self.assertNotEqual(f.read(), "edited")

    def test_engine_export_opens_on_the_project(self):
        self.create()
        self.assertEqual(export_ui.default_directory(bpy.context), (self.unity.replace("\\", "/"), 'UNITY_URP'))

    def test_ui_is_registered(self):
        self.assertTrue(hasattr(bpy.types, "VIEW3D_PT_dasktoon_project"))
        self.assertTrue(hasattr(bpy.types, "TOPBAR_MT_dasktoon_project"))
        ours = [f for f in bpy.types.TOPBAR_MT_file._dyn_ui_initialize()
                if getattr(f, "__module__", "") == project_ui.__name__ and f.__name__ == "menu_func_file"]
        self.assertEqual(len(ours), 1)


if __name__ == "__main__":
    tu.run_tests()
