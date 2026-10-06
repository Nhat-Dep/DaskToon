# DaskToon: quy trình hướng dự án (Phần 2) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng chọn chạy **tự động, inline** (superpowers:executing-plans) trên nhánh `dasktoon-project-workflow`,
> commit từng task, tự quyết các điểm mơ hồ và ghi vào báo cáo. Không push.

**Goal:** Mọi cách mở, tạo, lưu file mà người dùng chạm tới đều đi qua dự án DaskToon; file ngoài dự án chỉ là bản nháp;
dự án tự chứa đủ texture; Unity gắn sau được.

**Architecture:** Thư viện `scripts/modules/dasktoon_project/` lo phần đĩa (dự án, model, texture, cảnh khởi đầu). Giao
diện chia ba module `bl_ui`: `dasktoon_project.py` (dự án, menu), `dasktoon_model.py` (New Model, Open, các lệnh Save),
`dasktoon_splash.py` (màn hình đầu). Lõi C++ (`wm_files.cc`) chuyển bốn lệnh file của Blender sang lệnh DaskToon khi
chúng được *invoke*, và chạy một lệnh "sau khi đọc file" để New Model hoàn tất sau hộp thoại hỏi lưu của Blender.

**Tech Stack:** Python `bpy`, C++ (Blender 5.2, MSBuild/VS 2022), `unittest` chạy trong DaskToon, event simulation
(`tests/python/ui_simulate/modules/easy_keys.py`) cho test có cửa sổ.

**Spec:** `docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md`

---

## Môi trường và các lệnh dùng chung

