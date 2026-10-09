# DaskToon: sửa các lỗi nhỏ và cảnh báo scale — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** (2026-10-10); Claude chạy **inline** trên nhánh `dasktoon-minor-fixes` (từ
> `dasktoon-spring-constraint`, `f328c25ca55`). Không push, không merge.

**Goal:** Sửa hết các lỗi nhỏ người dùng duyệt sửa (spec rig §16 mục 4 và 6) mà constraint Spring chưa sửa: ba lỗi của rig
trong DaskToon và cảnh báo scale (§12), hai lỗi của lắc trong Unity, ba lỗi của Phần 2 (dự án). Hai lỗi còn lại của rig (dời
rig thì giật, collider không theo scale) đã hết nhờ constraint Spring.

**Architecture:** Thay đổi nhỏ, đúng chỗ: `skeleton.editing()` trả lại mode cũ; danh sách phần bớt tên lặp; Build thêm
`mesh_warnings()`; script Unity bỏ qua bước `dt <= 0` và trình import thêm `OnPostprocessAllAssets`; module dự án đọc lại
`dasktoon_project.json` chỉ khi file đổi; hai lệnh lưu của model báo lý do trên bản nháp.

**Tech Stack:** Python `bpy`, numpy, C# (Unity 6000.5), harness Unity của test.

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` §12, §16; danh sách lỗi nhỏ trong các báo cáo
`docs/superpowers/reports/2026-10-06-dasktoon-anime-rig-r1-report.md` (§5, §7) và
`docs/superpowers/reports/2026-10-05-dasktoon-project-workflow-report.md`.

## Global Constraints

- Không push, không merge; test và công cụ dùng thư mục tạm, `DASKTOON_CONFIG_DIR` trỏ thư mục tạm; không ghi vào project
  Unity trong `D:\Unity\` (test Unity chỉ dùng project tạm của harness).
- Chữ mới có bản Việt trong `dasktoon_translations.py`; quy tắc quét bản dịch (không f-string, không nối chuỗi trong
  `rpt_`/`text=`); bản Việt giữ đường dẫn menu tiếng Anh như các mục đã có.
- Script C# đổi thì `SCRIPTS_VERSION` tăng, để bản đã cài trong project Unity được thay.

## Review Focus

1. **Mode**: Fit to Parts bấm trong Edit Mode thì vẫn ở Edit Mode; Build vẫn trả lại mode cũ như trước. Test Task 1.
2. **Cảnh báo không báo nhầm**: nhân vật thử (tách và gộp) không có cảnh báo pháp tuyến hay scale; Body lật pháp tuyến thì có.
   Test Task 1.
3. **Bộ nhớ đệm file dự án**: đổi tên trong DaskToon hay file bị sửa bên ngoài đều hiện ngay; file hỏng vẫn bị bỏ qua như cũ.
   Test Task 3.
4. **Unity**: bước khi tạm dừng không làm tóc trôi; file rig thêm sau model làm model import lại; model và file rig đến cùng
   lúc thì không import hai lần. Test Task 2.

---

### Task 1: Rig trong DaskToon — Fit to Parts giữ mode, danh sách phần, cảnh báo pháp tuyến và scale

**Files:**
- Modify: `scripts/modules/dasktoon_rig/skeleton.py` (`editing()` trả lại mode của object đang active trước đó)
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (`DASKTOON_UL_rig_parts.draw_item`: tên object chỉ hiện khi khác tên phần)
- Modify: `scripts/modules/dasktoon_rig/build.py` (`mesh_warnings(parts, owners)`; `build()` thêm vào `result.warnings`)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py` (2 thông báo)
- Test: `tests/python/dasktoon_rig_ui_test.py`, `tests/python/dasktoon_rig_build_test.py`

**Interfaces:**
- Produces: `build.mesh_warnings(parts, owners) -> [str]`; `build.INWARD_RATIO = -0.5`.

- [ ] **Step 1: Test** — trong `dasktoon_rig_ui_test.py` (`PanelTest`):
```python
    def test_fit_in_edit_mode_stays_in_edit_mode(self):
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.rig_fit(), {'FINISHED'})
        self.assertEqual(self.rig.mode, 'EDIT')
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)

    def test_parts_list_names_the_object_only_when_it_differs(self):
        ui.add_part(self.rig, self.objs["Body"], 'BODY')
        ui.add_part(self.rig, self.objs["Body"], 'CLOTHING', name="Skin")
        found = []
        for part in self.rig.data.dasktoon_rig.parts:
            log = tu.RecordingLayout()
            ui.DASKTOON_UL_rig_parts.draw_item(None, bpy.context, log, None, part, 0, None, "", 0)
            found.append(tu.labels(log))
        self.assertEqual(found, [[], ["Body"]])
```
  Trong `dasktoon_rig_build_test.py` (lớp mới `MeshWarningTest`, dùng `separate_parts`, `fx`):
