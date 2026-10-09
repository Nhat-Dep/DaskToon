# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Projects in the interface (project workflow spec 3, 6, 7, 11): the selected project, New Project, Open Project,
choosing a project, Project Settings, Export This Model and Reinstall Shaders before Unity is linked, the Project and
Models menus, the top bar label, and the Engine Export default target."""

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

SHADER = os.path.join("Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")


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
        self.location = tempfile.mkdtemp(prefix="dt_projui_")

    def create(self, name="Proj", unity=True):
        return bpy.ops.dasktoon.project_create(name=name, location=self.location,
                                               engine_path=self.unity if unity else "")

    def save_model(self, name="Hero"):
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(project_ui.selected_project(), name))

    def test_new_project_is_selected_and_its_location_remembered(self):
        self.assertEqual(self.create(unity=False), {'FINISHED'})
        project = project_ui.selected_project()
        self.assertEqual((project.name, project.engines), ("Proj", []))
        self.assertTrue(dtp.same_path(project.folder, os.path.join(self.location, "Proj")))
        self.assertTrue(os.path.isdir(project.models_folder))
        self.assertTrue(dtp.same_path(dtp.project_location(), self.location))
        self.assertTrue(project_ui.is_draft())

    def test_new_project_cleans_the_name_and_refuses_a_bad_unity_path(self):
        self.assertEqual(self.create(name="A:B", unity=False), {'FINISHED'})
        self.assertTrue(os.path.isdir(os.path.join(self.location, "A_B")))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_create(name="Bad", location=self.location,
                                            engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertFalse(os.path.exists(os.path.join(self.location, "Bad")))

    def test_selected_project_is_the_open_one_then_the_chosen_one_then_the_most_recent(self):
        first = dtp.create_project("First", os.path.join(self.location, "First"))
        second = dtp.create_project("Second", os.path.join(self.location, "Second"))
        self.assertEqual(project_ui.selected_project().name, "Second")
        self.assertEqual(bpy.ops.dasktoon.project_select(filepath=first.file), {'FINISHED'})
        dtp.add_recent(second.file)
        self.assertEqual(project_ui.selected_project().name, "First")
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(second, "Hero"))
        self.assertEqual(project_ui.selected_project().name, "Second")
        self.assertFalse(project_ui.is_draft())

    def test_a_broken_recent_project_is_passed_over(self):
        good = dtp.create_project("Good", os.path.join(self.location, "Good"))
        broken = dtp.create_project("Broken", os.path.join(self.location, "Broken"))
        with open(broken.file, "w", encoding="utf-8") as f:
            f.write("{")
        self.assertEqual(dtp.recent_projects()[0], broken.file)
        self.assertEqual(project_ui.selected_project().name, "Good")
        self.assertIn("Good", tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)))
        self.assertIn(("dasktoon.project_open", "Good"), tu.operators(tu.draw(bpy.types.TOPBAR_MT_file_open_recent)))
        self.assertTrue(dtp.same_path(project_ui.selected_project().file, good.file))

    def test_open_project_takes_the_file_or_the_folder(self):
        project = dtp.create_project("Opened", os.path.join(self.location, "Opened"))
        dtp.create_project("Later", os.path.join(self.location, "Later"))
        self.assertEqual(bpy.ops.dasktoon.project_open(filepath=project.folder), {'FINISHED'})
        self.assertEqual(project_ui.selected_project().name, "Opened")
        self.assertEqual(dtp.recent_projects()[0], project.file)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_open(filepath=tempfile.mkdtemp(prefix="dt_not_project_"))

    def test_project_settings_rename_and_link_unity_later(self):
        self.create(unity=False)
        self.assertEqual(bpy.ops.dasktoon.project_settings(name="Renamed", engine='UNITY_URP',
                                                           engine_path=self.unity), {'FINISHED'})
        project = project_ui.selected_project()
        self.assertEqual((project.name, project.engine_path), ("Renamed", self.unity.replace("\\", "/")))
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_settings(name="Renamed", engine='UNITY_URP',
                                              engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertEqual(project_ui.selected_project().engine_path, self.unity.replace("\\", "/"))

    def test_export_and_reinstall_wait_until_unity_is_linked_then_go_on(self):
        self.create(unity=False)
        self.save_model()
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_export()
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_reinstall_shaders()
        self.assertEqual(bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity,
                                                           then='EXPORT'), {'FINISHED'})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")))

    def test_export_this_model_writes_into_the_unity_project(self):
        self.create()
        self.save_model()
        self.assertEqual(bpy.ops.dasktoon.project_export(), {'FINISHED'})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Model", "Hero.fbx")))

    def test_reinstall_shaders_rewrites_edited_files(self):
        self.create()
        shader = os.path.join(self.unity, SHADER)
        with open(shader, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertEqual(bpy.ops.dasktoon.project_reinstall_shaders(), {'FINISHED'})
        with open(shader, encoding="utf-8") as f:
            self.assertNotEqual(f.read(), "edited")

    def test_engine_export_opens_on_a_linked_project_only(self):
        self.create(unity=False)
        self.assertNotEqual(export_ui.default_directory(bpy.context)[0], self.unity.replace("\\", "/"))
        bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity)
        self.assertEqual(export_ui.default_directory(bpy.context), (self.unity.replace("\\", "/"), 'UNITY_URP'))

    def test_project_menu(self):
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)), ["Create or open a project"])
        self.create(unity=False)
        log = tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)
        self.assertEqual(tu.labels(log), ["Proj", "Engine: not linked"])
        self.assertEqual([idname for idname, _text in tu.operators(log)],
                         ["dasktoon.project_settings", "dasktoon.project_export",
                          "dasktoon.project_reinstall_shaders", "dasktoon.project_open_folder"])
        bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity)
        labels = tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project))
        self.assertEqual(labels[1], "Engine: Unity 6 (URP)")
        self.assertTrue(labels[2].startswith("Shaders: version"))
        menu = bpy.types.TOPBAR_MT_dasktoon_project
        self.assertEqual((menu.bl_label, menu.bl_rna.translation_context), ("Project", "DaskToon"))

    def test_models_menu_lists_the_selected_projects_models(self):
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)), ["Create or open a project"])
        self.create(unity=False)
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)), ["No models yet"])
        self.save_model("Hero")
        project_ui.forget_models()
        log = tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)
        self.assertEqual(tu.operators(log), [("dasktoon.project_open_model", "Hero")])
        self.assertEqual(log[0][3], 'RADIOBUT_ON')

    def test_open_recent_lists_models_then_projects(self):
        self.create(unity=False)
        self.save_model("Hero")
        dtp.add_recent_model(bpy.data.filepath)
        log = tu.draw(bpy.types.TOPBAR_MT_file_open_recent)
        self.assertEqual(tu.operators(log), [("dasktoon.project_open_model", "Proj › Hero"),
                                             ("dasktoon.project_open", "Proj")])

    def test_topbar_label_names_the_model_or_warns_about_a_draft(self):
        layout = tu.RecordingLayout()
        project_ui.draw_topbar_label(layout)
        self.assertEqual([entry[2:4] for entry in layout.log], [("Draft (not in a project)", 'ERROR')])
        self.create(unity=False)
        self.save_model("Hero_Armor")
        layout = tu.RecordingLayout()
        project_ui.draw_topbar_label(layout)
        self.assertEqual([entry[2:4] for entry in layout.log], [("Proj › Hero_Armor", 'FILE_FOLDER')])

    def test_ui_is_registered(self):
        for name in ("TOPBAR_MT_dasktoon_project", "TOPBAR_MT_file_open_recent", "TOPBAR_MT_dasktoon_project_models",
                     "DASKTOON_OT_project_select", "DASKTOON_OT_project_settings"):
            self.assertTrue(hasattr(bpy.types, name), name)
        ours = [f for f in bpy.types.TOPBAR_MT_file._dyn_ui_initialize()
                if getattr(f, "__module__", "") == project_ui.__name__]
        self.assertEqual(ours, [])


if __name__ == "__main__":
    tu.run_tests()
