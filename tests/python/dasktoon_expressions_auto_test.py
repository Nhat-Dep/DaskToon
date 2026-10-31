# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Auto Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md, part C): one button for the
whole character, a list of what it has, a way to try each on every mesh, and a way to write the eye keys again. The
tools of a mesh are still there, under Expression Tools; every new shape key starts off, whichever tool made it."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_expressions_test as xt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import auto_expressions, expressions  # noqa: E402
from bl_ui import dasktoon_shape_key_manager as skm  # noqa: E402


def shaped(obj, name, delta=(0.0, 0.0, 0.01), value=0.0):
    """A key `name` on `obj` moving every vertex by `delta`."""
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.data.shape_keys
    block = key.key_blocks.get(name) or obj.shape_key_add(name=name, from_mix=False)
    base = np.array([p.co for p in key.reference_key.data])
    block.data.foreach_set("co", (base + np.array(delta)).ravel())
    block.value = value
    return block


def seen(obj):
    """The vertices of `obj` as the mix of its keys shows them."""
    bpy.context.view_layer.update()
    copy = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    out = np.array([v.co for v in copy.vertices])
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return out


def values(obj):
    key = obj.data.shape_keys
    return {b.name: b.value for b in key.key_blocks if b != key.reference_key}


def activate(obj):
    bpy.context.view_layer.objects.active = obj


class KeysStartOffTest(unittest.TestCase):
    """Blender starts a new key at 1. Only Sculpt and Fill were tested for it, and the other tools left theirs on: a key
    showing by itself is a face changed before anything is pressed, doubled by the next tool, and sent as is to the
    game."""

    def setUp(self):
        tu.reset_scene()
        self.obj = tu.add_sphere(segments=8, rings=4)
        activate(self.obj)
        self.rest = np.array([v.co for v in self.obj.data.vertices])

    def assert_off(self):
        self.assertEqual(set(values(self.obj).values()), {0.0}, values(self.obj))
        np.testing.assert_allclose(seen(self.obj), self.rest, atol=1e-6)

    def test_the_vrm_sets(self):
        for kind in ('VRM_0', 'VRM_1'):
            self.assertEqual(bpy.ops.dasktoon.vrm_init_standard(standard_type=kind), {'FINISHED'})
        self.assert_off()

    def test_the_arkit_placeholders(self):
        self.assertEqual(bpy.ops.dasktoon.arkit_init_placeholders(), {'FINISHED'})
        self.assert_off()

    def test_a_split(self):
        shaped(self.obj, "blink")
        self.assertEqual(bpy.ops.dasktoon.vrm_split_shape_key('EXEC_DEFAULT', source_shape="blink"), {'FINISHED'})
        self.assertIn("blink_L", values(self.obj))
        self.assert_off()

    def test_a_bake_does_not_double_what_it_saved(self):
        shaped(self.obj, "joy", value=0.5)
        before = seen(self.obj)
        self.assertEqual(bpy.ops.dasktoon.vrm_bake_expression('EXEC_DEFAULT', new_name="mine", reset_after=False),
                         {'FINISHED'})
        self.assertEqual(values(self.obj)["mine"], 0.0)
        np.testing.assert_allclose(seen(self.obj), before, atol=1e-6)

    def test_a_bake_clearing_goes_back_to_rest(self):
        shaped(self.obj, "joy", value=0.5)
        self.assertEqual(bpy.ops.dasktoon.vrm_bake_expression('EXEC_DEFAULT', new_name="mine", reset_after=True),
                         {'FINISHED'})
        self.assert_off()

    def test_the_arkit_shapes_built_from_the_vrm_keys(self):
        shaped(self.obj, "joy")
        shaped(self.obj, "blink")
        self.assertEqual(bpy.ops.dasktoon.vrm_synthesize_arkit52(), {'FINISHED'})
        self.assertIn("eyeBlinkLeft", values(self.obj))
        self.assert_off()


class Character(unittest.TestCase):
    def setUp(self):
        self.rig, self.objs, self.eyes = et.character()
        self.body = self.objs["Body"]
        for obj in self.objs.values():
            obj.modifiers.new("Armature", 'ARMATURE').object = self.rig
        self.meshes = auto_expressions.meshes_of(self.eyes)
        activate(self.eyes)


