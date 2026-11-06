# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unreal models: the .uemodel files FModel writes (the UEFormat layout, github.com/h4lfheart/UEFormat docs), read by
DaskToon itself, since the UEFormat plugin carries no licence to ship it.

A file is a header ("UEFORMAT", the kind "UEMODEL", a version byte, the object's name, then the body, maybe GZIP or
ZSTD compressed) and sections. Before version 10 a section is (name, count, byte size, data) and the sections follow
one another to the end; from version 10 a set is (count, then (name, byte size, data) each). The model has LODS (each
with VERTICES, NORMALS, TEXCOORDS, INDICES, VERTEXCOLORS, MATERIALS, WEIGHTS, MORPHTARGETS), a SKELETON (BONES) and
COLLISION. Unreal works in centimetres; from version 8 the file keeps Unreal's left-handed axes, so Y is mirrored (and
the bones' rotations with it) and the UVs turned upside down, as Blender has them.

Only the most detailed level (LOD0) is made: one mesh with its UV maps, colour layers, custom normals, materials, shape
keys and vertex groups, bound to an armature of the skeleton. Each material gets its diffuse texture when FModel wrote
the material's description (Materials/<name>.json) and the image is found beside the model."""

import gzip
import json
import os
import struct

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

MAGIC = b"UEFORMAT"
MODEL = "UEMODEL"
LOD_RESTRUCTURE = 4  # versions: LODS appear; before, the one level's sections were at the root
MATERIAL_PATH = 6  # a material has its path
KEEPS_UNREAL_AXES = 8  # positions, rotations and UVs as Unreal has them
ATTRIBUTE_SETS = 10  # sections become sets
LATEST = 10
IMAGE_EXTENSIONS = (".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".exr", ".dds")
# Material parameters holding the colour texture, most telling first (Wuthering Waves: MainTex, PM_Diffuse).
DIFFUSE_KEYS = ("maintex", "pm_diffuse", "diffuse", "basecolor", "base color", "basecolortexture", "albedo", "texture",
                "diffusetexture", "colortexture")

WEIGHT = np.dtype([("bone", "<u2"), ("vertex", "<i4"), ("weight", "<f4")])
MORPH_DELTA = np.dtype([("position", "<f4", 3), ("normal", "<f4", 3), ("vertex", "<u4")])


class FormatError(Exception):
    """The file cannot be read, worded for the user."""


class Reader:
    def __init__(self, data, version=0):
        self.data = data
        self.pos = 0
        self.end = len(data)
        self.version = version

    def at_end(self):
        return self.pos >= self.end

    def take(self, size):
        if size < 0 or self.pos + size > self.end:
            raise FormatError(rpt_("The file ends too early: it is cut short or not a .uemodel"))
        out = self.data[self.pos:self.pos + size]
        self.pos += size
        return out

    def sub(self, size):
        """A reader over the next `size` bytes, which this one skips."""
        return Reader(self.take(size), self.version)

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def u8(self):
        return self.take(1)[0]

    def string(self):
        size = self.i32()
        return bytes(self.take(size)).rstrip(b"\x00").decode("utf-8", "replace")

    def array(self, dtype, count):
        dtype = np.dtype(dtype)
        return np.frombuffer(self.take(dtype.itemsize * count), dtype).copy()


class Lod:
    def __init__(self, name):
        self.name = name
        self.vertices = np.zeros((0, 3))
        self.normals = None
        self.indices = np.zeros((0, 3), np.int64)
        self.uvs = []
        self.colors = []  # (name, n x 4 floats 0..1)
        self.materials = []  # (name, path, first index, face count)
        self.weights = np.zeros(0, WEIGHT)
        self.morphs = []  # (name, deltas of MORPH_DELTA)


class Bone:
    def __init__(self, name, parent, position, rotation, scale):
        self.name, self.parent = name, parent
        self.position, self.rotation, self.scale = position, rotation, scale  # rotation x, y, z, w


class Model:
    def __init__(self, name, version):
        self.name, self.version = name, version
        self.lods = []
        self.bones = []


def read_header(data):
    """(kind, version, object name, body reader)."""
    ar = Reader(memoryview(data))
    if bytes(ar.take(len(MAGIC))) != MAGIC:
        raise FormatError(rpt_("Not a UEFormat file (.uemodel)"))
    kind = ar.string()
    version = ar.u8()
    if version > LATEST:
        raise FormatError(rpt_("This .uemodel is version %d; DaskToon reads versions up to %d") % (version, LATEST))
    name = ar.string()
    if version >= ATTRIBUTE_SETS:
        ar.string()  # the object's path in the game
    if ar.u8():
        method = ar.string()
        _full = ar.i32()
        _packed = ar.i32()
        rest = bytes(ar.take(ar.end - ar.pos))
        if method == "GZIP":
            body = Reader(memoryview(gzip.decompress(rest)), version)
        else:
            raise FormatError(rpt_("This .uemodel is compressed with %s, which DaskToon cannot read: export it "
                                  "from FModel without compression") % method)
    else:
        body = Reader(ar.data[ar.pos:], version)
        body.version = version
    return kind, version, name, body


def _chunks(ar):
    """(name, count, reader) of the sections before version 10."""
    while not ar.at_end():
        name = ar.string()
        count = ar.i32()
        size = ar.i32()
        yield name, count, ar.sub(size)


def _attributes(ar):
    """(name, reader) of a set from version 10."""
    for _ in range(ar.i32()):
        name = ar.string()
        size = ar.i32()
        yield name, ar.sub(size)


def _counted(ar, count):
    """The count of an array: given by the section before version 10, written before the items from it."""
    return ar.i32() if count is None else count


def _lod_section(lod, name, ar, count):
    """One section of a level; `count` is None from version 10 (the payload starts with it)."""
    version = ar.version
    if name == "VERTICES":
        lod.vertices = ar.array("<f4", _counted(ar, count) * 3).reshape(-1, 3).astype(float)
    elif name == "NORMALS":
        n = _counted(ar, count)
        if version >= 1:  # binormal sign, then the normal
            lod.normals = ar.array("<f4", n * 4).reshape(-1, 4)[:, 1:].astype(float)
        else:
            lod.normals = ar.array("<f4", n * 3).reshape(-1, 3).astype(float)
    elif name == "INDICES":
        lod.indices = ar.array("<u4", _counted(ar, count)).astype(np.int64).reshape(-1, 3)
    elif name == "TEXCOORDS":
        for _ in range(_counted(ar, count)):
            if count is None:
                ar.string()  # the map's name
            lod.uvs.append(ar.array("<f4", ar.i32() * 2).reshape(-1, 2).astype(float))
    elif name == "VERTEXCOLORS":
        if version < 2:
            lod.colors.append(("COL0", ar.array("u1", count * 4).reshape(-1, 4) / 255.0))
        else:
            for _ in range(_counted(ar, count)):
                layer = ar.string()
                lod.colors.append((layer, ar.array("u1", ar.i32() * 4).reshape(-1, 4) / 255.0))
    elif name == "MATERIALS":
        for _ in range(_counted(ar, count)):
            material = ar.string()
            path = ar.string() if version >= MATERIAL_PATH else ""
            lod.materials.append((material, path, ar.i32(), ar.i32()))
    elif name == "WEIGHTS":
        lod.weights = ar.array(WEIGHT, _counted(ar, count))
    elif name == "MORPHTARGETS":
        for _ in range(_counted(ar, count)):
            morph = ar.string()
            lod.morphs.append((morph, ar.array(MORPH_DELTA, ar.i32())))


def _bones(ar, count):
    out = []
    for _ in range(_counted(ar, count)):
        name = ar.string()
        parent = ar.i32()
        position = ar.array("<f4", 3).astype(float)
        rotation = ar.array("<f4", 4).astype(float)
        scale = ar.array("<f4", 3).astype(float) if ar.version >= ATTRIBUTE_SETS else np.ones(3)
        out.append(Bone(name, parent, position, rotation, scale))
    return out


def read_model(data):
    """The Model in `data` (the file's bytes), in Unreal's units and axes."""
    kind, version, name, ar = read_header(data)
    if kind != MODEL:
        raise FormatError(rpt_("This UEFormat file holds %s, not a model") % (kind or "?"))
    model = Model(name, version)
    if version >= ATTRIBUTE_SETS:
        for section, payload in _attributes(ar):
            if section == "LODS":
                for _ in range(payload.i32()):
                    lod = Lod(payload.string())
                    for part, part_ar in _attributes(payload):
                        _lod_section(lod, part, part_ar, None)
                    model.lods.append(lod)
            elif section == "SKELETON":
                for part, part_ar in _attributes(payload):
                    if part == "BONES":
                        model.bones = _bones(part_ar, None)
        return model
    if version < LOD_RESTRUCTURE:  # one level, its sections and the bones at the root
        lod = Lod("LOD0")
        for section, count, payload in _chunks(ar):
            if section == "BONES":
                model.bones = _bones(payload, count)
            else:
                _lod_section(lod, section, payload, count)
        model.lods.append(lod)
        return model
    for section, count, payload in _chunks(ar):
        if section == "LODS":
            for _ in range(count):
                lod = Lod(payload.string())
                for part, part_count, part_ar in _chunks(payload.sub(payload.i32())):
                    _lod_section(lod, part, part_ar, part_count)
                model.lods.append(lod)
        elif section == "SKELETON":
            for part, part_count, part_ar in _chunks(payload):
                if part == "BONES":
                    model.bones = _bones(part_ar, part_count)
    return model


def to_blender(model, scale=0.01):
    """`model` in metres (times `scale`) and in Blender's axes, in place."""
    mirror = model.version >= KEEPS_UNREAL_AXES
    flip = np.array((1.0, -1.0, 1.0)) if mirror else np.ones(3)
    for lod in model.lods:
        lod.vertices = lod.vertices * scale * flip
        if lod.normals is not None:
            lod.normals = lod.normals * flip
        if mirror:
            lod.uvs = [uv * (1.0, -1.0) + (0.0, 1.0) for uv in lod.uvs]
        for _name, deltas in lod.morphs:
            deltas["position"] = deltas["position"] * scale * flip
    for bone in model.bones:
        bone.position = bone.position * scale * flip
        if mirror:
            bone.rotation = bone.rotation * (1.0, -1.0, 1.0, -1.0)


# ------------------------------------------------------------------------------------------------- making the objects

def _mesh(lod, name):
    import bpy
    tris = lod.indices
    keep = (tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])
    face_material = np.zeros(len(tris), np.int64)
    for index, (_material, _path, first, count) in enumerate(lod.materials):
        start = first // 3
        face_material[start:start + count] = index
    tris, face_material = tris[keep], face_material[keep]  # a triangle using a vertex twice is no face in Blender
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(lod.vertices))
    mesh.vertices.foreach_set("co", lod.vertices.astype(np.float32).ravel())
    mesh.loops.add(tris.size)
    mesh.loops.foreach_set("vertex_index", tris.astype(np.int32).ravel())
    mesh.polygons.add(len(tris))
    mesh.polygons.foreach_set("loop_start", np.arange(0, tris.size, 3, dtype=np.int32))
    mesh.update(calc_edges=True)
    corners = tris.ravel()
    for index, uv in enumerate(lod.uvs):
        if len(uv) != len(lod.vertices):
            continue
        layer = mesh.uv_layers.new(name="UV%d" % index)
        layer.uv.foreach_set("vector", uv[corners].astype(np.float32).ravel())
    for layer_name, colors in lod.colors:
        if len(colors) != len(lod.vertices):
            continue
        layer = mesh.color_attributes.new(layer_name or "Color", 'BYTE_COLOR', 'POINT')
        layer.data.foreach_set("color", colors.astype(np.float32).ravel())
    if len(lod.materials):
        mesh.polygons.foreach_set("material_index", face_material.astype(np.int32))
    if lod.normals is not None and len(lod.normals) == len(lod.vertices):
        mesh.shade_smooth()
        normals = lod.normals / np.maximum(np.linalg.norm(lod.normals, axis=1), 1e-12)[:, None]
        mesh.normals_split_custom_set_from_vertices(normals.tolist())
    return mesh


