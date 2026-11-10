# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A test machine for the machine rig (not a test), in metres: a box body; a turret standing flat on it with two ears;
a gun whose trunnion sits between the ears and a barrel along +X; a hatch standing on the body along one edge; a leg
on the +X end (thigh, shin, foot); an axle on the -X end and a wheel with a hole round it, as a mesh of its own.
Each named piece is one loose part; `PIECES` maps its name to the mesh and a vertex in it."""

import math

import bpy

SEGMENTS = 16


def box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces


def _frame(axis):
    """(u, v, w): w along `axis` ('X', 'Y' or 'Z'), u and v across it."""
    return {'X': ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
            'Y': ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
            'Z': ((1, 0, 0), (0, 1, 0), (0, 0, 1))}[axis]


def cylinder(centre, axis, radius, length, rings=1, hole=0.0, end_radius=None):
    """A closed cylinder (n-gon caps) along `axis`, `rings` segments long, narrowing to `end_radius` at its + end; with
    `hole` > 0 a thick ring round a hole of that radius instead (a wheel)."""
    u, v, w = _frame(axis)
    verts, faces = [], []

    def point(r, a, t):
        c, s = math.cos(a) * r, math.sin(a) * r
        return tuple(centre[i] + u[i] * c + v[i] * s + w[i] * t for i in range(3))

    ts = [-length / 2 + length * k / rings for k in range(rings + 1)]
    for r, t in enumerate(ts):
        ring_radius = radius if end_radius is None else radius + (end_radius - radius) * r / rings
        for k in range(SEGMENTS):
            verts.append(point(ring_radius, 2 * math.pi * k / SEGMENTS, t))
    n = SEGMENTS
    for r in range(rings):
        for k in range(n):
            a, b = r * n + k, r * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    if hole <= 0.0:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(rings * n + k for k in range(n)))
        return verts, faces
    inner = len(verts)
    for t in (ts[0], ts[-1]):
        for k in range(n):
            verts.append(point(hole, 2 * math.pi * k / SEGMENTS, t))
    for k in range(n):
        k1 = (k + 1) % n
        faces.append((inner + n + k, inner + n + k1, inner + k1, inner + k))  # the hole's wall
        faces.append((k1, k, inner + k, inner + k1))  # bottom face of the ring
        top, itop = rings * n, inner + n
        faces.append((top + k, top + k1, itop + k1, itop + k))  # top face of the ring
    return verts, faces


def tilted_ring(centre, normal, radius, width=0.01, segments=32):
    """A flat band round `centre` in the plane across `normal` (a gyroscope's ring)."""
    n = [c / math.sqrt(sum(v * v for v in normal)) for c in normal]
    a = [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]
    u = [a[1] * n[2] - a[2] * n[1], a[2] * n[0] - a[0] * n[2], a[0] * n[1] - a[1] * n[0]]
    lu = math.sqrt(sum(v * v for v in u))
    u = [v / lu for v in u]
    v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]]
    verts, faces = [], []
    for r in (radius, radius - width):
        for k in range(segments):
            t = 2 * math.pi * k / segments
            verts.append(tuple(centre[i] + (u[i] * math.cos(t) + v[i] * math.sin(t)) * r for i in range(3)))
    for k in range(segments):
        k1 = (k + 1) % segments
        faces.append((k, k1, segments + k1, segments + k))
    return verts, faces


