# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime unwrap (docs/superpowers/specs/2026-10-20-dasktoon-anime-unwrap-design.md) on the regions chibi (rigged, its
Body, Shirt and Boots): every face in the square, no island over another except the right limbs lying on the left ones,
the face one island, the head cut at the back, the face with more pixels than the torso, a tight packing."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_regions_test as rt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import regions  # noqa: E402
from dasktoon_uv import seams, transfer, unwrap  # noqa: E402

GRID = 256


def uvs(obj):
    data = obj.data.uv_layers.active.data
    out = np.empty(len(data) * 2, dtype=np.float32)
    data.foreach_get("uv", out)
    return out.reshape(-1, 2)


def triangles(obj, faces=None):
    """[(uv tri, 3D tri)] of the faces (all when None), fanned from their first corner."""
    mesh = obj.data
    uv = uvs(obj)
    world = np.array([obj.matrix_world @ v.co for v in mesh.vertices])
    out = []
    for poly in mesh.polygons if faces is None else (mesh.polygons[i] for i in faces):
        loops = list(poly.loop_indices)
        for k in range(1, len(loops) - 1):
            corners = (loops[0], loops[k], loops[k + 1])
            out.append((uv[list(corners)], world[[mesh.loops[c].vertex_index for c in corners]]))
    return out


def area2(points):
    a, b, c = points
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2


def area3(points):
    a, b, c = points
    return float(np.linalg.norm(np.cross(b - a, c - a))) / 2


def coverage(tris):
    """How many triangles cover each cell of a GRID × GRID raster of the square."""
    counts = np.zeros((GRID, GRID), dtype=np.int32)
    ys, xs = np.mgrid[0:GRID, 0:GRID]
    centres = np.stack([(xs + 0.5) / GRID, (ys + 0.5) / GRID], axis=-1)
    for (a, b, c), _world in tris:
        low = np.floor(np.minimum(np.minimum(a, b), c) * GRID).astype(int).clip(0, GRID - 1)
        high = np.ceil(np.maximum(np.maximum(a, b), c) * GRID).astype(int).clip(0, GRID)
        box = centres[low[1]:high[1], low[0]:high[0]]
        d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(d) < 1e-12:
            continue
        p = box - a
        u = ((c[1] - a[1]) * p[..., 0] - (c[0] - a[0]) * p[..., 1]) / d
        v = (-(b[1] - a[1]) * p[..., 0] + (b[0] - a[0]) * p[..., 1]) / d
        counts[low[1]:high[1], low[0]:high[0]] += ((u >= 0) & (v >= 0) & (u + v <= 1)).astype(np.int32)
    return counts


class UnwrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig, objs = rt.rigged()
        cls.meshes = [objs["Body"], objs["Shirt"], objs["Boots"]]
        cls.result = unwrap.unwrap(bpy.context, cls.meshes, cls.rig)

    def test_every_face_is_in_the_square(self):
        for obj in self.meshes:
            uv = uvs(obj)
            self.assertTrue((uv >= -1e-4).all() and (uv <= 1 + 1e-4).all(), obj.name)

    def test_islands_do_not_overlap_but_the_mirrored_limbs(self):
        tris = []
        for obj in self.meshes:
            mirrored = {face for (o, face) in self.result.mirrored if o == obj}
            tris += triangles(obj, [i for i in range(len(obj.data.polygons)) if i not in mirrored])
        counts = coverage(tris)
        self.assertLess((counts > 1).sum() / max((counts > 0).sum(), 1), 0.01)

    def test_the_right_limbs_lie_on_the_left_ones(self):
        self.assertGreater(len(self.result.mirrored), 50)
        for (obj, face), (other_obj, other) in list(self.result.mirrored.items())[:400]:
            mine = sorted(map(tuple, np.round(uvs(obj)[list(obj.data.polygons[face].loop_indices)], 5)))
            theirs = sorted(map(tuple, np.round(uvs(other_obj)[list(other_obj.data.polygons[other].loop_indices)], 5)))
            self.assertEqual(mine, theirs)

    def test_the_head_is_cut_at_the_back(self):
        body = self.meshes[0]
        labels = self.result.labels[body]
        head = regions.REGIONS.index('HEAD')
        mesh = body.data
        head_faces = [p for p in mesh.polygons if labels[p.index] == head]
        head_verts = {v for p in head_faces for v in p.vertices}
        middle_y = np.mean([mesh.vertices[v].co.y for v in head_verts])
        cut = [e for e in mesh.edges if e.use_seam and set(e.vertices) <= head_verts]
        inside =[e for e in cut if sum(1 for p in head_faces if set(e.vertices) <= set(p.vertices)) == 2]
        self.assertTrue(inside, "the head has no cut of its own")
        self.assertGreater(np.mean([mesh.vertices[v].co.y for e in inside for v in e.vertices]), middle_y)

    def test_the_face_gets_more_pixels_than_the_torso(self):
        body = self.meshes[0]
        labels = self.result.labels[body]

        def density(region):
            faces = [i for i, label in enumerate(labels) if label == regions.REGIONS.index(region)]
            tris = triangles(body, faces)
            return (sum(area2(t[0]) for t in tris) / sum(area3(t[1]) for t in tris)) ** 0.5

        self.assertGreater(density('HEAD'), 1.3 * density('TORSO'))

    def test_the_packing_is_tight(self):
        tris = []
        for obj in self.meshes:
            tris += triangles(obj)
        self.assertGreater((coverage(tris) > 0).mean(), 0.45)


