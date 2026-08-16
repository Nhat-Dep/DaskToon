/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_light_info_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Int>("Light Index"_ustr).default_value(0).min(0).max(32);
  b.add_input<decl::Int>("Light Group"_ustr).default_value(0).min(0).max(128);

  b.add_output<decl::Vector>("Light Vector"_ustr);
  b.add_output<decl::Color>("Light Color"_ustr);
  b.add_output<decl::Float>("Light Power"_ustr);
  b.add_output<decl::Float>("Is Sun"_ustr);
}

static int node_shader_gpu_light_info(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_light_info", in, out);
}

}  // namespace nodes::node_shader_light_info_cc

/* node type definition */
void register_node_type_sh_light_info()
{
  namespace file_ns = nodes::node_shader_light_info_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeLightInfo"_ustr, SH_NODE_LIGHT_INFO);
  ntype.ui_name = "Light Info";
  ntype.ui_description = "Goo Engine Light Info node: Retrieve scene light vectors, color, power, and type with Light Group filtering";
  ntype.enum_name_legacy = "LIGHT_INFO";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_light_info;

  bke::node_register_type(ntype);
}

}  // namespace blender
