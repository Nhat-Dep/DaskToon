# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# DaskToon's illustration finish over the 3D view (<model>_finish.tscn): keeps the Light Gradient's light_direction on
# the side the Sun shines from, as the camera sees it (scripts/modules/dasktoon_finish/sun.py), every frame. Written by
# DaskToon Engine Export.
extends ColorRect

# Follow Sun: the first DirectionalLight3D; off, the light comes from `gradient_angle` (radians; 90 degrees: the top).
@export var gradient_auto = true
@export var gradient_angle = PI / 2.0


func _sun(node):
	if node is DirectionalLight3D and node.visible:
		return node
	for child in node.get_children():
		var found = _sun(child)
		if found:
			return found
	return null


func _process(_delta):
	var direction = Vector2(cos(gradient_angle), sin(gradient_angle))
	var camera = get_viewport().get_camera_3d()
	var sun = _sun(get_viewport()) if gradient_auto else null
	if camera and sun:
		# A light shines along its -Z: the Sun lies along +Z. In the camera's frame x is right and y is up.
		var local = camera.global_transform.basis.inverse() * sun.global_transform.basis.z
		var flat = Vector2(local.x, local.y)
		direction = flat.normalized() if flat.length() > 1e-6 else Vector2(0.0, 1.0)
	material.set_shader_parameter("light_direction", direction)
