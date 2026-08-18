/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_face_shadow(float3 head_fwd,
                            float3 head_right,
                            float3 light_dir,
                            float face_map,
                            float shadow_thresh,
                            float shadow_softness,
                            float smoothing,
                            float3 geom_normal,
                            float &out_shadow_mask,
                            float &out_light_angle,
                            float &out_side_factor,
                            float3 &out_smooth_normal)
{
  head_fwd = safe_normalize(head_fwd);
  head_right = safe_normalize(head_right);
  geom_normal = safe_normalize(geom_normal);

  if (dot(light_dir, light_dir) < 1e-6f) {
    light_dir = float3(0.57735f, 0.57735f, 0.57735f);
  }
  else {
    light_dir = safe_normalize(light_dir);
  }

  /* 1. Project light vector onto head coordinate axes */
  float front_dot = dot(light_dir, head_fwd);
  float right_dot = dot(light_dir, head_right);
  out_light_angle = front_dot;
  out_side_factor = right_dot;

  /* 2. Compute pristine anime face normal:
   * Smooths bumpy geometry normals around nose, brow, and eyes towards head forward/right orientation */
  float3 head_up = cross(head_right, head_fwd);
  float3 flat_normal = safe_normalize(head_fwd * 0.70f + head_right * dot(geom_normal, head_right) * 0.45f + head_up * dot(geom_normal, head_up) * 0.30f);
  out_smooth_normal = safe_normalize(mix(geom_normal, flat_normal, clamp(smoothing, 0.0f, 1.0f)));

  /* 3. Compute anime face shadow factor */
  float fw = max(fwidth(front_dot), 0.0005f);
  float s_soft = max(shadow_softness, fw);

  float shadow_signal;
  if (face_map > 0.001f) {
    /* Industry SDF Face Map calculation (Genshin / Honkai / HoyoToon standard):
     * When light comes from the right, sample forward gradient; from left, invert. */
    float sdf_val = (right_dot >= 0.0f) ? (1.0f - face_map) : face_map;
    float light_azimuth = clamp(abs(right_dot) * 0.7f - front_dot * 0.5f + shadow_thresh + 0.5f, 0.0f, 1.0f);
    shadow_signal = 1.0f - smoothstep(sdf_val - s_soft, sdf_val + s_soft, light_azimuth);
  }
  else {
    /* Procedural Face Shadow using smoothed anime normal */
    float n_dot_l = dot(out_smooth_normal, light_dir) * 0.5f + 0.5f;
    float s_min = clamp(shadow_thresh + 0.5f - s_soft * 0.5f, 0.0f, 1.0f);
    float s_max = clamp(shadow_thresh + 0.5f + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
    shadow_signal = smoothstep(s_min, s_max, n_dot_l);
  }

  out_shadow_mask = shadow_signal;
}