```python
def flip(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def mesh_warnings(result):
    return [w for w in result.warnings if "inward" in w or "scale" in w]


class MeshWarningTest(unittest.TestCase):
    def test_the_test_character_has_none(self):
        for merged in (False, True):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            objs = fx.character(merged=merged)
            parts = separate_parts(objs) if not merged else merged_parts(objs["Character"])
            self.assertEqual(mesh_warnings(build.build(bpy.context, fx.rig_for(), parts)), [], merged)

    def test_inward_body_normals(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        flip(objs["Body"])
        found = mesh_warnings(build.build(bpy.context, fx.rig_for(), separate_parts(objs)))
        self.assertEqual(len(found), 1)
        self.assertIn("Body", found[0])
        self.assertIn("inward", found[0])

    def test_negative_or_uneven_scale(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        objs["Skirt"].scale = (1.0, 1.0, 1.2)
        objs["Ribbon"].scale = (-1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        found = mesh_warnings(build.build(bpy.context, fx.rig_for(), separate_parts(objs)))
        self.assertEqual(sorted(w.split(" ")[0] for w in found), ["Ribbon", "Skirt"])
```
  (`merged_parts` là cách test hiện có dựng phần theo material cho nhân vật gộp; nếu chưa có hàm chung thì tách ra từ
  `MergedTest`.)

- [ ] **Step 2: Chạy, thấy FAIL** — `rig.mode` là `'OBJECT'`; nhãn `["Body"]` ở phần đầu; không có cảnh báo.

- [ ] **Step 3: Code**
  - `skeleton.editing()`:
```python
    view_layer = context.view_layer
    previous = view_layer.objects.active
    previous_mode = previous.mode if previous is not None else 'OBJECT'
    if previous_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        yield rig.data.edit_bones
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous
        if previous_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=previous_mode)
```
    Docstring: "afterwards the previous active object, in its mode".
  - `draw_item`: `if item.object is not None and item.object.name != item.name: row.label(text=item.object.name, translate=False)`.
  - `build.py`:
