# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Game texture sets (docs/superpowers/specs/2026-10-20-dasktoon-game-texture-sets-design.md): every face goes to the Hair,
Body or Face set; a material used by more than one set is copied for the others; islands are turned to stand upright;
each set gets the image size its share of one character-wide sharpness asks for (the face twice as sharp); one colour
picture per set holds each material's base colour, and every Base Color reads it."""

import math

import bpy
import numpy as np
from mathutils import Color

from dasktoon_rig import regions

from . import seams as seams_
from . import transfer

NAMES = ('HAIR', 'BODY', 'FACE')
SUFFIX = {'HAIR': "Hair", 'BODY': "Body", 'FACE': "Face"}
FACE_SHARPNESS = 2.0  # the face's pixels per metre over the body's
MAX_SIZE, MIN_SIZE = 2048, 256
MARGIN_PIXELS = 8
HEAD = seams_.LABELS.index('HEAD')
ARMS = {seams_.LABELS.index(name): side for name, side in (
    ('ARM_L', "Left"), ('HAND_L', "Left"), ('ARM_R', "Right"), ('HAND_R', "Right"))}
SHADERS = ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel', 'ShaderNodeBsdfPrincipled')


IN_HEAD = 1.2  # a loose piece whose middle lies within this many head lengths of the head's middle is on the head
FRONT = 0.3  # a head piece this many head lengths in front of the head's middle, and
SMALL = 0.6  # no larger than this many head lengths, is a face piece (an eye, a brow, a mouth)


def face_sets(obj, rig, labels):
    """The set (index in NAMES) of every face. Hair: what a Hair part of the rig owns, and the pieces on the head that
    are neither its skin nor small pieces in front of the face (a hair cap or locks in the body mesh, ears, a ribbon).
    Face: the head's skin (the piece reaching the neck or holding the chin) and the small pieces in front of it.
    Body: the rest."""
    from dasktoon_rig import build
    mesh = obj.data
    labels = np.asarray(labels)
    parts = list(rig.data.dasktoon_rig.parts)
    owners = build.ownership(parts).get(obj)
    first = np.array([p.vertices[0] for p in mesh.polygons], dtype=np.int64)
    out = np.full(len(mesh.polygons), NAMES.index('BODY'), dtype=np.int64)
    hair = np.zeros(len(mesh.polygons), dtype=bool)
    if owners is not None:
        hair = np.array([part.role == 'HAIR' for part in parts] + [False])[owners][first]

    bones = rig.data.bones
    if "Head" in bones:
        head = bones["Head"]
        centre = np.array((head.head_local + head.tail_local) / 2)
        size = max(head.length, 1e-6)
        to_rig = rig.matrix_world.inverted() @ obj.matrix_world
        local = np.array([to_rig @ v.co for v in mesh.vertices]).reshape(-1, 3)
        pieces = seams_.loose_pieces(mesh)[first]
        on_head = labels == HEAD
        for piece in np.unique(pieces):
            faces = pieces == piece
            middle = local[np.unique(np.concatenate([list(mesh.polygons[f].vertices)
                                                     for f in np.nonzero(faces)[0][:400]]))].mean(axis=0)
            if not on_head[faces].any() and (labels[faces] < seams_.PIECE).any():
                continue  # a body part of the rig away from the head
            if not on_head[faces].any() and np.linalg.norm(middle - centre) > IN_HEAD * size:
                continue  # a loose piece elsewhere
            head_faces = faces & (on_head | (labels >= seams_.PIECE))
            verts = np.unique(np.concatenate([list(mesh.polygons[f].vertices) for f in np.nonzero(head_faces)[0]]))
            points = local[verts]
            skin = (faces & ~on_head & (labels < seams_.PIECE)).any()  # it reaches the neck
            skin |= on_head[faces].any() and points[:, 2].min() <= local[np.isin(np.arange(len(local)), np.unique(
                np.concatenate([list(mesh.polygons[f].vertices) for f in np.nonzero(on_head)[0]])))][:, 2].min() + 1e-6
            in_front = (points[:, 1].mean() < centre[1] - FRONT * size
                        and float(np.ptp(points, axis=0).max()) < SMALL * size)
            out[head_faces] = NAMES.index('FACE') if (skin or in_front) else NAMES.index('HAIR')
    out[hair] = NAMES.index('HAIR')
    return out


