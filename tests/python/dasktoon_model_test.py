# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models and drafts (project workflow spec 4, 6, 9, 10, 12): New Model and its four starting scenes, Open, Save, Save to
Project, Save Model As, Save Copy, Save Incremental, drafts and the recent models."""

import os
import sys
import tempfile
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_model as model_ui  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_export import textures as png  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def write_png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png.png_bytes(2, 2, bytes((255, 0, 0, 255)) * 4))
    return path


def read(path):
    with open(path, "rb") as f:
        return f.read()


class ModelTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_model_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        self.base = tempfile.mkdtemp(prefix="dt_model_")
        self.project = dtp.create_project("Hero", os.path.join(self.base, "Hero"))
        project_ui.select_project(self.project)

    def model(self, name):
        return os.path.join(self.project.models_folder, name + ".blend")

    def assertOpen(self, path):
        self.assertTrue(dtp.same_path(bpy.data.filepath, path), bpy.data.filepath)


class NewModelTest(ModelTestCase):
    def test_dasktoon_scene_has_a_sun_a_camera_on_the_origin_and_the_dasktoon_look(self):
        tu.add_sphere(segments=8, rings=4)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Hero", start_from='DASKTOON'), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        scene = bpy.context.scene
        self.assertEqual(sorted((obj.type, obj.name) for obj in scene.objects), [('CAMERA', "Camera"), ('LIGHT', "Sun")])
        self.assertEqual(scene.objects["Sun"].data.type, 'SUN')
        camera = scene.camera
        self.assertEqual(camera.name, "Camera")
        view = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        self.assertAlmostEqual(view.angle(-camera.location), 0.0, places=4)
        self.assertEqual((scene.render.engine, scene.view_settings.view_transform), ('DASKTOON_ANIME', 'Standard'))
        self.assertTrue(os.path.isfile(self.model("Hero")))

    def test_empty_scene_is_empty(self):
        tu.add_sphere(segments=8, rings=4)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Blank", start_from='EMPTY'), {'FINISHED'})
        self.assertOpen(self.model("Blank"))
        self.assertEqual(len(bpy.data.objects), 0)

    def test_current_scene_becomes_the_model(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Body Model", start_from='CURRENT'), {'FINISHED'})
        self.assertOpen(self.model("Body Model"))
        self.assertIn("Body", bpy.data.objects)

    def test_copy_of_model_starts_from_the_chosen_model(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        bpy.ops.dasktoon.model_new(name="A", start_from='CURRENT')
        before = read(self.model("A"))
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="B", start_from='COPY', copy_from="Models/A.blend"),
                         {'FINISHED'})
        self.assertOpen(self.model("B"))
        self.assertIn("Body", bpy.data.objects)
        self.assertEqual(read(self.model("A")), before)

    def test_a_model_name_is_taken_whatever_the_case(self):
        bpy.ops.dasktoon.model_new(name="Hero", start_from='EMPTY')
        before = read(self.model("Hero"))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="hero", start_from='CURRENT')
        self.assertEqual(read(self.model("Hero")), before)

    def test_odd_characters_become_underscores_and_vietnamese_names_work(self):
        image = bpy.data.images.load(write_png(os.path.join(self.base, "Ảnh nguồn", "da.png")))
        image.use_fake_user = True
        self.assertEqual(bpy.ops.dasktoon.model_new(name='Nhân vật: "A"?', start_from='CURRENT'), {'FINISHED'})
        self.assertOpen(self.model("Nhân vật_ _A__"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "da.png")))
        self.assertTrue(bpy.data.images["da.png"].filepath_raw.startswith("//"))

    def test_a_file_in_the_way_of_models_is_reported(self):
        os.rmdir(self.project.models_folder)
        with open(self.project.models_folder, "wb") as f:
            f.write(b"not a folder")
        tu.add_sphere(segments=8, rings=4)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="Hero", start_from='CURRENT')
        self.assertEqual(bpy.data.filepath, "")

    def test_without_a_project_new_model_reports_it(self):
        project_ui.forget_session_project()
        os.remove(os.path.join(dtp.config_dir(), dtp.RECENT_FILE))
        self.assertIsNone(project_ui.selected_project())
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="Hero", start_from='EMPTY')

    def test_current_scene_is_the_default_for_a_draft_worth_keeping(self):
        self.assertFalse(model_ui.keeps_current(True, "", False))
        self.assertTrue(model_ui.keeps_current(True, "", True))
        self.assertTrue(model_ui.keeps_current(True, "D:/outside/a.blend", False))
        self.assertFalse(model_ui.keeps_current(False, "D:/Hero/Models/a.blend", True))


class DraftTest(ModelTestCase):
    def outside(self, name):
        path = os.path.join(self.base, "outside", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def test_unsaved_scenes_and_outside_files_are_drafts(self):
        self.assertTrue(project_ui.is_draft())
        bpy.ops.wm.save_as_mainfile(filepath=self.outside("a.blend"))
        self.assertTrue(project_ui.is_draft())
        bpy.ops.wm.save_as_mainfile(filepath=self.model("A"))
        self.assertFalse(project_ui.is_draft())

    def test_save_to_project_saves_a_copy_and_leaves_the_draft_file_alone(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        draft = self.outside("draft.blend")
        bpy.ops.wm.save_as_mainfile(filepath=draft)
        before = read(draft)
        tu.add_plane().name = "Floor"
        self.assertEqual(bpy.ops.dasktoon.save_to_project(project=self.project.file, name="Hero"), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        self.assertIn("Floor", bpy.data.objects)
        self.assertEqual(read(draft), before)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.save_to_project(project=self.project.file, name="HERO")

    def test_save_on_a_draft_writes_nothing_without_a_window(self):
        draft = self.outside("draft.blend")
        bpy.ops.wm.save_as_mainfile(filepath=draft)
        before = read(draft)
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'CANCELLED'})
        self.assertEqual(bpy.ops.dasktoon.model_save_as(name="X"), {'CANCELLED'})
        self.assertEqual(read(draft), before)
        self.assertEqual(os.listdir(self.project.models_folder), [])

    def test_a_model_whose_project_file_is_gone_is_a_draft(self):
        bpy.ops.wm.save_as_mainfile(filepath=self.model("A"))
        os.remove(self.project.file)
        self.assertTrue(project_ui.is_draft())
        before = read(self.model("A"))
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'CANCELLED'})
        self.assertEqual(read(self.model("A")), before)


class SaveTest(ModelTestCase):
    def setUp(self):
        super().setUp()
        texture = write_png(os.path.join(self.base, "outside", "skin.png"))
        bpy.data.images.load(texture).use_fake_user = True
        tu.add_sphere(segments=8, rings=4).name = "Body"
        bpy.ops.wm.save_as_mainfile(filepath=self.model("Hero"))  # a script save: the texture stays outside

    def test_save_copies_outside_textures_then_saves_in_place(self):
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "skin.png")))
        self.assertEqual(bpy.data.images["skin.png"].filepath_raw, "//../Textures/skin.png")

    def test_save_model_as_switches_to_the_new_model(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_as(name="Hero2"), {'FINISHED'})
        self.assertOpen(self.model("Hero2"))
        self.assertTrue(os.path.isfile(self.model("Hero")))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_save_as(name="hero")

    def test_save_copy_keeps_the_current_file(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_copy(name="Backup"), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        with bpy.data.libraries.load(self.model("Backup")) as (src, _dst):
            self.assertIn("Body", src.objects)

    def test_save_incremental_numbers_the_file_next_to_it(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_incremental(), {'FINISHED'})
        self.assertOpen(self.model("Hero_001"))
        bpy.ops.dasktoon.model_save_incremental()
        self.assertOpen(self.model("Hero_002"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "skin.png")))

    def test_copy_and_incremental_need_a_model_of_a_project(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertFalse(bpy.ops.dasktoon.model_save_copy.poll())
        self.assertFalse(bpy.ops.dasktoon.model_save_incremental.poll())


class OpenTest(ModelTestCase):
    def test_open_takes_models_drafts_and_projects(self):
        model = self.model("Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        outside = os.path.join(self.base, "outside", "loose.blend")
        os.makedirs(os.path.dirname(outside))
        bpy.ops.wm.save_as_mainfile(filepath=outside)
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual(bpy.ops.dasktoon.open(filepath=model), {'FINISHED'})
        self.assertOpen(model)
        self.assertFalse(project_ui.is_draft())
        bpy.ops.dasktoon.open(filepath=outside)
        self.assertOpen(outside)
        self.assertTrue(project_ui.is_draft())
        other = dtp.create_project("Other", os.path.join(self.base, "Other"))
        project_ui.select_project(self.project)
        self.assertEqual(bpy.ops.dasktoon.open(filepath=other.file), {'FINISHED'})
        self.assertEqual(project_ui.selected_project().name, "Other")
        self.assertOpen(outside)

    def test_open_reports_a_missing_file(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.open(filepath=os.path.join(self.base, "missing.blend"))


class RecentModelsTest(ModelTestCase):
    def test_models_are_remembered_and_drafts_are_not(self):
        model = self.model("Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        model_ui.remember(model)
        model_ui.remember(os.path.join(self.base, "outside", "loose.blend"))
        self.assertEqual(dtp.recent_models(), [model])
        self.assertEqual(dtp.recent_projects()[0], self.project.file)
        self.assertIn(model_ui.remember_on_file_change, bpy.app.handlers.load_post)
        self.assertIn(model_ui.remember_on_file_change, bpy.app.handlers.save_post)

    def test_the_commands_the_core_hands_over_to_are_registered(self):
        for name in ("model_new", "open", "project_save", "model_save_incremental", "model_save_as", "model_save_copy"):
            self.assertTrue(hasattr(bpy.types, "DASKTOON_OT_" + name), name)


if __name__ == "__main__":
    tu.run_tests()
