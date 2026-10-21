# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Use DaskToon Shader (docs/superpowers/specs/2026-10-19-dasktoon-model-import-fixes-design.md, section 2): models
brought in with Principled, Emission, Diffuse or their own toon node group get DaskToon's Anime BSDF with its outline,
fed the colour or texture the old shader had. The old nodes stay in the tree, only unhooked from the output.

A model shaded by a node setup of its own that shows a colour (2026-10-21, luna: two toon groups that multiply the
texture by itself) keeps its look: the setup is copied twice, the light it reads (Shader to RGB) replaced by the scene's
Sun and World for Base Color and by the World alone for Shadow Color. The texture alone made luna's black dress grey."""

import math

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
WORLD = (0.05, 0.05, 0.05)  # the light of a World that is not a single colour
# Nodes copied as they are when they lie between a Shader to RGB and the output (their settings are plain values).
COPIED = {'ShaderNodeMix', 'ShaderNodeMixRGB', 'ShaderNodeMath', 'ShaderNodeHueSaturation', 'ShaderNodeBrightContrast',
          'ShaderNodeInvert', 'ShaderNodeGamma', 'ShaderNodeRGBToBW', 'ShaderNodeSeparateColor',
          'ShaderNodeCombineColor', 'ShaderNodeMapRange', 'ShaderNodeClamp', 'ShaderNodeValToRGB', 'NodeReroute'}
LIGHT_READERS = {'ShaderNodeLayerWeight', 'ShaderNodeFresnel', 'ShaderNodeLightPath', 'ShaderNodeAmbientOcclusion',
                 'ShaderNodeCameraData'}


class _Unsupported(Exception):
    """The setup reads the light or the view some other way: the colour comes from the texture as before."""


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


def lighting(scene):
    """(lit, shadow) RGB light a toon setup reads: the brightest visible Sun (its colour x strength / pi, facing it)
    plus the World colour, and the World alone."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        ambient = WORLD
    else:
        strength = background.inputs["Strength"].default_value
        ambient = tuple(c * strength for c in background.inputs["Color"].default_value[:3])
    suns = [o for o in scene.objects if o.type == 'LIGHT' and o.data.type == 'SUN' and o.visible_get()]
    sun = max(suns, key=lambda o: o.data.energy, default=None)
    direct = tuple(c * sun.data.energy / math.pi for c in sun.data.color) if sun is not None else (1.0, 1.0, 1.0)
    return tuple(a + d for a, d in zip(ambient, direct)), ambient


def _reads_light(tree, seen):
    """True when `tree` (or a group in it) has a Shader to RGB; _Unsupported when it reads the light another way."""
    if tree.as_pointer() in seen:
        return seen[tree.as_pointer()]
    seen[tree.as_pointer()] = False
    found = False
    for node in tree.nodes:
        if node.bl_idname in LIGHT_READERS:
            raise _Unsupported(node.name)
        if node.bl_idname == 'ShaderNodeShaderToRGB':
            found = True
        elif node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
            found |= _reads_light(node.node_tree, seen)
    seen[tree.as_pointer()] = found
    return found


def _shader_colour(tree, to_rgb):
    """(socket, value) of the colour of the shader a Shader to RGB reads: its Color, Base Color or Emission colour."""
    link = to_rgb.inputs["Shader"].links[0] if to_rgb.inputs["Shader"].is_linked else None
    shader = link.from_node if link is not None else None
    if shader is None:
        return None, (0.0, 0.0, 0.0, 1.0)
    name = next((n for n in ("Color", "Base Color") if n in shader.inputs), None)
    if name is None or shader.bl_idname not in COLOUR_INPUT and shader.bl_idname != 'ShaderNodeBsdfToon':
        raise _Unsupported(shader.name)
    socket = shader.inputs[name]
    return (socket.links[0].from_socket if socket.is_linked else None), tuple(socket.default_value)


def _lit_group(group, light, made):
    """A copy of `group` whose Shader to RGB nodes give the shader's colour x `light` (groups inside copied too)."""
    key = (group.as_pointer(), light)
    if key in made:
        return made[key]
    copy = group.copy()
    copy.name = "%s (%s)" % (group.name, "lit" if light[0] > 0.0 else "shadow")  # shown in the node editor
    made[key] = copy
    for node in list(copy.nodes):
        if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
            node.node_tree = _lit_group(node.node_tree, light, made)
        elif node.bl_idname == 'ShaderNodeShaderToRGB':
            source, value = _shader_colour(copy, node)
            lit = _multiply(copy, light, source, value)
            for link in list(node.outputs["Color"].links):
                copy.links.new(lit, link.to_socket)
            for link in list(node.outputs["Alpha"].links):
                link.to_socket.default_value = 1.0
                copy.links.remove(link)
            copy.nodes.remove(node)
    # The shaders the Shader to RGB nodes read are left over: the copy reads no light (an export can bake it).
    for node in list(copy.nodes):
        if any(o.type == 'SHADER' for o in node.outputs) and not any(o.is_linked for o in node.outputs):
            copy.nodes.remove(node)
    return made[key]


