# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export merges the meshes of a character into one (the user's choice, 2026-10-20): the meshes its armature
deforms become one mesh named after its Body in the FBX of the model and of every clip, each material kept; the file
being worked on stays as it was. Off, the meshes go out one by one as before."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import rig_json, targets  # noqa: E402
from dasktoon_rig import build  # noqa: E402

PARTS = (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT'))


def built(parts=PARTS):
    """The rig fixture's character with these parts, built; every part has a material of its own."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    for name in [name for name in objs if name not in dict(parts)]:  # pieces of the fixture not used here
        bpy.data.objects.remove(objs.pop(name))
    rig = fx.rig_for()
    for name, role in parts:
        objs[name].data.materials.append(bpy.data.materials.new(name + " Material"))
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    return rig, objs


def export(merge=True):
    """Engine Export of the scene to a new folder; returns (report, folder of the written files)."""
    target = targets.make_target(tempfile.mkdtemp(prefix="dt_merge_"), "Hero", 'UNITY_URP')
    objects = [obj for obj in bpy.context.view_layer.objects if obj.type in ('MESH', 'ARMATURE')]
    rep = dasktoon_export.export_model(bpy.context, target, objects, dasktoon_export.ExportOptions(
        export_materials=False, merge_meshes=merge))
    return rep, target.root


def imported(path):
    """The meshes of the FBX at `path`, imported into an empty file."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    return [obj for obj in bpy.data.objects if obj.type == 'MESH']


class MergeTest(unittest.TestCase):
    def test_one_mesh_named_after_the_body(self):
        _rig, objs = built()
        counts = {name: len(objs[name].data.vertices) for name, _role in PARTS}
        rep, root = export()
        self.assertIn("Body", " ".join(rep.lines()))
        meshes = imported(os.path.join(root, rep.model))
        self.assertEqual([obj.name for obj in meshes], ["Body"])
        mesh = meshes[0].data
        self.assertEqual(len(mesh.vertices), sum(counts.values()))
        self.assertEqual(sorted(m.name for m in mesh.materials), sorted(name + " Material" for name, _r in PARTS))
        self.assertIn("Hair_1", meshes[0].vertex_groups)  # the hair's chain still sways it
        self.assertIn("Spine", meshes[0].vertex_groups)

    def test_off_keeps_the_meshes(self):
        built()
        rep, root = export(merge=False)
        self.assertEqual(sorted(obj.name for obj in imported(os.path.join(root, rep.model))),
                         sorted(name for name, _role in PARTS))

    def test_the_file_is_left_as_it_was(self):
        rig, objs = built()
        names = sorted(obj.name for obj in bpy.data.objects)
        counts = (len(bpy.data.meshes), len(bpy.data.shape_keys), len(bpy.data.materials))
        modifiers = {name: [m.name for m in objs[name].modifiers] for name, _role in PARTS}
        export()
        self.assertEqual(sorted(obj.name for obj in bpy.data.objects), names)
        self.assertEqual((len(bpy.data.meshes), len(bpy.data.shape_keys), len(bpy.data.materials)), counts)
        self.assertEqual({name: [m.name for m in objs[name].modifiers] for name, _role in PARTS}, modifiers)
        self.assertEqual(objs["Body"].name, "Body")

    def test_the_render_uv_maps_join(self):
        """Joined, UV maps of other names became other UV maps: Unity reads the first, so the shirt's texture would
        have come out wrong."""
        _rig, objs = built()
        objs["Body"].data.uv_layers.new(name="UVMap")
        objs["Shirt"].data.uv_layers.new(name="Shirt UV")
        objs["Hair"].data.uv_layers.new(name="Hair UV")
        rep, root = export()
        mesh = imported(os.path.join(root, rep.model))[0].data
        render = [layer.name for layer in mesh.uv_layers if not layer.name.startswith("DT_")]
        self.assertEqual(render, ["UVMap"])

    def test_shape_key_animation_in_clips(self):
        from dasktoon_animation import clips
        rig, objs = built()
        body = objs["Body"]
        body.shape_key_add(name="Basis")
        body.shape_key_add(name="Smile").data[0].co.x += 0.05
        scene = bpy.context.scene
        clip = clips.new(rig, list(bpy.context.view_layer.objects), "Smile", scene=scene)
        key = body.data.shape_keys
        for frame, value in ((1, 0.0), (10, 1.0)):
            key.key_blocks["Smile"].value = value
            key.key_blocks["Smile"].keyframe_insert("value", frame=frame)
        rep, root = export()
        self.assertEqual([name for name, _loop in rep.clips], [clip.name])
        model = os.path.join(root, rep.model)
        meshes = imported(os.path.join(os.path.dirname(model), "Hero@Smile.fbx"))
        self.assertEqual([obj.name for obj in meshes], ["Body"])
        anim = meshes[0].data.shape_keys.animation_data
        self.assertTrue(anim is not None and anim.action is not None)
        bpy.context.scene.frame_set(10)
        self.assertGreater(meshes[0].data.shape_keys.key_blocks["Smile"].value, 0.9)

    def test_a_flat_eye_on_a_mesh_of_its_own_points_at_the_merged_mesh(self):
        built(PARTS + (("Eye", 'FLAT_EYE'),))
        rep, root = export()
        with open(os.path.join(root, rep.rig), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([eye["object"] for eye in data["flatEyes"]], ["Body"])
        self.assertEqual([eye["material"] for eye in data["flatEyes"]], ["Eye Material"])


if __name__ == "__main__":
    tu.run_tests()