Git Bash, thư mục gốc `d:/DaskToon`, nhánh `dasktoon-project-workflow`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
INSTALL=/d/build_windows_x64_vc17_Release/bin/Release/5.2
PY=$INSTALL/python/bin/python.exe
MSBUILD="/c/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe"
```

- **Đồng bộ script vào bản cài** (sau mỗi thay đổi Python): `"$PY" tools/dasktoon_sync_build.py "$INSTALL"`.
- **Build** (sau thay đổi C++; đóng DaskToon trước; lâu nên chạy nền, trong lúc chờ chỉ sửa file không thuộc lần build):
  `MSYS_NO_PATHCONV=1 "$MSBUILD" "D:/build_windows_x64_vc17_Release/INSTALL.vcxproj" -p:Configuration=Release -m -v:m -nologo 2>&1 | tail -30`.
  Target INSTALL chép cả script của repo vào bản cài; chạy lệnh đồng bộ ở trên ngay sau đó để xóa file cũ.
- **Chạy một file test:** `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py 2>&1 | tail -30`.
  Exit code 0 là PASS.
- **Toàn bộ test DaskToon:** mọi file trong `foreach(dasktoon_test ...)` của `tests/python/CMakeLists.txt`.

### Đã kiểm chứng trước khi viết kế hoạch (chạy thử trong bản build hiện có)

- `wm.read_homefile(use_empty=True)` giữ 1 scene, 0 object, không có World, giữ workspace; engine `DASKTOON_ANIME`, view
  `Filmic`.
- Save Incremental của Blender đặt tên `Hero.blend` → `Hero1.blend` → `Hero2.blend`. Spec 6 ghi `<tên>_001.blend`, nên
  DaskToon tự tính tên (`incremental_path`) rồi lưu bằng `wm.save_mainfile(filepath=...)`.
- `save_post`/`load_post` nhận đường dẫn file (Save Copy: đường dẫn của bản sao).
- Đường dẫn tương đối khi lưu: file chưa từng lưu thì mọi đường dẫn tuyệt đối thành tương đối tới file mới; file đã lưu thì
  chỉ đường dẫn tương đối được đổi gốc (rebase), đường dẫn tuyệt đối giữ nguyên; `copy=True` trả lại đường dẫn trong bộ nhớ.
- Gán `image.filepath` làm ảnh nạp lại (mất nét vẽ chưa lưu); gán `image.filepath_raw` thì không, ảnh vẫn `is_dirty`.
- Chạy nền (`--background`): không có cửa sổ nên `bpy.ops.X('INVOKE_DEFAULT')` trả về mà không chạy `invoke`; keymap rỗng;
  `bpy.data.is_dirty` luôn False. Vì thế mọi đường invoke chỉ test được bằng test có cửa sổ (Task 8).
- Python không đăng ký được menu tên `TOPBAR_MT_file_open_recent` khi menu C++ cùng tên còn đó ("is built-in").
- Chữ phím tắt cạnh một mục menu chỉ đến từ mục keymap có cùng lệnh và cùng thuộc tính (`but_event_operator_string` trong
  `interface.cc`). Keymap Blender (cửa sổ): Ctrl+N = `wm.call_menu(TOPBAR_MT_file_new)`, Ctrl+O = `wm.open_mainfile`,
  Shift+Ctrl+O = `wm.call_menu(TOPBAR_MT_file_open_recent)`, Ctrl+S = `wm.save_mainfile(show_save_modified_images_dialog)`,
  Shift+Ctrl+S = `wm.save_as_mainfile(show_save_modified_images_dialog)`, Ctrl+Alt+S = `wm.save_mainfile(incremental,
  show_save_modified_images_dialog)`. Industry Compatible: Ctrl+N = `wm.read_homefile`.
- Màn hình đầu là popup `BLOCK_KEEP_OPEN`: bấm một mục không đóng nó; hàm của block chạy *sau* lệnh, khi đó nếu lệnh đã
  đọc file khác thì block đã bị giải phóng. Muốn bấm là đóng thì bỏ `KEEP_OPEN` cho màn hình này (giữ cho Quick Setup).
- Hộp thoại hỏi lưu: sau Save/Don't Save, Blender gọi lại lệnh với bản sao thuộc tính (`read_homefile` bằng exec,
  `open_mainfile` bằng invoke với `state` đã tiến lên).
- `vi.po` của Blender dịch "Project" (ngữ cảnh mặc định) là "Phóng Chiếu", và bản của Blender thắng. Menu có
  `bl_translation_context = "DaskToon"` cùng mục dịch `("DaskToon", "Project")` thì hiện "Dự án" (đã thử).
- Mọi icon dùng trong kế hoạch có trong Blender 5.2.

## Global Constraints

- Không push. Mỗi task một commit trên nhánh `dasktoon-project-workflow`. Không ghi vào project Unity trong `D:\Unity\`;
  test và công cụ chỉ dùng thư mục tạm, và luôn đặt `DASKTOON_CONFIG_DIR` vào thư mục tạm.
- `dasktoon_project.json` giữ đúng định dạng version 1: `{"version": 1, "name": "Hero", "engines": [{"engine":
  "UNITY_URP", "path": "D:/Unity/Game"}]}`; `engines` được phép là `[]`.
- Thư mục cấu hình (`config_dir()`): `recent_projects.json` tối đa **8**, `recent_models.json` tối đa **10** (mới nhất
  trước), `settings.json` = `{"project_location": "<thư mục>"}`.
- Model mới luôn là `Models/<tên>.blend`; texture chép vào `Textures/<tên file>`, trùng tên khác nội dung thêm `_1`, `_2`…
- Chỉ **invoke** bị chuyển hướng (`wm.read_homefile`, `wm.open_mainfile`, `wm.save_mainfile`, `wm.save_as_mainfile`);
  **exec không bao giờ**. DaskToon gọi lệnh gốc bằng invoke thì luôn kèm `use_project_redirect=False`.
- Không sửa file keymap (`scripts/presets/keyconfig/**`).
- Chữ gốc tiếng Anh kiểu Blender, không emoji; chữ có biến: `iface_()`/`rpt_()` rồi mới `%`, `translate=False` cho
  `layout`; không f-string cho chữ hiển thị; mọi chữ mới có bản dịch trong `scripts/startup/bl_ui/dasktoon_translations.py`
  (test bản dịch của Phần 1 tự quét mọi file `dasktoon_*`).
- Ngoài phạm vi (không làm): chép thư viện `.blend` được Link vào dự án; đổi tên/xóa/di chuyển model; tự dời file dự án cũ
  vào `Models/`; Unreal, Godot; chép chuỗi ảnh.

## Review Focus

1. **Dự án gần đây có file JSON hỏng hoặc thư mục đã bị xóa trong lúc làm.** Người dùng mong menu, màn hình đầu và "dự án
   được chọn" vẫn chạy, bỏ qua dự án hỏng. Test ở Task 4.
2. **Tên có chữ tiếng Việt và khoảng trắng** (thư mục dự án, tên model, thư mục ảnh). Mong file, texture và đường dẫn
   tương đối đều đúng. Test ở Task 2 và Task 5.
3. **Không ghi được chỗ cần ghi** (một *file* tên `Models` chắn chỗ thư mục). Mong một thông báo lỗi, cảnh hiện tại không
   đổi, không lỗi Python. Test ở Task 5.
4. **File `dasktoon_project.json` bị xóa khi một model đang mở.** Mong file thành bản nháp: Save không ghi đè gì, mà đi qua
   Save to Project. Test ở Task 6.
5. **Texture trùng tên chỉ khác hoa thường** (`Skin.png` có sẵn, ảnh ngoài tên `skin.png`, nội dung khác). Trên Windows hai
   tên này là một file; mong file có sẵn không bị ghi đè và ảnh trỏ tới bản sao đúng nội dung. Test ở Task 2.

---

### Task 1: Thư viện dự án: không cần Unity, Models/ và Textures/, tên, danh sách model, model gần đây, settings, gắn Unity sau

**Files:**
- Modify (viết lại): `scripts/modules/dasktoon_project/project.py`
- Modify (viết lại): `tests/python/dasktoon_project_test.py`
- Modify: `scripts/startup/bl_ui/dasktoon_project.py` (lệnh tạo dự án theo chữ ký mới, bỏ "Save Current File in Project")
- Modify: `tests/python/dasktoon_project_ui_test.py` (gọi `create_project` theo chữ ký mới)
- Modify: `tools/dasktoon_ui_screenshots.py` (gọi `create_project` theo chữ ký mới)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Produces (`dasktoon_project.project`, import là `dtp`): hằng `MODELS_DIR = "Models"`, `TEXTURES_DIR = "Textures"`,
  `MAX_RECENT = 8`, `MAX_RECENT_MODELS = 10`, `RECENT_FILE`, `RECENT_MODELS_FILE`, `SETTINGS_FILE`, `PROJECT_FILE`;
  `Project(folder, name, engines)` thêm `.models_folder`, `.textures_folder`;
  `clean_name(name) -> str` (ValueError khi rỗng); `same_path(a, b) -> bool`; `is_inside(path, folder) -> bool`;
  `create_project(name, folder, engine_path="", engine='UNITY_URP') -> Project`;
  `check_engine_path(engine, engine_path) -> str`; `link_engine(project, engine, engine_path) -> list[str]` (cảnh báo shader);
  `project_models(project) -> list[str]`; `model_label(project, path) -> str`; `model_path(project, name) -> str`;
  `model_exists(project, name) -> bool`; `new_model_path(project, name) -> str` (ValueError khi trùng, OSError khi không tạo
  được `Models/`); `free_model_name(project, base) -> str`; `incremental_path(path) -> str`;
  `recent_projects()`, `add_recent(project_file)`, `recent_models()`, `add_recent_model(path)`;
  `default_location()`, `project_location()`, `set_project_location(folder)`; giữ nguyên `load`, `save`, `find_project`,
  `project_target`, `install_project_shaders`, `config_dir`.

- [ ] **Step 1: Viết test (đỏ)**

File: `tests/python/dasktoon_project_test.py` (thay toàn bộ)
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects on disk (unity export spec 7; project workflow spec 3, 4, 11, 12): creation with or without Unity,
Models/ and Textures/, older projects, the model list, names, recent projects and models, settings, linking Unity later."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402

SHADER = os.path.join("Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_proj_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


def touch(path, data=b""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ProjectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_proj_config_")
        tu.reset_scene()
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_proj_"), "MyProject")

    def test_create_without_unity_makes_models_and_textures(self):
        project = dtp.create_project("Dự án của tôi", self.folder)
        self.assertEqual(read_json(os.path.join(self.folder, dtp.PROJECT_FILE)),
                         {"version": 1, "name": "Dự án của tôi", "engines": []})
        self.assertTrue(os.path.isdir(os.path.join(self.folder, "Models")))
        self.assertTrue(os.path.isdir(os.path.join(self.folder, "Textures")))
        self.assertEqual((project.engine, project.engine_path), ("", ""))
        self.assertEqual(dtp.recent_projects(), [project.file])

    def test_create_with_unity_links_it_and_installs_the_shaders(self):
        dtp.create_project("P", self.folder, self.unity)
        self.assertEqual(read_json(os.path.join(self.folder, dtp.PROJECT_FILE))["engines"],
                         [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}])
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))

    def test_a_bad_unity_path_creates_nothing(self):
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, tempfile.mkdtemp(prefix="dt_not_unity_"))
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, self.unity, 'GODOT_4')
        self.assertFalse(os.path.exists(self.folder))

    def test_existing_project_is_not_overwritten(self):
        dtp.create_project("P", self.folder)
        with self.assertRaises(ValueError):
            dtp.create_project("Q", self.folder)
        self.assertEqual(dtp.load(self.folder).name, "P")

    def test_a_folder_with_files_becomes_a_project_and_its_blend_files_models(self):
        touch(os.path.join(self.folder, "Hero.blend"))
        touch(os.path.join(self.folder, "notes.txt"))
        project = dtp.create_project("P", self.folder)
        self.assertEqual(dtp.project_models(project), [os.path.join(self.folder, "Hero.blend")])

    def test_model_list_puts_models_first_and_skips_backups_textures_and_hidden_folders(self):
        project = dtp.create_project("P", self.folder)
        for rel in ("Models/b.blend", "Models/A.blend", "Models/A.blend1", "Root.blend", "sub/x.blend",
                    "Textures/t.blend", ".hidden/h.blend"):
            touch(os.path.join(self.folder, *rel.split("/")))
        models = dtp.project_models(project)
        self.assertEqual([dtp.model_label(project, path) for path in models], ["A", "b", "Root.blend", "sub/x.blend"])

    def test_model_scan_skips_unity_library_folders(self):
        project = dtp.create_project("P", self.folder)
        for rel in ("Game/Assets/model.blend", "Game/Library/cache.blend", "Game/Temp/t.blend"):
            touch(os.path.join(self.folder, *rel.split("/")))
        touch(os.path.join(self.folder, *["d%d" % i for i in range(dtp.MAX_SCAN_DEPTH + 2)], "deep.blend"))
        self.assertEqual(dtp.project_models(project), [os.path.join(self.folder, "Game", "Assets", "model.blend")])

    def test_older_project_keeps_its_blend_files_at_the_root(self):
        os.makedirs(self.folder)
        dtp.save(dtp.Project(self.folder, "Old", [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}]))
        hero = touch(os.path.join(self.folder, "Hero.blend"), b"old model")
        project = dtp.find_project(hero)
        self.assertEqual((project.name, project.engine), ("Old", 'UNITY_URP'))
        self.assertFalse(os.path.exists(project.models_folder))
        self.assertEqual(dtp.project_models(project), [hero])
        self.assertEqual(dtp.new_model_path(project, "Sword"), os.path.join(self.folder, "Models", "Sword.blend"))
        self.assertTrue(os.path.isdir(project.models_folder))
        with open(hero, "rb") as f:
            self.assertEqual(f.read(), b"old model")

    def test_names_lose_the_characters_windows_refuses(self):
        self.assertEqual(dtp.clean_name(' Hero: "Boss"? '), "Hero_ _Boss__")
        self.assertEqual(dtp.clean_name("a/b\\c"), "a_b_c")
        self.assertEqual(dtp.clean_name("Hero."), "Hero")
        self.assertEqual(dtp.clean_name("Nhân vật"), "Nhân vật")
        for empty in ("", "   ", "..."):
            with self.assertRaises(ValueError):
                dtp.clean_name(empty)

    def test_model_names_are_unique_whatever_the_case(self):
        project = dtp.create_project("P", self.folder)
        mine = touch(os.path.join(project.models_folder, "Hero.blend"), b"mine")
        with self.assertRaises(ValueError):
            dtp.new_model_path(project, "hero")
        self.assertTrue(dtp.model_exists(project, "HERO"))
        self.assertEqual(dtp.free_model_name(project, "Hero"), "Hero_1")
        self.assertEqual(dtp.free_model_name(project, "Sword"), "Sword")
        self.assertEqual(dtp.free_model_name(project, "  "), "Untitled")
        self.assertEqual(dtp.new_model_path(project, "A/B"), os.path.join(project.models_folder, "A_B.blend"))
        with open(mine, "rb") as f:
            self.assertEqual(f.read(), b"mine")

    def test_incremental_names(self):
        folder = tempfile.mkdtemp(prefix="dt_proj_inc_")
        hero = touch(os.path.join(folder, "Hero.blend"))
        self.assertEqual(os.path.basename(dtp.incremental_path(hero)), "Hero_001.blend")
        touch(os.path.join(folder, "Hero_001.blend"))
        self.assertEqual(os.path.basename(dtp.incremental_path(hero)), "Hero_002.blend")
        self.assertEqual(os.path.basename(dtp.incremental_path(os.path.join(folder, "Hero_001.blend"))),
                         "Hero_002.blend")
        self.assertEqual(os.path.basename(dtp.incremental_path(os.path.join(folder, "Take9.blend"))), "Take10.blend")

    def test_project_is_found_from_a_subfolder(self):
        dtp.create_project("P", self.folder)
        self.assertEqual(dtp.find_project(os.path.join(self.folder, "characters", "hero", "hero.blend")).name, "P")
        self.assertIsNone(dtp.find_project(os.path.join(tempfile.mkdtemp(), "loose.blend")))
        self.assertIsNone(dtp.find_project(""))
        self.assertTrue(dtp.is_inside(os.path.join(self.folder, "Models", "a.blend"), self.folder))
        self.assertFalse(dtp.is_inside(self.folder + "2", self.folder))

    def test_recent_projects_keep_the_eight_newest(self):
        files = []
        for i in range(10):
            project = dtp.Project(os.path.join(tempfile.mkdtemp(prefix="dt_recent_"), "P%d" % i), "P%d" % i, [])
            dtp.save(project)
            dtp.add_recent(project.file)
            files.append(project.file)
        dtp.add_recent(files[5])
        recent = dtp.recent_projects()
        self.assertEqual(len(recent), dtp.MAX_RECENT)
        self.assertEqual(recent[:2], [files[5], files[9]])

    def test_recent_models_keep_the_ten_newest_existing_files(self):
        folder = tempfile.mkdtemp(prefix="dt_recent_models_")
        paths = [touch(os.path.join(folder, "m%d.blend" % i)) for i in range(12)]
        for path in paths:
            dtp.add_recent_model(path)
        dtp.add_recent_model(paths[3])
        os.remove(paths[11])
        recent = dtp.recent_models()
        self.assertEqual(recent[0], paths[3])
        self.assertNotIn(paths[11], recent)
        self.assertEqual(len(recent), dtp.MAX_RECENT_MODELS - 1)

    def test_settings_remember_where_projects_go(self):
        self.assertEqual(dtp.project_location(), dtp.default_location())
        self.assertEqual(os.path.basename(dtp.default_location()), "DaskToon Projects")
        place = tempfile.mkdtemp(prefix="dt_proj_place_")
        dtp.set_project_location(place)
        self.assertEqual(dtp.project_location(), place)
        self.assertEqual(read_json(os.path.join(dtp.config_dir(), dtp.SETTINGS_FILE)), {"project_location": place})
        os.rmdir(place)
        self.assertEqual(dtp.project_location(), dtp.default_location())

    def test_unity_can_be_linked_later(self):
        project = dtp.create_project("P", self.folder)
        dtp.link_engine(project, 'UNITY_URP', self.unity)
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))
        self.assertEqual(dtp.load(self.folder).engine_path, self.unity.replace("\\", "/"))
        os.remove(os.path.join(self.unity, SHADER))
        dtp.link_engine(project, 'UNITY_URP', self.unity)  # same project: nothing is installed again
        self.assertFalse(os.path.isfile(os.path.join(self.unity, SHADER)))
        other = fake_unity()
        dtp.link_engine(project, 'UNITY_URP', other)
        self.assertTrue(os.path.isfile(os.path.join(other, SHADER)))
        with self.assertRaises(ValueError):
            dtp.link_engine(project, 'UNITY_URP', tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertEqual(dtp.load(self.folder).engine_path, other.replace("\\", "/"))
        dtp.link_engine(project, 'UNITY_URP', "")
        self.assertEqual(dtp.load(self.folder).engines, [])

    def test_project_target_writes_into_the_unity_project(self):
        project = dtp.create_project("P", self.folder, self.unity)
        target = dtp.project_target(project, "Hero")
        self.assertEqual((target.mode, target.root), ('PROJECT', os.path.join(self.unity, "Assets", "DaskToon")))
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [body], options)
        self.assertEqual(rep.shaders, 'UP_TO_DATE')
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")))
        self.assertTrue(targets.find_unity_project(target.root))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ**

Run: `"$DT" ... --python tests/python/dasktoon_project_test.py`
Expected: FAIL/ERROR — `create_project() missing 1 required positional argument`, `AttributeError: ... 'clean_name'`.

- [ ] **Step 3: Viết lại thư viện**

File: `scripts/modules/dasktoon_project/project.py` (thay toàn bộ)
```python
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
```

- [ ] **Step 4: Cập nhật chỗ gọi `create_project` cũ**

`scripts/startup/bl_ui/dasktoon_project.py`, lớp `DASKTOON_OT_project_create` (lớp này được viết lại hẳn ở Task 4; ở đây chỉ
cho nó chạy với chữ ký mới): xóa thuộc tính `save_current` và thay `execute` bằng:
```python
    def execute(self, _context):
        try:
            project = dtp.create_project(self.name, bpy.path.abspath(self.folder),
                                         bpy.path.abspath(self.engine_path) if self.engine_path else "", self.engine)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        self.report({'INFO'}, rpt_("Created project %s") % project.name)
        return {'FINISHED'}
```
Bỏ `BoolProperty` khỏi dòng import nếu không còn dùng.

`tests/python/dasktoon_project_ui_test.py`:
- hàm `create` thành
```python
    def create(self):
        result = bpy.ops.dasktoon.project_create(name="Proj", folder=self.folder, engine='UNITY_URP',
                                                 engine_path=self.unity)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.folder, "Proj.blend"))
        return result
```
- trong `test_open_sets_the_session_project_for_an_unsaved_file`: `dtp.create_project("Opened", self.folder, self.unity)`.

`tools/dasktoon_ui_screenshots.py`, cuối `build_scene()`: thay dòng `dtp.create_project(... save_current=True)` bằng
```python
    project = dtp.create_project("Hero", os.path.join(WORK, "Hero"), unity)
    bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(project, "Hero"))
```

- [ ] **Step 5: Bản dịch**

Trong `VI` của `dasktoon_translations.py`, khối `# bl_ui/dasktoon_project.py and dasktoon_project/project.py`:
- xóa `"Save Current File in Project"`, `"Created project %s and installed the shaders into %s"` và
  `"%s already has another file named %s: rename the current file or turn off Save Current File in Project"`;
- thêm:
```python
    "The name is empty": "Tên đang để trống",
    "The project already has a model named %s": "Dự án đã có model tên %s",
    "Created project %s": "Đã tạo dự án %s",
```

- [ ] **Step 6: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_project_test.py`, `dasktoon_project_ui_test.py`, `dasktoon_translations_test.py`.
Expected: tất cả OK.

- [ ] **Step 7: Commit**
```bash
git add scripts/modules/dasktoon_project/project.py scripts/startup/bl_ui/dasktoon_project.py \
        scripts/startup/bl_ui/dasktoon_translations.py tests/python/dasktoon_project_test.py \
        tests/python/dasktoon_project_ui_test.py tools/dasktoon_ui_screenshots.py
git commit -m "feat: projects without Unity, with Models/ and Textures/, recent models and a remembered location"
```

---

### Task 2: Chép texture vào dự án

**Files:**
- Create: `scripts/modules/dasktoon_project/textures.py`
- Create: `tests/python/dasktoon_project_textures_test.py`
- Modify: `tests/python/CMakeLists.txt`, `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: `dtp.is_inside`, `Project.textures_folder` (Task 1).
- Produces (`dasktoon_project.textures`, import là `dtt`): `Collected` (`copied: int`, `images: list[bpy.types.Image]`,
  `warnings: list[str]`, `summary() -> str`); `collect(project, images=None) -> Collected`;
  `relink_absolute(images) -> int`; `unsaved_images() -> list[str]`; `suffixed(name, number, token) -> str`.

- [ ] **Step 1: Viết test (đỏ)**

File: `tests/python/dasktoon_project_textures_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Images from outside the project are copied into <project>/Textures/ when a person saves (project workflow spec 10):
relative paths, name clashes, identical files, UDIM, what is only warned about and what is left alone."""

import filecmp
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import textures as png  # noqa: E402
from dasktoon_project import project as dtp, textures as dtt  # noqa: E402


def write_png(path, rgba=(255, 0, 0, 255)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png.png_bytes(2, 2, bytes(rgba) * 4))
    return path


def load(path):
    image = bpy.data.images.load(path, check_existing=False)
    image.use_fake_user = True
    return image


def resolved(image):
    return os.path.normcase(os.path.normpath(bpy.path.abspath(image.filepath_raw)))


def norm(path):
    return os.path.normcase(os.path.normpath(path))


class TextureCollectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_tex_config_")
        tu.reset_scene()
        base = tempfile.mkdtemp(prefix="dt_tex_")
        self.project = dtp.create_project("P", os.path.join(base, "Dự án P"))
        self.outside = os.path.join(base, "Ảnh ngoài")
        self.textures = self.project.textures_folder

    def test_outside_image_is_copied_and_relative_after_saving(self):
        source = write_png(os.path.join(self.outside, "skin.png"))
        image = load(source)
        result = dtt.collect(self.project)
        copy = os.path.join(self.textures, "skin.png")
        self.assertEqual((result.copied, result.images, result.warnings), (1, [image], []))
        self.assertTrue(filecmp.cmp(source, copy, shallow=False))
        self.assertEqual(result.summary(), "Copied 1 texture into Textures/")
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        self.assertTrue(image.filepath_raw.startswith("//"))
        self.assertEqual(resolved(image), norm(copy))
        self.assertTrue(os.path.isfile(source))

    def test_saved_draft_gets_a_relative_path_that_follows_the_save(self):
        image = load(write_png(os.path.join(self.outside, "skin.png")))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.outside, "draft.blend"))
        dtt.collect(self.project)
        self.assertTrue(image.filepath_raw.startswith("//"))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        self.assertEqual(resolved(image), norm(os.path.join(self.textures, "skin.png")))
        self.assertEqual(dtt.relink_absolute([image]), 0)

    def test_same_name_other_content_gets_a_suffix_and_an_identical_file_is_reused(self):
        write_png(os.path.join(self.textures, "skin.png"), rgba=(0, 0, 255, 255))
        red = load(write_png(os.path.join(self.outside, "a", "skin.png")))
        blue = load(write_png(os.path.join(self.outside, "b", "skin.png"), rgba=(0, 0, 255, 255)))
        result = dtt.collect(self.project)
        self.assertEqual(resolved(red), norm(os.path.join(self.textures, "skin_1.png")))
        self.assertEqual(resolved(blue), norm(os.path.join(self.textures, "skin.png")))
        self.assertEqual(result.copied, 1)
        self.assertEqual(result.summary(), "Copied 1 texture into Textures/")
        self.assertEqual(sorted(os.listdir(self.textures)), ["skin.png", "skin_1.png"])

    def test_a_clash_in_letter_case_only_never_overwrites(self):
        existing = write_png(os.path.join(self.textures, "Skin.png"), rgba=(0, 0, 255, 255))
        with open(existing, "rb") as f:
            before = f.read()
        source = write_png(os.path.join(self.outside, "skin.png"))
        image = load(source)
        dtt.collect(self.project)
        with open(existing, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertTrue(filecmp.cmp(source, bpy.path.abspath(image.filepath_raw), shallow=False))

    def test_udim_tiles_are_copied_with_their_pattern(self):
        pattern = os.path.join(self.outside, "body.<UDIM>.png")
        for number in (1001, 1002):
            write_png(pattern.replace("<UDIM>", str(number)), rgba=(number % 256, 0, 0, 255))
        image = bpy.data.images.new("body", 2, 2, tiled=True)
        image.tiles.new(1002)
        image.source = 'TILED'
        image.filepath_raw = pattern
        image.use_fake_user = True
        result = dtt.collect(self.project)
        self.assertEqual(result.copied, 1)
        self.assertEqual(sorted(os.listdir(self.textures)), ["body.1001.png", "body.1002.png"])
        self.assertEqual(resolved(image), norm(os.path.join(self.textures, "body.<UDIM>.png")))
        self.assertEqual(dtt.suffixed("body.<UDIM>.png", 1, "<UDIM>"), "body_1.<UDIM>.png")
        self.assertEqual(dtt.suffixed("skin.png", 2, None), "skin_2.png")

    def test_movies_are_copied(self):
        clip = os.path.join(self.outside, "clip.mp4")
        os.makedirs(self.outside, exist_ok=True)
        with open(clip, "wb") as f:
            f.write(b"not really a movie")
        image = bpy.data.images.new("clip", 2, 2)
        image.source = 'FILE'
        image.filepath_raw = clip
        image.source = 'MOVIE'
        image.use_fake_user = True
        self.assertEqual(dtt.collect(self.project).copied, 1)
        self.assertTrue(os.path.isfile(os.path.join(self.textures, "clip.mp4")))

    def test_sequences_and_missing_files_are_only_warned_about(self):
        sequence = load(write_png(os.path.join(self.outside, "frame_0001.png")))
        sequence.source = 'SEQUENCE'
        missing = load(write_png(os.path.join(self.outside, "gone.png")))
        os.remove(os.path.join(self.outside, "gone.png"))
        before = (sequence.filepath_raw, missing.filepath_raw)
        result = dtt.collect(self.project)
        self.assertEqual((result.copied, result.images, len(result.warnings)), (0, [], 2))
        self.assertEqual((sequence.filepath_raw, missing.filepath_raw), before)
        self.assertEqual(os.listdir(self.textures), [])

    def test_packed_generated_linked_and_project_images_are_left_alone(self):
        load(write_png(os.path.join(self.outside, "packed.png"))).pack()
        bpy.data.images.new("generated", 2, 2).use_fake_user = True
        load(write_png(os.path.join(self.textures, "inside.png")))
        library = os.path.join(self.outside, "library.blend")
        lib_image = load(write_png(os.path.join(self.outside, "lib.png")))
        bpy.data.libraries.write(library, {lib_image}, fake_user=True)
        bpy.data.images.remove(lib_image)
        with bpy.data.libraries.load(library, link=True) as (_src, dst):
            dst.images = ["lib.png"]
        self.assertIsNotNone(dst.images[0].library)
        paths = {image.name: image.filepath_raw for image in bpy.data.images}
        result = dtt.collect(self.project)
        self.assertEqual((result.copied, result.images, result.warnings), (0, [], []))
        self.assertEqual({image.name: image.filepath_raw for image in bpy.data.images}, paths)
        self.assertEqual(os.listdir(self.textures), ["inside.png"])

    def test_relink_makes_absolute_project_paths_relative(self):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        image = load(write_png(os.path.join(self.textures, "skin.png")))
        self.assertFalse(image.filepath_raw.startswith("//"))
        self.assertEqual(dtt.relink_absolute([image]), 1)
        self.assertEqual(image.filepath_raw, "//../Textures/skin.png")

    def test_painted_images_are_listed_and_keep_their_paint(self):
        image = load(write_png(os.path.join(self.outside, "paint.png")))
        self.assertEqual(dtt.unsaved_images(), [])
        pixels = list(image.pixels)
        pixels[0] = 0.5
        image.pixels = pixels
        self.assertEqual(dtt.unsaved_images(), ["paint.png"])
        dtt.collect(self.project)
        self.assertTrue(image.is_dirty)
        self.assertAlmostEqual(image.pixels[0], 0.5, places=2)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: ERROR `ImportError: cannot import name 'textures' from 'dasktoon_project'`.

- [ ] **Step 3: Viết module**

File: `scripts/modules/dasktoon_project/textures.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Copy the images a model uses from outside its project into <project>/Textures/ before a person saves
(docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 10). Saves made by scripts and auto-save
do not call this."""

import filecmp
import os
import shutil
from dataclasses import dataclass, field

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

from . import project as dtp

TILE_TOKENS = ("<UDIM>", "<UVTILE>")
COPIED_SOURCES = {'FILE', 'MOVIE', 'TILED'}


@dataclass
class Collected:
    copied: int = 0                               # images whose files were copied into Textures/
    images: list = field(default_factory=list)    # images that now point into Textures/
    warnings: list = field(default_factory=list)  # one translated line each

    def summary(self):
        if self.copied == 1:
            return rpt_("Copied 1 texture into Textures/")
        if self.copied:
            return rpt_("Copied %d textures into Textures/") % self.copied
        return ""


def _tile_path(pattern, token, number):
    if token == "<UDIM>":
        return pattern.replace(token, str(number))
    return pattern.replace(token, "u%d_v%d" % ((number - 1001) % 10 + 1, (number - 1001) // 10 + 1))


def suffixed(name, number, token):
    """`name` with _<number> before its extension, or before the tile token (skin.<UDIM>.png gives skin_1.<UDIM>.png)."""
    if number == 0:
        return name
    if token:
        head, _token, tail = name.partition(token)
        stem = head.rstrip("._-")
        return "%s_%d%s%s%s" % (stem, number, head[len(stem):], token, tail)
    stem, extension = os.path.splitext(name)
    return "%s_%d%s" % (stem, number, extension)


def _place(folder, name, sources, token):
    """(destination path or tile pattern, [(source, destination)] still to copy): the first name in `folder` whose files
    are missing or identical to `sources`, trying name, name_1, name_2…"""
    number = 0
    while True:
        target = os.path.join(folder, suffixed(name, number, token))
        pending, clash = [], False
        for tile, source in sources:
            destination = target if token is None else _tile_path(target, token, tile)
            if not os.path.exists(destination):
                pending.append((source, destination))
            elif not os.path.isfile(destination) or not filecmp.cmp(source, destination, shallow=False):
                clash = True
                break
        if not clash:
            return target, pending
        number += 1


def _blend_path(path):
    """`path` as the open .blend file should store it: relative ("//...") when the file is saved and a relative path
    exists, absolute otherwise. Saving into another folder then rebases the relative path (Blender's relative remap)."""
    if bpy.data.filepath:
        try:
            return "//" + os.path.relpath(path, os.path.dirname(bpy.data.filepath)).replace(os.sep, "/")
        except ValueError:  # another drive
            pass
    return path


def collect(project, images=None):
    """Copy into the project's Textures/ the files of the images that live outside `project`, and point the images at
    the copies through filepath_raw (no reload, so paint not saved yet stays). Packed, generated and linked images and
    images already in the project are left alone; image sequences and missing files only get a warning."""
    result = Collected()
    for image in bpy.data.images if images is None else images:
        if image.users == 0 or image.library is not None or image.packed_file is not None:
            continue
        if image.source not in COPIED_SOURCES | {'SEQUENCE'} or not image.filepath_raw:
            continue
        path = os.path.normpath(bpy.path.abspath(image.filepath_raw))
        if dtp.is_inside(path, project.folder):
            continue
        if image.source == 'SEQUENCE':
            result.warnings.append(rpt_("%s: image sequences are not copied into the project") % image.name)
            continue
        token = next((t for t in TILE_TOKENS if t in path), None) if image.source == 'TILED' else None
        if token is None:
            sources = [(None, path)]
        else:
            sources = [(tile.number, _tile_path(path, token, tile.number)) for tile in image.tiles]
        missing = [source for _tile, source in sources if not os.path.isfile(source)]
        if missing:
            result.warnings.append(rpt_("%s: file not found: %s") % (image.name, missing[0]))
            continue
        os.makedirs(project.textures_folder, exist_ok=True)
        target, pending = _place(project.textures_folder, os.path.basename(path), sources, token)
        for source, destination in pending:
            shutil.copy2(source, destination)
        if pending:
            result.copied += 1
        image.filepath_raw = _blend_path(target)
        result.images.append(image)
    return result


def relink_absolute(images):
    """After the open file was saved under a new path: make relative the copied images whose path stayed absolute
    (the file used to be on another drive). Returns how many changed; the caller saves again when there are any."""
    changed = 0
    for image in images:
        if image.filepath_raw.startswith("//"):
            continue
        relative = _blend_path(image.filepath_raw)
        if relative != image.filepath_raw:
            image.filepath_raw = relative
            changed += 1
    return changed


def unsaved_images():
    """Names of images with paint changes that saving the .blend file does not keep (workflow spec 12)."""
    return sorted(image.name for image in bpy.data.images if image.users and image.is_dirty)
```

- [ ] **Step 4: Bản dịch và đăng ký test**

Thêm vào `VI` (khối `# dasktoon_project/textures.py` mới, ngay sau khối của `dasktoon_project.py`):
```python
    # dasktoon_project/textures.py
    "Copied 1 texture into Textures/": "Đã chép 1 texture vào Textures/",
    "Copied %d textures into Textures/": "Đã chép %d texture vào Textures/",
    "%s: image sequences are not copied into the project": "%s: chuỗi ảnh không được chép vào dự án",
    "%s: file not found: %s": "%s: không tìm thấy file: %s",
```
Thêm `dasktoon_project_textures_test` vào danh sách `foreach(dasktoon_test ...)` (sau `dasktoon_project_ui_test`).
Thêm `"scripts/modules/dasktoon_project/textures.py"` vào `TRANSLATED` của `tests/python/dasktoon_translations_test.py`
(`test_every_dasktoon_file_is_checked` đòi mọi file `dasktoon_*` mới có trong danh sách này).

- [ ] **Step 5: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_project_textures_test.py`, `dasktoon_translations_test.py`.
Expected: OK. (Đặt `source = 'MOVIE'` cho một file không phải video đã thử được trong bản build: Blender giữ nguồn MOVIE
và đường dẫn.)

- [ ] **Step 6: Commit**
```bash
git add scripts/modules/dasktoon_project/textures.py tests/python/dasktoon_project_textures_test.py \
        tests/python/CMakeLists.txt scripts/startup/bl_ui/dasktoon_translations.py
git commit -m "feat: copy images from outside a project into its Textures/ folder before a save"
```

---

### Task 3: Lõi C++: chuyển hướng khi invoke, lệnh sau khi đọc file, nút Save của hộp thoại hỏi lưu, Open Recent bằng Python

**Files:**
- Modify: `source/blender/windowmanager/intern/wm_files.cc`
- Modify: `source/blender/windowmanager/intern/wm_splash_screen.cc`
- Modify: `source/blender/editors/space_topbar/space_topbar.cc`
- Modify: `source/blender/editors/interface/interface.cc`
- Modify: `scripts/startup/bl_ui/dasktoon_project.py` (menu `TOPBAR_MT_file_open_recent` thay `TOPBAR_MT_dasktoon_project_recent`)
- Create: `tests/python/dasktoon_file_redirect_test.py`
- Modify: `tests/python/dasktoon_test_utils.py` (layout ghi lại cho test vẽ menu)
- Modify: `tests/python/dasktoon_project_ui_test.py`, `tests/python/dasktoon_ui_layout_test.py`, `tests/python/CMakeLists.txt`,
  `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Produces (C++ → Python): thuộc tính ẩn `use_project_redirect` (bool, mặc định True) trên `wm.read_homefile`,
  `wm.open_mainfile`, `wm.save_mainfile`, `wm.save_as_mainfile`; thuộc tính ẩn `post_read_operator` (string) trên
  `wm.read_homefile`, `wm.open_mainfile`: tên lệnh chạy bằng exec ngay sau khi file đọc xong.
- Produces: bảng chuyển hướng khi invoke: `read_homefile` → `DASKTOON_OT_model_new`; `open_mainfile` (chỉ lần gọi đầu và
  chỉ khi sẽ mở hộp chọn file) → `DASKTOON_OT_open` (kèm `filepath`); `save_mainfile` → `DASKTOON_OT_project_save`, hoặc
  `DASKTOON_OT_model_save_incremental` khi `incremental` (kèm `show_save_modified_images_dialog`); `save_as_mainfile` →
  `DASKTOON_OT_model_save_as`, hoặc `DASKTOON_OT_model_save_copy` khi `copy`. Nút Save của hộp thoại hỏi lưu gọi
  `DASKTOON_OT_project_save` bằng exec khi lệnh đó đã đăng ký.
- Produces (Python): `bl_ui.dasktoon_project.TOPBAR_MT_file_open_recent` (`bl_idname = "TOPBAR_MT_file_open_recent"`).
- Produces (test helper, `dasktoon_test_utils`): `RecordingLayout`, `Props`, `draw(menu, context=None) -> log`,
  `operators(log) -> [(idname, text)]`, `labels(log) -> [text]`. Mỗi dòng log: `(kind, name, text, icon, enabled, props)`,
  `kind` là `"operator"`, `"menu"`, `"label"`, `"prop"`, `"separator"` hoặc `"call"` (hàm khác, ví dụ `template_ID`).

- [ ] **Step 1: Viết helper vẽ menu cho test**

Thêm vào `tests/python/dasktoon_test_utils.py` (`import types` ở đầu file, phần còn lại ở cuối file trước `run_tests`):
```python
class Props:
    """Operator properties a draw function sets (RecordingLayout.operator returns one)."""


class RecordingLayout:
    """Stands in for UILayout in draw tests. Each operator, menu, label, prop and separator is logged as
    (kind, name, text, icon, enabled, props); sub-layouts share the log and pass `enabled` down. Any other call
    (template_ID, ...) is logged as ("call", name, ...) and returns a sub-layout."""

    def __init__(self, log=None, parent=None):
        self.log = [] if log is None else log
        self.parent = parent
        self.enabled = True

    def is_enabled(self):
        layout = self
        while layout is not None:
            if not layout.enabled:
                return False
            layout = layout.parent
        return True

    def _add(self, kind, name, text="", icon='NONE', props=None):
        self.log.append((kind, name, text, icon, self.is_enabled(), props))

    def _child(self, *_args, **_kwargs):
        return RecordingLayout(self.log, self)

    split = column = row = box = _child

    def operator(self, idname, text="", icon='NONE', **_kwargs):
        props = Props()
        self._add("operator", idname, text, icon, props)
        return props

    def menu(self, idname, text="", icon='NONE', **_kwargs):
        self._add("menu", idname, text, icon)

    def label(self, text="", icon='NONE', **_kwargs):
        self._add("label", "", text, icon)

    def prop(self, _data, name, text="", icon='NONE', **_kwargs):
        self._add("prop", name, text, icon)

    def separator(self, **_kwargs):
        self._add("separator", "")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*_args, **_kwargs):
            self._add("call", name)
            return RecordingLayout(self.log, self)
        return call


def draw(menu, context=None):
    """The log of `menu`'s draw: a Menu or Header class, or anything with draw(self, context)."""
    layout = RecordingLayout()
    menu.draw(types.SimpleNamespace(layout=layout), context or bpy.context)
    return layout.log


def operators(log):
    """[(idname, text)] of the logged operators, enabled or not."""
    return [(entry[1], entry[2]) for entry in log if entry[0] == "operator"]


def labels(log):
    return [entry[2] for entry in log if entry[0] == "label"]
```

- [ ] **Step 2: Viết test (đỏ)**

File: `tests/python/dasktoon_file_redirect_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Blender's file operators hand over to DaskToon only when invoked (project workflow spec 8): the switch is there,
exec with a path still saves, opens and reads like Blender while the DaskToon commands are registered, a command named
in post_read_operator runs once the file has been read, and Open Recent is DaskToon's Python menu (spec 7)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402

OPERATORS = ("read_homefile", "open_mainfile", "save_mainfile", "save_as_mainfile")
TARGETS = ("dasktoon.model_new", "dasktoon.open", "dasktoon.project_save", "dasktoon.model_save_incremental",
           "dasktoon.model_save_as", "dasktoon.model_save_copy")
calls = []


def stub(idname):
    """An operator that only records that it ran, registered in place of a DaskToon command."""
    return type("STUB_OT_" + idname.replace(".", "_"), (bpy.types.Operator,), {
        "bl_idname": idname,
        "bl_label": "Stub",
        "invoke": lambda self, _context, _event: calls.append(idname) or {'FINISHED'},
        "execute": lambda self, _context: calls.append(idname) or {'FINISHED'},
    })


class PostRead(bpy.types.Operator):
    bl_idname = "test.dasktoon_post_read"
    bl_label = "Post Read"
    seen = []

    def execute(self, _context):
        PostRead.seen.append((bpy.data.filepath, len(bpy.data.objects)))
        return {'FINISHED'}


def setUpModule():
    for idname in TARGETS:
        bpy.utils.register_class(stub(idname))
    bpy.utils.register_class(PostRead)


class SwitchTest(unittest.TestCase):
    def test_the_four_file_operators_have_the_redirect_switch(self):
        for name in OPERATORS:
            prop = getattr(bpy.ops.wm, name).get_rna_type().properties["use_project_redirect"]
            self.assertEqual((prop.type, prop.default, prop.is_hidden, prop.is_skip_save),
                             ('BOOLEAN', True, True, True), name)

    def test_read_and_open_have_a_post_read_operator(self):
        for name in ("read_homefile", "open_mainfile"):
            prop = getattr(bpy.ops.wm, name).get_rna_type().properties["post_read_operator"]
            self.assertEqual((prop.type, prop.is_hidden, prop.is_skip_save), ('STRING', True, True), name)


class ExecIsNotRedirectedTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        calls.clear()
        PostRead.seen.clear()
        self.folder = tempfile.mkdtemp(prefix="dt_redirect_")

    def path(self, name):
        return os.path.join(self.folder, name)

    def test_exec_saves_opens_and_reads_like_blender(self):
        bpy.context.scene.collection.objects.link(bpy.data.objects.new("Marker", None))
        bpy.ops.wm.save_as_mainfile(filepath=self.path("a.blend"))
        self.assertEqual(bpy.data.filepath, self.path("a.blend"))
        bpy.ops.wm.save_as_mainfile(filepath=self.path("copy.blend"), copy=True)
        self.assertEqual(bpy.data.filepath, self.path("a.blend"))
        bpy.ops.wm.save_mainfile()
        bpy.ops.wm.save_mainfile(incremental=True)
        self.assertEqual(os.path.basename(bpy.data.filepath), "a1.blend")
        bpy.ops.wm.open_mainfile(filepath=self.path("copy.blend"))
        self.assertIn("Marker", bpy.data.objects)
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual((bpy.data.filepath, len(bpy.data.objects)), ("", 0))
        for name in ("a.blend", "a1.blend", "copy.blend"):  # (a.blend1 is Blender's backup of the second save)
            self.assertTrue(os.path.isfile(self.path(name)), name)
        self.assertEqual(calls, [])

    def test_post_read_operator_runs_once_the_file_is_read(self):
        bpy.ops.wm.save_as_mainfile(filepath=self.path("a.blend"))
        bpy.ops.wm.read_homefile(use_empty=True, post_read_operator=PostRead.bl_idname)
        self.assertEqual(PostRead.seen, [("", 0)])
        bpy.ops.wm.open_mainfile(filepath=self.path("a.blend"), post_read_operator="TEST_OT_dasktoon_post_read")
        self.assertEqual(PostRead.seen[-1][0], self.path("a.blend"))
        with self.assertRaises(RuntimeError):
            bpy.ops.wm.open_mainfile(filepath=self.path("missing.blend"), post_read_operator=PostRead.bl_idname)
        self.assertEqual(len(PostRead.seen), 2)
        bpy.ops.wm.read_homefile(post_read_operator="test.no_such_operator")
        self.assertEqual(len(PostRead.seen), 2)
        self.assertEqual(calls, [])


class OpenRecentMenuTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_redirect_config_")
        tu.reset_scene()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_redirect_recent_"), "Proj")

    def test_open_recent_is_dasktoons_menu_with_models_then_projects(self):
        self.assertIs(bpy.types.TOPBAR_MT_file_open_recent, project_ui.TOPBAR_MT_file_open_recent)
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_file_open_recent)), ["No recent models or projects"])
        project = dtp.create_project("Proj", self.folder)
        model = dtp.new_model_path(project, "Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        dtp.add_recent_model(model)
        log = tu.draw(bpy.types.TOPBAR_MT_file_open_recent)
        self.assertEqual([entry[:3] for entry in log if entry[0] != "separator"],
                         [("label", "", "Models"), ("operator", "dasktoon.project_open_model", "Proj › Hero"),
                          ("label", "", "Projects"), ("operator", "dasktoon.project_open", "Proj")])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy, phải đỏ** — Expected: ERROR `KeyError: 'use_project_redirect'` / thiếu `TOPBAR_MT_file_open_recent`.

- [ ] **Step 4: Sửa `wm_files.cc`**

4a. Thêm `#include <initializer_list>` và `#include <string>` ngay dưới `#include <cstring>`.

4b. Ngay trước khối `/** \name Read Startup & Preferences Operator`, thêm khối:
```cpp
/* -------------------------------------------------------------------- */
/** \name DaskToon: File Operators Go Through Projects
 *
 * docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 8. When a person *invokes* New,
 * Open, Save or Save As (a menu, a shortcut, F3 search, a dialog button), the DaskToon command of the same job runs
 * instead. Exec is never redirected: scripts, add-ons, tests and DaskToon itself keep Blender's behavior, and DaskToon
 * invokes these operators with `use_project_redirect=False` when it wants Blender's own dialogs.
 * \{ */

