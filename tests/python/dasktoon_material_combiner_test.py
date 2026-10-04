# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Combine Materials and Restore Original Slots live in the material slot menu ⌄ (UI spec 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_material_combiner as combiner  # noqa: E402


class Recorder:
    def __init__(self):
        self.log = []

    def separator(self, **_kw):
        pass

    def operator(self, idname, **_kw):
        self.log.append(idname)


class Fake:
    def __init__(self):
        self.layout = Recorder()


class MaterialCombinerMenuTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(self.obj, tu.emission_material("A", (1, 0, 0, 1)))
        self.obj.data.materials.append(tu.emission_material("B", (0, 0, 1, 1)))

    def draw(self):
        fake = Fake()
        combiner.menu_func(fake, bpy.context)
        return fake.layout.log

    def test_menu_offers_combine_and_restores_only_when_there_is_something_to_restore(self):
        self.assertEqual(self.draw(), ["dasktoon.combine_materials"])
        self.obj["dasktoon_orig_materials"] = ["A", "B"]
        self.assertEqual(self.draw(), ["dasktoon.combine_materials", "dasktoon.restore_materials"])

    def test_combine_then_restore_gives_back_the_slots(self):
        self.assertEqual(bpy.ops.dasktoon.combine_materials(resolution='1024', margin=1), {'FINISHED'})
        self.assertEqual([m.name for m in self.obj.data.materials], [self.obj.name + "_Consolidated_DaskToon"])
        self.assertEqual(bpy.ops.dasktoon.restore_materials(), {'FINISHED'})
        self.assertEqual([m.name for m in self.obj.data.materials], ["A", "B"])

    def test_combine_refuses_a_mesh_with_one_slot(self):
        self.obj.data.materials.pop()
        ok, msg = combiner.combine_object_materials(self.obj)
        self.assertFalse(ok)
        self.assertIn(self.obj.name, msg)

    def test_menu_is_in_the_material_slot_menu_and_the_panel_is_gone(self):
        funcs = bpy.types.MATERIAL_MT_context_menu.draw._draw_funcs
        self.assertIn(combiner.menu_func.__name__, [f.__name__ for f in funcs if f.__module__ == combiner.__name__])
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_material_combiner"))


if __name__ == "__main__":
    tu.run_tests()
