# DaskToon: nhịp anime và bộ lọc hành động nhanh (C) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **làm C, tự động như B** (2026-10-13); Claude chạy **inline** trên nhánh `dasktoon-anime-timing`
> (từ `dasktoon-clips`, `0b7a00e9310`). Không push, không merge.

**Goal:** Clip chạy theo nhịp anime (1s–4s, Giữ, đổi nhịp giữa clip) trong DaskToon và Unity; onion skin cho nhân vật; bộ
lọc hành động nhanh (smear, afterimage, speed lines) khi render trong DaskToon.

**Architecture:** C++ lượng tử hóa thời gian khi tính action có `dasktoon_timing`; module `dasktoon_animation` thêm
`timing.py`, `onion.py`, `fast_action.py`; giao diện ở header timeline nhân vật (`bl_ui/dasktoon_animation.py`); Unity: dấu
trong meta + `DaskToonClipImporter.cs`.

**Tech Stack:** C++ (blenkernel), Python `bpy`/`gpu`, Geometry Nodes (Simulation Zone), C# (Unity 6000.5).

**Spec:** `docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md`.

## Global Constraints

- Action không có bảng nhịp tính như Blender (không đổi một giá trị nào).
- Chữ mới có bản Việt; quy tắc quét bản dịch.
- Không push, không merge; test dùng thư mục tạm; test Unity chỉ dùng project tạm của harness.
- Build: `MSYS_NO_PATHCONV=1 "$MSBUILD" "D:/build_windows_x64_vc17_Release/INSTALL.vcxproj" -p:Configuration=Release -m -v:m -nologo`.

## Review Focus

1. Giá trị từng khung theo nhịp (xương và shape key), khung lẻ, không bảng thì như cũ. Task 1.
2. Unity: tiếp tuyến Constant, giá trị giữ đúng giữa hai khung vẽ. Task 3.
3. Onion skin trả khung hiện tại và trạng thái như cũ sau khi chép hình. Task 4.
4. Hành động nhanh: có hiệu ứng khi nhanh, không có khi dừng. Task 5.

---

### Task 1: Tính nhịp (C++) và bảng nhịp

**Files:** `source/blender/blenkernel/intern/anim_sys.cc`; Create `scripts/modules/dasktoon_animation/timing.py`; Modify
`scripts/startup/bl_ui/dasktoon_animation.py` (PropertyGroup `DaskTimingStep` {frame: Int, step: Int (0 = Giữ)},
`Action.dasktoon_timing`); Test `tests/python/dasktoon_timing_test.py` (CMake).

**Interfaces:** `timing.step_at(action, frame) -> int` (0 = Giữ), `timing.drawn_frame(action, frame) -> int`,
`timing.set_step(action, frame, step)`, `timing.remove(action, frame)`, `timing.has_steps(action) -> bool`,
`timing.LABELS = {1: "1s", 2: "2s", 3: "3s", 4: "4s", 0: "Hold"}`.

- [ ] Test: xương Root có key vị trí x = khung (1..12, tuyến tính), shape key Smile = khung/12. Bảng {1: 2} → ở khung 2 bằng
  khung 1, khung 4 bằng khung 3; {1: 3}; {1: 2, 7: 1} → khung 8 là 8; {1: 0 (Giữ), 5: 1} → khung 1–4 bằng khung 1; khung lẻ
  2.5 với 2s bằng khung 1; action không bảng: khung 2.5 là 2.5; `drawn_frame`.
- [ ] FAIL → Code: trong `animsys_evaluate_animdata` (nhánh active action, không NLA) gọi hàm mới
  `dasktoon_timing_eval_time(const ID &action_id, float eval_time)`: đọc `system_properties` → `"dasktoon_timing"`
  (IDP_IDPARRAY các group có `frame`, `step`), chọn dòng có khung lớn nhất ≤ t; nhịp > 1 lượng tử hóa, 0 giữ ở khung dòng;
  dùng bản sao `AnimationEvalContext` với `eval_time` mới. Build, PASS.
- [ ] Commit: `feat: a clip can run on twos, threes, fours or hold, evaluated with its timing table`.

### Task 2: Giao diện nhịp, Key Pose theo nhịp

**Files:** `bl_ui/dasktoon_animation.py` (popover `DASKTOON_PT_character_timing`, operator `dasktoon.timing_set`
{step}, `dasktoon.timing_remove` {frame}, nhãn nút trong `draw_character_header`; Key Pose key vào `drawn_frame`),
`dasktoon_translations.py`; Test thêm vào `dasktoon_timing_test.py`.

