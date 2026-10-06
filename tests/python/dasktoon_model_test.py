# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models (project workflow spec 6, 12): New Model and its four starting scenes, model names, and what stops it."""

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


if __name__ == "__main__":
    tu.run_tests()
