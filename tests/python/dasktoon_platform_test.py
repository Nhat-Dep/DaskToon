# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402


def _geometry_group(name):
    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    tree.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    return tree


class PlatformAssumptions(unittest.TestCase):
    def test_set_material_outside_slots_renders(self):
        """Spec 4.3: Set Material may use a material that is not in the object's slots."""
        tu.reset_scene()
        plane = tu.add_plane()
        red = tu.emission_material("Red", (1.0, 0.0, 0.0, 1.0))
        blue = tu.emission_material("Blue", (0.0, 0.0, 1.0, 1.0))
        plane.data.materials.append(red)
        tree = _geometry_group("Spike")
        nodes, links = tree.nodes, tree.links
        group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
        lift = nodes.new('GeometryNodeSetPosition')
        lift.inputs["Offset"].default_value = (0.0, 0.0, 0.5)
        set_material = nodes.new('GeometryNodeSetMaterial')
        set_material.inputs["Material"].default_value = blue
        join = nodes.new('GeometryNodeJoinGeometry')
        links.new(group_in.outputs[0], lift.inputs["Geometry"])
        links.new(lift.outputs[0], set_material.inputs["Geometry"])
        links.new(group_in.outputs[0], join.inputs[0])
        links.new(set_material.outputs[0], join.inputs[0])
        links.new(join.outputs[0], group_out.inputs[0])
        plane.modifiers.new("Spike", 'NODES').node_group = tree
        self.assertEqual(len(plane.material_slots), 1)
        r, _g, b, _a = tu.render_center("set_material_outside_slots")
        self.assertGreater(b, 0.5)
        self.assertLess(r, 0.1)

    def test_real_uv_map_and_shape_keys_survive_fbx(self):
        """Spec 5: real UV maps survive FBX export together with shape keys."""
        tu.reset_scene()
        obj = tu.add_sphere(segments=16, rings=8)
        obj.shape_key_add(name="Basis")
        key = obj.shape_key_add(name="Smile")
        key.data[0].co.z += 0.1
        obj.data.uv_layers.new(name="DT_OutlineN")
        path = os.path.join(tu.OUT_DIR, "uv_shape_keys.fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_mesh_modifiers=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
        imported = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
        self.assertIn("DT_OutlineN", [uv.name for uv in imported.data.uv_layers])
        self.assertEqual([k.name for k in imported.data.shape_keys.key_blocks], ["Basis", "Smile"])


if __name__ == "__main__":
    tu.run_tests()
