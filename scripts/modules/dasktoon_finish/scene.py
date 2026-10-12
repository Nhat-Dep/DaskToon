# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The illustration finish in the scene's compositor (spec section 7). A scene without a compositor gets DaskToon's
own (Render Layers, the finish, the output); a compositor the user made is left alone unless the finish is added to it
on purpose. Off, the finish's node is muted, so the tree around it is kept."""

import bpy

TREE_NAME = "DaskToon Compositor"
OWN = "dasktoon_compositor"  # marks the compositor DaskToon made


def is_own(tree):
    return tree is not None and bool(tree.get(OWN))


def group_nodes(scene, group):
    """The nodes of the scene's compositor that use `group`."""
    tree = scene.compositing_node_group
    if tree is None:
        return []
    return [node for node in tree.nodes if node.bl_idname == "CompositorNodeGroup" and node.node_tree == group]


def enable_depth(scene):
    """The Depth pass, which Air, Soft Background and Back Light Wrap read."""
    for view_layer in scene.view_layers:
        if not view_layer.use_pass_z:
            view_layer.use_pass_z = True
    tree = scene.compositing_node_group
    for node in tree.nodes if tree is not None else ():
        if node.bl_idname == "CompositorNodeRLayers" and "Depth" not in node.outputs:
            node.layer = node.layer  # Render Layers makes the sockets of new passes when its layer is set


def _group_node(tree, group):
    node = tree.nodes.new("CompositorNodeGroup")
    node.node_tree = group
    node.name = node.label = group.name
    return node


def _link_depth(tree, node):
    layers = next((n for n in tree.nodes if n.bl_idname == "CompositorNodeRLayers"), None)
    if layers is not None and "Depth" in layers.outputs:
        tree.links.new(layers.outputs["Depth"], node.inputs["Depth"])


def ensure_compositor(scene, group):
    """The scene's nodes using `group`. A scene without a compositor gets DaskToon's with the finish in it; DaskToon's
    own compositor gets the finish back if it lost it; a compositor the user made is not changed."""
    enable_depth(scene)
    tree = scene.compositing_node_group
    if tree is None:
        tree = bpy.data.node_groups.new(TREE_NAME, 'CompositorNodeTree')
        tree[OWN] = True
        tree.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor').name = "Image"
        layers = tree.nodes.new("CompositorNodeRLayers")
        layers.location = (-400.0, 0.0)
        node = _group_node(tree, group)
        output = tree.nodes.new("NodeGroupOutput")
        output.location = (400.0, 0.0)
        tree.links.new(layers.outputs["Image"], node.inputs["Image"])
        _link_depth(tree, node)
        tree.links.new(node.outputs[0], output.inputs[0])
        scene.compositing_node_group = tree
        return [node]
    found = group_nodes(scene, group)
    if found or not is_own(tree):
        return found
    return [insert(scene, group)]


def insert(scene, group):
    """Put the finish right before the output of the scene's compositor; returns its node."""
    enable_depth(scene)
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.bl_idname == "NodeGroupOutput")
    node = _group_node(tree, group)
    node.location = (output.location.x, output.location.y - 200.0)
    link = next((link for link in tree.links if link.to_socket == output.inputs[0]), None)
    if link is not None:
        source = link.from_socket
        tree.links.remove(link)
        tree.links.new(source, node.inputs["Image"])
    else:
        layers = next((n for n in tree.nodes if n.bl_idname == "CompositorNodeRLayers"), None)
        if layers is not None:
            tree.links.new(layers.outputs["Image"], node.inputs["Image"])
    tree.links.new(node.outputs[0], output.inputs[0])
    _link_depth(tree, node)
    return node


def set_enabled(scene, group, enabled):
    """On, the finish's nodes work (and the scene composites); off, they are muted."""
    for node in group_nodes(scene, group):
        if node.mute == enabled:
            node.mute = not enabled
    if enabled and not scene.render.use_compositing:
        scene.render.use_compositing = True
