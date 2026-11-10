# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Machine rig interface (machine rig spec 1): Object › Create Machine Rig, the Machine Rig panels of an armature and
of a mesh, the commands behind their buttons. The Add Joint tool's clicks are tested on its ToolState
(dasktoon_machine_test.py)."""

import os
import sys
import types
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_machine_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_machine as machine  # noqa: E402
from bl_ui import dasktoon_machine as ui  # noqa: E402
from bl_ui import dasktoon_rig as rig_ui  # noqa: E402
from dasktoon_machine import joints, pieces, tool  # noqa: E402


def select_only(objects, active):
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def panel_context(obj):
    return types.SimpleNamespace(object=obj, scene=bpy.context.scene, mode='OBJECT')


def ops(log):
    return [name for name, _text in tu.operators(log)]


class UiTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs, parts = fx.machine()
        self.p = {name: pieces.piece_of_vertex(o, i) for name, (o, i) in parts.items()}
        select_only(list(self.objs.values()), self.objs["Mech"])
        self.assertEqual(bpy.ops.dasktoon.machine_create(), {'FINISHED'})
        self.rig = bpy.context.view_layer.objects.active

    def leg(self):
        t = tool.ToolState(bpy.context, self.rig)
        t.click(self.p["Body"])
        t.click(None)
        t.confirm()
        for name, (pivot, axis) in (("Thigh", fx.HIP), ("Shin", fx.KNEE), ("Foot", fx.ANKLE)):
            t.click(self.p[name])
            t.move_pivot(pivot)
            t.set_axis(axis)
            t.joint.kind = 'HINGE'
            t.confirm()

    def test_object_menu_has_create(self):
        log = tu.draw(bpy.types.VIEW3D_MT_object)
        self.assertIn("dasktoon.machine_create", ops(log))

    def test_create_makes_the_rig_active_and_counts_pieces(self):
        self.assertTrue(machine.is_machine(self.rig))
        self.assertEqual(self.rig.data.dasktoon_machine.unbound, len(fx.PARTS))
        self.assertEqual(self.rig.name, "Mech Machine")
        log = tu.draw(ui.DATA_PT_dasktoon_machine, panel_context(self.rig))
        self.assertIn("dasktoon.machine_joint_tool", ops(log))
        self.assertIn("%d pieces have no joint yet (red in the tool)" % len(fx.PARTS), tu.labels(log))

    def test_anime_rig_panels_stay_away_from_a_machine(self):
        self.assertFalse(rig_ui.DATA_PT_dasktoon_rig.poll(panel_context(self.rig)))
        self.assertTrue(ui.DATA_PT_dasktoon_machine.poll(panel_context(self.rig)))
        self.assertFalse(ui.DATA_PT_dasktoon_machine.poll(panel_context(self.objs["Mech"])))

    def test_mesh_panel(self):
        log = tu.draw(ui.DATA_PT_dasktoon_machine_mesh, panel_context(self.objs["Mech"]))
        self.assertIn("dasktoon.machine_piece_from_selection", ops(log))
        other = fx.cylinder((3, 0, 0), 'Z', 0.1, 0.1)
        mesh = bpy.data.meshes.new("Other")
        mesh.from_pydata(*other[:1], [], other[1])
        obj = bpy.data.objects.new("Other", mesh)
        bpy.context.scene.collection.objects.link(obj)
        log = tu.draw(ui.DATA_PT_dasktoon_machine_mesh, panel_context(obj))
        self.assertIn("dasktoon.machine_create", ops(log))

    def test_joint_panel_and_commands(self):
        log = tu.draw(ui.DATA_PT_dasktoon_machine_joint, panel_context(self.rig))
        self.assertIn("Select a joint (a bone) to set it up", tu.labels(log))
        self.leg()
        self.rig.data.bones.active = self.rig.data.bones["Shin"]
        log = tu.draw(ui.DATA_PT_dasktoon_machine_joint, panel_context(self.rig))
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertIn("kind", props)
        self.assertIn("angle_max", props)
        self.rig.data.bones.active = self.rig.data.bones["Foot"]
        select_only([self.rig], self.rig)
        self.assertEqual(bpy.ops.dasktoon.machine_leg_add(), {'FINISHED'})
        log = tu.draw(ui.DATA_PT_dasktoon_machine_legs, panel_context(self.rig))
        self.assertIn("dasktoon.machine_leg_snap", ops(log))
        self.assertEqual(bpy.ops.dasktoon.machine_leg_snap(target="IK Foot", to='FK'), {'FINISHED'})
        self.assertEqual(self.rig.pose.bones["IK Foot"]["IK_FK"], 1.0)
        self.assertEqual(bpy.ops.dasktoon.machine_leg_remove(target="IK Foot"), {'FINISHED'})
        self.assertNotIn("IK Foot", self.rig.data.bones)
        self.rig.data.bones.active = self.rig.data.bones["Shin"]
        self.assertEqual(bpy.ops.dasktoon.machine_remove_joint(), {'FINISHED'})
        self.assertNotIn("Shin", self.rig.data.bones)
        self.assertEqual(self.rig.data.dasktoon_machine.unbound, len(fx.PARTS) - 3)

    def test_aim_panel_and_commands(self):
        t = tool.ToolState(bpy.context, self.rig)
        for child, parent in ((["Turret", "EarL", "EarR"], "Body"), (["Trunnion", "Barrel"], "Turret")):
            t.default_parent = None
            t.click(self.p[child[0]])
            for name in child[1:]:
                t.click(self.p[name], shift=True)
            t.click(self.p[parent])
            t.confirm()
        gun = pieces.Binding(self.rig).bone_of(self.p["Trunnion"])
        self.rig.data.bones.active = self.rig.data.bones[gun]
        select_only([self.rig], self.rig)
        self.assertEqual(bpy.ops.dasktoon.machine_aim_add(), {'FINISHED'})
        log = tu.draw(ui.DATA_PT_dasktoon_machine_aim, panel_context(self.rig))
        self.assertIn("dasktoon.machine_aim_remove", ops(log))
        self.assertEqual(bpy.ops.dasktoon.machine_aim_remove(target="Aim " + gun), {'FINISHED'})
        log = tu.draw(ui.DATA_PT_dasktoon_machine_aim, panel_context(self.rig))
        self.assertIn("Select a barrel or an eye joint and press Add Aim Target", tu.labels(log))

    def test_piece_from_selection_in_edit_mode(self):
        mech = self.objs["Mech"]
        b = pieces.Binding(self.rig)
        barrel = set(b.verts(self.p["Barrel"]).tolist())
        for v in mech.data.vertices:
            v.select = False
        for e in mech.data.edges:
            e.select = False
        for poly in mech.data.polygons:
            poly.select = set(poly.vertices) <= barrel and poly.center.x > 0.45
            for v in poly.vertices if poly.select else ():
                mech.data.vertices[v].select = True
        select_only([mech], mech)
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.machine_piece_from_selection(), {'FINISHED'})
        self.assertEqual(mech.mode, 'EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.assertEqual(len(pieces.Binding(self.rig).pieces()), len(fx.PARTS) + 1)
        self.assertEqual(self.rig.data.dasktoon_machine.unbound, len(fx.PARTS) + 1)

    def test_overlay_reads_triangles_of_each_piece(self):
        overlay = ui._Overlay(pieces.Binding(self.rig))
        tri, owner = overlay.tris[self.objs["Mech"]]
        self.assertEqual(len(tri), len(owner))
        self.assertIn(self.p["Barrel"][1], owner.tolist())


class AdoptUiTest(unittest.TestCase):
    def test_make_pieces_rigid_selects_the_split_ones(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs, parts = fx.machine()
        p = {name: pieces.piece_of_vertex(o, i) for name, (o, i) in parts.items()}
        arm = bpy.data.armatures.new("Imported")
        rig = bpy.data.objects.new("Imported", arm)
        bpy.context.scene.collection.objects.link(rig)
        select_only([rig], rig)
        bpy.ops.object.mode_set(mode='EDIT')
        for name, head in (("a", (0, 0, 0)), ("b", (0, 0, 1))):
            eb = arm.edit_bones.new(name)
            eb.head, eb.tail = head, (head[0], 0.2, head[2])
        bpy.ops.object.mode_set(mode='OBJECT')
        mech = objs["Mech"]
        for name in ("a", "b"):
            mech.vertex_groups.new(name=name)
        mech.modifiers.new("Armature", 'ARMATURE').object = rig
        verts = pieces.Binding(rig, [mech]).verts(p["Body"]).tolist()
        mech.vertex_groups["a"].add(verts, 0.5, 'REPLACE')
        mech.vertex_groups["b"].add(verts, 0.5, 'REPLACE')
        for poly in mech.data.polygons:
            poly.select = False
        self.assertEqual(bpy.ops.dasktoon.machine_adopt(), {'FINISHED'})
        selected = {v for poly in mech.data.polygons if poly.select for v in poly.vertices}
        self.assertEqual(selected, set(verts))
        self.assertTrue(machine.is_machine(rig))


if __name__ == "__main__":
    tu.run_tests()
