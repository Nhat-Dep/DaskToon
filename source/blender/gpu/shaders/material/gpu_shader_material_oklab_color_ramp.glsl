/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

float3 linear_to_oklab(float3 c)
{
  float l = 0.4122214708f * c.r + 0.5363325363f * c.g + 0.0514459929f * c.b;
  float m = 0.2119034982f * c.r + 0.6806995451f * c.g + 0.1073969566f * c.b;
  float s = 0.0883024619f * c.r + 0.2817188376f * c.g + 0.6299787005f * c.b;

  float l_ = pow(max(l, 0.0f), 1.0f / 3.0f);
  float m_ = pow(max(m, 0.0f), 1.0f / 3.0f);
  float s_ = pow(max(s, 0.0f), 1.0f / 3.0f);

  return float3(0.2104542553f * l_ + 0.7936177850f * m_ - 0.0040720468f * s_,
                1.9779984951f * l_ - 2.4285922050f * m_ + 0.4505937099f * s_,
                0.0259040371f * l_ + 0.7827717662f * m_ - 0.8086757660f * s_);
}

float3 oklab_to_linear(float3 c)
{
  float l_ = c.x + 0.3963377774f * c.y + 0.2158037573f * c.z;
  float m_ = c.x - 0.1055613458f * c.y - 0.0638541728f * c.z;
  float s_ = c.x - 0.0894841775f * c.y - 1.2914855480f * c.z;

  float l = l_ * l_ * l_;
  float m = m_ * m_ * m_;
  float s = s_ * s_ * s_;

  return float3(+4.0767416621f * l - 3.3077115913f * m + 0.2309699292f * s,
                -1.2684380046f * l + 2.6097574011f * m - 0.3413193965f * s,
                -0.0041960863f * l - 0.7034186147f * m + 1.7076147010f * s);
}

[[node]]
void node_oklab_color_ramp(float fac,
                           float4 col1,
                           float4 col2,
                           float4 col3,
                           float pos1,
                           float pos2,
                           float pos3,
                           float4 &out_color)
{
  fac = clamp(fac, 0.0f, 1.0f);

  float3 lab1 = linear_to_oklab(col1.rgb);
  float3 lab2 = linear_to_oklab(col2.rgb);
  float3 lab3 = linear_to_oklab(col3.rgb);

  float3 lab_res;
  float alpha_res;

  if (fac <= pos2) {
    float t = clamp((fac - pos1) / max(pos2 - pos1, 0.0001f), 0.0f, 1.0f);
    lab_res = mix(lab1, lab2, t);
    alpha_res = mix(col1.a, col2.a, t);
  }
  else {
    float t = clamp((fac - pos2) / max(pos3 - pos2, 0.0001f), 0.0f, 1.0f);
    lab_res = mix(lab2, lab3, t);
    alpha_res = mix(col2.a, col3.a, t);
  }

  out_color = float4(clamp(oklab_to_linear(lab_res), 0.0f, 1.0f), alpha_res);
}
