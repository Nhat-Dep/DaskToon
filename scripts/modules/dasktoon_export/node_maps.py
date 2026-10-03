# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon node inputs -> Unity material properties, enums -> floats, module flags -> keywords (spec 5, 6)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputMap:
    socket: str          # input name on the DaskToon node
    prop: str            # Unity property holding the value
    kind: str            # 'COLOR', 'FLOAT' or 'BOOL'
    map_prop: str = ""   # texture property; "" when Unity takes no texture for this input
    flag_prop: str = ""  # float that switches the texture on


@dataclass(frozen=True)
class NodeMap:
    shader: str
    inputs: tuple
    enums: tuple = ()     # (node property, Unity float)
    modules: tuple = ()   # (node property, keyword)
    normal: bool = False  # has a Normal input (tangent-space normal map)
    ramp: bool = False    # has the Simple / Ramp shading switch


def _in(socket, prop, kind, mapped=False):
    if not mapped:
        return InputMap(socket, prop, kind)
    if prop == "_BaseColor":
        return InputMap(socket, prop, kind, "_BaseMap", "_DT_BaseMapOn")
    return InputMap(socket, prop, kind, prop + "Map", prop + "MapOn")


ANIME_BSDF = NodeMap("AnimeBSDF", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Ambient Color", "_DT_AmbientColor", 'COLOR', True),
    _in("Use Custom Color", "_DT_AmbientUseCustom", 'BOOL'),
    _in("Ambient Shadow Only", "_DT_AmbientShadowOnly", 'BOOL'),
    _in("Ambient Factor", "_DT_AmbientFactor", 'FLOAT'),
    _in("Light Tint Strength", "_DT_LightTintStrength", 'FLOAT'),
    _in("Light Factor", "_DT_LightFactor", 'FLOAT'),
    _in("AO Color", "_DT_AOColor", 'COLOR', True),
    _in("AO Distance", "_DT_AODistance", 'FLOAT'),
    _in("AO Darkness", "_DT_AODarkness", 'FLOAT'),
    _in("AO Factor", "_DT_AOFactor", 'FLOAT'),
    _in("AO Mask", "_DT_AOMask", 'FLOAT', True),
    _in("Rim Color", "_DT_RimColor", 'COLOR', True),
    _in("Rim Fresnel Power", "_DT_RimPower", 'FLOAT'),
    _in("Rim Lift", "_DT_RimLift", 'FLOAT'),
    _in("Rim Lighting Mix", "_DT_RimLightingMix", 'FLOAT'),
    _in("Rim Factor", "_DT_RimFactor", 'FLOAT'),
    _in("Color Filter", "_DT_ColorFilter", 'COLOR', True),
    _in("Shadow Tint", "_DT_ShadowTint", 'COLOR', True),
    _in("Highlight Tint", "_DT_HighlightTint", 'COLOR', True),
    _in("Saturation", "_DT_Saturation", 'FLOAT'),
    _in("Brightness", "_DT_Brightness", 'FLOAT'),
    _in("Contrast", "_DT_Contrast", 'FLOAT'),
    _in("Grade Factor", "_DT_GradeFactor", 'FLOAT'),
    _in("Strength", "_DT_Strength", 'FLOAT'),
    _in("Alpha", "_DT_Alpha", 'FLOAT', True),
), enums=(("ambient_mode", "_DT_AmbientMode"), ("light_blend_mode", "_DT_LightMode"),
          ("outline_tint_mode", "_DT_OutlineTintMode")),
   modules=(("use_ambient", "_DT_AMBIENT"), ("use_light", "_DT_LIGHT"), ("use_ao", "_DT_AO"),
            ("use_rim", "_DT_RIM"), ("use_grade", "_DT_GRADE")),
   normal=True, ramp=True)

ANIME_CEL = NodeMap("AnimeCel", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Ambient Color", "_DT_AmbientColor", 'COLOR', True),
    _in("Ambient Blend", "_DT_AmbientBlend", 'FLOAT'),
    _in("Ambient Shadow Only", "_DT_AmbientShadowOnly", 'BOOL'),
    _in("Light Tint Strength", "_DT_LightTintStrength", 'FLOAT'),
    _in("Specular Color", "_DT_SpecularColor", 'COLOR', True),
    _in("Specular Size", "_DT_SpecularSize", 'FLOAT'),
    _in("Specular Softness", "_DT_SpecularSoftness", 'FLOAT'),
), enums=(("ambient_mode", "_DT_AmbientMode"), ("light_blend_mode", "_DT_LightMode")), normal=True, ramp=True)

