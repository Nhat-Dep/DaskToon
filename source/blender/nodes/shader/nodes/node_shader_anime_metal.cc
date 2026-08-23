/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_metal_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.85f, 0.88f, 0.92f, 1.0f});
  b.add_input<decl::Color>("Metal Tint"_ustr).default_value({0.95f, 0.85f, 0.50f, 0.0f})
      .description("Tint for Gold, Silver, Bronze or Dark Iron");
  b.add_input<decl::Color>("Specular Color"_ustr).default_value({1.0f, 1.0f, 1.0f, 1.0f});

  b.add_input<decl::Float>("Specular Sharpness"_ustr)
      .default_value(0.7f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Specular Intensity"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(5.0f);
  b.add_input<decl::Float>("Anisotropy Angle"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Rotation angle of anisotropic specular band");
  b.add_input<decl::Float>("Anisotropy Strength"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Float>("Rim Glint Power"_ustr)
      .default_value(4.0f)
      .min(0.1f)
      .max(20.0f);
  b.add_input<decl::Float>("Rim Glint Width"_ustr)
      .default_value(0.3f)
      .min(0.01f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Tangent"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Specular Mask"_ustr);
  b.add_output<decl::Float>("Glint Mask"_ustr);
}

static int node_shader_gpu_anime_metal(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                       GPUNodeStack *in,
                                       GPUNodeStack *out)
{
  if (!in[9].link) {
    GPU_link(mat, "world_normals_get", &in[9].link);
  }
  if (!in[10].link) {
    GPU_link(mat, "world_position_get", &in[10].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_metal", in, out);
}

}  // namespace nodes::node_shader_anime_metal_cc

/* node type definition */
void register_node_type_sh_anime_metal()
{
  namespace file_ns = nodes::node_shader_anime_metal_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeMetal"_ustr, SH_NODE_ANIME_METAL);
  ntype.ui_name = "Anime Metal";
  ntype.ui_description = "Native DaskToon High-Contrast Anime Metal, Steel & Armor NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_METAL";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_metal;

  bke::node_register_type(ntype);
}

}  // namespace blender
