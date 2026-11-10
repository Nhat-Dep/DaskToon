# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Imported models made DaskToon characters (docs/superpowers/specs/2026-11-10-dasktoon-import-adopt-design.md): bone
names of every naming read, the skeleton matched by name and shape, weights folded and tidied, and a small
MikuMikuDance-like character built here (turned away from the front, above the floor, A-pose, twin bones, an elbow
helper turning with the forearm, a hair chain, Japanese expressions, MMD Tools' kind of material) adopted whole."""

import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

from dasktoon_import import adopt, bones, faces  # noqa: E402,F401
from dasktoon_rig import skeleton  # noqa: E402


# --- skeletons as SourceBone lists, named in each convention ---

MMD = {"Hips": "下半身", "Spine": "上半身", "Chest": "上半身2", "Neck": "首", "Head": "頭",
       "Shoulder": "肩.{s}", "UpperArm": "腕.{s}", "LowerArm": "ひじ.{s}", "Hand": "手首.{s}",
       "UpperLeg": "足.{s}", "LowerLeg": "ひざ.{s}", "Foot": "足首.{s}", "Toes": "足先EX.{s}",
       "Thumb": "親指{n}.{s}", "Index": "人指{n}.{s}", "Eye": "目.{s}"}
BIPED = {"Hips": "Bip001 Pelvis", "Spine": "Bip001 Spine", "Chest": "Bip001 Spine1", "UpperChest": "Bip001 Spine2",
         "Neck": "Bip001 Neck", "Head": "Bip001 Head", "Shoulder": "Bip001 {s} Clavicle",
         "UpperArm": "Bip001 {s} UpperArm", "LowerArm": "Bip001 {s} Forearm", "Hand": "Bip001 {s} Hand",
         "UpperLeg": "Bip001 {s} Thigh", "LowerLeg": "Bip001 {s} Calf", "Foot": "Bip001 {s} Foot",
         "Toes": "Bip001 {s} Toe0", "Thumb": "Bip001 {s} Finger0{m}", "Index": "Bip001 {s} Finger1{m}"}
UNREAL = {"Hips": "pelvis", "Spine": "spine_01", "Chest": "spine_03", "UpperChest": "spine_05", "Neck": "neck_01",
          "Head": "head", "Shoulder": "clavicle_{l}", "UpperArm": "upperarm_{l}", "LowerArm": "lowerarm_{l}",
          "Hand": "hand_{l}", "UpperLeg": "thigh_{l}", "LowerLeg": "calf_{l}", "Foot": "foot_{l}",
          "Toes": "ball_{l}", "Thumb": "thumb_0{n1}_{l}", "Index": "index_0{n1}_{l}"}
MIXAMO = {"Hips": "mixamorig:Hips", "Spine": "mixamorig:Spine", "Chest": "mixamorig:Spine1",
          "UpperChest": "mixamorig:Spine2", "Neck": "mixamorig:Neck", "Head": "mixamorig:Head",
          "Shoulder": "mixamorig:{side}Shoulder", "UpperArm": "mixamorig:{side}Arm",
          "LowerArm": "mixamorig:{side}ForeArm", "Hand": "mixamorig:{side}Hand", "UpperLeg": "mixamorig:{side}UpLeg",
          "LowerLeg": "mixamorig:{side}Leg", "Foot": "mixamorig:{side}Foot", "Toes": "mixamorig:{side}ToeBase",
          "Thumb": "mixamorig:{side}HandThumb{n1}", "Index": "mixamorig:{side}HandIndex{n1}"}
VROID = {"Hips": "J_Bip_C_Hips", "Spine": "J_Bip_C_Spine", "Chest": "J_Bip_C_Chest",
         "UpperChest": "J_Bip_C_UpperChest", "Neck": "J_Bip_C_Neck", "Head": "J_Bip_C_Head",
         "Shoulder": "J_Bip_{s}_Shoulder", "UpperArm": "J_Bip_{s}_UpperArm", "LowerArm": "J_Bip_{s}_LowerArm",
         "Hand": "J_Bip_{s}_Hand", "UpperLeg": "J_Bip_{s}_UpperLeg", "LowerLeg": "J_Bip_{s}_LowerLeg",
         "Foot": "J_Bip_{s}_Foot", "Toes": "J_Bip_{s}_ToeBase", "Thumb": "J_Bip_{s}_Thumb{n1}",
         "Index": "J_Bip_{s}_Index{n1}", "Eye": "J_Adj_{s}_FaceEye"}
FULLWIDTH = "０１２３"


def _name(table, kind, side, segment):
    pattern = table.get(kind)
    if pattern is None:
        return None
    return pattern.format(s=side[0], l=side[0].lower(), side=side, n=FULLWIDTH[segment], n1=segment + 1, m=(
        "" if segment == 0 else str(segment)))


def skeleton_named(table, flip=False):
    """The DaskToon template skeleton 1.6 tall, its bones named by `table` (bones it has no name for left out, their
    children hung on the nearest named bone); `flip` puts the character's left at -X."""
    out, renamed = [], {}
    for name, parent, head, tail, _z in skeleton.bones():
        side = "Left" if name.startswith("Left") else "Right" if name.startswith("Right") else ""
        rest = name[len(side):]
        kind, segment = rest, 0
        for finger in bones.FINGERS:
            if rest.startswith(finger):
                kind, segment = finger, bones.SEGMENTS.index(rest[len(finger):])
        source = _name(table, kind, side or "Left", segment) if (kind not in bones.SIDED and kind not in
                                                                   bones.FINGERS) == (not side) else None
        if source is None or (table is MMD and kind == "Thumb" and segment == 2):
            renamed[name] = renamed.get(parent)
            continue
        renamed[name] = source
        sign = -1.0 if flip else 1.0
        h = (head[0] * 1.6 * sign, head[1] * 1.6, head[2] * 1.6)
        t = (tail[0] * 1.6 * sign, tail[1] * 1.6, tail[2] * 1.6)
        out.append(bones.SourceBone(source, renamed.get(parent), h, t))
    return out, renamed


class NamesTest(unittest.TestCase):
    def test_every_naming(self):
        for table in (MMD, BIPED, UNREAL, MIXAMO, VROID):
            source, renamed = skeleton_named(table)
            matched, members = bones.match(source)
            for dask, name in renamed.items():
                if name is not None and (dask in matched or dask in skeleton.REQUIRED):
                    self.assertEqual(matched.get(dask), name, (table["Hips"], dask))

    def test_names_alone(self):
        for name, expected in (
                ("左足D", ("UpperLeg", "L", 0)), ("右ひざD", ("LowerLeg", "R", 0)), ("足首.L", ("Foot", "L", 0)),
                ("左親指０", ("Thumb", "L", 0)), ("右人指３", ("Index", "R", 3)), ("Bip001LFinger21", ("Middle", "L", 1)),
                ("Bip001RToe0", ("Toes", "R", 0)), ("index_metacarpal_l", None), ("upperarm_twist_01_l", None),
                ("左つま先", None), ("両目", None), ("腕捩.L", None), ("ひじ補助.R", None), ("Bone_Hair001_L", None),
                ("LeftThumbDistal", ("Thumb", "L", 2)), ("左", None), ("Bip001", None)):
            self.assertEqual(bones.classify(name), expected, name)

    def test_spine_of_any_length(self):
        for count, expected in ((1, ("s0", None, None)), (2, ("s0", "s1", None)), (3, ("s0", "s1", "s2")),
                                (5, ("s0", "s2", "s4"))):
            source, _renamed = skeleton_named(UNREAL)
            spine = [b for b in source if b.name.startswith("spine")]
            first = spine[0]
            others = [b for b in source if not b.name.startswith("spine")]
            chain = [bones.SourceBone("spine_%02d" % (k + 1), "pelvis" if k == 0 else "spine_%02d" % k,
                                      (0, 0, first.head[2] + 0.05 * k), (0, 0, first.head[2] + 0.05 * (k + 1)))
                     for k in range(count)]
            last = chain[-1].name
            others = [b._replace(parent=last) if b.parent and b.parent.startswith("spine") else b for b in others]
            matched, _members = bones.match(others + chain)
            got = tuple(matched.get(n) for n in ("Spine", "Chest", "UpperChest"))
            want = tuple(("spine_%02d" % (int(e[1:]) + 1)) if e else None for e in expected)
            self.assertEqual(got, want, count)

    def test_sides_by_where_they_are(self):
        source, _renamed = skeleton_named(MIXAMO, flip=True)  # named left, standing at -X
        matched, _members = bones.match(source)
        self.assertEqual(matched["LeftUpperArm"], "mixamorig:RightArm")
        self.assertEqual(matched["RightHand"], "mixamorig:LeftHand")

    def test_missing(self):
        source, _renamed = skeleton_named(MMD)
        with self.assertRaises(bones.MapError) as caught:
            bones.match([b for b in source if not b.name.startswith("ひざ")])
        self.assertEqual(caught.exception.missing, ["LeftLowerLeg", "RightLowerLeg"])


class WeightsTest(unittest.TestCase):
    def test_sparse_tidy_is_tidy(self):
        from dasktoon_rig import weights
        rng = np.random.default_rng(3)
        dense = rng.random((300, 9)) * (rng.random((300, 9)) < 0.5)
        dense[5] = 0.0
        dense[7] = [0.005] * 9  # all under the minimum: the largest kept
        dense[9, :6] = 0.2  # alike across the limit
        dense[11] = 0.0
        dense[11, 2] = 0.004
        rows, cols = np.nonzero(dense)
        v, c, w = adopt.sparse_tidy(rows, cols, dense[rows, cols])
        got = np.zeros_like(dense)
        got[v, c] = w
        np.testing.assert_allclose(got, weights.tidy(dense), atol=1e-9)

    def test_plan(self):
        source = [bones.SourceBone(n, p, (0, 0, 0), (0, 0, 1)) for n, p in (
            ("root", None), ("arm", "root"), ("forearm", "arm"), ("helper", "arm"), ("twist", "arm"),
            ("cancel", "root"), ("hair", "head"), ("head", "root"))]
        members = {"arm": "LeftUpperArm", "forearm": "LeftLowerArm", "head": "Head"}
        additional = {"helper": ("forearm", 0.5), "twist": ("arm", 0.25), "cancel": ("arm", -1.0)}
        out = adopt.plan(source, members, {"hair"}, {"hair": "hair"}, additional)
        self.assertEqual(out["helper"], [("LeftUpperArm", 0.5), ("LeftLowerArm", 0.5)])
        self.assertEqual(out["twist"], [("LeftUpperArm", 1.0)])
        self.assertEqual(out["cancel"], [("Hips", 1.0)])  # no parent named: the hips
        self.assertEqual(out["hair"], [("hair", 1.0)])
        self.assertEqual(out["arm"], [("LeftUpperArm", 1.0)])

    def test_chains_without_physics(self):
        source = [bones.SourceBone(n, p, (0, 0, 0), (0, 0, 1)) for n, p in (
            ("head", None), ("lock1", "head"), ("lock2", "lock1"), ("lone", "head"), ("arm_twist", "head"),
            ("arm_twist2", "arm_twist"), ("hat", "head"), ("ribbon_a1", "hat"), ("ribbon_a2", "ribbon_a1"),
            ("ribbon_b1", "hat"), ("ribbon_b2", "ribbon_b1"), ("bow", "hat"))]
        weighted = {b.name for b in source} - {"head"}
        found = adopt.chain_bones(source, {"head": "Head"}, weighted)
        self.assertEqual(found, {"lock1", "lock2", "ribbon_a1", "ribbon_a2", "ribbon_b1", "ribbon_b2"})


# --- a whole character ---

S = {"L": 1.0, "R": -1.0}
CHARACTER = [  # name, parent, head, tail, Japanese name; x of the left side (mirrored for the right)
    ("全ての親", None, (0, 0, 0), (0, 0, 0.1), "全ての親"),
    ("センター", "全ての親", (0, 0, 0.8), (0, 0, 0.7), "センター"),
    ("下半身", "センター", (0, 0, 0.95), (0, 0, 0.82), "下半身"),
    ("上半身", "センター", (0, 0, 0.95), (0, 0, 1.12), "上半身"),
    ("上半身2", "上半身", (0, 0, 1.12), (0, 0, 1.3), "上半身2"),
    ("首", "上半身2", (0, 0, 1.3), (0, 0, 1.38), "首"),
    ("頭", "首", (0, 0, 1.38), (0, 0, 1.55), "頭"),
    ("髪1", "頭", (0, 0.1, 1.5), (0, 0.11, 1.35), "髪1"),
    ("髪2", "髪1", (0, 0.11, 1.35), (0, 0.11, 1.2), "髪2"),
    ("髪3", "髪2", (0, 0.11, 1.2), (0, 0.11, 1.05), "髪3"),
]
SIDE = [
    ("肩.{s}", "上半身2", (0.02, 0, 1.28), (0.12, 0, 1.27), "{j}肩"),
    ("腕.{s}", "肩.{s}", (0.12, 0, 1.27), (0.33, 0, 1.12), "{j}腕"),
    ("ひじ.{s}", "腕.{s}", (0.33, 0, 1.12), (0.53, 0, 0.98), "{j}ひじ"),
    ("ひじ補助.{s}", "腕.{s}", (0.33, 0, 1.12), (0.33, 0, 1.08), "{j}ひじ補助"),
    ("手首.{s}", "ひじ.{s}", (0.53, 0, 0.98), (0.6, 0, 0.93), "{j}手首"),
    ("足.{s}", "下半身", (0.09, 0, 0.88), (0.09, 0, 0.48), "{j}足"),
    ("ひざ.{s}", "足.{s}", (0.09, 0, 0.48), (0.09, 0, 0.08), "{j}ひざ"),
    ("足首.{s}", "ひざ.{s}", (0.09, 0, 0.08), (0.09, -0.1, 0.02), "{j}足首"),
    ("足D.{s}", "下半身", (0.09, 0, 0.88), (0.09, 0, 0.48), "{j}足D"),
    ("ひざD.{s}", "足D.{s}", (0.09, 0, 0.48), (0.09, 0, 0.08), "{j}ひざD"),
    ("足首D.{s}", "ひざD.{s}", (0.09, 0, 0.08), (0.09, -0.1, 0.02), "{j}足首D"),
    ("足先EX.{s}", "足首D.{s}", (0.09, -0.1, 0.02), (0.09, -0.16, 0.02), "{j}足先EX"),
    ("目.{s}", "頭", (0.035, -0.09, 1.46), (0.035, -0.11, 1.46), "{j}目"),
]
# boxes of the mesh: (bone weighted, middle, size); x of the left side
BOXES = [
    ("下半身", (0, 0, 0.88), (0.24, 0.16, 0.14)), ("上半身", (0, 0, 1.03), (0.22, 0.14, 0.16)),
    ("上半身2", (0, 0, 1.21), (0.26, 0.16, 0.18)), ("首", (0, 0, 1.34), (0.06, 0.06, 0.08)),
    ("頭", (0, 0, 1.47), (0.18, 0.18, 0.18)), ("髪1", (0, 0.11, 1.42), (0.06, 0.02, 0.14)),
    ("髪2", (0, 0.11, 1.27), (0.06, 0.02, 0.14)), ("髪3", (0, 0.11, 1.12), (0.06, 0.02, 0.14)),
]
SIDE_BOXES = [
    ("腕.{s}", (0.22, 0, 1.2), (0.18, 0.06, 0.06)), ("ひじ補助.{s}", (0.33, 0, 1.12), (0.04, 0.06, 0.06)),
    ("ひじ.{s}", (0.43, 0, 1.05), (0.16, 0.05, 0.05)), ("手首.{s}", (0.57, 0, 0.96), (0.06, 0.03, 0.06)),
    ("足D.{s}", (0.09, 0, 0.68), (0.1, 0.1, 0.36)), ("ひざD.{s}", (0.09, 0, 0.29), (0.08, 0.08, 0.36)),
    ("足首D.{s}", (0.09, -0.04, 0.04), (0.08, 0.2, 0.06)), ("目.{s}", (0.035, -0.095, 1.46), (0.03, 0.01, 0.02)),
]
TURN = Matrix.Translation((0.3, 0.2, 0.5)) @ Matrix.Rotation(math.pi, 4, 'Z')  # away from the front, in the air


def _sided(entries):
    """The entries with "{s}" once for each side, the right's x mirrored: bones (name, parent, head, tail, Japanese)
    and boxes (bone, middle, size)."""
    out = []
    for entry in entries:
        if "{s}" not in entry[0]:
            out.append(entry)
            continue
        places = (2, 3) if len(entry) == 5 else (1,)
        for s, j in (("L", "左"), ("R", "右")):
            fill = [e.format(s=s, j=j) if isinstance(e, str) else e for e in entry]
            for k in places:
                fill[k] = (fill[k][0] * S[s], fill[k][1], fill[k][2])
            out.append(tuple(fill))
    return out


def build_character(context):
    """The MikuMikuDance-like character of the module docstring: (armature, mesh, material)."""
    data = bpy.data.armatures.new("Tester_arm")
    arm = bpy.data.objects.new("Tester_arm", data)
    context.collection.objects.link(arm)
    context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    entries = _sided(CHARACTER + SIDE)
    for name, parent, head, tail, _j in entries:
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    for name, _parent, _head, _tail, japanese in entries:
        arm.pose.bones[name].mmd_bone.name_j = japanese
    for s in ("L", "R"):
        helper = arm.pose.bones["ひじ補助." + s].mmd_bone
        helper.has_additional_rotation = True
        helper.additional_transform_bone = "ひじ." + s
        helper.additional_transform_influence = 0.5
    verts, faces_, groups = [], [], []
    for bone, middle, size in _sided(BOXES + SIDE_BOXES):
        base = len(verts)
        for dx in (-0.5, 0.5):
            for dy in (-0.5, 0.5):
                for dz in (-0.5, 0.5):
                    verts.append((middle[0] + dx * size[0], middle[1] + dy * size[1], middle[2] + dz * size[2]))
        faces_ += [[base + a for a in f] for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6),
                                                   (0, 2, 6, 4), (1, 5, 7, 3))]
        groups += [bone] * 8
    mesh = bpy.data.meshes.new("Tester_mesh")
    mesh.from_pydata(verts, [], faces_)
    obj = bpy.data.objects.new("Tester_mesh", mesh)
    context.collection.objects.link(obj)
    for index, bone in enumerate(groups):
        group = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        group.add([index], 1.0, 'REPLACE')
    obj.modifiers.new("mmd_armature", 'ARMATURE').object = arm
    obj.parent = arm
    _expressions(obj, groups)
    mat = _mmd_material()
    mesh.materials.append(mat)
    arm.matrix_world = TURN
    context.view_layer.update()
    return arm, obj, mat