```python
INWARD_RATIO = -0.5  # signed / unsigned volume of a Body below this: its faces point inward (about -1)


def _signed_volume_ratio(obj, vertices):
    """Signed over unsigned volume of the triangles of `obj` whose corners are all in `vertices`, in world space around
    their centre: about 1 for a surface facing out (closed or not), about -1 facing in, near 0 for a flat card."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    tris = np.empty(len(mesh.loop_triangles) * 3, np.int64)
    mesh.loop_triangles.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3)
    inside = np.zeros(len(mesh.vertices), bool)
    inside[vertices] = True
    tris = tris[inside[tris].all(axis=1)]
    world, _edges = rig_parts.mesh_arrays(obj)
    world = world - world[vertices].mean(axis=0)
    a, b, c = world[tris[:, 0]], world[tris[:, 1]], world[tris[:, 2]]
    volumes = np.einsum("ij,ij->i", a, np.cross(b, c))
    total = np.abs(volumes).sum()
    return float(volumes.sum() / total) if total > 1e-12 else 0.0


def mesh_warnings(parts, owners):
    """Warnings about the meshes of the parts (spec 12): a negative or non-uniform scale (apply it before exporting to
    Unity); Body faces that point inward, which give automatic weights the wrong bones (not checked under a negative
    scale, whose warning says what to do)."""
    out = []
    body_ids = [i for i, part in enumerate(parts) if part.role == 'BODY']
    for obj, owner in owners.items():
        scale = obj.matrix_world.to_scale()
        negative = obj.matrix_world.is_negative
        if negative or max(scale) > min(scale) * (1.0 + 1e-4):
            out.append(rpt_("%s has a negative or non-uniform scale: apply its scale (Object › Apply › Scale) before "
                            "building and exporting to Unity") % obj.name)
        vertices = np.nonzero(np.isin(owner, body_ids))[0]
        if not negative and len(vertices) and _signed_volume_ratio(obj, vertices) < INWARD_RATIO:
            out.append(rpt_("%s: the faces of the body point inward, so automatic weights may pick the wrong bones. "
                            "Recalculate the normals outside (Edit Mode, Mesh › Normals)") % obj.name)
    return out
```
    `build()`: ngay sau `owners = ownership(parts)`: `result.warnings.extend(mesh_warnings(parts, owners))`.
  - Bản Việt: "%s có scale âm hoặc không đều: hãy Apply Scale (Object › Apply › Scale) trước khi dựng rig và xuất sang
    Unity"; "%s: mặt của phần thân quay vào trong nên weight tự động có thể chọn sai xương. Hãy tính lại pháp tuyến hướng ra
    ngoài (Edit Mode, Mesh › Normals)".

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_rig_ui_test dasktoon_rig_build_test dasktoon_rig_skeleton_test dasktoon_translations_test`.
- [ ] **Step 5: Commit** — `fix: Fit to Parts keeps the mode, the parts list stops repeating names, Build warns about scale and inward faces`.

---

### Task 2: Lắc trong Unity — tạm dừng không trôi, file rig thêm sau thì model import lại

**Files:**
- Modify: `scripts/modules/dasktoon_export/unity_scripts/DaskToonSpringBone.cs` (`Step`: `dt <= 0` thì không làm gì)
- Modify: `scripts/modules/dasktoon_export/unity_scripts/Editor/DaskToonRigImporter.cs` (`OnPostprocessAllAssets`)
- Modify: `scripts/modules/dasktoon_export/scripts_install.py` (`SCRIPTS_VERSION = 2`)
- Test: `tests/unity/Editor/DaskToonRigTests.cs` (`CheckRig` đo `pausedDrift`; `CheckLateRig` mới),
  `tests/python/dasktoon_unity_rig_test.py`, `tests/python/dasktoon_export_rig_test.py`

- [ ] **Step 1: Test**
  - `dasktoon_export_rig_test.py`: bản cài có `"if (dt <= 0f) return;"` và `OnPostprocessAllAssets`; test mới
    `test_older_scripts_are_replaced` (ghi phiên bản `SCRIPTS_VERSION - 1` vào file phiên bản, cài lại → `True`, phiên bản
    thành `SCRIPTS_VERSION`), và `si.SCRIPTS_VERSION == 2`.
  - `DaskToonRigTests.CheckRig`: sau 20 bước, ghi lại đuôi, gọi `Step(0f)`, `result["pausedDrift"]` = độ dời lớn nhất.
  - `DaskToonRigTests.CheckLateRig` (tham số `model`): đọc nội dung file rig, `AssetDatabase.DeleteAsset(rig)`,
    `AssetDatabase.ImportAsset(model, ImportAssetOptions.ForceUpdate)` → `result["withoutRig"]` = số spring bone trên
    prefab; ghi lại file rig, `AssetDatabase.ImportAsset(rig)` → `result["withRig"]`.
  - `dasktoon_unity_rig_test.py`: `pausedDrift < 1e-9`; sau `CheckRig` chạy `CheckLateRig`: `withoutRig == 0`,
    `withRig == 9`.

- [ ] **Step 2: Chạy, thấy FAIL** — chuỗi trong bản cài chưa có; `pausedDrift` > 0; `withRig == 0`.

- [ ] **Step 3: Code**
  - `Step`: dòng đầu `if (dt <= 0f) return;  // paused (Time.timeScale 0): the hair stays where it is`.
  - Trình import:
```csharp
        /// <summary>A rig file that arrives after its model (exported later, copied in) imports the model again, so
        /// the model gets its spring bones; a model imported in the same pass reads the file itself.</summary>
        static void OnPostprocessAllAssets(string[] importedAssets, string[] deletedAssets, string[] movedAssets,
                                           string[] movedFromAssetPaths)
        {
            var imported = new HashSet<string>(importedAssets);
            foreach (var path in importedAssets)
            {
                if (!path.EndsWith(".rig.json", StringComparison.OrdinalIgnoreCase)) continue;
                var model = path.Substring(0, path.Length - ".rig.json".Length) + ".fbx";
                if (File.Exists(model) && !imported.Contains(model)) AssetDatabase.ImportAsset(model);
            }
        }
```
  - `SCRIPTS_VERSION = 2`.

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_export_rig_test`; `rt.sh dasktoon_unity_rig_test` (Unity thật).
- [ ] **Step 5: Commit** — `fix: Unity spring bones stand still while paused, and a rig file added later reimports its model`.

---

### Task 3: Phần 2 — tên dự án gần đây, đọc file dự án khi đổi, lệnh lưu trên bản nháp báo lý do

**Files:**
- Modify: `scripts/modules/dasktoon_project/project.py` (`load` nhớ theo `(mtime_ns, size)`; `save` bỏ bản nhớ;
  `project_label(path)`)
- Modify: `scripts/startup/bl_ui/dasktoon_splash.py`, `scripts/startup/bl_ui/dasktoon_project.py` (danh sách gần đây dùng
  `project_label`)
- Modify: `scripts/startup/bl_ui/dasktoon_model.py` (Save Copy, Save Incremental: `poll` luôn đúng, `invoke`/`execute`
  báo lỗi trên bản nháp; menu File vẫn làm mờ như cũ)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py` (1 thông báo)
