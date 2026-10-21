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
import struct
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


def glb_json(path):
    """The JSON chunk of a binary glTF."""
    with open(path, "rb") as f:
        data = f.read()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + length])


def morph_targets(path):
    return [t for mesh in glb_json(path)["meshes"] for p in mesh["primitives"] for t in p.get("targets", [])]


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

    def test_report_gives_the_godot_settings_of_the_anime_look(self):
        # tdt in Godot (2026-10-21): at Godot's shadow Normal Bias 2 the eyelids and the fringe shade the eyes in
        # speckles that EEVEE leaves lit, 4 matches; without MSAA the 2 mm outlines break into dots.
        body, _mat, _node = character()
        _target, rep = export([body])
        text = "\n".join(rep.lines())
        self.assertIn("Normal Bias to 4", text)
        self.assertIn("MSAA 3D", text)


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
        # Written beside it, so Godot imports it before the model (the import script loads the material).
        settings = os.path.join(target.root, "Hero", "Textures", "Skin_Base.png.import")
        self.assertIn('importer="texture"', read(settings))
        with open(settings, "w", encoding="utf-8") as f:
            f.write(read(settings) + '\nuid="uid://keepme"\n')
        export([body], os.path.dirname(os.path.dirname(target.root)))
        self.assertIn('uid="uid://keepme"', read(settings))

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

    def test_each_shading_node_has_its_shader(self):
        for node_type, shader in (('ShaderNodeAnimeCel', "anime_cel"), ('ShaderNodeAnimeEye', "anime_eye"),
                                  ('ShaderNodeDaskCel', "dask_cel")):
            tu.reset_scene()
            body = tu.add_sphere(segments=8, rings=4)
            mat, _node = tu.node_material("Mat", node_type)
            mat.use_backface_culling = True
            tu.assign(body, mat)
            target, rep = export([body])
            sections = tres(os.path.join(target.root, "Hero", "Materials", "Mat.tres"))
            self.assertEqual(ext_path(sections, resource(sections)["shader"]),
                             "res://DaskToon/Shaders/%s_cull.gdshader" % shader)
            self.assertFalse(any("Anime BSDF" in w for w in rep.warnings), rep.warnings)

    def test_hair_keeps_its_angel_ring(self):
        import dasktoon_unity_render_test as unity_render
        tu.reset_scene()
        body = tu.add_sphere(segments=8, rings=4)
        tu.assign(body, unity_render.hair())
        target, _rep = export([body])
        res = resource(tres(os.path.join(target.root, "Hero", "Materials", "hair.tres")))
        self.assertEqual(res["shader_parameter/use_angel_ring"], "true")
        self.assertIn("shader_parameter/ring_intensity", res)


def finish_on(layers, **values):
    """The scene's illustration finish on with only `layers`, and `values`."""
    from dasktoon_finish import settings
    finish = bpy.context.scene.dasktoon_finish
    finish.enabled = True
    for key in settings.LAYER_KEYS:
        setattr(finish, key, key in layers)
    for key, value in values.items():
        setattr(finish, key, value)
    return finish


class FinishTest(unittest.TestCase):
    """The illustration finish's Painting Colors layers (and Vignette) go to Godot as a screen layer to add to a scene
    (<model>_finish.tscn); the layers Godot does not have are named in the report."""

    def test_the_painting_colours_go_to_godot(self):
        body, _mat, _node = character()
        finish_on(("grade", "color", "glow"), saturation=1.3, shadow_tint=(0.5, 0.4, 0.9))
        target, rep = export([body])
        folder = os.path.join(target.root, "Hero")
        sections = tres(os.path.join(folder, "Hero_finish.tres"))
        res = resource(sections)
        self.assertEqual(ext_path(sections, res["shader"]), "res://DaskToon/Shaders/dasktoon_finish.gdshader")
        self.assertEqual((res["shader_parameter/grade_on"], res["shader_parameter/color_on"],
                          res["shader_parameter/gradient_on"], res["shader_parameter/vignette_on"]),
                         ("true", "true", "false", "false"))
        self.assertAlmostEqual(float(res["shader_parameter/saturation"]), 1.3, places=5)
        self.assertEqual(res["shader_parameter/shadow_tint"], "Vector3(0.5, 0.4, 0.9)")  # colors as seen, unchanged
        scene_text = read(os.path.join(folder, "Hero_finish.tscn"))
        self.assertIn('path="res://DaskToon/Hero/Hero_finish.tres"', scene_text)
        self.assertIn('path="res://DaskToon/Scripts/dasktoon_finish.gd"', scene_text)
        self.assertTrue(os.path.isfile(os.path.join(target.root, "Shaders", "dasktoon_finish.gdshader")))
        text = "\n".join(rep.lines())
        self.assertIn("Hero/Hero_finish.tscn", text)
        self.assertIn("Soft Glow", text)  # on in DaskToon, not in Godot

    def test_without_the_finish_there_is_no_screen_layer(self):
        body, _mat, _node = character()
        target, rep = export([body])
        self.assertFalse(os.path.exists(os.path.join(target.root, "Hero", "Hero_finish.tscn")))
        self.assertEqual(rep.finish, "")


