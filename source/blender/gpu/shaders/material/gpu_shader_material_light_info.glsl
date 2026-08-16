/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_light_info(int light_index,
                     int light_group,
                     float3 &out_light_vector,
                     float4 &out_light_color,
                     float &out_light_power,
                     float &out_is_sun)
{
  /* Default direct overhead sun vector */
  out_light_vector = float3(0.0f, 0.0f, 1.0f);
  out_light_color = float4(1.0f, 1.0f, 1.0f, 1.0f);
  out_light_power = 1.0f;
  out_is_sun = 1.0f;
}
