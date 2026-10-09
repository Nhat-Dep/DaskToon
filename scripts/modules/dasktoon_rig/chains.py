# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The maths of generated chains (anime rig spec 6.3, 6.4) on plain numpy arrays, so it is tested without meshes:
geodesic distance along edges, the joints and weights of a hair lock, and the strips of a skirt."""

import heapq
import math

import numpy as np

ROOT_SHARE = 0.10   # vertices this close (share of the distance range) to the attach bone lie on the head: the root
SHORT = 1.5         # a piece whose main spread is under SHORT times its second spread is wide: no chain
TIP_SHARE = 0.05    # the tip joint is the centre of this share of the farthest vertices
MIN_VERTICES = 4


def segment_distance(points, head, tail):
    """Distance of each point (n x 3) to the segment head-tail."""
    points = np.asarray(points, float)
    head, tail = np.asarray(head, float), np.asarray(tail, float)
    axis = tail - head
    length2 = float(axis @ axis)
    if length2 < 1e-18:
        return np.linalg.norm(points - head, axis=1)
    t = np.clip((points - head) @ axis / length2, 0.0, 1.0)
    return np.linalg.norm(points - (head + t[:, None] * axis), axis=1)


def components(count, edges):
    """Connected components of a graph of `count` vertices: sorted index arrays, ordered by their first vertex."""
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in np.asarray(edges, np.int64).reshape(-1, 2).tolist():
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(count)], np.int64)
    return [np.nonzero(roots == r)[0] for r in np.unique(roots)]


def geodesic(points, edges, seeds):
    """Shortest distance from any of `seeds` to every vertex walking along `edges` (inf where unreachable)."""
    points = np.asarray(points, float)
    edges = np.asarray(edges, np.int64).reshape(-1, 2)
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1).tolist()
    neighbours = [[] for _ in range(len(points))]
    for (a, b), length in zip(edges.tolist(), lengths):
        neighbours[a].append((b, length))
        neighbours[b].append((a, length))
    dist = [math.inf] * len(points)
    heap = []
    for seed in seeds:
        dist[int(seed)] = 0.0
        heap.append((0.0, int(seed)))
    heapq.heapify(heap)
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v]:
            continue
        for w, length in neighbours[v]:
            nd = d + length
            if nd < dist[w]:
                dist[w] = nd
                heapq.heappush(heap, (nd, w))
    return np.array(dist)


def tent(u, count):
    """Weights (n x count+1) along a chain for positions u in [0, count]: column 0 (the attach bone) peaks at u = 0
    and column j (the j-th chain bone) at u = j; each row sums to 1."""
    u = np.clip(np.asarray(u, float), 0.0, count)
    w = np.maximum(0.0, 1.0 - np.abs(u[:, None] - np.arange(count + 1)[None, :]))
    return w / w.sum(axis=1, keepdims=True)


class Chain:
    """One lock: joints (count+1 x 3) from root to tip, and weights (n x count+1, column 0 for the attach bone)."""

    def __init__(self, joints, weights):
        self.joints = joints
        self.weights = weights


def _fill(rows):
    """`rows` with the rows that are nan interpolated from the known rows around them."""
    known = np.nonzero(~np.isnan(rows[:, 0]))[0]
    for axis in range(rows.shape[1]):
        rows[:, axis] = np.interp(np.arange(len(rows)), known, rows[known, axis])
    return rows


def is_long(points):
    """True when the points spread at least SHORT times more along their main axis than along the second one."""
    centred = points - points.mean(axis=0)
    _values, vectors = np.linalg.eigh(centred.T @ centred)
    main, second = (float(np.ptp(centred @ vectors[:, i])) for i in (2, 1))
    return main >= SHORT * second


def hair_chain(points, edges, attach_head, attach_tail, count):
    """The chain of one lock (spec 6.3), or None for a piece that is too small or too wide for one. The root (vertices
    close to the attach bone, lying on the head) follows the attach bone; joint 0 is the middle of the root's rim."""
    points = np.asarray(points, float)
    if len(points) < MIN_VERTICES or not is_long(points):
        return None
    edges = np.asarray(edges, np.int64).reshape(-1, 2)
    near = segment_distance(points, attach_head, attach_tail)
    seeds = near <= near.min() + ROOT_SHARE * (near.max() - near.min()) + 1e-12
    dist = geodesic(points, edges, np.nonzero(seeds)[0])
    reached = np.isfinite(dist)
    dist[~reached] = dist[reached].max()
    length = float(dist.max())
    if length <= 1e-9:
        return None
    rim = np.zeros(len(points), bool)
    rim[edges[seeds[edges[:, 0]] != seeds[edges[:, 1]]].ravel()] = True
    rim &= seeds
    u = dist / length * count
    joints = np.full((count + 1, 3), np.nan)
    joints[0] = points[rim if rim.any() else seeds].mean(axis=0)
    joints[count] = points[np.argsort(dist)[-max(1, int(round(TIP_SHARE * len(points)))):]].mean(axis=0)
    for k in range(1, count):
        band = np.abs(u - k) <= 0.25
        if band.any():
            joints[k] = points[band].mean(axis=0)
    return Chain(_fill(joints), tent(u, count))


