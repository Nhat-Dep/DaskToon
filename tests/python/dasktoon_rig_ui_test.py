# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig interface: Add › Armature › Anime Humanoid, the Anime Rig panels and their commands (spec 7)."""

import os
import sys
import types
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402


def select_only(objects, active):
    # Without a window, Context.selected_objects only lists objects the view layer has evaluated.
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def panel_context(obj):
    return types.SimpleNamespace(object=obj, scene=bpy.context.scene, mode='OBJECT')


class AddTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_menu_entry(self):
        from bl_ui.space_view3d import VIEW3D_MT_armature_add
        self.assertTrue(VIEW3D_MT_armature_add.is_extended())
        log = tu.RecordingLayout()
        for draw in VIEW3D_MT_armature_add._dyn_ui_initialize():
            draw(types.SimpleNamespace(layout=log), bpy.context)
        self.assertIn(("dasktoon.rig_add_humanoid", "Anime Humanoid"), tu.operators(log.log))

    def test_add_fits_and_makes_parts(self):
        objs = fx.character()
        select_only([objs["Body"], objs["Hair"], objs["Shirt"]], objs["Body"])
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertTrue(rig.select_get())
        self.assertFalse(objs["Body"].select_get())
        top = (rig.matrix_world @ rig.data.bones["Head"].tail_local).z
        self.assertAlmostEqual(top, 0.05 * fx.HEIGHT + 0.99 * (0.96 - 0.05) * fx.HEIGHT, places=3)
        roles = {p.object.name: p.role for p in rig.data.dasktoon_rig.parts}
        self.assertEqual(roles, {"Body": 'BODY', "Hair": 'HAIR', "Shirt": 'CLOTHING'})

    def test_add_without_meshes_uses_the_cursor(self):
        bpy.context.scene.cursor.location = (2.0, 0.0, 0.0)
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        self.assertEqual(tuple(rig.matrix_world.translation), (2.0, 0.0, 0.0))
        self.assertEqual(len(rig.data.dasktoon_rig.parts), 0)


class PanelTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        select_only([self.rig], self.rig)

    def test_joints_panel(self):
        log = tu.draw(ui.DATA_PT_dasktoon_rig_joints, panel_context(self.rig))
        self.assertIn("Standard skeleton", tu.labels(log))
        ops = [name for name, _text in tu.operators(log)]
        self.assertEqual(ops, ["dasktoon.rig_edit_joints", "dasktoon.rig_fit"])
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Spine"])
        log = tu.draw(ui.DATA_PT_dasktoon_rig_joints, panel_context(self.rig))
        self.assertIn("Missing bones: Spine", tu.labels(log))

    def test_parts_panel_and_commands(self):
        log = tu.draw(ui.DATA_PT_dasktoon_rig_parts, panel_context(self.rig))
        self.assertIn("Select meshes and press + to add them as parts", tu.labels(log))
        select_only([self.rig, self.objs["Body"], self.objs["Skirt"]], self.rig)
        bpy.ops.dasktoon.rig_add_selected()
        bpy.ops.dasktoon.rig_add_selected()  # already there: nothing new
        parts = self.rig.data.dasktoon_rig.parts
        self.assertEqual([(p.name, p.role, p.bone_count) for p in parts], [("Body", 'BODY', 4), ("Skirt", 'SKIRT', 3)])
        log = tu.draw(ui.DATA_PT_dasktoon_rig_parts, panel_context(self.rig))
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertEqual(props, ["object", "scope", "role", "bone_count", "chain_count"])
        self.assertIn(("call", "prop_search"), [entry[:2] for entry in log])
        self.objs["Body"].data.materials.append(bpy.data.materials.new("Skin"))
        self.rig.data.dasktoon_rig.active_part_index = 0
        bpy.ops.dasktoon.rig_add_material_part(material="Skin")
        self.assertEqual((parts[2].scope, parts[2].material, parts[2].role), ('MATERIAL', "Skin", 'BODY'))
        bpy.ops.dasktoon.rig_remove_part()
        self.assertEqual(len(parts), 2)

    def test_build_command(self):
        select_only([self.rig] + list(self.objs.values()), self.rig)
        bpy.ops.dasktoon.rig_add_selected()
        bpy.ops.dasktoon.rig_build()
        self.assertIn("Hair_4", self.rig.data.bones)
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)
        self.assertEqual(len(tu.draw(ui.DATA_PT_dasktoon_rig_build, panel_context(self.rig))), 2)

    def test_build_error_is_reported(self):
        with self.assertRaises(RuntimeError) as caught:
            bpy.ops.dasktoon.rig_build()
        self.assertIn("Add parts before building the rig", str(caught.exception))

    def test_part_from_selection(self):
        body = self.objs["Body"]
        select_only([body], body)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in body.data.vertices[:16]:
            v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertIs(ui.find_rig(bpy.context, body), self.rig)
        bpy.ops.dasktoon.rig_part_from_selection(part_name="Collar", role='ACCESSORY', rig=self.rig.name)
        self.assertEqual(body.mode, 'EDIT')
        part = self.rig.data.dasktoon_rig.parts[-1]
        self.assertEqual((part.name, part.scope, part.vertex_group, part.role),
                         ("Collar", 'VERTEX_GROUP', "DT_Collar", 'ACCESSORY'))
        bpy.ops.object.mode_set(mode='OBJECT')
        members = [v.index for v in body.data.vertices if any(g.group == body.vertex_groups["DT_Collar"].index
                                                                for g in v.groups)]
        self.assertEqual(members, list(range(16)))
        log = tu.draw(ui.DATA_PT_dasktoon_rig_mesh, panel_context(body))
        self.assertIn("dasktoon.rig_part_from_selection", [name for name, _text in tu.operators(log)])
        self.assertIn("role", [entry[1] for entry in log if entry[0] == "prop"])


