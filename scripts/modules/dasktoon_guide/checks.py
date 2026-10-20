# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Model Check (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): each check looks at the
character the way DaskToon's automatic tools will (the same functions where there are some) and says OK, WARN (should
be fixed), ERROR (the tools fail on it) or LATER (it needs the rig first), in one sentence.

The character checked: a selected DaskToon rig, or one deforming a selected mesh, means that rig's meshes; otherwise
the selected meshes; nothing selected, every visible mesh."""

from typing import NamedTuple

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

SIZE = (0.5, 3.5)  # metres: a character outside is too small or too big for DaskToon's and Unity's defaults
FLOOR = 0.02  # x the height: the lowest point this near z = 0 stands on the floor
MIDDLE = 0.05  # x the height: where it stands this near x = 0, y = 0 is in the middle
POSE = (0.45, 0.55)  # width / height: below the first the arms hang down, below the second they are low
ANIME = {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}  # DaskToon's shaders (as dasktoon_material_convert)
BLENDED = 8  # vertices blending across a knee or elbow, fewest for its bend fixes to round it
NAMES = 4  # objects named in a sentence, at most


class Result(NamedTuple):
    id: str
    group: str  # 'STANDING', 'MESH', 'MATERIALS' or 'RIG'
    step: str  # the step it belongs to (steps.py), whose page explains it
    status: str  # 'OK', 'WARN', 'ERROR' or 'LATER'
    text: str
    fixable: bool


def _names(objects):
    names = [obj.name for obj in objects]
    return ", ".join(names[:NAMES]) + (", …" if len(names) > NAMES else "")


def humanoid_rig(meshes):
    """The DaskToon humanoid rig deforming `meshes`, or None."""
    from dasktoon_rig import skeleton
    for obj in meshes:
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object is not None and skeleton.is_humanoid(modifier.object):
                return modifier.object
    return None


def character(context):
    """(meshes, rig or None) of the character the selection points at (module docstring)."""
    from dasktoon_rig import skeleton
    selected = [obj for obj in context.selected_objects]
    visible = [obj for obj in context.view_layer.objects if obj.visible_get()]
    rig = next((obj for obj in selected if obj.type == 'ARMATURE' and skeleton.is_humanoid(obj)), None)
    rig = rig or humanoid_rig([obj for obj in selected if obj.type == 'MESH'])
    if rig is not None:
        return [obj for obj in visible if obj.type == 'MESH'
                and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)], rig
    meshes = [obj for obj in selected if obj.type == 'MESH'] or [obj for obj in visible if obj.type == 'MESH']
    return meshes, None


def body_of(meshes, rig):
    """The Body: the rig's Body part when there is one, else the mesh with the most vertices."""
    data = getattr(rig.data, "dasktoon_rig", None) if rig is not None else None
    body = next((p.object for p in (data.parts if data is not None else ()) if p.role == 'BODY'
                 and p.object in meshes), None)
    return body or max(meshes, key=lambda obj: len(obj.data.vertices))


class _Context:
    def __init__(self, context, meshes, rig):
        from dasktoon_rig import facing
        self.context, self.meshes, self.rig = context, meshes, rig
        self.shown = facing._shown(context, meshes) if meshes else None


def _standing(c, fn):
    if c.shown is None:
        return 'LATER', rpt_("No mesh to check")
    return fn(*c.shown)


def check_size(c):
    def size(world, floor, height):
        if SIZE[0] <= height <= SIZE[1]:
            return 'OK', rpt_("%.2f m tall") % height
        return 'WARN', rpt_("%.2f m tall: DaskToon and Unity count in metres, a person is 1 to 2 m") % height
    return _standing(c, size)


def check_floor(c):
    def floor_(world, floor, height):
        if abs(floor) <= FLOOR * height:
            return 'OK', rpt_("Standing on the floor")
        return 'WARN', rpt_("The feet are %.2f m above or below the floor (z = 0)") % floor
    return _standing(c, floor_)


