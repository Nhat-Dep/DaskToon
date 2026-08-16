/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_manga_screentone(float shading_fac,
                                 float dot_scale,
                                 float dot_angle,
                                 float dot_sharpness,
                                 float4 ink_col,
                                 float4 paper_col,
                                 float3 uv,
                                 float4 &out_color,
                                 float &out_fac)
{
  ink_col = max(ink_col, float4(0.0f));
  paper_col = max(paper_col, float4(0.0f));

  /* Use custom UV if linked, otherwise fallback to 2D Screen-space / Window coordinates */
  float2 coord = (dot(uv, uv) > 1e-6f) ? uv.xy : (gl_FragCoord.xy * 0.005f);

  /* Rotate coordinates */
  float cos_a = cos(dot_angle);
  float sin_a = sin(dot_angle);
  float2 rot_coord = float2(coord.x * cos_a - coord.y * sin_a, coord.x * sin_a + coord.y * cos_a) * max(dot_scale, 0.1f);

  /* Compute 2D Halftone dot matrix via 2D periodic cosine harmonics */
  float dot_pattern = (cos(rot_coord.x * 6.283185f) * cos(rot_coord.y * 6.283185f)) * 0.5f + 0.5f;

  /* Quantize / Threshold with Shading Factor */
  float s_soft = max(dot_sharpness, 0.001f);
  float d_min = clamp(shading_fac - s_soft * 0.5f, 0.0f, 1.0f);
  float d_max = clamp(shading_fac + s_soft * 0.5f, d_min + 0.0001f, 1.0f);
  float dot_fac = smoothstep(d_min, d_max, dot_pattern);

  out_fac = dot_fac;
  out_color = mix(ink_col, paper_col, dot_fac);
}