def strip_angle(index, strips):
    """Angle around the vertical axis of skirt strip `index`: strip 0 at the front (-Y), then counter-clockwise seen
    from above (towards the character's left, +X)."""
    return -math.pi / 2.0 + 2.0 * math.pi * index / strips


class Skirt:
    """Skirt strips: their joints (count+1 x 3, None for a strip with no vertex near it) and the weights (n x 1 +
    strips*count): column 0 for the attach bone, then strip c bone k (1..count) in column 1 + c*count + k-1."""

    def __init__(self, strips, weights):
        self.strips = strips
        self.weights = weights


def skirt_chains(points, count, strips):
    """`strips` strips of `count` bones around the vertical axis through the middle of `points` (spec 6.4)."""
    points = np.asarray(points, float)
    low, high = points.min(axis=0), points.max(axis=0)
    centre = (low[:2] + high[:2]) / 2.0
    top, height = float(high[2]), max(float(high[2] - low[2]), 1e-9)
    rel = points[:, :2] - centre
    radius = np.linalg.norm(rel, axis=1)
    u = (top - points[:, 2]) / height * count
    step = 2.0 * math.pi / strips
    a = np.mod(np.arctan2(rel[:, 1], rel[:, 0]) - strip_angle(0, strips), 2.0 * math.pi) / step
    lower = np.floor(a).astype(np.int64) % strips
    upper = (lower + 1) % strips
    frac = a - np.floor(a)
    nearest = np.where(frac < 0.5, lower, upper)
    used = np.zeros(strips, bool)
    used[np.unique(nearest)] = True
    level = np.rint(np.clip(u, 0.0, count)).astype(np.int64)
    out = []
    for c in range(strips):
        if not used[c]:
            out.append(None)
            continue
        radii = np.full((count + 1, 1), np.nan)
        for k in range(count + 1):
            here = (nearest == c) & (level == k)
            ring = here if here.any() else level == k
            if ring.any():
                radii[k, 0] = radius[ring].mean()
        radii = _fill(radii)[:, 0]
        theta = strip_angle(c, strips)
        out.append(np.array([(centre[0] + radii[k] * math.cos(theta), centre[1] + radii[k] * math.sin(theta),
                              top - k * height / count) for k in range(count + 1)]))
    along = tent(u, count)
    share_lower = np.where(used[upper], 1.0 - frac, 1.0)
    share_upper = np.where(used[upper], frac, 0.0)
    share_upper = np.where(used[lower], share_upper, 1.0)
    share_lower = np.where(used[lower], share_lower, 0.0)
    weights = np.zeros((len(points), 1 + strips * count))
    weights[:, 0] = along[:, 0]
    rows = np.arange(len(points))
    for k in range(1, count + 1):
        np.add.at(weights, (rows, 1 + lower * count + k - 1), share_lower * along[:, k])
        np.add.at(weights, (rows, 1 + upper * count + k - 1), share_upper * along[:, k])
    return Skirt(out, weights)
