/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_shader_util.hh"

namespace blender {

namespace nodes::node_shader_depth_info_cc {

static void node_declare(NodeDeclarationBuilder &b)
{
  // Inputs
  b.add_input<decl::Float>("Near Distance"_ustr)
      .default_value(0.1f)
      .min(0.0f)
      .max(10000.0f)
      .description("Start distance from camera in meters where normalized depth begins at 0.0");
  b.add_input<decl::Float>("Far Distance"_ustr)
      .default_value(25.0f)
      .min(0.01f)
      .max(10000.0f)
      .description("End distance from camera in meters where normalized depth reaches 1.0");
  b.add_input<decl::Float>("Curve Exponent"_ustr)
      .default_value(1.0f)
      .min(0.1f)
      .max(10.0f)
      .description("Falloff power exponent (1.0 = Linear, > 1.0 = Exponential curve)");

  // Outputs
  b.add_output<decl::Color>("Depth Map"_ustr)
      .description("Visual depth map formatted as grayscale RGBA (d, d, d, 1.0), ready to plug directly into shaders, emission, or AOVs");
  b.add_output<decl::Float>("Linear Depth"_ustr)
      .description("True perpendicular distance along camera view axis in meters (|Z_view|)");
  b.add_output<decl::Float>("Normalized Depth"_ustr)
      .description("Linear depth normalized within [Near Distance, Far Distance] clamped from 0.0 to 1.0");
  b.add_output<decl::Float>("Inverse Depth"_ustr)
      .description("Inverted depth range (1.0 - Normalized Depth) for near-bright / far-dark effects");
  b.add_output<decl::Float>("Radial Distance"_ustr)
      .description("True 3D Euclidean spherical distance from camera point to surface point (||P_view||)");
  b.add_output<decl::Float>("Screen Depth"_ustr)
      .description("Raw GPU Depth Buffer Z value (gl_FragCoord.z)");
  b.add_output<decl::Float>("Depth Fade"_ustr)
      .description("Smoothstep depth transition mask from Near Distance to Far Distance");
}

static int node_shader_gpu_depth_info(GPUMaterial *mat,
                                      bNode *node,
                                      bNodeExecData * /*execdata*/,
                                      GPUNodeStack *in,
                                      GPUNodeStack *out)
{
  return GPU_stack_link(mat, node, "node_depth_info", in, out);
}

}  // namespace nodes::node_shader_depth_info_cc

/* node type definition */
void register_node_type_sh_depth_info()
{
  namespace file_ns = nodes::node_shader_depth_info_cc;

  static bke::bNodeType ntype;

  sh_node_type_base(&ntype, "ShaderNodeDepthInfo"_ustr, SH_NODE_DEPTH_INFO);
  ntype.ui_name = "Depth Info";
  ntype.ui_description =
      "Depth Info node: Real-time Camera Linear Depth, Depth Map (Grayscale RGBA), Normalized Range, Radial Distance, Screen Buffer Z, and Depth Fade Mask for Anime/Toon effects";
  ntype.enum_name_legacy = "DEPTH_INFO";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.declare = file_ns::node_declare;
  ntype.add_ui_poll = object_dasktoon_anime_shader_nodes_poll;
  ntype.default_width = bke::NodeWidth::_180;
  ntype.gpu_fn = file_ns::node_shader_gpu_depth_info;

  bke::node_register_type(ntype);
}

}  // namespace blender
