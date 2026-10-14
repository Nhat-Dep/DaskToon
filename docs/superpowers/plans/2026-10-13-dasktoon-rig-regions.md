# DaskToon: vùng cơ thể và lọn gắn đầu — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** cho phần 1 (2026-10-13, "Tự động làm tiếp"); Claude chạy **inline** trên nhánh
> `dasktoon-rig-regions` (từ `dasktoon-real-model-fixes`, `021a5836fd6`). Không push, không merge, không subagent.

**Goal:** Rig nhận ra vùng đầu, thân, tay, chân của mô hình và các lọn gắn đầu, để giơ tay không kéo tai, tóc, dây đeo; vùng
tô được lên mô hình và sửa bằng Vertex Paint; lọn là phần chọn được cứng hay lắc.

**Architecture:** Module mới `dasktoon_rig/regions.py` (nhận diện vùng, mảnh gắn đầu, lọn, lớp màu, giới hạn weight theo
vùng); `build.build()` gọi giới hạn sau khi vẽ weight; `model_fbx.write_fbx` tạm bỏ lớp vùng; giao diện trong
`bl_ui/dasktoon_rig.py` (panel Regions, các nút, làm sáng phần đang chọn).

**Tech Stack:** Python `bpy`, numpy, `mathutils.kdtree`, `gpu` (vẽ làm sáng).

**Spec:** `docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md`

## Global Constraints

- Không push, không merge; test và công cụ dùng thư mục tạm, `DASKTOON_CONFIG_DIR` trỏ thư mục tạm; không ghi vào project
  Unity trong `D:\Unity\`; chỉ làm trên bản sao của file mô hình người dùng, ảnh có nhân vật của người dùng không vào git.
- Chữ mới có bản Việt trong `dasktoon_translations.py`; file mới vào danh sách quét của `dasktoon_translations_test.py`.
- Mỗi Task một commit, test viết trước và chạy thấy hỏng trước khi sửa.
- Kế hoạch ngắn (không chép code trước): code viết trong bước TDD, như kế hoạch sửa lỗi mô hình thật.

## Review Focus

1. Nhân vật không có tay, chân rõ trong bóng (ống thử cũ, T-pose): Build cho weight như trước (không giới hạn sai).
2. Phần Hair, Skirt, Accessory, mặt trên cùng mesh: không bị tô vùng, không bị giới hạn, không thành lọn.
3. Mesh có Mirror hoặc modifier khác: lớp vùng và lọn theo đỉnh của mesh gốc.
4. Vật liệu đọc màu đỉnh mặc định: không đổi màu sau khi Nhận diện.
5. Xuất FBX lỗi giữa chừng: lớp vùng vẫn được trả lại.

---

### Task 1: Nhận diện vùng, mảnh gắn đầu, lọn (`regions.py`, chưa đụng Build)

- Create: `scripts/modules/dasktoon_rig/regions.py`: `REGIONS`, `COLORS`, `LAYER = "DaskToon Region"`, `AUTO = -1`;
  `half_widths(context, rig, objects) -> {bone: half width}` (bóng nhìn trước, tư thế nghỉ, có giới hạn UpperChest, Neck);
  `head_pieces(rig, world, edges, vertices, height) -> [pieces]`; `labels(rig, world, half, head) -> int array`;
  `locks(pieces, world, height, middle) -> [(name, vertices)]`.
- Test: `tests/python/dasktoon_rig_regions_test.py` (mới): nhân vật chibi một mesh có tai, lọn tóc, áo có dây đeo, giày.

### Task 2: Lớp màu vùng và xuất FBX

- `regions.read(obj)`, `regions.write(obj, vertices, labels)` (giữ màu mặc định của mesh), `regions.recognize(context, rig,
  parts)` (ghi vùng, tạo lại lọn là phần, giữ vai trò lọn cũ), cờ `made_by_recognize` của `DaskRigPart` và `parts.Part`.
- Modify: `scripts/modules/dasktoon_export/model_fbx.py` (tạm bỏ lớp vùng khi ghi FBX).
- Test: regions test (đọc, ghi, nhận diện lại), `tests/python/dasktoon_export_fbx_test.py` (không có lớp vùng trong FBX).

### Task 3: Build giới hạn weight theo vùng

- `regions.restrict(context, rig, parts, owners)`; `build.build()` gọi sau `_paint`; nút Build Rig tự Nhận diện khi chưa có
  lớp vùng.
- Test: regions test (giơ tay không kéo tai, dây đeo; tay áo giữ weight; giày giữ weight; tô tay áo sang Thân), các test rig
  cũ vẫn xanh.

### Task 4: Lọn từ chỗ chọn

- Operator `dasktoon.rig_lock_from_selection` (Edit Mode của mesh): mở rộng ra cả mảnh, tách khỏi lọn khác, xóa lọn rỗng.
- Test: regions test (tách, gộp, lọn rỗng bị xóa).

### Task 5: Giao diện

- Panel con Regions (Recognize có hỏi, Show Regions, Paint Regions với ô chọn vùng, chú giải); trong panel mesh khi Vertex
  Paint: nút đổi màu vùng, về rig; Highlight Part trong panel Parts (vẽ mặt của phần đang chọn); bản Việt.
- Test: `tests/python/dasktoon_rig_ui_test.py` (panel, Show Regions bật tắt, Paint Regions, Recognize hỏi), translations.

### Task 6: Thử lại trên mô hình thật và báo cáo

- Bản sao `tdt.blend`, `lr_shape.blend`: Fit, Build (tự Nhận diện), đếm đỉnh xa tay có weight tay, ảnh giơ tay trước và
  sau (chỉ trên máy), báo cáo `docs/superpowers/reports/2026-10-13-dasktoon-rig-regions-report.md`.
