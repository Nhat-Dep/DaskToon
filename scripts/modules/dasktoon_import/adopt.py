# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Make an imported character a DaskToon character (docs/superpowers/specs/2026-11-10-dasktoon-import-adopt-design.md):
standing on the floor in the middle facing -Y, its skeleton turned into DaskToon's (the joints where the model's own
bones are, the model's own weights kept), the bones that swing (MikuMikuDance's physics, or chains of extra bones) as
DaskToon sway chains with colliders, expressions under DaskToon's names (faces.py) and DaskToon's shader.

A source bone gives its weights to: the DaskToon bone it is named as (bones.match); itself, when it is kept (it sways,
or a swinging bone hangs from it); else, when MikuMikuDance turns it partly with another bone (a twist or an elbow
helper), its share to that bone's DaskToon bone and the rest to its parent's; else its parent's. A vertex keeps at most
four weights, as Unity wants."""

from types import SimpleNamespace

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Matrix, Vector

from . import bones as source_bones

IMPORTED = "dt_imported"  # on the rig's armature data: where it came from ('MMD', 'UNREAL', 'OTHER')
TWIST_WORDS = ("twist", "捩")
# the template proportions (dasktoon_rig.skeleton) used for the bones a skeleton lacks
CHEST_AT = 0.42  # Chest's head, from Spine's head to the Neck's
UPPER_CHEST_AT = 0.71
UPPER_CHEST_FROM_CHEST = 0.45  # UpperChest's head, from Chest's head to the Neck's, when only it is missing
HEAD_LENGTH = 0.09  # of the height, the Head bone's length when its source tells nothing
EYE_LENGTH = 0.02
NEXT = {"Hips": "Spine", "Spine": "Chest", "Chest": "UpperChest", "UpperChest": "Neck", "Neck": "Head"}
for _side in ("Left", "Right"):
    NEXT.update({_side + a: _side + b for a, b in (
        ("Shoulder", "UpperArm"), ("UpperArm", "LowerArm"), ("LowerArm", "Hand"), ("Hand", "MiddleProximal"),
        ("UpperLeg", "LowerLeg"), ("LowerLeg", "Foot"), ("Foot", "Toes"))})
    for _finger in source_bones.FINGERS:
        NEXT[_side + _finger + "Proximal"] = _side + _finger + "Intermediate"
        NEXT[_side + _finger + "Intermediate"] = _side + _finger + "Distal"


class AdoptError(Exception):
    """The character cannot be made a DaskToon character, worded for the user."""


class Result:
    def __init__(self, rig):
        self.rig = rig
        self.notes = []
        self.chains = 0
        self.expressions = []
        self.materials = 0
        self.controls = 0  # control bones added; 0 without
        self.controls_error = ""
        self.face_knobs = 0


def source_of(objects):
    """(armature, its meshes) among `objects`: the armature deforming the most vertices of their meshes, or None."""
    meshes = [obj for obj in objects if obj.type == 'MESH']
    count = {}
    for obj in meshes:
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object is not None:
                count[modifier.object] = count.get(modifier.object, 0) + len(obj.data.vertices)
    armatures = [obj for obj in objects if obj.type == 'ARMATURE']
    rig = max(count, key=count.get) if count else (armatures[0] if armatures else None)
    if rig is None:
        return None, meshes
    deformed = [obj for obj in bpy.data.objects if obj.type == 'MESH'
                and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)]
    return rig, deformed


# --- the scene: MikuMikuDance's leftovers, standing ---

def drop_mmd_root(armature):
    """MMD Tools hangs the model under an empty with its rigid bodies and joints: the armature leaves it where it is,
    the empty and the objects only it holds go."""
    root = armature.parent
    if root is None or root.type != 'EMPTY':
        return
    world = armature.matrix_world.copy()
    armature.parent = None
    armature.matrix_world = world
    doomed = [root] + [obj for obj in root.children_recursive if obj.type != 'MESH' or not any(
        m.type == 'ARMATURE' for m in obj.modifiers)]
    for obj in doomed:
        if obj != armature and armature not in obj.children_recursive:
            bpy.data.objects.remove(obj)


def drop_mmd_keys(meshes):
    """MMD Tools' SDEF helper shape keys are not expressions."""
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        for block in [b for b in key.key_blocks if b.name.startswith("mmd_sdef")]:
            obj.shape_key_remove(block)