class ShapeKeyTest(unittest.TestCase):
    def test_shape_keys_change_normals(self):
        body, _mat, _node = character(outlined=False)
        body.shape_key_add(name="Basis")
        body.shape_key_add(name="Smile").data[0].co.z += 0.1
        target, _rep = export([body])
        found = morph_targets(os.path.join(target.root, "Hero", "Hero.glb"))
        self.assertTrue(found and all("NORMAL" in t for t in found), found)

    def test_shape_keys_of_a_face_shaded_model_keep_its_normals(self):
        from bl_ui import dasktoon_face_shading as face_shading
        tu.reset_scene()
        head, _rig = tu.add_test_head(with_armature=False)
        face_shading.setup(head, selected=range(len(head.data.vertices)))
        head.shape_key_add(name="Basis")
        head.shape_key_add(name="Smile").data[0].co.z += 0.01
        target, rep = export([head])
        self.assertEqual(rep.face_meshes, [head.name])
        found = morph_targets(os.path.join(target.root, "Hero", "Hero.glb"))
        self.assertTrue(found and not any("NORMAL" in t for t in found), found)


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
        body, mat, node = character()
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = file_picture("Skin Paint")
        mat.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
        body.data.uv_layers.new(name="Second")
        body.shape_key_add(name="Basis")
        blink = body.shape_key_add(name="Blink")
        blink.data[0].co.z += 0.01
        blink.value = 0.4  # on in DaskToon: Godot leaves glTF's default weights out
        smile = body.shape_key_add(name="Smile")
        smile.data[1].co.z += 0.01
        smile.value = 0.0
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
        self.assertNotIn("Failed loading resource", output)  # the textures were imported before the model
        result, _output = harness.run_script(root, "dasktoon_check", {
            "model": "res://DaskToon/Hero/Hero.glb", "params": ["base_color", "base_map", "outline_width",
                                                                 "outline_uv"],
            "shapes": ["Blink", "Smile"],
            "outline": {"mesh": "Body", "uv": uv_index, "normals": normals}})
        self.assertTrue(result["ok"], result.get("error"))
        surfaces = {s.get("name"): s for s in result["meshes"]["Body"]}
        self.assertEqual(set(surfaces), {"Skin", "Cloth"}, output[-2000:])
        self.assertEqual(surfaces["Skin"]["material"], "res://DaskToon/Hero/Materials/Skin.tres")
        self.assertEqual(surfaces["Skin"]["shader"], "res://DaskToon/Shaders/anime_bsdf.gdshader")
        self.assertEqual(surfaces["Skin"]["params"]["base_map"], "res://DaskToon/Hero/Textures/Skin_Base.png")
        self.assertEqual(surfaces["Skin"]["next_pass"], "res://DaskToon/Shaders/anime_outline.gdshader")
        self.assertEqual(surfaces["Cloth"]["shader"], "res://DaskToon/Shaders/anime_bsdf_cull.gdshader")
        self.assertEqual(surfaces["Cloth"]["next_pass"], "")
        self.assertAlmostEqual(result["shapes"]["Body/Blink"], 0.4, places=5)
        self.assertEqual(result["shapes"]["Body/Smile"], 0.0)
        decoded = result["outline"]
        self.assertGreater(decoded["matched"], 0.9 * decoded["vertices"])
        self.assertLess(decoded["maxNormalAngle"], 2.0)


if __name__ == "__main__":
    tu.run_tests()
