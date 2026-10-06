# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Window test of the project workflow (project workflow spec 14). It needs a screen, so it is not in the CMake list.
Run it with the bundled Python, which starts DaskToon and checks what only shows after DaskToon quits:

    "$PY" tests/python/dasktoon_project_window_test.py "$DT"

Inside DaskToon (event simulation, like tools/dasktoon_ui_screenshots.py) the steps press the real keys:
1. Ctrl+N opens DaskToon's New menu.
2. Ctrl+O opens DaskToon's file browser (dasktoon.open).
3. Ctrl+S on a draft opens Save to Project; Return saves it into Models/; the draft file is not touched.
4. Opening another model with unsaved changes: Save in the "save changes?" dialog saves this model, then opens the other.
5. The same dialog on a draft from outside any project: Save opens Save to Project and the opening stops.
6. Ctrl+Q with unsaved changes: Save saves the model into the project and DaskToon quits."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import types

try:
    import bpy
except ImportError:
    bpy = None

RESULT = "result.json"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_outside(exe):
    work = tempfile.mkdtemp(prefix="dt_window_")
    env = dict(os.environ, DASKTOON_CONFIG_DIR=os.path.join(work, "config"), DASKTOON_WINDOW_TEST=work)
    subprocess.call([exe, "--enable-event-simulate", "--factory-startup", "--python", os.path.abspath(__file__)],
                    env=env, timeout=600)
    result_path = os.path.join(work, RESULT)
    if not os.path.isfile(result_path):
        print("FAIL: DaskToon wrote no result (see its console output)")
        return 1
    with open(result_path, encoding="utf-8") as f:
        result = json.load(f)
    errors = list(result["errors"])
    if not result.get("quit_started"):
        errors.append("the quit step did not run")
    elif os.path.getmtime(result["model"]) <= result["model_mtime"]:
        errors.append("quitting with Save did not save %s" % result["model"])
    if sha256(result["draft"]) != result["draft_sha256"]:
        errors.append("the draft from outside the project was overwritten: %s" % result["draft"])
    for error in errors:
        print("FAIL:", error)
    print("OK" if not errors else "%d failure(s)" % len(errors))
    return 0 if not errors else 1


