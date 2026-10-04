# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reads a DaskToon material into a MaterialSpec: shader, values, texture sources, keywords, render state and
outline (spec 5). Nothing here writes files; the only data it may create is the <material>.Outline companion,
through project 1's sync_material."""

from dataclasses import dataclass, field

from . import node_maps

LIGHT_NODES = {
    'ShaderNodeShaderToRGB', 'ShaderNodeLayerWeight', 'ShaderNodeFresnel', 'ShaderNodeLightPath',
    'ShaderNodeAmbientOcclusion', 'ShaderNodeCameraData',
}
LIGHT_OUTPUTS = {
    'ShaderNodeNewGeometry': {"Incoming", "Backfacing"},
    'ShaderNodeTexCoord': {"Window", "Camera", "Reflection"},
}
DASKTOON_PREFIXES = ("ShaderNodeAnime", "ShaderNodeDask", "ShaderNodeManga", "ShaderNodeArtist")
UV_NORMAL = "DT_OutlineN"
UV_MASK = "DT_OutlineW"
OUTLINE_PASS = "SRPDefaultUnlit"
MAX_UNITY_UV = 8


@dataclass
class TexSource:
    kind: str             # 'IMAGE' (copy the file), 'NORMAL' (copy as a normal map) or 'BAKE'
    color: bool           # colour data (sRGB) or numbers
    tree_owner: object    # material whose node tree holds the branch
    node: str             # node whose input is exported
    socket: str           # identifier of that input
    value: object = None  # the input's own value, restored when no texture can be written
    value_prop: str = ""  # Unity property of that value
    flag_prop: str = ""   # Unity float that switches the texture on
    image: object = None


@dataclass
class MaterialSpec:
    material: object
    shader: str
    floats: dict = field(default_factory=dict)
    colors: dict = field(default_factory=dict)
    textures: dict = field(default_factory=dict)
    keywords: set = field(default_factory=set)
    queue: int = -1
    render_type: str = "Opaque"
    disabled_passes: list = field(default_factory=list)
    ramp: object = None
    outline: bool = False
    warnings: list = field(default_factory=list)


def _socket(collection, identifier):
    return next((s for s in collection if s.identifier == identifier), None)


def follow(socket):
    """The output socket feeding `socket`, walking through Reroutes; None when unlinked or muted."""
    for _ in range(64):
        if socket is None or not socket.is_linked:
            return None
        link = socket.links[0]
        if link.is_muted or not link.is_valid:
            return None
        if link.from_node.bl_idname != 'NodeReroute':
            return link.from_socket
        socket = link.from_node.inputs[0]
    return None


def is_outline_companion(mat):
    """True for the <material>.Outline companions of project 1: a parameter source, never exported."""
    from bl_ui import dasktoon_outline as outline
    import bpy
    return any(m.get(outline.OUTLINE_MAT_PROP) == mat for m in bpy.data.materials if m != mat)


def _is_dasktoon(idname):
    return idname.startswith(DASKTOON_PREFIXES)


def _node_reason(node, out):
    if out.type == 'SHADER':
        return "nhánh chứa shader (%s)" % node.name
    if node.bl_idname in LIGHT_NODES or _is_dasktoon(node.bl_idname):
        return "nhánh phụ thuộc ánh sáng hoặc góc nhìn (%s)" % node.name
    if out.name in LIGHT_OUTPUTS.get(node.bl_idname, ()):
        return "nhánh phụ thuộc góc nhìn (%s › %s)" % (node.name, out.name)
    if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
        return _group_reason(node.node_tree, set())
    return None


def _group_reason(tree, seen):
    if tree.as_pointer() in seen:
        return None
    seen.add(tree.as_pointer())
    for node in tree.nodes:
        linked = [o for o in node.outputs if o.is_linked]
        if (node.bl_idname in LIGHT_NODES or _is_dasktoon(node.bl_idname) or any(o.type == 'SHADER' for o in linked)
                or any(o.name in LIGHT_OUTPUTS.get(node.bl_idname, ()) for o in linked)):
            return "node group %s phụ thuộc ánh sáng hoặc góc nhìn" % tree.name
        if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
            reason = _group_reason(node.node_tree, seen)
            if reason:
                return reason
    return None


def light_dependency(src):
    """Why the branch ending at output socket `src` cannot be baked, or None (spec 5, input sources)."""
    seen = set()
    stack = [src]
    while stack:
        out = stack.pop()
        reason = _node_reason(out.node, out)
        if reason:
            return reason
        if out.node.as_pointer() in seen:
            continue
        seen.add(out.node.as_pointer())
        for inp in out.node.inputs:
            if inp.enabled:
                upstream = follow(inp)
                if upstream is not None:
                    stack.append(upstream)
    return None


