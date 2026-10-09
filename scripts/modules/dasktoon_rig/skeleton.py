# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon standard skeleton (anime rig spec 4): Unity's 55 human bones (HumanBodyBones names), in T-pose, facing
-Y with the character's left at +X and the feet at z = 0. Positions are for a character 1 tall; they are scaled to the
character's height."""

from contextlib import contextmanager

import bpy
import numpy as np
from mathutils import Matrix, Vector

DEFAULT_HEIGHT = 1.6
REQUIRED = (
    "Hips", "Spine", "Head",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
)
# Never part of the automatic body weights: the eyes and the jaw get their weights from their own parts.
FACE_BONES = ("LeftEye", "RightEye", "Jaw")

_FRONT = (0.0, -1.0, 0.0)
_UP = (0.0, 0.0, 1.0)

# (name, parent, head, tail, where the bone's Z axis points)
_CENTER = (
    ("Hips", None, (0.0, 0.0, 0.52), (0.0, 0.0, 0.58), _FRONT),
    ("Spine", "Hips", (0.0, 0.0, 0.58), (0.0, 0.0, 0.645), _FRONT),
    ("Chest", "Spine", (0.0, 0.0, 0.645), (0.0, 0.0, 0.715), _FRONT),
    ("UpperChest", "Chest", (0.0, 0.0, 0.715), (0.0, 0.0, 0.80), _FRONT),
    ("Neck", "UpperChest", (0.0, 0.0, 0.80), (0.0, -0.005, 0.85), _FRONT),
    ("Head", "Neck", (0.0, -0.005, 0.85), (0.0, -0.005, 0.99), _FRONT),
    ("Jaw", "Head", (0.0, 0.0, 0.885), (0.0, -0.06, 0.855), _UP),
)
_LEFT = (
    ("LeftEye", "Head", (0.03, -0.045, 0.915), (0.03, -0.075, 0.915), _UP),
    ("LeftShoulder", "UpperChest", (0.015, 0.0, 0.78), (0.10, 0.0, 0.78), _UP),
    ("LeftUpperArm", "LeftShoulder", (0.10, 0.0, 0.78), (0.255, 0.005, 0.78), _UP),
    ("LeftLowerArm", "LeftUpperArm", (0.255, 0.005, 0.78), (0.39, 0.0, 0.78), _UP),
    ("LeftHand", "LeftLowerArm", (0.39, 0.0, 0.78), (0.44, 0.0, 0.78), _UP),
    ("LeftThumbProximal", "LeftHand", (0.395, -0.015, 0.775), (0.41, -0.03, 0.772), _UP),
    ("LeftThumbIntermediate", "LeftThumbProximal", (0.41, -0.03, 0.772), (0.422, -0.04, 0.771), _UP),
    ("LeftThumbDistal", "LeftThumbIntermediate", (0.422, -0.04, 0.771), (0.432, -0.048, 0.77), _UP),
    ("LeftUpperLeg", "Hips", (0.05, 0.0, 0.52), (0.055, -0.005, 0.28), _FRONT),
    ("LeftLowerLeg", "LeftUpperLeg", (0.055, -0.005, 0.28), (0.06, 0.0, 0.045), _FRONT),
    ("LeftFoot", "LeftLowerLeg", (0.06, 0.0, 0.045), (0.06, -0.06, 0.012), _UP),
    ("LeftToes", "LeftFoot", (0.06, -0.06, 0.012), (0.06, -0.09, 0.012), _UP),
)
# (finger, its y, the x where it starts, length scale); every finger has three bones along +X.
_FINGERS = (("Index", -0.012, 0.44, 1.0), ("Middle", -0.004, 0.442, 1.08), ("Ring", 0.004, 0.44, 1.0),
            ("Little", 0.012, 0.436, 0.8))
_SEGMENTS = (("Proximal", 0.02), ("Intermediate", 0.015), ("Distal", 0.012))


def _fingers():
    out = []
    for finger, y, x, scale in _FINGERS:
        parent = "LeftHand"
        for segment, length in _SEGMENTS:
            name = "Left" + finger + segment
            end = x + length * scale
            out.append((name, parent, (x, y, 0.78), (end, y, 0.78), _UP))
            parent, x = name, end
    return out


def _right(name):
    return "Right" + name[4:] if name is not None and name.startswith("Left") else name


