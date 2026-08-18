/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dasktoon_grade_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dasktoon_grade_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_dask_grade(float4 in_color,
                     float4 color_filter,
                     float4 shadow_tint,
                     float4 highlight_tint,
                     float saturation,
                     float brightness,
                     float contrast,
                     float strength,
                     float weight,
                     Closure &out_bsdf,
                     float4 &out_color)
{
  float3 col = in_color.rgb;

  /* 1. Global Atmospheric Color Filter */
  col *= color_filter.rgb;

  /* 2. Split Toning: Shadow Tint vs Highlight Tint based on luminance */
  float lum = dot(col, float3(0.299f, 0.587f, 0.114f));
  float3 split_toned = mix(col * shadow_tint.rgb, col * highlight_tint.rgb, clamp(lum, 0.0f, 1.0f));
  col = split_toned;

  /* 3. Saturation / Vibrancy Control */
  if (abs(saturation - 1.0f) > 0.001f) {
    float3 hsv = dasktoon_grade_rgb_to_hsv(col);
    hsv.y = clamp(hsv.y * max(saturation, 0.0f), 0.0f, 1.0f);
    col = dasktoon_grade_hsv_to_rgb(hsv);
  }

  /* 4. Brightness & Contrast */
  col += brightness;
  col = (col - 0.5f) * (1.0f + contrast) + 0.5f;
  col = max(col, float3(0.0f));

  /* 5. Master Strength */
  col *= max(strength, 0.0f);

  /* 6. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = col;
  out_bsdf = closure_eval(emission_data);

  out_color = float4(col, 1.0f);
}