class WholeCharacterTest(Character):
    """The eyes, the skin round them and the mouth are often meshes of their own. The tools worked on the active mesh:
    tried from the wrong one, an expression showed nothing, or half of it."""

    def test_any_mesh_or_the_rig_means_all_its_meshes(self):
        self.assertIn(self.body, self.meshes)
        self.assertIn(self.eyes, self.meshes)
        self.assertEqual(set(auto_expressions.meshes_of(self.body)), set(self.meshes))
        self.assertEqual(set(auto_expressions.meshes_of(self.rig)), set(self.meshes))

    def test_a_mesh_without_a_rig_is_on_its_own(self):
        tu.reset_scene()
        lone = tu.add_sphere(segments=8, rings=4)
        self.assertEqual(auto_expressions.meshes_of(lone), [lone])
        self.assertIsNone(auto_expressions.rig_of(lone))

    def test_trying_shows_on_every_mesh(self):
        shaped(self.eyes, "blink")
        shaped(self.body, "blink")
        activate(self.body)
        self.assertEqual(bpy.ops.dasktoon.expression_try(slot="BLINK"), {'FINISHED'})
        self.assertEqual(values(self.eyes)["blink"], 1.0)
        self.assertEqual(values(self.body)["blink"], 1.0)

    def test_trying_one_turns_the_others_off(self):
        shaped(self.eyes, "blink", value=1.0)
        shaped(self.body, "joy", value=1.0)
        self.assertEqual(bpy.ops.dasktoon.expression_try(slot="JOY"), {'FINISHED'})
        self.assertEqual(values(self.eyes)["blink"], 0.0)
        self.assertEqual(values(self.body)["joy"], 1.0)

    def test_a_shape_of_the_body_is_no_expression(self):
        shaped(self.body, "slimmer waist", value=0.4)
        shaped(self.eyes, "blink")
        bpy.ops.dasktoon.expression_try(slot="BLINK")
        self.assertAlmostEqual(values(self.body)["slimmer waist"], 0.4, places=5)
        bpy.ops.dasktoon.expression_rest()
        self.assertAlmostEqual(values(self.body)["slimmer waist"], 0.4, places=5)

    def test_back_to_the_rest_face(self):
        shaped(self.eyes, "blink", value=1.0)
        shaped(self.body, "joy", value=0.5)
        shaped(self.body, "eyeWideLeft", value=0.5)
        self.assertEqual(bpy.ops.dasktoon.expression_rest(), {'FINISHED'})
        self.assertEqual(set(values(self.eyes).values()) | set(values(self.body).values()), {0.0})

    def test_the_preview_cards_show_on_every_mesh_too(self):
        shaped(self.eyes, "blink_l")
        activate(self.body)
        if self.body.data.shape_keys is None:
            self.body.shape_key_add(name="Basis", from_mix=False)
        self.assertEqual(bpy.ops.dasktoon.vrm_guide_solo_preview(card_key='WINK_L'), {'FINISHED'})
        self.assertEqual(values(self.eyes)["blink_l"], 1.0)

    def test_the_arkit_preview_shows_on_every_mesh_too(self):
        shaped(self.eyes, "eyeBlinkLeft")
        activate(self.body)
        self.assertEqual(bpy.ops.dasktoon.arkit_solo_preview(shape_name="eyeBlinkLeft"), {'FINISHED'})
        self.assertEqual(values(self.eyes)["eyeBlinkLeft"], 1.0)


