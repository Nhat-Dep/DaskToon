# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""thumbnail.png of a .dlive (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md): a small render of the model
in a scene of its own, seen from the front. It can fail (no GPU, a shader that does not compile); the export then goes
on without one."""

import os

import bpy
from mathutils import Vector


def render(objects, path, size=256):
    """Render `objects` seen from the front (the character faces -Y) to `path`; True when the file was written."""
    meshes = [o for o in objects if o.type == 'MESH']
    if not meshes:
        return False
    corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    low = Vector((min(c[i] for c in corners) for i in range(3)))
    high = Vector((max(c[i] for c in corners) for i in range(3)))
    centre, extent = (low + high) / 2.0, max((high - low).z, (high - low).x, 1e-3)
    scene = bpy.data.scenes.new("dlive thumbnail")
    camera_data = bpy.data.cameras.new("dlive thumbnail")
    camera = bpy.data.objects.new("dlive thumbnail", camera_data)
    linked = []
    try:
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.resolution_x = scene.render.resolution_y = size
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.filepath = path
        scene.world = bpy.context.scene.world
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = extent * 1.1
        camera.location = (centre.x, centre.y - extent * 3.0, centre.z)
        camera.rotation_euler = (1.5707963, 0.0, 0.0)
        scene.collection.objects.link(camera)
        scene.camera = camera
        for obj in objects:
            try:
                scene.collection.objects.link(obj)
                linked.append(obj)
            except RuntimeError:
                pass
        bpy.ops.render.render(scene=scene.name, write_still=True)
        return os.path.isfile(path)
    finally:
        for obj in linked:
            scene.collection.objects.unlink(obj)
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera)
        bpy.data.cameras.remove(camera_data)
