# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity 6000.5 batchmode works on a throwaway URP project: license, URP 17.5, Linear, render read-back (spec 8, 9)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnitySmokeTest(unittest.TestCase):
    def test_batchmode_renders_with_urp_in_linear(self):
        harness.ensure_project()
        result = harness.run_method("DaskToonTests.Smoke")
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["colorSpace"], "Linear")
        self.assertTrue(result["urp"])
        # _BaseColor (0.25, 0.5, 0.75) is an sRGB value; the linear render target holds its linear form.
        for got, want in zip(result["center"], (0.0508, 0.2140, 0.5225)):
            self.assertAlmostEqual(got, want, delta=0.005)

    def test_project_is_outside_user_unity_folder(self):
        self.assertFalse(os.path.abspath(harness.project_dir()).lower().startswith("d:\\unity"))


if __name__ == "__main__":
    tu.run_tests()