static void wm_project_redirect_def(wmOperatorType *ot)
{
  PropertyRNA *prop = RNA_def_boolean(
      ot->srna,
      "use_project_redirect",
      true,
      "Project Redirect",
      "When invoked, hand over to the DaskToon project command that does the same job");
  RNA_def_property_flag(prop, PROP_HIDDEN | PROP_SKIP_SAVE);
}

/**
 * Invoke the DaskToon operator `idname` in place of `op` when `op` allows it and `idname` is registered, copying the
 * properties named in `forward` that are set on `op`. Returns true when `idname` took over: the caller then ends `op`.
 */
static bool wm_project_redirect(bContext *C,
                                wmOperator *op,
                                const char *idname,
                                const std::initializer_list<const char *> forward = {})
{
  if (!RNA_boolean_get(op->ptr, "use_project_redirect")) {
    return false;
  }
  wmOperatorType *ot = WM_operatortype_find(idname, true);
  if (ot == nullptr) {
    return false;
  }
  PointerRNA props = WM_operator_properties_create_ptr(ot);
  for (const char *name : forward) {
    PropertyRNA *prop_src = RNA_struct_find_property(op->ptr, name);
    PropertyRNA *prop_dst = RNA_struct_find_property(&props, name);
    if (prop_src == nullptr || prop_dst == nullptr || !RNA_property_is_set(op->ptr, prop_src)) {
      continue;
    }
    if (RNA_property_type(prop_src) == PROP_BOOLEAN) {
      RNA_property_boolean_set(&props, prop_dst, RNA_property_boolean_get(op->ptr, prop_src));
    }
    else if (RNA_property_type(prop_src) == PROP_STRING) {
      RNA_property_string_set(&props, prop_dst, RNA_property_string_get(op->ptr, prop_src).c_str());
    }
  }
  WM_operator_name_call_ptr(C, ot, wm::OpCallContext::InvokeDefault, &props, nullptr);
  WM_operator_properties_free(&props);
  return true;
}

static void wm_post_read_operator_def(wmOperatorType *ot)
{
  PropertyRNA *prop = RNA_def_string(ot->srna,
                                     "post_read_operator",
                                     nullptr,
                                     OP_MAX_TYPENAME,
                                     "Post-Read Operator",
                                     "Operator to run once the file has been read (DaskToon's New Model finishes "
                                     "in the new file this way, after Blender asked to save changes)");
  RNA_def_property_flag(prop, PROP_HIDDEN | PROP_SKIP_SAVE);
}

/** The "post_read_operator" of `op`, empty when it has none. Read it before the file read frees anything. */
static std::string wm_post_read_operator_get(wmOperator *op)
{
  PropertyRNA *prop = RNA_struct_find_property(op->ptr, "post_read_operator");
  return prop ? RNA_property_string_get(op->ptr, prop) : std::string();
}

static void wm_post_read_operator_call(bContext *C, const std::string &idname)
{
  if (idname.empty()) {
    return;
  }
  if (wmOperatorType *ot = WM_operatortype_find(idname.c_str(), true)) {
    WM_operator_name_call_ptr(C, ot, wm::OpCallContext::ExecDefault, nullptr, nullptr);
  }
}

/** \} */
```

4c. `wm_homefile_read_exec`: dòng đầu thân hàm thêm `const std::string post_read = wm_post_read_operator_get(op);`; ngay
trước `return OPERATOR_FINISHED;` cuối hàm thêm `wm_post_read_operator_call(C, post_read);`.

4d. `wm_homefile_read_invoke`: dòng đầu thân hàm thêm
```cpp
  if (wm_project_redirect(C, op, "DASKTOON_OT_model_new")) {
    return OPERATOR_CANCELLED;
  }
```

4e. `WM_OT_read_homefile`: sau `read_homefile_props(ot);` thêm `wm_project_redirect_def(ot);` và
`wm_post_read_operator_def(ot);` (không thêm vào `WM_OT_read_factory_settings`).

4f. `wm_open_mainfile_invoke` thay thân hàm bằng:
```cpp
  /* DaskToon: only a person's first call that would show the file browser; later calls come back from the
   * save-changes dialog with the state moved on, and DaskToon opens the files people chose itself. */
  if (get_operator_state(op) == OPEN_MAINFILE_STATE_DISCARD_CHANGES &&
      (RNA_boolean_get(op->ptr, "display_file_selector") ||
       !RNA_struct_property_is_set(op->ptr, "filepath")) &&
      wm_project_redirect(C, op, "DASKTOON_OT_open", {"filepath"}))
  {
    return OPERATOR_CANCELLED;
  }
  return wm_open_mainfile_dispatch(C, op);
