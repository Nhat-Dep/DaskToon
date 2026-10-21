// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon's illustration finish in Godot 4 (scripts/modules/dasktoon_finish/nodes.py), the layers that change each
// pixel's colour: Shadow and Light Tint, Light Gradient, Saturation and Contrast, Vignette, in the finish's order. It
// works on the colours as seen (sRGB, 0 to 1), as the finish does, over the screen of a CanvasLayer above the 3D view
// (<model>_finish.tscn). Written by DaskToon Engine Export; edit the finish in DaskToon and export again.
shader_type canvas_item;
render_mode unshaded;

uniform sampler2D screen : hint_screen_texture, filter_nearest;

uniform float amount : hint_range(0.0, 1.0) = 1.0;

group_uniforms ShadowAndLightTint;
uniform bool grade_on = true;
uniform vec3 shadow_tint = vec3(0.60, 0.55, 0.90);
uniform vec3 light_tint = vec3(1.0, 0.86, 0.66);
uniform float grade_strength : hint_range(0.0, 1.0) = 0.45;

group_uniforms LightGradient;
uniform bool gradient_on = true;
uniform vec3 gradient_light = vec3(1.0, 0.82, 0.62);
uniform vec3 gradient_dark = vec3(0.42, 0.48, 0.80);
uniform float gradient_strength : hint_range(0.0, 1.0) = 0.25;
// The direction on the picture the light comes from (x right, y up); dasktoon_finish.gd follows the camera and Sun.
uniform vec2 light_direction = vec2(0.0, 1.0);

group_uniforms SaturationAndContrast;
uniform bool color_on = true;
uniform float saturation : hint_range(0.0, 2.0) = 1.15;
uniform float contrast : hint_range(-0.5, 0.5) = 0.1;

group_uniforms Vignette;
uniform bool vignette_on = true;
uniform float vignette_size : hint_range(0.0, 1.5) = 0.75;
uniform float vignette_softness : hint_range(0.01, 1.5) = 0.9;
uniform vec3 vignette_color = vec3(0.12, 0.10, 0.20);
uniform float vignette_strength : hint_range(0.0, 1.0) = 0.25;
group_uniforms;

float luminance(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

// Map Range, Smooth Step, clamped.
float map_range(float value, float low, float high, float to_low, float to_high) {
	float t = clamp((value - low) / (high - low), 0.0, 1.0);
	t = t * t * (3.0 - 2.0 * t);
	return to_low + t * (to_high - to_low);
}

// Blender's Mix node, Color: Multiply and Soft Light, result clamped.
vec3 mix_multiply(vec3 a, vec3 b, float factor) {
	return clamp(mix(a, a * b, factor), 0.0, 1.0);
}

vec3 mix_soft_light(vec3 a, vec3 b, float factor) {
	vec3 screen_ab = 1.0 - (1.0 - b) * (1.0 - a);
	return clamp(mix(a, (1.0 - a) * b * a + a * screen_ab, factor), 0.0, 1.0);
}

vec3 rgb_to_hsv(vec3 c) {
	float high = max(c.r, max(c.g, c.b));
	float low = min(c.r, min(c.g, c.b));
	float delta = high - low;
	float h = 0.0;
	if (delta > 0.0) {
		if (high == c.r) {
			h = mod((c.g - c.b) / delta, 6.0);
		} else if (high == c.g) {
			h = (c.b - c.r) / delta + 2.0;
		} else {
			h = (c.r - c.g) / delta + 4.0;
		}
		h /= 6.0;
	}
	return vec3(h, high > 0.0 ? delta / high : 0.0, high);
}

vec3 hsv_to_rgb(vec3 c) {
	vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
	return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

vec3 to_srgb(vec3 c) {
	c = max(c, 0.0);
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

void fragment() {
	vec3 rendered = textureLod(screen, SCREEN_UV, 0.0).rgb;
	vec3 img = clamp(rendered, 0.0, 1.0);
	// The picture's coordinates as the finish reads them: 0 to 1 from the bottom left.
	vec2 centered = vec2(SCREEN_UV.x, 1.0 - SCREEN_UV.y) - 0.5;
	if (grade_on) {
		// The dark areas deepen toward the shadow tint; the light areas take the light tint's hue, not its lightness.
		float lum = luminance(img);
		float dark = map_range(lum, 0.05, 0.55, 1.0, 0.0);
		float light = map_range(lum, 0.45, 0.95, 0.0, 1.0);
		img = mix_multiply(img, shadow_tint, dark * grade_strength);
		vec3 hue = light_tint - luminance(light_tint) + 0.5;
		img = mix_soft_light(img, hue, light * grade_strength);
	}
	if (gradient_on) {
		float side = map_range(dot(centered, light_direction), -0.5, 0.5, 0.0, 1.0);
		img = mix_soft_light(img, clamp(mix(gradient_dark, gradient_light, side), 0.0, 1.0), gradient_strength);
	}
	if (color_on) {
		vec3 hsv = rgb_to_hsv(img);
		hsv.y = clamp(hsv.y * saturation, 0.0, 1.0);
		img = max(hsv_to_rgb(hsv), 0.0);
		img = clamp(mix(img, vec3(0.5), -contrast), 0.0, 1.0);
	}
	if (vignette_on) {
		float mask = map_range(length(centered * 2.0), vignette_size, vignette_size + vignette_softness, 0.0, 1.0);
		img = mix_multiply(img, vignette_color, mask * vignette_strength);
	}
	// Amount: the finish over the picture as rendered, in linear colour.
	COLOR = vec4(to_srgb(mix(to_linear(rendered), to_linear(img), amount)), 1.0);
}
