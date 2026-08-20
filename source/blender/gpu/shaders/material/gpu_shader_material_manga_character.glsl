/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float dask_manga_stipple(float2 p)
{
  return fract(sin(dot(p, float2(12.9898f, 78.233f))) * 43758.5453f);
}

[[node]]
void node_manga_character(float3 N,
                          float4 paper_color,
                          float4 ink_color,
                          float4 tone1_color,
                          float4 tone2_color,
                          float shadow_thresh,
                          float shadow_softness,
                          float tone_scale,
                          float tone_angle,
                          float tone_sharpness,
                          float screen_lock,
                          float rim_strength,
                          float3 uv_in,
                          float manga_mode,
                          float pattern_type,
                          float4 &out_color,
                          float &out_tone_fac,
                          float &out_shadow_fac)
{
  N = safe_normalize(N);

  /* 1. Extract Light Intensity from Scene Lamps */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float light_intensity = max(max(light_rgba.r, light_rgba.g), light_rgba.b);

  /* 2. Cel Shading Split (Shadow Factor) */
  float s_soft = max(shadow_softness, 0.001f);
  float s_min = clamp(shadow_thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(shadow_thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  float shadow_fac = 1.0f - smoothstep(s_min, s_max, light_intensity);

  /* 3. Coordinate System (2D Comic Screen vs 3D Mesh UV) */
  float2 pos_screen = gl_FragCoord.xy * 0.05f;
  float2 pos_uv = uv_in.xy * 10.0f;
  float2 pos = mix(pos_uv, pos_screen, clamp(screen_lock, 0.0f, 1.0f));
  pos *= max(tone_scale, 0.1f) * 0.1f;

  /* 2D Rotation using float trigonometry */
  float rad1 = radians(tone_angle);
  float c1 = cos(rad1);
  float s1 = sin(rad1);
  float2 p1 = float2(c1 * pos.x - s1 * pos.y, s1 * pos.x + c1 * pos.y);

  float rad2 = radians(tone_angle + 90.0f);
  float c2 = cos(rad2);
  float s2 = sin(rad2);
  float2 p2 = float2(c2 * pos.x - s2 * pos.y, s2 * pos.x + c2 * pos.y);

  /* 4. Synthesize Manga Screentone Pattern */
  float pattern = 0.0f;
  float p_type = round(pattern_type);
  float density = clamp(tone_sharpness * 10.0f, 0.5f, 5.0f);

  if (p_type < 0.5f) {
    /* Mode 0: Halftone Dots (Classic Manga Screentone 網点) */
    float2 grid = fract(p1) - 0.5f;
    float dist = length(grid);
    float dot_radius = sqrt(clamp(shadow_fac, 0.0f, 1.0f)) * 0.55f;
    pattern = step(dist, dot_radius);
  }
  else if (p_type < 1.5f) {
    /* Mode 1: Cross-Hatch (Shonen Action G-Pen Manga) */
    float line1 = step(0.5f - clamp(shadow_fac * 0.45f, 0.02f, 0.48f), fract(p1.y));
    float line2 = 0.0f;
    if (shadow_fac > 0.45f) {
      line2 = step(0.5f - clamp((shadow_fac - 0.45f) * 0.70f, 0.02f, 0.48f), fract(p2.y));
    }
    pattern = max(line1, line2);
  }
  else if (p_type < 2.5f) {
    /* Mode 2: Parallel Speed Lines (Parallel Hatching) */
    pattern = step(0.5f - clamp(shadow_fac * 0.45f, 0.02f, 0.48f), fract(p1.y));
  }
  else {
    /* Mode 3: Stipple Grain / Sand Screentone */
    float noise = dask_manga_stipple(floor(p1 * 4.0f));
    pattern = step(noise, shadow_fac);
  }

  /* 5. Render Style Modes */
  float m_mode = round(manga_mode);
  float3 final_rgb;

  if (m_mode < 0.5f) {
    /* Mode 0: B&W Traditional Manga Comic Book */
    final_rgb = mix(paper_color.rgb, ink_color.rgb, pattern);
  }
  else if (m_mode < 1.5f) {
    /* Mode 1: Color Webtoon (Manhwa / Modern Manga) */
    float3 cel_tone = mix(paper_color.rgb, tone1_color.rgb, shadow_fac);
    float3 ink_hatch = mix(cel_tone, tone2_color.rgb, pattern);
    final_rgb = ink_hatch;
  }
  else {
    /* Mode 2: Pencil Sketch (Doujinshi / Concept Art) */
    float pencil_tone = pattern * 0.85f;
    final_rgb = mix(paper_color.rgb, ink_color.rgb, pencil_tone);
  }

  /* 6. Stylized Contour Rim Highlight */
  float rim_str = max(rim_strength, 0.0f);
  if (rim_str > 0.01f) {
    float3 vP;
    point_transform_world_to_view(g_data.P, vP);
    float3 V = safe_normalize(-vP);
    float3 vN;
    direction_transform_world_to_view(N, vN);
    vN = safe_normalize(vN);
    float NdotV = clamp(dot(vN, V), 0.0f, 1.0f);
    float rim_fac = pow(1.0f - NdotV, 3.5f) * rim_str;
    final_rgb = mix(final_rgb, paper_color.rgb, clamp(rim_fac, 0.0f, 1.0f));
  }

  out_color = float4(final_rgb, 1.0f);
  out_tone_fac = pattern;
  out_shadow_fac = shadow_fac;
}