```

4g. `wm_open_mainfile__open`: dòng đầu thân hàm thêm `const std::string post_read = wm_post_read_operator_get(op);`; trong
nhánh `if (success) {`, ngay trước `return OPERATOR_FINISHED;` thêm `wm_post_read_operator_call(C, post_read);`.

4h. `WM_OT_open_mainfile`: ngay trước `create_operator_state(ot, OPEN_MAINFILE_STATE_DISCARD_CHANGES);` thêm
`wm_project_redirect_def(ot);` và `wm_post_read_operator_def(ot);`.

4i. `wm_save_as_mainfile_invoke`: dòng đầu thân hàm thêm
```cpp
  if (wm_project_redirect(C,
                          op,
                          RNA_boolean_get(op->ptr, "copy") ? "DASKTOON_OT_model_save_copy" :
                                                             "DASKTOON_OT_model_save_as",
                          {"show_save_modified_images_dialog"}))
  {
    return OPERATOR_CANCELLED;
  }
```
và cuối `WM_OT_save_as_mainfile` thêm `wm_project_redirect_def(ot);`.

4j. `wm_save_mainfile_invoke`: dòng đầu thân hàm (trước kiểm tra cửa sổ) thêm
```cpp
  if (wm_project_redirect(C,
                          op,
                          RNA_boolean_get(op->ptr, "incremental") ? "DASKTOON_OT_model_save_incremental" :
                                                                    "DASKTOON_OT_project_save",
                          {"show_save_modified_images_dialog"}))
  {
    return OPERATOR_CANCELLED;
  }
```
và cuối `WM_OT_save_mainfile` thêm `wm_project_redirect_def(ot);`.

4k. `wm_block_file_close_save`: thay đoạn từ `bool file_has_been_saved_before = ...` tới hết khối `if/else` (trước
`if (execute_callback) {`) bằng:
```cpp
  bool file_has_been_saved_before = BKE_main_blendfile_path(bmain)[0] != '\0';
  /* DaskToon: Save saves through the project (outside textures are copied in). For a draft it opens Save to Project
   * and returns cancelled, which stops what was going on, as Blender does for a file never saved (project workflow
   * spec, section 8). */
  wmOperatorType *ot_project_save = WM_operatortype_find("DASKTOON_OT_project_save", true);

  if (file_has_been_saved_before &&
      (bmain->has_forward_compatibility_issues || bmain->colorspace.is_missing_opencolorio_config))
  {
    /* Need to invoke to get the file-browser and choose where to save the new file.
     * This also makes it impossible to keep on going with current operation, which is why
     * callback cannot be executed anymore.
     *
     * This is the same situation as what happens when the file has never been saved before
     * (outer `else` statement, below). */
    WM_operator_name_call(
        C, "WM_OT_save_as_mainfile", wm::OpCallContext::InvokeDefault, nullptr, nullptr);
    execute_callback = false;
  }
  else if (ot_project_save) {
    const wmOperatorStatus status = WM_operator_name_call_ptr(
        C, ot_project_save, wm::OpCallContext::ExecDefault, nullptr, nullptr);
    if (status & OPERATOR_CANCELLED) {
      execute_callback = false;
    }
  }
  else if (file_has_been_saved_before) {
    const wmOperatorStatus status = WM_operator_name_call(
        C, "WM_OT_save_mainfile", wm::OpCallContext::ExecDefault, nullptr, nullptr);
    if (status & OPERATOR_CANCELLED) {
      execute_callback = false;
    }
  }
  else {
    WM_operator_name_call(
        C, "WM_OT_save_mainfile", wm::OpCallContext::InvokeDefault, nullptr, nullptr);
    execute_callback = false;
  }
```

- [ ] **Step 5: Sửa ba file C++ còn lại**

`wm_splash_screen.cc`, hàm `wm_block_splash_create`:
- `block_flag_enable(block, ui::BLOCK_LOOP | ui::BLOCK_KEEP_OPEN | ui::BLOCK_NO_WIN_CLIP);` thành
  `block_flag_enable(block, ui::BLOCK_LOOP | ui::BLOCK_NO_WIN_CLIP);`
- nhánh Quick Setup thêm `block_flag_enable(block, ui::BLOCK_KEEP_OPEN);` kèm chú thích `/* Settings are changed here, so
  the Quick Setup stays open. */`; nhánh `else` (`WM_MT_splash`) thêm chú thích `/* DaskToon start screen: using one of its
  items closes it, like a menu (project workflow spec, section 5). */`.

`space_topbar.cc`:
- xóa hai hàm `recent_files_menu_draw` và `recent_files_menu_register`; chỗ gọi `recent_files_menu_register();` trong
  `ED_spacetype_topbar` thay bằng chú thích
  `/* DaskToon: "Open Recent" (TOPBAR_MT_file_open_recent) is a Python menu, scripts/startup/bl_ui/dasktoon_project.py. */`.
- `topbar_header_listener`, nhánh `case NC_WM:` thành
```cpp
    case NC_WM:
      /* DaskToon: the top bar names the open project and model, which change on save and open. */
      if (ELEM(wmn->data, ND_JOB, ND_FILESAVE, ND_FILEREAD)) {
        ED_region_tag_redraw(region);
      }
      break;
```

`interface.cc`: thay `but_event_operator_string_from_menu` bằng hai hàm, và sửa nhánh operator của
`but_event_operator_string`:
```cpp
static std::optional<std::string> but_event_operator_string_from_menu_idname(const bContext *C,
                                                                            const char *menu_idname,
                                                                            const size_t menu_idname_maxncpy)
{
  /* Dummy, name is unimportant. */
  IDProperty *prop_menu = bke::idprop::create_group(__func__).release();
  IDP_AddToGroup(prop_menu, IDP_NewStringMaxSize(menu_idname, menu_idname_maxncpy, "name"));

  const std::optional<std::string> result = WM_key_event_operator_string(
      C, "WM_OT_call_menu", wm::OpCallContext::InvokeRegionWin, prop_menu, true);

  IDP_FreeProperty(prop_menu);
  return result;
}

static std::optional<std::string> but_event_operator_string_from_menu(const bContext *C,
                                                                      Button *but)
{
  MenuType *mt = button_menutype_get(but);
  BLI_assert(mt != nullptr);
  return but_event_operator_string_from_menu_idname(C, mt->idname, sizeof(mt->idname));
}
```
```cpp
  if (but->optype != nullptr) {
    wmOperatorCallParams params = {};
    params.optype = but->optype;
    params.opptr = but->opptr;
    params.opcontext = but->opcontext;
    std::optional<std::string> result = but_event_operator_string_from_operator(C, &params);
    if (!result && STREQ(but->optype->idname, "WM_OT_read_homefile")) {
      /* DaskToon: File › New Model… runs "wm.read_homefile", which the core hands to "dasktoon.model_new". Blender's
       * keymap reaches New Model with Ctrl+N through the New menu, so show that menu's shortcut
       * (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 7). */
      static const char menu_idname[] = "TOPBAR_MT_file_new";
      result = but_event_operator_string_from_menu_idname(C, menu_idname, sizeof(menu_idname));
    }
    return result;
  }
```

- [ ] **Step 6: Build (chạy nền) và trong lúc chờ sửa Python**

Run: lệnh Build ở phần Môi trường (đóng DaskToon trước). Expected: `0 Error(s)`. Lỗi biên dịch: đọc thông báo, sửa đúng chỗ,
build lại.

Trong lúc chờ, sửa `scripts/startup/bl_ui/dasktoon_project.py`: thay lớp `TOPBAR_MT_dasktoon_project_recent` bằng
```python
class TOPBAR_MT_file_open_recent(Menu):
    # Replaces Blender's list of recent files (project workflow spec 7): recent models first, then recent projects.
    bl_idname = "TOPBAR_MT_file_open_recent"
    bl_label = "Open Recent"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        recent_models, recent_projects = dtp.recent_models(), dtp.recent_projects()
        if not recent_models and not recent_projects:
            layout.label(text="No recent models or projects")
            return
        if recent_models:
            layout.label(text="Models")
            for path in recent_models:
                project = dtp.find_project(path)
                text = "%s › %s" % (project.name, dtp.model_label(project, path)) if project else os.path.basename(path)
                layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=text, icon='FILE_BLEND',
                                translate=False).filepath = path
        if recent_projects:
            if recent_models:
                layout.separator()
            layout.label(text="Projects")
            for path in recent_projects:
                layout.operator(DASKTOON_OT_project_open.bl_idname, text=os.path.basename(os.path.dirname(path)),
                                icon='FILE_FOLDER', translate=False).filepath = path
```
Trong `TOPBAR_MT_dasktoon_project.draw` đổi `TOPBAR_MT_dasktoon_project_recent.bl_idname` thành
`TOPBAR_MT_file_open_recent.bl_idname`; trong `classes` đổi tên lớp tương ứng.

`tests/python/dasktoon_project_ui_test.py`: `test_file_menu_holds_everything_the_project_panel_had` đổi
`("menu", "TOPBAR_MT_dasktoon_project_recent")` thành `("menu", "TOPBAR_MT_file_open_recent")`;
`test_recent_and_models_submenus_list_their_files` thành
```python
    def test_recent_and_models_submenus_list_their_files(self):
        self.assertEqual(draw_menu(bpy.types.TOPBAR_MT_file_open_recent), [("label", "No recent models or projects")])
        self.assertEqual(self.create(), {'FINISHED'})
        self.assertEqual(draw_menu(bpy.types.TOPBAR_MT_file_open_recent),
                         [("label", "Projects"), ("operator", "dasktoon.project_open")])
        self.assertEqual(draw_menu(bpy.types.TOPBAR_MT_dasktoon_project_models),
                         [("operator", "dasktoon.project_open_model")])
```
`test_ui_is_registered`: trong tuple tên menu đổi `"TOPBAR_MT_dasktoon_project_recent"` thành `"TOPBAR_MT_file_open_recent"`.

`tests/python/dasktoon_ui_layout_test.py`: thêm `"TOPBAR_MT_dasktoon_project_recent"` vào `REMOVED`.

`dasktoon_translations.py`, khối `dasktoon_project.py`: thêm
```python
    "No recent models or projects": "Chưa có model hay dự án gần đây",
    "Projects": "Dự án",
```
`CMakeLists.txt`: thêm `dasktoon_file_redirect_test` vào danh sách.

- [ ] **Step 7: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_file_redirect_test.py`, `dasktoon_project_ui_test.py`, `dasktoon_project_test.py`,
`dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `dasktoon_install_test.py`.
Expected: tất cả OK.

- [ ] **Step 8: Commit**
```bash
git add source/blender/windowmanager/intern/wm_files.cc source/blender/windowmanager/intern/wm_splash_screen.cc \
        source/blender/editors/space_topbar/space_topbar.cc source/blender/editors/interface/interface.cc \
        scripts/startup/bl_ui/ tests/python/
git commit -m "feat: hand invoked New/Open/Save to DaskToon in the core, run an operator after a file read, list recent models in Open Recent"
```

---

### Task 4: Dự án trong giao diện: dự án được chọn, New/Open/Choose Project, Project Settings, menu Project và Models, nhãn thanh trên cùng

**Files:**
- Modify (viết lại): `scripts/startup/bl_ui/dasktoon_project.py`
- Modify: `scripts/startup/bl_ui/dasktoon_engine_export.py` (dùng `selected_project()`)
- Modify (viết lại): `tests/python/dasktoon_project_ui_test.py`
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: Task 1 (`dtp.*`), Task 3 (`use_project_redirect`, `TOPBAR_MT_file_open_recent`, `tu.RecordingLayout`...).
- Produces (`bl_ui.dasktoon_project`, import là `projects`/`project_ui`): `forget_session_project()`, `load_project(path)
  -> Project | None`, `select_project(project)`, `open_project() -> Project | None`, `is_draft() -> bool`,
  `selected_project() -> Project | None`, `models(project) -> list[str]` (cache 2 s), `forget_models()`,
  `engine_label(project) -> str`, `call_mode() -> 'INVOKE_DEFAULT' | 'EXEC_DEFAULT'`, `open_blend(path)`,
  `show_start_screen()`, `draw_topbar_label(layout)`; lệnh `dasktoon.project_create` (thuộc tính `name`, `location`,
  `engine_path`, ẩn `model_start_from`), `dasktoon.project_open` (`filepath`), `dasktoon.project_select` (`filepath`),
  `dasktoon.project_settings` (`name`, `engine`, `engine_path`, ẩn `then` ∈ `NONE|EXPORT|REINSTALL`),
  `dasktoon.project_open_model` (`filepath`), `dasktoon.project_export`, `dasktoon.project_reinstall_shaders`,
  `dasktoon.project_open_folder`; menu `TOPBAR_MT_file_open_recent`, `TOPBAR_MT_dasktoon_project_models` ("Models"),
  `TOPBAR_MT_dasktoon_project` ("Project", ngữ cảnh dịch `"DaskToon"`).
- Produces (`dasktoon_translations`): `VI_CONTEXT = {"DaskToon": {...}}`, đăng ký thêm các mục có ngữ cảnh riêng.

- [ ] **Step 1: Viết test (đỏ)**

File: `tests/python/dasktoon_project_ui_test.py` (thay toàn bộ)
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Projects in the interface (project workflow spec 3, 6, 7, 11): the selected project, New Project, Open Project,
choosing a project, Project Settings, Export This Model and Reinstall Shaders before Unity is linked, the Project and
Models menus, the top bar label, and the Engine Export default target."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_engine_export as export_ui  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402

SHADER = os.path.join("Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_projui_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class ProjectUITest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_projui_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        body = tu.add_sphere(segments=8, rings=4)
        body.name = "Body"
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        self.unity = fake_unity()
        self.location = tempfile.mkdtemp(prefix="dt_projui_")

    def create(self, name="Proj", unity=True):
        return bpy.ops.dasktoon.project_create(name=name, location=self.location,
                                               engine_path=self.unity if unity else "")

    def save_model(self, name="Hero"):
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(project_ui.selected_project(), name))

    def test_new_project_is_selected_and_its_location_remembered(self):
        self.assertEqual(self.create(unity=False), {'FINISHED'})
        project = project_ui.selected_project()
        self.assertEqual((project.name, project.engines), ("Proj", []))
        self.assertTrue(dtp.same_path(project.folder, os.path.join(self.location, "Proj")))
        self.assertTrue(os.path.isdir(project.models_folder))
        self.assertTrue(dtp.same_path(dtp.project_location(), self.location))
        self.assertTrue(project_ui.is_draft())

    def test_new_project_cleans_the_name_and_refuses_a_bad_unity_path(self):
        self.assertEqual(self.create(name="A:B", unity=False), {'FINISHED'})
        self.assertTrue(os.path.isdir(os.path.join(self.location, "A_B")))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_create(name="Bad", location=self.location,
                                            engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertFalse(os.path.exists(os.path.join(self.location, "Bad")))

    def test_selected_project_is_the_open_one_then_the_chosen_one_then_the_most_recent(self):
        first = dtp.create_project("First", os.path.join(self.location, "First"))
        second = dtp.create_project("Second", os.path.join(self.location, "Second"))
        self.assertEqual(project_ui.selected_project().name, "Second")
        self.assertEqual(bpy.ops.dasktoon.project_select(filepath=first.file), {'FINISHED'})
        dtp.add_recent(second.file)
        self.assertEqual(project_ui.selected_project().name, "First")
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(second, "Hero"))
        self.assertEqual(project_ui.selected_project().name, "Second")
        self.assertFalse(project_ui.is_draft())

    def test_a_broken_recent_project_is_passed_over(self):
        good = dtp.create_project("Good", os.path.join(self.location, "Good"))
        broken = dtp.create_project("Broken", os.path.join(self.location, "Broken"))
        with open(broken.file, "w", encoding="utf-8") as f:
            f.write("{")
        self.assertEqual(dtp.recent_projects()[0], broken.file)
        self.assertEqual(project_ui.selected_project().name, "Good")
        self.assertIn("Good", tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)))
        self.assertIn(("dasktoon.project_open", "Good"), tu.operators(tu.draw(bpy.types.TOPBAR_MT_file_open_recent)))
        self.assertTrue(dtp.same_path(project_ui.selected_project().file, good.file))

    def test_open_project_takes_the_file_or_the_folder(self):
        project = dtp.create_project("Opened", os.path.join(self.location, "Opened"))
        dtp.create_project("Later", os.path.join(self.location, "Later"))
        self.assertEqual(bpy.ops.dasktoon.project_open(filepath=project.folder), {'FINISHED'})
        self.assertEqual(project_ui.selected_project().name, "Opened")
        self.assertEqual(dtp.recent_projects()[0], project.file)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_open(filepath=tempfile.mkdtemp(prefix="dt_not_project_"))

    def test_project_settings_rename_and_link_unity_later(self):
        self.create(unity=False)
        self.assertEqual(bpy.ops.dasktoon.project_settings(name="Renamed", engine='UNITY_URP',
                                                           engine_path=self.unity), {'FINISHED'})
        project = project_ui.selected_project()
        self.assertEqual((project.name, project.engine_path), ("Renamed", self.unity.replace("\\", "/")))
        self.assertTrue(os.path.isfile(os.path.join(self.unity, SHADER)))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_settings(name="Renamed", engine='UNITY_URP',
                                              engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))
        self.assertEqual(project_ui.selected_project().engine_path, self.unity.replace("\\", "/"))

    def test_export_and_reinstall_wait_until_unity_is_linked_then_go_on(self):
        self.create(unity=False)
        self.save_model()
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_export()
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_reinstall_shaders()
        self.assertEqual(bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity,
                                                           then='EXPORT'), {'FINISHED'})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")))

    def test_export_this_model_writes_into_the_unity_project(self):
        self.create()
        self.save_model()
        self.assertEqual(bpy.ops.dasktoon.project_export(), {'FINISHED'})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Model", "Hero.fbx")))

    def test_reinstall_shaders_rewrites_edited_files(self):
        self.create()
        shader = os.path.join(self.unity, SHADER)
        with open(shader, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertEqual(bpy.ops.dasktoon.project_reinstall_shaders(), {'FINISHED'})
        with open(shader, encoding="utf-8") as f:
            self.assertNotEqual(f.read(), "edited")

    def test_engine_export_opens_on_a_linked_project_only(self):
        self.create(unity=False)
        self.assertNotEqual(export_ui.default_directory(bpy.context)[0], self.unity.replace("\\", "/"))
        bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity)
        self.assertEqual(export_ui.default_directory(bpy.context), (self.unity.replace("\\", "/"), 'UNITY_URP'))

    def test_project_menu(self):
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)), ["Create or open a project"])
        self.create(unity=False)
        log = tu.draw(bpy.types.TOPBAR_MT_dasktoon_project)
        self.assertEqual(tu.labels(log), ["Proj", "Engine: not linked"])
        self.assertEqual([idname for idname, _text in tu.operators(log)],
                         ["dasktoon.project_settings", "dasktoon.project_export",
                          "dasktoon.project_reinstall_shaders", "dasktoon.project_open_folder"])
        bpy.ops.dasktoon.project_settings(name="Proj", engine='UNITY_URP', engine_path=self.unity)
        labels = tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project))
        self.assertEqual(labels[1], "Engine: Unity 6 (URP)")
        self.assertTrue(labels[2].startswith("Shaders: version"))
        menu = bpy.types.TOPBAR_MT_dasktoon_project
        self.assertEqual((menu.bl_label, menu.bl_rna.translation_context), ("Project", "DaskToon"))

    def test_models_menu_lists_the_selected_projects_models(self):
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)), ["Create or open a project"])
        self.create(unity=False)
        self.assertEqual(tu.labels(tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)), ["No models yet"])
        self.save_model("Hero")
        project_ui.forget_models()
        log = tu.draw(bpy.types.TOPBAR_MT_dasktoon_project_models)
        self.assertEqual(tu.operators(log), [("dasktoon.project_open_model", "Hero")])
        self.assertEqual(log[0][3], 'RADIOBUT_ON')

    def test_open_recent_lists_models_then_projects(self):
        self.create(unity=False)
        self.save_model("Hero")
        dtp.add_recent_model(bpy.data.filepath)
        log = tu.draw(bpy.types.TOPBAR_MT_file_open_recent)
        self.assertEqual(tu.operators(log), [("dasktoon.project_open_model", "Proj › Hero"),
                                             ("dasktoon.project_open", "Proj")])

    def test_topbar_label_names_the_model_or_warns_about_a_draft(self):
        layout = tu.RecordingLayout()
        project_ui.draw_topbar_label(layout)
        self.assertEqual([entry[2:4] for entry in layout.log], [("Draft (not in a project)", 'ERROR')])
        self.create(unity=False)
        self.save_model("Hero_Armor")
        layout = tu.RecordingLayout()
        project_ui.draw_topbar_label(layout)
        self.assertEqual([entry[2:4] for entry in layout.log], [("Proj › Hero_Armor", 'FILE_FOLDER')])

    def test_ui_is_registered(self):
        for name in ("TOPBAR_MT_dasktoon_project", "TOPBAR_MT_file_open_recent", "TOPBAR_MT_dasktoon_project_models",
                     "DASKTOON_OT_project_select", "DASKTOON_OT_project_settings"):
            self.assertTrue(hasattr(bpy.types, name), name)
        ours = [f for f in bpy.types.TOPBAR_MT_file._dyn_ui_initialize()
                if getattr(f, "__module__", "") == project_ui.__name__]
        self.assertEqual(ours, [])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL/ERROR (`location` không có, `selected_project` chưa có...).

- [ ] **Step 3: Viết lại module giao diện dự án**

File: `scripts/startup/bl_ui/dasktoon_project.py` (thay toàn bộ)
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects in the interface (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections
3, 6, 7 and 11): the selected project, New Project, Open Project, Project Settings, Export This Model, Reinstall Shaders,
Open Project Folder, the Open Recent, Models and Project menus of File, and the top bar label."""

import os
import time

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Menu, Operator

from dasktoon_export import targets
from dasktoon_project import project as dtp

_session = {"project_file": ""}  # the project chosen this session: start screen, Open Project, New Project
_models_cache = {"key": None, "time": 0.0, "models": []}
MODELS_REFRESH = 2.0  # seconds; menus redraw often and must not walk the folder every time
THEN = (('NONE', "", ""), ('EXPORT', "", ""), ('REINSTALL', "", ""))  # what Project Settings runs once Unity is linked


def forget_session_project():
    _session["project_file"] = ""
    _models_cache["key"] = None


def load_project(path):
    """The project at `path` (its file or its folder), or None when it is gone or unreadable."""
    try:
        return dtp.load(path)
    except (OSError, ValueError):
        return None


def select_project(project):
    """`project` becomes the selected project of this session and the most recent one."""
    _session["project_file"] = project.file
    dtp.add_recent(project.file)


def open_project():
    """The project that holds the open .blend file; None for a draft (spec 3)."""
    return dtp.find_project(bpy.data.filepath)


def is_draft():
    return open_project() is None


def selected_project():
    """The open project; for a draft, the project chosen last this session, else the most recent one (spec 3)."""
    project = open_project()
    if project is not None:
        return project
    for path in [_session["project_file"]] + dtp.recent_projects():
        project = load_project(path) if path else None
        if project is not None:
            return project
    return None


def models(project):
    """dtp.project_models(project), cached for MODELS_REFRESH seconds."""
    now = time.monotonic()
    if _models_cache["key"] != project.folder or now - _models_cache["time"] > MODELS_REFRESH:
        _models_cache.update(key=project.folder, time=now, models=dtp.project_models(project))
    return _models_cache["models"]


def forget_models():
    _models_cache["key"] = None


def engine_label(project):
    """"Engine: Unity 6 (URP)", or "Engine: not linked" until a Unity project is linked (spec 11)."""
    if not project.engines:
        return iface_("Engine: not linked")
    names = {key: label for key, label, _desc in targets.ENGINES}
    return iface_("Engine: %s") % iface_(names.get(project.engine, project.engine))


def call_mode():
    """How DaskToon calls Blender's file operators: invoked when a window can show Blender's dialogs (save changes,
    modified images), executed otherwise (background, scripts)."""
    return 'INVOKE_DEFAULT' if bpy.context.window is not None else 'EXEC_DEFAULT'


def open_blend(path):
    """Open `path` as Blender does from a menu, asking to save changes first: a model when it lies in a project, a draft
    otherwise (spec 9). use_project_redirect=False: the core must not hand this back to DaskToon."""
    bpy.ops.wm.open_mainfile(call_mode(), filepath=path, display_file_selector=False, use_project_redirect=False)


def show_start_screen():
    if bpy.context.window is not None:
        bpy.ops.wm.splash('INVOKE_DEFAULT')


def draw_topbar_label(layout):
    """Top bar, before the scene selector (spec 7): "Hero › Hero_Armor" for a model of a project, a warning for a
    draft."""
    project = open_project()
    if project is None:
        layout.label(text="Draft (not in a project)", icon='ERROR')
        return
    model = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    layout.label(text="%s › %s" % (project.name, model), icon='FILE_FOLDER', translate=False)


def _choose(op, project):
    select_project(project)
    forget_models()
    op.report({'INFO'}, rpt_("Opened project %s") % project.name)
    show_start_screen()
    return {'FINISHED'}


def _linked_project(op, then):
    """The selected project when a Unity project is linked to it. Otherwise Project Settings opens to link one, and runs
    `then` afterwards (spec 11); returns None."""
    project = selected_project()
    if project is None:
        op.report({'ERROR'}, rpt_("No DaskToon project is open"))
        return None
    if not project.engines:
        if bpy.context.window is not None:
            bpy.ops.dasktoon.project_settings('INVOKE_DEFAULT', then=then)
        else:
            op.report({'ERROR'}, rpt_("Project %s is not linked to a Unity project yet: link it in Project Settings")
                      % project.name)
        return None
    return project


class DASKTOON_OT_project_create(Operator):
    """Create a DaskToon project: a folder with Models/ and Textures/; link a Unity project now or later"""
    bl_idname = "dasktoon.project_create"
    bl_label = "New Project"

    name: StringProperty(name="Name", default="New Project")
    location: StringProperty(name="Location", subtype='DIR_PATH',
                             description="The folder that receives the project folder")
    engine_path: StringProperty(name="Unity Project", subtype='DIR_PATH',
                                description="Optional: the Unity project models are exported to (link it later in "
                                            "Project Settings)")
    model_start_from: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})  # passed on to New Model

    def invoke(self, context, _event):
        if not self.location:
            self.location = dtp.project_location()
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, context):
        location = bpy.path.abspath(self.location) if self.location else dtp.project_location()
        engine_path = bpy.path.abspath(self.engine_path) if self.engine_path else ""
        try:
            name = dtp.clean_name(self.name)
            project = dtp.create_project(name, os.path.join(location, name), engine_path)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        dtp.set_project_location(location)
        select_project(project)
        forget_models()
        self.report({'INFO'}, rpt_("Created project %s") % project.name)
        if context.window is not None:
            options = {"name": dtp.free_model_name(project, project.name)}
            if self.model_start_from:
                options["start_from"] = self.model_start_from
            bpy.ops.dasktoon.model_new('INVOKE_DEFAULT', **options)
        return {'FINISHED'}


class DASKTOON_OT_project_open(Operator):
    """Open a DaskToon project (its dasktoon_project.json or its folder) and show its models on the start screen"""
    bl_idname = "dasktoon.project_open"
    bl_label = "Open Project"

    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    filter_glob: StringProperty(default=dtp.PROJECT_FILE, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self, context, _event):
        if self.filepath and os.path.exists(self.filepath):
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        try:
            project = dtp.load(self.filepath)
        except ValueError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        except OSError:
            self.report({'ERROR'}, rpt_("%s is not a DaskToon project") % self.filepath)
            return {'CANCELLED'}
        return _choose(self, project)


class DASKTOON_OT_project_select(Operator):
    """Choose this project: the start screen shows its models"""
    bl_idname = "dasktoon.project_select"
    bl_label = "Choose Project"
    bl_options = {'INTERNAL'}

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, _context):
        project = load_project(self.filepath)
        if project is None:
            self.report({'ERROR'}, rpt_("%s is not a DaskToon project") % self.filepath)
            return {'CANCELLED'}
        return _choose(self, project)


class DASKTOON_OT_project_settings(Operator):
    """Rename the project and link it to a Unity project; the DaskToon shaders are installed when the link is new or changes"""
    bl_idname = "dasktoon.project_settings"
    bl_label = "Project Settings"

    name: StringProperty(name="Name")
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    engine_path: StringProperty(name="Unity Project", subtype='DIR_PATH',
                                description="The Unity project models are exported to; leave empty to unlink")
    then: EnumProperty(items=THEN, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, _context):
        return selected_project() is not None

    def invoke(self, context, _event):
        project = selected_project()
        self.name = project.name
        if project.engines:
            if project.engine in {key for key, _label, _desc in targets.ENGINES}:
                self.engine = project.engine
            self.engine_path = project.engine_path
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        project = selected_project()
        try:
            project.name = dtp.clean_name(self.name)
            path = bpy.path.abspath(self.engine_path) if self.engine_path else ""
            warnings = dtp.link_engine(project, self.engine, path)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, rpt_("Saved the settings of project %s") % project.name)
        try:
            if project.engines and self.then == 'EXPORT':
                return bpy.ops.dasktoon.project_export()
            if project.engines and self.then == 'REINSTALL':
                return bpy.ops.dasktoon.project_reinstall_shaders()
        except RuntimeError:
            return {'CANCELLED'}  # the command reported why
        return {'FINISHED'}


class DASKTOON_OT_project_open_model(Operator):
    """Open this model of the project (DaskToon asks to save the current file first when it has changes)"""
    bl_idname = "dasktoon.project_open_model"
    bl_label = "Open"

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, _context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, rpt_("File not found: %s") % self.filepath)
            return {'CANCELLED'}
        open_blend(self.filepath)
        return {'FINISHED'}


class DASKTOON_OT_project_export(Operator):
    """Export this file's model, materials and shaders straight into the project's Unity project"""
    bl_idname = "dasktoon.project_export"
    bl_label = "Export This Model"

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        project = _linked_project(self, 'EXPORT')
        if project is None:
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, selected_only=False)
        if not objects:
            self.report({'ERROR'}, rpt_("This file has no object to export"))
            return {'CANCELLED'}
        target = dtp.project_target(project, targets.blend_name(bpy.data.filepath))
        rep = dasktoon_export.export_model(context, target, objects, dasktoon_export.ExportOptions())
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


class DASKTOON_OT_project_reinstall_shaders(Operator):
    """Write the DaskToon shaders into the project's Unity project again"""
    bl_idname = "dasktoon.project_reinstall_shaders"
    bl_label = "Reinstall Shaders"

    def execute(self, _context):
        project = _linked_project(self, 'REINSTALL')
        if project is None:
            return {'CANCELLED'}
        _written, warnings = dtp.install_project_shaders(project, force=True)
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, rpt_("Reinstalled the shaders into %s") % project.engine_path)
        return {'FINISHED'}


class DASKTOON_OT_project_open_folder(Operator):
    """Open the project folder in the file manager"""
    bl_idname = "dasktoon.project_open_folder"
    bl_label = "Open Project Folder"

    def execute(self, _context):
        project = selected_project()
        if project is None:
            self.report({'ERROR'}, rpt_("No DaskToon project is open"))
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=project.folder)
        return {'FINISHED'}


class TOPBAR_MT_file_open_recent(Menu):
    # Replaces Blender's list of recent files (project workflow spec 7): recent models first, then recent projects.
    bl_idname = "TOPBAR_MT_file_open_recent"
    bl_label = "Open Recent"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        recent_models, recent_projects = dtp.recent_models(), dtp.recent_projects()
        if not recent_models and not recent_projects:
            layout.label(text="No recent models or projects")
            return
        if recent_models:
            layout.label(text="Models")
            for path in recent_models:
                project = dtp.find_project(path)
                text = "%s › %s" % (project.name, dtp.model_label(project, path)) if project else os.path.basename(path)
                layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=text, icon='FILE_BLEND',
                                translate=False).filepath = path
        if recent_projects:
            if recent_models:
                layout.separator()
            layout.label(text="Projects")
            for path in recent_projects:
                layout.operator(DASKTOON_OT_project_open.bl_idname, text=os.path.basename(os.path.dirname(path)),
                                icon='FILE_FOLDER', translate=False).filepath = path


class TOPBAR_MT_dasktoon_project_models(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project_models"
    bl_label = "Models"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        project = selected_project()
        if project is None:
            layout.label(text="Create or open a project")
            return
        found = models(project)
        if not found:
            layout.label(text="No models yet")
        for path in found:
            current = bool(bpy.data.filepath) and dtp.same_path(path, bpy.data.filepath)
            layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=dtp.model_label(project, path),
                            icon='RADIOBUT_ON' if current else 'FILE_BLEND', translate=False).filepath = path


class TOPBAR_MT_dasktoon_project(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project"
    bl_label = "Project"
    # Blender's Vietnamese for "Project" in the default context means "projection".
    bl_translation_context = "DaskToon"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        project = selected_project()
        if project is None:
            layout.label(text="Create or open a project")
            return
        layout.label(text=project.name, icon='FILE_FOLDER', translate=False)
        layout.label(text=engine_label(project), translate=False)
        if project.engines:
            version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
            layout.label(text=(iface_("Shaders: version %d") % version) if version else iface_("Shaders: not installed"),
                         icon='CHECKMARK' if version else 'ERROR', translate=False)
        layout.separator()
        layout.operator(DASKTOON_OT_project_settings.bl_idname, text="Project Settings…", icon='PREFERENCES')
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        layout.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        layout.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')


classes = (
    DASKTOON_OT_project_create,
    DASKTOON_OT_project_open,
    DASKTOON_OT_project_select,
    DASKTOON_OT_project_settings,
    DASKTOON_OT_project_open_model,
    DASKTOON_OT_project_export,
    DASKTOON_OT_project_reinstall_shaders,
    DASKTOON_OT_project_open_folder,
    TOPBAR_MT_file_open_recent,
    TOPBAR_MT_dasktoon_project_models,
    TOPBAR_MT_dasktoon_project,
)
```
(Module không còn `register`/`unregister`: File vẽ thẳng các menu này từ Task 7. Giữa Task 4 và Task 7, menu File chưa có
mục Project; đó là bước trung gian chấp nhận được.)

`scripts/startup/bl_ui/dasktoon_engine_export.py`, `default_directory`: `dasktoon_project.active_project()` thành
`dasktoon_project.selected_project()`.

- [ ] **Step 4: Bản dịch, kể cả ngữ cảnh riêng**

`dasktoon_translations.py`:
- `KEEP` thêm `"Engine: %s"`.
- Sau `VI`, thêm:
```python
# Words that need their own translation context, because Blender's own translation of the same word in the default
# context means something else here, and Blender's translation always wins in that context.
VI_CONTEXT = {
    "DaskToon": {
        "Project": "Dự án",
    },
}
```
- `_table()` thành:
```python
def _table():
    table = {}
    for msgid, msgstr in VI.items():
        for context in ("*", "Operator"):
            table[(context, msgid)] = msgstr
    for context, entries in VI_CONTEXT.items():
        for msgid, msgstr in entries.items():
            table[(context, msgid)] = msgstr
    return {"vi_VN": table}
```
- Khối `# bl_ui/dasktoon_project.py ...`: xóa `"DaskToon Project"`, `"Create DaskToon Project"`,
  `"Create a DaskToon project linked to a Unity project and install the DaskToon shaders into it"`, `"Project Folder"`,
  `"Open DaskToon Project"`, `"Open a DaskToon project (dasktoon_project.json)"`,
  `"Open this .blend file of the project (DaskToon asks to save the current file first when it has changes)"`; thêm:
```python
    "New Project": "Tạo dự án",
    "Create a DaskToon project: a folder with Models/ and Textures/; link a Unity project now or later":
        "Tạo dự án DaskToon: một thư mục có Models/ và Textures/; gắn project Unity ngay hoặc để sau",
    "The folder that receives the project folder": "Thư mục sẽ chứa thư mục dự án",
    "Optional: the Unity project models are exported to (link it later in Project Settings)":
        "Không bắt buộc: project Unity nhận model khi xuất (có thể gắn sau trong Cài đặt dự án)",
    "Open Project": "Mở dự án",
    "Open a DaskToon project (its dasktoon_project.json or its folder) and show its models on the start screen":
        "Mở một dự án DaskToon (file dasktoon_project.json hoặc thư mục của nó) và hiện các model của nó ở màn hình đầu",
    "%s is not a DaskToon project": "%s không phải dự án DaskToon",
    "Choose Project": "Chọn dự án",
    "Choose this project: the start screen shows its models": "Chọn dự án này: màn hình đầu hiện các model của nó",
    "Project Settings": "Cài đặt dự án",
    "Project Settings…": "Cài đặt dự án…",
    "Rename the project and link it to a Unity project; the DaskToon shaders are installed when the link is new or changes":
        "Đổi tên dự án và gắn với một project Unity; shader DaskToon được cài khi gắn mới hoặc đổi project",
    "The Unity project models are exported to; leave empty to unlink":
        "Project Unity nhận model khi xuất; để trống để bỏ gắn",
    "Saved the settings of project %s": "Đã lưu cài đặt của dự án %s",
    "Project %s is not linked to a Unity project yet: link it in Project Settings":
        "Dự án %s chưa gắn với project Unity: hãy gắn trong Cài đặt dự án",
    "Open this model of the project (DaskToon asks to save the current file first when it has changes)":
        "Mở model này của dự án (DaskToon hỏi lưu file hiện tại trước nếu file có thay đổi)",
    "File not found: %s": "Không tìm thấy file: %s",
    "Create or open a project": "Hãy tạo hoặc mở một dự án",
    "No models yet": "Chưa có model nào",
    "Engine: not linked": "Engine: chưa gắn",
    "Draft (not in a project)": "Bản nháp (chưa thuộc dự án)",
```
Thêm vào `dasktoon_translations_test.py`, lớp `TranslationTest`:
```python
    def test_project_has_its_own_vietnamese_word(self):
        with iu.language('vi_VN'):
            self.assertEqual(bpy.app.translations.pgettext_iface("Project", "DaskToon"), "Dự án")
```

- [ ] **Step 5: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_project_ui_test.py`, `dasktoon_file_redirect_test.py`, `dasktoon_engine_export_ui_test.py`,
`dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`. Expected: tất cả OK.

- [ ] **Step 6: Commit**
```bash
git add scripts/startup/bl_ui/ tests/python/
git commit -m "feat: choose, open and set up projects; link Unity later; Project, Models and Open Recent menus"
```

---

### Task 5: New Model với bốn cảnh khởi đầu

**Files:**
- Create: `scripts/modules/dasktoon_project/scene.py`
- Create: `scripts/startup/bl_ui/dasktoon_model.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_model"` vào `_modules`, ngay sau `"dasktoon_project"`)
- Create: `tests/python/dasktoon_model_test.py`
- Modify: `tests/python/CMakeLists.txt`, `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: Task 1 (`dtp`), Task 2 (`dtt.collect`, `relink_absolute`, `unsaved_images`), Task 3 (`post_read_operator`,
  `use_project_redirect`), Task 4 (`projects.selected_project`, `select_project`, `load_project`, `models`,
  `forget_models`, `is_draft`, `call_mode`).
- Produces (`dasktoon_project.scene`, import là `dts`): `build(scene) -> (sun, camera)`, `ENGINE = 'DASKTOON_ANIME'`.
- Produces (`bl_ui.dasktoon_model`, import là `model_ui`): `START_FROM`; `keeps_current(draft, filepath, dirty) -> bool`;
  `save_into(op, project, path, copy=False) -> dtt.Collected | None`; `report_textures(op, collected)`;
  lệnh `dasktoon.model_new` (`name`, `start_from` ∈ `DASKTOON|EMPTY|CURRENT|COPY`, `copy_from` = đường dẫn tương đối
  trong dự án như `"Models/A.blend"`), `dasktoon.model_new_finish` (INTERNAL).

- [ ] **Step 1: Viết test (đỏ)**

File: `tests/python/dasktoon_model_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models (project workflow spec 6, 12): New Model and its four starting scenes, model names, and what stops it."""

import os
import sys
import tempfile
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_model as model_ui  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_export import textures as png  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def write_png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png.png_bytes(2, 2, bytes((255, 0, 0, 255)) * 4))
    return path


def read(path):
    with open(path, "rb") as f:
        return f.read()


class ModelTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_model_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        self.base = tempfile.mkdtemp(prefix="dt_model_")
        self.project = dtp.create_project("Hero", os.path.join(self.base, "Hero"))
        project_ui.select_project(self.project)

    def model(self, name):
        return os.path.join(self.project.models_folder, name + ".blend")

    def assertOpen(self, path):
        self.assertTrue(dtp.same_path(bpy.data.filepath, path), bpy.data.filepath)


class NewModelTest(ModelTestCase):
    def test_dasktoon_scene_has_a_sun_a_camera_on_the_origin_and_the_dasktoon_look(self):
        tu.add_sphere(segments=8, rings=4)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Hero", start_from='DASKTOON'), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        scene = bpy.context.scene
        self.assertEqual(sorted((obj.type, obj.name) for obj in scene.objects), [('CAMERA', "Camera"), ('LIGHT', "Sun")])
        self.assertEqual(scene.objects["Sun"].data.type, 'SUN')
        camera = scene.camera
        self.assertEqual(camera.name, "Camera")
        view = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        self.assertAlmostEqual(view.angle(-camera.location), 0.0, places=4)
        self.assertEqual((scene.render.engine, scene.view_settings.view_transform), ('DASKTOON_ANIME', 'Standard'))
        self.assertTrue(os.path.isfile(self.model("Hero")))

    def test_empty_scene_is_empty(self):
        tu.add_sphere(segments=8, rings=4)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Blank", start_from='EMPTY'), {'FINISHED'})
        self.assertOpen(self.model("Blank"))
        self.assertEqual(len(bpy.data.objects), 0)

    def test_current_scene_becomes_the_model(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        self.assertEqual(bpy.ops.dasktoon.model_new(name="Body Model", start_from='CURRENT'), {'FINISHED'})
        self.assertOpen(self.model("Body Model"))
        self.assertIn("Body", bpy.data.objects)

    def test_copy_of_model_starts_from_the_chosen_model(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        bpy.ops.dasktoon.model_new(name="A", start_from='CURRENT')
        before = read(self.model("A"))
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual(bpy.ops.dasktoon.model_new(name="B", start_from='COPY', copy_from="Models/A.blend"),
                         {'FINISHED'})
        self.assertOpen(self.model("B"))
        self.assertIn("Body", bpy.data.objects)
        self.assertEqual(read(self.model("A")), before)

    def test_a_model_name_is_taken_whatever_the_case(self):
        bpy.ops.dasktoon.model_new(name="Hero", start_from='EMPTY')
        before = read(self.model("Hero"))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="hero", start_from='CURRENT')
        self.assertEqual(read(self.model("Hero")), before)

    def test_odd_characters_become_underscores_and_vietnamese_names_work(self):
        image = bpy.data.images.load(write_png(os.path.join(self.base, "Ảnh nguồn", "da.png")))
        image.use_fake_user = True
        self.assertEqual(bpy.ops.dasktoon.model_new(name='Nhân vật: "A"?', start_from='CURRENT'), {'FINISHED'})
        self.assertOpen(self.model("Nhân vật_ _A__"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "da.png")))
        self.assertTrue(bpy.data.images["da.png"].filepath_raw.startswith("//"))

    def test_a_file_in_the_way_of_models_is_reported(self):
        os.rmdir(self.project.models_folder)
        with open(self.project.models_folder, "wb") as f:
            f.write(b"not a folder")
        tu.add_sphere(segments=8, rings=4)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="Hero", start_from='CURRENT')
        self.assertEqual(bpy.data.filepath, "")

    def test_without_a_project_new_model_reports_it(self):
        project_ui.forget_session_project()
        os.remove(os.path.join(dtp.config_dir(), dtp.RECENT_FILE))
        self.assertIsNone(project_ui.selected_project())
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_new(name="Hero", start_from='EMPTY')

    def test_current_scene_is_the_default_for_a_draft_worth_keeping(self):
        self.assertFalse(model_ui.keeps_current(True, "", False))
        self.assertTrue(model_ui.keeps_current(True, "", True))
        self.assertTrue(model_ui.keeps_current(True, "D:/outside/a.blend", False))
        self.assertFalse(model_ui.keeps_current(False, "D:/Hero/Models/a.blend", True))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: ERROR `ImportError: cannot import name 'dasktoon_model'`.

- [ ] **Step 3: Viết cảnh DaskToon**

File: `scripts/modules/dasktoon_project/scene.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon Scene a new model can start from (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md,
section 6): no cube, a Sun so face shading and Light Vector follow it, a camera looking at the origin, the DaskToon
Anime engine and the Standard view."""

import math

import bpy
from mathutils import Vector

ENGINE = 'DASKTOON_ANIME'
SUN_LOCATION = (2.0, -2.0, 4.0)
SUN_ROTATION = (math.radians(50.0), 0.0, math.radians(30.0))
CAMERA_LOCATION = (0.0, -8.0, 2.0)


def build(scene):
    """Add the Sun and the camera to `scene` (expected empty) and set its engine and view. Returns (sun, camera)."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.location = SUN_LOCATION
    sun.rotation_euler = SUN_ROTATION
    scene.collection.objects.link(sun)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.location = CAMERA_LOCATION
    camera.rotation_euler = (-Vector(CAMERA_LOCATION)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = ENGINE
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    return sun, camera
```

- [ ] **Step 4: Viết module model (phần New Model)**

File: `scripts/startup/bl_ui/dasktoon_model.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models and drafts (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections 6, 8, 9, 10 and
12). A person's New, Open and Save reach these commands from DaskToon's menus, or from Blender's operators, which the
core hands over when they are invoked (source/blender/windowmanager/intern/wm_files.cc, "use_project_redirect")."""

import os

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from dasktoon_project import project as dtp, scene as dts, textures as dtt
from . import dasktoon_project as projects

START_FROM = (
    ('DASKTOON', n_("DaskToon Scene"),
     n_("An empty scene with a Sun, a camera looking at the origin, the DaskToon Anime engine and the Standard view")),
    ('EMPTY', n_("Empty Scene"), n_("A completely empty scene")),
    ('CURRENT', n_("Current Scene"), n_("Save the scene that is open now as the new model")),
    ('COPY', n_("Copy of Model"), n_("Start from a copy of another model of the project")),
)
_pending = {}  # the New Model waiting for the file read it asked for (DASKTOON_OT_model_new_finish)
_enum_items = {"models": [], "projects": []}  # Blender needs the strings of dynamic enum items kept alive


def keeps_current(draft, filepath, dirty):
    """True when New Model should start from the current scene: a draft that is a file from outside any project, or
    that has unsaved changes. The untouched scene DaskToon opens with starts from the DaskToon Scene instead (spec 6)."""
    return draft and (bool(filepath) or dirty)


def report_textures(op, collected):
    """The status bar line about copied textures; reported last so the status bar shows it (spec 10)."""
    if collected.summary():
        op.report({'INFO'}, collected.summary())


def save_into(op, project, path, copy=False):
    """Copy outside textures into `project` (spec 10) and write the open scene to `path`, a new file of the project,
    with exec so no Blender dialog shows: images with unsaved paint changes are named in warnings instead (spec 12).
    Without `copy`, `path` becomes the open file. Returns the textures report, or None when nothing was written."""
    collected = dtt.collect(project)
    for warning in collected.warnings:
        op.report({'WARNING'}, warning)
    for name in dtt.unsaved_images():
        op.report({'WARNING'}, rpt_("Image %s has unsaved paint changes: save it with Image › Save") % name)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=copy, relative_remap=True)
        if not copy and dtt.relink_absolute(collected.images):
            bpy.ops.wm.save_mainfile()
    except RuntimeError as ex:
        op.report({'ERROR'}, str(ex))
        return None
    projects.forget_models()
    return collected


