// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon shading core for Godot 4: DaskToon's GLSL node functions
// (source/blender/gpu/shaders/material/gpu_shader_material_*.glsl), as ported for Unity in
// scripts/modules/dasktoon_export/unity_urp/DaskToonCore.hlsl. Written by DaskToon Engine Export; edit the materials in
// DaskToon and export again.

#define DT_PI 3.14159265

// gpu_shader_material_dasktoon_shading.glsl

vec3 dt_rgb_to_hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 dt_hsv_to_rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Rec.709 luminance, identical to Blender's default OCIO luminance coefficients.
float dt_luminance(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

vec3 dt_overlay(vec3 a, vec3 b) {
	return mix(2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b), step(0.5, a));
}

vec3 dt_light_norm(vec3 light_col) {
	float l_max = max(max(light_col.r, light_col.g), light_col.b);
	return (l_max > 0.001) ? (light_col / l_max) : vec3(1.0);
}

vec3 dt_shade_simple(float light, vec3 base, vec3 shadow, float thresh, float softness, out float cel) {
	float s_soft = max(softness, 0.001);
	float s_min = clamp(thresh - s_soft * 0.5, 0.0, 1.0);
	float s_max = clamp(thresh + s_soft * 0.5, s_min + 0.0001, 1.0);
	cel = smoothstep(s_min, s_max, light);
	vec3 auto_shadow = base * shadow * 1.25;
	vec3 final_shadow = (length(shadow) > 0.001) ? mix(shadow, auto_shadow, 0.75) : base * 0.5;
	return mix(final_shadow, base, cel);
}

// The ramp texture is 256x1 with pixel i = ColorRamp.evaluate((i + 0.5) / 256). A CONSTANT ramp snaps t to a texel
// centre, which turns the bilinear clamp sampler into nearest sampling (Blender's valtorgb_nearest).
vec3 dt_ramp_color(sampler2D ramp, bool is_constant, float t) {
	if (is_constant) {
		t = (min(floor(t * 256.0), 255.0) + 0.5) / 256.0;
	}
	return textureLod(ramp, vec2(t, 0.5), 0.0).rgb;
}

vec3 dt_shade_ramp(float light, vec3 base, float thresh, sampler2D ramp, bool is_constant, out float cel) {
	float t = clamp(light + 0.5 - thresh, 0.0, 1.0);
	vec3 tint = dt_ramp_color(ramp, is_constant, t);
	float lum_dark = dt_luminance(dt_ramp_color(ramp, is_constant, 0.0));
	float lum_lit = dt_luminance(dt_ramp_color(ramp, is_constant, 1.0));
	cel = clamp((dt_luminance(tint) - lum_dark) / max(lum_lit - lum_dark, 0.0001), 0.0, 1.0);
	return base * tint;
}

// Ambient Mode: 0 OVERLAY, 1 HUE, 2 HUE_SAT, 3 SAT, 4 VAL, 5 MULTIPLY, 6 MIX.
vec3 dt_ambient_mode(vec3 a, vec3 b, int mode) {
	if (mode == 0) {
		return dt_overlay(a, b);
	}
	if (mode == 5) {
		return a * b;
	}
	if (mode < 1 || mode > 4) {
		return b;
	}
	vec3 ha = dt_rgb_to_hsv(a);
	vec3 hb = dt_rgb_to_hsv(b);
	if (mode == 1) {
		ha.x = hb.x;
	} else if (mode == 2) {
		ha.x = hb.x;
		ha.y = mix(ha.y, hb.y, 0.65);
	} else if (mode == 3) {
		ha.y = hb.y;
	} else {
		ha.z = hb.z;
	}
	return dt_hsv_to_rgb(ha);
}

