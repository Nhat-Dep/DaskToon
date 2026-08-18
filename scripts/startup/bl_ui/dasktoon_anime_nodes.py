# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Operator, Menu
from bpy.props import StringProperty, BoolProperty
from bl_operators.node import NodeAddOperator


# =============================================================================
# Helper: Socket Creation Compatibility
# =============================================================================

def _add_socket(node_tree, name, in_out, socket_type, default_val=None, min_val=None, max_val=None):
    """Safely create an interface socket for a NodeTree in Blender 4.0+."""
    socket = node_tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    if default_val is not None and hasattr(socket, 'default_value'):
        try:
            socket.default_value = default_val
        except (TypeError, ValueError):
            pass
    if min_val is not None and hasattr(socket, 'min_value'):
        try:
            socket.min_value = min_val
        except (TypeError, ValueError):
            pass
    if max_val is not None and hasattr(socket, 'max_value'):
        try:
            socket.max_value = max_val
        except (TypeError, ValueError):
            pass
    return socket


# =============================================================================
# 1. DaskToon Anime Cel Shader Node Group
# =============================================================================

def get_or_create_cel_shader_group():
    group_name = "DaskToon_Anime_CelShader"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'COLOR'

    # Interface Sockets
    _add_socket(tree, "Base Color", 'INPUT', 'NodeSocketColor', (0.95, 0.85, 0.8, 1.0))
    _add_socket(tree, "Shadow 1 Color", 'INPUT', 'NodeSocketColor', (0.75, 0.55, 0.55, 1.0))
    _add_socket(tree, "Shadow 2 Color", 'INPUT', 'NodeSocketColor', (0.45, 0.35, 0.45, 1.0))
    _add_socket(tree, "Shadow 1 Threshold", 'INPUT', 'NodeSocketFloat', 0.48, 0.0, 1.0)
    _add_socket(tree, "Shadow 2 Threshold", 'INPUT', 'NodeSocketFloat', 0.22, 0.0, 1.0)
    _add_socket(tree, "Shadow Softness", 'INPUT', 'NodeSocketFloat', 0.02, 0.001, 0.5)
    _add_socket(tree, "Specular Color", 'INPUT', 'NodeSocketColor', (1.0, 1.0, 1.0, 1.0))
    _add_socket(tree, "Specular Size", 'INPUT', 'NodeSocketFloat', 0.08, 0.0, 1.0)
    _add_socket(tree, "Specular Softness", 'INPUT', 'NodeSocketFloat', 0.02, 0.001, 0.5)
    _add_socket(tree, "Rim Color", 'INPUT', 'NodeSocketColor', (0.85, 0.92, 1.0, 1.0))
    _add_socket(tree, "Rim Intensity", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 5.0)
    _add_socket(tree, "Rim Width", 'INPUT', 'NodeSocketFloat', 0.35, 0.0, 1.0)
    _add_socket(tree, "Normal", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))

    _add_socket(tree, "BSDF", 'OUTPUT', 'NodeSocketShader')
    _add_socket(tree, "Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Shadow Mask", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Specular Mask", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Rim Mask", 'OUTPUT', 'NodeSocketFloat')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-900, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (900, 0)

    # Diffuse lighting extraction
    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = (-700, 200)
    links.new(group_in.outputs['Normal'], diffuse.inputs['Normal'])

    s2rgb = nodes.new('ShaderNodeShaderToRGB')
    s2rgb.location = (-500, 200)
    links.new(diffuse.outputs['BSDF'], s2rgb.inputs['Shader'])

    rgb_bw = nodes.new('ShaderNodeRGBToBW')
    rgb_bw.location = (-320, 200)
    links.new(s2rgb.outputs['Color'], rgb_bw.inputs['Color'])

    # Shadow 1 MapRange (Smoothstep)
    sub1_min = nodes.new('ShaderNodeMath')
    sub1_min.operation = 'SUBTRACT'
    sub1_min.location = (-320, 40)
    links.new(group_in.outputs['Shadow 1 Threshold'], sub1_min.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], sub1_min.inputs[1])

    add1_max = nodes.new('ShaderNodeMath')
    add1_max.operation = 'ADD'
    add1_max.location = (-320, -100)
    links.new(group_in.outputs['Shadow 1 Threshold'], add1_max.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], add1_max.inputs[1])

    map_s1 = nodes.new('ShaderNodeMapRange')
    map_s1.clamp = True
    map_s1.location = (-120, 200)
    links.new(rgb_bw.outputs['Val'], map_s1.inputs['Value'])
    links.new(sub1_min.outputs['Value'], map_s1.inputs['From Min'])
    links.new(add1_max.outputs['Value'], map_s1.inputs['From Max'])

    # Shadow 2 MapRange
    sub2_min = nodes.new('ShaderNodeMath')
    sub2_min.operation = 'SUBTRACT'
    sub2_min.location = (-320, -260)
    links.new(group_in.outputs['Shadow 2 Threshold'], sub2_min.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], sub2_min.inputs[1])

    add2_max = nodes.new('ShaderNodeMath')
    add2_max.operation = 'ADD'
    add2_max.location = (-320, -400)
    links.new(group_in.outputs['Shadow 2 Threshold'], add2_max.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], add2_max.inputs[1])


    map_s2 = nodes.new('ShaderNodeMapRange')
    map_s2.clamp = True
    map_s2.location = (-120, -260)
    links.new(rgb_bw.outputs['Val'], map_s2.inputs['Value'])
    links.new(sub2_min.outputs['Value'], map_s2.inputs['From Min'])
    links.new(add2_max.outputs['Value'], map_s2.inputs['From Max'])

    # Color Mixing: Shadow 2 -> Shadow 1 -> Base
    mix_s21 = nodes.new('ShaderNodeMix')
    mix_s21.data_type = 'RGBA'
    mix_s21.location = (100, 100)
    links.new(map_s2.outputs['Result'], mix_s21.inputs['Factor'])
    links.new(group_in.outputs['Shadow 2 Color'], mix_s21.inputs[6])
    links.new(group_in.outputs['Shadow 1 Color'], mix_s21.inputs[7])

    mix_base = nodes.new('ShaderNodeMix')
    mix_base.data_type = 'RGBA'
    mix_base.location = (280, 100)
    links.new(map_s1.outputs['Result'], mix_base.inputs['Factor'])
    links.new(mix_s21.outputs[2], mix_base.inputs[6])
    links.new(group_in.outputs['Base Color'], mix_base.inputs[7])

    # Specular calculation
    glossy = nodes.new('ShaderNodeBsdfGlossy')
    glossy.inputs['Roughness'].default_value = 0.05
    glossy.location = (-500, 450)
    links.new(group_in.outputs['Normal'], glossy.inputs['Normal'])

    glossy_s2rgb = nodes.new('ShaderNodeShaderToRGB')
    glossy_s2rgb.location = (-320, 450)
    links.new(glossy.outputs['BSDF'], glossy_s2rgb.inputs['Shader'])

    glossy_bw = nodes.new('ShaderNodeRGBToBW')
    glossy_bw.location = (-140, 450)
    links.new(glossy_s2rgb.outputs['Color'], glossy_bw.inputs['Color'])

    spec_min = nodes.new('ShaderNodeMath')
    spec_min.operation = 'SUBTRACT'
    spec_min.inputs[0].default_value = 1.0
    spec_min.location = (-140, 600)
    links.new(group_in.outputs['Specular Size'], spec_min.inputs[1])

    spec_max = nodes.new('ShaderNodeMath')
    spec_max.operation = 'ADD'
    spec_max.location = (60, 600)
    links.new(spec_min.outputs['Value'], spec_max.inputs[0])
    links.new(group_in.outputs['Specular Softness'], spec_max.inputs[1])

    spec_map = nodes.new('ShaderNodeMapRange')
    spec_map.clamp = True
    spec_map.location = (240, 450)
    links.new(glossy_bw.outputs['Val'], spec_map.inputs['Value'])
    links.new(spec_min.outputs['Value'], spec_map.inputs['From Min'])
    links.new(spec_max.outputs['Value'], spec_map.inputs['From Max'])

    # Rim light calculation
    fresnel = nodes.new('ShaderNodeLayerWeight')
    fresnel.inputs['Blend'].default_value = 0.5
    fresnel.location = (-320, -550)
    links.new(group_in.outputs['Normal'], fresnel.inputs['Normal'])

    rim_map = nodes.new('ShaderNodeMapRange')
    rim_map.clamp = True
    rim_map.location = (-120, -550)
    links.new(fresnel.outputs['Facing'], rim_map.inputs['Value'])
    rim_map.inputs['From Min'].default_value = 0.0
    links.new(group_in.outputs['Rim Width'], rim_map.inputs['From Max'])
    rim_map.inputs['To Min'].default_value = 1.0
    rim_map.inputs['To Max'].default_value = 0.0

    rim_mult = nodes.new('ShaderNodeMath')
    rim_mult.operation = 'MULTIPLY'
    rim_mult.location = (80, -550)
    links.new(rim_map.outputs['Result'], rim_mult.inputs[0])
    links.new(group_in.outputs['Rim Intensity'], rim_mult.inputs[1])

    # Combine Base + Specular + Rim
    mix_spec = nodes.new('ShaderNodeMix')
    mix_spec.data_type = 'RGBA'
    mix_spec.blend_type = 'ADD'
    mix_spec.location = (460, 100)
    links.new(spec_map.outputs['Result'], mix_spec.inputs['Factor'])
    links.new(mix_base.outputs[2], mix_spec.inputs[6])
    links.new(group_in.outputs['Specular Color'], mix_spec.inputs[7])

    mix_rim = nodes.new('ShaderNodeMix')
    mix_rim.data_type = 'RGBA'
    mix_rim.blend_type = 'ADD'
    mix_rim.location = (640, 100)
    links.new(rim_mult.outputs['Value'], mix_rim.inputs['Factor'])
    links.new(mix_spec.outputs[2], mix_rim.inputs[6])
    links.new(group_in.outputs['Rim Color'], mix_rim.inputs[7])

    # Emission BSDF
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (720, 300)
    links.new(mix_rim.outputs[2], emission.inputs['Color'])

    # Link to Group Output
    links.new(emission.outputs['Emission'], group_out.inputs['BSDF'])
    links.new(mix_rim.outputs[2], group_out.inputs['Color'])
    links.new(map_s1.outputs['Result'], group_out.inputs['Shadow Mask'])
    links.new(spec_map.outputs['Result'], group_out.inputs['Specular Mask'])
    links.new(rim_map.outputs['Result'], group_out.inputs['Rim Mask'])

    return tree


