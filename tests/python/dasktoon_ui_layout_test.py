# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where the DaskToon interface lives (UI spec 3): removed parts stay removed, moved parts sit in their new place."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

# Names in bpy.types (panels by bl_idname or class name, operators by their OT name).
REMOVED = (
    "DASKTOON_RENDER_PT_header", "DASKTOON_RENDER_PT_cel_shading", "DASKTOON_RENDER_PT_lineart",
    "DASKTOON_RENDER_PT_shadows", "DASKTOON_RENDER_PT_manga", "DASKTOON_RENDER_PT_animation",
    "DASKTOON_RENDER_PT_presets", "DaskToonEngineSettings", "DASKTOON_OT_setup_lighting", "DASKTOON_OT_setup_lineart",
    "DATA_PT_DaskToon_light_npr", "DASKTOON_PT_light_groups",
    "VIEW3D_PT_dasktoon_main", "VIEW3D_PT_dasktoon_shader_nodes", "DASKTOON_OT_activate_engine",
    "DASKTOON_OT_setup_anime_preset", "NODE_OT_dasktoon_add_anime_node", "DASKTOON_OT_link_sun_direction",
    "DASKTOON_OT_fix_face_normals", "DASKTOON_OT_reset_face_normals", "DASKTOON_OT_toggle_face_normals_display",
    "DASKTOON_PT_face_shading_advanced",
    "MATERIAL_PT_dasktoon_outline", "DASKTOON_OT_outline_toggle_material",
    "DASKTOON_PT_face_shading",
    "DASKTOON_PT_material_combiner",
    "VIEW3D_PT_dasktoon_anime_fx",
    "DASKTOON_PT_shape_axis_panel", "DASKTOON_PT_vrm_toolset_panel", "DASKTOON_PT_arkit_studio_panel",
    "DASKTOON_OT_vrm_zero_all_shapes", "DASKTOON_OT_vrm_mirror_shape_key",
    "VIEW3D_PT_dasktoon_project",
)
REMOVED_MODULES = ("dasktoon_light_groups", "bl_ui.dasktoon_anime_nodes", "bl_ui.dasktoon_face_normals",
                   "bl_ui.properties_dasktoon")


def subclasses(base):
    out, stack = [], list(base.__subclasses__())
    while stack:
        cls = stack.pop()
        out.append(cls)
        stack.extend(cls.__subclasses__())
    return out


class RemovedUITest(unittest.TestCase):
    def test_removed_classes_are_not_registered(self):
        self.assertEqual([name for name in REMOVED if hasattr(bpy.types, name)], [])
        self.assertFalse(hasattr(bpy.types.Scene, "dasktoon_engine"))

    def test_removed_modules_are_not_loaded(self):
        self.assertEqual([name for name in REMOVED_MODULES if name in sys.modules], [])

    def test_dasktoon_engine_shows_the_eevee_settings(self):
        missing = [cls.__name__ for cls in subclasses(bpy.types.Panel)
                   if getattr(cls, "is_registered", False) and isinstance(getattr(cls, "COMPAT_ENGINES", None), set)
                   and 'BLENDER_EEVEE' in cls.COMPAT_ENGINES and 'DASKTOON_ANIME' not in cls.COMPAT_ENGINES]
        self.assertEqual(missing, [])

    def test_startup_init_still_sets_the_standard_view(self):
        import dasktoon_init
        tu.reset_scene()
        scene = bpy.context.scene
        scene.view_settings.view_transform = 'AgX'
        dasktoon_init.dasktoon_enforce_color_management(scene)
        self.assertEqual(scene.view_settings.view_transform, 'Standard')



def appended(menu, module):
    funcs = getattr(getattr(menu, "draw", None), "_draw_funcs", None) or []
    return [f for f in funcs if getattr(f, "__module__", "") == module]


class MovedUITest(unittest.TestCase):
    def test_outline_removal_is_in_the_material_slot_menu(self):
        self.assertTrue(appended(bpy.types.MATERIAL_MT_context_menu, "bl_ui.dasktoon_outline"))

class NoSidebarTest(unittest.TestCase):
    def test_no_dasktoon_panel_in_any_sidebar_or_in_render_and_light(self):
        bad = []
        for cls in subclasses(bpy.types.Panel):
            if not getattr(cls, "is_registered", False):
                continue
            module = getattr(cls, "__module__", "")
            dasktoon = "dasktoon" in module or "DASKTOON" in cls.__name__.upper()
            if not dasktoon:
                continue
            if cls.bl_region_type == 'UI' or getattr(cls, "bl_category", "") in {"DaskToon", "ARKit", "Shape Axis"}:
                bad.append(cls.__name__)
            if cls.bl_space_type == 'PROPERTIES' and getattr(cls, "bl_context", "") in {"render", "data"} and \
                    getattr(cls, "bl_parent_id", "").startswith("DATA_PT_EEVEE_light"):
                bad.append(cls.__name__)
            if cls.bl_space_type == 'PROPERTIES' and getattr(cls, "bl_context", "") == "render":
                bad.append(cls.__name__)
        self.assertEqual(bad, [])


if __name__ == "__main__":
    tu.run_tests()
