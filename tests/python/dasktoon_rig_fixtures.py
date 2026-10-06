# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Test characters for the anime rig (not a test): simple meshes around the standard skeleton of a character HEIGHT
tall, as separate objects or as one mesh with a material per piece. Sizes are in units of the height."""

import math

import bpy

HEIGHT = 1.6


def mesh_object(name, verts, faces, materials=(), face_materials=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat_name in materials:
        mesh.materials.append(bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name))
    if face_materials is not None:
        mesh.polygons.foreach_set("material_index", face_materials)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def tube(z_top, z_bottom, r_top, r_bottom, rings=12, segments=16):
    """(verts, faces) of an open tube around the Z axis from z_top down to z_bottom; vertex s of a ring is at angle
    360 * s / segments degrees from +X (s = 12 of 16 is the front, -Y)."""
    verts, faces = [], []
    for r in range(rings + 1):
        t = r / rings
        z = (z_top + (z_bottom - z_top) * t) * HEIGHT
        radius = (r_top + (r_bottom - r_top) * t) * HEIGHT
        for s in range(segments):
            a = 2.0 * math.pi * s / segments
            verts.append((radius * math.cos(a), radius * math.sin(a), z))
    for r in range(rings):
        for s in range(segments):
            a, b = r * segments + s, r * segments + (s + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    return verts, faces


def strip(top, bottom, width, rings=10):
    """(verts, faces) of a ribbon from `top` to `bottom` (xyz), `width` wide along X; the first ring is the top."""
    verts, faces = [], []
    for r in range(rings + 1):
        t = r / rings
        x, y, z = (top[i] + (bottom[i] - top[i]) * t for i in range(3))
        verts += [((x - width / 2) * HEIGHT, y * HEIGHT, z * HEIGHT), ((x + width / 2) * HEIGHT, y * HEIGHT, z * HEIGHT)]
    for r in range(rings):
        faces.append((2 * r, 2 * r + 1, 2 * r + 3, 2 * r + 2))
    return verts, faces


def cube(centre, size):
    (cx, cy, cz), h = centre, size / 2
    verts = [((cx + dx * h) * HEIGHT, (cy + dy * h) * HEIGHT, (cz + dz * h) * HEIGHT)
             for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces


PIECES = (
    ("Body", lambda: tube(0.86, 0.05, 0.07, 0.07, rings=24)),
    ("Shirt", lambda: tube(0.78, 0.60, 0.08, 0.08, rings=6)),
    ("Hair", lambda: strip((0.0, 0.06, 0.96), (0.0, 0.10, 0.62), 0.04)),
    ("Skirt", lambda: tube(0.53, 0.36, 0.08, 0.13, rings=6)),
    ("Ribbon", lambda: cube((0.0, 0.07, 0.97), 0.02)),
    ("Eye", lambda: cube((0.03, -0.06, 0.915), 0.01)),
)


def combine(name, pieces):
    """One mesh object of (verts, faces, material name) pieces, a material slot per piece."""
    verts, faces, face_materials, materials = [], [], [], []
    for piece_verts, piece_faces, material in pieces:
        offset = len(verts)
        verts += piece_verts
        faces += [tuple(i + offset for i in f) for f in piece_faces]
        face_materials += [len(materials)] * len(piece_faces)
        materials.append(material)
    return mesh_object(name, verts, faces, materials, face_materials)


def character(merged=False):
    """{piece name: object}, or {"Character": object} with materials named after the pieces when `merged`."""
    if merged:
        return {"Character": combine("Character", [(*make(), name) for name, make in PIECES])}
    return {name: mesh_object(name, *make()) for name, make in PIECES}


def rig_for(context=None):
    from dasktoon_rig import skeleton
    return skeleton.create_humanoid(context or bpy.context, HEIGHT, (0.0, 0.0, 0.0))
