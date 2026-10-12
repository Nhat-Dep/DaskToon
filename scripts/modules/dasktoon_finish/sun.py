# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""What the finish's group cannot see by itself (spec section 4): where the scene's Sun is on the picture, the
direction the light comes from on the picture, and the distance to keep sharp."""

from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

FAR = 1.0e4  # the Sun is this far along its direction from the camera


def find_sun(scene):
    """The scene's first visible Sun, as DaskToon's sun sync finds it."""
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN' and obj.visible_get():
            return obj
    return None


def toward_sun(sun):
    """A Sun shines along its -Z, so the Sun lies along +Z."""
    return (sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()


def sun_on_picture(scene, camera, sun):
    """((x, y) on the picture, 0 to 1 from the bottom left, may lie outside it; True when the Sun is in front)."""
    point = camera.matrix_world.translation + toward_sun(sun) * FAR
    co = world_to_camera_view(scene, camera, point)
    return (co.x, co.y), co.z > 0.0


def light_direction(camera, sun):
    """The direction on the picture (x right, y up, length 1) the light comes from: toward the Sun as the camera sees
    it. Straight ahead or behind, it comes from the top."""
    local = camera.matrix_world.to_quaternion().inverted() @ toward_sun(sun)
    flat = Vector((local.x, local.y))
    return flat.normalized() if flat.length > 1e-6 else Vector((0.0, 1.0))


def _depth(camera, obj):
    """Distance from the camera along its view, as the Depth pass measures it."""
    return -(camera.matrix_world.inverted() @ obj.matrix_world.translation).z


def focus_distance(camera, subject):
    """The camera's focus when its depth of field is on (its focus object, else its distance), else the depth of
    `subject`; None without one."""
    dof = camera.data.dof
    if dof.use_dof:
        return _depth(camera, dof.focus_object) if dof.focus_object is not None else dof.focus_distance
    if subject is None or subject == camera:
        return None
    return _depth(camera, subject)
