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
from bl_ui import dasktoon_outline as outline  # noqa: E402
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


def add_island(head, location, size):
    """Join a box (world location, full size) to the head mesh as a separate island weighted 1 to bone Head."""
    import bmesh
    from mathutils import Matrix
    count = len(head.data.vertices)
    piece = bpy.data.meshes.new("Piece")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.LocRotScale(Vector(location), None, Vector(size)))
    bm.to_mesh(piece)
    bm.free()
    joined = bmesh.new()
    joined.from_mesh(head.data)
    joined.from_mesh(piece)
    joined.to_mesh(head.data)
    joined.free()
    bpy.data.meshes.remove(piece)
    head.vertex_groups["Head"].add(list(range(count, len(head.data.vertices))), 1.0, 'REPLACE')
    return list(range(count, len(head.data.vertices)))


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

    def test_a_lock_of_hair_in_front_of_the_face_is_passed_over(self):
        head, _rig = tu.add_test_head()
        lock = add_island(head, (0.0, -0.135, 1.52), (0.01, 0.01, 0.06))  # in front of the nose, narrow
        fs.setup(head)
        skin = head["dt_skin_vertices"]
        face = weights(head, fsn.MASK_NAME)
        self.assertTrue((face[:skin] == 1.0).all())
        self.assertTrue((face[skin:] == 0.0).all(), "hair or the lock of hair got into DT_Face")
        self.assertEqual(face[lock].sum(), 0.0)

    def test_expression_shape_keys_pick_the_face_island(self):
        head, _rig = tu.add_test_head()
        add_island(head, (0.0, -0.14, 1.52), (0.08, 0.01, 0.02))  # a visor in front of the face, wider than 1/4 head
        skin = head["dt_skin_vertices"]
        head.shape_key_add(name="Basis")
        smile = head.shape_key_add(name="Smile")
        for i, point in enumerate(smile.data[:skin]):
            if point.co.y < -0.05 and point.co.z < 1.47:
                point.co.z += 0.005
        fs.setup(head)
        face = weights(head, fsn.MASK_NAME)
        self.assertTrue((face[:skin] == 1.0).all())
        self.assertTrue((face[skin:] == 0.0).all(), "the visor or the hair got into DT_Face")

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

    def test_selection_without_a_middle_is_reported(self):
        head, _rig = tu.add_test_head(with_armature=False)
        sides = [v.index for v in head.data.vertices if abs(v.co.x) > 0.08]  # two clusters, nothing in the middle
        with self.assertRaises(fs.FaceShadingError):
            fs.setup(head, selected=sides)
        self.assertIsNone(fsn.get_modifier(head))

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


class Recorder:
    """Stands in for UILayout: records the labels, operators and properties a panel draws."""

    def __init__(self, log=None):
        self.log = [] if log is None else log
        self.scale_y = 1.0

    def column(self, **_kw):
        return Recorder(self.log)

    def row(self, **_kw):
        return Recorder(self.log)

    def box(self):
        return Recorder(self.log)

    def separator(self, **_kw):
        pass

    def label(self, text="", **_kw):
        self.log.append(("label", text))

    def operator(self, idname, text=None, **_kw):
        self.log.append(("operator", idname))

    def prop(self, _data, _prop, text=None, **_kw):
        self.log.append(("prop", text))


def draw(panel):
    recorder = Recorder()

    class Fake:
        layout = recorder

    panel.draw(Fake(), bpy.context)
    return recorder.log


