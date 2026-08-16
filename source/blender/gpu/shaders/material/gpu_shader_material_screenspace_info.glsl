/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_screenspace_info(float3 &out_screen_uv,
                           float &out_scene_depth,
                           float4 &out_scene_color,
                           float3 &out_pixel_size,
                           float &out_aspect_ratio)
{
  float2 uv = gl_FragCoord.xy;
  out_screen_uv = float3(uv, 0.0f);
  out_scene_depth = gl_FragCoord.z;
  out_scene_color = float4(0.0f, 0.0f, 0.0f, 1.0f);
  out_pixel_size = float3(1.0f, 1.0f, 0.0f);
  out_aspect_ratio = 1.0f;
}
