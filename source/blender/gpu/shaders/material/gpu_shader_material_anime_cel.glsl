/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dasktoon_cel_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dasktoon_cel_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_anime_cel(float4 base_color,
                    float4 shadow_color,
                    float shadow_thresh,
                    float shadow_softness,
                    float4 ambient_color,
                    float ambient_blend,
                    float ambient_shadow_only,
                    float light_tint_strength,
                    float4 spec_color,
                    float spec_size,
                    float spec_softness,
                    float3 N,
                    float weight,
                    Closure &result,
                    float4 &out_color)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  ambient_color = max(ambient_color, float4(0.0f));
  spec_color = max(spec_color, float4(0.0f));
  N = safe_normalize(N);

  /* 1. Advanced World Ambient Blend (HSV Hue Shift) */
  float3 amb_rgb = ambient_color.rgb;
  float blend_fac = clamp(ambient_blend * ambient_color.a, 0.0f, 1.0f);
  float3 sh_hsv = dasktoon_cel_rgb_to_hsv(shadow_color.rgb);
  float3 amb_hsv = dasktoon_cel_rgb_to_hsv(amb_rgb);
  float3 res_hsv = float3(mix(sh_hsv.x, amb_hsv.x, blend_fac), mix(sh_hsv.y, amb_hsv.y, blend_fac), sh_hsv.z);
  float3 shadow_amb = dasktoon_cel_hsv_to_rgb(res_hsv);

  float3 final_shadow = shadow_amb;
  float3 lit_col = base_color.rgb;
  if (ambient_shadow_only < 0.5f) {
    lit_col = mix(lit_col, lit_col * amb_rgb, blend_fac * 0.5f);
  }

  out_color = float4(lit_col, base_color.a);

  /* 2. True 3D Multi-Light Cel BSDF (No Fresnel for Shadow!):
   * - Diffuse closure carries the true surface normal N to calculate light direction from all scene lamps. */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight * clamp(light_tint_strength, 0.0f, 2.0f);
  diffuse_data.color = lit_col;
  diffuse_data.N = N;
  Closure direct_lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = final_shadow * 0.15f;
  Closure shadow_base_cl = closure_eval(emission_data);

  result = closure_add(shadow_base_cl, direct_lit_cl);
}
