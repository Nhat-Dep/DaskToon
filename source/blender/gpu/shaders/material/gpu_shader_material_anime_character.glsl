/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_material_transform_utils.glsl"
#include "gpu_shader_utildefines_lib.glsl"
#include "gpu_shader_material_dasktoon_shading.glsl"

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
                          float ao_mask,
                          float4 rim_color,
                          float rim_fresnel_power,
                          float rim_lift,
                          float rim_lighting_mix,
                          float rim_factor,
                          float outline_width,
                          float4 outline_color,
                          float outline_lighting_mix,
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
                          sampler1DArray ramp_tex,
                          float ramp_layer,
                          const float4 modes2,
                          Closure &result)
{
  N = safe_normalize(N);
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));

  float ambient_mode = modes.x;
  float outline_tint_mode = modes.y;
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
   * 2. DISCRETE 2-TONE CEL SHADING CALCULATION (CLASSIC SHADER)
   * ========================================================================= */
  float cel_factor;
  float3 surface_color;
  if (modes2.y > 0.5f) {
    surface_color = dt_shade_ramp(
        light_intensity, base_color.rgb, shadow_thresh, ramp_tex, ramp_layer, modes2.z, cel_factor);
  }
  else {
    surface_color = dt_shade_simple(
        light_intensity, base_color.rgb, shadow_color.rgb, shadow_thresh, shadow_softness, cel_factor);
  }

  /* =========================================================================
   * 3. BUILT-IN WORLD AMBIENT LIGHTING LAYER (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float amb_fac = use_ambient ? clamp(ambient_factor, 0.0f, 1.0f) : 0.0f;
  if (amb_fac > 0.0001f) {
    float3 amb_color;
    if (use_custom_color > 0.5f) {
      amb_color = ambient_color.rgb;
    }
    else {
      ClosureDiffuse amb_diff;
      amb_diff.weight = 1.0f;
      amb_diff.color = float3(1.0f);
      amb_diff.N = float3(0.0f, 0.0f, 1.0f);
      Closure amb_eval = closure_eval(amb_diff);
      float4 amb_rgba = closure_to_rgba(amb_eval);
      amb_color = amb_rgba.rgb;
    }

    float3 amb_shaded = dt_ambient_mode(surface_color, amb_color, int(ambient_mode + 0.5f));

    float apply_mask = (ambient_shadow_only > 0.5f) ? (1.0f - cel_factor) : 1.0f;
    surface_color = mix(surface_color, amb_shaded, amb_fac * apply_mask);
  }

  /* =========================================================================
   * 4. BUILT-IN SCENE LIGHT TINT LAYER (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float lit_fac = use_light ? clamp(light_factor, 0.0f, 1.0f) : 0.0f;
  if (lit_fac > 0.0001f) {
    float3 lit_shaded = dt_light_mode(
        surface_color, light_col, dt_light_norm(light_col), light_tint_strength, int(modes2.x + 0.5f));

    surface_color = mix(surface_color, lit_shaded, lit_fac * cel_factor);
  }

  /* =========================================================================
   * 5. BUILT-IN HARDWARE HBAO CREVICE SHADOWS (FAC = 0 WHEN DISABLED)
   * ========================================================================= */
  float ao_f = use_ao ? (clamp(ao_factor, 0.0f, 1.0f) * clamp(ao_mask, 0.0f, 1.0f)) : 0.0f;
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
    /* Default tighter falloff to keep rim light strictly on outer silhouette (hair & shoulders) */
    float rim_power = max(rim_fresnel_power, 0.5f);
    float rim_term = clamp(pow(fresnel, rim_power) + rim_lift, 0.0f, 1.0f);

    float3 rim_col = rim_color.rgb;
    float rim_l_mix = clamp(rim_lighting_mix, 0.0f, 1.0f);
    if (rim_l_mix > 0.001f) {
      rim_col = mix(rim_col, rim_col * light_col, rim_l_mix);
    }

    float light_visibility = mix(1.0f, clamp(light_intensity * 1.5f, 0.0f, 1.0f), rim_l_mix);
    surface_color += rim_col * (rim_term * rim_f * light_visibility);
  }

  /* =========================================================================
   * 7. BUILT-IN DYNAMIC INVERTED HULL / CONTOUR ANIME OUTLINE
   * =========================================================================
   * Inverted Hull outlines are synthesized via DaskToon's Zero-Click VRM
   * auto-sync pipeline (Slot 2 Inverted Hull Solidify). Frontface surface
   * remains clean and free of Fresnel crease smudges. */

  /* =========================================================================
   * 8. BUILT-IN CINEMATIC COLOR GRADING LAYER (FAC = 0 WHEN DISABLED)
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
      float3 hsv = dt_rgb_to_hsv(graded);
      hsv.y = clamp(hsv.y * max(saturation, 0.0f), 0.0f, 1.0f);
      graded = dt_hsv_to_rgb(hsv);
    }

    /* Brightness & Contrast */
    graded += brightness;
    graded = (graded - 0.5f) * (1.0f + contrast) + 0.5f;
    graded = max(graded, float3(0.0f));

    surface_color = mix(surface_color, graded, grd_fac);
  }

  /* =========================================================================
   * 9. MASTER CONTROLS & FINAL EMISSION CLOSURE
   * ========================================================================= */
  surface_color = max(surface_color * max(strength, 0.0f), float3(0.0f));

  float a = clamp(alpha, 0.0f, 1.0f);
  ClosureTransparency transparency_data;
  transparency_data.weight = weight * (1.0f - a);
  transparency_data.transmittance = float3(1.0f);
  transparency_data.holdout = 0.0f;
  ClosureEmission emission_data;
  emission_data.weight = weight * a;
  emission_data.emission = surface_color;
  result = closure_add(closure_eval(transparency_data), closure_eval(emission_data));
}
