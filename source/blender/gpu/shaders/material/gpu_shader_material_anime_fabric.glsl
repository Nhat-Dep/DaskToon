/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_fabric(float4 base_color,
                        float4 shadow_color,
                        float4 sheen_color,
                        float4 silk_shift_color,
                        float sheen_power,
                        float sheen_width,
                        float silk_blend,
                        float crease_darkness,
                        float weave_scale,
                        float weave_strength,
                        float3 N,
                        float3 local_pos,
                        float weight,
                        Closure &result,
                        float4 &out_color,
                        float &out_sheen_mask)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  sheen_color = max(sheen_color, float4(0.0f));
  silk_shift_color = max(silk_shift_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Procedural Micro-Weave Pattern */
  float w_scale = max(weave_scale, 0.1f);
  float2 uv = float2(local_pos.x, local_pos.y) * w_scale * 50.0f;
  float weave = sin(uv.x) * sin(uv.y);
  float weave_fac = 1.0f + weave * clamp(weave_strength, 0.0f, 0.5f);

  /* 2. Velvet / Micro-Fiber Rim Sheen */
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);
  float s_pow = max(sheen_power, 0.1f);
  float sheen_raw = pow(rim, s_pow);
  float s_w = clamp(sheen_width, 0.01f, 1.0f);
  float sheen_mask = smoothstep(1.0f - s_w, 1.0f, sheen_raw);
  out_sheen_mask = sheen_mask;

  /* 3. Two-Tone Silk/Satin Color Shift */
  float silk_fac = clamp(pow(rim, 1.5f) * silk_blend, 0.0f, 1.0f);
  float3 fabric_albedo = mix(base_color.rgb * weave_fac, silk_shift_color.rgb, silk_fac);

  /* Add velvet sheen on top */
  fabric_albedo += sheen_color.rgb * sheen_mask * sheen_color.a;

  /* 4. Crease & Shadow tint */
  float crease_fac = clamp(crease_darkness, 0.0f, 1.0f);
  float3 final_shadow = mix(shadow_color.rgb * base_color.rgb, shadow_color.rgb * (1.0f - crease_fac * 0.5f), 0.5f);

  out_color = float4(fabric_albedo, base_color.a);

  /* 5. Diffuse Cel Lighting */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight;
  diffuse_data.color = fabric_albedo;
  diffuse_data.N = N;
  Closure lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = final_shadow * 0.2f;
  Closure shadow_cl = closure_eval(emission_data);

  result = closure_add(shadow_cl, lit_cl);
}
