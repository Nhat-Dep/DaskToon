# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Every DaskToon shader pass compiles in Unity 6000.5 / URP 17.5 (spec 8, Unity step 1)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
from dasktoon_export import shaders_install, targets  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityShaderTest(unittest.TestCase):
    def test_every_shader_variant_compiles(self):
        root = harness.ensure_project()
        target = targets.make_target(root, "ShaderTest")
        self.assertEqual(target.mode, 'PROJECT')
        shaders_install.install_shaders(target, [], force=True)
        result = harness.run_method("DaskToonShaderTests.CompileShaders")
        self.assertTrue(result["ok"], "\n".join(result.get("errors") or []) or result.get("error"))
        self.assertGreater(result["compiled"], 100)


if __name__ == "__main__":
    tu.run_tests()
