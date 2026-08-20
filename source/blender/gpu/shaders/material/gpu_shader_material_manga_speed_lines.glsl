/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_manga_speed_lines(float center_x,
                            float center_y,
                            float ray_density,
                            float inner_radius,
                            float line_sharpness,
                            float jitter,
                            float4 ink_col,
                            float4 bg_col,
                            float3 uv,
                            float4 &out_color,
                            float &out_alpha)
{
  ink_col = max(ink_col, float4(0.0f));
  bg_col = max(bg_col, float4(0.0f));

  float2 coord = (dot(uv, uv) > 1e-6f) ? uv.xy : (gl_FragCoord.xy * 0.002f);
  float2 center = float2(center_x, center_y);
  float2 delta = coord - center;

  float r = length(delta);
  float theta = atan(delta.y, delta.x) + 3.14159265f;

  /* Angular ray segmentation */
  float ray_num = (theta / 6.2831853f) * max(ray_density, 4.0f);
  float ray_idx = floor(ray_num);
  float ray_frac = fract(ray_num);

  /* Pseudo-random jitter based on ray index */
  float rnd = fract(sin(ray_idx * 127.1f) * 43758.5453f);
  float dynamic_inner = inner_radius * (1.0f + (rnd - 0.5f) * jitter);
  float ray_width = 0.5f + (rnd - 0.5f) * 0.3f * jitter;

  /* Radial distance mask */
  float rad_mask = smoothstep(dynamic_inner, dynamic_inner + max(line_sharpness, 0.01f), r);

  /* Angular ray sharp wedge */
  float ray_wedge = 1.0f - abs(ray_frac - 0.5f) * 2.0f;
  float line_mask = step(1.0f - ray_width, ray_wedge);

  float final_alpha = rad_mask * line_mask * ink_col.a;
  out_alpha = clamp(final_alpha, 0.0f, 1.0f);
  out_color = mix(bg_col, ink_col, final_alpha);
}
