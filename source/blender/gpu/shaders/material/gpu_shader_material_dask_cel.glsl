/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dask_cel_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dask_cel_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

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
                    float outline_tint_mode,
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

  /* 3. Blend Shadow & Base Color (Classic Shader) */
  float3 auto_shadow = base_color.rgb * shadow_color.rgb * 1.25f;
  float3 final_shadow = (length(shadow_color.rgb) > 0.001f) ?
                        mix(shadow_color.rgb, auto_shadow, 0.75f) :
                        base_color.rgb * 0.5f;

  float3 surface_color = mix(final_shadow, base_color.rgb, cel_factor);

  /* 4. Automated Harmonic Inverted Hull Outline Integration */
  if (use_outline > 0.5f) {
    float3 vP;
    point_transform_world_to_view(g_data.P, vP);
    float3 V = safe_normalize(-vP);
    float3 vN;
    direction_transform_world_to_view(N, vN);
    vN = safe_normalize(vN);
    float NdotV = dot(vN, V);
    float edge_factor = 1.0f - abs(NdotV);
    float outline_thresh = 1.0f - clamp(outline_width * 50.0f, 0.005f, 0.99f);
    if (edge_factor > outline_thresh) {
      float3 line_col = outline_color.rgb;
      if (outline_tint_mode > 0.5f && outline_tint_mode < 1.5f) {
        /* Auto Harmonic Kyoto Outline: darken base color, boost sat, warm hue */
        float3 base_hsv = dask_cel_rgb_to_hsv(base_color.rgb);
        float o_h = fract(base_hsv.x - 0.03f + 1.0f);
        float o_s = clamp(base_hsv.y * 1.40f + 0.10f, 0.0f, 1.0f);
        float o_v = base_hsv.z * 0.35f;
        line_col = dask_cel_hsv_to_rgb(float3(o_h, o_s, o_v));
      }
      else if (outline_tint_mode >= 1.5f) {
        /* Light Reactive Tint */
        float3 base_hsv = dask_cel_rgb_to_hsv(base_color.rgb);
        float3 dark_tint = dask_cel_hsv_to_rgb(float3(base_hsv.x, clamp(base_hsv.y * 1.3f, 0.0f, 1.0f), base_hsv.z * 0.35f));
        line_col = mix(dark_tint, dark_tint * light_rgba.rgb * 3.14159265f, 0.6f);
      }
      if (outline_lighting_mix > 0.01f) {
        line_col = mix(line_col, line_col * light_rgba.rgb * 3.14159265f, outline_lighting_mix);
      }
      surface_color = line_col;
    }
  }

  surface_color = max(surface_color * max(strength, 0.0f), float3(0.0f));

  /* 5. Standalone BSDF Output */
  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = surface_color;
  out_bsdf = closure_eval(emission_data);

  /* 6. Outputs */
  out_color = float4(surface_color, 1.0f);
  out_shadow_factor = cel_factor;
}