def stand(context, armature, meshes):
    """Facing -Y, about 1.6 m tall when far off, on the floor in the middle (the Model Check's fixes), then every
    transform applied, so the armature and the meshes are at the origin unrotated and unscaled."""
    from dasktoon_guide import checks, fixes
    for name in ("facing", "size", "floor", "middle"):
        entry = next(e for e in checks.CHECKS if e[0] == name)
        status, _text = entry[3](checks._Context(context, meshes, armature))
        if status in ('WARN', 'ERROR'):
            fixes.FIXES[name](context, meshes, armature)
            context.view_layer.update()
    objects = [armature] + [obj for obj in meshes if obj.data.users == 1]
    with context.temp_override(selected_editable_objects=objects, selected_objects=objects, active_object=armature,
                               object=armature):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


# --- the skeleton ---

def read_bones(armature):
    """The armature's bones as SourceBone in world space; MikuMikuDance's Japanese names as aliases."""
    world = armature.matrix_world
    out = []
    for bone in armature.data.bones:
        pb = armature.pose.bones.get(bone.name)
        mmd = getattr(pb, "mmd_bone", None) if pb is not None else None
        aliases = (mmd.name_j,) if mmd is not None and mmd.name_j else ()
        out.append(source_bones.SourceBone(bone.name, bone.parent.name if bone.parent else None,
                                           tuple(world @ bone.head_local), tuple(world @ bone.tail_local), aliases))
    return out


def read_weights(obj):
    """(vertex, group name, weight) arrays of every weight above 0 of `obj`: sparse, as a model with hundreds of bones
    and a hundred thousand vertices would fill a full matrix of gigabytes."""
    names = np.array([g.name for g in obj.vertex_groups] or [""], dtype=object)
    vertices, groups, values = [], [], []
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            if element.weight > 0.0:
                vertices.append(vertex.index)
                groups.append(element.group)
                values.append(element.weight)
    groups = np.array(groups, np.int64)
    return np.array(vertices, np.int64), names[groups] if len(groups) else np.zeros(0, object), np.array(values)


def weighted_groups(weights_of, names):
    """The names of `names` with a weight above 0 in `weights_of` ({mesh: read_weights})."""
    wanted = set(names)
    return {n for _v, groups, _w in weights_of.values() for n in set(groups.tolist()) if n in wanted}


def chain_bones(source, members, weighted):
    """Bones that sway when nothing says which (a .uemodel): weighted bones not named as DaskToon's, no twist, in a
    chain of two or more of them (a lock of hair, not a lone helper)."""
    parent = {b.name: b.parent for b in source}
    free = {b.name for b in source if b.name in weighted and b.name not in members
            and not any(word in b.name.lower() for word in TWIST_WORDS)}
    # A bone two or more chains hang from (a hat with its ribbons) holds still; its chains sway.
    children = {}
    for name in free:
        if parent[name] in free:
            children.setdefault(parent[name], []).append(name)
    free -= {name for name, kids in children.items() if len(kids) > 1}
    has_child = {parent[n] for n in free if parent[n] in free}
    return {n for n in free if n in has_child or parent[n] in free}


def kept_bones(source, members, swaying):
    """The swinging bones (not named as DaskToon's) and the bones between them and the DaskToon bones they hang from."""
    parent = {b.name: b.parent for b in source}
    keep = set()
    for name in swaying:
        if name in members:
            continue
        current = name
        while current is not None and current not in members and current not in keep:
            keep.add(current)
            current = parent.get(current)
    return keep


def plan(source, members, keep, renamed, additional=None):
    """{source bone: [(new bone, share)]}: where each source bone's weights go (module docstring). `renamed` names the
    kept bones in the new rig; `additional` {bone: (bone it turns with, influence)} is MikuMikuDance's."""
    parent = {b.name: b.parent for b in source}
    additional = additional or {}

    def resolve(name):
        seen = 0
        while name is not None and seen < 10000:
            if name in keep:
                return renamed[name]
            if name in members:
                return members[name]
            name = parent.get(name)
            seen += 1
        return "Hips"

    out = {}
    for bone in source:
        name = bone.name
        if name in keep:
            out[name] = [(renamed[name], 1.0)]
        elif name in members:
            out[name] = [(members[name], 1.0)]
        else:
            own = resolve(parent[name])
            other, share = additional.get(name, (None, 0.0))
            target = resolve(other) if other else None
            if target is None or share <= 0.0 or target == own:
                out[name] = [(own, 1.0)]
            elif share >= 1.0:
                out[name] = [(target, 1.0)]
            else:
                out[name] = [(own, 1.0 - share), (target, share)]
    return out


