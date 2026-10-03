/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_material_dasktoon_shading.glsl"
#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

/* Classic Cel: shared DaskToon shading core (Simple or Ramp), ambient and light modes, and the
 * toon specular of the original node-group version.
 * Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md (3.4, 3.6, 3.10). */
[[node]]
void node_anime_cel(float4 base_color,
                    float4 shadow_color,
                    float shadow_thresh,
                    float shadow_softness,
                    float4 ambient_color,
                    float ambient_blend,
                    float ambient_shadow_only,
                    float light_tint_strength,
                    float4 spec_color,
                    float spec_size,
                    float spec_softness,
                    float3 N,
                    float weight,
                    const float4 modes,
                    sampler1DArray ramp_tex,
                    float ramp_layer,
                    Closure &result,
                    float4 &out_color)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  ambient_color = max(ambient_color, float4(0.0f));
  spec_color = max(spec_color, float4(0.0f));
  N = safe_normalize(N);
  int ambient_mode = int(modes.x + 0.5f);
  int light_mode = int(modes.y + 0.5f);

  /* Ambient: tints the shadow tone, and the lit tone unless "shadow only". */
  float3 amb_rgb = ambient_color.rgb;
  float blend_fac = clamp(ambient_blend * ambient_color.a, 0.0f, 1.0f);
  float3 shadow_amb = mix(
      shadow_color.rgb, dt_ambient_mode(shadow_color.rgb, amb_rgb, ambient_mode), blend_fac);
  float3 lit_col = base_color.rgb;
  if (ambient_shadow_only < 0.5f) {
    lit_col = mix(lit_col, lit_col * amb_rgb, blend_fac * 0.5f);
  }

  /* Scene light. */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  float3 light_col = closure_to_rgba(closure_eval(diff_in)).rgb;
  float light = max(max(light_col.r, light_col.g), light_col.b);

  /* Shading core. */
  float cel;
  float3 color;
  if (modes.z > 0.5f) {
    color = dt_shade_ramp(light, lit_col, shadow_thresh, ramp_tex, ramp_layer, modes.w, cel);
  }
  else {
    color = dt_shade_simple(light, lit_col, shadow_amb, shadow_thresh, shadow_softness, cel);
  }

  /* Lamp color on the lit side. */
  color = mix(color,
              dt_light_mode(color, light_col, dt_light_norm(light_col), light_tint_strength, light_mode),
              cel);

  /* Toon specular: glossy light level cut at (1 - size). */
  ClosureReflection refl;
  refl.weight = 1.0f;
  refl.color = float3(1.0f);
  refl.N = N;
  refl.roughness = 0.05f;
  float glossy = dt_luminance(closure_to_rgba(closure_eval(refl)).rgb);
  float spec = clamp((glossy - (1.0f - spec_size)) / max(spec_softness, 0.0001f), 0.0f, 1.0f);
  color += spec_color.rgb * spec;

  out_color = float4(color, base_color.a);
  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = color;
  result = closure_eval(emission_data);
}
