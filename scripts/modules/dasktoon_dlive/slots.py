# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Faces without a material (a .dlive must name every surface of its model): the glTF exporter writes a primitive for
them with no material, which a player cannot match to materials.json. Meanwhile the export, every mesh that has such
faces (no slots, an empty slot, or an index past the slots) gets a plain DaskToon material for them; the meshes are given
back as they were."""

import contextlib

import bpy

NAME = "Unassigned"


def _material():
    mat = bpy.data.materials.new(NAME)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    node = tree.nodes.new('ShaderNodeAnimeCharacter')
    node.use_outline = False
    node.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    tree.links.new(next(s for s in node.outputs if s.enabled), out.inputs["Surface"])
    return mat


def _in_model(obj):
    """The glTF export writes the selectable, visible objects of the view layer (a bone shape the glTF importer left
    hidden is not in the model, and gets no material)."""
    try:
        return obj.name in bpy.context.view_layer.objects and obj.visible_get()
    except RuntimeError:
        return False


def _needs(mesh):
    slots = mesh.materials
    if len(mesh.polygons) == 0:
        return False
    if len(slots) == 0:
        return True
    used = {p.material_index for p in mesh.polygons}
    return any(i >= len(slots) or slots[i] is None for i in used)


@contextlib.contextmanager
def filled(objects):
    """Gives the meshes' unassigned faces a material while the block runs; yields the names of the meshes changed."""
    changed = []  # (mesh, materials before as a list, material_index of faces moved)
    mat = None
    try:
        for obj in objects:
            if obj.type != 'MESH' or not _needs(obj.data) or not _in_model(obj):
                continue
            mesh = obj.data
            mat = mat or _material()
            before = list(mesh.materials)
            indices = [p.material_index for p in mesh.polygons]
            if len(before) == 0:
                mesh.materials.append(mat)
                target = 0
            else:
                free = next((i for i, m in enumerate(before) if m is None), None)
                if free is None:
                    mesh.materials.append(mat)
                    free = len(before)
                else:
                    mesh.materials[free] = mat
                target = free
            fixed = [target if i >= len(before) or before[i] is None else i for i in indices]
            mesh.polygons.foreach_set("material_index", fixed)
            mesh.update()
            changed.append((mesh, before, indices))
        yield [mesh.name for mesh, _before, _indices in changed]
    finally:
        for mesh, before, indices in changed:
            mesh.materials.clear()
            for m in before:
                mesh.materials.append(m)
            mesh.polygons.foreach_set("material_index", indices)
            mesh.update()
        if mat is not None:
            bpy.data.materials.remove(mat)