def steps(work):
    import datetime
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_simulate", "modules"))
    import easy_keys
    from bl_ui import dasktoon_project as projects
    from dasktoon_project import project as dtp

    def wait(seconds):
        return datetime.timedelta(seconds=seconds)

    errors = []
    result = {"errors": errors}

    def write_result():
        with open(os.path.join(work, RESULT), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def check(ok, message):
        if not ok:
            errors.append(message)

    ui = types.SimpleNamespace()

    def find_window():
        """The window, its event generator and its 3D Viewport. Opening a .blend file with its interface replaces the
        windows, so this runs again after every file read."""
        ui.win = bpy.context.window_manager.windows[0]
        ui.e = easy_keys.EventGenerate(ui.win)
        ui.view = next(a for a in ui.win.screen.areas if a.type == 'VIEW_3D')
        ui.region = next(r for r in ui.view.regions if r.type == 'WINDOW')
        ui.e.cursor_position_set(ui.view.x + ui.view.width // 2, ui.view.y + ui.view.height // 2, move=True)

    find_window()
    yield wait(1.0)
    ui.e.esc()  # a start screen shown before the preferences were set would take the keys
    yield wait(0.5)

    def change_something():
        """An edit the "save changes?" dialog knows about: an operator called from a script pushes no undo step, so
        push one, as a person's edit does."""
        with bpy.context.temp_override(window=ui.win, area=ui.view, region=ui.region):
            bpy.ops.object.empty_add()
            bpy.ops.ed.undo_push(message="DaskToon window test")
        check(bpy.data.is_dirty, "the test's change did not mark the file as changed")

    def open_model(path):
        """What clicking a model in File › Models does."""
        with bpy.context.temp_override(window=ui.win, area=ui.view, region=ui.region):
            bpy.ops.dasktoon.project_open_model(filepath=path)

    project = dtp.create_project("Hero", os.path.join(work, "Hero"))
    projects.select_project(project)
    outside = os.path.join(work, "outside")
    os.makedirs(outside)
    draft = os.path.join(outside, "draft.blend")
    bpy.ops.wm.save_as_mainfile(filepath=draft)
    draft_sha = sha256(draft)

    # 1. Ctrl+N opens DaskToon's New menu.
    seen = []

    def spy(_self, _context):
        seen.append(True)

    bpy.types.TOPBAR_MT_file_new.append(spy)
    ui.e.ctrl.n()
    yield wait(1.0)
    check(bool(seen), "Ctrl+N did not open the New menu")
    ui.e.esc()
    yield wait(0.5)
    bpy.types.TOPBAR_MT_file_new.remove(spy)

    # 2. Ctrl+O opens DaskToon's file browser.
    ui.e.ctrl.o()
    yield wait(1.5)
    browsers = [area.spaces.active for window in bpy.context.window_manager.windows
                for area in window.screen.areas if area.type == 'FILE_BROWSER']
    operator = browsers[0].active_operator if browsers else None
    check(operator is not None and operator.bl_idname == "DASKTOON_OT_open",
          "Ctrl+O did not open DaskToon's file browser: %r" % (operator and operator.bl_idname))
    ui.e.esc()
    yield wait(1.0)

    # 3. Ctrl+S on a draft: Save to Project, Return saves it as Models/draft.blend; the draft file stays as it was.
    change_something()
    ui.e.ctrl.s()
    yield wait(1.0)
    ui.e.ret()
    yield wait(2.0)
    first = os.path.join(project.models_folder, "draft.blend")
    check(dtp.same_path(bpy.data.filepath, first),
          "Ctrl+S on a draft did not save it into Models/ through Save to Project: %s" % bpy.data.filepath)
    check(sha256(draft) == draft_sha, "Ctrl+S changed the draft file")

    # 4. Opening another model with unsaved changes: Save saves this model, then the other one opens.
    other = os.path.join(project.models_folder, "other.blend")
    bpy.ops.wm.save_as_mainfile(filepath=other, copy=True)
    change_something()
    before = os.path.getmtime(first)
    open_model(other)
    yield wait(1.0)
    ui.e.ret()  # Save is the dialog's default button
    yield wait(2.0)
    find_window()
    check(dtp.same_path(bpy.data.filepath, other), "the other model did not open: %s" % bpy.data.filepath)
    check(os.path.getmtime(first) > before, "Save in the dialog did not save the model first")

    # 5. The same dialog on a draft from outside: Save opens Save to Project and the opening stops.
    second = os.path.join(outside, "second.blend")
    bpy.ops.wm.save_as_mainfile(filepath=second, copy=True)
    bpy.ops.wm.open_mainfile(filepath=second)
    find_window()
    yield wait(1.0)
    second_sha = sha256(second)
    change_something()
    open_model(other)
    yield wait(1.0)
    ui.e.ret()  # Save: the draft goes to Save to Project, so the opening stops
    yield wait(1.5)
    check(dtp.same_path(bpy.data.filepath, second), "the opening went on though the draft was not saved")
    ui.e.ret()  # Save to Project: OK
    yield wait(2.0)
    saved = os.path.join(project.models_folder, "second.blend")
    check(dtp.same_path(bpy.data.filepath, saved), "Save to Project did not save the draft: %s" % bpy.data.filepath)
    check(sha256(second) == second_sha, "the file from outside the project was overwritten")

    # 6. Ctrl+Q with unsaved changes: Save saves the model, then DaskToon quits; run_outside() checks the file.
    change_something()
    result.update(model=bpy.data.filepath, model_mtime=os.path.getmtime(bpy.data.filepath), draft=second,
                  draft_sha256=second_sha, quit_started=True)
    write_result()
    ui.e.ctrl.q()
    yield wait(1.0)
    ui.e.ret()
    yield wait(10.0)
    errors.append("DaskToon did not quit after Save in the quit dialog")
    write_result()
    bpy.ops.wm.quit_blender()


def run_inside():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_simulate", "modules"))
    import easy_keys
    work = os.environ["DASKTOON_WINDOW_TEST"]
    prefs = bpy.context.preferences
    easy_keys.setup_default_preferences(prefs)
    prefs.view.use_save_prompt = True  # the dialogs under test
    prefs.view.filebrowser_display_type = 'SCREEN'

    def on_error():
        with open(os.path.join(work, RESULT), "w", encoding="utf-8") as f:
            json.dump({"errors": ["a step raised an error, see the DaskToon console"]}, f)
        bpy.ops.wm.quit_blender()

    easy_keys.run(steps(work), on_error=on_error)


if bpy is None:
    if __name__ == "__main__":
        sys.exit(run_outside(sys.argv[1]))
else:
    run_inside()