# name: (mesh, builder)
PARTS = (
    ("Body", "Mech", lambda: box((-0.3, -0.2, 0.5), (0.3, 0.2, 0.7))),
    ("Turret", "Mech", lambda: cylinder((0.0, 0.0, 0.75), 'Z', 0.15, 0.1)),
    ("EarL", "Mech", lambda: box((0.06, 0.05, 0.8), (0.14, 0.09, 0.9))),
    ("EarR", "Mech", lambda: box((0.06, -0.09, 0.8), (0.14, -0.05, 0.9))),
    ("Trunnion", "Mech", lambda: cylinder((0.1, 0.0, 0.84), 'Y', 0.04, 0.1)),
    ("Barrel", "Mech", lambda: cylinder((0.32, 0.0, 0.84), 'X', 0.025, 0.36, rings=4)),
    ("Hatch", "Mech", lambda: box((-0.25, 0.1, 0.7), (-0.05, 0.11, 0.8))),
    ("Thigh", "Mech", lambda: box((0.3, -0.03, 0.57), (0.5, 0.03, 0.63))),
    ("Shin", "Mech", lambda: box((0.47, -0.03, 0.15), (0.53, 0.03, 0.6))),
    ("Foot", "Mech", lambda: box((0.44, -0.04, 0.1), (0.62, 0.04, 0.15))),
    ("Axle", "Mech", lambda: cylinder((-0.2, 0.275, 0.55), 'Y', 0.03, 0.15)),
    ("Wheel", "Wheel", lambda: cylinder((-0.2, 0.3, 0.55), 'Y', 0.12, 0.05, hole=0.03)),
    # a lamp head wider than the mast it sits on: only the mast's corners touch it
    ("Mast", "Mech", lambda: box((-0.27, -0.17, 0.7), (-0.23, -0.13, 0.85))),
    ("Lamp", "Mech", lambda: box((-0.3, -0.2, 0.85), (-0.2, -0.1, 0.9))),
    # a drill bit hanging under the body without touching it, round about its own axis
    ("Drill", "Mech", lambda: cylinder((0.0, 0.0, 0.38), 'Z', 0.01, 0.2, end_radius=0.05)),
    # a fan off the -X end: a round hub with two blades reaching out of it, none touching the body
    ("Hub", "Mech", lambda: cylinder((-0.36, -0.1, 0.6), 'X', 0.03, 0.06)),
    ("Blade", "Mech", lambda: box((-0.37, -0.11, 0.63), (-0.35, -0.09, 0.8))),
    ("Blade2", "Mech", lambda: box((-0.37, -0.3, 0.59), (-0.35, -0.13, 0.61))),
    # two tilted rings crossing, floating over a round plinth on the body, spinning together about its axis
    ("Plinth", "Mech", lambda: cylinder((0.22, 0.12, 0.75), 'Z', 0.05, 0.1)),
    ("RingA", "Mech", lambda: tilted_ring((0.22, 0.12, 1.0), (0.94, 0.0, 0.34), 0.06, width=0.003)),
    ("RingB", "Mech", lambda: tilted_ring((0.22, 0.12, 1.0), (0.0, 0.94, 0.34), 0.06, width=0.003)),
)

# Where the joints of the test machine are: (pivot, axis).
HIP = ((0.3, 0.0, 0.6), (0.0, 1.0, 0.0))
KNEE = ((0.5, 0.0, 0.6), (0.0, 1.0, 0.0))
ANKLE = ((0.5, 0.0, 0.125), (0.0, 1.0, 0.0))


def machine():
    """({mesh name: object}, {part name: (object, first vertex index)})."""
    meshes, firsts = {}, {}
    data = {}
    for name, mesh_name, make in PARTS:
        verts, faces = make()
        mv, mf, mm, mats = data.setdefault(mesh_name, ([], [], [], []))
        firsts[name] = (mesh_name, len(mv))
        offset = len(mv)
        mv += verts
        mf += [tuple(i + offset for i in f) for f in faces]
        mm += [len(mats)] * len(faces)
        mats.append(name)
    for mesh_name, (mv, mf, mm, mats) in data.items():
        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(mv, [], mf)
        for mat_name in mats:
            mesh.materials.append(bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name))
        mesh.polygons.foreach_set("material_index", mm)
        mesh.validate()
        mesh.update()
        obj = bpy.data.objects.new(mesh_name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        meshes[mesh_name] = obj
    return meshes, {name: (meshes[m], i) for name, (m, i) in firsts.items()}
