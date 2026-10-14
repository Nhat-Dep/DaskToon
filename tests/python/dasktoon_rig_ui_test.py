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

    def test_add_follows_the_shape_of_the_character(self):
        """Adding the skeleton to selected meshes fits it to their shape at once (no separate Fit to Parts for someone
        new to rigging): the arms of an A-pose chibi reach its hands."""
        import dasktoon_rig_skeleton_test as st
        body, ears, marks = st.chibi()
        select_only([body, ears], body)
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        tip = rig.matrix_world @ rig.data.bones["LeftMiddleDistal"].tail_local
        self.assertLess((tip - marks["tip_left"]).length, 0.06)

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

    def test_fit_in_edit_mode_stays_in_edit_mode(self):
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.rig_fit(), {'FINISHED'})
        self.assertEqual(self.rig.mode, 'EDIT')
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)

    def test_fit_reads_the_shape_of_the_body_and_clothing_only(self):
        """A staff held out to the side, an Accessory part, is not read as an arm."""
        h = fx.HEIGHT
        verts, faces = fx.cube((0.0, 0.0, 0.0), 1.0 / h)  # a cube 1 wide, stretched into a staff from x 0.04h to 0.6h
        staff = fx.mesh_object("Staff", [(0.32 * h + x * 0.56 * h, y * 0.02 * h, 0.5 * h + z * 0.02 * h)
                                         for x, y, z in verts], faces)
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        ui.add_part(self.rig, staff, 'ACCESSORY')
        select_only([self.rig], self.rig)
        self.assertEqual(bpy.ops.dasktoon.rig_fit(), {'FINISHED'})
        arm = self.rig.matrix_world @ self.rig.data.bones["LeftUpperArm"].head_local
        low, high = 0.05 * h, 0.86 * h  # the Body tube: the template's shoulders, no arm found
        self.assertAlmostEqual(arm.z, low + 0.78 * (high - low), delta=0.01 * h)

    def test_parts_list_names_the_object_only_when_it_differs(self):
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        ui.add_part(self.rig, self.objs["Body"], 'CLOTHING', name="Skin")
        found = []
        for part in self.rig.data.dasktoon_rig.parts:
            log = tu.RecordingLayout()
            ui.DASKTOON_UL_rig_parts.draw_item(None, bpy.context, log, None, part, 0, None, "", 0)
            found.append(tu.labels(log.log))
        self.assertEqual(found, [[], ["Body"]])

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
        self.assertEqual(props, ["highlight_part", "object", "scope", "role", "bone_count", "chain_count"])
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

    def test_lock_from_selection(self):
        hair = self.objs["Hair"]
        select_only([hair], hair)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        hair.data.vertices[0].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.rig_lock_from_selection(), {'FINISHED'})
        self.assertEqual(hair.mode, 'EDIT')
        part = self.rig.data.dasktoon_rig.parts[-1]
        self.assertEqual((part.name, part.object, part.vertex_group, part.role, part.bone, part.made_by_recognize),
                         ("Lock M1", hair, "DT_Lock M1", 'ACCESSORY', "Head", False))
        bpy.ops.object.mode_set(mode='OBJECT')
        from dasktoon_rig import parts as rig_parts
        self.assertEqual(len(rig_parts.part_vertices(part)), len(hair.data.vertices))  # the whole piece
        log = tu.draw(ui.DATA_PT_dasktoon_rig_mesh, panel_context(hair))
        self.assertIn("dasktoon.rig_lock_from_selection", [name for name, _text in tu.operators(log)])



