/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Storage layout of the DaskToon shading core shared by Anime BSDF, Anime Cel and Dask Cel.
 * Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md, section 3.5.
 */

#pragma once

struct bNode;
struct ColorBand;

namespace blender::nodes::dasktoon {

/** Bit of bNode::custom2 that selects Ramp shading, or -1 for other node types. */
int shading_ramp_mode_bit(int node_type_legacy);
bool shading_is_ramp_mode(const bNode &node);
/** Switching to Ramp creates the ColorBand storage when a legacy node has none. */
void shading_set_ramp_mode(bNode &node, bool ramp);
/** New ColorBand initialized with the "Anime 2 tông" preset. */
ColorBand *shading_ramp_new();
/** Anime BSDF: custom1 bits 8-11. Anime Cel: custom2 bits 0-3. */
int light_blend_mode_get(const bNode &node);
void light_blend_mode_set(bNode &node, int value);

}  // namespace blender::nodes::dasktoon
