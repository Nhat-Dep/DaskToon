# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export end to end: folder layout in both modes, metas, stable GUIDs, user files, report (spec 4, 5)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import assets, targets, textures  # noqa: E402

OPTIONS = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_character(blend_dir=None):
    """Body: Skin (Anime BSDF, outline, image base colour), 'Áo: đỏ' (Dask Cel), Plastic (unsupported), an empty slot."""
    tu.reset_scene()
    outline.reset_cache()
    tu.add_sun(strength=3.0, rotation=(0.6, 0.0, 0.8))
    body = tu.add_sphere(segments=16, rings=8)
    body.name = "Body"
    skin, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.use_outline = True
    png = os.path.join(tempfile.mkdtemp(prefix="dt_layout_img_"), "skin.png")
    with open(png, "wb") as f:
        f.write(textures.png_bytes(2, 2, bytes([200, 150, 120, 255] * 4)))
    tex = skin.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(png)
    skin.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
    cloth, _cel = tu.node_material("Áo: đỏ", 'ShaderNodeDaskCel')
    # DaskToon's default new material uses Anime BSDF, so the unsupported one is built from Principled BSDF.
    plastic, _principled = tu.node_material("Plastic", 'ShaderNodeBsdfPrincipled')
    for mat in (skin, cloth, plastic):
        body.data.materials.append(mat)
    body.data.materials.append(None)
    for i, poly in enumerate(body.data.polygons):
        poly.material_index = i % 3
    outline.sync_all(bpy.context.scene)
    if blend_dir:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blend_dir, "Hero.blend"))
    return body


def export_to(directory, objects=None):
    name = targets.blend_name(bpy.data.filepath)
    target = targets.make_target(directory, name)
    objects = objects or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    return target, dasktoon_export.export_model(bpy.context, target, objects, OPTIONS)


