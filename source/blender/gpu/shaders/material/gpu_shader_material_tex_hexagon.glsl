/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_tex_hexagon(float3 p,
                      float scale,
                      float line_width,
                      float4 &out_color,
                      float &out_fac)
{
  float2 uv = p.xy * scale;
  float2 r = float2(1.0f, 1.7320508f);
  float2 h = r * 0.5f;

  float2 a = mod(uv, r) - h;
  float2 b = mod(uv - h, r) - h;

  float2 gv = dot(a, a) < dot(b, b) ? a : b;

  float d = max(abs(gv.x) * 1.5f + abs(gv.y) * 0.8660254f, abs(gv.y) * 1.7320508f);
  float edge = smoothstep(0.5f - line_width, 0.5f, d);

  out_fac = edge;
  out_color = float4(edge, edge, edge, 1.0f);
}
