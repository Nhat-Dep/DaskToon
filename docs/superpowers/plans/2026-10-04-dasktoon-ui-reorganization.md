# DaskToon: sắp xếp lại giao diện (Phần 1) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng chọn chạy **tự động, inline** (superpowers:executing-plans) trên nhánh `dasktoon-ui-reorganization`, commit từng task, tự quyết các điểm mơ hồ và ghi vào báo cáo. Không push.

**Goal:** Mỗi tính năng DaskToon nằm đúng nơi Blender vốn đặt loại việc đó, bỏ phần thừa/không có tác dụng, chữ gốc tiếng Anh có bản dịch tiếng Việt, chỉ còn 3 ngôn ngữ, bản cài khớp repo.

**Architecture:** Giữ module theo tính năng; mỗi module tự gắn giao diện vào đúng chỗ (Properties › Object Data, menu ⌄ của Material, Add menu, menu File). Bản dịch nằm trong `bl_ui/dasktoon_translations.py`, đăng ký bằng `bpy.app.translations`. Một bộ trích chuỗi bằng `ast` trong test bảo đảm không chữ nào thiếu bản dịch. Script `tools/dasktoon_sync_build.py` làm bản cài giống hệt repo.

**Tech Stack:** Python `bpy`, `bpy.app.translations`, `ast`, `unittest` chạy trong DaskToon; Unity 6000.5.4f1 cho bài so sánh render cuối.

**Spec:** `docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md`

---

## Môi trường và các lệnh dùng chung

Git Bash, thư mục gốc `d:/DaskToon`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
INSTALL=/d/build_windows_x64_vc17_Release/bin/Release/5.2
PY=$INSTALL/python/bin/python.exe
```

- **Đồng bộ bản cài** (từ Task 1 trở đi, thay cho `cp -r`): `"$PY" tools/dasktoon_sync_build.py "$INSTALL"`.
  Trước Task 1 dùng `cp -r scripts/startup/. "$INSTALL/scripts/startup/" && cp -r scripts/modules/. "$INSTALL/scripts/modules/"`.
- **Chạy một file test**: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py 2>&1 | tail -30`
- **Toàn bộ test DaskToon**: mọi file trong danh sách `foreach(dasktoon_test ...)` của `tests/python/CMakeLists.txt`.

### Đã kiểm chứng trước khi viết kế hoạch

- `bpy.app.translations.register(name, {"vi_VN": {(ngữ cảnh, chữ): bản dịch}})` chạy; đặt
  `bpy.context.preferences.view.language = 'vi_VN'` trong headless thì `pgettext_iface/tip/rpt` trả bản dịch. Ngữ cảnh
  mặc định là `"*"`, tên lệnh dùng `"Operator"`.
