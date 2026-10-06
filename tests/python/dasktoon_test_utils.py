# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Helpers shared by the DaskToon tests. Runs inside DaskToon (--background)."""

import os
import sys
import tempfile
import types
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

    def sphere(segments, rings, matrix):
        bm = bmesh.new()
        bm.loops.layers.uv.verify()
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius, matrix=matrix,
                                  calc_uvs=True)
        return bm

    # Skin and hair are built apart and joined with from_mesh: create_uvsphere reuses freed vertex slots, so a second
    # sphere in the same BMesh would interleave its vertices with the first one's.
    skin_bm = sphere(*TEST_HEAD_SEGMENTS, Matrix.Translation(centre))
    for v in skin_bm.verts:
        d = (v.co - Vector(centre)).normalized()
        if d.y < 0.0:
            nose = max(0.0, 1.0 - (d.x / 0.2) ** 2 - ((d.z + 0.15) / 0.2) ** 2)
            dents = sum(max(0.0, 1.0 - ((d.x - side) / 0.16) ** 2 - ((d.z - 0.12) / 0.12) ** 2) for side in (-0.38, 0.38))
            v.co += d * radius * (0.12 * nose - 0.08 * dents)
    hair_bm = sphere(24, 12, Matrix.LocRotScale(Vector(centre) + Vector((0.0, 0.25 * radius, 0.45 * radius)), None,
                                                Vector((1.1, 1.1, 0.7))))
    mesh, hair = bpy.data.meshes.new(name), bpy.data.meshes.new(name + "Hair")
    skin_bm.to_mesh(mesh)
    hair_bm.to_mesh(hair)
    skin = len(skin_bm.verts)
    skin_bm.free()
    hair_bm.free()
    joined = bmesh.new()
    joined.from_mesh(mesh)
    joined.from_mesh(hair)
    joined.to_mesh(mesh)
    joined.free()
    bpy.data.meshes.remove(hair)
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


class Props:
    """Operator properties a draw function sets (RecordingLayout.operator returns one)."""


class RecordingLayout:
    """Stands in for UILayout in draw tests. Each operator, menu, label, prop and separator is logged as
    (kind, name, text, icon, enabled, props); sub-layouts share the log and pass `enabled` down. Any other call
    (template_ID, ...) is logged as ("call", name, ...) and returns a sub-layout."""

    def __init__(self, log=None, parent=None):
        self.log = [] if log is None else log
        self.parent = parent
        self.enabled = True

    def is_enabled(self):
        layout = self
        while layout is not None:
            if not layout.enabled:
                return False
            layout = layout.parent
        return True

    def _add(self, kind, name, text="", icon='NONE', props=None):
        self.log.append((kind, name, text, icon, self.is_enabled(), props))

    def _child(self, *_args, **_kwargs):
        return RecordingLayout(self.log, self)

    split = column = row = box = _child

    def operator(self, idname, text="", icon='NONE', **_kwargs):
        props = Props()
        self._add("operator", idname, text, icon, props)
        return props

    def menu(self, idname, text="", icon='NONE', **_kwargs):
        self._add("menu", idname, text, icon)

    def label(self, text="", icon='NONE', **_kwargs):
        self._add("label", "", text, icon)

    def prop(self, _data, name, text="", icon='NONE', **_kwargs):
        self._add("prop", name, text, icon)

    def separator(self, **_kwargs):
        self._add("separator", "")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*_args, **_kwargs):
            self._add("call", name)
            return RecordingLayout(self.log, self)
        return call


def draw(menu, context=None):
    """The log of `menu`'s draw: a Menu or Header class, or anything with draw(self, context)."""
    layout = RecordingLayout()
    menu.draw(types.SimpleNamespace(layout=layout), context or bpy.context)
    return layout.log


def operators(log):
    """[(idname, text)] of the logged operators, enabled or not."""
    return [(entry[1], entry[2]) for entry in log if entry[0] == "operator"]


def labels(log):
    return [entry[2] for entry in log if entry[0] == "label"]


def run_tests():
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    result = unittest.main(module="__main__", argv=argv, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
