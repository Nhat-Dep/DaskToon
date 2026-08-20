/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_rim_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Rim Color"_ustr).default_value({0.80f, 0.90f, 1.0f, 1.0f});
  b.add_input<decl::Float>("Rim Power"_ustr)
      .default_value(3.0f)
      .min(0.1f)
      .max(20.0f);
  b.add_input<decl::Float>("Rim Width"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Rim Softness"_ustr)
      .default_value(0.05f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
}

static int node_shader_gpu_anime_rim(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  if (!in[4].link) {
    GPU_link(mat, "world_normals_get", &in[4].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_EMISSION);

  return GPU_stack_link(mat, node, "node_anime_rim", in, out);
}

}  // namespace nodes::node_shader_anime_rim_cc

/* node type definition */
void register_node_type_sh_anime_rim()
{
  namespace file_ns = nodes::node_shader_anime_rim_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeRim"_ustr, SH_NODE_ANIME_RIM);
  ntype.ui_name = "Anime Rim";
  ntype.ui_description = "Native DaskToon Crisp & Soft Anime Rim Light / Backlight Shader Node";
  ntype.enum_name_legacy = "ANIME_RIM";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_rim;

  bke::node_register_type(ntype);
}

}  // namespace blender
