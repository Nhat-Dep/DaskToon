# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Use DaskToon Shader (docs/superpowers/specs/2026-10-19-dasktoon-model-import-fixes-design.md, section 2): models
brought in with Principled, Emission, Diffuse or their own toon node group get DaskToon's Anime BSDF with its outline,
fed the colour or texture the old shader had. The old nodes stay in the tree, only unhooked from the output."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import EnumProperty
from bpy.types import Operator

ANIME = {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}
COLOUR_INPUT = {"ShaderNodeBsdfPrincipled": "Base Color", "ShaderNodeEmission": "Color",
                "ShaderNodeBsdfDiffuse": "Color", "ShaderNodeBsdfToon": "Color"}
SHADOW = (0.78, 0.72, 0.86)  # the colour in shadow: darker, a little cooler
OUTLINE = (0.3, 0.22, 0.25)  # the outline: the colour, much darker
SETTINGS = {"Shadow Threshold": 0.46, "Shadow Softness": 0.035, "Ambient Color": (0.85, 0.9, 1.0, 1.0),
            "Ambient Factor": 0.5, "Rim Color": (1.0, 0.98, 0.9, 1.0), "Rim Factor": 0.5, "Outline Width": 0.002,
            "Outline Lighting Mix": 0.1}
GREY = (0.7, 0.7, 0.7, 1.0)


def _output(tree):
    outputs = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial']
    return next((n for n in outputs if n.is_active_output), outputs[0] if outputs else None)


def colour_of(mat):
    """(socket feeding the colour or None, the colour when nothing feeds it, socket feeding alpha or None), or None when
    the material has no shader to read or already uses DaskToon's."""
    tree = mat.node_tree
    out = _output(tree) if tree is not None else None
    if out is None or not out.inputs["Surface"].is_linked:
        return None
    shader = out.inputs["Surface"].links[0].from_node
    if shader.bl_idname in ANIME:
        return None
    alpha = None
    if shader.bl_idname in COLOUR_INPUT:
        socket = shader.inputs[COLOUR_INPUT[shader.bl_idname]]
        if "Alpha" in shader.inputs and shader.inputs["Alpha"].is_linked:
            alpha = shader.inputs["Alpha"].links[0].from_socket
    elif shader.bl_idname == 'ShaderNodeGroup':
        socket = next((s for s in shader.inputs if s.type == 'RGBA'), None)
    else:
        socket = None
    if socket is None:  # a mix or anything else: the first image texture, else grey
        tex = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeTexImage' and n.image), None)
        return (tex.outputs["Color"], GREY, None) if tex else (None, GREY, None)
    if socket.is_linked:
        return socket.links[0].from_socket, GREY, alpha
    return None, tuple(socket.default_value), alpha


def _multiply(tree, rgb, source, value):
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["B"].default_value = rgb + (1.0,)
    if source is not None:
        tree.links.new(source, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = value
    return mix.outputs["Result"]


def convert(mat):
    """Give `mat` an Anime BSDF fed its old colour; True when it changed (False: nothing to read, or already DaskToon's)."""
    found = colour_of(mat)
    if found is None:
        return False
    source, value, alpha = found
    tree = mat.node_tree
    out = _output(tree)
    anime = tree.nodes.new("ShaderNodeAnimeCharacter")
    anime.location = (out.location.x - 300.0, out.location.y + 300.0)
    anime.use_outline = True
    for name, setting in SETTINGS.items():
        if name in anime.inputs:
            anime.inputs[name].default_value = setting
    if source is not None:
        tree.links.new(source, anime.inputs["Base Color"])
    else:
        anime.inputs["Base Color"].default_value = value
    tree.links.new(_multiply(tree, SHADOW, source, value), anime.inputs["Shadow Color"])
    tree.links.new(_multiply(tree, OUTLINE, source, value), anime.inputs["Outline Color"])
    if alpha is not None:
        tree.links.new(alpha, anime.inputs["Alpha"])
    tree.links.new(anime.outputs["BSDF"], out.inputs["Surface"])
    return True


def _materials(context, scope):
    if scope == 'ACTIVE':
        obj = context.object
        return [obj.active_material] if obj is not None and obj.active_material is not None else []
    objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if context.object is not None and context.object.type == 'MESH' and context.object not in objects:
        objects.append(context.object)
    return list(dict.fromkeys(slot.material for obj in objects for slot in obj.material_slots if slot.material))


class DASKTOON_OT_material_to_anime(Operator):
    """Give materials DaskToon's Anime BSDF with an outline, keeping their colour or texture; the old nodes stay"""
    bl_idname = "dasktoon.material_to_anime"
    bl_label = "Use DaskToon Shader"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Materials", description="Which materials to change",
        items=(('ACTIVE', "This Material", "The active material only"),
               ('OBJECTS', "All of the Selected Objects", "Every material of the selected objects")),
        default='OBJECTS')

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        materials = _materials(context, self.scope)
        changed = sum(1 for mat in materials if convert(mat))
        if not materials:
            self.report({'WARNING'}, rpt_("No materials to change"))
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("DaskToon shader on %d materials, %d left as they were")
                    % (changed, len(materials) - changed))
        return {'FINISHED'}


def menu_func(self, _context):
    layout = self.layout
    layout.separator()
    layout.operator("dasktoon.material_to_anime", text="Use DaskToon Shader", icon='SHADING_RENDERED').scope = 'ACTIVE'
    layout.operator("dasktoon.material_to_anime", text="Use DaskToon Shader on All Selected",
                    icon='SHADING_RENDERED').scope = 'OBJECTS'


classes = (DASKTOON_OT_material_to_anime,)


# bl_ui registers `classes`; register()/unregister() only manage the menu entry.
def register():
    from .properties_material import MATERIAL_MT_context_menu
    MATERIAL_MT_context_menu.append(menu_func)


def unregister():
    from .properties_material import MATERIAL_MT_context_menu
    MATERIAL_MT_context_menu.remove(menu_func)
