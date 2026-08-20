/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_eye_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Iris Color"_ustr).default_value({0.15f, 0.45f, 0.85f, 1.0f});
  b.add_input<decl::Color>("Pupil Color"_ustr).default_value({0.02f, 0.05f, 0.12f, 1.0f});
  b.add_input<decl::Color>("Bottom Glow Color"_ustr).default_value({0.35f, 0.85f, 1.0f, 1.0f});
  b.add_input<decl::Float>("Bottom Glow Power"_ustr)
      .default_value(1.5f)
      .min(0.0f)
      .max(5.0f);
  b.add_input<decl::Color>("Top Shadow Tint"_ustr).default_value({0.08f, 0.12f, 0.25f, 1.0f});
  b.add_input<decl::Color>("Sparkle Color"_ustr).default_value({1.0f, 1.0f, 1.0f, 1.0f});
  b.add_input<decl::Vector>("UV Vector"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
}

static int node_shader_gpu_anime_eye(GPUMaterial *mat,
                                     bNode *node,
                                     bNodeExecData * /*execdata*/,
                                     GPUNodeStack *in,
                                     GPUNodeStack *out)
{
  GPU_material_flag_set(mat, GPU_MATFLAG_EMISSION);

  return GPU_stack_link(mat, node, "node_anime_eye", in, out);
}

}  // namespace nodes::node_shader_anime_eye_cc

/* node type definition */
void register_node_type_sh_anime_eye()
{
  namespace file_ns = nodes::node_shader_anime_eye_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeEye"_ustr, SH_NODE_ANIME_EYE);
  ntype.ui_name = "Anime Eye";
  ntype.ui_description = "Native DaskToon Anime Eye BSDF (Iris, Pupil, Crescent Bottom Glow, Top Eyelash Shadow & Sparkles)";
  ntype.enum_name_legacy = "ANIME_EYE";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.gather_link_search_ops = search_link_ops_for_shader_bsdf_node;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_200;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_eye;

  bke::node_register_type(ntype);
}

}  // namespace blender
