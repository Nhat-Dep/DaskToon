/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_angel_ring(float4 highlight_color,
                           float band_pos,
                           float band_width,
                           float band_softness,
                           float strand_jitter,
                           float noise_scale,
                           float intensity,
                           float3 N,
                           float weight,
                           Closure &result,
                           float4 &out_color,
                           float &out_fac)
{
  highlight_color = max(highlight_color, float4(0.0f));
  N = safe_normalize(N);

  /* Compute pseudo hair-strand jitter along normal */
  float jitter = sin(dot(g_data.P.xy, float2(noise_scale * 0.7f, noise_scale * 1.3f))) * strand_jitter * 0.1f;

  /* Anisotropic Normal Z Band distance */
  float ring_dist = abs(N.z + jitter - clamp(band_pos, 0.0f, 1.0f));
  float r_fw = max(fwidth(ring_dist), 0.0005f);
  float r_soft = max(band_softness, r_fw);
  float r_width = max(band_width, 0.001f);
  float ring_min = max(r_width - r_soft * 0.5f, 0.0f);
  float ring_max = r_width + r_soft * 0.5f + 0.0001f;
  float ring_fac = 1.0f - smoothstep(ring_min, ring_max, ring_dist);

  out_fac = ring_fac * max(intensity, 0.0f);
  out_color = float4(highlight_color.rgb * out_fac, highlight_color.a * ring_fac);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = out_color.rgb;

  result = closure_eval(emission_data);
}
