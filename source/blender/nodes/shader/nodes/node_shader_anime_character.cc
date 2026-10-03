/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"
#include "node_shader_dasktoon_shading.hh"
#include "node_util.hh"

#include "RNA_access.hh"
#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_anime_character_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);


  // Group 1: Core Discrete 2-Tone Cel Shading (Always Visible)
  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();
  b.add_input<decl::Color>("Base Color"_ustr)
      .default_value({0.98f, 0.88f, 0.82f, 1.0f})
      .description("Base surface anime albedo color (Lit area)");
  b.add_input<decl::Color>("Shadow Color"_ustr)
      .default_value({0.88f, 0.65f, 0.66f, 1.0f})
      .description("Shadow tone color (Unlit area - Warm Kyoto Anime blush shadow)");
  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.46f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description(
          "Light level where shadow begins. World lighting counts too: a bright World leaves "
          "fewer shadows");
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.035f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR)
      .description("Softness/feathering of the shadow boundary line (0.035 = Anti-aliased 2D Anime line)");

  // Group 2: Dynamic World Ambient (Visible when Use Ambient is enabled)
  b.add_input<decl::Color>("Ambient Color"_ustr)
      .default_value({0.85f, 0.90f, 1.0f, 1.0f})
      .make_available([](bNode &node) { node.custom2 |= (1 << 0); })
      .description("Custom Ambient Tint Color (Sky blue fill)");
  b.add_input<decl::Bool>("Use Custom Color"_ustr)
      .default_value(true)
      .description("When enabled, uses custom Ambient Color. When disabled, extracts ambient lighting from World Scene environment");
  b.add_input<decl::Bool>("Ambient Shadow Only"_ustr)
      .default_value(true)
      .description("When enabled, World Ambient only tints the shadow areas (Anime standard)");
  b.add_input<decl::Float>("Ambient Factor"_ustr)
      .default_value(0.30f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend factor for World Ambient lighting");

  // Group 3: Dynamic Scene Light (Visible when Use Light is enabled)
  b.add_input<decl::Float>("Light Tint Strength"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR)
      .make_available([](bNode &node) { node.custom2 |= (1 << 1); })
      .description("How strongly colored lamps affect the lit surface");
  b.add_input<decl::Float>("Light Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend factor for Scene Lamps");

  // Group 4: Dynamic Ambient Occlusion (Visible when Use AO is enabled)
  b.add_input<decl::Color>("AO Color"_ustr)
      .default_value({0.0f, 0.0f, 0.0f, 1.0f})
      .make_available([](bNode &node) { node.custom2 |= (1 << 2); })
      .description("Color of the ambient occlusion crevice shadow (Default Black)");
  b.add_input<decl::Float>("AO Distance"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(100.0f)
      .description("Distance / radius of crevice occlusion search in world units");
  b.add_input<decl::Float>("AO Darkness"_ustr)
      .default_value(1.5f)
      .min(0.0f)
      .max(10.0f)
      .subtype(PROP_FACTOR)
      .description("Độ đậm của màu bóng kẽ AO (AO Color Darkness / Depth)");
  b.add_input<decl::Float>("AO Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend factor for Ambient Occlusion crevice shadows");
  b.add_input<decl::Float>("AO Mask"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .make_available([](bNode &node) { node.custom2 |= (1 << 2); })
      .description("Texture / Vertex Color mask to control exactly where AO shadows can appear (0.0 = Clean skin, 1.0 = Crevices)");

  // Group 5: Dynamic VRM Parametric Rim Light (Visible when Use Rim is enabled)
  b.add_input<decl::Color>("Rim Color"_ustr)
      .default_value({1.0f, 0.98f, 0.90f, 1.0f})
      .make_available([](bNode &node) { node.custom2 |= (1 << 3); })
      .description("Color of the hair and body silhouette Rim Light");
  b.add_input<decl::Float>("Rim Fresnel Power"_ustr)
      .default_value(4.0f)
      .min(0.1f)
      .max(10.0f)
      .description("Falloff power of the anime Rim Light (4.0 = tight silhouette on hair/shoulders)");
  b.add_input<decl::Float>("Rim Lift"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f)
      .description("Lift/offset of the Rim Light threshold");
  b.add_input<decl::Float>("Rim Lighting Mix"_ustr)
      .default_value(0.6f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend between pure rim color and scene lighting");
  b.add_input<decl::Float>("Rim Factor"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Blend factor for Rim Light");

  // Group 6: Dynamic 3D Inverted Hull Outline (Visible when Use Outline is enabled)
  b.add_input<decl::Float>("Outline Width"_ustr)
      .default_value(0.002f)
      .min(0.0f)
      .max(0.05f)
      .make_available([](bNode &node) { node.custom2 |= (1 << 4); })
      .description("Width / thickness of the Inverted Hull outline (Anime standard: 0.0015 - 0.003)");
  b.add_input<decl::Color>("Outline Color"_ustr)
      .default_value({0.22f, 0.08f, 0.06f, 1.0f})
      .description("Color of the 2D Anime Inked Line Art outline (Dark chestnut / sepia)");
  b.add_input<decl::Float>("Outline Lighting Mix"_ustr)
      .default_value(0.10f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("0.0 = Flat Unlit 2D Ink, 1.0 = Full blending with scene light and ambient");

  // Group 7: Dynamic Cinematic Color Grading (Visible when Use Grade is enabled)
  b.add_input<decl::Color>("Color Filter"_ustr)
      .default_value({1.0f, 1.0f, 1.0f, 1.0f})
      .make_available([](bNode &node) { node.custom2 |= (1 << 5); })
      .description("Global atmospheric cinematic color filter");
  b.add_input<decl::Color>("Shadow Tint"_ustr)
      .default_value({0.58f, 0.60f, 0.77f, 1.0f})
      .description("Color tint applied specifically to shadows (Split Toning)");
  b.add_input<decl::Color>("Highlight Tint"_ustr)
      .default_value({1.0f, 0.96f, 0.90f, 1.0f})
      .description("Color tint applied specifically to highlights (Split Toning)");
  b.add_input<decl::Float>("Saturation"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(3.0f)
      .subtype(PROP_FACTOR)
      .description("Anime color saturation / vibrancy boost");
  b.add_input<decl::Float>("Brightness"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f);
  b.add_input<decl::Float>("Contrast"_ustr)
      .default_value(0.0f)
      .min(-1.0f)
      .max(1.0f);
  b.add_input<decl::Float>("Grade Factor"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
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

  if (RNA_boolean_get(ptr, "use_light")) {
    layout.prop(ptr, "light_blend_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Light Mode", ICON_NONE);
  }
  if (RNA_boolean_get(ptr, "use_ambient")) {
    layout.prop(ptr, "ambient_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Ambient Mode", ICON_NONE);
  }
  if (RNA_boolean_get(ptr, "use_outline")) {
    layout.prop(ptr, "outline_tint_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Outline Mode", ICON_NONE);
  }
  dasktoon::draw_shading_buttons(layout, ptr);
}

static void node_init(bNodeTree * /*ntree*/, bNode *node)
{
  node->storage = dasktoon::shading_ramp_new();
}

/* Module checkboxes (custom2 bits) and the shading mode decide which inputs are shown. */
static void node_update(bNodeTree *ntree, bNode *node)
{
  dasktoon::update_shading_sockets(*ntree, *node);
  struct ModuleSockets {
    int bit;
    const char *names[7];
  };
  static const ModuleSockets modules[] = {
      {0, {"Ambient Color", "Use Custom Color", "Ambient Shadow Only", "Ambient Factor"}},
      {1, {"Light Tint Strength", "Light Factor"}},
      {2, {"AO Color", "AO Distance", "AO Darkness", "AO Factor", "AO Mask"}},
      {3, {"Rim Color", "Rim Fresnel Power", "Rim Lift", "Rim Lighting Mix", "Rim Factor"}},
      {4, {"Outline Width", "Outline Color", "Outline Lighting Mix"}},
      {5,
       {"Color Filter",
        "Shadow Tint",
        "Highlight Tint",
        "Saturation",
        "Brightness",
        "Contrast",
        "Grade Factor"}},
  };
  for (bNodeSocket &sock : node->inputs) {
    for (const ModuleSockets &module : modules) {
      for (const char *name : module.names) {
        if (name != nullptr && STREQ(sock.name, name)) {
          bke::node_set_socket_availability(
              *ntree, sock, (node->custom2 & (1 << module.bit)) != 0);
        }
      }
    }
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
  modes[0] = float(node->custom1 & 0x0F);        // ambient_mode
  modes[1] = float((node->custom1 >> 4) & 0x0F); // outline_tint_mode (Custom / Auto Harmonic Kyoto / Light Reactive)
  modes[2] = float(node->custom2);               // module flags
  modes[3] = 4.0f;                               // ao_samples

  GPU_material_flag_set(mat, GPU_MATFLAG_AO | GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);

  const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
  float modes2[4] = {float(dasktoon::light_blend_mode_get(*node)),
                     shading.ramp_mode,
                     shading.ramp_constant,
                     0.0f};
  return GPU_stack_link(mat,
                        node,
                        "node_anime_character",
                        in,
                        out,
                        GPU_constant(modes),
                        shading.ramp_tex,
                        GPU_constant(&shading.ramp_layer),
                        GPU_constant(modes2));
}

}  // namespace nodes::node_shader_anime_character_cc

/* node type definition */
void register_node_type_sh_anime_character()
{
  namespace file_ns = nodes::node_shader_anime_character_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeCharacter"_ustr, SH_NODE_ANIME_CHARACTER);
  ntype.ui_name = "Anime BSDF";
  ntype.ui_description = "All-in-One Master Anime Shader with Dynamic Checkbox Module Visibility (Cel Shading, Ambient, Light, AO, Rim, Outline, Grade)";
  ntype.enum_name_legacy = "ANIME_CHARACTER";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_anime_character;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_character;
  ntype.initfunc = file_ns::node_init;
  ntype.updatefunc = file_ns::node_update;
  bke::node_type_storage(
      ntype, "ColorBand", node_free_standard_storage, node_copy_standard_storage);

  bke::node_register_type(ntype);
}

}  // namespace blender
