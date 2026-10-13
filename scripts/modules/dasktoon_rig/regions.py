# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Body regions and locks on the head (docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md).

Every vertex of the Body and Clothing parts belongs to one of six regions: the head, the torso, an arm or a leg. A vertex
goes to the region it is nearest, measured from the region's surface: the distance to its bones minus the half width of
the body there, read from the front view. The loose pieces hanging from the head (rabbit ears, hair locks modelled with
the skin) go to the head; grouped into locks, they become parts the user makes rigid on the head or Hair. Build keeps
each arm's and leg's bones to their region, so lifting an arm no longer drags an ear, a lock or a strap along (real
model test: Bone Heat weighs by distance to the bones, and the Head bone of a chibi is a thin line in a wide head)."""

from contextlib import contextmanager

import numpy as np

from . import body_shape, chains, parts as rig_parts, skeleton

REGIONS = ('HEAD', 'TORSO', 'ARM_L', 'ARM_R', 'LEG_L', 'LEG_R')
LIMBS = ('ARM_L', 'ARM_R', 'LEG_L', 'LEG_R')
COLORS = {  # sRGB, as painted
    'HEAD': (1.0, 0.85, 0.2), 'TORSO': (0.25, 0.55, 1.0), 'ARM_L': (1.0, 0.3, 0.25), 'ARM_R': (1.0, 0.6, 0.15),
    'LEG_L': (0.3, 0.85, 0.35), 'LEG_R': (0.7, 0.4, 0.95)}
LAYER = "DaskToon Region"
AUTO = -1
TRUNK = ("Hips", "Spine", "Chest", "UpperChest", "Neck")
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
SEGMENTS = ("Proximal", "Intermediate", "Distal")
ROOTS = {'ARM_L': "LeftUpperArm", 'ARM_R': "RightUpperArm", 'LEG_L': "LeftUpperLeg", 'LEG_R': "RightUpperLeg"}
FALLBACK = {'ARM': 0.03, 'LEG': 0.05, 'TRUNK': 0.1}  # half widths (x height) when the front view tells nothing
NECK_BAND = 0.05  # (x height) a piece surrounding the neck this near the neck joint's height is skin, not a lock
SIDE_MARGIN = 0.01  # (x height) how far past the neck joint a vertex is on that side of it
LOCK_GAP = 0.005  # (x height) pieces this near are one lock
MIDDLE_LOCK = 0.02  # (x height) a lock whose middle is this near the body's middle is on neither side
BODY_ROLES = ('BODY', 'CLOTHING')


def _side(region):
    return "Left" if region.endswith("_L") else "Right"


def region_bones(rig):
    """{region: [bone names]} of the bones measuring each region (those the rig has)."""
    out = {'HEAD': ["Head"], 'TORSO': list(TRUNK)}
    for region in LIMBS:
        side = _side(region)
        if region.startswith("ARM"):
            out[region] = [side + n for n in ("UpperArm", "LowerArm", "Hand")] + [
                side + finger + segment for finger in FINGERS for segment in SEGMENTS]
        else:
            out[region] = [side + n for n in ("UpperLeg", "LowerLeg", "Foot", "Toes")]
    bones = rig.data.bones
    return {region: [name for name in names if bones.get(name) is not None] for region, names in out.items()}


@contextmanager
def resting(context, rig):
    """`rig` in its rest pose meanwhile."""
    data = rig.data
    previous = data.pose_position
    if previous != 'REST':
        data.pose_position = 'REST'
        context.view_layer.update()
    try:
        yield
    finally:
        if previous != 'REST':
            data.pose_position = previous
            context.view_layer.update()


def _run_half(shape, x, z):
    """Half the width of the front view's run through (x, z); 0 when that pixel is empty."""
    row, col = shape.pixel((x, z))
    line = shape.mask[row]
    if not line[col]:
        return 0.0
    empty = np.nonzero(~line)[0]
    left, right = empty[empty < col], empty[empty > col]
    start = left[-1] + 1 if len(left) else 0
    end = right[0] - 1 if len(right) else len(line) - 1
    return (end - start + 1) * shape.step / 2.0


def half_widths(context, rig, objects, height, feet):
    """{bone: half the width of the body there} for the bones of region_bones(rig), read from the front view of
    `objects` at rest: a trunk bone from the run through the body's middle at its middle height (UpperChest and Neck no
    wider than the trunk below the arms, where the arms join the run), an arm or leg from the limb found."""
    bones = region_bones(rig)
    middle = float(rig_parts.bone_segment(rig, "Hips")[0][0])
    with resting(context, rig):
        shape = body_shape.Shape(context, objects, feet, height)
    found = {}
    if shape.mask is not None:
        for region in LIMBS:
            side = 1 if region.endswith("_L") else -1
            limb = shape.arm(side, middle) if region.startswith("ARM") else shape.leg(side, middle)
            found[region] = limb.width / 2.0 if limb is not None else None
    out = {}
    for region in LIMBS:  # both sides found: their mean, so the regions mirror like the fitted skeleton
        other = region[:-1] + ("R" if region.endswith("L") else "L")
        sides = [half for half in (found.get(region), found.get(other)) if half is not None]
        half = float(np.mean(sides)) if sides else FALLBACK[region[:3]] * height
        out.update({name: half for name in bones[region]})
    for name in bones['TORSO'] + bones['HEAD']:
        head, tail = rig_parts.bone_segment(rig, name)
        half = _run_half(shape, middle, (head[2] + tail[2]) / 2.0) if shape.mask is not None else 0.0
        out[name] = half if half > 0.0 else FALLBACK['TRUNK'] * height
    below = [out[name] for name in ("Hips", "Spine", "Chest") if name in out]
    for name in ("UpperChest", "Neck"):
        if name in out and below:
            out[name] = min(out[name], max(below))
    return out