def _model_items(_self, _context):
    items = _enum_items["models"]
    items.clear()
    project = projects.selected_project()
    if project is not None:
        for path in projects.models(project):
            items.append((os.path.relpath(path, project.folder).replace(os.sep, "/"), dtp.model_label(project, path), ""))
    if not items:
        items.append(('NONE', iface_("No models yet"), ""))
    return items


class DASKTOON_OT_model_new(Operator):
    """Create a model in the selected project: Models/<name>.blend, saved at once and opened"""
    bl_idname = "dasktoon.model_new"
    bl_label = "New Model"

    name: StringProperty(name="Name", default="Untitled")
    start_from: EnumProperty(name="Start From", items=START_FROM, default='DASKTOON')
    copy_from: EnumProperty(name="Model", items=_model_items)

    def invoke(self, context, _event):
        project = projects.selected_project()
        if project is None:
            bpy.ops.dasktoon.project_create('INVOKE_DEFAULT')
            return {'CANCELLED'}
        if not self.properties.is_property_set("name"):
            self.name = dtp.free_model_name(project, project.name)
        if not self.properties.is_property_set("start_from"):
            keep = keeps_current(projects.is_draft(), bpy.data.filepath, bpy.data.is_dirty)
            self.start_from = 'CURRENT' if keep else 'DASKTOON'
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "name")
        layout.prop(self, "start_from")
        if self.start_from == 'COPY':
            layout.prop(self, "copy_from")

    def execute(self, _context):
        project = projects.selected_project()
        if project is None:
            self.report({'ERROR'}, rpt_("Create or open a project first"))
            return {'CANCELLED'}
        source = ""
        if self.start_from == 'COPY':
            source = os.path.join(project.folder, *self.copy_from.split("/"))
            if self.copy_from == 'NONE' or not os.path.isfile(source):
                self.report({'ERROR'}, rpt_("Choose the model to copy"))
                return {'CANCELLED'}
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        projects.select_project(project)
        if self.start_from == 'CURRENT':
            collected = save_into(self, project, path)
            if collected is None:
                return {'CANCELLED'}
            self.report({'INFO'}, rpt_("Created model %s") % dtp.model_label(project, path))
            report_textures(self, collected)
            return {'FINISHED'}
        # The other starts leave the open file: Blender's own operator asks to save changes first (invoked), then reads
        # the file, then runs the finishing command from the core (post_read_operator). Cancelling never finishes.
        _pending.clear()
        _pending.update(project=project.file, path=path, start_from=self.start_from)
        finish = DASKTOON_OT_model_new_finish.bl_idname
        if source:
            bpy.ops.wm.open_mainfile(projects.call_mode(), filepath=source, display_file_selector=False,
                                     use_project_redirect=False, post_read_operator=finish)
        else:
            bpy.ops.wm.read_homefile(projects.call_mode(), use_empty=True, use_project_redirect=False,
                                     post_read_operator=finish)
        return {'FINISHED'}


