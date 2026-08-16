/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_shader_info_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Shader>("Shader"_ustr);
  b.add_input<decl::Int>("Light Group"_ustr).default_value(0).min(0).max(128);

  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Color>("Diffuse Light"_ustr);
  b.add_output<decl::Float>("Shadow"_ustr);
  b.add_output<decl::Color>("Ambient"_ustr);
  b.add_output<decl::Color>("Specular"_ustr);
}

static int node_shader_gpu_shader_info(GPUMaterial *mat,
                                       bNode *node,
                                       bNodeExecData * /*execdata*/,
                                       GPUNodeStack *in,
                                       GPUNodeStack *out)
{
  GPU_material_flag_set(mat, GPU_MATFLAG_SHADER_TO_RGBA | GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION);

  return GPU_stack_link(mat, node, "node_shader_info", in, out);
}

}  // namespace nodes::node_shader_shader_info_cc

/* node type definition */
void register_node_type_sh_shader_info()
{
  namespace file_ns = nodes::node_shader_shader_info_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeShaderInfo"_ustr, SH_NODE_SHADER_INFO);
  ntype.ui_name = "Shader Info";
  ntype.ui_description = "Goo Engine Shader Info node: Separates lighting into Diffuse Light, Shadow, Ambient, and Specular passes with Light Group filtering";
  ntype.enum_name_legacy = "SHADER_INFO";
  ntype.nclass = NODE_CLASS_CONVERTER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_shader_info;

  bke::node_register_type(ntype);
}

}  // namespace blender
