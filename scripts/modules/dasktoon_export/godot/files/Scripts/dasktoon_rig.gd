# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# DaskToon's face and bend fixes in Godot, a modifier of the character's Skeleton3D that runs after the animation and the
# sway (docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md, wave 3). DaskToon's import script adds it and
# fills it from <model>.dasktoon.json; it does what DaskToon's Unity scripts do:
# - bend fixes (DaskToonCorrective): knees, elbows, hips and shoulders have blend shapes that keep the joint round as it
#   bends; their weights follow the pose. The child bone's swing from rest, seen from its parent, splits into the bend
#   along the fix's arc and the swing off it; the weight rises from start to angle, falls back to 0 at end when a deeper
#   fix follows (end 0: it stays) and fades over reach off the arc.
# - flat eyes (DaskToonFlatEye): the iris drawn on the face slides on its UVs as its eye bone turns, by
#   (-range * gaze.left, -range * gaze.up).
# - 2D mouths (DaskToonMouthAtlas): the material shows one cell of its atlas, rows x columns from the top left; the cell
#   is the Y scale of the bone MouthCell minus 1.
# The UVs move through the uv_transform of DaskToon's shaders, on a copy of the material made for this character.
# It also puts the sway's collider capsules along their bones: Godot saves a capsule's offset only once it has found the
# skeleton, which it has not while it imports the model.
# Written by DaskToon Engine Export; exporting again replaces it.
extends SkeletonModifier3D

# {shape, parent, child, target: [left, up, front], angle, start, end, reach}
@export var fixes: Array = []
# {mesh: NodePath, surface, side, range}
@export var flat_eyes: Array = []
# {mesh: NodePath, surface, rows, columns, bone}
@export var mouths: Array = []
# {node: NodePath of a SpringBoneCollision3D, offset: Vector3}
@export var colliders: Array = []

var _ready_fixes = []
var _ready_eyes = []
var _ready_mouths = []
var _set_up = false
var _last_frame = -1


func _ready():
	for collider in colliders:
		var node = get_node_or_null(collider["node"])
		if node:
			node.position_offset = collider["offset"]


func _process_modification_with_delta(_delta):
	apply()


func _process_modification():
	apply()


func _bone(skeleton, name):
	return skeleton.find_bone(name) if name else -1


func _rest_basis(skeleton, bone):
	return skeleton.get_bone_global_rest(bone).basis.orthonormalized()


# The child's frame in its parent bone's frame, from the local poses (or rests) of the bones between them: the local
# poses are what the animation sets, the global poses are worked out later.
func _in_parent(skeleton, parent, child, rest = false):
	var basis = Basis()
	var bone = child
	while bone >= 0 and bone != parent:
		basis = (skeleton.get_bone_rest(bone).basis if rest else skeleton.get_bone_pose(bone).basis) * basis
		bone = skeleton.get_bone_parent(bone)
	return basis.orthonormalized()


# The material of a surface, copied for this character so its uv_transform is its own.
func _own_material(mesh, surface):
	if mesh == null or surface < 0 or surface >= mesh.get_surface_override_material_count():
		return null
	var material = mesh.get_active_material(surface)
	if not material is ShaderMaterial:
		return null
	material = material.duplicate()
	mesh.set_surface_override_material(surface, material)
	return material


func _meshes_with(node, shape, out):
	if node is MeshInstance3D and node.mesh:
		var index = node.find_blend_shape_by_name(shape)
		if index >= 0:
			out.append([node, index])
	for child in node.get_children():
		_meshes_with(child, shape, out)


