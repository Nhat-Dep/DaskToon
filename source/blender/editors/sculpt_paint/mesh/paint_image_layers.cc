/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup edsculpt
 *
 * DaskToon paint layers (docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md, section 2): an image can
 * hold layers, each an image of its own (Python owns them: `Image.dasktoon_layers`, `Image.dasktoon_layer_index`, in
 * the image's system properties). Strokes go to the active layer's image; after each stroke step the painted region
 * of every image the layer belongs to is composited again, so the image itself, which the material, the image editor,
 * the render and the export see, is the composite.
 */

#include <algorithm>

#include "BLI_rect.h"
#include "BLI_vector.hh"

#include "DNA_image_types.h"
#include "DNA_windowmanager_types.h"

#include "BKE_context.hh"
#include "BKE_global.hh"
#include "BKE_idprop.hh"
#include "BKE_image.hh"
#include "BKE_lib_id.hh"
#include "BKE_main.hh"

#include "IMB_imbuf.hh"
#include "IMB_imbuf_types.hh"

#include "DEG_depsgraph.hh"

#include "RNA_access.hh"
#include "RNA_define.hh"

#include "WM_api.hh"
#include "WM_types.hh"

#include "ED_paint.hh"

#include "../paint_intern.hh"

namespace blender::ed::sculpt_paint {

namespace {

/** The blend modes, as the Python enum numbers them. */
enum class LayerBlend { Normal = 0, Multiply = 1, Add = 2, Screen = 3, Overlay = 4 };

struct PaintLayer {
  Image *image;
  float opacity;
  LayerBlend blend;
  bool hide;
};

float prop_float(const IDProperty *group, const char *name, const float fallback)
{
  const IDProperty *prop = IDP_GetPropertyFromGroup(group, name);
  if (prop == nullptr) {
    return fallback;
  }
  switch (prop->type) {
    case IDP_FLOAT:
      return IDP_float_get(prop);
    case IDP_DOUBLE:
      return float(IDP_double_get(prop));
    case IDP_INT:
      return float(IDP_int_get(prop));
    default:
      return fallback;
  }
}

int prop_int(const IDProperty *group, const char *name, const int fallback)
{
  const IDProperty *prop = IDP_GetPropertyFromGroup(group, name);
  if (prop == nullptr) {
    return fallback;
  }
  switch (prop->type) {
    case IDP_INT:
      return IDP_int_get(prop);
    case IDP_BOOLEAN:
      return IDP_bool_get(prop);
    default:
      return fallback;
  }
}

/** The layers of `image`, bottom first (Python's order); `r_active` the active one's index. */
Vector<PaintLayer> layers_of(const Image &image, int *r_active = nullptr)
{
  Vector<PaintLayer> layers;
  const IDProperty *props = image.id.system_properties;
  const IDProperty *list = props ? IDP_GetPropertyTypeFromGroup(props, "dasktoon_layers", IDP_IDPARRAY) :
                                   nullptr;
  if (list == nullptr) {
    return layers;
  }
  const IDProperty *items = IDP_property_array_get(list);
  for (int i = 0; i < list->len; i++) {
    const IDProperty *pointer = IDP_GetPropertyTypeFromGroup(&items[i], "image", IDP_ID);
    PaintLayer layer;
    layer.image = pointer ? reinterpret_cast<Image *>(IDP_ID_get(pointer)) : nullptr;
    layer.opacity = std::clamp(prop_float(&items[i], "opacity", 1.0f), 0.0f, 1.0f);
    layer.blend = LayerBlend(std::clamp(prop_int(&items[i], "blend", 0), 0, 4));
    layer.hide = prop_int(&items[i], "hide", 0) != 0;
    layers.append(layer);
  }
  if (r_active) {
    *r_active = prop_int(props, "dasktoon_layer_index", 0);
  }
  return layers;
}

float blend_channel(const LayerBlend blend, const float below, const float above)
{
  switch (blend) {
    case LayerBlend::Multiply:
      return below * above;
    case LayerBlend::Add:
      return below + above;
    case LayerBlend::Screen:
      return 1.0f - (1.0f - below) * (1.0f - above);
    case LayerBlend::Overlay:
      return below <= 0.5f ? 2.0f * below * above : 1.0f - 2.0f * (1.0f - below) * (1.0f - above);
    case LayerBlend::Normal:
    default:
      return above;
  }
}

/** A layer's pixel as straight RGBA, from its byte or float buffer. */
void read_pixel(const ImBuf &ibuf, const int index, float r_rgba[4])
{
  if (const float *data = ibuf.float_data()) {
    const float *pixel = data + size_t(index) * ibuf.channels;
    r_rgba[0] = pixel[0];
    r_rgba[1] = ibuf.channels > 1 ? pixel[1] : pixel[0];
    r_rgba[2] = ibuf.channels > 2 ? pixel[2] : pixel[0];
    r_rgba[3] = ibuf.channels > 3 ? pixel[3] : 1.0f;
    return;
  }
  const uint8_t *pixel = ibuf.byte_data() + size_t(index) * 4;
  for (int c = 0; c < 4; c++) {
    r_rgba[c] = pixel[c] / 255.0f;
  }
}

/**
 * Composite the visible layers into `image`'s pixels inside `rect` (the W3C separable blend over a transparent
 * start, straight alpha in and out). False when the image has no layers or no pixels.
 */
bool composite_rect(Image &image, const rcti *region)
{
  const Vector<PaintLayer> layers = layers_of(image);
  if (layers.is_empty()) {
    return false;
  }
  ImBuf *dst = BKE_image_acquire_ibuf(&image, nullptr, nullptr);
  if (dst == nullptr) {
    return false;
  }
  rcti rect;
  BLI_rcti_init(&rect, 0, dst->x, 0, dst->y);
  if (region != nullptr && !BLI_rcti_isect(&rect, region, &rect)) {
    BKE_image_release_ibuf(&image, dst, nullptr);
    return false;
  }

  struct Source {
    const ImBuf *ibuf;
    float opacity;
    LayerBlend blend;
  };
  Vector<Source> sources;
  Vector<std::pair<Image *, ImBuf *>> acquired;
  for (const PaintLayer &layer : layers) {
    if (layer.image == nullptr || layer.image == &image) {
      continue;
    }
    ImBuf *ibuf = BKE_image_acquire_ibuf(layer.image, nullptr, nullptr);
    if (ibuf == nullptr) {
      continue;
    }
    acquired.append({layer.image, ibuf});
    /* A layer of another size is left out (spec, ruling 3). */
    if (!layer.hide && layer.opacity > 0.0f && ibuf->x == dst->x && ibuf->y == dst->y) {
      sources.append({ibuf, layer.opacity, layer.blend});
    }
  }

  float *dst_float = dst->float_data() ? dst->float_data_for_write() : nullptr;
  uint8_t *dst_byte = dst_float ? nullptr : dst->byte_data_for_write();
  for (int y = rect.ymin; y < rect.ymax; y++) {
    for (int x = rect.xmin; x < rect.xmax; x++) {
      const int index = y * dst->x + x;
      float out[4] = {0.0f, 0.0f, 0.0f, 0.0f};
      for (const Source &source : sources) {
        float src[4];
        read_pixel(*source.ibuf, index, src);
        const float src_alpha = src[3] * source.opacity;
        if (src_alpha <= 0.0f) {
          continue;
        }
        const float below_alpha = out[3];
        const float alpha = src_alpha + below_alpha * (1.0f - src_alpha);
        for (int c = 0; c < 3; c++) {
          const float mixed = (1.0f - below_alpha) * src[c] +
                              below_alpha * blend_channel(source.blend, out[c], src[c]);
          const float premultiplied = src_alpha * mixed + (1.0f - src_alpha) * below_alpha * out[c];
          out[c] = alpha > 0.0f ? premultiplied / alpha : 0.0f;
        }
        out[3] = alpha;
      }
      if (dst_float) {
        float *pixel = dst_float + size_t(index) * dst->channels;
        for (int c = 0; c < std::min(dst->channels, 4); c++) {
          pixel[c] = out[c];
        }
      }
      else if (dst_byte) {
        uint8_t *pixel = dst_byte + size_t(index) * 4;
        for (int c = 0; c < 4; c++) {
          pixel[c] = uint8_t(std::clamp(out[c], 0.0f, 1.0f) * 255.0f + 0.5f);
        }
      }
    }
  }
  for (const std::pair<Image *, ImBuf *> &item : acquired) {
    BKE_image_release_ibuf(item.first, item.second, nullptr);
  }

  if (dst_float) {
    dst->userflags |= IB_RECT_INVALID; /* The byte copy is made again from the floats. */
  }
  dst->userflags |= IB_DISPLAY_BUFFER_INVALID;
  BKE_image_mark_dirty(&image, dst);
  BKE_image_release_ibuf(&image, dst, nullptr);

  if (region == nullptr) {
    BKE_image_partial_update_mark_full_update(&image);
  }
  else {
    BKE_image_update_gputexture(
        &image, nullptr, rect.xmin, rect.ymin, BLI_rcti_size_x(&rect), BLI_rcti_size_y(&rect));
  }
  DEG_id_tag_update(&image.id, 0);
  return true;
}

bool has_layer(const Image &owner, const Image *layer)
{
  for (const PaintLayer &item : layers_of(owner)) {
    if (item.image == layer) {
      return true;
    }
  }
  return false;
}

}  // namespace

}  // namespace blender::ed::sculpt_paint

namespace blender {

using namespace ed::sculpt_paint;

Image *ED_paint_layers_target(Image *image)
{
  if (image == nullptr || image->source == IMA_SRC_TILED) {
    return image; /* Layers are for single images (spec, ruling 3). */
  }
  int active = 0;
  const Vector<PaintLayer> layers = layers_of(*image, &active);
  if (active < 0 || active >= layers.size() || layers[active].image == nullptr ||
      layers[active].image == image)
  {
    return image;
  }
  return layers[active].image;
}

bool ED_paint_layers_composite(Image *image, const rcti *region)
{
  return image != nullptr && composite_rect(*image, region);
}

void ED_paint_layers_painted(Main *bmain, Image *layer, const rcti *region)
{
  if (bmain == nullptr || layer == nullptr) {
    return;
  }
  for (Image *owner = static_cast<Image *>(bmain->images.first); owner;
       owner = static_cast<Image *>(owner->id.next))
  {
    if (owner != layer && has_layer(*owner, layer)) {
      composite_rect(*owner, region);
    }
  }
}

void ED_paint_layers_refresh_all(Main *bmain)
{
  if (bmain == nullptr) {
    return;
  }
  for (Image *image = static_cast<Image *>(bmain->images.first); image;
       image = static_cast<Image *>(image->id.next))
  {
    composite_rect(*image, nullptr);
  }
}

static wmOperatorStatus dasktoon_layers_composite_exec(bContext *C, wmOperator *op)
{
  Main *bmain = CTX_data_main(C);
  const std::string name = RNA_string_get(op->ptr, "image");
  if (name.empty()) {
    ED_paint_layers_refresh_all(bmain);
    WM_event_add_notifier(C, NC_IMAGE | NA_EDITED, nullptr);
    return OPERATOR_FINISHED;
  }
  Image *image = reinterpret_cast<Image *>(BKE_libblock_find_name(bmain, ID_IM, name.c_str()));
  if (image == nullptr || !ED_paint_layers_composite(image, nullptr)) {
    return OPERATOR_CANCELLED;
  }
  WM_event_add_notifier(C, NC_IMAGE | NA_EDITED, image);
  return OPERATOR_FINISHED;
}

void PAINT_OT_dasktoon_layers_composite(wmOperatorType *ot)
{
  ot->name = "Composite Paint Layers";
  ot->idname = "PAINT_OT_dasktoon_layers_composite";
  ot->description = "Composite the image's paint layers into the image (every image with layers when none is named)";

  ot->exec = dasktoon_layers_composite_exec;

  ot->flag = OPTYPE_INTERNAL;

  RNA_def_string(ot->srna, "image", nullptr, MAX_ID_NAME - 2, "Image", "The image whose layers to composite");
}

}  // namespace blender