ANIME_EYE = NodeMap("AnimeEye", (
    _in("Iris Color", "_BaseColor", 'COLOR', True),
    _in("Pupil Color", "_DT_PupilColor", 'COLOR', True),
    _in("Bottom Glow Color", "_DT_GlowColor", 'COLOR', True),
    _in("Bottom Glow Power", "_DT_GlowPower", 'FLOAT'),
    _in("Top Shadow Tint", "_DT_TopShadowTint", 'COLOR', True),
    _in("Sparkle Color", "_DT_SparkleColor", 'COLOR', True),
))

DASK_CEL = NodeMap("DaskCel", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Strength", "_DT_Strength", 'FLOAT'),
), enums=(("outline_tint_mode", "_DT_OutlineTintMode"),), normal=True, ramp=True)

NODE_MAPS = {
    'ShaderNodeAnimeCharacter': ANIME_BSDF,
    'ShaderNodeAnimeCel': ANIME_CEL,
    'ShaderNodeAnimeEye': ANIME_EYE,
    'ShaderNodeDaskCel': DASK_CEL,
}

ANGEL_RING_INPUTS = (
    _in("Highlight Color", "_DT_RingColor", 'COLOR'),
    _in("Band Position", "_DT_RingPosition", 'FLOAT'),
    _in("Band Width", "_DT_RingWidth", 'FLOAT'),
    _in("Band Softness", "_DT_RingSoftness", 'FLOAT'),
    _in("Strand Jitter", "_DT_RingJitter", 'FLOAT'),
    _in("Noise Scale", "_DT_RingNoiseScale", 'FLOAT'),
    _in("Intensity", "_DT_RingIntensity", 'FLOAT'),
)

# Dask Outline node of the <material>.Outline companion (project 1, spec 4.2).
OUTLINE_INPUTS = (
    _in("Base Color", "_DT_OutlineBaseColor", 'COLOR', True),
    _in("Outline Color", "_DT_OutlineColor", 'COLOR', True),
    _in("Outline Width", "_DT_OutlineWidth", 'FLOAT'),
    _in("Light Bleed", "_DT_OutlineLightBleed", 'FLOAT'),
    _in("Hand Wobble", "_DT_OutlineWobble", 'FLOAT'),
    _in("Tint Darkness", "_DT_OutlineTintDarkness", 'FLOAT'),
    _in("Tint Saturation Boost", "_DT_OutlineTintSatBoost", 'FLOAT'),
    _in("Outline Lighting Mix", "_DT_OutlineLightingMix", 'FLOAT'),
)

# Keywords each shader declares, and the inspector toggle that mirrors each keyword.
SHADER_KEYWORDS = {
    "AnimeBSDF": ("_DT_RAMP", "_DT_AMBIENT", "_DT_LIGHT", "_DT_AO", "_DT_RIM", "_DT_GRADE", "_DT_OUTLINE",
                  "_DT_ALPHATEST_ON", "_DT_NORMALMAP"),
    "AnimeCel": ("_DT_RAMP", "_DT_ANGEL_RING", "_DT_OUTLINE", "_DT_NORMALMAP"),
    "AnimeEye": ("_DT_OUTLINE",),
    "DaskCel": ("_DT_RAMP", "_DT_OUTLINE", "_DT_NORMALMAP"),
}
KEYWORD_TOGGLES = {
    "_DT_RAMP": "_DT_UseRamp",
    "_DT_AMBIENT": "_DT_UseAmbient",
    "_DT_LIGHT": "_DT_UseLight",
    "_DT_AO": "_DT_UseAO",
    "_DT_RIM": "_DT_UseRim",
    "_DT_GRADE": "_DT_UseGrade",
    "_DT_OUTLINE": "_DT_UseOutline",
    "_DT_ANGEL_RING": "_DT_UseAngelRing",
    "_DT_ALPHATEST_ON": "_AlphaClip",
    "_DT_NORMALMAP": "_DT_UseNormalMap",
}
