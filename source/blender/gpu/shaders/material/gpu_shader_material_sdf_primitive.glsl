/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_sdf_primitive(float3 p,
                        float3 size,
                        float radius,
                        float &out_dist)
{
  /* Sphere / Circle SDF */
  out_dist = length(p) - radius;
}
