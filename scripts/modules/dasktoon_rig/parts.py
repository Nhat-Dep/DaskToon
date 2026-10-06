# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Parts of a character (anime rig spec 5): the vertices of a part, its loose pieces, the role its name suggests and
the bones it hangs from. Positions are world space at rest: mesh coordinates without shape keys or modifiers."""

import re
import unicodedata

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import chains, skeleton

ROLES = ('BODY', 'CLOTHING', 'ACCESSORY', 'HAIR', 'SKIRT')  # a later role wins a vertex (spec 5.2)
CHAIN_ROLES = ('HAIR', 'SKIRT')
DEFAULT_BONE = {'HAIR': "Head", 'SKIRT': "Hips"}
BONE_COUNT = 4
DEFAULT_BONE_COUNT = {'SKIRT': 3}
CHAIN_COUNT = 8
WORDS = (
    ('HAIR', {"hair", "bang", "bangs", "fringe", "ponytail", "twintail", "twintails", "tail", "tails", "ahoge",
              "braid", "toc", "kami"}),
    ('SKIRT', {"skirt", "vay"}),
    ('ACCESSORY', {"eye", "eyes", "eyeball", "glass", "glasses", "ribbon", "hairpin", "clip", "earring", "hat",
                   "cap", "bow"}),
    ('CLOTHING', {"cloth", "clothes", "shirt", "tshirt", "jacket", "coat", "dress", "pant", "pants", "shoe",
                  "shoes", "sock", "socks", "glove", "gloves", "uniform"}),
    ('BODY', {"body", "skin", "face", "head"}),
)
MARKS = (('HAIR', "\u9aea"), ('SKIRT', "\u30b9\u30ab\u30fc\u30c8"), ('ACCESSORY', "\u76ee"), ('CLOTHING', "\u670d"),
         ('BODY', "\u4f53"))


class PartError(Exception):
    """Why a part cannot be used, worded for the user."""


class Part:
    """A part outside Blender data (tests, scripts); the interface passes DaskRigPart items with the same fields."""

    def __init__(self, name, obj, role='BODY', scope='OBJECT', material="", vertex_group="", bone="",
                 bone_count=None, chain_count=CHAIN_COUNT, stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03):
        self.name = name
        self.object = obj
        self.role = role
        self.scope = scope
        self.material = material
        self.vertex_group = vertex_group
        self.bone = bone
        self.bone_count = DEFAULT_BONE_COUNT.get(role, BONE_COUNT) if bone_count is None else bone_count
        self.chain_count = chain_count
        self.stiffness = stiffness
        self.gravity = gravity
        self.drag = drag
        self.radius = radius


def _plain(name):
    """`name` with accents dropped (the Vietnamese d with stroke becomes d)."""
    name = name.replace(chr(0x111), "d").replace(chr(0x110), "D")
    return "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))


def words(name):
    """Lower-case words of a name: split at anything but a letter and where lower case turns to upper case."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", _plain(name))
    return [w.lower() for w in re.split(r"[^A-Za-z]+", spaced) if w]


def ascii_name(name):
    """The ASCII letters and digits of a name (accents dropped), or "Part": the start of generated bone names."""
    return re.sub(r"[^A-Za-z0-9]+", "", _plain(name)) or "Part"


def guess_role(name):
    """The role a name suggests (spec 5.3), or None; the first role of WORDS that matches wins."""
    found = set(words(name))
    for role, keys in WORDS:
        if found & keys:
            return role
    for role, mark in MARKS:
        if mark in name:
            return role
    return None


def _height(obj):
    box = skeleton.bounds([obj])
    return box[1].z - box[0].z if box else 0.0


def initial_roles(objects, has_body=False):
    """{object: role} for new whole-object parts: the role the name suggests; otherwise the tallest object is the Body
    when the rig has none yet, and the rest Clothing (spec 5.3)."""
    roles = {obj: guess_role(obj.name) for obj in objects}
    if not has_body and 'BODY' not in roles.values():
        unknown = [obj for obj in objects if roles[obj] is None]
        if unknown:
            roles[max(unknown, key=_height)] = 'BODY'
    return {obj: role or 'CLOTHING' for obj, role in roles.items()}


def mesh_arrays(obj):
    """(world positions n x 3, edges m x 2) of the vertices of obj's mesh, without shape keys or modifiers."""
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", co)
    edges = np.empty(len(mesh.edges) * 2, np.int32)
    mesh.edges.foreach_get("vertices", edges)
    matrix = np.array(obj.matrix_world)
    world = co.reshape(-1, 3).astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
    return world, edges.reshape(-1, 2).astype(np.int64)


def part_vertices(part):
    """Sorted indices of the vertices of `part` on its mesh (spec 5.1); PartError when there is none."""
    obj = part.object
    mesh = obj.data
    if part.scope == 'MATERIAL':
        slots = [i for i, slot in enumerate(obj.material_slots)
                 if slot.material is not None and slot.material.name == part.material]
        if not slots:
            raise PartError(rpt_("Part %s: material %s is not on %s") % (part.name, part.material, obj.name))
        face_material = np.empty(len(mesh.polygons), np.int32)
        mesh.polygons.foreach_get("material_index", face_material)
        sizes = np.empty(len(mesh.polygons), np.int32)
        mesh.polygons.foreach_get("loop_total", sizes)
        corners = np.empty(len(mesh.loops), np.int32)
        mesh.loops.foreach_get("vertex_index", corners)
        found = np.unique(corners[np.repeat(np.isin(face_material, slots), sizes)]).astype(np.int64)
    elif part.scope == 'VERTEX_GROUP':
        group = obj.vertex_groups.get(part.vertex_group)
        if group is None:
            raise PartError(rpt_("Part %s: vertex group %s is not on %s") % (part.name, part.vertex_group, obj.name))
        index = group.index
        found = np.array([v.index for v in mesh.vertices
                          if any(g.group == index and g.weight > 0.0 for g in v.groups)], np.int64)
    else:
        found = np.arange(len(mesh.vertices), dtype=np.int64)
    if len(found) == 0:
        raise PartError(rpt_("Part %s has no vertices") % part.name)
    return found


def local_edges(edges, vertices):
    """The edges with both ends in `vertices`, renumbered as positions in `vertices`."""
    if len(edges) == 0 or len(vertices) == 0:
        return np.zeros((0, 2), np.int64)
    local = np.full(max(int(vertices.max()), int(edges.max())) + 1, -1, np.int64)
    local[vertices] = np.arange(len(vertices))
    a, b = local[edges[:, 0]], local[edges[:, 1]]
    keep = (a >= 0) & (b >= 0)
    return np.stack([a[keep], b[keep]], axis=1)


def pieces(edges, vertices):
    """The loose pieces of `vertices`: sorted arrays of mesh vertex indices, joined by edges inside `vertices`."""
    return [vertices[c] for c in chains.components(len(vertices), local_edges(edges, vertices))]


def bone_segment(rig, name):
    """World (head, tail) of a bone of `rig` at rest."""
    bone = rig.data.bones[name]
    return np.array(rig.matrix_world @ bone.head_local), np.array(rig.matrix_world @ bone.tail_local)


def nearest_bone(rig, point, names):
    """The name in `names` of the bone of `rig` nearest to the world `point` (the first one on a tie)."""
    point = np.asarray(point, float)[None, :]
    best, best_distance = None, None
    for name in names:
        distance = float(chains.segment_distance(point, *bone_segment(rig, name))[0])
        if best_distance is None or distance < best_distance - 1e-12:
            best, best_distance = name, distance
    return best
