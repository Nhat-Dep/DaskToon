// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon shading core for Unity: a line-by-line port of DaskToon's GLSL node functions in
// source/blender/gpu/shaders/material/gpu_shader_material_*.glsl. This file calls no URP function: lighting
// arrives in DTLighting, gathered by DaskToonURP.hlsl with the meaning of EEVEE's closure_eval(). It only needs
// the SRP Core macros (TEXTURE2D, SAMPLER, ...), which every DaskToon shader includes first.

#ifndef DASKTOON_CORE_INCLUDED
#define DASKTOON_CORE_INCLUDED

#define DT_PI 3.14159265

// Material fields every DaskToon shader has (outline pass, alpha clip). Each .shader puts this macro inside its
// UnityPerMaterial CBUFFER, so all passes share one layout (SRP Batcher).
#define DT_SHARED_MATERIAL_FIELDS \
    float4 _DT_OutlineColor; \
    float4 _DT_OutlineBaseColor; \
    float _DT_OutlineColorMapOn; \
    float _DT_OutlineBaseColorMapOn; \
    float _DT_OutlineWidth; \
    float _DT_OutlineLightBleed; \
    float _DT_OutlineWobble; \
    float _DT_OutlineTintDarkness; \
    float _DT_OutlineTintSatBoost; \
    float _DT_OutlineLightingMix; \
    float _DT_OutlineTintMode; \
    float _DT_OutlineUV; \
    float _DT_OutlineWUV; \
    float _Cutoff;

#define DT_SHARED_TEXTURES \
    TEXTURE2D(_DT_OutlineColorMap); \
    TEXTURE2D(_DT_OutlineBaseColorMap);

// Every material texture goes through these inline samplers, so no pass gets near the 16-sampler limit.
SAMPLER(sampler_linear_repeat);
SAMPLER(sampler_linear_clamp);

struct DTLighting
{
    float3 diffuse;    // closure_eval(ClosureDiffuse) at N: every lamp (Lambert) plus the ambient
    float3 diffuseUp;  // the same for the world up direction (Blender +Z)
    float glossy;      // luminance of the sharp reflection used by the Anime Cel toon specular
    float ao;          // ambient occlusion visibility, 1 = open
    float NdotV;       // dot(N, V), signed
};

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_dasktoon_shading.glsl