// Light Mode: 0 OVERLAY, 1 HUE, 2 MULTIPLY, 3 ADD, 4 PURE_CEL.
vec3 dt_light_mode(vec3 c, vec3 light_col, vec3 light_norm, float strength, int mode) {
	float s = clamp(strength, 0.0, 2.0);
	vec3 ls = mix(vec3(1.0), light_norm, s);
	if (mode == 0) {
		return dt_overlay(c, ls);
	}
	if (mode == 1) {
		vec3 hc = dt_rgb_to_hsv(c);
		vec3 hl = dt_rgb_to_hsv(light_norm);
		vec3 tinted = dt_hsv_to_rgb(vec3(hl.x, hc.y, hc.z));
		return mix(c, tinted, clamp(s, 0.0, 1.0) * hl.y);
	}
	if (mode == 2) {
		return c * ls;
	}
	if (mode == 3) {
		return c + (light_col - min(min(light_col.r, light_col.g), light_col.b)) * s;
	}
	return c;
}

// Blender's UV (origin at the bottom) of a Godot UV (origin at the top), moved by a UV transform (scale xy, offset zw):
// how a flat eye or a 2D mouth moves its UVs (DaskToon's dasktoon_rig.gd sets it; Unity: _DT_UVTransform).
vec2 dt_blender_uv(vec2 uv, vec4 t) {
	return vec2(uv.x, 1.0 - uv.y) * t.xy + t.zw;
}

// The moved UV back in Godot's terms, for reading textures.
vec2 dt_moved_uv(vec2 uv, vec4 t) {
	vec2 b = dt_blender_uv(uv, t);
	return vec2(b.x, 1.0 - b.y);
}

// value x texture when the map is on. Float inputs read the texture's luminance, like Blender's implicit
// colour-to-float conversion.
vec4 dt_color_input(vec4 value, sampler2D tex, bool map_on, vec2 uv) {
	return map_on ? value * texture(tex, uv) : value;
}

float dt_float_input(float value, sampler2D tex, bool map_on, vec2 uv) {
	return map_on ? value * dt_luminance(texture(tex, uv).rgb) : value;
}

vec3 dt_grade(vec3 c, vec3 filter_col, vec3 shadow_tint, vec3 highlight_tint, float saturation, float brightness,
		float contrast) {
	vec3 graded = c * filter_col;
	float lum = dot(graded, vec3(0.299, 0.587, 0.114));
	graded = mix(graded * shadow_tint, graded * highlight_tint, clamp(lum, 0.0, 1.0));
	if (abs(saturation - 1.0) > 0.001) {
		vec3 hsv = dt_rgb_to_hsv(graded);
		hsv.y = clamp(hsv.y * max(saturation, 0.0), 0.0, 1.0);
		graded = dt_hsv_to_rgb(hsv);
	}
	graded += brightness;
	graded = (graded - 0.5) * (1.0 + contrast) + 0.5;
	return max(graded, vec3(0.0));
}

// gpu_shader_material_anime_character.glsl (Anime BSDF). The modules are switches of the material.

struct DTAnimeBSDF {
	vec3 base_color;
	vec3 shadow_color;
	float shadow_threshold;
	float shadow_softness;
	bool use_ramp;
	bool ramp_constant;
	bool use_ambient;
	vec3 ambient_color;
	bool ambient_use_custom;
	bool ambient_shadow_only;
	float ambient_factor;
	int ambient_mode;
	bool use_light;
	float light_tint_strength;
	float light_factor;
	int light_mode;
	bool use_ao;
	vec3 ao_color;
	float ao_darkness;
	float ao_factor;
	float ao_mask;
	bool use_rim;
	vec3 rim_color;
	float rim_power;
	float rim_lift;
	float rim_lighting_mix;
	float rim_factor;
	bool use_grade;
	vec3 color_filter;
	vec3 shadow_tint;
	vec3 highlight_tint;
	float saturation;
	float brightness;
	float contrast;
	float grade_factor;
	float strength;
};