class DASKTOON_OT_model_new_finish(Operator):
    """Finish New Model once the startup file or the model to copy has been read"""
    bl_idname = "dasktoon.model_new_finish"
    bl_label = "Finish New Model"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        request = dict(_pending)
        _pending.clear()
        project = projects.load_project(request["project"]) if request else None
        if project is None:
            return {'CANCELLED'}
        if os.path.exists(request["path"]):
            self.report({'ERROR'}, rpt_("The project already has a model named %s")
                        % dtp.model_label(project, request["path"]))
            return {'CANCELLED'}
        if request["start_from"] == 'DASKTOON':
            dts.build(context.scene)
        collected = save_into(self, project, request["path"])
        if collected is None:
            return {'CANCELLED'}
        projects.select_project(project)
        self.report({'INFO'}, rpt_("Created model %s") % dtp.model_label(project, request["path"]))
        report_textures(self, collected)
        return {'FINISHED'}


classes = (
    DASKTOON_OT_model_new,
    DASKTOON_OT_model_new_finish,
)
```
`bl_ui/__init__.py`: thêm `"dasktoon_model",` ngay sau `"dasktoon_project",`.

- [ ] **Step 5: Bản dịch và đăng ký test**

Thêm khối mới vào `VI`:
```python
    # bl_ui/dasktoon_model.py
    "New Model": "Tạo model",
    "New Model…": "Tạo model…",
    "Create a model in the selected project: Models/<name>.blend, saved at once and opened":
        "Tạo model trong dự án đang chọn: Models/<tên>.blend, được lưu ngay và mở ra",
    "Start From": "Bắt đầu từ",
    "DaskToon Scene": "Cảnh DaskToon",
    "An empty scene with a Sun, a camera looking at the origin, the DaskToon Anime engine and the Standard view":
        "Cảnh trống có một Sun, một camera nhìn vào gốc tọa độ, engine DaskToon Anime và view Standard",
    "A completely empty scene": "Cảnh trống hoàn toàn",
    "Current Scene": "Cảnh hiện tại",
    "Save the scene that is open now as the new model": "Lưu cảnh đang mở làm model mới",
    "Copy of Model": "Bản sao của model",
    "Start from a copy of another model of the project": "Bắt đầu từ bản sao của một model khác trong dự án",
    "Create or open a project first": "Hãy tạo hoặc mở một dự án trước",
    "Choose the model to copy": "Hãy chọn model để sao chép",
    "Created model %s": "Đã tạo model %s",
    "Finish New Model": "Hoàn tất tạo model",
    "Finish New Model once the startup file or the model to copy has been read":
        "Hoàn tất tạo model sau khi đã đọc file khởi động hoặc model cần sao chép",
    "Image %s has unsaved paint changes: save it with Image › Save":
        "Ảnh %s có nét vẽ chưa lưu: hãy lưu bằng Image › Save",
```
`CMakeLists.txt`: thêm `dasktoon_model_test` (sau `dasktoon_file_redirect_test`).
`tests/python/dasktoon_translations_test.py`: thêm `"scripts/startup/bl_ui/dasktoon_model.py"` và
`"scripts/modules/dasktoon_project/scene.py"` vào `TRANSLATED`.

- [ ] **Step 6: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_model_test.py`, `dasktoon_translations_test.py`, `dasktoon_ui_layout_test.py`.
Expected: tất cả OK.

- [ ] **Step 7: Commit**
```bash
git add scripts/modules/dasktoon_project/scene.py scripts/startup/bl_ui/ tests/python/
git commit -m "feat: New Model from a DaskToon scene, an empty scene, the current scene or a copy of a model"
```

---

### Task 6: Open, Save, Save to Project, Save Model As, Save Copy, Save Incremental, bản nháp, model gần đây

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_model.py`
- Modify: `tests/python/dasktoon_model_test.py`
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: Task 5 (`save_into`, `report_textures`, `_enum_items`), Task 4 (`projects.*`), Task 2, Task 1.
- Produces (`bl_ui.dasktoon_model`): `save_here(op, mode, filepath="") -> set`; `remember(filepath)`;
  handler `remember_on_file_change` (load_post, save_post); lệnh `dasktoon.open` (`filepath`), `dasktoon.project_save`
  (ẩn `show_save_modified_images_dialog`), `dasktoon.save_to_project` (`project` = đường dẫn file dự án, `name`),
  `dasktoon.model_save_as` (`name`), `dasktoon.model_save_copy` (`name`), `dasktoon.model_save_incremental`
  (ẩn `show_save_modified_images_dialog`).

- [ ] **Step 1: Viết test (đỏ)**

Trong `tests/python/dasktoon_model_test.py`: docstring đầu file thành `"""Models and drafts (project workflow spec 4, 6, 9,
10, 12): New Model and its four starting scenes, Open, Save, Save to Project, Save Model As, Save Copy, Save Incremental,
drafts and the recent models."""`; thêm các lớp sau trước `if __name__ == "__main__":`
```python
class DraftTest(ModelTestCase):
    def outside(self, name):
        path = os.path.join(self.base, "outside", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def test_unsaved_scenes_and_outside_files_are_drafts(self):
        self.assertTrue(project_ui.is_draft())
        bpy.ops.wm.save_as_mainfile(filepath=self.outside("a.blend"))
        self.assertTrue(project_ui.is_draft())
        bpy.ops.wm.save_as_mainfile(filepath=self.model("A"))
        self.assertFalse(project_ui.is_draft())

    def test_save_to_project_saves_a_copy_and_leaves_the_draft_file_alone(self):
        tu.add_sphere(segments=8, rings=4).name = "Body"
        draft = self.outside("draft.blend")
        bpy.ops.wm.save_as_mainfile(filepath=draft)
        before = read(draft)
        tu.add_plane().name = "Floor"
        self.assertEqual(bpy.ops.dasktoon.save_to_project(project=self.project.file, name="Hero"), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        self.assertIn("Floor", bpy.data.objects)
        self.assertEqual(read(draft), before)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.save_to_project(project=self.project.file, name="HERO")

    def test_save_on_a_draft_writes_nothing_without_a_window(self):
        draft = self.outside("draft.blend")
        bpy.ops.wm.save_as_mainfile(filepath=draft)
        before = read(draft)
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'CANCELLED'})
        self.assertEqual(bpy.ops.dasktoon.model_save_as(name="X"), {'CANCELLED'})
        self.assertEqual(read(draft), before)
        self.assertEqual(os.listdir(self.project.models_folder), [])

    def test_a_model_whose_project_file_is_gone_is_a_draft(self):
        bpy.ops.wm.save_as_mainfile(filepath=self.model("A"))
        os.remove(self.project.file)
        self.assertTrue(project_ui.is_draft())
        before = read(self.model("A"))
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'CANCELLED'})
        self.assertEqual(read(self.model("A")), before)


