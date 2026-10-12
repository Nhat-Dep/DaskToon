# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The illustration finish filter (docs/superpowers/specs/2026-10-13-dasktoon-illustration-finish-design.md): its node
group (one input per setting, only the layers that are on), the scene's compositor (made when the scene has none, the
user's own left alone unless the filter is added to it), muting when off and the Depth pass."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_finish import nodes, scene as finish_scene, settings  # noqa: E402

ALL = set(settings.LAYER_KEYS)


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def layer_nodes(tree, layer):
    return [node for node in tree.nodes if node.get("dasktoon_layer") == layer]


class NodeGroupTest(unittest.TestCase):
    def setUp(self):
        empty_scene()

    def test_inputs_follow_the_settings(self):
        group = nodes.ensure(None, ALL)
        names = [item.name for item in group.interface.items_tree
                 if item.item_type == 'SOCKET' and item.in_out == 'INPUT']
        self.assertEqual(names[:2], ["Image", "Depth"])
        for setting in settings.SETTINGS:
            self.assertEqual(setting.key in names, setting.is_input, setting.key)
        for key in nodes.COMPUTED:
            self.assertIn(key, names)

    def test_only_the_layers_that_are_on(self):
        group = nodes.ensure(None, ALL)
        for layer in settings.LAYER_KEYS:
            self.assertTrue(layer_nodes(group, layer), layer)
        group = nodes.ensure(group, {"haze", "glow"})
        self.assertEqual({node["dasktoon_layer"] for node in group.nodes if node.get("dasktoon_layer")},
                         {"haze", "glow", "amount"})
        self.assertEqual(nodes.layers_of(group), {"haze", "glow"})
        same = group.nodes[:]
        self.assertIs(nodes.ensure(group, {"glow", "haze"}), group)
        self.assertEqual(group.nodes[:], same)  # nothing rebuilt when the layers are the same

    def test_input_values(self):
        values = settings.defaults()
        values["glow_strength"] = 0.9
        mapped = nodes.input_values(values, {"focus": 3.0})
        self.assertAlmostEqual(mapped["glow_strength"], 0.9)
        self.assertAlmostEqual(mapped["focus"], 3.0)
        self.assertNotIn("glow", mapped)          # layer switches are the group's structure, not inputs
        self.assertNotIn("focus_auto", mapped)    # options Python uses itself

    def test_in_vietnamese(self):
        view = bpy.context.preferences.view
        language, translate = view.language, view.use_translate_new_dataname
        view.language, view.use_translate_new_dataname = 'vi_VN', True
        try:
            group = nodes.ensure(None, ALL)
            self.assertIn("Image", [item.name for item in group.interface.items_tree])
        finally:
            view.language, view.use_translate_new_dataname = language, translate


class SceneCompositorTest(unittest.TestCase):
    def setUp(self):
        self.scene = empty_scene()
        self.group = nodes.ensure(None, ALL)

    def test_a_scene_without_compositor_gets_one(self):
        found = finish_scene.ensure_compositor(self.scene, self.group)
        tree = self.scene.compositing_node_group
        self.assertEqual(tree.name, finish_scene.TREE_NAME)
        self.assertEqual(len(found), 1)
        node = found[0]
        self.assertTrue(self.scene.view_layers[0].use_pass_z)
        linked = {link.to_socket.name: link.from_socket.name for link in tree.links if link.to_node == node}
        self.assertEqual(linked, {"Image": "Image", "Depth": "Depth"})
        output = next(n for n in tree.nodes if n.bl_idname == "NodeGroupOutput")
        self.assertTrue(any(link.from_node == node and link.to_node == output for link in tree.links))
        self.assertEqual(finish_scene.ensure_compositor(self.scene, self.group), found)  # once only

    def user_tree(self):
        tree = bpy.data.node_groups.new("Mine", 'CompositorNodeTree')
        tree.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
        layers = tree.nodes.new("CompositorNodeRLayers")
        blur = tree.nodes.new("CompositorNodeBlur")
        output = tree.nodes.new("NodeGroupOutput")
        tree.links.new(layers.outputs["Image"], blur.inputs["Image"])
        tree.links.new(blur.outputs["Image"], output.inputs[0])
        self.scene.compositing_node_group = tree
        return tree, blur, output

    def test_the_users_compositor_is_left_alone(self):
        tree, _blur, _output = self.user_tree()
        before = len(tree.nodes)
        self.assertEqual(finish_scene.ensure_compositor(self.scene, self.group), [])
        self.assertEqual(len(tree.nodes), before)
        self.assertFalse(finish_scene.is_own(tree))

    def test_add_to_the_users_compositor(self):
        tree, blur, output = self.user_tree()
        node = finish_scene.insert(self.scene, self.group)
        self.assertTrue(any(link.from_node == blur and link.to_node == node for link in tree.links))
        self.assertTrue(any(link.from_node == node and link.to_node == output for link in tree.links))
        self.assertTrue(node.inputs["Depth"].is_linked)
        self.assertEqual(finish_scene.group_nodes(self.scene, self.group), [node])

    def test_off_mutes(self):
        node, = finish_scene.ensure_compositor(self.scene, self.group)
        finish_scene.set_enabled(self.scene, self.group, False)
        self.assertTrue(node.mute)
        finish_scene.set_enabled(self.scene, self.group, True)
        self.assertFalse(node.mute)
        self.assertTrue(self.scene.render.use_compositing)


