/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_screenspace_info_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_output<decl::Vector>("Screen UV"_ustr);
  b.add_output<decl::Float>("Scene Depth"_ustr);
  b.add_output<decl::Color>("Scene Color"_ustr);
  b.add_output<decl::Vector>("Pixel Size"_ustr);
  b.add_output<decl::Float>("Aspect Ratio"_ustr);
}

static int node_shader_gpu_screenspace_info(GPUMaterial *mat,
                                            bNode *node,
                                            bNodeExecData * /*execdata*/,
                                            GPUNodeStack *in,
                                            GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_screenspace_info", in, out);
}

}  // namespace nodes::node_shader_screenspace_info_cc

/* node type definition */
void register_node_type_sh_screenspace_info()
{
  namespace file_ns = nodes::node_shader_screenspace_info_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeScreenspaceInfo"_ustr, SH_NODE_SCREENSPACE_INFO);
  ntype.ui_name = "Screenspace Info";
  ntype.ui_description = "Goo Engine Screenspace Info node: Access screen-space coordinates, depth, and scene color";
  ntype.enum_name_legacy = "SCREENSPACE_INFO";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_screenspace_info;

  bke::node_register_type(ntype);
}

}  // namespace blender
