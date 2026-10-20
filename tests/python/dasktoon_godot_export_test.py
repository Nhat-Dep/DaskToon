# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export for Godot 4 (docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md): where it writes, the
files, the materials and the report; with Godot installed, a throwaway project imports the export and the DaskToon
materials sit on the model."""

import json
import math
import os
import re
import sys
import tempfile
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_godot_harness as harness  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gamedata  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets, textures  # noqa: E402

SCRIPT = 'import_script/path="res://DaskToon/Scripts/dasktoon_import.gd"'


def srgb(x):
    return x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1.0 / 2.4) - 0.055


def to_godot(v):
    return [v[0], v[2], -v[1]]


def character(name="Skin", outlined=True):
    tu.reset_scene()
    outline.reset_cache()
    body = tu.add_sphere(segments=16, rings=8)
    body.name = "Body"
    mat, node = tu.node_material(name, 'ShaderNodeAnimeCharacter')
    node.use_outline = outlined
    node.use_rim = True
    node.inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1.0)
    node.inputs["Shadow Threshold"].default_value = 0.4
    tu.assign(body, mat)
    outline.sync_all(bpy.context.scene)
    return body, mat, node


def export(objects, folder=None, name="Hero", **options):
    target = targets.make_target(folder or tempfile.mkdtemp(prefix="dt_godot_"), name, 'GODOT_4')
    settings = dict(include_animation=False, bake_size=32, bake_samples=2, merge_meshes=False)
    settings.update(options)
    rep = dasktoon_export.export_model(bpy.context, target, objects, dasktoon_export.ExportOptions(**settings))
    return target, rep


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def tres(path):
    """{section header: {key: value}} of a Godot text resource; [resource] is the material itself."""
    sections, current = {}, None
    for line in read(path).splitlines():
        if line.startswith("["):
            current = sections.setdefault(line, {})
        elif current is not None and " = " in line:
            key, value = line.split(" = ", 1)
            current[key] = value
    return sections


def resource(sections):
    return sections["[resource]"]


def ext_path(sections, value):
    """res:// path of ExtResource("id")."""
    ident = re.match(r'ExtResource\("([^"]+)"\)', value).group(1)
    header = next(h for h in sections if h.startswith("[ext_resource") and 'id="%s"' % ident in h)
    return re.search(r'path="([^"]+)"', header).group(1)


def color(value):
    return [float(v) for v in re.match(r"Color\(([^)]*)\)", value).group(1).split(",")]


def file_picture(name, size=8):
    path = os.path.join(tempfile.mkdtemp(prefix="dt_godot_tex_"), name + ".png")
    image = bpy.data.images.new(name, size, size)
    image.pixels.foreach_set(np.full(size * size * 4, 0.5, np.float32))
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    return image


class TargetTest(unittest.TestCase):
    def test_a_folder_inside_a_godot_project_writes_into_its_DaskToon_folder(self):
        project = tempfile.mkdtemp(prefix="dt_godot_project_")
        open(os.path.join(project, "project.godot"), "w").close()
        inside = os.path.join(project, "characters")
        os.makedirs(inside)
        target = targets.make_target(inside, "Hero", 'GODOT_4')
        self.assertEqual((target.mode, target.root, target.project),
                         ('PROJECT', os.path.join(project, "DaskToon"), project))

    def test_any_other_folder_gets_a_Name_Godot_folder(self):
        folder = tempfile.mkdtemp(prefix="dt_godot_folder_")
        target = targets.make_target(folder, "Hero", 'GODOT_4')
        self.assertEqual((target.mode, target.root), ('FOLDER', os.path.join(folder, "Hero_Godot", "DaskToon")))

    def test_godot_is_supported(self):
        self.assertIn('GODOT_4', targets.SUPPORTED_ENGINES)
        label = next(item[1] for item in targets.ENGINES if item[0] == 'GODOT_4')
        self.assertNotIn("soon", label)


