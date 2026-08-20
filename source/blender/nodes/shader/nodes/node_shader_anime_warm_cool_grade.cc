/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_warm_cool_grade_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.92f, 0.84f, 0.80f, 1.0f});
  b.add_input<decl::Color>("Lit Warm Tint"_ustr).default_value({1.05f, 1.00f, 0.92f, 1.0f});
  b.add_input<decl::Color>("Shadow Cool Tint"_ustr).default_value({0.82f, 0.86f, 1.08f, 1.0f});
  b.add_input<decl::Float>("Penumbra Saturation"_ustr)
      .default_value(1.25f)
      .min(1.0f)
      .max(3.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Shadow Factor"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_output<decl::Color>("Graded Color"_ustr);
}

static int node_shader_gpu_anime_warm_cool_grade(GPUMaterial *mat,
                                                  bNode *node,
                                                  bNodeExecData * /*execdata*/,
                                                  GPUNodeStack *in,
                                                  GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_anime_warm_cool_grade", in, out);
}

}  // namespace nodes::node_shader_anime_warm_cool_grade_cc

/* node type definition */
void register_node_type_sh_anime_warm_cool_grade()
{
  namespace file_ns = nodes::node_shader_anime_warm_cool_grade_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeWarmCoolGrade"_ustr, SH_NODE_ANIME_WARM_COOL_GRADE);
  ntype.ui_name = "Warm/Cool Grade";
  ntype.ui_description = "Native DaskToon Penumbra Saturation Boost & Warm/Cool Color Grade (Lit Warm Tint vs Shadow Cool Tint)";
  ntype.enum_name_legacy = "ANIME_WARM_COOL_GRADE";
  ntype.nclass = NODE_CLASS_OP_COLOR;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_warm_cool_grade;

  bke::node_register_type(ntype);
}

}  // namespace blender
