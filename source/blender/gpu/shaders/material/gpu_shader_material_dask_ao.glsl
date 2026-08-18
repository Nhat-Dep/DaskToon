/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_dask_ao(float3 normal,
                  float4 ao_color,
                  float dist,
                  float darkness,
                  float weight,
                  const float inverted,
                  const float sample_count,
                  Closure &out_bsdf,
                  float4 &out_color,
                  float &out_raw_ao,
                  float &out_dist)
{
  ao_color = max(ao_color, float4(0.0f));
  float d = max(dist, 0.0001f);
  float dark_val = max(darkness, 0.0f);

  /* 1. Real Hardware Horizon-Based Ambient Occlusion (HBAO) Evaluation in EEVEE */
  float raw_ao = ambient_occlusion_eval(safe_normalize(normal), d, inverted, sample_count);

  /* 2. Deepen and enhance crevice occlusion based on AO Darkness */
  float occlusion = clamp(1.0f - raw_ao, 0.0f, 1.0f);
  float deep_occlusion = clamp(pow(occlusion, 1.0f / max(dark_val, 0.01f)) * min(dark_val, 3.0f), 0.0f, 1.0f);
  float3 ao_multiplier = mix(float3(1.0f), ao_color.rgb, deep_occlusion);

  /* 3. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = ao_multiplier;
  out_bsdf = closure_eval(emission_data);

  out_color = float4(ao_multiplier, 1.0f);
  out_raw_ao = 1.0f - deep_occlusion;
  out_dist = d;
}
