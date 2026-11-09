# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Jiggle ("Rung mềm", docs/superpowers/specs/2026-11-10-dasktoon-jiggle-design.md): the presets, adding the modifier
(a vertex group from the selection with a soft edge, placed after the bones), and the rig's colliders with the two
hands copied onto it so the character's own hands and arms push its soft parts."""

import heapq
import math

import numpy as np

GROUP = "DT_Jiggle"
NAME = "Jiggle"
HAND_SHARE = 0.9  # of the hand's mean thickness, like the rig's colliders (build.COLLIDER_SHARE)
HAND_FALLBACK = 0.35  # of the hand's length, for a hand no vertex follows
EDGE = 0.5  # the soft edge of a selection, as a share of the selection's radius
SIDES = ("Left", "Right")

# name: (frequency, damping, spread, volume, follow, pin bottom) (spec 7)
PRESETS = {
    'PUDDING': (3.0, 0.12, 0.6, 0.8, 0.0, True),
    'JELLY': (5.0, 0.08, 0.4, 0.6, 0.0, True),
    'BREAST': (2.5, 0.18, 0.5, 0.5, 0.3, False),
    'FLESH': (3.5, 0.25, 0.5, 0.5, 0.5, False),
    'CHEEK': (5.0, 0.3, 0.5, 0.3, 0.6, False),
}
PRESET_ITEMS = (
    ('PUDDING', "Pudding", "Soft and slow, the bottom stands still"),
    ('JELLY', "Jelly", "Quick and springy, the bottom stands still"),
    ('BREAST', "Breast", "Bounces with the body, settles slowly"),
    ('FLESH', "Soft Flesh", "Belly, thighs: a short wobble"),
    ('CHEEK', "Cheek", "Small and quick, mostly when touched"),
)


def apply_preset(md, preset):
    frequency, damping, spread, volume, follow, pin = PRESETS[preset]
    md.frequency = frequency
    md.damping = damping
    md.spread = spread
    md.volume = volume
    md.follow = follow
    md.use_pin_bottom = pin


def find_rig(obj):
    """The armature that moves `obj`: its Armature modifier's, else an armature parent."""
    for md in obj.modifiers:
        if md.type == 'ARMATURE' and md.object is not None:
            return md.object
    parent = obj.parent
    return parent if parent is not None and parent.type == 'ARMATURE' else None


def insert_index(obj):
    """Right after the last Armature modifier (the jiggle follows the posed shape), else the top of the stack."""
    index = 0
    for i, md in enumerate(obj.modifiers):
        if md.type == 'ARMATURE':
            index = i + 1
    return index


def soft_weights(obj, selected):
    """{vertex: weight} of the selection: 1 inside, falling smoothly to 0 along the surface over EDGE x the
    selection's radius (spec 6)."""
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ np.array(obj.matrix_world.to_3x3()).T
    selected = sorted(selected)
    if not selected:
        return {}
    centre = co[selected].mean(axis=0)
    radius = float(np.linalg.norm(co[selected] - centre, axis=1).max())
    edge = EDGE * radius
    weights = {i: 1.0 for i in selected}
    if edge <= 1e-9:
        return weights
    neighbours = [[] for _ in mesh.vertices]
    for e in mesh.edges:
        a, b = e.vertices
        neighbours[a].append(b)
        neighbours[b].append(a)
    dist = {i: 0.0 for i in selected}
    heap = [(0.0, i) for i in selected]
    while heap:
        d, i = heapq.heappop(heap)
        if d > dist.get(i, math.inf):
            continue
        for j in neighbours[i]:
            nd = d + float(np.linalg.norm(co[i] - co[j]))
            if nd < edge and nd < dist.get(j, math.inf):
                dist[j] = nd
                heapq.heappush(heap, (nd, j))
    for i, d in dist.items():
        if i not in weights:
            t = d / edge
            weights[i] = 1.0 - t * t * (3.0 - 2.0 * t)
    return {i: w for i, w in weights.items() if w > 1e-4}


def _rig_meshes(rig):
    import bpy
    return [obj for obj in bpy.data.objects if obj.type == 'MESH' and find_rig(obj) == rig]