def _shape_keys(obj, lod):
    if not lod.morphs:
        return
    base = lod.vertices.astype(np.float32)
    obj.shape_key_add(name="Basis", from_mix=False)
    count = len(base)
    for name, deltas in lod.morphs:
        block = obj.shape_key_add(name=name, from_mix=False)
        co = base.copy()
        inside = deltas["vertex"] < count
        np.add.at(co, deltas["vertex"][inside].astype(np.int64), deltas["position"][inside])
        block.data.foreach_set("co", co.ravel())


def _vertex_groups(obj, lod, bones):
    weights = lod.weights
    if not len(weights) or not bones:
        return
    weights = weights[(weights["bone"] < len(bones)) & (weights["vertex"] >= 0)
                      & (weights["vertex"] < len(lod.vertices)) & (weights["weight"] > 0.0)]
    for bone in np.unique(weights["bone"]):
        mine = weights[weights["bone"] == bone]
        group = obj.vertex_groups.get(bones[bone].name) or obj.vertex_groups.new(name=bones[bone].name)
        values = np.round(mine["weight"], 5)
        for value in np.unique(values):
            group.add(mine["vertex"][values == value].tolist(), float(value), 'ADD')


def _armature(context, model, name):
    """The armature of `model`'s bones: each bone from its joint to its child's (the middle of its children's), a
    bone without children going on as its parent does."""
    import bpy
    from mathutils import Matrix, Quaternion, Vector
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    context.collection.objects.link(rig)
    world = []
    for bone in model.bones:
        x, y, z, w = bone.rotation
        local = Matrix.LocRotScale(Vector(bone.position), Quaternion((w, x, y, z)), Vector(bone.scale))
        world.append(world[bone.parent] @ local if 0 <= bone.parent < len(world) else local)
    heads = [m.to_translation() for m in world]
    children = [[] for _ in model.bones]
    for index, bone in enumerate(model.bones):
        if 0 <= bone.parent < len(model.bones):
            children[bone.parent].append(index)
    span = max((max(h[k] for h in heads) - min(h[k] for h in heads) for k in range(3)), default=1.0) if heads else 1.0
    least = max(span * 0.005, 1e-4)
    previous = bpy.context.view_layer.objects.active
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        made = []
        tails = [None] * len(model.bones)
        for index, bone in enumerate(model.bones):
            edit = data.edit_bones.new(bone.name)
            head = heads[index]
            ahead = [heads[c] for c in children[index] if (heads[c] - head).length > least]
            if ahead:
                tail = sum(ahead, Vector()) / len(ahead)
                if (tail - head).length < least:
                    tail = ahead[0]
            elif 0 <= bone.parent < index and tails[bone.parent] is not None:
                parent_dir = tails[bone.parent] - heads[bone.parent]
                tail = head + parent_dir.normalized() * max(parent_dir.length * 0.5, least * 4)
            else:
                tail = head + Vector((0.0, 0.0, least * 10))
            edit.head, edit.tail = head, tail
            tails[index] = tail
            edit.align_roll(world[index].to_3x3() @ Vector((0.0, 0.0, 1.0)))
            if 0 <= bone.parent < index:
                edit.parent = made[bone.parent]
            made.append(edit)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = previous
    rig.show_in_front = True
    return rig


