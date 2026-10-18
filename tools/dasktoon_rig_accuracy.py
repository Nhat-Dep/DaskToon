# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""How accurate an anime rig is, measured on a rigged file (work on a copy of a model).

DaskToon.exe -b <rigged copy.blend> --python tools/dasktoon_rig_accuracy.py -- [<report.json>]

Prints lines starting with "ACC" and, given a path, writes them as JSON:

- joints: how far the bones pass from the middle of the limb round them (JOINTS: near the roots of the arms and
  legs, at the elbows and knees, above the wrists and ankles, the neck and the waist): the innermost outline round the
  bone where a plane across it cuts the Body meshes as shown (else Body and Clothing), its centre by area, the distance
  as a share of the outline's radius;
- poses: in each test pose of the Check, the meshes as shown (modifiers on, so the half a Mirror makes counts): edges
  grown past 1.5 and 2.5 times and by more than GROWN of the height (a tiny edge doubling is no tear), triangles
  squashed under 40% of their area, and where the worst are;
- symmetry: on meshes that are their own mirror image across the skeleton's middle, how much a vertex's weights differ
  from its mirror vertex's (Left and Right bones swapped);
- leaks: an arm's or a leg's weight on vertices farther than FAR of the height from every bone of that limb.
"""

import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# Where the bone line is measured against the limb round it: (bone, share of the way from its head to its tail, the
# bone before it when the point is a joint, for the plane across both).
JOINTS = {
    "LeftArmRoot": ("LeftUpperArm", 0.2, None), "RightArmRoot": ("RightUpperArm", 0.2, None),
    "LeftElbow": ("LeftLowerArm", 0.0, "LeftUpperArm"), "RightElbow": ("RightLowerArm", 0.0, "RightUpperArm"),
    "LeftAboveWrist": ("LeftLowerArm", 0.85, None), "RightAboveWrist": ("RightLowerArm", 0.85, None),
    "LeftThighRoot": ("LeftUpperLeg", 0.15, None), "RightThighRoot": ("RightUpperLeg", 0.15, None),
    "LeftKnee": ("LeftLowerLeg", 0.0, "LeftUpperLeg"), "RightKnee": ("RightLowerLeg", 0.0, "RightUpperLeg"),
    "LeftAboveAnkle": ("LeftLowerLeg", 0.85, None), "RightAboveAnkle": ("RightLowerLeg", 0.85, None),
    "Neck": ("Neck", 0.5, None), "Waist": ("Spine", 0.5, None),
}
REACH = 0.12  # (x height) the cross-section: triangles this near the joint
TRUNK_REACH = 0.3  # (x height) the same for the waist: wider than a limb (cut short, no outline closes)
STRETCHED, TORN, SQUASHED = 1.5, 2.5, 0.4
GROWN = 0.003  # (x height) an edge must also grow by this much
FAR = 0.1
out = {"joints": {}, "poses": {}, "symmetry": {}, "leaks": {}}


def log(*parts):
    print("ACC", *parts)


def rig_and_parts():
    from dasktoon_rig import skeleton
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and skeleton.is_humanoid(o))
    parts = [p for p in rig.data.dasktoon_rig.parts if p.object is not None and p.object.type == 'MESH']
    return rig, parts


def evaluated(obj):
    """World positions and loop triangles of obj as shown."""
    shown = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = shown.to_mesh()
    try:
        co = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", co)
        mesh.calc_loop_triangles()
        tris = np.empty(len(mesh.loop_triangles) * 3, np.int64)
        mesh.loop_triangles.foreach_get("vertices", tris)
        edges = np.empty(len(mesh.edges) * 2, np.int64)
        mesh.edges.foreach_get("vertices", edges)
    finally:
        shown.to_mesh_clear()
    matrix = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3], tris.reshape(-1, 3), edges.reshape(-1, 2)


def joints(rig, parts, height):
    from dasktoon_rig import sections
    skin = list(dict.fromkeys(p.object for p in parts if p.role == 'BODY'))
    body = list(dict.fromkeys(skin + [p.object for p in parts if p.role == 'CLOTHING']))
    meshes = {obj: evaluated(obj) for obj in body}
    for joint, (bone, share, before) in JOINTS.items():
        if rig.data.bones.get(bone) is None or (before is not None and rig.data.bones.get(before) is None):
            continue
        b = rig.data.bones[bone]
        point = np.array(rig.matrix_world @ (b.head_local + (b.tail_local - b.head_local) * share))
        direction = (b.tail_local - b.head_local).normalized()
        if before is not None:
            p = rig.data.bones[before]
            direction = direction + (p.tail_local - p.head_local).normalized()
        along = np.array((rig.matrix_world.to_3x3() @ direction).normalized())
        if joint == "Neck":  # its own cross-section, level: across a neck bone leaning forward the cut ran into the jaw
            along = np.array((0.0, 0.0, 1.0))
        best = None
        for name, objects in (("skin", skin), ("body", body)):
            found = []
            for obj in objects:
                world, tris, _edges = meshes[obj]
                reach = TRUNK_REACH if joint == "Waist" else REACH
                for loop in sections.outlines(world, tris, point, along, reach * height):
                    found.append(sections.outline(loop, point, along))
            inside = [f for f in found if f[2] and f[0] > 0.0]
            if inside:
                best = (name,) + min(inside, key=lambda f: f[0])  # the innermost outline round the bone
                break
            if found and best is None:
                best = (name,) + min(found, key=lambda f: np.linalg.norm(f[1] - point))
        if best is None:
            log("joint", joint, "no cross-section")
            continue
        name, area, centre, inside = best
        radius = math.sqrt(area / math.pi)
        world_offset = centre - point  # from the bone to the middle of the limb
        offset = float(np.linalg.norm(world_offset))
        out["joints"][joint] = {"mesh": name, "offset": round(offset, 4), "radius": round(radius, 4),
                                "share": round(offset / max(radius, 1e-9), 3), "inside": bool(inside),
                                "towards": [round(float(c), 4) for c in world_offset]}
        log("joint %-15s %s%s offset %5.1f mm (x %+5.1f, y %+5.1f, z %+5.1f), radius %5.1f mm, share %.2f" % (
            joint, name, "" if inside else " (outside it)", offset * 1000.0, world_offset[0] * 1000.0,
            world_offset[1] * 1000.0, world_offset[2] * 1000.0, radius * 1000.0, offset / max(radius, 1e-9)))


def nearest_bones(rig, points):
    names = [b.name for b in rig.data.bones if b.use_deform]
    from dasktoon_rig import chains, parts as rig_parts
    distance = np.stack([chains.segment_distance(points, *rig_parts.bone_segment(rig, n)) for n in names], axis=1)
    return [names[i] for i in distance.argmin(axis=1)]


def poses(rig, parts, height):
    from dasktoon_rig import check
    objects = list(dict.fromkeys(p.object for p in parts))
    check.apply_pose(bpy.context, rig, 'REST')
    rest = {obj: evaluated(obj) for obj in objects}
    for pose in check.TRIED:
        check.apply_pose(bpy.context, rig, pose)
        summary = {"stretched": 0, "torn": 0, "squashed": 0, "spots": []}
        for obj in objects:
            world, tris, edges = rest[obj]
            moved, tris2, edges2 = evaluated(obj)
            if len(moved) != len(world) or len(edges) == 0:
                continue
            length0 = np.linalg.norm(world[edges[:, 0]] - world[edges[:, 1]], axis=1)
            length1 = np.linalg.norm(moved[edges[:, 0]] - moved[edges[:, 1]], axis=1)
            ratio = np.where(length1 - length0 > GROWN * height, length1 / np.maximum(length0, 1e-9), 1.0)
            area0 = np.linalg.norm(np.cross(world[tris[:, 1]] - world[tris[:, 0]], world[tris[:, 2]] - world[tris[:, 0]]),
                                   axis=1)
            area1 = np.linalg.norm(np.cross(moved[tris[:, 1]] - moved[tris[:, 0]], moved[tris[:, 2]] - moved[tris[:, 0]]),
                                   axis=1)
            squashed = (area1 < SQUASHED * area0) & (area0 > 1e-12)
            summary["stretched"] += int((ratio > STRETCHED).sum())
            summary["torn"] += int((ratio > TORN).sum())
            summary["squashed"] += int(squashed.sum())
            bad = np.concatenate([world[edges[ratio > STRETCHED]].reshape(-1, 3), world[tris[squashed]].reshape(-1, 3)])
            if len(bad):
                where = nearest_bones(rig, bad)
                counts = {}
                for name in where:
                    counts[name] = counts.get(name, 0) + 1
                top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
                worst = int(np.argmax(ratio))
                summary["spots"].append({"object": obj.name, "near": top, "worst_edge": round(float(ratio[worst]), 2),
                                         "worst_mm": round(float(length1[worst] - length0[worst]) * 1000.0, 1),
                                         "worst_at": [round(float(v), 3) for v in world[edges[worst, 0]]]})
        out["poses"][pose] = summary
        log("pose %-9s edges >1.5x %d, >2.5x %d, squashed triangles %d" % (
            pose, summary["stretched"], summary["torn"], summary["squashed"]))
        for spot in summary["spots"]:
            log("     %-14s worst edge %.2fx (+%.0f mm at %s), near %s" % (
                spot["object"], spot["worst_edge"], spot["worst_mm"], spot["worst_at"], spot["near"]))
    check.apply_pose(bpy.context, rig, 'REST')


def flipped(name):
    if name.startswith("Left"):
        return "Right" + name[4:]
    if name.startswith("Right"):
        return "Left" + name[5:]
    return name


def symmetry(rig, parts, height):
    from dasktoon_rig import parts as rig_parts, weights
    middle = (rig.matrix_world @ rig.data.bones["Hips"].head_local).x
    names = [b.name for b in rig.data.bones if b.use_deform]
    swap = [names.index(flipped(n)) if flipped(n) in names else i for i, n in enumerate(names)]
    for obj in dict.fromkeys(p.object for p in parts):
        world, _edges = rig_parts.mesh_arrays(obj)
        mirrored = world.copy()
        mirrored[:, 0] = 2.0 * middle - mirrored[:, 0]
        tree = KDTree(len(world))
        for i, co in enumerate(world):
            tree.insert(co, i)
        tree.balance()
        pairs = []
        for i, co in enumerate(mirrored):
            _found, j, distance = tree.find(co)
            if distance < 0.002 * height:
                pairs.append((i, j))
        share = len(pairs) / max(len(world), 1)
        if share < 0.5:
            log("symmetry %-14s not its own mirror image (%.0f%% of vertices)" % (obj.name, 100.0 * share))
            continue
        matrix = weights.read(obj, names)
        a = np.array([i for i, _j in pairs])
        b = np.array([j for _i, j in pairs])
        difference = np.abs(matrix[a] - matrix[b][:, swap]).max(axis=1)
        result = {"pairs": len(pairs), "mean": round(float(difference.mean()), 4),
                  "over_0.1": round(float((difference > 0.1).mean()), 4), "max": round(float(difference.max()), 3)}
        out["symmetry"][obj.name] = result
        log("symmetry %-14s %d pairs: mean difference %.3f, %.1f%% over 0.1, max %.2f" % (
            obj.name, len(pairs), result["mean"], 100.0 * result["over_0.1"], result["max"]))


def leaks(rig, parts, height):
    from dasktoon_rig import chains, parts as rig_parts, regions, weights
    bones = regions.region_bones(rig)
    for obj in dict.fromkeys(p.object for p in parts):
        world, _edges = rig_parts.mesh_arrays(obj)
        for region in regions.LIMBS:
            names = bones[region]
            if not names:
                continue
            w = weights.read(obj, names).sum(axis=1)
            near = np.min(np.stack([chains.segment_distance(world, *rig_parts.bone_segment(rig, n)) for n in names],
                                   axis=1), axis=1)
            bad = (w > 0.05) & (near > FAR * height)
            if bad.any():
                out["leaks"].setdefault(obj.name, {})[region] = {"vertices": int(bad.sum()),
                                                                 "max": round(float(w[bad].max()), 3)}
                log("leak %-14s %-6s %d vertices, up to %.2f" % (obj.name, region, int(bad.sum()), float(w[bad].max())))


def main():
    rig, parts = rig_and_parts()
    from dasktoon_rig import skeleton
    box = skeleton.bounds([p.object for p in parts])
    height = float(box[1].z - box[0].z)
    log("file", bpy.data.filepath, "height %.3f" % height)
    joints(rig, parts, height)
    poses(rig, parts, height)
    symmetry(rig, parts, height)
    leaks(rig, parts, height)
    if ARGS:
        with open(ARGS[0], "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)


main()
