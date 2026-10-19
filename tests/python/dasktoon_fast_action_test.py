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

    def test_a_mesh_changing_its_vertices_starts_afresh(self):
        """Subdivision rendered finer than shown (lr_shape's clothes: 1 level shown, 2 rendered) gives the mesh other
        vertices than those the motion was remembered for: matched by their numbers, the afterimages and lines of a
        character fanned out to the wrong places, from its first frame. Where the vertices change, nothing is fast."""
        subdivision = self.body.modifiers.new("Subdivision", 'SUBSURF')
        subdivision.levels = 1
        self.settings.enabled = True
        self.settings.line_density = 1.0
        evaluated(self.body, 3)
        subdivision.levels = 2
        verts, _materials = evaluated(self.body, 4)
        self.assertEqual(len(verts), 98)  # the cube subdivided twice, and nothing more
        for v in verts:
            self.assertLess(max(abs(v[0]), abs(v[1]), abs(v[2])), HALF + 1e-4, v)

    def test_a_remembered_frame_with_other_vertices_shows_nothing_fast(self):
        """Back on a frame played before, the remembered state is shown as it was, for the vertices of then (the render
        of lr_shape read what the viewport remembered at 1 level of Subdivision with the 2 it renders)."""
        subdivision = self.body.modifiers.new("Subdivision", 'SUBSURF')
        subdivision.levels = 1
        self.settings.enabled = True
        self.settings.line_density = 1.0
        evaluated(self.body, 4)
        subdivision.levels = 2
        bpy.context.scene.frame_set(3)
        mesh = self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertEqual(len(mesh.vertices), 98)
        for v in mesh.vertices:
            self.assertLess(max(abs(c) for c in v.co), HALF + 1e-4, tuple(v.co))

    def test_settings_follow_after_an_object_is_deleted(self):
        """Deleting an object leaves an empty entry in the view layer's objects until it updates: the modifiers no
        longer followed the settings (seen deleting a camera in a test)."""
        other = bpy.data.objects.new("Other", None)
        bpy.context.scene.collection.objects.link(other)
        bpy.context.view_layer.update()
        bpy.data.objects.remove(other)
        self.settings.enabled = True
        self.assertIsNotNone(self.modifier())

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

    def test_sized_to_the_character(self):
        """The threshold and the line width are for a character 1.6 m tall and scale with the character's height (real
        model test: a character 2.95 m tall was covered in lines); fewer lines by default."""
        self.body.scale.z = 3.2 / (2 * HALF)  # 3.2 m tall: twice the reference
        bpy.context.view_layer.update()
        self.settings.enabled = True
        modifier = self.modifier()
        self.assertAlmostEqual(fast_action.input_value(modifier, "Threshold"), 2.0 * self.settings.threshold, places=4)
        self.assertAlmostEqual(fast_action.input_value(modifier, "Line Width"), 2.0 * fast_action.LINE_WIDTH, places=6)
        self.assertAlmostEqual(fast_action.input_value(modifier, "Line Length"), self.settings.line_length, places=6)
        self.assertAlmostEqual(self.settings.line_density, 0.08, places=6)

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
        # Wide enough for its Vietnamese labels and notes (cut off at the default width in a real window).
        self.assertGreaterEqual(ui.DASKTOON_PT_fast_action.bl_ui_units_x, 18)
        self.rig.select_set(True)
        log = tu.draw(ui.DASKTOON_PT_fast_action)
        self.assertEqual([entry[1] for entry in log if entry[0] == "prop"],
                         ["threshold", "smear", "afterimages", "afterimage_opacity", "afterimage_color",
                          "line_density", "line_length", "line_color"])
        self.assertEqual([entry[1] for entry in log if entry[0] == "operator"], ["dasktoon.fast_action_bake"])
        self.assertIn("Not baked: Render bakes it first", tu.labels(log))
        self.settings.enabled = True
        bpy.ops.dasktoon.fast_action_bake()
        log = tu.draw(ui.DASKTOON_PT_fast_action)
        self.assertEqual([entry[1] for entry in log if entry[0] == "operator"],
                         ["dasktoon.fast_action_bake", "dasktoon.fast_action_free"])
        self.assertIn("Baked for frames 1 to 24", tu.labels(log))
        self.settings.smear = 0.3
        self.assertIn("Changed since the bake: Render bakes it again", tu.labels(tu.draw(ui.DASKTOON_PT_fast_action)))

    def test_baked_effects_show_without_playing(self):
        """A render reads what playback last worked out, so a frame not played through showed stale effects (the
        combat test); baked, any frame is right at once, played or not."""
        self.settings.enabled = True
        bpy.context.scene.frame_set(4)  # straight there: the frames before were never worked out
        stale = len(self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
        self.assertEqual(fast_action.baked(self.rig), None)
        fast_action.bake(bpy.context, self.rig, list(bpy.context.scene.objects))
        self.assertEqual(fast_action.baked(self.rig), (1, 24, False))
        for frame, expected in ((4, 24), (12, 8), (4, 24)):  # the cube and two afterimages, then the cube alone
            bpy.context.scene.frame_set(frame)
            mesh = self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            self.assertEqual(len(mesh.vertices), expected, msg=frame)
        self.assertNotEqual(stale, 24)

    def test_what_needs_a_bake(self):
        """Rendering bakes first where the bake is missing or old: a setting changed (marked as it changes), the
        frames to render changed, or the motion changed since: keys moved or the timing table changed, which nothing
        marks."""
        from dasktoon_animation import timing
        objects = list(bpy.context.scene.objects)
        self.assertFalse(fast_action.needs_bake(bpy.context, self.rig, objects))  # off: nothing to bake
        self.settings.enabled = True
        self.assertTrue(fast_action.needs_bake(bpy.context, self.rig, objects))
        fast_action.bake(bpy.context, self.rig, objects)
        self.assertFalse(fast_action.needs_bake(bpy.context, self.rig, objects))
        action = self.rig.animation_data.action
        action.layers[0].strips[0].channelbags[0].fcurves[0].keyframe_points[1].co.y = 5.0
        self.assertTrue(fast_action.needs_bake(bpy.context, self.rig, objects))
        fast_action.bake(bpy.context, self.rig, objects)
        timing.set_step(action, 1, 2)
        self.assertTrue(fast_action.needs_bake(bpy.context, self.rig, objects))
        fast_action.bake(bpy.context, self.rig, objects)
        bpy.context.scene.frame_end = 30
        self.assertTrue(fast_action.needs_bake(bpy.context, self.rig, objects))
        fast_action.bake(bpy.context, self.rig, objects)
        self.settings.smear = 0.3
        self.assertTrue(fast_action.needs_bake(bpy.context, self.rig, objects))

    def test_render_bakes_first(self):
        """The user chose (2026-10-19) that rendering bakes what it needs first, then renders; a fresh bake is kept."""
        from unittest import mock
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = scene.render.resolution_y = 16
        camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        scene.collection.objects.link(camera)
        scene.camera = camera
        self.settings.enabled = True
        with mock.patch.object(fast_action, "bake", wraps=fast_action.bake) as bake:
            self.assertEqual(bpy.ops.dasktoon.render(), {'FINISHED'})
            self.assertEqual(bake.call_count, 1)
            self.assertFalse(fast_action.needs_bake(bpy.context, self.rig, list(scene.objects)))
            self.assertEqual(bpy.ops.dasktoon.render(), {'FINISHED'})
            self.assertEqual(bake.call_count, 1)  # still fresh: not baked again
        self.assertIn("Render Result", bpy.data.images)

    def test_render_menu_and_keys_bake_first(self):
        import importlib.util
        ops = [entry[1] for entry in tu.draw(bpy.types.TOPBAR_MT_render) if entry[0] == "operator"]
        self.assertIn("dasktoon.render", ops)
        self.assertNotIn("render.render", ops)
        for module in ("blender_default", "industry_compatible_data"):
            path = os.path.join(bpy.utils.system_resource('SCRIPTS'), "presets", "keyconfig", "keymap_data",
                                module + ".py")
            spec = importlib.util.spec_from_file_location("dt_keymap_" + module, path)
            data = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(data)
            idnames = [idname for _name, _where, keymap in data.generate_keymaps(data.Params())
                       for idname, _event, _options in keymap["items"]]
            self.assertIn("dasktoon.render", idnames, module)
            self.assertNotIn("render.render", idnames, module)

    def test_a_baked_character_exports_to_fbx(self):
        """Engine Export of a baked character failed (the whole workflow tried on RG2, a real model): the bake's state,
        three whole numbers kept on the armature as a custom property, went into the FBX as a vector, which takes
        decimals. It lives in the registered settings now, which the FBX leaves out."""
        import tempfile
        self.settings.enabled = True
        fast_action.bake(bpy.context, self.rig, list(bpy.context.scene.objects))
        path = os.path.join(tempfile.mkdtemp(prefix="dt_fast_fbx_"), "baked.fbx")
        self.assertEqual(bpy.ops.export_scene.fbx(filepath=path, use_custom_props=True), {'FINISHED'})
        self.assertEqual([key for key in self.rig.data.keys() if key.startswith("dasktoon_fast_action_")], [])
        self.assertEqual(fast_action.baked(self.rig), (1, 24, False))

    def test_a_change_after_baking_makes_the_bake_old_and_free_drops_it(self):
        self.settings.enabled = True
        fast_action.bake(bpy.context, self.rig, list(bpy.context.scene.objects))
        self.settings.threshold = 5.0
        self.assertEqual(fast_action.baked(self.rig), (1, 24, True))
        fast_action.free(bpy.context, self.rig, list(bpy.context.scene.objects))
        self.assertIsNone(fast_action.baked(self.rig))


if __name__ == "__main__":
    tu.run_tests()