# =============================================================================
# 2. DaskToon Anime Rim Light Node Group
# =============================================================================

def get_or_create_rim_light_group():
    group_name = "DaskToon_Anime_RimLight"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'COLOR'

    _add_socket(tree, "Rim Color", 'INPUT', 'NodeSocketColor', (0.8, 0.92, 1.0, 1.0))
    _add_socket(tree, "Rim Power", 'INPUT', 'NodeSocketFloat', 3.0, 0.1, 20.0)
    _add_socket(tree, "Rim Width", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)
    _add_socket(tree, "Rim Softness", 'INPUT', 'NodeSocketFloat', 0.05, 0.001, 0.5)
    _add_socket(tree, "Normal", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))

    _add_socket(tree, "Rim Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Rim Factor", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Emission BSDF", 'OUTPUT', 'NodeSocketShader')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-600, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (600, 0)

    lw = nodes.new('ShaderNodeLayerWeight')
    lw.location = (-400, 0)
    links.new(group_in.outputs['Normal'], lw.inputs['Normal'])

    # Invert facing: 1.0 - Facing
    sub_facing = nodes.new('ShaderNodeMath')
    sub_facing.operation = 'SUBTRACT'
    sub_facing.inputs[0].default_value = 1.0
    sub_facing.location = (-220, 0)
    links.new(lw.outputs['Facing'], sub_facing.inputs[1])

    # Power
    pow_facing = nodes.new('ShaderNodeMath')
    pow_facing.operation = 'POWER'
    pow_facing.location = (-60, 0)
    links.new(sub_facing.outputs['Value'], pow_facing.inputs[0])
    links.new(group_in.outputs['Rim Power'], pow_facing.inputs[1])

    # Map Range to Width & Softness
    map_rim = nodes.new('ShaderNodeMapRange')
    map_rim.clamp = True
    map_rim.location = (120, 0)
    links.new(pow_facing.outputs['Value'], map_rim.inputs['Value'])
    links.new(group_in.outputs['Rim Softness'], map_rim.inputs['From Min'])
    links.new(group_in.outputs['Rim Width'], map_rim.inputs['From Max'])

    # Multiply Color
    mix_col = nodes.new('ShaderNodeMix')
    mix_col.data_type = 'RGBA'
    mix_col.blend_type = 'MULTIPLY'
    mix_col.location = (300, 0)
    mix_col.inputs['Factor'].default_value = 1.0
    links.new(group_in.outputs['Rim Color'], mix_col.inputs[6])
    links.new(map_rim.outputs['Result'], mix_col.inputs[7])

    emission = nodes.new('ShaderNodeEmission')
    emission.location = (420, 150)
    links.new(mix_col.outputs[2], emission.inputs['Color'])

    links.new(mix_col.outputs[2], group_out.inputs['Rim Color'])
    links.new(map_rim.outputs['Result'], group_out.inputs['Rim Factor'])
    links.new(emission.outputs['Emission'], group_out.inputs['Emission BSDF'])

    return tree


# =============================================================================
# 3. DaskToon Anime Hair Highlight / Angel Ring Node Group
# =============================================================================

def get_or_create_angel_ring_group():
    group_name = "DaskToon_Anime_AngelRing"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'COLOR'

    _add_socket(tree, "Highlight Color", 'INPUT', 'NodeSocketColor', (1.0, 0.96, 0.88, 1.0))
    _add_socket(tree, "Band Position", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)
    _add_socket(tree, "Band Width", 'INPUT', 'NodeSocketFloat', 0.08, 0.001, 0.5)
    _add_socket(tree, "Band Softness", 'INPUT', 'NodeSocketFloat', 0.02, 0.001, 0.2)
    _add_socket(tree, "Strand Noise Jitter", 'INPUT', 'NodeSocketFloat', 0.12, 0.0, 1.0)
    _add_socket(tree, "Noise Scale", 'INPUT', 'NodeSocketFloat', 35.0, 1.0, 200.0)
    _add_socket(tree, "Intensity", 'INPUT', 'NodeSocketFloat', 1.5, 0.0, 10.0)
    _add_socket(tree, "UV Vector", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))

    _add_socket(tree, "Highlight Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Highlight Factor", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Emission BSDF", 'OUTPUT', 'NodeSocketShader')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-800, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (800, 0)

    # Texture Coordinate fallback if UV not plugged
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-800, -200)

    sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
    sep_xyz.location = (-600, 0)
    links.new(group_in.outputs['UV Vector'], sep_xyz.inputs['Vector'])

    # Noise for hair strands
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Roughness'].default_value = 0.5
    noise.location = (-600, -200)
    links.new(group_in.outputs['Noise Scale'], noise.inputs['Scale'])
    links.new(tex_coord.outputs['UV'], noise.inputs['Vector'])

    # Center noise (-0.5 to +0.5)
    noise_sub = nodes.new('ShaderNodeMath')
    noise_sub.operation = 'SUBTRACT'
    noise_sub.inputs[1].default_value = 0.5
    noise_sub.location = (-420, -200)
    links.new(noise.outputs['Fac'], noise_sub.inputs[0])

    noise_mult = nodes.new('ShaderNodeMath')
    noise_mult.operation = 'MULTIPLY'
    noise_mult.location = (-260, -200)
    links.new(noise_sub.outputs['Value'], noise_mult.inputs[0])
    links.new(group_in.outputs['Strand Noise Jitter'], noise_mult.inputs[1])

    # Displaced UV Y
    uv_displaced = nodes.new('ShaderNodeMath')
    uv_displaced.operation = 'ADD'
    uv_displaced.location = (-260, 0)
    links.new(sep_xyz.outputs['Y'], uv_displaced.inputs[0])
    links.new(noise_mult.outputs['Value'], uv_displaced.inputs[1])

    # Distance to Band Position
    dist_sub = nodes.new('ShaderNodeMath')
    dist_sub.operation = 'SUBTRACT'
    dist_sub.location = (-100, 0)
    links.new(uv_displaced.outputs['Value'], dist_sub.inputs[0])
    links.new(group_in.outputs['Band Position'], dist_sub.inputs[1])

    dist_abs = nodes.new('ShaderNodeMath')
    dist_abs.operation = 'ABSOLUTE'
    dist_abs.location = (60, 0)
    links.new(dist_sub.outputs['Value'], dist_abs.inputs[0])

    # Smoothstep Map Range (1 at center, 0 at edge)
    map_band = nodes.new('ShaderNodeMapRange')
    map_band.clamp = True
    map_band.location = (220, 0)
    links.new(dist_abs.outputs['Value'], map_band.inputs['Value'])
    map_band.inputs['From Min'].default_value = 0.0
    links.new(group_in.outputs['Band Width'], map_band.inputs['From Max'])
    map_band.inputs['To Min'].default_value = 1.0
    map_band.inputs['To Max'].default_value = 0.0

    # Intensity mult
    mult_intensity = nodes.new('ShaderNodeMath')
    mult_intensity.operation = 'MULTIPLY'
    mult_intensity.location = (400, 0)
    links.new(map_band.outputs['Result'], mult_intensity.inputs[0])
    links.new(group_in.outputs['Intensity'], mult_intensity.inputs[1])

    # Color mult
    mix_col = nodes.new('ShaderNodeMix')
    mix_col.data_type = 'RGBA'
    mix_col.blend_type = 'MULTIPLY'
    mix_col.location = (560, 0)
    mix_col.inputs['Factor'].default_value = 1.0
    links.new(group_in.outputs['Highlight Color'], mix_col.inputs[6])
    links.new(mult_intensity.outputs['Value'], mix_col.inputs[7])

    emission = nodes.new('ShaderNodeEmission')
    emission.location = (620, 200)
    links.new(mix_col.outputs[2], emission.inputs['Color'])

    links.new(mix_col.outputs[2], group_out.inputs['Highlight Color'])
    links.new(mult_intensity.outputs['Value'], group_out.inputs['Highlight Factor'])
    links.new(emission.outputs['Emission'], group_out.inputs['Emission BSDF'])

    return tree


# =============================================================================
# 4. DaskToon Anime Face Shadow Node Group
# =============================================================================