def mmd_additional(armature):
    """{bone: (bone it turns with, influence)} of MikuMikuDance's additional rotations."""
    out = {}
    for pb in armature.pose.bones:
        mmd = getattr(pb, "mmd_bone", None)
        if mmd is not None and mmd.has_additional_rotation and mmd.additional_transform_bone:
            out[pb.name] = (mmd.additional_transform_bone, float(mmd.additional_transform_influence))
    return out


def _z_axes():
    from dasktoon_rig import skeleton
    return {name: Vector(z) for name, _parent, _head, _tail, z in skeleton.bones()}


def _parents():
    from dasktoon_rig import skeleton
    return {name: parent for name, parent, _head, _tail, _z in skeleton.bones()}


def joints(source, matched, height):
    """{DaskToon bone: (head, tail)} in world space: heads at the matched bones (the Hips between the upper legs), the
    spine's missing bones between its others, tails at the next bone's head, else along the source bone, else on from
    the parent."""
    by_name = {b.name: b for b in source}
    head = {target: Vector(by_name[name].head) for target, name in matched.items()}
    head["Hips"] = (head["LeftUpperLeg"] + head["RightUpperLeg"]) / 2.0
    neck = head.get("Neck", head["Head"])
    if "Chest" not in head:
        head["Chest"] = head["Spine"].lerp(neck, CHEST_AT)
        if "UpperChest" not in head:
            head["UpperChest"] = head["Spine"].lerp(neck, UPPER_CHEST_AT)
    elif "UpperChest" not in head:
        head["UpperChest"] = head["Chest"].lerp(neck, UPPER_CHEST_FROM_CHEST)
    if "Neck" not in head:
        head["Neck"] = head["UpperChest"].lerp(head["Head"], 0.5)
    for side in ("Left", "Right"):
        if side + "Shoulder" not in head:
            arm = head[side + "UpperArm"]
            middle = head["UpperChest"]
            head[side + "Shoulder"] = Vector((middle.x + 0.15 * (arm.x - middle.x), arm.y, arm.z))
    parents = _parents()
    out = {}
    for name in [n for n in parents if n in head]:  # parents first
        start = head[name]
        following = NEXT.get(name)
        tail = head.get(following) if following else None
        if tail is None or (tail - start).length < 1e-4 * height:
            tail = _own_tail(name, start, matched, by_name, out, parents, height)
        out[name] = (start, tail)
    return out


def _own_tail(name, start, matched, by_name, done, parents, height):
    if name == "Head":
        return start + Vector((0.0, 0.0, HEAD_LENGTH * height))
    if name.endswith("Eye"):
        return start + Vector((0.0, -EYE_LENGTH * height, 0.0))
    parent = parents.get(name)
    before = done.get(parent) if parent else None
    along = (before[1] - before[0]) if before is not None else Vector((0.0, 0.0, 0.05 * height))
    source = by_name.get(matched.get(name))
    if source is not None:
        own = Vector(source.tail) - Vector(source.head)
        if own.length > 1e-4 * height and (along.length == 0.0 or own.normalized().dot(along.normalized()) > 0.3):
            return start + own
    return start + along.normalized() * max(along.length * 0.7, 0.01 * height)


def build_rig(context, armature, source, positions, keep, renamed, members, name):
    """A new armature at the origin: DaskToon's bones at `positions` ({bone: (head, tail)} world), the kept source bones
    copied (same place and roll) under their new parents."""
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    context.collection.objects.link(rig)
    rig.show_in_front = True
    z_axes, parents = _z_axes(), _parents()
    by_name = {b.name: b for b in source}
    rolls = {b.name: armature.matrix_world @ b.matrix_local for b in armature.data.bones if b.name in keep}
    view_layer = context.view_layer
    previous = view_layer.objects.active
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        edit = data.edit_bones
        for bone_name, (head, tail) in positions.items():
            bone = edit.new(bone_name)
            bone.head, bone.tail = head, tail
            bone.align_roll(z_axes[bone_name])
        for bone_name in positions:
            parent = parents[bone_name]
            while parent is not None and parent not in positions:
                parent = parents[parent]
            if parent is not None:
                edit[bone_name].parent = edit[parent]
                edit[bone_name].use_connect = (edit[parent].tail - edit[bone_name].head).length < 1e-7
        made = {}
        depth = {b.name: len(source_bones.ancestors(source, b.name)) for b in source}
        for src in sorted(keep, key=lambda n: depth[n]):
            bone = edit.new(renamed[src])
            b = by_name[src]
            bone.head, bone.tail = Vector(b.head), Vector(b.tail)
            if (bone.tail - bone.head).length < 1e-6:
                bone.tail = bone.head + Vector((0.0, 0.0, 0.01))
            bone.align_roll(rolls[src].to_3x3() @ Vector((0.0, 0.0, 1.0)))
            made[src] = bone
        for src, bone in made.items():
            parent = by_name[src].parent
            while parent is not None and parent not in keep and parent not in members:
                parent = by_name[parent].parent if parent in by_name else None
            if parent is None:
                bone.parent = edit["Hips"]
            elif parent in keep:
                bone.parent = made[parent]
            else:
                bone.parent = edit[members[parent]]
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous
    return rig


