/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_wood_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.75f, 0.52f, 0.35f, 1.0f});
  b.add_input<decl::Color>("Grain Color"_ustr).default_value({0.45f, 0.28f, 0.18f, 1.0f});
  b.add_input<decl::Color>("Shadow Color"_ustr).default_value({0.35f, 0.20f, 0.12f, 1.0f});

  b.add_input<decl::Float>("Grain Scale"_ustr)
      .default_value(4.0f)
      .min(0.1f)
      .max(50.0f);
  b.add_input<decl::Float>("Grain Distortion"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Grain Contrast"_ustr)
      .default_value(1.2f)
      .min(0.1f)
      .max(5.0f);

  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Edge Wear"_ustr)
      .default_value(0.2f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Grain Mask"_ustr);
}

static int node_shader_gpu_anime_wood(GPUMaterial *mat,
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

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_wood", in, out);
}

}  // namespace nodes::node_shader_anime_wood_cc

/* node type definition */
void register_node_type_sh_anime_wood()
{
  namespace file_ns = nodes::node_shader_anime_wood_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeWood"_ustr, SH_NODE_ANIME_WOOD);
  ntype.ui_name = "Anime Wood";
  ntype.ui_description = "Native DaskToon Hand-Painted Anime Wood & Bamboo NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_WOOD";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_wood;

  bke::node_register_type(ntype);
}

}  // namespace blender
