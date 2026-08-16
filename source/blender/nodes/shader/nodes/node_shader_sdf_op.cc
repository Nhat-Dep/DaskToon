/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_sdf_op_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Float>("Distance A"_ustr).default_value(0.0f);
  b.add_input<decl::Float>("Distance B"_ustr).default_value(0.0f);
  b.add_input<decl::Float>("Smoothness"_ustr).default_value(0.1f).min(0.0f).max(5.0f);

  b.add_output<decl::Float>("Union"_ustr);
  b.add_output<decl::Float>("Subtract"_ustr);
  b.add_output<decl::Float>("Intersect"_ustr);
  b.add_output<decl::Float>("Smooth Union"_ustr);
}

static int node_shader_gpu_sdf_op(GPUMaterial *mat,
                                   bNode *node,
                                   bNodeExecData * /*execdata*/,
                                   GPUNodeStack *in,
                                   GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_sdf_op", in, out);
}

}  // namespace nodes::node_shader_sdf_op_cc

/* node type definition */
void register_node_type_sh_sdf_op()
{
  namespace file_ns = nodes::node_shader_sdf_op_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeSDFOp"_ustr, SH_NODE_SDF_OP);
  ntype.ui_name = "SDF Op";
  ntype.ui_description = "Goo Engine SDF Op: Boolean operations (Union, Subtract, Intersect, Smooth Union) on Signed Distance Fields";
  ntype.enum_name_legacy = "SDF_OP";
  ntype.nclass = NODE_CLASS_CONVERTER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_sdf_op;

  bke::node_register_type(ntype);
}

}  // namespace blender