def get_or_create_face_shadow_group():
    group_name = "DaskToon_Anime_FaceShadow"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'VECTOR'

    _add_socket(tree, "Head Forward Vector", 'INPUT', 'NodeSocketVector', (0.0, 1.0, 0.0))
    _add_socket(tree, "Head Right Vector", 'INPUT', 'NodeSocketVector', (1.0, 0.0, 0.0))
    _add_socket(tree, "Light Vector", 'INPUT', 'NodeSocketVector', (0.0, -1.0, 0.0))
    _add_socket(tree, "Shadow Threshold", 'INPUT', 'NodeSocketFloat', 0.0, -1.0, 1.0)
    _add_socket(tree, "Shadow Softness", 'INPUT', 'NodeSocketFloat', 0.04, 0.001, 0.5)

    _add_socket(tree, "Face Shadow Mask", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Light Angle", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Side Factor", 'OUTPUT', 'NodeSocketFloat')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-600, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (600, 0)

    # Dot product light vs forward
    dot_fwd = nodes.new('ShaderNodeVectorMath')
    dot_fwd.operation = 'DOT_PRODUCT'
    dot_fwd.location = (-380, 100)
    links.new(group_in.outputs['Light Vector'], dot_fwd.inputs[0])
    links.new(group_in.outputs['Head Forward Vector'], dot_fwd.inputs[1])

    # Dot product light vs right
    dot_right = nodes.new('ShaderNodeVectorMath')
    dot_right.operation = 'DOT_PRODUCT'
    dot_right.location = (-380, -100)
    links.new(group_in.outputs['Light Vector'], dot_right.inputs[0])
    links.new(group_in.outputs['Head Right Vector'], dot_right.inputs[1])

    # Smoothstep for clean anime facial shadow boundary
    sub_soft = nodes.new('ShaderNodeMath')
    sub_soft.operation = 'SUBTRACT'
    sub_soft.location = (-180, 200)
    links.new(group_in.outputs['Shadow Threshold'], sub_soft.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], sub_soft.inputs[1])

    add_soft = nodes.new('ShaderNodeMath')
    add_soft.operation = 'ADD'
    add_soft.location = (-180, 60)
    links.new(group_in.outputs['Shadow Threshold'], add_soft.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], add_soft.inputs[1])

    map_shadow = nodes.new('ShaderNodeMapRange')
    map_shadow.clamp = True
    map_shadow.location = (40, 100)
    links.new(dot_fwd.outputs['Value'], map_shadow.inputs['Value'])
    links.new(sub_soft.outputs['Value'], map_shadow.inputs['From Min'])
    links.new(add_soft.outputs['Value'], map_shadow.inputs['From Max'])

    links.new(map_shadow.outputs['Result'], group_out.inputs['Face Shadow Mask'])
    links.new(dot_fwd.outputs['Value'], group_out.inputs['Light Angle'])
    links.new(dot_right.outputs['Value'], group_out.inputs['Side Factor'])

    return tree


# =============================================================================
# 5. DaskToon Anime Manga Screentone Node Group
# =============================================================================

def get_or_create_screentone_group():
    group_name = "DaskToon_Anime_MangaScreentone"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'TEXTURE'

    _add_socket(tree, "Shading Factor", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)
    _add_socket(tree, "Dot Scale", 'INPUT', 'NodeSocketFloat', 45.0, 1.0, 500.0)
    _add_socket(tree, "Dot Angle", 'INPUT', 'NodeSocketFloat', 0.785, -3.14, 3.14)
    _add_socket(tree, "Dot Sharpness", 'INPUT', 'NodeSocketFloat', 0.05, 0.001, 1.0)
    _add_socket(tree, "Ink Color", 'INPUT', 'NodeSocketColor', (0.05, 0.05, 0.08, 1.0))
    _add_socket(tree, "Paper Color", 'INPUT', 'NodeSocketColor', (0.96, 0.96, 0.96, 1.0))

    _add_socket(tree, "Screentone Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Dot Factor", 'OUTPUT', 'NodeSocketFloat')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-700, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (700, 0)

    # Window Coordinates for true 2D Screen-space manga screentone
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-700, -200)

    # Rotate coordinates
    v_rot = nodes.new('ShaderNodeVectorRotate')
    v_rot.rotation_type = 'Z_AXIS'
    v_rot.location = (-500, -200)
    links.new(tex_coord.outputs['Window'], v_rot.inputs['Vector'])
    links.new(group_in.outputs['Dot Angle'], v_rot.inputs['Angle'])

    # Scale coordinates
    v_scale = nodes.new('ShaderNodeVectorMath')
    v_scale.operation = 'MULTIPLY'
    v_scale.location = (-320, -200)
    links.new(v_rot.outputs['Vector'], v_scale.inputs[0])
    links.new(group_in.outputs['Dot Scale'], v_scale.inputs[1])

    # Periodic dot pattern via Cosine (cos(x)*cos(y))
    sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
    sep_xyz.location = (-160, -200)
    links.new(v_scale.outputs['Vector'], sep_xyz.inputs['Vector'])

    cos_x = nodes.new('ShaderNodeMath')
    cos_x.operation = 'COSINE'
    cos_x.location = (20, -120)
    links.new(sep_xyz.outputs['X'], cos_x.inputs[0])

    cos_y = nodes.new('ShaderNodeMath')
    cos_y.operation = 'COSINE'
    cos_y.location = (20, -280)
    links.new(sep_xyz.outputs['Y'], cos_y.inputs[0])

    mult_dot = nodes.new('ShaderNodeMath')
    mult_dot.operation = 'MULTIPLY'
    mult_dot.location = (180, -200)
    links.new(cos_x.outputs['Value'], mult_dot.inputs[0])
    links.new(cos_y.outputs['Value'], mult_dot.inputs[1])

    # Normalize dot from [-1, 1] to [0, 1]
    norm_dot = nodes.new('ShaderNodeMapRange')
    norm_dot.clamp = True
    norm_dot.inputs['From Min'].default_value = -1.0
    norm_dot.inputs['From Max'].default_value = 1.0
    norm_dot.inputs['To Min'].default_value = 0.0
    norm_dot.inputs['To Max'].default_value = 1.0
    norm_dot.location = (320, -200)
    links.new(mult_dot.outputs['Value'], norm_dot.inputs['Value'])

    # Threshold with Shading Factor
    map_thresh = nodes.new('ShaderNodeMapRange')
    map_thresh.clamp = True
    map_thresh.location = (460, 0)
    links.new(norm_dot.outputs['Result'], map_thresh.inputs['Value'])
    links.new(group_in.outputs['Shading Factor'], map_thresh.inputs['From Min'])
    links.new(group_in.outputs['Dot Sharpness'], map_thresh.inputs['To Max'])

    # Mix Ink and Paper
    mix_col = nodes.new('ShaderNodeMix')
    mix_col.data_type = 'RGBA'
    mix_col.location = (540, 150)
    links.new(map_thresh.outputs['Result'], mix_col.inputs['Factor'])
    links.new(group_in.outputs['Paper Color'], mix_col.inputs[6])
    links.new(group_in.outputs['Ink Color'], mix_col.inputs[7])

    links.new(mix_col.outputs[2], group_out.inputs['Screentone Color'])
    links.new(map_thresh.outputs['Result'], group_out.inputs['Dot Factor'])

    return tree


# =============================================================================
# 6. DaskToon Anime Warm/Cool Color Grade Node Group
# =============================================================================

def get_or_create_warm_cool_group():
    group_name = "DaskToon_Anime_WarmCoolGrade"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'COLOR'

    _add_socket(tree, "Base Color", 'INPUT', 'NodeSocketColor', (0.92, 0.84, 0.8, 1.0))
    _add_socket(tree, "Lit Warm Tint", 'INPUT', 'NodeSocketColor', (1.05, 1.0, 0.92, 1.0))
    _add_socket(tree, "Shadow Cool Tint", 'INPUT', 'NodeSocketColor', (0.82, 0.86, 1.08, 1.0))
    _add_socket(tree, "Penumbra Saturation", 'INPUT', 'NodeSocketFloat', 1.25, 1.0, 3.0)
    _add_socket(tree, "Shadow Factor", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)

    _add_socket(tree, "Graded Color", 'OUTPUT', 'NodeSocketColor')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-600, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (600, 0)

    # Tint Base Color with Warm and Cool
    mix_warm = nodes.new('ShaderNodeMix')
    mix_warm.data_type = 'RGBA'
    mix_warm.blend_type = 'MULTIPLY'
    mix_warm.location = (-380, 100)
    mix_warm.inputs['Factor'].default_value = 1.0
    links.new(group_in.outputs['Base Color'], mix_warm.inputs[6])
    links.new(group_in.outputs['Lit Warm Tint'], mix_warm.inputs[7])

    mix_cool = nodes.new('ShaderNodeMix')
    mix_cool.data_type = 'RGBA'
    mix_cool.blend_type = 'MULTIPLY'
    mix_cool.location = (-380, -100)
    mix_cool.inputs['Factor'].default_value = 1.0
    links.new(group_in.outputs['Base Color'], mix_cool.inputs[6])
    links.new(group_in.outputs['Shadow Cool Tint'], mix_cool.inputs[7])

    # Mix according to Shadow Factor
    mix_graded = nodes.new('ShaderNodeMix')
    mix_graded.data_type = 'RGBA'
    mix_graded.location = (-160, 0)
    links.new(group_in.outputs['Shadow Factor'], mix_graded.inputs['Factor'])
    links.new(mix_cool.outputs[2], mix_graded.inputs[6])
    links.new(mix_warm.outputs[2], mix_graded.inputs[7])

    # Penumbra saturation boost
    hsv = nodes.new('ShaderNodeHueSaturation')
    hsv.location = (60, 0)
    links.new(group_in.outputs['Penumbra Saturation'], hsv.inputs['Saturation'])
    links.new(mix_graded.outputs[2], hsv.inputs['Color'])

    # Penumbra Bell Curve factor: 1.0 - 4.0 * (ShadowFactor - 0.5)^2
    sub_half = nodes.new('ShaderNodeMath')
    sub_half.operation = 'SUBTRACT'
    sub_half.inputs[1].default_value = 0.5
    sub_half.location = (-160, -240)
    links.new(group_in.outputs['Shadow Factor'], sub_half.inputs[0])

    sq_half = nodes.new('ShaderNodeMath')
    sq_half.operation = 'MULTIPLY'
    sq_half.location = (20, -240)
    links.new(sub_half.outputs['Value'], sq_half.inputs[0])
    links.new(sub_half.outputs['Value'], sq_half.inputs[1])

    mult_four = nodes.new('ShaderNodeMath')
    mult_four.operation = 'MULTIPLY'
    mult_four.inputs[1].default_value = 4.0
    mult_four.location = (180, -240)
    links.new(sq_half.outputs['Value'], mult_four.inputs[0])

    penumbra_mask = nodes.new('ShaderNodeMath')
    penumbra_mask.operation = 'SUBTRACT'
    penumbra_mask.inputs[0].default_value = 1.0
    penumbra_mask.use_clamp = True
    penumbra_mask.location = (320, -240)
    links.new(mult_four.outputs['Value'], penumbra_mask.inputs[1])

    mix_final = nodes.new('ShaderNodeMix')
    mix_final.data_type = 'RGBA'
    mix_final.location = (420, 0)
    links.new(penumbra_mask.outputs['Value'], mix_final.inputs['Factor'])
    links.new(mix_graded.outputs[2], mix_final.inputs[6])
    links.new(hsv.outputs['Color'], mix_final.inputs[7])

    links.new(mix_final.outputs[2], group_out.inputs['Graded Color'])

    return tree


