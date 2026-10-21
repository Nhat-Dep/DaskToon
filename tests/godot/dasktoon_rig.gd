# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run by tests/python/dasktoon_godot_rig_test.py: loads a DaskToon model as Godot imported it and reports its sway
# (SpringBoneSimulator3D and its colliders) and what DaskToon's modifier does for given poses: bend fix weights, the flat
# eye's UV offset, the 2D mouth's cell; with a clip, MouthCell's scale in it.
extends SceneTree


func _find(node, type, name = ""):
	if is_instance_of(node, type) and (name == "" or str(node.name) == name):
		return node
	for child in node.get_children():
		var found = _find(child, type, name)
		if found:
			return found
	return null


func _all(node, type, out):
	if is_instance_of(node, type):
		out.append(node)
	for child in node.get_children():
		_all(child, type, out)
	return out


func _excluded(sway, setting):
	var out = []
	for j in sway.get_exclude_collision_count(setting):
		out.append(str(sway.get_node(sway.get_exclude_collision_path(setting, j)).bone_name))
	return out


func _vec(a):
	return Vector3(a[0], a[1], a[2])


# The child bone turned (from rest) so that its +Y points along `direction`, a direction of the skeleton's space.
func _point(skeleton, bone, direction):
	var rest = skeleton.get_bone_global_rest(bone).basis.orthonormalized()
	var turned = Basis(Quaternion(rest.y, direction.normalized())) * rest
	var parent = skeleton.get_bone_parent(bone)
	# The other bones are at rest.
	var parent_basis = skeleton.get_bone_global_rest(parent).basis.orthonormalized() if parent >= 0 else Basis()
	skeleton.set_bone_pose_rotation(bone, (parent_basis.inverse() * turned).get_rotation_quaternion())


var data
var scene
var frames = 0


func _init():
	data = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	scene = load(data["model"]).instantiate()
	root.add_child(scene)


# The scene enters the tree (and its nodes run _ready) once the main loop runs: check two frames in.
func _process(_delta):
	frames += 1
	if frames == 2:
		_check()
	return false


func _check():
	var skeleton = _find(scene, Skeleton3D)
	var result = {"ok": true}
	var sway = _find(scene, SpringBoneSimulator3D)
	result["sway"] = sway != null
	if sway:
		var settings = []
		for i in sway.setting_count:
			settings.append({"root": sway.get_root_bone_name(i), "end": sway.get_end_bone_name(i),
					"stiffness": sway.get_stiffness(i), "drag": sway.get_drag(i), "gravity": sway.get_gravity(i),
					"radius": sway.get_radius(i), "length": sway.get_end_bone_length(i),
					"collisions": sway.are_all_child_collisions_enabled(i), "exclude": _excluded(sway, i)})
		result["settings"] = settings
		var colliders = []
		for capsule in _all(sway, SpringBoneCollisionCapsule3D, []):
			colliders.append({"bone": capsule.bone_name, "radius": capsule.radius, "length": capsule.mid_height,
					"offset": capsule.position_offset.y})
		result["colliders"] = colliders
	var modifier = _find(scene, SkeletonModifier3D, "DaskToonRig")
	result["modifier"] = modifier != null
	if modifier and skeleton:
		modifier.apply(true)
		# The character's frame, as the modifier builds it.
		var hips = skeleton.find_bone("Hips")
		var up = (skeleton.get_bone_global_rest(skeleton.find_bone("Head")).origin
				- skeleton.get_bone_global_rest(hips).origin).normalized()
		var side = skeleton.get_bone_global_rest(skeleton.find_bone("LeftUpperLeg")).origin \
				- skeleton.get_bone_global_rest(skeleton.find_bone("RightUpperLeg")).origin
		var left = (side - up * side.dot(up)).normalized()
		var front = left.cross(up)
		var weights = []
		for pose in data.get("poses", []):
			skeleton.reset_bone_poses()
			var d = pose["direction"]
			_point(skeleton, skeleton.find_bone(pose["child"]), left * d[0] + up * d[1] + front * d[2])
			modifier.apply(true)
			var mesh = null
			var value = -1.0
			for candidate in _all(scene, MeshInstance3D, []):
				var index = candidate.find_blend_shape_by_name(pose["shape"]) if candidate.mesh else -1
				if index >= 0:
					value = candidate.get_blend_shape_value(index)
					mesh = str(candidate.name)
			weights.append(value)
			result["fixMesh"] = mesh
		result["weights"] = weights
		skeleton.reset_bone_poses()
		modifier.apply(true)
		result["fixCount"] = modifier._ready_fixes.size()
		if not modifier._ready_eyes.is_empty():
			var eye = modifier._ready_eyes[0]
			var bone = eye["bone"]
			result["eyeBone"] = skeleton.get_bone_name(bone)
			result["eyeMesh"] = str(modifier.get_node(modifier.flat_eyes[0]["mesh"]).name)
			var rest = skeleton.get_bone_global_rest(bone).basis.orthonormalized()
			var gaze = rest.y
			var to_left = (skeleton.get_bone_global_rest(skeleton.find_bone("LeftEye")).origin
					- skeleton.get_bone_global_rest(skeleton.find_bone("RightEye")).origin).normalized()
			var offsets = {}
			for turn in [["left", to_left, 20.0], ["up", Vector3.UP, 10.0], ["rest", gaze, 0.0]]:
				skeleton.reset_bone_poses()
				var axis = gaze.cross(turn[1])
				var direction = gaze if axis.length_squared() < 1e-12 \
						else gaze.rotated(axis.normalized(), deg_to_rad(turn[2]))
				_point(skeleton, bone, direction)
				modifier.apply(true)
				var t = eye["material"].get_shader_parameter("uv_transform")
				offsets[turn[0]] = [t.z, t.w]
			result["eye"] = offsets
		if not modifier._ready_mouths.is_empty():
			var mouth = modifier._ready_mouths[0]
			skeleton.reset_bone_poses()
			modifier.apply(true)
			var rest = modifier.mouth_transform(mouth, skeleton)
			result["mouthRest"] = [rest.x, rest.y, rest.z, rest.w]
			skeleton.set_bone_pose_scale(mouth["bone"], Vector3(1.0, 4.0, 1.0))
			modifier.apply(true)
			var t = mouth["material"].get_shader_parameter("uv_transform")
			result["mouth"] = [t.x, t.y, t.z, t.w]
			result["mouthBone"] = skeleton.get_bone_name(mouth["bone"])
	if data.has("clip"):
		var player = _find(scene, AnimationPlayer)
		if player and player.has_animation(data["clip"]):
			var animation = player.get_animation(data["clip"])
			for t in animation.get_track_count():
				if animation.track_get_type(t) == Animation.TYPE_SCALE_3D \
						and str(animation.track_get_path(t)).ends_with(":MouthCell"):
					result["cellScale"] = animation.scale_track_interpolate(t, float(data["cellTime"])).y
	print("DT_RESULT ", JSON.stringify(result))
	quit()
