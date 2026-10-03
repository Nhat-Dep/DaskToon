# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon outline: per-material sources, companion `.Outline` materials and the sync handler (spec 4)."""

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator, Panel

from . import dasktoon_outline_nodes as gn

OUTLINE_PROP = "dasktoon_outline"
OUTLINE_MAT_PROP = "dasktoon_outline_material"
MASK_NAMES = ("Outline_Weight", "outline_weight", "DaskOutline_Mask", "Outline_Mask", "Outline_Width", "outline_mask")

_signatures = {}
_busy = False


def reset_cache():
    _signatures.clear()


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


def _set_value(socket, value):
    current = socket.default_value
    try:
        same = tuple(current) == tuple(value)
    except TypeError:
        same = current == value
    if not same:
        socket.default_value = value


def _sync_socket(source_socket, target_tree, target_socket):
    from .dasktoon_anime_nodes import _sync_outline_socket
    if source_socket.is_linked:
        _sync_outline_socket(source_socket, target_tree, target_socket, {})
    else:
        for link in list(target_socket.links):
            target_tree.links.remove(link)
        _set_value(target_socket, tuple(source_socket.default_value))


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
    for n in list(tree.nodes):
        if n.bl_idname not in {'ShaderNodeDaskOutline', 'ShaderNodeOutputMaterial'}:
            tree.nodes.remove(n)
    _sync_socket(node.inputs["Outline Color"], tree, dask.inputs["Outline Color"])
    _sync_socket(node.inputs["Base Color"], tree, dask.inputs["Base Color"])
    _set_value(dask.inputs["Outline Lighting Mix"], node.inputs["Outline Lighting Mix"].default_value)
    tint_value = node.bl_rna.properties["outline_tint_mode"].enum_items[node.outline_tint_mode].value
    for item in dask.bl_rna.properties["tint_mode"].enum_items:
        if item.value == tint_value and dask.tint_mode != item.identifier:
            dask.tint_mode = item.identifier


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
        width_socket = node.inputs["Outline Width"] if node is not None else dask.inputs["Outline Width"]
        slots.append(gn.SlotParams(True, float(width_socket.default_value),
                                   float(dask.inputs["Light Bleed"].default_value),
                                   float(dask.inputs["Hand Wobble"].default_value), companion))
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


@persistent
def outline_load_post(_filepath):
    reset_cache()
    for scene in bpy.data.scenes:
        sync_all(scene)


class DASKTOON_OT_outline_toggle_material(Operator):
    """Turn the DaskToon outline on or off for a material without an Anime BSDF / Dask Cel node"""
    bl_idname = "dasktoon.outline_toggle_material"
    bl_label = "Outline"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mat = context.material
        if mat is None:
            return {'CANCELLED'}
        mat[OUTLINE_PROP] = not bool(mat.get(OUTLINE_PROP))
        return {'FINISHED'}


class MATERIAL_PT_dasktoon_outline(Panel):
    bl_label = "DaskToon Outline"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        mat = context.material
        main = None
        if mat.node_tree is not None:
            main = next((n for n in mat.node_tree.nodes
                         if n.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}), None)
        if main is not None and main.bl_idname == 'ShaderNodeAnimeCharacter':
            layout.prop(main, "use_outline", text="Outline")
        elif main is not None:
            layout.prop(main.inputs["Use Outline"], "default_value", text="Outline")
        else:
            layout.operator(DASKTOON_OT_outline_toggle_material.bl_idname,
                            text="Outline", depress=bool(mat.get(OUTLINE_PROP)))
        companion = outline_material_for(mat, create=False)
        dask = outline_node(companion)
        if find_source(mat) is not None and dask is not None:
            col = layout.column(align=True)
            if main is None:
                col.prop(dask.inputs["Outline Width"], "default_value", text="Width")
            col.prop(dask.inputs["Light Bleed"], "default_value", text="Light Bleed")
            col.prop(dask.inputs["Hand Wobble"], "default_value", text="Hand Wobble")
            col.prop(dask, "tint_mode", text="")
        layout.operator("dasktoon.outline_prepare_game_data", icon='EXPORT')


classes = (DASKTOON_OT_outline_toggle_material, MATERIAL_PT_dasktoon_outline)


# bl_ui registers `classes` itself; register()/unregister() only manage the handlers.
def register():
    if outline_depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(outline_depsgraph_post)
    if outline_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(outline_load_post)


def unregister():
    for handler_list, handler in ((bpy.app.handlers.depsgraph_update_post, outline_depsgraph_post),
                                  (bpy.app.handlers.load_post, outline_load_post)):
        if handler in handler_list:
            handler_list.remove(handler)