class ShownOnceTest(Character):
    """An expression has several keys: blink and its two sides, joy and happy, joy and the ARKit shapes built from it.
    Turned on together they add up: a blink and its sides move the lids twice as far, past the line they close on, and the
    eye comes out upside down. The previews were tested on one key at a time."""

    def shown(self, obj):
        """How far `obj` moved, as seen, at its furthest."""
        return float(np.abs(seen(obj) - et.rest(obj)).max())

    def test_a_blink_is_not_doubled_by_its_sides(self):
        auto_expressions.run(self.rig, self.meshes)
        once = float(np.abs(et.offsets(self.eyes, "blink")).max())
        self.assertEqual(bpy.ops.dasktoon.expression_try(slot="BLINK"), {'FINISHED'})
        self.assertAlmostEqual(self.shown(self.eyes), once, places=5)
        self.assertEqual(values(self.eyes)["blink_L"], 0.0)

    def test_two_names_of_one_expression_show_once(self):
        shaped(self.eyes, "joy")
        shaped(self.eyes, "happy")
        bpy.ops.dasktoon.expression_try(slot="JOY")
        self.assertAlmostEqual(self.shown(self.eyes), 0.01, places=5)

    def test_of_two_names_the_one_that_moves_is_shown(self):
        self.eyes.shape_key_add(name="Basis", from_mix=False)
        self.eyes.shape_key_add(name="happy", from_mix=False).value = 0.0
        shaped(self.eyes, "joy")
        bpy.ops.dasktoon.expression_try(slot="JOY")
        self.assertAlmostEqual(self.shown(self.eyes), 0.01, places=5)

    def test_a_blink_of_two_sides_only_shows_both(self):
        shaped(self.eyes, "blink_L")
        shaped(self.eyes, "blink_R")
        bpy.ops.dasktoon.expression_try(slot="BLINK")
        self.assertEqual({values(self.eyes)["blink_L"], values(self.eyes)["blink_R"]}, {1.0})

    def test_a_card_takes_the_whole_key_over_the_arkit_shapes(self):
        shaped(self.eyes, "joy")
        shaped(self.eyes, "mouthSmileLeft")
        bpy.ops.dasktoon.vrm_guide_solo_preview(card_key='JOY')
        self.assertEqual(values(self.eyes)["joy"], 1.0)
        self.assertEqual(values(self.eyes)["mouthSmileLeft"], 0.0)

    def test_a_card_takes_the_blink_over_its_sides(self):
        shaped(self.eyes, "blink")
        shaped(self.eyes, "eyeBlinkLeft")
        shaped(self.eyes, "eyeBlinkRight")
        bpy.ops.dasktoon.vrm_guide_solo_preview(card_key='BLINK_BOTH')
        self.assertEqual(values(self.eyes)["blink"], 1.0)
        self.assertEqual(values(self.eyes)["eyeBlinkLeft"], 0.0)

    def test_without_a_whole_key_a_card_takes_the_arkit_shapes(self):
        shaped(self.eyes, "mouthSmileLeft")
        shaped(self.eyes, "mouthSmileRight")
        bpy.ops.dasktoon.vrm_guide_solo_preview(card_key='JOY')
        self.assertEqual({values(self.eyes)["mouthSmileLeft"], values(self.eyes)["mouthSmileRight"]}, {1.0})

    def test_the_looping_preview_closes_the_eyes_once(self):
        auto_expressions.run(self.rig, self.meshes)
        activate(self.body)  # the eyes are a mesh of their own
        keys = skm._live_keys(self.body)
        skm._live_show(keys, skm._live_values('AUTO_BLINK', 0.125))
        self.assertAlmostEqual(values(self.eyes)["blink"], 1.0, places=5)
        self.assertEqual(values(self.eyes)["blink_L"], 0.0)

    def test_the_looping_preview_goes_through_the_emotions(self):
        shaped(self.eyes, "joy")
        shaped(self.eyes, "angry")
        keys = skm._live_keys(self.eyes)
        skm._live_show(keys, skm._live_values('EMOTIONS', 1.0))  # half way through the first
        self.assertAlmostEqual(values(self.eyes)["joy"], 1.0, places=5)
        self.assertEqual(values(self.eyes)["angry"], 0.0)


class ListTest(Character):
    def test_what_moves_what_is_empty_what_is_missing(self):
        shaped(self.eyes, "blink")
        self.eyes.shape_key_add(name="joy", from_mix=False)
        states = auto_expressions.states(self.meshes)
        self.assertEqual(states["BLINK"], 'READY')
        self.assertEqual(states["JOY"], 'EMPTY')
        self.assertEqual(states["SURPRISED"], 'MISSING')

    def test_a_key_moving_on_any_mesh_will_do(self):
        self.eyes.shape_key_add(name="Basis", from_mix=False)
        self.eyes.shape_key_add(name="blink", from_mix=False)
        shaped(self.body, "blink")
        self.assertEqual(auto_expressions.states(self.meshes)["BLINK"], 'READY')

    def test_it_lists_every_expression_a_character_is_asked_for(self):
        self.assertEqual(set(auto_expressions.LISTED) - set(expressions.SLOTS), set())
        for slot in ("BLINK", "BLINK_L", "BLINK_R", "JOY", "ANGRY", "SORROW", "FUN", "SURPRISED", "A", "I", "U", "E", "O"):
            self.assertIn(slot, auto_expressions.LISTED)