def _first_uv_ok(meshes, uv_name=None):
    """Unity samples uv0 = the first UV map. A node with no UV name uses the render-active map."""
    for mesh in meshes:
        if not mesh.uv_layers:
            return False
        first = mesh.uv_layers[0]
        if (uv_name is None and not first.active_render) or (uv_name is not None and uv_name != first.name):
            return False
    return True


def _direct_image(tex_node, meshes):
    image = tex_node.image
    if image is None or image.source != 'FILE' or tex_node.projection != 'FLAT':
        return False
    vector = follow(tex_node.inputs["Vector"])
    if vector is None:
        return _first_uv_ok(meshes)
    if vector.node.bl_idname == 'ShaderNodeUVMap':
        return _first_uv_ok(meshes, vector.node.uv_map or None)
    if vector.node.bl_idname == 'ShaderNodeTexCoord' and vector.identifier == "UV":
        return _first_uv_ok(meshes)
    return False


def _is_srgb(image):
    return image.colorspace_settings.name == 'sRGB'


def _texture_source(owner, node, sock, src, im, meshes):
    """A TexSource for an input's link, or the reason the link cannot reach Unity."""
    reason = light_dependency(src)
    if reason:
        return reason
    is_color = im.kind == 'COLOR'
    value = tuple(sock.default_value) if is_color else float(sock.default_value)
    tex_node = src.node
    if tex_node.bl_idname == 'ShaderNodeTexImage' and src.identifier == "Color" and _direct_image(tex_node, meshes):
        return TexSource('IMAGE', _is_srgb(tex_node.image), owner, node.name, sock.identifier, value, im.prop,
                         im.flag_prop, tex_node.image)
    return TexSource('BAKE', is_color, owner, node.name, sock.identifier, value, im.prop, im.flag_prop)


def _set_value(spec, im, value):
    if im.kind == 'COLOR':
        spec.colors[im.prop] = tuple(float(v) for v in value)
    else:
        spec.floats[im.prop] = float(value)


def _read_input(owner, node, im, spec, meshes):
    # Lookup by name skips unavailable sockets; iterate so a module that is off still keeps its values.
    sock = next((s for s in node.inputs if s.name == im.socket), None)
    if sock is None:
        return
    _set_value(spec, im, sock.default_value)
    if not sock.enabled:
        return
    src = follow(sock)
    if src is None:
        return
    label = "%s › %s" % (owner.name, im.socket)
    if not im.map_prop:
        spec.warnings.append("%s: input này không nhận texture trong Unity; dùng giá trị đang đặt" % label)
        return
    tex = _texture_source(owner, node, sock, src, im, meshes)
    if isinstance(tex, str):
        spec.warnings.append("%s: %s; dùng giá trị đang đặt" % (label, tex))
        return
    spec.textures[im.map_prop] = tex
    spec.floats[im.flag_prop] = 1.0
    _set_value(spec, im, (1.0, 1.0, 1.0, 1.0) if im.kind == 'COLOR' else 1.0)


def _normal_map(owner, node, spec, meshes):
    sock = node.inputs.get("Normal")
    src = follow(sock) if sock is not None and sock.enabled else None
    if src is None:
        return
    normal_map = src.node
    if (normal_map.bl_idname == 'ShaderNodeNormalMap' and normal_map.space == 'TANGENT'
            and _first_uv_ok(meshes, normal_map.uv_map or None)):
        color = follow(normal_map.inputs["Color"])
        if (color is not None and color.node.bl_idname == 'ShaderNodeTexImage' and color.identifier == "Color"
                and _direct_image(color.node, meshes)):
            strength = normal_map.inputs["Strength"]
            spec.textures["_DT_NormalMap"] = TexSource('NORMAL', False, owner, normal_map.name, "Color",
                                                       image=color.node.image)
            spec.floats["_DT_NormalStrength"] = float(strength.default_value)
            spec.keywords.add("_DT_NORMALMAP")
            if strength.is_linked:
                spec.warnings.append("%s › Normal Map: Strength có nối node; dùng giá trị đang đặt" % owner.name)
            return
    spec.warnings.append("%s › Normal: chỉ hỗ trợ Normal Map (Tangent) nối từ Image Texture; dùng normal của mesh"
                         % owner.name)


