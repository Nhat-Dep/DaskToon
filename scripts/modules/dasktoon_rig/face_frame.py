# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Finding a face without a DaskToon rig (docs/superpowers/specs/2026-11-11-dasktoon-dlive-face-sculpt-design.md).

eye_shapes, mouth_shapes and face_shapes read a face in the head's frame: a Head bone, the character facing -Y with its
left at +X, the roles of the parts (Body, Hair). A character without a DaskToon rig has none of that, so `located` gives
the code a temporary armature object that does: its single Head bone is a unit long, centred on the object's origin, and
the object's own transform maps the head's frame onto the scene (a head of any size, facing any of the four ways). The
armature has the parts the names and shapes of the meshes suggest (parts.initial_roles) and an Armature modifier on each
mesh, which moves nothing since no vertex group names its bone; everything goes when the block ends.

Where is the head: the eyes tell. Small loose pieces, a twin on each side of the face's middle at the same height, set
in front of the head's centre (what eye_shapes.find_eyes starts from); the frame is tried at several sizes (a head is a
seventh to the whole of the character) and all four ways, for every one the prefilter finds such a pair in, the full
eye search (find_eyes) has the last word. A humanoid armature of any naming (VRM, MMD, Mixamo, Unreal: the bone names of
dasktoon_import.bones) gives the head's top and base, which narrows the sizes to try."""

import contextlib
import math

import bpy
import numpy as np
from mathutils import Matrix

from . import eye_shapes, parts, skeleton

FACINGS = ((0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0))  # the horizontal way the character looks (x, y)
HEADS = (1.0 / 8.0, 1.0 / 6.5, 1.0 / 5.0, 1.0 / 4.0, 1.0 / 3.0, 1.0 / 2.2, 0.6, 1.0)  # a head's share of the height
FRONT_AT = 0.5  # the face's front lies this far (of the head) forward of its centre
BEST = -0.08  # where the eyes lie in a head: this far (of its height) from its centre
TRIES = 8  # the most frames the full eye search runs in
SLAB = 1.15  # the frame's vertices: those this many heads under the top


def _vertices(obj):
    """The vertices of mesh `obj` at rest (its reference key's) in the scene."""
    key = obj.data.shape_keys
    points = key.reference_key.data if key is not None else obj.data.vertices
    co = np.empty(len(points) * 3)
    points.foreach_get("co", co)
    return co.reshape(-1, 3) @ np.array(obj.matrix_world.to_3x3()).T + np.array(obj.matrix_world.translation)


def _basis(facing):
    """Columns: the scene's directions of the frame's X (the character's left), Y (backwards) and Z (up)."""
    left = np.array((-facing[1], facing[0], 0.0))
    return np.stack([left, -np.array((facing[0], facing[1], 0.0)), np.array((0.0, 0.0, 1.0))], axis=1)


def _matrix(centre, size, facing):
    m = Matrix.Identity(4)
    basis = _basis(facing) * size
    for i in range(3):
        for j in range(3):
            m[i][j] = basis[i][j]
        m[i][3] = centre[i]
    return m


def head_bone(rig):
    """(head, tail) in the scene of the head bone of the humanoid armature `rig`, whatever its naming; None without
    one."""
    from dasktoon_import import bones
    if rig is None or rig.type != 'ARMATURE':
        return None
    for bone in rig.data.bones:
        hit = bones.classify(bone.name)
        if hit is not None and hit[0] == "Head":
            return (np.array(rig.matrix_world @ bone.head_local), np.array(rig.matrix_world @ bone.tail_local))
    return None


def _make_rig(context):
    """The temporary armature: a Hips bone for the middle and a Head bone a unit long, centred on the origin."""
    data = bpy.data.armatures.new("DaskFace")
    rig = bpy.data.objects.new("DaskFace", data)
    context.scene.collection.objects.link(rig)
    with skeleton.editing(context, rig) as edit:
        hips = edit.new("Hips")
        hips.head, hips.tail = (0.0, 0.0, -3.0), (0.0, 0.0, -2.0)
        head = edit.new("Head")
        head.head, head.tail = (0.0, 0.0, -0.5), (0.0, 0.0, 0.5)
        head.parent = hips
    return rig


class _Pieces:
    """The small loose pieces of the meshes that may be part of an eye, as boxes in the scene."""

    def __init__(self, meshes, hair):
        self.owner, self.low, self.high = [], [], []
        for obj in meshes:
            if obj in hair or not len(obj.data.vertices):
                continue
            world = _vertices(obj)
            for piece in eye_shapes._pieces(obj.data):
                if len(piece) >= eye_shapes.FEWEST:
                    self.owner.append(obj)
                    self.low.append(world[piece].min(axis=0))
                    self.high.append(world[piece].max(axis=0))
        self.low, self.high = np.array(self.low).reshape(-1, 3), np.array(self.high).reshape(-1, 3)

    def twins(self, centre, size, facing):
        """The face's middle across (the frame's x, size units) when pieces of an eye are in the frame, else None."""
        to_head = _basis(facing).T / size
        a, b = (self.low - centre) @ to_head.T, (self.high - centre) @ to_head.T
        low, high = np.minimum(a, b), np.maximum(a, b)
        middle = (low + high) / 2.0
        keep = ((middle[:, 1] < eye_shapes.FRONT) & (np.abs(middle[:, 0]) < eye_shapes.SIDE[1] + eye_shapes.OFF_MIDDLE)
                & (middle[:, 2] > eye_shapes.HEIGHT[0]) & (middle[:, 2] < eye_shapes.HEIGHT[1])
                & ((high - low).max(axis=1) < eye_shapes.WIDEST))
        found = [(self.owner[i], i, low[i], high[i]) for i in np.nonzero(keep)[0][:400]]
        return eye_shapes._twins(found)[0] if len(found) > 1 else None


