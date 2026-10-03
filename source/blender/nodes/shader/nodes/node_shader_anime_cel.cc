/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"
#include "node_shader_dasktoon_shading.hh"
#include "node_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_anime_cel_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.90f, 0.82f, 0.78f, 1.0f});
  b.add_input<decl::Color>("Shadow Color"_ustr)
      .default_value({0.60f, 0.50f, 0.55f, 1.0f});
  b.add_input<decl::Float>("Shadow Threshold"_ustr)
      .default_value(0.48f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description(
          "Light level where shadow begins. World lighting counts too: a bright World leaves "
          "fewer shadows");
  b.add_input<decl::Float>("Shadow Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);

  // WORLD / AMBIENT INFLUENCE Panel
  b.add_input<decl::Color>("Ambient Color"_ustr).default_value({0.80f, 0.85f, 0.95f, 1.0f});
  b.add_input<decl::Float>("Ambient Blend"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Bool>("Ambient Shadow Only"_ustr)
      .default_value(true)
      .description("When enabled, World Ambient only tints the shadow areas (Anime standard)");

  // SCENE LIGHT INFLUENCE Panel
  b.add_input<decl::Float>("Light Tint Strength"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR)
      .description("How strongly colored lights (Sun, Point, Spot) tint the surface (0=pure intensity, 1=full color tint)");

  // SPECULAR Panel
  b.add_input<decl::Color>("Specular Color"_ustr).default_value({1.0f, 1.0f, 1.0f, 1.0f});
  b.add_input<decl::Float>("Specular Size"_ustr)
      .default_value(0.08f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR);
  b.add_input<decl::Float>("Specular Softness"_ustr)
      .default_value(0.02f)
      .min(0.001f)
      .max(0.5f)
      .subtype(PROP_FACTOR);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr);
  b.add_output<decl::Color>("Color"_ustr);
}

static void node_shader_buts_anime_cel(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "ambient_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
  layout.prop(ptr, "light_blend_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
  dasktoon::draw_shading_buttons(layout, ptr);
}

static void node_update(bNodeTree *ntree, bNode *node)
{
  dasktoon::update_shading_sockets(*ntree, *node);
}

static void node_init(bNodeTree * /*ntree*/, bNode *node)
{
  node->custom1 = 2; /* Ambient Mode: HUE_SAT. */
  node->custom2 = 0; /* Light Mode: OVERLAY, Simple shading. */
  node->storage = dasktoon::shading_ramp_new();
}

static int node_shader_gpu_anime_cel(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  /* The previous code linked the world normal into in[10] (Specular Softness). */
  int normal_index = 0;
  int index = 0;
  for (const bNodeSocket *socket = static_cast<const bNodeSocket *>(node->inputs.first); socket;
       socket = socket->next, index++)
  {
    if (StringRef(socket->identifier) == "Normal") {
      normal_index = index;
    }
  }
  if (!in[normal_index].link) {
    GPU_link(mat, "world_normals_get", &in[normal_index].link);
  }

  GPU_material_flag_set(mat,
                        GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_GLOSSY | GPU_MATFLAG_EMISSION |
                            GPU_MATFLAG_SHADER_TO_RGBA);

  const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
  float modes[4] = {float(node->custom1),
                    float(dasktoon::light_blend_mode_get(*node)),
                    shading.ramp_mode,
                    shading.ramp_constant};
  return GPU_stack_link(mat,
                        node,
                        "node_anime_cel",
                        in,
                        out,
                        GPU_constant(modes),
                        shading.ramp_tex,
                        GPU_constant(&shading.ramp_layer));
}

}  // namespace nodes::node_shader_anime_cel_cc

/* node type definition */
void register_node_type_sh_anime_cel()
{
  namespace file_ns = nodes::node_shader_anime_cel_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeAnimeCel"_ustr, SH_NODE_ANIME_CEL);
  ntype.ui_name = "Classic Cel";
  ntype.ui_description =
      "Native DaskToon Multi-Tone Anime Cel-Shading Shader Node with World and Light Influence Options (All-in-one: includes specular & world/light tinting; no built-in outline.)";
  ntype.enum_name_legacy = "ANIME_CEL";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.gather_link_search_ops = search_link_ops_for_shader_bsdf_node;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_anime_cel;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_anime_cel;
  ntype.initfunc = file_ns::node_init;
  ntype.updatefunc = file_ns::node_update;
  bke::node_type_storage(
      ntype, "ColorBand", node_free_standard_storage, node_copy_standard_storage);

  bke::node_register_type(ntype);
}

}  // namespace blender
