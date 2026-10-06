# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build Rig (anime rig spec 6): check the rig and its parts, generate the hair and skirt chains, bind the meshes and
paint the weights of every part, then clean them up for Unity. Every build starts again from the parts."""

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import chains, parts as rig_parts, skeleton, weights

MARK = "dt_part"
MIN_BONE = 1e-4


class BuildError(Exception):
    """Why the rig cannot be built, worded for the user."""


class Result:
    """What a build did: the generated bones, the chains, the objects it painted and the warnings."""

    def __init__(self):
        self.bones = []
        self.chains = 0
        self.objects = []
        self.warnings = []

    def summary(self):
        return rpt_("Built %d bones in %d chains, weights on %d objects") % (
            len(self.bones), self.chains, len(self.objects))


def check(rig, parts):
    """BuildError when the rig cannot be built (spec 6.1)."""
    if rig is None or rig.type != 'ARMATURE':
        raise BuildError(rpt_("The active object is not an armature"))
    if rig.library is not None or rig.data.library is not None:
        raise BuildError(rpt_("%s is linked from a library") % rig.name)
    missing = skeleton.missing_bones(rig.data)
    if missing:
        raise BuildError(rpt_("%s is not a standard skeleton; missing bones: %s") % (rig.name, ", ".join(missing)))
    if not rig.visible_get():
        raise BuildError(rpt_("%s is hidden; show it before building") % rig.name)
    if not parts:
        raise BuildError(rpt_("Add parts before building the rig"))
    for part in parts:
        obj = part.object
        if obj is None:
            raise BuildError(rpt_("Part %s has no object") % part.name)
        if obj.type != 'MESH':
            raise BuildError(rpt_("Part %s: %s is not a mesh") % (part.name, obj.name))
        if obj.library is not None or obj.data.library is not None:
            raise BuildError(rpt_("%s is linked from a library") % obj.name)
        if obj.data.users > 1:
            raise BuildError(rpt_("%s shares its mesh with other objects; make it single user first") % obj.name)
        if not obj.visible_get():
            raise BuildError(rpt_("%s is hidden; show it before building") % obj.name)
        if part.bone and rig.data.bones.get(part.bone) is None:
            raise BuildError(rpt_("Part %s: bone %s is not in %s") % (part.name, part.bone, rig.name))
        if part.bone and MARK in rig.data.bones[part.bone]:  # removed and made again by the build
            raise BuildError(rpt_("Part %s: bone %s is made by Build Rig; pick a bone of the skeleton")
                             % (part.name, part.bone))
        try:
            rig_parts.part_vertices(part)
        except rig_parts.PartError as ex:
            raise BuildError(str(ex)) from None
    roles = {part.role for part in parts}
    if 'CLOTHING' in roles and 'BODY' not in roles:
        raise BuildError(rpt_("Clothing copies its weights from a Body part; add a Body part first"))


def ownership(parts):
    """{object: array giving, for each vertex, the index in `parts` of the part that owns it (-1 for none)}: a later
    role wins, then a later part (spec 5.2)."""
    owners = {}
    for i in sorted(range(len(parts)), key=lambda i: (rig_parts.ROLES.index(parts[i].role), i)):
        obj = parts[i].object
        if obj not in owners:
            owners[obj] = np.full(len(obj.data.vertices), -1, np.int64)
        owners[obj][rig_parts.part_vertices(parts[i])] = i
    return owners


class _Plan:
    """Chains to generate: bones (name, parent, world head, world tail, part name) and paint jobs (part index,
    vertices, bone names, weights) whose names are the planned ones."""

    def __init__(self):
        self.bones = []
        self.paint = []
        self.chains = 0


def _local_x(rig, point):
    return (rig.matrix_world.inverted() @ Vector(point)).x


def _plan_hair(rig, index, part, vertices, plan):
    attach = part.bone or rig_parts.DEFAULT_BONE['HAIR']
    head, tail = rig_parts.bone_segment(rig, attach)
    world, edges = rig_parts.mesh_arrays(part.object)
    locks = []
    for piece in rig_parts.pieces(edges, vertices):
        chain = chains.hair_chain(world[piece], rig_parts.local_edges(edges, piece), head, tail, part.bone_count)
        if chain is None:
            plan.paint.append((index, piece, [attach], np.ones((len(piece), 1))))
        else:
            locks.append((piece, chain))
    locks.sort(key=lambda lock: _local_x(rig, lock[1].joints[0]))
    base = rig_parts.ascii_name(part.name)
    for number, (piece, chain) in enumerate(locks, 1):
        prefix = base if len(locks) == 1 else "%s%d" % (base, number)
        names = ["%s_%d" % (prefix, k) for k in range(1, part.bone_count + 1)]
        parent = attach
        for k, name in enumerate(names):
            plan.bones.append((name, parent, chain.joints[k], chain.joints[k + 1], part.name))
            parent = name
        plan.paint.append((index, piece, [attach] + names, chain.weights))
        plan.chains += 1


def _plan_skirt(rig, index, part, vertices, plan):
    attach = part.bone or rig_parts.DEFAULT_BONE['SKIRT']
    world, _edges = rig_parts.mesh_arrays(part.object)
    skirt = chains.skirt_chains(world[vertices], part.bone_count, part.chain_count)
    base = rig_parts.ascii_name(part.name)
    names = [attach]
    for c, joints in enumerate(skirt.strips):
        strip = ["%s%d_%d" % (base, c + 1, k) for k in range(1, part.bone_count + 1)]
        names += strip
        if joints is None:
            continue
        parent = attach
        for k, name in enumerate(strip):
            plan.bones.append((name, parent, joints[k], joints[k + 1], part.name))
            parent = name
        plan.chains += 1
    plan.paint.append((index, vertices, names, skirt.weights))


def _make_bones(context, rig, plan):
    """Remove the bones of the last build and add the planned ones. Returns ({planned name: actual name}, the names
    of the removed bones)."""
    to_rig = rig.matrix_world.inverted()
    actual, removed = {}, []
    with skeleton.editing(context, rig) as edit:
        for bone in list(edit):
            if MARK in bone:
                removed.append(bone.name)
                edit.remove(bone)
        for name, parent, head, tail, part_name in plan.bones:
            bone = edit.new(name)
            bone.head = to_rig @ Vector(head)
            bone.tail = to_rig @ Vector(tail)
            if (bone.tail - bone.head).length < MIN_BONE:
                bone.tail = bone.head + Vector((0.0, 0.0, -MIN_BONE))
            parent_bone = edit.get(actual.get(parent, parent))
            bone.parent = parent_bone
            if parent in actual and (parent_bone.tail - bone.head).length < 1e-6:
                bone.use_connect = True
            outward = bone.head - (parent_bone.head + parent_bone.tail) / 2.0
            if outward.length > 1e-9:
                bone.align_roll(outward)
            bone.use_deform = True
            bone[MARK] = part_name
            actual[name] = bone.name
    return actual, removed


def _paint(context, rig, parts, owners, plan, actual, result):
    deform = [b.name for b in rig.data.bones if b.use_deform]
    generated = set(actual.values())
    body_bones = [n for n in deform if n not in generated and n not in skeleton.FACE_BONES]
    fixed_bones = [n for n in deform if n not in generated]
    body_ids = [i for i, part in enumerate(parts) if part.role == 'BODY']
    for obj in owners:
        weights.bind(rig, obj)
    sources = []
    for obj, owner in owners.items():
        body = np.isin(owner, body_ids)
        if not body.any():
            continue
        sources.append((obj, body))
        weights.clear(obj, np.arange(len(owner)), deform)
        weights.body_heat(context, rig, obj, set(body_bones))
        vertices = np.nonzero(body)[0]
        matrix = weights.read(obj, body_bones)[vertices]
        empty = matrix.sum(axis=1) <= 0.0
        if empty.any():
            world, _edges = rig_parts.mesh_arrays(obj)
            weights.write(obj, vertices[empty], body_bones,
                          weights.nearest_bone_weights(rig, body_bones, world[vertices[empty]]))
            result.warnings.append(rpt_("%s: %d vertices took the nearest bone (automatic weights found no "
                                        "solution there)") % (obj.name, int(empty.sum())))
    for i, part in enumerate(parts):
        obj = part.object
        vertices = np.nonzero(owners[obj] == i)[0]
        if len(vertices) == 0 or part.role in ('BODY',) + rig_parts.CHAIN_ROLES:
            continue
        weights.clear(obj, vertices, deform)
        if part.role == 'CLOTHING':
            world, _edges = rig_parts.mesh_arrays(obj)
            matrix = weights.surface_weights(sources, body_bones, world[vertices])
            if not (matrix.sum(axis=1) > 0.0).all():
                result.warnings.append(rpt_("%s: no Body surface to copy weights from") % part.name)
            weights.write(obj, vertices, body_bones, matrix)
        else:
            world, _edges = rig_parts.mesh_arrays(obj)
            bone = part.bone or rig_parts.nearest_bone(rig, world[vertices].mean(axis=0), fixed_bones)
            weights.write(obj, vertices, [bone], np.ones((len(vertices), 1)))
    for index, vertices, names, matrix in plan.paint:
        obj = parts[index].object
        weights.clear(obj, vertices, deform)
        weights.write(obj, vertices, [actual.get(n, n) for n in names], matrix)


def _drop_stale_groups(owners, removed, current):
    for obj in owners:
        for name in removed:
            group = obj.vertex_groups.get(name)
            if group is not None and name not in current:
                obj.vertex_groups.remove(group)


def _tidy(rig, owners):
    names = [b.name for b in rig.data.bones if b.use_deform]
    for obj in owners:
        matrix = weights.read(obj, names)
        rows = np.nonzero(matrix.sum(axis=1) > 0.0)[0]
        weights.clear(obj, rows, names)
        weights.write(obj, rows, names, weights.tidy(matrix[rows]))


def build(context, rig, parts):
    """Build the rig from `parts` (spec 6.2); BuildError, before any change, when it cannot be built. The active object
    and its mode come back afterwards."""
    parts = list(parts)
    view_layer = context.view_layer
    active = view_layer.objects.active
    mode = active.mode if active is not None else 'OBJECT'
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    try:
        check(rig, parts)
        result = Result()
        owners = ownership(parts)
        plan = _Plan()
        for i, part in enumerate(parts):
            vertices = np.nonzero(owners[part.object] == i)[0]
            if len(vertices) == 0:
                continue
            if part.role == 'HAIR':
                _plan_hair(rig, i, part, vertices, plan)
            elif part.role == 'SKIRT':
                _plan_skirt(rig, i, part, vertices, plan)
        actual, removed = _make_bones(context, rig, plan)
        _paint(context, rig, parts, owners, plan, actual, result)
        _drop_stale_groups(owners, removed, set(actual.values()))
        _tidy(rig, owners)
        result.bones = list(actual.values())
        result.chains = plan.chains
        result.objects = [obj.name for obj in owners]
        return result
    finally:
        view_layer.objects.active = active
        if active is not None and mode != 'OBJECT' and active.mode != mode:
            bpy.ops.object.mode_set(mode=mode)
