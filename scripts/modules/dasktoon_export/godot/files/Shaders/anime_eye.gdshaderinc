// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon Anime Eye for Godot 4 (unlit), included by the anime_eye*.gdshader files, which choose the culling. Written
// by DaskToon Engine Export; edit the materials in DaskToon and export again.

#include "res://DaskToon/Shaders/dasktoon_core.gdshaderinc"

group_uniforms Eye;
uniform vec4 base_color : source_color = vec4(0.424, 0.701, 0.931, 1.0);
uniform sampler2D base_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool base_map_on = false;
uniform vec4 pupil_color : source_color = vec4(0.152, 0.248, 0.381, 1.0);
uniform sampler2D pupil_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool pupil_color_map_on = false;
uniform vec4 glow_color : source_color = vec4(0.626, 0.931, 1.0, 1.0);
uniform sampler2D glow_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool glow_color_map_on = false;
uniform float glow_power = 1.5;
uniform vec4 top_shadow_tint : source_color = vec4(0.313, 0.381, 0.537, 1.0);
uniform sampler2D top_shadow_tint_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool top_shadow_tint_map_on = false;
uniform vec4 sparkle_color : source_color = vec4(1.0);
uniform sampler2D sparkle_color_map : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool sparkle_color_map_on = false;
// Off: the eye is drawn from the Blender world position's XY, as the node does when its UV input is unlinked.
uniform bool eye_use_uv = true;
group_uniforms;

void fragment() {
	vec2 uv = UV;
	// The node reads Blender's UV, whose origin is at the bottom; glTF and Godot put it at the top.
	vec2 blender_uv = vec2(UV.x, 1.0 - UV.y);
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 eye_uv = (eye_use_uv && dot(blender_uv, blender_uv) > 1e-6) ? blender_uv : vec2(world.x, -world.z) * 0.5 + 0.5;
	ALBEDO = dt_anime_eye(dt_color_input(base_color, base_map, base_map_on, uv).rgb,
			dt_color_input(pupil_color, pupil_color_map, pupil_color_map_on, uv).rgb,
			dt_color_input(glow_color, glow_color_map, glow_color_map_on, uv).rgb, glow_power,
			dt_color_input(top_shadow_tint, top_shadow_tint_map, top_shadow_tint_map_on, uv).rgb,
			dt_color_input(sparkle_color, sparkle_color_map, sparkle_color_map_on, uv).rgb, eye_uv);
}
