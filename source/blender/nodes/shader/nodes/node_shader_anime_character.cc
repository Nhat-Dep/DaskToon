/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "RNA_access.hh"
#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_anime_character_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  const bNode *node = b.node_or_null();
  const int flags = node ? node->custom2 : 0;
  const bool use_ambient = (flags & (1 << 0)) != 0;
  const bool use_light = (flags & (1 << 1)) != 0;
  const bool use_ao = (flags & (1 << 2)) != 0;
  const bool use_rim = (flags & (1 << 3)) != 0;
  const bool use_outline = (flags & (1 << 4)) != 0;
  const bool use_grade = (flags & (1 << 5)) != 0;

  // Group 0: Geometry Normal
  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();

  // Group 1: Core Cel Shading (Always Visible)
  b.add_input<decl::Color>("Base Color"_ustr)
      .default_value({0.95f, 0.85f, 0.80f, 1.0f})
      .description("Anime surface unshadowed lit color");
  b.add_input<decl::Color>("Shadow Color"_ustr)
      .default_value({0.65f, 0.50f, 0.55f, 1.0f})
      .description("Anime surface 2nd-tone shadow color");
  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.48f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Boundary threshold between Lit and Shadow areas");
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR)
      .description("Softness/feathering of the shadow boundary line");

  // Group 2: Dynamic World Ambient (Visible when Use Ambient is enabled)
  b.add_input<decl::Color>("Ambient Color"_ustr)
      .default_value({0.80f, 0.85f, 0.95f, 1.0f})
      .available(use_ambient)
      .make_available([](bNode &node) { node.custom2 |= (1 << 0); })
      .description("Custom Ambient Tint Color");
  b.add_input<decl::Bool>("Use Custom Color"_ustr)
      .default_value(true)
      .available(use_ambient)
      .description("When enabled, uses custom Ambient Color. When disabled, extracts ambient lighting from World Scene environment");
  b.add_input<decl::Bool>("Ambient Shadow Only"_ustr)
      .default_value(true)
      .available(use_ambient)
      .description("When enabled, World Ambient only tints the shadow areas (Anime standard)");
  b.add_input<decl::Float>("Ambient Factor"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_ambient)
      .description("Blend factor for World Ambient lighting");

  // Group 3: Dynamic Scene Light (Visible when Use Light is enabled)
  b.add_input<decl::Float>("Light Tint Strength"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR)
      .available(use_light)
      .make_available([](bNode &node) { node.custom2 |= (1 << 1); })
      .description("How strongly colored lamps affect the lit surface");
  b.add_input<decl::Float>("Light Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_light)
      .description("Blend factor for Scene Lamps");

  // Group 4: Dynamic Ambient Occlusion (Visible when Use AO is enabled)
  b.add_input<decl::Color>("AO Color"_ustr)
      .default_value({0.0f, 0.0f, 0.0f, 1.0f})
      .available(use_ao)
      .make_available([](bNode &node) { node.custom2 |= (1 << 2); })
      .description("Color of the ambient occlusion crevice shadow (Default Black)");
  b.add_input<decl::Float>("AO Distance"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(100.0f)
      .available(use_ao)
      .description("Distance / radius of crevice occlusion search in world units");
  b.add_input<decl::Float>("AO Darkness"_ustr)
      .default_value(1.5f)
      .min(0.0f)
      .max(10.0f)
      .subtype(PROP_FACTOR)
      .available(use_ao)
      .description("Độ đậm của màu bóng kẽ AO (AO Color Darkness / Depth)");
  b.add_input<decl::Float>("AO Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_ao)
      .description("Blend factor for Ambient Occlusion crevice shadows");

  // Group 5: Dynamic VRM Parametric Rim Light (Visible when Use Rim is enabled)
  b.add_input<decl::Color>("Rim Color"_ustr)
      .default_value({1.0f, 1.0f, 1.0f, 1.0f})
      .available(use_rim)
      .make_available([](bNode &node) { node.custom2 |= (1 << 3); })
      .description("Color of the hair and body silhouette Rim Light");
  b.add_input<decl::Float>("Rim Fresnel Power"_ustr)
      .default_value(3.0f)
      .min(0.1f)
      .max(10.0f)
      .available(use_rim)
      .description("Falloff power of the anime Rim Light");
  b.add_input<decl::Float>("Rim Lift"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f)
      .available(use_rim)
      .description("Lift/offset of the Rim Light threshold");
  b.add_input<decl::Float>("Rim Lighting Mix"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_rim)
      .description("Blend between pure rim color and scene lighting");
  b.add_input<decl::Float>("Rim Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_rim)
      .description("Blend factor for Rim Light");

  // Group 6: Dynamic 3D Inverted Hull Outline (Visible when Use Outline is enabled)
  b.add_input<decl::Float>("Outline Width"_ustr)
      .default_value(0.0015f)
      .min(0.0f)
      .max(0.05f)
      .available(use_outline)
      .make_available([](bNode &node) { node.custom2 |= (1 << 4); })
      .description("Width / thickness of the Inverted Hull outline (Anime standard: 0.001 - 0.002)");
  b.add_input<decl::Color>("Outline Color"_ustr)
      .default_value({0.16f, 0.08f, 0.08f, 1.0f})
      .available(use_outline)
      .description("Color of the 2D Anime Inked Line Art outline");
  b.add_input<decl::Float>("Outline Lighting Mix"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_outline)
      .description("0.0 = Flat Unlit 2D Ink, 1.0 = Full blending with scene light and ambient");

  // Group 7: Dynamic Cinematic Color Grading (Visible when Use Grade is enabled)
  b.add_input<decl::Color>("Color Filter"_ustr)
      .default_value({1.0f, 1.0f, 1.0f, 1.0f})
      .available(use_grade)
      .make_available([](bNode &node) { node.custom2 |= (1 << 5); })
      .description("Global atmospheric cinematic color filter");
  b.add_input<decl::Color>("Shadow Tint"_ustr)
      .default_value({0.58f, 0.60f, 0.77f, 1.0f})
      .available(use_grade)
      .description("Color tint applied specifically to shadows (Split Toning)");
  b.add_input<decl::Color>("Highlight Tint"_ustr)
      .default_value({1.0f, 0.96f, 0.90f, 1.0f})
      .available(use_grade)
      .description("Color tint applied specifically to highlights (Split Toning)");
  b.add_input<decl::Float>("Saturation"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(3.0f)
      .subtype(PROP_FACTOR)
      .available(use_grade)
      .description("Anime color saturation / vibrancy boost");
  b.add_input<decl::Float>("Brightness"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f)
      .available(use_grade);
  b.add_input<decl::Float>("Contrast"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f)
      .available(use_grade);
  b.add_input<decl::Float>("Grade Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .available(use_grade)
      .description("Blend factor for Color Grading");

  // Master Controls (Always Visible)
  b.add_input<decl::Float>("Strength"_ustr).default_value(1.0f).min(0.0f).max(10.0f);
  b.add_input<decl::Float>("Alpha"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  // Master BSDF Output
  b.add_output<decl::Shader>("BSDF"_ustr).description("Master synthesized Anime Surface BSDF");
}

static void node_shader_buts_anime_character(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  ui::Layout &row1 = layout.row(true);
  row1.prop(ptr, "use_ambient", ui::ITEM_R_SPLIT_EMPTY_NAME, "Ambient", ICON_NONE);
  row1.prop(ptr, "use_light", ui::ITEM_R_SPLIT_EMPTY_NAME, "Light", ICON_NONE);
  row1.prop(ptr, "use_ao", ui::ITEM_R_SPLIT_EMPTY_NAME, "AO", ICON_NONE);

  ui::Layout &row2 = layout.row(true);
  row2.prop(ptr, "use_rim", ui::ITEM_R_SPLIT_EMPTY_NAME, "Rim", ICON_NONE);
  row2.prop(ptr, "use_outline", ui::ITEM_R_SPLIT_EMPTY_NAME, "Outline", ICON_NONE);
  row2.prop(ptr, "use_grade", ui::ITEM_R_SPLIT_EMPTY_NAME, "Grade", ICON_NONE);

  if (RNA_boolean_get(ptr, "use_ambient")) {
    layout.prop(ptr, "ambient_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Ambient Mode", ICON_NONE);
  }
}

static int node_shader_gpu_anime_character(GPUMaterial *mat,
                                           bNode *node,
                                           bNodeExecData * /*execdata*/,
                                           GPUNodeStack *in,
                                           GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }
  float modes[4];
  modes[0] = float(node->custom1); // ambient_mode
  modes[1] = 0.0f;                 // light_blend_mode
  modes[2] = float(node->custom2); // module flags
  modes[3] = 4.0f;                 // ao_samples

  GPU_material_flag_set(mat, GPU_MATFLAG_AO | GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  GPUNodeStack gpu_in[31];
  int idx = 0;
  for (int i = 0; i < 20; i++) {
    gpu_in[idx++] = in[i];
  }
  // Skip geometry outline inputs (indices 20, 21, 22)
  for (int i = 23; i < 33; i++) {
    gpu_in[idx++] = in[i];
  }

  return GPU_stack_link(mat,
                        node,
                        "node_anime_character",
                        gpu_in,
                        out,
                        GPU_constant(modes));
}

}  // namespace nodes::node_shader_anime_character_cc

/* node type definition */
void register_node_type_sh_anime_character()
{
  namespace file_ns = nodes::node_shader_anime_character_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeCharacter"_ustr, SH_NODE_ANIME_CHARACTER);
  ntype.ui_name = "Dask Shader BSDF";
  ntype.ui_description = "All-in-One Master Anime Shader with Dynamic Checkbox Module Visibility (Cel Shading, Ambient, Light, AO, Rim, Outline, Grade)";
  ntype.enum_name_legacy = "ANIME_CHARACTER";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_anime_character;
  ntype.default_width = bke::NodeWidth::_240;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_character;

  bke::node_register_type(ntype);
}

}  // namespace blender
