# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import time
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402


def update():
    bpy.context.view_layer.update()


class OutlineSyncTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.obj = tu.add_sphere(segments=16, rings=8)
        self.mat, self.node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(self.obj, self.mat)
        update()

    def test_enable_creates_modifier_and_outline_material(self):
        self.assertIsNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        self.node.use_outline = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        companion = outline.outline_material_for(self.mat, create=False)
        self.assertEqual(companion.name, "Skin.Outline")
        self.assertEqual(len(self.obj.material_slots), 1)
        self.node.use_outline = False
        update()
        self.assertIsNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        self.assertIsNotNone(bpy.data.materials.get("Skin.Outline"))

    def test_reroute_between_node_and_output(self):
        nt = self.mat.node_tree
        output = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        reroute = nt.nodes.new('NodeReroute')
        nt.links.new(self.node.outputs[0], reroute.inputs[0])
        nt.links.new(reroute.outputs[0], output.inputs["Surface"])
        self.node.use_outline = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_rename_does_not_duplicate_outline_material(self):
        self.node.use_outline = True
        update()
        self.mat.name = "Face"
        self.obj.name = "Hero"
        self.node.inputs["Outline Width"].default_value = 0.01
        update()
        companions = [m for m in bpy.data.materials if m.name.endswith(".Outline")]
        self.assertEqual(len(companions), 1)
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_empty_slots_and_non_mesh_objects(self):
        self.obj.data.materials.append(None)
        bpy.ops.object.empty_add()
        bpy.ops.mesh.primitive_cube_add()  # no material at all
        self.node.use_outline = True
        update()
        outline.sync_all(bpy.context.scene)
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_linked_duplicates_keep_slot_count(self):
        self.node.use_outline = True
        update()
        for _i in range(200):
            dup = self.obj.copy()
            bpy.context.scene.collection.objects.link(dup)
        update()
        self.assertEqual(len(self.obj.data.materials), 1)

    def test_transform_only_update_is_cheap_and_writes_nothing(self):
        self.node.use_outline = True
        update()
        calls = []
        original = gn.build_object_group
        gn.build_object_group = lambda *a, **k: calls.append(1) or original(*a, **k)
        try:
            start = time.perf_counter()
            self.obj.location.x += 1.0
            update()
            elapsed = time.perf_counter() - start
        finally:
            gn.build_object_group = original
        self.assertEqual(calls, [])
        self.assertLess(elapsed, 0.05)

    def test_mesh_data_untouched(self):
        before = [tuple(v.co) for v in self.obj.data.vertices]
        self.node.use_outline = True
        update()
        self.assertEqual(before, [tuple(v.co) for v in self.obj.data.vertices])
        self.assertEqual(len(self.obj.data.materials), 1)

    def test_material_without_main_node_uses_checkbox(self):
        plain = tu.emission_material("Plain", (1, 1, 1, 1))
        tu.assign(self.obj, plain)
        plain[outline.OUTLINE_PROP] = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_quick_controls_reach_outline_material(self):
        self.node.use_outline = True
        self.node.outline_tint_mode = 'HARMONIC_KYOTO'
        self.node.inputs["Outline Color"].default_value = (0.2, 0.1, 0.05, 1.0)
        update()
        companion = outline.outline_material_for(self.mat, create=False)
        dask = outline.outline_node(companion)
        self.assertEqual(dask.bl_rna.properties["tint_mode"].enum_items[dask.tint_mode].value, 1)
        self.assertAlmostEqual(dask.inputs["Outline Color"].default_value[0], 0.2, places=4)

    def test_editing_companion_material_resyncs_object(self):
        """Light Bleed / Hand Wobble live on <material>.Outline, which is in no slot of the object."""
        self.node.use_outline = True
        self.node.inputs["Outline Width"].default_value = 0.05
        update()
        dask = outline.outline_node(outline.outline_material_for(self.mat, create=False))
        group = self.obj.modifiers[gn.MODIFIER_NAME].node_group
        bleed_tables = [n for n in group.nodes if n.bl_idname == 'GeometryNodeIndexSwitch']
        before = [n.inputs[1].default_value for n in bleed_tables]
        dask.inputs["Light Bleed"].default_value = 0.9
        update()
        group = self.obj.modifiers[gn.MODIFIER_NAME].node_group
        after = [n.inputs[1].default_value for n in group.nodes if n.bl_idname == 'GeometryNodeIndexSwitch']
        self.assertIn(0.9, [round(v, 4) for v in after if isinstance(v, float)])
        self.assertNotEqual(before, after)

    def test_outline_preset_operator(self):
        bpy.context.view_layer.objects.active = self.obj
        result = bpy.ops.dasktoon.setup_anime_preset(preset_type='OUTLINE')
        self.assertEqual(result, {'FINISHED'})
        update()
        self.assertTrue(self.node.use_outline)
        self.assertFalse(any(m.type == 'SOLIDIFY' for m in self.obj.modifiers))


if __name__ == "__main__":
    tu.run_tests()
