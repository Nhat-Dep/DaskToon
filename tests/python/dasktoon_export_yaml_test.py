# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity YAML written by the exporter matches Unity's own format (spec 4)."""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import unity_yaml as uy  # noqa: E402

SHADER = "651389b857c37954216341111b253e67"
TEX = "0123456789abcdef0123456789abcdef"

GOLDEN_MAT = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_Name: Skin
  m_Shader: {fileID: 4800000, guid: 651389b857c37954216341111b253e67, type: 3}
  m_Parent: {fileID: 0}
  m_ModifiedSerializedProperties: 0
  m_ValidKeywords:
  - _DT_AMBIENT
  - _DT_RIM
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap:
    RenderType: Opaque
  disabledShaderPasses:
  - SRPDefaultUnlit
  m_LockedProperties: 
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BaseMap:
        m_Texture: {fileID: 2800000, guid: 0123456789abcdef0123456789abcdef, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _DT_ShadowColorMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    m_Ints: []
    m_Floats:
    - _Cull: 2
    - _DT_ShadowThreshold: 0.46
    m_Colors:
    - _BaseColor: {r: 1, g: 0.735357, b: 0, a: 1}
  m_BuildTextureStacks: []
  m_AllowLocking: 1
"""


def golden_material(**overrides):
    args = dict(name="Skin", shader_guid=SHADER, keywords={"_DT_RIM", "_DT_AMBIENT"}, queue=-1,
                render_type="Opaque", disabled_passes=["SRPDefaultUnlit"],
                floats={"_DT_ShadowThreshold": 0.46, "_Cull": 2.0},
                colors={"_BaseColor": (1.0, 0.5, 0.0, 1.0)},
                textures={"_BaseMap": TEX, "_DT_ShadowColorMap": None})
    args.update(overrides)
    return uy.material_yaml(**args)


class YamlTest(unittest.TestCase):
    def test_guid_is_md5_of_model_name_and_relative_path(self):
        want = hashlib.md5(b"dasktoon:Hero:Hero/Materials/Skin.mat").hexdigest()
        self.assertEqual(uy.guid_for("Hero", "Hero/Materials/Skin.mat"), want)
        self.assertEqual(uy.guid_for("Hero", "Hero\\Materials\\Skin.mat"), want)

    def test_linear_to_srgb_piecewise_and_above_one(self):
        self.assertEqual(uy.linear_to_srgb(0.0), 0.0)
        self.assertEqual(uy.linear_to_srgb(-0.5), 0.0)
        self.assertAlmostEqual(uy.linear_to_srgb(0.002), 0.02584, places=5)
        self.assertAlmostEqual(uy.linear_to_srgb(0.5), 0.735357, places=6)
        self.assertAlmostEqual(uy.linear_to_srgb(2.0), 1.353256, places=6)

    def test_material_matches_golden(self):
        self.assertEqual(golden_material(), GOLDEN_MAT)

    def test_material_name_with_special_characters_is_quoted(self):
        text = golden_material(name="Áo: đỏ #1")
        self.assertIn("  m_Name: 'Áo: đỏ #1'\n", text)
        self.assertIn("  m_Name: 'It''s'\n", golden_material(name="It's"))

    def test_empty_lists_are_inline(self):
        text = golden_material(keywords=set(), disabled_passes=[], textures={}, floats={}, colors={})
        self.assertIn("  m_ValidKeywords: []\n", text)
        self.assertIn("  disabledShaderPasses: []\n", text)
        self.assertIn("    m_TexEnvs: []\n", text)
        self.assertIn("    m_Floats: []\n", text)
        self.assertIn("    m_Colors: []\n", text)

    def test_texture_meta_follows_spec_table(self):
        color = uy.texture_meta(TEX, 'COLOR')
        self.assertIn("    sRGBTexture: 1\n", color)
        self.assertIn("    textureCompression: 2\n", color)
        self.assertIn("    wrapU: 0\n", color)
        self.assertIn("    enableMipMap: 1\n", color)
        data = uy.texture_meta(TEX, 'DATA')
        self.assertIn("    sRGBTexture: 0\n", data)
        self.assertIn("    textureCompression: 0\n", data)
        self.assertIn("  textureType: 1\n", uy.texture_meta(TEX, 'NORMAL'))
        ramp = uy.texture_meta(TEX, 'RAMP', size=(256, 1), point_filter=True)
        self.assertIn("    wrapU: 1\n", ramp)
        self.assertIn("    enableMipMap: 0\n", ramp)
        self.assertIn("    filterMode: 0\n", ramp)
        self.assertIn("  nPOTScale: 0\n", ramp)
        self.assertIn("  maxTextureSize: 4096\n", uy.texture_meta(TEX, 'COLOR', size=(4096, 2048)))
        self.assertTrue(color.startswith("fileFormatVersion: 2\nguid: %s\nTextureImporter:\n" % TEX))

    def test_model_meta_remaps_materials_by_fbx_name(self):
        text = uy.model_meta(TEX, {"Skin": "a" * 32, "Áo": "b" * 32}, True)
        self.assertIn("ModelImporter:\n", text)
        self.assertIn("  externalObjects:\n  - first:\n      type: UnityEngine:Material\n"
                      "      assembly: UnityEngine.CoreModule\n      name: Skin\n"
                      "    second: {fileID: 2100000, guid: %s, type: 2}\n" % ("a" * 32), text)
        self.assertIn("      name: 'Áo'\n", text)
        for line in ("    importBlendShapes: 1\n", "    normalImportMode: 0\n", "    tangentImportMode: 3\n",
                     "    blendShapeNormalImportMode: 0\n", "  importAnimation: 1\n"):
            self.assertIn(line, text)
        bare = uy.model_meta(TEX, {}, False)
        self.assertIn("  externalObjects: {}\n", bare)
        self.assertIn("  importAnimation: 0\n", bare)

    def test_simple_metas(self):
        head = "fileFormatVersion: 2\nguid: %s\n" % TEX
        cases = {
            uy.folder_meta: "folderAsset: yes\nDefaultImporter:\n",
            uy.default_meta: "DefaultImporter:\n",
            uy.text_meta: "TextScriptImporter:\n",
            uy.shader_meta: "ShaderImporter:\n",
            uy.include_meta: "ShaderIncludeImporter:\n",
            uy.material_meta: "NativeFormatImporter:\n",
        }
        for func, body in cases.items():
            text = func(TEX)
            self.assertTrue(text.startswith(head + body), func.__name__)
            self.assertTrue(text.endswith("  assetBundleVariant: \n"), func.__name__)
        self.assertIn("  mainObjectFileID: 2100000\n", uy.material_meta(TEX))


    def test_model_meta_turns_blend_shape_normals_off_for_face_shading(self):
        self.assertIn("    blendShapeNormalImportMode: 0\n", uy.model_meta(TEX, {}, False))
        self.assertIn("    blendShapeNormalImportMode: 2\n", uy.model_meta(TEX, {}, False, blend_shape_normals=False))

    def test_model_meta_humanoid(self):
        self.assertIn("  animationType: 2\n", uy.model_meta(TEX, {}, True))
        self.assertIn("  animationType: 3\n", uy.model_meta(TEX, {}, True, humanoid=True))


if __name__ == "__main__":
    tu.run_tests()
