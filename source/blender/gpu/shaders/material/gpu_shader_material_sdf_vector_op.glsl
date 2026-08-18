/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_sdf_vector_op(float3 p,
                        float3 translation,
                        float3 rotation,
                        float3 scale,
                        float3 &out_p)
{
  float3 res = p - translation;

  /* Scale */
  scale = max(abs(scale), float3(0.0001f));
  res = res / scale;

  out_p = res;
}
