# DaskToon: vai nâng theo tay — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao "tự lm" (2026-10-14); Claude làm inline trên nhánh `dasktoon-shoulder-follow` (từ
> `dasktoon-master` 371fd2c, đã đẩy). Không đẩy, không gộp khi chưa hỏi; không subagent.

**Goal:** Xương vai tự nâng khi cánh tay giơ cao, chỉnh được bằng thanh trượt, sang được Unity qua clip.

**Architecture:** Module mới `dasktoon_rig/shoulders.py`: xương phụ ẩn có driver đọc góc giơ của cánh tay, xương vai
chép xoay của nó (Copy Rotation, cục bộ, cộng trước khóa hình). Dựng rig gọi nó; thanh trượt trên `DaskRig`.

**Tech Stack:** Python `bpy`, driver biểu thức đơn giản, ràng buộc Copy Rotation, FBX bake.

**Spec:** `docs/superpowers/specs/2026-10-14-dasktoon-shoulder-follow-design.md`

## Global Constraints

- Không đẩy, không gộp khi chưa hỏi; test dùng thư mục tạm; chữ mới có bản Việt; file mới vào danh sách quét bản dịch.
- Mỗi Task một lần lưu phiên bản; kiểm tra viết trước, thấy hỏng trước; chỉ lưu khi kiểm tra đạt.

## Review Focus

1. Vòng lặp phụ thuộc: xương vai là cha của cánh tay; driver chỉ được đọc giá trị xoay riêng của cánh tay.
2. Khóa hình vai của người dùng vẫn có tác dụng.
3. Nhân vật tư thế T và tư thế A: tư thế nghỉ không bị nâng sẵn.
4. FBX: góc nâng được ghi vào xương vai; xương phụ không lọt vào file.
5. Dựng lại nhiều lần không nhân đôi.

---

### Task 1: Vai nâng theo tay (module, Dựng rig, thanh trượt)

- `shoulders.py`: `apply(context, rig)`, `sync(rig)`; Dựng rig gọi `apply`; `DaskRig.shoulder_follow`; thanh trượt
  trong Khớp nối; bản Việt.
- Test: `tests/python/dasktoon_rig_shoulder_test.py` (mới), `dasktoon_rig_ui_test.py`.

### Task 2: Kiểm chứng trên mô hình thật và báo cáo

- Bản sao tdt: render cận vai ở Vẫy tay trước/sau (chỉ trên máy); đo lại nếp nách; ghi vào báo cáo tự rig một đoạn
  "Vai nâng theo tay"; chạy toàn bộ kiểm tra.