- Test: `tests/python/dasktoon_project_test.py`, `tests/python/dasktoon_project_ui_test.py`, `tests/python/dasktoon_model_test.py`

**Interfaces:**
- Produces: `dtp.project_label(path) -> str`; `dtp.load()` trả bản sao (sửa không ảnh hưởng bản nhớ).

- [ ] **Step 1: Test**
  - `dasktoon_project_test.py`: `test_load_reads_the_file_again_only_when_it_changed` (đếm `json.load`: hai lần `load` liền
    nhau chỉ đọc một lần; `save` với tên mới → `load` ra tên mới ngay; ghi file bên ngoài với tên dài khác → `load` ra tên
    đó); `test_loaded_projects_are_copies` (thêm engine vào bản trả về, `load` lại vẫn rỗng); `test_project_label`
    (tên lưu trong file; file hỏng → tên thư mục).
  - `dasktoon_project_ui_test.py`: `test_recent_lists_show_the_project_name` (dự án thư mục "Folder" đổi tên "Renamed":
    Open Recent và màn hình đầu hiện "Renamed").
  - `dasktoon_model_test.py`: thay `test_copy_and_incremental_need_a_model_of_a_project` bằng
    `test_copy_and_incremental_on_a_draft_say_why` (`poll()` đúng; gọi thì `RuntimeError` có chữ "draft").

- [ ] **Step 2: Chạy, thấy FAIL**.

- [ ] **Step 3: Code**
```python
_loaded = {}  # normcase(abspath(project file)) -> (mtime_ns, size, Project)


def _copy(project):
    return Project(project.folder, project.name, [dict(engine) for engine in project.engines])


def load(path):
    """The project of a dasktoon_project.json file (or of the folder holding it). The file is read again only when it
    changed: the top bar and the menus ask on every redraw."""
    if os.path.isdir(path):
        path = os.path.join(path, PROJECT_FILE)
    key = os.path.normcase(os.path.abspath(path))
    stat = os.stat(path)
    cached = _loaded.get(key)
    if cached is None or cached[:2] != (stat.st_mtime_ns, stat.st_size):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != PROJECT_VERSION:
            raise ValueError(rpt_("%s: project version %r is not supported") % (path, data.get("version")))
        cached = (stat.st_mtime_ns, stat.st_size,
                  Project(os.path.dirname(os.path.abspath(path)), data.get("name", ""), list(data.get("engines", []))))
        _loaded[key] = cached
    return _copy(cached[2])


def project_label(path):
    """What the recent lists show for the project file `path`: its name, or its folder's name when it cannot be read."""
    folder = os.path.basename(os.path.dirname(path))
    try:
        return load(path).name or folder
    except (OSError, ValueError):
        return folder
```
  `save()` thêm cuối: `_loaded.pop(os.path.normcase(os.path.abspath(project.file)), None)`.
  Màn hình đầu và Open Recent: `text=dtp.project_label(path)`.
  `dasktoon_model.py`, hai lệnh:
```python
DRAFT = "This file is a draft: save it into a project first"

    @classmethod
    def poll(cls, _context):
        return True  # on a draft it runs and says why it cannot (a shortcut must not stay silent)

    def invoke(self, context, _event):
        if projects.open_project() is None:
            self.report({'ERROR'}, rpt_(DRAFT))
            return {'CANCELLED'}
        ...
```
  (`execute` kiểm tra như vậy; chuỗi viết thẳng trong `rpt_(...)` ở mỗi chỗ nếu bộ quét bản dịch không nhận hằng.)
  Bản Việt: "File này là bản nháp: hãy lưu nó vào một dự án trước".

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_project_test dasktoon_project_ui_test dasktoon_model_test dasktoon_file_ui_test dasktoon_file_redirect_test dasktoon_translations_test`.
- [ ] **Step 5: Commit** — `fix: recent projects show their names, the project file is read only when it changes, draft saves say why`.

---

### Task 4: Kiểm tra, ảnh, báo cáo

- [ ] Toàn bộ suite CMake; test Unity rig.
- [ ] Ảnh: chạy lại `tools/dasktoon_rig_screenshots.py` (en, vi): `24_rig_panel` không còn tên lặp.
- [ ] Báo cáo `docs/superpowers/reports/2026-10-10-dasktoon-minor-fixes-report.md`: lỗi nào, sửa thế nào, test nào; quyết
  định khi làm; review.
