/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_manga_character_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();

  // Core Manga Colors
  b.add_input<decl::Color>("Paper / Base Color"_ustr)
      .default_value({0.98f, 0.98f, 0.98f, 1.0f})
      .description("Paper or light tone base surface color");
  b.add_input<decl::Color>("Ink Color"_ustr)
      .default_value({0.02f, 0.02f, 0.03f, 1.0f})
      .description("Deep black comic ink color");
  b.add_input<decl::Color>("1st Tone Color"_ustr)
      .default_value({0.75f, 0.75f, 0.78f, 1.0f})
      .description("First level midtone shade");
  b.add_input<decl::Color>("2nd Tone Color"_ustr)
      .default_value({0.40f, 0.40f, 0.45f, 1.0f})
      .description("Second level dark shadow tone");

  // Shading Thresholds
  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.50f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Light/Shadow cel boundary split");
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR)
      .description("Feathering softness of the shadow line");

  // Manga Pattern & Style Controls
  b.add_input<decl::Float>("Tone Scale"_ustr)
      .default_value(45.0f)
      .min(1.0f)
      .max(500.0f)
      .description("Screentone matrix density / dot frequency");
  b.add_input<decl::Float>("Tone Angle"_ustr)
      .default_value(0.785398f)
      .min(-3.14159f)
      .max(3.14159f)
      .subtype(PROP_ANGLE)
      .description("Screentone rotation angle (Default 45 degrees)");
  b.add_input<decl::Float>("Tone Sharpness"_ustr)
      .default_value(0.10f)
      .min(0.001f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Contrast / sharpness of screentone dots");
  b.add_input<decl::Float>("Screen Space Lock"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .description("1.0: Lock to 2D Screen (Comic Page), 0.0: Follow 3D UV");
  b.add_input<decl::Float>("Rim Light Strength"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(2.0f)
      .description("Stylized anime rim highlight on manga contours");
  b.add_input<decl::Vector>("Vector"_ustr).hide_value();

  // Outputs
  b.add_output<decl::Color>("Color"_ustr);
  b.add_output<decl::Float>("Tone Fac"_ustr);
  b.add_output<decl::Float>("Shadow Fac"_ustr);
}

static void node_shader_buts_manga_character(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "manga_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
  layout.prop(ptr, "pattern_type", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
}

static int node_shader_gpu_manga_character(GPUMaterial *mat,
                                           bNode *node,
                                           bNodeExecData * /*execdata*/,
                                           GPUNodeStack *in,
                                           GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  float manga_mode = float(node->custom1);
  float pattern_type = float(node->custom2);

  return GPU_stack_link(mat,
                        node,
                        "node_manga_character",
                        in,
                        out,
                        GPU_constant(&manga_mode),
                        GPU_constant(&pattern_type));
}

}  // namespace nodes::node_shader_manga_character_cc

/* node type definition */
void register_node_type_sh_manga_character()
{
  namespace file_ns = nodes::node_shader_manga_character_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeMangaCharacter"_ustr, SH_NODE_MANGA_CHARACTER);
  ntype.ui_name = "Manga BSDF";
  ntype.ui_description =
      "All-in-one Japanese Manga & Webtoon Shading Node (B&W Comic, Halftone Screentones, Cross-Hatching & Color Webtoon)";
  ntype.enum_name_legacy = "MANGA_CHARACTER";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.draw_buttons = file_ns::node_shader_buts_manga_character;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_240;
  ntype.gpu_fn = file_ns::node_shader_gpu_manga_character;

  bke::node_register_type(ntype);
}

}  // namespace blender