class LabelTest(unittest.TestCase):
    def test_without_a_rig_the_loose_parts_are_the_labels(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.join()
        obj = bpy.context.active_object
        labels = seams.face_labels(bpy.context, obj, None)
        self.assertEqual(len(set(labels.tolist())), 2)
        unwrap.unwrap(bpy.context, [obj], None)
        counts = coverage(triangles(obj))
        self.assertEqual((counts > 1).sum(), 0)  # two closed cubes, cut open, side by side


class OperatorTest(unittest.TestCase):
    def test_the_operator_keeps_the_old_map(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_uv_sphere_add()
        obj = bpy.context.active_object
        self.assertEqual(bpy.ops.dasktoon.uv_unwrap_anime(), {'FINISHED'})
        self.assertEqual([layer.name for layer in obj.data.uv_layers], ["UVMap" + unwrap.OLD, "UVMap"])
        self.assertTrue(obj.data.uv_layers["UVMap"].active_render)
        self.assertEqual(obj.mode, 'OBJECT')

    def test_from_edit_mode_where_the_uv_menu_is(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_uv_sphere_add()
        obj = bpy.context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.uv_unwrap_anime(), {'FINISHED'})
        self.assertEqual(obj.mode, 'EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.assertEqual(len(obj.data.uv_layers), 2)


class TransferTest(unittest.TestCase):
    def test_the_picture_keeps_its_colours_on_the_new_map(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
        obj = bpy.context.active_object
        mat = bpy.data.materials.new("Skin")
        obj.data.materials.append(mat)
        size = 128
        image = bpy.data.images.new("Skin Color", size, size, alpha=True)
        ys, xs = np.mgrid[0:size, 0:size]
        px = np.stack([xs / size, ys / size, np.full(xs.shape, 0.5), np.ones(xs.shape)], axis=-1).astype(np.float32)
        image.pixels.foreach_set(px.ravel())
        mat.node_tree.nodes.new("ShaderNodeTexImage").image = image
        from dasktoon_paint import layers
        top = layers.add(image).image
        top.pixels.foreach_set(np.tile(np.array((1, 0, 0, 0.5), np.float32), size * size))
        layers.composite(image)
        old_name = obj.data.uv_layers.active.name
        before = {}
        old_uv = uvs(obj)
        base = image.dasktoon_layers[0].image
        source = np.empty(size * size * 4, np.float32)
        base.pixels.foreach_get(source)
        source = source.reshape(size, size, 4)
        for poly in list(obj.data.polygons)[::7]:
            centre = old_uv[list(poly.loop_indices)].mean(axis=0)
            before[poly.index] = transfer._sample(source, centre[None])[0]
        result = unwrap.unwrap(bpy.context, [obj], None)
        self.assertEqual(result.old[obj], old_name + unwrap.OLD)
        transfer.transfer([obj], result.old, result.mirrored)
        new_uv = uvs(obj)
        after = np.empty(size * size * 4, np.float32)
        base.pixels.foreach_get(after)
        after = after.reshape(size, size, 4)
        errors = [np.abs(transfer._sample(after, new_uv[list(obj.data.polygons[f].loop_indices)].mean(axis=0)[None])[0]
                         - colour).max() for f, colour in before.items()]
        self.assertLess(np.median(errors), 0.03)
        self.assertEqual(len(image.dasktoon_layers), 2)  # the layers carried over too, the picture composited again
        shown = np.empty(size * size * 4, np.float32)
        image.pixels.foreach_get(shown)
        self.assertGreater(shown.reshape(-1, 4)[:, 0].max(), 0.9)


if __name__ == "__main__":
    tu.run_tests()
