/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_set_depth(Closure cl,
                    float depth_offset,
                    float weight,
                    Closure &result)
{
  /* Reverse-Z depth offset: In Reverse-Z, higher values are closer to the camera.
   * Applying depth_offset moves the fragment forward (visible in front) or backward */
  gl_FragDepth = clamp(gl_FragCoord.z + depth_offset, 0.0f, 1.0f);
  result = cl;
}
