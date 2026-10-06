# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects on disk: dasktoon_project.json, the Models/ and Textures/ folders, the model list, and the user's
recent projects, recent models and settings (docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md,
section 7; docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections 3, 4, 11 and 12)."""

import json
import os
import re
from dataclasses import dataclass, field

from bpy.app.translations import pgettext_rpt as rpt_

PROJECT_FILE = "dasktoon_project.json"
PROJECT_VERSION = 1
MODELS_DIR = "Models"
TEXTURES_DIR = "Textures"
DEFAULT_LOCATION = "DaskToon Projects"
MAX_RECENT = 8
MAX_RECENT_MODELS = 10
RECENT_FILE = "recent_projects.json"
RECENT_MODELS_FILE = "recent_models.json"
SETTINGS_FILE = "settings.json"
MAX_SCAN_DEPTH = 6
MAX_SCAN_DIRS = 2000
SKIP_DIRS = {"library", "temp", "logs", "obj", "usersettings", "node_modules", "__pycache__"}
FORBIDDEN = '<>:"/\\|?*'


@dataclass
class Project:
    folder: str
    name: str
    engines: list = field(default_factory=list)  # [{"engine": "UNITY_URP", "path": ...}]; empty until Unity is linked

    @property
    def file(self):
        return os.path.join(self.folder, PROJECT_FILE)

    @property
    def engine(self):
        return self.engines[0]["engine"] if self.engines else ""

    @property
    def engine_path(self):
        return self.engines[0]["path"] if self.engines else ""

    @property
    def models_folder(self):
        return os.path.join(self.folder, MODELS_DIR)

    @property
    def textures_folder(self):
        return os.path.join(self.folder, TEXTURES_DIR)


def clean_name(name):
    """`name` usable as a folder or file name: the characters Windows refuses become "_" (workflow spec 12)."""
    cleaned = "".join("_" if c in FORBIDDEN or ord(c) < 32 else c for c in name).strip().rstrip(". ")
    if not cleaned:
        raise ValueError(rpt_("The name is empty"))
    return cleaned


def same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def is_inside(path, folder):
    """True when `path` is `folder` or lies somewhere under it."""
    path, folder = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    try:
        return os.path.commonpath([path, folder]) == folder
    except ValueError:  # another drive
        return False


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


def check_engine_path(engine, engine_path):
    """The absolute path of the game-engine project, or ValueError when DaskToon cannot export into it."""
    from dasktoon_export import targets
    if engine not in targets.SUPPORTED_ENGINES:
        raise ValueError(rpt_("Engine %s is not supported yet") % engine)
    engine_path = os.path.abspath(engine_path)
    if not targets.is_unity_project(engine_path):
        raise ValueError(rpt_("%s is not a Unity project (it needs Assets/ and ProjectSettings/)") % engine_path)
    return engine_path


def create_project(name, folder, engine_path="", engine='UNITY_URP'):
    """Create `folder` with dasktoon_project.json, Models/ and Textures/; link the Unity project at `engine_path` and
    install the shaders into it when one is given; remember the project. A folder that already holds files is fine (its
    .blend files become models); a folder that is already a project is refused (workflow spec 6, 12)."""
    folder = os.path.abspath(folder)
    if os.path.exists(os.path.join(folder, PROJECT_FILE)):
        raise ValueError(rpt_("%s is already a DaskToon project") % folder)
    engines = []
    if engine_path:
        engines = [{"engine": engine, "path": check_engine_path(engine, engine_path).replace("\\", "/")}]
    project = Project(folder, name, engines)
    save(project)
    os.makedirs(project.models_folder, exist_ok=True)
    os.makedirs(project.textures_folder, exist_ok=True)
    if engines:
        install_project_shaders(project)
    add_recent(project.file)
    return project


def link_engine(project, engine, engine_path):
    """Link the game-engine project at `engine_path` (an empty path unlinks) and save the project. The shaders are
    installed when the link is new or points somewhere else (workflow spec 11). Returns the shader warnings."""
    if not engine_path:
        project.engines = []
        save(project)
        return []
    path = check_engine_path(engine, engine_path).replace("\\", "/")
    changed = not project.engines or project.engine != engine or not same_path(project.engine_path, path)
    project.engines = [{"engine": engine, "path": path}]
    save(project)
    return install_project_shaders(project)[1] if changed else []


def project_models(project):
    """The project's .blend files: Models/ first by name, then the others by their path in the project (projects made
    before Models/ existed keep theirs at the top). .blend1 backups, hidden folders, Textures/ and Unity's cache folders
    are skipped. Menus call this while drawing, so the walk stops at MAX_SCAN_DEPTH levels and MAX_SCAN_DIRS folders."""
    found = []
    base_depth = project.folder.rstrip("\\/").count(os.sep)
    visited = 0
    for root, dirs, files in os.walk(project.folder):
        visited += 1
        depth = root.rstrip("\\/").count(os.sep) - base_depth
        if depth >= MAX_SCAN_DEPTH or visited >= MAX_SCAN_DIRS:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.lower() not in SKIP_DIRS
                             and not (depth == 0 and d.lower() == TEXTURES_DIR.lower()))
        found += [os.path.join(root, f) for f in files if f.lower().endswith(".blend")]
    models = os.path.normcase(project.models_folder)

    def order(path):
        in_models = os.path.normcase(os.path.dirname(path)) == models
        return 0 if in_models else 1, os.path.relpath(path, project.folder).replace(os.sep, "/").lower()

    return sorted(found, key=order)


def model_label(project, path):
    """How menus name a model: its name for Models/<name>.blend, else its path inside the project."""
    if os.path.normcase(os.path.dirname(os.path.abspath(path))) == os.path.normcase(project.models_folder):
        return os.path.splitext(os.path.basename(path))[0]
    return os.path.relpath(path, project.folder).replace(os.sep, "/")


def model_path(project, name):
    return os.path.join(project.models_folder, name + ".blend")


def model_exists(project, name):
    """True when Models/ already has <name>.blend, whatever the letter case (workflow spec 12)."""
    if not os.path.isdir(project.models_folder):
        return False
    wanted = (name + ".blend").lower()
    return any(entry.lower() == wanted for entry in os.listdir(project.models_folder))


def new_model_path(project, name):
    """Models/<clean name>.blend for a model that does not exist yet; Models/ is created when missing."""
    name = clean_name(name)
    if model_exists(project, name):
        raise ValueError(rpt_("The project already has a model named %s") % name)
    os.makedirs(project.models_folder, exist_ok=True)
    return model_path(project, name)


def free_model_name(project, base):
    """`base`, or `base`_1, `base`_2… when Models/ already has it: the name dialogs suggest."""
    try:
        base = clean_name(base)
    except ValueError:
        base = "Untitled"
    name, number = base, 0
    while model_exists(project, name):
        number += 1
        name = "%s_%d" % (base, number)
    return name


def incremental_path(path):
    """The next free file next to `path` for Save Incremental: Hero.blend gives Hero_001.blend, Hero_001.blend gives
    Hero_002.blend; a trailing number keeps its width (workflow spec 6)."""
    folder, stem = os.path.dirname(path), os.path.splitext(os.path.basename(path))[0]
    match = re.match(r"^(.*?)(\d+)$", stem)
    if match:
        head, number, width = match.group(1), int(match.group(2)), len(match.group(2))
    else:
        head, number, width = stem + "_", 0, 3
    while True:
        number += 1
        candidate = os.path.join(folder, "%s%0*d.blend" % (head, width, number))
        if not os.path.exists(candidate):
            return candidate


def config_dir():
    override = os.environ.get("DASKTOON_CONFIG_DIR")
    if override:
        return override
    import bpy
    return bpy.utils.user_resource('CONFIG', path="dasktoon", create=True)


def _read_json(name, default):
    try:
        with open(os.path.join(config_dir(), name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(name, data):
    os.makedirs(config_dir(), exist_ok=True)
    with open(os.path.join(config_dir(), name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _recent(name, limit):
    items = _read_json(name, [])
    if not isinstance(items, list):
        return []
    return [p for p in items if isinstance(p, str) and os.path.isfile(p)][:limit]


def _add_recent(name, limit, path):
    path = os.path.abspath(path)
    items = [p for p in _recent(name, limit) if os.path.normcase(p) != os.path.normcase(path)]
    items.insert(0, path)
    _write_json(name, items[:limit])


def recent_projects():
    """Project files opened or created lately, newest first, existing ones only."""
    return _recent(RECENT_FILE, MAX_RECENT)


def add_recent(project_file):
    _add_recent(RECENT_FILE, MAX_RECENT, project_file)


def recent_models():
    """Model files opened or saved lately, newest first, existing ones only (workflow spec 4)."""
    return _recent(RECENT_MODELS_FILE, MAX_RECENT_MODELS)


def add_recent_model(path):
    _add_recent(RECENT_MODELS_FILE, MAX_RECENT_MODELS, path)


def default_location():
    """Documents/DaskToon Projects (the home folder stands in when there is no Documents folder)."""
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents")
    return os.path.join(documents if os.path.isdir(documents) else home, DEFAULT_LOCATION)


def project_location():
    """Where New Project puts projects: the folder used last time when it still exists, else default_location()."""
    settings = _read_json(SETTINGS_FILE, {})
    location = settings.get("project_location", "") if isinstance(settings, dict) else ""
    return location if location and os.path.isdir(location) else default_location()


def set_project_location(folder):
    settings = _read_json(SETTINGS_FILE, {})
    if not isinstance(settings, dict):
        settings = {}
    settings["project_location"] = os.path.abspath(folder)
    _write_json(SETTINGS_FILE, settings)
