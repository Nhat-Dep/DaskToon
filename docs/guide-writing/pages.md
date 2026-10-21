# Hướng dẫn các chức năng của DaskToon: danh sách trang

Bộ trang thứ hai của Hướng dẫn, bên cạnh "Chín bước từ model mới đến Unity" đã có. Mỗi trang nói về một chức năng
DaskToon có mà Blender không có: dùng để làm gì, bấm ở đâu, cách dùng, điều cần biết. Trang mục lục
`features.html` liệt kê tất cả và được `index.html` dẫn tới.

Người viết đọc `docs/guide-writing/rules.md` trước. Mỗi trang có bản tiếng Anh (`pages/en/`) và tiếng Việt
(`pages/vi/`), cùng tên tệp. Cột "Đọc" là chỗ tìm hiểu chức năng; mã trong `scripts/startup/bl_ui/` là đúng nhất (bản
thiết kế có chỗ đã cũ).

## Các trang

| Tệp | Tên trang (vi / en) | Nội dung | Đọc |
|---|---|---|---|
| `project.html` | Dự án và model / Projects and Models | Màn hình đầu, Tiếp tục như bản nháp, Dự án (mới, mở, cài đặt, gắn dự án game), danh sách Models, các kiểu lưu, nâng cấp tệp cũ | `bl_ui/dasktoon_project.py`, `dasktoon_model.py`, `dasktoon_splash.py`, `dasktoon_upgrade.py`; spec `2026-10-05-dasktoon-project-workflow-design.md` |
| `interface.html` | Giao diện / The Interface | Giao diện khác Blender ở đâu: các thẻ, menu, tiếng Việt, thẻ Hướng dẫn | spec `2026-10-04-dasktoon-ui-reorganization-design.md` |
| `shader.html` | Shader anime / The Anime Shader | Anime BSDF và các phần của nó (Môi trường, Ánh sáng, AO, Viền sáng, Viền, Chỉnh màu), Kiểu đổ bóng, Dùng shader DaskToon, bộ dựng hình DaskToon Anime, Gộp vật liệu | `source/blender/nodes/shader/nodes/node_shader_anime_character.cc`, `bl_ui/dasktoon_material_convert.py`, `dasktoon_shading_styles.py`, `engine_dasktoon_anime.py`, `dasktoon_sun_sync.py`, `dasktoon_material_combiner.py`; spec `2026-10-03-dasktoon-shading-outline-design.md` |
| `nodes.html` | Các node anime khác / Other Anime Nodes | Mỗi node một đoạn: Classic Cel, Anime Eye, Angel Ring, Face Shadow, Anime Fabric/Glass/Knit/Metal/Tights/Water/Wood, Anime Rim, Warm/Cool Grade, Screentone, các node Manga, World Ambient, Crevice AO, Cel Shading, Color Grade, Light Tint | `source/blender/nodes/shader/nodes/node_shader_anime_*.cc`, `node_shader_dask_*.cc`, `node_shader_manga_*.cc` |
| `outline.html` | Viền / Outlines | Viền DaskToon, màu viền, Viền màu cho mọi vật liệu, Chuẩn bị viền cho game, gỡ viền | `bl_ui/dasktoon_outline.py`, `dasktoon_outline_nodes.py`, `dasktoon_outline_gamedata.py`; spec `2026-10-03-dasktoon-shading-outline-design.md` |
| `face-shading.html` | Bóng mặt / Face Shading | Đặt bóng mặt, Khớp proxy, chọn proxy, gỡ | `bl_ui/dasktoon_face_shading.py`, `dasktoon_face_shading_nodes.py`; spec `2026-10-04-dasktoon-face-shading-design.md` |
| `finish.html` | Hoàn thiện tranh / Illustration Finish | 12 lớp theo nhóm Màu tranh, Chiều sâu, Ánh sáng, Chất liệu; kiểu có sẵn và kiểu của bạn; Thêm vào compositor | `scripts/modules/dasktoon_finish/`, `bl_ui/dasktoon_finish.py`; spec `2026-10-13-dasktoon-illustration-finish-design.md` |
| `paint.html` | Tô vẽ theo lớp / Painting in Layers | Bắt đầu tô vẽ, các lớp trong ảnh, bút anime, Tô màu một phần | `scripts/modules/dasktoon_paint/`, `bl_ui/dasktoon_paint.py`; spec `2026-10-20-dasktoon-paint-layers-design.md` |
| `unwrap.html` | Trải UV anime / Anime Unwrap | Trải UV anime, xếp chặt, ảnh theo phần cho game | `scripts/modules/dasktoon_uv/`, `bl_ui/dasktoon_uv.py`; spec `2026-10-20-dasktoon-anime-unwrap-design.md`, `2026-10-20-dasktoon-game-texture-sets-design.md` |
| `anime-rig.html` | Rig anime / The Anime Rig | Khung người anime, Dựng rig, Phần, Khớp, Khớp theo phần, Quay nhân vật, vai theo tay, sửa chỗ gập, ngón tay | `scripts/modules/dasktoon_rig/`, `bl_ui/dasktoon_rig.py`; spec `2026-10-06-dasktoon-anime-rig-design.md`, `2026-10-14-dasktoon-auto-rig-design.md`, `2026-10-14-dasktoon-shoulder-follow-design.md`, `2026-10-20-dasktoon-bend-fixes-design.md`, `2026-10-19-dasktoon-rig-fingers-design.md` |
| `regions.html` | Vùng cơ thể / Body Regions | Nhận diện, Tô vùng, Lọn từ phần chọn | `dasktoon_rig/regions.py`; spec `2026-10-13-dasktoon-rig-regions-design.md` |
| `rig-check.html` | Kiểm tra khung / The Rig Check | Tư thế thử, Kiểm tra, Sửa khớp, Xem chỗ, Đổi vai trò, biến phần dưới eo thành váy | `dasktoon_rig/check.py`; spec `2026-10-14-dasktoon-auto-rig-design.md` |
| `sway.html` | Tóc, váy đung đưa / Sway | Lắc, khối va chạm, Nướng lắc, Lắc trong game | `dasktoon_rig/sway.py`, `spring.py`, `chains.py`, `source/blender/blenkernel/intern/constraint.cc` (Spring); spec `2026-10-06-dasktoon-anime-rig-design.md` mục 9 |
| `eyes-mouth.html` | Mắt, miệng, ánh nhìn / Eyes, Mouth and Gaze | Ánh mắt, mắt phẳng, miệng 2D, hàm, Lip sync từ âm thanh | `dasktoon_rig/eyes.py`, `look.py`, `mouth.py`, `lipsync.py`; spec `2026-10-06-dasktoon-anime-rig-design.md` mục 10 |
| `expression-tools.html` | Bộ biểu cảm / Expression Tools | Bộ biểu cảm VRM, ARKit 52, Điền biểu cảm trống, Nặn biểu cảm mắt, Tách trái phải, Đổi cách đặt tên | `bl_ui/dasktoon_shape_key_manager.py`, `dasktoon_rig/expressions.py`, `eye_shapes.py`; spec `2026-10-20-dasktoon-auto-expressions-design.md` |
| `controllers.html` | Bộ điều khiển biểu cảm / Expression Controllers | Bộ điều khiển, HUD trong khung nhìn, bảng rig 3D, xem trước | `bl_ui/dasktoon_shape_key_manager.py` |
| `animation.html` | Thẻ Hoạt hình / The Animation Tab | Bố cục thẻ, Cả nhân vật, Key tư thế | `bl_ui/dasktoon_animation.py`; spec `2026-10-10-dasktoon-animation-tab-design.md` |
| `clips.html` | Clip / Clips | Clip mới, dùng, xoá, lặp | `dasktoon_animation/clips.py`; spec `2026-10-10-dasktoon-clips-design.md` |
| `timing.html` | Nhịp anime và bóng mờ / Anime Timing and Onion Skin | Vẽ hai, vẽ ba, giữ khung, bóng mờ | `dasktoon_animation/timing.py`, `onion.py`; spec `2026-10-13-dasktoon-anime-timing-design.md` |
| `fast-action.html` | Hành động nhanh và hiệu ứng / Fast Action and Effects | Vệt nhoè, bóng lặp, đường tốc độ, Nướng để dựng hình, Thêm hiệu ứng anime | `dasktoon_animation/fast_action.py`, `bl_ui/dasktoon_anime_fx.py`; spec `2026-10-13-dasktoon-anime-timing-design.md` |
| `export-unity.html` | Xuất sang Unity / Export to Unity | Xuất sang engine với Unity: các lựa chọn, thư mục, báo cáo, dùng trong Unity | `scripts/modules/dasktoon_export/`; spec `2026-10-03-dasktoon-unity-export-design.md` |
| `export-godot.html` | Xuất sang Godot / Export to Godot | Như trên với Godot; lớp Hoàn thiện tranh `<Tên>_finish.tscn`; Normal Bias 4, MSAA 3D | `scripts/modules/dasktoon_export/godot/`; spec `2026-10-20-dasktoon-godot-export-design.md` |

Tên trong cột "Tên trang" là tên tạm; tên nút trong trang phải lấy đúng từ giao diện (xem quy tắc).

## Các đợt

Mỗi đợt một lần giao, xong đợt nào thì Claude soát, chạy phép thử rồi đẩy lên GitHub.

1. **Đợt thử** (xong, Claude đã soát): `features.html`, dòng dẫn trong `index.html`, `outline.html`,
   `face-shading.html`. Hai ảnh bị gỡ vì hỏng; làm lại ở Đợt 2.
2. (xong, Claude làm) Làm lại ảnh `outline.png`, `face-shading.png` theo `rules.md` mục 5 và đặt lại vào hai trang; `shader.html`,
   `nodes.html`, `finish.html`, `paint.html`, `unwrap.html`, `project.html`, `interface.html`.
3. `anime-rig.html`, `regions.html`, `rig-check.html`, `sway.html`, `eyes-mouth.html`, `expression-tools.html`,
   `controllers.html`.
4. `animation.html`, `clips.html`, `timing.html`, `fast-action.html`, `export-unity.html`, `export-godot.html`.

Mỗi đợt thêm các trang của nó vào `features.html`.