class SaveTest(ModelTestCase):
    def setUp(self):
        super().setUp()
        texture = write_png(os.path.join(self.base, "outside", "skin.png"))
        bpy.data.images.load(texture).use_fake_user = True
        tu.add_sphere(segments=8, rings=4).name = "Body"
        bpy.ops.wm.save_as_mainfile(filepath=self.model("Hero"))  # a script save: the texture stays outside

    def test_save_copies_outside_textures_then_saves_in_place(self):
        self.assertEqual(bpy.ops.dasktoon.project_save(), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "skin.png")))
        self.assertEqual(bpy.data.images["skin.png"].filepath_raw, "//../Textures/skin.png")

    def test_save_model_as_switches_to_the_new_model(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_as(name="Hero2"), {'FINISHED'})
        self.assertOpen(self.model("Hero2"))
        self.assertTrue(os.path.isfile(self.model("Hero")))
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.model_save_as(name="hero")

    def test_save_copy_keeps_the_current_file(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_copy(name="Backup"), {'FINISHED'})
        self.assertOpen(self.model("Hero"))
        with bpy.data.libraries.load(self.model("Backup")) as (src, _dst):
            self.assertIn("Body", src.objects)

    def test_save_incremental_numbers_the_file_next_to_it(self):
        self.assertEqual(bpy.ops.dasktoon.model_save_incremental(), {'FINISHED'})
        self.assertOpen(self.model("Hero_001"))
        bpy.ops.dasktoon.model_save_incremental()
        self.assertOpen(self.model("Hero_002"))
        self.assertTrue(os.path.isfile(os.path.join(self.project.textures_folder, "skin.png")))

    def test_copy_and_incremental_need_a_model_of_a_project(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertFalse(bpy.ops.dasktoon.model_save_copy.poll())
        self.assertFalse(bpy.ops.dasktoon.model_save_incremental.poll())


class OpenTest(ModelTestCase):
    def test_open_takes_models_drafts_and_projects(self):
        model = self.model("Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        outside = os.path.join(self.base, "outside", "loose.blend")
        os.makedirs(os.path.dirname(outside))
        bpy.ops.wm.save_as_mainfile(filepath=outside)
        bpy.ops.wm.read_homefile(use_empty=True)
        self.assertEqual(bpy.ops.dasktoon.open(filepath=model), {'FINISHED'})
        self.assertOpen(model)
        self.assertFalse(project_ui.is_draft())
        bpy.ops.dasktoon.open(filepath=outside)
        self.assertOpen(outside)
        self.assertTrue(project_ui.is_draft())
        other = dtp.create_project("Other", os.path.join(self.base, "Other"))
        project_ui.select_project(self.project)
        self.assertEqual(bpy.ops.dasktoon.open(filepath=other.file), {'FINISHED'})
        self.assertEqual(project_ui.selected_project().name, "Other")
        self.assertOpen(outside)

    def test_open_reports_a_missing_file(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.open(filepath=os.path.join(self.base, "missing.blend"))


class RecentModelsTest(ModelTestCase):
    def test_models_are_remembered_and_drafts_are_not(self):
        model = self.model("Hero")
        bpy.ops.wm.save_as_mainfile(filepath=model)
        model_ui.remember(model)
        model_ui.remember(os.path.join(self.base, "outside", "loose.blend"))
        self.assertEqual(dtp.recent_models(), [model])
        self.assertEqual(dtp.recent_projects()[0], self.project.file)
        self.assertIn(model_ui.remember_on_file_change, bpy.app.handlers.load_post)
        self.assertIn(model_ui.remember_on_file_change, bpy.app.handlers.save_post)

    def test_the_commands_the_core_hands_over_to_are_registered(self):
        for name in ("model_new", "open", "project_save", "model_save_incremental", "model_save_as", "model_save_copy"):
            self.assertTrue(hasattr(bpy.types, "DASKTOON_OT_" + name), name)
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: ERROR/FAIL (`dasktoon.save_to_project` chưa có...).

- [ ] **Step 3: Viết các lệnh**

Trong `scripts/startup/bl_ui/dasktoon_model.py`:
- import: `from bpy.app.handlers import persistent`; `from bpy.props import BoolProperty, EnumProperty, StringProperty`.
- thêm sau `save_into`:
```python
def save_here(op, mode, filepath=""):
    """Save the open model where it is, or as `filepath` next to it (Save Incremental), after copying outside textures
    into its project. Invoked, Blender's own dialogs (modified images, a file from a newer version) still show."""
    collected = dtt.collect(projects.open_project())
    for warning in collected.warnings:
        op.report({'WARNING'}, warning)
    options = {"use_project_redirect": False}
    if filepath:
        options["filepath"] = filepath
    if mode == 'INVOKE_DEFAULT':
        options["show_save_modified_images_dialog"] = op.show_save_modified_images_dialog
    try:
        bpy.ops.wm.save_mainfile(mode, **options)
    except RuntimeError as ex:
        op.report({'ERROR'}, str(ex))
        return {'CANCELLED'}
    projects.forget_models()
    report_textures(op, collected)
    return {'FINISHED'}


def _save_draft(context):
    """Save and Save Model As on a draft open Save to Project (spec 9). Nothing is saved yet, so this is cancelled:
    the "save changes?" dialog stops what it was doing, as Blender does for a file never saved."""
    if context.window is not None:
        bpy.ops.dasktoon.save_to_project('INVOKE_DEFAULT')
    return {'CANCELLED'}


def _project_items(_self, _context):
    """The selected project, then the recent ones (Save to Project, spec 6)."""
    items = _enum_items["projects"]
    items.clear()
    selected = projects.selected_project()
    seen = set()
    for path in ([selected.file] if selected else []) + dtp.recent_projects():
        key = os.path.normcase(os.path.abspath(path))
        project = projects.load_project(path) if key not in seen else None
        seen.add(key)
        if project is not None:
            items.append((path, project.name, path))
    return items


def _current_name():
    return os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "Untitled"
```
- thêm các lớp sau `DASKTOON_OT_model_new_finish`:
```python
class DASKTOON_OT_open(Operator):
    """Open a model, a .blend file from outside any project (as a draft), or a project"""
    bl_idname = "dasktoon.open"
    bl_label = "Open"

    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    filter_blender: BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    filter_glob: StringProperty(default="*.blend;" + dtp.PROJECT_FILE, options={'HIDDEN'})

    def invoke(self, context, _event):
        if not self.filepath:
            project = projects.selected_project()
            if project is not None:
                folder = project.models_folder if os.path.isdir(project.models_folder) else project.folder
                self.filepath = os.path.join(folder, "")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        path = bpy.path.abspath(self.filepath)
        if os.path.isdir(path) or os.path.basename(path).lower() == dtp.PROJECT_FILE:
            try:
                return bpy.ops.dasktoon.project_open(filepath=path)
            except RuntimeError:
                return {'CANCELLED'}  # Open Project reported why
        if not os.path.isfile(path):
            self.report({'ERROR'}, rpt_("File not found: %s") % path)
            return {'CANCELLED'}
        projects.open_blend(path)
        return {'FINISHED'}


class DASKTOON_OT_project_save(Operator):
    """Save this model in its project, copying textures from outside into Textures/ first; a draft is saved into a project"""
    bl_idname = "dasktoon.project_save"
    bl_label = "Save"

    show_save_modified_images_dialog: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, _event):
        if projects.open_project() is None:
            return _save_draft(context)
        return save_here(self, projects.call_mode())

    def execute(self, context):
        if projects.open_project() is None:
            return _save_draft(context)
        return save_here(self, 'EXEC_DEFAULT')


class DASKTOON_OT_save_to_project(Operator):
    """Save this draft as a new model of a project; the file it came from is not changed"""
    bl_idname = "dasktoon.save_to_project"
    bl_label = "Save to Project"

    project: EnumProperty(name="Project", items=_project_items, translation_context="DaskToon")
    name: StringProperty(name="Name", default="Untitled")

    def invoke(self, context, _event):
        items = _project_items(self, context)
        if not items:
            bpy.ops.dasktoon.project_create('INVOKE_DEFAULT', model_start_from='CURRENT')
            return {'CANCELLED'}
        self.project = items[0][0]
        self.name = dtp.free_model_name(projects.load_project(self.project), _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, _context):
        project = projects.load_project(self.project) if self.project else None
        if project is None:
            self.report({'ERROR'}, rpt_("Choose a project"))
            return {'CANCELLED'}
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path)
        if collected is None:
            return {'CANCELLED'}
        projects.select_project(project)
        self.report({'INFO'}, rpt_("Saved model %s in project %s") % (dtp.model_label(project, path), project.name))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_as(Operator):
    """Save this model under a new name in its project's Models/ folder and keep working on the new file"""
    bl_idname = "dasktoon.model_save_as"
    bl_label = "Save Model As"

    name: StringProperty(name="Name")

    def invoke(self, context, _event):
        project = projects.open_project()
        if project is None:
            return _save_draft(context)
        self.name = dtp.free_model_name(project, _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, context):
        project = projects.open_project()
        if project is None:
            return _save_draft(context)
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path)
        if collected is None:
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Saved as model %s") % dtp.model_label(project, path))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_copy(Operator):
    """Write a copy of this model into its project's Models/ folder and keep working on this file"""
    bl_idname = "dasktoon.model_save_copy"
    bl_label = "Save Copy"

    name: StringProperty(name="Name")

    @classmethod
    def poll(cls, _context):
        return projects.open_project() is not None

    def invoke(self, context, _event):
        self.name = dtp.free_model_name(projects.open_project(), _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, _context):
        project = projects.open_project()
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path, copy=True)
        if collected is None:
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Saved a copy as model %s") % dtp.model_label(project, path))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_incremental(Operator):
    """Save this model as the next numbered file next to it (Hero.blend gives Hero_001.blend) and keep working on that one"""
    bl_idname = "dasktoon.model_save_incremental"
    bl_label = "Save Incremental"

    show_save_modified_images_dialog: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, _context):
        return projects.open_project() is not None

    def invoke(self, _context, _event):
        return save_here(self, projects.call_mode(), dtp.incremental_path(bpy.data.filepath))

    def execute(self, _context):
        return save_here(self, 'EXEC_DEFAULT', dtp.incremental_path(bpy.data.filepath))


def remember(filepath):
    """A model of a project goes to the top of the recent models, its project to the top of the recent projects
    (spec 4). A draft is not remembered."""
    project = dtp.find_project(filepath) if filepath else None
    if project is not None:
        dtp.add_recent_model(filepath)
        dtp.add_recent(project.file)


@persistent
def remember_on_file_change(filepath):
    """load_post and save_post. Background runs (scripts, tests) are not a person's work and are not remembered."""
    if not bpy.app.background:
        remember(filepath)
```
- `classes` thành
```python
classes = (
    DASKTOON_OT_model_new,
    DASKTOON_OT_model_new_finish,
    DASKTOON_OT_open,
    DASKTOON_OT_project_save,
    DASKTOON_OT_save_to_project,
    DASKTOON_OT_model_save_as,
    DASKTOON_OT_model_save_copy,
    DASKTOON_OT_model_save_incremental,
)


# bl_ui registers `classes`; register()/unregister() manage the recent-models handler.
def register():
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.save_post):
        if remember_on_file_change not in handlers:
            handlers.append(remember_on_file_change)


def unregister():
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.save_post):
        if remember_on_file_change in handlers:
            handlers.remove(remember_on_file_change)
```

- [ ] **Step 4: Bản dịch**

Thêm vào khối `# bl_ui/dasktoon_model.py` của `VI`:
```python
    "Open a model, a .blend file from outside any project (as a draft), or a project":
        "Mở một model, một file .blend ngoài mọi dự án (làm bản nháp), hoặc một dự án",
    "Save this model in its project, copying textures from outside into Textures/ first; a draft is saved into a project":
        "Lưu model này vào dự án của nó, chép trước texture ở ngoài vào Textures/; bản nháp thì được lưu vào một dự án",
    "Save to Project": "Lưu vào dự án",
    "Save this draft as a new model of a project; the file it came from is not changed":
        "Lưu bản nháp này thành model mới của một dự án; file gốc không bị thay đổi",
    "Choose a project": "Hãy chọn một dự án",
    "Saved model %s in project %s": "Đã lưu model %s vào dự án %s",
    "Save Model As": "Lưu model thành",
    "Save this model under a new name in its project's Models/ folder and keep working on the new file":
        "Lưu model này với tên mới trong thư mục Models/ của dự án và làm việc tiếp trên file mới",
    "Saved as model %s": "Đã lưu thành model %s",
    "Write a copy of this model into its project's Models/ folder and keep working on this file":
        "Ghi bản sao của model này vào thư mục Models/ của dự án và làm việc tiếp trên file này",
    "Saved a copy as model %s": "Đã lưu bản sao thành model %s",
    "Save this model as the next numbered file next to it (Hero.blend gives Hero_001.blend) and keep working on that one":
        "Lưu model này thành file đánh số tiếp theo cạnh nó (Hero.blend thành Hero_001.blend) và làm việc tiếp trên file đó",
```

- [ ] **Step 5: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_model_test.py`, `dasktoon_file_redirect_test.py`, `dasktoon_project_ui_test.py`,
`dasktoon_translations_test.py`. Expected: tất cả OK.

- [ ] **Step 6: Commit**
```bash
git add scripts/startup/bl_ui/ tests/python/dasktoon_model_test.py
git commit -m "feat: Open, Save and Save to Project go through projects; drafts are never overwritten; remember recent models"
```

---

### Task 7: Menu File, menu New, nhãn thanh trên cùng, màn hình đầu

**Files:**
- Modify: `scripts/startup/bl_ui/space_topbar.py` (`TOPBAR_HT_upper_bar.draw_right`, `TOPBAR_MT_file`, `TOPBAR_MT_file_new`;
  xóa `TOPBAR_MT_templates_more`)
- Modify: `scripts/startup/bl_operators/wm.py` (`WM_MT_splash`)
- Create: `scripts/startup/bl_ui/dasktoon_splash.py`; Modify: `scripts/startup/bl_ui/__init__.py` (`"dasktoon_splash"` ngay
  sau `"dasktoon_model"`)
- Create: `tests/python/dasktoon_file_ui_test.py`
- Modify: `tests/python/dasktoon_i18n_utils.py`, `tests/python/dasktoon_translations_test.py`,
  `tests/python/dasktoon_ui_layout_test.py`, `tests/python/CMakeLists.txt`, `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: Task 4 (`projects.selected_project`, `engine_label`, `models`, `is_draft`, `draw_topbar_label`), Task 5–6 (lệnh).
- Produces: `bl_ui.dasktoon_splash.draw_splash(layout, context)`, `MAX_MODELS = 12`, lệnh `dasktoon.continue_as_draft`;
  `dasktoon_i18n_utils.module_strings(path, classes=None)`, `all_strings(path, classes=None)`.

- [ ] **Step 1: Viết test (đỏ)**

File: `tests/python/dasktoon_file_ui_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The file side of the interface (project workflow spec 5, 7, 9): the start screen in its two states, the File and New
menus, the top bar label, and the shortcuts the File menu shows."""

import importlib.util
import os
import sys
import tempfile
import types
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from bl_ui import dasktoon_splash as splash  # noqa: E402
from bl_ui.space_topbar import TOPBAR_HT_upper_bar  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def window_keymap(module):
    """[(operator, properties)] of the Window keymap of a keymap preset: Blender's or Industry Compatible."""
    path = os.path.join(bpy.utils.system_resource('SCRIPTS'), "presets", "keyconfig", "keymap_data", module + ".py")
    spec = importlib.util.spec_from_file_location("dt_keymap_" + module, path)
    data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data)
    _name, _where, keymap = data.km_window(data.Params())
    return [(idname, dict((options or {}).get("properties", ()))) for idname, _event, options in keymap["items"]]


class FileUITest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_fileui_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        self.base = tempfile.mkdtemp(prefix="dt_fileui_")

    def make_project(self, *models):
        project = dtp.create_project("Hero", os.path.join(self.base, "Hero"))
        for name in models:
            with open(dtp.new_model_path(project, name), "wb"):
                pass
        project_ui.forget_models()
        return project

    def start_screen(self):
        layout = tu.RecordingLayout()
        splash.draw_splash(layout, bpy.context)
        return layout.log

    def test_start_screen_without_a_project(self):
        log = self.start_screen()
        self.assertEqual(tu.operators(log), [
            ("dasktoon.project_create", "New Project…"), ("dasktoon.project_open", "Open Project…"),
            ("dasktoon.model_new", "New Model…"), ("wm.recover_last_session", ""),
            ("dasktoon.continue_as_draft", "")])
        self.assertIn("Create or open a project", tu.labels(log))
        new_model = next(entry for entry in log if entry[1] == "dasktoon.model_new")
        self.assertFalse(new_model[4])

    def test_start_screen_shows_the_selected_projects_models(self):
        hero = self.make_project("Hero", "Sword")
        dtp.create_project("Other", os.path.join(self.base, "Other"))
        project_ui.select_project(hero)
        log = self.start_screen()
        self.assertEqual([entry[1:4] for entry in log if entry[1] == "dasktoon.project_select"],
                         [("dasktoon.project_select", "Hero", 'RADIOBUT_ON'),
                          ("dasktoon.project_select", "Other", 'RADIOBUT_OFF')])
        operators = tu.operators(log)
        self.assertIn(("dasktoon.project_open_model", "Hero"), operators)
        self.assertIn(("dasktoon.project_open_model", "Sword"), operators)
        self.assertIn("Engine: not linked", tu.labels(log))
        self.assertTrue(next(entry for entry in log if entry[1] == "dasktoon.model_new")[4])
        self.assertFalse({"wm.read_homefile", "wm.open_mainfile", "wm.url_open"} & {entry[1] for entry in log})

    def test_a_long_model_list_is_cut_short(self):
        self.make_project(*["M%02d" % i for i in range(splash.MAX_MODELS + 3)])
        log = self.start_screen()
        self.assertEqual(len([e for e in log if e[1] == "dasktoon.project_open_model"]), splash.MAX_MODELS)
        self.assertIn("3 more in File › Models", tu.labels(log))

    def test_splash_menu_draws_the_start_screen(self):
        self.assertIn(("dasktoon.continue_as_draft", ""), tu.operators(tu.draw(bpy.types.WM_MT_splash)))
        self.assertEqual(bpy.ops.dasktoon.continue_as_draft(), {'FINISHED'})

    def test_file_menu(self):
        log = tu.draw(bpy.types.TOPBAR_MT_file)
        entries = [entry[:3] for entry in log if entry[0] in {"operator", "menu"}]
        self.assertEqual(entries[:11], [
            ("operator", "dasktoon.project_create", "New Project…"),
            ("operator", "wm.read_homefile", "New Model…"),
            ("operator", "wm.open_mainfile", "Open…"),
            ("menu", "TOPBAR_MT_file_open_recent", ""),
            ("menu", "TOPBAR_MT_dasktoon_project_models", ""),
            ("operator", "wm.revert_mainfile", ""),
            ("menu", "TOPBAR_MT_file_recover", ""),
            ("operator", "wm.save_mainfile", "Save"),
            ("operator", "wm.save_as_mainfile", "Save Model As…"),
            ("operator", "wm.save_as_mainfile", "Save Copy…"),
            ("operator", "wm.save_mainfile", "Save Incremental")])
        self.assertEqual(entries[-3:], [("menu", "TOPBAR_MT_dasktoon_project", ""),
                                        ("menu", "TOPBAR_MT_file_defaults", ""),
                                        ("operator", "wm.quit_blender", "Quit")])
        self.assertNotIn("TOPBAR_MT_file_new", [entry[1] for entry in entries])
        self.assertEqual({e[2]: e[4] for e in log if e[2] in ("Save Copy…", "Save Incremental")},
                         {"Save Copy…": False, "Save Incremental": False})
        project = self.make_project()
        bpy.ops.wm.save_as_mainfile(filepath=dtp.new_model_path(project, "Hero"))
        self.assertEqual({e[2]: e[4] for e in tu.draw(bpy.types.TOPBAR_MT_file)
                          if e[2] in ("Save Copy…", "Save Incremental")},
                         {"Save Copy…": True, "Save Incremental": True})

    def test_file_menu_items_carry_the_keymap_shortcuts(self):
        log = tu.draw(bpy.types.TOPBAR_MT_file)
        items = {entry[2]: (entry[1], vars(entry[5])) for entry in log if entry[0] == "operator"}
        default = window_keymap("blender_default")
        for text in ("Open…", "Save", "Save Model As…", "Save Incremental"):
            self.assertIn(items[text], default, text)
        self.assertIn(("wm.call_menu", {"name": "TOPBAR_MT_file_open_recent"}), default)
        # Ctrl+N opens the New menu in Blender's keymap (the core shows that shortcut on New Model…) and runs
        # wm.read_homefile in the Industry Compatible one.
        self.assertIn(("wm.call_menu", {"name": "TOPBAR_MT_file_new"}), default)
        self.assertEqual(items["New Model…"], ("wm.read_homefile", {}))
        self.assertIn(("wm.read_homefile", {}), window_keymap("industry_compatible_data"))

    def test_new_menu_offers_a_model_or_a_project(self):
        self.assertEqual(tu.operators(tu.draw(bpy.types.TOPBAR_MT_file_new)),
                         [("dasktoon.model_new", "New Model…"), ("dasktoon.project_create", "New Project…")])

    def test_top_bar_label_comes_before_the_scene_selector(self):
        context = types.SimpleNamespace(window=types.SimpleNamespace(scene=bpy.context.scene),
                                        screen=types.SimpleNamespace(show_statusbar=True))
        layout = tu.RecordingLayout()
        TOPBAR_HT_upper_bar.draw_right(types.SimpleNamespace(layout=layout), context)
        kinds = [entry[:2] for entry in layout.log]
        self.assertEqual(kinds[:2], [("label", ""), ("call", "template_ID")])
        self.assertEqual(layout.log[0][2:4], ("Draft (not in a project)", 'ERROR'))


if __name__ == "__main__":
    tu.run_tests()
```
`tests/python/dasktoon_ui_layout_test.py`: thêm `"TOPBAR_MT_templates_more"` vào `REMOVED`.

`tests/python/dasktoon_translations_test.py`: thêm dưới `TRANSLATED`
```python
# Blender files DaskToon rewrote parts of (project workflow spec 13): only these classes are DaskToon's.
TRANSLATED_CLASSES = {
    "scripts/startup/bl_ui/space_topbar.py": ("TOPBAR_MT_file", "TOPBAR_MT_file_new", "TOPBAR_HT_upper_bar"),
    "scripts/startup/bl_operators/wm.py": ("WM_MT_splash",),
}
```
và trong `TranslationTest`:
```python
    def test_rewritten_blender_classes_are_english_and_translated(self):
        with iu.language('vi_VN'):
            for rel, classes in TRANSLATED_CLASSES.items():
                strings, dynamic = iu.module_strings(path(rel), classes)
                self.assertEqual(dynamic, [], rel)
                self.assertEqual(iu.untranslated(strings, dt.KEEP), [], rel)
                bad = sorted(s for s in iu.all_strings(path(rel), classes) if iu.VI_CHARS.search(s) or iu.EMOJI.search(s))
                self.assertEqual(bad, [], rel)
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: ERROR `ImportError: cannot import name 'dasktoon_splash'`; test bản dịch lỗi vì
  `module_strings` chưa nhận `classes`.

- [ ] **Step 3: Cho bộ trích chuỗi chỉ quét vài lớp**

`tests/python/dasktoon_i18n_utils.py`: thêm
```python
def _roots(tree, classes):
    """The parts of `tree` to scan: the whole file, or only the named top-level classes."""
    if classes is None:
        return [tree]
    return [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in classes]
```
`module_strings(path)` thành `module_strings(path, classes=None)` và vòng `for node in ast.walk(tree):` thành
`for node in (n for root in _roots(tree, classes) for n in ast.walk(root)):`. `all_strings(path)` thành
`all_strings(path, classes=None)`; cả hai vòng `ast.walk(tree)` trong hàm này cũng đi qua
`(n for root in _roots(tree, classes) for n in ast.walk(root))`.

- [ ] **Step 4: Màn hình đầu**

File: `scripts/startup/bl_ui/dasktoon_splash.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon start screen (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 5):
projects on the left, the selected project's models on the right, Recover Last Session and Continue as Draft below.
WM_MT_splash (bl_operators/wm.py) draws it under the splash image; DaskToon › Splash Screen shows it again."""

import os

from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Operator

from dasktoon_project import project as dtp
from . import dasktoon_project as projects

MAX_MODELS = 12  # a taller start screen would not fit small screens; File › Models lists them all


def draw_splash(layout, _context):
    layout.operator_context = 'EXEC_DEFAULT'
    layout.emboss = 'PULLDOWN_MENU'
    selected = projects.selected_project()

    split = layout.split()
    left = split.column()
    left.label(text="Projects")
    sub = left.column()
    sub.operator_context = 'INVOKE_DEFAULT'
    sub.operator("dasktoon.project_create", text="New Project…", icon='NEWFOLDER')
    sub.operator("dasktoon.project_open", text="Open Project…", icon='FILE_FOLDER')
    left.separator()
    left.label(text="Recent")
    recent = dtp.recent_projects()
    if not recent:
        left.label(text="No recent projects")
    for path in recent:
        chosen = selected is not None and dtp.same_path(path, selected.file)
        left.operator("dasktoon.project_select", text=os.path.basename(os.path.dirname(path)),
                      icon='RADIOBUT_ON' if chosen else 'RADIOBUT_OFF', translate=False).filepath = path

    right = split.column()
    if selected is None:
        right.label(text="Create or open a project")
        sub = right.column()
        sub.enabled = False
        sub.operator("dasktoon.model_new", text="New Model…", icon='FILE_NEW')
    else:
        right.label(text=selected.name, icon='FILE_FOLDER', translate=False)
        right.label(text=projects.engine_label(selected), translate=False)
        sub = right.column()
        sub.operator_context = 'INVOKE_DEFAULT'
        sub.operator("dasktoon.model_new", text="New Model…", icon='FILE_NEW')
        found = projects.models(selected)
        for path in found[:MAX_MODELS]:
            right.operator("dasktoon.project_open_model", text=dtp.model_label(selected, path), icon='FILE_BLEND',
                           translate=False).filepath = path
        if len(found) > MAX_MODELS:
            right.label(text=iface_("%d more in File › Models") % (len(found) - MAX_MODELS), translate=False)

    col = layout.column()
    col.separator()
    col.separator(type='LINE')
    col.separator()

    split = layout.split()
    split.column().operator("wm.recover_last_session", icon='RECOVER_LAST')
    split.column().operator(DASKTOON_OT_continue_as_draft.bl_idname, icon='FILE_BLEND')
    layout.separator()


class DASKTOON_OT_continue_as_draft(Operator):
    """Close the start screen and keep working on the open scene as a draft, outside any project"""
    bl_idname = "dasktoon.continue_as_draft"
    bl_label = "Continue as Draft"

    def execute(self, _context):
        return {'FINISHED'}  # the start screen closes when one of its items is used


classes = (DASKTOON_OT_continue_as_draft,)
```
`scripts/startup/bl_operators/wm.py`: thân `WM_MT_splash.draw` thay bằng
```python
    def draw(self, context):
        # DaskToon start screen: projects and their models (scripts/startup/bl_ui/dasktoon_splash.py).
        from bl_ui.dasktoon_splash import draw_splash
        draw_splash(self.layout, context)
```

- [ ] **Step 5: Menu File, menu New, nhãn thanh trên cùng**

`scripts/startup/bl_ui/space_topbar.py`:

`TOPBAR_HT_upper_bar.draw_right`: ngay trước dòng chú thích `# Active workspace view-layer is retrieved through window...`
thêm
```python
        # DaskToon: the open project and model, or a warning for a draft (project workflow spec 7).
        from bl_ui.dasktoon_project import draw_topbar_label
        draw_topbar_label(layout)
```

`TOPBAR_MT_file.draw` thay toàn bộ thân bằng
```python
    def draw(self, context):
        # DaskToon: every way to open or save a file goes through projects
        # (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 7). New Model, Open and the
        # Save items call Blender's operators, invoked, so their shortcuts show; the core hands them to DaskToon.
        from bl_ui.dasktoon_project import is_draft
        layout = self.layout

        layout.operator_context = 'INVOKE_AREA'
        layout.operator("dasktoon.project_create", text="New Project…", icon='NEWFOLDER')
        layout.operator("wm.read_homefile", text="New Model…", icon='FILE_NEW')
        layout.operator("wm.open_mainfile", text="Open…", icon='FILE_FOLDER')
        layout.menu("TOPBAR_MT_file_open_recent")
        layout.menu("TOPBAR_MT_dasktoon_project_models", icon='FILE_BLEND')
        layout.operator("wm.revert_mainfile")
        layout.menu("TOPBAR_MT_file_recover")

        layout.separator()

        layout.operator("wm.save_mainfile", text="Save", icon='FILE_TICK').show_save_modified_images_dialog = True
        layout.operator("wm.save_as_mainfile", text="Save Model As…").show_save_modified_images_dialog = True
        sub = layout.column()
        sub.enabled = not is_draft()
        save_copy = sub.operator("wm.save_as_mainfile", text="Save Copy…")
        save_copy.copy = True
        save_copy.show_save_modified_images_dialog = True
        save_incremental = sub.operator("wm.save_mainfile", text="Save Incremental")
        save_incremental.incremental = True
        save_incremental.show_save_modified_images_dialog = True

        layout.separator()

        layout.operator("wm.link", text="Link...", icon='LINK_BLEND')
        layout.operator("wm.append", text="Append...", icon='APPEND_BLEND')
        layout.menu("TOPBAR_MT_file_previews")

        layout.separator()

        layout.menu("TOPBAR_MT_file_import", icon='IMPORT')
        layout.menu("TOPBAR_MT_file_export", icon='EXPORT')
        row = layout.row()
        row.operator("wm.collection_export_all")
        row.enabled = context.view_layer.has_export_collections

        layout.separator()

        layout.menu("TOPBAR_MT_file_external_data")
        layout.menu("TOPBAR_MT_file_cleanup")

        layout.separator()

        layout.menu("TOPBAR_MT_dasktoon_project", icon='FILE_FOLDER')
        layout.menu("TOPBAR_MT_file_defaults")

        layout.separator()

        layout.operator("wm.quit_blender", text="Quit", icon='QUIT')
```

`TOPBAR_MT_file_new` thay cả lớp bằng
```python
class TOPBAR_MT_file_new(Menu):
    bl_label = "New"

    def draw(self, _context):
        # DaskToon: something new is a model in a project, or a project (project workflow spec 7). Ctrl+N opens this.
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("dasktoon.model_new", text="New Model…", icon='FILE_NEW')
        layout.operator("dasktoon.project_create", text="New Project…", icon='NEWFOLDER')
```
Xóa lớp `TOPBAR_MT_templates_more` và tên của nó trong `classes` cuối file. Trước khi xóa, chạy
`grep -rn "draw_ex\|app_template_paths\|TOPBAR_MT_templates_more" scripts/` để chắc không còn chỗ nào gọi
`TOPBAR_MT_file_new.draw_ex`/`app_template_paths` (chỉ `WM_MT_splash` cũ gọi; `bpy.utils.app_template_paths` của
`TOPBAR_MT_file_defaults` là hàm khác, giữ nguyên).

`bl_ui/__init__.py`: thêm `"dasktoon_splash",` ngay sau `"dasktoon_model",`.

- [ ] **Step 6: Bản dịch và đăng ký test**

Thêm vào `VI`:
```python
    # bl_ui/dasktoon_splash.py, and DaskToon's parts of space_topbar.py and bl_operators/wm.py
    "%d more in File › Models": "còn %d model trong File › Models",
    "Continue as Draft": "Tiếp tục với bản nháp",
    "Close the start screen and keep working on the open scene as a draft, outside any project":
        "Đóng màn hình đầu và làm tiếp trên cảnh đang mở như một bản nháp, ngoài mọi dự án",
    "Open…": "Mở…",
    "Save Model As…": "Lưu model thành…",
    "Save Copy…": "Lưu bản sao…",
```
Các chữ của Blender còn lại trong bốn lớp đã viết lại ("File", "New", "Splash", "Save", "Save Incremental", "Link...",
"Append...", "Quit", "Back to Previous") đã có trong `vi.po` (đã kiểm), nên không cần thêm vào `VI`.
`CMakeLists.txt`: thêm `dasktoon_file_ui_test` (sau `dasktoon_model_test`).
`tests/python/dasktoon_translations_test.py`: thêm `"scripts/startup/bl_ui/dasktoon_splash.py"` vào `TRANSLATED`.

- [ ] **Step 7: Đồng bộ, chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_file_ui_test.py`, `dasktoon_project_ui_test.py`, `dasktoon_model_test.py`,
`dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `dasktoon_install_test.py`. Expected: tất cả OK.

- [ ] **Step 8: Commit**
```bash
git add scripts/startup/ tests/python/
git commit -m "feat: the start screen lists projects and models; File and New offer models and projects; the top bar names the open model"
```

---

### Task 8: Test có cửa sổ (event simulation)

**Files:**
- Create: `tests/python/dasktoon_project_window_test.py` (không thêm vào CMake: cần màn hình)

**Interfaces:**
- Consumes: mọi task trước; `easy_keys` (`tests/python/ui_simulate/modules`).

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_project_window_test.py`
```python
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

    win = bpy.context.window_manager.windows[0]
    e = easy_keys.EventGenerate(win)
    yield wait(1.0)
    e.esc()  # a start screen shown before the preferences were set would take the keys
    yield wait(0.5)
    view = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in view.regions if r.type == 'WINDOW')
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)
    yield wait(0.5)

    def change_something():
        """An operator with undo marks the file as changed, as a person's edit does."""
        with bpy.context.temp_override(window=win, area=view, region=region):
            bpy.ops.object.empty_add()

    def open_model(path):
        """What clicking a model in File › Models does."""
        with bpy.context.temp_override(window=win, area=view, region=region):
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
    e.ctrl.n()
    yield wait(1.0)
    check(bool(seen), "Ctrl+N did not open the New menu")
    e.esc()
    yield wait(0.5)
    bpy.types.TOPBAR_MT_file_new.remove(spy)

    # 2. Ctrl+O opens DaskToon's file browser.
    e.ctrl.o()
    yield wait(1.5)
    browsers = [area.spaces.active for window in bpy.context.window_manager.windows
                for area in window.screen.areas if area.type == 'FILE_BROWSER']
    operator = browsers[0].active_operator if browsers else None
    check(operator is not None and operator.bl_idname == "DASKTOON_OT_open",
          "Ctrl+O did not open DaskToon's file browser: %r" % (operator and operator.bl_idname))
    e.esc()
    yield wait(1.0)

    # 3. Ctrl+S on a draft: Save to Project, Return saves it as Models/draft.blend; the draft file stays as it was.
    change_something()
    e.ctrl.s()
    yield wait(1.0)
    e.ret()
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
    e.ret()  # Save is the dialog's default button
    yield wait(2.0)
    check(dtp.same_path(bpy.data.filepath, other), "the other model did not open: %s" % bpy.data.filepath)
    check(os.path.getmtime(first) > before, "Save in the dialog did not save the model first")

    # 5. The same dialog on a draft from outside: Save opens Save to Project and the opening stops.
    second = os.path.join(outside, "second.blend")
    bpy.ops.wm.save_as_mainfile(filepath=second, copy=True)
    bpy.ops.wm.open_mainfile(filepath=second)
    second_sha = sha256(second)
    change_something()
    open_model(other)
    yield wait(1.0)
    e.ret()  # Save: the draft goes to Save to Project, so the opening stops
    yield wait(1.5)
    check(dtp.same_path(bpy.data.filepath, second), "the opening went on though the draft was not saved")
    e.ret()  # Save to Project: OK
    yield wait(2.0)
    saved = os.path.join(project.models_folder, "second.blend")
    check(dtp.same_path(bpy.data.filepath, saved), "Save to Project did not save the draft: %s" % bpy.data.filepath)
    check(sha256(second) == second_sha, "the file from outside the project was overwritten")

    # 6. Ctrl+Q with unsaved changes: Save saves the model, then DaskToon quits; run_outside() checks the file.
    change_something()
    result.update(model=bpy.data.filepath, model_mtime=os.path.getmtime(bpy.data.filepath), draft=second,
                  draft_sha256=second_sha, quit_started=True)
    write_result()
    e.ctrl.q()
    yield wait(1.0)
    e.ret()
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
```

- [ ] **Step 2: Chạy**

Run: `"$PY" tests/python/dasktoon_project_window_test.py "$DT"` (một cửa sổ DaskToon mở khoảng nửa phút rồi tự đóng; không
chạm chuột/bàn phím trong lúc đó).
Expected: dòng cuối `OK`, exit code 0.

Nếu một bước báo lỗi:
- Bước 1: không thấy menu → kiểm tra keymap đang dùng có Ctrl+N gọi `TOPBAR_MT_file_new` không (`--factory-startup` dùng
  keymap Blender).
- Bước 3–5: Return không xác nhận hộp thoại → tăng thời gian chờ trước `e.ret()` lên 1.5 s; nếu hộp thoại mở dưới chỗ
  khác, giữ con trỏ ở giữa 3D Viewport.
- Bước 4: nếu file của bước 3 không được lưu lại, nút Save của hộp thoại chưa gọi `dasktoon.project_save` → xem lại 4k
  của Task 3 và đã build lại chưa.

- [ ] **Step 3: Commit**
```bash
git add tests/python/dasktoon_project_window_test.py
git commit -m "test: drive Ctrl+N, Ctrl+O, Ctrl+S and the save-changes dialog in a real DaskToon window"
```

---

### Task 9: Ảnh chụp giao diện

**Files:**
- Modify: `tools/dasktoon_ui_screenshots.py`
- Create: `docs/superpowers/reports/project-workflow/en/*.png`, `docs/superpowers/reports/project-workflow/vi/*.png`

- [ ] **Step 1: Sửa công cụ**

`tools/dasktoon_ui_screenshots.py`:
- `build_scene()`: xóa dòng `from dasktoon_project import project as dtp`, xóa mọi dòng từ `unity = os.path.join(WORK,
  "MyGame")` tới dòng `bpy.ops.wm.save_as_mainfile(...)` thêm ở Task 1, và đổi `log("scene ready", bpy.data.filepath)`
  thành `log("scene ready")`. Hàm chỉ còn dựng cảnh mẫu (một bản nháp chưa lưu) và `return head`.
- thêm sau `build_scene()`:
```python
def make_project():
    """The Hero project, linked to a fake Unity project in WORK, chosen as the selected project."""
    from bl_ui import dasktoon_project as projects
    from dasktoon_project import project as dtp
    unity = os.path.join(WORK, "MyGame")
    for sub in ("Assets", "ProjectSettings"):
        os.makedirs(os.path.join(unity, sub), exist_ok=True)
    project = dtp.create_project("Hero", os.path.join(WORK, "Hero"), unity)
    projects.select_project(project)
    return project
```
- trong `steps()`, thay đoạn từ `head = build_scene()` tới hết `yield datetime.timedelta(seconds=1.0)` ngay sau nó bằng:
```python
    view = area_of('VIEW_3D')
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)

    def shot_popup(name, call):
        """Open a popup (start screen, dialog) under the cursor, save what it covers as <name>.png, close it."""
        before = grab()
        with bpy.context.temp_override(window=win, area=view, region=region_of(view)):
            call()
        yield datetime.timedelta(seconds=1.0)
        after = grab()
        save(after, changed_rect(before, after, (0, 0, win.width, win.height)), name)
        e.esc()
        yield datetime.timedelta(seconds=0.5)

    # 11. The start screen before any project exists.
    yield from shot_popup("11_start_screen_empty", lambda: bpy.ops.wm.splash('INVOKE_DEFAULT'))
    head = build_scene()
    project = make_project()
    # 16. Save to Project for the draft, then save it there for real.
    yield from shot_popup("16_save_to_project", lambda: bpy.ops.dasktoon.save_to_project('INVOKE_DEFAULT'))
    bpy.ops.dasktoon.save_to_project(project=project.file, name="Hero")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(project.models_folder, "Hero_Armor.blend"), copy=True)
    proxy = next(o for o in bpy.data.objects if o.type == 'EMPTY')
    yield datetime.timedelta(seconds=1.0)
```
- ảnh 9: chú thích thành `# 9. File › Project (Quit, Defaults, Project from the bottom).`, `e.up_arrow()` thành
  `e.up_arrow(3)`, tên ảnh `"09_file_dasktoon_project"` thành `"09_file_project"`.
- ngay sau ảnh 9 thêm ảnh menu File:
```python
    # 13. The File menu itself.
    before = grab()
    e.cursor_position_set(40, win.height - 12, move=True)
    yield datetime.timedelta(seconds=0.3)
    e.leftmouse()
    yield datetime.timedelta(seconds=1.0)
    after = grab()
    menus = changed_rect(before, after, (0, view.y, props.x - 4, win.height))
    save(after, union(menus, (0, win.height - 26, 260, win.height)), "13_file_menu")
    e.esc()
    yield datetime.timedelta(seconds=0.5)
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)
```
- ngay trước `log("done")` thêm:
```python
    # 12, 14, 15. The start screen with the project, New Project and New Model.
    e.cursor_position_set(view.x + view.width // 2, view.y + view.height // 2, move=True)
    yield from shot_popup("12_start_screen", lambda: bpy.ops.wm.splash('INVOKE_DEFAULT'))
    yield from shot_popup("14_new_project", lambda: bpy.ops.dasktoon.project_create('INVOKE_DEFAULT'))
    yield from shot_popup("15_new_model", lambda: bpy.ops.dasktoon.model_new('INVOKE_DEFAULT'))
```
- docstring đầu file: thêm câu "Part 2 (project workflow) adds the start screen, the File menu and the New Project, New
  Model and Save to Project dialogs (docs/superpowers/reports/2026-10-05-dasktoon-project-workflow-report.md)."

- [ ] **Step 2: Chụp hai ngôn ngữ**

Run:
```bash
"$DT" --enable-event-simulate --factory-startup --python tools/dasktoon_ui_screenshots.py -- docs/superpowers/reports/project-workflow/en en_US
"$DT" --enable-event-simulate --factory-startup --python tools/dasktoon_ui_screenshots.py -- docs/superpowers/reports/project-workflow/vi vi_VN
```
Expected: mỗi thư mục có `01`…`16` (trừ những số không dùng) và `capture_log.txt` kết thúc bằng `done`.

- [ ] **Step 3: Xem từng ảnh**

Mở từng PNG (Read tool) và kiểm:
- `11`: màn hình đầu có cột Projects và chữ "Create or open a project"; không có New File, Recent Files, link web.
- `12`: Hero được đánh dấu; cột phải có "Engine: Unity 6 (URP)", New Model…, Hero, Hero_Armor.
- `13`: menu File đúng thứ tự spec 7; cạnh **New Model…** có **Ctrl N**, Open… Ctrl O, Open Recent Shift Ctrl O, Save
  Ctrl S, Save Model As… Shift Ctrl S, Save Incremental Ctrl Alt S.
- `09`: menu con Project có Project Settings…, Export This Model, Reinstall Shaders, Open Project Folder.
- `14`, `15`, `16`: đúng ba hộp thoại; bản `vi` hiện tiếng Việt.
Ảnh sai (mũi tên mở nhầm menu, hộp thoại lệch): sửa số lần bấm hoặc vị trí trong công cụ, chụp lại. Ảnh `01`–`10` cũ
không cần trong thư mục mới: xóa những ảnh không dùng trong báo cáo (giữ `09`, `11`–`16` và `capture_log.txt`).

- [ ] **Step 4: Commit**
```bash
git add tools/dasktoon_ui_screenshots.py docs/superpowers/reports/project-workflow/
git commit -m "docs: screenshots of the start screen, the File menu and the project dialogs"
```

---

### Task 10: Kiểm chứng toàn bộ và báo cáo

**Files:**
- Create: `docs/superpowers/reports/2026-10-05-dasktoon-project-workflow-report.md`

- [ ] **Step 1: Toàn bộ test nền** — đồng bộ, chạy mọi file trong danh sách CMake. Expected: tất cả OK (shading baseline
  chạy lâu, khoảng 6 phút).
- [ ] **Step 2: Test có cửa sổ** — `"$PY" tests/python/dasktoon_project_window_test.py "$DT"`. Expected: `OK`.
- [ ] **Step 3: Thử tay nhanh** (mở `$DT` không có `--factory-startup` cần cẩn thận vì dùng cấu hình thật; chạy với
  `DASKTOON_CONFIG_DIR` tạm): màn hình đầu hiện; Continue as Draft đóng nó; bấm một dự án thì màn hình mở lại với dự án đó;
  thanh trên cùng ghi "Draft (not in a project)" rồi đổi thành "Hero › …" sau khi lưu; Help/DaskToon › Splash Screen hiện
  lại màn hình đầu. Ghi lại điều gì khác spec.
- [ ] **Step 4: Báo cáo** (tiếng Việt, cho người dùng): tóm tắt; cách dùng mới (dự án, model, bản nháp, texture, gắn Unity
  sau) kèm ảnh `project-workflow/en/*.png` (bản `vi` cùng tên); những gì đã đổi so với Blender (Ctrl+N, Ctrl+O, Ctrl+S,
  Shift+Ctrl+O, hộp thoại hỏi lưu, màn hình đầu, Save Incremental đặt `_001`); thay đổi C++ và lý do (bốn file); số test;
  các quyết định tự đưa ra (Mục "Quyết định của kế hoạch" dưới đây và mọi quyết định phát sinh khi làm, kèm cái giá); việc
  còn để lại; việc cần làm (build lại bản cài, chọn merge/PR/giữ nhánh).
- [ ] **Step 5: Commit**
```bash
git add docs/superpowers/reports/2026-10-05-dasktoon-project-workflow-report.md
git commit -m "docs: add the project workflow report"
```

---

## Quyết định của kế hoạch (spec để kế hoạch chọn, hoặc spec im lặng)

| Chỗ | Quyết định | Vì sao |
|---|---|---|
| "New Model… Ctrl N" trong menu File (spec 7) | Mục gọi `wm.read_homefile` (lõi chuyển sang `dasktoon.model_new`). Keymap Blender không có mục nào cho lệnh đó, nên `interface.cc` cho nút `wm.read_homefile` hiện phím tắt của menu New (Ctrl+N mở menu đó) | Spec cấm sửa keymap và bắt Ctrl+N mở menu New; chữ phím tắt chỉ lấy được từ keymap. Industry Compatible (Ctrl+N = `wm.read_homefile`) hiện đúng mà không cần ngoại lệ |
| Open Recent (spec 7) | Bỏ menu C++ `TOPBAR_MT_file_open_recent`, đăng ký menu Python cùng tên; `TOPBAR_MT_dasktoon_project_recent` nhập vào đó | Python không thay được menu C++ cùng tên; Shift+Ctrl+O gọi đúng tên này |
| New Model với DaskToon Scene, Empty Scene, Copy of Model | Gọi lệnh Blender bằng invoke (hỏi lưu như Blender), rồi lõi chạy `dasktoon.model_new_finish` qua thuộc tính mới `post_read_operator` | Spec 8 muốn hộp thoại hỏi lưu của Blender cả khi "tạo mới"; hủy hộp thoại thì không có model nửa vời; Copy of Model lưu lại bằng Save As nên đường dẫn tương đối được đổi gốc đúng (chép byte thì hỏng khi model gốc nằm ở gốc dự án cũ) |
| Màn hình đầu đóng khi bấm | Bỏ `BLOCK_KEEP_OPEN` cho màn hình đầu, giữ cho Quick Setup | Không có API Python đóng popup; đóng sau khi lệnh đã đọc file khác thì block đã bị giải phóng |
| Thanh trên cùng cập nhật khi lưu | `space_topbar.cc` vẽ lại header khi có `ND_FILESAVE`, `ND_FILEREAD` | Trước đây header không nghe sự kiện lưu, nhãn "Draft" sẽ đứng yên sau khi lưu vào dự án |
| "Project" trong tiếng Việt | Menu Project dùng ngữ cảnh dịch "DaskToon" | `vi.po` dịch "Project" là "Phóng Chiếu" và bản Blender thắng ở ngữ cảnh mặc định |
| Save Incremental | DaskToon tự tính tên `<tên>_001.blend` rồi lưu bằng `wm.save_mainfile(filepath=...)` | Blender đặt `Hero1.blend`; spec ghi `_001` |
| Lưu vào file mới (Save to Project, Save Model As, Save Copy, Current Scene) | Dùng exec, không có hộp thoại ảnh đã sửa của Blender; DaskToon cảnh báo tên ảnh có nét vẽ chưa lưu | Spec 12 cho bản nháp; áp dụng chung cho mọi lần lưu sang file mới để hành vi giống nhau. Save và Save Incremental tại chỗ vẫn invoke nên hộp thoại của Blender còn |
| Dự án được chọn cho Engine Export, Models, Project | Dùng `selected_project()` (kể cả dự án gần đây nhất khi đang là bản nháp) | Theo định nghĩa spec 3; Phần 1 đã dùng dự án mở trong phiên cho bản nháp |
| Model gần đây | Ghi bằng handler `load_post`/`save_post`, bỏ qua khi chạy nền | Bắt được mọi lần mở (dòng lệnh, kéo thả, Open Recent) mà không ghi rác từ script và test |
| Unity Project để trống trong Project Settings | Bỏ gắn (`engines = []`) | Ô được điền sẵn đường dẫn hiện tại, nên để trống là ý của người dùng |
