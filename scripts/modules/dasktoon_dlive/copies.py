# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Temporary copies of a character's meshes (DaskToon spec 2026-11-10-dasktoon-dlive-design.md, R4): the .dlive export
makes expressions on these, so the file being worked on stays as it was.

A copy takes the name of its mesh (the original waits under another name), links to the same collections and keeps the
armature, so the model, the rig data and the shape key names come out as they would from the original. The rig's parts
point at the copies meanwhile: Auto Expressions finds the eyes, the hair and the body by them. Afterwards the copies,
their meshes and shape keys go, the names and the pointers come back."""

import contextlib

import bpy

PARKED = "dlive original %d"


def _rigs(objects):
    return [obj for obj in objects if obj.type == 'ARMATURE' and getattr(obj.data, "dasktoon_rig", None) is not None]


def _make(obj, index):
    """(the copy, its name, its mesh's name); the original is parked under another name so the copy takes its own."""
    name, data_name = obj.name, obj.data.name
    obj.name = PARKED % index
    obj.data.name = PARKED % index
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name, copy.data.name = name, data_name
    for collection in obj.users_collection or [bpy.context.scene.collection]:
        collection.objects.link(copy)
    return copy, name, data_name


@contextlib.contextmanager
def temporary(context, objects):
    """Yields `objects` with every mesh replaced by a copy of it. Nothing of the file's own changes: names, the parts'
    objects and the data-blocks are as before once this ends."""
    originals = [obj for obj in objects if obj.type == 'MESH']
    copies = {}  # original -> (copy, name, mesh name)
    retargeted = []  # (part, original)
    made_keys = []
    try:
        for index, obj in enumerate(originals):
            copies[obj] = _make(obj, index)
            if copies[obj][0].data.shape_keys is not None:
                made_keys.append(copies[obj][0].data.shape_keys)
        for rig in _rigs(objects):
            for part in rig.data.dasktoon_rig.parts:
                if part.object in copies:
                    retargeted.append((part, part.object))
                    part.object = copies[part.object][0]
        context.view_layer.update()
        yield [copies[obj][0] if obj in copies else obj for obj in objects]
    finally:
        for part, original in retargeted:
            part.object = original
        meshes = []
        for original, (copy, name, data_name) in copies.items():
            meshes.append(copy.data)
            bpy.data.objects.remove(copy)
            original.name, original.data.name = name, data_name
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for key in made_keys:
            try:
                if key.users == 0:
                    bpy.data.shape_keys.remove(key)
            except ReferenceError:  # went with its mesh
                pass