def _eye_uv(owner, node, spec):
    src = follow(node.inputs["UV Vector"])
    spec.floats["_DT_EyeUseUV"] = 0.0 if src is None else 1.0
    if src is None:
        return
    is_uv = ((src.node.bl_idname == 'ShaderNodeTexCoord' and src.identifier == "UV")
             or src.node.bl_idname == 'ShaderNodeUVMap')
    if not is_uv:
        spec.warnings.append("%s › UV Vector: chỉ hỗ trợ UV map đầu tiên; Unity dùng uv0" % owner.name)


def _node_inputs(owner, node, spec, meshes):
    nmap = node_maps.NODE_MAPS[node.bl_idname]
    for im in nmap.inputs:
        _read_input(owner, node, im, spec, meshes)
    for prop, unity in nmap.enums:
        spec.floats[unity] = float(node.bl_rna.properties[prop].enum_items[getattr(node, prop)].value)
    for prop, keyword in nmap.modules:
        if getattr(node, prop):
            spec.keywords.add(keyword)
    if nmap.ramp and node.shading_mode == 'RAMP':
        spec.keywords.add("_DT_RAMP")
        spec.ramp = node.shading_ramp
        spec.floats["_DT_RampConstant"] = 1.0 if node.shading_ramp.interpolation == 'CONSTANT' else 0.0
    if nmap.normal:
        _normal_map(owner, node, spec, meshes)
    if node.bl_idname == 'ShaderNodeAnimeEye':
        _eye_uv(owner, node, spec)
    if node.bl_idname == 'ShaderNodeAnimeCel':
        spec.floats["_DT_EmissionStrength"] = 1.0


def _hair_parts(emission):
    """Emission(Color <- Mix[RGBA, ADD](A <- AnimeCel.Color, B <- AngelRing.Color, Factor <- AngelRing.Fac))."""
    color = follow(emission.inputs["Color"])
    if color is None:
        return None
    mix = color.node
    if mix.bl_idname == 'ShaderNodeMix' and mix.data_type == 'RGBA' and mix.blend_type == 'ADD':
        a, b = _socket(mix.inputs, "A_Color"), _socket(mix.inputs, "B_Color")
        fac = _socket(mix.inputs, "Factor_Float")
        clamp_factor, clamp_result = mix.clamp_factor, mix.clamp_result
    elif mix.bl_idname == 'ShaderNodeMixRGB' and mix.blend_type == 'ADD':
        a, b, fac = mix.inputs["Color1"], mix.inputs["Color2"], mix.inputs["Fac"]
        clamp_factor, clamp_result = True, mix.use_clamp
    else:
        return None
    cel_out, ring_out, fac_out = follow(a), follow(b), follow(fac)
    if cel_out is None or ring_out is None or fac_out is None:
        return None
    cel, ring = cel_out.node, ring_out.node
    if cel.bl_idname != 'ShaderNodeAnimeCel' or cel_out.identifier != "Color":
        return None
    if ring.bl_idname != 'ShaderNodeAnimeAngelRing' or ring_out.identifier != "Color":
        return None
    if fac_out.node != ring or fac_out.identifier != "Fac":
        return None
    return cel, ring, clamp_factor, clamp_result


def _hair(mat, emission, parts, spec, meshes):
    cel, ring, clamp_factor, clamp_result = parts
    _node_inputs(mat, cel, spec, meshes)
    for im in node_maps.ANGEL_RING_INPUTS:
        _read_input(mat, ring, im, spec, meshes)
    spec.keywords.add("_DT_ANGEL_RING")
    spec.floats["_DT_RingClampFactor"] = 1.0 if clamp_factor else 0.0
    spec.floats["_DT_RingClampResult"] = 1.0 if clamp_result else 0.0
    # EEVEE also evaluates the closures of nodes whose BSDF output is unused, scaled by their hidden Weight socket:
    # with the HAIR preset the Anime Cel adds its colour once more (Weight 1). Unity reproduces what DaskToon shows.
    for node, prop in ((cel, "_DT_CelSelfEmission"), (ring, "_DT_RingSelfEmission")):
        weight = next((s for s in node.inputs if s.name == "Weight"), None)
        spec.floats[prop] = float(weight.default_value) if weight is not None and not weight.is_linked else 0.0
    strength = emission.inputs["Strength"]
    spec.floats["_DT_EmissionStrength"] = float(strength.default_value)
    if strength.is_linked:
        spec.warnings.append("%s › Emission Strength: có nối node; dùng giá trị đang đặt" % mat.name)
    if ring.inputs["Normal"].is_linked:
        spec.warnings.append("%s › Angel Ring › Normal: Unity dùng normal của bề mặt" % mat.name)