// `diffuse` is the diffuse light reaching the surface (Blender's closure_eval: the lamps and the world), `diffuse_up`
// the same for the world up direction, `ao` the ambient occlusion visibility (1 = open).
vec3 dt_anime_bsdf(DTAnimeBSDF s, vec3 diffuse, vec3 diffuse_up, float ao, float n_dot_v, sampler2D ramp) {
	vec3 base = max(s.base_color, 0.0);
	vec3 shadow = max(s.shadow_color, 0.0);
	vec3 light_col = diffuse;
	float light_intensity = max(max(light_col.r, light_col.g), light_col.b);

	float cel;
	vec3 c;
	if (s.use_ramp) {
		c = dt_shade_ramp(light_intensity, base, s.shadow_threshold, ramp, s.ramp_constant, cel);
	} else {
		c = dt_shade_simple(light_intensity, base, shadow, s.shadow_threshold, s.shadow_softness, cel);
	}

	if (s.use_ambient) {
		float amb_fac = clamp(s.ambient_factor, 0.0, 1.0);
		if (amb_fac > 0.0001) {
			vec3 amb_color = s.ambient_use_custom ? s.ambient_color : diffuse_up;
			vec3 amb_shaded = dt_ambient_mode(c, amb_color, s.ambient_mode);
			float apply_mask = s.ambient_shadow_only ? (1.0 - cel) : 1.0;
			c = mix(c, amb_shaded, amb_fac * apply_mask);
		}
	}

	if (s.use_light) {
		float lit_fac = clamp(s.light_factor, 0.0, 1.0);
		if (lit_fac > 0.0001) {
			vec3 lit_shaded = dt_light_mode(c, light_col, dt_light_norm(light_col), s.light_tint_strength,
					s.light_mode);
			c = mix(c, lit_shaded, lit_fac * cel);
		}
	}

	if (s.use_ao) {
		float ao_f = clamp(s.ao_factor, 0.0, 1.0) * clamp(s.ao_mask, 0.0, 1.0);
		if (ao_f > 0.0001) {
			float darkness = max(s.ao_darkness, 0.0);
			float occlusion = clamp(1.0 - ao, 0.0, 1.0);
			float deep_occlusion = clamp(pow(occlusion, 1.0 / max(darkness, 0.01)) * min(darkness, 3.0), 0.0, 1.0);
			vec3 ao_multiplier = mix(vec3(1.0), s.ao_color, deep_occlusion);
			c = mix(c, c * ao_multiplier, ao_f);
		}
	}

	if (s.use_rim) {
		float rim_f = clamp(s.rim_factor, 0.0, 1.0);
		if (rim_f > 0.0001) {
			float fresnel = 1.0 - clamp(n_dot_v, 0.0, 1.0);
			float rim_term = clamp(pow(fresnel, max(s.rim_power, 0.5)) + s.rim_lift, 0.0, 1.0);
			vec3 rim_col = s.rim_color;
			float rim_l_mix = clamp(s.rim_lighting_mix, 0.0, 1.0);
			if (rim_l_mix > 0.001) {
				rim_col = mix(rim_col, rim_col * light_col, rim_l_mix);
			}
			float light_visibility = mix(1.0, clamp(light_intensity * 1.5, 0.0, 1.0), rim_l_mix);
			c += rim_col * (rim_term * rim_f * light_visibility);
		}
	}

	if (s.use_grade) {
		float grd_fac = clamp(s.grade_factor, 0.0, 1.0);
		if (grd_fac > 0.0001) {
			vec3 graded = dt_grade(c, s.color_filter, s.shadow_tint, s.highlight_tint, s.saturation, s.brightness,
					s.contrast);
			c = mix(c, graded, grd_fac);
		}
	}

	return max(c * max(s.strength, 0.0), vec3(0.0));
}

