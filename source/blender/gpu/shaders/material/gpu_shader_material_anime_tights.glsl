/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_tights(float4 tights_color,
                        float4 skin_color,
                        float4 sheen_color,
                        float sheerness,
                        float denier_falloff,
                        float fishnet_mode,
                        float fishnet_scale,
                        float fishnet_thickness,
                        float fishnet_distortion,
                        float sheen_power,
                        float3 N,
                        float3 local_pos,
                        float weight,
                        Closure &result,
                        float4 &out_color,
                        float &out_fishnet_mask,
                        float &out_skin_visibility)
{
  tights_color = max(tights_color, float4(0.0f));
  skin_color = max(skin_color, float4(0.0f));
  sheen_color = max(sheen_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Sheer Tights / Pantyhose Skin Falloff (20D - 80D Sheerness) */
  /* Direct viewing angle shows more skin; grazing edge shows denser black nylon */
  float falloff_pow = max(denier_falloff, 0.1f);
  float skin_fac = pow(facing, falloff_pow) * clamp(sheerness, 0.0f, 1.0f);
  out_skin_visibility = skin_fac;

  float3 base_layer = mix(tights_color.rgb, skin_color.rgb, skin_fac);

  /* 2. Procedural Diamond Fishnet Grid (45-degree rotated lattice) */
  float fn_scale = max(fishnet_scale, 0.5f);
  float2 uv = float2(local_pos.x + local_pos.y, local_pos.x - local_pos.y) * fn_scale * 0.70710678f;
  
  /* Distortion from curvature */
  float2 dist_offset = float2(sin(uv.y * 3.0f), cos(uv.x * 3.0f)) * fishnet_distortion * 0.1f;
  uv += dist_offset;

  float2 f_grid = abs(fract(uv) - 0.5f);
  float line_dist = min(f_grid.x, f_grid.y);
  float th = clamp(fishnet_thickness * 0.25f, 0.01f, 0.45f);
  float fishnet_mask = 1.0f - smoothstep(th - 0.02f, th + 0.02f, line_dist);
  out_fishnet_mask = fishnet_mask;

  /* Composite Fishnet on top of Skin/Tights */
  float fn_blend = clamp(fishnet_mode, 0.0f, 1.0f);
  float3 surface_rgb = mix(base_layer, mix(skin_color.rgb, tights_color.rgb, fishnet_mask), fn_blend);

  /* 3. Subtle Nylon / Spandex Sheen Glow */
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);
  float s_pow = max(sheen_power, 0.1f);
  float sheen_fac = pow(rim, s_pow);
  surface_rgb += sheen_color.rgb * sheen_fac * sheen_color.a * 0.5f;

  out_color = float4(surface_rgb, tights_color.a);

  /* 4. Diffuse Cel BSDF with Subsurface Warm Shadow */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight;
  diffuse_data.color = surface_rgb;
  diffuse_data.N = N;
  Closure lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = tights_color.rgb * surface_rgb * 0.15f;
  Closure shadow_cl = closure_eval(emission_data);

  result = closure_add(shadow_cl, lit_cl);
}
