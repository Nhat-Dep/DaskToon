/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_eye(float4 iris_color,
                    float4 pupil_color,
                    float4 bottom_glow_color,
                    float bottom_glow_power,
                    float4 top_shadow_tint,
                    float4 sparkle_color,
                    float3 uv_in,
                    float weight,
                    Closure &result,
                    float4 &out_color)
{
  iris_color = max(iris_color, float4(0.0f));
  pupil_color = max(pupil_color, float4(0.0f));
  bottom_glow_color = max(bottom_glow_color, float4(0.0f));
  top_shadow_tint = max(top_shadow_tint, float4(0.0f));
  sparkle_color = max(sparkle_color, float4(0.0f));

  /* Use linked UV or fallback to normalized planar coordinate */
  float2 uv = (dot(uv_in, uv_in) > 1e-6f) ? uv_in.xy : (g_data.P.xy * 0.5f + 0.5f);

  /* 1. Radial Pupil Mask (smooth circular center) */
  float dist_center = length(uv - float2(0.5f, 0.5f));
  float pupil_fac = 1.0f - smoothstep(0.16f, 0.22f, dist_center);
  float3 base_iris = mix(iris_color.rgb, pupil_color.rgb, pupil_fac);

  /* 2. Bottom Crescent Glow */
  float bottom_curve = pow(clamp(1.0f - uv.y, 0.0f, 1.0f), 2.2f) * max(bottom_glow_power, 0.0f);
  float3 with_glow = base_iris + bottom_glow_color.rgb * bottom_curve;

  /* 3. Top Eyelash Shadow */
  float top_shadow_fac = smoothstep(0.45f, 0.85f, uv.y);
  float3 with_shadow = mix(with_glow, with_glow * top_shadow_tint.rgb, top_shadow_fac);

  /* 4. Anime Eye Sparkle Highlights */
  float sp1 = 1.0f - smoothstep(0.035f, 0.055f, length(uv - float2(0.38f, 0.65f)));
  float sp2 = 1.0f - smoothstep(0.018f, 0.032f, length(uv - float2(0.62f, 0.40f)));
  float sparkle_fac = clamp(sp1 + sp2, 0.0f, 1.0f);
  float3 final_eye = mix(with_shadow, sparkle_color.rgb, sparkle_fac);

  out_color = float4(final_eye, iris_color.a);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = final_eye;

  result = closure_eval(emission_data);
}
