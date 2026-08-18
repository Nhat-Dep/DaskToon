/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_sdf_noise_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Vector"_ustr);
  b.add_input<decl::Float>("Scale"_ustr).default_value(5.0f).min(0.0f).max(100.0f);
  b.add_input<decl::Float>("Roughness"_ustr).default_value(0.5f).min(0.0f).max(1.0f);
  b.add_input<decl::Float>("Distortion"_ustr).default_value(0.0f).min(0.0f).max(10.0f);

  b.add_output<decl::Float>("Noise"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
}

static int node_shader_gpu_sdf_noise(GPUMaterial *mat,
                                     bNode *node,
                                     bNodeExecData * /*execdata*/,
                                     GPUNodeStack *in,
                                     GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "generated_get", &in[0].link);
  }

  return GPU_stack_link(mat, node, "node_sdf_noise", in, out);
}

}  // namespace nodes::node_shader_sdf_noise_cc

/* node type definition */
void register_node_type_sh_sdf_noise()
{
  namespace file_ns = nodes::node_shader_sdf_noise_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeSDFNoise"_ustr, SH_NODE_SDF_NOISE);
  ntype.ui_name = "SDF Noise";
  ntype.ui_description = "Goo Engine SDF Noise: Generates continuous noise patterns for anime organic shapes and procedural dissolution";
  ntype.enum_name_legacy = "SDF_NOISE";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_sdf_noise;

  bke::node_register_type(ntype);
}

}  // namespace blender
