# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The fast action filter (anime timing spec 7): where a part of the character moves faster than the threshold, its
trailing side is smeared back, afterimages of the frames before show and speed lines trail it; once it stops nothing
is added. The character's settings drive the modifier of each of its meshes; off, the modifiers are off."""

import os
import sys
import unittest

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_animation import fast_action  # noqa: E402

HALF = 0.25  # half the cube's size


def character():
    """Armature "Rig" with a cube "Body" (its child) that moves 3 m along x from frame 1 to 6 (14.4 m/s), then
    stays."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 24
    scene.render.fps = 24
    rig = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
    scene.collection.objects.link(rig)
    mesh = bpy.data.meshes.new("Body")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2 * HALF)
    bm.to_mesh(mesh)
    bm.free()
    body = bpy.data.objects.new("Body", mesh)
    scene.collection.objects.link(body)
    body.parent = rig
    for frame, x in ((1, 0.0), (6, 3.0)):
        rig.location.x = x
        rig.keyframe_insert("location", index=0, frame=frame)
    for point in rig.animation_data.action.layers[0].strips[0].channelbags[0].fcurves[0].keyframe_points:
        point.interpolation = 'LINEAR'
    bpy.context.view_layer.objects.active = rig
    return rig, body


def evaluated(body, frame):
    """(local vertex positions, material names) of the evaluated `body` at `frame`, the scene played up to it."""
    scene = bpy.context.scene
    for f in range(scene.frame_current + 1 if scene.frame_current < frame else 1, frame + 1):
        scene.frame_set(f)
    mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [tuple(v.co) for v in mesh.vertices], [m.name for m in mesh.materials if m is not None]


class FastActionTest(unittest.TestCase):
    def setUp(self):
        self.rig, self.body = character()
        self.settings = self.rig.data.dasktoon_fast_action
        bpy.context.scene.frame_set(1)

    def modifier(self):
        return self.body.modifiers.get(fast_action.MODIFIER)

    def test_fast_then_still(self):
        self.settings.enabled = True
        modifier = self.modifier()
        self.assertIsNotNone(modifier)
        self.assertEqual(modifier.node_group.name, fast_action.GROUP)
        self.assertEqual(self.body.modifiers[-1], modifier)
        verts, materials = evaluated(self.body, 4)
        self.assertGreaterEqual(len(verts), 3 * 8)  # the cube and two afterimages (and maybe speed lines)
        self.assertIn(fast_action.material_name(self.rig, "Afterimage"), materials)
        verts, _materials = evaluated(self.body, 12)
        self.assertEqual(len(verts), 8)
        self.assertAlmostEqual(min(v[0] for v in verts), -HALF, places=4)

    def test_smear(self):
        self.settings.enabled = True
        self.settings.afterimages = 0
        self.settings.line_density = 0.0
        verts, _materials = evaluated(self.body, 4)
        self.assertEqual(len(verts), 8)
        # The trailing side is smeared back, against the motion (+x); the leading side stays.
        self.assertLess(min(v[0] for v in verts), -HALF - 0.05)
        self.assertAlmostEqual(max(v[0] for v in verts), HALF, places=4)

    def test_afterimages_and_lines(self):
        self.settings.enabled = True
        self.settings.line_density = 1.0
        self.settings.afterimages = 0
        verts, materials = evaluated(self.body, 4)
        self.assertNotIn(fast_action.material_name(self.rig, "Afterimage"), materials)
        self.assertIn(fast_action.material_name(self.rig, "Lines"), materials)
        # Lines trail behind the cube: some of their vertices are far behind it.
        self.assertLess(min(v[0] for v in verts), -HALF - 0.3)

    def test_settings_drive_the_modifier(self):
        self.settings.enabled = True
        self.settings.smear = 0.2
        self.settings.afterimage_color = (1.0, 0.0, 0.0)
        modifier = self.modifier()
        self.assertAlmostEqual(fast_action.input_value(modifier, "Smear"), 0.2, places=5)
        afterimage = bpy.data.materials[fast_action.material_name(self.rig, "Afterimage")]
        self.assertEqual(tuple(fast_action.material_color(afterimage))[:3], (1.0, 0.0, 0.0))
        self.settings.enabled = False
        self.assertFalse(modifier.show_viewport)
        self.assertFalse(modifier.show_render)
        self.settings.enabled = True
        self.assertTrue(modifier.show_viewport)

    def test_in_vietnamese(self):
        """The interface translates new data names; the group's sockets keep their English names."""
        view = bpy.context.preferences.view
        language, translate = view.language, view.use_translate_new_dataname
        view.language, view.use_translate_new_dataname = 'vi_VN', True
        try:
            self.settings.enabled = True
            self.assertAlmostEqual(fast_action.input_value(self.modifier(), "Smear"), self.settings.smear, places=5)
        finally:
            view.language, view.use_translate_new_dataname = language, translate

    def test_only_meshes_of_the_character(self):
        other = bpy.data.objects.new("Other", bpy.data.meshes.new("Other"))
        bpy.context.scene.collection.objects.link(other)
        self.settings.enabled = True
        self.assertIsNone(other.modifiers.get(fast_action.MODIFIER))
        self.assertIsNone(self.rig.modifiers.get(fast_action.MODIFIER))

    def test_popover(self):
        from bl_ui import dasktoon_animation as ui
        self.rig.select_set(True)
        log = tu.draw(ui.DASKTOON_PT_fast_action)
        self.assertEqual([entry[1] for entry in log if entry[0] == "prop"],
                         ["threshold", "smear", "afterimages", "afterimage_opacity", "afterimage_color",
                          "line_density", "line_length", "line_color"])


if __name__ == "__main__":
    tu.run_tests()
