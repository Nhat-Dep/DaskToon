# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon Engine Export: model, materials and shaders for game engines.
Design: docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md"""

from dataclasses import dataclass

from . import report  # noqa: F401  (re-exported for callers: dasktoon_export.report)

_FORBIDDEN = '<>:"/\\|?*'


@dataclass
class ExportOptions:
    model_format: str = 'FBX'       # 'FBX' or 'NONE'
    include_animation: bool = True
    export_materials: bool = True
    bake_size: int = 1024
    bake_samples: int = 16


def safe_name(name):
    """A file name that Windows and Unity accept, as close to the material name as possible."""
    cleaned = "".join("_" if c in _FORBIDDEN or ord(c) < 32 else c for c in name).strip().rstrip(".")
    return cleaned or "Material"


def _tex_label(prop):
    label = prop[len("_DT_"):] if prop.startswith("_DT_") else prop.lstrip("_")
    return label[:-3] if label.endswith("Map") else label


def _materials(objects):
    """{material: [mesh objects using it]} in slot order; empty slots and outline companions are left out."""
    from . import graph
    found = {}
    for obj in objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or graph.is_outline_companion(mat):
                continue
            users = found.setdefault(mat, [])
            if obj not in users:
                users.append(obj)
    return found


def _drop_texture(spec, prop, src):
    """The texture could not be written: Unity falls back to the input's own value."""
    spec.textures.pop(prop, None)
    if src.kind == 'NORMAL':
        spec.keywords.discard("_DT_NORMALMAP")
        spec.floats["_DT_UseNormalMap"] = 0.0
        return
    spec.floats[src.flag_prop] = 0.0
    if isinstance(src.value, tuple):
        spec.colors[src.value_prop] = src.value
    else:
        spec.floats[src.value_prop] = src.value


class _Writer:
    """Writes one model's materials and textures under target.root (spec 4 layout)."""

    def __init__(self, target, options, rep):
        from . import assets, unity_yaml
        self.target, self.options, self.rep = target, options, rep
        self.assets, self.yaml = assets, unity_yaml
        self.written = {}   # (image pointer, kind) -> texture GUID, so a shared image is written once
        self.stems = set()

    def guid(self, relpath):
        return self.yaml.guid_for(self.target.name, relpath)

    def folder(self, relpath):
        self.assets.ensure_folder(self.target.root, relpath, self.guid(relpath))

    def unique_stem(self, mat):
        stem = base = safe_name(mat.name)
        index = 2
        while stem.lower() in self.stems:
            stem = "%s_%d" % (base, index)
            index += 1
        self.stems.add(stem.lower())
        return stem

    def texture(self, spec, stem, prop, src, users):
        from . import bake, textures
        name = self.target.name
        if src.kind in ('IMAGE', 'NORMAL'):
            key = (src.image.as_pointer(), src.kind, src.color)
            if key in self.written:
                return self.written[key]
            found = textures.image_file(src.image)
            if found is not None:
                ext, data = found
                kind = 'NORMAL' if src.kind == 'NORMAL' else ('COLOR' if src.color and ext not in (".exr", ".hdr")
                                                              else 'DATA')
                rel = "%s/Textures/%s_%s%s" % (name, stem, _tex_label(prop), ext)
                guid = self.guid(rel)
                meta = self.yaml.texture_meta(guid, kind, tuple(src.image.size))
                if not self.assets.write_asset(self.target.root, rel, guid, meta, self.rep.warnings, data=data):
                    return None
                self.written[key] = guid
                return guid
            if src.kind == 'NORMAL':
                self.rep.warnings.append("%s: không đọc được ảnh normal map %s; bỏ normal map"
                                         % (spec.material.name, src.image.name))
                return None
        size = bake.branch_size(src.tree_owner, src.node, src.socket, self.options.bake_size)
        try:
            pixels = bake.bake_input(users[0], spec.material, src, size, self.options.bake_samples)
        except Exception as ex:  # A failed bake must not stop the export; the input keeps its value.
            self.rep.warnings.append("%s › %s: bake lỗi (%s); dùng giá trị đang đặt" % (spec.material.name, src.socket, ex))
            return None
        if textures.needs_float(pixels):
            ext, data, kind = ".exr", textures.exr_bytes(pixels, size, size), 'DATA'
        else:
            ext, kind = ".png", ('COLOR' if src.color else 'DATA')
            data = textures.float_to_png(pixels, size, size, src.color)
        rel = "%s/Textures/%s_%s%s" % (name, stem, _tex_label(prop), ext)
        guid = self.guid(rel)
        if not self.assets.write_asset(self.target.root, rel, guid, self.yaml.texture_meta(guid, kind, (size, size)),
                                       self.rep.warnings, data=data):
            return None
        self.rep.baked.append("%s › %s" % (spec.material.name, src.socket))
        if len(users) > 1:
            self.rep.warnings.append("%s › %s: bake trên mesh của %s, các mesh khác dùng chung texture này"
                                     % (spec.material.name, src.socket, users[0].name))
        return guid

    def material(self, spec, users):
        from . import shaders_install, textures
        name = self.target.name
        stem = self.unique_stem(spec.material)
        tex_guids = {}
        if spec.textures:
            self.folder(name + "/Textures")
        for prop, src in sorted(spec.textures.items()):
            guid = self.texture(spec, stem, prop, src, users)
            if guid is None:
                _drop_texture(spec, prop, src)
            else:
                tex_guids[prop] = guid
        if spec.ramp is not None:
            self.folder(name + "/Textures")
            rel = "%s/Textures/%s_Ramp.png" % (name, stem)
            guid = self.guid(rel)
            point = spec.floats.get("_DT_RampConstant", 0.0) > 0.5
            meta = self.yaml.texture_meta(guid, 'RAMP', (textures.RAMP_WIDTH, 1), point_filter=point)
            if self.assets.write_asset(self.target.root, rel, guid, meta, self.rep.warnings,
                                       data=textures.ramp_png(spec.ramp)):
                tex_guids["_DT_RampMap"] = guid
        self.folder(name + "/Materials")
        rel = "%s/Materials/%s.mat" % (name, stem)
        guid = self.guid(rel)
        text = self.yaml.material_yaml(stem, shaders_install.shader_guid(spec.shader), spec.keywords, spec.queue,
                                       spec.render_type, spec.disabled_passes, spec.floats, spec.colors, tex_guids)
        self.rep.warnings += spec.warnings
        if not self.assets.write_asset(self.target.root, rel, guid, self.yaml.material_meta(guid), self.rep.warnings,
                                       data=text.encode("utf-8")):
            return None
        self.rep.materials.append(spec.material.name)
        return guid


