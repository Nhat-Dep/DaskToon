# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading set-up: head bone, DT_Face, the proxy fitted to the face, refit and removal (face spec 3, 5)."""

import os
import sys
import tempfile
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402


def weights(obj, name):
    out = np.zeros(len(obj.data.vertices))
    group = obj.vertex_groups.get(name)
    if group is None:
        return out
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                out[v.index] = g.weight
    return out


def rig_with_bones(names):
    rig = bpy.data.objects.new("Bones", bpy.data.armatures.new("Bones"))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for i, name in enumerate(names):
        bone = rig.data.edit_bones.new(name)
        bone.head = (0.0, 0.0, i)
        bone.tail = (0.0, 0.0, i + 0.5)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def expected_fit(head):
    """Face spec 5.4 on the skin of the test head, world space, at rest."""
    skin = head["dt_skin_vertices"]
    world = np.array([tuple(head.matrix_world @ v.co) for v in head.data.vertices[:skin]])
    low, high = world.min(axis=0), world.max(axis=0)
    rx, rz = (high[0] - low[0]) / 2.0, (high[2] - low[2]) / 2.0
    ry = max((high[1] - low[1]) / 2.0, 0.85 * rx)
    centre = Vector(((low[0] + high[0]) / 2.0, np.percentile(world[:, 1], 5.0) + ry, (low[2] + high[2]) / 2.0))
    return centre, Vector((rx, ry, rz))


def face_proxies():
    return [o for o in bpy.data.objects if o.get(fs.PROXY_MARK)]


class FaceShadingSetupTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def assert_at_rest(self, proxy, head, rig):
        if rig is not None:
            rig.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        centre, radii = expected_fit(head)
        location, _rotation, scale = proxy.matrix_world.decompose()
        self.assertLess((location - centre).length, 1e-4)
        self.assertLess((scale - radii).length, 1e-4)
        if rig is not None:
            rig.data.pose_position = 'POSE'
            bpy.context.view_layer.update()

    def test_head_bone_names(self):
        self.assertEqual(fs.find_head_bone(rig_with_bones(["Hips", "Spine", "J_Bip_C_Head"])), "J_Bip_C_Head")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["mixamorig:HeadTop_End", "mixamorig:Head"])),
                         "mixamorig:Head")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["首", "頭"])), "頭")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["HeadTop_End", "Head_tip", "MyHeadBone"])), "MyHeadBone")
        self.assertIsNone(fs.find_head_bone(rig_with_bones(["Spine", "Neck"])))

    def test_dt_face_holds_the_face_island_not_the_hair(self):
        head, _rig = tu.add_test_head()
        fs.setup(head)
        skin = head["dt_skin_vertices"]
        face = weights(head, fsn.MASK_NAME)
        self.assertTrue((face[:skin] == 1.0).all())
        self.assertTrue((face[skin:] == 0.0).all())

    def test_proxy_fits_the_skin_and_hangs_from_the_head_bone(self):
        head, rig = tu.add_test_head()
        proxy = fs.setup(head)
        self.assertEqual((proxy.parent, proxy.parent_type, proxy.parent_bone), (rig, 'BONE', "Head"))
        self.assertEqual(proxy.name, "DT_FaceProxy::Rig:Head")
        self.assertEqual((proxy.empty_display_type, proxy.empty_display_size, proxy.hide_render), ('SPHERE', 1.0, True))
        self.assertEqual(proxy.users_collection[0], head.users_collection[0])
        self.assertEqual(fs.proxy_of(head), proxy)
        self.assertEqual(head[fs.PROXY_PROP], proxy)
        self.assertEqual(fsn.input_socket(fsn.get_modifier(head), "Proxy").value, proxy)
        self.assert_at_rest(proxy, head, rig)
        rest = proxy.matrix_world.copy()
        bone = rig.pose.bones["Head"]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0.0, 0.0, 0.6)
        bpy.context.view_layer.update()
        self.assertGreater((proxy.matrix_world.translation - rest.translation).length, 1e-3)

    def test_setup_while_posed_fits_the_rest_pose(self):
        head, rig = tu.add_test_head()
        bone = rig.pose.bones["Head"]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0.4, 0.0, 0.7)
        bpy.context.view_layer.update()
        proxy = fs.setup(head)
        self.assertEqual(rig.data.pose_position, 'POSE')
        self.assert_at_rest(proxy, head, rig)

    def test_fit_with_a_transformed_rig(self):
        head, rig = tu.add_test_head()
        rig.location = (1.0, 2.0, 0.5)
        rig.rotation_euler = (0.0, 0.0, 0.3)
        rig.scale = (1.2, 1.2, 1.2)
        bpy.context.view_layer.update()
        proxy = fs.setup(head)
        self.assert_at_rest(proxy, head, rig)

    def test_second_mesh_reuses_the_proxy_without_refitting(self):
        head, _rig = tu.add_test_head()
        brows = head.copy()
        brows.data = head.data.copy()
        brows.name = "Brows"
        bpy.context.scene.collection.objects.link(brows)
        proxy = fs.setup(head)
        proxy.location.x += 0.01
        moved = proxy.location.copy()
        self.assertEqual(fs.setup(brows), proxy)
        self.assertEqual(proxy.location, moved)
        self.assertEqual(len(face_proxies()), 1)
        self.assertEqual(set(o.name for o in fs.proxy_users(proxy)), {"Head", "Brows"})

    def test_selected_vertices_without_an_armature(self):
        head, _rig = tu.add_test_head(with_armature=False)
        skin = head["dt_skin_vertices"]
        proxy = fs.setup(head, selected=range(skin))
        self.assertEqual((proxy.parent, proxy.parent_type), (head, 'OBJECT'))
        self.assertEqual(proxy.name, "DT_FaceProxy::Head")
        self.assert_at_rest(proxy, head, None)

    def test_head_vertices_fallbacks(self):
        head, _rig = tu.add_test_head()
        self.assertEqual(len(fs.head_vertices(head, "Head")), len(head.data.vertices))
        self.assertEqual(list(fs.head_vertices(head, "Missing", selected=[3, 1, 2])), [1, 2, 3])
        with self.assertRaises(fs.FaceShadingError):
            fs.head_vertices(head, None)

    def test_nothing_to_work_with_raises(self):
        head, _rig = tu.add_test_head(with_armature=False)
        with self.assertRaises(fs.FaceShadingError):
            fs.setup(head)
        self.assertIsNone(fsn.get_modifier(head))
        self.assertEqual(face_proxies(), [])

    def test_refit_moves_the_proxy_back_and_keeps_the_sliders(self):
        head, rig = tu.add_test_head()
        proxy = fs.setup(head)
        modifier = fsn.get_modifier(head)
        fsn.set_inputs(modifier, {"Coverage": 0.5})
        proxy.location.z += 0.05
        proxy.scale = (0.3, 0.3, 0.3)
        self.assertEqual(fs.refit(head), proxy)
        self.assertAlmostEqual(fsn.input_socket(modifier, "Coverage").value, 0.5, places=6)
        self.assert_at_rest(proxy, head, rig)

    def test_refit_rebuilds_a_deleted_proxy(self):
        head, rig = tu.add_test_head()
        bpy.data.objects.remove(fs.setup(head))
        proxy = fs.refit(head)
        self.assertEqual(fs.proxy_of(head), proxy)
        self.assert_at_rest(proxy, head, rig)

    def test_remove_cleans_up_and_keeps_a_shared_proxy(self):
        head, _rig = tu.add_test_head()
        brows = head.copy()
        brows.data = head.data.copy()
        bpy.context.scene.collection.objects.link(brows)
        proxy = fs.setup(head)
        fs.setup(brows)
        name = proxy.name
        fs.remove(head)
        self.assertIsNone(head.modifiers.get(fsn.MODIFIER_NAME))
        self.assertIsNone(head.vertex_groups.get(fsn.MASK_NAME))
        self.assertNotIn(fs.PROXY_PROP, head)
        self.assertIn(name, bpy.data.objects)
        fs.remove(brows)
        self.assertNotIn(name, bpy.data.objects)

    def test_linked_mesh_is_refused(self):
        head, _rig = tu.add_test_head()
        path = os.path.join(tempfile.mkdtemp(prefix="dt_face_lib_"), "lib.blend")
        bpy.data.libraries.write(path, {head})
        tu.reset_scene()
        with bpy.data.libraries.load(path, link=True) as (_src, dst):
            dst.objects = ["Head"]
        linked = dst.objects[0]
        bpy.context.scene.collection.objects.link(linked)
        with self.assertRaises(fs.FaceShadingError):
            fs.setup(linked)

    def test_panel_target_follows_the_proxy(self):
        head, _rig = tu.add_test_head()
        proxy = fs.setup(head)
        self.assertEqual(fs.panel_target(bpy.context), head)
        bpy.context.view_layer.objects.active = proxy
        self.assertEqual(fs.panel_target(bpy.context), head)
        bpy.context.view_layer.objects.active = None
        self.assertIsNone(fs.panel_target(bpy.context))


if __name__ == "__main__":
    tu.run_tests()
