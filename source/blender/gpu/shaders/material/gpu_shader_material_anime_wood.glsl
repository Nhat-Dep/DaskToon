/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float dasktoon_wood_noise(float2 p)
{
  float2 i = floor(p);
  float2 f = fract(p);
  f = f * f * (3.0f - 2.0f * f);
  float n = i.x + i.y * 57.0f;
  float a = fract(sin(n) * 43758.5453f);
  float b = fract(sin(n + 1.0f) * 43758.5453f);
  float c = fract(sin(n + 57.0f) * 43758.5453f);
  float d = fract(sin(n + 58.0f) * 43758.5453f);
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

[[node]]
void node_anime_wood(float4 base_color,
                      float4 grain_color,
                      float4 shadow_color,
                      float grain_scale,
                      float grain_distortion,
                      float grain_contrast,
                      float shadow_thresh,
                      float shadow_softness,
                      float edge_wear,
                      float3 N,
                      float3 local_pos,
                      float weight,
                      Closure &result,
                      float4 &out_color,
                      float &out_grain_mask)
{
  base_color = max(base_color, float4(0.0f));
  grain_color = max(grain_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  N = safe_normalize(N);

  /* 1. Procedural Anime Wood Grain (Ghibli / Hand-painted streak pattern) */
  float scale = max(grain_scale, 0.001f);
  float dist = grain_distortion * 2.0f;
  float2 uv = float2(local_pos.x, local_pos.y) * scale;

  float n1 = dasktoon_wood_noise(uv * 1.5f);
  float n2 = dasktoon_wood_noise(uv * 4.0f + float2(n1 * dist, n1 * dist));
  float grain_val = sin(uv.y * 8.0f + (n1 + n2 * 0.5f) * dist * 4.0f);
  grain_val = clamp((grain_val * 0.5f + 0.5f), 0.0f, 1.0f);

  /* Contrast curve */
  float c_power = max(grain_contrast, 0.1f);
  float grain_mask = pow(grain_val, c_power);
  out_grain_mask = grain_mask;

  /* Composite Wood Albedo */
  float3 wood_albedo = mix(base_color.rgb, grain_color.rgb, grain_mask * grain_color.a);

  /* 2. Edge Wear / Weathering on sharp curves */
  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));
  float edge_factor = smoothstep(0.4f, 0.1f, facing) * clamp(edge_wear, 0.0f, 1.0f);
  wood_albedo = mix(wood_albedo, base_color.rgb * 1.25f + float3(0.08f, 0.06f, 0.04f), edge_factor);

  out_color = float4(wood_albedo, base_color.a);

  /* 3. True Cel Shading with Warm Wood Shadow */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight;
  diffuse_data.color = wood_albedo;
  diffuse_data.N = N;
  Closure lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = shadow_color.rgb * wood_albedo * 0.25f;
  Closure shadow_cl = closure_eval(emission_data);

  result = closure_add(shadow_cl, lit_cl);
}
