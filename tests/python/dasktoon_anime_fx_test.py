# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime effects are added from Add › Anime Effect (UI spec 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_anime_fx as fx  # noqa: E402


class Props:
    pass


class Recorder:
    def __init__(self):
        self.log = []

    def separator(self, **_kw):
        pass

    def label(self, **_kw):
        pass

    def operator(self, idname, **_kw):
        props = Props()
        self.log.append((idname, props))
        return props

    def menu(self, idname, **_kw):
        self.log.append((idname, None))


class Fake:
    def __init__(self):
        self.layout = Recorder()


class AnimeEffectMenuTest(unittest.TestCase):
    def test_menu_lists_every_effect_once(self):
        fake = Fake()
        bpy.types.VIEW3D_MT_dasktoon_anime_effect.draw(fake, bpy.context)
        kinds = [props.fx_type for idname, props in fake.layout.log if idname == "dasktoon.add_anime_fx"]
        items = [item.identifier for item in
                 bpy.ops.dasktoon.add_anime_fx.get_rna_type().properties["fx_type"].enum_items]
        self.assertEqual(sorted(kinds), sorted(items))
        self.assertEqual(len(kinds), 11)

    def test_add_menu_has_the_submenu_and_the_panel_is_gone(self):
        funcs = bpy.types.VIEW3D_MT_add.draw._draw_funcs
        self.assertTrue([f for f in funcs if f.__module__ == fx.__name__])
        self.assertFalse(hasattr(bpy.types, "VIEW3D_PT_dasktoon_anime_fx"))

    def test_an_effect_can_be_added(self):
        tu.reset_scene()
        before = len(bpy.data.objects)
        self.assertEqual(bpy.ops.dasktoon.add_anime_fx(fx_type='SAKURA'), {'FINISHED'})
        self.assertGreater(len(bpy.data.objects), before)

    def test_every_effect_can_be_added(self):
        for item in bpy.ops.dasktoon.add_anime_fx.get_rna_type().properties["fx_type"].enum_items:
            with self.subTest(item.identifier):
                tu.reset_scene()
                self.assertEqual(bpy.ops.dasktoon.add_anime_fx(fx_type=item.identifier), {'FINISHED'})


if __name__ == "__main__":
    tu.run_tests()