class LayoutTest(unittest.TestCase):
    def test_model_materials_shaders_and_import_script(self):
        body, _mat, _node = character()
        target, rep = export([body])
        root = target.root
        for rel in ("Shaders/dasktoon_core.gdshaderinc", "Shaders/anime_bsdf.gdshaderinc",
                    "Shaders/anime_bsdf.gdshader", "Shaders/anime_outline.gdshader", "Scripts/dasktoon_import.gd",
                    "Hero/Hero.glb", "Hero/Hero.glb.import", "Hero/Hero.dasktoon.json", "Hero/Materials/Skin.tres"):
            self.assertTrue(os.path.isfile(os.path.join(root, rel)), rel)
        self.assertEqual(rep.materials, ["Skin"])
        self.assertEqual(rep.model, "Hero/Hero.glb")
        self.assertIn(SCRIPT, read(os.path.join(root, "Hero", "Hero.glb.import")))
        data = json.loads(read(os.path.join(root, "Hero", "Hero.dasktoon.json")))
        self.assertEqual(data["materials"], {"Skin": "Materials/Skin.tres"})

    def test_folder_mode_has_a_readme_beside_the_DaskToon_folder(self):
        body, _mat, _node = character()
        target, _rep = export([body])
        readme = read(os.path.join(os.path.dirname(target.root), "README.txt"))
        self.assertIn("Godot", readme)
        self.assertIn("DaskToon", readme)

    def test_a_second_export_keeps_what_godot_wrote_into_the_import_file(self):
        body, _mat, _node = character()
        folder = tempfile.mkdtemp(prefix="dt_godot_again_")
        target, _rep = export([body], folder)
        path = os.path.join(target.root, "Hero", "Hero.glb.import")
        text = read(path).replace('importer="scene"', 'importer="scene"\nuid="uid://b123"')
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        export([body], folder)
        text = read(path)
        self.assertIn('uid="uid://b123"', text)
        self.assertEqual(text.count("import_script/path="), 1)
        self.assertIn(SCRIPT, text)

    def test_report_speaks_of_godot(self):
        body, _mat, _node = character()
        tu.add_sun(3.0)
        _target, rep = export([body])
        text = "\n".join(rep.lines())
        self.assertIn("Godot", text)
        self.assertNotIn("Unity", text)
        self.assertIn("DirectionalLight3D", text)
        self.assertIn("%.3f" % (3.0 / math.pi), text)


class MaterialTest(unittest.TestCase):
    def material(self, body, name="Skin"):
        target, rep = export([body])
        return target, rep, tres(os.path.join(target.root, "Hero", "Materials", name + ".tres"))

    def test_values_in_godots_names_and_colours_as_srgb(self):
        body, _mat, _node = character()
        _target, _rep, sections = self.material(body)
        res = resource(sections)
        self.assertEqual(ext_path(sections, res["shader"]), "res://DaskToon/Shaders/anime_bsdf.gdshader")
        for got, want in zip(color(res["shader_parameter/base_color"]), (srgb(0.8), srgb(0.2), srgb(0.1), 1.0)):
            self.assertAlmostEqual(got, want, places=4)
        self.assertAlmostEqual(float(res["shader_parameter/shadow_threshold"]), 0.4, places=5)
        self.assertEqual(res["shader_parameter/use_rim"], "true")
        self.assertEqual(res["shader_parameter/use_ramp"], "false")

    def test_outline_is_the_next_pass(self):
        body, mat, node = character()
        _target, _rep, sections = self.material(body)
        res = resource(sections)
        ident = re.match(r'SubResource\("([^"]+)"\)', res["next_pass"]).group(1)
        outline_section = next(v for h, v in sections.items() if h.startswith("[sub_resource") and ident in h)
        self.assertEqual(ext_path(sections, outline_section["shader"]),
                         "res://DaskToon/Shaders/anime_outline.gdshader")
        self.assertAlmostEqual(float(outline_section["shader_parameter/outline_width"]),
                               node.inputs["Outline Width"].default_value, places=5)
        self.assertEqual(outline_section["shader_parameter/outline_uv"],
                         str(body.data.uv_layers.find("DT_OutlineN")))

    def test_without_outline_there_is_no_next_pass(self):
        body, _mat, _node = character(outlined=False)
        _target, _rep, sections = self.material(body)
        self.assertNotIn("next_pass", resource(sections))

    def test_culling_and_alpha_pick_the_shader(self):
        cases = ((True, 'DITHERED', 0.5, "anime_bsdf_cull_clip.gdshader"),
                 (False, 'BLENDED', 0.5, "anime_bsdf_blend.gdshader"),
                 (True, 'DITHERED', 1.0, "anime_bsdf_cull.gdshader"))
        for culling, method, alpha, shader in cases:
            body, mat, node = character(outlined=False)
            mat.use_backface_culling = culling
            mat.surface_render_method = method
            node.inputs["Alpha"].default_value = alpha
            _target, _rep, sections = self.material(body)
            self.assertEqual(ext_path(sections, resource(sections)["shader"]), "res://DaskToon/Shaders/" + shader)

    def test_image_texture_is_copied_and_read(self):
        body, mat, node = character(outlined=False)
        image = file_picture("Skin Paint")
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        mat.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
        target, _rep, sections = self.material(body)
        res = resource(sections)
        path = ext_path(sections, res["shader_parameter/base_map"])
        self.assertEqual(path, "res://DaskToon/Hero/Textures/Skin_Base.png")
        self.assertTrue(os.path.isfile(os.path.join(target.root, "Hero", "Textures", "Skin_Base.png")))
        self.assertEqual(res["shader_parameter/base_map_on"], "true")

    def test_ramp_is_a_strip_godot_keeps_sharp(self):
        body, _mat, node = character(outlined=False)
        node.shading_mode = 'RAMP'
        target, _rep, sections = self.material(body)
        res = resource(sections)
        self.assertEqual(res["shader_parameter/use_ramp"], "true")
        path = ext_path(sections, res["shader_parameter/ramp_map"])
        self.assertEqual(path, "res://DaskToon/Hero/Textures/Skin_Ramp.png")
        settings = read(os.path.join(target.root, "Hero", "Textures", "Skin_Ramp.png.import"))
        self.assertIn("compress/mode=0", settings)
        self.assertIn("mipmaps/generate=false", settings)

    def test_world_colour_is_the_ambient(self):
        body, _mat, _node = character()
        tu.set_world_color((0.05, 0.06, 0.08))
        _target, _rep, sections = self.material(body)
        got = color(resource(sections)["shader_parameter/world_ambient"])
        for g, want in zip(got, (srgb(0.05), srgb(0.06), srgb(0.08))):
            self.assertAlmostEqual(g, want, places=4)

    def test_other_shading_nodes_use_anime_bsdf_for_now_and_say_so(self):
        tu.reset_scene()
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Cel", 'ShaderNodeAnimeCel')
        tu.assign(body, mat)
        target, rep = export([body])
        sections = tres(os.path.join(target.root, "Hero", "Materials", "Cel.tres"))
        self.assertEqual(ext_path(sections, resource(sections)["shader"]),
                         "res://DaskToon/Shaders/anime_bsdf.gdshader")
        self.assertTrue(any("Cel" in w and "Anime BSDF" in w for w in rep.warnings), rep.warnings)


