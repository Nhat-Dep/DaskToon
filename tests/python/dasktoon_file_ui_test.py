# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The file side of the interface (project workflow spec 5, 7, 9): the start screen in its two states, the File and New
menus, the top bar label, and the shortcuts the File menu shows."""

import importlib.util
import os
import sys
import tempfile
import types
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from bl_ui import dasktoon_splash as splash  # noqa: E402
from bl_ui.space_topbar import TOPBAR_HT_upper_bar  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def window_keymap(module):
    """[(operator, properties)] of the Window keymap of a keymap preset: Blender's or Industry Compatible."""
    path = os.path.join(bpy.utils.system_resource('SCRIPTS'), "presets", "keyconfig", "keymap_data", module + ".py")
    spec = importlib.util.spec_from_file_location("dt_keymap_" + module, path)
    data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data)
    _name, _where, keymap = data.km_window(data.Params())
    return [(idname, dict((options or {}).get("properties", ()))) for idname, _event, options in keymap["items"]]


class FileUITest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_fileui_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        self.base = tempfile.mkdtemp(prefix="dt_fileui_")

    def make_project(self, *models):
        project = dtp.create_project("Hero", os.path.join(self.base, "Hero"))
        for name in models:
            with open(dtp.new_model_path(project, name), "wb"):
                pass
        project_ui.forget_models()
        return project

    def start_screen(self):
        layout = tu.RecordingLayout()
        splash.draw_splash(layout, bpy.context)
        return layout.log

    def test_start_screen_without_a_project(self):
        log = self.start_screen()
        self.assertEqual(tu.operators(log), [
            ("dasktoon.project_create", "New Project…"), ("dasktoon.project_open", "Open Project…"),
            ("dasktoon.model_new", "New Model…"), ("wm.recover_last_session", ""),
            ("dasktoon.continue_as_draft", "")])
        self.assertIn("Create or open a project", tu.labels(log))
        new_model = next(entry for entry in log if entry[1] == "dasktoon.model_new")
        self.assertFalse(new_model[4])

    def test_start_screen_shows_the_selected_projects_models(self):
        hero = self.make_project("Hero", "Sword")
        dtp.create_project("Other", os.path.join(self.base, "Other"))
        project_ui.select_project(hero)
        log = self.start_screen()
        self.assertEqual([entry[1:4] for entry in log if entry[1] == "dasktoon.project_select"],
                         [("dasktoon.project_select", "Hero", 'RADIOBUT_ON'),
                          ("dasktoon.project_select", "Other", 'RADIOBUT_OFF')])
        operators = tu.operators(log)
        self.assertIn(("dasktoon.project_open_model", "Hero"), operators)
        self.assertIn(("dasktoon.project_open_model", "Sword"), operators)
        self.assertIn("Engine: not linked", tu.labels(log))
        self.assertTrue(next(entry for entry in log if entry[1] == "dasktoon.model_new")[4])
        self.assertFalse({"wm.read_homefile", "wm.open_mainfile", "wm.url_open"} & {entry[1] for entry in log})

    def test_a_long_model_list_is_cut_short(self):
        self.make_project(*["M%02d" % i for i in range(splash.MAX_MODELS + 3)])
        log = self.start_screen()
        self.assertEqual(len([e for e in log if e[1] == "dasktoon.project_open_model"]), splash.MAX_MODELS)
        self.assertIn("3 more in File › Models", tu.labels(log))

    def test_splash_menu_draws_the_start_screen(self):
        self.assertIn(("dasktoon.continue_as_draft", ""), tu.operators(tu.draw(bpy.types.WM_MT_splash)))
        self.assertEqual(bpy.ops.dasktoon.continue_as_draft(), {'FINISHED'})

    def test_file_menu(self):
        log = tu.draw(bpy.types.TOPBAR_MT_file)
        entries = [entry[:3] for entry in log if entry[0] in {"operator", "menu"}]
        self.assertEqual(entries[:11], [
            ("operator", "dasktoon.project_create", "New Project…"),
            ("operator", "wm.read_homefile", "New Model…"),
            ("operator", "wm.open_mainfile", "Open…"),
            ("menu", "TOPBAR_MT_file_open_recent", ""),
            ("menu", "TOPBAR_MT_dasktoon_project_models", ""),
            ("operator", "wm.revert_mainfile", ""),
            ("menu", "TOPBAR_MT_file_recover", ""),
            ("operator", "wm.save_mainfile", "Save"),
            ("operator", "wm.save_as_mainfile", "Save Model As…"),
            ("operator", "wm.save_as_mainfile", "Save Copy…"),
            ("operator", "wm.save_mainfile", "Save Incremental")])
        self.assertEqual(entries[-3:], [("menu", "TOPBAR_MT_dasktoon_project", ""),
                                        ("menu", "TOPBAR_MT_file_defaults", ""),
                                        ("operator", "wm.quit_blender", "Quit")])
        self.assertNotIn("TOPBAR_MT_file_new", [entry[1] for entry in entries])
        self.assertEqual({e[2]: e[4] for e in log if e[2] in ("Save Copy…", "Save Incremental")},
                         {"Save Copy…": False, "Save Incremental": False})
        project = self.make_project()
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(project, "Hero"))
        self.assertEqual({e[2]: e[4] for e in tu.draw(bpy.types.TOPBAR_MT_file)
                          if e[2] in ("Save Copy…", "Save Incremental")},
                         {"Save Copy…": True, "Save Incremental": True})

    def test_file_menu_items_carry_the_keymap_shortcuts(self):
        log = tu.draw(bpy.types.TOPBAR_MT_file)
        items = {entry[2]: (entry[1], vars(entry[5])) for entry in log if entry[0] == "operator"}
        default = window_keymap("blender_default")
        for text in ("Open…", "Save", "Save Model As…", "Save Incremental"):
            self.assertIn(items[text], default, text)
        self.assertIn(("wm.call_menu", {"name": "TOPBAR_MT_file_open_recent"}), default)
        # Ctrl+N opens the New menu in Blender's keymap (the core shows that shortcut on New Model…) and runs
        # wm.read_homefile in the Industry Compatible one.
        self.assertIn(("wm.call_menu", {"name": "TOPBAR_MT_file_new"}), default)
        self.assertEqual(items["New Model…"], ("wm.read_homefile", {}))
        self.assertIn(("wm.read_homefile", {}), window_keymap("industry_compatible_data"))

    def test_new_menu_offers_a_model_or_a_project(self):
        self.assertEqual(tu.operators(tu.draw(bpy.types.TOPBAR_MT_file_new)),
                         [("dasktoon.model_new", "New Model…"), ("dasktoon.project_create", "New Project…")])

    def test_top_bar_label_comes_before_the_scene_selector(self):
        context = types.SimpleNamespace(window=types.SimpleNamespace(scene=bpy.context.scene),
                                        screen=types.SimpleNamespace(show_statusbar=True))
        layout = tu.RecordingLayout()
        TOPBAR_HT_upper_bar.draw_right(types.SimpleNamespace(layout=layout), context)
        kinds = [entry[:2] for entry in layout.log]
        self.assertEqual(kinds[:2], [("label", ""), ("call", "template_ID")])
        self.assertEqual(layout.log[0][2:4], ("Draft (not in a project)", 'ERROR'))


if __name__ == "__main__":
    tu.run_tests()
