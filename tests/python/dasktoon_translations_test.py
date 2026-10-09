# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""English source strings with a Vietnamese translation shown when the language is Tiếng Việt (UI spec 6)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Grows task by task; Task 12 checks that it covers every DaskToon file.
TRANSLATED = [
    "scripts/startup/bl_ui/dasktoon_engine_export.py",
    "scripts/startup/bl_ui/dasktoon_sun_sync.py",
    "scripts/startup/bl_ui/dasktoon_outline.py",
    "scripts/startup/bl_ui/dasktoon_outline_gamedata.py",
    "scripts/startup/bl_ui/dasktoon_face_shading.py",
    "scripts/startup/bl_ui/dasktoon_material_combiner.py",
    "scripts/startup/bl_ui/dasktoon_anime_fx.py",
    "scripts/startup/bl_ui/dasktoon_shape_key_manager.py",
    "scripts/startup/bl_ui/dasktoon_project.py",
    "scripts/modules/dasktoon_project/project.py",
    "scripts/modules/dasktoon_export/__init__.py",
    "scripts/modules/dasktoon_export/assets.py",
    "scripts/modules/dasktoon_export/bake.py",
    "scripts/modules/dasktoon_export/face_shading.py",
    "scripts/modules/dasktoon_export/graph.py",
    "scripts/modules/dasktoon_export/model_fbx.py",
    "scripts/modules/dasktoon_export/node_maps.py",
    "scripts/modules/dasktoon_export/report.py",
    "scripts/modules/dasktoon_export/shaders_install.py",
    "scripts/modules/dasktoon_export/targets.py",
    "scripts/modules/dasktoon_export/textures.py",
    "scripts/modules/dasktoon_export/unity_yaml.py",
    "scripts/modules/dasktoon_project/__init__.py",
    "scripts/modules/dasktoon_project/textures.py",
    "scripts/modules/dasktoon_project/scene.py",
    "scripts/startup/bl_ui/dasktoon_model.py",
    "scripts/startup/bl_ui/dasktoon_splash.py",
    "scripts/startup/bl_ui/dasktoon_face_shading_nodes.py",
    "scripts/startup/bl_ui/dasktoon_outline_nodes.py",
    "scripts/startup/bl_ui/dasktoon_shading_styles.py",
    "scripts/startup/bl_ui/dasktoon_upgrade.py",
    "scripts/startup/bl_ui/engine_dasktoon_anime.py",
    "scripts/startup/dasktoon_init.py",
    "scripts/modules/dasktoon_rig/__init__.py",
    "scripts/modules/dasktoon_rig/skeleton.py",
    "scripts/modules/dasktoon_rig/chains.py",
    "scripts/modules/dasktoon_rig/parts.py",
    "scripts/modules/dasktoon_rig/weights.py",
    "scripts/modules/dasktoon_rig/build.py",
    "scripts/modules/dasktoon_rig/spring.py",
    "scripts/modules/dasktoon_rig/sway.py",
    "scripts/modules/dasktoon_export/rig_json.py",
    "scripts/modules/dasktoon_export/scripts_install.py",
    "scripts/startup/bl_ui/dasktoon_rig.py",
]
# Blender files DaskToon rewrote parts of (project workflow spec 13): only these classes are DaskToon's.
TRANSLATED_CLASSES = {
    "scripts/startup/bl_ui/space_topbar.py": ("TOPBAR_MT_file", "TOPBAR_MT_file_new", "TOPBAR_HT_upper_bar"),
    "scripts/startup/bl_operators/wm.py": ("WM_MT_splash",),
}


def path(rel):
    return os.path.join(REPO, *rel.split("/"))


def dasktoon_files():
    """Every DaskToon Python file that can show text."""
    import glob
    found = set()
    for pattern in ("scripts/startup/bl_ui/dasktoon_*.py", "scripts/startup/bl_ui/engine_dasktoon_anime.py",
                    "scripts/startup/dasktoon_*.py", "scripts/modules/dasktoon_export/*.py",
                    "scripts/modules/dasktoon_project/*.py", "scripts/modules/dasktoon_rig/*.py"):
        found.update(os.path.relpath(p, REPO).replace(os.sep, "/") for p in glob.glob(path(pattern)))
    found.discard("scripts/startup/bl_ui/dasktoon_translations.py")
    return found


