# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Helpers shared by the DaskToon tests. Runs inside DaskToon (--background)."""

import os
import sys
import tempfile
import unittest

import bpy

OUT_DIR = os.environ.get("DASKTOON_TEST_OUT") or tempfile.mkdtemp(prefix="dasktoon_test_")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dasktoon_data")


def _drop_legacy_outline_handler():
    """The pre-rewrite outline handler adds Solidify modifiers behind the tests' back."""
    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in list(handlers):
        if getattr(handler, "__name__", "") == "dasktoon_vrm_outline_auto_sync":
            handlers.remove(handler)


def setup_render_scene(resolution=16):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    if scene.world is None:
        scene.world = bpy.data.worlds.new("TestWorld")
    set_world_color((0.0, 0.0, 0.0))
    if scene.camera is None:
        cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        scene.collection.objects.link(cam)
        cam.location = (0.0, 0.0, 5.0)
        scene.camera = cam
    return scene


def reset_scene(resolution=16):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _drop_legacy_outline_handler()
    return setup_render_scene(resolution)


def set_world_color(rgb):
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)


def add_plane(size=4.0):
    bpy.ops.mesh.primitive_plane_add(size=size)
    return bpy.context.active_object


def add_sphere(radius=1.0, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    obj.data.shade_smooth()
    return obj


def add_sun(strength=1.0, rotation=(0.0, 0.0, 0.0), color=(1.0, 1.0, 1.0)):
    data = bpy.data.lights.new("Sun", 'SUN')
    data.energy = strength
    data.color = color
    obj = bpy.data.objects.new("Sun", data)
    obj.rotation_euler = rotation
    bpy.context.scene.collection.objects.link(obj)
    return obj


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.node_tree.nodes.clear()
    return mat


def emission_material(name, rgba, strength=1.0):
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emission = nt.nodes.new('ShaderNodeEmission')
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = strength
    nt.links.new(emission.outputs[0], out.inputs["Surface"])
    return mat


def node_material(name, node_type):
    """Material whose Surface is driven directly by one node of `node_type`."""
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new(node_type)
    nt.links.new(node.outputs[0], out.inputs["Surface"])
    return mat, node


def mix_with_black_material(name, node_type):
    """node -> Mix Shader slot 1, black emission -> slot 2, factor = Is Camera Ray (1, not constant)."""
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new(node_type)
    mix = nt.nodes.new('ShaderNodeMixShader')
    black = nt.nodes.new('ShaderNodeEmission')
    black.inputs["Strength"].default_value = 0.0
    light_path = nt.nodes.new('ShaderNodeLightPath')
    nt.links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(node.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat, node


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def render_pixels(name):
    """Render to a linear EXR; return (flat RGBA list, (width, height))."""
    scene = bpy.context.scene
    path = os.path.join(OUT_DIR, name + ".exr")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    pixels = list(img.pixels)
    size = tuple(img.size)
    bpy.data.images.remove(img)
    return pixels, size


def render_center(name):
    pixels, (w, h) = render_pixels(name)
    i = ((h // 2) * w + w // 2) * 4
    return tuple(pixels[i:i + 4])


def run_tests():
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    result = unittest.main(module="__main__", argv=argv, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
