# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon outline: per-material sources, companion `.Outline` materials and the sync handler (spec 4)."""

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator

from . import dasktoon_outline_nodes as gn

OUTLINE_PROP = "dasktoon_outline"
OUTLINE_MAT_PROP = "dasktoon_outline_material"
MASK_NAMES = ("Outline_Weight", "outline_weight", "DaskOutline_Mask", "Outline_Mask", "Outline_Width", "outline_mask")
# Hand-drawn line weight, fixed (UI spec 4): thinner on the lit side, a slight pen wobble.
LIGHT_BLEED = 0.70
HAND_WOBBLE = 0.15

_signatures = {}
_companion_signatures = {}
_busy = False

# Node properties that do not change what a cloned node computes.
_LAYOUT_PROPS = {
    "name", "label", "location", "location_absolute", "width", "height", "width_hidden", "select",
    "hide", "mute", "parent", "color", "color_tag", "use_custom_color", "show_options",
    "show_preview", "show_texture", "warning_propagation",
}


def reset_cache():
    _signatures.clear()
    _companion_signatures.clear()


def find_source(mat):
    """Companion `.Outline` materials never contain a source node, so they return None."""
    if mat is None or mat.node_tree is None:
        return None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeAnimeCharacter' and node.use_outline:
            return ('ANIME_BSDF', node)
        if node.bl_idname == 'ShaderNodeDaskCel' and node.inputs["Use Outline"].default_value:
            return ('DASK_CEL', node)
    if mat.get(OUTLINE_PROP):
        return ('MATERIAL', None)
    return None


def outline_node(outline_mat):
    if outline_mat is None or outline_mat.node_tree is None:
        return None
    return next((n for n in outline_mat.node_tree.nodes if n.bl_idname == 'ShaderNodeDaskOutline'), None)


def outline_material_for(mat, create=True):
    companion = mat.get(OUTLINE_MAT_PROP)
    if isinstance(companion, bpy.types.Material):
        return companion
    if not create:
        return None
    companion = bpy.data.materials.new(mat.name + ".Outline")
    companion.use_backface_culling = True
    if hasattr(companion, "use_backface_culling_shadow"):
        companion.use_backface_culling_shadow = True
    nt = companion.node_tree
    nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial')
    output.location = (300.0, 0.0)
    dask = nt.nodes.new('ShaderNodeDaskOutline')
    nt.links.new(dask.outputs["BSDF"], output.inputs["Surface"])
    mat[OUTLINE_MAT_PROP] = companion
    return companion


def _sync_outline_socket(src_socket, target_tree, target_socket, visited_nodes):
    """Clones upstream node network for a single socket into the target material."""
    if not src_socket or not target_socket:
        return

    if not src_socket.is_linked:
        for lk in list(target_socket.links):
            target_tree.links.remove(lk)
        try:
            target_socket.default_value = src_socket.default_value
        except Exception:
            pass
        return

    def copy_node(src_node):
        if src_node in visited_nodes:
            return visited_nodes[src_node]
        dst_node = target_tree.nodes.new(src_node.bl_idname)
        visited_nodes[src_node] = dst_node

        # Copy RNA properties (like image, blend_type, color_ramp, etc.)
        for prop in src_node.rna_type.properties:
            if not prop.is_readonly and prop.identifier not in {'name', 'location'}:
                try:
                    setattr(dst_node, prop.identifier, getattr(src_node, prop.identifier))
                except Exception:
                    pass

        # Copy unlinked input default values
        for i, in_s in enumerate(src_node.inputs):
            if i < len(dst_node.inputs) and not in_s.is_linked:
                try:
                    dst_node.inputs[i].default_value = in_s.default_value
                except Exception:
                    pass
        return dst_node

    def build(src_sock):
        if not src_sock.is_linked:
            return None
        link = src_sock.links[0]
        src_from_n = link.from_node
        src_from_s = link.from_socket
        dst_from_n = copy_node(src_from_n)

        for in_s in src_from_n.inputs:
            if in_s.is_linked:
                in_link = in_s.links[0]
                up_dst_n = copy_node(in_link.from_node)
                try:
                    f_idx = list(in_link.from_node.outputs).index(in_link.from_socket)
                    t_idx = list(src_from_n.inputs).index(in_s)
                    target_tree.links.new(up_dst_n.outputs[f_idx], dst_from_n.inputs[t_idx])
                    build(in_s)
                except Exception:
                    pass

        try:
            f_sock_idx = list(src_from_n.outputs).index(src_from_s)
            return dst_from_n.outputs[f_sock_idx]
        except Exception:
            return None

    out_s = build(src_socket)
    if out_s:
        for lk in list(target_socket.links):
            target_tree.links.remove(lk)
        target_tree.links.new(out_s, target_socket)