- Chữ mà bản dịch tiếng Việt của Blender (`vi.po`, 96%) đã có thì **bản của Blender thắng** (vd. "Shadow Color" → "Màu Bóng
  Tối"). Test bản dịch vì thế kiểm *chữ hiển thị thật*, không đòi chữ đó phải có trong bảng của DaskToon.
- Header node dùng `IFACE_(ui_name)` (ngữ cảnh mặc định); ô node dùng ngữ cảnh khai báo trên ô (mặc định `"*"`); menu Add
  dùng ngữ cảnh của node.
- Bản build **không có** `bl_i18n_utils` (công cụ trích chuỗi của Blender), nên tự viết bộ trích bằng `ast`.
- Khác biệt giữa bản cài và repo trong `scripts/startup`, `scripts/modules` chỉ là 6 file sót (không có file hợp lệ nào do
  build sinh ra), nên "soi gương" an toàn.
- `dasktoon_init.py` import `bl_ui.dasktoon_anime_nodes` **không bọc try**: phải sửa trước khi xóa module đó.
- Trong `node_shader_light_info.cc`, "Light Vector" là ô **ra**; chỉ `ShaderNodeAnimeFaceShadow` có ô **vào** "Light Vector".

## Global Constraints

- Không push. Commit từng task trên nhánh `dasktoon-ui-reorganization`. Không sửa C++/GLSL, shader Unity, tên engine.
- Không ghi vào project Unity trong `D:\Unity\`; test Unity chỉ dùng `%TEMP%/dasktoon_unity_test`. Không lưu `tdt.blend`.
- **Chữ gốc tiếng Anh, kiểu Blender**: tên viết hoa chữ đầu mỗi từ, mô tả là câu thường, **không emoji**, icon có sẵn
  của Blender. Không còn ký tự tiếng Việt trong chuỗi giao diện của source.
- **Cách viết chuỗi để dịch được**:
  - Chữ cố định đặt thẳng vào `text=`, `bl_label`, docstring, `name=`/`description=`, mục enum: Blender tự dịch.
  - Chữ có biến: dịch mẫu trước rồi mới điền: `iface_("Proxy of %s") % name` với `translate=False` cho `layout`;
    `rpt_("...") % ...` cho `self.report` và thông báo lỗi; `tip_` cho mô tả. Import:
    `from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_, pgettext_tip as tip_, pgettext_n as n_`.
  - Chữ nằm trong bảng dữ liệu (thẻ tham chiếu, danh sách…): bọc `n_("...")` ở chỗ định nghĩa, dịch bằng `iface_` khi vẽ.
  - Không dùng f-string cho chữ hiển thị.
- **Mã định danh giữ nguyên** (`dasktoon.*`, thuộc tính lưu trong file), trừ những thứ spec bỏ hoặc đổi chỗ.
- Bảng dịch đăng ký mỗi mục cho cả ngữ cảnh `"*"` và `"Operator"`.
- Light Bleed = **0.70**, Hand Wobble = **0.15** (cố định).
- `locale/languages` giữ đúng `0:Automatic:DEFAULT:100%`, `1:English (US):en_US:100%`, `41:Vietnamese - Tiếng Việt:vi_VN:96%`.
- Lỗ hổng AI Bridge đã được gỡ ở `92cadb7926e`; không đưa lại. Không chép access token trong `Editor.log` của Unity.

## Review Focus

1. **Chữ ghép động không dịch được** (chuỗi nối `+`, f-string, `%` sau khi đã dịch). Người dùng tiếng Việt mong thấy cả câu
   tiếng Việt. Bộ trích `ast` (Task 4) báo f-string và nối chuỗi trong `text=`/`report` là lỗi; test ở từng task.
2. **Mở file .blend cũ** có cài đặt Render giả, outline Light Bleed chỉnh tay, driver "Sync Sun", material outline kiểu cũ:
   không lỗi, được đưa về đúng. Test ở Task 5 (driver), Task 6 (outline), Task 3 (thuộc tính Render không còn).
3. **Panel con trong Properties khi không có dữ liệu** (mesh chưa có shape key, Empty không phải khối trứng, object không
   phải mesh): không vẽ lỗi, không hiện nút vô nghĩa. Test ở Task 7 và Task 10.
4. **Bản cài bị đồng bộ từ nhánh cũ** (file đã xóa quay lại). Test "bản cài khớp repo" ở Task 1 bắt được.
5. **Đổi tên built-in Shading Style** làm hỏng style người dùng đã lưu hoặc file đã áp style. Task 12 kiểm tra style
   người dùng (file JSON) vẫn đọc được và tên cũ vẫn tra được.

---

### Task 1: Script đồng bộ bản cài và test bản cài khớp repo

**Files:**
- Create: `tools/dasktoon_sync_build.py`
- Create: `tests/python/dasktoon_install_test.py`
- Modify: `tests/python/CMakeLists.txt`

**Interfaces:**
- Produces: `dasktoon_sync_build.mirror_tree(src, dst, dry_run=False) -> list[(verb, relpath)]`,
  `sync_locale(repo, install, dry_run=False) -> list`, `sync(install, dry_run=False) -> list`, `MIRRORED`.

- [ ] **Step 1: Viết test (đỏ vì chưa có script, và vì bản cài còn 6 file sót)**

File: `tests/python/dasktoon_install_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The installed DaskToon matches the repository (UI spec 8): the sync script, and a check of the running install."""

import importlib.util
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("dasktoon_sync_build",
                                               os.path.join(REPO, "tools", "dasktoon_sync_build.py"))
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def files(root):
    out = set()
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        out.update(os.path.relpath(os.path.join(base, n), root).replace(os.sep, "/") for n in names)
    return out


class SyncScriptTest(unittest.TestCase):
    def setUp(self):
        base = tempfile.mkdtemp(prefix="dt_sync_")
        self.src, self.dst = os.path.join(base, "src"), os.path.join(base, "dst")
        write(os.path.join(self.src, "a.py"), "new")
        write(os.path.join(self.src, "pkg", "b.py"), "b")
        write(os.path.join(self.dst, "a.py"), "old")
        write(os.path.join(self.dst, "stale.py"))
        write(os.path.join(self.dst, "old_pkg", "c.py"))
        write(os.path.join(self.dst, "pkg", "__pycache__", "b.cpython-313.pyc"))

    def test_mirror_copies_changes_and_removes_what_the_repository_does_not_have(self):
        actions = sync.mirror_tree(self.src, self.dst)
        self.assertEqual(files(self.dst), {"a.py", "pkg/b.py"})
        with open(os.path.join(self.dst, "a.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "new")
        self.assertTrue(os.path.exists(os.path.join(self.dst, "pkg", "__pycache__", "b.cpython-313.pyc")))
        verbs = {(verb, path.replace(os.sep, "/")) for verb, path in actions}
        self.assertTrue({("copy", "a.py"), ("copy", "pkg/b.py"), ("remove", "stale.py"), ("remove", "old_pkg/")} <= verbs)
        self.assertEqual(sync.mirror_tree(self.src, self.dst), [])

    def test_dry_run_changes_nothing(self):
        before = files(self.dst)
        self.assertTrue(sync.mirror_tree(self.src, self.dst, dry_run=True))
        self.assertEqual(files(self.dst), before)

    def test_locale_keeps_only_languages_that_have_a_po_file(self):
        base = tempfile.mkdtemp(prefix="dt_sync_locale_")
        repo, install = os.path.join(base, "repo"), os.path.join(base, "install")
        write(os.path.join(repo, "locale", "languages"), "0:Automatic:DEFAULT:100%\n")
        write(os.path.join(repo, "locale", "po", "vi.po"))
        write(os.path.join(install, "datafiles", "locale", "languages"), "old")
        write(os.path.join(install, "datafiles", "locale", "vi", "LC_MESSAGES", "blender.mo"))
        write(os.path.join(install, "datafiles", "locale", "ja", "LC_MESSAGES", "blender.mo"))
        sync.sync_locale(repo, install)
        locale = os.path.join(install, "datafiles", "locale")
        self.assertEqual(sorted(os.listdir(locale)), ["languages", "vi"])
        with open(os.path.join(locale, "languages"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "0:Automatic:DEFAULT:100%\n")


class InstalledBuildTest(unittest.TestCase):
    def test_installed_scripts_match_the_repository(self):
        """A file removed from the repository must not stay in the install (Blender would keep loading it)."""
        installed = bpy.utils.system_resource('SCRIPTS')
        for sub in sync.MIRRORED:
            src = os.path.join(REPO, *sub.split("/"))
            dst = os.path.join(installed, os.path.basename(sub))
            self.assertEqual(sync.mirror_tree(src, dst, dry_run=True), [], sub)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ**

Run: `"$DT" ... --python tests/python/dasktoon_install_test.py`
Expected: FAIL — `FileNotFoundError` cho `tools/dasktoon_sync_build.py`.

- [ ] **Step 3: Viết script**

File: `tools/dasktoon_sync_build.py`
```python
#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Make an installed DaskToon match this repository: scripts/startup, scripts/modules and the translations.

    python tools/dasktoon_sync_build.py D:/build_windows_x64_vc17_Release/bin/Release/5.2 [--dry-run]

Changed files are copied, and files or folders the repository does not have are removed: copying alone left removed
modules behind, and Blender kept loading them. datafiles/locale/languages is copied and installed language folders
without a locale/po/<language>.po are removed."""

import argparse
import filecmp
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRRORED = ("scripts/startup", "scripts/modules")
SKIP = {"__pycache__"}


def mirror_tree(src, dst, dry_run=False):
    """Make `dst` a copy of `src`, leaving __pycache__ folders alone. Returns [(verb, relative path)]."""
    actions = []
    for base, dirs, names in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        rel = os.path.relpath(base, src)
        for name in sorted(names):
            source = os.path.join(base, name)
            target = os.path.normpath(os.path.join(dst, rel, name))
            if not os.path.isfile(target) or not filecmp.cmp(source, target, shallow=False):
                actions.append(("copy", os.path.normpath(os.path.join(rel, name))))
                if not dry_run:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(source, target)
    if not os.path.isdir(dst):
        return actions
    for base, dirs, names in os.walk(dst):
        rel = os.path.relpath(base, dst)
        source_dir = os.path.normpath(os.path.join(src, rel))
        kept = []
        for name in sorted(dirs):
            if name in SKIP:
                continue
            if os.path.isdir(os.path.join(source_dir, name)):
                kept.append(name)
                continue
            actions.append(("remove", os.path.normpath(os.path.join(rel, name)) + os.sep))
            if not dry_run:
                shutil.rmtree(os.path.join(base, name))
        dirs[:] = kept
        for name in sorted(names):
            if not os.path.exists(os.path.join(source_dir, name)):
                actions.append(("remove", os.path.normpath(os.path.join(rel, name))))
                if not dry_run:
                    os.remove(os.path.join(base, name))
    return actions


def sync_locale(repo, install, dry_run=False):
    """Copy locale/languages and remove installed language folders that have no .po file in the repository."""
    actions = []
    locale_dir = os.path.join(install, "datafiles", "locale")
    source = os.path.join(repo, "locale", "languages")
    target = os.path.join(locale_dir, "languages")
    if not os.path.isfile(target) or not filecmp.cmp(source, target, shallow=False):
        actions.append(("copy", "datafiles/locale/languages"))
        if not dry_run:
            os.makedirs(locale_dir, exist_ok=True)
            shutil.copy2(source, target)
    kept = {os.path.splitext(n)[0] for n in os.listdir(os.path.join(repo, "locale", "po")) if n.endswith(".po")}
    if os.path.isdir(locale_dir):
        for name in sorted(os.listdir(locale_dir)):
            if os.path.isdir(os.path.join(locale_dir, name)) and name not in kept:
                actions.append(("remove", "datafiles/locale/%s/" % name))
                if not dry_run:
                    shutil.rmtree(os.path.join(locale_dir, name))
    return actions


def sync(install, dry_run=False, repo=REPO):
    actions = []
    for sub in MIRRORED:
        name = os.path.basename(sub)
        actions += [(verb, "scripts/%s/%s" % (name, path)) for verb, path in
                    mirror_tree(os.path.join(repo, *sub.split("/")), os.path.join(install, "scripts", name), dry_run)]
    actions += sync_locale(repo, install, dry_run)
    return actions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("install", help="the version folder of the install, e.g. .../bin/Release/5.2")
    parser.add_argument("--dry-run", action="store_true", help="only list what would change")
    args = parser.parse_args(argv)
    if not os.path.isdir(os.path.join(args.install, "scripts")):
        parser.error("%s has no scripts folder" % args.install)
    actions = sync(args.install, args.dry_run)
    for verb, path in actions:
        print("%-6s %s" % (verb, path.replace(os.sep, "/")))
    print("%d change(s)%s" % (len(actions), " (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Chạy thử trước, rồi đồng bộ thật**

Run: `"$PY" tools/dasktoon_sync_build.py "$INSTALL" --dry-run`
Expected: liệt kê đúng 6 file sót cần xóa (`goo_engine_light_groups.py`, 2 thư mục app template, `engine_unity.py`,
`unity_shader_graph.py`, `dasktoon_uv_optimizer.py`) và có thể vài file `copy` nếu bản cài cũ hơn repo; không có `remove`
nào khác. Sau đó chạy không có `--dry-run`.

- [ ] **Step 5: Chạy test, phải xanh**

Expected: `Ran 4 tests ... OK`.

- [ ] **Step 6: Đăng ký và commit**

Thêm `dasktoon_install_test` vào danh sách `foreach(dasktoon_test ...)`.
```bash
git add tools/dasktoon_sync_build.py tests/python/dasktoon_install_test.py tests/python/CMakeLists.txt
git commit -m "feat: add a sync script that makes the installed DaskToon match the repository, with a check of the install"
```

---

### Task 2: Chỉ giữ Automatic, English, Tiếng Việt

**Files:**
- Modify: `locale/languages`
- Delete: 48 file `locale/po/*.po` (mọi file trừ `vi.po`)
- Create: `tests/python/dasktoon_languages_test.py`; Modify: `tests/python/CMakeLists.txt`

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_languages_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Preferences › Interface › Language offers Automatic, English and Tiếng Việt only (UI spec 7)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LanguagesTest(unittest.TestCase):
    def test_language_list(self):
        with open(os.path.join(REPO, "locale", "languages"), encoding="utf-8") as f:
            entries = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        self.assertEqual(entries, ["0:Automatic:DEFAULT:100%", "1:English (US):en_US:100%",
                                   "41:Vietnamese - Tiếng Việt:vi_VN:96%"])
        self.assertEqual(sorted(os.listdir(os.path.join(REPO, "locale", "po"))), ["vi.po"])

    def test_installed_languages(self):
        self.assertEqual(sorted(bpy.app.translations.locales), ["en_US", "vi_VN"])
        locale_dir = os.path.join(bpy.utils.system_resource('DATAFILES'), "locale")
        self.assertEqual(sorted(n for n in os.listdir(locale_dir) if os.path.isdir(os.path.join(locale_dir, n))), ["vi"])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (51 mục, 49 file `.po`, 50 locale).

- [ ] **Step 3: Sửa danh sách và xóa `.po`**

`locale/languages`: giữ nguyên 10 dòng chú thích đầu file, thêm dòng
`# DaskToon keeps English and Vietnamese only (docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md).`
rồi chỉ 3 dòng ngôn ngữ ở Global Constraints. Xóa: `git rm` mọi `locale/po/*.po` trừ `vi.po`.
Đồng bộ: `"$PY" tools/dasktoon_sync_build.py "$INSTALL"` (chép `languages`, xóa 48 thư mục ngôn ngữ).

- [ ] **Step 4: Chạy test, phải xanh** — Expected: `Ran 2 tests ... OK`; `dasktoon_install_test.py` vẫn OK.

- [ ] **Step 5: Đăng ký và commit**
```bash
git add -A locale/ tests/python/dasktoon_languages_test.py tests/python/CMakeLists.txt
git commit -m "feat: offer only Automatic, English and Vietnamese in the language list"
```

---

### Task 3: Bỏ phần không có tác dụng (Render, Light, Suite, node group Python, công cụ normal cũ)

**Files:**
- Delete: `scripts/startup/bl_ui/properties_dasktoon.py`, `scripts/startup/bl_ui/dasktoon_anime_nodes.py`,
  `scripts/startup/bl_ui/dasktoon_face_normals.py`, `scripts/startup/dasktoon_light_groups.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (bỏ 3 tên khỏi `_modules`), `scripts/startup/bl_ui/engine_dasktoon_anime.py`
  (chỉ còn đoạn COMPAT), `scripts/startup/bl_ui/properties_data_light.py` (bỏ `DATA_PT_DaskToon_light_npr`),
  `scripts/startup/bl_ui/dasktoon_outline.py` (nhận `_sync_outline_socket`, `_sync_outline_node_subgraph`),
  `scripts/startup/bl_ui/dasktoon_upgrade.py` (import mới), `scripts/startup/dasktoon_init.py`,
  `scripts/startup/bl_ui/dasktoon_face_shading.py` (bỏ panel *Nâng cao*, nút gợi ý dùng lệnh Blender)
- Create: `tests/python/dasktoon_ui_layout_test.py`
- Modify: `tests/python/dasktoon_face_shading_test.py`, `tests/python/dasktoon_outline_sync_test.py`, `tests/python/CMakeLists.txt`

**Interfaces:**
- Produces: `bl_ui.dasktoon_outline._sync_outline_socket(src_socket, target_tree, target_socket, visited_nodes)` và
  `_sync_outline_node_subgraph(src_socket, target_tree, target_socket)` (chuyển nguyên văn).
- Produces: `tests/python/dasktoon_ui_layout_test.py` với `REMOVED` (tên trong `bpy.types`) — các task sau thêm vào.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_ui_layout_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where the DaskToon interface lives (UI spec 3): removed parts stay removed, moved parts sit in their new place."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

# Names in bpy.types (panels by bl_idname or class name, operators by their OT name).
REMOVED = (
    "DASKTOON_RENDER_PT_header", "DASKTOON_RENDER_PT_cel_shading", "DASKTOON_RENDER_PT_lineart",
    "DASKTOON_RENDER_PT_shadows", "DASKTOON_RENDER_PT_manga", "DASKTOON_RENDER_PT_animation",
    "DASKTOON_RENDER_PT_presets", "DaskToonEngineSettings", "DASKTOON_OT_setup_lighting", "DASKTOON_OT_setup_lineart",
    "DATA_PT_DaskToon_light_npr", "DASKTOON_PT_light_groups",
    "VIEW3D_PT_dasktoon_main", "VIEW3D_PT_dasktoon_shader_nodes", "DASKTOON_OT_activate_engine",
    "DASKTOON_OT_setup_anime_preset", "NODE_OT_dasktoon_add_anime_node", "DASKTOON_OT_link_sun_direction",
    "DASKTOON_OT_fix_face_normals", "DASKTOON_OT_reset_face_normals", "DASKTOON_OT_toggle_face_normals_display",
    "DASKTOON_PT_face_shading_advanced",
)
REMOVED_MODULES = ("dasktoon_light_groups", "bl_ui.dasktoon_anime_nodes", "bl_ui.dasktoon_face_normals",
                   "bl_ui.properties_dasktoon")


def subclasses(base):
    out, stack = [], list(base.__subclasses__())
    while stack:
        cls = stack.pop()
        out.append(cls)
        stack.extend(cls.__subclasses__())
    return out


class RemovedUITest(unittest.TestCase):
    def test_removed_classes_are_not_registered(self):
        self.assertEqual([name for name in REMOVED if hasattr(bpy.types, name)], [])
        self.assertFalse(hasattr(bpy.types.Scene, "dasktoon_engine"))

    def test_removed_modules_are_not_loaded(self):
        self.assertEqual([name for name in REMOVED_MODULES if name in sys.modules], [])

    def test_dasktoon_engine_shows_the_eevee_settings(self):
        missing = [cls.__name__ for cls in subclasses(bpy.types.Panel)
                   if getattr(cls, "is_registered", False) and isinstance(getattr(cls, "COMPAT_ENGINES", None), set)
                   and 'BLENDER_EEVEE' in cls.COMPAT_ENGINES and 'DASKTOON_ANIME' not in cls.COMPAT_ENGINES]
        self.assertEqual(missing, [])

    def test_startup_init_still_sets_the_standard_view(self):
        import dasktoon_init
        tu.reset_scene()
        scene = bpy.context.scene
        scene.view_settings.view_transform = 'AgX'
        dasktoon_init.dasktoon_enforce_color_management(scene)
        self.assertEqual(scene.view_settings.view_transform, 'Standard')


if __name__ == "__main__":
    tu.run_tests()
```

Sửa `tests/python/dasktoon_face_shading_test.py` (lớp `FaceShadingUITest`):
- `test_classes_are_registered_and_the_old_panel_is_gone`: bỏ `DASKTOON_PT_face_shading_advanced`,
  `DASKTOON_OT_fix_face_normals`, `DASKTOON_OT_reset_face_normals` khỏi danh sách phải có; bỏ dòng kiểm `bl_parent_id`.
- `test_panel_suggests_clearing_old_custom_normals`: chờ `("operator", "mesh.customdata_custom_splitnormals_clear")`.
- Xóa `test_advanced_panel_holds_the_old_tools`.

Sửa `tests/python/dasktoon_outline_sync_test.py`: xóa test gọi `bpy.ops.dasktoon.setup_anime_preset` (quanh dòng 159).

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL — các class trong `REMOVED` vẫn đăng ký; module vẫn nạp.

- [ ] **Step 3: Chuyển hai hàm đồng bộ outline**

Chép nguyên văn `_sync_outline_socket` và `_sync_outline_node_subgraph` (cuối `dasktoon_anime_nodes.py`) vào
`dasktoon_outline.py` (ngay trên `_set_value`); trong `_sync_socket` bỏ dòng `from .dasktoon_anime_nodes import ...`. Trong
`dasktoon_upgrade.py` đổi `from .dasktoon_anime_nodes import _sync_outline_socket` thành
`from .dasktoon_outline import _sync_outline_socket`.

- [ ] **Step 4: Xóa và rút gọn**

- `git rm` 4 file ở mục Delete; bỏ `"properties_dasktoon"`, `"dasktoon_anime_nodes"`, `"dasktoon_face_normals"` khỏi
  `_modules` trong `bl_ui/__init__.py`.
- `engine_dasktoon_anime.py` thay toàn bộ bằng:

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon Anime Engine renders with EEVEE, so it shows the EEVEE settings: every panel that supports
BLENDER_EEVEE also supports DASKTOON_ANIME."""

import bpy

classes = ()


def register():
    for cls in bpy.types.Panel.__subclasses__():
        engines = getattr(cls, "COMPAT_ENGINES", None)
        if isinstance(engines, set) and 'BLENDER_EEVEE' in engines:
            engines.add('DASKTOON_ANIME')
```

  Ghi chú: test `test_dasktoon_engine_shows_the_eevee_settings` duyệt cả lớp con gián tiếp; nếu nó báo panel thiếu (panel
  kế thừa qua lớp trung gian), đổi vòng lặp sang hàm `subclasses()` như trong test.
- `properties_data_light.py`: xóa class `DATA_PT_DaskToon_light_npr` và dòng của nó trong `classes`.
- `dasktoon_init.py`: `register()` chỉ còn `dasktoon_enforce_color_management()` (và handler load nếu file đang có);
  `unregister()` không còn import nào; bỏ mọi tham chiếu `dasktoon_anime_nodes`, `dasktoon_light_groups`,
  `dasktoon_ai_bridge`; sửa docstring đầu file cho đúng.
- `dasktoon_face_shading.py`: xóa class `DASKTOON_PT_face_shading_advanced` (và khỏi `classes`); nút gợi ý custom normal
  đổi thành `box.operator("mesh.customdata_custom_splitnormals_clear", icon='LOOP_BACK')`.

- [ ] **Step 5: Đồng bộ bản cài và chạy test**

Run: đồng bộ bằng script, rồi `dasktoon_ui_layout_test.py`, `dasktoon_face_shading_test.py`, `dasktoon_outline_sync_test.py`,
`dasktoon_upgrade_test.py`, `dasktoon_outline_nodes_test.py`, `dasktoon_install_test.py`.
Expected: tất cả OK.

- [ ] **Step 6: Đăng ký và commit**
```bash
git add -A scripts/ tests/python/
git commit -m "refactor: remove DaskToon panels and tools that had no effect or repeated Blender's own"
```

---

### Task 4: Hạ tầng bản dịch và bộ trích chuỗi; dịch Engine Export

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_translations.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_translations"` vào `_modules`, trước các module dasktoon khác)
- Create: `tests/python/dasktoon_i18n_utils.py` (helper), `tests/python/dasktoon_translations_test.py`
- Modify: `scripts/startup/bl_ui/dasktoon_engine_export.py` (chữ sang tiếng Anh), `tests/python/CMakeLists.txt`

**Interfaces:**
- Produces: `bl_ui.dasktoon_translations.VI: dict[str, str]`, `KEEP: set[str]`, `translations`.
- Produces: `dasktoon_i18n_utils.module_strings(path) -> (set[str], list[str])` (chữ, và các vị trí ghép động),
  `language(code)` (context manager), `untranslated(msgids, keep) -> list[str]`, `VI_CHARS`, `EMOJI`.
- Produces: `dasktoon_translations_test.TRANSLATED` — danh sách file mà các task sau thêm vào.

- [ ] **Step 1: Viết helper và test (đỏ vì chưa có module dịch)**

File: `tests/python/dasktoon_i18n_utils.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Collect the strings a DaskToon source file shows, and check them against the active translation (test helper)."""

import ast
import contextlib
import re

import bpy

UI_KEYWORDS = {"text", "name", "description", "label", "title", "message", "confirm_text"}
TRANSLATE_CALLS = {"pgettext", "pgettext_iface", "pgettext_tip", "pgettext_rpt", "pgettext_data", "pgettext_n",
                   "iface_", "tip_", "rpt_", "n_", "data_"}
UI_BASES = {"Operator", "Panel", "Menu", "PropertyGroup", "UIList", "AddonPreferences"}
VI_CHARS = re.compile("[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"
                      "ĂÂĐÊÔƠƯÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")


def _name(func):
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def _literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def module_strings(path):
    """(strings, dynamic): the user-visible string literals of a Python file, and the places where a visible string
    is built at run time (f-string or concatenation in text=/report/an error message), which cannot be translated."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    strings, dynamic = set(), []

    def take(node, where):
        value = _literal(node)
        if value is not None:
            strings.add(value)
        elif isinstance(node, ast.JoinedStr) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            dynamic.append("%s line %d: %s" % (where, node.lineno, ast.unparse(node)[:80]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _name(node.func)
            if name in TRANSLATE_CALLS and node.args:
                take(node.args[0], name)
            if name == "report" and len(node.args) >= 2:
                take(node.args[1], "report")
            if name.endswith("Error") and node.args:
                take(node.args[0], name)
            for kw in node.keywords:
                if kw.arg in UI_KEYWORDS:
                    take(kw.value, kw.arg)
                if kw.arg == "items" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    for item in kw.value.elts:
                        if isinstance(item, ast.Tuple):
                            for part in item.elts[1:3]:
                                take(part, "enum item")
        elif isinstance(node, ast.ClassDef):
            bases = {_name(b) for b in node.bases}
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id in ("bl_label", "bl_description"):
                            take(stmt.value, target.id)
            if bases & UI_BASES:
                doc = ast.get_docstring(node)
                if doc:
                    strings.add(doc)
    strings.discard("")
    return strings, dynamic


def visible(msgid):
    return re.search("[A-Za-z]", msgid) is not None


@contextlib.contextmanager
def language(code):
    view = bpy.context.preferences.view
    saved = view.language
    view.language = code
    try:
        yield
    finally:
        view.language = saved


def untranslated(msgids, keep=()):
    """The visible msgids that the active language shows unchanged (neither Blender nor DaskToon translates them)."""
    tr = bpy.app.translations
    missing = []
    for msgid in sorted(msgids):
        if not visible(msgid) or msgid in keep:
            continue
        if any(fn(msgid, ctx) != msgid for fn in (tr.pgettext_iface, tr.pgettext_tip, tr.pgettext_rpt)
               for ctx in ("*", "Operator")):
            continue
        missing.append(msgid)
    return missing
```

File: `tests/python/dasktoon_translations_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""English source strings with a Vietnamese translation shown when the language is Tiếng Việt (UI spec 6)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Grows task by task; Task 12 checks that it covers every DaskToon file.
TRANSLATED = [
    "scripts/startup/bl_ui/dasktoon_engine_export.py",
]


def path(rel):
    return os.path.join(REPO, *rel.split("/"))


class TranslationTest(unittest.TestCase):
    def test_vietnamese_shows_only_when_the_language_is_vietnamese(self):
        iface = bpy.app.translations.pgettext_iface
        with iu.language('vi_VN'):
            self.assertEqual(iface("Engine Export", "Operator"), dt.VI["Engine Export"])
        self.assertEqual(iface("Engine Export", "Operator"), "Engine Export")

    def test_source_strings_are_english_without_emoji(self):
        for rel in TRANSLATED:
            strings, _dynamic = iu.module_strings(path(rel))
            bad = sorted(s for s in strings if iu.VI_CHARS.search(s) or iu.EMOJI.search(s))
            self.assertEqual(bad, [], rel)

    def test_no_visible_string_is_built_at_run_time(self):
        for rel in TRANSLATED:
            self.assertEqual(iu.module_strings(path(rel))[1], [], rel)

    def test_every_visible_string_is_translated(self):
        with iu.language('vi_VN'):
            for rel in TRANSLATED:
                self.assertEqual(iu.untranslated(iu.module_strings(path(rel))[0], dt.KEEP), [], rel)

    def test_translation_table_is_vietnamese(self):
        for msgid, msgstr in dt.VI.items():
            self.assertTrue(msgstr.strip(), msgid)
            self.assertFalse(iu.EMOJI.search(msgstr), msgid)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL — `ImportError: cannot import name 'dasktoon_translations'`.

- [ ] **Step 3: Viết module dịch**

File: `scripts/startup/bl_ui/dasktoon_translations.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Vietnamese translation of the DaskToon interface (docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md,
section 6). The source strings are English; with Preferences › Interface › Language set to Tiếng Việt Blender shows
these. Strings Blender already translates keep Blender's wording. Every entry is registered for the default context
("*") and for operator names ("Operator")."""

import bpy

# Names that stay as they are in Vietnamese (brands, standards, shape key names).
KEEP = {
    "DaskToon", "Unity", "Unity 6 (URP)", "VRM", "VRoid", "ARKit", "FBX", "URP",
}

VI = {
    # bl_ui/dasktoon_engine_export.py
    "Engine Export": "Xuất sang engine",
    "Engine Export…": "Xuất sang engine…",
}


def _table():
    table = {}
    for msgid, msgstr in VI.items():
        for context in ("*", "Operator"):
            table[(context, msgid)] = msgstr
    return {"vi_VN": table}


translations = _table()
classes = ()


def register():
    try:
        bpy.app.translations.unregister(__name__)
    except (ValueError, RuntimeError):
        pass
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)
```

Thêm `"dasktoon_translations",` vào `_modules` ngay trước `"properties_dasktoon"` cũ (tức trước `"engine_dasktoon_anime"`).

- [ ] **Step 4: Chuyển `dasktoon_engine_export.py` sang tiếng Anh và bổ sung bản dịch**

| Cũ | Mới (chữ gốc) |
|---|---|
| "Ghi thẳng vào project Unity" | "Writes straight into the Unity project" |
| `"Tạo thư mục " + name` | `iface_("Creates the folder %s") % name` (`translate=False`) |
| "Engine này sắp có; hiện chỉ hỗ trợ Unity 6 (URP)" | "This engine is coming soon; only Unity 6 (URP) is supported for now" |
| "Chưa chọn thư mục đích" | "No destination folder chosen" |
| "Không có object nào để export (chưa chọn object?)" | "Nothing to export (no object selected?)" |

Mọi chữ khác của file (nhãn thuộc tính, mục enum, mô tả) cũng sang tiếng Anh. Thêm vào `VI` bản dịch của **mọi** chữ test
còn báo thiếu (`test_every_visible_string_is_translated` liệt kê chúng), đặt dưới chú thích `# bl_ui/dasktoon_engine_export.py`.
Chữ do `rep.summary()` trả về thuộc thư viện export (Task 12).

- [ ] **Step 5: Chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_translations_test.py`, `dasktoon_engine_export_ui_test.py`.
Expected: OK (cập nhật test UI nào đang so chữ tiếng Việt cũ sang chữ mới).

- [ ] **Step 6: Đăng ký và commit**
```bash
git add scripts/startup/bl_ui/ tests/python/
git commit -m "feat: add the Vietnamese translation table and its coverage test; translate Engine Export"
```

---

### Task 5: Hướng Sun tự đồng bộ

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_sun_sync.py`; Modify: `scripts/startup/bl_ui/__init__.py` (thêm vào `_modules`)
- Create: `tests/python/dasktoon_sun_sync_test.py`; Modify: `tests/python/CMakeLists.txt`

**Interfaces:**
- Produces: `dasktoon_sun_sync.find_sun(scene)`, `sun_vector(sun) -> Vector`, `sync_materials(materials, vector) -> int`
  (số ô đã đổi), handler `sun_depsgraph_post`, `sun_load_post`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_sun_sync_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Light Vector inputs follow the scene Sun without a button or drivers (UI spec 5)."""

import math
import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_sun_sync as ss  # noqa: E402


def face_shadow_material(name="Face"):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeFaceShadow')
    return mat, node


def close(a, b):
    return (Vector(a) - Vector(b)).length < 1e-5


class SunSyncTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.sun = tu.add_sun(rotation=(math.radians(40.0), 0.0, math.radians(30.0)))
        bpy.context.view_layer.update()

    def test_sync_writes_the_sun_direction_once(self):
        mat, node = face_shadow_material()
        vector = ss.sun_vector(self.sun)
        self.assertEqual(ss.sync_materials([mat], vector), 1)
        self.assertTrue(close(node.inputs["Light Vector"].default_value, vector))
        self.assertEqual(ss.sync_materials([mat], vector), 0)

    def test_linked_input_is_left_alone(self):
        mat, node = face_shadow_material()
        combine = mat.node_tree.nodes.new('ShaderNodeCombineXYZ')
        mat.node_tree.links.new(combine.outputs[0], node.inputs["Light Vector"])
        before = tuple(node.inputs["Light Vector"].default_value)
        self.assertEqual(ss.sync_materials([mat], ss.sun_vector(self.sun)), 0)
        self.assertEqual(tuple(node.inputs["Light Vector"].default_value), before)

    def test_node_inside_a_group_follows_too(self):
        group = bpy.data.node_groups.new("FaceGroup", 'ShaderNodeTree')
        inner = group.nodes.new('ShaderNodeAnimeFaceShadow')
        mat = tu.new_material("Grouped")
        holder = mat.node_tree.nodes.new('ShaderNodeGroup')
        holder.node_tree = group
        self.assertEqual(ss.sync_materials([mat], ss.sun_vector(self.sun)), 1)
        self.assertTrue(close(inner.inputs["Light Vector"].default_value, ss.sun_vector(self.sun)))

    def test_old_sync_sun_driver_is_removed(self):
        mat, node = face_shadow_material()
        node.inputs["Light Vector"].driver_add("default_value", 0)
        ss.sync_materials([mat], ss.sun_vector(self.sun))
        drivers = mat.node_tree.animation_data.drivers if mat.node_tree.animation_data else []
        self.assertEqual(len(drivers), 0)

    def test_rotating_the_sun_updates_materials_through_the_handler(self):
        mat, node = face_shadow_material()
        bpy.context.view_layer.update()
        self.sun.rotation_euler = (math.radians(70.0), 0.0, math.radians(-60.0))
        bpy.context.view_layer.update()
        self.assertTrue(close(node.inputs["Light Vector"].default_value, ss.sun_vector(self.sun)))

    def test_no_sun_changes_nothing(self):
        bpy.data.objects.remove(self.sun)
        mat, node = face_shadow_material()
        before = tuple(node.inputs["Light Vector"].default_value)
        bpy.context.view_layer.update()
        self.assertEqual(tuple(node.inputs["Light Vector"].default_value), before)
        self.assertIsNone(ss.find_sun(bpy.context.scene))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL — `ImportError: dasktoon_sun_sync`.

- [ ] **Step 3: Viết module**

File: `scripts/startup/bl_ui/dasktoon_sun_sync.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Light Vector inputs of DaskToon nodes (Face Shadow) follow the scene Sun (docs/superpowers/specs/
2026-10-04-dasktoon-ui-reorganization-design.md, section 5). Replaces the "Sync Sun" button and its scripted drivers,
which needed Auto Run Python Scripts."""

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

SOCKET = "Light Vector"
EPSILON = 1e-6
_busy = False
classes = ()


def find_sun(scene):
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN' and obj.visible_get():
            return obj
    return None


def sun_vector(sun):
    """Towards the Sun, as the old Sync Sun computed it."""
    return (sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()


def _trees(materials):
    seen, stack = set(), [m.node_tree for m in materials if m.node_tree is not None and m.library is None]
    while stack:
        tree = stack.pop()
        if tree.as_pointer() in seen or tree.library is not None:
            continue
        seen.add(tree.as_pointer())
        yield tree
        stack.extend(n.node_tree for n in tree.nodes if n.type == 'GROUP' and n.node_tree is not None)


def _drop_driver(tree, socket):
    animation = tree.animation_data
    if animation is None or not animation.drivers:
        return
    path = socket.path_from_id("default_value")
    for fcurve in list(animation.drivers):
        if fcurve.data_path == path:
            animation.drivers.remove(fcurve)


def sync_materials(materials, vector):
    """Write `vector` into every unlinked Light Vector input; returns how many inputs changed."""
    changed = 0
    for tree in _trees(materials):
        for node in tree.nodes:
            socket = node.inputs.get(SOCKET)
            if socket is None or socket.is_linked:
                continue
            _drop_driver(tree, socket)
            if max(abs(a - b) for a, b in zip(socket.default_value, vector)) > EPSILON:
                socket.default_value = vector
                changed += 1
    return changed


def _sync_scene(scene, materials):
    global _busy
    sun = find_sun(scene)
    if sun is None:
        return
    _busy = True
    try:
        sync_materials(materials, sun_vector(sun))
    finally:
        _busy = False


@persistent
def sun_depsgraph_post(scene, depsgraph):
    if _busy:
        return
    materials, lights = set(), False
    for update in depsgraph.updates:
        data = update.id.original
        if isinstance(data, bpy.types.Object) and data.type == 'LIGHT':
            lights = True
        elif isinstance(data, bpy.types.Material):
            materials.add(data)
    if lights:
        _sync_scene(scene, bpy.data.materials)
    elif materials:
        _sync_scene(scene, materials)


@persistent
def sun_load_post(_filepath):
    if bpy.context.scene is not None:
        _sync_scene(bpy.context.scene, bpy.data.materials)


def register():
    if sun_depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sun_depsgraph_post)
    if sun_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(sun_load_post)


def unregister():
    if sun_depsgraph_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sun_depsgraph_post)
    if sun_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(sun_load_post)
```

Thêm `"dasktoon_sun_sync",` vào `_modules` (sau `"dasktoon_outline_gamedata"`). Thêm file vào `TRANSLATED` của
`dasktoon_translations_test.py` (không có chữ hiển thị, test vẫn qua).

- [ ] **Step 4: Chạy test, phải xanh** — Expected: `Ran 6 tests ... OK`. Nếu test handler đỏ vì handler không chạy trong
  `reset_scene` (factory settings xóa handler không persistent): handler đã `@persistent`, kiểm lại `register()`.

- [ ] **Step 5: Đăng ký và commit**
```bash
git add scripts/startup/bl_ui/ tests/python/
git commit -m "feat: keep Light Vector inputs in line with the scene Sun automatically, without drivers"
```

---

### Task 6: Outline: Light Bleed / Hand Wobble cố định, bỏ panel Material, gỡ outline kiểu cũ qua menu ⌄

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_outline.py`, `scripts/startup/bl_ui/dasktoon_outline_gamedata.py` (chữ)
- Modify tests: `dasktoon_outline_sync_test.py`, `dasktoon_export_graph_test.py`, `dasktoon_export_layout_test.py`,
  `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `dasktoon_unity_render_test.py`, `dasktoon_visual_review.py`

**Interfaces:**
- Produces: `dasktoon_outline.LIGHT_BLEED = 0.70`, `HAND_WOBBLE = 0.15`, operator `dasktoon.outline_remove_legacy`
  ("Remove DaskToon Outline"), hàm `material_menu_func` gắn vào `MATERIAL_MT_context_menu`.

- [ ] **Step 1: Viết test**

Trong `dasktoon_outline_sync_test.py`: thay test "Light Bleed / Hand Wobble live on <material>.Outline…" (quanh dòng 124)
bằng:

```python
    def test_light_bleed_and_hand_wobble_are_fixed(self):
        mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(obj, mat)
        outline.sync_all(bpy.context.scene)
        dask = outline.outline_node(outline.outline_material_for(mat))
        dask.inputs["Light Bleed"].default_value = 0.2   # as an older file may have it
        dask.inputs["Hand Wobble"].default_value = 0.9
        outline.reset_cache()
        outline.sync_all(bpy.context.scene)
        self.assertAlmostEqual(dask.inputs["Light Bleed"].default_value, outline.LIGHT_BLEED, places=6)
        self.assertAlmostEqual(dask.inputs["Hand Wobble"].default_value, outline.HAND_WOBBLE, places=6)

    def test_legacy_material_outline_can_be_removed_from_the_slot_menu(self):
        mat = tu.emission_material("Plain", (1, 1, 1, 1))
        mat[outline.OUTLINE_PROP] = True
        obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(obj, mat)
        outline.sync_all(bpy.context.scene)
        self.assertIsNotNone(obj.modifiers.get("DaskToon Outline"))
        with bpy.context.temp_override(material=mat, object=obj):
            self.assertEqual(bpy.ops.dasktoon.outline_remove_legacy(), {'FINISHED'})
        self.assertNotIn(outline.OUTLINE_PROP, mat)
        outline.sync_all(bpy.context.scene)
        self.assertIsNone(obj.modifiers.get("DaskToon Outline"))
```

Trong `dasktoon_ui_layout_test.py`: thêm `"MATERIAL_PT_dasktoon_outline"`, `"DASKTOON_OT_outline_toggle_material"` vào
`REMOVED`, và lớp:

```python
def appended(menu, module):
    funcs = getattr(getattr(menu, "draw", None), "_draw_funcs", None) or []
    return [f for f in funcs if getattr(f, "__module__", "") == module]


class MovedUITest(unittest.TestCase):
    def test_outline_removal_is_in_the_material_slot_menu(self):
        self.assertTrue(appended(bpy.types.MATERIAL_MT_context_menu, "bl_ui.dasktoon_outline"))
```

Sửa `dasktoon_export_graph_test.py` (quanh dòng 301) và `dasktoon_export_layout_test.py` (quanh dòng 167): bỏ việc đặt
Light Bleed tay; giá trị mong đợi trong `.mat` là `outline.LIGHT_BLEED` / `outline.HAND_WOBBLE`.
Thêm `"scripts/startup/bl_ui/dasktoon_outline.py"`, `"scripts/startup/bl_ui/dasktoon_outline_gamedata.py"` vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (`LIGHT_BLEED` chưa có, operator chưa có, panel còn).

- [ ] **Step 3: Sửa `dasktoon_outline.py`**

1. Hằng số dưới `MASK_NAMES`:
```python
# Hand-drawn line weight, fixed (UI spec 4): thinner on the lit side, a slight pen wobble.
LIGHT_BLEED = 0.70
HAND_WOBBLE = 0.15
```
2. Hàm mới, gọi ở cuối `sync_material` (khi có companion) và trong `_slot_params` cho mọi nguồn:
```python
def _fix_line_weight(dask):
    _set_value(dask.inputs["Light Bleed"], LIGHT_BLEED)
    _set_value(dask.inputs["Hand Wobble"], HAND_WOBBLE)
```
   `_slot_params`: `slots.append(gn.SlotParams(True, float(width_socket.default_value), LIGHT_BLEED, HAND_WOBBLE, companion))`.
3. Xóa `DASKTOON_OT_outline_toggle_material` và `MATERIAL_PT_dasktoon_outline`; thêm:
```python
class DASKTOON_OT_outline_remove_legacy(Operator):
    """Turn off the DaskToon outline this material got before outlines moved onto the Anime BSDF and Dask Cel nodes"""
    bl_idname = "dasktoon.outline_remove_legacy"
    bl_label = "Remove DaskToon Outline"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mat = getattr(context, "material", None)
        return mat is not None and mat.library is None and bool(mat.get(OUTLINE_PROP))

    def execute(self, context):
        del context.material[OUTLINE_PROP]
        sync_all(context.scene)
        return {'FINISHED'}


def material_menu_func(self, context):
    """Material slot menu ⌄: only for a material outlined the old way (no Anime BSDF / Dask Cel node with outline)."""
    mat = getattr(context, "material", None)
    if mat is not None and mat.get(OUTLINE_PROP) and find_source(mat) == ('MATERIAL', None):
        self.layout.separator()
        self.layout.operator(DASKTOON_OT_outline_remove_legacy.bl_idname, icon='X')


classes = (DASKTOON_OT_outline_remove_legacy,)
```
4. `register()`/`unregister()` thêm `from .properties_material import MATERIAL_MT_context_menu` và
   `append`/`remove(material_menu_func)`.
5. Mọi chữ hiển thị còn lại sang tiếng Anh. `dasktoon_outline_gamedata.py`: nhãn lệnh "Prepare Outline for Games", thông
   báo `report` và thông báo trả về của `write_outline_uvs` sang tiếng Anh với `rpt_()` (thông báo này hiện trong báo cáo
   export). Bổ sung `VI` cho đến khi test bản dịch qua.

- [ ] **Step 4: Chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_outline_sync_test.py`, `dasktoon_outline_nodes_test.py`, `dasktoon_outline_gamedata_test.py`,
`dasktoon_export_graph_test.py`, `dasktoon_export_layout_test.py`, `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`.
Expected: tất cả OK.

- [ ] **Step 5: Sửa test Unity và ảnh duyệt (chạy ở Task 13)**

`dasktoon_unity_render_test.py`: hàm `outlined()` bỏ tham số `bleed`, `wobble` và hai dòng đặt chúng; hai ca outline dùng
mức cố định. `dasktoon_visual_review.py`: hàng outline chỉ còn một ô với mức cố định (bỏ đặt tay).

- [ ] **Step 6: Commit**
```bash
git add scripts/startup/bl_ui/ tests/python/
git commit -m "feat: fix Light Bleed and Hand Wobble, drop the Material outline panel, remove old outlines from the slot menu"
```

---

### Task 7: Face Shading chuyển sang Properties › Object Data

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_face_shading.py`
- Modify tests: `dasktoon_face_shading_test.py`, `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`

**Interfaces:**
- Produces: panel `DATA_PT_dasktoon_face_shading` (PROPERTIES / WINDOW / context `data`); `panel_target(context)` đọc
  `context.object` trước, rồi `context.active_object`.

- [ ] **Step 1: Viết test**

Trong `dasktoon_face_shading_test.py` (lớp `FaceShadingUITest`): mọi chỗ `bpy.types.DASKTOON_PT_face_shading` đổi thành
`bpy.types.DATA_PT_dasktoon_face_shading`; kiểm chỗ ở:
```python
        panel = bpy.types.DATA_PT_dasktoon_face_shading
        self.assertEqual((panel.bl_space_type, panel.bl_region_type, panel.bl_context), ('PROPERTIES', 'WINDOW', "data"))
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_face_shading"))
```
nhãn thanh trượt mong đợi `["Coverage", "Falloff", "Keep Nose Shadow", "Keep Chin Shadow"]`; nhãn khối trứng
`("label", "Proxy of Head")`. Thêm:
```python
    def test_panel_shows_only_for_meshes_and_face_proxies(self):
        head, _rig = tu.add_test_head()
        proxy = fs.setup(head)
        panel = bpy.types.DATA_PT_dasktoon_face_shading
        self.assertTrue(panel.poll(bpy.context))
        bpy.context.view_layer.objects.active = proxy
        self.assertTrue(panel.poll(bpy.context))
        other = bpy.data.objects.new("Plain", None)
        bpy.context.scene.collection.objects.link(other)
        bpy.context.view_layer.objects.active = other
        self.assertFalse(panel.poll(bpy.context))
```
Thêm `"DASKTOON_PT_face_shading"` vào `REMOVED`; thêm `"scripts/startup/bl_ui/dasktoon_face_shading.py"` vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (`DATA_PT_dasktoon_face_shading` chưa có).

- [ ] **Step 3: Chuyển panel và đổi chữ**

- Đổi class panel thành `DATA_PT_dasktoon_face_shading` với `bl_space_type = 'PROPERTIES'`, `bl_region_type = 'WINDOW'`,
  `bl_context = "data"`, `bl_label = "Face Shading"`, bỏ `bl_category`, `bl_order`; thêm
  `poll = classmethod(lambda cls, context: panel_target(context) is not None)`.
- `panel_target(context)`: `obj = getattr(context, "object", None) or context.active_object`.
- Chữ: lệnh "Set Up Face Shading", "Fit Proxy", "Remove Face Shading", "Select Proxy"; thanh trượt `SLIDERS =
  (("Coverage", "Coverage"), ("Falloff", "Falloff"), ("Nose Keep", "Keep Nose Shadow"), ("Chin Keep", "Keep Chin Shadow"))`;
  nhãn `iface_("Proxy of %s") % obj.name` (`translate=False`); "No proxy yet: press Fit Proxy"; gợi ý custom normal
  "This mesh still has old custom normals: the nose and chin shadows follow them instead of the real shape";
  mọi `FaceShadingError(...)` và thông báo `report` sang tiếng Anh với `rpt_()` khi hiển thị (`str(ex)` đã là chữ gốc tiếng
  Anh: dịch bằng `rpt_(str(ex))` không khớp với chữ có biến, nên lỗi có biến dùng `FaceShadingError(rpt_("... %s") % x)`).
- Bổ sung `VI` (vd. "Face Shading" → "Bóng mặt", "Set Up Face Shading" → "Tạo bóng mặt anime", "Keep Nose Shadow" → "Giữ
  bóng mũi", "Keep Chin Shadow" → "Giữ bóng cằm", "Proxy of %s" → "Khối trứng của %s", "Fit Proxy" → "Căn lại khối trứng",
  "Coverage" → "Độ phủ", "Falloff" → "Vùng chuyển", "Select Proxy" → "Chọn khối trứng", "Remove Face Shading" → "Gỡ bóng mặt").

- [ ] **Step 4: Chạy test, phải xanh**

Run: đồng bộ, rồi `dasktoon_face_shading_test.py`, `dasktoon_face_shading_nodes_test.py`, `dasktoon_face_shading_export_test.py`,
`dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`. Expected: OK.

- [ ] **Step 5: Commit**
```bash
git add scripts/startup/bl_ui/dasktoon_face_shading.py tests/python/
git commit -m "feat: move Face Shading to Properties › Object Data, for the mesh and its proxy"
```

---

### Task 8: Gộp material vào menu ⌄ của slot

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_material_combiner.py`
- Create: `tests/python/dasktoon_material_combiner_test.py`; Modify: `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `CMakeLists.txt`

**Interfaces:**
- Produces: `dasktoon_material_combiner.menu_func` gắn vào `MATERIAL_MT_context_menu`; lệnh "Combine Materials",
  "Restore Original Slots" (giữ `bl_idname`).

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_material_combiner_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Combine Materials and Restore Original Slots live in the material slot menu ⌄ (UI spec 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_material_combiner as combiner  # noqa: E402


class Recorder:
    def __init__(self):
        self.log = []

    def separator(self, **_kw):
        pass

    def operator(self, idname, **_kw):
        self.log.append(idname)


class Fake:
    def __init__(self):
        self.layout = Recorder()


class MaterialCombinerMenuTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj = tu.add_sphere(segments=8, rings=4)
        tu.assign(self.obj, tu.emission_material("A", (1, 0, 0, 1)))
        self.obj.data.materials.append(tu.emission_material("B", (0, 0, 1, 1)))

    def draw(self):
        fake = Fake()
        combiner.menu_func(fake, bpy.context)
        return fake.layout.log

    def test_menu_offers_combine_and_restores_only_when_there_is_something_to_restore(self):
        self.assertEqual(self.draw(), ["dasktoon.combine_materials"])
        self.obj["dasktoon_orig_materials"] = ["A", "B"]
        self.assertEqual(self.draw(), ["dasktoon.combine_materials", "dasktoon.restore_materials"])

    def test_menu_is_in_the_material_slot_menu_and_the_panel_is_gone(self):
        funcs = bpy.types.MATERIAL_MT_context_menu.draw._draw_funcs
        self.assertIn(combiner.menu_func.__name__, [f.__name__ for f in funcs if f.__module__ == combiner.__name__])
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_material_combiner"))


if __name__ == "__main__":
    tu.run_tests()
```
Thêm `"DASKTOON_PT_material_combiner"` vào `REMOVED`; thêm file vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (`menu_func` chưa có).

- [ ] **Step 3: Sửa module**

Xóa `DASKTOON_PT_material_combiner`; thêm:
```python
def menu_func(self, context):
    """Material slot menu ⌄ (Properties › Material)."""
    layout = self.layout
    layout.separator()
    layout.operator(DASKTOON_OT_combine_materials.bl_idname, icon='IMAGE_ZDEPTH')
    obj = context.object
    if obj is not None and "dasktoon_orig_materials" in obj:
        layout.operator(DASKTOON_OT_restore_materials.bl_idname, icon='LOOP_BACK')


classes = (DASKTOON_OT_combine_materials, DASKTOON_OT_restore_materials)


# bl_ui registers `classes`; register()/unregister() only manage the menu entry.
def register():
    from .properties_material import MATERIAL_MT_context_menu
    MATERIAL_MT_context_menu.append(menu_func)


def unregister():
    from .properties_material import MATERIAL_MT_context_menu
    MATERIAL_MT_context_menu.remove(menu_func)
```
Nhãn: `bl_label = "Combine Materials"`, `"Restore Original Slots"`; mô tả, `report` sang tiếng Anh không emoji, chữ có biến
dùng `rpt_()`. Bổ sung `VI`.

- [ ] **Step 4: Chạy test, phải xanh** — Expected: OK (cùng `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`).

- [ ] **Step 5: Đăng ký và commit**
```bash
git add scripts/startup/bl_ui/dasktoon_material_combiner.py tests/python/
git commit -m "feat: move Combine Materials and Restore Original Slots to the material slot menu"
```

---

### Task 9: Hiệu ứng anime vào Add › Anime Effect

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_anime_fx.py`
- Create: `tests/python/dasktoon_anime_fx_test.py`; Modify: `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `CMakeLists.txt`

**Interfaces:**
- Produces: menu `VIEW3D_MT_dasktoon_anime_effect` ("Anime Effect"), `EFFECTS = (("IMPACT", ((fx_type, icon), ...)),
  ("ATMOSPHERE", (...)))`, `menu_func` gắn vào `VIEW3D_MT_add`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_anime_fx_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime effects are added from Add › Anime Effect (UI spec 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_anime_fx as fx  # noqa: E402


class Props:
    pass


class Recorder:
    def __init__(self):
        self.log = []

    def separator(self, **_kw):
        pass

    def label(self, **_kw):
        pass

    def operator(self, idname, **_kw):
        props = Props()
        self.log.append((idname, props))
        return props

    def menu(self, idname, **_kw):
        self.log.append((idname, None))


class Fake:
    def __init__(self):
        self.layout = Recorder()


class AnimeEffectMenuTest(unittest.TestCase):
    def test_menu_lists_every_effect_once(self):
        fake = Fake()
        bpy.types.VIEW3D_MT_dasktoon_anime_effect.draw(fake, bpy.context)
        kinds = [props.fx_type for idname, props in fake.layout.log if idname == "dasktoon.add_anime_fx"]
        items = [item.identifier for item in
                 bpy.types.DASKTOON_OT_add_anime_fx.bl_rna.properties["fx_type"].enum_items]
        self.assertEqual(sorted(kinds), sorted(items))
        self.assertEqual(len(kinds), 11)

    def test_add_menu_has_the_submenu_and_the_panel_is_gone(self):
        funcs = bpy.types.VIEW3D_MT_add.draw._draw_funcs
        self.assertTrue([f for f in funcs if f.__module__ == fx.__name__])
        self.assertFalse(hasattr(bpy.types, "VIEW3D_PT_dasktoon_anime_fx"))

    def test_an_effect_can_be_added(self):
        tu.reset_scene()
        before = len(bpy.data.objects)
        self.assertEqual(bpy.ops.dasktoon.add_anime_fx(fx_type='SAKURA'), {'FINISHED'})
        self.assertGreater(len(bpy.data.objects), before)


if __name__ == "__main__":
    tu.run_tests()
```
Thêm `"VIEW3D_PT_dasktoon_anime_fx"` vào `REMOVED`; thêm file vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (`VIEW3D_MT_dasktoon_anime_effect` chưa có).

- [ ] **Step 3: Sửa module**

- Mục enum `fx_type` bỏ emoji, giữ id; tên tiếng Anh ngắn: Shockwave Ring, Hit Spark, Slash Arc, Debris Blast, Bubbles
  Rising, Bubbles Sinking, Sakura Petals, Magic Sparkles, Falling Leaves, Cel Rain, Fire Embers; mô tả là câu tiếng Anh.
- Xóa `VIEW3D_PT_dasktoon_anime_fx`; thêm:
```python
EFFECTS = (
    (n_("Impact"), (('IMPACT_SHOCKWAVE', 'SPHERE'), ('IMPACT_HIT_SPARK', 'LIGHT_SUN'),
                    ('IMPACT_SLASH_ARC', 'CURVE_DATA'), ('IMPACT_DEBRIS', 'MOD_EXPLODE'))),
    (n_("Atmosphere"), (('BUBBLES_UP', 'META_BALL'), ('BUBBLES_DOWN', 'MOD_FLUID'), ('SAKURA', 'COMMUNITY'),
                        ('LEAVES', 'FORCE_WIND'), ('SPARKLES', 'LIGHT_SUN'), ('EMBERS', 'FIRE'), ('RAIN', 'MOD_WAVE'))),
)


class VIEW3D_MT_dasktoon_anime_effect(Menu):
    bl_idname = "VIEW3D_MT_dasktoon_anime_effect"
    bl_label = "Anime Effect"

    def draw(self, _context):
        layout = self.layout
        names = {item.identifier: item.name
                 for item in DASKTOON_OT_add_anime_fx.bl_rna.properties["fx_type"].enum_items}
        for index, (group, effects) in enumerate(EFFECTS):
            if index:
                layout.separator()
            layout.label(text=group)
            for fx_type, icon in effects:
                layout.operator(DASKTOON_OT_add_anime_fx.bl_idname, text=names[fx_type], icon=icon).fx_type = fx_type


def menu_func(self, _context):
    self.layout.menu(VIEW3D_MT_dasktoon_anime_effect.bl_idname, icon='PARTICLES')


classes = (DASKTOON_OT_add_anime_fx, VIEW3D_MT_dasktoon_anime_effect)


# bl_ui registers `classes`; register() only adds the submenu to Add (space_view3d registers after this module).
def register():
    from .space_view3d import VIEW3D_MT_add
    VIEW3D_MT_add.append(menu_func)


def unregister():
    from .space_view3d import VIEW3D_MT_add
    VIEW3D_MT_add.remove(menu_func)
```
- Docstring, `report`, thuộc tính khác sang tiếng Anh; bổ sung `VI` (vd. "Anime Effect" → "Hiệu ứng anime",
  "Sakura Petals" → "Cánh hoa anh đào").

- [ ] **Step 4: Chạy test, phải xanh** — Expected: OK (cùng `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`).

- [ ] **Step 5: Đăng ký và commit**
```bash
git add scripts/startup/bl_ui/dasktoon_anime_fx.py tests/python/
git commit -m "feat: add anime effects from Add › Anime Effect instead of a sidebar panel"
```

---

### Task 10: Biểu cảm vào Properties › Object Data › Shape Keys

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_shape_key_manager.py`
- Create: `tests/python/dasktoon_expressions_test.py`; Modify: `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`, `CMakeLists.txt`

**Interfaces:**
- Produces: panel `DATA_PT_dasktoon_expression_sets`, `_tools`, `_preview`, `_controllers` (cha `DATA_PT_shape_keys`);
  `ARKIT_GROUPS = ((n_("Eyes"), 0, 14), (n_("Jaw & Mouth"), 14, 41), (n_("Brows"), 41, 46), (n_("Cheeks & Nose"), 46, 52))`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_expressions_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""VRM, ARKit and Shape Axis tools live under Properties › Object Data › Shape Keys (UI spec 3.2)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_shape_key_manager as skm  # noqa: E402

PANELS = ("DATA_PT_dasktoon_expression_sets", "DATA_PT_dasktoon_expression_tools",
          "DATA_PT_dasktoon_expression_preview", "DATA_PT_dasktoon_expression_controllers")


class Recorder:
    """Stands in for UILayout: every call returns a child recorder that shares the log."""

    def __init__(self, log=None):
        self.log = [] if log is None else log

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.log.append((name, args[0] if args else None, kwargs.get("text")))
            return Recorder(self.log)
        return call

    def __setattr__(self, name, value):
        if name == "log":
            object.__setattr__(self, name, value)


def draw(panel):
    recorder = Recorder()

    class Fake:
        layout = recorder

    panel.draw(Fake(), bpy.context)
    return recorder.log


class ExpressionPanelsTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj = tu.add_sphere(segments=8, rings=4)
        bpy.context.view_layer.objects.active = self.obj

    def test_panels_sit_under_shape_keys(self):
        for name in PANELS:
            panel = getattr(bpy.types, name)
            self.assertEqual((panel.bl_space_type, panel.bl_context, panel.bl_parent_id),
                             ('PROPERTIES', "data", "DATA_PT_shape_keys"), name)

    def test_sidebar_panels_and_duplicate_tools_are_gone(self):
        for name in ("DASKTOON_PT_shape_axis_panel", "DASKTOON_PT_vrm_toolset_panel", "DASKTOON_PT_arkit_studio_panel",
                     "DASKTOON_OT_vrm_zero_all_shapes", "DASKTOON_OT_vrm_mirror_shape_key"):
            self.assertFalse(hasattr(bpy.types, name), name)

    def test_tools_need_shape_keys(self):
        for name in PANELS[1:]:
            self.assertFalse(getattr(bpy.types, name).poll(bpy.context), name)
        self.assertTrue(bpy.types.DATA_PT_dasktoon_expression_sets.poll(bpy.context))
        self.obj.shape_key_add(name="Basis")
        for name in PANELS:
            self.assertTrue(getattr(bpy.types, name).poll(bpy.context), name)

    def test_every_panel_draws(self):
        self.obj.shape_key_add(name="Basis")
        for name in PANELS:
            self.assertTrue(draw(getattr(bpy.types, name)), name)
        operators = {entry[1] for entry in draw(bpy.types.DATA_PT_dasktoon_expression_preview) if entry[0] == "operator"}
        self.assertIn("object.shape_key_clear", operators)
        self.assertNotIn("dasktoon.vrm_zero_all_shapes", operators)

    def test_arkit_groups_cover_the_52_shapes(self):
        covered = [name for _label, start, end in skm.ARKIT_GROUPS for name in skm.ARKIT_52_ALL_NAMES[start:end]]
        self.assertEqual(covered, skm.ARKIT_52_ALL_NAMES)
        self.assertEqual(len(covered), 52)

    def test_placeholders_create_the_52_arkit_shapes(self):
        self.assertEqual(bpy.ops.dasktoon.arkit_init_placeholders(), {'FINISHED'})
        names = set(self.obj.data.shape_keys.key_blocks.keys())
        self.assertTrue(set(skm.ARKIT_52_ALL_NAMES) <= names)


if __name__ == "__main__":
    tu.run_tests()
```
Thêm 5 tên đã bỏ vào `REMOVED`; thêm file vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (panel mới chưa có).

- [ ] **Step 3: Thay 3 panel thanh bên bằng 4 panel con**

Xóa `DASKTOON_PT_shape_axis_panel`, `DASKTOON_PT_vrm_toolset_panel`, `DASKTOON_PT_arkit_studio_panel`,
`DASKTOON_OT_vrm_zero_all_shapes`, `DASKTOON_OT_vrm_mirror_shape_key` (và khỏi `classes`; tìm mọi chỗ gọi hai lệnh này
trước khi xóa). Thêm:

```python
ARKIT_GROUPS = ((n_("Eyes"), 0, 14), (n_("Jaw & Mouth"), 14, 41), (n_("Brows"), 41, 46), (n_("Cheeks & Nose"), 46, 52))


class DaskExpressionPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_parent_id = "DATA_PT_shape_keys"
    bl_options = {'DEFAULT_CLOSED'}
    needs_shape_keys = True

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            return False
        return obj.data.shape_keys is not None or not cls.needs_shape_keys


def _card(layout, title, region, text, translate_title=True):
    col = layout.box().column(align=True)
    col.label(text=iface_(title) if translate_title else title, icon='SOLO_ON', translate=False)
    col.label(text=iface_(region), icon='RESTRICT_SELECT_OFF', translate=False)
    col.separator()
    col.label(text=iface_(text), translate=False)


class DATA_PT_dasktoon_expression_sets(DaskExpressionPanel, Panel):
    bl_label = "Expression Sets"
    needs_shape_keys = False

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_init_standard", text="VRM 0.x Set", icon='ADD').standard_type = 'VRM_0'
        row.operator("dasktoon.vrm_init_standard", text="VRM 1.0 Set", icon='ADD').standard_type = 'VRM_1'
        col = layout.column(align=True)
        col.operator("dasktoon.vrm_synthesize_arkit52", icon='SOLO_ON')
        col.operator("dasktoon.arkit_init_placeholders", icon='ADD')
        col.operator("dasktoon.vrm_convert_naming", icon='SYNTAX_OFF')
        keys = context.object.data.shape_keys
        if keys is None:
            return
        present = sum(1 for name in ARKIT_52_ALL_NAMES if name in keys.key_blocks)
        box = layout.box()
        box.label(text=iface_("ARKit 52: %d / 52 shapes") % present, translate=False,
                  icon='CHECKMARK' if present == 52 else 'INFO')
        grid = box.grid_flow(columns=2, align=True)
        for label, start, end in ARKIT_GROUPS:
            count = sum(1 for name in ARKIT_52_ALL_NAMES[start:end] if name in keys.key_blocks)
            grid.label(text="%s: %d/%d" % (iface_(label), count, end - start), translate=False)


class DATA_PT_dasktoon_expression_tools(DaskExpressionPanel, Panel):
    bl_label = "Expression Tools"

    def draw(self, _context):
        col = self.layout.column(align=True)
        col.operator("dasktoon.vrm_split_shape_key", icon='ARROW_LEFTRIGHT')
        col.operator("dasktoon.vrm_bake_expression", icon='EXPERIMENTAL')
        col.operator("dasktoon.vrm_remove_empty_shapes", icon='TRASH')


class DATA_PT_dasktoon_expression_preview(DaskExpressionPanel, Panel):
    bl_label = "Expression Preview"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "dask_guide_card_key", text="VRM")
        card = VRM_GUIDE_CARDS.get(scene.dask_guide_card_key, VRM_GUIDE_CARDS['JOY'])
        _card(layout, card['name'], card['region'], card['desc'])
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_guide_solo_preview", text="Test on Model", icon='VIEWZOOM').card_key = \
            scene.dask_guide_card_key
        row.operator("object.shape_key_clear", text="Clear Values", icon='LOOP_BACK')
        layout.separator()
        layout.prop(scene, "dask_arkit_selected_shape", text="ARKit")
        name = scene.dask_arkit_selected_shape
        region, text = ARKIT_GUIDE_DB.get(name, (n_("Face"), n_("An ARKit facial movement.")))
        _card(layout, name, region, text, translate_title=False)
        row = layout.row(align=True)
        row.operator("dasktoon.arkit_solo_preview", text="Test on Model", icon='VIEWZOOM').shape_name = name
        row.operator("object.shape_key_clear", text="Clear Values", icon='LOOP_BACK')
        layout.separator()
        row = layout.row(align=True)
        row.operator("dasktoon.vrm_live_preview", text="Blink", icon='HIDE_OFF').preview_mode = 'AUTO_BLINK'
        row.operator("dasktoon.vrm_live_preview", text="Speech", icon='SPEAKER').preview_mode = 'AIUEO_TALK'
        row.operator("dasktoon.vrm_live_preview", text="Emotions", icon='SCENE').preview_mode = 'EMOTIONS'


class DATA_PT_dasktoon_expression_controllers(DaskExpressionPanel, Panel):
    bl_label = "Controllers"

    def draw(self, context):
        # Body of the former DASKTOON_PT_shape_axis_panel.draw, unchanged except: English text without emoji,
        # labels with numbers through iface_(...) % ... with translate=False.
        ...
```
`DATA_PT_dasktoon_expression_controllers.draw` là thân hàm `DASKTOON_PT_shape_axis_panel.draw` cũ (dòng 1148–1247) chép
nguyên văn, chỉ đổi chữ: "Open Viewport HUD" / "Close Viewport HUD", "Reset Group", "Reset All", "Insert Keyframe",
"Auto Setup", "Auto Detect VRM / VRoid", "VRM Emotions", "AIUEO Visemes", "Blink Sliders", "Ears & Tail",
"Controller Groups", `iface_("Fader Channels (%d sliders)") % len(grp.mappings)`, "Shape Key Mappings",
"Influence Radius", "Generate 3D Rig Board"; dòng 1132 (`X:… Y:…`) dùng `"X:%.2f Y:%.2f" % (...)` với `translate=False`.
- `VRM_GUIDE_CARDS` và `ARKIT_GUIDE_DB`: viết lại chữ gốc tiếng Anh bọc `n_()`, bỏ emoji; chữ tiếng Việt hiện có (bỏ emoji)
  thành bản dịch trong `VI`. Ví dụ `'eyeBlinkLeft': (n_("Left Eyelid"), n_("Closes the left upper eyelid fully onto the
  lower one."))` ↔ VI `"Left Eyelid": "Mí mắt trái"`.
- Enum `dask_guide_card_key` và các lệnh, mô tả, `report`, chữ trên HUD (`blf.draw`: dịch bằng `iface_` lúc vẽ) sang tiếng
  Anh không emoji. Lệnh đã bỏ: gọi `object.shape_key_clear` thay `dasktoon.vrm_zero_all_shapes` ở mọi nơi.

- [ ] **Step 4: Chạy test, phải xanh** — Expected: `dasktoon_expressions_test.py`, `dasktoon_ui_layout_test.py`,
  `dasktoon_translations_test.py` OK.

- [ ] **Step 5: Đăng ký và commit**
```bash
git add scripts/startup/bl_ui/dasktoon_shape_key_manager.py tests/python/
git commit -m "feat: move VRM, ARKit and Shape Axis tools under Properties › Object Data › Shape Keys"
```

---

### Task 11: Dự án chỉ còn trong menu File

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_project.py`, `scripts/modules/dasktoon_project/project.py` (thông báo lỗi)
- Modify tests: `dasktoon_project_ui_test.py`, `dasktoon_project_test.py`, `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py`

**Interfaces:**
- Produces: `TOPBAR_MT_dasktoon_project` ("DaskToon Project"), `TOPBAR_MT_dasktoon_project_recent` ("Open Recent"),
  `TOPBAR_MT_dasktoon_project_models` ("Models").

- [ ] **Step 1: Viết test**

Trong `dasktoon_project_ui_test.py`: test kiểm `VIEW3D_PT_dasktoon_project` đổi thành kiểm **không** còn panel đó và có
`TOPBAR_MT_dasktoon_project`, `TOPBAR_MT_dasktoon_project_recent`, `TOPBAR_MT_dasktoon_project_models`. Thêm:
```python
    def test_file_menu_holds_everything_the_project_panel_had(self):
        log = draw_menu(bpy.types.TOPBAR_MT_dasktoon_project)
        self.assertIn(("operator", "dasktoon.project_create"), log)
        self.assertIn(("operator", "dasktoon.project_open"), log)
        self.assertIn(("menu", "TOPBAR_MT_dasktoon_project_recent"), log)
        self.assertNotIn(("operator", "dasktoon.project_export"), log)
        self.assertEqual(self.create(), {'FINISHED'})
        log = draw_menu(bpy.types.TOPBAR_MT_dasktoon_project)
        for entry in (("menu", "TOPBAR_MT_dasktoon_project_models"), ("operator", "dasktoon.project_export"),
                      ("operator", "dasktoon.project_reinstall_shaders"), ("operator", "dasktoon.project_open_folder")):
            self.assertIn(entry, log)
```
với helper `draw_menu(menu)` dùng một `Recorder` ghi `("operator", idname)`, `("menu", idname)`, `("label", text)`.
Thêm `"VIEW3D_PT_dasktoon_project"` vào `REMOVED`; thêm `bl_ui/dasktoon_project.py` và
`scripts/modules/dasktoon_project/project.py` vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL (menu con chưa có, panel còn).

- [ ] **Step 3: Sửa module**

Xóa `VIEW3D_PT_dasktoon_project`. Thêm hai menu con và vẽ lại menu chính:
```python
class TOPBAR_MT_dasktoon_project_recent(Menu):
    bl_label = "Open Recent"

    def draw(self, _context):
        layout = self.layout
        recent = dtp.recent_projects()
        if not recent:
            layout.label(text="No recent projects")
        for path in recent:
            op = layout.operator(DASKTOON_OT_project_open.bl_idname, text=os.path.basename(os.path.dirname(path)),
                                 icon='FILE_FOLDER', translate=False)
            op.filepath = path


class TOPBAR_MT_dasktoon_project_models(Menu):
    bl_label = "Models"

    def draw(self, _context):
        layout = self.layout
        project = active_project()
        if project is None:
            return
        current = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
        for path in _models(project):
            icon = 'RADIOBUT_ON' if os.path.normcase(path) == current else 'BLENDER'
            op = layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=os.path.relpath(path, project.folder),
                                 icon=icon, translate=False)
            op.filepath = path


class TOPBAR_MT_dasktoon_project(Menu):
    bl_label = "DaskToon Project"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        layout.operator(DASKTOON_OT_project_create.bl_idname, text="New Project…", icon='NEWFOLDER')
        layout.operator(DASKTOON_OT_project_open.bl_idname, text="Open Project…", icon='FILE_FOLDER')
        layout.menu(TOPBAR_MT_dasktoon_project_recent.bl_idname, icon='RECOVER_LAST')
        project = active_project()
        if project is None:
            return
        layout.separator()
        layout.label(text=project.name, icon='FILE_FOLDER', translate=False)
        engines = {key: label for key, label, _desc in targets.ENGINES}
        layout.label(text="%s: %s" % (iface_("Engine"), iface_(engines.get(project.engine, project.engine))),
                     translate=False)
        version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
        layout.label(text=(iface_("Shaders: version %d") % version) if version else iface_("Shaders: not installed"),
                     icon='CHECKMARK' if version else 'ERROR', translate=False)
        layout.menu(TOPBAR_MT_dasktoon_project_models.bl_idname, icon='BLENDER')
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        layout.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        layout.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')
```
`classes`: bỏ panel, thêm 2 menu con (trước menu chính). Mọi nhãn lệnh ("Create DaskToon Project", "Open DaskToon Project",
"Open", "Export This Model", "Reinstall Shaders", "Open Project Folder"…), mô tả, `report` và lỗi của
`dasktoon_project/project.py` sang tiếng Anh với `rpt_()`. Bổ sung `VI`.

- [ ] **Step 4: Chạy test, phải xanh** — Expected: `dasktoon_project_ui_test.py`, `dasktoon_project_test.py`,
  `dasktoon_engine_export_ui_test.py`, `dasktoon_ui_layout_test.py`, `dasktoon_translations_test.py` OK.

- [ ] **Step 5: Commit**
```bash
git add scripts/ tests/python/
git commit -m "feat: keep DaskToon projects in File › DaskToon Project only"
```

---

### Task 12: Chữ còn lại, node C++ và hai kiểm tra tổng

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_shading_styles.py`, `dasktoon_upgrade.py`, `dasktoon_face_shading_nodes.py`
  (nếu có chữ), `node_add_menu_shader.py` (chỉ phần DaskToon: nhãn đã là tiếng Anh, chỉ cần `VI`),
  `scripts/modules/dasktoon_export/*.py` (báo cáo, cảnh báo, lý do bỏ qua, README), `scripts/startup/dasktoon_init.py`
- Modify tests: `dasktoon_shading_styles_test.py`, `dasktoon_export_*_test.py`, `dasktoon_face_shading_export_test.py`,
  `dasktoon_unity_render_test.py` (tên style), `dasktoon_translations_test.py`, `dasktoon_ui_layout_test.py`

**Interfaces:**
- Produces: `dasktoon_shading_styles.BUILTIN_STYLES` với tên tiếng Anh và `LEGACY_NAMES = {"Anime 3 tông": ...}` để tra tên
  cũ; thông báo của thư viện export là chữ gốc tiếng Anh dịch bằng `rpt_()` lúc tạo.

- [ ] **Step 1: Viết test tổng**

Thêm vào `dasktoon_translations_test.py`:
```python
def dasktoon_files():
    """Every DaskToon Python file that can show text."""
    import glob
    found = set()
    for pattern in ("scripts/startup/bl_ui/dasktoon_*.py", "scripts/startup/bl_ui/engine_dasktoon_anime.py",
                    "scripts/startup/dasktoon_*.py", "scripts/modules/dasktoon_export/*.py",
                    "scripts/modules/dasktoon_project/*.py"):
        found.update(os.path.relpath(p, REPO).replace(os.sep, "/") for p in glob.glob(path(pattern)))
    found.discard("scripts/startup/bl_ui/dasktoon_translations.py")
    return found


def dasktoon_node_types():
    """bl_idname of the C++ nodes in the Shader Editor's DaskToon Anime menus."""
    import ast
    with open(path("scripts/startup/bl_ui/node_add_menu_shader.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    found = set()
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef) and "anime" in n.name.lower()]:
        for call in [n for n in ast.walk(cls) if isinstance(n, ast.Call)]:
            for arg in call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("ShaderNode"):
                    found.add(arg.value)
    return found


    # in class TranslationTest:
    def test_every_dasktoon_file_is_checked(self):
        self.assertEqual(dasktoon_files() - set(TRANSLATED), set())

    def test_dasktoon_nodes_are_translated(self):
        mat = bpy.data.materials.new("DT_NodeStrings")
        strings = set()
        for idname in sorted(dasktoon_node_types()):
            node = mat.node_tree.nodes.new(idname)
            strings.add(node.bl_rna.name)
            strings.update(s.name for s in list(node.inputs) + list(node.outputs))
            for prop in node.bl_rna.properties:
                if prop.identifier in bpy.types.ShaderNode.bl_rna.properties:
                    continue
                strings.update((prop.name, prop.description))
                if prop.type == 'ENUM':
                    for item in prop.enum_items:
                        strings.update((item.name, item.description))
        bpy.data.materials.remove(mat)
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])
```
Thêm vào `dasktoon_ui_layout_test.py`:
```python
class NoSidebarTest(unittest.TestCase):
    def test_no_dasktoon_panel_in_any_sidebar_or_in_render_and_light(self):
        bad = []
        for cls in subclasses(bpy.types.Panel):
            if not getattr(cls, "is_registered", False):
                continue
            module = getattr(cls, "__module__", "")
            dasktoon = "dasktoon" in module or "DASKTOON" in cls.__name__.upper()
            if not dasktoon:
                continue
            if cls.bl_region_type == 'UI' or getattr(cls, "bl_category", "") in {"DaskToon", "ARKit", "Shape Axis"}:
                bad.append(cls.__name__)
            if cls.bl_space_type == 'PROPERTIES' and getattr(cls, "bl_context", "") in {"render", "data"} and \
                    getattr(cls, "bl_parent_id", "").startswith("DATA_PT_EEVEE_light"):
                bad.append(cls.__name__)
            if cls.bl_space_type == 'PROPERTIES' and getattr(cls, "bl_context", "") == "render":
                bad.append(cls.__name__)
        self.assertEqual(bad, [])
```
Thêm mọi file còn thiếu vào `TRANSLATED`.

- [ ] **Step 2: Chạy, phải đỏ** — Expected: FAIL — các file chưa dịch, node C++ chưa có bản dịch.

- [ ] **Step 3: Chuyển chữ còn lại**

- `dasktoon_shading_styles.py`: tên built-in style tiếng Anh ("Simple", "Anime 2-Tone", "Anime 3-Tone", "Soft Painted",
  "Manga"… theo bảng hiện có), giữ `LEGACY_NAMES` để `get_style` tra được tên tiếng Việt cũ; menu "Shading Style",
  "Delete Style", "Save My Style", "Convert from Simple"; `report` với `rpt_()`. Kiểm style người dùng đã lưu (file JSON)
  vẫn đọc được. Sửa test style và tên style trong `dasktoon_unity_render_test.py`.
- Thư viện `dasktoon_export` (`report.py`, `__init__.py`, `model_fbx.py`, `face_shading.py`, `graph.py`, `bake.py`,
  `targets.py`, `assets.py`, `shaders_install.py`): mọi thông báo, dòng báo cáo, lý do bỏ qua và README thành chữ gốc tiếng
  Anh; dịch mẫu bằng `rpt_()` ngay lúc tạo (báo cáo, README theo ngôn ngữ đang dùng). Sửa các test đang so chữ tiếng Việt
  (vd. "slot trống" → "empty slot", "thứ tự UV" → "UV order", "Bóng mặt" → "Face shading", "Đèn gợi ý" → "Suggested light").
- `dasktoon_upgrade.py`, `dasktoon_init.py`, `dasktoon_face_shading_nodes.py`: chữ hiển thị (nếu có) sang tiếng Anh.
- Bổ sung `VI` cho mọi chữ còn thiếu, kể cả tên node, ô, thuộc tính, mục enum của node DaskToon C++ (danh sách lấy từ
  `test_dasktoon_nodes_are_translated`). Tên shape key ARKit/VRM và tên riêng đưa vào `KEEP`.

- [ ] **Step 4: Chạy test, phải xanh** — Expected: `dasktoon_translations_test.py`, `dasktoon_ui_layout_test.py` và các test
  đã sửa đều OK.

- [ ] **Step 5: Commit**
```bash
git add scripts/ tests/python/
git commit -m "feat: translate the rest of DaskToon and its nodes; check that no DaskToon panel is left in a sidebar"
```

---

### Task 13: Kiểm chứng toàn bộ, Unity, báo cáo

**Files:**
- Create: `docs/superpowers/reports/2026-10-04-dasktoon-ui-reorganization-report.md`

- [ ] **Step 1: Toàn bộ test DaskToon** — đồng bộ bằng script, chạy mọi file trong danh sách CMake. Expected: tất cả OK.
- [ ] **Step 2: Unity** — `dasktoon_unity_render_test.py` và `dasktoon_unity_model_test.py`. Expected: OK; ghi số liệu hai ca
  outline với mức Light Bleed/Hand Wobble cố định.
- [ ] **Step 3: Ảnh duyệt** — chạy `dasktoon_visual_review.py` (đã sửa ở Task 6), mở ảnh kiểm hàng outline.
- [ ] **Step 4: Báo cáo** (tiếng Việt, cho người dùng): tóm tắt; bảng "tìm ở đâu" (tính năng → chỗ mới); những gì đã bỏ và
  vì sao; số test; các quyết định tự đưa ra (từ ledger, kèm cái giá); nhỏ để lại; việc cần làm (đồng bộ bằng script mới,
  bật Tiếng Việt để xem bản dịch, chọn merge/PR/giữ nhánh).
- [ ] **Step 5: Commit**
```bash
git add docs/superpowers/reports/2026-10-04-dasktoon-ui-reorganization-report.md
git commit -m "docs: add the interface reorganization report"
```
