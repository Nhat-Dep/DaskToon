# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bend fixes (docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md): corrective shape keys for the knees,
elbows, hips and shoulders, made by Build Rig. Linear blending puts a vertex weighted across a joint on the straight line
between where each bone would take it, so a bent joint loses volume; at the fix's pose the key moves such a vertex to
where turning it about the joint by its share of the bend puts it. Only on the outer side of the bend (the knee cap,
the seat, the top of the shoulder), where linear blending loses the volume: on the inner side (the back of the knee, the
groin, the armpit) the turned vertices bulged out, as tdt (a real model) showed in DaskToon's shader with its arm
raised; the key fades from one side to the other over a band OUTER_BAND of the vertex's distance from the bone wide.

The fix's pose: the child bone turned about the joint, from its rest direction (along the bone) to the target, by
`angle` about `axis`. A vertex with the share `a` of its weight on the child side goes, with linear blending, to
x' + a (R x' - x') (x' from the joint) and should go to R(a angle) x'. The key holds the rest offset that makes linear
blending land there: M^-1 (wanted - linear), M = (1 - a) I + a R, since the bones' blend M acts on the offset too.

A driver shows the key. The child's swing from rest (its turn as seen from the parent, without the twist about itself),
read in its own frame as the swing quaternion's vector v = sin(alpha / 2) n, splits into the bend along the fix's arc,
2 asin(v . axis), and the swing off it, 2 asin(v . across). The key's value rises from 0 at `start` to 1 at `angle`
along the arc (exactly linear in the bend), stays at 1 past it, or, when a deeper fix follows on the same arc, falls back
to 0 at `end` while that one rises (a knee: 90 degrees, then kneeling at 150); it fades for a limb swung off the arc,
over `reach` (a leg out to the side leaves the sitting fix):
clamp((bend - start) / (angle - start)) * clamp((end - bend) / (end - angle)) * clamp(1 - |off| / reach). A Transform variable in
Swing and Y Twist mode gives 2 asin of v's X and Z, so sin(x / 2) and sin(z / 2) are v's components: a simple
expression, no Python, no Auto Run. DaskToon's Unity script works the value out the same way."""

import math
from typing import NamedTuple

import numpy as np
from mathutils import Matrix, Vector

PREFIX = "DT_Fix_"  # the shape keys: DT_Fix_LeftKnee
SIDES = ("Left", "Right")
FRONT, BACK = Vector((0.0, -1.0, 0.0)), Vector((0.0, 1.0, 0.0))
DOWN = Vector((0.0, 0.0, -1.0))
# (joint, parent, child, where the child turns, its bends in degrees): toward FRONT or BACK across the bone, a fix at
# each bend in turn (the second named ...Deep); straight DOWN, one fix there (bends None). No fix for the arm raised:
# in DaskToon's shader it bulged the armpit out (tdt) and pushed the skin through the shirt (lr_shape), real models.
JOINTS = (("Knee", "{}UpperLeg", "{}LowerLeg", BACK, (90.0, 150.0)),
          ("Elbow", "{}UpperArm", "{}LowerArm", FRONT, (90.0, 140.0)),
          ("Hip", "Hips", "{}UpperLeg", FRONT, (90.0,)),
          ("Shoulder", "{}Shoulder", "{}UpperArm", DOWN, None))
DEEP = "Deep"
LEAST_TURN = math.radians(20.0)  # an arm hanging this near down needs no fix there
SMALLEST = 0.0005  # x the character's height: a key moving no vertex further is not made
OUTER_BAND = 0.5  # the key fades from the outer to the inner side of the bend over this x the distance from the bone
LONGEST = 255  # characters Blender keeps of a driver's expression


class Fix(NamedTuple):
    name: str  # "LeftKnee"
    parent: str
    child: str
    joint: Vector  # the child's head, armature space, rest
    rest: Vector  # the child's direction at rest (along the bone)
    target: Vector  # its direction at the fix's pose
    axis: Vector  # rest x target: the fix turns the child about it
    angle: float  # the bend of the fix's pose, where the key is 1
    start: float  # the bend where it starts to show: 0, or the fix before on the same arc
    end: float  # the bend where it is gone again (the next fix on the arc), 0 when it stays past its pose
    reach: float  # the swing off the arc it fades over (the arc's first bend)


