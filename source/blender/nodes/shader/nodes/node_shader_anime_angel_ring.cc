/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_angel_ring_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Highlight Color"_ustr).default_value({1.0f, 0.96f, 0.88f, 1.0f});
  b.add_input<decl::Float>("Band Position"_ustr)
      .default_value(0.50f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Band Width"_ustr)
      .default_value(0.08f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Band Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.2f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Strand Jitter"_ustr)
      .default_value(0.12f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Noise Scale"_ustr)
      .default_value(35.0f)
      .min(1.0f)
      .max(200.0f);
  b.add_input<decl::Float>("Intensity"_ustr)
      .default_value(1.5f)
      .min(0.0f)
      .max(10.0f);
  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Fac"_ustr);
}

static int node_shader_gpu_anime_angel_ring(GPUMaterial *mat,
                                             bNode *node,
                                             bNodeExecData * /*execdata*/,
                                             GPUNodeStack *in,
                                             GPUNodeStack *out)
{
  if (!in[7].link) {
    GPU_link(mat, "world_normals_get", &in[7].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_EMISSION);

  return GPU_stack_link(mat, node, "node_anime_angel_ring", in, out);
}

}  // namespace nodes::node_shader_anime_angel_ring_cc

/* node type definition */
void register_node_type_sh_anime_angel_ring()
{
  namespace file_ns = nodes::node_shader_anime_angel_ring_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeAngelRing"_ustr, SH_NODE_ANIME_ANGEL_RING);
  ntype.ui_name = "Angel Ring";
  ntype.ui_description = "Native DaskToon Hair Angel Ring / Halo Highlight (Anisotropic Normal Z, Noise Jitter & Emission Output)";
  ntype.enum_name_legacy = "ANIME_ANGEL_RING";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.gather_link_search_ops = search_link_ops_for_shader_bsdf_node;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_angel_ring;

  bke::node_register_type(ntype);
}

}  // namespace blender