class AutoTest(Character):
    def test_the_eyes_get_their_keys_and_all_stay_off(self):
        result = auto_expressions.run(self.rig, self.meshes)
        self.assertIn("blink", [name for name, _meshes in result.sculpted])
        states = auto_expressions.states(self.meshes)
        for slot in ("BLINK", "BLINK_L", "BLINK_R", "JOY", "SURPRISED"):
            self.assertEqual(states[slot], 'READY', slot)
        self.assertEqual(set(values(self.eyes).values()), {0.0})

    def test_a_set_of_empty_keys_is_used_not_doubled(self):
        activate(self.eyes)
        bpy.ops.dasktoon.vrm_init_standard(standard_type='VRM_1')  # blink, blinkLeft, blinkRight, happy, surprised
        auto_expressions.run(self.rig, self.meshes)
        names = values(self.eyes)
        self.assertNotIn("blink_L", names)
        self.assertNotIn("joy", names)
        states = auto_expressions.states(self.meshes)
        for slot in ("BLINK_L", "BLINK_R", "JOY", "SURPRISED"):
            self.assertEqual(states[slot], 'READY', slot)

    def test_what_is_left_is_told(self):
        result = auto_expressions.run(self.rig, self.meshes)
        for slot in ("A", "ANGRY"):
            self.assertIn(slot, result.left)
        self.assertNotIn("BLINK", result.left)

    def test_a_blink_made_by_hand_is_kept_and_its_sides_come_from_it(self):
        shaped(self.eyes, "blink", delta=(0.0, 0.0, -0.02))
        hand = et.offsets(self.eyes, "blink").copy()
        auto_expressions.run(self.rig, self.meshes)
        np.testing.assert_allclose(et.offsets(self.eyes, "blink"), hand, atol=1e-6)
        left = et.side_mask(self.rig, self.eyes, 1.0)
        np.testing.assert_allclose(et.offsets(self.eyes, "blink_L")[left], hand[left], atol=1e-5)

    def test_a_blink_made_on_another_mesh_is_not_doubled(self):
        """The skin closes over the eyes by a key of its own: writing one on the eyes as well would close them twice."""
        shaped(self.body, "blink")
        auto_expressions.run(self.rig, self.meshes)
        self.assertNotIn("blink", values(self.eyes) if self.eyes.data.shape_keys else {})

    def test_without_a_rig_it_still_fills_the_mesh(self):
        tu.reset_scene()
        lone = tu.add_sphere(segments=8, rings=4)
        shaped(lone, "joy")
        lone.shape_key_add(name="happy", from_mix=False)
        result = auto_expressions.run(None, [lone])
        self.assertIn("happy", [name for name, _how in result.filled])
        self.assertEqual(result.sculpted, [])

    def test_the_button(self):
        activate(self.body)
        self.assertEqual(bpy.ops.dasktoon.auto_expressions(), {'FINISHED'})
        self.assertEqual(auto_expressions.states(self.meshes)["BLINK"], 'READY')

    def test_the_button_works_from_the_rig_too(self):
        activate(self.rig)
        self.assertEqual(bpy.ops.dasktoon.auto_expressions(), {'FINISHED'})
        self.assertEqual(auto_expressions.states(self.meshes)["BLINK"], 'READY')