def _roles(meshes):
    return parts.initial_roles(meshes)


def _slab(cloud, top, size, facing):
    """(centre across, front depth) of the vertices `cloud` within SLAB sizes of `top`, along the character's own axes
    (left, forward) in the scene; None without any."""
    basis = _basis(facing)
    world = cloud[cloud[:, 2] > top - SLAB * size]
    if not len(world):
        return None
    across, ahead = world @ basis[:, 0], world @ -basis[:, 1]
    return (across.min() + across.max()) / 2.0, float(np.percentile(ahead, 99.5))


@contextlib.contextmanager
def located(context, meshes, rig):
    """Yields the rig `eye_shapes` and its kin read `meshes` with: `rig` itself when it is a DaskToon rig with a Head
    bone; otherwise a temporary armature sitting on the head found (module docstring); None when no face is found.
    The temporary armature and the Armature modifiers it needed are gone afterwards."""
    if rig is not None and rig.data.bones.get("Head") is not None and getattr(rig.data, "dasktoon_rig", None) is not None:
        yield rig
        return
    meshes = [obj for obj in meshes if obj.type == 'MESH' and len(obj.data.vertices)]
    temp = _make_rig(context) if meshes else None
    added = []
    try:
        if temp is not None:
            from bl_ui import dasktoon_rig as ui
            for obj, role in _roles(meshes).items():
                ui.add_part(temp, obj, role)
            for obj in meshes:
                modifier = obj.modifiers.new("DaskFace", 'ARMATURE')
                modifier.object = temp
                obj.modifiers.move(len(obj.modifiers) - 1, 0)
                added.append((obj, modifier))
            context.view_layer.update()
            if not _find(context, temp, meshes, rig):
                yield None
                return
        yield temp
    finally:
        for obj, modifier in added:
            obj.modifiers.remove(modifier)
        if temp is not None:
            data = temp.data
            bpy.data.objects.remove(temp)
            bpy.data.armatures.remove(data)


def _find(context, temp, meshes, rig):
    """Put `temp` on the head of the character `meshes` (and the humanoid armature `rig` if it has one); False when no
    face is found."""
    hair = {part.object for part in temp.data.dasktoon_rig.parts if part.role == 'HAIR'}
    world = np.concatenate([_vertices(obj) for obj in meshes if obj not in hair] or [_vertices(meshes[0])])
    low, high = world.min(axis=0), world.max(axis=0)
    top, height = float(np.percentile(world[:, 2], 99.8)), float(high[2] - low[2])
    sizes = [share * height for share in HEADS]
    bone = head_bone(rig)
    if bone is not None:  # the head's base and top narrow the sizes: the bone's own length is no head's height
        reach = top - min(bone[0][2], bone[1][2])
        sizes = [reach * f for f in (1.0, 1.15, 0.9, 1.3, 0.75)] + sizes
    pieces = _Pieces(meshes, hair)
    tried = []
    for size in sizes:
        for facing in FACINGS:
            found = _slab(world, top, size, facing)
            if found is None:
                continue
            across, ahead = found
            basis = _basis(facing)
            centre = basis[:, 0] * across + basis[:, 1] * -(ahead - FRONT_AT * size)
            centre = np.array((centre[0], centre[1], top - size / 2.0))
            middle = pieces.twins(centre, size, facing)
            if middle is not None:
                centre = centre + basis[:, 0] * middle * size
                score = abs(_eye_height(pieces, centre, size, facing) - BEST)
                tried.append((score, size, centre, facing))
    tried.sort(key=lambda t: t[0])
    for _score, size, centre, facing in tried[:TRIES]:
        temp.matrix_world = _matrix(centre, size, facing)
        context.view_layer.update()
        if eye_shapes.find_eyes(temp, meshes):
            return True
    return False


def _eye_height(pieces, centre, size, facing):
    """How far from the head's centre (heads) the pieces that look like eyes lie, on average."""
    to_head = _basis(facing).T / size
    middle = ((pieces.low + pieces.high) / 2.0 - centre) @ to_head.T
    near = middle[(middle[:, 2] > eye_shapes.HEIGHT[0]) & (middle[:, 2] < eye_shapes.HEIGHT[1])
                  & (middle[:, 1] < eye_shapes.FRONT) & (np.abs(middle[:, 0]) < eye_shapes.SIDE[1])]
    return float(np.median(near[:, 2])) if len(near) else 9.0


def apply_mirrors(context, meshes):
    """Apply the Mirror modifier (across X, no mirror object) of every mesh of `meshes` without shape keys, so that
    each side of a character modelled in half is a real side a key can move on its own. Meshes are copies."""
    for obj in meshes:
        if obj.type != 'MESH' or obj.data.shape_keys is not None or not eye_shapes.has_mirror(obj):
            continue
        for modifier in [m for m in obj.modifiers if m.type == 'MIRROR' and m.use_axis[0] and m.mirror_object is None
                         and m.show_viewport]:
            try:
                with context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:
                break
