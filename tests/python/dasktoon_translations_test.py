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
]


def path(rel):
    return os.path.join(REPO, *rel.split("/"))


class TranslationTest(unittest.TestCase):
    def test_vietnamese_shows_only_when_the_language_is_vietnamese(self):
        iface = bpy.app.translations.pgettext_iface
        with iu.language('vi_VN'):
            self.assertEqual(iface("Engine Export", "Operator"), dt.VI["Engine Export"])
        self.assertEqual(iface("Engine Export", "Operator"), "Engine Export")

    def test_source_strings_are_english_without_emoji(self):
        for rel in TRANSLATED:
            strings, _dynamic = iu.module_strings(path(rel))
            bad = sorted(s for s in strings if iu.VI_CHARS.search(s) or iu.EMOJI.search(s))
            self.assertEqual(bad, [], rel)

    def test_no_visible_string_is_built_at_run_time(self):
        for rel in TRANSLATED:
            self.assertEqual(iu.module_strings(path(rel))[1], [], rel)

    def test_every_visible_string_is_translated(self):
        with iu.language('vi_VN'):
            for rel in TRANSLATED:
                self.assertEqual(iu.untranslated(iu.module_strings(path(rel))[0], dt.KEEP), [], rel)

    def test_translation_table_is_vietnamese(self):
        for msgid, msgstr in dt.VI.items():
            self.assertTrue(msgstr.strip(), msgid)
            self.assertFalse(iu.EMOJI.search(msgstr), msgid)


if __name__ == "__main__":
    tu.run_tests()