class RedoTest(Character):
    """Keys that move are kept, so the keys of an older version, or of an eye found wrongly, stay as they are until asked
    to go: the button writes them again from the eyes found now."""

    def test_auto_keeps_them_and_redo_replaces_them(self):
        auto_expressions.run(self.rig, self.meshes)
        shaped(self.eyes, "blink", delta=(0.0, 0.0, 0.05), value=1.0)  # opens instead of closing
        wrong = et.offsets(self.eyes, "blink").copy()
        auto_expressions.run(self.rig, self.meshes)
        np.testing.assert_allclose(et.offsets(self.eyes, "blink"), wrong, atol=1e-6)
        self.assertEqual(bpy.ops.dasktoon.redo_eye_expressions('EXEC_DEFAULT'), {'FINISHED'})
        self.assertLess(et.offsets(self.eyes, "blink")[:, 2].min(), -1e-3)
        self.assertEqual(values(self.eyes)["blink"], 0.0)

    def test_a_character_without_eyes_keeps_its_keys(self):
        for obj in self.meshes:
            if obj != self.body:
                bpy.data.objects.remove(obj)
        shaped(self.body, "blink", delta=(0.0, 0.0, 0.05))
        activate(self.body)
        before = et.offsets(self.body, "blink").copy()
        self.assertEqual(bpy.ops.dasktoon.redo_eye_expressions('EXEC_DEFAULT'), {'FINISHED'})
        np.testing.assert_allclose(et.offsets(self.body, "blink"), before, atol=1e-6)

    def test_it_needs_a_rig(self):
        tu.reset_scene()
        lone = tu.add_sphere(segments=8, rings=4)
        shaped(lone, "blink")
        activate(lone)
        self.assertFalse(bpy.ops.dasktoon.redo_eye_expressions.poll())


class PanelTest(Character):
    def test_it_sits_first_under_shape_keys_and_open(self):
        panel = bpy.types.DATA_PT_dasktoon_auto_expressions
        self.assertEqual((panel.bl_context, panel.bl_parent_id), ("data", "DATA_PT_shape_keys"))
        self.assertNotIn('DEFAULT_CLOSED', getattr(panel, "bl_options", set()))
        self.assertLess(skm.classes.index(skm.DATA_PT_dasktoon_auto_expressions),
                        skm.classes.index(skm.DATA_PT_dasktoon_expression_sets))

    def test_it_shows_without_any_shape_key(self):
        self.assertTrue(bpy.types.DATA_PT_dasktoon_auto_expressions.poll(bpy.context))

    def test_one_button_comes_first_then_one_try_for_each_expression(self):
        log = xt.draw(bpy.types.DATA_PT_dasktoon_auto_expressions)
        operators = [entry[1] for entry in log if entry[0] == "operator"]
        self.assertEqual(operators[0], "dasktoon.auto_expressions")
        self.assertEqual(operators.count("dasktoon.expression_try"), len(auto_expressions.LISTED))
        self.assertIn("dasktoon.expression_rest", operators)
        self.assertIn("dasktoon.redo_eye_expressions", operators)

    def test_the_rig_shows_them_too(self):
        """After Anime Humanoid the rig is the active object: its tab is where you are."""
        activate(self.rig)
        operators = [entry[1] for entry in xt.draw(bpy.types.DATA_PT_dasktoon_rig_expressions)
                     if entry[0] == "operator"]
        self.assertEqual(operators[0], "dasktoon.auto_expressions")
        self.assertEqual(operators.count("dasktoon.expression_try"), len(auto_expressions.LISTED))

    def test_the_tools_of_one_mesh_moved_out_of_the_way(self):
        operators = [entry[1] for entry in xt.draw(bpy.types.DATA_PT_dasktoon_expression_sets)
                     if entry[0] == "operator"]
        self.assertNotIn("dasktoon.sculpt_eye_expressions", operators)
        self.assertNotIn("dasktoon.fill_empty_expressions", operators)
        operators = [entry[1] for entry in xt.draw(bpy.types.DATA_PT_dasktoon_expression_tools)
                     if entry[0] == "operator"]
        self.assertIn("dasktoon.sculpt_eye_expressions", operators)
        self.assertIn("dasktoon.fill_empty_expressions", operators)


class GuideTest(Character):
    def test_the_guide_fix_is_the_same_button(self):
        from dasktoon_guide import fixes
        shaped(self.eyes, "blink", delta=(0.0, 0.0, 0.05))
        fixes.fix_expressions(bpy.context, self.meshes, self.rig)
        states = auto_expressions.states(self.meshes)
        self.assertEqual(states["BLINK_L"], 'READY')
        self.assertEqual(states["JOY"], 'READY')  # a blink of its own no longer means no smile


if __name__ == "__main__":
    tu.run_tests()
