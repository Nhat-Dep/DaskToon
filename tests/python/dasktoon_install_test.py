# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The installed DaskToon matches the repository (UI spec 8): the sync script, and a check of the running install."""

import importlib.util
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("dasktoon_sync_build",
                                               os.path.join(REPO, "tools", "dasktoon_sync_build.py"))
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def files(root):
    out = set()
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        out.update(os.path.relpath(os.path.join(base, n), root).replace(os.sep, "/") for n in names)
    return out


class SyncScriptTest(unittest.TestCase):
    def setUp(self):
        base = tempfile.mkdtemp(prefix="dt_sync_")
        self.src, self.dst = os.path.join(base, "src"), os.path.join(base, "dst")
        write(os.path.join(self.src, "a.py"), "new")
        write(os.path.join(self.src, "pkg", "b.py"), "b")
        write(os.path.join(self.dst, "a.py"), "old")
        write(os.path.join(self.dst, "stale.py"))
        write(os.path.join(self.dst, "old_pkg", "c.py"))
        write(os.path.join(self.dst, "pkg", "__pycache__", "b.cpython-313.pyc"))

    def test_mirror_copies_changes_and_removes_what_the_repository_does_not_have(self):
        actions = sync.mirror_tree(self.src, self.dst)
        self.assertEqual(files(self.dst), {"a.py", "pkg/b.py"})
        with open(os.path.join(self.dst, "a.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "new")
        self.assertTrue(os.path.exists(os.path.join(self.dst, "pkg", "__pycache__", "b.cpython-313.pyc")))
        verbs = {(verb, path.replace(os.sep, "/")) for verb, path in actions}
        self.assertTrue({("copy", "a.py"), ("copy", "pkg/b.py"), ("remove", "stale.py"), ("remove", "old_pkg/")} <= verbs)
        self.assertEqual(sync.mirror_tree(self.src, self.dst), [])

    def test_dry_run_changes_nothing(self):
        before = files(self.dst)
        self.assertTrue(sync.mirror_tree(self.src, self.dst, dry_run=True))
        self.assertEqual(files(self.dst), before)

    def test_locale_keeps_only_languages_that_have_a_po_file(self):
        base = tempfile.mkdtemp(prefix="dt_sync_locale_")
        repo, install = os.path.join(base, "repo"), os.path.join(base, "install")
        write(os.path.join(repo, "locale", "languages"), "0:Automatic:DEFAULT:100%\n")
        write(os.path.join(repo, "locale", "po", "vi.po"))
        write(os.path.join(install, "datafiles", "locale", "languages"), "old")
        write(os.path.join(install, "datafiles", "locale", "vi", "LC_MESSAGES", "blender.mo"))
        write(os.path.join(install, "datafiles", "locale", "ja", "LC_MESSAGES", "blender.mo"))
        sync.sync_locale(repo, install)
        locale = os.path.join(install, "datafiles", "locale")
        self.assertEqual(sorted(os.listdir(locale)), ["languages", "vi"])
        with open(os.path.join(locale, "languages"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "0:Automatic:DEFAULT:100%\n")


class InstalledBuildTest(unittest.TestCase):
    def test_installed_scripts_match_the_repository(self):
        """A file removed from the repository must not stay in the install (Blender would keep loading it)."""
        installed = bpy.utils.system_resource('SCRIPTS')
        for sub in sync.MIRRORED:
            src = os.path.join(REPO, *sub.split("/"))
            dst = os.path.join(installed, os.path.basename(sub))
            self.assertEqual(sync.mirror_tree(src, dst, dry_run=True), [], sub)


if __name__ == "__main__":
    tu.run_tests()
