/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_twirl_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Vector"_ustr);
  b.add_input<decl::Vector>("Center"_ustr).default_value({0.5f, 0.5f, 0.0f});
  b.add_input<decl::Float>("Strength"_ustr).default_value(3.14159f).min(-20.0f).max(20.0f);
  b.add_input<decl::Float>("Radius"_ustr).default_value(0.5f).min(0.01f).max(10.0f);

  b.add_output<decl::Vector>("Vector"_ustr);
}

static int node_shader_gpu_twirl(GPUMaterial *mat,
                                 bNode *node,
                                 bNodeExecData * /*execdata*/,
                                 GPUNodeStack *in,
                                 GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "generated_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_twirl", in, out);
}

}  // namespace nodes::node_shader_twirl_cc

/* node type definition */
void register_node_type_sh_twirl()
{
  namespace file_ns = nodes::node_shader_twirl_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeTwirl"_ustr, SH_NODE_TWIRL);
  ntype.ui_name = "Twirl";
  ntype.ui_description = "Goo Engine Twirl node: Rotational vortex distortion for anime magical spells, energy effects, and stylized warps";
  ntype.enum_name_legacy = "TWIRL";
  ntype.nclass = NODE_CLASS_OP_VECTOR;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_twirl;

  bke::node_register_type(ntype);
}

}  // namespace blender
