# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon Scene a new model can start from (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md,
section 6): no cube, a Sun so face shading and Light Vector follow it, a camera looking at the origin, the DaskToon
Anime engine and the Standard view."""

import math

import bpy
from mathutils import Vector

ENGINE = 'DASKTOON_ANIME'
SUN_LOCATION = (2.0, -2.0, 4.0)
SUN_ROTATION = (math.radians(50.0), 0.0, math.radians(30.0))
CAMERA_LOCATION = (0.0, -8.0, 2.0)


def build(scene):
    """Add the Sun and the camera to `scene` (expected empty) and set its engine and view. Returns (sun, camera)."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.location = SUN_LOCATION
    sun.rotation_euler = SUN_ROTATION
    scene.collection.objects.link(sun)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.location = CAMERA_LOCATION
    camera.rotation_euler = (-Vector(CAMERA_LOCATION)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = ENGINE
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    return sun, camera