def surface_distance(rig, world, names, half):
    """Distance of each world point to the nearest of the bones `names`, minus that bone's half width."""
    if not names:
        return np.full(len(world), np.inf)
    return np.min(np.stack([chains.segment_distance(world, *rig_parts.bone_segment(rig, name)) - half[name]
                            for name in names], axis=1), axis=1)


def labels(rig, world, half, head=None):
    """Region (index in REGIONS) of each world point: the one nearest from its surface; points of the mask `head` are
    HEAD."""
    bones = region_bones(rig)
    distance = np.stack([surface_distance(rig, world, bones[region], half) for region in REGIONS], axis=1)
    out = distance.argmin(axis=1).astype(np.int8)
    if head is not None:
        out[head] = REGIONS.index('HEAD')
    return out


def head_pieces(rig, world, edges, vertices, height):
    """The loose pieces of `vertices` (mesh indices) hanging from the head: their top above the neck joint, their
    bottom above the hip joint, and not surrounding the neck (the skin of the face and neck does)."""
    neck = rig_parts.bone_segment(rig, "Head")[0]
    hip = rig_parts.bone_segment(rig, "Hips")[0]
    band, margin = NECK_BAND * height, SIDE_MARGIN * height
    out = []
    for piece in rig_parts.pieces(edges, vertices):
        z = world[piece, 2]
        if z.max() <= neck[2] or z.min() <= hip[2]:
            continue
        near = world[piece[np.abs(z - neck[2]) < band]]
        if len(near) and ((near[:, 0] < neck[0] - margin).any() and (near[:, 0] > neck[0] + margin).any()
                          and (near[:, 1] < neck[1] - margin).any() and (near[:, 1] > neck[1] + margin).any()):
            continue
        out.append(piece)
    return out


def _groups(pieces, world, gap):
    """Vertex arrays of the groups of `pieces` nearer than `gap` to each other."""
    from mathutils.kdtree import KDTree
    points = np.concatenate([world[piece] for piece in pieces])
    owner = np.concatenate([np.full(len(piece), i) for i, piece in enumerate(pieces)])
    tree = KDTree(len(points))
    for i, co in enumerate(points.tolist()):
        tree.insert(co, i)
    tree.balance()
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, co in enumerate(points.tolist()):
        for _co, j, _distance in tree.find_range(co, gap):
            a, b = find(int(owner[i])), find(int(owner[j]))
            if a != b:
                parent[a] = b
    groups = {}
    for i, piece in enumerate(pieces):
        groups.setdefault(find(i), []).append(piece)
    return [np.unique(np.concatenate(members)) for members in groups.values()]


def _side_of(world, vertices, middle, height):
    dx = float(world[vertices, 0].mean()) - middle
    return "M" if abs(dx) < MIDDLE_LOCK * height else ("L" if dx > 0.0 else "R")


def _named(found):
    """[(name, item)] for [(side, top, item)]: "Lock L1", "Lock L2", ... top first on each side."""
    out = []
    for side in ("L", "R", "M"):
        mine = sorted((item for item in found if item[0] == side), key=lambda item: -item[1])
        out += [("Lock %s%d" % (side, k), item[2]) for k, item in enumerate(mine, 1)]
    return out


def locks(pieces, world, height, middle):
    """[(name, vertex indices)] of the locks of the head `pieces` of one mesh: pieces nearer than LOCK_GAP x height are
    one lock; named "Lock L1", "Lock R2", "Lock M1" by side (the character's left is +X), top first."""
    if not pieces:
        return []
    groups = _groups(pieces, world, LOCK_GAP * height)
    return _named([(_side_of(world, g, middle, height), float(world[g, 2].max()), g) for g in groups])


class Analysis:
    """What recognition found: {object: (Body and Clothing vertex indices, their regions)}, the locks
    [(name, object, vertex indices)], the half widths {bone: width} and the character's height."""

    def __init__(self):
        self.objects = {}
        self.locks = []
        self.half = {}
        self.height = 0.0


def body_vertices(parts, owners):
    """{object: indices of its vertices owned by Body or Clothing parts} for the objects that have some."""
    ids = [i for i, part in enumerate(parts) if part.role in BODY_ROLES]
    out = {}
    for obj, owner in owners.items():
        vertices = np.nonzero(np.isin(owner, ids))[0]
        if len(vertices):
            out[obj] = vertices
    return out


def analyse(context, rig, parts, owners=None):
    """Recognize the regions of the Body and Clothing vertices of the meshes of `parts`, and the locks of their pieces
    hanging from the head (nothing is written)."""
    from . import build
    owners = build.ownership(parts) if owners is None else owners
    found = Analysis()
    vertices_of = body_vertices(parts, owners)
    if not vertices_of:
        return found
    objects = list(vertices_of)
    height, feet = skeleton.placement(objects, rig.matrix_world.translation)
    found.height = height
    found.half = half_widths(context, rig, objects, height, feet)
    middle = float(rig_parts.bone_segment(rig, "Hips")[0][0])
    named = []
    for obj, vertices in vertices_of.items():
        world, edges = rig_parts.mesh_arrays(obj)
        pieces = head_pieces(rig, world, edges, vertices, height)
        head = np.zeros(len(world), bool)
        for piece in pieces:
            head[piece] = True
        found.objects[obj] = (vertices, labels(rig, world[vertices], found.half, head[vertices]))
        if pieces:
            named += [(_side_of(world, g, middle, height), float(world[g, 2].max()), (obj, g))
                      for g in _groups(pieces, world, LOCK_GAP * height)]
    found.locks = [(name, obj, g) for name, (obj, g) in _named(named)]
    return found