def outline_material(name, idname):
    """A material whose node `idname` (Anime Character or Dask Cel) has its outline on, in Custom color."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    node = mat.node_tree.nodes.new(idname)
    if idname == 'ShaderNodeAnimeCharacter':
        node.use_outline = True
    else:
        node.inputs["Use Outline"].default_value = True
    node.outline_tint_mode = 'CUSTOM'
    return mat, node


class FinishSettingsTest(unittest.TestCase):
    def setUp(self):
        self.scene = empty_scene()
        self.finish = self.scene.dasktoon_finish

    def node(self):
        node, = finish_scene.group_nodes(self.scene, self.finish.group)
        return node

    def test_on_makes_the_compositor_and_writes_the_inputs(self):
        self.assertFalse(self.finish.enabled)
        self.finish.enabled = True
        self.assertIsNotNone(self.finish.group)
        self.assertEqual(self.scene.compositing_node_group.name, finish_scene.TREE_NAME)
        self.finish.glow_strength = 0.8
        self.assertAlmostEqual(self.node().inputs["glow_strength"].default_value, 0.8, places=5)
        self.finish.shadow_tint = (1.0, 0.0, 0.0)
        self.assertEqual(tuple(self.node().inputs["shadow_tint"].default_value)[:3], (1.0, 0.0, 0.0))
        self.finish.enabled = False
        self.assertTrue(self.node().mute)

    def test_a_layer_switch_rebuilds_the_group(self):
        self.finish.enabled = True
        self.assertNotIn("strokes", nodes.layers_of(self.finish.group))
        self.finish.strokes = True
        self.assertIn("strokes", nodes.layers_of(self.finish.group))
        self.finish.haze = False
        self.assertNotIn("haze", nodes.layers_of(self.finish.group))
        self.assertAlmostEqual(self.node().inputs["glow_strength"].default_value, self.finish.glow_strength, places=5)

    def test_viewport(self):
        self.finish.enabled = True
        self.finish.viewport = 'ALWAYS'
        spaces = [area.spaces.active for screen in bpy.data.screens for area in screen.areas
                  if area.type == 'VIEW_3D']
        self.assertTrue(spaces)
        self.assertEqual({space.shading.use_compositor for space in spaces}, {'ALWAYS'})

    def test_add_to_the_users_compositor(self):
        tree = bpy.data.node_groups.new("Mine", 'CompositorNodeTree')
        tree.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
        layers, output = tree.nodes.new("CompositorNodeRLayers"), tree.nodes.new("NodeGroupOutput")
        tree.links.new(layers.outputs["Image"], output.inputs[0])
        self.scene.compositing_node_group = tree
        from bl_ui import dasktoon_finish as ui
        self.finish.enabled = True
        self.assertEqual(ui.compositor_state(self.scene), 'USER')
        self.assertEqual(bpy.ops.dasktoon.finish_add_to_compositor(), {'FINISHED'})
        self.assertEqual(ui.compositor_state(self.scene), 'IN')
        self.assertIs(self.scene.compositing_node_group, tree)

    def test_colored_lines(self):
        anime_mat, anime = outline_material("Skin", 'ShaderNodeAnimeCharacter')
        cel_mat, cel = outline_material("Cloth", 'ShaderNodeDaskCel')
        plain = bpy.data.materials.new("Plain")
        self.assertEqual(bpy.ops.dasktoon.finish_colored_lines(), {'FINISHED'})
        self.assertEqual((anime.outline_tint_mode, cel.outline_tint_mode), ('HARMONIC_KYOTO', 'HARMONIC_KYOTO'))
        self.assertIsNone(plain.get("dasktoon_outline"))

    def test_panels(self):
        from bl_ui import dasktoon_finish as ui
        self.finish.enabled = True
        log = tu.draw(ui.DASKTOON_PT_finish)
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertIn("amount", props)
        self.assertIn("viewport", props)
        self.assertIn("dasktoon.finish_colored_lines", [idname for idname, _text in tu.operators(log)])
        log = tu.draw(ui.DASKTOON_PT_finish_LIGHT)
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertEqual(props[:4], ["glow", "glow_threshold", "glow_size", "glow_strength"])
        self.assertIn("rays", props)
        self.assertIn("wrap", props)


if __name__ == "__main__":
    tu.run_tests()
