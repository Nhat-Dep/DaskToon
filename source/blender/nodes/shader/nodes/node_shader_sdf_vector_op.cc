/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_sdf_vector_op_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Vector"_ustr);
  b.add_input<decl::Vector>("Translation"_ustr).default_value({0.0f, 0.0f, 0.0f});
  b.add_input<decl::Vector>("Rotation"_ustr).default_value({0.0f, 0.0f, 0.0f});
  b.add_input<decl::Vector>("Scale"_ustr).default_value({1.0f, 1.0f, 1.0f});

  b.add_output<decl::Vector>("Vector"_ustr);
}

static int node_shader_gpu_sdf_vector_op(GPUMaterial *mat,
                                         bNode *node,
                                         bNodeExecData * /*execdata*/,
                                         GPUNodeStack *in,
                                         GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "generated_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_sdf_vector_op", in, out);
}

}  // namespace nodes::node_shader_sdf_vector_op_cc

/* node type definition */
void register_node_type_sh_sdf_vector_op()
{
  namespace file_ns = nodes::node_shader_sdf_vector_op_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeSDFVectorOp"_ustr, SH_NODE_SDF_VECTOR_OP);
  ntype.ui_name = "SDF Vector Op";
  ntype.ui_description = "Goo Engine SDF Vector Op: Spatial transform operations (Translate, Rotate, Scale) for SDF shapes";
  ntype.enum_name_legacy = "SDF_VECTOR_OP";
  ntype.nclass = NODE_CLASS_OP_VECTOR;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_sdf_vector_op;

  bke::node_register_type(ntype);
}

}  // namespace blender
