# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Animation tab (Animation tab spec 6): bpy.data.workspaces.replace puts a workspace in the place of
another without making the file modified."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402


def appended(folder, name):
    """A copy of workspace `name`, written to a library in `folder` and appended back (it gets a ".001" name)."""
    lib = os.path.join(folder, "lib_%s.blend" % name)
    bpy.data.libraries.write(lib, {bpy.data.workspaces[name]}, fake_user=True)
    with bpy.data.libraries.load(lib, link=False) as (_src, dst):
        dst.workspaces = [name]
    return dst.workspaces[0]


class ReplaceTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.folder = tempfile.mkdtemp(prefix="dt_animtab_")

    def test_replace_takes_the_place_and_the_name(self):
        main = os.path.join(self.folder, "main.blend")
        bpy.ops.wm.save_as_mainfile(filepath=main)
        bpy.ops.wm.open_mainfile(filepath=main)
        count = len(bpy.data.workspaces)
        new = appended(self.folder, "Layout")
        self.assertEqual(new.name, "Layout.001")
        new["mark"] = 1
        bpy.data.workspaces.replace(bpy.data.workspaces["Animation"], new)
        self.assertEqual(bpy.data.workspaces["Animation"].get("mark"), 1)
        self.assertNotIn("Layout.001", bpy.data.workspaces)
        self.assertEqual(len(bpy.data.workspaces), count)
        self.assertFalse(bpy.data.is_dirty)

    def test_a_workspace_cannot_replace_itself(self):
        workspace = bpy.data.workspaces["Layout"]
        with self.assertRaises(RuntimeError):
            bpy.data.workspaces.replace(workspace, workspace)


if __name__ == "__main__":
    tu.run_tests()
