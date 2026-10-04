# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export of face shading: rest-pose ellipsoid normals in the FBX, the mesh given back exactly (face spec 6)."""

import os
import sys
import tempfile
import unittest
from unittest import mock

import bpy
import numpy as np
from mathutils import kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import face_shading as export_face  # noqa: E402
from dasktoon_export import model_fbx, targets  # noqa: E402

OPTIONS = dasktoon_export.ExportOptions(include_animation=False, bake_size=16, bake_samples=1)


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def corner_normals(mesh):
    values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get("vector", values)
    return values.reshape(-1, 3).astype(np.float64)


def raw(mesh, name):
    attr = mesh.attributes.get(name)
    if attr is None:
        return None
    key, width, dtype = {'INT16_2D': ("value", 2, np.int32), 'FLOAT_VECTOR': ("vector", 3, np.float32),
                         'BOOLEAN': ("value", 1, bool)}[attr.data_type]
    values = np.empty(len(attr.data) * width, dtype=dtype)
    attr.data.foreach_get(key, values)
    return attr.domain, attr.data_type, values


def face_head():
    tu.reset_scene()
    head, rig = tu.add_test_head()
    mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    tu.assign(head, mat)
    smile = head.shape_key_add(name="Basis")
    smile = head.shape_key_add(name="Smile")
    for point in smile.data[:200]:
        point.co.z += 0.01
    smile.value = 1.0
    fs.setup(head)
    bone = rig.pose.bones["Head"]
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler = (0.3, 0.0, 0.5)
    bpy.context.view_layer.update()
    return head, rig


def rest_normals(head, rig):
    """What the modifier gives at rest with only the Basis shape (face spec 6.2), in object space."""
    only, index = head.show_only_shape_key, head.active_shape_key_index
    head.show_only_shape_key = True
    head.active_shape_key_index = 0
    with fs.rest_pose([rig]):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = head.evaluated_get(depsgraph)
        normals = corner_normals(evaluated.to_mesh())
        evaluated.to_mesh_clear()
    head.show_only_shape_key = only
    head.active_shape_key_index = index
    bpy.context.view_layer.update()
    return normals


def to_world(obj, normals):
    """Object-space normals to world space (inverse transpose of the 3x3, for row vectors)."""
    return normalize(normals @ np.linalg.inv(np.array(obj.matrix_world.to_3x3())))


def degrees(a, b):
    return np.degrees(np.arccos(np.clip((normalize(a) * normalize(b)).sum(axis=1), -1.0, 1.0)))


