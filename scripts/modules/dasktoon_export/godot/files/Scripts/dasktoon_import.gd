# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# DaskToon import script: Godot runs it after importing a model DaskToon Engine Export wrote (the model's .glb.import
# names it). It reads <model>.dasktoon.json beside the model and puts the DaskToon materials on the surfaces whose glTF
# material has the same name. Written by DaskToon Engine Export.
@tool
extends EditorScenePostImport


func _post_import(scene):
	var source = get_source_file()
	var data_path = source.get_basename() + ".dasktoon.json"
	if not FileAccess.file_exists(data_path):
		push_warning("DaskToon: %s not found; the model keeps its own materials" % data_path)
		return scene
	var data = JSON.parse_string(FileAccess.get_file_as_string(data_path))
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("DaskToon: %s cannot be read" % data_path)
		return scene
	var folder = source.get_base_dir()
	var materials = {}
	for name in data.get("materials", {}):
		var material = load(folder.path_join(data["materials"][name]))
		if material:
			materials[name] = material
		else:
			push_warning("DaskToon: material %s not found" % data["materials"][name])
	_assign(scene, materials)
	return scene


func _assign(node, materials):
	if node is MeshInstance3D and node.mesh:
		for i in node.mesh.get_surface_count():
			var current = node.mesh.surface_get_material(i)
			if current and materials.has(current.resource_name):
				node.mesh.surface_set_material(i, materials[current.resource_name])
	for child in node.get_children():
		_assign(child, materials)