# =============================================================================
# 7. DaskToon Anime Eye Shader Node Group
# =============================================================================

def get_or_create_eye_shader_group():
    group_name = "DaskToon_Anime_EyeShader"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'COLOR'

    _add_socket(tree, "Iris Color", 'INPUT', 'NodeSocketColor', (0.15, 0.45, 0.85, 1.0))
    _add_socket(tree, "Pupil Color", 'INPUT', 'NodeSocketColor', (0.02, 0.05, 0.12, 1.0))
    _add_socket(tree, "Bottom Glow Color", 'INPUT', 'NodeSocketColor', (0.35, 0.85, 1.0, 1.0))
    _add_socket(tree, "Bottom Glow Power", 'INPUT', 'NodeSocketFloat', 1.5, 0.0, 5.0)
    _add_socket(tree, "Top Shadow Tint", 'INPUT', 'NodeSocketColor', (0.08, 0.12, 0.25, 1.0))
    _add_socket(tree, "Sparkle Color", 'INPUT', 'NodeSocketColor', (1.0, 1.0, 1.0, 1.0))
    _add_socket(tree, "UV Vector", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))

    _add_socket(tree, "Eye Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Emission BSDF", 'OUTPUT', 'NodeSocketShader')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-800, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (800, 0)

    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-800, -200)

    # Separate UV
    sep_uv = nodes.new('ShaderNodeSeparateXYZ')
    sep_uv.location = (-600, 0)
    links.new(group_in.outputs['UV Vector'], sep_uv.inputs['Vector'])

    # Radial pupil distance: length(UV - (0.5, 0.5))
    sub_center = nodes.new('ShaderNodeVectorMath')
    sub_center.operation = 'SUBTRACT'
    sub_center.inputs[1].default_value = (0.5, 0.5, 0.0)
    sub_center.location = (-600, -200)
    links.new(group_in.outputs['UV Vector'], sub_center.inputs[0])

    dist_center = nodes.new('ShaderNodeVectorMath')
    dist_center.operation = 'LENGTH'
    dist_center.location = (-420, -200)
    links.new(sub_center.outputs['Vector'], dist_center.inputs[0])

    # Pupil Mask: smoothstep(0.18, 0.22, length)
    pupil_map = nodes.new('ShaderNodeMapRange')
    pupil_map.clamp = True
    pupil_map.inputs['From Min'].default_value = 0.18
    pupil_map.inputs['From Max'].default_value = 0.22
    pupil_map.location = (-240, -200)
    links.new(dist_center.outputs['Value'], pupil_map.inputs['Value'])

    # Mix Iris and Pupil
    mix_iris_pupil = nodes.new('ShaderNodeMix')
    mix_iris_pupil.data_type = 'RGBA'
    mix_iris_pupil.location = (-60, 0)
    links.new(pupil_map.outputs['Result'], mix_iris_pupil.inputs['Factor'])
    links.new(group_in.outputs['Pupil Color'], mix_iris_pupil.inputs[6])
    links.new(group_in.outputs['Iris Color'], mix_iris_pupil.inputs[7])

    # Bottom Crescent Glow: UV.Y inverted and boosted
    inv_y = nodes.new('ShaderNodeMath')
    inv_y.operation = 'SUBTRACT'
    inv_y.inputs[0].default_value = 1.0
    inv_y.location = (-420, 200)
    links.new(sep_uv.outputs['Y'], inv_y.inputs[1])

    pow_glow = nodes.new('ShaderNodeMath')
    pow_glow.operation = 'POWER'
    pow_glow.inputs[1].default_value = 2.5
    pow_glow.location = (-240, 200)
    links.new(inv_y.outputs['Value'], pow_glow.inputs[0])

    mult_glow = nodes.new('ShaderNodeMath')
    mult_glow.operation = 'MULTIPLY'
    mult_glow.location = (-80, 200)
    links.new(pow_glow.outputs['Value'], mult_glow.inputs[0])
    links.new(group_in.outputs['Bottom Glow Power'], mult_glow.inputs[1])

    mix_glow = nodes.new('ShaderNodeMix')
    mix_glow.data_type = 'RGBA'
    mix_glow.blend_type = 'ADD'
    mix_glow.location = (120, 0)
    links.new(mult_glow.outputs['Value'], mix_glow.inputs['Factor'])
    links.new(mix_iris_pupil.outputs[2], mix_glow.inputs[6])
    links.new(group_in.outputs['Bottom Glow Color'], mix_glow.inputs[7])

    # Top Shadow
    top_shadow_map = nodes.new('ShaderNodeMapRange')
    top_shadow_map.clamp = True
    top_shadow_map.inputs['From Min'].default_value = 0.4
    top_shadow_map.inputs['From Max'].default_value = 0.9
    top_shadow_map.location = (120, 240)
    links.new(sep_uv.outputs['Y'], top_shadow_map.inputs['Value'])

    mix_top_shadow = nodes.new('ShaderNodeMix')
    mix_top_shadow.data_type = 'RGBA'
    mix_top_shadow.blend_type = 'MULTIPLY'
    mix_top_shadow.location = (320, 0)
    links.new(top_shadow_map.outputs['Result'], mix_top_shadow.inputs['Factor'])
    links.new(mix_glow.outputs[2], mix_top_shadow.inputs[6])
    links.new(group_in.outputs['Top Shadow Tint'], mix_top_shadow.inputs[7])

    # Main Sparkle Highlight (at ~ (0.65, 0.65))
    sparkle_sub = nodes.new('ShaderNodeVectorMath')
    sparkle_sub.operation = 'SUBTRACT'
    sparkle_sub.inputs[1].default_value = (0.62, 0.65, 0.0)
    sparkle_sub.location = (120, -200)
    links.new(group_in.outputs['UV Vector'], sparkle_sub.inputs[0])

    sparkle_dist = nodes.new('ShaderNodeVectorMath')
    sparkle_dist.operation = 'LENGTH'
    sparkle_dist.location = (280, -200)
    links.new(sparkle_sub.outputs['Vector'], sparkle_dist.inputs[0])

    sparkle_map = nodes.new('ShaderNodeMapRange')
    sparkle_map.clamp = True
    sparkle_map.inputs['From Min'].default_value = 0.07
    sparkle_map.inputs['From Max'].default_value = 0.08
    sparkle_map.inputs['To Min'].default_value = 1.0
    sparkle_map.inputs['To Max'].default_value = 0.0
    sparkle_map.location = (440, -200)
    links.new(sparkle_dist.outputs['Value'], sparkle_map.inputs['Value'])

    mix_sparkle = nodes.new('ShaderNodeMix')
    mix_sparkle.data_type = 'RGBA'
    mix_sparkle.blend_type = 'ADD'
    mix_sparkle.location = (520, 0)
    links.new(sparkle_map.outputs['Result'], mix_sparkle.inputs['Factor'])
    links.new(mix_top_shadow.outputs[2], mix_sparkle.inputs[6])
    links.new(group_in.outputs['Sparkle Color'], mix_sparkle.inputs[7])

    emission = nodes.new('ShaderNodeEmission')
    emission.location = (620, 180)
    links.new(mix_sparkle.outputs[2], emission.inputs['Color'])

    links.new(mix_sparkle.outputs[2], group_out.inputs['Eye Color'])
    links.new(emission.outputs['Emission'], group_out.inputs['Emission BSDF'])

    return tree


# =============================================================================
# 8. DaskToon Anime Normal Softener Node Group
# =============================================================================

def get_or_create_normal_softener_group():
    group_name = "DaskToon_Anime_NormalSoftener"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'VECTOR'

    _add_socket(tree, "Mesh Normal", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))
    _add_socket(tree, "Flatten Amount", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)
    _add_socket(tree, "Camera Bias", 'INPUT', 'NodeSocketFloat', 0.25, 0.0, 1.0)

    _add_socket(tree, "Modified Normal", 'OUTPUT', 'NodeSocketVector')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-600, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (600, 0)

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-600, -200)

    # Flat Forward Vector (0, 0, 1)
    mix_flat = nodes.new('ShaderNodeMix')
    mix_flat.data_type = 'VECTOR'
    mix_flat.location = (-360, 0)
    mix_flat.inputs[5].default_value = (0.0, 0.0, 1.0)
    links.new(group_in.outputs['Flatten Amount'], mix_flat.inputs['Factor'])
    links.new(group_in.outputs['Mesh Normal'], mix_flat.inputs[4])

    # Mix with Camera Incoming
    mix_cam = nodes.new('ShaderNodeMix')
    mix_cam.data_type = 'VECTOR'
    mix_cam.location = (-160, 0)
    links.new(group_in.outputs['Camera Bias'], mix_cam.inputs['Factor'])
    links.new(mix_flat.outputs[1], mix_cam.inputs[4])
    links.new(geom.outputs['Incoming'], mix_cam.inputs[5])

    # Normalize
    v_norm = nodes.new('ShaderNodeVectorMath')
    v_norm.operation = 'NORMALIZE'
    v_norm.location = (80, 0)
    links.new(mix_cam.outputs[1], v_norm.inputs[0])

    links.new(v_norm.outputs['Vector'], group_out.inputs['Modified Normal'])

    return tree


