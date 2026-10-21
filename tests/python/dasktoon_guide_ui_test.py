# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Guide tab (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): two panels in the 3D Viewport's
sidebar; Check Model fills the window's list for the selected character, Fix puts one right and checks again, the
Steps open the first step not done, and Engine Export marks the last one done."""

import os
import re
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_guide_checks_test as gt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_guide as ui  # noqa: E402
from dasktoon_guide import checks, steps  # noqa: E402


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


def draw(panel_class):
    recorder = Recorder()
    panel_class.draw(type("Panel", (), {"layout": recorder})(), bpy.context)
    return recorder.log


def select(objects):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = objects[0]


class GuideTest(unittest.TestCase):
    def setUp(self):
        self.body = gt.good()
        select([self.body])
        bpy.context.window_manager.dasktoon_guide_results.clear()

    def test_two_panels_in_the_viewport_sidebar(self):
        for name in ("VIEW3D_PT_dasktoon_guide_check", "VIEW3D_PT_dasktoon_guide_steps"):
            cls = getattr(bpy.types, name)
            self.assertEqual((cls.bl_space_type, cls.bl_region_type, cls.bl_category), ('VIEW_3D', 'UI', "Guide"))

    def test_check_fills_the_list_and_fix_puts_one_right(self):
        self.assertEqual(bpy.ops.dasktoon.guide_check(), {'FINISHED'})
        results = bpy.context.window_manager.dasktoon_guide_results
        self.assertEqual([item.check for item in results], list(checks.ORDER))
        self.body.location.z = 0.4
        bpy.ops.dasktoon.guide_check()
        self.assertEqual(ui.statuses(bpy.context)["floor"], 'WARN')
        self.assertEqual(bpy.ops.dasktoon.guide_fix(check="floor"), {'FINISHED'})
        self.assertEqual(ui.statuses(bpy.context)["floor"], 'OK')  # checked again

    def test_the_steps_open_the_first_one_not_done(self):
        bpy.ops.dasktoon.guide_check()
        found = ui.statuses(bpy.context)
        self.assertEqual(steps.current(found, bpy.context.scene, [self.body]), 'RIG')  # good, not rigged yet
        for step in ('NEW', 'BODY', 'HEAD', 'HAIR', 'CLOTHES', 'MATERIALS'):
            self.assertTrue(steps.done(step, found, bpy.context.scene, [self.body]), step)
        self.assertEqual(set(steps.IDS), {'NEW', 'BODY', 'HEAD', 'HAIR', 'CLOTHES', 'MATERIALS', 'RIG',
                                          'EXPRESSIONS', 'UNITY'})
        every = [name for step in steps.IDS for name in steps.checks_of(step)]
        self.assertEqual(sorted(every), sorted(checks.ORDER))  # every check belongs to one step

    def test_the_panels_draw(self):
        log = draw(ui.VIEW3D_PT_dasktoon_guide_check)
        self.assertIn(("operator", "dasktoon.guide_check", "Check Model"), log)
        bpy.ops.dasktoon.guide_check()
        log = draw(ui.VIEW3D_PT_dasktoon_guide_check)
        self.assertIn(("operator", "dasktoon.guide_check", "Check Again"), log)
        self.assertIn(("operator", "dasktoon.guide_fix", "Fix"), log)  # the rig is still to make
        log = draw(ui.VIEW3D_PT_dasktoon_guide_steps)
        self.assertIn(("operator", "dasktoon.guide_page", "Read the Guide"), log)
        labels = [entry[2] for entry in log if entry[0] == "label"]
        self.assertTrue(any(text and text.startswith("7. ") for text in labels))

    def test_engine_export_marks_the_last_step_done(self):
        self.assertFalse(steps.done('UNITY', {}, bpy.context.scene, [self.body]))
        folder = tempfile.mkdtemp(prefix="dt_guide_export_")
        bpy.ops.export_scene.dasktoon_engine(directory=folder, engine='UNITY_URP', model_format='FBX',
                                             use_selection=False, include_animation=False, export_materials=False)
        self.assertTrue(steps.done('UNITY', {}, bpy.context.scene, [self.body]))

    def test_page_urls(self):
        url = ui.page_url('BODY', "facing", language="vi")
        self.assertTrue(url.startswith("file:///"))
        self.assertTrue(url.endswith("/vi/body.html#facing"))

    def test_a_section_opens_through_a_page_without_anchor(self):
        # Windows drops the #section of a file URL it hands to the browser: open a page that goes there instead.
        url = ui.opening_url('BODY', "facing")
        self.assertNotIn("#", url)
        with open(url[len("file:///"):], encoding="utf-8") as f:
            self.assertIn(ui.page_url('BODY', "facing"), f.read())
        self.assertEqual(ui.opening_url('BODY', ""), ui.page_url('BODY'))


class PagesTest(unittest.TestCase):
    """The pages: a page a step in both languages, a section a check on its step's page, every picture and link a
    page uses there."""
    LANGUAGES = ("en", "vi")

    def read(self, language, name):
        path = os.path.join(ui.PAGES, language, name)
        self.assertTrue(os.path.exists(path), path)
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_every_step_has_its_page_in_both_languages(self):
        for language in self.LANGUAGES:
            for step in steps.IDS + ("index",):
                self.read(language, step.lower() + ".html")

    def test_every_check_has_its_section_on_its_steps_page(self):
        for language in self.LANGUAGES:
            for name, _group, step, _fn, _fixable in checks.CHECKS:
                self.assertIn('<section id="%s">' % name, self.read(language, step.lower() + ".html"),
                              (language, name))

    def test_every_picture_and_link_is_there(self):
        for language in self.LANGUAGES:
            folder = os.path.join(ui.PAGES, language)
            for name in os.listdir(folder):
                for target, anchor in re.findall(r'(?:src|href)="([^"#:]*)(?:#([^"]*))?"', self.read(language, name)):
                    path = os.path.normpath(os.path.join(folder, target or name))
                    self.assertTrue(os.path.exists(path), (language, name, target))
                    if anchor:
                        with open(path, encoding="utf-8") as f:
                            self.assertIn('id="%s"' % anchor, f.read(), (language, name, target, anchor))


PAGE = """<!doctype html>
<html lang="%(lang)s">
<head><meta charset="utf-8"><title>T</title><link rel="stylesheet" href="../guide.css"></head>
<body><main>
<nav><a href="index.html">%(home)s</a> <a href="../%(other)s/%(name)s">%(other)s</a></nav>
<h1>T</h1>
%(body)s
</main></body>
</html>
"""


class PageCheckTest(unittest.TestCase):
    """The check a page writer (a person or another program) runs before handing pages in: every page in both
    languages and reached from the index, the two languages with the same sections and pictures, and every button name
    in <b> one the interface really shows in that language (DaskToon's or Blender's own)."""

    def write(self, root, lang, name, body, real_lang=None):
        other = "vi" if lang == "en" else "en"
        with open(os.path.join(root, lang, name), "w", encoding="utf-8") as f:
            f.write(PAGE % {"lang": real_lang or lang, "other": other, "name": name, "body": body,
                            "home": "Home"})

    def test_the_pages_pass_the_page_check(self):
        from dasktoon_guide import page_check
        self.assertEqual(page_check.problems(ui.PAGES), [])

    def test_the_page_check_finds_what_a_writer_gets_wrong(self):
        from dasktoon_guide import page_check
        root = tempfile.mkdtemp(prefix="dt_page_check_")
        for folder in ("en", "vi", "pictures"):
            os.makedirs(os.path.join(root, folder))
        open(os.path.join(root, "guide.css"), "w").close()
        open(os.path.join(root, "pictures", "rig.png"), "wb").close()
        for lang in ("en", "vi"):
            self.write(root, lang, "index.html", '<a href="good.html">x</a> <a href="mixed.html">x</a>')
        # Right in both languages.
        self.write(root, "en", "good.html", '<section id="parts"><b>Anime Rig › Check</b>'
                   '<img src="../pictures/rig.png"></section>')
        self.write(root, "vi", "good.html", '<section id="parts"><b>Rig anime › Kiểm tra</b>'
                   '<img src="../pictures/rig.png"></section>')
        # Wrong: a made-up button, a section and a picture only in English, the wrong lang, a missing picture.
        self.write(root, "en", "mixed.html", '<section id="a"><b>Anime Rig</b></section><section id="b"></section>'
                   '<img src="../pictures/rig.png">')
        self.write(root, "vi", "mixed.html", '<section id="a"><b>Nút Không Có</b></section>'
                   '<img src="../pictures/none.png">', real_lang="en")
        # Only in English, and nothing links to it.
        self.write(root, "en", "lonely.html", "")
        found = "\n".join(page_check.problems(root))
        for expected in ("Nút Không Có", "lonely.html", '"b"', "none.png", "lang"):
            self.assertIn(expected, found)
        self.assertNotIn("good.html", found)
        self.assertNotIn("Rig anime", found)


if __name__ == "__main__":
    tu.run_tests()
