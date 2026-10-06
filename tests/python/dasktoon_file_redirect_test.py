# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Blender's file operators hand over to DaskToon only when invoked (project workflow spec 8): the switch is there,
exec with a path still saves, opens and reads like Blender while the DaskToon commands are registered, a command named
in post_read_operator runs once the file has been read, and Open Recent is DaskToon's Python menu (spec 7)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402

OPERATORS = ("read_homefile", "open_mainfile", "save_mainfile", "save_as_mainfile")
TARGETS = ("dasktoon.model_new", "dasktoon.open", "dasktoon.project_save", "dasktoon.model_save_incremental",
           "dasktoon.model_save_as", "dasktoon.model_save_copy")
calls = []


def stub(idname):
    """An operator that only records that it ran, registered in place of a DaskToon command."""
    return type("STUB_OT_" + idname.replace(".", "_"), (bpy.types.Operator,), {
        "bl_idname": idname,
        "bl_label": "Stub",
        "invoke": lambda self, _context, _event: calls.append(idname) or {'FINISHED'},
        "execute": lambda self, _context: calls.append(idname) or {'FINISHED'},
    })


class PostRead(bpy.types.Operator):
    bl_idname = "test.dasktoon_post_read"
    bl_label = "Post Read"
    seen = []

    def execute(self, _context):
        PostRead.seen.append((bpy.data.filepath, len(bpy.data.objects)))
        return {'FINISHED'}


def setUpModule():
    for idname in TARGETS:
        bpy.utils.register_class(stub(idname))
    bpy.utils.register_class(PostRead)


class SwitchTest(unittest.TestCase):
    def test_the_four_file_operators_have_the_redirect_switch(self):
        for name in OPERATORS:
            prop = getattr(bpy.ops.wm, name).get_rna_type().properties["use_project_redirect"]
            self.assertEqual((prop.type, prop.default, prop.is_hidden, prop.is_skip_save),
                             ('BOOLEAN', True, True, True), name)

    def test_read_and_open_have_a_post_read_operator(self):
        for name in ("read_homefile", "open_mainfile"):
            prop = getattr(bpy.ops.wm, name).get_rna_type().properties["post_read_operator"]
            self.assertEqual((prop.type, prop.is_hidden, prop.is_skip_save), ('STRING', True, True), name)


class ExecIsNotRedirectedTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        calls.clear()
        PostRead.seen.clear()
        self.folder = tempfile.mkdtemp(prefix="dt_redirect_")

    def path(self, name):
        return os.path.join(self.folder, name)

    def test_exec_saves_opens_and_reads_like_blender(self):
        bpy.context.scene.collection.objects.link(bpy.data.objects.new("Marker", None))
        bpy.ops.wm.save_as_mainfile(filepath=self.path("a.blend"))
        self.assertEqual(bpy.data.filepath, self.path("a.blend"))
        bpy.ops.wm.save_as_mainfile(filepath=self.path("copy.blend"), copy=True)
        self.assertEqual(bpy.data.filepath, self.path("a.blend"))
        bpy.ops.wm.save_mainfile()
        bpy.ops.wm.save_mainfile(incremental=True)
        self.assertEqual(os.path.basename(bpy.data.filepath), "a1.blend")
        bpy.ops.wm.open_mainfile(filepath=self.path("copy.blend"))
        self.assertIn("Marker", bpy.data.objects)
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual((bpy.data.filepath, len(bpy.data.objects)), ("", 0))
        for name in ("a.blend", "a1.blend", "copy.blend"):  # (a.blend1 is Blender's backup of the second save)
            self.assertTrue(os.path.isfile(self.path(name)), name)
        self.assertEqual(calls, [])

    def test_post_read_operator_runs_once_the_file_is_read(self):
        bpy.ops.wm.save_as_mainfile(filepath=self.path("a.blend"))
        bpy.ops.wm.read_homefile(use_empty=True, post_read_operator=PostRead.bl_idname)
        self.assertEqual(PostRead.seen, [("", 0)])
        bpy.ops.wm.open_mainfile(filepath=self.path("a.blend"), post_read_operator="TEST_OT_dasktoon_post_read")
        self.assertEqual(PostRead.seen[-1][0], self.path("a.blend"))
        with self.assertRaises(RuntimeError):
            bpy.ops.wm.open_mainfile(filepath=self.path("missing.blend"), post_read_operator=PostRead.bl_idname)
        self.assertEqual(len(PostRead.seen), 2)
        bpy.ops.wm.read_homefile(post_read_operator="test.no_such_operator")
        self.assertEqual(len(PostRead.seen), 2)
        self.assertEqual(calls, [])


class OpenRecentMenuTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_redirect_config_")
        tu.reset_scene()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_redirect_recent_"), "Proj")

    def test_open_recent_is_dasktoons_menu_with_models_then_projects(self):
        self.assertIs(bpy.types.TOPBAR_MT_file_open_recent, project_ui.TOPBAR_MT_file_open_recent)
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_file_open_recent)), ["No recent models or projects"])
        project = dtp.create_project("Proj", self.folder)
        model = dtp.new_model_path(project, "Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        dtp.add_recent_model(model)
        log = tu.draw(bpy.types.TOPBAR_MT_file_open_recent)
        self.assertEqual([entry[:3] for entry in log if entry[0] != "separator"],
                         [("label", "", "Models"), ("operator", "dasktoon.project_open_model", "Proj › Hero"),
                          ("label", "", "Projects"), ("operator", "dasktoon.project_open", "Proj")])


if __name__ == "__main__":
    tu.run_tests()
