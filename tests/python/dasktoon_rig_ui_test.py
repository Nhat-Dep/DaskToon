# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig interface: Add › Armature › Anime Humanoid, the Anime Rig panels and their commands (spec 7); the auto rig
and the Check panel (docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md)."""

import math
import os
import sys
import types
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402


def facing_the_back():
    """A chibi Body modelled facing +Y, as lr_shape (one of the real models) was: its feet reach to +Y."""
    st = rt.st
    return st.polyline_chibi(st.CentreLineTest.ARM, st.CentreLineTest.LEG, extra=[st.FacingTest.BACK])


def assert_turned_round(body):
    st = rt.st
    np.testing.assert_allclose(np.array(body.matrix_world), np.array(st.turned(math.pi, st.FacingTest.MIDDLE)),
                               atol=1e-5)


def select_only(objects, active):
    # Without a window, Context.selected_objects only lists objects the view layer has evaluated.
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def panel_context(obj):
    return types.SimpleNamespace(object=obj, scene=bpy.context.scene, mode='OBJECT')


def chibi_meshes():
    """The meshes of the regions test's chibi (Body, Shirt, Boots), without its skeleton."""
    rig, objs, _parts = rt.character()
    armature = rig.data
    bpy.data.objects.remove(rig)
    bpy.data.armatures.remove(armature)
    return objs


def add_skirt_and_hair(rig):
    """A flared skirt and a lock of hair hanging behind the head, both added as Clothing."""
    skirt = rt.merged("Circle.007", [rt.st.tube((0, 0, 0.92), (0, 0, 0.62), 0.22)])
    for v in skirt.data.vertices:  # wider at the hem
        if v.co.z < 0.8:
            v.co.x *= 1.4
            v.co.y *= 1.4
    hair = rt.merged("Circle.008", [rt.st.tube((0, 0.32, 1.95), (0, 0.36, 1.2), 0.05)])
    ui.add_part(rig, skirt, 'CLOTHING')
    ui.add_part(rig, hair, 'CLOTHING')
    return skirt, hair


def tear_left_arm(rig, objs):
    """Weights tearing the chibi's left arm when it rises: a ring halfway down it on the hips (the tests of the Check
    do not hang on what the auto rig leaves torn)."""
    from dasktoon_rig import parts as rig_parts, weights
    body = objs["Body"]
    arm = rt.piece_at(body, rt.ARM_END)
    world, _edges = rig_parts.mesh_arrays(body)
    axis = np.array(rt.ARM_END - rt.ARM_START)
    ring = arm[np.abs((world[arm] - np.array(rt.ARM_START)) @ axis / (axis @ axis) - 0.5) < 0.05]
    weights.clear(body, ring, [bone.name for bone in rig.data.bones if bone.use_deform])
    weights.write(body, ring, ["Hips"], np.ones((len(ring), 1)))


def move_left_wrist(rig, x):
    rig.data.use_mirror_x = False  # the right wrist stays
    with skeleton.editing(bpy.context, rig) as edit:
        edit["LeftHand"].head.x += x  # the elbow-to-wrist bone follows: it is connected
        edit["LeftHand"].tail.x += x


def properties_spaces():
    return [area.spaces.active for window in bpy.context.window_manager.windows for area in window.screen.areas
            if area.type == 'PROPERTIES']


