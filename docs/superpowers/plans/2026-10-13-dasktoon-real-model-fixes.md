# DaskToon: sửa bốn lỗi tìm ra khi thử trên mô hình thật — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** (2026-10-13, "Duyệt, làm tự động"); Claude chạy **inline** trên nhánh
> `dasktoon-real-model-fixes` (từ `dasktoon-anime-rig-r3`, `786ad0de4b7`). Không push, không merge.

**Goal:** Sửa bốn lỗi mà lần thử trên mô hình thật (`D:\game\lagote rabina\tdt.blend`, bản sao) tìm ra: clip dính tư thế của
clip khác, Fit to Parts đặt khớp tay và tâm sai trên mesh thật, weight áo kéo theo cánh tay, hành động nhanh tính theo m/s
tuyệt đối nên rối trên nhân vật cao. Thử lại trên bản sao của `tdt.blend`, viết báo cáo có ảnh so sánh.

**Architecture:** Bốn thay đổi đúng chỗ, mỗi cái một commit theo TDD:
1. `dasktoon_animation/clips.use()` đưa về nghỉ những gì clip khác của nhân vật key mà clip này không key.
2. `dasktoon_rig/skeleton.fit()` đặt khớp theo đỉnh mesh của phần Body (tâm, vai, khuỷu, cổ tay, bàn tay, hông, gối, cổ
   chân); không đọc được thì giữ cách cũ theo hộp bao.
3. `dasktoon_rig/weights.surface_weights()` chỉ chép weight từ tam giác da quay cùng phía với đỉnh áo.
4. `dasktoon_animation/fast_action` nhân ngưỡng, độ dài và độ dày vệt theo chiều cao nhân vật / 1.6 m; mật độ vệt mặc định
   0.15 → 0.08.

**Tech Stack:** Python `bpy`, numpy, Geometry Nodes.

**Spec:** thiết kế duyệt trong hội thoại 2026-10-13 (bốn mục, chép ở từng Task dưới); spec rig
`docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md`, spec clip
`docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md`, spec nhịp anime và hành động nhanh.

## Global Constraints

- Không push, không merge; test và công cụ dùng thư mục tạm, `DASKTOON_CONFIG_DIR` trỏ thư mục tạm; không ghi vào project
  Unity trong `D:\Unity\`; chỉ làm trên bản sao của file mô hình người dùng.
- Chữ mới có bản Việt trong `dasktoon_translations.py`.
- Mỗi Task một commit, test viết trước và chạy thấy hỏng trước khi sửa.

## Review Focus

1. **Clip**: thuộc tính không clip nào key (thiết lập tĩnh của người dùng, vị trí object) giữ nguyên khi đổi clip.
2. **Clip xuất**: mỗi file `@Clip.fbx` bắt đầu từ tư thế nghỉ cho những xương clip đó không key.
3. **Fit**: nhân vật thử của test (hộp, T-pose) vẫn khớp như trước; mesh không có tay rõ ràng thì dùng cách cũ.
4. **Weight áo**: áo ôm sát da (tam giác da cùng phía) vẫn nhận weight như trước; không còn đỉnh thân áo theo cánh tay.
5. **Hành động nhanh**: nhân vật cao 1.6 m cho đúng kết quả cũ (trừ mật độ mặc định).

---

### Task 1: Clip không dính tư thế của clip khác

Thiết kế duyệt: khi dùng một clip, những thuộc tính mà một clip khác của nhân vật có key nhưng clip này không key sẽ về giá
trị nghỉ: xương về tư thế nghỉ, shape key về 0, `dt_mouth` về 0. Thuộc tính không clip nào key thì giữ nguyên. Xuất clip
dùng đúng hàm này, nên file Unity cũng sạch.

- Modify: `scripts/modules/dasktoon_animation/clips.py` (`_keyed`, `_rest`, `use`)
- Test: `tests/python/dasktoon_clips_test.py::test_switching_clips_rests_what_the_new_clip_does_not_key`,
  `tests/python/dasktoon_export_clips_test.py::test_each_clip_file_starts_from_rest`

### Task 2: Fit to Parts theo mesh

Thiết kế duyệt: tâm lấy theo trung vị đỉnh của phần Body (không theo hộp bao có tai, tóc); dải đỉnh ở hai bên ngoài vai →
trục chính (PCA) → vai, khuỷu, cổ tay, bàn tay; dải chân → hông, gối, cổ chân; không đọc được thì dùng hộp bao như cũ. Đạt:
bàn tay cách da dưới 5 cm trên bản sao `tdt.blend` và `lr_shape`.

- Modify: `scripts/modules/dasktoon_rig/skeleton.py` (`fit`)
- Test: `tests/python/dasktoon_rig_skeleton_test.py`

### Task 3: Weight áo không theo cánh tay

Thiết kế duyệt: `weights.surface_weights` chỉ lấy tam giác da có pháp tuyến cùng phía với pháp tuyến đỉnh áo (tích vô hướng
> 0); không có thì lấy gần nhất như cũ.

*Đổi khi làm (ruling):* đo trên `tdt.blend` cho thấy nguyên nhân không phải hướng tam giác: da không có phần thân dưới
váy, nên váy chép weight từ da cổ và vai cách 14–42 cm. Quy tắc cùng hướng không đổi gì trên tdt và làm tóc của lr_shape
tệ hơn, nên bỏ. Thay bằng: đỉnh áo xa Body hơn 2% chiều cao Body thì pha dần sang weight tự động của chính phần áo, xa từ
4% trở lên thì dùng hẳn.

- Modify: `scripts/modules/dasktoon_rig/weights.py` (`clothing_weights`, `heat_of_copy`, `surface_weights(distances=)`),
  `scripts/modules/dasktoon_rig/build.py`
- Test: `tests/python/dasktoon_rig_build_test.py` (`FarClothingTest`)

### Task 4: Hành động nhanh theo cỡ nhân vật

Thiết kế duyệt: ngưỡng, độ dài vệt và độ dày vệt nhân theo chiều cao nhân vật / 1.6 m; mật độ vệt mặc định 0.15 → 0.08.

*Đổi khi làm (ruling):* độ dài vệt là thời gian ("dài bằng quãng đi trong khoảng thời gian này"), đã tự theo tốc độ nên
không nhân; chỉ ngưỡng và độ dày vệt nhân theo chiều cao.

- Modify: `scripts/modules/dasktoon_animation/fast_action.py`, `scripts/startup/bl_ui/dasktoon_animation.py`
- Test: `tests/python/dasktoon_fast_action_test.py`

### Task 5: Thử lại trên mô hình thật và báo cáo

- Bản sao `tdt.blend`: Fit, Build, clip Wave và Talk, xuất sang project tạm của harness Unity, ảnh so sánh trước/sau.
- Create: `docs/superpowers/reports/2026-10-13-dasktoon-real-model-report.md`
