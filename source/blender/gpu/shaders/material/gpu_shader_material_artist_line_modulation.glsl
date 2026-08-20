/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 artist_line_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 artist_line_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_artist_line_modulation(float3 normal_in,
                                 float4 base_color,
                                 float base_width,
                                 float light_bleed,
                                 float curvature_accent,
                                 float view_taper,
                                 float hand_wobble,
                                 float4 custom_outline_color,
                                 float tint_darkness,
                                 float tint_sat_boost,
                                 float line_break_thresh,
                                 float3 uv_in,
                                 float weight,
                                 float tint_mode,
                                 float4 &out_line_color,
                                 float &out_line_width,
                                 float &out_line_alpha,
                                 Closure &out_bsdf)
{
  base_color = max(base_color, float4(0.0f));
  custom_outline_color = max(custom_outline_color, float4(0.0f));

  /* 1. Extract Lighting Radiance & Shading Angles */
  float3 N = safe_normalize(normal_in);
  float3 L = normalize(float3(0.5f, 0.8f, 0.6f));
  float NdotL = dot(N, L);
  float half_lambert = NdotL * 0.5f + 0.5f;

  /* 2. Light Bleed (Ánh sáng tràn nét) */
  float light_attenuation = 1.0f;
  if (half_lambert > 0.50f) {
    float hl_intensity = (half_lambert - 0.50f) / 0.50f;
    light_attenuation = 1.0f - hl_intensity * clamp(light_bleed, 0.0f, 1.0f) * 0.80f;
  }

  /* 3. View Angle Taper */
  float3 V = safe_normalize(-g_data.camera_pos);
  float NdotV = abs(dot(N, V));
  float taper = mix(1.0f, smoothstep(0.0f, 0.6f, NdotV), clamp(view_taper, 0.0f, 1.0f));

  /* 4. Curvature Crevice Accent */
  float curvature_boost = 1.0f + (1.0f - clamp(half_lambert, 0.0f, 1.0f)) * clamp(curvature_accent, 0.0f, 2.0f) * 0.5f;

  /* 5. G-Pen Hand-Drawn Wobble */
  float2 pos = (dot(uv_in, uv_in) > 1e-6f) ? uv_in.xy * 150.0f : (gl_FragCoord.xy * 0.15f);
  float wobble = (sin(pos.x * 2.0f) * cos(pos.y * 3.0f) + sin(pos.y * 6.28f) * 0.5f) * clamp(hand_wobble, 0.0f, 1.0f) * 0.25f;

  /* 6. Modulated Line Width Calculation */
  float calculated_width = base_width * light_attenuation * taper * curvature_boost * (1.0f + wobble);
  calculated_width = max(calculated_width, 0.0f);

  /* 7. Line Break in Highlights */
  float alpha_factor = 1.0f;
  if (line_break_thresh > 0.01f && half_lambert > (1.0f - line_break_thresh * 0.3f)) {
    float break_progress = (half_lambert - (1.0f - line_break_thresh * 0.3f)) / (line_break_thresh * 0.3f + 1e-4f);
    alpha_factor = 1.0f - clamp(break_progress, 0.0f, 1.0f);
  }

  /* 8. Harmonic Line Color Synthesizer (Kyoto Animation & Ufotable Formula) */
  float3 base_rgb = base_color.rgb;
  float3 base_hsv = artist_line_rgb_to_hsv(base_rgb);

  float target_v = clamp(base_hsv.z * clamp(tint_darkness, 0.05f, 1.0f), 0.02f, 0.95f);
  float target_s = clamp(base_hsv.y * clamp(tint_sat_boost, 0.5f, 3.0f), 0.10f, 1.0f);
  float3 harmonic_hsv = float3(base_hsv.x, target_s, target_v);
  float3 harmonic_rgb = artist_line_hsv_to_rgb(harmonic_hsv);

  float3 final_line_rgb = custom_outline_color.rgb;
  if (tint_mode > 0.5f && tint_mode < 1.5f) {
    /* Mode 1: Auto Harmonic Kyoto/Ufotable Style */
    final_line_rgb = harmonic_rgb;
    if (half_lambert > 0.7f && light_bleed > 0.2f) {
      float glow_fac = (half_lambert - 0.7f) * 3.33f * light_bleed;
      final_line_rgb = mix(final_line_rgb, base_rgb, clamp(glow_fac, 0.0f, 0.6f));
    }
  }
  else if (tint_mode >= 1.5f) {
    /* Mode 2: Light-Reactive Tint */
    float3 lit_tint = mix(harmonic_rgb, harmonic_rgb * (half_lambert * 0.8f + 0.2f), 0.8f);
    final_line_rgb = lit_tint;
  }

  out_line_color = float4(final_line_rgb, 1.0f);
  out_line_width = calculated_width;
  out_line_alpha = alpha_factor;

  /* 9. Standalone BSDF Emission Closure Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w * alpha_factor;
  emission_data.emission = final_line_rgb;
  out_bsdf = closure_eval(emission_data);
}