# =============================================================================
# 9. DaskToon Anime Character BSDF (All-in-One Character Uber Shader)
# =============================================================================
# 9. Dask Shader BSDF (All-in-One Anime & Character Uber Shader)
# =============================================================================

def get_or_create_dask_shader_group():
    group_name = "DaskToon_DaskShader_BSDF"
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    tree = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    tree.color_tag = 'SHADER'

    # Interface Sockets
    _add_socket(tree, "Normal", 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0))
    _add_socket(tree, "Strength", 'INPUT', 'NodeSocketFloat', 1.0, 0.0, 10.0)

    # COLOR Panel
    _add_socket(tree, "skin_color", 'INPUT', 'NodeSocketColor', (0.95, 0.85, 0.80, 1.0))
    _add_socket(tree, "Shadow Color", 'INPUT', 'NodeSocketColor', (0.65, 0.50, 0.55, 1.0))
    _add_socket(tree, "Shadow Threshold", 'INPUT', 'NodeSocketFloat', 0.48, 0.0, 1.0)
    _add_socket(tree, "Shadow Softness", 'INPUT', 'NodeSocketFloat', 0.02, 0.001, 0.5)
    _add_socket(tree, "Alpha", 'INPUT', 'NodeSocketFloat', 1.0, 0.0, 1.0)
    _add_socket(tree, "AO_color", 'INPUT', 'NodeSocketColor', (0.35, 0.30, 0.35, 1.0))
    _add_socket(tree, "AO Strength", 'INPUT', 'NodeSocketFloat', 0.5, 0.0, 1.0)

    # HAIR / HIGHLIGHT Panel
    _add_socket(tree, "Hair Ring Color", 'INPUT', 'NodeSocketColor', (1.0, 0.95, 0.85, 1.0))
    _add_socket(tree, "Hair Ring Position", 'INPUT', 'NodeSocketFloat', 0.565, 0.0, 1.0)
    _add_socket(tree, "Hair Ring Width", 'INPUT', 'NodeSocketFloat', 0.08, 0.001, 0.5)
    _add_socket(tree, "Strand Noise Scale", 'INPUT', 'NodeSocketFloat', 35.0, 1.0, 200.0)
    _add_socket(tree, "Strand Noise Jitter", 'INPUT', 'NodeSocketFloat', 0.12, 0.0, 1.0)

    # OUTLINE Panel
    _add_socket(tree, "Outline Darkening", 'INPUT', 'NodeSocketFloat', -0.30, -1.0, 0.0)
    _add_socket(tree, "Brightness", 'INPUT', 'NodeSocketFloat', 0.0, -1.0, 1.0)
    _add_socket(tree, "Contrast", 'INPUT', 'NodeSocketFloat', 0.0, -1.0, 1.0)

    # SWITCH Panel
    _add_socket(tree, "hair", 'INPUT', 'NodeSocketBool', True)
    _add_socket(tree, "Ouline", 'INPUT', 'NodeSocketBool', False)
    _add_socket(tree, "AO", 'INPUT', 'NodeSocketBool', True)

    # Outputs
    _add_socket(tree, "output", 'OUTPUT', 'NodeSocketShader')
    _add_socket(tree, "Color", 'OUTPUT', 'NodeSocketColor')
    _add_socket(tree, "Shadow Mask", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Highlight Mask", 'OUTPUT', 'NodeSocketFloat')
    _add_socket(tree, "Alpha", 'OUTPUT', 'NodeSocketFloat')

    nodes = tree.nodes
    links = tree.links

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1200, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (1400, 0)

    # -------------------------------------------------------------
    # 1. Skin Frame: Diffuse light capture + 2-tone Cel Shading
    # -------------------------------------------------------------
    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = (-950, 400)
    links.new(group_in.outputs['Normal'], diffuse.inputs['Normal'])

    s2rgb = nodes.new('ShaderNodeShaderToRGB')
    s2rgb.location = (-750, 400)
    links.new(diffuse.outputs['BSDF'], s2rgb.inputs['Shader'])

    rgb_bw = nodes.new('ShaderNodeRGBToBW')
    rgb_bw.location = (-550, 400)
    links.new(s2rgb.outputs['Color'], rgb_bw.inputs['Color'])

    # Smoothstep Shadow Map Range
    sub_min = nodes.new('ShaderNodeMath')
    sub_min.operation = 'SUBTRACT'
    sub_min.location = (-550, 240)
    links.new(group_in.outputs['Shadow Threshold'], sub_min.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], sub_min.inputs[1])

    add_max = nodes.new('ShaderNodeMath')
    add_max.operation = 'ADD'
    add_max.location = (-550, 100)
    links.new(group_in.outputs['Shadow Threshold'], add_max.inputs[0])
    links.new(group_in.outputs['Shadow Softness'], add_max.inputs[1])

    map_s = nodes.new('ShaderNodeMapRange')
    map_s.clamp = True
    map_s.interpolation_type = 'SMOOTHSTEP'
    map_s.location = (-350, 400)
    links.new(rgb_bw.outputs[0], map_s.inputs[0])
    links.new(sub_min.outputs[0], map_s.inputs[1])
    links.new(add_max.outputs[0], map_s.inputs[2])
    map_s.inputs[3].default_value = 0.0
    map_s.inputs[4].default_value = 1.0

    # Brightness / Contrast on skin_color
    bc_skin = nodes.new('ShaderNodeBrightContrast')
    bc_skin.location = (-350, 200)
    links.new(group_in.outputs['skin_color'], bc_skin.inputs['Color'])
    links.new(group_in.outputs['Brightness'], bc_skin.inputs['Bright'])
    links.new(group_in.outputs['Contrast'], bc_skin.inputs['Contrast'])

    # Normalized Light/World Tint (extracts green environment/sun color without smooth gradient)
    val_max = nodes.new('ShaderNodeMath')
    val_max.operation = 'MAXIMUM'
    val_max.inputs[1].default_value = 0.05
    val_max.location = (-550, -40)
    links.new(rgb_bw.outputs['Val'], val_max.inputs[0])

    div_light = nodes.new('ShaderNodeVectorMath')
    div_light.operation = 'DIVIDE'
    div_light.location = (-350, -40)
    links.new(s2rgb.outputs['Color'], div_light.inputs[0])
    links.new(val_max.outputs['Value'], div_light.inputs[1])

    # Mix Shadow Color and Skin Color
    mix_skin = nodes.new('ShaderNodeMix')
    mix_skin.data_type = 'RGBA'
    mix_skin.location = (-150, 400)
    links.new(map_s.outputs['Result'], mix_skin.inputs['Factor'])
    links.new(group_in.outputs['Shadow Color'], mix_skin.inputs[6])
    links.new(bc_skin.outputs['Color'], mix_skin.inputs[7])

    # -------------------------------------------------------------
    # 2. hair_skin Frame: Anisotropic Angel Ring highlight
    # -------------------------------------------------------------
    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-950, -200)

    sep_n = nodes.new('ShaderNodeSeparateXYZ')
    sep_n.location = (-750, -200)
    links.new(geom.outputs['Normal'], sep_n.inputs['Vector'])

    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-950, -400)

    sep_uv = nodes.new('ShaderNodeSeparateXYZ')
    sep_uv.location = (-750, -400)
    links.new(tex_coord.outputs['UV'], sep_uv.inputs['Vector'])

    noise = nodes.new('ShaderNodeTexNoise')
    noise.location = (-550, -400)
    links.new(group_in.outputs['Strand Noise Scale'], noise.inputs['Scale'])
    links.new(tex_coord.outputs['UV'], noise.inputs['Vector'])

    noise_bc = nodes.new('ShaderNodeBrightContrast')
    noise_bc.inputs['Bright'].default_value = 0.900
    noise_bc.inputs['Contrast'].default_value = 10.000
    noise_bc.location = (-350, -400)
    links.new(noise.outputs['Fac'], noise_bc.inputs['Color'])

    # Distance to Hair Ring Position
    sub_pos = nodes.new('ShaderNodeMath')
    sub_pos.operation = 'SUBTRACT'
    sub_pos.location = (-550, -200)
    links.new(sep_n.outputs['Z'], sub_pos.inputs[0])
    links.new(group_in.outputs['Hair Ring Position'], sub_pos.inputs[1])

    abs_pos = nodes.new('ShaderNodeMath')
    abs_pos.operation = 'ABSOLUTE'
    abs_pos.location = (-350, -200)
    links.new(sub_pos.outputs['Value'], abs_pos.inputs[0])

    map_ring = nodes.new('ShaderNodeMapRange')
    map_ring.clamp = True
    map_ring.location = (-150, -200)
    links.new(abs_pos.outputs['Value'], map_ring.inputs['Value'])
    map_ring.inputs['From Min'].default_value = 0.0
    links.new(group_in.outputs['Hair Ring Width'], map_ring.inputs['From Max'])
    map_ring.inputs['To Min'].default_value = 1.0
    map_ring.inputs['To Max'].default_value = 0.0

    # Multiply with noise jitter
    mult_ring = nodes.new('ShaderNodeMath')
    mult_ring.operation = 'MULTIPLY'
    mult_ring.location = (50, -200)
    links.new(map_ring.outputs['Result'], mult_ring.inputs[0])
    links.new(noise_bc.outputs['Color'], mult_ring.inputs[1])

    # Lighten hair onto skin
    mix_hair = nodes.new('ShaderNodeMix')
    mix_hair.data_type = 'RGBA'
    mix_hair.blend_type = 'LIGHTEN'
    mix_hair.location = (250, -200)
    mix_hair.inputs['Factor'].default_value = 1.0
    links.new(mix_skin.outputs[2], mix_hair.inputs[6])
    links.new(group_in.outputs['Hair Ring Color'], mix_hair.inputs[7])

    # -------------------------------------------------------------
    # 3. outline Frame: Brightness & Contrast outline tone
    # -------------------------------------------------------------
    bc_outline = nodes.new('ShaderNodeBrightContrast')
    bc_outline.inputs['Bright'].default_value = -0.300
    bc_outline.inputs['Contrast'].default_value = -0.400
    bc_outline.location = (50, 500)
    links.new(mix_skin.outputs[2], bc_outline.inputs['Color'])

    # -------------------------------------------------------------
    # 4. switch Frame: hair, Ouline, AO switches
    # -------------------------------------------------------------
    # hair switch
    switch_hair = nodes.new('ShaderNodeMix')
    switch_hair.data_type = 'RGBA'
    switch_hair.location = (450, 400)
    links.new(group_in.outputs['hair'], switch_hair.inputs['Factor'])
    links.new(mix_skin.outputs[2], switch_hair.inputs[6])
    links.new(mix_hair.outputs[2], switch_hair.inputs[7])

    # outline switch
    switch_outline = nodes.new('ShaderNodeMix')
    switch_outline.data_type = 'RGBA'
    switch_outline.location = (650, 400)
    links.new(group_in.outputs['Ouline'], switch_outline.inputs['Factor'])
    links.new(switch_hair.outputs[2], switch_outline.inputs[6])
    links.new(bc_outline.outputs['Color'], switch_outline.inputs[7])

    # -------------------------------------------------------------
    # 5. AO Frame: Ambient Occlusion blend
    # -------------------------------------------------------------
    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 32
    ao.inputs['Distance'].default_value = 1.0
    ao.location = (250, -500)
    links.new(group_in.outputs['Normal'], ao.inputs['Normal'])

    inv_ao = nodes.new('ShaderNodeInvert')
    inv_ao.inputs['Fac'].default_value = 1.0
    inv_ao.location = (450, -500)
    links.new(ao.outputs['Color'], inv_ao.inputs['Color'])

    # Blend AO with AO_color
    mix_ao_col = nodes.new('ShaderNodeMix')
    mix_ao_col.data_type = 'RGBA'
    mix_ao_col.blend_type = 'MULTIPLY'
    mix_ao_col.location = (650, -500)
    links.new(group_in.outputs['AO'], mix_ao_col.inputs['Factor'])
    links.new(switch_outline.outputs[2], mix_ao_col.inputs[6])
    links.new(group_in.outputs['AO_color'], mix_ao_col.inputs[7])

    # -------------------------------------------------------------
    # 6. Final Emission & Transparent BSDF with Scene Light & Environment Tint
    # -------------------------------------------------------------
    mix_light = nodes.new('ShaderNodeMix')
    mix_light.data_type = 'RGBA'
    mix_light.blend_type = 'MULTIPLY'
    mix_light.inputs['Factor'].default_value = 1.0
    mix_light.location = (850, 200)
    links.new(mix_ao_col.outputs[2], mix_light.inputs[6])
    links.new(div_light.outputs['Vector'], mix_light.inputs[7])

    emission = nodes.new('ShaderNodeEmission')
    emission.location = (1050, 200)
    links.new(mix_light.outputs[2], emission.inputs['Color'])
    links.new(group_in.outputs['Strength'], emission.inputs['Strength'])

    transparent = nodes.new('ShaderNodeBsdfTransparent')
    transparent.location = (1050, 40)

    mix_shader = nodes.new('ShaderNodeMixShader')
    mix_shader.location = (1250, 200)
    links.new(group_in.outputs['Alpha'], mix_shader.inputs['Fac'])
    links.new(transparent.outputs['BSDF'], mix_shader.inputs[1])
    links.new(emission.outputs['Emission'], mix_shader.inputs[2])

    # Outputs
    links.new(mix_shader.outputs['Shader'], group_out.inputs['output'])
    links.new(mix_light.outputs[2], group_out.inputs['Color'])
    links.new(map_s.outputs['Result'], group_out.inputs['Shadow Mask'])
    links.new(mult_ring.outputs['Value'], group_out.inputs['Highlight Mask'])
    links.new(group_in.outputs['Alpha'], group_out.inputs['Alpha'])

    return tree


