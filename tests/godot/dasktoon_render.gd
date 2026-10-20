# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run by tests/python/dasktoon_godot_render_test.py: draws each case of an exported DaskToon model alone, with an
# orthographic camera and one directional light, and saves each picture as PNG.
extends SceneTree

var data
var viewport
var camera
var meshes = {}
var index = -1
var wait = 0
var outputs = {}


func _vec(a):
	return Vector3(a[0], a[1], a[2])


func _collect(node):
	if node is MeshInstance3D:
		meshes[str(node.name)] = node
	for child in node.get_children():
		_collect(child)


func _init():
	data = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	viewport = SubViewport.new()
	viewport.size = Vector2i(int(data["resolution"]), int(data["resolution"]))
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.own_world_3d = true
	root.add_child(viewport)
	var model = load(data["model"]).instantiate()
	viewport.add_child(model)
	_collect(model)
	var env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = float(data["orthoSize"])
	camera.near = 0.05
	camera.far = 100.0
	camera.environment = env
	viewport.add_child(camera)
	var light = DirectionalLight3D.new()
	var c = data["lightColor"]
	light.light_color = Color(c[0], c[1], c[2])
	light.light_energy = float(data["lightEnergy"])
	light.shadow_enabled = false
	viewport.add_child(light)
	var towards = _vec(data["lightDir"]).normalized()
	light.look_at_from_position(towards, Vector3.ZERO, Vector3.FORWARD if abs(towards.y) > 0.99 else Vector3.UP)


func _process(_delta):
	if wait > 0:
		wait -= 1
		return false
	var cases = data["cases"]
	if index >= 0:
		var path = "%s/%s.png" % [data["outDir"], cases[index]["name"]]
		viewport.get_texture().get_image().save_png(path)
		outputs[cases[index]["name"]] = path
	index += 1
	if index >= cases.size():
		print("DT_RESULT ", JSON.stringify({"ok": true, "outputs": outputs}))
		quit()
		return true
	var shown = cases[index]["obj"]
	for name in meshes:
		meshes[name].visible = name == shown
	camera.position = _vec(cases[index]["camPos"])
	wait = 4
	return false