def logged(log, idname):
    """[(text, properties)] of each logged button of operator `idname`."""
    return [(entry[2], entry[5]) for entry in log if entry[0] == "operator" and entry[1] == idname]


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

    def test_add_turns_a_character_facing_the_back(self):
        """The skeleton faces -Y, as Unity wants: a character modelled facing +Y is turned round on the spot before
        the skeleton is fitted, so its left gets the left bones and its knees bend the right way."""
        body = facing_the_back()
        select_only([body], body)
        bpy.ops.dasktoon.rig_add_humanoid()
        assert_turned_round(body)

    def test_add_rigs_the_selected_character(self):
        """Selected meshes: one press adds the skeleton fitted to them, recognizes the regions and locks, builds the rig
        and checks it (auto rig spec 2); the Properties editor shows the rig's data, where Anime Rig is."""
        objs = chibi_meshes()
        for space in properties_spaces():
            space.context = 'OBJECT'
        select_only(list(objs.values()), objs["Body"])
        self.assertEqual(bpy.ops.dasktoon.rig_add_humanoid(), {'FINISHED'})
        rig = bpy.context.view_layer.objects.active
        data = rig.data.dasktoon_rig
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertEqual(sorted(part.name for part in data.parts if part.made_by_recognize),
                         ["Lock L1", "Lock R1", "Lock R2"])
        self.assertTrue(any(m.type == 'ARMATURE' and m.object == rig for m in objs["Body"].modifiers))  # built
        self.assertTrue(data.checked)
        # The chibi's arms and legs are tubes pushed into its torso: Bone Heat blends their first rings with the chest
        # and the hips, and raising the arms or sitting tears them there (by 7 and 20 cm), which the Check rightly
        # finds; nothing else (not the strap on the shirt, which turned with the head under a head region reaching
        # down over the chest).
        found = {(item.kind, item.pose, item.region) for item in data.issues}
        self.assertTrue(found)
        self.assertLessEqual(found, {('STRETCH', 'ARMS_UP', 'ARM_L'), ('STRETCH', 'ARMS_UP', 'ARM_R'),
                                     ('STRETCH', 'SIT', 'LEG_L'), ('STRETCH', 'SIT', 'LEG_R')})
        self.assertTrue(properties_spaces())
        self.assertEqual({space.context for space in properties_spaces()}, {'DATA'})
        self.assertTrue(rig.select_get())

    def test_add_keeps_the_skeleton_when_the_rig_cannot_be_built(self):
        objs = fx.character()
        objs["Shirt"].data = objs["Body"].data  # one mesh for two objects: Build cannot paint it
        select_only([objs["Body"], objs["Shirt"]], objs["Body"])
        with self.assertRaises(RuntimeError) as caught:
            bpy.ops.dasktoon.rig_add_humanoid()
        self.assertIn("the rig could not be built", str(caught.exception))
        self.assertIn("shares its mesh with other objects", str(caught.exception))
        rig = bpy.context.view_layer.objects.active
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertEqual(len(rig.data.dasktoon_rig.parts), 2)
        self.assertFalse(rig.data.dasktoon_rig.checked)

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
        self.assertIn("shoulder_follow", [entry[1] for entry in log if entry[0] == "prop"])
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

    def test_fit_turns_a_character_facing_the_back(self):
        body = facing_the_back()
        ui.add_part(self.rig, body, 'BODY')
        select_only([self.rig], self.rig)
        self.assertEqual(bpy.ops.dasktoon.rig_fit(), {'FINISHED'})
        assert_turned_round(body)

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


