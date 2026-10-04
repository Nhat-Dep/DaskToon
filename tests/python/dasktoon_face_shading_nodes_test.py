# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading Geometry Nodes against a numpy reference of the formula in face spec 4."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
from bl_ui import dasktoon_outline_nodes as outline_nodes  # noqa: E402


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def reference(position, n0, mask, matrix, coverage, falloff, nose_keep, chin_keep):
    """Face spec 4 per corner, in object space: position and n0 are (n, 3), mask (n,), matrix the proxy relative to the
    object. Returns a dict with the result N and the intermediate terms."""
    m = np.array(matrix)
    inv = np.linalg.inv(m)
    q = position @ inv[:3, :3].T + inv[:3, 3]
    r = np.linalg.norm(q, axis=1)
    d = q / r[:, None]
    n_e = normalize(d @ inv[:3, :3])  # (L^-1)^T d, written for row vectors
    down = normalize(m[:3, :3] @ np.array([0.0, 0.0, -1.0]))
    region = mask * (1.0 - smoothstep(1.0, 1.0 + falloff, r))
    nose = smoothstep(0.80, 0.95, -d[:, 1]) * smoothstep(0.02, 0.08, r - 1.0)
    chin = smoothstep(0.25, 0.55, -d[:, 2]) * smoothstep(0.35, 0.70, n0 @ down)
    w = coverage * region * (1.0 - nose_keep * nose) * (1.0 - chin_keep * chin)
    return {"N": normalize(n0 + (n_e - n0) * w[:, None]), "n_e": n_e, "w": w, "r": r, "nose": nose, "chin": chin}


def corner_normals(obj, evaluated=True):
    holder = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else None
    mesh = holder.to_mesh() if evaluated else obj.data
    values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get("vector", values)
    if holder is not None:
        holder.to_mesh_clear()
    return values.reshape(-1, 3).astype(np.float64)


def degrees(a, b):
    return np.degrees(np.arccos(np.clip((normalize(a) * normalize(b)).sum(axis=1), -1.0, 1.0)))


class FaceShadingNodesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj, _rig = tu.add_test_head(with_armature=False)
        self.obj.location = (0.3, -0.2, 0.1)  # the proxy matrix is relative to the object
        self.obj.rotation_euler = (0.0, 0.0, 0.4)
        bpy.context.view_layer.update()
        self.obj.vertex_groups.new(name=fsn.MASK_NAME).add(list(range(len(self.obj.data.vertices))), 1.0, 'REPLACE')
        self.proxy = bpy.data.objects.new("Proxy", None)
        bpy.context.scene.collection.objects.link(self.proxy)
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.095, 0.1, 0.1)))
        self.mod = fsn.ensure_modifier(self.obj)
        fsn.set_inputs(self.mod, {"Proxy": self.proxy})

    def place_proxy(self, centre, radii):
        self.proxy.matrix_world = self.obj.matrix_world @ Matrix.LocRotScale(centre, Euler((0.1, 0.0, 0.2)), radii)
        bpy.context.view_layer.update()

    def run_case(self, coverage=1.0, falloff=0.3, nose_keep=0.6, chin_keep=0.8):
        """(N0, N from the modifier, reference terms); asserts that the modifier matches the reference within 1 degree."""
        fsn.set_inputs(self.mod, {"Coverage": coverage, "Falloff": falloff, "Nose Keep": nose_keep,
                                  "Chin Keep": chin_keep})
        self.mod.show_viewport = False
        n0 = corner_normals(self.obj)
        self.mod.show_viewport = True
        got = corner_normals(self.obj)
        mesh = self.obj.data
        corner_vert = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", corner_vert)
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        weights = np.zeros(len(mesh.vertices))
        group = self.obj.vertex_groups.get(fsn.MASK_NAME)
        for v in mesh.vertices:
            for g in v.groups:
                if group is not None and g.group == group.index:
                    weights[v.index] = g.weight
        relative = self.obj.matrix_world.inverted() @ self.proxy.matrix_world
        ref = reference(co.reshape(-1, 3).astype(np.float64)[corner_vert], n0, weights[corner_vert], relative,
                        coverage, falloff, nose_keep, chin_keep)
        self.assertLessEqual(degrees(got, ref["N"]).max(), 1.0)
        return n0, got, ref

    def test_matches_the_reference_with_the_defaults(self):
        n0, got, _ref = self.run_case()
        self.assertGreater(degrees(got, n0).max(), 5.0)

    def test_full_coverage_without_keeps_is_the_ellipsoid_normal(self):
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.12, 0.13, 0.12)))  # the skin lies inside: region = 1
        _n0, got, ref = self.run_case(nose_keep=0.0, chin_keep=0.0)
        inside = ref["r"] <= 1.0
        self.assertGreater(inside.sum(), 100)
        self.assertLessEqual(degrees(got[inside], ref["n_e"][inside]).max(), 1.0)

    def test_coverage_zero_changes_nothing(self):
        n0, got, _ref = self.run_case(coverage=0.0)
        self.assertLessEqual(degrees(got, n0).max(), 0.1)

    def test_outside_the_falloff_is_unchanged(self):
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.05, 0.05, 0.05)))
        n0, got, ref = self.run_case(falloff=0.3)
        outside = ref["r"] > 1.3
        self.assertGreater(outside.sum(), 100)
        self.assertLessEqual(degrees(got[outside], n0[outside]).max(), 0.1)

    def test_nose_keep_keeps_the_real_nose_normal(self):
        n0, kept, ref = self.run_case(nose_keep=1.0, chin_keep=0.0)
        tip = ref["nose"] >= 0.999
        self.assertGreaterEqual(tip.sum(), 1)
        self.assertLessEqual(degrees(kept[tip], n0[tip]).max(), 0.1)
        bump = ref["nose"] >= 0.5
        _n0, free, _ref = self.run_case(nose_keep=0.0, chin_keep=0.0)
        self.assertGreater(degrees(free[bump], n0[bump]).mean(), degrees(kept[bump], n0[bump]).mean() + 1.0)

    def test_chin_keep_keeps_the_underside(self):
        n0, got, ref = self.run_case(nose_keep=0.0, chin_keep=1.0)
        chin = ref["chin"] >= 0.999
        self.assertGreaterEqual(chin.sum(), 4)
        self.assertLessEqual(degrees(got[chin], n0[chin]).max(), 0.1)

    def test_moving_the_proxy_changes_the_normals(self):
        _n0, before, _ref = self.run_case()
        self.place_proxy(Vector((0.03, 0.0, 1.5)), Vector((0.095, 0.1, 0.1)))
        _n0, after, _ref = self.run_case()
        self.assertGreater(degrees(before, after).max(), 1.0)

    def test_missing_mask_changes_nothing(self):
        self.obj.vertex_groups.remove(self.obj.vertex_groups[fsn.MASK_NAME])
        n0, got, _ref = self.run_case()
        self.assertLessEqual(degrees(got, n0).max(), 0.1)

    def test_existing_custom_normals_are_the_base(self):
        mesh = self.obj.data
        geometric = corner_normals(self.obj, evaluated=False)
        mesh.normals_split_custom_set_from_vertices([(v.normal + Vector((0.4, 0.0, 0.0))).normalized()
                                                     for v in mesh.vertices])
        mesh.update()
        custom = corner_normals(self.obj, evaluated=False)
        self.assertGreater(degrees(custom, geometric).max(), 5.0)
        n0, _got, _ref = self.run_case(coverage=0.5)
        self.assertLessEqual(degrees(n0, custom).max(), 0.1)  # N0 is the custom normal, not the geometric one

    def test_group_is_rebuilt_when_its_version_differs(self):
        tree = fsn.ensure_group()
        tree["dasktoon_version"] = 0
        rebuilt = fsn.ensure_group()
        self.assertEqual(rebuilt, tree)
        self.assertEqual(rebuilt["dasktoon_version"], fsn.VERSION)
        self.assertEqual([s.name for s in rebuilt.interface.items_tree if s.in_out == 'INPUT'],
                         ["Geometry", "Proxy", "Coverage", "Falloff", "Nose Keep", "Chin Keep", "Mask Name"])

    def test_modifier_goes_right_before_the_outline(self):
        obj = tu.add_sphere(segments=8, rings=4)
        obj.modifiers.new("Armature", 'ARMATURE')
        obj.modifiers.new(outline_nodes.MODIFIER_NAME, 'NODES')
        fsn.ensure_modifier(obj)
        self.assertEqual([m.name for m in obj.modifiers], ["Armature", fsn.MODIFIER_NAME, outline_nodes.MODIFIER_NAME])
        plain = tu.add_sphere(segments=8, rings=4)
        plain.modifiers.new("Armature", 'ARMATURE')
        fsn.ensure_modifier(plain)
        self.assertEqual([m.name for m in plain.modifiers], ["Armature", fsn.MODIFIER_NAME])
        self.assertEqual(fsn.ensure_modifier(plain), plain.modifiers[fsn.MODIFIER_NAME])
        self.assertEqual(len(plain.modifiers), 2)

    def test_get_modifier_ignores_a_modifier_without_the_group(self):
        obj = tu.add_sphere(segments=8, rings=4)
        obj.modifiers.new(fsn.MODIFIER_NAME, 'NODES')
        self.assertIsNone(fsn.get_modifier(obj))
        modifier = fsn.ensure_modifier(obj)
        self.assertEqual(fsn.get_modifier(obj), modifier)
        fsn.remove_modifier(obj)
        self.assertEqual(len(obj.modifiers), 0)


if __name__ == "__main__":
    tu.run_tests()
