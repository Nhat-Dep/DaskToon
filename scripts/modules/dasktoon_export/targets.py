# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where an export goes: straight into a Unity or Godot project (PROJECT) or into a folder to drag into Unity or copy
into a Godot project (FOLDER). Spec 4; Godot: docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md, 2."""

import os
from dataclasses import dataclass

from bpy.app.translations import pgettext_n as n_

ENGINES = (
    ('UNITY_URP', n_("Unity 6 (URP)"), n_("Unity 6, Universal Render Pipeline 17.5")),
    ('UNREAL_5', n_("Unreal 5 (coming soon)"), n_("Not supported yet")),
    ('GODOT_4', n_("Godot 4"), n_("Godot 4.4 or newer, Forward+ or Mobile renderer")),
)
SUPPORTED_ENGINES = {'UNITY_URP', 'GODOT_4'}
GODOT_PROJECT_FILE = "project.godot"
GODOT_FOLDER = "DaskToon"  # res://DaskToon, the folder every path in the exported files points into
TARGET_PROP = "dasktoon_engine_target"
UNTITLED = "Untitled"


@dataclass(frozen=True)
class ExportTarget:
    engine: str
    mode: str      # 'PROJECT' or 'FOLDER'
    root: str      # folder that receives Shaders/ and <name>/
    name: str      # model name: the .blend file name without extension
    project: str = ""


def is_unity_project(path):
    return os.path.isdir(os.path.join(path, "Assets")) and os.path.isdir(os.path.join(path, "ProjectSettings"))


def find_unity_project(path):
    """Walk up from `path`; the first folder holding both Assets/ and ProjectSettings/ is a Unity project."""
    current = os.path.abspath(path)
    while True:
        if is_unity_project(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def find_godot_project(path):
    """Walk up from `path`; the first folder holding project.godot is a Godot project."""
    current = os.path.abspath(path)
    while True:
        if os.path.isfile(os.path.join(current, GODOT_PROJECT_FILE)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def blend_name(filepath):
    if not filepath:
        return UNTITLED
    return os.path.splitext(os.path.basename(filepath))[0] or UNTITLED


def make_target(directory, name, engine='UNITY_URP'):
    if engine == 'GODOT_4':
        project = find_godot_project(directory)
        if project:
            return ExportTarget(engine, 'PROJECT', os.path.join(project, GODOT_FOLDER), name, project)
        return ExportTarget(engine, 'FOLDER', os.path.join(os.path.abspath(directory), name + "_Godot", GODOT_FOLDER),
                            name)
    project = find_unity_project(directory)
    if project:
        return ExportTarget(engine, 'PROJECT', os.path.join(project, "Assets", "DaskToon"), name, project)
    return ExportTarget(engine, 'FOLDER', os.path.join(os.path.abspath(directory), name + "_Unity"), name)


def remember_target(scene, directory, engine):
    scene[TARGET_PROP] = {"directory": directory, "engine": engine}


def remembered_target(scene):
    data = scene.get(TARGET_PROP)
    if data is None:
        return None
    data = data.to_dict() if hasattr(data, "to_dict") else dict(data)
    if not data.get("directory"):
        return None
    return data["directory"], data.get("engine", 'UNITY_URP')
