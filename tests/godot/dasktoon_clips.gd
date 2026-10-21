# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run by tests/python/dasktoon_godot_clips_test.py: reports every animation of a DaskToon model as Godot imported it
# (length, loop, the interpolations of its tracks) with one bone's position and one shape key's value on every frame.
extends SceneTree


func _player(node):
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var found = _player(child)
		if found:
			return found
	return null


func _track(animation, suffix, type):
	for t in animation.get_track_count():
		if animation.track_get_type(t) == type and str(animation.track_get_path(t)).ends_with(suffix):
			return t
	return -1


func _init():
	var data = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var scene = load(data["model"]).instantiate()
	var player = _player(scene)
	if player == null:
		print("DT_RESULT ", JSON.stringify({"ok": false, "error": "no AnimationPlayer"}))
		scene.free()
		quit()
		return
	var out = {}
	for name in player.get_animation_list():
		var animation = player.get_animation(name)
		var interpolations = {}
		for t in animation.get_track_count():
			interpolations[animation.track_get_interpolation_type(t)] = true
		var frames = int(round(animation.length * float(data.get("fps", 24.0)))) + 1
		var bone = []
		var shape = []
		var bone_track = _track(animation, ":" + data["bone"], Animation.TYPE_POSITION_3D)
		var shape_track = _track(animation, ":" + data["shape"], Animation.TYPE_BLEND_SHAPE)
		for k in frames:
			var time = k / float(data.get("fps", 24.0))
			if bone_track >= 0:
				var p = animation.position_track_interpolate(bone_track, time)
				bone.append([p.x, p.y, p.z])
			if shape_track >= 0:
				shape.append(animation.blend_shape_track_interpolate(shape_track, time))
		var bone_interpolation = animation.track_get_interpolation_type(bone_track) if bone_track >= 0 else -1
		out[str(name)] = {"length": animation.length, "loop": animation.loop_mode,
				"interpolation": interpolations.keys(), "bone_interpolation": bone_interpolation, "bone": bone,
				"shape": shape}
	print("DT_RESULT ", JSON.stringify({"ok": true, "clips": out}))
	scene.free()
	quit()
