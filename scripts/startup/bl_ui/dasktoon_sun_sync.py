# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Light Vector inputs of DaskToon nodes (Face Shadow) follow the scene Sun (docs/superpowers/specs/
2026-10-04-dasktoon-ui-reorganization-design.md, section 5). Replaces the "Sync Sun" button and its scripted drivers,
which needed Auto Run Python Scripts."""

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

SOCKET = "Light Vector"
EPSILON = 1e-6
_busy = False
classes = ()


def find_sun(scene):
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN' and obj.visible_get():
            return obj
    return None


def sun_vector(sun):
    """Towards the Sun, as the old Sync Sun computed it."""
    return (sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()


def _trees(materials):
    seen, stack = set(), [m.node_tree for m in materials if m.node_tree is not None and m.library is None]
    while stack:
        tree = stack.pop()
        if tree.as_pointer() in seen or tree.library is not None:
            continue
        seen.add(tree.as_pointer())
        yield tree
        stack.extend(n.node_tree for n in tree.nodes if n.type == 'GROUP' and n.node_tree is not None)


def _drop_driver(tree, socket):
    animation = tree.animation_data
    if animation is None or not animation.drivers:
        return
    path = socket.path_from_id("default_value")
    for fcurve in list(animation.drivers):
        if fcurve.data_path == path:
            animation.drivers.remove(fcurve)


def sync_materials(materials, vector):
    """Write `vector` into every unlinked Light Vector input; returns how many inputs changed."""
    changed = 0
    for tree in _trees(materials):
        for node in tree.nodes:
            socket = node.inputs.get(SOCKET)
            if socket is None or socket.is_linked:
                continue
            _drop_driver(tree, socket)
            if max(abs(a - b) for a, b in zip(socket.default_value, vector)) > EPSILON:
                socket.default_value = vector
                changed += 1
    return changed


def _sync_scene(scene, materials):
    global _busy
    sun = find_sun(scene)
    if sun is None:
        return
    _busy = True
    try:
        sync_materials(materials, sun_vector(sun))
    finally:
        _busy = False


@persistent
def sun_depsgraph_post(scene, depsgraph):
    if _busy:
        return
    materials, lights = set(), False
    for update in depsgraph.updates:
        data = update.id.original
        if isinstance(data, bpy.types.Object) and data.type == 'LIGHT':
            lights = True
        elif isinstance(data, bpy.types.Material):
            materials.add(data)
    if lights:
        _sync_scene(scene, bpy.data.materials)
    elif materials:
        _sync_scene(scene, materials)


@persistent
def sun_load_post(_filepath):
    if bpy.context.scene is not None:
        _sync_scene(bpy.context.scene, bpy.data.materials)


def register():
    if sun_depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sun_depsgraph_post)
    if sun_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(sun_load_post)


def unregister():
    if sun_depsgraph_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sun_depsgraph_post)
    if sun_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(sun_load_post)
