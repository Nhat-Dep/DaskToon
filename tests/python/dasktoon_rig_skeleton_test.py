# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon standard skeleton: Unity's 55 human bones, T-pose, mirrored sides, fitted to meshes (anime rig spec 4)."""

import math
import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402

UNITY_HUMAN_BONES = {
    "Hips", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot", "Spine",
    "Chest", "UpperChest", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm",
    "LeftLowerArm", "RightLowerArm", "LeftHand", "RightHand", "LeftToes", "RightToes", "LeftEye", "RightEye", "Jaw",
} | {side + finger + segment for side in ("Left", "Right")
     for finger in ("Thumb", "Index", "Middle", "Ring", "Little")
     for segment in ("Proximal", "Intermediate", "Distal")}


def box(name, low, high):
    """A mesh object filling the box low-high (world)."""
    mesh = bpy.data.meshes.new(name)
    (x0, y0, z0), (x1, y1, z1) = low, high
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def tube(a, b, radius, rings=8, segments=12):
    """(verts, faces) of a closed tube from point a to point b."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    side = axis.orthogonal().normalized()
    other = axis.cross(side)
    verts, faces = [], []
    for r in range(rings + 1):
        centre = a + (b - a) * (r / rings)
        for k in range(segments):
            angle = 2.0 * math.pi * k / segments
            verts.append(tuple(centre + (side * math.cos(angle) + other * math.sin(angle)) * radius))
    for r in range(rings):
        for k in range(segments):
            i, j = r * segments + k, r * segments + (k + 1) % segments
            faces.append((i, i + segments, j + segments, j))
    last = rings * segments
    faces += [tuple(range(segments))[::-1], tuple(range(last, last + segments))]
    return verts, faces


def chibi(offset=(3.0, 0.5, 0.0)):
    """A chibi character 2 tall in A-pose, as one Body mesh: a big head (the top quarter), a short torso, arms 50
    degrees down from the shoulders, legs; and rabbit ears behind the head, a mesh of their own that pushes the
    bounding box back. Returns (body, ears, {landmark: world point})."""
    o = Vector(offset)
    angle = math.radians(50.0)
    marks = {"tip_left": o + Vector((0.12 + 0.62 * math.cos(angle), 0.0, 1.42 - 0.62 * math.sin(angle))),
             "shoulder_left": o + Vector((0.16, 0.0, 1.38)), "hip_left": o + Vector((0.08, 0.0, 0.95)),
             "ankle_left": o + Vector((0.09, 0.0, 0.08))}
    pieces = [tube(o + Vector((0, 0, 0.88)), o + Vector((0, 0, 1.46)), 0.18),  # torso
              tube(o + Vector((0, 0, 1.46)), o + Vector((0, 0, 2.0)), 0.3)]  # head
    for s in (1.0, -1.0):
        pieces.append(tube(o + Vector((0.12 * s, 0, 1.42)),
                           o + Vector(((0.12 + 0.62 * math.cos(angle)) * s, 0, 1.42 - 0.62 * math.sin(angle))), 0.05))
        pieces.append(tube(o + Vector((0.08 * s, 0, 0.95)), o + Vector((0.09 * s, 0, 0.0)), 0.07))
    verts, faces = [], []
    for piece_verts, piece_faces in pieces:
        faces += [tuple(i + len(verts) for i in face) for face in piece_faces]
        verts += piece_verts
    mesh = bpy.data.meshes.new("Body")
    mesh.from_pydata(verts, [], faces)
    body = bpy.data.objects.new("Body", mesh)
    bpy.context.scene.collection.objects.link(body)
    ears = box("Ears", tuple(o + Vector((-0.2, 0.4, 1.7))), tuple(o + Vector((0.2, 1.4, 2.0))))
    return body, ears, marks


def line_distance(point, a, b):
    """Distance from `point` to the line through a and b."""
    axis = (b - a).normalized()
    return (point - a - axis * (point - a).dot(axis)).length


def world_head(rig, name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def world_tail(rig, name):
    return rig.matrix_world @ rig.data.bones[name].tail_local


class TemplateTest(unittest.TestCase):
    def test_bones_are_unity_human_bones(self):
        names = [b[0] for b in skeleton.bones()]
        self.assertEqual(len(names), 55)
        self.assertEqual(set(names), UNITY_HUMAN_BONES)
        self.assertEqual(tuple(names), skeleton.BONE_NAMES)

    def test_parents_come_first(self):
        seen = set()
        for name, parent, _head, _tail, _z in skeleton.bones():
            self.assertTrue(parent is None or parent in seen, name)
            seen.add(name)

    def test_sides_mirror(self):
        table = {b[0]: b for b in skeleton.bones()}
        for name, (_n, parent, head, tail, _z) in table.items():
            if not name.startswith("Left"):
                continue
            right = table["Right" + name[4:]]
            self.assertEqual(right[1], parent if parent is None or not parent.startswith("Left")
                             else "Right" + parent[4:])
            self.assertEqual(right[2], (-head[0], head[1], head[2]))
            self.assertEqual(right[3], (-tail[0], tail[1], tail[2]))
            self.assertGreater(head[0], 0.0, name)

    def test_required_bones_are_in_the_template(self):
        self.assertEqual(len(skeleton.REQUIRED), 15)
        self.assertTrue(set(skeleton.REQUIRED) <= set(skeleton.BONE_NAMES))
        self.assertTrue(set(skeleton.FACE_BONES) <= set(skeleton.BONE_NAMES))


class CreateTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_create_humanoid(self):
        rig = skeleton.create_humanoid(bpy.context, 1.6, (1.0, 2.0, 0.0))
        self.assertEqual(len(rig.data.bones), 55)
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertTrue(rig.data.use_mirror_x)
        self.assertTrue(rig.show_in_front)
        self.assertEqual(rig.mode, 'OBJECT')
        self.assertAlmostEqual((rig.matrix_world.translation - Vector((1.0, 2.0, 0.0))).length, 0.0, places=6)
        self.assertAlmostEqual(world_tail(rig, "Head").z, 0.99 * 1.6, places=5)
        self.assertGreater(world_head(rig, "LeftHand").x, 1.0)
        self.assertLess(world_head(rig, "RightHand").x, 1.0)
        self.assertEqual(rig.data.bones["LeftUpperArm"].parent.name, "LeftShoulder")
        self.assertTrue(rig.data.bones["LeftLowerArm"].use_connect)
        self.assertFalse(rig.data.bones["LeftShoulder"].use_connect)
        self.assertIsNone(rig.data.bones["Hips"].parent)

    def test_create_keeps_the_active_object(self):
        other = box("Other", (0, 0, 0), (1, 1, 1))
        bpy.context.view_layer.objects.active = other
        skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        self.assertEqual(bpy.context.view_layer.objects.active, other)

    def test_missing_bones(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["Spine"])
            edit.remove(edit["LeftIndexDistal"])
        self.assertEqual(skeleton.missing_bones(rig.data), ["Spine"])
        self.assertFalse(skeleton.is_humanoid(rig))
        self.assertFalse(skeleton.is_humanoid(None))
        self.assertFalse(skeleton.is_humanoid(box("Mesh", (0, 0, 0), (1, 1, 1))))

    def test_placement(self):
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        height, location = skeleton.placement([mesh], (0.0, 0.0, 0.0))
        self.assertAlmostEqual(height, 2.0, places=6)
        self.assertAlmostEqual((location - Vector((5.0, 0.0, 1.0))).length, 0.0, places=6)
        height, location = skeleton.placement([], (7.0, 0.0, 0.0))
        self.assertEqual(height, skeleton.DEFAULT_HEIGHT)
        self.assertEqual(tuple(location), (7.0, 0.0, 0.0))

    def test_fit_moves_joints_not_the_object(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["LeftLittleDistal"])
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        self.assertAlmostEqual(skeleton.fit(bpy.context, rig, [mesh]), 2.0, places=6)
        self.assertEqual(tuple(rig.matrix_world.translation), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(world_tail(rig, "Head").z, 1.0 + 0.99 * 2.0, places=5)
        self.assertAlmostEqual(world_head(rig, "Hips").x, 5.0, places=5)
        self.assertNotIn("LeftLittleDistal", rig.data.bones)
        self.assertEqual(len(rig.data.bones), 54)

    def test_fit_follows_the_shape_of_the_body(self):
        """A chibi in A-pose (real model test: the bounding box fit gave T-pose arms 0.7 m from the hands and a spine
        behind the body): the arms follow the mesh down to the hands, the legs end at the ankles, the spine is in the
        body, not in the middle of a box that includes the ears."""
        body, ears, marks = chibi()
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        skeleton.fit(bpy.context, rig, [body, ears], body=[body])
        for s, side in ((1.0, "Left"), (-1.0, "Right")):
            def mirrored(name):
                point = marks[name + "_left"].copy()
                point.x = 3.0 + (point.x - 3.0) * s
                return point

            shoulder, tip = mirrored("shoulder"), mirrored("tip")
            self.assertLess((world_tail(rig, side + "MiddleDistal") - tip).length, 0.06, side)
            self.assertLess((world_head(rig, side + "UpperArm") - shoulder).length, 0.1, side)
            for bone in ("LowerArm", "Hand"):
                self.assertLess(line_distance(world_head(rig, side + bone), shoulder, tip), 0.03, side + bone)
            hip, ankle = world_head(rig, side + "UpperLeg"), world_head(rig, side + "Foot")
            self.assertLess(abs(hip.z - mirrored("hip").z), 0.12, side)
            self.assertLess((ankle - mirrored("ankle")).length, 0.06, side)
        hips = world_head(rig, "Hips")
        self.assertLess((hips.to_2d() - Vector((3.0, 0.5))).length, 0.01)
        self.assertLess(abs(hips.z - 0.95), 0.12)
        self.assertTrue(world_head(rig, "LeftUpperArm").z < world_head(rig, "Neck").z < world_head(rig, "Head").z
                        < 1.7)
        self.assertLess(abs(world_head(rig, "Head").y - 0.5), 0.05)

    def test_fit_keeps_the_sides_mirrored(self):
        """A bag behind the left hip (part of the Body) pulls that side's depth back: both sides still get the same
        depth, so the skeleton stays mirrored (real model test: the hips were 9 cm apart in depth)."""
        body, ears, _marks = chibi()
        bag = box("Bag", (3.05, 0.6, 0.7), (3.25, 0.9, 1.0))
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        skeleton.fit(bpy.context, rig, [body, ears, bag], body=[body, bag])
        middle = world_head(rig, "Hips").x
        for bone in ("UpperLeg", "LowerLeg", "Foot", "UpperArm", "Hand"):
            left, right = world_head(rig, "Left" + bone), world_head(rig, "Right" + bone)
            self.assertAlmostEqual(left.y, right.y, places=4, msg=bone)
            self.assertAlmostEqual(left.x - middle, middle - right.x, places=4, msg=bone)

    def bent_chibi(self):
        """The chibi of chibi(), as one Body mesh, seen the same from the front, with its elbows 8 cm forward and its
        knees 6 cm back."""
        o = Vector((3.0, 0.5, 0.0))
        angle = math.radians(50.0)
        down = Vector((math.cos(angle), 0.0, -math.sin(angle)))
        pieces = [tube(o + Vector((0, 0, 0.88)), o + Vector((0, 0, 1.46)), 0.18),
                  tube(o + Vector((0, 0, 1.46)), o + Vector((0, 0, 2.0)), 0.3)]
        elbow, knee = Vector((0.0, -0.08, 0.0)), Vector((0.0, 0.06, 0.0))
        for s in (1.0, -1.0):
            flip = Vector((s, 1.0, 1.0))
            shoulder = o + Vector((0.12, 0.0, 1.42)) * flip
            arm = [shoulder + (down * 0.62 * t) * flip for t in (0.0, 0.35, 0.65, 1.0)]
            arm[1] += elbow
            arm[2] += elbow
            hip, ankle = o + Vector((0.08 * s, 0.0, 0.95)), o + Vector((0.09 * s, 0.0, 0.0))
            leg = [hip + (ankle - hip) * t for t in (0.0, 0.35, 0.65, 1.0)]
            leg[1] += knee
            leg[2] += knee
            for line, radius in ((arm, 0.05), (leg, 0.07)):
                pieces += [tube(line[k], line[k + 1], radius) for k in range(3)]
        verts, faces = [], []
        for piece_verts, piece_faces in pieces:
            faces += [tuple(i + len(verts) for i in face) for face in piece_faces]
            verts += piece_verts
        mesh = bpy.data.meshes.new("Body")
        mesh.from_pydata(verts, [], faces)
        body = bpy.data.objects.new("Body", mesh)
        bpy.context.scene.collection.objects.link(body)
        return body

    def assert_bends_followed(self, rig):
        for side in ("Left", "Right"):
            self.assertAlmostEqual(world_head(rig, side + "LowerArm").y, 0.5 - 0.08, delta=0.015, msg=side)
            self.assertAlmostEqual(world_head(rig, side + "LowerLeg").y, 0.5 + 0.06, delta=0.015, msg=side)
            self.assertLess((world_tail(rig, side + "UpperArm") - world_head(rig, side + "LowerArm")).length, 1e-5)
            self.assertLess((world_tail(rig, side + "UpperLeg") - world_head(rig, side + "LowerLeg")).length, 1e-5)

    def test_elbows_and_knees_sit_in_the_middle_of_the_limb(self):
        """Real models (tdt, lr_shape) hold their arms a little forward at the elbow and bend their knees: on the
        straight line from the shoulder to the hand, the hip to the ankle, the Check of the auto rig found the elbows
        and knees 1 to 4 cm outside the arms and legs."""
        body = self.bent_chibi()
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        skeleton.fit(bpy.context, rig, [body], body=[body])
        self.assert_bends_followed(rig)

    def test_an_outline_shell_is_not_the_limb(self):
        """An anime outline: a shell a few millimetres outside the skin with its faces turned in (Solidify, normals
        flipped), as on tdt. Its surfaces are crossed the other way round and pair with nothing: the knee is not put
        between the shell and the skin."""
        body = self.bent_chibi()
        shell = body.modifiers.new("Outline", 'SOLIDIFY')
        shell.thickness, shell.offset, shell.use_flip_normals = 0.004, 1.0, True
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        skeleton.fit(bpy.context, rig, [body], body=[body])
        self.assert_bends_followed(rig)

if __name__ == "__main__":
    tu.run_tests()
