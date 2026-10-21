# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon materials as Godot ShaderMaterial resources (.tres) with their textures (Godot spec 4). The values come from
the material analysis Unity uses (graph.analyze_material), renamed the Godot way: _BaseColor -> base_color,
_DT_ShadowColorMapOn -> shadow_color_map_on. Only what the shader declares is written."""

import functools
import os
import re

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import files

GODOT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp", ".exr", ".hdr", ".svg"}
SHADERS = {"AnimeBSDF": "anime_bsdf", "AnimeCel": "anime_cel", "AnimeEye": "anime_eye", "DaskCel": "dask_cel"}
SHADER_NAMES = {"AnimeBSDF": "Anime BSDF", "AnimeCel": "Anime Cel", "AnimeEye": "Anime Eye", "DaskCel": "Dask Cel"}
OUTLINE = "anime_outline"
_UNIFORM = re.compile(r"^\s*uniform\s+(\w+)\s+(\w+)\s*(?::\s*([^=;]*))?", re.M)
_WORD_BREAK = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Texture import settings (Godot adds the rest): the ramp strip stays lossless and without mipmaps, so its hard steps
# stay hard; a normal map is imported as one.
RAMP_IMPORT = ("compress/mode=0", "mipmaps/generate=false", "detect_3d/compress_to=0")
NORMAL_IMPORT = ("compress/normal_map=1",)


def godot_name(prop):
    """Unity property -> Godot uniform: _DT_AOColorMapOn -> ao_color_map_on, _BaseColor -> base_color."""
    name = prop[len("_DT_"):] if prop.startswith("_DT_") else prop.lstrip("_")
    return _WORD_BREAK.sub("_", name).lower()


@functools.lru_cache(maxsize=None)
def uniforms(base):
    """[(name, type, is colour)] in the order <base>.gdshaderinc declares them."""
    with open(os.path.join(files.SOURCE_DIR, files.SHADERS, base + ".gdshaderinc"), encoding="utf-8") as f:
        text = f.read()
    return [(m.group(2), m.group(1), "source_color" in (m.group(3) or "")) for m in _UNIFORM.finditer(text)]


def srgb(x):
    x = max(x, 0.0)
    return x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1.0 / 2.4) - 0.055


def number(x):
    text = "%.6g" % x
    return text if any(c in text for c in ".en") else text + ".0"


def value_text(kind, is_colour, value):
    """A shader parameter value as Godot writes it in a .tres; colours are stored as sRGB."""
    if kind == "bool":
        return "true" if value > 0.5 else "false"
    if kind == "int":
        return "%d" % int(round(value))
    if kind == "float":
        return number(value)
    if kind == "vec4":
        rgb = [srgb(v) for v in value[:3]] if is_colour else list(value[:3])
        return "Color(%s)" % ", ".join(number(v) for v in rgb + [value[3] if len(value) > 3 else 1.0])
    if kind == "vec3":
        return "Vector3(%s)" % ", ".join(number(v) for v in value[:3])
    raise ValueError(kind)


def quoted(text):
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')


class _Resource:
    """Builds one .tres: ext resources by path, sub resources, and the [resource] section."""

    def __init__(self):
        self.ext = {}  # res path -> (id, type)
        self.subs = []

    def ext_id(self, kind, path):
        if path not in self.ext:
            self.ext[path] = ("%d_dt" % (len(self.ext) + 1), kind)
        return 'ExtResource("%s")' % self.ext[path][0]

    def params(self, base, values, textures):
        lines = []
        for name, kind, is_colour in uniforms(base):
            if kind.startswith("sampler"):
                if name in textures:
                    lines.append("shader_parameter/%s = %s" % (name, self.ext_id("Texture2D", textures[name])))
            elif name in values:
                lines.append("shader_parameter/%s = %s" % (name, value_text(kind, is_colour, values[name])))
        return lines

    def text(self, body):
        out = ['[gd_resource type="ShaderMaterial" load_steps=%d format=3]' % (len(self.ext) + len(self.subs) + 1), ""]
        for path, (ident, kind) in self.ext.items():
            out.append('[ext_resource type="%s" path=%s id="%s"]' % (kind, quoted(path), ident))
        out.append("")
        for header, lines in self.subs:
            out += [header] + lines + [""]
        out += ["[resource]"] + body
        return "\n".join(out) + "\n"


class Writer:
    """Writes one model's materials and textures under target.root/<name>/ (Godot spec 2)."""

    def __init__(self, target, options, rep, ambient, light_direction):
        self.target, self.options, self.rep = target, options, rep
        self.extras = {"world_ambient": tuple(ambient) + (1.0,), "light_direction": tuple(light_direction)}
        self.written = {}  # (image pointer, kind, colour) -> relative path, so a shared image is written once
        self.stems = set()

    def path(self, rel):
        return os.path.join(self.target.root, rel)

    def unique_stem(self, mat):
        from .. import safe_name
        stem = base = safe_name(mat.name)
        index = 2
        while stem.lower() in self.stems:
            stem = "%s_%d" % (base, index)
            index += 1
        self.stems.add(stem.lower())
        return stem

    def _image(self, spec, src, rel_stem):
        """Relative path of an image texture copied as it is (or as PNG when Godot cannot read its format)."""
        from .. import textures
        key = (src.image.as_pointer(), src.kind, src.color)
        if key in self.written:
            return self.written[key]
        found = textures.image_file(src.image)
        if found is None:
            return None
        ext, data = found
        if ext not in GODOT_IMAGE_EXTENSIONS:
            width, height = src.image.size
            pixels = np.array(src.image.pixels[:], dtype=np.float32)
            ext, data = ".png", textures.float_to_png(pixels, width, height, src.image.is_float and src.color)
        rel = rel_stem + ext
        files.write_texture_import(self.path(rel + ".import"), NORMAL_IMPORT if src.kind == 'NORMAL' else ())
        files.write_bytes(self.path(rel), data)
        self.written[key] = rel
        return rel

    def texture(self, spec, stem, prop, src, users):
        """Relative path of the texture written for `prop`, or None (the input then keeps its value)."""
        from .. import _tex_label, bake, textures
        rel_stem = "%s/Textures/%s_%s" % (self.target.name, stem, _tex_label(prop))
        if src.kind in ('IMAGE', 'NORMAL'):
            rel = self._image(spec, src, rel_stem)
            if rel is not None:
                return rel
            if src.kind == 'NORMAL':
                self.rep.warnings.append(rpt_("%s: cannot read the normal map image %s; normal map left out")
                                         % (spec.material.name, src.image.name))
                return None
        size = bake.branch_size(src.tree_owner, src.node, src.socket, self.options.bake_size)
        try:
            pixels = bake.bake_input(users[0], spec.material, src, size, self.options.bake_samples)
        except Exception as ex:  # A failed bake must not stop the export; the input keeps its value.
            self.rep.warnings.append(rpt_("%s › %s: bake failed (%s); using its value")
                                     % (spec.material.name, src.socket, ex))
            return None
        if textures.needs_float(pixels):
            rel, data = rel_stem + ".exr", textures.exr_bytes(pixels, size, size)
        else:
            rel, data = rel_stem + ".png", textures.float_to_png(pixels, size, size, src.color)
        files.write_texture_import(self.path(rel + ".import"))
        files.write_bytes(self.path(rel), data)
        self.rep.baked.append("%s › %s" % (spec.material.name, src.socket))
        if len(users) > 1:
            self.rep.warnings.append(rpt_("%s › %s: baked on the mesh of %s; the other meshes share this texture")
                                     % (spec.material.name, src.socket, users[0].name))
        return rel

    def _ramp(self, spec, stem):
        from .. import textures
        rel = "%s/Textures/%s_Ramp.png" % (self.target.name, stem)
        files.write_texture_import(self.path(rel + ".import"), RAMP_IMPORT)
        files.write_bytes(self.path(rel), textures.ramp_png(spec.ramp))
        return rel

    def _warnings(self, spec):
        # The material analysis is shared with the Unity export and names Unity in its messages.
        out = [w.replace("Unity", "Godot") for w in spec.warnings]
        if spec.shader not in SHADERS:
            out.append(rpt_("%s: %s is not in Godot yet; it is shown with Anime BSDF and its colours")
                       % (spec.material.name, SHADER_NAMES.get(spec.shader, spec.shader)))
        if "_DT_AO" in spec.keywords:
            out.append(rpt_("%s: AO is not drawn in Godot (Godot gives custom shading no ambient occlusion)")
                       % spec.material.name)
        return out

    def material(self, spec, users):
        """Write the material's textures and .tres; returns the .tres path relative to the model folder."""
        from .. import _drop_texture
        stem = self.unique_stem(spec.material)
        textures = {}
        for prop, src in sorted(spec.textures.items()):
            rel = self.texture(spec, stem, prop, src, users)
            if rel is None:
                _drop_texture(spec, prop, src)
            else:
                textures[godot_name(prop)] = files.res(rel)
        if spec.ramp is not None:
            textures["ramp_map"] = files.res(self._ramp(spec, stem))
        values = {godot_name(prop): value for prop, value in list(spec.floats.items()) + list(spec.colors.items())}
        values.update(self.extras)
        resource = _Resource()
        body = ["resource_name = %s" % quoted(spec.material.name), "render_priority = 0"]
        if spec.outline:
            alpha = 'CLIP' if "_DT_ALPHATEST_ON" in spec.keywords else 'OPAQUE'
            shader = resource.ext_id("Shader", files.res("%s/%s" % (files.SHADERS, files.shader_file(OUTLINE,
                                                                                                    alpha=alpha))))
            resource.subs.append(('[sub_resource type="ShaderMaterial" id="ShaderMaterial_outline"]',
                                  ["render_priority = 0", "shader = " + shader]
                                  + resource.params(OUTLINE, values, textures)))
            body.append('next_pass = SubResource("ShaderMaterial_outline")')
        cull_back = spec.floats.get("_Cull", 0.0) > 1.5
        alpha = ('BLEND' if spec.render_type == "Transparent"
                 else 'CLIP' if "_DT_ALPHATEST_ON" in spec.keywords else 'OPAQUE')
        base = SHADERS.get(spec.shader, "anime_bsdf")
        if base != "anime_bsdf":
            alpha = 'OPAQUE'  # only the Anime BSDF has an alpha (graph._render_state)
        body.append("shader = " + resource.ext_id("Shader", files.res("%s/%s" % (
            files.SHADERS, files.shader_file(base, cull_back, alpha)))))
        body += resource.params(base, values, textures)
        rel = "Materials/%s.tres" % stem
        files.write_bytes(self.path("%s/%s" % (self.target.name, rel)), resource.text(body).encode("utf-8"))
        self.rep.warnings += self._warnings(spec)
        self.rep.materials.append(spec.material.name)
        return rel
