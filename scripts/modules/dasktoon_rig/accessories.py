# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Accessories: what a character wears or carries that does not bend with the skin under it (a bow, a bag, a brow, the
crystals round a cloak). They are parts with the role Accessory, listed in a group of their own, each piece rigid on one
bone (docs/superpowers/specs/2026-10-30-dasktoon-accessories-design.md).

find_far, before the skeleton is fitted: the pieces of Clothing floating off the skin and reaching far out of it, seen
from above, without going round the body. Read as part of the body's shape they would become its arms (Evita: her
shoulders came out level with her eyes). Skin is modelled where it shows, so being far from it says nothing by itself:
shoes and socks lie under the legs, and a sleeve touches its hand; both are the shape of the body.

find, with the skeleton fitted: Clothing and small Body meshes lying wholly on the head go with the head (Encore's
brows, lashes, mouth, blush: a mesh each); and the pieces of Clothing standing off the surfaces round them, small and
going round no bone. What a mesh keeps of its Clothing stays; the rest makes a part of its own on a vertex group, or the
whole part an Accessory when nothing stays.

Without a bone chosen, each group of touching pieces follows the bone it sits on (bone_for)."""

import math

import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from . import chains, parts as rig_parts, regions

FAR_REACH = 0.12  # (x height) a piece reaching this far out of the skin, seen from above, is off the body ...
ROUND_THE_BODY = 1.5 * math.pi  # ... unless it goes this far round it (a wide skirt)
TOUCHES = 0.01  # (x height) ... or lies this near the skin somewhere (a sleeve at its hand, a cloak at its neck)
COMPACT = 0.22  # (x height) a piece no longer than this may be an accessory
STANDS_OFF = 0.012  # (x height) ... when half its vertices are this far from the surfaces round it
ROUND_A_BONE = 1.3 * math.pi  # ... and it does not go this far round its nearest bone (a cuff, a belt)
FEWEST = 4  # vertices of a piece
HEAD_MARGIN = 0.01  # (x height) how far below the head joint a mesh on the head may reach
ON_A_LIMB = 0.02  # (x height) an accessory this near the surface of a limb follows the limb
TOUCHING = 0.005  # (x height) pieces this near are one accessory
GROUP = "DT_Accessories"
LIMBS = ('ARM_L', 'ARM_R', 'LEG_L', 'LEG_R')


def part_name(obj):
    """The name of the part holding the accessories of a mesh."""
    return "%s Accessories" % obj.name


def masks(parts):
    """{object: vertex mask} of the vertices of the Accessory `parts`."""
    out = {}
    for part in parts:
        if part.role != 'ACCESSORY' or part.object is None or part.object.type != 'MESH':
            continue
        try:
            vertices = rig_parts.part_vertices(part)
        except rig_parts.PartError:
            continue
        out.setdefault(part.object, np.zeros(len(part.object.data.vertices), bool))[vertices] = True
    return out


def _whole_parts(rig, roles):
    return [part for part in rig.data.dasktoon_rig.parts
            if part.role in roles and part.scope == 'OBJECT' and part.object is not None
            and part.object.type == 'MESH' and len(part.object.data.vertices)]


def _triangles(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    return corners.reshape(-1, 3).astype(np.int64)


def _surface(sources):
    """A BVH tree of the triangles of `sources` [(object, vertex mask or None)], or None without any."""
    verts, tris, offset = [], [], 0
    for obj, mask in sources:
        world, _edges = rig_parts.mesh_arrays(obj)
        corners = _triangles(obj)
        if mask is not None:
            corners = corners[mask[corners].all(axis=1)]
        verts.append(world)
        tris.append(corners + offset)
        offset += len(world)
    if not tris or not sum(len(t) for t in tris):
        return None
    return BVHTree.FromPolygons(np.concatenate(verts).tolist(), np.concatenate(tris).tolist(), all_triangles=True)


def _distances(tree, points):
    """Distance of each of `points` to the surface of `tree`."""
    out = np.full(len(points), np.inf)
    for i, point in enumerate(points.tolist()):
        location = tree.find_nearest(point)[0]
        if location is not None:
            out[i] = (location - type(location)(point)).length
    return out


def _from_above(points):
    """A tree of `points` flattened onto the floor."""
    tree = KDTree(len(points))
    for i, (x, y) in enumerate(points[:, :2].tolist()):
        tree.insert((x, y, 0.0), i)
    tree.balance()
    return tree


def _beyond(tree, points):
    """How far `points` reach out of those of `tree`, seen from above."""
    return max(tree.find((x, y, 0.0))[2] for x, y in points[:, :2].tolist())


def _turned(angles):
    """How far (radians) `angles` go round: a full turn but for their widest gap."""
    angles = np.sort(angles)
    return 2.0 * math.pi - float(np.diff(np.append(angles, angles[0] + 2.0 * math.pi)).max())


def _sample(points, count=64):
    return points[::max(1, len(points) // count)]


def _mark(rig, part, count, found):
    """The pieces `found` of the whole-object `part`, of `count` it has, become Accessories. `part` itself when they are
    all of it; otherwise a part of its own, on a vertex group. Whatever you chose for that part stays."""
    from bl_ui.dasktoon_rig import add_part
    obj = part.object
    data = rig.data.dasktoon_rig
    name = part_name(obj)
    if not found:
        return None
    if len(found) == count:
        part.role = 'ACCESSORY'
        return part.name
    group = obj.vertex_groups.get(GROUP) or obj.vertex_groups.new(name=GROUP)
    group.remove(list(range(len(obj.data.vertices))))
    group.add(np.concatenate(found).tolist(), 1.0, 'REPLACE')
    if not any(p.name == name for p in data.parts):
        add_part(rig, obj, 'ACCESSORY', name=name, scope='VERTEX_GROUP', vertex_group=group.name)
        data.parts[-1].made_by_recognize = True
    return name


def _marked(rig, marks):
    """_mark for each of `marks` (part name, how many pieces it has, the pieces found); the names of the parts holding
    them. Each part is looked up here, one at a time: adding one moves the list in memory, and what was held of it is
    gone."""
    held = [_mark(rig, rig.data.dasktoon_rig.parts[name], count, found) for name, count, found in marks]
    return [name for name in held if name]


def find_far(rig):
    """The pieces of the Clothing parts floating off the Body parts and reaching far out of them without going round the
    body become Accessories (the module's docstring). Returns the names of the parts holding them."""
    bodies = _whole_parts(rig, ('BODY',))
    tree = _surface([(part.object, None) for part in bodies])
    if tree is None:
        return []
    skin = np.concatenate([rig_parts.mesh_arrays(part.object)[0] for part in bodies])
    height = float(np.ptp(skin[:, 2]))
    middle = np.median(skin[:, :2], axis=0)
    above = _from_above(skin)
    marks = []
    for part in _whole_parts(rig, ('CLOTHING',)):
        world, edges = rig_parts.welded_arrays(part.object)
        pieces = rig_parts.pieces(edges, np.arange(len(world)))
        found = []
        for piece in pieces:
            points = world[piece]
            turned = _turned(np.arctan2(points[:, 1] - middle[1], points[:, 0] - middle[0]))
            if turned < ROUND_THE_BODY and _beyond(above, _sample(points)) > FAR_REACH * height \
                    and _distances(tree, points).min() > TOUCHES * height:
                found.append(piece)
        marks.append((part.name, len(pieces), found))
    return _marked(rig, marks)


def _on_head(rig, world, height):
    return float(world[:, 2].min()) >= rig_parts.bone_segment(rig, "Head")[0][2] - HEAD_MARGIN * height


def _round_a_bone(rig, points, names):
    """True when `points` go round the bone of `names` nearest their middle."""
    middle = points.mean(axis=0)
    name = rig_parts.nearest_bone(rig, middle, names)
    head, tail = rig_parts.bone_segment(rig, name)
    axis = (tail - head) / max(float(np.linalg.norm(tail - head)), 1e-9)
    side = np.cross(axis, (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0))
    side /= np.linalg.norm(side)
    other = np.cross(axis, side)
    away = points - head
    return _turned(np.arctan2(away @ other, away @ side)) >= ROUND_A_BONE


def find(context, rig):
    """Meshes on the head and pieces standing off the body become Accessories (the module's docstring). Returns the names
    of the parts holding them."""
    height = rig_parts.rig_height(rig)
    out = []
    for part in _whole_parts(rig, ('BODY', 'CLOTHING')):
        world, _edges = rig_parts.mesh_arrays(part.object)
        if _on_head(rig, world, height) and (part.role == 'CLOTHING'
                                             or rig_parts.on_head_in_small_pieces(rig, part.object)):
            part.role, part.bone = 'ACCESSORY', "Head"
            out.append(part.name)
    bones = [name for names in regions.region_bones(rig).values() for name in names if rig.data.bones.get(name)]
    clothing = _whole_parts(rig, ('CLOTHING',))
    sources = [(part.object, None) for part in _whole_parts(rig, ('BODY',))]
    whole = {}
    for part in clothing:
        world, edges = rig_parts.welded_arrays(part.object)
        pieces = rig_parts.pieces(edges, np.arange(len(world)))
        compact = [len(p) >= FEWEST and float(np.ptp(world[p], axis=0).max()) <= COMPACT * height for p in pieces]
        whole[part] = (world, pieces, compact)
        big = np.zeros(len(world), bool)
        for piece, small in zip(pieces, compact):
            big[piece] = not small
        if big.any():
            sources.append((part.object, big))
    tree = _surface(sources)
    if tree is None:
        return out
    marks = []
    for part in clothing:
        world, pieces, compact = whole[part]
        found = [piece for piece, small in zip(pieces, compact)
                 if small and float(np.median(_distances(tree, _sample(world[piece])))) > STANDS_OFF * height
                 and not _round_a_bone(rig, world[piece], bones)]
        marks.append((part.name, len(pieces), found))
    return out + _marked(rig, marks)


def groups(world, edges, vertices, height):
    """Vertex arrays of the accessories among `vertices`: the loose pieces, those touching taken together."""
    pieces = rig_parts.pieces(edges, vertices)
    return regions._groups(pieces, world, TOUCHING * height) if pieces else []


def bone_for(rig, points, half, height, bones):
    """The bone an accessory at `points` follows: of the limb on whose surface it sits (not a finger: a ring is rigid on
    the hand), the Head when it sits on the head, else the nearest of the trunk and shoulders (a crystal floating by the
    shoulder does not swing with the arm). `half`: the half widths of regions.half_widths; `bones`: those it may use."""
    middle = points.mean(axis=0)[None, :]
    reach = ON_A_LIMB * height
    region_bones = regions.region_bones(rig)
    best, best_distance = None, reach
    for region in LIMBS:
        names = [n for n in region_bones[region] if n in bones and n in half and not n.endswith(regions.SEGMENTS)]
        for name in names:
            distance = float(chains.segment_distance(middle, *rig_parts.bone_segment(rig, name))[0]) - half[name]
            if distance < best_distance:
                best, best_distance = name, distance
    if best is not None:
        return best
    if "Head" in bones and "Head" in half and float(regions.head_distance(rig, middle, half)[0]) <= reach:
        return "Head"
    trunk = [name for name in regions.TRUNK + ("Head", "LeftShoulder", "RightShoulder") if name in bones]
    return rig_parts.nearest_bone(rig, middle[0], trunk or bones)
