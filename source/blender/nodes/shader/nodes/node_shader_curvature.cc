/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_curvature_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Float>("Radius"_ustr).default_value(1.0f).min(0.01f).max(10.0f);
  b.add_input<decl::Float>("Contrast"_ustr).default_value(1.0f).min(0.0f).max(10.0f);
  b.add_input<decl::Float>("Invert"_ustr).default_value(0.0f).min(0.0f).max(1.0f);

  b.add_output<decl::Float>("Curvature"_ustr);
  b.add_output<decl::Float>("Cavity"_ustr);
  b.add_output<decl::Float>("Ridge"_ustr);
}

static int node_shader_gpu_curvature(GPUMaterial *mat,
                                     bNode *node,
                                     bNodeExecData * /*execdata*/,
                                     GPUNodeStack *in,
                                     GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_curvature", in, out);
}

}  // namespace nodes::node_shader_curvature_cc

/* node type definition */
void register_node_type_sh_curvature()
{
  namespace file_ns = nodes::node_shader_curvature_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeCurvature"_ustr, SH_NODE_CURVATURE);
  ntype.ui_name = "Curvature";
  ntype.ui_description = "Goo Engine Curvature node: Real-time geometry cavity and ridge extraction from screen-space normal derivatives";
  ntype.enum_name_legacy = "CURVATURE";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_curvature;

  bke::node_register_type(ntype);
}

}  // namespace blender
