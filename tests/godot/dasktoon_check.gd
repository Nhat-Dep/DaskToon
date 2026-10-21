# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run by tests/python/dasktoon_godot_harness.py: loads a DaskToon model as Godot imported it and reports the material of
# every surface, and how far DT_OutlineN decodes from DaskToon's smoothed normals in Godot's tangent frame.
extends SceneTree


func _params(material, names):
	var out = {}
	for name in names:
		var value = material.get_shader_parameter(name)
		if value is Resource:
			out[name] = value.resource_path
		elif value != null:
			out[name] = var_to_str(value)
	return out


func _material_info(material, names):
	if material == null:
		return {"material": ""}
	var info = {"material": material.resource_path, "name": material.resource_name, "class": material.get_class()}
	if material is ShaderMaterial:
		info["shader"] = material.shader.resource_path if material.shader else ""
		info["params"] = _params(material, names)
		var next = material.next_pass
		info["next_pass"] = next.shader.resource_path if next is ShaderMaterial and next.shader else ""
		if next is ShaderMaterial:
			info["next_params"] = _params(next, names)
	return info


func _shape_values(node, names, out):
	if node is MeshInstance3D and node.mesh:
		for name in names:
			var index = node.find_blend_shape_by_name(name)
			if index >= 0:
				out[str(node.name) + "/" + name] = node.get_blend_shape_value(index)
	for child in node.get_children():
		_shape_values(child, names, out)


func _collect(node, names, out):
	if node is MeshInstance3D and node.mesh:
		var surfaces = []
		for i in node.mesh.get_surface_count():
			surfaces.append(_material_info(node.get_active_material(i), names))
		out[str(node.name)] = surfaces
	for child in node.get_children():
		_collect(child, names, out)


func _find(node, name):
	if str(node.name) == name:
		return node
	for child in node.get_children():
		var found = _find(child, name)
		if found:
			return found
	return null


# Godot puts glTF's TEXCOORD_0 in UV, TEXCOORD_1 in UV2 and TEXCOORD_2 onwards two by two in CUSTOM0 to CUSTOM2.
func _channel(arrays, k, i, count):
	if k == 0:
		return arrays[Mesh.ARRAY_TEX_UV][i]
	if k == 1:
		return arrays[Mesh.ARRAY_TEX_UV2][i]
	var custom = arrays[Mesh.ARRAY_CUSTOM0 + int((k - 2) / 2)]
	var stride = int(custom.size() / count)
	var offset = i * stride + ((k - 2) % 2) * 2
	return Vector2(custom[offset], custom[offset + 1])


func _oct_decode(e):
	var n = Vector3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y))
	var t = max(-n.z, 0.0)
	n.x += -t if n.x >= 0.0 else t
	n.y += -t if n.y >= 0.0 else t
	return n.normalized()


func _key(p):
	return "%d,%d,%d" % [roundi(p.x * 1000.0), roundi(p.y * 1000.0), roundi(p.z * 1000.0)]


func _outline_normals(node, k, expected):
	var by_position = {}
	for e in expected:
		by_position[_key(Vector3(e.p[0], e.p[1], e.p[2]))] = Vector3(e.n[0], e.n[1], e.n[2])
	var matched = {}
	var worst = 0.0
	for s in node.mesh.get_surface_count():
		var arrays = node.mesh.surface_get_arrays(s)
		var vertices = arrays[Mesh.ARRAY_VERTEX]
		var normals = arrays[Mesh.ARRAY_NORMAL]
		var tangents = arrays[Mesh.ARRAY_TANGENT]
		for i in vertices.size():
			var key = _key(vertices[i])
			if not by_position.has(key):
				continue
			var ch = _channel(arrays, k, i, vertices.size())
			var nts = _oct_decode(Vector2(ch.x, 1.0 - ch.y))  # glTF stores V flipped
			var n = normals[i]
			var t = Vector3(tangents[i * 4], tangents[i * 4 + 1], tangents[i * 4 + 2])
			var b = n.cross(t) * tangents[i * 4 + 3]  # Godot's BINORMAL
			var direction = (t * nts.x + b * nts.y + n * nts.z).normalized()
			worst = max(worst, rad_to_deg(direction.angle_to(by_position[key])))
			matched[key] = true
	return {"matched": matched.size(), "vertices": by_position.size(), "maxNormalAngle": worst}


func _init():
	var data = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var packed = load(data["model"])
	if packed == null:
		print("DT_RESULT ", JSON.stringify({"ok": false, "error": "cannot load " + data["model"]}))
		quit()
		return
	var scene = packed.instantiate()
	var meshes = {}
	_collect(scene, data.get("params", []), meshes)
	var shapes = {}
	_shape_values(scene, data.get("shapes", []), shapes)
	var result = {"ok": true, "meshes": meshes, "shapes": shapes}
	if data.has("outline"):
		var outline = data["outline"]
		result["outline"] = _outline_normals(_find(scene, outline["mesh"]), int(outline["uv"]), outline["normals"])
	print("DT_RESULT ", JSON.stringify(result))
	scene.free()
	quit()
