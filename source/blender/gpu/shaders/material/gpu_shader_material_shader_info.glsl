/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_shader_info(Closure cl,
                      int light_group,
                      float4 &out_color,
                      float4 &out_diffuse_light,
                      float &out_shadow,
                      float4 &out_ambient,
                      float4 &out_specular)
{
  float4 rgba = closure_to_rgba(cl);
  out_color = rgba;

  /* Diffuse light irradiance */
  out_diffuse_light = float4(rgba.rgb, 1.0f);

  /* Shadow intensity calculated from light radiance luminance */
  float lum = dot(rgba.rgb, float3(0.2126f, 0.7152f, 0.0722f));
  out_shadow = clamp(1.0f - lum, 0.0f, 1.0f);

  /* Ambient floor estimation */
  out_ambient = float4(rgba.rgb * 0.1f, 1.0f);

  /* Specular reflection component */
  out_specular = float4(pow(rgba.rgb, float3(2.2f)), 1.0f);
}