class SwayPanelTest(unittest.TestCase):
    def test_sway_panel_and_bake(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        select_only([rig, objs["Body"], objs["Hair"]], rig)
        bpy.ops.dasktoon.rig_add_selected()
        log = tu.draw(ui.DATA_PT_dasktoon_rig_sway, panel_context(rig))
        self.assertIn("Build Rig first to make the hair and skirt chains", tu.labels(log))
        bpy.ops.dasktoon.rig_build()
        rig.data.dasktoon_rig.active_part_index = 1  # Hair
        log = tu.draw(ui.DATA_PT_dasktoon_rig_sway, panel_context(rig))
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertEqual(props, ["live_sway", "stiffness", "gravity", "drag", "radius", "sway_in_unity"])
        self.assertIn("dasktoon.rig_bake_sway", [name for name, _text in tu.operators(log)])
        self.assertEqual(ui.DATA_PT_dasktoon_rig_colliders.bl_parent_id, "DATA_PT_dasktoon_rig_sway")
        self.assertIn('DEFAULT_CLOSED', ui.DATA_PT_dasktoon_rig_colliders.bl_options)
        log = tu.draw(ui.DATA_PT_dasktoon_rig_colliders, panel_context(rig))
        self.assertEqual([entry[1] for entry in log if entry[0] == "prop"], ["radius"] * 14)
        bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 5
        bpy.ops.dasktoon.rig_bake_sway()
        self.assertFalse(rig.data.dasktoon_rig.live_sway)


class TextTest(unittest.TestCase):
    def test_properties_and_enums_are_translated(self):
        # Registered property groups are not in bpy.types: take the classes from the module.
        strings = {ui.DaskRigPart.bl_rna.description, ui.DaskRig.bl_rna.description,
                   ui.DaskRigCollider.bl_rna.description}
        operators = [cls for cls in ui.classes if issubclass(cls, bpy.types.Operator)]
        self.assertEqual(len(operators), 9)
        for struct in operators:
            strings.update((struct.bl_label, struct.__doc__))
        for struct in [ui.DaskRigPart, ui.DaskRigCollider, ui.DaskRig] + operators:
            for prop in struct.bl_rna.properties:
                if prop.identifier not in struct.__annotations__:  # Operator's own RNA (bl_options...) is Blender's
                    continue
                strings.update((prop.name, prop.description))
                if prop.type == 'ENUM':
                    for item in prop.enum_items_static:
                        strings.update((item.name, item.description))
        strings.discard("")
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])

    def test_chains_has_its_own_vietnamese_word(self):
        self.assertEqual(ui.DaskRigPart.bl_rna.properties["chain_count"].translation_context, "DaskToon")
        with iu.language('vi_VN'):
            self.assertEqual(bpy.app.translations.pgettext_iface("Chains", "DaskToon"), "Số chuỗi")

    def test_role_icons_exist(self):
        icons = {i.identifier for i in bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items}
        self.assertTrue(set(ui.ROLE_ICONS.values()) <= icons)


if __name__ == "__main__":
    tu.run_tests()
