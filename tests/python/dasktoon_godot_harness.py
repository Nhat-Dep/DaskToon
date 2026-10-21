# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Runs Godot 4 on a throwaway project (docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md). Never
touches the user's own Godot projects."""

import json
import os
import shutil
import subprocess
import tempfile

DEFAULT_GODOT = r"D:\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"
SKIP_REASON = "Godot 4 not found (set DASKTOON_GODOT to its console executable)"
TESTS_GODOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "godot")
RESULT_PREFIX = "DT_RESULT "
QUIT_AFTER = 5000  # frames: a test script that stops on an error does not reach quit(), and Godot would wait
PROJECT_FILE = 'config_version=5\n\n[application]\n\nconfig/name="DaskToonTest"\n'


def godot_exe():
    path = os.environ.get("DASKTOON_GODOT", DEFAULT_GODOT)
    return path if os.path.isfile(path) else None


def new_project(name="dasktoon_godot_test"):
    """An empty Godot project in the temp folder, made afresh (a project left by an earlier run would keep its
    imports)."""
    root = os.path.join(tempfile.gettempdir(), name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    with open(os.path.join(root, "project.godot"), "w", encoding="utf-8") as f:
        f.write(PROJECT_FILE)
    return root


def run(root, args, headless=True, timeout=900):
    """(exit code, everything Godot printed)."""
    command = [godot_exe()] + (["--headless"] if headless else []) + ["--path", root] + list(args)
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)
    return done.returncode, done.stdout + done.stderr


def import_project(root):
    """Import every file of the project, as the editor does when it opens it. Returns Godot's output."""
    return run(root, ["--import"])[1]


def run_script(root, script, data, headless=True):
    """Run tests/godot/<script>.gd as the main loop with `data` (JSON); returns (result dict, Godot's output). The
    script prints its result as one line starting with DT_RESULT."""
    folder = os.path.join(root, "dt_tests")
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(os.path.join(TESTS_GODOT_DIR, script + ".gd"), os.path.join(folder, script + ".gd"))
    args_path = os.path.join(folder, script + ".json")
    with open(args_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    _code, output = run(root, ["--quit-after", str(QUIT_AFTER), "--script", "res://dt_tests/%s.gd" % script, "--",
                               args_path], headless=headless)
    for line in output.splitlines():
        if line.startswith(RESULT_PREFIX):
            return json.loads(line[len(RESULT_PREFIX):]), output
    return {"ok": False, "error": "no result from Godot:\n" + output[-3000:]}, output


def shader_errors(output):
    """Lines of Godot's output that report a shader that does not compile."""
    lines = output.splitlines()
    return [line for i, line in enumerate(lines) if "SHADER ERROR" in line or "Shader compilation failed" in line
            or ("ERROR" in line and i + 1 < len(lines) and ".gdshader" in lines[i + 1])]
