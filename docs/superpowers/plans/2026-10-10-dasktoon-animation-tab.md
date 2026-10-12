# DaskToon: tab Animation gọn (A) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** (2026-10-10); Claude chạy **inline** trên nhánh `dasktoon-animation-tab` (từ
> `dasktoon-minor-fixes`, `8983b341a40`). Không push, không merge.

**Goal:** Tab Animation mới cho nhân vật anime: bố cục gọn (camera, viewport, Properties, một timeline), timeline hiện cả
nhân vật khi chọn bất kỳ phần nào, Key Pose và phím I key cả xương lẫn mặt; file cũ mở ra cũng có tab mới.

**Architecture:** Cờ lọc C++ `ADS_FILTER_WHOLE_CHARACTER` trong bộ lọc kênh animation; keying set Python "DaskToon
Character" dùng định nghĩa nhân vật trong module `dasktoon_animation`; workspace mẫu `.blend` dựng bằng script, thay tab
"Animation" khi mở file qua hàm C++ `bpy.data.workspaces.replace(old, new)`.

**Tech Stack:** C++ (Blender 5.2: DNA, editors/animation, RNA), Python `bpy`, MSBuild/VS 2022.

**Spec:** `docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md`.

## Global Constraints

- Ngoài tab Animation và những gì người dùng bật, Blender như cũ: cờ Whole Character tắt sẵn ở mọi editor khác; keying set
  chỉ đặt cho scene chưa có keying set.
- Mở file không làm file "đã sửa".
- Chữ mới có bản Việt; quy tắc quét bản dịch; không panel ở thanh bên.
- Không push, không merge; test dùng thư mục tạm và `DASKTOON_CONFIG_DIR` tạm.
- Build: `MSYS_NO_PATHCONV=1 "$MSBUILD" "D:/build_windows_x64_vc17_Release/INSTALL.vcxproj" -p:Configuration=Release -m -v:m -nologo`
  rồi `"$PY" tools/dasktoon_sync_build.py "$INSTALL"`.

## Review Focus

1. **Bộ lọc**: chọn mesh mặt thì thấy mọi xương (kể cả xương không chọn) và shape key của nhân vật; object rời chỉ khi
   chọn; cờ tắt thì như Blender. Test Task 1.
2. **Keying**: Key Pose key đủ xương, shape key (trừ Basis), controller; object rời key vị trí/xoay/scale. Test Task 2.
3. **Thay workspace**: tên, vị trí tab, cửa sổ đang mở tab cũ chuyển sang tab mới, file không "đã sửa". Test Task 3, 4.
4. **Mở file**: tab cũ bị thay một lần; tab đúng phiên bản giữ nguyên; tab bị xóa không thêm lại. Test Task 4.

---

### Task 1: Cờ lọc "Whole Character" (C++), công tắc trong header Dope Sheet

**Files:**
- Modify: `source/blender/makesdna/DNA_action_types.h` (`ADS_FILTER_WHOLE_CHARACTER = (1 << 8)` trong
  `eDopeSheet_FilterFlag2`)
- Modify: `source/blender/editors/include/ED_anim_api.hh` (`bAnimContext`: con trỏ tạm tới tập armature của các nhân vật có
  phần đang chọn)