def _index_images(folder):
    """{lower-case file stem: path} of the images under `folder` and its parent (FModel puts Textures beside the
    model, or keeps the game's folders above it)."""
    out = {}
    seen = 0
    for root in (folder, os.path.dirname(folder)):
        for path, _dirs, files in os.walk(root):
            for name in files:
                stem, ext = os.path.splitext(name)
                if ext.lower() in IMAGE_EXTENSIONS:
                    out.setdefault(stem.lower(), os.path.join(path, name))
                seen += 1
            if seen > 20000:
                return out
    return out


def _texture_names(description):
    """The material's textures {parameter (lower case): texture name}, from FModel's material description."""
    textures = description.get("Textures") if isinstance(description, dict) else None
    out = {}
    if isinstance(textures, dict):
        for key, value in textures.items():
            if isinstance(value, str) and value:
                out[key.lower()] = value.rsplit("/", 1)[-1].split(".")[-1]
    return out


def diffuse_name(description):
    """The name of the colour texture a material description names, or None."""
    names = _texture_names(description)
    for key in DIFFUSE_KEYS:
        if key in names:
            return names[key]
    return next((n for n in names.values() if n.lower().endswith("_d")), None)


def _material(name, folder, images, cache):
    import bpy
    if name in cache:
        return cache[name]
    material = bpy.data.materials.new(name)
    cache[name] = material
    description = None
    path = os.path.join(folder, "Materials", name + ".json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as stream:
                description = json.load(stream)
        except (OSError, ValueError):
            description = None
    texture = diffuse_name(description) if description is not None else None
    image_path = images.get(texture.lower()) if texture else None
    if image_path is None:
        return material
    material.use_nodes = True
    tree = material.node_tree
    output = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None)
    surface = output.inputs["Surface"].links[0].from_node if output and output.inputs["Surface"].links else None
    socket = None
    if surface is not None:
        socket = surface.inputs.get("Base Color") or surface.inputs.get("Color")
    if socket is None:
        return material
    image = bpy.data.images.load(image_path, check_existing=True)
    node = tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    node.location = (surface.location.x - 360.0, surface.location.y)
    tree.links.new(node.outputs["Color"], socket)
    return material


