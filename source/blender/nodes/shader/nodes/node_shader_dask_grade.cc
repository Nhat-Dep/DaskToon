/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_dask_grade_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Color"_ustr)
      .default_value({1.0f, 1.0f, 1.0f, 1.0f})
      .description("Base color input to apply color grading to");
  b.add_input<decl::Color>("Color Filter"_ustr)
      .default_value({1.0f, 1.0f, 1.0f, 1.0f})
      .description("Global atmospheric cinematic color filter");
  b.add_input<decl::Color>("Shadow Tint"_ustr)
      .default_value({0.58f, 0.60f, 0.77f, 1.0f})
      .description("Color tint applied specifically to shadows (Split Toning)");
  b.add_input<decl::Color>("Highlight Tint"_ustr)
      .default_value({1.0f, 0.96f, 0.90f, 1.0f})
      .description("Color tint applied specifically to highlights (Split Toning)");
  b.add_input<decl::Float>("Saturation"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(3.0f)
      .subtype(PROP_FACTOR)
      .description("Anime color saturation / vibrancy boost");
  b.add_input<decl::Float>("Brightness"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f);
  b.add_input<decl::Float>("Contrast"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f);
  b.add_input<decl::Float>("Strength"_ustr).default_value(1.0f).min(0.0f).max(10.0f);
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Standalone Anime Color Grading BSDF output");
  b.add_output<decl::Color>("Color"_ustr).description("Graded anime color result");
}

static int node_shader_gpu_dask_grade(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  GPU_material_flag_set(mat, GPU_MATFLAG_EMISSION);
  return GPU_stack_link(mat, node, "node_dask_grade", in, out);
}

}  // namespace nodes::node_shader_dask_grade_cc

/* node type definition */
void register_node_type_sh_dask_grade()
{
  namespace file_ns = nodes::node_shader_dask_grade_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskGrade"_ustr, SH_NODE_DASK_GRADE);
  ntype.ui_name = "Color Grade";
  ntype.ui_description = "Standalone Cinematic Anime Color Grading (Color Filter, Shadow/Highlight Split Toning, Saturation)";
  ntype.enum_name_legacy = "DASK_GRADE";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_grade;

  bke::node_register_type(ntype);
}

}  // namespace blender
