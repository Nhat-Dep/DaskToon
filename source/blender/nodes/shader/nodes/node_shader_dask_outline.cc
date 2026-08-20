/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_dask_outline_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  // Normal Input
  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();

  // Surface Base Color (for Kyoto/Ufotable Auto Harmonic Tinting)
  b.add_input<decl::Color>("Base Color"_ustr)
      .default_value({0.95f, 0.85f, 0.80f, 1.0f})
      .description("Surface material base color used to automatically synthesize matching harmonic outline tint");

  // Thickness Dynamics
  b.add_input<decl::Float>("Outline Width"_ustr)
      .default_value(0.002f)
      .min(0.0f)
      .max(0.05f)
      .description("Width / thickness of the Inverted Hull outline (Anime standard: 0.0015 - 0.003)");
  b.add_input<decl::Float>("Light Bleed"_ustr)
      .default_value(0.70f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("How strongly key light thins out and softens the outline (Light Attenuation)");
  b.add_input<decl::Float>("Hand Wobble"_ustr)
      .default_value(0.15f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Organic G-Pen hand-drawn micro-jitter along the stroke");

  // Tint Controls
  b.add_input<decl::Color>("Outline Color"_ustr)
      .default_value({0.16f, 0.08f, 0.08f, 1.0f})
      .description("Fixed outline color when Tint Mode is Custom");
  b.add_input<decl::Float>("Tint Darkness"_ustr)
      .default_value(0.35f)
      .min(0.05f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Darkness multiplier for harmonic line tint relative to Base Color");
  b.add_input<decl::Float>("Tint Saturation Boost"_ustr)
      .default_value(1.40f)
      .min(0.5f)
      .max(3.0f)
      .description("Saturation multiplier to keep line colors rich and vivid");
  b.add_input<decl::Float>("Outline Lighting Mix"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("0.0 = Flat Unlit 2D Ink, 1.0 = Full blending with scene light and ambient");

  b.add_input<decl::Vector>("Vector"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  // Outputs
  b.add_output<decl::Shader>("BSDF"_ustr).description("Inverted Hull Outline BSDF output (Unlit/Lit)");
  b.add_output<decl::Color>("Color"_ustr).description("Synthesized harmonic outline color output");
  b.add_output<decl::Float>("Width"_ustr).description("Active modulated outline thickness factor");
  b.add_output<decl::Float>("Alpha"_ustr).description("Outline opacity mask");
}

static void node_shader_buts_dask_outline(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "tint_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
}

static int node_shader_gpu_dask_outline(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                        GPUNodeStack *in,
                                        GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);
  
  float tint_mode = float(node->custom1);
  return GPU_stack_link(mat, node, "node_dask_outline", in, out, GPU_constant(&tint_mode));
}

}  // namespace nodes::node_shader_dask_outline_cc

/* node type definition */
void register_node_type_sh_dask_outline()
{
  namespace file_ns = nodes::node_shader_dask_outline_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskOutline"_ustr, SH_NODE_DASK_OUTLINE);
  ntype.ui_name = "Outline Ink";
  ntype.ui_description =
      "Automated Inverted Hull Anime 3D Outline Node with Artist Light Bleed, Kyoto/Ufotable Harmonic Tinting & G-Pen Wobble";
  ntype.enum_name_legacy = "DASK_OUTLINE";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_dask_outline;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_outline;

  bke::node_register_type(ntype);
}

}  // namespace blender
