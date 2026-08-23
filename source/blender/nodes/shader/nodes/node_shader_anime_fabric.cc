/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_fabric_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.20f, 0.25f, 0.45f, 1.0f});
  b.add_input<decl::Color>("Shadow Color"_ustr).default_value({0.10f, 0.12f, 0.25f, 1.0f});
  b.add_input<decl::Color>("Sheen Color"_ustr).default_value({0.40f, 0.50f, 0.80f, 0.8f})
      .description("Velvet / Micro-fiber rim glow color");
  b.add_input<decl::Color>("Silk Shift Color"_ustr).default_value({0.60f, 0.30f, 0.50f, 1.0f})
      .description("Two-tone silk / satin color shift");

  b.add_input<decl::Float>("Sheen Power"_ustr)
      .default_value(3.0f)
      .min(0.1f)
      .max(10.0f);
  b.add_input<decl::Float>("Sheen Width"_ustr)
      .default_value(0.4f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Silk Blend"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Float>("Crease Darkness"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Weave Scale"_ustr)
      .default_value(1.0f)
      .min(0.01f)
      .max(50.0f);
  b.add_input<decl::Float>("Weave Strength"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Sheen Mask"_ustr);
}

static int node_shader_gpu_anime_fabric(GPUMaterial *mat,
                                         bNode *node,
                                         bNodeExecData * /*execdata*/,
                                         GPUNodeStack *in,
                                         GPUNodeStack *out)
{
  if (!in[10].link) {
    GPU_link(mat, "world_normals_get", &in[10].link);
  }
  if (!in[11].link) {
    GPU_link(mat, "world_position_get", &in[11].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_fabric", in, out);
}

}  // namespace nodes::node_shader_anime_fabric_cc

/* node type definition */
void register_node_type_sh_anime_fabric()
{
  namespace file_ns = nodes::node_shader_anime_fabric_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeFabric"_ustr, SH_NODE_ANIME_FABRIC);
  ntype.ui_name = "Anime Fabric";
  ntype.ui_description = "Native DaskToon Velvet Sheen & Silk Color-Shift Anime Fabric NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_FABRIC";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_fabric;

  bke::node_register_type(ntype);
}

}  // namespace blender
