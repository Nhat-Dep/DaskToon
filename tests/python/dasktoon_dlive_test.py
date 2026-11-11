# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskLive export and import (docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md; format
D:\\DaskLive\\docs\\dlive-format.md): the archive and its schema, material values equal to the Godot export's, expressions
made on copies (the file unchanged), the round trip and the version check."""

import json
import os
import re
import sys
import tempfile
import unittest
import zipfile

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_expressions_eyes_test as et  # noqa: E402
import dasktoon_expressions_mouth_test as mt  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_godot_export_test as gt  # noqa: E402
import dasktoon_dlive  # noqa: E402
from dasktoon_dlive import importer  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402

FIXTURE = os.environ.get("DASKTOON_DLIVE_FIXTURE_DIR")


def character(plain=False):
    """A rigged character with eyes and a painted face but no expressions; the Body has an outlined DaskToon material
    with a texture, the Shirt a plain one."""
    rig, objs, eyes = et.character()
    face = mt.face_with_slit(rig)
    cavity = et.eyes_object(rig, name="Cavity", sides=(1.0,), pieces=mt.INSIDE, depth=-0.5)
    teeth = et.eyes_object(rig, name="Teeth", sides=(1.0,), pieces=mt.TEETH, depth=-0.55)
    outline.reset_cache()
    for obj in objs.values():
        obj.modifiers.new("Armature", 'ARMATURE').object = rig
    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.use_outline = not plain
    node.inputs["Base Color"].default_value = (0.8, 0.5, 0.4, 1.0)
    image = bpy.data.images.new("SkinTex", 64, 64)
    image.pixels.foreach_set(np.tile((0.9, 0.6, 0.5, 1.0), 64 * 64).astype(np.float32))
    image.pack()
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    mat.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
    tu.assign(objs["Body"], mat)
    cloth, cnode = tu.node_material("Cloth", 'ShaderNodeAnimeCharacter')
    cnode.inputs["Base Color"].default_value = (0.2, 0.3, 0.9, 1.0)
    tu.assign(objs["Shirt"], cloth)
    tu.assign(face, mat)
    objects = [rig, eyes, face, cavity, teeth] + list(objs.values())
    for obj in objects[1:]:  # the game engines read a skin from a mesh whose parent is the armature
        obj.parent = rig
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        if not obj.vertex_groups:  # no weights, no skin
            obj.vertex_groups.new(name="Head").add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    outline.sync_all(bpy.context.scene)
    return rig, objects


def counts():
    return {name: len(getattr(bpy.data, name)) for name in
            ("objects", "meshes", "shape_keys", "materials", "images", "armatures")}


def shape_names():
    return {o.name: [b.name for b in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
            for o in bpy.data.objects if o.type == 'MESH'}


def new_path(name="Hero.dlive"):
    return os.path.join(tempfile.mkdtemp(prefix="dt_dlive_"), name)


def options(**kwargs):
    kwargs.setdefault("thumbnail", False)
    return dasktoon_dlive.Options(**kwargs)


def pack(path=None, **kwargs):
    rig, objects = character(**kwargs)
    path = path or new_path()
    rep = dasktoon_dlive.export(bpy.context, path, objects, options())
    return rig, objects, path, rep


def glb_json(data):
    import struct
    length = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + length])


def read(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


class ArchiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tu.reset_scene()
        cls.rig, cls.objects, cls.path, cls.rep = pack()
        cls.files = read(cls.path)
        cls.manifest = json.loads(cls.files["manifest.json"])
        cls.materials = {m["name"]: m for m in json.loads(cls.files["materials.json"])["materials"]}

    def test_entries_and_manifest(self):
        for name in ("manifest.json", "model.glb", "rig.json", "materials.json", "expressions.json"):
            self.assertIn(name, self.files)
        self.assertEqual(self.files["model.glb"][:4], b"glTF")
        self.assertEqual((self.manifest["format"], self.manifest["version"]), ("dlive", 1))
        self.assertEqual(self.manifest["model"], "model.glb")
        self.assertEqual(len(self.manifest["scene"]["light_direction"]), 3)
        self.assertEqual(len(self.manifest["scene"]["ambient"]), 3)
        self.assertIsNone(self.manifest["thumbnail"])
        self.assertIsNone(self.manifest["finish"])
        for name in self.files:
            if name.endswith(".json"):
                self.assertFalse(self.files[name].startswith(b"\xef\xbb\xbf"))
        with zipfile.ZipFile(self.path) as z:
            info = {i.filename: i.compress_type for i in z.infolist()}
        self.assertEqual(info["model.glb"], zipfile.ZIP_STORED)
        self.assertEqual(info["manifest.json"], zipfile.ZIP_DEFLATED)

    def test_materials_schema(self):
        skin = self.materials["Skin"]
        self.assertEqual((skin["shader"], skin["alpha"]), ("anime_bsdf", "OPAQUE"))
        self.assertIn(skin["cull"], ("back", "disabled"))
        self.assertEqual(skin["outline"]["shader"], "anime_outline")
        self.assertEqual(len(skin["params"]["base_color"]), 4)
        self.assertTrue(skin["params"]["base_map"].startswith("textures/"))
        self.assertIn(skin["params"]["base_map"], zipfile.ZipFile(self.path).namelist())
        self.assertNotIn("outline", self.materials["Cloth"])
        self.assertEqual(self.materials["Cloth"]["dasktoon"]["node"], "ShaderNodeAnimeCharacter")

    def test_the_values_are_the_godot_export_s(self):
        """The .tres of the same material holds the same numbers (one mapping, two outputs)."""
        folder = tempfile.mkdtemp(prefix="dt_godot_")
        target, _rep = gt.export(list(self.objects), folder, name="Hero", merge_meshes=True)
        text = open(os.path.join(target.root, "Hero", "Materials", "Cloth.tres"), encoding="utf-8").read()
        tres = dict(re.findall(r"shader_parameter/(\w+) = (.+)", text))
        params = self.materials["Cloth"]["params"]
        self.assertTrue(params)
        for name, value in params.items():
            raw = tres[name]
            if isinstance(value, bool):
                self.assertEqual(raw, "true" if value else "false")
            elif isinstance(value, list):
                numbers = [float(x) for x in re.findall(r"-?[\d.]+(?:e[+-]?\d+)?", raw.split("(", 1)[1])]
                np.testing.assert_allclose(numbers, value, atol=1e-6)
            else:
                self.assertAlmostEqual(float(raw), value, places=5)

    def test_rig_json_is_the_godot_data(self):
        data = json.loads(self.files["rig.json"])
        self.assertEqual(data["version"], 1)
        self.assertIn("shapes", data)


class FinishAndThumbnailTest(unittest.TestCase):
    def test_finish_layers_and_the_picture(self):
        tu.reset_scene()
        rig, objects = character()
        bpy.context.scene.dasktoon_finish.enabled = True
        path = new_path()
        rep = dasktoon_dlive.export(bpy.context, path, objects, options(thumbnail=True))
        files = read(path)
        self.assertEqual(json.loads(files["manifest.json"])["finish"], "finish.json")
        finish = json.loads(files["finish.json"])
        self.assertTrue(finish["layers"]["grade"]["grade_on"])
        self.assertIn("gradient_auto", finish["layers"]["gradient"])
        self.assertEqual(files["thumbnail.png"][1:4], b"PNG")
        self.assertEqual(json.loads(files["manifest.json"])["thumbnail"], "thumbnail.png")
        self.assertTrue(rep.thumbnail)
        self.assertFalse(bpy.data.scenes.get("dlive thumbnail"))


class ExpressionsTest(unittest.TestCase):
    def test_made_on_copies_and_the_file_unchanged(self):
        tu.reset_scene()
        rig, objects = character()
        before, names = counts(), shape_names()
        self.assertFalse(any(names.values()))
        path = new_path()
        rep = dasktoon_dlive.export(bpy.context, path, objects, options())
        self.assertEqual(counts(), before)
        self.assertEqual(shape_names(), names)
        self.assertEqual({o.name for o in bpy.data.objects}, {o.name for o in objects})
        parts = {p.object for p in rig.data.dasktoon_rig.parts if p.object}
        self.assertTrue(parts <= set(objects))
        data = json.loads(read(path)["expressions.json"])
        keys = data["keys"]
        self.assertIn("blink", keys, data["made"])
        self.assertIn("aa", keys, data["made"])
        self.assertIn("eyeBlinkLeft", keys)
        self.assertIn("jawOpen", keys)
        for pairs in keys.values():
            for pair in pairs:
                self.assertEqual(pair["weight"], 1.0)
        self.assertTrue(data["made"]["sculpted"])
        self.assertEqual(data["bones"].get("head"), "Head")
        self.assertEqual(rep.expressions["bones"], data["bones"])

    def test_without_making_nothing_is_added(self):
        tu.reset_scene()
        rig, objects = character()
        path = new_path()
        dasktoon_dlive.export(bpy.context, path, objects, options(make_expressions=False))
        data = json.loads(read(path)["expressions.json"])
        self.assertEqual(data["keys"], {})


class RoundTripTest(unittest.TestCase):
    def test_export_import_export(self):
        tu.reset_scene()
        rig, objects = character()
        path = new_path()
        dasktoon_dlive.export(bpy.context, path, objects, options())
        first = read(path)
        tu.reset_scene()
        new = dasktoon_dlive.import_dlive(bpy.context, path)
        self.assertTrue(new)
        self.assertTrue(any(o.data.shape_keys for o in new if o.type == 'MESH'))
        second_path = new_path()
        dasktoon_dlive.export(bpy.context, second_path, new, options(make_expressions=False))
        second = read(second_path)
        a, b = (json.loads(f["expressions.json"]) for f in (first, second))
        ga, gb = glb_json(first["model.glb"]), glb_json(second["model.glb"])
        self.assertEqual(len(ga["meshes"]), len(gb["meshes"]))
        self.assertEqual([m["extras"]["targetNames"] for m in ga["meshes"]],
                         [m["extras"]["targetNames"] for m in gb["meshes"]])
        self.assertEqual(sorted(n["name"] for n in ga["nodes"]), sorted(n["name"] for n in gb["nodes"]))
        self.assertEqual(a["bones"], b["bones"])
        for name in ("blink", "aa", "eyeBlinkLeft", "jawOpen"):
            self.assertIn(name, b["keys"])
        ma = {m["name"]: m for m in json.loads(first["materials.json"])["materials"]}
        mb = {m["name"]: m for m in json.loads(second["materials.json"])["materials"]}
        self.assertEqual(set(ma), set(mb))
        for name in ma:
            self.assertEqual(ma[name]["shader"], mb[name]["shader"])
            self.assertEqual(("outline" in ma[name]), ("outline" in mb[name]))
            for key, value in ma[name]["params"].items():
                if key in ("world_ambient", "light_direction"):
                    continue  # the scene's, and the scene differs
                if isinstance(value, str):
                    self.assertIn(key, mb[name]["params"])
                elif isinstance(value, list):
                    np.testing.assert_allclose(mb[name]["params"][key], value, atol=1e-4)
                else:
                    self.assertAlmostEqual(mb[name]["params"][key], value, places=4)

    def test_sway_comes_back(self):
        tu.reset_scene()
        from dasktoon_rig import build, sway
        rig = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        bpy.context.scene.collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        eb = rig.data.edit_bones
        root = eb.new("Root")
        root.head, root.tail = (0, 0, 0), (0, 0, 0.2)
        names = ["Lock1", "Lock2"]
        for i, n in enumerate(names):
            b = eb.new(n)
            b.head, b.tail = (0, 0, 0.2 + 0.1 * i), (0, 0, 0.3 + 0.1 * i)
            b.parent = root if i == 0 else eb[names[0]]
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = tu.add_sphere(segments=8, rings=4)
        mesh.modifiers.new("Armature", 'ARMATURE').object = rig
        mesh.parent = rig
        for n in ["Root"] + names:
            mesh.vertex_groups.new(name=n).add(list(range(len(mesh.data.vertices))), 1.0, 'REPLACE')
        for n in names:
            rig.data.bones[n][build.MARK] = "Hair"
        part = rig.data.dasktoon_rig.parts.add()
        part.name, part.role, part.stiffness = "Hair", 'HAIR', 2.5
        col = rig.data.dasktoon_rig.colliders.add()
        col.bone, col.radius = "Root", 0.07
        path = new_path("Rig.dlive")
        dasktoon_dlive.export(bpy.context, path, [rig, mesh], options(make_expressions=False))
        data = json.loads(read(path)["rig.json"])
        self.assertEqual(data["rig"]["chains"][0]["bones"], names)
        tu.reset_scene()
        new = dasktoon_dlive.import_dlive(bpy.context, path)
        imported = next(o for o in new if o.type == 'ARMATURE')
        parts = imported.data.dasktoon_rig.parts
        self.assertEqual([p.name for p in parts], ["Hair"])
        self.assertAlmostEqual(parts[0].stiffness, 2.5, places=3)
        self.assertEqual([c.bone for c in imported.data.dasktoon_rig.colliders], ["Root"])
        self.assertEqual(sway.chains(imported)[0][1], names)


class VersionTest(unittest.TestCase):
    def test_version_2_is_refused(self):
        tu.reset_scene()
        rig, objects, path, _rep = pack()
        files = read(path)
        manifest = json.loads(files["manifest.json"])
        manifest["version"] = 2
        files["manifest.json"] = json.dumps(manifest).encode()
        bad = new_path("v2.dlive")
        with zipfile.ZipFile(bad, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)
        before = counts()
        with self.assertRaises(importer.DliveError) as ctx:
            dasktoon_dlive.import_dlive(bpy.context, bad)
        self.assertIn("version 2", str(ctx.exception))
        self.assertEqual(counts(), before)

    def test_other_files_are_refused(self):
        tu.reset_scene()
        path = new_path("x.dlive")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("manifest.json", json.dumps({"format": "other", "version": 1}))
        with self.assertRaises(importer.DliveError):
            dasktoon_dlive.import_dlive(bpy.context, path)


class UnassignedFacesTest(unittest.TestCase):
    """Every surface of the model names a material of materials.json, also faces with an empty slot or no slot at all."""

    def test_every_primitive_has_a_material_of_the_file(self):
        tu.reset_scene()
        rig, objects = character()
        # An empty slot beside a real one, faces past the slots, and a mesh with no slot.
        body = bpy.data.objects["Body"]
        body.data.materials.append(None)
        for index, poly in enumerate(body.data.polygons):
            poly.material_index = 1 if index % 3 == 0 else 0
        before = {o.name: [m.name if m else None for m in o.data.materials] for o in objects if o.type == 'MESH'}
        indices = [p.material_index for p in body.data.polygons]
        path = new_path()
        dasktoon_dlive.export(bpy.context, path, objects, options())
        files = read(path)
        gltf = glb_json(files["model.glb"])
        names = {m["name"] for m in json.loads(files["materials.json"])["materials"]}
        for mesh in gltf["meshes"]:
            for prim in mesh["primitives"]:
                self.assertIn("material", prim, mesh["name"])
                self.assertIn(gltf["materials"][prim["material"]]["name"], names)
        self.assertEqual(before, {o.name: [m.name if m else None for m in o.data.materials]
                                  for o in objects if o.type == 'MESH'})
        self.assertEqual(indices, [p.material_index for p in body.data.polygons])
        self.assertFalse([m for m in bpy.data.materials if m.name.startswith("Unassigned")])


class SizeTest(unittest.TestCase):
    """What a game does not need stays out of the file: shape keys no expression plays, the morph normals."""

    def pack_with_extra_keys(self, **kwargs):
        tu.reset_scene()
        rig, objects = character()
        body = bpy.data.objects["Body"]
        body.shape_key_add(name="Basis", from_mix=False)
        extra = body.shape_key_add(name="zzz_unplayed", from_mix=False)
        for index, point in enumerate(extra.data):
            point.co.z += 0.002 * (index % 5)
        extra.value = 0.0
        body.shape_key_add(name="zzz_empty", from_mix=False)
        path = new_path()
        dasktoon_dlive.export(bpy.context, path, objects, options(**kwargs))
        files = read(path)
        return body, files, glb_json(files["model.glb"])

    def target_names(self, gltf):
        return [n for m in gltf["meshes"] for n in m.get("extras", {}).get("targetNames", [])]

    def test_unplayed_keys_are_left_out_and_the_file_keeps_them(self):
        body, files, gltf = self.pack_with_extra_keys()
        names = self.target_names(gltf)
        self.assertNotIn("zzz_unplayed", names)
        self.assertTrue(names)  # what an expression plays is there
        self.assertIn("zzz_unplayed", [b.name for b in body.data.shape_keys.key_blocks])

    def test_unplayed_keys_stay_when_asked(self):
        _body, _files, gltf = self.pack_with_extra_keys(drop_unused_keys=False)
        self.assertIn("zzz_unplayed", self.target_names(gltf))

    def test_morph_normals_only_when_asked(self):
        for wanted in (False, True):
            _body, _files, gltf = self.pack_with_extra_keys(morph_normals=wanted)
            targets = [t for m in gltf["meshes"] for p in m["primitives"] for t in p.get("targets", [])]
            self.assertTrue(targets)
            self.assertEqual(all("NORMAL" in t for t in targets), wanted)


class TextureTest(unittest.TestCase):
    """Colour maps with nothing see-through are JPEG, one with some transparency stays PNG, and the same picture under
    two inputs is in the file once."""

    def image(self, name, alpha):
        image = bpy.data.images.new(name, 64, 64, alpha=True)
        px = np.tile((0.9, 0.6, 0.5, 1.0), 64 * 64).reshape(64, 64, 4).astype(np.float32)
        px[:, :, 0] = np.linspace(0.0, 1.0, 64)[None, :]  # not flat: a gradient, so it is no accident they are equal
        px[:32, :, 3] = alpha
        image.pixels.foreach_set(px.ravel())
        image.pack()
        return image

    def link(self, mat, node, socket, image):
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        mat.node_tree.links.new(tex.outputs["Color"], node.inputs[socket])

    def test_formats_and_one_copy(self):
        tu.reset_scene()
        rig, objects = character()
        solid = self.image("Solid", 1.0)
        same = self.image("Same", 1.0)
        see_through = self.image("SeeThrough", 0.2)
        mat, node = tu.node_material("Plain", 'ShaderNodeAnimeCharacter')
        self.link(mat, node, "Base Color", solid)
        self.link(mat, node, "Shadow Color", same)
        glass, gnode = tu.node_material("Glass", 'ShaderNodeAnimeCharacter')
        self.link(glass, gnode, "Base Color", see_through)
        tu.assign(bpy.data.objects["Boots"], mat)
        tu.assign(bpy.data.objects["Teeth"], glass)
        path = new_path()
        dasktoon_dlive.export(bpy.context, path, objects, options())
        files = read(path)
        mats = {m["name"]: m for m in json.loads(files["materials.json"])["materials"]}
        plain, clear = mats["Plain"]["params"], mats["Glass"]["params"]
        self.assertTrue(plain["base_map"].endswith(".jpg"), plain["base_map"])
        self.assertEqual(files[plain["base_map"]][:2], bytes([0xFF, 0xD8]))
        self.assertEqual(plain["base_map"], plain["shadow_color_map"])  # the same picture, one file
        self.assertTrue(clear["base_map"].endswith(".png"), clear["base_map"])
        self.assertEqual(files[clear["base_map"]][1:4], b"PNG")
        self.assertEqual(len([n for n in files if n.startswith("textures/")
                              and n.startswith("textures/Plain")]), 1)


class OperatorsTest(unittest.TestCase):
    def test_operators_are_registered(self):
        self.assertTrue(hasattr(bpy.ops.export_scene, "dasktoon_dlive"))
        self.assertTrue(hasattr(bpy.ops.import_scene, "dasktoon_dlive"))


@unittest.skipUnless(FIXTURE, "set DASKTOON_DLIVE_FIXTURE_DIR to write the fixtures for DaskLive")
class FixtureTest(unittest.TestCase):
    def test_write_fixtures(self):
        tu.reset_scene()
        os.makedirs(FIXTURE, exist_ok=True)
        pack(path=os.path.join(FIXTURE, "simple.dlive"), plain=True)


if __name__ == "__main__":
    tu.run_tests()