// The GGX highlight of one lamp (Unity port: DT_GGX), NdotL included: the toon specular's sharp reflection.
float dt_ggx(vec3 N, vec3 V, vec3 L, float alpha) {
	vec3 H = normalize(L + V);
	float n_dot_h = clamp(dot(N, H), 0.0, 1.0);
	float n_dot_l = clamp(dot(N, L), 0.0, 1.0);
	float n_dot_v = max(clamp(dot(N, V), 0.0, 1.0), 0.0001);
	float a2 = alpha * alpha;
	float d = n_dot_h * n_dot_h * (a2 - 1.0) + 1.0;
	float D = a2 / (DT_PI * d * d + 1e-7);
	float k = alpha * 0.5;
	float vis = 1.0 / (4.0 * (n_dot_l * (1.0 - k) + k) * (n_dot_v * (1.0 - k) + k));
	return D * vis * n_dot_l;
}

// gpu_shader_material_anime_cel.glsl (Anime Cel / Classic Cel)

struct DTAnimeCel {
	vec3 base_color;
	vec3 shadow_color;
	float shadow_threshold;
	float shadow_softness;
	bool use_ramp;
	bool ramp_constant;
	vec4 ambient_color;
	float ambient_blend;
	bool ambient_shadow_only;
	int ambient_mode;
	float light_tint_strength;
	int light_mode;
	vec3 specular_color;
	float specular_size;
	float specular_softness;
};

// `glossy` is the luminance of the sharp reflection (the lamps through GGX and the world).
vec3 dt_anime_cel(DTAnimeCel s, vec3 diffuse, float glossy, sampler2D ramp) {
	vec3 base = max(s.base_color, 0.0);
	vec3 shadow = max(s.shadow_color, 0.0);
	vec4 ambient = max(s.ambient_color, 0.0);
	vec3 spec_color = max(s.specular_color, 0.0);

	// Ambient: tints the shadow tone, and the lit tone unless "shadow only".
	float blend_fac = clamp(s.ambient_blend * ambient.a, 0.0, 1.0);
	vec3 shadow_amb = mix(shadow, dt_ambient_mode(shadow, ambient.rgb, s.ambient_mode), blend_fac);
	vec3 lit_col = base;
	if (!s.ambient_shadow_only) {
		lit_col = mix(lit_col, lit_col * ambient.rgb, blend_fac * 0.5);
	}

	vec3 light_col = diffuse;
	float light = max(max(light_col.r, light_col.g), light_col.b);

	float cel;
	vec3 color;
	if (s.use_ramp) {
		color = dt_shade_ramp(light, lit_col, s.shadow_threshold, ramp, s.ramp_constant, cel);
	} else {
		color = dt_shade_simple(light, lit_col, shadow_amb, s.shadow_threshold, s.shadow_softness, cel);
	}

	// Lamp colour on the lit side.
	color = mix(color, dt_light_mode(color, light_col, dt_light_norm(light_col), s.light_tint_strength, s.light_mode),
			cel);

	// Toon specular: glossy light level cut at (1 - size).
	float spec = clamp((glossy - (1.0 - s.specular_size)) / max(s.specular_softness, 0.0001), 0.0, 1.0);
	color += spec_color * spec;
	return color;
}

// gpu_shader_material_anime_angel_ring.glsl. position_b / normal_b are in Blender world space. It takes fwidth, so
// only fragment() calls it. Returns the ring Color output; `fac` is the Fac output.
vec3 dt_angel_ring(vec3 highlight_color, float band_position, float band_width, float band_softness,
		float strand_jitter, float noise_scale, float intensity, vec3 position_b, vec3 normal_b, out float fac) {
	vec3 highlight = max(highlight_color, 0.0);
	vec3 N = normalize(normal_b);
	float jitter = sin(dot(position_b.xy, vec2(noise_scale * 0.7, noise_scale * 1.3))) * strand_jitter * 0.1;
	float ring_dist = abs(N.z + jitter - clamp(band_position, 0.0, 1.0));
	float r_fw = max(fwidth(ring_dist), 0.0005);
	float r_soft = max(band_softness, r_fw);
	float r_width = max(band_width, 0.001);
	float ring_min = max(r_width - r_soft * 0.5, 0.0);
	float ring_max = r_width + r_soft * 0.5 + 0.0001;
	float ring_fac = 1.0 - smoothstep(ring_min, ring_max, ring_dist);
	fac = ring_fac * max(intensity, 0.0);
	return highlight * fac;
}

