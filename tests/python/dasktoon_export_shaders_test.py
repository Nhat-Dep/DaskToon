# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Shader install (fixed GUIDs, version file) and static checks of the Unity shader sources (spec 4, 6)."""

import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import assets, shaders_install as si, targets  # noqa: E402

GLSL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "source", "blender", "gpu", "shaders", "material")
KEYWORDS = {"_DT_RAMP", "_DT_AMBIENT", "_DT_LIGHT", "_DT_AO", "_DT_RIM", "_DT_GRADE", "_DT_OUTLINE",
            "_DT_ANGEL_RING", "_DT_ALPHATEST_ON", "_DT_NORMALMAP"}


def fake_project():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_shaders_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.project = fake_project()
        self.target = targets.make_target(self.project, "Hero")
        self.shaders = os.path.join(self.target.root, si.SHADER_DIR)

    def test_first_install_writes_every_file_with_fixed_guid(self):
        self.assertTrue(si.install_shaders(self.target, []))
        for name, guid in si.FILE_GUIDS.items():
            self.assertTrue(os.path.isfile(os.path.join(self.shaders, name)), name)
            self.assertEqual(assets.read_meta_guid(os.path.join(self.shaders, name + ".meta")), guid)
        self.assertEqual(si.installed_version(self.target.root), si.SHADER_VERSION)
        self.assertEqual(assets.read_meta_guid(self.shaders + ".meta"), si.SHADERS_FOLDER_GUID)
        self.assertEqual(assets.read_meta_guid(self.target.root + ".meta"), si.ROOT_FOLDER_GUID)
        self.assertIn("ShaderImporter:", read(os.path.join(self.shaders, "AnimeBSDF.shader.meta")))
        self.assertIn("ShaderIncludeImporter:", read(os.path.join(self.shaders, "DaskToonCore.hlsl.meta")))

    def test_up_to_date_project_install_is_skipped(self):
        si.install_shaders(self.target, [])
        edited = os.path.join(self.shaders, "AnimeBSDF.shader")
        with open(edited, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertFalse(si.install_shaders(self.target, []))
        self.assertEqual(read(edited), "edited")
        self.assertTrue(si.install_shaders(self.target, [], force=True))
        self.assertNotEqual(read(edited), "edited")

    def test_newer_version_overwrites(self):
        si.install_shaders(self.target, [])
        edited = os.path.join(self.shaders, "AnimeBSDF.shader")
        with open(edited, "w", encoding="utf-8") as f:
            f.write("edited")
        old = si.SHADER_VERSION
        si.SHADER_VERSION = old + 1
        try:
            self.assertTrue(si.install_shaders(self.target, []))
            self.assertEqual(si.installed_version(self.target.root), old + 1)
        finally:
            si.SHADER_VERSION = old
        self.assertNotEqual(read(edited), "edited")

    def test_folder_mode_always_writes(self):
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_folder_"), "Hero")
        self.assertTrue(si.install_shaders(target, []))
        self.assertTrue(si.install_shaders(target, []))


class SourceTest(unittest.TestCase):
    def test_every_shader_has_the_passes_and_name(self):
        for name in si.SHADER_NAMES:
            text = read(os.path.join(si.SOURCE_DIR, name + ".shader"))
            self.assertIn('Shader "DaskToon/%s"' % name, text)
            for light_mode in ("UniversalForward", "SRPDefaultUnlit", "ShadowCaster", "DepthOnly", "DepthNormals"):
                self.assertIn('"LightMode" = "%s"' % light_mode, text, name)
            self.assertIn("DT_SHARED_MATERIAL_FIELDS", text, name)
            self.assertIn("float DT_SurfaceAlpha(float2 uv)", text, name)

    def test_every_keyword_is_declared(self):
        declared = set()
        for name in si.SHADER_NAMES:
            declared |= set(re.findall(r"shader_feature_local\w*\s+(_DT_\w+)",
                                       read(os.path.join(si.SOURCE_DIR, name + ".shader"))))
        self.assertEqual(declared, KEYWORDS)

    def test_core_ports_every_shared_glsl_function(self):
        glsl = read(os.path.join(GLSL_DIR, "gpu_shader_material_dasktoon_shading.glsl"))
        core = read(os.path.join(si.SOURCE_DIR, "DaskToonCore.hlsl"))
        for func in re.findall(r"^\w+\s+(dt_\w+)\(", glsl, re.MULTILINE):
            self.assertRegex(core, r"\b%s\(" % func)
        # Constants of the node formulas that must survive the port unchanged.
        for constant in ("0.0001", "1.25", "0.75", "0.65", "0.299, 0.587, 0.114", "0.2126, 0.7152, 0.0722",
                         "0.16, 0.22", "2.2", "0.45, 0.85", "0.035, 0.055", "0.018, 0.032", "0.55", "0.45",
                         "6.28", "0.5, 0.8, 0.6", "3.33", "0.03", "1.4", "0.35", "50.0"):
            self.assertIn(constant, core, constant)


if __name__ == "__main__":
    tu.run_tests()
