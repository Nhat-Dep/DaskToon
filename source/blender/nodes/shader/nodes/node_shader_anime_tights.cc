/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_tights_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Tights Color"_ustr).default_value({0.12f, 0.10f, 0.15f, 1.0f});
  b.add_input<decl::Color>("Skin Color"_ustr).default_value({0.95f, 0.80f, 0.75f, 1.0f});
  b.add_input<decl::Color>("Sheen Color"_ustr).default_value({0.70f, 0.75f, 0.90f, 0.5f});

  b.add_input<decl::Float>("Sheerness"_ustr)
      .default_value(0.6f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("How much skin shows through sheer black tights (0=thick opaque 120D, 1=sheer 20D)");
  b.add_input<decl::Float>("Denier Falloff"_ustr)
      .default_value(1.8f)
      .min(0.1f)
      .max(5.0f)
      .description("Fresnel falloff curve for sheer nylon density");

  b.add_input<decl::Float>("Fishnet Mode"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend between sheer tights (0) and diamond fishnet stockings (1)");
  b.add_input<decl::Float>("Fishnet Scale"_ustr)
      .default_value(8.0f)
      .min(0.5f)
      .max(50.0f);
  b.add_input<decl::Float>("Fishnet Thickness"_ustr)
      .default_value(0.15f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Fishnet Distortion"_ustr)
      .default_value(0.3f)
      .min(0.0f)
      .max(2.0f);

  b.add_input<decl::Float>("Sheen Power"_ustr)
      .default_value(3.5f)
      .min(0.1f)
      .max(10.0f);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Fishnet Mask"_ustr);
  b.add_output<decl::Float>("Skin Visibility"_ustr);
}

static int node_shader_gpu_anime_tights(GPUMaterial *mat,
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

  return GPU_stack_link(mat, node, "node_anime_tights", in, out);
}

}  // namespace nodes::node_shader_anime_tights_cc

/* node type definition */
void register_node_type_sh_anime_tights()
{
  namespace file_ns = nodes::node_shader_anime_tights_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeTights"_ustr, SH_NODE_ANIME_TIGHTS);
  ntype.ui_name = "Anime Tights & Fishnet";
  ntype.ui_description = "Native DaskToon Sheer Tights, Pantyhose & Diamond Fishnet Anime NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_TIGHTS";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_tights;

  bke::node_register_type(ntype);
}

}  // namespace blender
