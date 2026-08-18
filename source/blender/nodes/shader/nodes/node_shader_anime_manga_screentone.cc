/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_anime_manga_screentone_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Float>("Shading Factor"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Dot Scale"_ustr)
      .default_value(45.0f)
      .min(1.0f)
      .max(500.0f);
  b.add_input<decl::Float>("Dot Angle"_ustr)
      .default_value(0.785398f)
      .min(-3.14159f)
      .max(3.14159f)
      .subtype(PROP_ANGLE);
  b.add_input<decl::Float>("Dot Sharpness"_ustr)
      .default_value(0.05f)
      .min(0.001f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Color>("Ink Color"_ustr).default_value({0.05f, 0.05f, 0.08f, 1.0f});
  b.add_input<decl::Color>("Paper Color"_ustr).default_value({0.96f, 0.96f, 0.96f, 1.0f});
  b.add_input<decl::Vector>("Vector"_ustr).hide_value();

  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Fac"_ustr);
}

static int node_shader_gpu_anime_manga_screentone(GPUMaterial *mat,
                                                  bNode *node,
                                                  bNodeExecData * /*execdata*/,
                                                  GPUNodeStack *in,
                                                  GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_anime_manga_screentone", in, out);
}

}  // namespace nodes::node_shader_anime_manga_screentone_cc

/* node type definition */
void register_node_type_sh_anime_manga_screentone()
{
  namespace file_ns = nodes::node_shader_anime_manga_screentone_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeMangaScreentone"_ustr, SH_NODE_ANIME_MANGA_SCREENTONE);
  ntype.ui_name = "Manga Comic Screentone";
  ntype.ui_description = "Native DaskToon 2D Manga Screentone & Halftone Pattern (Screen-Space Dot Matrix, Angle & Sharpness)";
  ntype.enum_name_legacy = "ANIME_MANGA_SCREENTONE";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_manga_screentone;

  bke::node_register_type(ntype);
}

}  // namespace blender