def _descendants(bone):
    out = []
    stack = list(bone.children)
    while stack:
        b = stack.pop()
        out.append(b)
        stack.extend(b.children)
    return out


def hand_colliders(rig):
    """[(bone, end bone, radius in armature units)]: a capsule from each hand's wrist to its furthest fingertip, as
    thick as HAND_SHARE of the hand's vertices around that line (spec 5)."""
    out = []
    for side in SIDES:
        hand = rig.data.bones.get(side + "Hand")
        if hand is None:
            continue
        head = np.array(hand.head_local)
        tips = _descendants(hand)
        end = max(tips, key=lambda b: float(np.linalg.norm(np.array(b.tail_local) - head)), default=None)
        tail = np.array(end.tail_local if end is not None else hand.tail_local)
        length = float(np.linalg.norm(tail - head))
        if length < 1e-9:
            continue
        names = {hand.name} | {b.name for b in tips}
        world_to_rig = np.array(rig.matrix_world.inverted())
        gaps = []
        for obj in _rig_meshes(rig):
            index_names = {g.index: g.name for g in obj.vertex_groups}
            to_rig = world_to_rig @ np.array(obj.matrix_world)
            for v in obj.data.vertices:
                best = max(v.groups, key=lambda g: g.weight, default=None)
                if best is None or index_names.get(best.group) not in names or best.weight < 0.5:
                    continue
                p = (to_rig @ np.array((*v.co, 1.0)))[:3]
                t = min(max(float((p - head) @ (tail - head)) / (length * length), 0.0), 1.0)
                gaps.append(float(np.linalg.norm(p - (head + (tail - head) * t))))
        radius = HAND_SHARE * float(np.mean(gaps)) if gaps else HAND_FALLBACK * length
        out.append((hand.name, end.name if end is not None else "", radius))
    return out


def sync(md, rig):
    """The modifier collides with `rig`'s colliders and both hands; the list is only made again when it differs (each
    collider rebuilds the depsgraph relations)."""
    wanted = []
    if rig is not None:
        data = getattr(rig.data, "dasktoon_rig", None)
        if data is not None:
            wanted = [(c.bone, "", c.radius) for c in data.colliders if rig.data.bones.get(c.bone) is not None]
        wanted += hand_colliders(rig)
    if md.rig != rig:
        md.rig = rig
    have = [(c.bone, c.bone_end, c.radius) for c in md.colliders]
    if len(have) != len(wanted) or any(a[:2] != b[:2] or abs(a[2] - b[2]) > 1e-6 for a, b in zip(have, wanted)):
        md.colliders_clear()
        for bone, bone_end, radius in wanted:
            md.collider_add(bone, bone_end, radius)


def sync_rig(rig):
    """Every Jiggle modifier moved by `rig` collides with its current colliders (after Build Rig)."""
    for obj in _rig_meshes(rig):
        for md in obj.modifiers:
            if md.type == 'JIGGLE':
                sync(md, rig)


def add(obj, selected=None, preset='AUTO'):
    """A Jiggle modifier on `obj`: on the `selected` vertices (soft edge) or the whole object; returns it."""
    rig = find_rig(obj)
    if preset == 'AUTO':
        preset = 'FLESH' if rig is not None else 'PUDDING'
    md = obj.modifiers.new(NAME, 'JIGGLE')
    apply_preset(md, preset)
    if selected:
        group = obj.vertex_groups.new(name=GROUP)
        for i, w in soft_weights(obj, selected).items():
            group.add([i], w, 'REPLACE')
        md.vertex_group = group.name
        md.use_pin_bottom = False
    if rig is not None:
        sync(md, rig)
    index = insert_index(obj)
    current = list(obj.modifiers).index(md)
    if current != index:
        obj.modifiers.move(current, index)
    return md


def make_collider(obj):
    """Give `obj` Collision (Physics) so jiggles collide with it; False when it already has it."""
    if any(md.type == 'COLLISION' for md in obj.modifiers):
        return False
    obj.modifiers.new("Collision", 'COLLISION')
    return True
