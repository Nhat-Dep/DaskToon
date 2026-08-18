/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_water_ripples_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Vector"_ustr);
  b.add_input<decl::Float>("Time"_ustr).default_value(0.0f);
  b.add_input<decl::Float>("Scale"_ustr).default_value(10.0f).min(0.1f).max(100.0f);
  b.add_input<decl::Float>("Speed"_ustr).default_value(1.0f).min(-10.0f).max(10.0f);
  b.add_input<decl::Float>("Amplitude"_ustr).default_value(0.1f).min(0.0f).max(2.0f);

  b.add_output<decl::Float>("Height"_ustr);
  b.add_output<decl::Vector>("Normal"_ustr);
}

static int node_shader_gpu_water_ripples(GPUMaterial *mat,
                                         bNode *node,
                                         bNodeExecData * /*execdata*/,
                                         GPUNodeStack *in,
                                         GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "generated_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_water_ripples", in, out);
}

}  // namespace nodes::node_shader_water_ripples_cc

/* node type definition */
void register_node_type_sh_water_ripples()
{
  namespace file_ns = nodes::node_shader_water_ripples_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeWaterRipples"_ustr, SH_NODE_WATER_RIPPLES);
  ntype.ui_name = "Water Ripples";
  ntype.ui_description = "Goo Engine Water Ripples: Procedural stylized anime water ripples and surface caustics";
  ntype.enum_name_legacy = "WATER_RIPPLES";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_water_ripples;

  bke::node_register_type(ntype);
}

}  // namespace blender
