/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_metal(float4 base_color,
                      float4 metal_tint,
                      float4 spec_color,
                      float spec_sharpness,
                      float spec_intensity,
                      float anisotropy_angle,
                      float anisotropy_strength,
                      float rim_glint_power,
                      float rim_glint_width,
                      float3 N,
                      float3 tangent,
                      float weight,
                      Closure &result,
                      float4 &out_color,
                      float &out_spec_mask,
                      float &out_glint_mask)
{
  base_color = max(base_color, float4(0.0f));
  metal_tint = max(metal_tint, float4(0.0f));
  spec_color = max(spec_color, float4(0.0f));
  N = safe_normalize(N);

  float3 V = coordinate_incoming(g_data.P);
  float facing = abs(dot(V, N));

  /* 1. Stylized Anime MatCap Reflection (View-Space Normal mapping) */
  float2 matcap_uv = N.xy * 0.5f + 0.5f;
  float matcap_spec = clamp(pow(matcap_uv.y, 2.5f) * 1.5f + pow(matcap_uv.x, 3.0f) * 0.8f, 0.0f, 2.0f);

  /* 2. Anisotropic Specular Highlight Band (Blade & Armor sheen) */
  float3 T = safe_normalize(tangent);
  if (length(T) < 0.1f) {
    /* Fallback tangent perpendicular to normal */
    T = abs(N.z) < 0.999f ? cross(N, float3(0.0f, 0.0f, 1.0f)) : cross(N, float3(1.0f, 0.0f, 0.0f));
    T = safe_normalize(T);
  }

  /* Rotate tangent by anisotropy angle */
  float rad = anisotropy_angle * 6.2831853f;
  float3 B = cross(N, T);
  float3 rot_T = T * cos(rad) + B * sin(rad);

  float dot_TV = dot(rot_T, V);
  float aniso_val = sqrt(max(0.0f, 1.0f - dot_TV * dot_TV));
  float aniso_sharp = max(spec_sharpness * 30.0f, 1.0f);
  float aniso_spec = pow(aniso_val, aniso_sharp) * clamp(anisotropy_strength, 0.0f, 2.0f);

  /* Total Specular Mask */
  float total_spec = clamp((matcap_spec * 0.4f + aniso_spec * 0.8f) * spec_intensity, 0.0f, 2.0f);
  out_spec_mask = total_spec;

  /* 3. Sharp Rim Glint (Anime edge chớp sáng) */
  float rim = clamp(1.0f - facing, 0.0f, 1.0f);
  float r_power = max(rim_glint_power, 0.1f);
  float glint = pow(rim, r_power);
  float g_width = clamp(rim_glint_width, 0.01f, 1.0f);
  float glint_mask = smoothstep(1.0f - g_width, 1.0f, glint);
  out_glint_mask = glint_mask;

  /* 4. Composite Metallic Anime Surface */
  float3 metal_rgb = mix(base_color.rgb, metal_tint.rgb * base_color.rgb, metal_tint.a);
  float3 spec_lit = spec_color.rgb * total_spec + spec_color.rgb * glint_mask * 1.5f;
  float3 final_color = metal_rgb + spec_lit;

  out_color = float4(final_color, base_color.a);

  /* 5. Metallic Lighting Closure */
  ClosureDiffuse diffuse_data;
  diffuse_data.weight = weight * 0.5f;
  diffuse_data.color = metal_rgb;
  diffuse_data.N = N;
  Closure lit_cl = closure_eval(diffuse_data);

  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = final_color * 0.6f;
  Closure emiss_cl = closure_eval(emission_data);

  result = closure_add(lit_cl, emiss_cl);
}
