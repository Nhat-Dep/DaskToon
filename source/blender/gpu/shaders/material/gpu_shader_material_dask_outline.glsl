/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_dask_outline(float outline_width,
                       float4 outline_color,
                       float outline_lighting_mix,
                       float weight,
                       Closure &out_bsdf,
                       float4 &out_color,
                       float &out_width)
{
  outline_color = max(outline_color, float4(0.0f));
  float3 base_col = outline_color.rgb;

  /* Calculate lighting if lighting mix is enabled */
  float mix_fac = clamp(outline_lighting_mix, 0.0f, 1.0f);
  float3 final_rgb = base_col;
  if (mix_fac > 0.001f) {
    ClosureDiffuse diff_in;
    diff_in.weight = 1.0f;
    diff_in.color = float3(1.0f);
    diff_in.N = float3(0.0f, 0.0f, 1.0f);
    Closure raw_diff = closure_eval(diff_in);
    float4 light_rgba = closure_to_rgba(raw_diff);
    float3 light_col = light_rgba.rgb * 3.14159265f;
    final_rgb = mix(base_col, base_col * light_col, mix_fac);
  }

  /* Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = final_rgb;
  out_bsdf = closure_eval(emission_data);

  out_color = float4(final_rgb, 1.0f);
  out_width = max(outline_width, 0.0f);
}
