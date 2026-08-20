/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_face_shadow_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Head Forward"_ustr).default_value({0.0f, 1.0f, 0.0f});
  b.add_input<decl::Vector>("Head Right"_ustr).default_value({1.0f, 0.0f, 0.0f});
  b.add_input<decl::Vector>("Light Vector"_ustr).default_value({0.57735f, 0.57735f, 0.57735f});
  b.add_input<decl::Float>("Face Map"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .description("Optional Face Shadow SDF Texture / Map (Genshin/Honkai style)");
  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.03f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Smoothing"_ustr)
      .default_value(0.70f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Procedural Face Normal Smoothing Amount (eliminates nose/eye bumps)");
  b.add_input<decl::Vector>("Normal"_ustr).hide_value();

  b.add_output<decl::Float>("Shadow Mask"_ustr);
  b.add_output<decl::Float>("Light Angle"_ustr);
  b.add_output<decl::Float>("Side Factor"_ustr);
  b.add_output<decl::Vector>("Smooth Normal"_ustr);
}

static int node_shader_gpu_anime_face_shadow(GPUMaterial *mat,
                                              bNode *node,
                                              bNodeExecData * /*execdata*/,
                                              GPUNodeStack *in,
                                              GPUNodeStack *out)
{
  if (!in[7].link) {
    GPU_link(mat, "world_normals_get", &in[7].link);
  }

  return GPU_stack_link(mat, node, "node_anime_face_shadow", in, out);
}

}  // namespace nodes::node_shader_anime_face_shadow_cc

/* node type definition */
void register_node_type_sh_anime_face_shadow()
{
  namespace file_ns = nodes::node_shader_anime_face_shadow_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeFaceShadow"_ustr, SH_NODE_ANIME_FACE_SHADOW);
  ntype.ui_name = "Face Shadow";
  ntype.ui_description = "Native DaskToon Anime Facial Shadow Smoothing & Direction Controller (SDF Map / Head Vector Normal Smoothing)";
  ntype.enum_name_legacy = "ANIME_FACE_SHADOW";
  ntype.nclass = NODE_CLASS_CONVERTER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_face_shadow;

  bke::node_register_type(ntype);
}

}  // namespace blender
