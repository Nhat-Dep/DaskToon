/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_warm_cool_grade(float4 base_color,
                                float4 lit_warm,
                                float4 shadow_cool,
                                float penumbra_sat,
                                float shadow_fac,
                                float4 &out_color)
{
  base_color = max(base_color, float4(0.0f));
  lit_warm = max(lit_warm, float4(0.0f));
  shadow_cool = max(shadow_cool, float4(0.0f));

  /* Tint base color for lit and shadow areas */
  float3 lit_col = base_color.rgb * lit_warm.rgb;
  float3 shadow_col = base_color.rgb * shadow_cool.rgb;
  float3 blended = mix(shadow_col, lit_col, clamp(shadow_fac, 0.0f, 1.0f));

  /* Penumbra (terminator) bell curve mask: 1.0 - 4.0 * (shadow_fac - 0.5)^2 */
  float delta = shadow_fac - 0.5f;
  float penumbra = clamp(1.0f - 4.0f * delta * delta, 0.0f, 1.0f);

  /* Saturation boost at terminator boundary */
  float luma = dot(blended, float3(0.2126f, 0.7152f, 0.0722f));
  float3 saturated = mix(float3(luma), blended, max(penumbra_sat, 0.0f));
  float3 final_rgb = mix(blended, saturated, penumbra);

  out_color = float4(final_rgb, base_color.a);
}
