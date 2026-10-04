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


TEST_HEAD_SEGMENTS = (48, 24)


def add_test_head(radius=0.1, centre=(0.0, 0.0, 1.5), with_armature=True, name="Head"):
    """Face shading test head (face spec 8), upright and facing -Y with the object at the world origin like a
    character: a UV sphere skin with a nose bump and two eye dents, then a hair cap that is a separate island. With an
    armature, every vertex is weighted 1 to bone "Head" of armature "Rig". Returns (head, rig or None);
    head["dt_skin_vertices"] is the number of skin vertices, which come first."""
    import bmesh
    from mathutils import Matrix, Vector
    bm = bmesh.new()
    bm.loops.layers.uv.verify()
    segments, rings = TEST_HEAD_SEGMENTS
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius, calc_uvs=True)
    skin = len(bm.verts)
    for v in bm.verts:
        d = v.co.normalized()
        if d.y < 0.0:
            nose = max(0.0, 1.0 - (d.x / 0.2) ** 2 - ((d.z + 0.15) / 0.2) ** 2)
            dents = sum(max(0.0, 1.0 - ((d.x - side) / 0.16) ** 2 - ((d.z - 0.12) / 0.12) ** 2) for side in (-0.38, 0.38))
            v.co += d * radius * (0.12 * nose - 0.08 * dents)
    hair = Matrix.LocRotScale(Vector((0.0, 0.25 * radius, 0.45 * radius)), None, Vector((1.1, 1.1, 0.7)))
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=radius, matrix=hair, calc_uvs=True)
    bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector(centre))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.shade_smooth()
    head = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(head)
    head["dt_skin_vertices"] = skin
    rig = None
    if with_armature:
        rig = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        bpy.context.scene.collection.objects.link(rig)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bone = rig.data.edit_bones.new("Head")
        bone.head = (centre[0], centre[1], centre[2] - radius)
        bone.tail = (centre[0], centre[1], centre[2] + radius)
        bpy.ops.object.mode_set(mode='OBJECT')
        head.vertex_groups.new(name="Head").add(list(range(len(mesh.vertices))), 1.0, 'REPLACE')
        head.parent = rig
        head.modifiers.new("Armature", 'ARMATURE').object = rig
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == head)
    bpy.context.view_layer.objects.active = head
    return head, rig


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


def shader_output(node):
    """The node's BSDF output when it has one (some DaskToon nodes list a Color output first)."""
    return node.outputs.get("BSDF") or node.outputs[0]


def node_material(name, node_type):
    """Material whose Surface is driven directly by one node of `node_type`."""
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new(node_type)
    nt.links.new(shader_output(node), out.inputs["Surface"])
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
    nt.links.new(shader_output(node), mix.inputs[1])
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


def is_shader_error(rgba):
    """EEVEE draws materials whose shader failed to compile in magenta (1, 0, 1)."""
    return rgba[0] > 0.99 and rgba[1] < 0.01 and rgba[2] > 0.99


def run_tests():
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    result = unittest.main(module="__main__", argv=argv, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
