# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Joints of a machine (machine rig spec 3, 4): a joint is a bone whose head is the pivot and whose local X axis is the
axis (hinges turn about it, slides move along it). Its Y axis points at its one child joint, or else at the far end of
its pieces, across the axis, so an IK chain of hinges reaches from pivot to pivot. guess() reads a pivot, an axis and a
kind from where a piece touches its parent."""

import math
from dataclasses import dataclass, field

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Matrix, Vector

from . import EditSession, MachineError, shapes

KINDS = ('HINGE', 'BALL', 'SLIDE', 'FIXED')
LIMIT = "DT Limit"
GAP = 0.05  # (x the child's size) nearer than this to the parent: they touch
TOUCH = 0.02  # (x the child's size) the contact: vertices of the child this near the parent's faces ...
TOUCH_MIN = 1.5  # ... or this many times the nearest distance
THIN = 0.05  # a spread this much smaller than the widest one is flat
ROUND = 0.2  # distances to an axis varying less than this (std / mean) are a cylinder round it
SHORTEST = 0.05  # (x the pieces' size) the shortest bone
SIDES = 6  # a part needs this many vertices to be read as round by its own shape
ORDERS = (3, 4, 5, 6, 8, 10, 12, 16)  # symmetric after a turn of 360 / k degrees, for one of these k: round
SAME = 0.02  # (x the piece's size) turned points this near the piece's own points land on it
SAMPLE = 300  # points tried per turn
THROUGH = 0.1  # (x the child's size) a parent's axis this near the child's middle goes through it


@dataclass
class Joint:
    pivot: np.ndarray
    axis: np.ndarray = field(default_factory=lambda: np.array((0.0, 0.0, 1.0)))
    kind: str = 'BALL'


def _signed(axis):
    axis = np.asarray(axis, dtype=float)
    axis = axis / (np.linalg.norm(axis) or 1.0)
    return axis if axis[np.argmax(np.abs(axis))] >= 0 else -axis


def contact_shape(points, size):
    """(kind, axis, centre) of a contact patch: a line or a cylinder or ring is a hinge about it, a flat patch a hinge
    about its normal, anything else a ball joint at its middle."""
    centre = points.mean(axis=0)
    if len(points) < 3:
        return 'BALL', np.array((0.0, 0.0, 1.0)), centre
    x = points - centre
    values, vectors = np.linalg.eigh(x.T @ x / len(points))
    if values[2] < 1e-12:
        return 'BALL', np.array((0.0, 0.0, 1.0)), centre
    if values[1] < THIN * values[2]:
        return 'HINGE', _signed(vectors[:, 2]), centre
    best = (None, ROUND)
    for k in range(3):
        e = vectors[:, k]
        r = np.linalg.norm(x - np.outer(x @ e, e), axis=1)
        mean = r.mean()
        if mean > 1e-4 * size and r.std() / mean < best[1]:
            best = (e, r.std() / mean)
    if best[0] is not None:
        return 'HINGE', _signed(best[0]), centre
    if values[0] < THIN * values[1]:
        return 'HINGE', _signed(vectors[:, 0]), centre
    return 'BALL', np.array((0.0, 0.0, 1.0)), centre


def _rotation(e, angle):
    """The matrix turning `angle` about the unit axis `e`."""
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = e
    return np.array(((c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s),
                     (y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s),
                     (z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c))))


def round_axis(points, size):
    """The axis a piece turns about by its shape (a drill bit, a hub, a geared wheel, crossed rings), or None: turned
    by 360/k degrees about it, for some k in ORDERS (3 or more), the piece lands on itself, within SAME x its size. A
    box (and a cylinder about a cross axis) only does so after half a turn. Of such axes, the one with the highest k
    wins. The axes tried go through the middle of the points: their principal axes and the world axes (crossed rings
    spread alike every way across theirs, so their principal axes say nothing)."""
    if len(points) < 3:
        return None
    from mathutils.kdtree import KDTree
    centre = points.mean(axis=0)
    x = points - centre
    tree = KDTree(len(x))
    for i, p in enumerate(x):
        tree.insert(p, i)
    tree.balance()
    sample = x[::max(1, len(x) // SAMPLE)]
    _values, vectors = np.linalg.eigh(x.T @ x / len(points))
    best, best_key = None, None
    for e in list(vectors.T) + list(np.eye(3)):
        if np.linalg.norm(x - np.outer(x @ e, e), axis=1).max() < 1e-3 * size:
            continue
        for k in sorted(ORDERS, reverse=True):
            turned = sample @ _rotation(e, 2 * math.pi / k).T
            miss = np.percentile([tree.find(p)[2] for p in turned], 90)
            if miss < SAME * size:
                key = (k, -miss)
                if best_key is None or key > best_key:
                    best, best_key = e, key
                break
    return None if best is None else _signed(best)


def _nearest(tree, points):
    """(distances, nearest surface points) of `points` to a BVH tree."""
    found = [tree.find_nearest(Vector(p)) for p in points]
    dist = np.array([f[3] if f[0] is not None else np.inf for f in found])
    near = np.array([tuple(f[0]) if f[0] is not None else (np.inf,) * 3 for f in found]).reshape(-1, 3)
    return dist, near


def _turning(binding, child, parent, points, dist, size):
    """(axis, a point on it) the child turns about when its contact says nothing: the whole child's when round; else
    the round parent's (or a round parent piece's) when its axis goes through the child's middle (a gimbal over its
    round base); else the axis of
    the child's round piece nearest the parent (a fan's hub among its blades); (None, centre) when nothing is round."""
    turns = round_axis(points, size)
    if turns is not None:
        return turns, points.mean(axis=0)
    centre = points.mean(axis=0)
    bases = [binding.points(parent)] + sorted((binding.points([p]) for p in parent),
                                              key=lambda q: np.linalg.norm(q.mean(axis=0) - centre) if len(q) else 0)
    for base in bases if len(parent) > 1 else bases[:1]:
        if len(base) < SIDES:
            continue
        axis = round_axis(base, float(np.linalg.norm(base.max(axis=0) - base.min(axis=0))) or size)
        if axis is not None:
            middle = base.mean(axis=0)
            off = centre - middle
            if np.linalg.norm(off - (off @ axis) * axis) <= THROUGH * size:
                return axis, middle
    counts = [len(binding.verts(p)) for p in child]
    starts = np.cumsum([0] + counts)
    order = sorted(range(len(child)), key=lambda k: dist[starts[k]:starts[k + 1]].min() if counts[k] else np.inf)
    for k in order:
        own = points[starts[k]:starts[k + 1]]
        if len(own) < SIDES:
            continue
        turns = round_axis(own, float(np.linalg.norm(own.max(axis=0) - own.min(axis=0))) or size)
        if turns is not None:
            return turns, own.mean(axis=0)
    return None, points.mean(axis=0)


def _on_axis(centre, axis, point):
    return centre + ((point - centre) @ axis) * axis


def guess(binding, child, parent):
    """The Joint of the pieces `child` on the pieces `parent` (world space). Without a parent: a ball joint in the
    middle of the child.

    The contact is measured both ways: the child's vertices on the parent's faces and the parent's vertices on the
    child's faces (a lamp wider than its mast touches it only with the mast's corners). When the contact reads as no
    axis (a gap, a blob), a child round about an axis of its own turns about it."""
    points = binding.points(child)
    if not len(points):
        raise MachineError(rpt_("The piece has no vertices"))
    lo, hi = points.min(axis=0), points.max(axis=0)
    size = float(np.linalg.norm(hi - lo)) or 1e-3
    tree = binding.surface(parent) if parent else None
    if tree is None:
        return Joint((lo + hi) / 2)
    dist, near = _nearest(tree, points)
    others = binding.points(parent)
    reach = GAP * size
    others = others[np.all((others >= lo - reach) & (others <= hi + reach), axis=1)]
    child_tree = binding.surface(child) if len(others) else None
    if child_tree is not None:
        back, back_near = _nearest(child_tree, others)
    else:
        back, back_near = np.zeros(0), np.zeros((0, 3))
    i, j = int(np.argmin(dist)), int(np.argmin(back)) if len(back) else -1
    nearest = dist[i] if j < 0 or dist[i] <= back[j] else back[j]
    pair = (points[i], near[i]) if j < 0 or dist[i] <= back[j] else (others[j], back_near[j])
    turns, centre = _turning(binding, child, parent, points, dist, size)
    if nearest > GAP * size:
        middle = (pair[0] + pair[1]) / 2
        if turns is not None:
            return Joint(_on_axis(centre, turns, middle), turns, 'HINGE')
        return Joint(middle)
    d = max(TOUCH * size, TOUCH_MIN * nearest) + 1e-9
    touching = np.concatenate([points[dist <= d], others[back <= d]])
    kind, axis, middle = contact_shape(touching, size)
    if kind == 'BALL' and turns is not None:
        return Joint(_on_axis(centre, turns, middle), turns, 'HINGE')
    return Joint(middle, axis, kind)


# Bones


def _arm_space(rig, points):
    m = np.array(rig.matrix_world.inverted())
    return np.asarray(points) @ m[:3, :3].T + m[:3, 3]


def _unique_name(rig, base):
    names = {b.name for b in rig.data.bones}
    if base not in names:
        return base
    k = 1
    while "%s.%03d" % (base, k) in names:
        k += 1
    return "%s.%03d" % (base, k)


def name_for(binding, pieces):
    obj = binding.whole_object(pieces)
    if obj is not None:
        return obj.name
    counts = {}
    for o, indices in binding.faces(pieces).items():
        if not len(indices):
            continue
        mats = np.empty(len(o.data.polygons), dtype=np.int64)
        o.data.polygons.foreach_get("material_index", mats)
        for m, c in zip(*np.unique(mats[indices], return_counts=True)):
            slot = o.material_slots[int(m)] if int(m) < len(o.material_slots) else None
            if slot is not None and slot.material is not None:
                counts[slot.material.name] = counts.get(slot.material.name, 0) + int(c)
    return max(counts, key=counts.get) if counts else "Part"


def _direction(head, axis, target, points):
    """(unit Y, length): from `head` towards `target` across `axis`, else towards the farthest of `points`."""
    def across(v):
        return v - (v @ axis) * axis

    size = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0))) if len(points) else 0.0
    shortest = max(SHORTEST * size, 0.01)
    if target is not None:
        y = across(np.asarray(target) - head)
        if np.linalg.norm(y) > 1e-5:
            return y / np.linalg.norm(y), max(float(np.linalg.norm(y)), 1e-3)
    if len(points):
        d = np.array([across(p - head) for p in points])
        lengths = np.linalg.norm(d, axis=1)
        k = int(np.argmax(lengths))
        if lengths[k] > 1e-5:
            return d[k] / lengths[k], max(float(lengths[k]), shortest)
    for v in (np.array((0.0, 0.0, 1.0)), np.array((0.0, 1.0, 0.0))):
        y = across(v)
        if np.linalg.norm(y) > 1e-3:
            return y / np.linalg.norm(y), shortest
    return np.array((1.0, 0.0, 0.0)), shortest


def _place(eb, head, axis, y, length):
    axis = np.asarray(axis, dtype=float)
    eb.head = Vector(head)
    eb.tail = Vector(head + y * length)
    eb.align_roll(Vector(np.cross(axis, y)))


def _orient(rig, edit_bones, binding, name, aims):
    """Point the Y axis of bone `name` (Edit Mode) at its one child, its aim point or the far end of its pieces."""
    eb = edit_bones[name]
    head = np.array(eb.head)
    axis = np.array(eb.x_axis)
    target = aims.get(name)
    if target is None and len(eb.children) == 1:
        target = np.array(eb.children[0].head)
    points = _arm_space(rig, binding.points(binding.pieces_of(name)))
    y, length = _direction(head, axis, target, points)
    _place(eb, head, axis, y, length)


def _aims(rig):
    return {b.name: np.array(b.dasktoon_joint.aim_point) for b in rig.data.bones if b.dasktoon_joint.aim}


def reorient(context, binding, names):
    rig = binding.rig
    aims = _aims(rig)
    root = binding.root
    with EditSession(context, rig) as edit_bones:
        for name in names:
            if name in edit_bones and name != root:
                _orient(rig, edit_bones, binding, name, aims)


def add(context, binding, child, parent, joint, name=None):
    """A new joint holding the pieces `child`, under the bone `parent` (the root when None). Returns its name."""
    rig = binding.rig
    parent = parent or binding.root
    if parent not in rig.data.bones:
        raise MachineError(rpt_("No joint named %s") % parent)
    name = _unique_name(rig, name or name_for(binding, child))
    aims = _aims(rig)
    pivot = _arm_space(rig, [joint.pivot])[0]
    axis = _signed(np.array(rig.matrix_world.inverted().to_3x3() @ Vector(joint.axis)))
    points = _arm_space(rig, binding.points(child))
    binding.bind(child, name)
    with EditSession(context, rig) as edit_bones:
        eb = edit_bones.new(name)
        eb.use_connect = False
        eb.parent = edit_bones[parent]
        y, length = _direction(pivot, axis, aims.get(name), points)
        _place(eb, pivot, axis, y, length)
        if parent != binding.root:
            _orient(rig, edit_bones, binding, parent, aims)
    data = rig.data.bones[name].dasktoon_joint
    data.kind = joint.kind
    apply_kind(rig, name)
    shapes.style(rig, name, binding)
    return name


def remove(context, binding, name):
    """Take joint `name` away: its pieces go back to the root (not given a joint), its children to its parent."""
    rig = binding.rig
    if name == binding.root or name not in rig.data.bones:
        raise MachineError(rpt_("This joint cannot be removed"))
    from . import aim, legs, linkage
    legs.remove_for(context, rig, name)
    aim.remove_for(context, rig, name)
    linkage.remove_for(context, rig, name)
    pieces = binding.pieces_of(name)
    if pieces:
        binding.bind(pieces, binding.root)
    parent = rig.data.bones[name].parent
    parent = parent.name if parent is not None else binding.root
    aims = _aims(rig)
    with EditSession(context, rig) as edit_bones:
        eb = edit_bones[name]
        for c in list(eb.children):
            c.parent = eb.parent
        edit_bones.remove(eb)
        if parent != binding.root:
            _orient(rig, edit_bones, binding, parent, aims)
    for obj in binding.objects:
        group = obj.vertex_groups.get(name)
        if group is not None:
            obj.vertex_groups.remove(group)
    return parent


def descendants(rig, name):
    return {b.name for b in rig.data.bones[name].children_recursive}


def set_parent(context, binding, name, parent):
    rig = binding.rig
    parent = parent or binding.root
    if parent == name or parent in descendants(rig, name):
        raise MachineError(rpt_("A joint cannot hang from itself or from a joint below it"))
    old = rig.data.bones[name].parent
    old = old.name if old is not None else None
    aims = _aims(rig)
    with EditSession(context, rig) as edit_bones:
        edit_bones[name].parent = edit_bones[parent]
        for n in (old, parent):
            if n is not None and n != binding.root:
                _orient(rig, edit_bones, binding, n, aims)


def move(context, binding, name, joint):
    """Joint `name` gets the pivot, axis and kind of `joint`."""
    rig = binding.rig
    pivot = _arm_space(rig, [joint.pivot])[0]
    axis = _signed(np.array(rig.matrix_world.inverted().to_3x3() @ Vector(joint.axis)))
    aims = _aims(rig)
    with EditSession(context, rig) as edit_bones:
        eb = edit_bones[name]
        target = aims.get(name)
        if target is None and len(eb.children) == 1:
            target = np.array(eb.children[0].head)
        points = _arm_space(rig, binding.points(binding.pieces_of(name)))
        y, length = _direction(pivot, axis, target, points)
        _place(eb, pivot, axis, y, length)
        if eb.parent is not None and eb.parent.name != binding.root:
            _orient(rig, edit_bones, binding, eb.parent.name, aims)
    rig.data.bones[name].dasktoon_joint.kind = joint.kind
    apply_kind(rig, name)
    shapes.style(rig, name, binding)


def joint_of(rig, name):
    """The Joint of bone `name` in world space."""
    bone = rig.data.bones[name]
    m = rig.matrix_world @ bone.matrix_local
    return Joint(np.array(m.translation), np.array(m.to_3x3().col[0].normalized()), bone.dasktoon_joint.kind)


# Kinds and limits


def apply_kind(rig, name):
    """Rotation mode, locks, IK locks and the limit constraint of joint `name` from its kind and limits."""
    pb = rig.pose.bones.get(name)
    if pb is None:
        return
    data = rig.data.bones[name].dasktoon_joint
    kind = data.kind
    pb.lock_scale = (True, True, True)
    if kind == 'HINGE':
        pb.rotation_mode = 'XYZ'
        pb.lock_rotation = (False, True, True)
        pb.lock_rotation_w = False
        pb.lock_location = (True, True, True)
        pb.lock_ik_x, pb.lock_ik_y, pb.lock_ik_z = False, True, True
    elif kind == 'BALL':
        pb.rotation_mode = 'QUATERNION'
        pb.lock_rotation = (False, False, False)
        pb.lock_rotation_w = False
        pb.lock_location = (True, True, True)
        pb.lock_ik_x = pb.lock_ik_y = pb.lock_ik_z = False
    elif kind == 'SLIDE':
        pb.rotation_mode = 'XYZ'
        pb.lock_rotation = (True, True, True)
        pb.lock_location = (False, True, True)
        pb.lock_ik_x = pb.lock_ik_y = pb.lock_ik_z = True
    else:
        pb.rotation_mode = 'XYZ'
        pb.lock_rotation = (True, True, True)
        pb.lock_location = (True, True, True)
        pb.lock_ik_x = pb.lock_ik_y = pb.lock_ik_z = True
    if kind != 'BALL':
        pb.rotation_euler = (pb.rotation_euler[0] if kind == 'HINGE' else 0.0, 0.0, 0.0)
    if kind != 'SLIDE':
        pb.location = (0.0, 0.0, 0.0)
    else:
        pb.location = (pb.location[0], 0.0, 0.0)
    for con in [c for c in pb.constraints if c.name == LIMIT]:
        pb.constraints.remove(con)
    limited = data.use_limit and kind in ('HINGE', 'SLIDE')
    pb.use_ik_limit_x = limited and kind == 'HINGE'
    if kind == 'HINGE':
        pb.ik_min_x = max(min(data.angle_min, 0.0), -np.pi)
        pb.ik_max_x = min(max(data.angle_max, 0.0), np.pi)
    if not limited:
        return
    if kind == 'HINGE':
        con = pb.constraints.new('LIMIT_ROTATION')
        con.use_limit_x = True
        con.min_x, con.max_x = data.angle_min, data.angle_max
    else:
        con = pb.constraints.new('LIMIT_LOCATION')
        con.use_min_x = con.use_max_x = True
        con.min_x, con.max_x = data.distance_min, data.distance_max
    con.name = LIMIT
    con.owner_space = 'LOCAL'
    con.use_transform_limit = True
