# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""dasktoon_project.json: read, write, detect from a .blend path, list models, remember recent projects (spec 7)."""

import json
import os
from dataclasses import dataclass, field

from bpy.app.translations import pgettext_rpt as rpt_

PROJECT_FILE = "dasktoon_project.json"
PROJECT_VERSION = 1
MAX_RECENT = 8
RECENT_FILE = "recent_projects.json"
MAX_SCAN_DEPTH = 6
MAX_SCAN_DIRS = 2000
SKIP_DIRS = {"library", "temp", "logs", "obj", "usersettings", "node_modules", "__pycache__"}


@dataclass
class Project:
    folder: str
    name: str
    engines: list = field(default_factory=list)  # [{"engine": "UNITY_URP", "path": ...}]; this version uses the first

    @property
    def file(self):
        return os.path.join(self.folder, PROJECT_FILE)

    @property
    def engine(self):
        return self.engines[0]["engine"] if self.engines else ""

    @property
    def engine_path(self):
        return self.engines[0]["path"] if self.engines else ""


def load(path):
    """The project of a dasktoon_project.json file (or of the folder holding it)."""
    if os.path.isdir(path):
        path = os.path.join(path, PROJECT_FILE)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != PROJECT_VERSION:
        raise ValueError(rpt_("%s: project version %r is not supported") % (path, data.get("version")))
    return Project(os.path.dirname(os.path.abspath(path)), data.get("name", ""), list(data.get("engines", [])))


def save(project):
    os.makedirs(project.folder, exist_ok=True)
    data = {"version": PROJECT_VERSION, "name": project.name, "engines": project.engines}
    with open(project.file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_project(blend_path):
    """The project whose folder holds `blend_path` (any depth), or None."""
    if not blend_path:
        return None
    current = os.path.dirname(os.path.abspath(blend_path))
    while True:
        candidate = os.path.join(current, PROJECT_FILE)
        if os.path.isfile(candidate):
            try:
                return load(candidate)
            except (OSError, ValueError):
                return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def project_target(project, name):
    """PROJECT-mode export target inside the project's Unity project."""
    from dasktoon_export import targets
    root = os.path.join(os.path.normpath(project.engine_path), "Assets", "DaskToon")
    return targets.ExportTarget(project.engine, 'PROJECT', root, name, os.path.normpath(project.engine_path))


def install_project_shaders(project, force=False):
    from dasktoon_export import shaders_install
    warnings = []
    written = shaders_install.install_shaders(project_target(project, ""), warnings, force=force)
    return written, warnings


def create_project(name, folder, engine, engine_path, save_current=False):
    """Create the folder and dasktoon_project.json, install the shaders into the Unity project, optionally save
    the current .blend file into the project, and remember the project (spec 7)."""
    import bpy
    from dasktoon_export import safe_name, targets
    if engine not in targets.SUPPORTED_ENGINES:
        raise ValueError(rpt_("Engine %s is not supported yet") % engine)
    engine_path = os.path.abspath(engine_path)
    if not targets.is_unity_project(engine_path):
        raise ValueError(rpt_("%s is not a Unity project (it needs Assets/ and ProjectSettings/)") % engine_path)
    folder = os.path.abspath(folder)
    if os.path.exists(os.path.join(folder, PROJECT_FILE)):
        raise ValueError(rpt_("%s is already a DaskToon project") % folder)
    save_path = ""
    if save_current:
        save_path = os.path.join(folder, os.path.basename(bpy.data.filepath) or safe_name(name) + ".blend")
        current = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
        if os.path.exists(save_path) and os.path.normcase(save_path) != current:
            raise ValueError(rpt_("%s already has another file named %s: rename the current file or turn off "
                                  "Save Current File in Project") % (folder, os.path.basename(save_path)))
    project = Project(folder, name, [{"engine": engine, "path": engine_path.replace("\\", "/")}])
    save(project)
    install_project_shaders(project)
    if save_path:
        bpy.ops.wm.save_as_mainfile(filepath=save_path)
    add_recent(project.file)
    return project


def project_models(project):
    """Every .blend file of the project (sub-folders included); .blend1 backups and hidden folders are skipped.
    The panel calls this while drawing, so the walk is bounded: Unity's cache folders are skipped (a Unity project
    may live inside the project folder) and the walk stops at MAX_SCAN_DEPTH levels and MAX_SCAN_DIRS folders."""
    found = []
    base_depth = project.folder.rstrip("\\/").count(os.sep)
    visited = 0
    for root, dirs, files in os.walk(project.folder):
        visited += 1
        depth = root.rstrip("\\/").count(os.sep) - base_depth
        if depth >= MAX_SCAN_DEPTH or visited >= MAX_SCAN_DIRS:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.lower() not in SKIP_DIRS)
        found += [os.path.join(root, f) for f in sorted(files) if f.lower().endswith(".blend")]
    return found


def config_dir():
    override = os.environ.get("DASKTOON_CONFIG_DIR")
    if override:
        return override
    import bpy
    return bpy.utils.user_resource('CONFIG', path="dasktoon", create=True)


def recent_projects():
    """Project files opened or created lately, newest first, existing ones only."""
    try:
        with open(os.path.join(config_dir(), RECENT_FILE), encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError):
        return []
    return [p for p in items if isinstance(p, str) and os.path.isfile(p)][:MAX_RECENT]


def add_recent(project_file):
    project_file = os.path.abspath(project_file)
    items = [p for p in recent_projects() if os.path.normcase(p) != os.path.normcase(project_file)]
    items.insert(0, project_file)
    os.makedirs(config_dir(), exist_ok=True)
    with open(os.path.join(config_dir(), RECENT_FILE), "w", encoding="utf-8") as f:
        json.dump(items[:MAX_RECENT], f, ensure_ascii=False, indent=2)
