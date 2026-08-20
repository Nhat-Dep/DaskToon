/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dask_outline_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dask_outline_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_dask_outline(float3 normal_in,
                       float4 base_color,
                       float outline_width,
                       float light_bleed,
                       float hand_wobble,
                       float4 outline_color,
                       float tint_darkness,
                       float tint_sat_boost,
                       float outline_lighting_mix,
                       float3 uv_in,
                       float weight,
                       float tint_mode,
                       Closure &out_bsdf,
                       float4 &out_color,
                       float &out_width,
                       float &out_alpha)
{
  base_color = max(base_color, float4(0.0f));
  outline_color = max(outline_color, float4(0.0f));

  /* 1. Calculate Surface Normal & Lighting Dynamics */
  float3 N = safe_normalize(normal_in);
  float3 L = normalize(float3(0.5f, 0.8f, 0.6f));
  float NdotL = dot(N, L);
  float half_lambert = NdotL * 0.5f + 0.5f;

  /* 2. Light Bleed (Ánh sáng tràn nét) */
  float light_thin = 1.0f;
  if (half_lambert > 0.55f) {
    float hl_intensity = (half_lambert - 0.55f) / 0.45f;
    light_thin = 1.0f - hl_intensity * clamp(light_bleed, 0.0f, 1.0f) * 0.75f;
  }

  /* 3. G-Pen Hand-Drawn Wobble */
  float2 pos = (dot(uv_in, uv_in) > 1e-6f) ? uv_in.xy * 120.0f : (gl_FragCoord.xy * 0.15f);
  float wobble = (sin(pos.x * 2.0f) * cos(pos.y * 3.0f) + sin(pos.y * 6.28f) * 0.5f) * clamp(hand_wobble, 0.0f, 1.0f) * 0.25f;

  /* 4. Modulated Line Width */
  float final_w = outline_width * light_thin * (1.0f + wobble);
  final_w = max(final_w, 0.0f);
  out_width = final_w;

  /* 5. Harmonic Line Color Synthesizer (Kyoto Animation & Ufotable Formula) */
  float3 base_rgb = base_color.rgb;
  float3 base_hsv = dask_outline_rgb_to_hsv(base_rgb);

  float target_v = clamp(base_hsv.z * clamp(tint_darkness, 0.05f, 1.0f), 0.02f, 0.95f);
  float target_s = clamp(base_hsv.y * clamp(tint_sat_boost, 0.5f, 3.0f), 0.10f, 1.0f);
  float3 harmonic_hsv = float3(base_hsv.x, target_s, target_v);
  float3 harmonic_rgb = dask_outline_hsv_to_rgb(harmonic_hsv);

  /* Synthesize final line color based on Tint Mode */
  float3 final_line_rgb = outline_color.rgb;
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

  /* Optional Scene Lighting Mix */
  float mix_fac = clamp(outline_lighting_mix, 0.0f, 1.0f);
  if (mix_fac > 0.001f) {
    ClosureDiffuse diff_in;
    diff_in.weight = 1.0f;
    diff_in.color = float3(1.0f);
    diff_in.N = N;
    Closure raw_diff = closure_eval(diff_in);
    float4 light_rgba = closure_to_rgba(raw_diff);
    float3 light_col = light_rgba.rgb * 3.14159265f;
    final_line_rgb = mix(final_line_rgb, final_line_rgb * light_col, mix_fac);
  }

  out_alpha = 1.0f;
  out_color = float4(final_line_rgb, 1.0f);

  /* 6. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = final_line_rgb;
  out_bsdf = closure_eval(emission_data);
}
