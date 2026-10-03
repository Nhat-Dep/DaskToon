# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""FBX for Unity keeps shape keys and DT_OutlineN/W and never contains the outline hull (spec 4)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402
from dasktoon_export import model_fbx  # noqa: E402


def outlined_character():
    tu.reset_scene()
    outline.reset_cache()
    obj = tu.add_sphere(segments=16, rings=8)
    obj.name = "Body"
    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.use_outline = True
    tu.assign(obj, mat)
    obj.shape_key_add(name="Basis")
    smile = obj.shape_key_add(name="Smile")
    smile.data[0].co.z += 0.1
    outline.sync_all(bpy.context.scene)
    return obj


class FbxTest(unittest.TestCase):
    def test_fbx_keeps_shape_keys_and_outline_uvs_without_hull(self):
        obj = outlined_character()
        self.assertIsNotNone(obj.modifiers.get(gn.MODIFIER_NAME))
        faces = len(obj.data.polygons)
        done, errors = model_fbx.prepare_outline_data([obj])
        self.assertEqual((done, errors), (["Body"], []))
        path = os.path.join(tempfile.mkdtemp(prefix="dt_fbx_"), "Hero.fbx")
        model_fbx.write_fbx(bpy.context, [obj], path, include_animation=False)
        tu.reset_scene()
        bpy.ops.import_scene.fbx(filepath=path)
        imported = next(o for o in bpy.data.objects if o.type == 'MESH')
        self.assertEqual(len(imported.data.polygons), faces)
        self.assertIn("Smile", imported.data.shape_keys.key_blocks)
        names = [uv.name for uv in imported.data.uv_layers]
        self.assertEqual(names[0], "UVMap")
        self.assertIn("DT_OutlineN", names)
        self.assertIn("DT_OutlineW", names)
        self.assertEqual([m.name for m in imported.data.materials], ["Skin"])

    def test_selection_is_restored_after_writing(self):
        obj = outlined_character()
        other = tu.add_sphere(segments=8, rings=4)
        bpy.context.view_layer.objects.active = other
        other.select_set(True)
        obj.select_set(False)
        path = os.path.join(tempfile.mkdtemp(prefix="dt_fbx_"), "Only.fbx")
        model_fbx.write_fbx(bpy.context, [obj], path, include_animation=False)
        self.assertTrue(other.select_get())
        self.assertFalse(obj.select_get())
        self.assertEqual(bpy.context.view_layer.objects.active, other)

    def test_selected_only_adds_the_deforming_armature(self):
        obj = outlined_character()
        arm = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        bpy.context.scene.collection.objects.link(arm)
        obj.modifiers.new("Armature", 'ARMATURE').object = arm
        for o in bpy.context.view_layer.objects:
            o.select_set(o == obj)
        chosen = model_fbx.export_objects(bpy.context, selected_only=True)
        self.assertEqual(set(o.name for o in chosen), {"Body", "Rig"})
        everything = model_fbx.export_objects(bpy.context, selected_only=False)
        self.assertNotIn("Camera", [o.name for o in everything])

    def test_outline_errors_are_reported_not_raised(self):
        obj = outlined_character()
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
        done, errors = model_fbx.prepare_outline_data([obj])
        self.assertEqual(done, [])
        self.assertEqual(len(errors), 1)

    def test_a_failing_mesh_does_not_stop_the_others(self):
        obj = outlined_character()
        while len(obj.data.uv_layers) < 8:   # Blender's limit: DT_OutlineN/W cannot be added
            obj.data.uv_layers.new(name="UV%d" % len(obj.data.uv_layers))
        other = tu.add_sphere(segments=8, rings=4)
        tu.assign(other, obj.data.materials[0])
        done, errors = model_fbx.prepare_outline_data([obj, other])
        self.assertEqual(done, [other.name])
        self.assertEqual(len(errors), 1)
        self.assertIn(obj.name, errors[0])

    def test_modifier_notes_skip_armature_and_outline(self):
        obj = outlined_character()
        obj.modifiers.new("Mirror", 'MIRROR')
        obj.modifiers.new("Armature", 'ARMATURE')
        notes = model_fbx.modifier_notes([obj])
        self.assertEqual(len(notes), 1)
        self.assertIn("Mirror", notes[0])
        self.assertNotIn(gn.MODIFIER_NAME, notes[0])


if __name__ == "__main__":
    tu.run_tests()