get_or_create_character_bsdf_group = get_or_create_dask_shader_group


# =============================================================================
# Registry Map of all Anime Nodes
# =============================================================================

ANIME_NODE_GENERATORS = {
    'DASK_SHADER_BSDF': (
        "Dask Shader BSDF",
        "All-in-One Anime Character Uber Shader (Skin Cel, Hair Angel Ring, AO, Outline & Switches)",
        get_or_create_dask_shader_group
    ),
    'CHARACTER_BSDF': (
        "Dask Shader BSDF",
        "All-in-One Anime Character Uber Shader (Skin Cel, Hair Angel Ring, AO, Outline & Switches)",
        get_or_create_dask_shader_group
    ),
    'CEL_SHADER': (
        "Anime Cel Shader",
        "DaskToon Multi-Tone Cel-Shading with 2-level shadow, specular & rim",
        get_or_create_cel_shader_group
    ),
    'RIM_LIGHT': (
        "Anime Rim Light",
        "Crisp & Feathered Anime Backlight / Fresnel Rim generator",
        get_or_create_rim_light_group
    ),
    'ANGEL_RING': (
        "Anime Hair Highlight",
        "Signature Anime Angel Ring anisotropic hair highlight with strand jitter",
        get_or_create_angel_ring_group
    ),
    'FACE_SHADOW': (
        "Anime Face Shadow",
        "Angle & Directional anime face shadow mapper for smooth facial shading",
        get_or_create_face_shadow_group
    ),
    'MANGA_SCREENTONE': (
        "Anime Manga Screentone",
        "Screen-space comic halftone dots & manga line screentone pattern",
        get_or_create_screentone_group
    ),
    'WARM_COOL': (
        "Anime Warm/Cool Grade",
        "Warm lit highlight and cool saturated shadow transition color tint",
        get_or_create_warm_cool_group
    ),
    'EYE_SHADER': (
        "Anime Eye Shader",
        "Multi-layered anime iris, pupil, top shadow, bottom glow & sparkle highlights",
        get_or_create_eye_shader_group
    ),
    'NORMAL_SOFTENER': (
        "Anime Normal Softener",
        "Smooths/flattens face normals to eliminate jagged 3D polygon shadow terminator",
        get_or_create_normal_softener_group
    ),
}


ANIME_NATIVE_NODES = {
    # DaskToon Anime Suite
    'CHARACTER': ("Dask Shader BSDF", "ShaderNodeAnimeCharacter", "ARMATURE_DATA"),
    'CEL_SHADER': ("Anime Cel BSDF", "ShaderNodeAnimeCel", "MATERIAL"),
    'RIM_LIGHT': ("Anime Rim Light", "ShaderNodeAnimeRim", "LIGHT_SUN"),
    'ANGEL_RING': ("Anime Hair Angel Ring", "ShaderNodeAnimeAngelRing", "STRANDS"),
    'FACE_SHADOW': ("Anime Face Shadow", "ShaderNodeAnimeFaceShadow", "ORIENTATION_VIEW"),
    'MANGA_SCREENTONE': ("Manga Comic Screentone", "ShaderNodeAnimeMangaScreentone", "TEXTURE"),
    'WARM_COOL': ("Anime Warm/Cool Grade", "ShaderNodeAnimeWarmCoolGrade", "COLOR"),
    'EYE_SHADER': ("Anime Eye Shader", "ShaderNodeAnimeEye", "HIDE_OFF"),

    # Goo Engine Core Suite
    'SHADER_INFO': ("Shader Info", "ShaderNodeShaderInfo", "NODE_CORNER"),
    'SCREENSPACE_INFO': ("Screenspace Info", "ShaderNodeScreenspaceInfo", "WINDOW"),
    'SET_DEPTH': ("Set Depth", "ShaderNodeSetDepth", "MOD_EDGESPLIT"),
    'CURVATURE': ("Curvature", "ShaderNodeCurvature", "EDGESEL"),
    'LIGHT_INFO': ("Light Info", "ShaderNodeLightInfo", "LIGHT_DATA"),
    'OKLAB_COLOR_RAMP': ("OKLab Color Ramp", "ShaderNodeOKLabColorRamp", "COLOR"),

    # Goo Engine SDF Suite
    'SDF_PRIMITIVE': ("SDF Primitive", "ShaderNodeSDFPrimitive", "MESH_ICOSPHERE"),
    'SDF_OP': ("SDF Op", "ShaderNodeSDFOp", "MOD_BOOLEAN"),
    'SDF_VECTOR_OP': ("SDF Vector Op", "ShaderNodeSDFVectorOp", "ORIENTATION_GIMBAL"),
    'SDF_NOISE': ("SDF Noise", "ShaderNodeSDFNoise", "TEXTURE"),

    # Goo Engine Procedural Texture Suite
    'TEX_HEXAGON': ("Hexagon Texture", "ShaderNodeTexHexagon", "GRID"),
    'TWIRL': ("Twirl", "ShaderNodeTwirl", "FORCE_VORTEX"),
    'WATER_RIPPLES': ("Water Ripples", "ShaderNodeWaterRipples", "MOD_WAVE"),

    # DaskToon Modular Sub-Nodes
    'DASK_CEL': ("Dask Cel Module", "ShaderNodeDaskCel", "BRUSH_DATA"),
    'DASK_AMBIENT': ("Dask Ambient Module", "ShaderNodeDaskAmbient", "WORLD"),
    'DASK_LIGHT': ("Dask Light Module", "ShaderNodeDaskLight", "LIGHT_SUN"),
    'DASK_AO': ("Dask AO Module", "ShaderNodeDaskAO", "SHADING_RENDERED"),
    'DASK_GRADE': ("Dask Grade Module", "ShaderNodeDaskGrade", "COLOR"),
    'DASK_OUTLINE': ("Dask Outline Module", "ShaderNodeDaskOutline", "MOD_LINEART"),
}


