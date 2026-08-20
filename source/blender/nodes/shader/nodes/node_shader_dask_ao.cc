/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_dask_ao_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Vector>("Normal"_ustr).min(-1.0f).max(1.0f).hide_value();
  b.add_input<decl::Color>("AO Color"_ustr)
      .default_value({0.0f, 0.0f, 0.0f, 1.0f})
      .description("Color of the ambient occlusion crevice shadow (Default Black)");
  b.add_input<decl::Float>("Distance"_ustr)
      .default_value(0.5f)
      .min(0.0f)
      .max(100.0f)
      .description("Distance / radius of crevice occlusion search in world units");
  b.add_input<decl::Float>("Darkness"_ustr)
      .default_value(1.5f)
      .min(0.0f)
      .max(10.0f)
      .subtype(PROP_FACTOR)
      .description("Độ đậm của màu bóng kẽ AO (AO Color Darkness / Depth)");
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Standalone Ambient Occlusion BSDF preview output");
  b.add_output<decl::Color>("Color"_ustr).description("Real geometric AO shaded color multiplier");
  b.add_output<decl::Float>("AO"_ustr).description("Raw 0..1 Ambient Occlusion occlusion factor");
  b.add_output<decl::Float>("Distance"_ustr);
}

static int node_shader_gpu_dask_ao(GPUMaterial *mat,
                                   bNode *node,
                                   bNodeExecData * /*execdata*/,
                                   GPUNodeStack *in,
                                   GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }

  GPU_material_flag_set(mat, GPU_MATFLAG_AO | GPU_MATFLAG_EMISSION);

  float inverted = 0.0f;
  float f_samples = 4.0f;

  return GPU_stack_link(mat,
                        node,
                        "node_dask_ao",
                        in,
                        out,
                        GPU_constant(&inverted),
                        GPU_constant(&f_samples));
}

}  // namespace nodes::node_shader_dask_ao_cc

/* node type definition */
void register_node_type_sh_dask_ao()
{
  namespace file_ns = nodes::node_shader_dask_ao_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskAO"_ustr, SH_NODE_DASK_AO);
  ntype.ui_name = "Crevice AO";
  ntype.ui_description = "Standalone Hardware Horizon-Based Ambient Occlusion (HBAO) crevice and contact shadow node with Darkness control";
  ntype.enum_name_legacy = "DASK_AO";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_ao;

  bke::node_register_type(ntype);
}

}  // namespace blender
