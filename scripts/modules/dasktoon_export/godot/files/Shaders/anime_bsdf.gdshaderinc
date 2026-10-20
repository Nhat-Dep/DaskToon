// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon Anime BSDF for Godot 4, included by the anime_bsdf*.gdshader files, which choose the culling and the alpha
// (DT_ALPHA_CLIP, DT_ALPHA_BLEND). Written by DaskToon Engine Export; edit the materials in DaskToon and export again.
//
// Godot lights a surface one lamp at a time in light(), while DaskToon shades the sum of all the light reaching it.
// fragment() shades the surface with the world light alone and emits that; light() shades it with the world light and
// one lamp, and the brightest result wins. With one lamp this is DaskToon's shading. The world light is World Ambient,
// written from the DaskToon scene's World: Godot's own ambient light is off.

#include "res://DaskToon/Shaders/dasktoon_core.gdshaderinc"

group_uniforms Surface;
uniform vec4 base_color : source_color = vec4(0.991, 0.945, 0.916, 1.0);
uniform sampler2D base_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool base_map_on = false;
uniform vec4 shadow_color : source_color = vec4(0.945, 0.827, 0.832, 1.0);
uniform sampler2D shadow_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_color_map_on = false;
uniform float shadow_threshold : hint_range(0.0, 1.0) = 0.46;
uniform sampler2D shadow_threshold_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_threshold_map_on = false;
uniform float shadow_softness : hint_range(0.001, 0.5) = 0.035;
uniform bool use_ramp = false;
uniform sampler2D ramp_map : source_color, hint_default_white, filter_linear, repeat_disable;
uniform bool ramp_constant = true;

group_uniforms Ambient;
uniform bool use_ambient = false;
uniform int ambient_mode : hint_enum("Overlay", "Hue", "Hue Saturation", "Saturation", "Value", "Multiply", "Mix") = 0;
uniform vec4 ambient_color : source_color = vec4(0.931, 0.955, 1.0, 1.0);
uniform sampler2D ambient_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool ambient_color_map_on = false;
uniform bool ambient_use_custom = true;
uniform bool ambient_shadow_only = true;
uniform float ambient_factor : hint_range(0.0, 1.0) = 0.3;

group_uniforms Light;
uniform bool use_light = false;
uniform int light_mode : hint_enum("Overlay", "Hue", "Multiply", "Add", "Pure Cel") = 0;
uniform float light_tint_strength : hint_range(0.0, 2.0) = 1.0;
uniform float light_factor : hint_range(0.0, 1.0) = 1.0;

group_uniforms AO;
uniform bool use_ao = false;
uniform vec4 ao_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform sampler2D ao_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool ao_color_map_on = false;
uniform float ao_darkness : hint_range(0.0, 10.0) = 1.5;
uniform float ao_factor : hint_range(0.0, 1.0) = 1.0;
uniform float ao_mask : hint_range(0.0, 1.0) = 1.0;
uniform sampler2D ao_mask_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool ao_mask_map_on = false;

group_uniforms Rim;
uniform bool use_rim = false;
uniform vec4 rim_color : source_color = vec4(1.0, 0.991, 0.955, 1.0);
uniform sampler2D rim_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool rim_color_map_on = false;
uniform float rim_power : hint_range(0.1, 10.0) = 4.0;
uniform float rim_lift : hint_range(-1.0, 1.0) = 0.0;
uniform float rim_lighting_mix : hint_range(0.0, 1.0) = 0.6;
uniform float rim_factor : hint_range(0.0, 1.0) = 0.5;

group_uniforms Grade;
uniform bool use_grade = false;
uniform vec4 color_filter : source_color = vec4(1.0);
uniform sampler2D color_filter_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool color_filter_map_on = false;
uniform vec4 shadow_tint : source_color = vec4(0.786, 0.798, 0.891, 1.0);
uniform sampler2D shadow_tint_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_tint_map_on = false;
uniform vec4 highlight_tint : source_color = vec4(1.0, 0.982, 0.955, 1.0);
uniform sampler2D highlight_tint_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool highlight_tint_map_on = false;
uniform float saturation : hint_range(0.0, 3.0) = 1.0;
uniform float brightness : hint_range(-1.0, 1.0) = 0.0;
uniform float contrast : hint_range(-1.0, 1.0) = 0.0;
uniform float grade_factor : hint_range(0.0, 1.0) = 1.0;

group_uniforms Master;
uniform float strength : hint_range(0.0, 10.0) = 1.0;
uniform float alpha : hint_range(0.0, 1.0) = 1.0;
uniform sampler2D alpha_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool alpha_map_on = false;
uniform float cutoff : hint_range(0.0, 1.0) = 0.5;
uniform bool use_normal_map = false;
uniform sampler2D normal_map : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float normal_strength : hint_range(0.0, 10.0) = 1.0;

group_uniforms World;
// The DaskToon scene's World colour times its strength: the light that reaches every surface (Godot's ambient is off).
uniform vec4 world_ambient : source_color = vec4(0.25, 0.25, 0.25, 1.0);
group_uniforms;

varying vec3 dt_base;
varying vec3 dt_shadow;
varying float dt_threshold;
varying vec3 dt_ambient;
varying vec3 dt_ao_color;
varying float dt_ao_mask;
varying vec3 dt_rim;
varying vec3 dt_filter;
varying vec3 dt_shadow_tint;
varying vec3 dt_highlight_tint;
varying vec3 dt_world_only;

