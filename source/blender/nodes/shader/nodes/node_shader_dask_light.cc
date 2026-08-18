/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_dask_light_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Vector>("Normal"_ustr).hide_value();
  b.add_input<decl::Float>("Light Tint Strength"_ustr)
      .default_value(1.0f)
      .min(0.0f)
      .max(2.0f)
      .subtype(PROP_FACTOR)
      .description("How strongly colored lamps affect the lit surface");
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Standalone Scene Lighting BSDF output");
  b.add_output<decl::Color>("Color"_ustr).description("Extracted scene lamp radiance result");
  b.add_output<decl::Float>("Light Intensity"_ustr).description("Scalar luminance of scene lighting");
}

static void node_shader_buts_dask_light(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "light_blend_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
}

static int node_shader_gpu_dask_light(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  if (!in[0].link) {
    GPU_link(mat, "world_normals_get", &in[0].link);
  }
  float light_blend_mode = float(node->custom1);
  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);
  return GPU_stack_link(mat, node, "node_dask_light", in, out, GPU_constant(&light_blend_mode));
}

}  // namespace nodes::node_shader_dask_light_cc

/* node type definition */
void register_node_type_sh_dask_light()
{
  namespace file_ns = nodes::node_shader_dask_light_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskLight"_ustr, SH_NODE_DASK_LIGHT);
  ntype.ui_name = "Dask Light Module";
  ntype.ui_description = "Standalone Scene Light & 5 Forward Blend Modes BSDF node";
  ntype.enum_name_legacy = "DASK_LIGHT";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_dask_light;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_light;

  bke::node_register_type(ntype);
}

}  // namespace blender
