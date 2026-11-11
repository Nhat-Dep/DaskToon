# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The .dlive model faces the front (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md, rulings): DaskLive's
camera looks at a character facing -Y in DaskToon (+Z in glTF and Godot), as DaskToon's standard skeleton does. A
character built facing another way (+Y is common in models from elsewhere) is turned on the export's temporary copies.

Which way it faces: a DaskToon rig's own front; else the eyes of the face the sculpting finds (dasktoon_rig.face_frame,
the eyes lie in front of the head's middle); else the feet (dasktoon_rig.facing). A turn is a multiple of a quarter."""

import numpy as np
from mathutils import Vector


def _rig_front(rig):
    if rig is None or rig.data.bones.get("Head") is None or getattr(rig.data, "dasktoon_rig", None) is None:
        return None
    front = rig.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))
    return (front.x, front.y) if Vector((front.x, front.y)).length > 1e-6 else None


def _face_front(context, meshes, rig):
    from dasktoon_rig import face_frame
    with face_frame.located(context, meshes, rig) as temp:
        if temp is None:
            return None
        ahead = -np.array(temp.matrix_world.col[1][:2])  # the temporary head's -Y is the face's front
    return tuple(ahead) if np.linalg.norm(ahead) > 1e-6 else None


def _feet_front(context, meshes):
    from dasktoon_rig import facing
    found = facing._shown(context, meshes)
    if found is None:
        return None
    world, floor, height = found
    standing = facing.feet(world, height, floor)
    return tuple(standing[1]) if standing is not None else None


def direction(context, objects, rig):
    """(x, y) the character made of `objects` faces in the scene, and what told it ('rig', 'face', 'feet'); (None,
    None) when nothing tells."""
    meshes = [obj for obj in objects if obj.type == 'MESH']
    found = _rig_front(rig)
    if found is not None:
        return found, 'rig'
    found = _face_front(context, meshes, rig) if meshes else None
    if found is not None:
        return found, 'face'
    found = _feet_front(context, meshes) if meshes else None
    if found is not None:
        return found, 'feet'
    return None, None


def turn_to_front(context, objects, rig):
    """Turn `objects` (temporary copies) to face -Y when they face another way; returns the turn in radians (0 when
    none) and what told the way."""
    from dasktoon_rig import facing
    way, told = direction(context, objects, rig)
    if way is None:
        return 0.0, None
    angle = facing.turn_to_front(way)
    if angle != 0.0:
        meshes = [obj for obj in objects if obj.type == 'MESH']
        facing.turn(context, list(objects), angle, body=meshes or None)
    return angle, told