def standing_point(world, floor, height):
    from dasktoon_rig import facing
    legs = facing._lower_legs(world, height, floor)
    return legs.mean(axis=0) if len(legs) else (world[:, :2].min(axis=0) + world[:, :2].max(axis=0)) / 2.0


def check_middle(c):
    def middle(world, floor, height):
        point = standing_point(world, floor, height)
        if np.abs(point).max() <= MIDDLE * height:
            return 'OK', rpt_("In the middle of the scene")
        return 'WARN', rpt_("Standing %.2f m away from the middle of the scene") % float(np.linalg.norm(point))
    return _standing(c, middle)


def check_facing(c):
    from dasktoon_rig import facing

    def facing_(world, floor, height):
        found = facing.feet(world, height, floor)
        if found is None:
            return 'WARN', rpt_("The feet do not tell which way the character faces: from the front view (1) you "
                                "should see its face")
        if facing.turn_to_front(found[1]) == 0.0:
            return 'OK', rpt_("Facing the front (-Y)")
        return 'ERROR', rpt_("Facing another way than the front (-Y): the rig would swap its left and right")
    return _standing(c, facing_)


def check_pose(c):
    def pose(world, floor, height):
        ratio = np.ptp(world[:, 0]) / height
        if ratio >= POSE[1]:
            return 'OK', rpt_("Arms out (T or A pose)")
        if ratio >= POSE[0]:
            return 'WARN', rpt_("The arms are low: a T or A pose (arms 0 to 45 degrees below level) rigs best")
        return 'ERROR', rpt_("The arms hang down: model the character in a T or A pose, the rig finds arms by them")
    return _standing(c, pose)


def check_scale(c):
    negative = [obj for obj in c.meshes if obj.matrix_world.is_negative]
    if negative:
        return 'ERROR', rpt_("Mirrored by a negative scale: %s") % _names(negative)
    uneven = []
    for obj in c.meshes:
        scale = obj.matrix_world.to_scale()
        if max(scale) > min(scale) * (1.0 + 1e-4):
            uneven.append(obj)
    if uneven:
        return 'WARN', rpt_("Stretched by an uneven scale (apply it): %s") % _names(uneven)
    return 'OK', rpt_("Even scale")


def check_normals(c):
    from dasktoon_rig import build
    if not c.meshes:
        return 'LATER', rpt_("No mesh to check")
    body = body_of(c.meshes, c.rig)
    if body.matrix_world.is_negative or not len(body.data.polygons):
        return 'OK', rpt_("Faces point outward")
    ratio = build._signed_volume_ratio(body, np.arange(len(body.data.vertices)))
    if ratio < build.INWARD_RATIO:
        return 'ERROR', rpt_("%s: the faces point inward, so the rig's weights pick the wrong bones") % body.name
    return 'OK', rpt_("Faces point outward")


def check_mirror(c):
    mirrored = [obj for obj in c.meshes if any(m.type == 'MIRROR' for m in obj.modifiers)]
    if mirrored:
        return 'WARN', rpt_("Mirror not applied (the bend fixes skip such meshes): %s") % _names(mirrored)
    return 'OK', rpt_("No Mirror left to apply")


def _sides(obj):
    sides = np.zeros(len(obj.data.polygons), dtype=np.int64)
    obj.data.polygons.foreach_get("loop_total", sides)
    return sides


def check_ngons(c):
    count = sum(int((_sides(obj) > 4).sum()) for obj in c.meshes)
    if count:
        return 'WARN', rpt_("%d faces with more than 4 sides: Unity splits them its own way") % count
    return 'OK', rpt_("Faces of 3 or 4 sides")


def check_parts(c):
    from dasktoon_rig import eye_shapes
    if len(c.meshes) >= 2 or (c.meshes and len(eye_shapes._pieces(c.meshes[0].data)) >= 3):
        return 'OK', rpt_("Parts DaskToon can tell apart")
    return 'WARN', rpt_("The whole character is one piece: keep the hair and clothes as objects or loose pieces of "
                        "their own, so DaskToon tells them apart")


