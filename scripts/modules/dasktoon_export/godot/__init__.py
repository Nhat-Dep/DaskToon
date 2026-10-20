# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon Engine Export for Godot 4: the model as binary glTF, each DaskToon material as a ShaderMaterial resource,
the shaders, and the import script that puts the materials on the model
(docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md)."""

import contextlib
import json
import os

from bpy.app.translations import pgettext_rpt as rpt_

from .. import report
from . import files, materials, model

DATA_VERSION = 1
HULL_LIGHT = (0.5, 0.8, 0.6)  # the outline hull's light when the scene has no Sun (dasktoon_outline_nodes._FALLBACK)


def to_godot(v):
    """Blender's Z-up axes -> Godot's Y-up axes, as the glTF export turns them."""
    return (v[0], v[2], -v[1])


def world_ambient(scene):
    """The light every surface gets: the World colour times its strength (linear); Blender's default grey when the
    World is not a single colour."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        return (0.0509, 0.0509, 0.0509)
    strength = background.inputs["Strength"].default_value
    return tuple(c * strength for c in background.inputs["Color"].default_value[:3])


def light_direction(scene):
    """Towards the scene's Sun (the outline hull is thinner on its side), in Godot's axes."""
    from bl_ui import dasktoon_outline as outline
    from mathutils import Vector
    sun = outline.find_sun(scene)
    direction = (sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))) if sun is not None else Vector(HULL_LIGHT)
    return to_godot(direction.normalized())


def _write_model(context, target, objects, options, rep, material_paths):
    """<name>/<name>.dasktoon.json, then .glb.import (Godot finds both when it imports the model), then the .glb."""
    from .. import merge
    folder = os.path.join(target.root, target.name)
    data = {"version": DATA_VERSION, "name": target.name, "materials": material_paths}
    files.write_bytes(os.path.join(folder, target.name + ".dasktoon.json"),
                      (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    path = os.path.join(folder, target.name + ".glb")
    model.write_import_settings(path + ".import")
    merging = merge.merged(context, objects) if options.merge_meshes else contextlib.nullcontext((objects, {}))
    with merging as (objects, renamed):
        if renamed:
            rep.merged = (len(renamed), next(iter(renamed.values())))
        left_out = model.write_glb(context, objects, path, options.include_animation)
    rep.model = "%s/%s.glb" % (target.name, target.name)
    if left_out:
        rep.warnings.append(rpt_("Not in the model: %s (not in the current view layer, for example in an excluded "
                                 "collection)") % ", ".join(left_out))


def export_model(context, target, objects, options):
    """Write `objects` (glTF), their DaskToon materials, the shaders and the import script to `target` (Godot spec
    2-4). Returns a Report. Face-shaded meshes get their rest-pose face normals for the model and are given back
    afterwards (face spec 6)."""
    from .. import _materials, face_shading, graph, model_fbx
    rep = report.Report(mode=target.mode, root=target.root, name=target.name, engine=target.engine)
    meshes = [o for o in objects if o.type == 'MESH']
    snapshots, rep.face_meshes, errors = face_shading.bake_rest_normals(context, meshes)
    rep.warnings += errors
    try:
        rep.outline_meshes, errors = model_fbx.prepare_outline_data(meshes)
        rep.warnings += errors
        rep.modifier_notes = model_fbx.modifier_notes(meshes, target.engine)
        os.makedirs(target.root, exist_ok=True)
        rep.shaders = 'INSTALLED' if files.install(target.root) else 'UP_TO_DATE'
        material_paths = {}
        if options.export_materials:
            writer = materials.Writer(target, options, rep, world_ambient(context.scene),
                                      light_direction(context.scene))
            for mat, users in _materials(meshes).items():
                spec, reason = graph.analyze_material(mat, list(dict.fromkeys(o.data for o in users)))
                if spec is None:
                    rep.skipped.append((mat.name, reason))
                    continue
                material_paths[mat.name] = writer.material(spec, users)
        if options.model_format != 'NONE':
            _write_model(context, target, objects, options, rep, material_paths)
    finally:
        face_shading.restore_normals(snapshots)
    rep.light_hint = report.light_hint(context.scene, target.engine)
    rep.ambient_hint = report.ambient_hint(context.scene, target.engine)
    if target.mode == 'FOLDER':
        files.write_bytes(os.path.join(os.path.dirname(target.root), "README.txt"),
                          report.readme_text(rep).encode("utf-8"))
    report.write_text(rep)
    return rep
