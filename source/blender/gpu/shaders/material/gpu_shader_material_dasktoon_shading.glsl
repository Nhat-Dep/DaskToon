/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/* Shared DaskToon stylized shading core used by Anime BSDF, Anime Cel and Dask Cel.
 * Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md (3.2, 3.3, 3.10). */

#include "gpu_shader_common_color_ramp.glsl"

float3 dt_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dt_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

/* Rec.709 luminance, identical to Blender's default OCIO luminance coefficients. */
float dt_luminance(float3 c)
{
  return dot(c, float3(0.2126f, 0.7152f, 0.0722f));
}

float3 dt_overlay(float3 a, float3 b)
{
  return mix(2.0f * a * b, 1.0f - 2.0f * (1.0f - a) * (1.0f - b), step(float3(0.5f), a));
}

float3 dt_light_norm(float3 light_col)
{
  float l_max = max(max(light_col.r, light_col.g), light_col.b);
  return (l_max > 0.001f) ? (light_col / l_max) : float3(1.0f);
}

float3 dt_shade_simple(
    float light, float3 base, float3 shadow, float thresh, float softness, float &cel)
{
  float s_soft = max(softness, 0.001f);
  float s_min = clamp(thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  cel = smoothstep(s_min, s_max, light);
  float3 auto_shadow = base * shadow * 1.25f;
  float3 final_shadow = (length(shadow) > 0.001f) ? mix(shadow, auto_shadow, 0.75f) : base * 0.5f;
  return mix(final_shadow, base, cel);
}

float3 dt_ramp_color(sampler1DArray ramp, float layer, float is_constant, float t)
{
  float4 col;
  float alpha;
  if (is_constant > 0.5f) {
    valtorgb_nearest(t, ramp, layer, col, alpha);
  }
  else {
    valtorgb(t, ramp, layer, col, alpha);
  }
  return col.rgb;
}

float3 dt_shade_ramp(float light,
                     float3 base,
                     float thresh,
                     sampler1DArray ramp,
                     float layer,
                     float is_constant,
                     float &cel)
{
  float t = clamp(light + 0.5f - thresh, 0.0f, 1.0f);
  float3 tint = dt_ramp_color(ramp, layer, is_constant, t);
  float lum_dark = dt_luminance(dt_ramp_color(ramp, layer, is_constant, 0.0f));
  float lum_lit = dt_luminance(dt_ramp_color(ramp, layer, is_constant, 1.0f));
  cel = clamp((dt_luminance(tint) - lum_dark) / max(lum_lit - lum_dark, 0.0001f), 0.0f, 1.0f);
  return base * tint;
}

/* Ambient Mode (spec 3.10): 0 OVERLAY, 1 HUE, 2 HUE_SAT, 3 SAT, 4 VAL, 5 MULTIPLY, 6 MIX. */
float3 dt_ambient_mode(float3 a, float3 b, int mode)
{
  if (mode == 0) {
    return dt_overlay(a, b);
  }
  if (mode == 5) {
    return a * b;
  }
  if (mode < 1 || mode > 4) {
    return b;
  }
  float3 ha = dt_rgb_to_hsv(a);
  float3 hb = dt_rgb_to_hsv(b);
  if (mode == 1) {
    ha.x = hb.x;
  }
  else if (mode == 2) {
    ha.x = hb.x;
    ha.y = mix(ha.y, hb.y, 0.65f);
  }
  else if (mode == 3) {
    ha.y = hb.y;
  }
  else {
    ha.z = hb.z;
  }
  return dt_hsv_to_rgb(ha);
}

/* Light Mode (spec 3.10): 0 OVERLAY, 1 HUE, 2 MULTIPLY, 3 ADD, 4 PURE_CEL. */
float3 dt_light_mode(float3 c, float3 light_col, float3 light_norm, float strength, int mode)
{
  float s = clamp(strength, 0.0f, 2.0f);
  float3 ls = mix(float3(1.0f), light_norm, s);
  if (mode == 0) {
    return dt_overlay(c, ls);
  }
  if (mode == 1) {
    float3 hc = dt_rgb_to_hsv(c);
    float3 hl = dt_rgb_to_hsv(light_norm);
    float3 tinted = dt_hsv_to_rgb(float3(hl.x, hc.y, hc.z));
    return mix(c, tinted, clamp(s, 0.0f, 1.0f) * hl.y);
  }
  if (mode == 2) {
    return c * ls;
  }
  if (mode == 3) {
    return c + (light_col - min(min(light_col.r, light_col.g), light_col.b)) * s;
  }
  return c;
}
