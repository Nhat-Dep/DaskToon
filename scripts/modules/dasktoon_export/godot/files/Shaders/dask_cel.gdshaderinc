// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon Dask Cel for Godot 4, with its in-surface outline (use_outline); included by the dask_cel*.gdshader files,
// which choose the culling. Written by DaskToon Engine Export; edit the materials in DaskToon and export again.
//
// As in anime_bsdf.gdshaderinc: fragment() shades with the world light alone and emits that; light() shades with the
// world light and one lamp, and the brightest result wins.

#include "res://DaskToon/Shaders/dasktoon_core.gdshaderinc"

group_uniforms Surface;
uniform vec4 base_color : source_color = vec4(0.978, 0.931, 0.906, 1.0);
uniform sampler2D base_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool base_map_on = false;
uniform vec4 shadow_color : source_color = vec4(0.827, 0.735, 0.767, 1.0);
uniform sampler2D shadow_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_color_map_on = false;
uniform float shadow_threshold : hint_range(0.0, 1.0) = 0.48;
uniform sampler2D shadow_threshold_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_threshold_map_on = false;
uniform float shadow_softness : hint_range(0.001, 0.5) = 0.02;
uniform bool use_ramp = false;
uniform sampler2D ramp_map : source_color, hint_default_white, filter_linear, repeat_disable;
uniform bool ramp_constant = true;
uniform float strength : hint_range(0.0, 10.0) = 1.0;
uniform bool use_normal_map = false;
uniform sampler2D normal_map : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float normal_strength : hint_range(0.0, 10.0) = 1.0;

group_uniforms Outline;
uniform bool use_outline = false;
uniform float outline_width : hint_range(0.0, 0.05) = 0.0015;
uniform vec4 outline_color : source_color = vec4(0.437, 0.313, 0.313, 1.0);
uniform sampler2D outline_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool outline_color_map_on = false;
uniform int outline_tint_mode : hint_enum("Custom", "Harmonic", "Light Reactive") = 0;
uniform float outline_lighting_mix : hint_range(0.0, 1.0) = 0.0;

group_uniforms World;
// The DaskToon scene's World colour times its strength: the light that reaches every surface (Godot's ambient is off).
uniform vec4 world_ambient : source_color = vec4(0.25, 0.25, 0.25, 1.0);
group_uniforms;

varying vec3 dt_base;
varying vec3 dt_shadow;
varying float dt_threshold;
varying vec3 dt_line;
varying vec3 dt_world_only;

DTDaskCel dt_settings(vec3 base, vec3 shadow, float threshold, vec3 line) {
	DTDaskCel s;
	s.base_color = base;
	s.shadow_color = shadow;
	s.shadow_threshold = threshold;
	s.shadow_softness = shadow_softness;
	s.use_ramp = use_ramp;
	s.ramp_constant = ramp_constant;
	s.use_outline = use_outline;
	s.outline_width = outline_width;
	s.outline_color = line;
	s.outline_lighting_mix = outline_lighting_mix;
	s.outline_tint_mode = outline_tint_mode;
	s.strength = strength;
	return s;
}

void fragment() {
	vec2 uv = UV;
	dt_base = dt_color_input(base_color, base_map, base_map_on, uv).rgb;
	dt_shadow = dt_color_input(shadow_color, shadow_color_map, shadow_color_map_on, uv).rgb;
	dt_threshold = dt_float_input(shadow_threshold, shadow_threshold_map, shadow_threshold_map_on, uv);
	dt_line = dt_color_input(outline_color, outline_color_map, outline_color_map_on, uv).rgb;
	if (use_normal_map) {
		NORMAL_MAP = texture(normal_map, uv).rgb;
		NORMAL_MAP_DEPTH = normal_strength;
	}
	// The anime colour arrives through EMISSION and DIFFUSE_LIGHT; nothing else of Godot's lighting is added.
	ALBEDO = vec3(1.0);
	METALLIC = 0.0;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	DTDaskCel s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_line);
	dt_world_only = dt_dask_cel(s, world_ambient.rgb, dot(NORMAL, VIEW), ramp_map);
	EMISSION = dt_world_only;
}

void light() {
	DTDaskCel s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_line);
	vec3 lamp = LIGHT_COLOR / DT_PI * ATTENUATION;
	vec3 diffuse = world_ambient.rgb + lamp * max(dot(NORMAL, LIGHT), 0.0);
	vec3 shaded = dt_dask_cel(s, diffuse, dot(NORMAL, VIEW), ramp_map);
	if (dt_luminance(shaded) > dt_luminance(dt_world_only + DIFFUSE_LIGHT) + 0.00001) {
		DIFFUSE_LIGHT = shaded - dt_world_only;
	}
}