def check_uv(c):
    missing = [obj for obj in c.meshes if not obj.data.uv_layers]
    if missing:
        return 'WARN', rpt_("No UV map (textures and the Unity export need one): %s") % _names(missing)
    return 'OK', rpt_("UV maps")


def used_materials(meshes):
    import dasktoon_export
    return list(dasktoon_export._materials(meshes))


def is_dasktoons(material):
    tree = material.node_tree if material.use_nodes else None
    return tree is not None and any(node.bl_idname in ANIME for node in tree.nodes)


def check_shader(c):
    other = [mat for mat in used_materials(c.meshes) if not is_dasktoons(mat)]
    if other:
        return 'WARN', rpt_("Not DaskToon's shader: %s") % _names(other)
    return 'OK', rpt_("DaskToon's shader")


def unused_slots(obj):
    used = set(np.unique(_material_indexes(obj)).tolist())
    return [i for i in range(len(obj.material_slots)) if i not in used]


def _material_indexes(obj):
    indexes = np.zeros(len(obj.data.polygons), dtype=np.int64)
    obj.data.polygons.foreach_get("material_index", indexes)
    return indexes


def check_unused(c):
    found = [obj for obj in c.meshes if unused_slots(obj)]
    if found:
        return 'WARN', rpt_("Material slots no face uses: %s") % _names(found)
    return 'OK', rpt_("No unused material")


def check_rig(c):
    if c.rig is None:
        return 'ERROR', rpt_("Not rigged yet: the auto rig makes the skeleton, weights and bend fixes")
    return 'OK', rpt_("Rigged by %s") % c.rig.name


def _after_rig(fn):
    def check(c):
        if c.rig is None:
            return 'LATER', rpt_("After the rig")
        return fn(c)
    return check


@_after_rig
def check_rig_check(c):
    data = c.rig.data.dasktoon_rig
    if not data.checked:
        return 'WARN', rpt_("The rig's Check has not run since it was built")
    if len(data.issues):
        return 'WARN', rpt_("The rig's Check found %d spots to look at (Anime Rig › Check)") % len(data.issues)
    return 'OK', rpt_("The rig's Check found nothing")


@_after_rig
def check_joints(c):
    from dasktoon_rig import correctives
    thin = []
    for fix in correctives.fixes(c.rig):
        if not fix.name.endswith(("Knee", "Elbow")):
            continue
        blended = 0
        for obj in c.meshes:
            share = correctives.child_share(c.rig, obj, fix.child)
            blended += int(((share > 0.05) & (share < 0.95)).sum())
        if blended < BLENDED:
            thin.append(fix.name)
    if thin:
        return 'WARN', rpt_("Too few edge loops round %s: add 2 or 3 loops so the joint bends round") % ", ".join(thin)
    return 'OK', rpt_("Enough edge loops round the knees and elbows")


def _moving_key(meshes, slot):
    from dasktoon_rig import expressions
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        base = np.empty(len(key.reference_key.data) * 3)
        key.reference_key.data.foreach_get("co", base)
        for block in key.key_blocks:
            if block != key.reference_key and expressions.slot_of(block.name) == slot:
                co = np.empty_like(base)
                block.data.foreach_get("co", co)
                if np.abs(co - base).max() > expressions.NOTHING:
                    return True
    return False


@_after_rig
def check_eyes(c):
    from dasktoon_rig import eye_shapes
    if eye_shapes.find_eyes(c.rig, c.meshes):
        return 'OK', rpt_("Eyes of loose pieces in front of the face: Sculpt Eye Expressions closes them")
    if _moving_key(c.meshes, "BLINK"):
        return 'OK', rpt_("The eyes close by a shape key of their own")
    return 'WARN', rpt_("No eyes DaskToon can close: build each eye of loose pieces in front of the face, or sculpt a "
                        "blink yourself")


