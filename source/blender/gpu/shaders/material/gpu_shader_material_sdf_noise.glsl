/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float dasktoon_hash(float3 p)
{
  p = fract(p * 0.3183099f + 0.1f);
  p *= 17.0f;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float dasktoon_noise(float3 x)
{
  float3 p = floor(x);
  float3 f = fract(x);
  f = f * f * (3.0f - 2.0f * f);

  return mix(mix(mix(dasktoon_hash(p + float3(0, 0, 0)),
                     dasktoon_hash(p + float3(1, 0, 0)),
                     f.x),
                 mix(dasktoon_hash(p + float3(0, 1, 0)),
                     dasktoon_hash(p + float3(1, 1, 0)),
                     f.x),
                 f.y),
             mix(mix(dasktoon_hash(p + float3(0, 0, 1)),
                     dasktoon_hash(p + float3(1, 0, 1)),
                     f.x),
                 mix(dasktoon_hash(p + float3(0, 1, 1)),
                     dasktoon_hash(p + float3(1, 1, 1)),
                     f.x),
                 f.y),
             f.z);
}

[[node]]
void node_sdf_noise(float3 p,
                    float scale,
                    float roughness,
                    float distortion,
                    float &out_noise,
                    float4 &out_color)
{
  float n = dasktoon_noise(p * scale);
  out_noise = n;
  out_color = float4(n, n, n, 1.0f);
}
