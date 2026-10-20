# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Model Check of the Guide (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): a character a
newcomer made right passes every check; each thing done wrong is caught by its check, and the check's fix, where
DaskToon has one, puts it right."""

import math
import os
import sys
import unittest

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_skeleton_test as st  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_material_convert as convert  # noqa: E402
from dasktoon_guide import checks, fixes  # noqa: E402

ARM = st.CentreLineTest.ARM
LEG = st.CentreLineTest.LEG
FOOT = st.FacingTest.FRONT  # reaching to -Y, the front
HANGING = [(0.2, 0.0, 1.42), (0.24, 0.0, 1.1), (0.26, 0.0, 0.8)]  # arms down along the body
BEFORE_RIG = ("size", "floor", "middle", "facing", "pose", "scale", "normals", "mirror", "ngons", "parts", "uv",
              "shader", "unused")


def good(arm=ARM, foot=True, reset=True):
    """The test chibi as a newcomer should leave it: standing on the floor in the middle, facing -Y (its feet tell),
    arms out, a UV map, DaskToon's shader. `reset` starts from an empty file (not in a window: it resets the UI)."""
    if reset:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    body = st.polyline_chibi(arm, LEG, extra=[FOOT] if foot else [])
    body.data.transform(Matrix.Translation((-3.0, -0.5, 0.0)))  # polyline_chibi stands at (3, 0.5)
    bm = bmesh.new()  # the tubes' caps are n-gons and their faces not all outward: as a newcomer should leave them
    bm.from_mesh(body.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    body.data.uv_layers.new(name="UVMap")
    mat = bpy.data.materials.new("Skin")
    mat.use_nodes = True
    convert.convert(mat)
    body.data.materials.append(mat)
    bpy.context.view_layer.update()
    return body


def results(objects):
    return {r.id: r for r in checks.run(bpy.context, objects)}


def status(objects, check):
    return results(objects)[check].status


def fix(objects, check):
    fixes.run(bpy.context, check, objects)
    bpy.context.view_layer.update()


class GoodTest(unittest.TestCase):
    def test_a_good_character_passes_every_check_before_the_rig(self):
        body = good()
        found = results([body])
        self.assertEqual({name: found[name].status for name in BEFORE_RIG}, {name: 'OK' for name in BEFORE_RIG})
        self.assertEqual(found["rig"].status, 'ERROR')  # not rigged yet
        self.assertTrue(found["rig"].fixable)
        for name in ("rig_check", "joints", "eyes", "mouth", "expressions"):
            self.assertEqual(found[name].status, 'LATER', name)  # they need the rig
        later = [found[name].text for name in ("rig_check", "joints", "eyes", "mouth", "expressions")]
        self.assertEqual(len(set(later)), len(later), later)  # each says which check waits
        self.assertTrue(all(r.text for r in found.values()))
        self.assertEqual([r.id for r in checks.run(bpy.context, [body])], list(checks.ORDER))


class StandingTest(unittest.TestCase):
    def test_size(self):
        body = good()
        body.data.transform(Matrix.Scale(3.0, 4))  # 6 m tall
        self.assertEqual(status([body], "size"), 'WARN')
        fix([body], "size")
        self.assertEqual(status([body], "size"), 'OK')
        world = np.array([body.matrix_world @ v.co for v in body.data.vertices])
        self.assertAlmostEqual(float(np.ptp(world[:, 2])), 1.6, places=3)
        self.assertEqual(status([body], "floor"), 'OK')  # scaled about its feet
        self.assertEqual(status([body], "scale"), 'OK')  # and applied

    def test_floor(self):
        body = good()
        body.location.z = 0.5
        self.assertEqual(status([body], "floor"), 'WARN')
        fix([body], "floor")
        self.assertEqual(status([body], "floor"), 'OK')

    def test_middle(self):
        body = good()
        body.location.x = 1.0
        self.assertEqual(status([body], "middle"), 'WARN')
        fix([body], "middle")
        self.assertEqual(status([body], "middle"), 'OK')

    def test_facing(self):
        body = good()
        body.rotation_euler.z = math.pi  # facing +Y
        self.assertEqual(status([body], "facing"), 'ERROR')
        fix([body], "facing")
        self.assertEqual(status([body], "facing"), 'OK')

    def test_feet_that_do_not_tell(self):
        self.assertEqual(status([good(foot=False)], "facing"), 'WARN')

    def test_arms_hanging_down(self):
        self.assertEqual(status([good(arm=HANGING)], "pose"), 'ERROR')


class MeshTest(unittest.TestCase):
    def test_uneven_and_negative_scale(self):
        body = good()
        body.scale = (1.0, 1.0, 1.2)
        self.assertEqual(status([body], "scale"), 'WARN')
        fix([body], "scale")
        self.assertEqual(status([body], "scale"), 'OK')
        self.assertAlmostEqual(body.scale.z, 1.0)
        body.scale = (-1.0, 1.0, 1.0)
        self.assertEqual(status([body], "scale"), 'ERROR')

    def test_normals_pointing_in(self):
        body = good()
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(body.data)
        bm.free()
        self.assertEqual(status([body], "normals"), 'ERROR')
        fix([body], "normals")
        self.assertEqual(status([body], "normals"), 'OK')

    def test_mirror(self):
        body = good()
        body.modifiers.new("Mirror", 'MIRROR')
        self.assertEqual(status([body], "mirror"), 'WARN')
        fix([body], "mirror")
        self.assertEqual(status([body], "mirror"), 'OK')
        self.assertFalse(any(m.type == 'MIRROR' for m in body.modifiers))

    def test_ngons(self):
        body = good()
        mesh = body.data
        start = len(mesh.vertices)
        mesh.vertices.add(5)
        for i in range(5):
            mesh.vertices[start + i].co = (math.cos(i * 1.2566) * 0.05, -0.4, 1.0 + math.sin(i * 1.2566) * 0.05)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.new([bm.verts[start + i] for i in range(5)])
        bm.to_mesh(mesh)
        bm.free()
        self.assertEqual(status([body], "ngons"), 'WARN')
        fix([body], "ngons")
        self.assertEqual(status([body], "ngons"), 'OK')
        self.assertLessEqual(max(len(p.vertices) for p in body.data.polygons), 4)

    def test_one_piece(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add()
        self.assertEqual(status([bpy.context.active_object], "parts"), 'WARN')


class MaterialsTest(unittest.TestCase):
    def test_no_uv_map(self):
        body = good()
        body.data.uv_layers.remove(body.data.uv_layers[0])
        self.assertEqual(status([body], "uv"), 'WARN')
        fix([body], "uv")
        self.assertEqual(status([body], "uv"), 'OK')

    def test_not_dasktoons_shader(self):
        body = good()
        plain = bpy.data.materials.new("Plain")
        plain.use_nodes = True  # a new material starts with DaskToon's shader: make it a Principled one
        tree = plain.node_tree
        tree.nodes.clear()
        tree.links.new(tree.nodes.new('ShaderNodeBsdfPrincipled').outputs[0],
                       tree.nodes.new('ShaderNodeOutputMaterial').inputs["Surface"])
        body.data.materials[0] = plain
        self.assertEqual(status([body], "shader"), 'WARN')
        fix([body], "shader")
        self.assertEqual(status([body], "shader"), 'OK')

    def test_a_material_no_face_uses(self):
        body = good()
        body.data.materials.append(bpy.data.materials.new("Unused"))
        self.assertEqual(status([body], "unused"), 'WARN')
        fix([body], "unused")
        self.assertEqual(status([body], "unused"), 'OK')
        self.assertEqual([m.name for m in body.data.materials], ["Skin"])


class AfterRigTest(unittest.TestCase):
    def test_the_rig_fix_is_the_auto_rig(self):
        body = good()
        fix([body], "rig")
        found = results([body])
        self.assertEqual(found["rig"].status, 'OK')
        self.assertNotEqual(found["rig_check"].status, 'LATER')  # the auto rig ran the rig's Check
        # its thin arm tubes blend over one ring at the elbow (6 or 7 vertices): too few to round it
        self.assertEqual(found["joints"].status, 'WARN')
        self.assertIn("Elbow", found["joints"].text)
        self.assertNotIn("Knee", found["joints"].text)  # 24 vertices at each knee
        self.assertEqual(found["eyes"].status, 'WARN')  # the test chibi has no eye pieces
        self.assertEqual(found["mouth"].status, 'WARN')
        self.assertEqual(found["expressions"].status, 'WARN')

    def test_joints_without_blended_vertices(self):
        """Hard weights (each vertex on one bone) leave nothing for the bend fixes to round."""
        import dasktoon_rig_regions_test as rt
        from dasktoon_rig import build
        rig, objs = rt.rigged()
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        body = objs["Body"]
        self.assertEqual(status([rig, body], "joints"), 'OK')  # its limbs blend over several rings
        for vertex in body.data.vertices:
            if len(vertex.groups) > 1:
                strongest = max(vertex.groups, key=lambda g: g.weight).group
                for element in list(vertex.groups):
                    if element.group != strongest:
                        body.vertex_groups[element.group].remove([vertex.index])
        found = results([rig, body])
        self.assertEqual(found["joints"].status, 'WARN')
        self.assertIn("Knee", found["joints"].text)

    def test_eyes_mouth_and_expressions(self):
        import dasktoon_expressions_eyes_test as et
        rig, _objs, eyes = et.character()
        face = et.painted_face(rig)
        objects = [rig, eyes, face]
        found = results(objects)
        self.assertEqual((found["eyes"].status, found["mouth"].status), ('OK', 'OK'))
        self.assertEqual(found["expressions"].status, 'WARN')
        self.assertTrue(found["expressions"].fixable)
        fix(objects, "expressions")  # no blink yet: Sculpt Eye Expressions
        self.assertEqual(status(objects, "expressions"), 'OK')
        eyes.shape_key_add(name="happy", from_mix=False)  # an empty one: joy moves, so it can be filled
        self.assertEqual(status(objects, "expressions"), 'WARN')
        fix(objects, "expressions")
        self.assertEqual(status(objects, "expressions"), 'OK')


if __name__ == "__main__":
    tu.run_tests()