def fixes(rig):
    """The fixes the rig's bones allow, at rest in armature space."""
    bones = rig.data.bones
    out = []
    for side in SIDES:
        for joint, parent, child, toward, bends in JOINTS:
            parent, child = parent.format(side), child.format(side)
            if bones.get(parent) is None or bones.get(child) is None:
                continue
            bone = bones[child]
            rest = (bone.tail_local - bone.head_local).normalized()
            across = toward - toward.dot(rest) * rest
            if across.length < 1e-3:
                continue
            across.normalize()
            angles = [math.radians(bend) for bend in bends] if bends else [rest.angle(toward)]
            if angles[0] < LEAST_TURN:
                continue
            axis = rest.cross(across).normalized()
            for i, angle in enumerate(angles):
                target = rest * math.cos(angle) + across * math.sin(angle)
                start = angles[i - 1] if i else 0.0
                end = angles[i + 1] if i + 1 < len(angles) else 0.0
                out.append(Fix(side + joint + (DEEP if i else ""), parent, child, bone.head_local.copy(), rest,
                               target, axis, angle, start, end, angles[0]))
    return out


def body_frame(rig):
    """(left, up, front) of the character at rest, unit vectors in armature space, from its upper legs, Hips and Head
    (bones every engine gets); None without them. Unity's frame is mirrored: there front = up x left (here left x
    up)."""
    bones = rig.data.bones
    if any(bones.get(name) is None for name in ("Hips", "Head", "LeftUpperLeg", "RightUpperLeg")):
        return None
    up = bones["Head"].head_local - bones["Hips"].head_local
    left = bones["LeftUpperLeg"].head_local - bones["RightUpperLeg"].head_local
    if up.length < 1e-6:
        return None
    up.normalize()
    left -= left.dot(up) * up
    if left.length < 1e-6:
        return None
    left.normalize()
    return left, up, left.cross(up)


def keyed(rig, objects):
    """The fixes with a shape key on a mesh among `objects` the rig deforms."""
    names = set()
    for obj in objects:
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is not None and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            names.update(block.name for block in key.key_blocks)
    return [fix for fix in fixes(rig) if PREFIX + fix.name in names]


def _height(rig):
    zs = [z for bone in rig.data.bones for z in (bone.head_local.z, bone.tail_local.z)]
    return max(zs) - min(zs) if zs else 1.0


def _deformed_by(obj, rig):
    """True when an Armature modifier of `obj` blends linearly with `rig` (Preserve Volume would blend otherwise) and
    no Mirror modifier copies its half: the key would show on the other half too, whose limb is not bent (lr_shape, a
    real model, models halves so)."""
    if any(m.type == 'MIRROR' for m in obj.modifiers):
        return False
    return any(m.type == 'ARMATURE' and m.object == rig and not m.use_deform_preserve_volume for m in obj.modifiers)


def _rest_coordinates(obj):
    key = obj.data.shape_keys
    points = key.reference_key.data if key is not None else obj.data.vertices
    co = np.empty(len(points) * 3)
    points.foreach_get("co", co)
    return co.reshape(-1, 3)


def child_share(rig, obj, child):
    """Per vertex of `obj`, the part of its deforming weight on `child` and the bones below it."""
    side = {child} | {bone.name for bone in rig.data.bones[child].children_recursive}
    deform = {bone.name for bone in rig.data.bones if bone.use_deform}
    columns = {group.index: group.name in side for group in obj.vertex_groups if group.name in deform}
    total = np.zeros(len(obj.data.vertices))
    share = np.zeros(len(obj.data.vertices))
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            on_child = columns.get(element.group)
            if on_child is not None:
                total[vertex.index] += element.weight
                if on_child:
                    share[vertex.index] += element.weight
    return np.divide(share, total, out=np.zeros_like(share), where=total > 0.0)


def _turned(points, axis, angles):
    """`points` (n x 3) each turned about `axis` (unit) by its angle (Rodrigues)."""
    k = np.array(axis)
    cos, sin = np.cos(angles)[:, None], np.sin(angles)[:, None]
    return points * cos + np.cross(k, points) * sin + np.outer(points @ k, k) * (1.0 - cos)


def offsets(rig, obj, fix):
    """The key's offsets (vertices x 3, the object's space) for `fix` on `obj`."""
    share = child_share(rig, obj, fix.child)
    out = np.zeros((len(share), 3))
    blended = np.nonzero((share > 1e-6) & (share < 1.0 - 1e-6))[0]
    if len(blended) == 0:
        return out
    to_arm = rig.matrix_world.inverted() @ obj.matrix_world
    linear_part = np.array(to_arm.to_3x3())
    rest = _rest_coordinates(obj)[blended] @ linear_part.T + np.array(to_arm.translation)
    relative = rest - np.array(fix.joint)
    a = share[blended]
    whole = np.array(Matrix.Rotation(fix.angle, 3, fix.axis))
    linear = relative + a[:, None] * (relative @ whole.T - relative)
    wanted = _turned(relative, fix.axis, a * fix.angle)
    blend = (1.0 - a)[:, None, None] * np.eye(3) + a[:, None, None] * whole
    moved = np.linalg.solve(blend, (wanted - linear)[:, :, None])[:, :, 0]
    inward = fix.target - fix.rest * fix.rest.dot(fix.target)  # where the limb folds to
    inward.normalize()
    along = relative @ np.array(inward)
    rest_dir = np.array(fix.rest)
    off_axis = np.linalg.norm(relative - np.outer(relative @ rest_dir, rest_dir), axis=1)
    t = np.clip(0.5 - along / (2.0 * np.maximum(OUTER_BAND * off_axis, 1e-9)), 0.0, 1.0)
    moved *= (t * t * (3.0 - 2.0 * t))[:, None]  # 1 on the outer side, 0 on the inner side
    out[blended] = moved @ np.linalg.inv(linear_part).T
    return out