# =============================================================================
# Operator: Add Anime Shader Node into active Node Tree
# =============================================================================

class NODE_OT_dasktoon_add_anime_node(NodeAddOperator, Operator):
    """Add a DaskToon Native Anime Shader Node to the active node tree"""
    bl_idname = "node.dasktoon_add_anime_node"
    bl_label = "Add Anime Shader Node"
    bl_options = {'REGISTER', 'UNDO'}

    node_type: StringProperty(
        name="Node Type",
        description="Type of Anime node to insert",
        default='CEL_SHADER'
    )

    def execute(self, context):
        space = context.space_data
        if not space or space.type != 'NODE_EDITOR' or not space.edit_tree:
            self.report({'WARNING'}, "No active Shader Node tree!")
            return {'CANCELLED'}

        tree = space.edit_tree
        self.deselect_nodes(context)

        # 1. First try creating Native C++ Shader Node
        node = None
        native_type = None
        for key, (lbl, ntype, _) in ANIME_NATIVE_NODES.items():
            if key == self.node_type:
                native_type = ntype
                break

        if native_type:
            try:
                node = tree.nodes.new(type=native_type)
            except Exception:
                node = None

        # 2. Fallback to Node Group generator if C++ type not yet compiled
        if not node:
            info = ANIME_NODE_GENERATORS.get(self.node_type)
            if not info:
                self.report({'ERROR'}, f"Unknown Anime node type: {self.node_type}")
                return {'CANCELLED'}

            label_name, desc, gen_func = info
            node_group = gen_func()
            node = tree.nodes.new(type='ShaderNodeGroup')
            node.node_tree = node_group
            node.label = label_name

        node.select = True
        tree.nodes.active = node
        node.location = space.cursor_location

        self.report({'INFO'}, f"Added {node.name} to {tree.name}")
        return {'FINISHED'}


# =============================================================================
# Operator: Setup Full Anime Material Presets
# =============================================================================

class DASKTOON_OT_setup_anime_preset(Operator):
    """Create a complete Anime Material preset for the active object"""
    bl_idname = "dasktoon.setup_anime_preset"
    bl_label = "Setup Anime Material Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_type: StringProperty(
        name="Preset Type",
        description="Type of anime material preset",
        default='CHARACTER'
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Please select a Mesh object!")
            return {'CANCELLED'}

        mat_names = {
            'CHARACTER': "DaskToon_Anime_Character",
            'HAIR': "DaskToon_Anime_Hair",
            'EYES': "DaskToon_Anime_Eyes",
            'MANGA': "DaskToon_Manga_Comic",
        }
        name = mat_names.get(self.preset_type, "DaskToon_Anime_Material")

        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out_node = nodes.new('ShaderNodeOutputMaterial')
        out_node.location = (500, 0)

        if self.preset_type == 'CHARACTER':
            # Try Native C++ Character BSDF
            try:
                char_node = nodes.new(type='ShaderNodeAnimeCharacter')
                char_node.location = (0, 0)
                links.new(char_node.outputs['BSDF'], out_node.inputs['Surface'])
            except Exception:
                cel_group = get_or_create_cel_shader_group()
                cel_node = nodes.new('ShaderNodeGroup')
                cel_node.node_tree = cel_group
                cel_node.location = (0, 0)
                wc_group = get_or_create_warm_cool_group()
                wc_node = nodes.new('ShaderNodeGroup')
                wc_node.node_tree = wc_group
                wc_node.location = (260, 0)
                links.new(cel_node.outputs['Color'], wc_node.inputs['Base Color'])
                links.new(cel_node.outputs['Shadow Mask'], wc_node.inputs['Shadow Factor'])
                emission = nodes.new('ShaderNodeEmission')
                emission.location = (460, 0)
                links.new(wc_node.outputs['Graded Color'], emission.inputs['Color'])
                links.new(emission.outputs['Emission'], out_node.inputs['Surface'])

        elif self.preset_type == 'HAIR':
            try:
                cel_node = nodes.new(type='ShaderNodeAnimeCel')
                cel_node.location = (0, 0)
                ring_node = nodes.new(type='ShaderNodeAnimeAngelRing')
                ring_node.location = (0, 300)
                mix_hair = nodes.new('ShaderNodeMix')
                mix_hair.data_type = 'RGBA'
                mix_hair.blend_type = 'ADD'
                mix_hair.location = (250, 0)
                links.new(ring_node.outputs['Fac'], mix_hair.inputs['Factor'])
                links.new(cel_node.outputs['Color'], mix_hair.inputs[6])
                links.new(ring_node.outputs['Color'], mix_hair.inputs[7])
                emission = nodes.new('ShaderNodeEmission')
                emission.location = (420, 0)
                links.new(mix_hair.outputs[2], emission.inputs['Color'])
                links.new(emission.outputs['Emission'], out_node.inputs['Surface'])
            except Exception:
                cel_group = get_or_create_cel_shader_group()
                cel_node = nodes.new('ShaderNodeGroup')
                cel_node.node_tree = cel_group
                cel_node.location = (-100, 0)
                ring_group = get_or_create_angel_ring_group()
                ring_node = nodes.new('ShaderNodeGroup')
                ring_node.node_tree = ring_group
                ring_node.location = (-100, 300)
                mix_hair = nodes.new('ShaderNodeMix')
                mix_hair.data_type = 'RGBA'
                mix_hair.blend_type = 'ADD'
                mix_hair.location = (250, 0)
                links.new(ring_node.outputs['Highlight Factor'], mix_hair.inputs['Factor'])
                links.new(cel_node.outputs['Color'], mix_hair.inputs[6])
                links.new(ring_node.outputs['Highlight Color'], mix_hair.inputs[7])
                emission = nodes.new('ShaderNodeEmission')
                emission.location = (420, 0)
                links.new(mix_hair.outputs[2], emission.inputs['Color'])
                links.new(emission.outputs['Emission'], out_node.inputs['Surface'])

        elif self.preset_type == 'EYES':
            try:
                eye_node = nodes.new(type='ShaderNodeAnimeEye')
                eye_node.location = (0, 0)
                links.new(eye_node.outputs['BSDF'], out_node.inputs['Surface'])
            except Exception:
                eye_group = get_or_create_eye_shader_group()
                eye_node = nodes.new('ShaderNodeGroup')
                eye_node.node_tree = eye_group
                eye_node.location = (0, 0)
                links.new(eye_node.outputs['Emission BSDF'], out_node.inputs['Surface'])

        elif self.preset_type == 'MANGA':
            try:
                cel_node = nodes.new(type='ShaderNodeAnimeCel')
                cel_node.location = (0, 0)
                tone_node = nodes.new(type='ShaderNodeAnimeMangaScreentone')
                tone_node.location = (220, 0)
                emission = nodes.new('ShaderNodeEmission')
                emission.location = (400, 0)
                links.new(tone_node.outputs['Color'], emission.inputs['Color'])
                links.new(emission.outputs['Emission'], out_node.inputs['Surface'])
            except Exception:
                cel_group = get_or_create_cel_shader_group()
                cel_node = nodes.new('ShaderNodeGroup')
                cel_node.node_tree = cel_group
                cel_node.location = (-200, 0)
                tone_group = get_or_create_screentone_group()
                tone_node = nodes.new('ShaderNodeGroup')
                tone_node.node_tree = tone_group
                tone_node.location = (150, 0)
                links.new(cel_node.outputs['Shadow Mask'], tone_node.inputs['Shading Factor'])
                emission = nodes.new('ShaderNodeEmission')
                emission.location = (400, 0)
                links.new(tone_node.outputs['Screentone Color'], emission.inputs['Color'])
                links.new(emission.outputs['Emission'], out_node.inputs['Surface'])

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        self.report({'INFO'}, f"Applied Anime Preset '{name}' to {obj.name}")
        return {'FINISHED'}


# =============================================================================
# 1-Click Sun Direction to Materials Binder
# =============================================================================

class DASKTOON_OT_link_sun_direction(Operator):
    """Link Scene Sun Light rotation directly to Light Vector on all Dask Anime Shader Nodes (Real-Time Driver)"""
    bl_idname = "dasktoon.link_sun_direction"
    bl_label = "Sync Sun Light to Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import mathutils
        sun_ob = None
        for ob in context.scene.objects:
            if ob.type == 'LIGHT' and getattr(ob.data, 'type', '') == 'SUN':
                sun_ob = ob
                break

        if not sun_ob:
            bpy.ops.dasktoon.setup_lighting()
            for ob in context.scene.objects:
                if ob.type == 'LIGHT' and getattr(ob.data, 'type', '') == 'SUN':
                    sun_ob = ob
                    break

        if not sun_ob:
            self.report({'WARNING'}, "No Sun Light found in Scene!")
            return {'CANCELLED'}

        # Calculate current Sun forward vector in World Space
        mat_rot = sun_ob.matrix_world.to_3x3()
        light_vector = (mat_rot @ mathutils.Vector((0.0, 0.0, 1.0))).normalized()
        light_tuple = (float(light_vector.x), float(light_vector.y), float(light_vector.z))

        count = 0
        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree:
                continue
            mat_updated = False
            for node in mat.node_tree.nodes:
                if hasattr(node, "inputs") and "Light Vector" in node.inputs:
                    sock = node.inputs["Light Vector"]
                    # Add real-time C++ animation drivers so modal viewport rotation updates at 60 FPS
                    try:
                        sock.driver_remove("default_value")
                    except Exception:
                        pass
                    
                    # Set direct values first
                    sock.default_value = light_tuple
                    
                    # Bind C++ Driver to Sun rotation
                    for axis_idx in range(3):
                        try:
                            fcurve = sock.driver_add("default_value", axis_idx)
                            drv = fcurve.driver
                            drv.type = 'SCRIPTED'
                            drv.variables.clear()
                            
                            # Add Sun rotation transform variables
                            for ax_name, ax_type in [('rx', 'ROT_X'), ('ry', 'ROT_Y'), ('rz', 'ROT_Z')]:
                                var = drv.variables.new()
                                var.name = ax_name
                                var.type = 'TRANSFORMS'
                                target = var.targets[0]
                                target.id = sun_ob
                                target.transform_space = 'WORLD_SPACE'
                                target.transform_type = ax_type

                            if axis_idx == 0:
                                drv.expression = "sin(ry)"
                            elif axis_idx == 1:
                                drv.expression = "-sin(rx) * cos(ry)"
                            else:
                                drv.expression = "cos(rx) * cos(ry)"
                        except Exception:
                            pass

                    count += 1
                    mat_updated = True

            if mat_updated:
                mat.node_tree.update_tag()

        self.report({'INFO'}, f"Bound live Sun rotation ({light_tuple[0]:.2f}, {light_tuple[1]:.2f}, {light_tuple[2]:.2f}) to {count} Anime shader(s)!")
        return {'FINISHED'}


