/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_manga_hatching(float shading_fac,
                         float density,
                         float primary_angle,
                         float cross_angle,
                         float stroke_width,
                         float hatch_levels,
                         float4 ink_col,
                         float4 paper_col,
                         float3 uv,
                         float4 &out_color,
                         float &out_fac)
{
  ink_col = max(ink_col, float4(0.0f));
  paper_col = max(paper_col, float4(0.0f));

  float2 coord = (dot(uv, uv) > 1e-6f) ? uv.xy : (gl_FragCoord.xy * 0.005f);
  float d = max(density, 0.1f);

  /* Primary Hatching Line Pattern */
  float cos_p = cos(primary_angle);
  float sin_p = sin(primary_angle);
  float2 rot_p = float2(coord.x * cos_p - coord.y * sin_p, coord.x * sin_p + coord.y * cos_p) * d;
  float line1 = fract(rot_p.x);
  float h1 = step(stroke_width, line1);

  /* Secondary Cross-Hatching Pattern */
  float cos_c = cos(cross_angle);
  float sin_c = sin(cross_angle);
  float2 rot_c = float2(coord.x * cos_c - coord.y * sin_c, coord.x * sin_c + coord.y * cos_c) * d;
  float line2 = fract(rot_c.x);
  float h2 = step(stroke_width, line2);

  /* Tertiary Dense Vertical Pattern */
  float2 rot_t = float2(coord.x, coord.y) * (d * 1.5f);
  float line3 = fract(rot_t.x);
  float h3 = step(stroke_width * 0.8f, line3);

  /* Progressive Hatch Accumulation based on Darkness */
  float dark = clamp(1.0f - shading_fac, 0.0f, 1.0f);
  float hatch_result = 1.0f;

  if (dark < 0.25f) {
    /* Pure Lit Area */
    hatch_result = 1.0f;
  }
  else if (dark < 0.55f || hatch_levels < 1.5f) {
    /* Level 1: Single Hatch */
    hatch_result = h1;
  }
  else if (dark < 0.85f || hatch_levels < 2.5f) {
    /* Level 2: Cross Hatch */
    hatch_result = min(h1, h2);
  }
  else {
    /* Level 3: Triple Dense Hatch */
    hatch_result = min(min(h1, h2), h3);
  }

  out_fac = hatch_result;
  out_color = mix(ink_col, paper_col, hatch_result);
}