class RegionsPanelTest(unittest.TestCase):
    """The Regions panel (rig regions spec 6): Recognize, Show Regions, painting each region, highlighting a part."""

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        for name, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR')):
            ui.add_part(self.rig, self.objs[name], role)
        select_only([self.rig], self.rig)

    def test_panel(self):
        log = tu.draw(ui.DATA_PT_dasktoon_rig_regions, panel_context(self.rig))
        ops = tu.operators(log)
        self.assertEqual(ops[0][0], "dasktoon.rig_recognize")
        self.assertIn("dasktoon_show_regions", [entry[1] for entry in log if entry[0] == "prop"])
        painted = [entry for entry in log if entry[0] == "operator" and entry[1] == "dasktoon.rig_paint_regions"]
        self.assertEqual([(entry[5].region, entry[3]) for entry in painted],
                         [('HEAD', 'STRIP_COLOR_03'), ('TORSO', 'STRIP_COLOR_05'),
                          ('ARM_L', 'STRIP_COLOR_01'), ('ARM_R', 'STRIP_COLOR_02'),
                          ('LEG_L', 'STRIP_COLOR_04'), ('LEG_R', 'STRIP_COLOR_06')])

    def test_region_icons_exist(self):
        """The recording layout takes any icon name; Blender's does not (a wrong one stops the panel drawing)."""
        icons = bpy.types.UILayout.bl_rna.functions["operator"].parameters["icon"].enum_items.keys()
        for item in ui.REGION_ITEMS + ui.ROLE_ITEMS:
            self.assertIn(item[3], icons, item[0])

    def test_recognize(self):
        from dasktoon_rig import regions
        self.assertEqual(bpy.ops.dasktoon.rig_recognize(), {'FINISHED'})
        for name in ("Body", "Shirt"):
            self.assertIsNotNone(self.objs[name].data.color_attributes.get(regions.LAYER), name)
        self.assertIsNone(self.objs["Hair"].data.color_attributes.get(regions.LAYER))  # Hair parts have no regions

    def test_paint_regions_then_done(self):
        from dasktoon_rig import regions
        body = self.objs["Body"]
        self.rig.data.dasktoon_rig.active_part_index = 0
        self.assertEqual(bpy.ops.dasktoon.rig_paint_regions(region='ARM_L'), {'FINISHED'})
        self.assertEqual((bpy.context.object, body.mode), (body, 'VERTEX_PAINT'))
        self.assertEqual(body.data.color_attributes.active_color_name, regions.LAYER)
        paint = bpy.context.scene.tool_settings.vertex_paint
        self.assertEqual(paint.palette.name, "DaskToon Regions")
        self.assertEqual(len(paint.palette.colors), 6)
        settings = paint.unified_paint_settings
        self.assertTrue(settings.use_unified_color)
        for got, want in zip(settings.color, regions.COLORS['ARM_L']):
            self.assertAlmostEqual(got, want, places=3)
        self.assertTrue(bpy.context.window_manager.dasktoon_show_regions)
        log = tu.draw(ui.DATA_PT_dasktoon_rig_mesh, types.SimpleNamespace(object=body, scene=bpy.context.scene,
                                                                          mode='PAINT_VERTEX'))
        names = [name for name, _text in tu.operators(log)]
        self.assertEqual(names.count("dasktoon.rig_paint_regions"), 6)
        self.assertIn("dasktoon.rig_paint_done", names)
        self.assertEqual(bpy.ops.dasktoon.rig_paint_regions(region='LEG_R'), {'FINISHED'})  # another color
        self.assertAlmostEqual(settings.color[2], regions.COLORS['LEG_R'][2], places=3)
        self.assertEqual(bpy.ops.dasktoon.rig_paint_done(), {'FINISHED'})
        self.assertEqual((body.mode, bpy.context.object), ('OBJECT', self.rig))

    def test_show_regions_and_back(self):
        from dasktoon_rig import regions
        bpy.ops.dasktoon.rig_recognize()
        body = self.objs["Body"]
        spaces = [space for screen in bpy.data.screens for area in screen.areas for space in area.spaces
                  if space.type == 'VIEW_3D']
        self.assertTrue(spaces)
        before = [(space.shading.type, space.shading.color_type) for space in spaces]
        wm = bpy.context.window_manager
        wm.dasktoon_show_regions = True
        self.assertEqual({(space.shading.type, space.shading.color_type) for space in spaces}, {('SOLID', 'VERTEX')})
        self.assertEqual(body.data.color_attributes.active_color_name, regions.LAYER)
        wm.dasktoon_show_regions = False
        self.assertEqual([(space.shading.type, space.shading.color_type) for space in spaces], before)
        self.assertEqual(body.data.color_attributes.active_color_name, "")

    def test_buttons_report_a_skeleton_they_cannot_use(self):
        """Not a standard skeleton: Build and Recognize say so, as Build always did, before recognizing anything."""
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Hips"])  # the bone recognizing measures from
        for op, args in ((bpy.ops.dasktoon.rig_build, {}), (bpy.ops.dasktoon.rig_recognize, {}),
                         (bpy.ops.dasktoon.rig_paint_regions, {"region": 'HEAD'})):
            with self.assertRaises(RuntimeError) as caught:
                op(**args)
            self.assertIn("is not a standard skeleton", str(caught.exception))

    def test_highlight_part(self):
        data = self.rig.data.dasktoon_rig
        self.assertTrue(data.highlight_part)
        body = self.objs["Body"]
        triangles = ui.part_triangles(data.parts[0])
        body.data.calc_loop_triangles()
        self.assertEqual(len(triangles), 3 * len(body.data.loop_triangles))
        self.assertIsNotNone(ui._highlight["handle"])

    def test_highlight_is_made_again_only_when_a_mesh_changes(self):
        """Not on every frame the armature deforms the meshes: only when mesh data changes."""
        generation = ui._highlight["generation"]
        moved = types.SimpleNamespace(id=self.objs["Body"], is_updated_geometry=True)
        ui._highlight_depsgraph(None, types.SimpleNamespace(updates=[moved]))
        self.assertEqual(ui._highlight["generation"], generation)
        edited = types.SimpleNamespace(id=self.objs["Body"].data, is_updated_geometry=True)
        ui._highlight_depsgraph(None, types.SimpleNamespace(updates=[edited]))
        self.assertEqual(ui._highlight["generation"], generation + 1)


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
        self.assertEqual(len(operators), 13)
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
