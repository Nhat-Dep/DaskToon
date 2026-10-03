/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_utildefines_lib.glsl"
#include "gpu_shader_material_dasktoon_shading.glsl"

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
                    const float4 modes,
                    sampler1DArray ramp_tex,
                    float ramp_layer,
                    Closure &out_bsdf,
                    float4 &out_color,
                    float &out_shadow_factor)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  N = safe_normalize(N);
  float outline_tint_mode = modes.x;

  /* 1. Extract Forward Radiance from all Scene Lamps */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float light_intensity = max(max(light_rgba.r, light_rgba.g), light_rgba.b);

  /* 2-3. Shared DaskToon shading core (Simple mode). */
  float cel_factor;
  float3 surface_color;
  if (modes.y > 0.5f) {
    surface_color = dt_shade_ramp(
        light_intensity, base_color.rgb, shadow_thresh, ramp_tex, ramp_layer, modes.z, cel_factor);
  }
  else {
    surface_color = dt_shade_simple(
        light_intensity, base_color.rgb, shadow_color.rgb, shadow_thresh, shadow_softness, cel_factor);
  }

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
        float3 base_hsv = dt_rgb_to_hsv(base_color.rgb);
        float o_h = fract(base_hsv.x - 0.03f + 1.0f);
        float o_s = clamp(base_hsv.y * 1.40f + 0.10f, 0.0f, 1.0f);
        float o_v = base_hsv.z * 0.35f;
        line_col = dt_hsv_to_rgb(float3(o_h, o_s, o_v));
      }
      else if (outline_tint_mode >= 1.5f) {
        /* Light Reactive Tint */
        float3 base_hsv = dt_rgb_to_hsv(base_color.rgb);
        float3 dark_tint = dt_hsv_to_rgb(float3(base_hsv.x, clamp(base_hsv.y * 1.3f, 0.0f, 1.0f), base_hsv.z * 0.35f));
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
  float w = weight;
  ClosureEmission emission_data;
  emission_data.weight = w;
  emission_data.emission = surface_color;
  out_bsdf = closure_eval(emission_data);

  /* 6. Outputs */
  out_color = float4(surface_color, 1.0f);
  out_shadow_factor = cel_factor;
}
