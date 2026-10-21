# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# DaskToon import script: Godot runs it after importing a model DaskToon Engine Export wrote (the model's .glb.import
# names it). It reads <model>.dasktoon.json beside the model and
# - puts the DaskToon materials on the surfaces whose glTF material has the same name;
# - sets the shape keys that were on in DaskToon (Godot leaves glTF's default weights out);
# - makes the looping clips loop and the clips with anime timing step from frame to frame;
# - gives the Skeleton3D a SpringBoneSimulator3D for the hair and skirts Godot sways (with a capsule on each collider
#   bone) and DaskToon's modifier (dasktoon_rig.gd) for the bend fixes, flat eyes and 2D mouths.
# Written by DaskToon Engine Export.
@tool
extends EditorScenePostImport

const RIG_SCRIPT = "res://DaskToon/Scripts/dasktoon_rig.gd"


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
		var path = folder.path_join(data["materials"][name])
		if FileAccess.file_exists(path):
			materials[name] = _material(path, name)
		else:
			push_warning("DaskToon: material %s not found" % path)
	_assign(scene, materials)
	_shapes(scene, data.get("shapes", {}))
	_clips(scene, data.get("clips", []))
	if typeof(data.get("rig")) == TYPE_DICTIONARY:
		_rig(scene, data["rig"])
	return scene


# The material file, by reference: Godot loads it when it opens the model. It is not loaded here: in a new project Godot
# imports the model before the textures, and a material loaded now would lose them.
func _material(path, name):
	if ResourceLoader.has_cached(path):
		return load(path)
	var reference = ShaderMaterial.new()
	reference.resource_name = name
	reference.set_path_cache(path)
	return reference


func _assign(node, materials):
	if node is MeshInstance3D and node.mesh:
		for i in node.mesh.get_surface_count():
			var current = node.mesh.surface_get_material(i)
			if current and materials.has(current.resource_name):
				node.mesh.surface_set_material(i, materials[current.resource_name])
	for child in node.get_children():
		_assign(child, materials)


func _shapes(node, shapes):
	if node is MeshInstance3D and node.mesh and shapes.has(str(node.name)):
		var values = shapes[str(node.name)]
		for shape in values:
			var index = node.find_blend_shape_by_name(shape)
			if index >= 0:
				node.set_blend_shape_value(index, values[shape])
	for child in node.get_children():
		_shapes(child, shapes)


# A looping clip loops; a clip with anime timing steps from frame to frame instead of sliding between its frames.
func _clips(node, clips):
	if node is AnimationPlayer:
		for clip in clips:
			if not node.has_animation(clip["name"]):
				continue
			var animation = node.get_animation(clip["name"])
			animation.loop_mode = Animation.LOOP_LINEAR if clip.get("loop", false) else Animation.LOOP_NONE
			if clip.get("stepped", false):
				for track in animation.get_track_count():
					animation.track_set_interpolation_type(track, Animation.INTERPOLATION_NEAREST)
	for child in node.get_children():
		_clips(child, clips)


func _find(node, name, type):
	if is_instance_of(node, type) and (name == "" or str(node.name) == name):
		return node
	for child in node.get_children():
		var found = _find(child, name, type)
		if found:
			return found
	return null


func _add(parent, node, scene):
	parent.add_child(node)
	node.owner = scene


# The surface of `mesh` whose material is named `material`, else `slot` (kept within the surfaces).
func _surface(mesh, material, slot):
	for i in mesh.mesh.get_surface_count():
		var current = mesh.mesh.surface_get_material(i)
		if current and current.resource_name == material:
			return i
	return clamp(int(slot), 0, max(mesh.mesh.get_surface_count() - 1, 0))


func _rig(scene, rig):
	var skeleton = _find(scene, "", Skeleton3D)
	if skeleton == null:
		return
	var capsules = []
	var chains = rig.get("chains", []).filter(func(chain): return chain.get("unity", "runtime") != "baked")
	if not chains.is_empty():
		var sway = SpringBoneSimulator3D.new()
		sway.name = "DaskToonSway"
		_add(skeleton, sway, scene)
		var by_bone = {}
		for collider in rig.get("colliders", []):
			# A capsule from the bone along its +Y for `length`.
			var capsule = SpringBoneCollisionCapsule3D.new()
			capsule.name = "Collider_" + collider["bone"]
			_add(sway, capsule, scene)
			capsule.bone_name = collider["bone"]
			capsule.radius = collider["radius"]
			capsule.mid_height = collider["length"]
			# Along the bone, from its head to its tail; DaskToon's modifier sets it again when the game runs (Godot
			# does not save it from here).
			capsule.position_offset = Vector3(0.0, collider["length"] / 2.0, 0.0)
			capsules.append({"node": capsule, "offset": capsule.position_offset})
			by_bone[collider["bone"]] = capsule
		sway.setting_count = chains.size()
		for i in chains.size():
			var chain = chains[i]
			var bones = chain["bones"]
			sway.set_root_bone_name(i, bones[0])
			sway.set_end_bone_name(i, bones[bones.size() - 1])
			# The last bone sways too: its tail, along its +Y, is the chain's end.
			sway.set_extend_end_bone(i, true)
			sway.set_end_bone_direction(i, SpringBoneSimulator3D.BONE_DIRECTION_PLUS_Y)
			sway.set_end_bone_length(i, chain["lengths"][chain["lengths"].size() - 1])
			sway.set_radius(i, chain["radius"])
			sway.set_stiffness(i, chain["stiffness"])
			sway.set_drag(i, chain["drag"])
			sway.set_gravity(i, chain["gravity"])
			sway.set_gravity_direction(i, Vector3.DOWN)
			sway.set_enable_all_child_collisions(i, true)
			# Not the capsules the chain starts in (Godot's spring bone throws such a chain far off).
			var inner = chain.get("exclude", []).filter(func(bone): return by_bone.has(bone))
			sway.set_exclude_collision_count(i, inner.size())
			for j in inner.size():
				sway.set_exclude_collision_path(i, j, sway.get_path_to(by_bone[inner[j]]))
	var eyes = []
	for eye in rig.get("flatEyes", []):
		var mesh = _find(scene, eye["object"], MeshInstance3D)
		if mesh:
			eyes.append({"mesh": mesh, "surface": _surface(mesh, eye["material"], eye["slot"]),
					"side": eye.get("side", "LEFT"), "range": eye.get("range", 0.1)})
	var mouths = []
	for mouth in rig.get("mouths", []):
		var mesh = _find(scene, mouth["object"], MeshInstance3D)
		if mesh:
			mouths.append({"mesh": mesh, "surface": _surface(mesh, mouth["material"], mouth["slot"]),
					"rows": mouth.get("rows", 1), "columns": mouth.get("columns", 1), "bone": mouth.get("bone", "")})
	var fixes = rig.get("correctives", [])
	if eyes.is_empty() and mouths.is_empty() and fixes.is_empty() and capsules.is_empty():
		return
	var modifier = load(RIG_SCRIPT).new()
	modifier.name = "DaskToonRig"
	_add(skeleton, modifier, scene)  # after the sway: it reads the final pose
	for entry in eyes + mouths:
		entry["mesh"] = modifier.get_path_to(entry["mesh"])
	for entry in capsules:
		entry["node"] = modifier.get_path_to(entry["node"])
	modifier.fixes = fixes
	modifier.flat_eyes = eyes
	modifier.mouths = mouths
	modifier.colliders = capsules
