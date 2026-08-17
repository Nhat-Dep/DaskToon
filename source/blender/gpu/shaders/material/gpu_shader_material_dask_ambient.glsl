/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_dask_ambient(float4 ambient_color,
                       float use_custom_color,
                       float ambient_shadow_only,
                       float weight,
                       const float ambient_mode,
                       Closure &out_bsdf,
                       float4 &out_ambient)
{
  ambient_color = max(ambient_color, float4(0.0f));

  /* 1. Determine Ambient Color Source (Custom vs World Environment) */
  float3 amb_rgb = ambient_color.rgb;
  if (use_custom_color < 0.5f) {
    /* Sample Sky / World Environment Radiance with PI compensation for true radiance */
    ClosureDiffuse diff_amb;
    diff_amb.weight = 1.0f;
    diff_amb.color = float3(1.0f);
    diff_amb.N = float3(0.0f, 0.0f, 1.0f);
    Closure raw_amb = closure_eval(diff_amb);
    float4 world_light = closure_to_rgba(raw_amb);
    if (length(world_light.rgb) > 0.0001f) {
      amb_rgb = world_light.rgb * 3.14159265f;
    }
  }

  /* 2. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = amb_rgb;
  out_bsdf = closure_eval(emission_data);

  /* 3. Output */
  out_ambient = float4(amb_rgb, 1.0f);
}
