/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_knit_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Wool Color"_ustr).default_value({0.85f, 0.40f, 0.40f, 1.0f});
  b.add_input<decl::Color>("Shadow Color"_ustr).default_value({0.45f, 0.15f, 0.18f, 1.0f});
  b.add_input<decl::Color>("Fuzz Color"_ustr).default_value({1.0f, 0.85f, 0.85f, 0.8f})
      .description("Soft peach fuzz rim glow color");

  b.add_input<decl::Float>("Knit Scale"_ustr)
      .default_value(4.0f)
      .min(0.5f)
      .max(50.0f);
  b.add_input<decl::Float>("Knit Depth"_ustr)
      .default_value(0.6f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Fuzz Power"_ustr)
      .default_value(2.0f)
      .min(0.1f)
      .max(10.0f);
  b.add_input<decl::Float>("Fuzz Width"_ustr)
      .default_value(0.5f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Yarn Thickness"_ustr)
      .default_value(0.8f)
      .min(0.1f)
      .max(2.0f);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Knit Bump"_ustr);
  b.add_output<decl::Float>("Fuzz Mask"_ustr);
}

static int node_shader_gpu_anime_knit(GPUMaterial *mat,
                                       bNode *node,
                                       bNodeExecData * /*execdata*/,
                                       GPUNodeStack *in,
                                       GPUNodeStack *out)
{
  if (!in[8].link) {
    GPU_link(mat, "world_normals_get", &in[8].link);
  }
  if (!in[9].link) {
    GPU_link(mat, "world_position_get", &in[9].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_knit", in, out);
}

}  // namespace nodes::node_shader_anime_knit_cc

/* node type definition */
void register_node_type_sh_anime_knit()
{
  namespace file_ns = nodes::node_shader_anime_knit_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeKnit"_ustr, SH_NODE_ANIME_KNIT);
  ntype.ui_name = "Anime Knit & Wool";
  ntype.ui_description = "Native DaskToon V-Stitch Loop & Peach Fuzz Anime Knit Sweater & Wool NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_KNIT";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_knit;

  bke::node_register_type(ntype);
}

}  // namespace blender
