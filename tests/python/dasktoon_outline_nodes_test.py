# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import unittest

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402


def evaluated_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(depsgraph).to_mesh()


def hull_verts(obj, original_count, expected=None):
    mesh = evaluated_mesh(obj)
    verts = [obj.matrix_world @ v.co for v in mesh.vertices[original_count:]]
    if expected is not None and len(verts) != expected:
        raise AssertionError("expected %d hull vertices, got %d" % (expected, len(verts)))
    return verts


def drop_outline_sync_handler():
    """These tests exercise the builders alone; the Task 8 sync handler would remove their modifiers."""
    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in list(handlers):
        if getattr(handler, "__name__", "") == "outline_depsgraph_post":
            handlers.remove(handler)


class OutlineNodesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        drop_outline_sync_handler()
        self.outline_mat = tu.emission_material("Skin.Outline", (0.1, 0.0, 0.0, 1.0))

    def _plane(self, scale=(1.0, 1.0, 1.0), cuts=0):
        obj = tu.add_plane(2.0)
        if cuts:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
            bm.to_mesh(obj.data)
            bm.free()
        obj.scale = scale
        obj.data.materials.append(tu.emission_material("Skin", (1.0, 1.0, 1.0, 1.0)))
        return obj

    def _apply(self, obj, width=0.05, bleed=0.0, wobble=0.0, sun=None, mask="", uv=""):
        slots = [gn.SlotParams(True, width, bleed, wobble, self.outline_mat)]
        gn.ensure_modifier(obj, gn.build_object_group(obj, slots, sun, mask, uv))
        bpy.context.view_layer.update()

    def test_only_enabled_slots_get_hull(self):
        obj = tu.add_sphere(segments=16, rings=8)
        obj.data.materials.append(tu.emission_material("A", (1, 1, 1, 1)))
        obj.data.materials.append(tu.emission_material("B", (1, 1, 1, 1)))
        for poly in obj.data.polygons:
            poly.material_index = 1 if poly.center.z < 0 else 0
        top = sum(1 for p in obj.data.polygons if p.material_index == 0)
        slots = [gn.SlotParams(True, 0.05, 0.0, 0.0, self.outline_mat), gn.SlotParams(False, 0.0, 0.0, 0.0, None)]
        gn.ensure_modifier(obj, gn.build_object_group(obj, slots, None, "", ""))
        bpy.context.view_layer.update()
        mesh = evaluated_mesh(obj)
        self.assertEqual(len(mesh.polygons), len(obj.data.polygons) + top)
        self.assertIn(self.outline_mat.name, [m.name for m in mesh.materials])
        original = [tuple(v.co) for v in obj.data.vertices]
        self.assertEqual([tuple(v.co) for v in mesh.vertices[:len(original)]], original)
        self.assertEqual(len(obj.material_slots), 2)
        self.assertEqual(obj.modifiers[-1].name, gn.MODIFIER_NAME)

    def test_offset_is_world_space_with_non_uniform_scale(self):
        obj = self._plane(scale=(1.0, 1.0, 2.0))
        count = len(obj.data.vertices)
        self._apply(obj, width=0.05)
        for co in hull_verts(obj, count, expected=count):
            self.assertAlmostEqual(co.z, 0.05, delta=1e-4)

    def test_light_bleed_thins_lit_side(self):
        obj = self._plane()
        count = len(obj.data.vertices)
        sun = tu.add_sun(1.0)  # points down: plane normal faces the light
        self._apply(obj, width=0.05, bleed=1.0, sun=sun)
        self.assertAlmostEqual(hull_verts(obj, count, expected=count)[0].z, 0.05 * 0.25, delta=1e-4)
        sun.rotation_euler = (math.pi, 0.0, 0.0)  # light from below: no thinning
        bpy.context.view_layer.update()
        self.assertAlmostEqual(hull_verts(obj, count)[0].z, 0.05, delta=1e-4)

    def test_wobble_varies_width_and_needs_uv(self):
        obj = self._plane(cuts=8)
        count = len(obj.data.vertices)
        self._apply(obj, width=0.05, wobble=1.0, uv=obj.data.uv_layers[0].name)
        zs = [co.z for co in hull_verts(obj, count, expected=count)]
        self.assertGreater(max(zs) - min(zs), 0.002)
        self._apply(obj, width=0.05, wobble=1.0, uv="")  # no UV map: wobble off, still works
        zs = [co.z for co in hull_verts(obj, count)]
        self.assertLess(max(zs) - min(zs), 1e-5)

    def test_mask_vertex_group(self):
        obj = self._plane(cuts=2)
        count = len(obj.data.vertices)
        group = obj.vertex_groups.new(name="Outline_Weight")
        group.add([v.index for v in obj.data.vertices if v.co.x > 0.0], 1.0, 'REPLACE')
        self._apply(obj, width=0.05, mask="Outline_Weight")
        zs = hull_verts(obj, count, expected=count)
        for v, co in zip(obj.data.vertices, zs):
            self.assertAlmostEqual(co.z, 0.05 if v.co.x > 0.0 else 0.0, delta=1e-4)

    def test_split_vertices_do_not_crack(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        obj = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.split_edges(bm, edges=bm.edges[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.materials.append(tu.emission_material("Skin", (1, 1, 1, 1)))
        count = len(obj.data.vertices)
        self.assertEqual(count, 24)
        self._apply(obj, width=0.1)
        by_position = {}
        for v, co in zip(obj.data.vertices, hull_verts(obj, count, expected=count)):
            by_position.setdefault(tuple(round(c, 5) for c in v.co), []).append(co)
        for moved in by_position.values():
            for co in moved[1:]:
                self.assertLess((co - moved[0]).length, 1e-5)


if __name__ == "__main__":
    tu.run_tests()
