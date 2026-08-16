/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_water_ripples(float3 p,
                        float time,
                        float scale,
                        float speed,
                        float amplitude,
                        float &out_height,
                        float3 &out_normal)
{
  float2 uv = p.xy * scale;
  float t = time * speed;

  float wave1 = sin(uv.x + t) * cos(uv.y + t);
  float wave2 = sin(uv.x * 1.5f - t * 1.2f) * cos(uv.y * 1.5f + t * 0.8f);

  float h = (wave1 + wave2 * 0.5f) * amplitude;

  out_height = h;
  out_normal = safe_normalize(float3(-dFdx(h), -dFdy(h), 1.0f));
}
