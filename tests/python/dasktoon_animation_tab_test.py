# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Animation tab (Animation tab spec 3, 6): the tab after startup, its replacement when a file opens (an old
tab is replaced once, a current one kept, a deleted one not added back, the file stays unmodified), and
bpy.data.workspaces.replace that does it."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_animation import tab  # noqa: E402


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


def areas(workspace):
    return workspace.screens[0].areas


class TabTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.folder = tempfile.mkdtemp(prefix="dt_animtab_")

    def reopen(self):
        path = os.path.join(self.folder, "file.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)

    def test_the_tab_after_startup(self):
        workspace = bpy.data.workspaces[tab.NAME]
        self.assertEqual(workspace.get(tab.MARK), tab.VERSION)
        self.assertEqual(workspace.object_mode, 'POSE')
        found = areas(workspace)
        self.assertEqual(sorted(area.type for area in found),
                         ['DOPESHEET_EDITOR', 'PROPERTIES', 'VIEW_3D', 'VIEW_3D'])
        views = sorted((area for area in found if area.type == 'VIEW_3D'), key=lambda area: area.x)
        camera, main = views[0].spaces.active, views[1].spaces.active
        self.assertEqual((camera.region_3d.view_perspective, camera.shading.type, camera.show_region_toolbar,
                          camera.show_gizmo), ('CAMERA', 'RENDERED', False, False))
        self.assertTrue(main.show_region_toolbar)
        properties = next(area for area in found if area.type == 'PROPERTIES')
        self.assertEqual(properties.spaces.active.context, 'DATA')
        self.assertEqual(properties.height, max(area.y + area.height for area in found) - properties.y)  # whole column
        dopesheet = next(area for area in found if area.type == 'DOPESHEET_EDITOR').spaces.active
        self.assertEqual(dopesheet.mode, 'DOPESHEET')
        self.assertTrue(dopesheet.dopesheet.show_whole_character)
        self.assertTrue(dopesheet.show_region_footer)

    def test_an_old_tab_is_replaced_and_the_file_stays_clean(self):
        count = len(bpy.data.workspaces)
        del bpy.data.workspaces[tab.NAME][tab.MARK]
        self.reopen()
        self.assertEqual(bpy.data.workspaces[tab.NAME].get(tab.MARK), tab.VERSION)
        self.assertNotIn(tab.NAME + ".001", bpy.data.workspaces)
        self.assertEqual(len(bpy.data.workspaces), count)
        self.assertFalse(bpy.data.is_dirty)

    def test_a_current_tab_is_kept(self):
        bpy.data.workspaces[tab.NAME]["kept"] = 1
        self.reopen()
        self.assertEqual(bpy.data.workspaces[tab.NAME].get("kept"), 1)

    def test_a_deleted_tab_is_not_added(self):
        bpy.data.batch_remove([bpy.data.workspaces[tab.NAME]])
        self.reopen()
        self.assertNotIn(tab.NAME, bpy.data.workspaces)

    def test_scenes_get_the_character_keying_set_on_open(self):
        from dasktoon_animation import KEYING_SET
        self.assertEqual(bpy.context.scene.keying_sets_all.active.bl_idname, KEYING_SET)

    def test_the_template_file(self):
        self.assertTrue(os.path.isfile(tab.TEMPLATE))
        with bpy.data.libraries.load(tab.TEMPLATE) as (src, _dst):
            self.assertEqual(list(src.workspaces), [tab.NAME])
            self.assertEqual(list(src.scenes), [])
            self.assertEqual(list(src.objects), [])


if __name__ == "__main__":
    tu.run_tests()