def _expressions(obj, groups):
    obj.shape_key_add(name="Basis")
    co = np.array([v.co[:] for v in obj.data.vertices])
    head = [i for i, g in enumerate(groups) if g == "頭"]
    eye_l = [i for i, g in enumerate(groups) if g == "目.L"]
    eye_r = [i for i, g in enumerate(groups) if g == "目.R"]

    def key(name, vertices, move):
        block = obj.shape_key_add(name=name, from_mix=False)
        block.value = 0.0
        for i in vertices:
            block.data[i].co = Vector(co[i]) + Vector(move)
    key("あ", head[:1], (0, 0, -0.01))
    key("まばたき", eye_l + eye_r, (0, 0, -0.005))
    key("ｳｨﾝｸ２右", eye_l, (0, 0, -0.005))  # named the right, closes the character's left (+X): the side decides
    key("ウィンク２", eye_r, (0, 0, -0.005))
    key("にこり", head[1:2], (0, 0, 0.01))
    key("笑い", eye_l + eye_r, (0, 0, -0.003))
    key("口角上げ", head[2:3], (0, 0, 0.004))
    key("mmd_sdef_c", head, (0, 0, 0))


def _mmd_material():
    """MMD Tools' kind of material: a group taking Ambient and Diffuse colours before its texture, an Anime BSDF the
    new material started with left unhooked."""
    group = bpy.data.node_groups.new("MMDShaderDev", 'ShaderNodeTree')
    for name, kind in (("Ambient Color", 'NodeSocketColor'), ("Diffuse Color", 'NodeSocketColor'),
                       ("Base Tex", 'NodeSocketColor'), ("Base Alpha", 'NodeSocketFloat')):
        group.interface.new_socket(name, in_out='INPUT', socket_type=kind)
    group.interface.new_socket("Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
    inside_in, inside_out = group.nodes.new('NodeGroupInput'), group.nodes.new('NodeGroupOutput')
    emission = group.nodes.new('ShaderNodeEmission')
    group.links.new(inside_in.outputs["Base Tex"], emission.inputs["Color"])
    group.links.new(emission.outputs[0], inside_out.inputs["Shader"])
    mat = bpy.data.materials.new("Tester_mat")
    mat.use_nodes = True
    tree = mat.node_tree
    for node in list(tree.nodes):
        if node.bl_idname != 'ShaderNodeOutputMaterial':
            tree.nodes.remove(node)
    tree.nodes.new('ShaderNodeAnimeCharacter')  # unhooked
    node = tree.nodes.new('ShaderNodeGroup')
    node.node_tree = group
    node.inputs["Ambient Color"].default_value = (0.4, 0.4, 0.4, 1.0)
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.new("Tester_tex", 4, 4)
    tree.links.new(tex.outputs["Color"], node.inputs["Base Tex"])
    tree.links.new(tex.outputs["Alpha"], node.inputs["Base Alpha"])
    output = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    tree.links.new(node.outputs["Shader"], output.inputs["Surface"])
    return mat


def _evaluated(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(depsgraph)
    count = len(obj.data.vertices)  # the outline adds its hull after the mesh
    return np.array([obj.matrix_world @ v.co for v in ev.data.vertices[:count]])


def _group_weights(obj, index):
    return {obj.vertex_groups[g.group].name: g.weight for g in obj.data.vertices[index].groups}


class CharacterTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.context = bpy.context
        self.arm, self.obj, self.mat = build_character(self.context)
        self.before = np.array([TURN @ v.co for v in self.obj.data.vertices])  # as shown, before

    def test_adopted(self):
        from dasktoon_guide import checks
        self.assertFalse(checks.is_dasktoons(self.mat))  # the unhooked Anime BSDF does not count
        result = adopt.adopt(self.context, self.arm, [self.obj], kind='MMD', swaying={"髪1", "髪2", "髪3"})
        rig, obj = result.rig, self.obj
        self.assertEqual(rig.name, "Tester_arm")
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertEqual([o.name for o in bpy.data.objects if o.type == 'ARMATURE'], ["Tester_arm"])
        self.assertEqual(obj.parent, rig)
        self.assertEqual(obj.modifiers[0].object, rig)
        self.assertEqual(rig.data[adopt.IMPORTED], 'MMD')
        # standing: turned to face -Y, on the floor, in the middle, every transform applied; nothing moves at rest
        self.assertTrue(np.allclose(np.array(rig.matrix_world), np.eye(4), atol=1e-6))
        self.assertTrue(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-6))
        self.assertTrue(rig.data.dasktoon_rig.live_sway)
        for frame in range(1, 25):  # standing still with the sway on: the hair keeps its modelled shape, though it is
            bpy.context.scene.frame_set(frame)  # rooted inside the head's collider
        self.assertEqual({k.name: k.value for k in obj.data.shape_keys.key_blocks[1:] if k.value}, {})
        shown = _evaluated(obj)
        np.testing.assert_allclose(shown, [v.co[:] for v in obj.data.vertices], atol=1e-5)
        self.assertAlmostEqual(float(shown[:, 2].min()), 0.0, places=4)
        eyes = shown[self._box("目.L")]
        self.assertTrue((eyes[:, 1] < 0.0).all() and (eyes[:, 0] > 0.0).all())  # in front, the left eye at +X
        c = checks._Context(self.context, [obj], rig)
        self.assertEqual(checks.check_middle(c)[0], 'OK')
        self.assertEqual(checks.check_facing(c)[0], 'OK')
        bones_ = rig.data.bones
        self.assertGreater(bones_["LeftUpperArm"].head_local.x, 0.0)  # the character's left at +X
        hips, chest = bones_["Hips"].head_local, bones_["Chest"].head_local
        self.assertAlmostEqual(bones_["LeftUpperArm"].head_local.z - hips.z, 1.27 - 0.88, places=4)
        self.assertAlmostEqual(bones_["LeftUpperArm"].head_local.x - hips.x, 0.12, places=4)
        self.assertAlmostEqual(chest.z - hips.z, 1.12 - 0.88, places=4)  # Hips between the legs, Chest at 上半身2
        self.assertAlmostEqual(bones_["UpperChest"].head_local.z - chest.z, 0.45 * 0.18, places=4)
        # weights: twins and helpers folded, at most four, summing to one
        for vertex in obj.data.vertices:
            weights = [g.weight for g in vertex.groups]
            self.assertLessEqual(len(weights), 4)
            self.assertAlmostEqual(sum(weights), 1.0, places=5)
        groups = {g.name for g in obj.vertex_groups}
        self.assertFalse(groups & {"足D.L", "ひじ補助.L", "全ての親", "mmd_sdef_c"})
        self.assertEqual(_group_weights(obj, self._box("ひじ補助.L")[0]), {"LeftUpperArm": 0.5, "LeftLowerArm": 0.5})
        self.assertEqual(_group_weights(obj, self._box("足D.L")[0]), {"LeftUpperLeg": 1.0})
        # the hair sways, with colliders
        from dasktoon_rig import build, sway
        self.assertEqual(result.chains, 1)
        self.assertEqual([names for _part, names in sway.chains(rig)], [["髪1", "髪2", "髪3"]])
        self.assertEqual(bones_["髪1"].parent.name, "Head")
        self.assertTrue(all(sway.spring_constraint(rig.pose.bones[n]) for n in ("髪1", "髪2", "髪3")))
        self.assertIn("Head", {c.bone for c in rig.data.dasktoon_rig.colliders})
        self.assertNotIn(build.MARK, bones_["Head"])
        # posed: the forearm takes the hand and half the elbow helper, not the upper arm
        rig.data.dasktoon_rig.live_sway = False
        rest = _evaluated(obj)
        pb = rig.pose.bones["LeftLowerArm"]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, 0.0, 1.2)
        moved = np.linalg.norm(_evaluated(obj) - rest, axis=1)
        self.assertGreater(moved[self._box("手首.L")].min(), 0.05)
        self.assertLess(moved[self._box("腕.L")].max(), 1e-6)
        helper = moved[self._box("ひじ補助.L")]
        self.assertTrue((helper > 0.0).any() and helper.max() < moved[self._box("手首.L")].min())
        # expressions
        key = obj.data.shape_keys.key_blocks
        names = {k.name for k in key}
        self.assertTrue({"A", "Blink", "Blink_L", "Blink_R", "Joy"} <= names, names)
        self.assertFalse({"あ", "まばたき"} & names)
        offsets = lambda name: np.array([(k.co - b.co)[:] for k, b in zip(key[name].data, key["Basis"].data)])
        left = np.nonzero(np.linalg.norm(offsets("Blink_L"), axis=1))[0]
        self.assertGreater(float(np.array([obj.data.vertices[i].co.x for i in left]).min()), 0.0)
        np.testing.assert_allclose(offsets("Joy"), offsets("にこり") + offsets("笑い") + offsets("口角上げ"), atol=1e-6)
        # DaskToon's shader, fed the texture, not the ambient colour
        self.assertTrue(checks.is_dasktoons(self.mat))
        anime = next(n for n in self.mat.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter'
                     and n.inputs["Base Color"].is_linked)
        self.assertEqual(anime.inputs["Base Color"].links[0].from_node.bl_idname, 'ShaderNodeTexImage')
        self.assertTrue(anime.inputs["Alpha"].is_linked)
        self.assertFalse(anime.use_outline)  # no outline by default: its hull makes a many-boned model play slowly
        self.assertFalse([m for m in obj.modifiers if m.type == 'NODES'])
        anime.use_outline = True  # turned on later: the outline is the texture, darker
        self.assertTrue(anime.inputs["Outline Color"].is_linked)

    def _box(self, bone):
        boxes = _sided(BOXES + SIDE_BOXES)
        k = [b[0] for b in boxes].index(bone)
        return list(range(8 * k, 8 * k + 8))

    def test_a_skeleton_it_cannot_use_stays(self):
        self.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in self.arm.data.edit_bones:
            if bone.name.startswith("ひざ"):  # no knees
                bone.name = "knee_helper" + bone.name[-2:]
        bpy.ops.object.mode_set(mode='OBJECT')
        for pb in self.arm.pose.bones:
            if pb.name.startswith("knee_helper"):
                pb.mmd_bone.name_j = ""
        with self.assertRaises(adopt.AdoptError):
            adopt.adopt(self.context, self.arm, [self.obj], kind='MMD')
        self.assertTrue(np.allclose(np.array(self.arm.matrix_world), np.array(TURN), atol=1e-6))
        self.assertIn("足D.L", self.obj.vertex_groups)
        self.assertIn("mmd_sdef_c", self.obj.data.shape_keys.key_blocks)


if __name__ == "__main__":
    tu.run_tests()
