# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""VRM, ARKit and Shape Axis tools live under Properties › Object Data › Shape Keys (UI spec 3.2)."""

import os
import sys
import types
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_shape_key_manager as skm  # noqa: E402

PANELS = ("DATA_PT_dasktoon_expression_sets", "DATA_PT_dasktoon_expression_tools",
          "DATA_PT_dasktoon_expression_preview", "DATA_PT_dasktoon_expression_controllers")


class Recorder:
    """Stands in for UILayout: every call returns a child recorder that shares the log."""

    def __init__(self, log=None):
        self.log = [] if log is None else log

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.log.append((name, args[0] if args else None, kwargs.get("text")))
            return Recorder(self.log)
        return call

    def __setattr__(self, name, value):
        if name == "log":
            object.__setattr__(self, name, value)


def draw(panel):
    recorder = Recorder()

    class Fake:
        layout = recorder

    panel.draw(Fake(), bpy.context)
    return recorder.log


class ExpressionPanelsTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj = tu.add_sphere(segments=8, rings=4)
        bpy.context.view_layer.objects.active = self.obj

    def test_panels_sit_under_shape_keys(self):
        for name in PANELS:
            panel = getattr(bpy.types, name)
            self.assertEqual((panel.bl_space_type, panel.bl_context, panel.bl_parent_id),
                             ('PROPERTIES', "data", "DATA_PT_shape_keys"), name)

    def test_sidebar_panels_and_duplicate_tools_are_gone(self):
        for name in ("DASKTOON_PT_shape_axis_panel", "DASKTOON_PT_vrm_toolset_panel", "DASKTOON_PT_arkit_studio_panel",
                     "DASKTOON_OT_vrm_zero_all_shapes", "DASKTOON_OT_vrm_mirror_shape_key"):
            self.assertFalse(hasattr(bpy.types, name), name)

    def test_tools_need_shape_keys(self):
        for name in PANELS[1:]:
            self.assertFalse(getattr(bpy.types, name).poll(bpy.context), name)
        self.assertTrue(bpy.types.DATA_PT_dasktoon_expression_sets.poll(bpy.context))
        self.obj.shape_key_add(name="Basis")
        for name in PANELS:
            self.assertTrue(getattr(bpy.types, name).poll(bpy.context), name)

    def test_every_panel_draws(self):
        self.obj.shape_key_add(name="Basis")
        for name in PANELS:
            self.assertTrue(draw(getattr(bpy.types, name)), name)
        operators = {entry[1] for entry in draw(bpy.types.DATA_PT_dasktoon_expression_preview) if entry[0] == "operator"}
        self.assertIn("object.shape_key_clear", operators)
        self.assertNotIn("dasktoon.vrm_zero_all_shapes", operators)

    def test_arkit_groups_cover_the_52_shapes(self):
        covered = [name for _label, start, end in skm.ARKIT_GROUPS for name in skm.ARKIT_52_ALL_NAMES[start:end]]
        self.assertEqual(covered, skm.ARKIT_52_ALL_NAMES)
        self.assertEqual(len(covered), 52)

    def test_hud_runs_in_a_3d_viewport_of_the_window(self):
        class Item:
            def __init__(self, kind, regions=()):
                self.type, self.regions = kind, list(regions)

        class Screen:
            def __init__(self, areas):
                self.areas = areas

        view = Item('VIEW_3D', [Item('HEADER'), Item('WINDOW')])
        screen = Screen([Item('PROPERTIES', [Item('WINDOW')]), view])
        self.assertEqual(skm._view3d_region(screen), (view, view.regions[1]))
        self.assertEqual(skm._view3d_region(Screen([Item('PROPERTIES', [Item('WINDOW')])])), (None, None))
        self.assertEqual(skm._view3d_region(None), (None, None))

    def test_hud_button_cancels_without_a_3d_viewport_and_closes_an_open_hud(self):
        # Background Blender has no window to invoke operators in, so invoke() is called directly, from a context
        # like the Properties editor of a window without a 3D Viewport.
        self.obj.shape_key_add(name="Basis")
        reports = []

        class Operator:
            def report(self, _kind, message):
                reports.append(message)

        context = types.SimpleNamespace(object=self.obj, area=None, region=None, screen=None)
        invoke = skm.DASKTOON_OT_shape_axis_toggle_hud.invoke
        self.assertEqual(invoke(Operator(), context, None), {'CANCELLED'})
        self.assertFalse(skm.DaskHUDState.is_active)
        self.assertEqual(len(reports), 1)
        skm.DaskHUDState.is_active = True
        self.obj.dask_shape_controllers.hud_enabled = True
        self.assertEqual(invoke(Operator(), context, None), {'FINISHED'})
        self.assertFalse(skm.DaskHUDState.is_active)
        self.assertFalse(self.obj.dask_shape_controllers.hud_enabled)

    def test_placeholders_create_the_52_arkit_shapes(self):
        self.assertEqual(bpy.ops.dasktoon.arkit_init_placeholders(), {'FINISHED'})
        names = set(self.obj.data.shape_keys.key_blocks.keys())
        self.assertTrue(set(skm.ARKIT_52_ALL_NAMES) <= names)


if __name__ == "__main__":
    tu.run_tests()