// Mix node, data type Color, blend ADD: mix(A, A + B, factor) = A + factor * B.
vec3 dt_hair(vec3 cel, vec3 ring, float ring_fac, bool clamp_factor, bool clamp_result) {
	float f = clamp_factor ? clamp(ring_fac, 0.0, 1.0) : ring_fac;
	vec3 c = cel + f * ring;
	return clamp_result ? clamp(c, 0.0, 1.0) : c;
}

// gpu_shader_material_anime_eye.glsl (unlit)

vec3 dt_anime_eye(vec3 iris_color, vec3 pupil_color, vec3 glow_color, float glow_power, vec3 top_shadow_tint,
		vec3 sparkle_color, vec2 uv) {
	vec3 iris = max(iris_color, 0.0);
	vec3 pupil = max(pupil_color, 0.0);
	vec3 glow = max(glow_color, 0.0);
	vec3 top_shadow = max(top_shadow_tint, 0.0);
	vec3 sparkle = max(sparkle_color, 0.0);

	float dist_center = length(uv - vec2(0.5, 0.5));
	float pupil_fac = 1.0 - smoothstep(0.16, 0.22, dist_center);
	vec3 base_iris = mix(iris, pupil, pupil_fac);

	float bottom_curve = pow(clamp(1.0 - uv.y, 0.0, 1.0), 2.2) * max(glow_power, 0.0);
	vec3 with_glow = base_iris + glow * bottom_curve;

	float top_shadow_fac = smoothstep(0.45, 0.85, uv.y);
	vec3 with_shadow = mix(with_glow, with_glow * top_shadow, top_shadow_fac);

	float sp1 = 1.0 - smoothstep(0.035, 0.055, length(uv - vec2(0.38, 0.65)));
	float sp2 = 1.0 - smoothstep(0.018, 0.032, length(uv - vec2(0.62, 0.40)));
	float sparkle_fac = clamp(sp1 + sp2, 0.0, 1.0);
	return mix(with_shadow, sparkle, sparkle_fac);
}

// gpu_shader_material_dask_cel.glsl. Its in-surface outline is on with use_outline.

struct DTDaskCel {
	vec3 base_color;
	vec3 shadow_color;
	float shadow_threshold;
	float shadow_softness;
	bool use_ramp;
	bool ramp_constant;
	bool use_outline;
	float outline_width;
	vec3 outline_color;
	float outline_lighting_mix;
	int outline_tint_mode;
	float strength;
};

vec3 dt_dask_cel(DTDaskCel s, vec3 diffuse, float n_dot_v, sampler2D ramp) {
	vec3 base = max(s.base_color, 0.0);
	vec3 shadow = max(s.shadow_color, 0.0);
	float light_intensity = max(max(diffuse.r, diffuse.g), diffuse.b);

	float cel;
	vec3 c;
	if (s.use_ramp) {
		c = dt_shade_ramp(light_intensity, base, s.shadow_threshold, ramp, s.ramp_constant, cel);
	} else {
		c = dt_shade_simple(light_intensity, base, shadow, s.shadow_threshold, s.shadow_softness, cel);
	}

	if (s.use_outline) {
		float edge_factor = 1.0 - abs(n_dot_v);
		float outline_thresh = 1.0 - clamp(s.outline_width * 50.0, 0.005, 0.99);
		if (edge_factor > outline_thresh) {
			vec3 line_col = s.outline_color;
			vec3 base_hsv = dt_rgb_to_hsv(base);
			if (s.outline_tint_mode == 1) {
				float o_h = fract(base_hsv.x - 0.03 + 1.0);
				float o_s = clamp(base_hsv.y * 1.40 + 0.10, 0.0, 1.0);
				float o_v = base_hsv.z * 0.35;
				line_col = dt_hsv_to_rgb(vec3(o_h, o_s, o_v));
			} else if (s.outline_tint_mode >= 2) {
				vec3 dark_tint = dt_hsv_to_rgb(vec3(base_hsv.x, clamp(base_hsv.y * 1.3, 0.0, 1.0), base_hsv.z * 0.35));
				line_col = mix(dark_tint, dark_tint * diffuse * DT_PI, 0.6);
			}
			if (s.outline_lighting_mix > 0.01) {
				line_col = mix(line_col, line_col * diffuse * DT_PI, s.outline_lighting_mix);
			}
			c = line_col;
		}
	}

	return max(c * max(s.strength, 0.0), vec3(0.0));
}

