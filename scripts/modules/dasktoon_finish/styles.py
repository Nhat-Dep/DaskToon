# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Styles of the illustration finish (spec section 5): built-in starting points, and the user's own, each a JSON file
in DaskToon's config folder (dasktoon/finish_styles; DASKTOON_FINISH_STYLES_DIR moves it), shared by every file. A
style holds every setting; one written before a setting existed gets its default."""

import json
import os
import re

import bpy
from bpy.app.translations import pgettext_n as n_

from . import settings

VERSION = 1

# Each built-in style: the settings it changes from the defaults.
BUILT_IN = {
    n_("Default"): {},
    n_("Early Morning"): {
        "shadow_tint": (0.70, 0.72, 0.95), "light_tint": (1.0, 0.90, 0.75), "grade_strength": 0.35,
        "saturation": 1.05, "contrast": 0.0,
        "haze_color": (0.85, 0.88, 0.95), "haze_strength": 0.6,
        "glow_threshold": 0.4, "glow_size": 0.04, "glow_strength": 0.45, "rays_strength": 0.3,
        "gradient_light": (1.0, 0.92, 0.75), "gradient_dark": (0.60, 0.68, 0.90), "gradient_strength": 0.25,
        "vignette_strength": 0.15,
    },
    n_("Sunset"): {
        "shadow_tint": (0.55, 0.40, 0.80), "light_tint": (1.0, 0.72, 0.45), "grade_strength": 0.6,
        "saturation": 1.25, "contrast": 0.1,
        "haze_color": (0.95, 0.65, 0.55), "haze_strength": 0.5,
        "glow_threshold": 0.5, "glow_strength": 0.45, "rays_length": 0.4, "rays_strength": 0.6,
        "gradient_light": (1.0, 0.60, 0.35), "gradient_dark": (0.45, 0.30, 0.70), "gradient_strength": 0.45,
        "vignette_color": (0.25, 0.08, 0.20), "vignette_strength": 0.35,
    },
    n_("Night"): {
        "shadow_tint": (0.35, 0.40, 0.75), "light_tint": (0.80, 0.90, 1.0), "grade_strength": 0.6,
        "saturation": 0.9, "contrast": 0.12,
        "haze_color": (0.20, 0.25, 0.45), "haze_strength": 0.5, "haze_sky": 0.3,
        "glow_threshold": 0.65, "glow_size": 0.05, "glow_strength": 0.55, "rays": False,
        "gradient_light": (0.70, 0.80, 1.0), "gradient_dark": (0.15, 0.15, 0.40), "gradient_strength": 0.4,
        "vignette_size": 0.6, "vignette_color": (0.02, 0.02, 0.10), "vignette_strength": 0.5,
    },
    n_("Watercolor"): {
        "grade_strength": 0.3, "saturation": 0.95, "contrast": -0.1,
        "strokes": True, "stroke_size": 0.006, "stroke_sharpness": 0.3,
        "haze_color": (0.92, 0.92, 0.90), "haze_strength": 0.4,
        "glow_strength": 0.2, "rays": False, "aberration": False,
        "vignette_strength": 0.15, "paper_scale": 0.6, "paper_strength": 0.35,
    },
}


def user_styles_dir(create=False):
    override = os.environ.get("DASKTOON_FINISH_STYLES_DIR")
    if override:
        if create:
            os.makedirs(override, exist_ok=True)
        return override
    return bpy.utils.user_resource('CONFIG', path=os.path.join("dasktoon", "finish_styles"), create=create)


def _file_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() + ".json"


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("settings"), dict) else None


def _user_files():
    """{style name: file path} of the user's styles."""
    folder = user_styles_dir()
    found = {}
    if folder and os.path.isdir(folder):
        for entry in sorted(os.listdir(folder)):
            if entry.endswith(".json"):
                path = os.path.join(folder, entry)
                data = _read(path)
                if data is not None:
                    found[str(data.get("name") or entry[:-5])] = path
    return found


def user_style_names():
    return sorted(_user_files())


def _clean(values):
    """`values` over the defaults: unknown keys dropped, colors as tuples."""
    out = settings.defaults()
    for key, value in values.items():
        setting = settings.BY_KEY.get(key)
        if setting is None:
            continue
        out[key] = tuple(value) if setting.kind == 'COLOR' else value
    return out


def style_values(name):
    """Every setting of the style `name` (built-in first), or None when there is none."""
    if name in BUILT_IN:
        return _clean(BUILT_IN[name])
    path = _user_files().get(name)
    data = _read(path) if path is not None else None
    return None if data is None else _clean(data["settings"])


def save(name, values):
    """Write the user style `name`; returns its file."""
    path = os.path.join(user_styles_dir(create=True), _file_name(name))
    data = {"name": name, "version": VERSION,
            "settings": {key: list(value) if isinstance(value, tuple) else value for key, value in values.items()}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def delete(name):
    path = _user_files().get(name)
    if path is not None:
        os.remove(path)