float3 dt_rgb_to_hsv(float3 c)
{
    float4 K = float4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    float4 p = lerp(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
    float4 q = lerp(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return float3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

float3 dt_hsv_to_rgb(float3 c)
{
    float4 K = float4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    float3 p = abs(frac(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * lerp(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Rec.709 luminance, identical to Blender's default OCIO luminance coefficients.
float dt_luminance(float3 c)
{
    return dot(c, float3(0.2126, 0.7152, 0.0722));
}

float3 dt_overlay(float3 a, float3 b)
{
    return lerp(2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b), step(0.5, a));
}

float3 dt_light_norm(float3 light_col)
{
    float l_max = max(max(light_col.r, light_col.g), light_col.b);
    return (l_max > 0.001) ? (light_col / l_max) : float3(1.0, 1.0, 1.0);
}

float3 dt_shade_simple(float light, float3 base, float3 shadow, float thresh, float softness, out float cel)
{
    float s_soft = max(softness, 0.001);
    float s_min = clamp(thresh - s_soft * 0.5, 0.0, 1.0);
    float s_max = clamp(thresh + s_soft * 0.5, s_min + 0.0001, 1.0);
    cel = smoothstep(s_min, s_max, light);
    float3 auto_shadow = base * shadow * 1.25;
    float3 final_shadow = (length(shadow) > 0.001) ? lerp(shadow, auto_shadow, 0.75) : base * 0.5;
    return lerp(final_shadow, base, cel);
}

// The ramp texture is 256x1 with pixel i = ColorRamp.evaluate((i + 0.5) / 256). A CONSTANT ramp snaps t to a
// texel centre, which turns the bilinear clamp sampler into nearest sampling (Blender's valtorgb_nearest).
float3 dt_ramp_color(TEXTURE2D_PARAM(ramp, rampSampler), float is_constant, float t)
{
    if (is_constant > 0.5)
    {
        t = (min(floor(t * 256.0), 255.0) + 0.5) / 256.0;
    }
    return SAMPLE_TEXTURE2D_LOD(ramp, rampSampler, float2(t, 0.5), 0).rgb;
}

float3 dt_shade_ramp(float light, float3 base, float thresh, TEXTURE2D_PARAM(ramp, rampSampler), float is_constant,
                     out float cel)
{
    float t = clamp(light + 0.5 - thresh, 0.0, 1.0);
    float3 tint = dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, t);
    float lum_dark = dt_luminance(dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, 0.0));
    float lum_lit = dt_luminance(dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, 1.0));
    cel = clamp((dt_luminance(tint) - lum_dark) / max(lum_lit - lum_dark, 0.0001), 0.0, 1.0);
    return base * tint;
}

// Ambient Mode: 0 OVERLAY, 1 HUE, 2 HUE_SAT, 3 SAT, 4 VAL, 5 MULTIPLY, 6 MIX.
float3 dt_ambient_mode(float3 a, float3 b, int mode)
{
    if (mode == 0)
    {
        return dt_overlay(a, b);
    }
    if (mode == 5)
    {
        return a * b;
    }
    if (mode < 1 || mode > 4)
    {
        return b;
    }
    float3 ha = dt_rgb_to_hsv(a);
    float3 hb = dt_rgb_to_hsv(b);
    if (mode == 1)
    {
        ha.x = hb.x;
    }
    else if (mode == 2)
    {
        ha.x = hb.x;
        ha.y = lerp(ha.y, hb.y, 0.65);
    }
    else if (mode == 3)
    {
        ha.y = hb.y;
    }
    else
    {
        ha.z = hb.z;
    }
    return dt_hsv_to_rgb(ha);
}

// Light Mode: 0 OVERLAY, 1 HUE, 2 MULTIPLY, 3 ADD, 4 PURE_CEL.
float3 dt_light_mode(float3 c, float3 light_col, float3 light_norm, float strength, int mode)
{
    float s = clamp(strength, 0.0, 2.0);
    float3 ls = lerp(float3(1.0, 1.0, 1.0), light_norm, s);
    if (mode == 0)
    {
        return dt_overlay(c, ls);
    }
    if (mode == 1)
    {
        float3 hc = dt_rgb_to_hsv(c);
        float3 hl = dt_rgb_to_hsv(light_norm);
        float3 tinted = dt_hsv_to_rgb(float3(hl.x, hc.y, hc.z));
        return lerp(c, tinted, clamp(s, 0.0, 1.0) * hl.y);
    }
    if (mode == 2)
    {
        return c * ls;
    }
    if (mode == 3)
    {
        return c + (light_col - min(min(light_col.r, light_col.g), light_col.b)) * s;
    }
    return c;
}

// value x texture when the map flag is on. Float inputs read the texture's luminance, like Blender's implicit
// colour-to-float conversion.
float4 DT_ColorInput(float4 value, TEXTURE2D_PARAM(tex, smp), float mapOn, float2 uv)
{
    UNITY_BRANCH
    if (mapOn > 0.5)
    {
        value *= SAMPLE_TEXTURE2D(tex, smp, uv);
    }
    return value;
}

float DT_FloatInput(float value, TEXTURE2D_PARAM(tex, smp), float mapOn, float2 uv)
{
    UNITY_BRANCH
    if (mapOn > 0.5)
    {
        value *= dt_luminance(SAMPLE_TEXTURE2D(tex, smp, uv).rgb);
    }
    return value;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_character.glsl (Anime BSDF). Modules are material keywords.

struct DTAnimeBSDFInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float3 ambientColor;
    float ambientUseCustom;
    float ambientShadowOnly;
    float ambientFactor;
    int ambientMode;
    float lightTintStrength;
    float lightFactor;
    int lightMode;
    float3 aoColor;
    float aoDarkness;
    float aoFactor;
    float aoMask;
    float3 rimColor;
    float rimPower;
    float rimLift;
    float rimLightingMix;
    float rimFactor;
    float3 colorFilter;
    float3 shadowTint;
    float3 highlightTint;
    float saturation;
    float brightness;
    float contrast;
    float gradeFactor;
    float strength;
};

float3 dt_grade(float3 c, float3 filter, float3 shadow_tint, float3 highlight_tint, float saturation,
                float brightness, float contrast)
{
    float3 graded = c * filter;
    float lum = dot(graded, float3(0.299, 0.587, 0.114));
    graded = lerp(graded * shadow_tint, graded * highlight_tint, clamp(lum, 0.0, 1.0));
    if (abs(saturation - 1.0) > 0.001)
    {
        float3 hsv = dt_rgb_to_hsv(graded);
        hsv.y = clamp(hsv.y * max(saturation, 0.0), 0.0, 1.0);
        graded = dt_hsv_to_rgb(hsv);
    }
    graded += brightness;
    graded = (graded - 0.5) * (1.0 + contrast) + 0.5;
    return max(graded, float3(0.0, 0.0, 0.0));
}

float3 dt_anime_bsdf(DTAnimeBSDFInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float3 light_col = l.diffuse;
    float light_intensity = max(max(light_col.r, light_col.g), light_col.b);

    float cel;
    float3 c;
#if defined(_DT_RAMP)
    c = dt_shade_ramp(light_intensity, base, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    c = dt_shade_simple(light_intensity, base, shadow, s.shadowThreshold, s.shadowSoftness, cel);
#endif

#if defined(_DT_AMBIENT)
    float amb_fac = clamp(s.ambientFactor, 0.0, 1.0);
    if (amb_fac > 0.0001)
    {
        float3 amb_color = (s.ambientUseCustom > 0.5) ? s.ambientColor : l.diffuseUp;
        float3 amb_shaded = dt_ambient_mode(c, amb_color, s.ambientMode);
        float apply_mask = (s.ambientShadowOnly > 0.5) ? (1.0 - cel) : 1.0;
        c = lerp(c, amb_shaded, amb_fac * apply_mask);
    }
#endif

#if defined(_DT_LIGHT)
    float lit_fac = clamp(s.lightFactor, 0.0, 1.0);
    if (lit_fac > 0.0001)
    {
        float3 lit_shaded = dt_light_mode(c, light_col, dt_light_norm(light_col), s.lightTintStrength, s.lightMode);
        c = lerp(c, lit_shaded, lit_fac * cel);
    }
#endif

#if defined(_DT_AO)
    float ao_f = clamp(s.aoFactor, 0.0, 1.0) * clamp(s.aoMask, 0.0, 1.0);
    if (ao_f > 0.0001)
    {
        float darkness = max(s.aoDarkness, 0.0);
        float occlusion = clamp(1.0 - l.ao, 0.0, 1.0);
        float deep_occlusion = clamp(pow(occlusion, 1.0 / max(darkness, 0.01)) * min(darkness, 3.0), 0.0, 1.0);
        float3 ao_multiplier = lerp(float3(1.0, 1.0, 1.0), s.aoColor, deep_occlusion);
        c = lerp(c, c * ao_multiplier, ao_f);
    }
#endif

#if defined(_DT_RIM)
    float rim_f = clamp(s.rimFactor, 0.0, 1.0);
    if (rim_f > 0.0001)
    {
        float fresnel = 1.0 - clamp(l.NdotV, 0.0, 1.0);
        float rim_term = clamp(pow(fresnel, max(s.rimPower, 0.5)) + s.rimLift, 0.0, 1.0);
        float3 rim_col = s.rimColor;
        float rim_l_mix = clamp(s.rimLightingMix, 0.0, 1.0);
        if (rim_l_mix > 0.001)
        {
            rim_col = lerp(rim_col, rim_col * light_col, rim_l_mix);
        }
        float light_visibility = lerp(1.0, clamp(light_intensity * 1.5, 0.0, 1.0), rim_l_mix);
        c += rim_col * (rim_term * rim_f * light_visibility);
    }
#endif

#if defined(_DT_GRADE)
    float grd_fac = clamp(s.gradeFactor, 0.0, 1.0);
    if (grd_fac > 0.0001)
    {
        float3 graded = dt_grade(c, s.colorFilter, s.shadowTint, s.highlightTint, s.saturation, s.brightness,
                                 s.contrast);
        c = lerp(c, graded, grd_fac);
    }
#endif

    return max(c * max(s.strength, 0.0), float3(0.0, 0.0, 0.0));
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_cel.glsl (Anime Cel / Classic Cel)

struct DTAnimeCelInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float4 ambientColor;
    float ambientBlend;
    float ambientShadowOnly;
    int ambientMode;
    float lightTintStrength;
    int lightMode;
    float3 specColor;
    float specSize;
    float specSoftness;
};

float3 dt_anime_cel(DTAnimeCelInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float4 ambient = max(s.ambientColor, 0.0);
    float3 spec_color = max(s.specColor, 0.0);

    // Ambient: tints the shadow tone, and the lit tone unless "shadow only".
    float blend_fac = clamp(s.ambientBlend * ambient.a, 0.0, 1.0);
    float3 shadow_amb = lerp(shadow, dt_ambient_mode(shadow, ambient.rgb, s.ambientMode), blend_fac);
    float3 lit_col = base;
    if (s.ambientShadowOnly < 0.5)
    {
        lit_col = lerp(lit_col, lit_col * ambient.rgb, blend_fac * 0.5);
    }

    float3 light_col = l.diffuse;
    float light = max(max(light_col.r, light_col.g), light_col.b);

    float cel;
    float3 color;
#if defined(_DT_RAMP)
    color = dt_shade_ramp(light, lit_col, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    color = dt_shade_simple(light, lit_col, shadow_amb, s.shadowThreshold, s.shadowSoftness, cel);
#endif

    // Lamp colour on the lit side.
    color = lerp(color, dt_light_mode(color, light_col, dt_light_norm(light_col), s.lightTintStrength, s.lightMode), cel);

    // Toon specular: glossy light level cut at (1 - size).
    float spec = clamp((l.glossy - (1.0 - s.specSize)) / max(s.specSoftness, 0.0001), 0.0, 1.0);
    color += spec_color * spec;
    return color;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_angel_ring.glsl, and the hair pattern Mix[ADD](AnimeCel.Color, Ring.Color, Ring.Fac).

struct DTAngelRingInput
{
    float3 highlightColor;
    float bandPosition;
    float bandWidth;
    float bandSoftness;
    float strandJitter;
    float noiseScale;
    float intensity;
};

// positionB / normalB are in Blender world space (EEVEE's g_data.P and the world normal). Returns the ring Color
// output; `fac` is the Fac output.
float3 dt_angel_ring(DTAngelRingInput s, float3 positionB, float3 normalB, out float fac)
{
    float3 highlight = max(s.highlightColor, 0.0);
    float3 N = normalize(normalB);
    float jitter = sin(dot(positionB.xy, float2(s.noiseScale * 0.7, s.noiseScale * 1.3))) * s.strandJitter * 0.1;
    float ring_dist = abs(N.z + jitter - clamp(s.bandPosition, 0.0, 1.0));
    float r_fw = max(fwidth(ring_dist), 0.0005);
    float r_soft = max(s.bandSoftness, r_fw);
    float r_width = max(s.bandWidth, 0.001);
    float ring_min = max(r_width - r_soft * 0.5, 0.0);
    float ring_max = r_width + r_soft * 0.5 + 0.0001;
    float ring_fac = 1.0 - smoothstep(ring_min, ring_max, ring_dist);
    fac = ring_fac * max(s.intensity, 0.0);
    return highlight * fac;
}

// Mix node, data type Color, blend ADD: mix(A, A + B, factor) = A + factor * B.
float3 dt_hair(float3 cel, float3 ring, float ring_fac, float clamp_factor, float clamp_result)
{
    float f = (clamp_factor > 0.5) ? clamp(ring_fac, 0.0, 1.0) : ring_fac;
    float3 c = cel + f * ring;
    return (clamp_result > 0.5) ? clamp(c, 0.0, 1.0) : c;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_eye.glsl (unlit)

struct DTAnimeEyeInput
{
    float3 irisColor;
    float3 pupilColor;
    float3 glowColor;
    float glowPower;
    float3 topShadowTint;
    float3 sparkleColor;
};

float3 dt_anime_eye(DTAnimeEyeInput s, float2 uv)
{
    float3 iris = max(s.irisColor, 0.0);
    float3 pupil = max(s.pupilColor, 0.0);
    float3 glow = max(s.glowColor, 0.0);
    float3 top_shadow = max(s.topShadowTint, 0.0);
    float3 sparkle = max(s.sparkleColor, 0.0);

    float dist_center = length(uv - float2(0.5, 0.5));
    float pupil_fac = 1.0 - smoothstep(0.16, 0.22, dist_center);
    float3 base_iris = lerp(iris, pupil, pupil_fac);

    float bottom_curve = pow(clamp(1.0 - uv.y, 0.0, 1.0), 2.2) * max(s.glowPower, 0.0);
    float3 with_glow = base_iris + glow * bottom_curve;

    float top_shadow_fac = smoothstep(0.45, 0.85, uv.y);
    float3 with_shadow = lerp(with_glow, with_glow * top_shadow, top_shadow_fac);

    float sp1 = 1.0 - smoothstep(0.035, 0.055, length(uv - float2(0.38, 0.65)));
    float sp2 = 1.0 - smoothstep(0.018, 0.032, length(uv - float2(0.62, 0.40)));
    float sparkle_fac = clamp(sp1 + sp2, 0.0, 1.0);
    return lerp(with_shadow, sparkle, sparkle_fac);
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_dask_cel.glsl. Its in-surface outline is on when the material keyword _DT_OUTLINE is set.

struct DTDaskCelInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float outlineWidth;
    float3 outlineColor;
    float outlineLightingMix;
    int outlineTintMode;
    float strength;
};

float3 dt_dask_cel(DTDaskCelInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant, out float cel)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float light_intensity = max(max(l.diffuse.r, l.diffuse.g), l.diffuse.b);

    float3 c;
#if defined(_DT_RAMP)
    c = dt_shade_ramp(light_intensity, base, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    c = dt_shade_simple(light_intensity, base, shadow, s.shadowThreshold, s.shadowSoftness, cel);
#endif

#if defined(_DT_OUTLINE)
    float edge_factor = 1.0 - abs(l.NdotV);
    float outline_thresh = 1.0 - clamp(s.outlineWidth * 50.0, 0.005, 0.99);
    if (edge_factor > outline_thresh)
    {
        float3 line_col = s.outlineColor;
        float3 base_hsv = dt_rgb_to_hsv(base);
        if (s.outlineTintMode == 1)
        {
            float o_h = frac(base_hsv.x - 0.03 + 1.0);
            float o_s = clamp(base_hsv.y * 1.40 + 0.10, 0.0, 1.0);
            float o_v = base_hsv.z * 0.35;
            line_col = dt_hsv_to_rgb(float3(o_h, o_s, o_v));
        }
        else if (s.outlineTintMode >= 2)
        {
            float3 dark_tint = dt_hsv_to_rgb(float3(base_hsv.x, clamp(base_hsv.y * 1.3, 0.0, 1.0), base_hsv.z * 0.35));
            line_col = lerp(dark_tint, dark_tint * l.diffuse * DT_PI, 0.6);
        }
        if (s.outlineLightingMix > 0.01)
        {
            line_col = lerp(line_col, line_col * l.diffuse * DT_PI, s.outlineLightingMix);
        }
        c = line_col;
    }
#endif

    return max(c * max(s.strength, 0.0), float3(0.0, 0.0, 0.0));
}

// ---------------------------------------------------------------------------------------------------------------
// Outline: gpu_shader_material_dask_outline.glsl (line colour) and the Geometry Nodes width of project 1, spec 4.3.

struct DTOutlineInput
{
    float3 baseColor;
    float3 outlineColor;
    float lightBleed;
    float tintDarkness;
    float tintSatBoost;
    float lightingMix;
    int tintMode;
};

// normalB: the hull's shading normal in Blender world space. diffuse: closure_eval(ClosureDiffuse) at that normal.
float3 dt_outline_color(DTOutlineInput s, float3 normalB, float3 diffuse)
{
    float3 base_rgb = max(s.baseColor, 0.0);
    float3 outline_rgb = max(s.outlineColor, 0.0);
    float3 N = normalize(normalB);
    float3 L = normalize(float3(0.5, 0.8, 0.6));
    float half_lambert = dot(N, L) * 0.5 + 0.5;

    float3 base_hsv = dt_rgb_to_hsv(base_rgb);
    float target_v = clamp(base_hsv.z * clamp(s.tintDarkness, 0.05, 1.0), 0.02, 0.95);
    float target_s = clamp(base_hsv.y * clamp(s.tintSatBoost, 0.5, 3.0), 0.10, 1.0);
    float3 harmonic_rgb = dt_hsv_to_rgb(float3(base_hsv.x, target_s, target_v));

    float3 line_rgb = outline_rgb;
    if (s.tintMode == 1)
    {
        line_rgb = harmonic_rgb;
        if (half_lambert > 0.7 && s.lightBleed > 0.2)
        {
            float glow_fac = (half_lambert - 0.7) * 3.33 * s.lightBleed;
            line_rgb = lerp(line_rgb, base_rgb, clamp(glow_fac, 0.0, 0.6));
        }
    }
    else if (s.tintMode >= 2)
    {
        line_rgb = lerp(harmonic_rgb, harmonic_rgb * (half_lambert * 0.8 + 0.2), 0.8);
    }

    float mix_fac = clamp(s.lightingMix, 0.0, 1.0);
    if (mix_fac > 0.001)
    {
        line_rgb = lerp(line_rgb, line_rgb * diffuse * DT_PI, mix_fac);
    }
    return line_rgb;
}

// Width of the Geometry Nodes hull (project 1, spec 4.3):
// light_thin = 1 - clamp((hl - 0.55) / 0.45) * bleed * 0.75, hl = dot(N, L) * 0.5 + 0.5,
// f(u, v) = sin(2u) cos(3v) + 0.5 sin(6.28v) with (u, v) = uv0 * 12.
float dt_outline_width(float width, float bleed, float wobble, float NdotL, float2 uv0, float mask)
{
    float hl = NdotL * 0.5 + 0.5;
    float light_thin = 1.0 - clamp((hl - 0.55) / 0.45, 0.0, 1.0) * bleed * 0.75;
    float u = uv0.x * 12.0;
    float v = uv0.y * 12.0;
    float f = sin(2.0 * u) * cos(3.0 * v) + 0.5 * sin(6.28 * v);
    return width * light_thin * (1.0 + 0.25 * wobble * f) * mask;
}

// Octahedral decode of DT_OutlineN (scripts/startup/bl_ui/dasktoon_outline_gamedata.py: oct_decode).
float3 dt_oct_decode(float2 e)
{
    float3 n = float3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y));
    float t = max(-n.z, 0.0);
    n.x += (n.x >= 0.0) ? -t : t;
    n.y += (n.y >= 0.0) ? -t : t;
    return normalize(n);
}

#endif // DASKTOON_CORE_INCLUDED
