// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon outline for Godot 4: the next pass of a DaskToon material, included by the anime_outline*.gdshader files
// (front faces culled, world space vertices). Pushes every vertex along DaskToon's smoothed outline normal (DT_OutlineN,
// octahedral, tangent space) by the width of project 1's Geometry Nodes hull and colours the line with the Dask Outline
// formula. outline_uv / outline_wuv < 0 means the mesh has no outline data: the vertex normal and a mask of 1 are used.
// Written by DaskToon Engine Export; edit the materials in DaskToon and export again.

#include "res://DaskToon/Shaders/dasktoon_core.gdshaderinc"

// Blender's normalize(0.5, 0.8, 0.6), the hull's fixed light, in Godot's axes.
const vec3 DT_HULL_LIGHT = vec3(0.4472136, 0.5366563, -0.7155418);

group_uniforms Outline;
uniform bool use_outline = true;
uniform float outline_width : hint_range(0.0, 0.05) = 0.002;
uniform vec4 outline_color : source_color = vec4(0.506, 0.313, 0.272, 1.0);
uniform sampler2D outline_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool outline_color_map_on = false;
uniform vec4 outline_base_color : source_color = vec4(0.991, 0.945, 0.916, 1.0);
uniform sampler2D outline_base_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool outline_base_color_map_on = false;
uniform float outline_light_bleed : hint_range(0.0, 1.0) = 0.7;
uniform float outline_wobble : hint_range(0.0, 1.0) = 0.15;
uniform int outline_tint_mode : hint_enum("Custom", "Harmonic", "Light Reactive") = 0;
uniform float outline_tint_darkness : hint_range(0.05, 1.0) = 0.35;
uniform float outline_tint_sat_boost : hint_range(0.5, 3.0) = 1.4;
uniform float outline_lighting_mix : hint_range(0.0, 1.0) = 0.1;
// Which UV map holds DT_OutlineN / DT_OutlineW: 0 UV, 1 UV2, 2 to 7 CUSTOM0 to CUSTOM2 (two per channel); -1 none.
uniform int outline_uv = -1;
uniform int outline_wuv = -1;
// Towards the DaskToon scene's Sun, in Godot's axes: the hull is thinner on the lit side.
uniform vec3 light_direction = vec3(0.4472136, 0.5366563, -0.7155418);

group_uniforms Master;
uniform float alpha : hint_range(0.0, 1.0) = 1.0;
uniform sampler2D alpha_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool alpha_map_on = false;
uniform float cutoff : hint_range(0.0, 1.0) = 0.5;

group_uniforms World;
uniform vec4 world_ambient : source_color = vec4(0.25, 0.25, 0.25, 1.0);
group_uniforms;

varying vec3 dt_inward;
varying vec3 dt_lit;

// Godot reads glTF's TEXCOORD_0 into UV, TEXCOORD_1 into UV2 and TEXCOORD_2 onwards two by two into CUSTOM0 to
// CUSTOM2. glTF stores V flipped (1 - v); the outline data wants Blender's v back.
vec2 dt_channel(int k, vec2 uv, vec2 uv2, vec4 c0, vec4 c1, vec4 c2) {
	vec2 v = uv;
	if (k == 1) {
		v = uv2;
	} else if (k == 2) {
		v = c0.xy;
	} else if (k == 3) {
		v = c0.zw;
	} else if (k == 4) {
		v = c1.xy;
	} else if (k == 5) {
		v = c1.zw;
	} else if (k == 6) {
		v = c2.xy;
	} else if (k == 7) {
		v = c2.zw;
	}
	return vec2(v.x, 1.0 - v.y);
}

void vertex() {
	vec3 n = normalize(NORMAL);
	vec3 direction = n;
	if (outline_uv >= 0) {
		vec3 nts = dt_oct_decode(dt_channel(outline_uv, UV, UV2, CUSTOM0, CUSTOM1, CUSTOM2));
		direction = normalize(TANGENT * nts.x + BINORMAL * nts.y + n * nts.z);
	}
	float mask = (outline_wuv >= 0) ? dt_channel(outline_wuv, UV, UV2, CUSTOM0, CUSTOM1, CUSTOM2).x : 1.0;
	float width = 0.0;
	if (use_outline) {
		width = dt_outline_width(outline_width, outline_light_bleed, outline_wobble,
				dot(direction, normalize(light_direction)), vec2(UV.x, 1.0 - UV.y), mask);
	}
	VERTEX += direction * width;
	// EEVEE draws a flipped hull: the line is shaded with the inward normal.
	dt_inward = -n;
}

void fragment() {
	vec2 uv = UV;
#if defined(DT_ALPHA_CLIP)
	ALPHA = clamp(dt_float_input(alpha, alpha_map, alpha_map_on, uv), 0.0, 1.0);
	ALPHA_SCISSOR_THRESHOLD = cutoff;
#endif
	vec3 inward = normalize(dt_inward);
	vec3 base = dt_color_input(outline_base_color, outline_base_color_map, outline_base_color_map_on, uv).rgb;
	vec3 line = dt_color_input(outline_color, outline_color_map, outline_color_map_on, uv).rgb;
	line = dt_outline_color(base, line, outline_light_bleed, outline_tint_darkness, outline_tint_sat_boost,
			outline_tint_mode, dot(inward, DT_HULL_LIGHT));
	// Dask Outline: mix(line, line x diffuse x PI, lighting mix), the diffuse being the world light and the lamps.
	float lit = clamp(outline_lighting_mix, 0.0, 1.0);
	ALBEDO = vec3(1.0);
	METALLIC = 0.0;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	EMISSION = line * (1.0 - lit) + line * lit * DT_PI * world_ambient.rgb;
	dt_lit = line * lit * DT_PI;
	NORMAL = normalize((VIEW_MATRIX * vec4(inward, 0.0)).xyz);
}

void light() {
	DIFFUSE_LIGHT += dt_lit * LIGHT_COLOR / DT_PI * max(dot(NORMAL, LIGHT), 0.0) * ATTENUATION;
}
