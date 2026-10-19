# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fill Empty Expressions (docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md): an expression shape
key that moves nothing, or barely moves next to the mesh's other expressions, is built from the ones that do: "e"
from "a" and "i", a blink side from the blink, the blink from its sides, the upper lip from the upward part of "i",
VRM 0 and VRM 1 names from each other. The rest face ("neutral") stays empty; keys that move are left alone."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import expressions  # noqa: E402

GRID = 9  # a flat face of GRID x GRID vertices, x from -1 to 1 (the character's left at +x), z from 0 to 2


def face(keys):
    """A plane object "Face" with a Basis and `keys` ({name: offsets (n x 3) or None for an empty key})."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts = [(x, 0.0, z) for z in np.linspace(0.0, 2.0, GRID) for x in np.linspace(-1.0, 1.0, GRID)]
    faces = [(r * GRID + c, r * GRID + c + 1, (r + 1) * GRID + c + 1, (r + 1) * GRID + c)
             for r in range(GRID - 1) for c in range(GRID - 1)]
    mesh = bpy.data.meshes.new("Face")
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new("Face", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.shape_key_add(name="Basis", from_mix=False)
    for name, offsets in keys.items():
        block = obj.shape_key_add(name=name, from_mix=False)
        if offsets is not None:
            co = np.array(verts) + offsets
            block.data.foreach_set("co", co.ravel())
    return obj


def offsets(obj, name):
    key = obj.data.shape_keys
    base = np.array([p.co for p in key.reference_key.data])
    return np.array([p.co for p in key.key_blocks[name].data]) - base


def xs():
    return np.array([(x, 0.0, z) for z in np.linspace(0.0, 2.0, GRID) for x in np.linspace(-1.0, 1.0, GRID)])


def moving(z_low, z_high, delta):
    """Offsets moving the vertices with z in [z_low, z_high] by `delta`."""
    co = xs()
    out = np.zeros_like(co)
    out[(co[:, 2] >= z_low) & (co[:, 2] <= z_high)] = delta
    return out


class FillTest(unittest.TestCase):
    def test_e_from_a_and_i(self):
        a = moving(0.0, 0.5, (0.0, 0.0, -0.2))
        i = moving(0.0, 0.5, (0.1, 0.0, 0.05))
        obj = face({"a": a, "i": i, "e": None, "neutral": None})
        filled = expressions.fill(obj)
        self.assertEqual([name for name, _how in filled], ["e"])
        np.testing.assert_allclose(offsets(obj, "e"), 0.5 * a + 0.5 * i, atol=1e-6)
        np.testing.assert_allclose(offsets(obj, "neutral"), 0.0, atol=1e-9)  # the rest face stays empty
        np.testing.assert_allclose(offsets(obj, "a"), a, atol=1e-6)  # sources are left alone

    def test_a_key_that_barely_moves_is_filled(self):
        a = moving(0.0, 0.5, (0.0, 0.0, -0.2))
        i = moving(0.0, 0.5, (0.1, 0.0, 0.0))
        obj = face({"a": a, "i": i, "e": moving(0.0, 0.1, (0.0, 0.0, -0.005)), "o": moving(0.0, 0.5, (0, 0, -0.15))})
        self.assertEqual([name for name, _how in expressions.fill(obj)], ["e"])
        np.testing.assert_allclose(offsets(obj, "e"), 0.5 * a + 0.5 * i, atol=1e-6)

    def test_blink_sides_from_the_blink_and_back(self):
        blink = moving(1.2, 1.5, (0.0, 0.0, -0.1))
        obj = face({"blink": blink, "blink_L": None, "blink_R": None})
        expressions.fill(obj)
        left, right = offsets(obj, "blink_L"), offsets(obj, "blink_R")
        x = xs()[:, 0]
        np.testing.assert_allclose(left[x > 0.1], blink[x > 0.1], atol=1e-6)  # the character's left is +x
        np.testing.assert_allclose(left[x < -0.1], 0.0, atol=1e-6)
        np.testing.assert_allclose(right[x < -0.1], blink[x < -0.1], atol=1e-6)
        np.testing.assert_allclose(left + right, blink, atol=1e-6)
        obj = face({"blinkLeft": blink * (x > 0)[:, None], "blinkRight": blink * (x <= 0)[:, None], "blink": None})
        expressions.fill(obj)
        np.testing.assert_allclose(offsets(obj, "blink"), blink, atol=1e-6)

    def test_upper_lip_from_the_upward_part_of_i(self):
        i = moving(0.4, 0.5, (0.0, 0.0, 0.05)) + moving(0.0, 0.3, (0.0, 0.0, -0.04))
        obj = face({"i": i, "mouthUpperUp": None, "mouthLowerDown": None, "a": None})
        expressions.fill(obj)
        np.testing.assert_allclose(offsets(obj, "mouthUpperUp"), moving(0.4, 0.5, (0.0, 0.0, 0.05)), atol=1e-6)
        np.testing.assert_allclose(offsets(obj, "mouthLowerDown"), 0.0, atol=1e-9)  # needs "a", empty here

    def test_vrm_names_fill_each_other(self):
        joy = moving(0.0, 2.0, (0.0, -0.05, 0.0))
        aa = moving(0.0, 0.5, (0.0, 0.0, -0.2))
        obj = face({"joy": joy, "happy": None, "aa": aa, "a": None})
        filled = dict(expressions.fill(obj))
        np.testing.assert_allclose(offsets(obj, "happy"), joy, atol=1e-6)
        np.testing.assert_allclose(offsets(obj, "a"), aa, atol=1e-6)
        self.assertIn("joy", filled["happy"])

    def test_the_characters_left_comes_from_its_rig(self):
        """filie (a real model) faces +Y in the scene: its mesh's own +X is the character's right. A mesh the rig
        deforms takes the sides from the rig (the character's left at +X of the armature, the middle at its Hips)."""
        import dasktoon_rig_regions_test as rt
        blink = moving(1.2, 1.5, (0.0, 0.0, -0.1))
        obj = face({})
        rig, _objs = rt.rigged(reset=False)
        for name, offsets_ in (("blink", blink), ("blink_L", None), ("blink_R", None)):
            block = obj.shape_key_add(name=name, from_mix=False)
            if offsets_ is not None:
                block.data.foreach_set("co", (xs() + offsets_).ravel())
        obj.rotation_euler.z = np.pi  # turned to face +Y, as filie
        obj.location.x = rig.data.bones["Hips"].head_local.x
        obj.modifiers.new("Armature", 'ARMATURE').object = rig
        bpy.context.view_layer.update()
        expressions.fill(obj)
        x = xs()[:, 0]  # the mesh's own X: the character's right
        np.testing.assert_allclose(offsets(obj, "blink_L")[x < -0.1], blink[x < -0.1], atol=1e-6)
        np.testing.assert_allclose(offsets(obj, "blink_L")[x > 0.1], 0.0, atol=1e-6)

    def test_nothing_to_fill(self):
        obj = face({"a": moving(0.0, 0.5, (0, 0, -0.2)), "e": None})
        self.assertEqual(expressions.fill(obj), [])  # "e" needs "i" too
        self.assertEqual(expressions.fill(face({})), [])

    def test_the_button(self):
        obj = face({"a": moving(0.0, 0.5, (0, 0, -0.2)), "i": moving(0.0, 0.5, (0.1, 0, 0)), "e": None})
        bpy.context.view_layer.objects.active = obj
        self.assertEqual(bpy.ops.dasktoon.fill_empty_expressions(), {'FINISHED'})
        self.assertGreater(np.abs(offsets(obj, "e")).max(), 0.01)


if __name__ == "__main__":
    tu.run_tests()
