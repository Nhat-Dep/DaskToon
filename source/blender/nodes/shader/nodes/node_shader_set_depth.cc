/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_set_depth_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Shader>("Shader"_ustr);
  b.add_input<decl::Float>("Depth Offset"_ustr).default_value(-0.005f).min(-1.0f).max(1.0f);
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("Shader"_ustr);
}

static int node_shader_gpu_set_depth(GPUMaterial *mat,
                                     bNode *node,
                                     bNodeExecData * /*execdata*/,
                                     GPUNodeStack *in,
                                     GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_set_depth", in, out);
}

}  // namespace nodes::node_shader_set_depth_cc

/* node type definition */
void register_node_type_sh_set_depth()
{
  namespace file_ns = nodes::node_shader_set_depth_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeSetDepth"_ustr, SH_NODE_SET_DEPTH);
  ntype.ui_name = "Set Depth";
  ntype.ui_description = "Goo Engine Set Depth node: Offsets pixel z-depth in Reverse-Z for Eyebrows/Eyes through Hair and 2.5D layer sorting";
  ntype.enum_name_legacy = "SET_DEPTH";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_set_depth;

  bke::node_register_type(ntype);
}

}  // namespace blender