- Modify: `source/blender/editors/animation/anim_filter.cc`
- Modify: `source/blender/makesrna/intern/rna_action.cc` (`DopeSheet.show_whole_character`)
- Modify: `scripts/startup/bl_ui/space_dopesheet.py` (công tắc trong header và popover Filters, chỉ ở Dope Sheet)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`
- Test: `tests/python/dasktoon_animation_filter_test.py` (đăng ký CMake)

**Interfaces:**
- Produces: `DopeSheet.show_whole_character` (bool, mặc định False).

- [ ] **Step 1: Test** — `dasktoon_animation_filter_test.py`:
  - dựng: armature "Rig" (xương "Root", "Arm", có key vị trí), mesh "Face" có modifier Armature → Rig và shape key
    "Basis", "Smile" (key giá trị), empty "Hat" làm con của Rig (key vị trí), armature "Rig2" (một xương có key), empty
    "Prop" (key vị trí);
  - `shown(selected, whole, only_selected=True, bones=None)`: chọn đúng các object trong `selected` (và xương trong `bones`),
    bỏ chọn mọi key bằng Python, đặt cờ cho Dope Sheet của screen "Animation" (chế độ DOPESHEET), chạy
    `action.select_all(action='SELECT')` trong `temp_override(screen=..., area=..., region=...)`, trả tập tên những gì có
    key được chọn: `"Rig:Root"`, `"Rig:Arm"`, `"Face:Smile"`, `"Hat"`, `"Rig2:Root"`, `"Prop"`;
  - `test_off_is_blender`: tắt, chọn Face → `{"Face:Smile"}`;
  - `test_a_selected_face_shows_the_whole_character`: bật, chọn Face → `{"Rig:Root", "Rig:Arm", "Face:Smile", "Hat"}`;
  - `test_a_selected_armature_shows_its_meshes`: bật, chọn Rig → cùng tập trên;
  - `test_every_bone_not_only_selected_ones`: Rig ở Pose Mode, chỉ chọn xương Root: tắt → `{"Rig:Root"}`, bật → có cả
    `"Rig:Arm"`;
  - `test_other_objects_only_when_selected`: bật, chọn Prop → `{"Prop"}`; chọn Prop và Hat → Prop cùng nhân vật Rig;
  - `test_two_characters`: chọn Face và Rig2 → cả hai nhân vật;
  - `test_nothing_selected_shows_nothing`: bật, không chọn gì → tập rỗng;
  - `test_property`: `DopeSheet.show_whole_character` mặc định False, ghi được.

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: 'DopeSheet' object has no attribute 'show_whole_character'`.

- [ ] **Step 3: Code**
  - DNA: `ADS_FILTER_WHOLE_CHARACTER = (1 << 8)` với chú thích "DaskToon: selecting a part of a character shows all of it".
  - `bAnimContext`: `const blender::Set<const Object *> *whole_character = nullptr;` (chú thích: armatures of the characters
    with a selected part, while the Dope Sheet filter runs).
  - `anim_filter.cc`:
    - `actedit_get_context`, `graphedit_get_context`, `nlaedit_get_context`: sau khi chép cờ, nếu `flag2` có
      `ADS_FILTER_WHOLE_CHARACTER` thì `flag |= ADS_FILTER_ONLYSEL` (mọi chỗ khác hành xử như "Only Show Selected").
    - hàm `character_armatures(const Object *ob, Vector<const Object *> &r)`: ob nếu là armature; armature trong chuỗi cha;
      object của mọi modifier Armature.
    - `animdata_filter_dopesheet`: khi cờ bật, trước khi duyệt base: một lượt qua base của view layer, base được chọn (hoặc
      object ở Pose Mode) thì thêm `character_armatures` vào một `Set`; gán `ac->whole_character`, trả về `nullptr` khi xong.
    - `animdata_filter_base_is_ok`: trong khối `ADS_FILTER_ONLYSEL`, nếu `ac->whole_character` thì giữ base khi được chọn,
      ở Pose Mode, hoặc một armature của nó nằm trong tập; ngược lại như cũ.
    - `skip_fcurve_selected_data`: bỏ kiểm tra `POSE_SELECTED` khi `ac->filters.flag2 & ADS_FILTER_WHOLE_CHARACTER`.
  - RNA `rna_def_dopesheet`, sau `show_only_selected`:
```cpp
  prop = RNA_def_property(srna, "show_whole_character", PROP_BOOLEAN, PROP_NONE);
  RNA_def_property_boolean_sdna(prop, nullptr, "filterflag2", ADS_FILTER_WHOLE_CHARACTER);
  RNA_def_property_ui_text(prop,
                           "Whole Character",
                           "Show every channel of the characters that have a selected part: the armature with "
                           "all its bones, the objects parented to it and the meshes it deforms (DaskToon)");
  RNA_def_property_ui_icon(prop, ICON_ARMATURE_DATA, 0);
  RNA_def_property_update(prop, NC_ANIMATION | ND_ANIMCHAN | NA_EDITED, nullptr);
```
  - `space_dopesheet.py`: trong `dopesheet_filter`, sau `show_only_selected`: `if context.area.type == 'DOPESHEET_EDITOR':
    row.prop(dopesheet, "show_whole_character", text="")`; trong `draw_generic_filters` tương tự (có chữ).
  - Bản Việt cho mô tả mới.

