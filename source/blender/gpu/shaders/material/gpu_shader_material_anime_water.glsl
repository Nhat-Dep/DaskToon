/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float dasktoon_water_noise(float2 p)
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
void node_anime_water(float4 shallow_color,
                      float4 deep_color,
                      float4 foam_color,
                      float4 caustics_color,
                      float depth_steepness,
                      float foam_width,
                      float caustics_scale,
                      float caustics_speed,
                      float opacity,
                      float3 N,
                      float3 local_pos,
                      float weight,
                      Closure &result,
                      float4 &out_color,
                      float &out_foam_mask)
{
  shallow_color = max(shallow_color, float4(0.0f));
  deep_color = max(deep_color, float4(0.0f));
  foam_color = max(foam_color, float4(0.0f));
  caustics_color = max(caustics_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Stepped Anime Water Depth Gradient */
  float depth_fac = clamp(pow(1.0f - facing, max(depth_steepness, 0.1f)), 0.0f, 1.0f);
  /* Stepped quantization (Anime 2-step depth) */
  float step_depth = floor(depth_fac * 3.0f) / 3.0f;
  float3 water_body = mix(shallow_color.rgb, deep_color.rgb, step_depth);

  /* 2. Animated Voronoi-like Anime Caustics (Gợn nắng đáy nước) */
  float c_scale = max(caustics_scale, 0.1f);
  float time_offset = local_pos.z * 2.0f; // Can use spatial phase or time
  float2 c_uv = float2(local_pos.x, local_pos.y) * c_scale * 5.0f;

  float n1 = dasktoon_water_noise(c_uv + float2(time_offset * caustics_speed, 0.0f));
  float n2 = dasktoon_water_noise(c_uv * 1.5f - float2(0.0f, time_offset * caustics_speed));
  float caustics_val = pow(clamp(n1 * n2 * 4.0f, 0.0f, 1.0f), 3.0f);

  /* 3. White Foam Edge (Viền bọt sóng mép bờ) */
  float f_width = clamp(foam_width, 0.01f, 1.0f);
  float foam_mask = smoothstep(1.0f - f_width, 1.0f, 1.0f - facing);
  out_foam_mask = foam_mask;

  /* 4. Composite Cel Water */
  float3 final_water = water_body + caustics_color.rgb * caustics_val * caustics_color.a;
  final_water = mix(final_water, foam_color.rgb, foam_mask * foam_color.a);
  float final_alpha = clamp(mix(opacity, 1.0f, foam_mask), 0.0f, 1.0f);

  out_color = float4(final_water, final_alpha);

  /* 5. True Alpha Transparency & Water Closure */
  ClosureTransparency transparency_data;
  transparency_data.weight = weight * clamp(1.0f - final_alpha, 0.0f, 1.0f);
  transparency_data.transmittance = shallow_color.rgb;
  transparency_data.holdout = 0.0f;
  Closure trans_cl = closure_eval(transparency_data);

  ClosureEmission emission_data;
  emission_data.weight = weight * clamp(final_alpha, 0.0f, 1.0f);
  emission_data.emission = final_water;
  Closure solid_cl = closure_eval(emission_data);

  result = closure_add(trans_cl, solid_cl);
}
