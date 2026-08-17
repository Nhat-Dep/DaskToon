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
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Inverted Hull Outline BSDF output (Unlit/Lit)");
  b.add_output<decl::Color>("Color"_ustr).description("Synthesized outline color output");
  b.add_output<decl::Float>("Width"_ustr).description("Active outline thickness factor");
}

static int node_shader_gpu_dask_outline(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                        GPUNodeStack *in,
                                        GPUNodeStack *out)
{
  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION);
  return GPU_stack_link(mat, node, "node_dask_outline", in, out);
}

}  // namespace nodes::node_shader_dask_outline_cc

/* node type definition */
void register_node_type_sh_dask_outline()
{
  namespace file_ns = nodes::node_shader_dask_outline_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskOutline"_ustr, SH_NODE_DASK_OUTLINE);
  ntype.ui_name = "Dask Outline Module";
  ntype.ui_description = "Automated Inverted Hull Anime 3D Outline Node (VRM / MToon Standard)";
  ntype.enum_name_legacy = "DASK_OUTLINE";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_outline;

  bke::node_register_type(ntype);
}

}  // namespace blender
