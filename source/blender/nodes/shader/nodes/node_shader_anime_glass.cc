/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_glass_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Crystal Tint"_ustr).default_value({0.30f, 0.70f, 0.95f, 1.0f});
  b.add_input<decl::Color>("Internal Glow Color"_ustr).default_value({0.70f, 0.40f, 0.90f, 0.6f});
  b.add_input<decl::Color>("Sparkle Color"_ustr).default_value({1.0f, 1.0f, 1.0f, 1.0f});

  b.add_input<decl::Float>("Sparkle Scale"_ustr)
      .default_value(2.0f)
      .min(0.1f)
      .max(20.0f);
  b.add_input<decl::Float>("Sparkle Density"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Dispersion Power"_ustr)
      .default_value(0.8f)
      .min(0.0f)
      .max(2.0f);

  b.add_input<decl::Float>("Fresnel Power"_ustr)
      .default_value(3.0f)
      .min(0.1f)
      .max(10.0f);
  b.add_input<decl::Float>("Opacity"_ustr)
      .default_value(0.7f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Vector>("Position"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Sparkle Mask"_ustr);
}

static int node_shader_gpu_anime_glass(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                        GPUNodeStack *in,
                                        GPUNodeStack *out)
{
  if (!in[8].link) {
    GPU_link(mat, "world_normals_get", &in[8].link);
  }
  if (!in[9].link) {
    GPU_link(mat, "world_position_get", &in[9].link);
  }

  GPU_material_flag_set(
      mat,
      GPU_MATFLAG_TRANSPARENT | GPU_MATFLAG_TRANSPARENT_MAYBE_COLORED | GPU_MATFLAG_EMISSION |
          GPU_MATFLAG_SHADER_TO_RGBA);

  return GPU_stack_link(mat, node, "node_anime_glass", in, out);
}

}  // namespace nodes::node_shader_anime_glass_cc

/* node type definition */
void register_node_type_sh_anime_glass()
{
  namespace file_ns = nodes::node_shader_anime_glass_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeGlass"_ustr, SH_NODE_ANIME_GLASS);
  ntype.ui_name = "Anime Glass";
  ntype.ui_description = "Native DaskToon Multi-Layer Sparkle & Internal Glow Anime Glass, Crystal & Gem NPR Shader Node";
  ntype.enum_name_legacy = "ANIME_GLASS";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_160;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_glass;

  bke::node_register_type(ntype);
}

}  // namespace blender
