# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Start Painting (spec section 3): a UV map when the mesh has none; for every material the faces use whose anime
shader has no picture on its Base Color, a new image filled with that colour, connected to it."""

import bpy
import numpy as np
from mathutils import Color

SIZE = 2048  # enough for a 1.6 m character's whole body (spec, ruling 6)
ISLAND_MARGIN = 0.01  # about 20 pixels at 2048: a fill's bleed over the seams stays off the next island
ANIME = ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel')  # DaskToon's shaders, as dasktoon_material_convert


def anime_node(mat):
    if mat is None or mat.node_tree is None:
        return None
    return next((node for kind in ANIME for node in mat.node_tree.nodes if node.bl_idname == kind), None)


def used_slots(obj):
    """Indices of the material slots the mesh's faces use."""
    indices = np.zeros(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", indices)
    return sorted(set(indices.tolist()) & set(range(len(obj.material_slots))))


def ensure_uv(context, obj):
    """A UV map by Smart UV Project when the mesh has none; True when one was made."""
    if obj.data.uv_layers:
        return False
    mode = obj.mode
    with context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=ISLAND_MARGIN)
        bpy.ops.object.mode_set(mode=mode if mode != 'EDIT' else 'OBJECT')
    return True


def new_picture(name, rgba, size=SIZE):
    """A size × size image filled with `rgba` (scene linear, as a node's colour)."""
    image = bpy.data.images.new(name, size, size, alpha=True)
    color = Color(rgba[:3]).from_scene_linear_to_srgb()  # the byte image holds sRGB values
    image.pixels.foreach_set(np.tile(np.array((*color, 1.0), dtype=np.float32), size * size))
    image.update()
    return image


def start(context, obj, size=SIZE):
    """Make `obj` paintable; returns the images made (none when every anime Base Color has its picture)."""
    ensure_uv(context, obj)
    made = []
    for index in used_slots(obj):
        mat = obj.material_slots[index].material
        node = anime_node(mat)
        if node is None or "Base Color" not in node.inputs or node.inputs["Base Color"].is_linked:
            continue
        socket = node.inputs["Base Color"]
        image = new_picture("%s Color" % mat.name, tuple(socket.default_value), size)
        texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.location = (node.location.x - 320, node.location.y)
        mat.node_tree.links.new(texture.outputs["Color"], socket)
        mat.node_tree.nodes.active = texture  # the texture paint slot
        made.append(image)
    return made
