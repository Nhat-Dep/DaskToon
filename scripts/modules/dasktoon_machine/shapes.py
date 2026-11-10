# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The look of a machine's controls (machine rig spec 4): a custom shape per kind of joint (a ring round a hinge's
axis, three rings for a ball joint, a double arrow for a slide, a small diamond for a fixed joint), sized to the joint's
pieces; a colour per kind; the bone collections Joints and Targets. The shapes are wire meshes kept in the hidden
collection "DT Machine Shapes"."""

import math

import bpy
import numpy as np

COLLECTION = "DT Machine Shapes"
JOINTS = "Joints"
TARGETS = "Targets"
COLOURS = {'HINGE': 'THEME01', 'BALL': 'THEME03', 'SLIDE': 'THEME04', 'FIXED': 'THEME10', 'ROOT': 'THEME09',
           'TARGET': 'THEME09'}


def _circle(plane, radius=1.0, segments=32, offset=0):
    a, b = plane
    verts = []
    for k in range(segments):
        t = 2 * math.pi * k / segments
        v = [0.0, 0.0, 0.0]
        v[a], v[b] = math.cos(t) * radius, math.sin(t) * radius
        verts.append(tuple(v))
    edges = [(offset + k, offset + (k + 1) % segments) for k in range(segments)]
    return verts, edges


def _join(*parts):
    verts, edges = [], []
    for v, e in parts:
        offset = len(verts)
        verts += v
        edges += [(a + offset, b + offset) for a, b in e]
    return verts, edges


def _arrow():
    verts = [(-1, 0, 0), (1, 0, 0), (0.8, 0.12, 0), (0.8, -0.12, 0), (-0.8, 0.12, 0), (-0.8, -0.12, 0),
             (0.8, 0, 0.12), (0.8, 0, -0.12), (-0.8, 0, 0.12), (-0.8, 0, -0.12)]
    edges = [(0, 1), (1, 2), (1, 3), (0, 4), (0, 5), (1, 6), (1, 7), (0, 8), (0, 9)]
    return verts, edges


def _diamond():
    verts = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    edges = [(a, b) for a in range(2) for b in range(2, 6)] + [(2, 4), (4, 3), (3, 5), (5, 2)]
    return [tuple(c * 0.3 for c in v) for v in verts], edges


def _cube():
    verts = [(x, y, z) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]
    return verts, edges


def _root():
    v, e = _circle((0, 1))
    tip = len(v)
    return v + [(0.0, 1.3, 0.0)], e + [(8 - 2, tip), (tip, 8 + 2)]


SHAPES = {
    'HINGE': lambda: _circle((1, 2)),
    'BALL': lambda: _join(_circle((1, 2)), _circle((0, 2)), _circle((0, 1))),
    'SLIDE': _arrow,
    'FIXED': _diamond,
    'ROOT': _root,
    'TARGET': _cube,
    'AIM': lambda: _join(_circle((1, 2), 0.5), _circle((0, 2), 0.5), _circle((0, 1), 0.5)),
}


def shape(kind):
    name = "DT Machine %s" % kind.title()
    obj = bpy.data.objects.get(name)
    if obj is not None and obj.type == 'MESH':
        return obj
    verts, edges = SHAPES[kind]()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        collection.hide_viewport = True
        collection.hide_render = True
        bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    return obj


def _collection(rig, name):
    arm = rig.data
    return arm.collections.get(name) or arm.collections.new(name)


def _assign(rig, name, collection, colour):
    bone = rig.data.bones[name]
    for c in list(bone.collections):
        c.unassign(bone)
    _collection(rig, collection).assign(bone)
    pb = rig.pose.bones[name]
    pb.color.palette = colour
    bone.color.palette = colour


def style_root(rig):
    from . import root_name
    name = root_name(rig)
    pb = rig.pose.bones.get(name)
    if pb is None:
        return
    pb.custom_shape = shape('ROOT')
    pb.use_custom_shape_bone_size = True
    pb.custom_shape_scale_xyz = (2.0, 2.0, 2.0)
    _assign(rig, name, JOINTS, COLOURS['ROOT'])


def style(rig, name, binding):
    """Shape, size, colour and collection of joint `name` from its kind and pieces."""
    bone = rig.data.bones[name]
    pb = rig.pose.bones[name]
    kind = bone.dasktoon_joint.kind
    m = rig.matrix_world @ bone.matrix_local
    head = np.array(m.translation)
    axis = np.array(m.to_3x3().col[0].normalized())
    points = binding.points(binding.pieces_of(name))
    radius = 0.05
    if len(points):
        d = points - head
        if kind == 'HINGE':
            d = d - np.outer(d @ axis, axis)
        radius = float(np.linalg.norm(d, axis=1).max())
        radius = radius * (1.15 if kind == 'HINGE' else 0.6)
        size = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        radius = max(radius, 0.05 * size, 0.01)
    scale = rig.matrix_world.to_scale()
    radius /= max(sum(scale) / 3.0, 1e-6)
    pb.custom_shape = shape(kind)
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = (radius, radius, radius)
    _assign(rig, name, JOINTS, COLOURS[kind])


def style_target(rig, name, kind, size):
    pb = rig.pose.bones[name]
    pb.custom_shape = shape(kind)
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = (size, size, size)
    _assign(rig, name, TARGETS, COLOURS['TARGET'])
