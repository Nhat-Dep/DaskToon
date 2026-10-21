// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon Anime Cel (Classic Cel) for Godot 4, with the hair pattern's Angel Ring layer (use_angel_ring); included by
// the anime_cel*.gdshader files, which choose the culling. Written by DaskToon Engine Export; edit the materials in
// DaskToon and export again.
//
// As in anime_bsdf.gdshaderinc: fragment() shades with the world light alone and emits that; light() shades with the
// world light and one lamp, and the brightest result wins.

#include "res://DaskToon/Shaders/dasktoon_core.gdshaderinc"

group_uniforms Surface;
uniform vec4 base_color : source_color = vec4(0.955, 0.916, 0.896, 1.0);
uniform sampler2D base_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool base_map_on = false;
uniform vec4 shadow_color : source_color = vec4(0.798, 0.735, 0.767, 1.0);
uniform sampler2D shadow_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_color_map_on = false;
uniform float shadow_threshold : hint_range(0.0, 1.0) = 0.48;
uniform sampler2D shadow_threshold_map : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool shadow_threshold_map_on = false;
uniform float shadow_softness : hint_range(0.001, 0.5) = 0.02;
uniform bool use_ramp = false;
uniform sampler2D ramp_map : source_color, hint_default_white, filter_linear, repeat_disable;
uniform bool ramp_constant = true;

group_uniforms Ambient;
uniform int ambient_mode : hint_enum("Overlay", "Hue", "Hue Saturation", "Saturation", "Value", "Multiply", "Mix") = 2;
uniform vec4 ambient_color : source_color = vec4(0.906, 0.931, 0.978, 1.0);
uniform sampler2D ambient_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool ambient_color_map_on = false;
uniform float ambient_blend : hint_range(0.0, 1.0) = 0.5;
uniform bool ambient_shadow_only = true;

group_uniforms Light;
uniform int light_mode : hint_enum("Overlay", "Hue", "Multiply", "Add", "Pure Cel") = 0;
uniform float light_tint_strength : hint_range(0.0, 2.0) = 1.0;

group_uniforms Specular;
uniform vec4 specular_color : source_color = vec4(1.0);
uniform sampler2D specular_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool specular_color_map_on = false;
uniform float specular_size : hint_range(0.0, 1.0) = 0.08;
uniform float specular_softness : hint_range(0.0, 1.0) = 0.02;

group_uniforms Master;
uniform bool use_normal_map = false;
uniform sampler2D normal_map : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float normal_strength : hint_range(0.0, 10.0) = 1.0;
uniform float emission_strength = 1.0;

group_uniforms AngelRing;
uniform bool use_angel_ring = false;
uniform vec4 ring_color : source_color = vec4(1.0, 0.982, 0.945, 1.0);
uniform float ring_position : hint_range(0.0, 1.0) = 0.5;
uniform float ring_width : hint_range(0.0, 1.0) = 0.08;
uniform float ring_softness : hint_range(0.0, 1.0) = 0.02;
uniform float ring_jitter : hint_range(0.0, 1.0) = 0.12;
uniform float ring_noise_scale = 35.0;
uniform float ring_intensity = 1.5;
uniform bool ring_clamp_factor = true;
uniform bool ring_clamp_result = false;
// EEVEE also adds the closures of the hair pattern's nodes, scaled by their hidden Weight: DaskToon shows them.
uniform float cel_self_emission = 0.0;
uniform float ring_self_emission = 0.0;

group_uniforms World;
// The DaskToon scene's World colour times its strength: the light that reaches every surface (Godot's ambient is off).
uniform vec4 world_ambient : source_color = vec4(0.25, 0.25, 0.25, 1.0);
group_uniforms;

varying vec3 dt_base;
varying vec3 dt_shadow;
varying float dt_threshold;
varying vec4 dt_ambient;
varying vec3 dt_specular;
varying vec3 dt_ring;
varying float dt_ring_fac;
varying vec3 dt_world_only;