# =============================================================================
# Helper: Universal 100% Real-Time Auto-Sync Sun & World to Materials
# =============================================================================

def dasktoon_ensure_default_dask_shader(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return
    nodes = mat.node_tree.nodes
    principled_node = None
    output_node = None
    for n in nodes:
        if n.bl_idname == 'ShaderNodeOutputMaterial':
            output_node = n
        elif n.bl_idname == 'ShaderNodeBsdfPrincipled':
            principled_node = n

    # If new default material (Principled BSDF + Output Material)
    if principled_node and output_node and len(nodes) == 2:
        base_col = (0.95, 0.85, 0.80, 1.0)
        if 'Base Color' in principled_node.inputs:
            base_col = tuple(principled_node.inputs['Base Color'].default_value)
        loc = principled_node.location.copy()
        nodes.remove(principled_node)
        try:
            dask_node = nodes.new(type='ShaderNodeAnimeCharacter')
        except Exception:
            dask_node = None
        if dask_node:
            dask_node.location = loc
            if 'Base Color' in dask_node.inputs:
                dask_node.inputs['Base Color'].default_value = base_col
            mat.node_tree.links.new(dask_node.outputs['BSDF'], output_node.inputs['Surface'])
            mat.node_tree.update_tag()


def _sync_outline_node_subgraph(src_socket, target_tree, target_socket):
    """Deeply clones all upstream node network (Textures, Hue/Sat, ColorRamp, Mix, etc.) into the Outline Material."""
    if not src_socket:
        return

    # Remove existing helper nodes (keep only ShaderNodeDaskOutline and Output)
    for n in list(target_tree.nodes):
        if n.bl_idname not in {'ShaderNodeDaskOutline', 'ShaderNodeOutputMaterial'}:
            target_tree.nodes.remove(n)

    if not src_socket.is_linked:
        for lk in list(target_socket.links):
            target_tree.links.remove(lk)
        try:
            target_socket.default_value = src_socket.default_value
        except Exception:
            pass
        return

    visited_nodes = {}

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
        target_tree.links.new(out_s, target_socket)


# =============================================================================
# Automated VRM Inverted Hull Outline Synchronizer (Zero-Click Node Experience)
# =============================================================================

@bpy.app.handlers.persistent
def dasktoon_vrm_outline_auto_sync(scene, depsgraph=None):
    """Automatically sync Inverted Hull outline whenever user enables/disables outline on Dask nodes."""
    for obj in scene.objects:
        if obj.type != 'MESH' or not obj.data or not obj.data.materials:
            continue

        outline_width = 0.0
        outline_mix = 0.0
        active_outline_sock = None
        enable_outline = False

        for mat in obj.data.materials:
            if not mat or not mat.node_tree:
                continue
            if mat.name.endswith("_DaskOutline"):
                continue  # Skip scanning generated outline material slot
            for node in mat.node_tree.nodes:
                # 1. Standalone Dask Outline Module
                if node.bl_idname == 'ShaderNodeDaskOutline':
                    enable_outline = True
                    if 'Outline Width' in node.inputs:
                        outline_width = max(outline_width, node.inputs['Outline Width'].default_value)
                    if 'Outline Color' in node.inputs:
                        active_outline_sock = node.inputs['Outline Color']
                    if 'Outline Lighting Mix' in node.inputs:
                        outline_mix = node.inputs['Outline Lighting Mix'].default_value
                # 2. Dask Cel Module
                elif node.bl_idname == 'ShaderNodeDaskCel':
                    use_ot = False
                    if 'Use Outline' in node.inputs:
                        use_ot = bool(node.inputs['Use Outline'].default_value)
                    elif hasattr(node, 'use_outline'):
                        use_ot = bool(node.use_outline)
                    if use_ot:
                        enable_outline = True
                        if 'Outline Width' in node.inputs:
                            outline_width = max(outline_width, node.inputs['Outline Width'].default_value)
                        if 'Outline Color' in node.inputs:
                            active_outline_sock = node.inputs['Outline Color']
                        if 'Outline Lighting Mix' in node.inputs:
                            outline_mix = node.inputs['Outline Lighting Mix'].default_value
                # 3. Master Dask Shader BSDF
                elif node.bl_idname == 'ShaderNodeAnimeCharacter':
                    use_ot = bool(getattr(node, 'use_outline', False))
                    if use_ot:
                        enable_outline = True
                        if 'Outline Width' in node.inputs:
                            outline_width = max(outline_width, node.inputs['Outline Width'].default_value)
                        if 'Outline Color' in node.inputs:
                            active_outline_sock = node.inputs['Outline Color']
                        if 'Outline Lighting Mix' in node.inputs:
                            outline_mix = node.inputs['Outline Lighting Mix'].default_value

        mod_name = "DaskToon_Outline"
        existing_mod = obj.modifiers.get(mod_name)

        if enable_outline and outline_width > 0.0001:
            # 1. Ensure Outline Material exists in object material slots
            outline_mat_name = f"{obj.name}_DaskOutline"
            outline_mat = bpy.data.materials.get(outline_mat_name)
            if not outline_mat:
                outline_mat = bpy.data.materials.new(name=outline_mat_name)
                outline_mat.use_nodes = True
                nt = outline_mat.node_tree
                nt.nodes.clear()
                ot_n = nt.nodes.new('ShaderNodeDaskOutline')
                ot_out = nt.nodes.new('ShaderNodeOutputMaterial')
                nt.links.new(ot_n.outputs['BSDF'], ot_out.inputs['Surface'])

            # Ensure backface culling and no shadow occlusion
            outline_mat.use_backface_culling = True
            if hasattr(outline_mat, 'use_backface_culling_shadow'):
                outline_mat.use_backface_culling_shadow = True
            if hasattr(outline_mat, 'use_backface_culling_lightprobe_volume'):
                outline_mat.use_backface_culling_lightprobe_volume = True
            if hasattr(outline_mat, 'use_transparent_shadow'):
                outline_mat.use_transparent_shadow = True

            # Sync outline material values and full upstream node network (HueSatVal, Textures, etc.)
            if outline_mat.node_tree:
                nt = outline_mat.node_tree
                ot_n = None
                for n in nt.nodes:
                    if n.bl_idname == 'ShaderNodeDaskOutline':
                        ot_n = n
                        break
                if not ot_n:
                    ot_n = nt.nodes.new('ShaderNodeDaskOutline')
                    ot_out = nt.nodes.get("Material Output") or nt.nodes.new('ShaderNodeOutputMaterial')
                    nt.links.new(ot_n.outputs['BSDF'], ot_out.inputs['Surface'])

                if 'Outline Lighting Mix' in ot_n.inputs:
                    ot_n.inputs['Outline Lighting Mix'].default_value = outline_mix

                if active_outline_sock:
                    _sync_outline_node_subgraph(active_outline_sock, nt, ot_n.inputs['Outline Color'])

            # Find or append material slot index
            slot_idx = -1
            for i, slot in enumerate(obj.material_slots):
                if slot.material == outline_mat:
                    slot_idx = i
                    break
            if slot_idx == -1:
                obj.data.materials.append(outline_mat)
                slot_idx = len(obj.data.materials) - 1

            # 2. Ensure Solidify Modifier exists and matches width with zero shadow occlusion
            if not existing_mod:
                existing_mod = obj.modifiers.new(name=mod_name, type='SOLIDIFY')

            existing_mod.use_flip_normals = True
            existing_mod.use_rim = False
            existing_mod.use_quality_normals = True
            existing_mod.offset = 1.0
            existing_mod.thickness = outline_width
            existing_mod.material_offset = slot_idx
            existing_mod.show_viewport = True
            existing_mod.show_render = True
        else:
            # Cleanly remove modifier when outline is disabled
            if existing_mod:
                obj.modifiers.remove(existing_mod)
            # Cleanly remove outline material slot if present
            outline_mat_name = f"{obj.name}_DaskOutline"
            for i in range(len(obj.material_slots) - 1, -1, -1):
                slot = obj.material_slots[i]
                if slot.material and slot.material.name == outline_mat_name:
                    obj.data.materials.pop(index=i)


# =============================================================================
# Registration
# =============================================================================

classes = (
    NODE_OT_dasktoon_add_anime_node,
    DASKTOON_OT_setup_anime_preset,
    DASKTOON_OT_link_sun_direction,
)


def register():
    for cls in classes:
        if not hasattr(cls, 'is_registered') or not cls.is_registered:
            try:
                bpy.utils.register_class(cls)
            except Exception:
                pass
    if dasktoon_vrm_outline_auto_sync not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(dasktoon_vrm_outline_auto_sync)


def unregister():
    if dasktoon_vrm_outline_auto_sync in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(dasktoon_vrm_outline_auto_sync)
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()


