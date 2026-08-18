/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_dask_light(float3 N,
                     float light_tint_strength,
                     float weight,
                     const float light_blend_mode,
                     Closure &out_bsdf,
                     float4 &out_color,
                     float &out_intensity)
{
  N = safe_normalize(N);

  /* Extract Scene Lighting from all Lamps */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float3 light_col = light_rgba.rgb;
  float light_intensity = max(max(light_col.r, light_col.g), light_col.b);
  float tint_fac = clamp(light_tint_strength, 0.0f, 2.0f);
  float3 result_col = light_col * tint_fac;

  /* Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = result_col;
  out_bsdf = closure_eval(emission_data);

  out_color = float4(result_col, 1.0f);
  out_intensity = light_intensity;
}