def _copy_node(tree, node):
    new = tree.nodes.new(node.bl_idname)
    new.location = (node.location.x, node.location.y - 600.0)
    for prop in node.bl_rna.properties:
        if prop.is_readonly or prop.identifier in {"name", "location", "select", "parent", "node_tree"}:
            continue
        try:
            setattr(new, prop.identifier, getattr(node, prop.identifier))
        except (AttributeError, TypeError, ValueError):
            pass
    if node.bl_idname == 'ShaderNodeValToRGB':
        ramp, src = new.color_ramp, node.color_ramp
        ramp.interpolation, ramp.color_mode = src.interpolation, src.color_mode
        while len(ramp.elements) < len(src.elements):
            ramp.elements.new(0.5)
        for element, other in zip(ramp.elements, src.elements):
            element.position, element.color = other.position, tuple(other.color)
    for socket, other in zip(new.inputs, node.inputs):
        if hasattr(other, "default_value") and socket.identifier == other.identifier:
            try:
                socket.default_value = other.default_value
            except (AttributeError, TypeError, ValueError):
                pass
    return new


def _rebuild(tree, socket, light, made, seen):
    """A socket of `tree` giving what `socket` gives with every Shader to RGB upstream reading `light`. Branches that
    do not read the light are linked as they are; the nodes between are copied."""
    node = socket.node
    if node.bl_idname == 'ShaderNodeShaderToRGB':
        source, value = _shader_colour(tree, node)
        if source is not None:
            source = _rebuild(tree, source, light, made, seen)
        return _multiply(tree, light, source, value)
    upstream = [link.from_node for i in node.inputs if i.is_linked for link in i.links]
    group = node.node_tree if node.bl_idname == 'ShaderNodeGroup' else None
    if not ((group is not None and _reads_light(group, seen)) or any(_needs(n, seen) for n in upstream)):
        return socket
    if group is None and node.bl_idname not in COPIED:
        raise _Unsupported(node.name)
    new = _copy_node(tree, node)
    if group is not None:
        new.node_tree = _lit_group(group, light, made)
    for inp in node.inputs:
        if inp.is_linked:
            target = next(s for s in new.inputs if s.identifier == inp.identifier)
            tree.links.new(_rebuild(tree, inp.links[0].from_socket, light, made, seen), target)
    return next(s for s in new.outputs if s.identifier == socket.identifier)


def _needs(node, seen):
    """True when `node` or anything upstream of it reads the light."""
    if node.bl_idname == 'ShaderNodeShaderToRGB':
        return True
    if node.bl_idname in LIGHT_READERS:
        raise _Unsupported(node.name)
    if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None and _reads_light(node.node_tree, seen):
        return True
    return any(_needs(link.from_node, seen) for i in node.inputs if i.is_linked for link in i.links)


def own_look(mat, scene):
    """(lit socket, shadow socket or None) for a material whose Surface takes a colour from a setup of its own; None
    when the Surface takes a shader, or the setup reads the light in a way that cannot be copied."""
    tree = mat.node_tree
    out = _output(tree) if tree is not None else None
    if out is None or not out.inputs["Surface"].is_linked:
        return None
    socket = out.inputs["Surface"].links[0].from_socket
    if socket.type == 'SHADER':
        return None
    lit_light, shadow_light = lighting(scene)
    seen, made = {}, {}
    try:
        if not _needs(socket.node, seen):
            return socket, None  # the colour does not change with the light
        return (_rebuild(tree, socket, lit_light, made, seen), _rebuild(tree, socket, shadow_light, made, seen))
    except _Unsupported:
        for group in made.values():
            bpy.data.node_groups.remove(group)
        return None


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


def convert(mat, scene=None):
    """Give `mat` an Anime BSDF fed its old colour; True when it changed (False: nothing to read, or already DaskToon's).
    A setup of its own keeps its lit and shadow colours, read with the light of `scene` (the current scene)."""
    found = colour_of(mat)
    if found is None:
        return False
    source, value, alpha = found
    look = own_look(mat, scene or bpy.context.scene)
    shadow = None
    if look is not None:
        source, shadow = look
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
    if shadow is not None:
        tree.links.new(shadow, anime.inputs["Shadow Color"])
    else:
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