def _indices(obj):
    indices = np.empty(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", indices)
    return indices


def split_materials(meshes, face_sets_of):
    """A material used by faces of several sets, in one mesh or across meshes (luna's clothes and a hair ornament), keeps
    the set using it most; the others get a copy named "<material> <Set>" (the face's own material, as games have),
    so every Base Color reads one set's picture."""
    usage = {}
    for obj in meshes:
        indices = _indices(obj)
        for slot_index, slot in enumerate(obj.material_slots):
            if slot.material is not None:
                counts = np.bincount(face_sets_of[obj][indices == slot_index], minlength=len(NAMES))
                usage[slot.material] = usage.get(slot.material, np.zeros(len(NAMES), np.int64)) + counts
    kept = {mat: int(counts.argmax()) for mat, counts in usage.items()}
    copies = {}
    for obj in meshes:
        mesh = obj.data
        indices = _indices(obj)
        changed = False
        for slot_index, slot in enumerate(list(obj.material_slots)):
            mat = slot.material
            if mat is None:
                continue
            here = face_sets_of[obj][indices == slot_index]
            for other in sorted(set(here.tolist()) - {kept[mat]}):
                if (mat, other) not in copies:
                    copy = mat.copy()
                    copy.name = "%s %s" % (mat.name, SUFFIX[NAMES[other]])
                    copies[(mat, other)] = copy
                copy = copies[(mat, other)]
                slot_of_copy = next((i for i, s in enumerate(obj.material_slots) if s.material == copy), None)
                if slot_of_copy is None:
                    mesh.materials.append(copy)
                    slot_of_copy = len(mesh.materials) - 1
                indices[(indices == slot_index) & (face_sets_of[obj] == other)] = slot_of_copy
                changed = True
        if changed:
            mesh.polygons.foreach_set("material_index", indices)
            mesh.update()


def _up_field(obj, labels, rig):
    """A height for every vertex that grows toward the character's top; along each arm, toward the shoulder."""
    mesh = obj.data
    to_rig = rig.matrix_world.inverted() @ obj.matrix_world
    local = np.array([to_rig @ v.co for v in mesh.vertices]).reshape(-1, 3)
    height = local[:, 2].copy()
    bones = rig.data.bones
    vertex_label = np.full(len(mesh.vertices), -1)
    for poly in mesh.polygons:
        vertex_label[list(poly.vertices)] = labels[poly.index]
    for label, side in ARMS.items():
        upper, hand = side + "UpperArm", side + "Hand"
        if upper not in bones or hand not in bones:
            continue
        toward_shoulder = np.array(bones[upper].head_local - bones[hand].head_local)
        toward_shoulder /= max(np.linalg.norm(toward_shoulder), 1e-9)
        mask = vertex_label == label
        height[mask] = local[mask] @ toward_shoulder
    return height


def _gradient(uv, field, mesh, faces):
    """The mean gradient, in UV, of `field` (per vertex) over the faces (weighted by their UV area)."""
    total = np.zeros(2)
    area = 0.0
    for f in faces:
        loops = list(mesh.polygons[f].loop_indices)
        a = uv[loops[0]]
        fa = field[mesh.loops[loops[0]].vertex_index]
        for k in range(1, len(loops) - 1):
            b, c = uv[loops[k]], uv[loops[k + 1]]
            fb, fc = field[mesh.loops[loops[k]].vertex_index], field[mesh.loops[loops[k + 1]].vertex_index]
            m = np.array([b - a, c - a], dtype=np.float64)
            det = np.linalg.det(m)
            if abs(det) < 1e-14:
                continue
            total += np.linalg.solve(m, np.array([fb - fa, fc - fa])) * abs(det) / 2
            area += abs(det) / 2
    return total / area if area > 0 else total


def island_up_gradients(obj, labels, rig):
    """For every island of obj, the UV direction in which the character's top (an arm's shoulder) lies."""
    from .unwrap import get_uv
    mesh = obj.data
    uv = get_uv(obj)
    field = _up_field(obj, labels, rig)
    return [_gradient(uv, field, mesh, group) for group in seams_.groups(mesh, labels, seams_._edge_faces(mesh))]


def stand_upright(obj, labels, faces_of, rig):
    """Turn every island about its middle so the character's top (an arm's shoulder) is up in the picture."""
    from .unwrap import get_uv, set_uv
    mesh = obj.data
    uv = get_uv(obj)
    field = _up_field(obj, labels, rig)
    for group in seams_.groups(mesh, labels, faces_of):
        g = _gradient(uv, field, mesh, group)
        loops = [loop for f in group for loop in mesh.polygons[f].loop_indices]
        verts = [mesh.loops[loop].vertex_index for loop in loops]
        extent = float(np.ptp(uv[loops], axis=0).max()) or 1.0
        rise = float(np.ptp(field[verts])) or 0.0
        if np.linalg.norm(g) < 0.1 * rise / extent or rise == 0.0:
            continue  # no clear top (a sole, a flat cap): left as unwrapped
        angle = math.atan2(g[0], g[1])
        rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
        middle = uv[loops].mean(axis=0)
        uv[loops] = (uv[loops] - middle) @ rotation.T + middle
    set_uv(obj, uv)


def size_for(sharpness, share):
    """The power of two (MIN_SIZE..MAX_SIZE) giving at least `sharpness` pixels per metre to a set whose UV square
    holds `share` UV units per metre."""
    if share <= 0:
        return MIN_SIZE
    need = sharpness / share
    return int(min(MAX_SIZE, max(MIN_SIZE, 2 ** math.ceil(math.log2(max(need, 1.0)) - 1e-9))))


def colour_source(mat):
    """('IMAGE', image) or ('FLAT', linear RGB) for the material's base colour (spec, ruling 2)."""
    node = next((n for kind in SHADERS for n in (mat.node_tree.nodes if mat and mat.node_tree else ())
                 if n.bl_idname == kind), None)
    if node is None or "Base Color" not in node.inputs:
        return 'FLAT', tuple(mat.diffuse_color[:3]) if mat else (0.8, 0.8, 0.8)
    socket = node.inputs["Base Color"]
    if not socket.is_linked:
        return 'FLAT', tuple(socket.default_value[:3])
    todo, seen = [socket.links[0].from_node], set()
    while todo:
        current = todo.pop(0)
        if current.name in seen:
            continue
        seen.add(current.name)
        if current.bl_idname == 'ShaderNodeTexImage' and transfer.has_pixels(current.image):
            return 'IMAGE', current.image
        if current.bl_idname == 'ShaderNodeRGB':
            return 'FLAT', tuple(current.outputs[0].default_value[:3])
        todo += [link.from_node for s in current.inputs for link in s.links]
    return 'FLAT', tuple(socket.default_value[:3])


def _source_pixels(image):
    px = transfer._pixels(image).copy()
    if image.is_float:  # scene linear: the atlas holds sRGB values like a painted picture
        rgb = np.clip(px[..., :3], 0, None)
        px[..., :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    return px


def make_atlases(meshes, rig, result):
    """One colour picture per set (named "<rig> <Set> Color", the set's size), every face painted with its material's
    base colour (pictures through the old UV map), and every Base Color of the set's materials reading it."""
    atlases = {}
    for index, name in enumerate(NAMES):
        size = result.sizes.get(name)
        if not size:
            continue
        dst = np.zeros((size, size, 4), np.float32)
        filled = np.zeros((size, size), dtype=bool)
        materials = set()
        sources = {}
        for obj in meshes:
            faces = np.nonzero(result.sets[obj] == index)[0].tolist() if obj in result.sets else []
            if not faces:
                continue
            mesh = obj.data
            new_uv = transfer._uv(mesh, mesh.uv_layers.active.name)
            old_name = result.old.get(obj)
            old_uv = transfer._uv(mesh, old_name) if old_name else None
            right = {f for (o, f) in result.mirrored if o == obj}
            for f in sorted(faces, key=lambda f: f not in right):  # the left side drawn last stays
                poly = mesh.polygons[f]
                mat = obj.material_slots[poly.material_index].material if poly.material_index < len(
                    obj.material_slots) else None
                if mat is not None:
                    materials.add(mat)
                if mat not in sources:
                    kind, value = colour_source(mat)
                    if kind == 'IMAGE' and old_uv is not None:
                        sources[mat] = ('IMAGE', _source_pixels(value))
                    else:
                        rgb = Color(value if kind == 'FLAT' else (0.8, 0.8, 0.8)).from_scene_linear_to_srgb()
                        sources[mat] = ('FLAT', np.array([[[*rgb, 1.0]]], np.float32))
                kind, src = sources[mat]
                loops = list(poly.loop_indices)
                for k in range(1, len(loops) - 1):
                    corners = [loops[0], loops[k], loops[k + 1]]
                    old = old_uv[corners] if kind == 'IMAGE' else np.zeros((3, 2))
                    transfer.draw(dst, filled, src, new_uv[corners], old)
        transfer.bleed(dst, filled, MARGIN_PIXELS)
        image = bpy.data.images.new("%s %s Color" % (rig.name, SUFFIX[name]), size, size, alpha=True)
        image.pixels.foreach_set(dst.ravel())
        image.update()
        atlases[name] = image
        for mat in materials:
            node = next((n for kind in SHADERS for n in mat.node_tree.nodes if n.bl_idname == kind), None) \
                if mat.node_tree else None
            if node is None or "Base Color" not in node.inputs:
                continue
            texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texture.image = image
            texture.location = (node.location.x - 360, node.location.y + 260)
            socket = node.inputs["Base Color"]
            for link in list(socket.links):
                mat.node_tree.links.remove(link)
            mat.node_tree.links.new(texture.outputs["Color"], socket)
    return atlases
