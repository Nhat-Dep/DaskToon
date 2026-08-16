/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_tex_hexagon_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Vector"_ustr);
  b.add_input<decl::Float>("Scale"_ustr).default_value(5.0f).min(0.1f).max(100.0f);
  b.add_input<decl::Float>("Line Width"_ustr).default_value(0.05f).min(0.0f).max(0.5f);

  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Fac"_ustr);
}

static int node_shader_gpu_tex_hexagon(GPUMaterial *mat,
                                       bNode *node,
                                       bNodeExecData * /*execdata*/,
                                       GPUNodeStack *in,
                                       GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "generated_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_tex_hexagon", in, out);
}

}  // namespace nodes::node_shader_tex_hexagon_cc

/* node type definition */
void register_node_type_sh_tex_hexagon()
{
  namespace file_ns = nodes::node_shader_tex_hexagon_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeTexHexagon"_ustr, SH_NODE_TEX_HEXAGON);
  ntype.ui_name = "Hexagon Texture";
  ntype.ui_description = "Goo Engine Hexagon Texture: Procedural honeycomb/mecha armor pattern for anime tech assets";
  ntype.enum_name_legacy = "TEX_HEXAGON";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_tex_hexagon;

  bke::node_register_type(ntype);
}

}  // namespace blender
