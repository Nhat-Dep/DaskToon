# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's illustration finish for Godot (Godot spec, 2026-10-21): the layers that change each pixel's colour
(Shadow and Light Tint, Light Gradient, Saturation and Contrast, Vignette) as a screen layer to add to a Godot scene,
<model>_finish.tscn, with the scene's settings in <model>_finish.tres. The other layers blur or read the depth; Godot
does not get them, and the report names those that are on."""

import os

from . import files, materials

SHADER = "dasktoon_finish"
SCRIPT = files.RES_ROOT + "/Scripts/dasktoon_finish.gd"
PORTED = ("grade", "gradient", "color", "vignette")
SCENE = '''[gd_scene load_steps=3 format=3]

[ext_resource type="Material" path=%(material)s id="1_dt"]
[ext_resource type="Script" path=%(script)s id="2_dt"]

[node name="DaskToonFinish" type="CanvasLayer"]
layer = 100

[node name="Picture" type="ColorRect" parent="."]
material = ExtResource("1_dt")
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
mouse_filter = 2
script = ExtResource("2_dt")
gradient_auto = %(auto)s
gradient_angle = %(angle)s
'''


def _values(finish):
    from bl_ui import dasktoon_finish as finish_ui
    values = finish_ui.values_of(finish)
    out = {key + "_on": 1.0 if values[key] else 0.0 for key in PORTED}
    for key, value in values.items():
        out[key] = value
    computed = finish_ui.computed(finish.id_data)
    out["light_direction"] = tuple(computed["light_direction"][:2])
    return out


def write(scene, target, rep):
    """<name>_finish.tres and .tscn when the scene's finish is on; the report gets the scene and the layers left out."""
    from dasktoon_finish import settings
    finish = getattr(scene, "dasktoon_finish", None)
    if finish is None or not finish.enabled:
        return
    values = _values(finish)
    resource = materials._Resource()
    body = ['resource_name = "DaskToon Finish"', "shader = " + resource.ext_id("Shader", files.res(
        "%s/%s.gdshader" % (files.SHADERS, SHADER)))]
    body += resource.params(SHADER, values, {}, ext=".gdshader")
    rel = "%s/%s_finish" % (target.name, target.name)
    files.write_bytes(os.path.join(target.root, rel + ".tres"), resource.text(body).encode("utf-8"))
    scene_text = SCENE % {"material": materials.quoted(files.res(rel + ".tres")),
                          "script": materials.quoted(SCRIPT),
                          "auto": "true" if finish.gradient_auto else "false",
                          "angle": materials.number(finish.gradient_angle)}
    files.write_bytes(os.path.join(target.root, rel + ".tscn"), scene_text.encode("utf-8"))
    rep.finish = rel + ".tscn"
    rep.finish_left_out = [label for key, label, _group in settings.LAYERS
                           if key not in PORTED and getattr(finish, key)]