- [ ] **Step 4: Build, chạy, thấy PASS** — build (đổi DNA: ~14 phút); `rt.sh dasktoon_animation_filter_test dasktoon_translations_test dasktoon_ui_layout_test`.
- [ ] **Step 5: Commit** — `feat: a Whole Character filter in the Dope Sheet shows every channel of a selected character`.

---

### Task 2: Nhân vật, keying set "DaskToon Character", nút Key Pose

**Files:**
- Create: `scripts/modules/dasktoon_animation/__init__.py`, `scripts/modules/dasktoon_animation/character.py`
- Create: `scripts/startup/bl_ui/dasktoon_animation.py` (keying set, operator, `draw_character_header`, đăng ký); thêm
  `"dasktoon_animation"` vào `_modules` của `bl_ui/__init__.py`
- Modify: `scripts/startup/bl_ui/space_dopesheet.py` (gọi `draw_character_header` khi Whole Character bật)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`, `tests/python/dasktoon_translations_test.py` (module mới vào
  danh sách quét nếu danh sách là tường minh)
- Test: `tests/python/dasktoon_animation_keying_test.py` (đăng ký CMake)

**Interfaces:**
- Produces: `character.armatures_of(obj) -> [Object]`, `character.selected_characters(context) -> [Object]` (armature, thứ
  tự theo tên), `character.members(armature, objects) -> [Object]`; `dasktoon_animation.KEYING_SET = "DASKTOON_KS_character"`;
  `bpy.ops.dasktoon.key_pose()`; `draw_character_header(layout, context)`; `use_character_keying_set(scene) -> bool`.

- [ ] **Step 1: Test** — `dasktoon_animation_keying_test.py` (nhân vật như Task 1, thêm một controller trên Face:
  `face.dask_shape_controllers.groups.add()`):
  - `test_members`: `members(Rig)` = Rig, Face, Hat; `armatures_of(Face)` = [Rig]; mesh có hai modifier Armature thuộc hai
    nhân vật;
  - `test_key_pose_keys_the_whole_character`: chỉ chọn Face, `bpy.ops.dasktoon.key_pose()` → Root và Arm có key xoay và scale
    (Root có cả vị trí; Arm nối với Root thì không), Smile có key, Basis không, `handle_x`/`handle_y` của controller có key;
    Hat không có key mới (spec §5);
  - `test_other_objects_key_location_rotation_scale`: chọn Prop → key `location`, `rotation_euler`, `scale`;
  - `test_nothing_selected`: không chọn gì → `RuntimeError` có chữ "Select a part of a character";
  - `test_character_keying_set_is_used_when_the_scene_has_none`: `use_character_keying_set(scene)` → True và keying set
    đang dùng là "DaskToon Character"; gọi lại khi scene đã có keying set khác (Blender "Location") → False, giữ nguyên;
  - `test_header`: Dope Sheet bật Whole Character thì header vẽ `dasktoon.key_pose`; tắt thì không (RecordingLayout).

- [ ] **Step 2: Chạy, thấy FAIL** — `ModuleNotFoundError: dasktoon_animation`.

- [ ] **Step 3: Code**
  - `character.py`:
```python
def armatures_of(obj):
    """Armatures whose characters `obj` belongs to (spec 4): itself, an armature among its parents, the objects of its
    Armature modifiers; no duplicates."""
    found = []
    if obj.type == 'ARMATURE':
        found.append(obj)
    parent = obj.parent
    while parent is not None:
        if parent.type == 'ARMATURE':
            found.append(parent)
        parent = parent.parent
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object is not None:
            found.append(modifier.object)
    return list(dict.fromkeys(found))


