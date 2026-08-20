/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

namespace blender {

namespace nodes::node_shader_dask_ambient_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  const bNodeTree *ntree = b.tree_or_null();
  const bool is_gpu_internal = ntree && (ntree->flag & NTREE_IS_GPU_SHADER_INTERNAL);

  b.add_input<decl::Color>("Ambient Color"_ustr).default_value({0.80f, 0.85f, 0.95f, 1.0f});
  b.add_input<decl::Bool>("Use Custom Color"_ustr)
      .default_value(true)
      .description("When enabled, uses custom Ambient Color. When disabled, extracts ambient lighting from World Scene environment");
  b.add_input<decl::Bool>("Ambient Shadow Only"_ustr)
      .default_value(true)
      .description("When enabled, World Ambient only tints the shadow areas (Anime standard)");
  b.add_input<decl::Float>("Weight"_ustr).default_value(1.0f).available(is_gpu_internal);

  b.add_output<decl::Shader>("BSDF"_ustr).description("Standalone World Ambient Shading BSDF output");
  b.add_output<decl::Color>("Color"_ustr).description("Blended ambient color result");
}

static void node_shader_buts_dask_ambient(ui::Layout &layout, bContext * /*C*/, PointerRNA *ptr)
{
  layout.prop(ptr, "ambient_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "", ICON_NONE);
}

static int node_shader_gpu_dask_ambient(GPUMaterial *mat,
                                        bNode *node,
                                        bNodeExecData * /*execdata*/,
                                        GPUNodeStack *in,
                                        GPUNodeStack *out)
{
  float ambient_mode = float(node->custom1);
  GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);
  return GPU_stack_link(mat, node, "node_dask_ambient", in, out, GPU_constant(&ambient_mode));
}

}  // namespace nodes::node_shader_dask_ambient_cc

/* node type definition */
void register_node_type_sh_dask_ambient()
{
  namespace file_ns = nodes::node_shader_dask_ambient_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDaskAmbient"_ustr, SH_NODE_DASK_AMBIENT);
  ntype.ui_name = "World Ambient";
  ntype.ui_description = "Standalone World Ambient & 7 Shading Modes BSDF node";
  ntype.enum_name_legacy = "DASK_AMBIENT";
  ntype.nclass = NODE_CLASS_SHADER;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.draw_buttons = file_ns::node_shader_buts_dask_ambient;
  ntype.default_width = bke::NodeWidth::_220;
  ntype.gpu_fn = file_ns::node_shader_gpu_dask_ambient;

  bke::node_register_type(ntype);
}

}  // namespace blender
