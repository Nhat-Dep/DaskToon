# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Import › Unreal Model (.uemodel): a small model written here in the two layouts FModel has used (sections
before version 10, attribute sets from 10), imported, and checked in Blender's units and axes."""

import os
import struct
import sys
import tempfile
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

# Unreal centimetres, left-handed: a quad of two triangles standing up, two bones.
VERTICES = [(0, 0, 0), (100, 0, 0), (100, 50, 100), (0, 50, 100)]
NORMALS = [(0, -1, 0)] * 4
UVS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.25, 0.25)]
INDICES = [0, 1, 2, 0, 2, 3]
MATERIALS = [("Skin", 0, 1), ("Cloth", 3, 1)]  # name, first index, faces
WEIGHTS = [(0, 0, 0.5), (1, 0, 0.5), (0, 1, 1.0), (1, 2, 1.0), (1, 3, 1.0)]  # bone, vertex, weight
MORPH = ("Smile", [((0, 0, 10), 3)])  # +10 cm up on vertex 3
BONES = [("Root", -1, (0, 0, 0)), ("Spine", 0, (0, 0, 100))]


def s(text):
    data = text.encode("utf-8")
    return struct.pack("<i", len(data)) + data


def floats(values):
    flat = np.asarray(values, np.float32).ravel()
    return flat.tobytes()


def weights():
    return b"".join(struct.pack("<Hif", b, v, w) for b, v, w in WEIGHTS)


def morph_deltas():
    return b"".join(floats(pos) + floats((0, 0, 0)) + struct.pack("<I", v) for pos, v in MORPH[1])


def bones(with_scale):
    out = b""
    for name, parent, pos in BONES:
        out += s(name) + struct.pack("<i", parent) + floats(pos) + floats((0, 0, 0, 1))
        if with_scale:
            out += floats((1, 1, 1))
    return out


def chunk(name, count, data):
    return s(name) + struct.pack("<ii", count, len(data)) + data


def version_9():
    lod = b"".join((
        chunk("VERTICES", 4, floats(VERTICES)),
        chunk("NORMALS", 4, b"".join(floats((1.0,) + n) for n in NORMALS)),
        chunk("TEXCOORDS", 1, struct.pack("<i", 4) + floats(UVS)),
        chunk("INDICES", 6, struct.pack("<6I", *INDICES)),
        chunk("MATERIALS", 2, b"".join(s(n) + s("/Game/" + n) + struct.pack("<ii", f, c) for n, f, c in MATERIALS)),
        chunk("WEIGHTS", len(WEIGHTS), weights()),
        chunk("MORPHTARGETS", 1, s(MORPH[0]) + struct.pack("<i", len(MORPH[1])) + morph_deltas()),
    ))
    body = chunk("LODS", 1, s("LOD0") + struct.pack("<i", len(lod)) + lod)
    body += chunk("SKELETON", 0, chunk("BONES", len(BONES), bones(False)))
    return b"UEFORMAT" + s("UEMODEL") + bytes((9,)) + s("Tester") + b"\x00" + body


def attribute_set(items):
    return struct.pack("<i", len(items)) + b"".join(s(n) + struct.pack("<i", len(d)) + d for n, d in items)


def counted(count, data):
    return struct.pack("<i", count) + data


def version_10():
    lod = s("LOD0") + attribute_set([
        ("VERTICES", counted(4, floats(VERTICES))),
        ("NORMALS", counted(4, b"".join(floats((1.0,) + n) for n in NORMALS))),
        ("TEXCOORDS", counted(1, s("UV0") + struct.pack("<i", 4) + floats(UVS))),
        ("INDICES", counted(6, struct.pack("<6I", *INDICES))),
        ("MATERIALS", counted(2, b"".join(s(n) + s("/Game/" + n) + struct.pack("<ii", f, c) for n, f, c in MATERIALS))),
        ("WEIGHTS", counted(len(WEIGHTS), weights())),
        ("MORPHTARGETS", counted(1, s(MORPH[0]) + struct.pack("<i", len(MORPH[1])) + morph_deltas())),
    ])
    body = attribute_set([("LODS", counted(1, lod)),
                          ("SKELETON", attribute_set([("BONES", counted(len(BONES), bones(True)))]))])
    return b"UEFORMAT" + s("UEMODEL") + bytes((10,)) + s("Tester") + s("/Game/Tester") + b"\x00" + body


class ImportUEModelTest(unittest.TestCase):
    def import_bytes(self, data):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "Tester.uemodel")
        with open(path, "wb") as stream:
            stream.write(data)
        self.assertEqual(bpy.ops.dasktoon.import_uemodel(filepath=path), {'FINISHED'})
        obj = bpy.data.objects["Tester"]
        rig = bpy.data.objects["Tester_Rig"]
        return obj, rig

    def check(self, obj, rig):
        mesh = obj.data
        co = np.array([v.co for v in mesh.vertices])
        np.testing.assert_allclose(co[2], (1.0, -0.5, 1.0), atol=1e-6)  # metres, Y mirrored from Unreal's
        self.assertEqual([p.material_index for p in mesh.polygons], [0, 1])
        self.assertEqual([m.name for m in mesh.materials], ["Skin", "Cloth"])
        uv = mesh.uv_layers["UV0"].uv
        corner = next(i for i, loop in enumerate(mesh.loops) if loop.vertex_index == 3)
        np.testing.assert_allclose(uv[corner].vector, (0.25, 0.75), atol=1e-6)  # upside down, as Blender has UVs
        smile = mesh.shape_keys.key_blocks["Smile"]
        np.testing.assert_allclose(smile.data[3].co, (0.0, -0.5, 1.1), atol=1e-6)
        np.testing.assert_allclose(smile.data[2].co, co[2], atol=1e-6)
        groups = {g.name: g.index for g in obj.vertex_groups}
        first = {groups_name: g.weight for g in mesh.vertices[0].groups
                 for groups_name, index in groups.items() if index == g.group}
        self.assertAlmostEqual(first["Root"], 0.5, places=5)
        self.assertAlmostEqual(first["Spine"], 0.5, places=5)
        self.assertEqual(rig.data.bones["Spine"].parent.name, "Root")
        np.testing.assert_allclose(rig.data.bones["Spine"].head_local, (0.0, 0.0, 1.0), atol=1e-6)
        self.assertEqual(obj.modifiers["Armature"].object, rig)

    def test_sections_layout(self):
        self.check(*self.import_bytes(version_9()))

    def test_attribute_sets_layout(self):
        self.check(*self.import_bytes(version_10()))

    def test_not_a_uemodel(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = os.path.join(tempfile.mkdtemp(), "Bad.uemodel")
        with open(path, "wb") as stream:
            stream.write(b"not a model")
        with self.assertRaises(RuntimeError):  # the operator reports the error and cancels
            bpy.ops.dasktoon.import_uemodel(filepath=path)


if __name__ == "__main__":
    tu.run_tests()