def _render_state(mat, spec):
    """Spec 5, material settings: BLENDED -> Transparent; DITHERED with alpha -> alpha clip; backface culling -> Cull."""
    has_alpha = spec.shader == "AnimeBSDF"
    spec.floats["_Cutoff"] = 0.5
    spec.floats["_Cull"] = 2.0 if mat.use_backface_culling else 0.0
    if has_alpha and mat.surface_render_method == 'BLENDED':
        spec.queue = 3000
        spec.render_type = "Transparent"
        spec.floats.update({"_Surface": 1.0, "_SrcBlend": 5.0, "_DstBlend": 10.0, "_ZWrite": 0.0})
        return
    spec.floats.update({"_Surface": 0.0, "_SrcBlend": 1.0, "_DstBlend": 0.0, "_ZWrite": 1.0})
    if has_alpha and ("_DT_AlphaMap" in spec.textures or spec.floats.get("_DT_Alpha", 1.0) < 1.0):
        spec.keywords.add("_DT_ALPHATEST_ON")
        spec.render_type = "TransparentCutout"


def _outline_channels(mat, spec, meshes):
    pairs = []
    for mesh in meshes:
        n, w = mesh.uv_layers.find(UV_NORMAL), mesh.uv_layers.find(UV_MASK)
        pairs.append((n if n < MAX_UNITY_UV else -1, w if w < MAX_UNITY_UV else -1))
    first = pairs[0] if pairs else (-1, -1)
    if any(pair != first for pair in pairs):
        spec.warnings.append("%s: các mesh dùng material này có thứ tự UV khác nhau; Unity dùng thứ tự của %s"
                             % (mat.name, meshes[0].name))
    if first[0] < 0:
        spec.warnings.append("%s: mesh chưa có %s (hoặc vượt 8 UV map); outline trong Unity đẩy theo normal của mesh"
                             % (mat.name, UV_NORMAL))
    spec.floats["_DT_OutlineUV"] = float(first[0])
    spec.floats["_DT_OutlineWUV"] = float(first[1])


def _outline(mat, spec, meshes):
    from bl_ui import dasktoon_outline as outline
    source = outline.find_source(mat)
    dask = None
    if source is not None:
        outline.sync_material(mat)
        companion = outline.outline_material_for(mat)
        dask = outline.outline_node(companion)
        if dask is None:
            spec.warnings.append("%s: %s thiếu node Dask Outline; tắt outline" % (mat.name, companion.name))
    if dask is None:
        spec.disabled_passes.append(OUTLINE_PASS)
        return
    for im in node_maps.OUTLINE_INPUTS:
        _read_input(companion, dask, im, spec, meshes)
    spec.floats["_DT_OutlineLightBleed"] = outline.LIGHT_BLEED
    spec.floats["_DT_OutlineWobble"] = outline.HAND_WOBBLE
    main = source[1]
    if main is not None:
        spec.floats["_DT_OutlineWidth"] = float(main.inputs["Outline Width"].default_value)
    spec.floats["_DT_OutlineTintMode"] = float(dask.bl_rna.properties["tint_mode"].enum_items[dask.tint_mode].value)
    spec.keywords.add("_DT_OUTLINE")
    spec.outline = True
    _outline_channels(mat, spec, meshes)


def _toggles(spec):
    for keyword in node_maps.SHADER_KEYWORDS[spec.shader]:
        spec.floats[node_maps.KEYWORD_TOGGLES[keyword]] = 1.0 if keyword in spec.keywords else 0.0


def _surface(mat):
    tree = mat.node_tree
    output = tree.get_output_node('EEVEE') if tree is not None else None
    return follow(output.inputs["Surface"]) if output is not None else None


def analyze_material(mat, meshes):
    """(MaterialSpec, "") for a supported material, or (None, reason). `meshes` are the meshes using it."""
    if mat is None:
        return None, "slot trống"
    source = _surface(mat)
    if source is None:
        return None, "Material Output › Surface không nối với node nào"
    node = source.node
    spec = None
    if node.bl_idname in node_maps.NODE_MAPS and source.identifier == "BSDF":
        spec = MaterialSpec(mat, node_maps.NODE_MAPS[node.bl_idname].shader)
        _node_inputs(mat, node, spec, meshes)
    elif node.bl_idname == 'ShaderNodeEmission':
        parts = _hair_parts(node)
        if parts is not None:
            spec = MaterialSpec(mat, "AnimeCel")
            _hair(mat, node, parts, spec, meshes)
    if spec is None:
        return None, "mẫu node chưa được hỗ trợ (%s)" % node.bl_idname
    _render_state(mat, spec)
    _outline(mat, spec, meshes)
    _toggles(spec)
    return spec, ""
