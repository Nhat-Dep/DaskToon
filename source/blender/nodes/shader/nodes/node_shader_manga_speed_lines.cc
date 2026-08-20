/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_manga_speed_lines_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Float>("Center X"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .description("Center point X of the speed line focus");
  b.add_input<decl::Float>("Center Y"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .description("Center point Y of the speed line focus");
  b.add_input<decl::Float>("Ray Density"_ustr)
      .default_value(60.0f)
      .min(4.0f)
      .max(300.0f)
      .description("Number of speed line rays around 360 degrees");
  b.add_input<decl::Float>("Inner Radius"_ustr)
      .default_value(0.25f)
      .min(0.0f)
      .max(1.0f)
      .description("Clear focal region radius inside the center");
  b.add_input<decl::Float>("Line Sharpness"_ustr)
      .default_value(0.80f)
      .min(0.01f)
      .max(1.0f)
      .description("Contrast / taper sharpness of the speed rays");
  b.add_input<decl::Float>("Jitter"_ustr)
      .default_value(0.50f)
      .min(0.0f)
      .max(1.0f)
      .description("Randomness in line length and thickness");
  b.add_input<decl::Color>("Ink Color"_ustr).default_value({0.02f, 0.02f, 0.03f, 1.0f});
  b.add_input<decl::Color>("Background Color"_ustr).default_value({0.98f, 0.98f, 0.98f, 0.0f});
  b.add_input<decl::Vector>("Vector"_ustr).hide_value();

  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Alpha"_ustr);
}

static int node_shader_gpu_manga_speed_lines(GPUMaterial *mat,
                                             bNode *node,
                                             bNodeExecData * /*execdata*/,
                                             GPUNodeStack *in,
                                             GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_manga_speed_lines", in, out);
}

}  // namespace nodes::node_shader_manga_speed_lines_cc

/* node type definition */
void register_node_type_sh_manga_speed_lines()
{
  namespace file_ns = nodes::node_shader_manga_speed_lines_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeMangaSpeedLines"_ustr, SH_NODE_MANGA_SPEED_LINES);
  ntype.ui_name = "Speed Lines";
  ntype.ui_description = "Dynamic 2D Manga Action & Impact Speed Lines Generator";
  ntype.enum_name_legacy = "MANGA_SPEED_LINES";
  ntype.nclass = NODE_CLASS_TEXTURE;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_200;
  ntype.gpu_fn = file_ns::node_shader_gpu_manga_speed_lines;

  bke::node_register_type(ntype);
}

}  // namespace blender
