# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import unittest

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gd  # noqa: E402


def decoded_world_normals(mesh):
    """Decode DT_OutlineN back to object space using the same MikkTSpace frame."""
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers["DT_OutlineN"].uv.foreach_get("vector", uv)
    n_ts = gd.oct_decode(uv.reshape(-1, 2).astype(np.float64))
    mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
    t = np.array([l.tangent for l in mesh.loops])
    sign = np.array([l.bitangent_sign for l in mesh.loops])
    n = np.array([cn.vector for cn in mesh.corner_normals])
    b = sign[:, None] * np.cross(n, t)
    mesh.free_tangents()
    return n_ts[:, :1] * t + n_ts[:, 1:2] * b + n_ts[:, 2:3] * n


class GameDataTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def test_oct_round_trip(self):
        rng = np.random.default_rng(1)
        v = rng.normal(size=(10000, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        self.assertLess(np.abs(gd.oct_decode(gd.oct_encode(v)) - v).max(), 1e-6)

    def test_sphere_decodes_to_vertex_normal(self):
        """On a mesh without split vertices the smoothed normal is Blender's (angle-weighted) vertex normal."""
        obj = tu.add_sphere(segments=24, rings=12)
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        mesh = obj.data
        decoded = decoded_world_normals(mesh)
        corner_vert = np.array([l.vertex_index for l in mesh.loops])
        vertex_normal = np.array([mesh.vertices[i].normal for i in corner_vert])
        self.assertLess(np.abs(decoded - vertex_normal).max(), 1e-3)

    def test_split_cube_shares_smoothed_normal(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        obj = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.split_edges(bm, edges=bm.edges[:])
        bm.to_mesh(obj.data)
        bm.free()
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        decoded = decoded_world_normals(obj.data)
        by_pos = {}
        for loop, normal in zip(obj.data.loops, decoded):
            key = tuple(round(c, 4) for c in obj.data.vertices[loop.vertex_index].co)
            by_pos.setdefault(key, []).append(normal)
        for normals in by_pos.values():
            self.assertLess(np.abs(np.array(normals) - normals[0]).max(), 1e-3)

    def test_mask_written_to_dt_outline_w(self):
        obj = tu.add_plane()
        group = obj.vertex_groups.new(name="Outline_Weight")
        group.add([0, 1], 0.25, 'REPLACE')
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        layer = obj.data.uv_layers["DT_OutlineW"]
        for loop, uv in zip(obj.data.loops, layer.uv):
            self.assertAlmostEqual(uv.vector[0], 0.25 if loop.vertex_index in (0, 1) else 0.0, places=5)

    def test_active_uv_preserved_and_signature(self):
        obj = tu.add_plane()
        mesh = obj.data
        first = mesh.uv_layers[0].name
        ok, _msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok)
        self.assertEqual(mesh.uv_layers.active.name, first)
        self.assertTrue([uv for uv in mesh.uv_layers if uv.active_render][0].name == first)
        self.assertFalse(gd.is_outline_data_stale(mesh))

    def test_errors_without_uv_or_with_ngon(self):
        bpy.ops.mesh.primitive_circle_add(vertices=8, fill_type='NGON')
        ngon = bpy.context.active_object
        ok, _msg = gd.write_outline_uvs(ngon)
        self.assertFalse(ok)
        self.assertNotIn("DT_OutlineN", [uv.name for uv in ngon.data.uv_layers])
        obj = tu.add_plane()
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        ok, _msg = gd.write_outline_uvs(obj)
        self.assertFalse(ok)


if __name__ == "__main__":
    tu.run_tests()
