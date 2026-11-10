# Rig cơ khí, phần 1 — Kế hoạch

Thiết kế: `docs/superpowers/specs/2026-11-10-dasktoon-machine-rig-design.md`. Mỗi bước: kiểm thử hỏng trước, mã, chạy,
commit. Chạy bằng `DaskToon.exe --background --factory-startup --python tests/python/dasktoon_machine_test.py` sau
khi đồng bộ `tools/dasktoon_sync_build.py`.

1. Máy giả lập (`dasktoon_machine_fixtures.py`) + `pieces.py`: dt_piece, cụm, bắn tia, từ vùng chọn. Tạo máy (`create`).
2. `joints.py`: đoán khớp (trụ / thẳng / phẳng / khối / hở).
3. `joints.py`: thêm khớp (xương, hướng, trọng lượng), gỡ, đổi cha, dời tâm; tư thế nghỉ 0; quay cứng.
4. Loại khớp + giới hạn (`Bone.dasktoon_joint` ở bl_ui, áp bằng `joints.apply_kind`), `shapes.py`.
5. `tool.py` ToolState.
6. `legs.py` chân IK + snap.
7. `aim.py` ngắm.
8. Làm cứng các mảnh (mô hình nhập).
9. `bl_ui/dasktoon_machine.py`: toán tử, công cụ modal + vẽ, bảng, menu; poll Anime Rig; tiếng Việt; CMake.
10. Chạy bộ kiểm thử rig + dịch; thử mô hình; ảnh chụp; push.
