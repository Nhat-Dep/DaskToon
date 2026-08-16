/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dasktoon_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dasktoon_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_anime_character(float3 N,
                          float strength,
                          float4 base_color,
                          float4 shadow_color,
                          float shadow_thresh,
                          float shadow_softness,
                          float4 ambient_color,
                          float ambient_blend,
                          float ambient_shadow_only,
                          float light_tint_strength,
                          float alpha,
                          float4 ao_color,
                          float ao_strength,
                          float use_ao,
                          float weight,
                          float ambient_mode,
                          float light_blend_mode,
                          Closure &result)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  ambient_color = max(ambient_color, float4(0.0f));
  ao_color = max(ao_color, float4(0.0f));
  N = safe_normalize(N);

  /* 1. Extract Forward Radiance from all Scene Lamps */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float light_intensity = max(max(light_rgba.r, light_rgba.g), light_rgba.b);
  float3 lamp_tint = (light_intensity > 0.001f) ? (light_rgba.rgb / light_intensity) : float3(1.0f);

  float3 lit_col = base_color.rgb;

  /* 2. Active Light Blend Mode on Lit Color */
  int l_mode = int(round(light_blend_mode));
  float tint_str = clamp(light_tint_strength, 0.0f, 2.0f);

  if (l_mode == 0) {
    /* 0: OVERLAY (Standard natural lighting tint) */
    float3 over_dark = 2.0f * lit_col * lamp_tint;
    float3 over_bright = float3(1.0f) - 2.0f * (float3(1.0f) - lit_col) * (float3(1.0f) - lamp_tint);
    float3 over_lit = mix(over_dark, over_bright, step(float3(0.5f), lit_col));
    lit_col = mix(lit_col, over_lit, tint_str);
  }
  else if (l_mode == 1) {
    /* 1: HUE (Hue Tint) */
    float3 b_hsv = dasktoon_rgb_to_hsv(lit_col);
    float3 l_hsv = dasktoon_rgb_to_hsv(lamp_tint);
    float3 h_hsv = float3(mix(b_hsv.x, l_hsv.x, tint_str), b_hsv.y, b_hsv.z);
    lit_col = dasktoon_hsv_to_rgb(h_hsv);
  }
  else if (l_mode == 2) {
    /* 2: MULTIPLY */
    lit_col = mix(lit_col, lit_col * lamp_tint, tint_str);
  }
  else if (l_mode == 3) {
    /* 3: ADD (Magic/Neon Glow) */
    lit_col = lit_col + lamp_tint * tint_str * 0.5f;
  }
  /* 4: PURE_CEL -> Keep lit_col pure */

  /* 3. Active Ambient Mode on Shadow Color */
  float3 amb_rgb = ambient_color.rgb;
  float blend_fac = clamp(ambient_blend * ambient_color.a, 0.0f, 1.0f);
  float3 sh_hsv = dasktoon_rgb_to_hsv(shadow_color.rgb);
  float3 amb_hsv = dasktoon_rgb_to_hsv(amb_rgb);

  float3 final_shadow = shadow_color.rgb;
  int amb_m = int(round(ambient_mode));

  if (amb_m == 0) {
    /* 0: OVERLAY (Classic Anime Movie) */
    float3 over_dark = 2.0f * shadow_color.rgb * amb_rgb;
    float3 over_bright = float3(1.0f) - 2.0f * (float3(1.0f) - shadow_color.rgb) * (float3(1.0f) - amb_rgb);
    float3 over = mix(over_dark, over_bright, step(float3(0.5f), shadow_color.rgb));
    final_shadow = mix(shadow_color.rgb, over, blend_fac);
  }
  else if (amb_m == 1) {
    /* 1: HUE ONLY */
    float3 res_hsv = float3(mix(sh_hsv.x, amb_hsv.x, blend_fac), sh_hsv.y, sh_hsv.z);
    final_shadow = dasktoon_hsv_to_rgb(res_hsv);
  }
  else if (amb_m == 2) {
    /* 2: HUE_SAT (Anime Standard) */
    float3 res_hsv = float3(mix(sh_hsv.x, amb_hsv.x, blend_fac), mix(sh_hsv.y, amb_hsv.y, blend_fac), sh_hsv.z);
    final_shadow = dasktoon_hsv_to_rgb(res_hsv);
  }
  else if (amb_m == 3) {
    /* 3: SAT ONLY */
    float3 res_hsv = float3(sh_hsv.x, mix(sh_hsv.y, amb_hsv.y, blend_fac), sh_hsv.z);
    final_shadow = dasktoon_hsv_to_rgb(res_hsv);
  }
  else if (amb_m == 4) {
    /* 4: VAL ONLY */
    float3 res_hsv = float3(sh_hsv.x, sh_hsv.y, mix(sh_hsv.z, amb_hsv.z * sh_hsv.z, blend_fac));
    final_shadow = dasktoon_hsv_to_rgb(res_hsv);
  }
  else if (amb_m == 5) {
    /* 5: MULTIPLY */
    final_shadow = mix(shadow_color.rgb, shadow_color.rgb * amb_rgb, blend_fac);
  }
  else {
    /* 6: MIX */
    final_shadow = mix(shadow_color.rgb, amb_rgb, blend_fac);
  }

  if (ambient_shadow_only < 0.5f) {
    lit_col = mix(lit_col, lit_col * amb_rgb, blend_fac * 0.5f);
  }

  /* 4. Ambient Occlusion (AO) */
  final_shadow = mix(final_shadow, ao_color.rgb * final_shadow, clamp(ao_strength * use_ao, 0.0f, 1.0f));

  /* 5. True Discrete Anime Cel Shading Calculation */
  float s_soft = max(shadow_softness, 0.001f);
  float s_min = clamp(shadow_thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(shadow_thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  float cel_factor = smoothstep(s_min, s_max, light_intensity);

  /* 6. Blend Shadow & Lit Color */
  float3 surface_color = mix(final_shadow, lit_col, cel_factor);
  surface_color = clamp(surface_color * max(strength, 0.0f), 0.0f, 10.0f);

  /* 7. Output Emission Closure */
  float w = (weight > 0.0001f) ? weight : 1.0f;

  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = surface_color;
  Closure emission_cl = closure_eval(emission_data);

  float final_alpha = clamp(alpha * base_color.a, 0.0f, 1.0f);
  if (final_alpha < 0.999f) {
    ClosureTransparency trans_data;
    trans_data.weight = w;
    trans_data.transmittance = float3(1.0f - final_alpha);
    trans_data.holdout = 0.0f;
    Closure trans_cl = closure_eval(trans_data);
    result = closure_add(emission_cl, trans_cl);
  }
  else {
    result = emission_cl;
  }
}
