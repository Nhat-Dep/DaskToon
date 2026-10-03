# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Export › Engine Export… operator (spec 3, 5). The dialog itself is checked by hand in DaskToon."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_engine_export as ui  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from dasktoon_export import targets  # noqa: E402


def character():
    tu.reset_scene()
    outline.reset_cache()
    body = tu.add_sphere(segments=12, rings=6)
    mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    tu.assign(body, mat)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    return body


class EngineExportOperatorTest(unittest.TestCase):
    def test_exports_and_remembers_the_target(self):
        character()
        out = tempfile.mkdtemp(prefix="dt_ui_")
        self.assertEqual(bpy.ops.export_scene.dasktoon_engine(directory=out, bake_size=64, include_animation=False),
                         {'FINISHED'})
        root = os.path.join(out, "Untitled_Unity")
        self.assertTrue(os.path.isfile(os.path.join(root, "Untitled", "Model", "Untitled.fbx")))
        self.assertTrue(os.path.isfile(os.path.join(root, "Untitled", "Materials", "Skin.mat")))
        self.assertEqual(targets.remembered_target(bpy.context.scene), (out, 'UNITY_URP'))
        self.assertEqual(ui.default_directory(bpy.context), (out, 'UNITY_URP'))

    def test_coming_soon_engine_is_refused(self):
        character()
        with self.assertRaises(RuntimeError):
            bpy.ops.export_scene.dasktoon_engine(directory=tempfile.mkdtemp(prefix="dt_ui_"), engine='GODOT_4')

    def test_nothing_selected_is_refused(self):
        character()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)
        with self.assertRaises(RuntimeError):
            bpy.ops.export_scene.dasktoon_engine(directory=tempfile.mkdtemp(prefix="dt_ui_"), use_selection=True)

    def test_menu_entry_is_registered(self):
        self.assertTrue(hasattr(bpy.ops.export_scene, "dasktoon_engine"))
        # bl_ui modules may be reloaded, so the entry is matched by module and name, not by identity.
        ours = [f for f in bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize()
                if getattr(f, "__module__", "") == ui.__name__ and f.__name__ == "menu_func_export"]
        self.assertEqual(len(ours), 1)


if __name__ == "__main__":
    tu.run_tests()