def import_file(context, filepath, scale=0.01, shape_keys=True):
    """Import the .uemodel at `filepath`: (the armature or None, the mesh object). Raises FormatError."""
    import bpy
    with open(filepath, "rb") as stream:
        model = read_model(stream.read())
    if not model.lods or not len(model.lods[0].vertices):
        raise FormatError(rpt_("The .uemodel holds no mesh"))
    to_blender(model, scale)
    lod = model.lods[0]
    name = model.name or os.path.splitext(os.path.basename(filepath))[0]
    mesh = _mesh(lod, name)
    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)
    folder = os.path.dirname(os.path.abspath(filepath))
    images = _index_images(folder) if lod.materials else {}
    cache = {}
    for material_name, _path, _first, _count in lod.materials:
        mesh.materials.append(_material(material_name, folder, images, cache))
    if shape_keys:
        _shape_keys(obj, lod)
    rig = None
    if model.bones:
        rig = _armature(context, model, name + "_Rig")
        _vertex_groups(obj, lod, model.bones)
        obj.parent = rig
        modifier = obj.modifiers.new("Armature", 'ARMATURE')
        modifier.object = rig
    for other in context.view_layer.objects:
        other.select_set(other in (obj, rig))
    context.view_layer.objects.active = rig or obj
    return rig, obj