def sparse_tidy(vertices, columns, values, limit=4, minimum=0.01, tie=1e-6):
    """dasktoon_rig.weights.tidy on sparse weights (no repeated vertex and column): under `minimum` dropped, at most
    `limit` per vertex (weights alike across the limit all go), summing to 1; a vertex left with none keeps its
    largest. Returns (vertices, columns, values)."""
    if len(vertices) == 0:
        return vertices, columns, values
    order = np.lexsort((-values, vertices))
    v, c, w = vertices[order], columns[order], values[order]
    starts = np.r_[0, np.nonzero(np.diff(v))[0] + 1]
    first = np.repeat(starts, np.diff(np.r_[starts, len(v)]))
    rank = np.arange(len(v)) - first
    keep = (w >= minimum) & (rank < limit)
    cut_at = first + limit  # the largest dropped by the limit, where there is one
    has_cut = (cut_at < len(v))
    has_cut[has_cut] &= v[cut_at[has_cut]] == v[has_cut]
    cut = np.where(has_cut, w[np.minimum(cut_at, len(v) - 1)], -1.0)
    keep &= ~(has_cut & (cut >= minimum) & (np.abs(w - cut) <= tie))
    kept_any = np.bincount(v, weights=keep.astype(float), minlength=int(v.max()) + 1) > 0
    keep |= (rank == 0) & ~kept_any[v]
    w = np.where((rank == 0) & ~kept_any[v], 1.0, w)
    v, c, w = v[keep], c[keep], w[keep]
    sums = np.bincount(v, weights=w, minlength=int(v.max()) + 1)
    return v, c, w / sums[v]