def bones():
    """Every bone of the standard skeleton, parents before children: (name, parent, head, tail, z axis)."""
    left = list(_LEFT) + _fingers()
    right = [(_right(n), _right(p), (-h[0], h[1], h[2]), (-t[0], t[1], t[2]), z) for n, p, h, t, z in left]
    return list(_CENTER) + left + right


BONE_NAMES = tuple(b[0] for b in bones())


def missing_bones(armature):
    """The REQUIRED bones that the Armature data lacks, in REQUIRED order."""
    present = armature.edit_bones if armature.is_editmode else armature.bones
    return [name for name in REQUIRED if present.get(name) is None]


def is_humanoid(obj):
    """True for an armature object with every REQUIRED bone (spec 4.2)."""
    return obj is not None and obj.type == 'ARMATURE' and not missing_bones(obj.data)


def bounds(objects):
    """(low, high) world corners around `objects` (a mesh by its vertices, anything else by its bounding box), or None
    when there is none."""
    lows, highs = [], []
    for obj in objects:
        if obj.type == 'MESH':
            if not obj.data.vertices:
                continue
            co = np.empty(len(obj.data.vertices) * 3, np.float32)
            obj.data.vertices.foreach_get("co", co)
            matrix = np.array(obj.matrix_world)
            world = co.reshape(-1, 3).astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
        else:
            world = np.array([tuple(obj.matrix_world @ Vector(corner)) for corner in obj.bound_box])
        lows.append(world.min(axis=0))
        highs.append(world.max(axis=0))
    if not lows:
        return None
    return Vector(np.min(lows, axis=0)), Vector(np.max(highs, axis=0))


def placement(objects, fallback_location):
    """(height, location of the feet) of a skeleton for `objects` (spec 4.3): the height of their bounding box and the
    middle of its bottom, or DEFAULT_HEIGHT at `fallback_location`."""
    box = bounds(objects)
    if box is None or box[1].z - box[0].z < 1e-4:
        return DEFAULT_HEIGHT, Vector(fallback_location)
    low, high = box
    return high.z - low.z, Vector(((low.x + high.x) / 2.0, (low.y + high.y) / 2.0, low.z))


@contextmanager
def editing(context, rig):
    """`rig` in Edit Mode meanwhile (yields its edit bones); afterwards Object Mode and the previous active object.
    An active object in another mode is put in Object Mode first."""
    view_layer = context.view_layer
    previous = view_layer.objects.active
    if previous is not None and previous.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        yield rig.data.edit_bones
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous


def set_joints(rig, matrix, create):
    """Put the standard bones of `rig` (in Edit Mode) where the template maps through `matrix` (template to armature
    space). `create` adds missing bones and sets parents and connections; otherwise only existing bones move."""
    edit = rig.data.edit_bones
    rotation = matrix.to_3x3()
    tails = {}
    for name, parent, head, tail, z_axis in bones():
        bone = edit.get(name)
        if bone is None:
            if not create:
                continue
            bone = edit.new(name)
        bone.head = matrix @ Vector(head)
        bone.tail = matrix @ Vector(tail)
        bone.align_roll(rotation @ Vector(z_axis))
        if create:
            bone.parent = edit.get(parent) if parent else None
            bone.use_connect = parent is not None and (Vector(head) - tails[parent]).length < 1e-9
        tails[name] = Vector(tail)


def create_humanoid(context, height=DEFAULT_HEIGHT, location=(0.0, 0.0, 0.0), name="Rig"):
    """A new armature object in the active collection with the standard skeleton of a character `height` tall whose
    feet are at `location`; X-Axis Mirror on and In Front shown, for fitting the joints."""
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    context.collection.objects.link(rig)
    rig.matrix_world = Matrix.Translation(location)
    rig.show_in_front = True
    data.use_mirror_x = True
    with editing(context, rig):
        set_joints(rig, Matrix.Scale(height, 4), create=True)
    return rig


def fit(context, rig, objects):
    """Move the standard bones of `rig` to the bounding box of `objects` (the object itself stays, so meshes bound to it
    do not move; bones the user deleted stay deleted). Returns the height used."""
    height, location = placement(objects, rig.matrix_world.translation)
    matrix = rig.matrix_world.inverted() @ Matrix.Translation(location) @ Matrix.Scale(height, 4)
    with editing(context, rig):
        set_joints(rig, matrix, create=False)
    return height
