/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 dasktoon_master_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));

  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dasktoon_master_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

[[node]]
void node_anime_character(float3 N,
                          float4 base_color,
                          float4 shadow_color,
                          float shadow_thresh,
                          float shadow_softness,
                          float4 ambient_color,
                          float use_custom_color,
                          float ambient_shadow_only,
                          float ambient_factor,
                          float light_tint_strength,
                          float light_factor,
                          float4 ao_color,
                          float ao_dist,
                          float ao_darkness,
                          float ao_factor,
                          float4 rim_color,
                          float rim_fresnel_power,
                          float rim_lift,
                          float rim_lighting_mix,
                          float rim_factor,
                          float4 color_filter,
                          float4 shadow_tint,
                          float4 highlight_tint,
                          float saturation,
                          float brightness,
                          float contrast,
                          float grade_factor,
                          float strength,
                          float alpha,
                          float weight,
                          const float4 modes,
                          Closure &result)
{
  N = safe_normalize(N);
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));

  float ambient_mode = modes.x;
  float light_blend_mode = modes.y;
  int module_flags = int(modes.z + 0.5f);
  float ao_samples = modes.w;

  bool use_ambient = (module_flags & (1 << 0)) != 0;
  bool use_light   = (module_flags & (1 << 1)) != 0;
  bool use_ao      = (module_flags & (1 << 2)) != 0;
  bool use_rim     = (module_flags & (1 << 3)) != 0;
  bool use_outline = (module_flags & (1 << 4)) != 0;
  bool use_grade   = (module_flags & (1 << 5)) != 0;

  /* =========================================================================
   * 1. SCENE LAMP LIGHTING EXTRACTION
   * ========================================================================= */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  Closure raw_diff = closure_eval(diff_in);
  float4 light_rgba = closure_to_rgba(raw_diff);

  float3 light_col = light_rgba.rgb;
  float light_intensity = max(max(light_col.r, light_col.g), light_col.b);

  /* =========================================================================
   * 2. DISCRETE 2-TONE CEL SHADING CALCULATION (AUTO HARMONIZED)
   * ========================================================================= */
  float s_soft = max(shadow_softness, 0.001f);
  float s_min = clamp(shadow_thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(shadow_thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  float cel_factor = smoothstep(s_min, s_max, light_intensity);

  /* Auto-harmonize shadow with base color so shadows never look muddy/grey */
  float3 auto_shadow = base_color.rgb * shadow_color.rgb * 1.25f;
  float3 final_shadow = (length(shadow_color.rgb) > 0.001f) ?
                        mix(shadow_color.rgb, auto_shadow, 0.75f) :
                        base_color.rgb * 0.5f;

  float3 surface_color = mix(final_shadow, base_color.rgb, cel_factor);

  /* =========================================================================
   * 3. BUILT-IN WORLD AMBIENT LIGHTING LAYER (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float amb_fac = use_ambient ? clamp(ambient_factor, 0.0f, 1.0f) : 0.0f;
  if (amb_fac > 0.0001f) {
    float3 amb_rgb = ambient_color.rgb;
    if (use_custom_color < 0.5f) {
      ClosureDiffuse diff_amb;
      diff_amb.weight = 1.0f;
      diff_amb.color = float3(1.0f);
      diff_amb.N = float3(0.0f, 0.0f, 1.0f);
      Closure raw_amb = closure_eval(diff_amb);
      float4 world_light = closure_to_rgba(raw_amb);
      if (length(world_light.rgb) > 0.0001f) {
        amb_rgb = world_light.rgb * 3.14159265f;
      }
    }

    float3 amb_shaded = surface_color;
    int mode = int(ambient_mode + 0.5f);
    if (mode == 0) { // Overlay
      amb_shaded = mix(2.0f * surface_color * amb_rgb,
                       1.0f - 2.0f * (1.0f - surface_color) * (1.0f - amb_rgb),
                       step(float3(0.5f), surface_color));
    }
    else if (mode == 1) { // Hue
      float3 hsv_surf = dasktoon_master_rgb_to_hsv(surface_color);
      float3 hsv_amb = dasktoon_master_rgb_to_hsv(amb_rgb);
      amb_shaded = dasktoon_master_hsv_to_rgb(float3(hsv_amb.x, hsv_surf.y, hsv_surf.z));
    }
    else if (mode == 2) { // Hue + Saturation
      float3 hsv_surf = dasktoon_master_rgb_to_hsv(surface_color);
      float3 hsv_amb = dasktoon_master_rgb_to_hsv(amb_rgb);
      amb_shaded = dasktoon_master_hsv_to_rgb(float3(hsv_amb.x, hsv_amb.y, hsv_surf.z));
    }
    else if (mode == 3) { // Saturation
      float3 hsv_surf = dasktoon_master_rgb_to_hsv(surface_color);
      float3 hsv_amb = dasktoon_master_rgb_to_hsv(amb_rgb);
      amb_shaded = dasktoon_master_hsv_to_rgb(float3(hsv_amb.x, hsv_surf.y, hsv_surf.z));
    }
    else if (mode == 4) { // Value
      float3 hsv_surf = dasktoon_master_rgb_to_hsv(surface_color);
      float3 hsv_amb = dasktoon_master_rgb_to_hsv(amb_rgb);
      amb_shaded = dasktoon_master_hsv_to_rgb(float3(hsv_amb.x, hsv_surf.y, hsv_amb.z));
    }
    else if (mode == 5) { // Multiply
      amb_shaded = surface_color * amb_rgb;
    }
    else { // Mix
      amb_shaded = mix(surface_color, amb_rgb, 0.5f);
    }

    if (ambient_shadow_only > 0.5f) {
      surface_color = mix(surface_color, amb_shaded, amb_fac * (1.0f - cel_factor));
    }
    else {
      surface_color = mix(surface_color, amb_shaded, amb_fac);
    }
  }

  /* =========================================================================
   * 4. BUILT-IN SCENE LIGHT LAYER (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float lit_fac = use_light ? clamp(light_factor, 0.0f, 1.0f) : 0.0f;
  if (lit_fac > 0.0001f) {
    float3 chroma = (light_intensity > 0.001f) ? (light_col / light_intensity) : float3(1.0f);
    float tint_fac = clamp(light_tint_strength, 0.0f, 2.0f);
    float3 lamp_tint = mix(float3(1.0f), chroma, tint_fac);

    float3 lit_shaded = surface_color;
    int lmode = int(light_blend_mode + 0.5f);
    if (lmode == 0) { // Overlay
      lit_shaded = mix(2.0f * surface_color * lamp_tint,
                       1.0f - 2.0f * (1.0f - surface_color) * (1.0f - lamp_tint),
                       step(float3(0.5f), surface_color));
    }
    else if (lmode == 1) { // Hue Tint
      float3 hsv_surf = dasktoon_master_rgb_to_hsv(surface_color);
      float3 hsv_lamp = dasktoon_master_rgb_to_hsv(lamp_tint);
      lit_shaded = dasktoon_master_hsv_to_rgb(float3(hsv_lamp.x, hsv_surf.y, hsv_surf.z));
    }
    else if (lmode == 2) { // Multiply
      lit_shaded = surface_color * lamp_tint;
    }
    else if (lmode == 3) { // Add
      lit_shaded = surface_color + lamp_tint * 0.5f;
    }
    else { // Pure Cel
      lit_shaded = surface_color;
    }

    surface_color = mix(surface_color, lit_shaded, lit_fac * cel_factor);
  }

  /* =========================================================================
   * 5. BUILT-IN HARDWARE HBAO CREVICE SHADOWS (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float ao_f = use_ao ? clamp(ao_factor, 0.0f, 1.0f) : 0.0f;
  if (ao_f > 0.0001f) {
    float d = max(ao_dist, 0.0001f);
    float darkness = max(ao_darkness, 0.0f);
    float raw_ao = ambient_occlusion_eval(N, d, 0.0f, ao_samples);
    float occlusion = clamp(1.0f - raw_ao, 0.0f, 1.0f);
    
    float deep_occlusion = clamp(pow(occlusion, 1.0f / max(darkness, 0.01f)) * min(darkness, 3.0f), 0.0f, 1.0f);
    float3 ao_multiplier = mix(float3(1.0f), ao_color.rgb, deep_occlusion);

    surface_color = mix(surface_color, surface_color * ao_multiplier, ao_f);
  }

  /* =========================================================================
   * 6. BUILT-IN VRM MTOON PARAMETRIC RIM LIGHT (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float rim_f = use_rim ? clamp(rim_factor, 0.0f, 1.0f) : 0.0f;
  if (rim_f > 0.0001f) {
    float3 vP;
    point_transform_world_to_view(g_data.P, vP);
    float3 V = safe_normalize(-vP);
    float3 vN;
    direction_transform_world_to_view(N, vN);
    vN = safe_normalize(vN);

    float NdotV = clamp(dot(vN, V), 0.0f, 1.0f);
    float fresnel = 1.0f - NdotV;
    float rim_power = max(rim_fresnel_power, 0.1f);
    float rim_term = clamp(pow(fresnel, rim_power) + rim_lift, 0.0f, 1.0f);

    float3 rim_col = rim_color.rgb;
    float rim_l_mix = clamp(rim_lighting_mix, 0.0f, 1.0f);
    if (rim_l_mix > 0.001f) {
      rim_col = mix(rim_col, rim_col * light_col, rim_l_mix);
    }

    /* Directional visibility: rim fades in total darkness when rim_lighting_mix > 0 */
    float light_visibility = mix(1.0f, clamp(light_intensity * 2.0f, 0.0f, 1.0f), rim_l_mix);
    surface_color += rim_col * (rim_term * rim_f * light_visibility);
  }

  /* =========================================================================
   * 7. BUILT-IN CINEMATIC COLOR GRADING LAYER (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float grd_fac = use_grade ? clamp(grade_factor, 0.0f, 1.0f) : 0.0f;
  if (grd_fac > 0.0001f) {
    float3 graded = surface_color;

    /* Global Color Filter */
    graded *= color_filter.rgb;

    /* Split Toning: Shadow Tint vs Highlight Tint */
    float lum = dot(graded, float3(0.299f, 0.587f, 0.114f));
    float3 split_toned = mix(graded * shadow_tint.rgb, graded * highlight_tint.rgb, clamp(lum, 0.0f, 1.0f));
    graded = split_toned;

    /* Saturation Boost */
    if (abs(saturation - 1.0f) > 0.001f) {
      float3 hsv = dasktoon_master_rgb_to_hsv(graded);
      hsv.y = clamp(hsv.y * max(saturation, 0.0f), 0.0f, 1.0f);
      graded = dasktoon_master_hsv_to_rgb(hsv);
    }

    /* Brightness & Contrast */
    graded += brightness;
    graded = (graded - 0.5f) * (1.0f + contrast) + 0.5f;
    graded = max(graded, float3(0.0f));

    surface_color = mix(surface_color, graded, grd_fac);
  }

  /* =========================================================================
   * 8. MASTER CONTROLS & FINAL EMISSION CLOSURE
   * ========================================================================= */
  surface_color = max(surface_color * max(strength, 0.0f), float3(0.0f));

  float w = (weight > 0.0001f) ? weight : 1.0f;
  ClosureEmission emission_data;
  emission_data.weight = w * clamp(alpha, 0.0f, 1.0f);
  emission_data.emission = surface_color;
  result = closure_eval(emission_data);
}