def move_weights(obj, found, shares, targets):
    """The vertex groups of the source bones become the groups of the new bones, by `shares` ({source: [(target,
    share)]}); `found` is read_weights(obj). At most four weights a vertex; other groups stay."""
    vertices, groups, values = found
    column = {t: j for j, t in enumerate(targets)}
    out_v, out_c, out_w = [], [], []
    for name in set(groups.tolist()):
        if name not in shares:
            continue
        mine = groups == name
        for target, share in shares[name]:
            out_v.append(vertices[mine])
            out_c.append(np.full(int(mine.sum()), column[target], np.int64))
            out_w.append(values[mine] * share)
    for name in shares:
        group = obj.vertex_groups.get(name)
        if group is not None:
            obj.vertex_groups.remove(group)
    if not out_v:
        return
    v, c, w = np.concatenate(out_v), np.concatenate(out_c), np.concatenate(out_w)
    keys, inverse = np.unique(v * len(targets) + c, return_inverse=True)
    w = np.bincount(inverse, weights=w)
    v, c, w = sparse_tidy(keys // len(targets), keys % len(targets), w)
    for j in np.unique(c).tolist():
        mine = c == j
        group = obj.vertex_groups.get(targets[j]) or obj.vertex_groups.new(name=targets[j])
        for index, value in zip(v[mine].tolist(), w[mine].tolist()):
            group.add([index], value, 'REPLACE')


def mark_chains(rig, swaying):
    """Mark the swaying bones as sway chains (dasktoon_rig.sway): each chain a line of them, from a bone whose parent
    does not sway, a bone with several swaying children going on with the first and starting new chains with the
    others. Returns the number of chains."""
    from dasktoon_rig import build
    bones = rig.data.bones
    roots = [bones[n] for n in swaying if bones[n].parent is None or bones[n].parent.name not in swaying]
    count = 0
    stack = list(roots)
    while stack:
        bone = stack.pop()
        count += 1
        part = bone.name
        while bone is not None:
            bone[build.MARK] = part
            children = [c for c in bone.children if c.name in swaying]
            stack.extend(children[1:])
            bone = children[0] if children else None
    return count


def add_sway(rig, meshes):
    """Spring constraints on the chains and capsule colliders round the body bones, as Build Rig makes them."""
    from dasktoon_rig import build, sway
    body = SimpleNamespace(role='BODY')
    owners = {obj: np.zeros(len(obj.data.vertices), np.int64) for obj in meshes}
    build._write_colliders(rig, build.collider_radii(rig, [body], owners), sway.rig_scale(rig))
    sway.sync(rig)


# --- all together ---

def adopt(context, armature, meshes, kind='OTHER', swaying=None, controls=True):
    """Make the character of `armature` and `meshes` a DaskToon character (module docstring). `swaying`: the source
    bones that swing (MikuMikuDance's physics), None to find chains of extra bones; `controls`: add the animation
    controls (dasktoon_rig.controls; a skeleton they cannot go on stays without, saying why). Returns a Result; raises
    AdoptError when its skeleton lacks a bone DaskToon needs."""
    try:
        source_bones.match(read_bones(armature))  # before anything changes: a skeleton it cannot use stays as it is
    except source_bones.MapError as ex:
        raise AdoptError(rpt_("The skeleton has no bone DaskToon knows as %s") % ", ".join(ex.missing)) from ex
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    drop_mmd_root(armature)
    drop_mmd_keys(meshes)
    stand(context, armature, meshes)
    source = read_bones(armature)
    matched, members = source_bones.match(source)  # again: standing it up may have turned it round
    names = [b.name for b in source]
    found = {obj: read_weights(obj) for obj in meshes}
    weighted = weighted_groups(found, names)
    if swaying is None:
        swaying = chain_bones(source, members, weighted)
    swaying = {n for n in swaying if n in weighted and n not in members}
    keep = kept_bones(source, members, swaying)
    from dasktoon_rig import skeleton
    reserved = set(skeleton.BONE_NAMES)
    renamed = {n: (n if n not in reserved else n + ".src") for n in keep}
    height = max(1e-6, max(b.head[2] for b in source) - min(b.head[2] for b in source))
    positions = joints(source, matched, height)
    shares = plan(source, members, keep, renamed, mmd_additional(armature))
    name = armature.name
    rig = build_rig(context, armature, source, positions, keep, renamed, members, name + " DaskToon")
    targets = list(positions) + [renamed[n] for n in keep]
    for obj in meshes:
        move_weights(obj, found[obj], shares, targets)
    from dasktoon_rig import weights
    for obj in meshes:
        weights.bind(rig, obj)
    old_data = armature.data
    bpy.data.objects.remove(armature)
    if old_data.users == 0:
        bpy.data.armatures.remove(old_data)
    rig.name = name
    rig.data.name = name
    rig.data[IMPORTED] = kind
    result = Result(rig)
    result.chains = mark_chains(rig, {renamed[n] for n in swaying})
    add_sway(rig, meshes)
    from . import faces
    result.expressions = faces.adopt(rig, meshes)
    result.materials = convert_materials(meshes)
    view_layer = context.view_layer
    view_layer.update()
    if controls:
        from dasktoon_rig import controls as rig_controls
        try:
            result.controls = rig_controls.add(context, rig)
        except rig_controls.ControlsError as ex:
            result.controls_error = str(ex)
        from dasktoon_rig import face_board
        result.face_knobs = face_board.build(context, rig)  # the expressions named above, on knobs beside the head
    for obj in context.scene.objects:
        obj.select_set(obj == rig or obj in meshes)
    view_layer.objects.active = rig
    return result


def convert_materials(meshes, outline=False):
    """DaskToon's shader on every material of the meshes, with an outline when `outline`; the number changed. No
    outline by default: an imported model has hundreds of bones, and the outline's hull joined to such a mesh makes
    playback slow."""
    from bl_ui import dasktoon_material_convert as convert
    done = 0
    for mat in materials_of(meshes):
        if mat.use_nodes and convert.convert(mat, outline=outline):
            done += 1
    return done


def materials_of(meshes):
    return list(dict.fromkeys(slot.material for obj in meshes for slot in obj.material_slots if slot.material))


def set_outline(meshes, on):
    """Turn the outline of DaskToon's shader on or off on every material of the meshes."""
    from dasktoon_guide.checks import ANIME
    for mat in materials_of(meshes):
        for node in (mat.node_tree.nodes if mat.node_tree is not None else ()):
            if node.bl_idname in ANIME and hasattr(node, "use_outline") and node.use_outline != on:
                node.use_outline = on