def expression(rig, fix):
    """The driver's expression on x and z, the child's swing channels (module docstring)."""
    frame = rig.data.bones[fix.child].matrix_local.to_3x3().inverted()  # armature space to the bone's rest frame
    along = frame @ fix.axis
    across = frame @ fix.rest.cross(fix.axis)

    def part(v):
        return "2*asin(min(max(%.5f*sin(x/2)+%.5f*sin(z/2),-1),1))" % (v.x, v.z)

    bend = part(along)
    if fix.start:
        rise = "clamp(%s*%.5f-%.5f)" % (bend, 1.0 / (fix.angle - fix.start), fix.start / (fix.angle - fix.start))
    else:
        rise = "clamp(%s/%.5f)" % (bend, fix.angle)
    fall = ("*clamp(%.5f-%s*%.5f)" % (fix.end / (fix.end - fix.angle), bend, 1.0 / (fix.end - fix.angle))
            if fix.end else "")
    text = "%s%s*clamp(1-abs(%s)/%.5f)" % (rise, fall, part(across), fix.reach)
    if len(text) > LONGEST:
        raise ValueError("driver expression too long: %d characters" % len(text))
    return text


def _drive(key, block_name, rig, fix):
    path = 'key_blocks["%s"].value' % block_name
    key.driver_remove(path)
    driver = key.driver_add(path).driver
    driver.type = 'SCRIPTED'
    for name, channel in (("x", 'ROT_X'), ("z", 'ROT_Z')):
        variable = driver.variables.new()
        variable.name = name
        variable.type = 'TRANSFORMS'
        target = variable.targets[0]
        target.id = rig
        target.bone_target = fix.child
        target.transform_type = channel
        target.rotation_mode = 'SWING_TWIST_Y'
        target.transform_space = 'LOCAL_SPACE'
    driver.expression = expression(rig, fix)


def _remove_key(obj, name):
    key = obj.data.shape_keys
    block = key.key_blocks.get(name) if key is not None else None
    if block is None:
        return
    key.driver_remove('key_blocks["%s"].value' % name)
    obj.shape_key_remove(block)


def _remove_stale(obj, keep):
    key = obj.data.shape_keys
    for name in [b.name for b in key.key_blocks] if key is not None else ():
        if name.startswith(PREFIX) and name not in keep:
            _remove_key(obj, name)


def remove(meshes):
    """Take every fix off `meshes`."""
    for obj in meshes:
        if obj.type == 'MESH':
            _remove_stale(obj, ())


def apply(rig, meshes):
    """Make, or make again, the fixes on `meshes` the rig deforms (Build Rig calls it after the weights). Returns the
    names of the fixes made."""
    meshes = [obj for obj in meshes if obj.type == 'MESH' and _deformed_by(obj, rig)]
    smallest = SMALLEST * _height(rig)
    made = set()
    for fix in fixes(rig):
        name = PREFIX + fix.name
        for obj in meshes:
            moved = offsets(rig, obj, fix)
            to_arm = np.array((rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
            if not len(moved) or np.linalg.norm(moved @ to_arm.T, axis=1).max() < smallest:
                _remove_key(obj, name)
                continue
            if obj.data.shape_keys is None:
                obj.shape_key_add(name="Basis", from_mix=False)
            block = obj.data.shape_keys.key_blocks.get(name) or obj.shape_key_add(name=name, from_mix=False)
            block.data.foreach_set("co", (_rest_coordinates(obj) + moved).ravel())
            block.slider_min, block.slider_max = 0.0, 1.0
            _drive(obj.data.shape_keys, name, rig, fix)
            made.add(fix.name)
    for obj in meshes:  # fixes the rig no longer allows (an arm now hanging, a bone gone)
        _remove_stale(obj, {PREFIX + name for name in made})
    return sorted(made)
