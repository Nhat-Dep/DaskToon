/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_sdf_op(float d1,
                 float d2,
                 float k,
                 float &out_union,
                 float &out_subtract,
                 float &out_intersect,
                 float &out_smooth_union)
{
  out_union = min(d1, d2);
  out_subtract = max(d1, -d2);
  out_intersect = max(d1, d2);

  /* Smooth minimum / smooth union */
  float h = clamp(0.5f + 0.5f * (d2 - d1) / max(k, 0.0001f), 0.0f, 1.0f);
  out_smooth_union = mix(d2, d1, h) - k * h * (1.0f - h);
}