def members(armature, objects):
    return [obj for obj in objects if armature in armatures_of(obj)]


def selected_characters(context):
    """Armatures of the characters with a selected part (or an object in Pose Mode), sorted by name."""
    found = {arm for obj in context.view_layer.objects if obj.select_get() or obj.mode == 'POSE'
             for arm in armatures_of(obj)}
    return sorted(found, key=lambda arm: arm.name)
```
  - Keying set (trong `bl_ui/dasktoon_animation.py`, dựa trên `keyingsets_builtins.WholeCharacterMixin`):
```python
class DASKTOON_KS_character(WholeCharacterMixin, KeyingSetInfo):
    """Key the whole pose of the selected characters: every bone, every shape key of their meshes and every expression
    controller; other selected objects get location, rotation and scale"""
    bl_idname = "DASKTOON_KS_character"
    bl_label = "DaskToon Character"

    def poll(self, context):
        return bool(context.selected_objects) or bool(character.selected_characters(context))

    def iterator(self, context, ks):
        objects = list(context.view_layer.objects)
        for armature in character.selected_characters(context):
            for bone in armature.pose.bones:
                self.generate(context, ks, bone)
            for obj in character.members(armature, objects):
                self.generate_face(ks, obj)
        for obj in context.selected_objects:
            if not character.armatures_of(obj):
                keyingsets_utils.RKS_GEN_location(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_rotation(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_scaling(self, context, ks, obj)

    def generate_face(self, ks, obj):
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is not None:
            for block in key.key_blocks:
                if block != key.reference_key:
                    ks.paths.add(key, 'key_blocks["%s"].value' % bpy.utils.escape_identifier(block.name),
                                 group_method='NAMED', group_name=obj.name)
        root = getattr(obj, "dask_shape_controllers", None)
        for i in range(len(root.groups) if root is not None else 0):
            for axis in ("handle_x", "handle_y"):
                ks.paths.add(obj, "dask_shape_controllers.groups[%d].%s" % (i, axis),
                             group_method='NAMED', group_name="Controllers")
```
    (`generate` của mixin cho xương giữ nguyên; tên tiền tố "xấu" của mixin không ảnh hưởng rig DaskToon.)
  - `DASKTOON_OT_key_pose` (`bl_options = {'REGISTER', 'UNDO'}`): không có object chọn và không có nhân vật →
    `report({'ERROR'}, rpt_("Select a part of a character to key its pose"))`; ngược lại
    `bpy.ops.anim.keyframe_insert_by_name(type=KEYING_SET)` rồi `report({'INFO'}, rpt_("Keyed the pose of %s") % names)`.
  - `draw_character_header(layout, context)`: `layout.operator("dasktoon.key_pose", icon='KEY_HLT')` (B, C thêm ở đây).
  - `space_dopesheet.py`, `DOPESHEET_HT_editor_buttons.draw_header`: ở chế độ DOPESHEET, nếu
    `st.dopesheet.show_whole_character`: `from bl_ui.dasktoon_animation import draw_character_header` và vẽ ngay sau menu.
  - `use_character_keying_set(scene)`: nếu `scene.keying_sets_all.active` là None thì đặt keying set "DaskToon Character"
    làm keying set đang dùng (theo cách Blender lưu keying set dựng sẵn: chỉ số âm trong `keying_sets_all`), trả True.
  - Bản Việt: nhãn, mô tả keying set, Key Pose, hai thông báo.

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_animation_keying_test dasktoon_animation_filter_test dasktoon_translations_test dasktoon_ui_layout_test dasktoon_expressions_test`.
- [ ] **Step 5: Commit** — `feat: Key Pose and a DaskToon Character keying set key every bone and expression of a character`.

---

### Task 3: `bpy.data.workspaces.replace(old, new)` (C++)

**Files:**
- Modify: `source/blender/makesrna/intern/rna_main_api.cc`
- Test: `tests/python/dasktoon_animation_tab_test.py` (lớp `ReplaceTest`; đăng ký CMake)

**Interfaces:**
- Produces: `bpy.data.workspaces.replace(old, new)`.

- [ ] **Step 1: Test** — `ReplaceTest`: ghi workspace "Layout" ra file tạm (`bpy.data.libraries.write`), nạp lại (thành
  "Layout.001"), đặt `new["mark"] = 1`; lưu file chính rồi mở lại (để `is_dirty` False); `replace(Animation, new)` →
  `bpy.data.workspaces["Animation"]["mark"] == 1`, không còn "Layout.001", số workspace như trước khi nạp, `is_dirty` vẫn
  False; `replace(x, x)` → `RuntimeError`.

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: 'bpy_prop_collection' object has no attribute 'replace'`.

- [ ] **Step 3: Code**
```cpp
static void rna_Main_workspaces_replace(
    Main *bmain, bContext *C, ReportList *reports, PointerRNA *old_ptr, PointerRNA *new_ptr)
{
  WorkSpace *old_workspace = static_cast<WorkSpace *>(old_ptr->data);
  WorkSpace *new_workspace = static_cast<WorkSpace *>(new_ptr->data);
  if (old_workspace == new_workspace) {
    BKE_report(reports, RPT_ERROR, "A workspace cannot replace itself");
    return;
  }
  wmWindowManager *wm = CTX_wm_manager(C);
  const bool file_saved = wm ? wm->file_saved : true;
  BKE_id_reorder(reinterpret_cast<const ListBaseT<ID> *>(&bmain->workspaces),
                 &new_workspace->id, &old_workspace->id, false);
  if (wm) {
    wmWindow *window = CTX_wm_window(C);
    for (wmWindow &win : wm->windows) {
      if (WM_window_get_active_workspace(&win) == old_workspace) {
        CTX_wm_window_set(C, &win);
        ED_workspace_change(new_workspace, C, wm, &win);
      }
    }
    CTX_wm_window_set(C, window);
  }
  const std::string name = BKE_id_name(old_workspace->id);
  ED_workspace_delete(old_workspace, bmain, C, wm);
  RNA_POINTER_INVALIDATE(old_ptr);
  BKE_libblock_rename(*bmain, new_workspace->id, name);
  if (wm) {
    wm->file_saved = file_saved;
  }
  WM_main_add_notifier(NC_SCREEN | ND_LAYOUTBROWSE, nullptr);
}
```
  Định nghĩa trong `RNA_def_main_workspaces`: `FUNC_USE_CONTEXT | FUNC_USE_REPORTS`; hai tham số `old`, `new`
  (`WorkSpace`, `PROP_NEVER_NULL`, `PARM_REQUIRED | PARM_RNAPTR`; `old` bỏ `PROP_THICK_WRAP` như các hàm remove); mô tả "Put
  a workspace in the place of another: its tab position, the windows that showed the other, and its name; the other is
  deleted (DaskToon)". (Tên hàm C++ phụ trợ đúng như trong mã nguồn khi làm, ví dụ `BKE_id_name`, `RNA_POINTER_INVALIDATE`.)

- [ ] **Step 4: Build, chạy, thấy PASS** — `rt.sh dasktoon_animation_tab_test`.
- [ ] **Step 5: Commit** — `feat: bpy.data.workspaces.replace puts a workspace in the place of another`.

---

### Task 4: File mẫu tab Animation, thay tab khi mở file

**Files:**
- Create: `tools/dasktoon_build_animation_tab.py`, `scripts/startup/bl_ui/dasktoon_animation.blend`
- Create: `scripts/modules/dasktoon_animation/tab.py`
- Modify: `scripts/startup/bl_ui/dasktoon_animation.py` (handler `load_post`)
- Test: `tests/python/dasktoon_animation_tab_test.py` (lớp `TabTest`)

**Interfaces:**
- Produces: `tab.TEMPLATE`, `tab.MARK = "dasktoon_animation_template"`, `tab.VERSION = 1`, `tab.ensure_animation_tab() -> bool`.

- [ ] **Step 1: Test** — `TabTest`:
  - `test_the_tab_after_startup`: workspace "Animation" có `MARK == VERSION`, `object_mode == 'POSE'`; các ô: hai
    VIEW_3D (một ô `view_perspective == 'CAMERA'`, `shading.type == 'RENDERED'`, không toolbar, không gizmo; ô kia có
    toolbar), PROPERTIES (`context == 'DATA'`), DOPESHEET_EDITOR (`mode == 'DOPESHEET'`, `show_whole_character`, có
    footer), không OUTLINER;
  - `test_an_old_tab_is_replaced_and_the_file_stays_clean`: xóa `MARK` khỏi tab, lưu, mở → có lại `MARK`, không có
    "Animation.001", số workspace như cũ, `is_dirty` False;
  - `test_a_current_tab_is_kept`: đặt `ws["kept"] = 1`, lưu, mở → còn `kept`;
  - `test_a_deleted_tab_is_not_added`: xóa workspace Animation (`bpy.data.batch_remove`), lưu, mở → không có "Animation";
  - `test_scenes_get_the_character_keying_set_on_open`;
  - `test_the_template_file`: `tab.TEMPLATE` tồn tại và chỉ có workspace "Animation".

- [ ] **Step 2: Chạy, thấy FAIL**.

- [ ] **Step 3: Code**
  - `tools/dasktoon_build_animation_tab.py` (`DaskToon.exe --background --factory-startup --python ... -- <out.blend>`;
    nếu `screen.area_close` cần cửa sổ thì chạy có cửa sổ): lấy tab "Animation" gốc của Blender, đóng ô Outliner
    (`screen.area_close` trong `temp_override(screen=..., area=...)`), đặt các thiết lập ở Step 1, `ws[MARK] = VERSION`, ghi
    `bpy.data.libraries.write(out, {ws}, fake_user=True)`; in cấu trúc ô để so.
  - `tab.py`:
```python
def ensure_animation_tab():
    """Replace the file's Animation tab by DaskToon's (spec 6) when it is Blender's or an older DaskToon one. A file
    without an Animation tab keeps it that way. Returns True when the tab was replaced."""
    old = bpy.data.workspaces.get("Animation")
    if old is None or old.get(MARK, 0) >= VERSION:
        return False
    with bpy.data.libraries.load(TEMPLATE, link=False) as (_src, dst):
        dst.workspaces = ["Animation"]
    new = dst.workspaces[0]
    new.use_fake_user = False
    bpy.data.workspaces.replace(old, new)
    return True
```
  - Handler `@persistent def load_post(_filepath)`: `tab.ensure_animation_tab()`, rồi `use_character_keying_set(scene)` cho
    mọi scene; đăng ký trong `register()`, gỡ trong `unregister()`.
  - Kiểm thứ tự undo: mở file trong cửa sổ, Ctrl+Z ngay không đưa tab cũ trở lại (ghi kết quả vào ledger).

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_animation_tab_test dasktoon_animation_keying_test dasktoon_animation_filter_test dasktoon_file_redirect_test dasktoon_model_test dasktoon_project_ui_test`.
- [ ] **Step 5: Commit** — `feat: DaskToon's Animation tab replaces Blender's when a file opens`.

---

### Task 5: Ảnh, báo cáo, kiểm tra

- [ ] Công cụ `tools/dasktoon_animation_screenshots.py` (cửa sổ thật, tiếng Anh và tiếng Việt): nhân vật thử của rig (Build
  Rig) có một shape key mặt; mở tab Animation, chọn mesh thân, Key Pose ở khung 1 và 12 với dáng khác; ảnh
  `30_animation_tab` (cả cửa sổ) và `31_character_timeline` (ô Dope Sheet), vào `docs/superpowers/reports/animation-tab/en|vi/`.
- [ ] Toàn bộ suite CMake, script nạp module.
- [ ] Báo cáo `docs/superpowers/reports/2026-10-10-dasktoon-animation-tab-report.md`: đã làm, cách dùng, kiểm thử, ảnh, quyết
  định Claude tự chốt (chờ duyệt), review, còn lại.
