/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup shdnodes
 *
 * GPU and UI helpers of the DaskToon shading core (Anime BSDF, Anime Cel, Dask Cel).
 */

#pragma once

#include "NOD_dasktoon_shading.hh"
#include "node_shader_util.hh"

namespace blender::nodes::dasktoon {

struct ShadingGPULinks {
  GPUNodeLink *ramp_tex = nullptr;
  float ramp_layer = 0.0f;
  float ramp_mode = 0.0f;
  float ramp_constant = 0.0f;
};

/** Always returns a valid ramp texture (white when not in Ramp mode or without storage). */
ShadingGPULinks shading_gpu_links(GPUMaterial *mat, const bNode &node);
/** Simple/Ramp switch, then (Ramp only) style menu, save, convert buttons and the ramp widget. */
void draw_shading_buttons(ui::Layout &layout, PointerRNA *ptr);
/** Hide Shadow Color and Shadow Softness in Ramp mode (call from the node's updatefunc). */
void update_shading_sockets(bNodeTree &ntree, bNode &node);

}  // namespace blender::nodes::dasktoon
