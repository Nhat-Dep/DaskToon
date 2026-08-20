/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_manga_hatching_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Float>("Shading Factor"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Darkness level determining hatching stroke density");
  b.add_input<decl::Float>("Density"_ustr)
      .default_value(30.0f)
      .min(1.0f)
      .max(500.0f)
      .description("Hatching line frequency / spacing");
  b.add_input<decl::Float>("Primary Angle"_ustr)
      .default_value(0.785398f)
      .min(-3.14159f)
      .max(3.14159f)
      .subtype(PROP_ANGLE)
      .description("Angle of 1st primary hatching strokes (Default 45 deg)");
  b.add_input<decl::Float>("Cross Angle"_ustr)
      .default_value(-0.785398f)
      .min(-3.14159f)
      .max(3.14159f)
      .subtype(PROP_ANGLE)
      .description("Angle of 2nd cross hatching strokes (Default -45 deg)");
  b.add_input<decl::Float>("Stroke Width"_ustr)
      .default_value(0.5f)
      .min(0.05f)
      .max(0.95f)
      .subtype(PROP_FACTOR)
      .description("Thickness ratio of ink lines vs paper gaps");
  b.add_input<decl::Float>("Hatch Levels"_ustr)
      .default_value(2.0f)
      .min(1.0f)
      .max(3.0f)
      .description("1: Single Hatch, 2: Cross Hatch, 3: Triple Dense Hatch");
  b.add_input<decl::Color>("Ink Color"_ustr).default_value({0.02f, 0.02f, 0.03f, 1.0f});
  b.add_input<decl::Color>("Paper Color"_ustr).default_value({0.98f, 0.98f, 0.98f, 1.0f});
  b.add_input<decl::Vector>("Vector"_ustr).hide_value();

  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Fac"_ustr);
}

static int node_shader_gpu_manga_hatching(GPUMaterial *mat,
                                          bNode *node,
                                          bNodeExecData * /*execdata*/,
                                          GPUNodeStack *in,
                                          GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_manga_hatching", in, out);
}

}  // namespace nodes::node_shader_manga_hatching_cc

/* node type definition */
void register_node_type_sh_manga_hatching()
{
  namespace file_ns = nodes::node_shader_manga_hatching_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeMangaHatching"_ustr, SH_NODE_MANGA_HATCHING);
  ntype.ui_name = "Cross-Hatching";
  ntype.ui_description = "Multi-level hand-drawn Manga pencil and ink cross-hatching shading node";
  ntype.enum_name_legacy = "MANGA_HATCHING";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_200;
  ntype.gpu_fn = file_ns::node_shader_gpu_manga_hatching;

  bke::node_register_type(ntype);
}

}  // namespace blender