def export_model(context, target, objects, options):
    """Write `objects` (FBX), their DaskToon materials and the shaders to `target` (spec 3-5). Returns a Report."""
    from . import assets, graph, model_fbx, shaders_install, targets, unity_yaml
    if target.engine not in targets.SUPPORTED_ENGINES:
        raise ValueError("Engine %s chưa được hỗ trợ" % target.engine)
    rep = report.Report(mode=target.mode, root=target.root, name=target.name)
    meshes = [o for o in objects if o.type == 'MESH']
    rep.outline_meshes, errors = model_fbx.prepare_outline_data(meshes)
    rep.warnings += errors
    rep.modifier_notes = model_fbx.modifier_notes(meshes)
    shaders_install.ensure_root(target)
    writer = _Writer(target, options, rep)
    writer.folder(target.name)
    mat_guids = {}
    if options.export_materials:
        rep.shaders = 'INSTALLED' if shaders_install.install_shaders(target, rep.warnings) else 'UP_TO_DATE'
        for mat, users in _materials(meshes).items():
            mesh_data = list(dict.fromkeys(o.data for o in users))
            spec, reason = graph.analyze_material(mat, mesh_data)
            if spec is None:
                rep.skipped.append((mat.name, reason))
                continue
            guid = writer.material(spec, users)
            if guid is not None:
                mat_guids[mat.name] = guid
    if options.model_format == 'FBX':
        model_dir = target.name + "/Model"
        writer.folder(model_dir)
        rel = "%s/%s.fbx" % (model_dir, safe_name(target.name))
        guid = writer.guid(rel)
        meta = unity_yaml.model_meta(guid, mat_guids, options.include_animation)
        if assets.write_asset(target.root, rel, guid, meta, rep.warnings,
                              writer=lambda path: model_fbx.write_fbx(context, objects, path, options.include_animation)):
            rep.model = rel
    rep.light_hint = report.light_hint(context.scene)
    rep.ambient_hint = report.ambient_hint(context.scene)
    if target.mode == 'FOLDER':
        guid = writer.guid("README.txt")
        assets.write_asset(target.root, "README.txt", guid, unity_yaml.text_meta(guid), rep.warnings,
                           data=report.readme_text(rep).encode("utf-8"))
    report.write_text(rep)
    return rep
