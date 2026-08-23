/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_knit(float4 wool_color,
                      float4 shadow_color,
                      float4 fuzz_color,
                      float knit_scale,
                      float knit_depth,
                      float fuzz_power,
                      float fuzz_width,
                      float yarn_thickness,
                      float3 N,
                      float3 local_pos,
                      float weight,
                      Closure &result,
                      float4 &out_color,
                      float &out_knit_bump,
                      float &out_fuzz_mask)
{
  wool_color = max(wool_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  fuzz_color = max(fuzz_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Procedural V-Stitch Cable-Knit Loop Pattern (Mũi đan len chữ V) */
  float k_scale = max(knit_scale, 0.5f);
  float2 uv = float2(local_pos.x, local_pos.y) * k_scale * 15.0f;
  
  /* Stagger alternating rows */
  float row = floor(uv.y);
  if (mod(row, 2.0f) > 0.5f) {
    uv.x += 0.5f;
  }
  
  float2 f_uv = fract(uv) - 0.5f;
  /* V-shaped stitch math: abs(x) - y */
  float v_shape = abs(f_uv.x * 2.0f) - f_uv.y;
  float stitch_loop = sin(v_shape * 3.14159f) * sin(f_uv.y * 3.14159f);
  float stitch_bump = clamp(stitch_loop * yarn_thickness * 1.5f, -1.0f, 1.0f);
  out_knit_bump = stitch_bump;

  /* Knit crevice shading */
  float depth_fac = clamp(knit_depth, 0.0f, 1.0f);
  float crevice_shadow = 1.0f - max(0.0f, -stitch_bump) * depth_fac * 0.6f;
  float3 wool_albedo = wool_color.rgb * crevice_shadow;

  /* 2. Soft Peach Fuzz / Wool Fiber Rim (Lông tơ len viền mềm) */
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);
  float f_pow = max(fuzz_power, 0.1f);
  float f_raw = pow(rim, f_pow);
  float f_w = clamp(fuzz_width, 0.01f, 1.0f);
  float fuzz_mask = smoothstep(1.0f - f_w, 1.0f, f_raw);
  out_fuzz_mask = fuzz_mask;

  /* Add warm fuzz glow to silhouette */
  wool_albedo += fuzz_color.rgb * fuzz_mask * fuzz_color.a * 0.7f;

  out_color = float4(wool_albedo, wool_color.a);

  /* 3. Deep Warm Cel Shading for Thick Knit Wear */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight;
  diffuse_data.color = wool_albedo;
  diffuse_data.N = N;
  Closure lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = shadow_color.rgb * wool_albedo * 0.25f;
  Closure shadow_cl = closure_eval(emission_data);

  result = closure_add(shadow_cl, lit_cl);
}
