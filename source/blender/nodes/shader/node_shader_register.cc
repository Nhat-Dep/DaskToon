/* SPDX-FileCopyrightText: 2023 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "NOD_register.hh"

#include "node_shader_register.hh"

namespace blender {

void register_shader_nodes()
{
  register_node_tree_type_sh();

  register_node_type_sh_group();

  register_node_type_sh_add_shader();
  register_node_type_sh_ambient_occlusion();
  register_node_type_sh_attribute();
  register_node_type_sh_background();
  register_node_type_sh_bevel();
  register_node_type_sh_blackbody();
  register_node_type_sh_brightcontrast();
  register_node_type_sh_bsdf_diffuse();
  register_node_type_sh_bsdf_glass();
  register_node_type_sh_bsdf_glossy();
  register_node_type_sh_bsdf_hair_principled();
  register_node_type_sh_bsdf_hair();
  register_node_type_sh_bsdf_metallic();
  register_node_type_sh_bsdf_principled();
  register_node_type_sh_bsdf_ray_portal();
  register_node_type_sh_bsdf_refraction();
  register_node_type_sh_bsdf_toon();
  /* DaskToon Anime Suite: all-in-one effect nodes. Used by preset operators
   * (dasktoon_anime_nodes.py) with a Python node-group fallback if unavailable. */
  register_node_type_sh_anime_cel();
  register_node_type_sh_anime_rim();
  register_node_type_sh_anime_character();
  register_node_type_sh_anime_angel_ring();
  register_node_type_sh_anime_face_shadow();
  register_node_type_sh_anime_manga_screentone();
  register_node_type_sh_anime_warm_cool_grade();
  register_node_type_sh_anime_eye();
  /* Goo Engine Core / SDF / Procedural-Texture Suite: base-engine NPR toolkit
   * (curvature, SDF ops, screen-space info, procedural textures). Independent
   * of the DaskToon Anime feature layer above and below — do not remove as
   * part of anime-scope cleanup. */
  register_node_type_sh_shader_info();
  register_node_type_sh_screenspace_info();
  register_node_type_sh_set_depth();
  register_node_type_sh_curvature();
  register_node_type_sh_light_info();
  register_node_type_sh_oklab_color_ramp();
  register_node_type_sh_sdf_primitive();
  register_node_type_sh_sdf_op();
  register_node_type_sh_sdf_vector_op();
  register_node_type_sh_sdf_noise();
  register_node_type_sh_tex_hexagon();
  register_node_type_sh_twirl();
  register_node_type_sh_water_ripples();
  /* DaskToon Dask Modules: composable single-purpose building blocks.
   * Complementary to the Anime Suite above, not a replacement for it
   * (covers Outline/Ambient/Light/AO/Grade; not yet wired into presets). */
  register_node_type_sh_dask_cel();
  register_node_type_sh_dask_ambient();
  register_node_type_sh_dask_light();
  register_node_type_sh_dask_ao();
  register_node_type_sh_dask_grade();
  register_node_type_sh_dask_outline();
  register_node_type_sh_bsdf_translucent();
  register_node_type_sh_bsdf_transparent();
  register_node_type_sh_bsdf_sheen();
  register_node_type_sh_bump();
  register_node_type_sh_camera();
  register_node_type_sh_clamp();
  register_node_type_sh_combcolor();
  register_node_type_sh_combxyz();
  register_node_type_sh_curve_float();
  register_node_type_sh_curve_rgb();
  register_node_type_sh_curve_vec();
  register_node_type_sh_displacement();
  register_node_type_sh_eevee_specular();
  register_node_type_sh_emission();
  register_node_type_sh_fresnel();
  register_node_type_sh_gamma();
  register_node_type_sh_geometry();
  register_node_type_sh_hair_info();
  register_node_type_sh_holdout();
  register_node_type_sh_hue_sat();
  register_node_type_sh_invert();
  register_node_type_sh_layer_weight();
  register_node_type_sh_light_falloff();
  register_node_type_sh_light_path();
  register_node_type_sh_map_range();
  register_node_type_sh_mapping();
  register_node_type_sh_math();
  register_node_type_sh_mix_rgb();
  register_node_type_sh_mix_shader();
  register_node_type_sh_mix();
  register_node_type_sh_normal_map();
  register_node_type_sh_normal();
  register_node_type_sh_object_info();
  register_node_type_sh_output_aov();
  register_node_type_sh_output_light();
  register_node_type_sh_output_linestyle();
  register_node_type_sh_output_material();
  register_node_type_sh_output_world();
  register_node_type_sh_particle_info();
  register_node_type_sh_point_info();
  register_node_type_sh_radial_tiling();
  register_node_type_sh_raycast();
  register_node_type_sh_rgb();
  register_node_type_sh_rgbtobw();
  register_node_type_sh_script();
  register_node_type_sh_sepcolor();
  register_node_type_sh_sepxyz();
  register_node_type_sh_shadertorgb();
  register_node_type_sh_squeeze();
  register_node_type_sh_subsurface_scattering();
  register_node_type_sh_tangent();
  register_node_type_sh_tex_brick();
  register_node_type_sh_tex_checker();
  register_node_type_sh_tex_coord();
  register_node_type_sh_tex_environment();
  register_node_type_sh_tex_gabor();
  register_node_type_sh_tex_gradient();
  register_node_type_sh_tex_ies();
  register_node_type_sh_tex_image();
  register_node_type_sh_tex_magic();
  register_node_type_sh_tex_noise();
  register_node_type_sh_tex_sky();
  register_node_type_sh_tex_voronoi();
  register_node_type_sh_tex_wave();
  register_node_type_sh_tex_white_noise();
  register_node_type_sh_uvalongstroke();
  register_node_type_sh_uvmap();
  register_node_type_sh_valtorgb();
  register_node_type_sh_value();
  register_node_type_sh_vect_math();
  register_node_type_sh_vect_transform();
  register_node_type_sh_vector_displacement();
  register_node_type_sh_vector_rotate();
  register_node_type_sh_vertex_color();
  register_node_type_sh_volume_absorption();
  register_node_type_sh_volume_info();
  register_node_type_sh_volume_principled();
  register_node_type_sh_volume_scatter();
  register_node_type_sh_volume_coefficients();
  register_node_type_sh_wavelength();
  register_node_type_sh_wireframe();
}

}  // namespace blender