@_after_rig
def check_mouth(c):
    from dasktoon_rig import eye_shapes
    eyes = eye_shapes.find_eyes(c.rig, c.meshes)
    if eyes and (eye_shapes.drawn_mouth(c.rig, c.meshes, eyes) or eye_shapes.piece_mouth(c.rig, c.meshes, eyes)):
        return 'OK', rpt_("A mouth DaskToon finds: joy smiles; for A I U E O use a 2D mouth")
    if _moving_key(c.meshes, "A"):
        return 'OK', rpt_("The mouth opens by a shape key of its own")
    return 'WARN', rpt_("No mouth DaskToon finds: draw it on the face texture, or use a 2D mouth")


@_after_rig
def check_expressions(c):
    if not _moving_key(c.meshes, "BLINK"):
        return 'WARN', rpt_("No blink yet: Sculpt Eye Expressions (or sculpt it yourself)")
    if _has_empty(c.meshes):
        return 'WARN', rpt_("Some expression shape keys move nothing: Fill Empty Expressions")
    return 'OK', rpt_("Expressions ready")


def _has_empty(meshes):
    from dasktoon_rig import expressions
    for obj in meshes:
        key = obj.data.shape_keys
        if key is None:
            continue
        base = np.empty(len(key.reference_key.data) * 3)
        key.reference_key.data.foreach_get("co", base)
        for block in key.key_blocks:
            slot = expressions.slot_of(block.name)
            if block == key.reference_key or slot is None or block.name.lower() == "neutral":
                continue
            co = np.empty_like(base)
            block.data.foreach_get("co", co)
            if np.abs(co - base).max() <= expressions.NOTHING:
                return True
    return False


# (id, group, step, check, has a fix)
CHECKS = (
    ("size", 'STANDING', 'BODY', check_size, True),
    ("floor", 'STANDING', 'BODY', check_floor, True),
    ("middle", 'STANDING', 'BODY', check_middle, True),
    ("facing", 'STANDING', 'BODY', check_facing, True),
    ("pose", 'STANDING', 'BODY', check_pose, False),
    ("scale", 'MESH', 'BODY', check_scale, True),
    ("normals", 'MESH', 'BODY', check_normals, True),
    ("mirror", 'MESH', 'HEAD', check_mirror, True),
    ("ngons", 'MESH', 'CLOTHES', check_ngons, True),
    ("parts", 'MESH', 'HAIR', check_parts, False),
    ("uv", 'MATERIALS', 'MATERIALS', check_uv, True),
    ("shader", 'MATERIALS', 'MATERIALS', check_shader, True),
    ("unused", 'MATERIALS', 'MATERIALS', check_unused, True),
    ("rig", 'RIG', 'RIG', check_rig, True),
    ("rig_check", 'RIG', 'RIG', check_rig_check, True),
    ("joints", 'RIG', 'RIG', check_joints, False),
    ("eyes", 'RIG', 'EXPRESSIONS', check_eyes, False),
    ("mouth", 'RIG', 'EXPRESSIONS', check_mouth, False),
    ("expressions", 'RIG', 'EXPRESSIONS', check_expressions, True),
)
ORDER = tuple(entry[0] for entry in CHECKS)


def character_of(context, objects=None):
    """(meshes, rig) of `objects` (meshes, perhaps a rig), else of the selection."""
    if objects is None:
        return character(context)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    rig = next((obj for obj in objects if obj.type == 'ARMATURE'), None) or humanoid_rig(meshes)
    return meshes, rig


def run(context, objects=None):
    """Every check on the character of `objects` (default: the selection), in ORDER."""
    meshes, rig = character_of(context, objects)
    c = _Context(context, meshes, rig)
    out = []
    for name, group, step, fn, fixable in CHECKS:
        status, text = fn(c)
        out.append(Result(name, group, step, status, text, fixable and status in ('WARN', 'ERROR')))
    return out
