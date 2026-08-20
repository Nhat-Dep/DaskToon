/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_oklab_color_ramp_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Float>("Fac"_ustr).default_value(0.5f).min(0.0f).max(1.0f).subtype(PROP_FACTOR);
  b.add_input<decl::Color>("Color 1"_ustr).default_value({0.1f, 0.1f, 0.2f, 1.0f});
  b.add_input<decl::Color>("Color 2"_ustr).default_value({0.6f, 0.3f, 0.4f, 1.0f});
  b.add_input<decl::Color>("Color 3"_ustr).default_value({1.0f, 0.8f, 0.7f, 1.0f});
  b.add_input<decl::Float>("Pos 1"_ustr).default_value(0.0f).min(0.0f).max(1.0f);
  b.add_input<decl::Float>("Pos 2"_ustr).default_value(0.5f).min(0.0f).max(1.0f);
  b.add_input<decl::Float>("Pos 3"_ustr).default_value(1.0f).min(0.0f).max(1.0f);

  b.add_output<decl::Color>("Color"_ustr);
}

static int node_shader_gpu_oklab_color_ramp(GPUMaterial *mat,
                                            bNode *node,
                                            bNodeExecData * /*execdata*/,
                                            GPUNodeStack *in,
                                            GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_oklab_color_ramp", in, out);
}

}  // namespace nodes::node_shader_oklab_color_ramp_cc

/* node type definition */
void register_node_type_sh_oklab_color_ramp()
{
  namespace file_ns = nodes::node_shader_oklab_color_ramp_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeOKLabColorRamp"_ustr, SH_NODE_OKLAB_COLOR_RAMP);
  ntype.ui_name = "OKLab Ramp";
  ntype.ui_description = "Goo Engine OKLab Color Ramp: Perceptually uniform color interpolation preventing desaturated grayish anime boundaries";
  ntype.enum_name_legacy = "OKLAB_COLOR_RAMP";
  ntype.nclass = NODE_CLASS_CONVERTER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_oklab_color_ramp;

  bke::node_register_type(ntype);
}

}  // namespace blender
