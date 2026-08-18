/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_twirl(float3 p,
                float3 center,
                float strength,
                float radius,
                float3 &out_p)
{
  float2 d = p.xy - center.xy;
  float dist = length(d);

  if (dist < radius) {
    float percent = (radius - dist) / radius;
    float theta = percent * percent * strength;
    float s = sin(theta);
    float c = cos(theta);
    d = float2(dot(d, float2(c, -s)), dot(d, float2(s, c)));
  }

  out_p = float3(center.xy + d, p.z);
}
