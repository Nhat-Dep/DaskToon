/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_depth_info(float near_dist,
                     float far_dist,
                     float curve_exponent,
                     float4 &out_depth_map,
                     float &out_linear_depth,
                     float &out_normalized_depth,
                     float &out_inverse_depth,
                     float &out_radial_dist,
                     float &out_screen_depth,
                     float &out_depth_fade)
{
  float3 vP;
  point_transform_world_to_view(g_data.P, vP);

  float linear_z = abs(vP.z);
  float radial_d = length(vP);
  float screen_z = gl_FragCoord.z;

  near_dist = max(near_dist, 0.0f);
  far_dist = max(far_dist, near_dist + 1.0e-4f);
  curve_exponent = max(curve_exponent, 0.01f);

  float range = far_dist - near_dist;
  float norm_d = clamp((linear_z - near_dist) / range, 0.0f, 1.0f);
  norm_d = pow(norm_d, curve_exponent);

  float inv_d = 1.0f - norm_d;
  float fade_d = smoothstep(near_dist, far_dist, linear_z);

  out_depth_map = float4(norm_d, norm_d, norm_d, 1.0f);
  out_linear_depth = linear_z;
  out_normalized_depth = norm_d;
  out_inverse_depth = inv_d;
  out_radial_dist = radial_d;
  out_screen_depth = screen_z;
  out_depth_fade = fade_d;
}