def dasktoon_node_menus():
    """(node types, labels) of the Shader Editor's DaskToon Anime and DaskToon Manga Add menus: the bl_idname of each
    C++ node they add, and the menu and item labels they show."""
    import ast
    with open(path("scripts/startup/bl_ui/node_add_menu_shader.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    types, labels = set(), set()
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef) and
                ("anime" in n.name.lower() or "manga" in n.name.lower())]:
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign) and any(getattr(tg, "id", "") == "bl_label" for tg in stmt.targets):
                labels.add(stmt.value.value)
        for call in [n for n in ast.walk(cls) if isinstance(n, ast.Call)]:
            for arg in call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("ShaderNode"):
                        types.add(arg.value)
                    elif "/" in arg.value and getattr(call.func, "attr", "") == "draw_menu":
                        labels.add(arg.value.rsplit("/", 1)[1])
            for kw in call.keywords:
                if kw.arg == "label" and isinstance(kw.value, ast.Constant):
                    labels.add(kw.value.value)
    return types, labels


class TranslationTest(unittest.TestCase):
    def test_vietnamese_shows_only_when_the_language_is_vietnamese(self):
        iface = bpy.app.translations.pgettext_iface
        with iu.language('vi_VN'):
            self.assertEqual(iface("Engine Export", "Operator"), dt.VI["Engine Export"])
        self.assertEqual(iface("Engine Export", "Operator"), "Engine Export")

    def test_source_strings_are_english_without_emoji(self):
        for rel in TRANSLATED:
            bad = sorted(s for s in iu.all_strings(path(rel)) if iu.VI_CHARS.search(s) or iu.EMOJI.search(s))
            self.assertEqual(bad, [], rel)

    def test_no_visible_string_is_built_at_run_time(self):
        for rel in TRANSLATED:
            self.assertEqual(iu.module_strings(path(rel))[1], [], rel)

    def test_every_visible_string_is_translated(self):
        with iu.language('vi_VN'):
            for rel in TRANSLATED:
                self.assertEqual(iu.untranslated(iu.module_strings(path(rel))[0], dt.KEEP), [], rel)

    def test_every_dasktoon_file_is_checked(self):
        self.assertEqual(dasktoon_files() - set(TRANSLATED), set())

    def test_dasktoon_nodes_are_translated(self):
        types, strings = dasktoon_node_menus()
        self.assertIn("ShaderNodeMangaCharacter", types)
        mat = bpy.data.materials.new("DT_NodeStrings")
        for idname in sorted(types):
            node = mat.node_tree.nodes.new(idname)
            strings.add(node.bl_rna.name)
            strings.update(s.name for s in list(node.inputs) + list(node.outputs))
            for prop in node.bl_rna.properties:
                if prop.identifier in bpy.types.ShaderNode.bl_rna.properties:
                    continue
                strings.update((prop.name, prop.description))
                if prop.type == 'ENUM':
                    for item in prop.enum_items:
                        strings.update((item.name, item.description))
        bpy.data.materials.remove(mat)
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])

    def test_project_has_its_own_vietnamese_word(self):
        with iu.language('vi_VN'):
            self.assertEqual(bpy.app.translations.pgettext_iface("Project", "DaskToon"), "Dự án")

    def test_rewritten_blender_classes_are_english_and_translated(self):
        with iu.language('vi_VN'):
            for rel, classes in TRANSLATED_CLASSES.items():
                strings, dynamic = iu.module_strings(path(rel), classes)
                self.assertEqual(dynamic, [], rel)
                self.assertEqual(iu.untranslated(strings, dt.KEEP), [], rel)
                bad = sorted(s for s in iu.all_strings(path(rel), classes) if iu.VI_CHARS.search(s) or iu.EMOJI.search(s))
                self.assertEqual(bad, [], rel)

    def test_translation_table_is_vietnamese(self):
        for msgid, msgstr in dt.VI.items():
            self.assertTrue(msgstr.strip(), msgid)
            self.assertFalse(iu.EMOJI.search(msgstr), msgid)


if __name__ == "__main__":
    tu.run_tests()