class CheckPanelTest(unittest.TestCase):
    """The Check panel (auto rig spec 5): the test poses, the list of spots to look at and the buttons that fix them."""

    def setUp(self):
        self.rig, self.objs = rt.rigged()
        select_only([self.rig], self.rig)
        self.data = self.rig.data.dasktoon_rig

    def draw(self):
        return tu.draw(ui.DATA_PT_dasktoon_rig_check, panel_context(self.rig))

    def first_stretch(self):
        return next(i for i, item in enumerate(self.data.issues) if item.kind == 'STRETCH')

    def test_panel_comes_first_with_the_test_poses(self):
        self.assertEqual(ui.DATA_PT_dasktoon_rig_check.bl_parent_id, "DATA_PT_dasktoon_rig")
        children = [cls for cls in ui.classes if getattr(cls, "bl_parent_id", "") == "DATA_PT_dasktoon_rig"]
        self.assertIs(children[0], ui.DATA_PT_dasktoon_rig_check)
        log = self.draw()
        self.assertEqual([props.pose for _text, props in logged(log, "dasktoon.rig_test_pose")],
                         ['ARMS_UP', 'SIT', 'TURN_HEAD', 'WAVE', 'REST'])
        self.assertIn("Not checked yet", tu.labels(log))
        self.assertEqual([text for text, _props in logged(log, "dasktoon.rig_check")], ["Check"])
        self.data.checked = True  # checked, nothing found
        log = self.draw()
        self.assertIn("Nothing to fix found", tu.labels(log))
        self.assertEqual([text for text, _props in logged(log, "dasktoon.rig_check")], ["Check Again"])
        self.assertTrue(logged(log, "dasktoon.rig_check_done"))

    def test_panel_without_a_standard_skeleton(self):
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Hips"])
        self.assertIn("The Check needs a standard skeleton", tu.labels(self.draw()))
        with self.assertRaises(RuntimeError) as caught:
            bpy.ops.dasktoon.rig_check()
        self.assertIn("is not a standard skeleton", str(caught.exception))

    def test_test_poses(self):
        self.assertEqual(bpy.ops.dasktoon.rig_test_pose(pose='ARMS_UP'), {'FINISHED'})
        hand = self.rig.matrix_world @ self.rig.pose.bones["LeftHand"].head
        shoulder = self.rig.matrix_world @ self.rig.pose.bones["LeftUpperArm"].head
        self.assertGreater(hand.z, shoulder.z + 0.2)
        self.assertEqual(bpy.ops.dasktoon.rig_test_pose(pose='REST'), {'FINISHED'})
        self.assertTrue(ui.at_rest(self.rig))
        self.assertIsNone(getattr(self.rig.animation_data, "action", None))  # nothing keyed (drivers live there too)

    def test_the_list_and_its_buttons(self):
        add_skirt_and_hair(self.rig)
        self.assertEqual(bpy.ops.dasktoon.rig_build(), {'FINISHED'})
        tear_left_arm(self.rig, self.objs)
        move_left_wrist(self.rig, 0.2)
        self.assertEqual(bpy.ops.dasktoon.rig_check(), {'FINISHED'})
        log = self.draw()
        labels = tu.labels(log)
        for sentence in ("Left wrist is outside the body", "Circle.007 looks like a skirt",
                         "Circle.008 looks like hair", "Left Arm stretched in the Arms Up pose (Body)"):
            self.assertIn(sentence, labels)
        self.assertEqual([(text, props.bone) for text, props in logged(log, "dasktoon.rig_fix_joint")],
                         [("Fix", "LeftHand")])
        roles = sorted((text, props.part, props.role) for text, props in logged(log, "dasktoon.rig_change_role"))
        self.assertEqual(roles, [("Make it Hair", "Circle.008", 'HAIR'), ("Make it a Skirt", "Circle.007", 'SKIRT')])
        shown = [props.index for _text, props in logged(log, "dasktoon.rig_show_spot")]
        painted = [props.index for _text, props in logged(log, "dasktoon.rig_paint_spot")]
        self.assertTrue(shown)
        self.assertEqual(painted, shown)  # every spot here is on a Body or Clothing mesh
        self.assertEqual({self.data.issues[i].kind for i in shown}, {'STRETCH'})
        self.assertIn("After a fix, press Build Rig to check again", labels)
        self.assertEqual([text for text, _props in logged(log, "dasktoon.rig_check")], ["Check Again"])

    def test_icons_exist(self):
        """The recording layout takes any icon name; Blender's does not (a wrong one stops the panel drawing)."""
        add_skirt_and_hair(self.rig)
        bpy.ops.dasktoon.rig_build()
        tear_left_arm(self.rig, self.objs)
        move_left_wrist(self.rig, 0.2)
        bpy.ops.dasktoon.rig_check()
        self.assertEqual({'JOINT', 'STRETCH', 'ROLE'}, {item.kind for item in self.data.issues})
        icons = set(bpy.types.UILayout.bl_rna.functions["operator"].parameters["icon"].enum_items.keys())
        used = {entry[3] for entry in self.draw() if entry[0] in ("operator", "label")}
        self.assertEqual(used - icons, set())

    def test_fix_selects_the_joint(self):
        self.assertEqual(bpy.ops.dasktoon.rig_fix_joint(bone="LeftHand"), {'FINISHED'})
        self.assertEqual(self.rig.mode, 'EDIT')
        self.assertTrue(self.rig.data.use_mirror_x)
        bones = self.rig.data.edit_bones
        self.assertEqual((bones["LeftHand"].select_head, bones["LeftHand"].select_tail, bones["LeftHand"].select),
                         (True, False, False))
        self.assertTrue(bones["LeftLowerArm"].select_tail)  # the same joint
        self.assertEqual(sum(bone.select_head or bone.select_tail for bone in bones), 2)
        self.assertEqual(bones.active.name, "LeftHand")
        bpy.ops.object.mode_set(mode='OBJECT')

    def test_show_and_paint_a_spot_then_done(self):
        from dasktoon_rig import check, regions
        bpy.ops.dasktoon.rig_build()
        tear_left_arm(self.rig, self.objs)
        bpy.ops.dasktoon.rig_check()
        index = self.first_stretch()
        issue = self.data.issues[index]
        body, region, spot = issue.object, issue.region, list(issue["vertices"])
        self.assertEqual(bpy.ops.dasktoon.rig_show_spot(index=index), {'FINISHED'})
        self.assertIs(ui.spot_shown(), self.rig)
        self.assertFalse(ui.at_rest(self.rig))  # in the pose of the spot
        corners = ui._spot["triangles"]
        self.assertTrue(len(corners))
        moved = check.deformed(self.rig, body)  # lit up where the pose moves the spot
        self.assertLess(np.linalg.norm(corners.mean(axis=0) - moved[spot].mean(axis=0)), 0.1)
        self.assertEqual(bpy.ops.dasktoon.rig_paint_spot(index=index), {'FINISHED'})
        self.assertEqual((bpy.context.object, body.mode), (body, 'VERTEX_PAINT'))
        self.assertEqual(body.data.color_attributes.active_color_name, regions.LAYER)
        color = bpy.context.scene.tool_settings.vertex_paint.unified_paint_settings.color
        for got, want in zip(color, regions.COLORS[region]):
            self.assertAlmostEqual(got, want, places=3)
        self.assertIs(ui.spot_shown(), self.rig)  # still lit while painting
        bpy.ops.dasktoon.rig_paint_done()
        self.assertEqual(bpy.context.object, self.rig)
        self.assertEqual(bpy.ops.dasktoon.rig_check_done(), {'FINISHED'})
        self.assertEqual((len(self.data.issues), self.data.checked), (0, False))
        self.assertIsNone(ui.spot_shown())

    def test_highlights_follow_the_pose(self):
        """The spot shows only while the rig is in its pose; the part, drawn at rest, only while the rig is at rest."""
        bpy.ops.dasktoon.rig_build()
        tear_left_arm(self.rig, self.objs)
        bpy.ops.dasktoon.rig_check()
        self.assertTrue(ui.at_rest(self.rig))
        bpy.ops.dasktoon.rig_show_spot(index=self.first_stretch())
        self.assertIs(ui.spot_shown(), self.rig)
        bpy.ops.dasktoon.rig_test_pose(pose='REST')
        self.assertIsNone(ui.spot_shown())
        bpy.ops.dasktoon.rig_show_spot(index=self.first_stretch())
        bpy.ops.dasktoon.rig_check()  # a new list: what was shown is not in it
        self.assertIsNone(ui._spot["rig"])

    def test_change_role_builds_and_checks_again(self):
        from dasktoon_rig import parts as rig_parts
        _skirt, hair = add_skirt_and_hair(self.rig)
        bpy.ops.dasktoon.rig_build()  # recognizes first: the hair hangs from the head, a lock of a Clothing mesh
        self.assertTrue(any(part.made_by_recognize and part.object == hair for part in self.data.parts))
        bpy.ops.dasktoon.rig_check()
        self.assertEqual(bpy.ops.dasktoon.rig_change_role(part="Circle.008", role='HAIR'), {'FINISHED'})
        part = next(part for part in self.data.parts if part.name == "Circle.008")
        self.assertEqual((part.role, part.bone_count), ('HAIR', rig_parts.BONE_COUNT))
        self.assertFalse(any(part.made_by_recognize and part.object == hair for part in self.data.parts))
        self.assertEqual([group.name for group in hair.vertex_groups if group.name.startswith("DT_Lock")], [])
        self.assertIn(rig_parts.ascii_name("Circle.008") + "_1", self.rig.data.bones)  # built again
        self.assertTrue(self.data.checked)
        self.assertEqual([(item.part, item.role) for item in self.data.issues if item.kind == 'ROLE'],
                         [("Circle.007", 'SKIRT')])
        with self.assertRaises(RuntimeError) as caught:
            bpy.ops.dasktoon.rig_change_role(part="Nothing", role='SKIRT')
        self.assertIn("There is no part Nothing", str(caught.exception))

    def test_change_role_of_a_part_without_a_mesh_keeps_the_locks(self):
        """A part whose mesh is gone cannot be built; the locks of the other meshes stay (no mesh is not every mesh)."""
        bpy.ops.dasktoon.rig_build()
        part = ui.add_part(self.rig, self.objs["Shirt"], 'CLOTHING', name="Gone")
        part.object = None
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.rig_change_role(part="Gone", role='HAIR')
        self.assertEqual(sorted(part.name for part in self.data.parts if part.made_by_recognize),
                         ["Lock L1", "Lock R1", "Lock R2"])

    def test_build_checks_again_when_a_list_shows(self):
        bpy.ops.dasktoon.rig_build()
        self.assertFalse(self.data.checked)  # Build checks only to keep a list up to date
        bpy.ops.dasktoon.rig_check()
        move_left_wrist(self.rig, 0.2)
        bpy.ops.dasktoon.rig_build()
        self.assertIn(('JOINT', "LeftHand"), [(item.kind, item.bone) for item in self.data.issues])


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
        self.assertEqual(len(operators), 20)
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

    def test_check_words_are_translated(self):
        """The joints in the Check's sentences, and the poses and Show, which Blender's own words would take ("Wave" is
        a modifier there)."""
        tr = bpy.app.translations
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(set(ui.JOINT_NAMES.values())), [])
            self.assertEqual([tr.pgettext_iface(name, "DaskToon") for _identifier, name, _tip in ui.POSE_ITEMS],
                             ["Giơ tay", "Ngồi", "Quay đầu", "Vẫy tay", "Về nghỉ"])
            self.assertEqual(tr.pgettext_iface("Show", "DaskToon"), "Xem")
            self.assertEqual(ui.issue_sentence(types.SimpleNamespace(kind='JOINT', bone="LeftHand")),
                             "Cổ tay trái nằm ngoài thân")
            self.assertEqual(ui.issue_sentence(types.SimpleNamespace(kind='STRETCH', region='HEAD', pose='ARMS_UP',
                                                                     part="Body")),
                             "Đầu bị kéo giãn ở tư thế Giơ tay (Body)")

    def test_chains_has_its_own_vietnamese_word(self):
        self.assertEqual(ui.DaskRigPart.bl_rna.properties["chain_count"].translation_context, "DaskToon")
        with iu.language('vi_VN'):
            self.assertEqual(bpy.app.translations.pgettext_iface("Chains", "DaskToon"), "Số chuỗi")

    def test_role_icons_exist(self):
        icons = {i.identifier for i in bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items}
        self.assertTrue(set(ui.ROLE_ICONS.values()) <= icons)


if __name__ == "__main__":
    tu.run_tests()
