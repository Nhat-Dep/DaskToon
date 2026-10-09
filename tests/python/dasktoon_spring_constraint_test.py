# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Spring constraint (anime rig spec 9.4): the constraint type, its colliders and settings, and how it sways
a bone like dasktoon_rig/spring.py."""

import math
import os
import sys
import tempfile
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402


def chain_rig(count=3):
    """An armature with a body bone "Spine" (up) and a horizontal chain "Tail_1".."Tail_<count>" along +Y from its top."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    spine = data.edit_bones.new("Spine")
    spine.head, spine.tail = (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    parent = spine
    for k in range(1, count + 1):
        bone = data.edit_bones.new("Tail_%d" % k)
        bone.head = (0.0, 0.1 * (k - 1), 1.0)
        bone.tail = (0.0, 0.1 * k, 1.0)
        bone.parent = parent
        bone.use_connect = k > 1
        parent = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def add_springs(rig, count=3, colliders=()):
    for k in range(1, count + 1):
        con = rig.pose.bones["Tail_%d" % k].constraints.new('SPRING')
        for bone, radius in colliders:
            item = con.colliders.new()
            item.target = rig
            item.subtarget = bone
            item.radius = radius
    return [rig.pose.bones["Tail_%d" % k].constraints[0] for k in range(1, count + 1)]


class TypeTest(unittest.TestCase):
    def test_new_spring_constraint(self):
        rig = chain_rig()
        con = rig.pose.bones["Tail_1"].constraints.new('SPRING')
        self.assertEqual(con.type, 'SPRING')
        self.assertEqual(con.bl_rna.identifier, "SpringConstraint")
        np.testing.assert_allclose((con.stiffness, con.gravity, con.drag), (1.0, 0.2, 0.4), rtol=1e-6)
        self.assertAlmostEqual(con.radius, 0.03, places=6)
        self.assertEqual(len(con.colliders), 0)
        item = con.colliders.new()
        self.assertEqual(item.target, rig)
        item.subtarget = "Spine"
        item.radius = 0.25
        self.assertEqual((con.colliders[0].subtarget, round(con.colliders[0].radius, 6)), ("Spine", 0.25))
        self.assertEqual(con.colliders[0].path_from_id(), 'pose.bones["Tail_1"].constraints["Spring"].colliders[0]')
        con.colliders.clear()
        self.assertEqual(len(con.colliders), 0)

    def test_save_and_reload_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        rig.pose.bones["Tail_1"].constraints[0].stiffness = 2.5
        path = os.path.join(tempfile.mkdtemp(prefix="dt_spring_"), "spring.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        con = bpy.data.objects["Rig"].pose.bones["Tail_1"].constraints[0]
        self.assertEqual(con.type, 'SPRING')
        self.assertAlmostEqual(con.stiffness, 2.5, places=6)
        self.assertEqual([(c.target.name, c.subtarget) for c in con.colliders], [("Rig", "Spine")])
        self.assertAlmostEqual(con.colliders[0].radius, 0.2, places=6)

    def test_copy_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        copy = rig.copy()
        bpy.context.scene.collection.objects.link(copy)
        con = copy.pose.bones["Tail_1"].constraints[0]
        self.assertEqual([c.subtarget for c in con.colliders], ["Spine"])

    def test_panels_and_texts(self):
        from bl_ui import properties_constraint as pc
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint"))
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint_colliders"))
        item = next(i for i in bpy.types.Constraint.bl_rna.properties["type"].enum_items if i.identifier == 'SPRING')
        strings = {item.name, item.description, bpy.types.SpringConstraint.bl_rna.description}
        for struct in (bpy.types.SpringConstraint, bpy.types.SpringConstraintCollider):
            for prop in struct.bl_rna.properties:
                if prop.identifier in bpy.types.Constraint.bl_rna.properties or prop.identifier == "rna_type":
                    continue
                strings.update((prop.name, prop.description))
        strings.discard("")
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])


if __name__ == "__main__":
    tu.run_tests()