class FaceShadingExportTest(unittest.TestCase):
    def test_rest_normals_are_written_and_the_state_comes_back(self):
        head, rig = face_head()
        want = rest_normals(head, rig)
        before = [(m.name, m.show_viewport) for m in head.modifiers]
        shape_index = head.active_shape_key_index
        snapshots, names, warnings = export_face.bake_rest_normals(bpy.context, [head, rig])
        self.assertEqual((names, warnings), (["Head"], []))
        self.assertLessEqual(degrees(corner_normals(head.data), want).max(), 0.5)
        self.assertEqual(rig.data.pose_position, 'POSE')
        self.assertAlmostEqual(rig.pose.bones["Head"].rotation_euler.z, 0.5, places=6)
        self.assertFalse(head.show_only_shape_key)
        self.assertEqual(head.active_shape_key_index, shape_index)
        self.assertEqual([(m.name, m.show_viewport) for m in head.modifiers], before)
        export_face.restore_normals(snapshots)
        self.assertFalse(head.data.has_custom_normals)
        self.assertIsNone(head.data.attributes.get("sharp_edge"))

    def test_existing_custom_normals_and_sharp_edges_come_back_exactly(self):
        head, _rig = face_head()
        mesh = head.data
        for edge in mesh.edges[:40]:
            edge.use_edge_sharp = True
        mesh.normals_split_custom_set_from_vertices([(v.normal.x, v.normal.y + 0.3, v.normal.z) for v in mesh.vertices])
        mesh.update()
        custom, sharp = raw(mesh, "custom_normal"), raw(mesh, "sharp_edge")
        snapshots, names, _warnings = export_face.bake_rest_normals(bpy.context, [head])
        self.assertEqual(names, ["Head"])
        export_face.restore_normals(snapshots)
        for name, saved in (("custom_normal", custom), ("sharp_edge", sharp)):
            now = raw(mesh, name)
            self.assertEqual(now[:2], saved[:2], name)
            self.assertTrue(np.array_equal(now[2], saved[2]), name)

    def test_topology_changing_modifier_before_face_shading_is_skipped(self):
        head, _rig = face_head()
        subdivision = head.modifiers.new("Subdivision", 'SUBSURF')
        head.modifiers.move(head.modifiers.find(subdivision.name), head.modifiers.find(fsn.MODIFIER_NAME))
        snapshots, names, warnings = export_face.bake_rest_normals(bpy.context, [head])
        self.assertEqual((snapshots, names), ([], []))
        self.assertEqual(len(warnings), 1)
        self.assertIn("Subdivision", warnings[0])
        self.assertFalse(head.data.has_custom_normals)

    def test_hidden_modifier_is_not_baked(self):
        head, _rig = face_head()
        fsn.get_modifier(head).show_viewport = False
        self.assertEqual(export_face.bake_rest_normals(bpy.context, [head])[:2], ([], []))

    def test_shared_mesh_data_is_baked_once(self):
        head, _rig = face_head()
        twin = head.copy()
        bpy.context.scene.collection.objects.link(twin)
        snapshots, names, _warnings = export_face.bake_rest_normals(bpy.context, [head, twin])
        self.assertEqual((len(snapshots), len(names)), (1, 1))
        export_face.restore_normals(snapshots)
        self.assertFalse(head.data.has_custom_normals)

    def test_export_model_writes_rest_normals_and_the_meta(self):
        head, rig = face_head()
        want_world = to_world(head, rest_normals(head, rig))
        out = tempfile.mkdtemp(prefix="dt_face_export_")
        target = targets.make_target(out, "Hero")
        rep = dasktoon_export.export_model(bpy.context, target, [head, rig], OPTIONS)
        self.assertEqual(rep.face_meshes, ["Head"])
        self.assertFalse(any(fsn.MODIFIER_NAME in note for note in rep.modifier_notes))
        self.assertTrue(any("Bóng mặt" in line for line in rep.lines()))
        self.assertFalse(head.data.has_custom_normals)
        self.assertEqual(rig.data.pose_position, 'POSE')
        with open(os.path.join(target.root, "Hero/Model/Hero.fbx.meta"), encoding="utf-8") as f:
            self.assertIn("    blendShapeNormalImportMode: 2\n", f.read())
        # Re-import: compare each original corner with the imported corner of the same world vertex and face.
        original = [(tuple(head.matrix_world @ head.data.vertices[loop.vertex_index].co),
                     tuple(head.matrix_world @ poly.center), want_world[loop.index])
                    for poly in head.data.polygons for loop in (head.data.loops[i] for i in poly.loop_indices)]
        tu.reset_scene()
        bpy.ops.import_scene.fbx(filepath=os.path.join(target.root, "Hero/Model/Hero.fbx"))
        imported = next(o for o in bpy.data.objects if o.type == 'MESH')
        mesh = imported.data
        normals = to_world(imported, corner_normals(mesh))
        tree = kdtree.KDTree(len(mesh.loops))
        for poly in mesh.polygons:
            centre = imported.matrix_world @ poly.center
            for i in poly.loop_indices:
                tree.insert((imported.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co) * 0.5 + centre * 0.5, i)
        tree.balance()
        worst = 0.0
        for vertex, centre, want in original:
            _co, index, dist = tree.find([(a + b) * 0.5 for a, b in zip(vertex, centre)])
            self.assertLess(dist, 1e-3)
            worst = max(worst, float(degrees(normals[index:index + 1], want[None, :])[0]))
        self.assertLessEqual(worst, 1.0)

    def test_export_without_face_shading_keeps_blend_shape_normals(self):
        tu.reset_scene()
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_face_plain_"), "Plain")
        rep = dasktoon_export.export_model(bpy.context, target, [body], OPTIONS)
        self.assertEqual(rep.face_meshes, [])
        with open(os.path.join(target.root, "Plain/Model/Plain.fbx.meta"), encoding="utf-8") as f:
            self.assertIn("    blendShapeNormalImportMode: 0\n", f.read())

    def test_failed_export_gives_the_mesh_back(self):
        head, rig = face_head()
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_face_fail_"), "Broken")
        with mock.patch.object(model_fbx, "write_fbx", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                dasktoon_export.export_model(bpy.context, target, [head, rig], OPTIONS)
        self.assertFalse(head.data.has_custom_normals)
        self.assertEqual(rig.data.pose_position, 'POSE')


if __name__ == "__main__":
    tu.run_tests()
