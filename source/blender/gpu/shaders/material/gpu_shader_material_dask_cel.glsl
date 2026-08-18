/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_dask_cel(float3 N,
                    float4 base_color,
                    float4 shadow_color,
                    float shadow_thresh,
                    float shadow_softness,
                    float use_outline,
                    float outline_width,
                    float4 outline_color,
                    float outline_lighting_mix,
                    float strength,
                    float weight,
                    Closure &out_bsdf,
                    float4 &out_color,
                    float &out_shadow_factor)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  N = safe_normalize(N);

  /* 1. Extract Forward Radiance from all Scene Lamps */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float light_intensity = max(max(light_rgba.r, light_rgba.g), light_rgba.b);

  /* 2. Discrete Anime Cel Shading Calculation */
  float s_soft = max(shadow_softness, 0.001f);
  float s_min = clamp(shadow_thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(shadow_thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  float cel_factor = smoothstep(s_min, s_max, light_intensity);

  /* 3. Blend Shadow & Base Color (Auto Harmonized) */
  float3 auto_shadow = base_color.rgb * shadow_color.rgb * 1.25f;
  float3 final_shadow = (length(shadow_color.rgb) > 0.001f) ?
                        mix(shadow_color.rgb, auto_shadow, 0.75f) :
                        base_color.rgb * 0.5f;

  float3 surface_color = mix(final_shadow, base_color.rgb, cel_factor);
  surface_color = max(surface_color * max(strength, 0.0f), float3(0.0f));

  /* 4. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = surface_color;
  out_bsdf = closure_eval(emission_data);

  /* 5. Outputs */
  out_color = float4(surface_color, 1.0f);
  out_shadow_factor = cel_factor;
}
