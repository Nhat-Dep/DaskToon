# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Preferences › Interface › Language offers Automatic, English and Tiếng Việt only (UI spec 7)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LanguagesTest(unittest.TestCase):
    def test_language_list(self):
        with open(os.path.join(REPO, "locale", "languages"), encoding="utf-8") as f:
            entries = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        self.assertEqual(entries, ["0:Automatic:DEFAULT:100%", "1:English (US):en_US:100%",
                                   "41:Vietnamese - Tiếng Việt:vi_VN:96%"])
        self.assertEqual(sorted(os.listdir(os.path.join(REPO, "locale", "po"))), ["vi.po"])

    def test_installed_languages(self):
        self.assertEqual(sorted(bpy.app.translations.locales), ["en_US", "vi_VN"])
        locale_dir = os.path.join(bpy.utils.system_resource('DATAFILES'), "locale")
        self.assertEqual(sorted(n for n in os.listdir(locale_dir) if os.path.isdir(os.path.join(locale_dir, n))), ["vi"])


if __name__ == "__main__":
    tu.run_tests()