- [ ] Test: operator đặt/sửa/xóa dòng; nhãn header ("2s"); popover liệt kê dòng; Key Pose ở khung 2 với 2s key vào khung 1.
- [ ] Code, PASS, bản dịch. Commit: `feat: the character timeline sets the clip's timing, and Key Pose keys the drawn frame`.

### Task 3: Nhịp anime trong Unity

**Files:** `dasktoon_export/__init__.py`, `unity_yaml.py` (dấu `DaskToonStepped`, `animationCompression: 0` cho clip có
nhịp; userData nhiều dấu cách nhau bởi dấu cách), `unity_scripts/Editor/DaskToonClipImporter.cs` (mới, GUID cố định),
`unity_scripts/Editor/DaskToonAvatarImporter.cs` (đọc dấu theo từng token), `scripts_install.py` (phiên bản 4); Test
`dasktoon_export_clips_test.py`, `dasktoon_export_yaml_test.py`, `dasktoon_export_rig_test.py`, `dasktoon_unity_clips_test.py`
+ `tests/unity/Editor/DaskToonClipTests.cs`.

- [ ] Test: meta clip có nhịp có `DaskToonStepped` và `animationCompression: 0`; clip không nhịp không có; Unity: mọi key
  của clip có nhịp có tiếp tuyến Constant, `Evaluate` giữa hai khung vẽ bằng giá trị khung vẽ trước.
- [ ] Code (`OnPostprocessAnimation`: với dấu, đặt `AnimationUtility.SetKeyLeftTangentMode/RightTangentMode(Constant)` cho
  mọi key của mọi binding, `SetEditorCurve`), PASS (Unity thật). Commit:
  `feat: clips with anime timing stay stepped in Unity`.

### Task 4: Onion skin

**Files:** Create `scripts/modules/dasktoon_animation/onion.py` (`ghost_frames(action, frame, before, after)`,
`capture(context, objects, frames) -> {frame: [(object, tris world)]}`); `bl_ui/dasktoon_animation.py` (thiết lập trên
scene `Scene.dasktoon_onion` {show, before, after, opacity}, popover, hẹn giờ tính lại khi dừng tay, draw handler `gpu`),
bản dịch; Test `tests/python/dasktoon_onion_test.py` (CMake).

- [ ] Test: khung bóng theo key của clip; số bóng; hình mesh ở khung bóng khác khung hiện tại; khung hiện tại và lựa chọn
  như cũ sau khi chép; nhân vật không có action thì không bóng.
- [ ] Code, PASS. Commit: `feat: onion skin shows the character's poses at the keys before and after`.

### Task 5: Bộ lọc hành động nhanh

**Files:** Create `scripts/modules/dasktoon_animation/fast_action.py` (nhóm node "DaskToon Fast Action", material
afterimage và vệt, `apply(armature, objects)`, `sync(armature, objects)`); `bl_ui/dasktoon_animation.py`
(`Armature.dasktoon_fast_action` PropertyGroup, popover, cập nhật), bản dịch; Test `tests/python/dasktoon_fast_action_test.py`
(CMake).

- [ ] Test: khối lập phương (mesh thuộc nhân vật qua modifier Armature hoặc mesh riêng có modifier) lướt nhanh khung 1–6 rồi
  dừng: khung 4 có đỉnh lệch khỏi vị trí của mesh gốc theo hướng ngược chuyển động, số đỉnh tăng (afterimage, vệt), có
  material afterimage và vệt; khung 12 (đã dừng lâu) hình như mesh gốc; đổi thiết lập nhân vật đổi đầu vào modifier; tắt thì
  modifier tắt.
- [ ] Code (Simulation Zone: trạng thái là hình của 3 khung trước; vận tốc theo Delta Time), PASS. Commit:
  `feat: a fast action filter adds smears, afterimages and speed lines where the character moves fast`.

### Task 6: Ảnh, báo cáo, kiểm tra

- [ ] Ảnh (tiếng Anh, tiếng Việt) trong `tools/dasktoon_animation_screenshots.py`: `33_timing` (popover), `34_onion_skin`,
  `35_fast_action` (khung có smear/afterimage/vệt, camera view Rendered).
- [ ] Toàn bộ suite CMake, test Unity (clips, rig, model); báo cáo `docs/superpowers/reports/2026-10-13-dasktoon-anime-timing-report.md`.
