/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_water_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Shallow Color"_ustr).default_value({0.20f, 0.85f, 0.85f, 1.0f});
  b.add_input<decl::Color>("Deep Color"_ustr).default_value({0.05f, 0.20f, 0.60f, 1.0f});
  b.add_input<decl::Color>("Foam Color"_ustr).default_value({1.0f, 1.0f, 1.0f, 1.0f});
  b.add_input<decl::Color>("Caustics Color"_ustr).default_value({0.80f, 1.0f, 1.0f, 0.8f});

  b.add_input<decl::Float>("Depth Steepness"_ustr)
      .default_value(1.5f)
      .min(0.1f)
      .max(10.0f);
  b.add_input<decl::Float>("Foam Width"_ustr)
      .default_value(0.15f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Caustics Scale"_ustr)
      .default_value(2.0f)
      .min(0.1f)
      .max(20.0f);
  b.add_input<decl::Float>("Caustics Speed"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(10.0f);
  b.add_input<decl::Float>("Opacity"_ustr)
      .default_value(0.85f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Foam Mask"_ustr);
}

static int node_shader_gpu_anime_water(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                        GPUNodeStack *in,
                                        GPUNodeStack *out)
{
  if (!in[9].link) {
    GPU_link(mat, "world_normals_get", &in[9].link);
  }
  if (!in[10].link) {
    GPU_link(mat, "world_position_get", &in[10].link);
  }

  GPU_material_flag_set(
      mat,
      GPU_MATFLAG_TRANSPARENT | GPU_MATFLAG_TRANSPARENT_MAYBE_COLORED | GPU_MATFLAG_EMISSION |
          GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_water", in, out);
}

}  // namespace nodes::node_shader_anime_water_cc

/* node type definition */
void register_node_type_sh_anime_water()
{
  namespace file_ns = nodes::node_shader_anime_water_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeWater"_ustr, SH_NODE_ANIME_WATER);
  ntype.ui_name = "Anime Water";
  ntype.ui_description = "Native DaskToon Stepped Depth, Foam & Animated Caustics Anime Water NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_WATER";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_water;

  bke::node_register_type(ntype);
}

}  // namespace blender