DTAnimeCel dt_settings(vec3 base, vec3 shadow, float threshold, vec4 ambient, vec3 specular) {
	DTAnimeCel s;
	s.base_color = base;
	s.shadow_color = shadow;
	s.shadow_threshold = threshold;
	s.shadow_softness = shadow_softness;
	s.use_ramp = use_ramp;
	s.ramp_constant = ramp_constant;
	s.ambient_color = ambient;
	s.ambient_blend = ambient_blend;
	s.ambient_shadow_only = ambient_shadow_only;
	s.ambient_mode = ambient_mode;
	s.light_tint_strength = light_tint_strength;
	s.light_mode = light_mode;
	s.specular_color = specular;
	s.specular_size = specular_size;
	s.specular_softness = specular_softness;
	return s;
}

// The hair pattern: Emission(Mix[ADD](Anime Cel, Angel Ring, Ring Fac)) plus each node's own emission.
vec3 dt_output(vec3 cel, vec3 ring, float ring_fac) {
	if (!use_angel_ring) {
		return cel;
	}
	return dt_hair(cel, ring, ring_fac, ring_clamp_factor, ring_clamp_result) * emission_strength
			+ cel * cel_self_emission + ring * ring_self_emission;
}

void fragment() {
	vec2 uv = UV;
	dt_base = dt_color_input(base_color, base_map, base_map_on, uv).rgb;
	dt_shadow = dt_color_input(shadow_color, shadow_color_map, shadow_color_map_on, uv).rgb;
	dt_threshold = dt_float_input(shadow_threshold, shadow_threshold_map, shadow_threshold_map_on, uv);
	dt_ambient = dt_color_input(ambient_color, ambient_color_map, ambient_color_map_on, uv);
	dt_specular = dt_color_input(specular_color, specular_color_map, specular_color_map_on, uv).rgb;
	if (use_normal_map) {
		NORMAL_MAP = texture(normal_map, uv).rgb;
		NORMAL_MAP_DEPTH = normal_strength;
	}
	dt_ring = vec3(0.0);
	dt_ring_fac = 0.0;
	if (use_angel_ring) {
		// The ring follows Blender's world axes: Godot's (x, y, z) is Blender's (x, -z, y).
		vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
		vec3 normal = (INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz;
		dt_ring = dt_angel_ring(ring_color.rgb, ring_position, ring_width, ring_softness, ring_jitter,
				ring_noise_scale, ring_intensity, vec3(world.x, -world.z, world.y),
				vec3(normal.x, -normal.z, normal.y), dt_ring_fac);
	}
	// The anime colour arrives through EMISSION and DIFFUSE_LIGHT; nothing else of Godot's lighting is added.
	ALBEDO = vec3(1.0);
	METALLIC = 0.0;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	DTAnimeCel s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_ambient, dt_specular);
	dt_world_only = dt_output(dt_anime_cel(s, world_ambient.rgb, dt_luminance(world_ambient.rgb), ramp_map), dt_ring,
			dt_ring_fac);
	EMISSION = dt_world_only;
}

void light() {
	DTAnimeCel s = dt_settings(dt_base, dt_shadow, dt_threshold, dt_ambient, dt_specular);
	vec3 lamp = LIGHT_COLOR / DT_PI * ATTENUATION;
	vec3 diffuse = world_ambient.rgb + lamp * max(dot(NORMAL, LIGHT), 0.0);
	// The sharp reflection of the Anime Cel's toon specular: roughness 0.05, alpha 0.0025.
	float glossy = dt_luminance(world_ambient.rgb + lamp * dt_ggx(NORMAL, VIEW, LIGHT, 0.0025));
	vec3 shaded = dt_output(dt_anime_cel(s, diffuse, glossy, ramp_map), dt_ring, dt_ring_fac);
	if (dt_luminance(shaded) > dt_luminance(dt_world_only + DIFFUSE_LIGHT) + 0.00001) {
		DIFFUSE_LIGHT = shaded - dt_world_only;
	}
}