class FaceShadingUITest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def test_classes_are_registered_and_the_old_panel_is_gone(self):
        for name in ("DASKTOON_OT_face_shading_setup", "DASKTOON_OT_face_shading_refit",
                     "DASKTOON_OT_face_shading_remove", "DASKTOON_OT_face_shading_select_proxy",
                     "DATA_PT_dasktoon_face_shading"):
            self.assertTrue(hasattr(bpy.types, name), name)
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_face_normals"))
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_face_shading"))
        panel = bpy.types.DATA_PT_dasktoon_face_shading
        self.assertEqual((panel.bl_space_type, panel.bl_region_type, panel.bl_context), ('PROPERTIES', 'WINDOW', "data"))

    def test_panel_shows_only_for_meshes_and_face_proxies(self):
        head, _rig = tu.add_test_head()
        proxy = fs.setup(head)
        panel = bpy.types.DATA_PT_dasktoon_face_shading
        self.assertTrue(panel.poll(bpy.context))
        bpy.context.view_layer.objects.active = proxy
        self.assertTrue(panel.poll(bpy.context))
        other = bpy.data.objects.new("Plain", None)
        bpy.context.scene.collection.objects.link(other)
        bpy.context.view_layer.objects.active = other
        self.assertFalse(panel.poll(bpy.context))

    def test_setup_operator_on_the_active_mesh(self):
        head, _rig = tu.add_test_head()
        self.assertEqual(bpy.ops.dasktoon.face_shading_setup(), {'FINISHED'})
        self.assertIsNotNone(fsn.get_modifier(head))

    def test_setup_operator_uses_the_edit_mode_selection(self):
        head, _rig = tu.add_test_head(with_armature=False)
        skin = head["dt_skin_vertices"]
        for v in head.data.vertices:
            v.select = v.index < skin
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.face_shading_setup(), {'FINISHED'})
        self.assertEqual(head.mode, 'EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.assertEqual(fs.proxy_of(head).parent, head)

    def test_setup_operator_reports_what_is_missing(self):
        tu.add_test_head(with_armature=False)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.face_shading_setup()

    def test_select_proxy_then_refit_and_remove_from_the_proxy(self):
        head, _rig = tu.add_test_head()
        bpy.ops.dasktoon.face_shading_setup()
        proxy = fs.proxy_of(head)
        self.assertEqual(bpy.ops.dasktoon.face_shading_select_proxy(), {'FINISHED'})
        self.assertEqual(bpy.context.view_layer.objects.active, proxy)
        self.assertTrue(proxy.select_get())
        self.assertFalse(head.select_get())
        self.assertEqual(bpy.ops.dasktoon.face_shading_refit(), {'FINISHED'})
        self.assertEqual(bpy.ops.dasktoon.face_shading_remove(), {'FINISHED'})
        self.assertIsNone(fsn.get_modifier(head))

    def test_panel_offers_setup_then_the_sliders(self):
        head, _rig = tu.add_test_head()
        self.assertIn(("operator", "dasktoon.face_shading_setup"), draw(bpy.types.DATA_PT_dasktoon_face_shading))
        fs.setup(head)
        log = draw(bpy.types.DATA_PT_dasktoon_face_shading)
        self.assertEqual([text for kind, text in log if kind == "prop"],
                         ["Coverage", "Falloff", "Keep Nose Shadow", "Keep Chin Shadow"])
        for idname in ("dasktoon.face_shading_select_proxy", "dasktoon.face_shading_refit",
                       "dasktoon.face_shading_remove"):
            self.assertIn(("operator", idname), log)
        self.assertNotIn(("operator", "mesh.customdata_custom_splitnormals_clear"), log)
        bpy.context.view_layer.objects.active = fs.proxy_of(head)
        self.assertIn(("label", "Proxy of Head"), draw(bpy.types.DATA_PT_dasktoon_face_shading))

    def test_panel_suggests_clearing_old_custom_normals(self):
        head, _rig = tu.add_test_head()
        head.data.normals_split_custom_set_from_vertices([v.normal for v in head.data.vertices])
        self.assertIn(("operator", "mesh.customdata_custom_splitnormals_clear"),
                      draw(bpy.types.DATA_PT_dasktoon_face_shading))


class OutlineCompatibilityTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.head, self.rig = tu.add_test_head()
        self.mat, self.node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        self.node.use_outline = True
        tu.assign(self.head, self.mat)
        outline.sync_all(bpy.context.scene)

    def hull(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = self.head.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        count = len(self.head.data.vertices)
        points = [tuple(v.co) for v in mesh.vertices[count:]]
        evaluated.to_mesh_clear()
        return np.array(points)

    def test_face_shading_stays_right_before_the_outline(self):
        fs.setup(self.head)
        names = ["Armature", fsn.MODIFIER_NAME, "DaskToon Outline"]
        self.assertEqual([m.name for m in self.head.modifiers], names)
        self.node.inputs["Outline Width"].default_value = 0.02
        outline.sync_all(bpy.context.scene)
        self.assertEqual([m.name for m in self.head.modifiers], names)

    def test_outline_hull_does_not_follow_the_face_normals(self):
        fs.setup(self.head)
        modifier = fsn.get_modifier(self.head)
        with_face = self.hull()
        modifier.show_viewport = False
        without_face = self.hull()
        self.assertEqual(with_face.shape, without_face.shape)
        self.assertLess(np.abs(with_face - without_face).max(), 1e-5)


if __name__ == "__main__":
    tu.run_tests()
