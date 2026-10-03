/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup shdnodes
 */

#include <algorithm>

#include "MEM_guardedalloc.h"

#include "BKE_colorband.hh"
#include "BKE_node_legacy_types.hh"

#include "DNA_colorband_types.h"

#include "RNA_access.hh"

#include "UI_interface_c.hh"
#include "UI_interface_layout.hh"
#include "UI_resources.hh"

#include "node_shader_dasktoon_shading.hh"

namespace blender::nodes::dasktoon {

int shading_ramp_mode_bit(const int node_type_legacy)
{
  switch (node_type_legacy) {
    case SH_NODE_ANIME_CHARACTER:
      return 6;
    case SH_NODE_ANIME_CEL:
      return 8;
    case SH_NODE_DASK_CEL:
      return 0;
    default:
      return -1;
  }
}

bool shading_is_ramp_mode(const bNode &node)
{
  const int bit = shading_ramp_mode_bit(node.type_legacy);
  return bit >= 0 && (node.custom2 & (1 << bit)) != 0;
}

void shading_set_ramp_mode(bNode &node, const bool ramp)
{
  const int bit = shading_ramp_mode_bit(node.type_legacy);
  if (bit < 0) {
    return;
  }
  if (ramp) {
    node.custom2 = short(node.custom2 | (1 << bit));
    if (node.storage == nullptr) {
      node.storage = shading_ramp_new();
    }
  }
  else {
    node.custom2 = short(node.custom2 & ~(1 << bit));
  }
}

ColorBand *shading_ramp_new()
{
  ColorBand *coba = BKE_colorband_add(true);
  coba->tot = 2;
  coba->cur = 0;
  coba->ipotype = COLBAND_INTERP_CONSTANT;
  coba->data[0].r = 0.80f;
  coba->data[0].g = 0.62f;
  coba->data[0].b = 0.66f;
  coba->data[0].a = 1.0f;
  coba->data[0].pos = 0.0f;
  coba->data[1].r = 1.0f;
  coba->data[1].g = 1.0f;
  coba->data[1].b = 1.0f;
  coba->data[1].a = 1.0f;
  coba->data[1].pos = 0.5f;
  return coba;
}

int light_blend_mode_get(const bNode &node)
{
  if (node.type_legacy == SH_NODE_ANIME_CHARACTER) {
    return (node.custom1 >> 8) & 0x0F;
  }
  return node.custom2 & 0x0F;
}

void light_blend_mode_set(bNode &node, const int value)
{
  if (node.type_legacy == SH_NODE_ANIME_CHARACTER) {
    node.custom1 = short((node.custom1 & ~0x0F00) | ((value & 0x0F) << 8));
  }
  else {
    node.custom2 = short((node.custom2 & ~0x000F) | (value & 0x0F));
  }
}

ShadingGPULinks shading_gpu_links(GPUMaterial *mat, const bNode &node)
{
  ShadingGPULinks links;
  const ColorBand *coba = static_cast<const ColorBand *>(node.storage);
  const bool ramp = shading_is_ramp_mode(node) && coba != nullptr;
  float *array = nullptr;
  int size = 0;
  if (ramp) {
    BKE_colorband_evaluate_table_rgba(coba, &array, &size);
    links.ramp_constant = (coba->ipotype == COLBAND_INTERP_CONSTANT) ? 1.0f : 0.0f;
  }
  else {
    /* Same allocator as BKE_colorband_evaluate_table_rgba: GPU_color_band frees with MEM_delete. */
    size = 2;
    array = MEM_new_array_zeroed<float>(size_t(size) * 4, __func__);
    std::fill_n(array, size * 4, 1.0f);
  }
  links.ramp_tex = GPU_color_band(mat, size, array, &links.ramp_layer);
  links.ramp_mode = ramp ? 1.0f : 0.0f;
  return links;
}

void update_shading_sockets(bNodeTree &ntree, bNode &node)
{
  const bool simple = !shading_is_ramp_mode(node);
  for (bNodeSocket &sock : node.inputs) {
    if (STREQ(sock.name, "Shadow Color") || STREQ(sock.name, "Shadow Softness")) {
      bke::node_set_socket_availability(ntree, sock, simple);
    }
  }
}

void draw_shading_buttons(ui::Layout &layout, PointerRNA *ptr)
{
  layout.prop(ptr, "shading_mode", ui::ITEM_R_EXPAND, std::nullopt, ICON_NONE);
  if (RNA_enum_get(ptr, "shading_mode") != 1) {
    return;
  }
  ui::Layout &row = layout.row(true);
  row.menu("NODE_MT_dasktoon_shading_styles", IFACE_("Style"), ICON_NONE);
  row.op("DASKTOON_OT_shading_style_save", "", ICON_FILE_TICK);
  row.op("DASKTOON_OT_shading_ramp_from_simple", "", ICON_IMPORT);
  template_color_ramp(&layout, ptr, "shading_ramp", false);
}

}  // namespace blender::nodes::dasktoon