class MergeTest(unittest.TestCase):
    def test_the_characters_meshes_go_out_as_one_with_every_material(self):
        import dasktoon_export_merge_test as merge_test
        merge_test.built()
        objects = [obj for obj in bpy.context.view_layer.objects if obj.type in ('MESH', 'ARMATURE')]
        target, rep = export(objects, merge_meshes=True, export_materials=False)
        self.assertEqual(rep.merged[1], "Body")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(target.root, "Hero", "Hero.glb"))
        # The glTF importer adds an Icosphere, the bones' shape, in a collection of its own.
        meshes = [obj for obj in bpy.context.scene.collection.objects if obj.type == 'MESH']
        self.assertEqual([obj.name for obj in meshes], ["Body"])
        self.assertEqual(sorted(slot.material.name for slot in meshes[0].material_slots),
                         sorted(name + " Material" for name, _role in merge_test.PARTS))


@unittest.skipUnless(harness.godot_exe(), harness.SKIP_REASON)
class GodotImportTest(unittest.TestCase):
    def test_godot_imports_the_model_with_the_DaskToon_materials(self):
        root = harness.new_project()
        body, mat, _node = character()
        body.data.uv_layers.new(name="Second")
        cloth, _cloth_node = tu.node_material("Cloth", 'ShaderNodeAnimeCharacter')
        cloth.use_backface_culling = True
        body.data.materials.append(cloth)
        for polygon in body.data.polygons:
            polygon.material_index = 1 if polygon.center.z < 0.0 else 0
        outline.sync_all(bpy.context.scene)
        _target, rep = export([body], root)
        self.assertEqual(sorted(rep.materials), ["Cloth", "Skin"])
        mesh = body.data
        uv_index = mesh.uv_layers.find("DT_OutlineN")
        self.assertEqual(uv_index, 2)  # past UV and UV2: Godot puts it in CUSTOM0
        smooth = gamedata.smoothed_vertex_normals(mesh)
        normals = [{"p": to_godot(v.co), "n": to_godot(s)} for v, s in zip(mesh.vertices, smooth)]
        output = harness.import_project(root)
        result, _output = harness.run_script(root, "dasktoon_check", {
            "model": "res://DaskToon/Hero/Hero.glb", "params": ["base_color", "outline_width", "outline_uv"],
            "outline": {"mesh": "Body", "uv": uv_index, "normals": normals}})
        self.assertTrue(result["ok"], result.get("error"))
        surfaces = {s.get("name"): s for s in result["meshes"]["Body"]}
        self.assertEqual(set(surfaces), {"Skin", "Cloth"}, output[-2000:])
        self.assertEqual(surfaces["Skin"]["material"], "res://DaskToon/Hero/Materials/Skin.tres")
        self.assertEqual(surfaces["Skin"]["shader"], "res://DaskToon/Shaders/anime_bsdf.gdshader")
        self.assertEqual(surfaces["Skin"]["next_pass"], "res://DaskToon/Shaders/anime_outline.gdshader")
        self.assertEqual(surfaces["Cloth"]["shader"], "res://DaskToon/Shaders/anime_bsdf_cull.gdshader")
        self.assertEqual(surfaces["Cloth"]["next_pass"], "")
        decoded = result["outline"]
        self.assertGreater(decoded["matched"], 0.9 * decoded["vertices"])
        self.assertLess(decoded["maxNormalAngle"], 2.0)


if __name__ == "__main__":
    tu.run_tests()
