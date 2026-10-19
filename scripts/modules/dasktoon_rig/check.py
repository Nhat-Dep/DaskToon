# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Check of the one-button auto rig (docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md): test poses
someone new to rigging can try with one button, the mesh moved through its weights as the Armature modifier moves it,
and the spots worth a look: joints outside the body, stretched spots, roles that look wrong."""

import math

import numpy as np
from mathutils import Matrix

from . import chains, parts as rig_parts, regions, skeleton, weights

POSES = ('ARMS_UP', 'SIT', 'TURN_HEAD', 'WAVE', 'REST')
TRIED = ('ARMS_UP', 'SIT', 'TURN_HEAD', 'WAVE')  # the poses the Check tries
# The joints checked for being inside the body (spec 4.1): the head of each bone.
JOINTS = ("LeftUpperArm", "RightUpperArm", "LeftLowerArm", "RightLowerArm", "LeftHand", "RightHand", "LeftUpperLeg",
          "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot", "Neck", "Head")
INSIDE_HITS = 4  # of the six rays from a joint, at least this many hit the body when it is inside (open sleeves, collars)
STRETCH = 2.5  # an edge this many times longer in a test pose is stretched
SPOT_EDGES = 3  # a stretched spot has at least this many edges
SPOT_SAME = 0.5  # a spot mostly made of an earlier spot's vertices is that spot again, in another pose
SPOT_GAP = 0.05  # (x height) stretched bits this near each other are one spot (one tear can split a ring in two)
FAR_BONES = 4  # a stretch between bones this many steps apart in the skeleton is not a joint bending (an ear on an arm)
WIDE = 0.02  # (x height) an edge growing this much is torn even between bones next to each other (a joint bending
# stretches the skin of tdt and lr_shape 2 cm at most; the hips they tore when sitting grew 11 to 16 cm)
FOLLOWS = 0.2  # a vertex follows the bones with at least this weight
SKIRT_SHARE = 0.8  # of a skirt's vertices, at least this share between the knees and the waist
SKIRT_FLARE = 1.1  # a skirt is this much wider at its hem than at its top
BAND = 0.05  # (x height) the height of the bands looked at
MARGIN = 0.01  # (x height) how far past a point a vertex is on that side of it
HEM_RING = 0.5  # a skirt's hem is a ring round the hips: its nearest point is at least this share of its mean radius
# (bone, world axis, degrees): each bone turned about its head, in order, from the rest pose (spec §3). The character
# faces -Y with its left at +X: about +Y a positive angle lifts the right arm, about X a negative one swings a thigh
# forward, about Z a positive one turns the face to the character's left.
TURNS = {
    'ARMS_UP': (("LeftUpperArm", 'Y', -110.0), ("RightUpperArm", 'Y', 110.0)),
    'SIT': (("LeftUpperLeg", 'X', -90.0), ("RightUpperLeg", 'X', -90.0),
            ("LeftLowerLeg", 'X', 90.0), ("RightLowerLeg", 'X', 90.0)),
    'TURN_HEAD': (("Head", 'Z', 45.0),),
    'WAVE': (("RightUpperArm", 'Y', 100.0), ("RightLowerArm", 'Y', 30.0)),
}


def apply_pose(context, rig, pose):
    """Put `rig` in a test pose: every bone back at rest, then the pose's turns. Nothing is keyed; on the next frame
    change the animation of the rig shows again. REST leaves every bone at rest."""
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    context.view_layer.update()
    to_rig = rig.matrix_world.inverted()
    for name, axis, degrees in TURNS.get(pose, ()):
        bone = rig.pose.bones.get(name)
        if bone is None:
            continue
        world = rig.matrix_world @ bone.matrix
        pivot = world.translation.copy()
        turn = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-pivot)
        bone.matrix = to_rig @ turn @ world
        context.view_layer.update()


def deformed(rig, obj):
    """World positions of the vertices of obj's mesh (no shape keys or modifiers) moved by the rig's current pose through
    their weights, blended as the Armature modifier blends them; a vertex without weight stays."""
    world, _edges = rig_parts.mesh_arrays(obj)
    names = [bone.name for bone in rig.data.bones if bone.use_deform]
    matrix = weights.read(obj, names)
    total = matrix.sum(axis=1)
    moved = np.zeros_like(world)
    to_rig = rig.matrix_world.inverted()
    for j, name in enumerate(names):
        share = matrix[:, j]
        if not share.any():
            continue
        bone = rig.pose.bones[name]
        move = np.array(rig.matrix_world @ bone.matrix @ rig.data.bones[name].matrix_local.inverted() @ to_rig)
        moved += share[:, None] * (world @ move[:3, :3].T + move[:3, 3])
    out = world.copy()
    have = total > 0.0
    out[have] = moved[have] / total[have, None]
    return out


def _mirror_copies(obj):
    """World-to-world matrices of the halves the Mirror modifiers of obj make across X (a mesh modelled in half)."""
    from mathutils import Matrix, Vector
    out = []
    for modifier in obj.modifiers:
        if modifier.type == 'MIRROR' and modifier.use_axis[0] and modifier.show_viewport:
            frame = (modifier.mirror_object or obj).matrix_world
            out.append(np.array(frame @ Matrix.Scale(-1.0, 4, Vector((1.0, 0.0, 0.0))) @ frame.inverted()))
    return out


def _body_tree(parts):
    """BVH tree of the meshes of the Body and Clothing parts at rest (world), with the halves their Mirror modifiers
    make, or None."""
    from mathutils.bvhtree import BVHTree
    verts, tris = [], []
    for obj in dict.fromkeys(part.object for part in parts if part.object is not None and part.object.type == 'MESH'
                             and part.role in regions.BODY_ROLES):
        world, _edges = rig_parts.mesh_arrays(obj)
        mesh = obj.data
        mesh.calc_loop_triangles()
        corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
        mesh.loop_triangles.foreach_get("vertices", corners)
        corners = corners.reshape(-1, 3)
        for copy, order in [(world, corners)] + [(world @ m[:3, :3].T + m[:3, 3], corners[:, ::-1])
                                                 for m in _mirror_copies(obj)]:
            tris.append(order + sum(len(v) for v in verts))
            verts.append(copy)
    if not verts or not sum(len(t) for t in tris):
        return None
    return BVHTree.FromPolygons(np.concatenate(verts).tolist(), np.concatenate(tris).tolist(), all_triangles=True)


def joint_issues(rig, parts):
    """The bones of JOINTS whose head is outside the body at rest (spec 4.1): fewer than INSIDE_HITS of the six rays from
    it hit the Body and Clothing meshes."""
    from mathutils import Vector
    tree = _body_tree(parts)
    if tree is None:
        return []
    directions = [Vector(d) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    out = []
    for name in JOINTS:
        bone = rig.data.bones.get(name)
        if bone is None:
            continue
        joint = rig.matrix_world @ bone.head_local
        hits = sum(tree.ray_cast(joint, direction)[0] is not None for direction in directions)
        if hits < INSIDE_HITS:
            out.append(name)
    return out


def _height(parts):
    box = skeleton.bounds([part.object for part in parts if part.object is not None])
    return float(box[1].z - box[0].z) if box is not None else 1.0


def _steps(rig):
    """{(bone, bone): steps between them in the skeleton} for the deform bones."""
    names = [bone.name for bone in rig.data.bones if bone.use_deform]
    chain = {}
    for name in names:
        up, bone = [], rig.data.bones[name]
        while bone is not None:
            up.append(bone.name)
            bone = bone.parent
        chain[name] = up
    out = {}
    for a in names:
        for b in names:
            common = next((i for i, bone in enumerate(chain[a]) if bone in chain[b]), None)
            out[a, b] = len(chain[a]) + len(chain[b]) if common is None else common + chain[b].index(chain[a][common])
    return names, out


def _far_apart(edges, follows, names, steps):
    """For each edge, whether its two vertices follow bones FAR_BONES or more steps apart in the skeleton (a joint bending
    stretches its skin between bones next to each other: the chest and the upper arm; an ear half on the head and half
    on the arm is torn between bones far apart). `follows`: the bones (indices in `names`) each vertex follows."""
    far = np.zeros(len(edges), bool)
    for k, (a, b) in enumerate(edges.tolist()):
        bones = set(follows[a]) | set(follows[b])
        far[k] = any(steps[names[i], names[j]] >= FAR_BONES for i in bones for j in bones)
    return far


def stretch_issues(context, rig, parts, half=None):
    """[(object, pose, region, vertex indices)] of the stretched spots (spec 4.2): in each pose of TRIED, the edges of the
    parts' meshes moved through their weights that grow more than STRETCH times between bones far apart in the skeleton
    (not a joint bending), or by more than WIDE of the height, in spots of at least SPOT_EDGES edges; each spot once, in
    the first pose that stretches it, named after the region nearest its middle. The rig is left at rest."""
    objects = list(dict.fromkeys(part.object for part in parts
                                 if part.object is not None and part.object.type == 'MESH'))
    rest = {}
    for obj in objects:
        world, edges = rig_parts.mesh_arrays(obj)
        rest[obj] = (world, edges, np.linalg.norm(world[edges[:, 0]] - world[edges[:, 1]], axis=1))
    names, steps = _steps(rig)
    follows = {}
    height = _height(parts)
    gap = SPOT_GAP * height
    found = []
    try:
        for pose in TRIED:
            apply_pose(context, rig, pose)
            for obj in objects:
                world, edges, length = rest[obj]
                if len(edges) == 0:
                    continue
                moved = deformed(rig, obj)
                now = np.linalg.norm(moved[edges[:, 0]] - moved[edges[:, 1]], axis=1)
                stretched = now > STRETCH * np.maximum(length, 1e-9)
                wide = now - length > WIDE * height
                if stretched.sum() < SPOT_EDGES:
                    continue
                if obj not in follows:
                    follows[obj] = [np.nonzero(row >= FOLLOWS)[0].tolist() for row in weights.read(obj, names)]
                stretched[stretched] = wide[stretched] | _far_apart(edges[stretched], follows[obj], names, steps)
                if stretched.sum() < SPOT_EDGES:
                    continue
                bad = edges[stretched]
                vertices = np.unique(bad)
                local = rig_parts.local_edges(bad, vertices)
                bits = [vertices[component] for component in chains.components(len(vertices), local)]
                for spot in regions._groups(bits, world, gap):
                    if np.isin(bad, spot).all(axis=1).sum() < SPOT_EDGES:
                        continue
                    if any(other is obj and np.isin(spot, seen).mean() >= SPOT_SAME for other, _p, _r, seen in found):
                        continue
                    region = 'TORSO'
                    if half:
                        middle = world[spot].mean(axis=0)[None, :]
                        region = regions.REGIONS[int(regions.labels(rig, middle, half)[0])]
                    found.append((obj, pose, region, spot))
    finally:
        apply_pose(context, rig, 'REST')
    return found


def _surrounds(points, centre, margin):
    """True when `points` (n x 3) lie on all four sides (left, right, front, back) of `centre`."""
    if not len(points):
        return False
    x, y = points[:, 0] - centre[0], points[:, 1] - centre[1]
    return bool((x < -margin).any() and (x > margin).any() and (y < -margin).any() and (y > margin).any())


def _looks_like_hair(world, neck, hip, height):
    z = world[:, 2]
    if not (z.max() > neck[2] and z.min() < neck[2] and z.min() > hip[2]):
        return False  # hair reaches above the head joint and hangs below it, not down to the legs
    return not _surrounds(world[np.abs(z - neck[2]) < BAND * height], neck, MARGIN * height)


def _looks_like_skirt(world, hip, knee_z, waist_z, height):
    z = world[:, 2]
    if np.mean((z >= knee_z) & (z <= waist_z)) < SKIRT_SHARE:
        return False
    low, high = z.min(), z.max()
    middle = (low + high) / 2.0
    if not _surrounds(world[np.abs(z - middle) < BAND * height], hip, MARGIN * height):
        return False
    hem = world[z < low + 0.2 * (high - low)]
    top = world[z > high - 0.2 * (high - low)]
    hem_radius = np.hypot(hem[:, 0] - hip[0], hem[:, 1] - hip[1])
    if hem_radius.min() < HEM_RING * hem_radius.mean():
        return False  # two legs (the inside of each leg comes near the middle), not one skirt round them
    top_radius = np.hypot(top[:, 0] - hip[0], top[:, 1] - hip[1])
    return float(hem_radius.mean()) > SKIRT_FLARE * float(top_radius.mean())


def role_issues(rig, parts):
    """[(part name, role)] of the whole-object Clothing parts that look like hair or a skirt (spec 4.3)."""
    neck = rig_parts.bone_segment(rig, "Head")[0]
    hip = rig_parts.bone_segment(rig, "Hips")[0]
    waist_z = float(rig_parts.bone_segment(rig, "Spine")[0][2])
    knee_z = float(np.mean([rig_parts.bone_segment(rig, side + "LowerLeg")[0][2] for side in ("Left", "Right")]))
    height = _height(parts)
    out = []
    for part in parts:
        obj = part.object
        if part.role != 'CLOTHING' or part.scope != 'OBJECT' or obj is None or obj.type != 'MESH':
            continue
        world, _edges = rig_parts.mesh_arrays(obj)
        if not len(world):
            continue
        if _looks_like_hair(world, neck, hip, height):
            out.append((part.name, 'HAIR'))
        elif _looks_like_skirt(world, hip, knee_z, waist_z, height):
            out.append((part.name, 'SKIRT'))
    return out


def run(context, rig):
    """Look for the spots worth a look (spec 4) and keep them on the rig (rig.data.dasktoon_rig.issues); the rig is left
    at rest. Returns how many were found."""
    from . import facing
    data = rig.data.dasktoon_rig
    parts = [part for part in data.parts if part.object is not None]
    found = regions.analyse(context, rig, parts)
    data.issues.clear()
    meshes = [part.object for part in parts if part.object.type == 'MESH']
    body = [part.object for part in parts if part.object.type == 'MESH' and part.role in regions.BODY_ROLES]
    if facing.sideways(context, list(dict.fromkeys(body or meshes))):
        data.issues.add().kind = 'FACING'  # first: everything else follows from the way it faces
    for name in joint_issues(rig, parts):
        item = data.issues.add()
        item.kind, item.bone = 'JOINT', name
    owner = {part.object: part.name for part in reversed(parts)}
    for obj, pose, region, spot in stretch_issues(context, rig, parts, found.half):
        item = data.issues.add()
        item.kind, item.object, item.part, item.pose, item.region = 'STRETCH', obj, owner.get(obj, ""), pose, region
        item["vertices"] = [int(v) for v in spot]
    for name, role in role_issues(rig, parts):
        item = data.issues.add()
        item.kind, item.part, item.role = 'ROLE', name, role
    data.checked = True
    return len(data.issues)
