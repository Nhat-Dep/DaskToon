/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_rim(float4 rim_color,
                    float rim_power,
                    float rim_width,
                    float rim_softness,
                    float3 N,
                    float weight,
                    Closure &emission_result,
                    float4 &out_color)
{
  rim_color = max(rim_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);

  rim_power = max(rim_power, 0.01f);
  rim = pow(rim, rim_power);

  float w = clamp(rim_width, 0.0f, 1.0f);
  float s = max(rim_softness, 0.001f);
  float rim_min = clamp(1.0f - w - s * 0.5f, 0.0f, 1.0f);
  float rim_max = clamp(1.0f - w + s * 0.5f, rim_min + 0.0001f, 1.0f);
  float rim_factor = smoothstep(rim_min, rim_max, rim);

  out_color = float4(rim_color.rgb * rim_factor, rim_color.a * rim_factor);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = out_color.rgb;

  emission_result = closure_eval(emission_data);
}
