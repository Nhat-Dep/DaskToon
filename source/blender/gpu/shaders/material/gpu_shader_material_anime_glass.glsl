/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_glass(float4 crystal_tint,
                      float4 internal_glow_color,
                      float4 sparkle_color,
                      float sparkle_scale,
                      float sparkle_density,
                      float dispersion_power,
                      float fresnel_power,
                      float opacity,
                      float3 N,
                      float3 local_pos,
                      float weight,
                      Closure &result,
                      float4 &out_color,
                      float &out_sparkle_mask)
{
  crystal_tint = max(crystal_tint, float4(0.0f));
  internal_glow_color = max(internal_glow_color, float4(0.0f));
  sparkle_color = max(sparkle_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Chromatic Dispersion Rim (Tán sắc viền mép cầu vồng) */
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);
  float f_pow = max(fresnel_power, 0.1f);
  float f_rim = pow(rim, f_pow);

  float disp = clamp(dispersion_power, 0.0f, 2.0f);
  float3 dispersion_rim = float3(
      pow(rim, f_pow * (1.0f - disp * 0.2f)),
      pow(rim, f_pow),
      pow(rim, f_pow * (1.0f + disp * 0.2f))
  );

  /* 2. Multi-Layer Anime Sparkle Stars / Glints */
  float s_scale = max(sparkle_scale, 0.5f);
  float3 p = local_pos * s_scale * 10.0f + V * 2.0f;
  float sp1 = sin(p.x * 5.0f) * sin(p.y * 5.0f) * sin(p.z * 5.0f);
  float sp2 = cos(p.x * 12.0f + p.y * 8.0f) * sin(p.z * 10.0f);
  float raw_sparkle = max(0.0f, (sp1 * 0.5f + sp2 * 0.5f));
  float sparkle_thresh = 1.0f - clamp(sparkle_density * 0.3f, 0.01f, 0.95f);
  float sparkle_mask = smoothstep(sparkle_thresh, 1.0f, raw_sparkle);
  out_sparkle_mask = sparkle_mask;

  /* 3. Composite Internal Refraction & Crystal Glow */
  float3 base_rgb = crystal_tint.rgb * (facing * 0.7f + 0.3f);
  float3 glow_rgb = internal_glow_color.rgb * internal_glow_color.a * (1.0f - facing * 0.6f);
  float3 sparkle_rgb = sparkle_color.rgb * sparkle_mask * sparkle_color.a * 3.0f;
  float3 rim_rgb = dispersion_rim * crystal_tint.rgb * 1.5f;

  float3 final_color = base_rgb + glow_rgb + sparkle_rgb + rim_rgb;
  float final_alpha = clamp(opacity + f_rim * 0.5f, 0.0f, 1.0f);

  out_color = float4(final_color, final_alpha);

  /* 4. True Alpha Transparency & Glass Emission Closure */
  ClosureTransparency transparency_data;
  transparency_data.weight = weight * clamp(1.0f - final_alpha, 0.0f, 1.0f);
  transparency_data.transmittance = crystal_tint.rgb;
  transparency_data.holdout = 0.0f;
  Closure trans_cl = closure_eval(transparency_data);

  ClosureEmission emission_data;
  emission_data.weight = weight * clamp(final_alpha, 0.0f, 1.0f);
  emission_data.emission = final_color;
  Closure solid_cl = closure_eval(emission_data);

  result = closure_add(trans_cl, solid_cl);
}