def _set_value(socket, value):
    current = socket.default_value
    try:
        same = tuple(current) == tuple(value)
    except TypeError:
        same = current == value
    if not same:
        socket.default_value = value


def _fix_line_weight(dask):
    """The companion's Dask Outline node gets the fixed Light Bleed and Hand Wobble (linked libraries stay as saved)."""
    if dask.id_data.library is None:
        _set_value(dask.inputs["Light Bleed"], LIGHT_BLEED)
        _set_value(dask.inputs["Hand Wobble"], HAND_WOBBLE)


def _sync_socket(source_socket, target_tree, target_socket):
    if source_socket.is_linked:
        _sync_outline_socket(source_socket, target_tree, target_socket, {})
    else:
        for link in list(target_socket.links):
            target_tree.links.remove(link)
        _set_value(target_socket, tuple(source_socket.default_value))


def _value_key(socket):
    value = getattr(socket, "default_value", None)
    try:
        return tuple(round(v, 6) for v in value)
    except TypeError:
        return round(value, 6) if isinstance(value, float) else value


def _node_key(node):
    """The settings `_sync_outline_socket` copies: writable RNA properties (images by pointer)."""
    parts = []
    for prop in node.bl_rna.properties:
        if prop.is_readonly or prop.identifier in _LAYOUT_PROPS:
            continue
        value = getattr(node, prop.identifier, None)
        if isinstance(value, bpy.types.ID):
            value = value.as_pointer()
        elif isinstance(value, bpy.types.bpy_struct):
            continue
        elif hasattr(value, "__len__") and not isinstance(value, str):
            value = tuple(value)
        parts.append((prop.identifier, value))
    return tuple(parts)


def _upstream_key(socket, depth=0):
    """Structural signature of everything that feeds `socket`."""
    if not socket.is_linked or depth > 64:
        return ("value", _value_key(socket))
    link = socket.links[0]
    node = link.from_node
    return (node.bl_idname, link.from_socket.identifier, _node_key(node),
            tuple(_upstream_key(s, depth + 1) for s in node.inputs))


def sync_material(mat):
    """Quick controls of the main node -> companion material (one-way, spec 4.2)."""
    source = find_source(mat)
    if source is None or source[1] is None:
        return
    _kind, node = source
    companion = outline_material_for(mat)
    dask = outline_node(companion)
    if dask is None:
        return
    tree = companion.node_tree
    # Re-clone the color branches only when they really changed: rebuilding the companion's nodes
    # recompiles its shader, which would stutter on every slider tick of the source material.
    key = (_upstream_key(node.inputs["Outline Color"]), _upstream_key(node.inputs["Base Color"]))
    if _companion_signatures.get(companion.as_pointer()) != key:
        for n in list(tree.nodes):
            if n.bl_idname not in {'ShaderNodeDaskOutline', 'ShaderNodeOutputMaterial'}:
                tree.nodes.remove(n)
        _sync_socket(node.inputs["Outline Color"], tree, dask.inputs["Outline Color"])
        _sync_socket(node.inputs["Base Color"], tree, dask.inputs["Base Color"])
        _companion_signatures[companion.as_pointer()] = key
    _set_value(dask.inputs["Outline Lighting Mix"], node.inputs["Outline Lighting Mix"].default_value)
    tint_value = node.bl_rna.properties["outline_tint_mode"].enum_items[node.outline_tint_mode].value
    for item in dask.bl_rna.properties["tint_mode"].enum_items:
        if item.value == tint_value and dask.tint_mode != item.identifier:
            dask.tint_mode = item.identifier
    _fix_line_weight(dask)


def find_sun(scene):
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN' and obj.visible_get():
            return obj
    return None


def _slot_params(obj):
    slots = []
    for slot in obj.material_slots:
        mat = slot.material
        source = find_source(mat)
        if source is None:
            slots.append(gn.SlotParams(False, 0.0, 0.0, 0.0, None))
            continue
        companion = outline_material_for(mat)
        dask = outline_node(companion)
        node = source[1]
        _fix_line_weight(dask)
        width_socket = node.inputs["Outline Width"] if node is not None else dask.inputs["Outline Width"]
        slots.append(gn.SlotParams(True, float(width_socket.default_value), LIGHT_BLEED, HAND_WOBBLE, companion))
    return slots


