# DaskToon: clip cho Unity (B) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **làm B, tự động như A** (2026-10-10); Claude chạy **inline** trên nhánh `dasktoon-clips` (từ
> `dasktoon-animation-tab`, `6c3d986b3ed`). Không push, không merge.

**Goal:** Mỗi nhân vật có nhiều clip (một Action có slot cho cả thân và mặt), quản lý trong header timeline nhân vật; Engine
Export đưa mỗi clip sang Unity thành một AnimationClip đúng tên, đúng cờ lặp.

**Architecture:** Module `dasktoon_animation/clips.py` (clip của nhân vật, tạo, chuyển, xóa, gom animation cũ); giao diện
trong `bl_ui/dasktoon_animation.py` (menu, operator, `draw_character_header`); xuất trong `dasktoon_export` (`clip_meta`,
ghi `<Model>@<Clip>.fbx`).

**Tech Stack:** Python `bpy` (Action slot của Blender 5.2), YAML meta của Unity, harness Unity.

**Spec:** `docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md`.

## Global Constraints

- Không xóa Action của người dùng trừ khi họ bấm Delete Clip (có xác nhận).
- Xuất xong thì clip đang dùng, khoảng khung scene và trạng thái mute như trước khi xuất.
- Chữ mới có bản Việt; quy tắc quét bản dịch.
- Không push, không merge; test dùng thư mục tạm; test Unity chỉ dùng project tạm của harness.

## Review Focus

1. Chuyển clip đổi cho mọi thành phần (armature, Key của mesh, object có controller); key mới vào đúng clip. Test Task 1.
2. Gom animation cũ không mất đường cong. Test Task 1.
3. Meta clip: tên, take, khoảng, lặp, avatar nguồn. Test Task 2; Unity thật Task 3.

---

### Task 1: Clip của nhân vật và giao diện

**Files:**
- Create: `scripts/modules/dasktoon_animation/clips.py`
- Modify: `scripts/startup/bl_ui/dasktoon_animation.py` (thuộc tính `Action.dasktoon_character`, menu
  `DASKTOON_MT_character_clips`, operator `dasktoon.clip_new`, `dasktoon.clip_use`, `dasktoon.clip_delete`, header)
- Modify: `scripts/startup/bl_ui/dasktoon_translations.py`, `tests/python/dasktoon_translations_test.py`
- Test: `tests/python/dasktoon_clips_test.py` (đăng ký CMake)

**Interfaces:**
- Produces: `clips.clips_of(armature)`, `clips.parts(armature, objects)` (ID nhận clip: armature, Key, object có
  controller), `clips.current(armature)`, `clips.new(armature, objects, name="Clip")`, `clips.use(armature, objects, clip)`,
  `clips.delete(armature, objects, clip)`, `clips.adopt(armature, objects)`, `clips.frame_range(clip)`.

- [ ] **Step 1: Test** — nhân vật của `dasktoon_animation_filter_test.scene()` (Rig, Face có Key, controller trên Face):
  `test_new_clip_is_assigned_to_every_part`, `test_keys_go_into_the_clip` (key xương và shape key khi clip Walk đang dùng
  nằm trong slot `OBRig`, `KEKey` của Walk), `test_switching`, `test_existing_animation_becomes_the_first_clip` (F-curve cũ
  của Rig và Key có trong clip "Clip"), `test_delete` (clip còn lại được dùng; hết clip thì không còn action),
  `test_loop_and_range`, `test_preview_range_follows_the_clip`, `test_header` (RecordingLayout: menu, tên, Loop, +).
- [ ] **Step 2: Chạy, thấy FAIL**.
- [ ] **Step 3: Code** theo spec §3–§5.
- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_clips_test dasktoon_animation_keying_test dasktoon_animation_filter_test dasktoon_translations_test`.
- [ ] **Step 5: Commit** — `feat: a character has clips, one action each, made and switched in the character timeline`.

---

### Task 2: Xuất clip sang Unity

**Files:**
- Modify: `scripts/modules/dasktoon_export/unity_yaml.py` (`clip_meta`), `scripts/modules/dasktoon_export/__init__.py`
  (ghi file clip, model không animation khi có clip), `scripts/modules/dasktoon_export/report.py` (dòng Clips)
- Test: `tests/python/dasktoon_export_clips_test.py` (đăng ký CMake)

- [ ] **Step 1: Test** — xuất vào thư mục tạm (PROJECT mode như `dasktoon_export_rig_test`): nhân vật hai clip (Walk lặp,
  Wave không lặp) → `Model/<M>.fbx` (meta `importAnimation: 0`), `Model/<M>@Walk.fbx`, `Model/<M>@Wave.fbx` với meta đúng
  tên, `takeName`, khoảng, `loopTime`, `avatarSetup: 2` và nguồn là guid của model; sau khi xuất clip đang dùng, khoảng khung,
  mute như cũ; không có clip thì không có file `@`; dòng báo cáo.
- [ ] **Step 2: Chạy, thấy FAIL**.
- [ ] **Step 3: Code** theo spec §6.
- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_export_clips_test dasktoon_export_rig_test dasktoon_export_fbx_test dasktoon_engine_export_ui_test`.
- [ ] **Step 5: Commit** — `feat: Engine Export writes each clip as <Model>@<Clip>.fbx for Unity`.

---

### Task 3: Unity thật, ảnh, báo cáo

- [ ] `tests/python/dasktoon_unity_clips_test.py` + `tests/unity/Editor/DaskToonClipTests.cs`: mỗi file `@` có một
  AnimationClip đúng tên, lặp, độ dài, có đường cong `blendShape.Smile`.
- [ ] Ảnh: thêm vào `tools/dasktoon_animation_screenshots.py` ảnh `32_clips` (menu clip mở).
- [ ] Toàn bộ suite CMake; báo cáo `docs/superpowers/reports/2026-10-10-dasktoon-clips-report.md`.