def fake_project():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_layout_proj_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class LayoutTest(unittest.TestCase):
    def test_folder_mode_layout(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target, rep = export_to(out)
        root = os.path.join(out, "Hero_Unity")
        self.assertEqual((target.mode, target.root), ('FOLDER', root))
        for rel in ("README.txt", "Shaders/AnimeBSDF.shader", "Shaders/DaskToonShaders.version", "Hero",
                    "Hero/Model", "Hero/Model/Hero.fbx", "Hero/Materials", "Hero/Materials/Skin.mat",
                    "Hero/Materials/Áo_ đỏ.mat", "Hero/Textures", "Hero/Textures/Skin_Base.png", "Shaders"):
            self.assertTrue(os.path.exists(os.path.join(root, rel)), rel)
            self.assertTrue(os.path.exists(os.path.join(root, rel) + ".meta"), rel + ".meta")
        self.assertFalse(os.path.exists(os.path.join(root, "Hero/Materials/Plastic.mat")))
        meta = read(os.path.join(root, "Hero/Model/Hero.fbx.meta"))
        self.assertIn("      name: Skin\n", meta)
        self.assertIn("      name: 'Áo: đỏ'\n", meta)
        self.assertNotIn("Plastic", meta)
        self.assertIn("Áo_ đỏ", read(os.path.join(root, "Hero/Materials/Áo_ đỏ.mat")))
        self.assertEqual([name for name, _reason in rep.skipped], ["Plastic"])
        self.assertEqual(rep.shaders, 'INSTALLED')
        readme = read(os.path.join(root, "README.txt"))
        self.assertIn("Sun 3.0 → Directional 0.955", readme)
        self.assertIn("Linear", readme)
        self.assertIn(rep.light_hint, "\n".join(rep.lines()))
        self.assertIn(dasktoon_export.report.REPORT_TEXT, bpy.data.texts)

    def test_guids_are_stable_between_exports(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        export_to(out)
        root = os.path.join(out, "Hero_Unity")
        first = {rel: read(os.path.join(root, rel)) for rel in
                 ("Hero/Materials/Skin.mat.meta", "Hero/Materials/Skin.mat", "Hero/Model/Hero.fbx.meta",
                  "Hero/Textures/Skin_Base.png.meta", "Hero.meta")}
        export_to(out)
        for rel, text in first.items():
            self.assertEqual(read(os.path.join(root, rel)), text, rel)

    def test_project_mode_writes_into_assets_dasktoon(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        project = fake_project()
        target, rep = export_to(os.path.join(project, "Assets"))
        root = os.path.join(project, "Assets", "DaskToon")
        self.assertEqual((target.mode, target.root), ('PROJECT', root))
        self.assertTrue(os.path.exists(root + ".meta"))
        self.assertTrue(os.path.exists(os.path.join(root, "Hero/Materials/Skin.mat")))
        self.assertFalse(os.path.exists(os.path.join(root, "README.txt")))
        _target, again = export_to(project)
        self.assertEqual(again.shaders, 'UP_TO_DATE')

    def test_user_file_with_the_same_name_is_kept(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        project = fake_project()
        user = os.path.join(project, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")
        os.makedirs(os.path.dirname(user))
        with open(user, "w", encoding="utf-8") as f:
            f.write("user material")
        _target, rep = export_to(project)
        self.assertEqual(read(user), "user material")
        self.assertTrue(any("Skin.mat" in w for w in rep.warnings), rep.warnings)

    def test_untitled_file(self):
        build_character()
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target, _rep = export_to(out)
        self.assertEqual(target.root, os.path.join(out, "Untitled_Unity"))
        self.assertTrue(os.path.exists(os.path.join(target.root, "Untitled/Model/Untitled.fbx")))

    def test_base_texture_shared_with_outline_is_written_once(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        export_to(out)
        textures_dir = os.path.join(out, "Hero_Unity", "Hero", "Textures")
        pngs = sorted(f for f in os.listdir(textures_dir) if f.endswith(".png"))
        self.assertEqual(pngs, ["Skin_Base.png"])
        guid = assets.read_meta_guid(os.path.join(textures_dir, "Skin_Base.png.meta"))
        mat = read(os.path.join(out, "Hero_Unity", "Hero", "Materials", "Skin.mat"))
        self.assertEqual(mat.count(guid), 2)

    def test_mesh_without_uv_still_exports(self):
        body = build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        body.data.uv_layers.remove(body.data.uv_layers[0])
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        _target, rep = export_to(out)
        self.assertTrue(rep.warnings)
        mat = read(os.path.join(out, "Hero_Unity", "Hero", "Materials", "Skin.mat"))
        self.assertIn("    - _DT_OutlineUV: -1\n", mat)

    def test_linked_material_with_outline_exports(self):
        tu.reset_scene()
        outline.reset_cache()
        mat, node = tu.node_material("LibSkin", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        tex = mat.node_tree.nodes.new('ShaderNodeRGB')    # a linked colour branch the sync must clone
        mat.node_tree.links.new(tex.outputs[0], node.inputs["Outline Color"])
        outline.sync_material(mat)                           # the library is saved with its .Outline companion
        outline.outline_node(outline.outline_material_for(mat)).inputs["Light Bleed"].default_value = 0.25
        mat.use_fake_user = True
        lib = os.path.join(tempfile.mkdtemp(prefix="dt_layout_lib_"), "lib.blend")
        bpy.ops.wm.save_as_mainfile(filepath=lib)
        tu.reset_scene()
        outline.reset_cache()
        with bpy.data.libraries.load(lib, link=True) as (_src, dst):
            dst.materials = ["LibSkin"]
        linked = dst.materials[0]
        self.assertIsNotNone(linked.library)
        body = tu.add_sphere(segments=8, rings=4)
        tu.assign(body, linked)
        outline.reset_cache()                               # a fresh session: the sync would rebuild the companion
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target, rep = export_to(out, [body])
        self.assertEqual(rep.materials, ["LibSkin"])
        mat_text = read(os.path.join(target.root, "Untitled", "Materials", "LibSkin.mat"))
        self.assertIn("  - _DT_OUTLINE\n", mat_text)
        self.assertIn("    - _DT_OutlineLightBleed: 0.7\n", mat_text)  # fixed, not the library's 0.25

    def test_object_outside_the_view_layer_is_left_out_of_the_fbx(self):
        body = build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        rig = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        rigs = bpy.data.collections.new("Rigs")
        bpy.context.scene.collection.children.link(rigs)
        rigs.objects.link(rig)
        bpy.context.view_layer.layer_collection.children["Rigs"].exclude = True
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        _target, rep = export_to(out, [body, rig])
        self.assertTrue(os.path.isfile(os.path.join(out, "Hero_Unity", "Hero", "Model", "Hero.fbx")))
        self.assertTrue(any("Rig" in w for w in rep.warnings), rep.warnings)

    def test_materials_only(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target = targets.make_target(out, "Hero")
        options = dasktoon_export.ExportOptions(model_format='NONE', bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [bpy.data.objects["Body"]], options)
        self.assertEqual(rep.model, "")
        self.assertFalse(os.path.exists(os.path.join(target.root, "Hero", "Model")))
        self.assertTrue(os.path.exists(os.path.join(target.root, "Hero", "Materials", "Skin.mat")))


if __name__ == "__main__":
    tu.run_tests()