// Dask Outline (project 1): the line colour. `n_dot_l` is the hull normal against Blender's fixed light
// normalize(0.5, 0.8, 0.6); `diffuse_mix` is applied by the caller, which owns the lights.
vec3 dt_outline_color(vec3 base_color, vec3 outline_color, float light_bleed, float tint_darkness,
		float tint_sat_boost, int tint_mode, float n_dot_l) {
	vec3 base_rgb = max(base_color, 0.0);
	vec3 outline_rgb = max(outline_color, 0.0);
	float half_lambert = n_dot_l * 0.5 + 0.5;

	vec3 base_hsv = dt_rgb_to_hsv(base_rgb);
	float target_v = clamp(base_hsv.z * clamp(tint_darkness, 0.05, 1.0), 0.02, 0.95);
	float target_s = clamp(base_hsv.y * clamp(tint_sat_boost, 0.5, 3.0), 0.10, 1.0);
	vec3 harmonic_rgb = dt_hsv_to_rgb(vec3(base_hsv.x, target_s, target_v));

	vec3 line_rgb = outline_rgb;
	if (tint_mode == 1) {
		line_rgb = harmonic_rgb;
		if (half_lambert > 0.7 && light_bleed > 0.2) {
			float glow_fac = (half_lambert - 0.7) * 3.33 * light_bleed;
			line_rgb = mix(line_rgb, base_rgb, clamp(glow_fac, 0.0, 0.6));
		}
	} else if (tint_mode >= 2) {
		line_rgb = mix(harmonic_rgb, harmonic_rgb * (half_lambert * 0.8 + 0.2), 0.8);
	}
	return line_rgb;
}

// Width of the Geometry Nodes hull (project 1, spec 4.3):
// light_thin = 1 - clamp((hl - 0.55) / 0.45) * bleed * 0.75, hl = dot(N, L) * 0.5 + 0.5,
// f(u, v) = sin(2u) cos(3v) + 0.5 sin(6.28v) with (u, v) = uv0 * 12 (Blender's UV, origin at the bottom).
float dt_outline_width(float width, float bleed, float wobble, float n_dot_l, vec2 uv0, float mask) {
	float hl = n_dot_l * 0.5 + 0.5;
	float light_thin = 1.0 - clamp((hl - 0.55) / 0.45, 0.0, 1.0) * bleed * 0.75;
	float u = uv0.x * 12.0;
	float v = uv0.y * 12.0;
	float f = sin(2.0 * u) * cos(3.0 * v) + 0.5 * sin(6.28 * v);
	return width * light_thin * (1.0 + 0.25 * wobble * f) * mask;
}

// Octahedral decode of DT_OutlineN (scripts/startup/bl_ui/dasktoon_outline_gamedata.py: oct_decode).
vec3 dt_oct_decode(vec2 e) {
	vec3 n = vec3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y));
	float t = max(-n.z, 0.0);
	n.x += (n.x >= 0.0) ? -t : t;
	n.y += (n.y >= 0.0) ? -t : t;
	return normalize(n);
}