DTAnimeBSDF dt_settings(vec3 base, vec3 shadow, float threshold, vec3 ambient, vec3 ao_col, float ao_msk, vec3 rim,
		vec3 filter_col, vec3 tint_dark, vec3 tint_light) {
	DTAnimeBSDF s;
	s.base_color = base;
	s.shadow_color = shadow;
	s.shadow_threshold = threshold;
	s.shadow_softness = shadow_softness;
	s.use_ramp = use_ramp;
	s.ramp_constant = ramp_constant;
	s.use_ambient = use_ambient;
	s.ambient_color = ambient;
	s.ambient_use_custom = ambient_use_custom;
	s.ambient_shadow_only = ambient_shadow_only;
	s.ambient_factor = ambient_factor;
	s.ambient_mode = ambient_mode;
	s.use_light = use_light;
	s.light_tint_strength = light_tint_strength;
	s.light_factor = light_factor;
	s.light_mode = light_mode;
	s.use_ao = use_ao;
	s.ao_color = ao_col;
	s.ao_darkness = ao_darkness;
	s.ao_factor = ao_factor;
	s.ao_mask = ao_msk;
	s.use_rim = use_rim;
	s.rim_color = rim;
	s.rim_power = rim_power;
	s.rim_lift = rim_lift;
	s.rim_lighting_mix = rim_lighting_mix;
	s.rim_factor = rim_factor;
	s.use_grade = use_grade;
	s.color_filter = filter_col;
	s.shadow_tint = tint_dark;
	s.highlight_tint = tint_light;
	s.saturation = saturation;
	s.brightness = brightness;
	s.contrast = contrast;
	s.grade_factor = grade_factor;
	s.strength = strength;
	return s;
}

void fragment() {
	vec2 uv = UV;
	dt_base = dt_color_input(base_color, base_map, base_map_on, uv).rgb;
	dt_shadow = dt_color_input(shadow_color, shadow_color_map, shadow_color_map_on, uv).rgb;
	dt_threshold = dt_float_input(shadow_threshold, shadow_threshold_map, shadow_threshold_map_on, uv);
	dt_ambient = dt_color_input(ambient_color, ambient_color_map, ambient_color_map_on, uv).rgb;
	dt_ao_color = dt_color_input(ao_color, ao_color_map, ao_color_map_on, uv).rgb;
	dt_ao_mask = dt_float_input(ao_mask, ao_mask_map, ao_mask_map_on, uv);
	dt_rim = dt_color_input(rim_color, rim_color_map, rim_color_map_on, uv).rgb;
	dt_filter = dt_color_input(color_filter, color_filter_map, color_filter_map_on, uv).rgb;
	dt_shadow_tint = dt_color_input(shadow_tint, shadow_tint_map, shadow_tint_map_on, uv).rgb;
	dt_highlight_tint = dt_color_input(highlight_tint, highlight_tint_map, highlight_tint_map_on, uv).rgb;
#if defined(DT_ALPHA_CLIP) || defined(DT_ALPHA_BLEND)
	ALPHA = clamp(dt_float_input(alpha, alpha_map, alpha_map_on, uv), 0.0, 1.0);
#endif
#if defined(DT_ALPHA_CLIP)
	ALPHA_SCISSOR_THRESHOLD = cutoff;
#endif
	if (use_normal_map) {
		NORMAL_MAP = texture(normal_map, uv).rgb;
		NORMAL_MAP_DEPTH = normal_strength;
	}
	// The anime colour arrives through EMISSION and DIFFUSE_LIGHT; nothing else of Godot's lighting is added.
	ALBEDO = vec3(1.0);
	METALLIC = 0.0;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	DTAnimeBSDF s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_ambient, dt_ao_color, dt_ao_mask, dt_rim,
			dt_filter, dt_shadow_tint, dt_highlight_tint);
	// Godot gives custom shading no ambient occlusion: AO stays open (1).
	dt_world_only = dt_anime_bsdf(s, world_ambient.rgb, world_ambient.rgb, 1.0, dot(NORMAL, VIEW), ramp_map);
	EMISSION = dt_world_only;
}

void light() {
	DTAnimeBSDF s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_ambient, dt_ao_color, dt_ao_mask, dt_rim,
			dt_filter, dt_shadow_tint, dt_highlight_tint);
	// LIGHT_COLOR is the lamp's colour x energy x PI: a lamp of energy E lights a facing surface with E.
	vec3 lamp = LIGHT_COLOR / DT_PI * ATTENUATION;
	vec3 up = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
	vec3 diffuse = world_ambient.rgb + lamp * max(dot(NORMAL, LIGHT), 0.0);
	vec3 diffuse_up = world_ambient.rgb + lamp * max(dot(up, LIGHT), 0.0);
	vec3 shaded = dt_anime_bsdf(s, diffuse, diffuse_up, 1.0, dot(NORMAL, VIEW), ramp_map);
	if (dt_luminance(shaded) > dt_luminance(dt_world_only + DIFFUSE_LIGHT) + 0.00001) {
		DIFFUSE_LIGHT = shaded - dt_world_only;
	}
}
