# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export merges the meshes of a character into one (the user's choice, 2026-10-20): Unity gets one mesh with
every material, instead of one object per part. Only the export is merged; the file being worked on stays as it was.

The meshes the character's armature deforms (an Armature modifier on it) are copied, the UV map each renders with is
named UV_NAME (joined, UV maps of other names stay apart, and Unity reads only the first), and the copies are joined
into one named after the Body, which the FBX of the model and of every clip take instead. Shape keys join by name; each
joined key follows the original one by a driver, so the clips still carry the shapes' animation. Afterwards the copy
goes, and the originals keep their names."""

import contextlib

import bpy

UV_NAME = "UVMap"
EXPORT_SUFFIX = " (exporting)"  # the Body's name meanwhile: the merged mesh takes its name


def sources(objects):
    """The meshes among `objects` the character's armature deforms, the Body first; [] without exactly one armature or
    with fewer than two such meshes."""
    rigs = [obj for obj in objects if obj.type == 'ARMATURE']
    if len(rigs) != 1:
        return []
    rig = rigs[0]
    meshes = [obj for obj in objects if obj.type == 'MESH'
              and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)]
    if len(meshes) < 2:
        return []
    data = getattr(rig.data, "dasktoon_rig", None)
    body = next((part.object for part in (data.parts if data is not None else ())
                 if part.role == 'BODY' and part.scope == 'OBJECT' and part.object in meshes), None)
    body = body or max(meshes, key=lambda obj: len(obj.data.vertices))
    return [body] + [obj for obj in meshes if obj != body]


def _render_uv_named(mesh):
    layers = mesh.uv_layers
    render = next((layer for layer in layers if layer.active_render), None)
    if render is None:
        return
    other = layers.get(UV_NAME)
    if other is not None and other != render:
        other.name = UV_NAME + " (other)"
    render.name = UV_NAME


def _copy(context, obj):
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.animation_data_clear()  # the character's meshes move with the armature
    if copy.data.shape_keys is not None:
        copy.data.shape_keys.animation_data_clear()  # the drivers below give the values
    context.scene.collection.objects.link(copy)
    copy.hide_viewport = copy.hide_render = False
    copy.hide_set(False)
    _render_uv_named(copy.data)
    return copy


def _follow_shape_keys(joined, meshes):
    """Each shape key of `joined` follows the first original of that name, by a driver (the average of one value: no
    Python needed)."""
    key = joined.data.shape_keys
    if key is None:
        return
    for block in key.key_blocks:
        if block == key.reference_key:
            continue
        source = next((mesh.data.shape_keys for mesh in meshes if mesh.data.shape_keys is not None
                       and block.name in mesh.data.shape_keys.key_blocks), None)
        if source is None:
            continue
        original = source.key_blocks[block.name]
        block.slider_min, block.slider_max = original.slider_min, original.slider_max
        driver = block.driver_add("value").driver
        driver.type = 'AVERAGE'
        variable = driver.variables.new()
        variable.type = 'SINGLE_PROP'
        target = variable.targets[0]
        target.id_type = 'KEY'
        target.id = source
        target.data_path = 'key_blocks["%s"].value' % bpy.utils.escape_identifier(block.name)


def _remove(objects, meshes, keys):
    """Remove the copies: `objects` still there, then the `meshes` and shape `keys` they leave unused."""
    for obj in objects:
        bpy.data.objects.remove(obj)
    for mesh in meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for key in keys:
        try:
            if key.users == 0:
                bpy.data.shape_keys.remove(key)
        except ReferenceError:  # went with its mesh
            pass


@contextlib.contextmanager
def merged(context, objects):
    """Yields (`objects` with the character's meshes replaced by one merged copy, {original name: merged name}); the
    copy is removed afterwards. Nothing to merge: (`objects`, {})."""
    meshes = sources(objects)
    if not meshes:
        yield objects, {}
        return
    body, name = meshes[0], meshes[0].name
    copies, made_meshes, made_keys = [], [], []
    try:
        for obj in meshes:
            copies.append(_copy(context, obj))
            made_meshes.append(copies[-1].data)
        if any(obj.data.shape_keys is not None for obj in meshes) and copies[0].data.shape_keys is None:
            copies[0].shape_key_add(name="Basis", from_mix=False)  # so the join keeps the others' shapes
        made_keys = [copy.data.shape_keys for copy in copies if copy.data.shape_keys is not None]
        context.view_layer.update()
        with context.temp_override(active_object=copies[0], object=copies[0], selected_objects=copies,
                                   selected_editable_objects=copies):
            bpy.ops.object.join()
        joined = copies[0]
        copies = [joined]  # the join removed the others
        _follow_shape_keys(joined, meshes)
        renamed = {obj.name: name for obj in meshes}
        body.name = name + EXPORT_SUFFIX
        joined.name = name
        context.view_layer.update()
        yield [obj for obj in objects if obj not in meshes] + [joined], renamed
    finally:
        _remove(copies, made_meshes, made_keys)
        body.name = name