func _setup(skeleton):
	_set_up = true
	var root = owner if owner else skeleton
	# The character's frame, from the same bones as in DaskToon: up from the hips to the head, left from the right leg
	# to the left one, front = left x up.
	var hips = _bone(skeleton, "Hips")
	var head = _bone(skeleton, "Head")
	var left_leg = _bone(skeleton, "LeftUpperLeg")
	var right_leg = _bone(skeleton, "RightUpperLeg")
	if hips >= 0 and head >= 0 and left_leg >= 0 and right_leg >= 0:
		var up = (skeleton.get_bone_global_rest(head).origin - skeleton.get_bone_global_rest(hips).origin).normalized()
		var side = skeleton.get_bone_global_rest(left_leg).origin - skeleton.get_bone_global_rest(right_leg).origin
		var left = (side - up * side.dot(up)).normalized()
		var front = left.cross(up)
		for fix in fixes:
			var parent = _bone(skeleton, fix.get("parent", ""))
			var child = _bone(skeleton, fix.get("child", ""))
			var t = fix.get("target", [])
			if parent < 0 or child < 0 or t.size() != 3:
				continue
			var to_parent = _rest_basis(skeleton, parent).inverse()
			var target = to_parent * (left * t[0] + up * t[1] + front * t[2]).normalized()
			var rest = _in_parent(skeleton, parent, child, true).y.normalized()
			var along = rest.cross(target)
			if along.length_squared() < 1e-12:
				continue
			along = along.normalized()
			var meshes = []
			_meshes_with(root, fix["shape"], meshes)
			if meshes.is_empty():
				continue
			_ready_fixes.append({"parent": parent, "child": child, "rest": rest, "along": along,
					"across": rest.cross(along), "angle": rest.angle_to(target), "start": float(fix.get("start", 0.0)),
					"end": float(fix.get("end", 0.0)), "reach": float(fix.get("reach", 0.0)), "meshes": meshes})
	var left_eye = _bone(skeleton, "LeftEye")
	var right_eye = _bone(skeleton, "RightEye")
	for eye in flat_eyes:
		if left_eye < 0 or right_eye < 0:
			break
		var bone = right_eye if eye.get("side", "LEFT") == "RIGHT" else left_eye
		var material = _own_material(get_node_or_null(eye["mesh"]), int(eye.get("surface", 0)))
		if material == null:
			continue
		# The character's left (from its right eye to its left) and up, in the eye's rest frame.
		var to_eye = _rest_basis(skeleton, bone).inverse()
		var across = skeleton.get_bone_global_rest(left_eye).origin - skeleton.get_bone_global_rest(right_eye).origin
		_ready_eyes.append({"bone": bone, "material": material, "range": float(eye.get("range", 0.1)),
				"rest": skeleton.get_bone_rest(bone).basis.get_rotation_quaternion(),
				"left": (to_eye * across).normalized(), "up": (to_eye * Vector3.UP).normalized()})
	for mouth in mouths:
		var bone = _bone(skeleton, mouth.get("bone", ""))
		var material = _own_material(get_node_or_null(mouth["mesh"]), int(mouth.get("surface", 0)))
		if bone < 0 or material == null:
			continue
		_ready_mouths.append({"bone": bone, "material": material, "rows": max(int(mouth.get("rows", 1)), 1),
				"columns": max(int(mouth.get("columns", 1)), 1)})


# The weight (0 to 1) of a fix for the child's direction `now`, in the parent's frame.
static func weight(fix, now):
	var normal = fix["rest"].cross(now)
	if normal.length_squared() < 1e-12 or fix["angle"] <= 0.0:
		return 0.0
	var turn = fix["rest"].angle_to(now)
	var swing = sin(turn / 2.0) * normal.normalized()  # the swing quaternion's vector part
	var bend = 2.0 * asin(clamp(swing.dot(fix["along"]), -1.0, 1.0))
	var off = 2.0 * asin(clamp(swing.dot(fix["across"]), -1.0, 1.0))
	var rise = clamp((bend - fix["start"]) / (fix["angle"] - fix["start"]), 0.0, 1.0) if fix["angle"] > fix["start"] \
			else 1.0
	var fall = clamp((fix["end"] - bend) / (fix["end"] - fix["angle"]), 0.0, 1.0) if fix["end"] > fix["angle"] \
			else 1.0
	var reach = fix["reach"] if fix["reach"] > 0.0 else fix["angle"]
	return rise * fall * clamp(1.0 - abs(off) / reach, 0.0, 1.0)


# The UV offset of a flat eye for its eye bone's turn now.
func eye_offset(eye, skeleton):
	var turn = eye["rest"].inverse() * skeleton.get_bone_pose_rotation(eye["bone"])
	var gaze = turn * Vector3.UP  # a bone's +Y runs along it, as in DaskToon
	return Vector2(-eye["range"] * gaze.dot(eye["left"]), -eye["range"] * gaze.dot(eye["up"]))


# (scale u, scale v, offset u, offset v) placing a mouth's 0 to 1 UVs in the cell its bone shows now.
func mouth_transform(mouth, skeleton):
	var count = mouth["rows"] * mouth["columns"]
	var cell = clamp(int(round(skeleton.get_bone_pose_scale(mouth["bone"]).y - 1.0)), 0, max(count - 1, 0))
	var column = cell % mouth["columns"]
	var row = cell / mouth["columns"]
	return Vector4(1.0 / mouth["columns"], 1.0 / mouth["rows"], float(column) / mouth["columns"],
			float(mouth["rows"] - 1 - row) / mouth["rows"])


func _skeleton():
	var skeleton = get_skeleton()
	if skeleton == null and get_parent() is Skeleton3D:
		skeleton = get_parent()  # Godot finds it only once the modifier has run
	return skeleton


func apply(force = false):
	var skeleton = _skeleton()
	if skeleton == null:
		return
	var frame = Engine.get_process_frames()
	if frame == _last_frame and not force:
		return  # both kinds of modification callback in one frame
	_last_frame = frame
	if not _set_up:
		_setup(skeleton)
	for fix in _ready_fixes:
		var value = weight(fix, _in_parent(skeleton, fix["parent"], fix["child"]).y.normalized())
		for found in fix["meshes"]:
			found[0].set_blend_shape_value(found[1], value)
	for eye in _ready_eyes:
		var offset = eye_offset(eye, skeleton)
		eye["material"].set_shader_parameter("uv_transform", Vector4(1.0, 1.0, offset.x, offset.y))
	for mouth in _ready_mouths:
		mouth["material"].set_shader_parameter("uv_transform", mouth_transform(mouth, skeleton))