def sync_object(obj, scene):
    if obj.type != 'MESH' or obj.library is not None:
        return
    slots = _slot_params(obj)
    if not any(s.enabled for s in slots):
        _signatures.pop(obj.as_pointer(), None)
        gn.remove_modifier(obj)
        return
    sun = find_sun(scene)
    uv_name = obj.data.uv_layers[0].name if obj.data.uv_layers else ""
    mask_name = next((name for name in MASK_NAMES if name in obj.vertex_groups), "")
    signature = (
        tuple((s.enabled, round(s.width, 6), round(s.bleed, 6), round(s.wobble, 6),
               s.outline_material.as_pointer() if s.outline_material else 0) for s in slots),
        sun.as_pointer() if sun else 0, uv_name, mask_name, obj.name,
    )
    if _signatures.get(obj.as_pointer()) == signature and obj.modifiers.get(gn.MODIFIER_NAME):
        return
    gn.ensure_modifier(obj, gn.build_object_group(obj, slots, sun, mask_name, uv_name))
    _signatures[obj.as_pointer()] = signature


def sync_all(scene):
    for mat in bpy.data.materials:
        if mat.library is None:
            sync_material(mat)
    for obj in scene.objects:
        sync_object(obj, scene)


@persistent
def outline_depsgraph_post(scene, depsgraph):
    global _busy
    if _busy:
        return
    materials, objects, everything = set(), set(), False
    for update in depsgraph.updates:
        data = update.id.original
        if isinstance(data, bpy.types.Material):
            materials.add(data)
        elif isinstance(data, bpy.types.Object):
            if data.type == 'LIGHT':
                everything = True
            elif update.is_updated_geometry or update.is_updated_shading:
                objects.add(data)
    if not (materials or objects or everything):
        return
    _busy = True
    try:
        # Light Bleed / Hand Wobble are edited on <material>.Outline, which is in no object slot:
        # map an edited companion back to the material(s) that own it.
        companions = {m for m in materials if find_source(m) is None}
        if companions:
            materials.update(m for m in bpy.data.materials if m.get(OUTLINE_MAT_PROP) in companions)
        for mat in materials:
            sync_material(mat)
        if everything:
            targets = list(scene.objects)
        else:
            targets = set(objects)
            if materials:
                targets.update(o for o in scene.objects
                               if any(slot.material in materials for slot in getattr(o, "material_slots", ())))
        for obj in targets:
            sync_object(obj, scene)
    finally:
        _busy = False


def outline_load_post(_filepath):
    """Called by dasktoon_upgrade's load_post handler, after any file upgrade has run."""
    reset_cache()
    for scene in bpy.data.scenes:
        sync_all(scene)


class DASKTOON_OT_outline_remove_legacy(Operator):
    """Turn off the DaskToon outline this material got before outlines moved onto the Anime BSDF and Dask Cel nodes"""
    bl_idname = "dasktoon.outline_remove_legacy"
    bl_label = "Remove DaskToon Outline"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mat = getattr(context, "material", None)
        return mat is not None and mat.library is None and bool(mat.get(OUTLINE_PROP))

    def execute(self, context):
        del context.material[OUTLINE_PROP]
        sync_all(context.scene)
        return {'FINISHED'}


def material_menu_func(self, context):
    """Material slot menu: only for a material outlined the old way (no Anime BSDF / Dask Cel node with outline)."""
    mat = getattr(context, "material", None)
    if mat is not None and mat.get(OUTLINE_PROP) and find_source(mat) == ('MATERIAL', None):
        self.layout.separator()
        self.layout.operator(DASKTOON_OT_outline_remove_legacy.bl_idname, icon='X')


classes = (DASKTOON_OT_outline_remove_legacy,)


# bl_ui registers `classes` itself; register()/unregister() manage the handler and the material slot menu entry.
def register():
    from .properties_material import MATERIAL_MT_context_menu
    if outline_depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(outline_depsgraph_post)
    MATERIAL_MT_context_menu.append(material_menu_func)


def unregister():
    from .properties_material import MATERIAL_MT_context_menu
    if outline_depsgraph_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(outline_depsgraph_post)
    MATERIAL_MT_context_menu.remove(material_menu_func)
