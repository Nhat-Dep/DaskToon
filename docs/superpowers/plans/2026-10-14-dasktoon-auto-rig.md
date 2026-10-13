# DaskToon: tự rig một nút và mục Kiểm tra — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** (2026-10-14, "Duyệt, làm tự động"); Claude chạy **inline** trên nhánh
> `dasktoon-auto-rig` (từ `dasktoon-rig-regions`, `e923ff7ce3d`). Không đẩy lên GitHub, không gộp nhánh, không subagent.

**Goal:** Chọn nhân vật, bấm Thêm › Khung xương › Khung người anime là có rig hoàn chỉnh; mục Kiểm tra cho thử tư thế và
chỉ ra khớp lệch, chỗ kéo giãn, vai trò có vẻ sai, mỗi chỗ có nút sửa.

**Architecture:** Module mới `dasktoon_rig/check.py` (tư thế thử, biến dạng tính bằng weight, ba loại kiểm tra); nút
thêm khung trong `bl_ui/dasktoon_rig.py` chạy tự rig; mục con Kiểm tra cùng các nút sửa; danh sách chỗ cần xem lưu trên
`DaskRig`.

**Tech Stack:** Python `bpy`, numpy, `mathutils.bvhtree`, `gpu` (làm sáng chỗ đang xem).

**Spec:** `docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md`

## Global Constraints

- Không đẩy lên GitHub, không gộp nhánh; test và công cụ dùng thư mục tạm, `DASKTOON_CONFIG_DIR` trỏ thư mục tạm; không
  ghi vào project Unity trong `D:\Unity\`; chỉ làm trên bản sao file mô hình của người dùng, ảnh có nhân vật của người
  dùng không vào git; ảnh giao diện chỉ một bộ, một ngôn ngữ.
- Chữ mới có bản Việt; file mới vào danh sách quét của `dasktoon_translations_test.py`; mọi biểu tượng có thật.
- Mỗi Task một lần lưu phiên bản; kiểm tra viết trước, thấy hỏng trước khi sửa; chỉ lưu phiên bản khi kiểm tra đạt.
- Kế hoạch ngắn, code viết trong bước TDD.
- Trả lời người dùng bằng tiếng Việt, ít chữ tiếng Anh.

## Review Focus

1. Rig có hoạt hình (clip): thử tư thế rồi đổi khung hình thì hoạt hình hiện lại; không khóa hình nào được thêm.
2. Mô hình hở (cổ tay áo, cổ áo): khớp đúng chỗ không bị báo nhầm là ngoài thân.
3. Gập khớp bình thường (khuỷu, gối khi Ngồi): không bị báo kéo giãn nhầm.
4. Quần (hai ống) không bị báo là váy; váy liền thân (váy đầm) không bị báo; mũ không bị báo là tóc.
5. Tự rig lỗi giữa chừng: khung vẫn còn, thông báo rõ.

---

### Task 1: Tư thế thử và biến dạng tính bằng weight (`check.py`)

- `POSES`, `apply_pose(context, rig, pose)`, `deformed(rig, obj) -> world positions` (weight × ma trận xương).
- Test: `tests/python/dasktoon_rig_check_test.py` (mới).

### Task 2: Ba loại kiểm tra

- `joint_issues(rig, parts)`, `stretch_issues(context, rig, parts)`, `role_issues(rig, parts)`, `run(context, rig)`
  (lưu vào `DaskRig.issues`).
- Test: check test (khớp dời ra ngoài, nửa tai theo tay, váy và tóc là Quần áo, nhân vật đúng thì không báo gì).

### Task 3: Tự rig và mục Kiểm tra

- Nút thêm khung chạy tự rig; mục con Kiểm tra; các nút: tư thế, Kiểm tra lại, Xong, Sửa (khớp), Xem, Tô vùng (theo phần),
  Đổi thành Tóc/Váy; làm sáng chỗ đang xem; bản Việt.
- Test: `tests/python/dasktoon_rig_ui_test.py`.

### Task 4: Thử trên mô hình thật, ảnh, báo cáo

- Bản sao tdt, lr_shape: tự rig, danh sách chỗ cần xem; một ảnh mục Kiểm tra (nhân vật thử, một ngôn ngữ); báo cáo
  `docs/superpowers/reports/2026-10-14-dasktoon-auto-rig-report.md`.
