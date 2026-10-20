# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Model Check's fixes (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): one a check that DaskToon
can put right by itself, each doing what a newcomer would do by hand (the menu it stands for in its docstring)."""

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

from . import checks

HEIGHT = 1.6  # metres: the size the Size fix gives


def _tops(meshes, rig):
    """The objects to move: the character's meshes and rig, without those that hang from another of them."""
    objects = list(meshes) + ([rig] if rig is not None else [])
    moving = set(objects)

    def hangs(obj):
        parent = obj.parent
        while parent is not None:
            if parent in moving:
                return True
            parent = parent.parent
        return False
    return [obj for obj in objects if not hangs(obj)]


def _move(context, meshes, rig, matrix):
    for obj in _tops(meshes, rig):
        obj.matrix_world = matrix @ obj.matrix_world
    context.view_layer.update()


def _apply_transforms(context, objects, rotation=False, scale=True):
    """Object › Apply › Rotation / Scale on `objects` (meshes whose data no other object shares)."""
    objects = [obj for obj in objects if obj.data is None or obj.data.users == 1]
    if not objects:
        return
    with context.temp_override(selected_editable_objects=objects, selected_objects=objects, active_object=objects[0],
                               object=objects[0]):
        bpy.ops.object.transform_apply(location=False, rotation=rotation, scale=scale)


def fix_size(context, meshes, rig):
    """Scale the character to HEIGHT about where it stands, then apply the scale."""
    world, floor, height = checks._Context(context, meshes, rig).shown
    point = checks.standing_point(world, floor, height)
    about = Matrix.Translation((point[0], point[1], floor))
    _move(context, meshes, rig, about @ Matrix.Scale(HEIGHT / height, 4) @ about.inverted())
    _apply_transforms(context, meshes)


def fix_floor(context, meshes, rig):
    """Move the character down (or up) onto the floor."""
    _world, floor, _height = checks._Context(context, meshes, rig).shown
    _move(context, meshes, rig, Matrix.Translation((0.0, 0.0, -floor)))


def fix_middle(context, meshes, rig):
    """Move the character to the middle of the scene."""
    world, floor, height = checks._Context(context, meshes, rig).shown
    point = checks.standing_point(world, floor, height)
    _move(context, meshes, rig, Matrix.Translation((-point[0], -point[1], 0.0)))


def fix_facing(context, meshes, rig):
    """Turn the character round where it stands to face the front (-Y), as its feet tell."""
    from dasktoon_rig import facing
    facing.face_front(context, _tops(meshes, rig), body=meshes)


def fix_scale(context, meshes, rig):
    """Object › Apply › Scale on the meshes stretched by an uneven scale."""
    uneven = []
    for obj in meshes:
        scale = obj.matrix_world.to_scale()
        if not obj.matrix_world.is_negative and max(scale) > min(scale) * (1.0 + 1e-4):
            uneven.append(obj)
    _apply_transforms(context, uneven)


def fix_normals(context, meshes, rig):
    """Mesh › Normals › Recalculate Outside on the Body."""
    body = checks.body_of(meshes, rig)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()


def fix_mirror(context, meshes, rig):
    """Apply the Mirror modifiers of the meshes (not those with shape keys, which Blender cannot apply under)."""
    for obj in meshes:
        if obj.data.shape_keys is not None:
            continue
        for modifier in [m for m in obj.modifiers if m.type == 'MIRROR']:
            with context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_apply(modifier=modifier.name)


def fix_ngons(context, meshes, rig):
    """Split the faces of more than 4 sides into triangles (Face › Triangulate Faces on them)."""
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        ngons = [f for f in bm.faces if len(f.verts) > 4]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
            bm.to_mesh(obj.data)
            obj.data.update()
        bm.free()


def fix_uv(context, meshes, rig):
    """The anime unwrap (dasktoon_uv) on the meshes without a UV map, together."""
    from dasktoon_uv import unwrap
    missing = [obj for obj in meshes if not obj.data.uv_layers]
    if missing:
        unwrap.unwrap(context, missing, rig, tight=False)  # quick: Anime Unwrap packs tighter


def fix_shader(context, meshes, rig):
    """Use DaskToon Shader on every material a face uses that is not DaskToon's."""
    from bl_ui import dasktoon_material_convert as convert
    for mat in checks.used_materials(meshes):
        if not checks.is_dasktoons(mat):
            convert.convert(mat)


def fix_unused(context, meshes, rig):
    """Remove the material slots no face uses (Material › Remove Unused Slots)."""
    for obj in meshes:
        for index in reversed(checks.unused_slots(obj)):
            obj.data.materials.pop(index=index)


def fix_rig(context, meshes, rig):
    """The auto rig: Add › Armature › Anime Humanoid with the character's meshes selected."""
    view_layer = context.view_layer
    for obj in view_layer.objects:
        obj.select_set(obj in meshes)
    view_layer.objects.active = checks.body_of(meshes, None)
    bpy.ops.dasktoon.rig_add_humanoid()


def fix_rig_check(context, meshes, rig):
    """Anime Rig › Check › Check."""
    from dasktoon_rig import check
    check.run(context, rig)


def fix_expressions(context, meshes, rig):
    """Fill Empty Expressions on every mesh, then Sculpt Eye Expressions when there is no blink yet."""
    from dasktoon_rig import expressions, eye_shapes
    for obj in meshes:
        if obj.data.shape_keys is not None:
            expressions.fill(obj)
    if not checks._moving_key(meshes, "BLINK"):
        eye_shapes.sculpt(rig, meshes)


FIXES = {"size": fix_size, "floor": fix_floor, "middle": fix_middle, "facing": fix_facing, "scale": fix_scale,
         "normals": fix_normals, "mirror": fix_mirror, "ngons": fix_ngons, "uv": fix_uv, "shader": fix_shader,
         "unused": fix_unused, "rig": fix_rig, "rig_check": fix_rig_check, "expressions": fix_expressions}


def run(context, check, objects=None):
    """Run the fix of `check` on the character of `objects` (default: the selection)."""
    meshes, rig = checks.character_of(context, objects)
    FIXES[check](context, meshes, rig)
    context.view_layer.update()
