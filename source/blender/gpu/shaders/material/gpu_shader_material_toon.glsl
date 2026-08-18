/* SPDX-FileCopyrightText: 2019-2022 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_bsdf_toon(
    float4 color, float size, float tsmooth, float3 N, float weight, Closure &result)
{
  color = max(color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = clamp(dot(N, V), 0.0f, 1.0f);

  float s_soft = max(tsmooth, 0.001f);
  float s_min = clamp(1.0f - size - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(1.0f - size + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  float toon_fac = smoothstep(s_min, s_max, facing);

  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight;
  diffuse_data.color = color.rgb * toon_fac;
  diffuse_data.N = N;

  result = closure_eval(diffuse_data);
}
