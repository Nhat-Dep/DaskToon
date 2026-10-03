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

namespace nodes::node_shader_dask_cel_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();
  b.add_input<decl::Color>("Base Color"_ustr).default_value({0.95f, 0.85f, 0.80f, 1.0f});
  b.add_input<decl::Color>("Shadow Color"_ustr)
      .default_value({0.65f, 0.50f, 0.55f, 1.0f});
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

  // Automated VRM Outline Controls
  b.add_input<decl::Bool>("Use Outline"_ustr)
      .default_value(false)
      .description("Enable / disable automated 3D Inverted Hull anime outline");
  b.add_input<decl::Float>("Outline Width"_ustr)
      .default_value(0.0015f)
      .min(0.0f)
      .max(0.05f)
      .description("Width / thickness of the Inverted Hull outline (Anime standard: 0.001 - 0.002)");
  b.add_input<decl::Color>("Outline Color"_ustr)
      .default_value({0.16f, 0.08f, 0.08f, 1.0f})
      .description("Color of the 2D Anime Inked Line Art outline");
  b.add_input<decl::Float>("Outline Lighting Mix"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("0.0 = Flat Unlit 2D Ink, 1.0 = Full blending with scene light and ambient");

  b.add_input<decl::Float>("Strength"_ustr).default_value(1.0f).min(0.0f).max(10.0f);
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Standalone Cel Shading BSDF output");
  b.add_output<decl::Color>("Color"_ustr).description("Final Cel Shaded Color (Base + Shadow blend)");
  b.add_output<decl::Float>("Shadow Factor"_ustr).description("0..1 factor of shadow vs lit area");
}

static void node_shader_buts_dask_cel(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  /* "Use Outline" is an input socket, not an RNA property, so the mode is always shown. */
  layout.prop(ptr, "outline_tint_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Outline Mode", ICON_NONE);
  dasktoon::draw_shading_buttons(layout, ptr);
}

static void node_update(bNodeTree *ntree, bNode *node)
{
  dasktoon::update_shading_sockets(*ntree, *node);
}

static void node_init(bNodeTree * /*ntree*/, bNode *node)
{
  node->storage = dasktoon::shading_ramp_new();
}

static int node_shader_gpu_dask_cel(GPUMaterial *mat,
                                    bNode *node,
                                    bNodeExecData * /*execdata*/,
                                    GPUNodeStack *in,
                                    GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }
  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);
  
  const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
  float modes[4] = {float(node->custom1), shading.ramp_mode, shading.ramp_constant, 0.0f};
  return GPU_stack_link(mat,
                        node,
                        "node_dask_cel",
                        in,
                        out,
                        GPU_constant(modes),
                        shading.ramp_tex,
                        GPU_constant(&shading.ramp_layer));
}

}  // namespace nodes::node_shader_dask_cel_cc

/* node type definition */
void register_node_type_sh_dask_cel()
{
  namespace file_ns = nodes::node_shader_dask_cel_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskCel"_ustr, SH_NODE_DASK_CEL);
  ntype.ui_name = "Cel Shading";
  ntype.ui_description =
      "Standalone Discrete 2-Tone Anime Cel Shading node with Harmonic Inverted Hull Outline controls";
  ntype.enum_name_legacy = "DASK_CEL";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_dask_cel;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_cel;
  ntype.initfunc = file_ns::node_init;
  ntype.updatefunc = file_ns::node_update;
  bke::node_type_storage(
      ntype, "ColorBand", node_free_standard_storage, node_copy_standard_storage);

  bke::node_register_type(ntype);
}

}  // namespace blender
