# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Runs Unity 6000.5 in batchmode on a throwaway URP project (spec 8). Never touches the user's own projects."""

import glob
import json
import os
import shutil
import subprocess
import tempfile

UNITY_VERSION = "6000.5.4f1"
DEFAULT_UNITY = r"C:\Program Files\Unity\Hub\Editor\6000.5.4f1\Editor\Unity.exe"
SKIP_REASON = "Unity %s not installed (set DASKTOON_UNITY)" % UNITY_VERSION
TESTS_UNITY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "unity")
SETUP_MARKER = os.path.join("ProjectSettings", "dt_setup_done")
MANIFEST = {"dependencies": {
    "com.unity.render-pipelines.universal": "17.5.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0",
}}


def unity_exe():
    path = os.environ.get("DASKTOON_UNITY", DEFAULT_UNITY)
    return path if os.path.isfile(path) else None


def project_dir():
    return os.environ.get("DASKTOON_UNITY_PROJECT") or os.path.join(tempfile.gettempdir(), "dasktoon_unity_test")


def _write_if_missing(path, text):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def ensure_project():
    """Create the test project once; the C# test scripts are refreshed on every call."""
    root = project_dir()
    # A ProjectVersion.txt written up front stops Unity from treating the folder as a new project and
    # replacing the manifest with its default template.
    _write_if_missing(os.path.join(root, "Packages", "manifest.json"), json.dumps(MANIFEST, indent=2))
    _write_if_missing(os.path.join(root, "ProjectSettings", "ProjectVersion.txt"),
                      "m_EditorVersion: %s\n" % UNITY_VERSION)
    editor_dir = os.path.join(root, "Assets", "Editor")
    os.makedirs(editor_dir, exist_ok=True)
    for source in glob.glob(os.path.join(TESTS_UNITY_DIR, "Editor", "*.cs")):
        shutil.copyfile(source, os.path.join(editor_dir, os.path.basename(source)))
    if not os.path.exists(os.path.join(root, SETUP_MARKER)):
        result = run_method("DaskToonTests.Setup")
        if not result.get("ok"):
            raise RuntimeError("Unity setup failed: %s" % result.get("error"))
        _write_if_missing(os.path.join(root, SETUP_MARKER), "ok\n")
    return root


def run_method(method, args=None, timeout=1800):
    """Run a static C# method in batchmode. It writes dt_result.json; that file is the verdict
    (Unity 6000.5 can crash while shutting down after a successful run)."""
    root = project_dir()
    result_path = os.path.join(root, "dt_result.json")
    args_path = os.path.join(root, "dt_args.json")
    for path in (result_path, args_path):
        if os.path.exists(path):
            os.remove(path)
    if args is not None:
        with open(args_path, "w", encoding="utf-8") as f:
            json.dump(args, f)
    log = os.path.join(root, "dt_unity_%s.log" % method.rsplit(".", 1)[-1])
    cmd = [unity_exe(), "-batchmode", "-projectPath", root, "-executeMethod", method, "-logFile", log]
    subprocess.run(cmd, timeout=timeout, check=False)
    if not os.path.exists(result_path):
        raise RuntimeError("Unity wrote no result for %s; see %s" % (method, log))
    with open(result_path, encoding="utf-8") as f:
        return json.load(f)
