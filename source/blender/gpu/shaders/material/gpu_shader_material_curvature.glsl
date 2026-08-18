/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_curvature(float3 N,
                    float radius,
                    float contrast,
                    float invert,
                    float &out_curvature,
                    float &out_cavity,
                    float &out_ridge)
{
  N = safe_normalize(N);

  /* 8-direction screen-space normal derivative curvature estimation */
  float3 dNdx = dFdx(N) * radius;
  float3 dNdy = dFdy(N) * radius;

  float curv_x = length(dNdx);
  float curv_y = length(dNdy);
  float curv = (curv_x + curv_y) * 0.5f * contrast;

  if (invert > 0.5f) {
    curv = 1.0f - curv;
  }

  out_curvature = clamp(curv, 0.0f, 1.0f);
  out_cavity = clamp(curv * step(0.0f, dNdx.x + dNdy.y), 0.0f, 1.0f);
  out_ridge = clamp(curv * step(0.0f, -(dNdx.x + dNdy.y)), 0.0f, 1.0f);
}
