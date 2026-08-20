/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_artist_line_modulation_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  // Normal Input
  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();

  // Surface Base Color (for Kyoto/Ufotable Auto Harmonic Tinting)
  b.add_input<decl::Color>("Base Color"_ustr)
      .default_value({0.95f, 0.80f, 0.75f, 1.0f})
      .description("Surface base color used for Kyoto Animation / Ufotable automatic harmonic line tinting");

  // Thickness Dynamics
  b.add_input<decl::Float>("Base Width"_ustr)
      .default_value(0.002f)
      .min(0.0f)
      .max(0.05f)
      .description("Base line thickness for Inverted Hull and linework (Anime standard: 0.0015 - 0.0025)");
  b.add_input<decl::Float>("Light Bleed"_ustr)
      .default_value(0.60f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("How strongly bright key light thins out and softens the outline (Light Attenuation)");
  b.add_input<decl::Float>("Curvature Accent"_ustr)
      .default_value(0.50f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR)
      .description("Increases stroke thickness at crevices, joints, and high-curvature creases (T-Junctions)");
  b.add_input<decl::Float>("View Taper"_ustr)
      .default_value(0.30f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Grazing angle stroke taper to maintain clean silhouette");
  b.add_input<decl::Float>("Hand Wobble"_ustr)
      .default_value(0.15f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Organic G-Pen hand-drawn micro-jitter along the stroke");

  // Color & Style Controls
  b.add_input<decl::Color>("Custom Outline Color"_ustr)
      .default_value({0.15f, 0.08f, 0.08f, 1.0f})
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
  b.add_input<decl::Float>("Line Break Threshold"_ustr)
      .default_value(0.0f)
      .min(0.0f)
      .max(1.0f)
      .subtype(PROP_FACTOR)
      .description("Artistic line-break threshold under intense overexposure highlights");

  b.add_input<decl::Vector>("Vector"_ustr).hide_value();
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  // Outputs
  b.add_output<decl::Color>("Line Color"_ustr).description("Synthesized harmonic artist line color");
  b.add_output<decl::Float>("Line Width"_ustr).description("Dynamic modulated line thickness factor");
  b.add_output<decl::Float>("Line Alpha"_ustr).description("Crease & stroke opacity mask");
  b.add_output<decl::Shader>("BSDF"_ustr).description("Direct Inverted Hull Emission BSDF");
}

static void node_shader_buts_artist_line_modulation(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "tint_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
}

static int node_shader_gpu_artist_line_modulation(GPUMaterial *mat,
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
  return GPU_stack_link(mat, node, "node_artist_line_modulation", in, out, GPU_constant(&tint_mode));
}

}  // namespace nodes::node_shader_artist_line_modulation_cc

/* node type definition */
void register_node_type_sh_artist_line_modulation()
{
  namespace file_ns = nodes::node_shader_artist_line_modulation_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeArtistLineModulation"_ustr, SH_NODE_ARTIST_LINE_MODULATION);
  ntype.ui_name = "Line Modulation";
  ntype.ui_description =
      "Dynamic Artist Linework Modulator: Light Bleed Attenuation, Crevice Accents, View Taper & Kyoto Harmonic Tinting";
  ntype.enum_name_legacy = "ARTIST_LINE_MODULATION";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_artist_line_modulation;
  ntype.default_width = bke::NodeWidth::_240;
  ntype.gpu_fn = file_ns::node_shader_gpu_artist_line_modulation;

  bke::node_register_type(ntype);
}

}  // namespace blender
