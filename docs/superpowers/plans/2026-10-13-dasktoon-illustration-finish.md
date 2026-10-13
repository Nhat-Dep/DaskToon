# Kế hoạch: bộ lọc hoàn thiện tranh (Illustration Finish)

Spec: `docs/superpowers/specs/2026-10-13-dasktoon-illustration-finish-design.md`. Chế độ: tự động (người dùng nói
"tự động" sau khi đọc spec), làm inline, mỗi task một commit, quyết định ghi vào ledger và báo cáo.

Sự thật đã thăm dò (Blender 5.2 của DaskToon):

- `scene.compositing_node_group` là node tree compositor; đầu ra là interface socket "Image" và node Group Output.
- Socket dạng menu đặt bằng chuỗi: Glare `Type` = `'Sun Beams'`, có đầu vào `Sun Position`. Kuwahara `Type`
  mặc định Anisotropic.
- Blur `Size` là vector pixel. Relative To Pixel (`reference_dimension = 'Y'`) đổi tỉ lệ thành pixel theo chiều cao ảnh.
- Mix (`ShaderNodeMix`, `data_type = 'RGBA'`) có Screen, Soft Light, Multiply…: đầu vào 0 (Factor), 6 (A), 7 (B), đầu
  ra 2. Math, Vector Math, Map Range, Clamp, Combine/Separate XYZ, Noise Texture, Scene Time dùng được.
- Render Layers có đầu ra Depth khi `view_layer.use_pass_z`. EEVEE đưa pass cho compositor của viewport.
- Nét Harmonic: `outline_tint_mode = 'HARMONIC_KYOTO'` trên Anime Character và Dask Cel; material nguồn kiểu
  `MATERIAL` thì đặt `tint_mode` của node Dask Outline trong `.Outline` theo giá trị 1.

Thiết kế code:

- `dasktoon_finish/settings.py`: **một bảng duy nhất** mô tả mọi thiết lập (khóa, nhãn, kiểu, mặc định, khoảng, lớp).
  PropertyGroup, đầu vào nhóm node và file style đều sinh từ bảng này.
- **Công tắc lớp** quyết định cấu trúc nhóm node: nhóm được dựng lại khi bật/tắt lớp, nên lớp tắt không tốn gì. **Thanh
  chỉnh** là đầu vào của nhóm, đổi không phải dựng lại.
- Mỗi scene một nhóm (`Scene.dasktoon_finish.group`).

## Task 1: Nhóm node và compositor của scene

**Files:** tạo `scripts/modules/dasktoon_finish/{__init__,settings,nodes,scene}.py`; test
`tests/python/dasktoon_finish_test.py` (CMake, danh sách bản dịch).

- [ ] Test: nhóm dựng được với mọi lớp bật và mọi lớp tắt; đầu vào nhóm đủ theo bảng; lớp tắt thì không có node của
  lớp đó; dựng được khi giao diện tiếng Việt; scene trống thì có tree "DaskToon Compositor" (Render Layers → nhóm →
  đầu ra, Depth nối); tree của người dùng không đổi; chèn vào tree người dùng trước đầu ra; tắt thì nhóm bị mute;
  pass Depth bật.
- [ ] Code, PASS. Commit: `feat: the illustration finish node group and the scene's compositor`.

## Task 2: Thiết lập, panel, nét màu

**Files:** tạo `scripts/startup/bl_ui/dasktoon_finish.py` (PropertyGroup sinh từ bảng, `Scene.dasktoon_finish`, panel và
panel con trong Render Properties, operator Thêm vào compositor, Nét màu cho mọi material, chế độ xem trong viewport),
đăng ký trong `bl_ui/__init__.py`; bản dịch; test thêm vào `dasktoon_finish_test.py`.

- [ ] Test: đổi thanh chỉnh ghi vào đầu vào của node nhóm; bật/tắt lớp dựng lại nhóm; bật bộ lọc tạo tree và bật pass;
  chế độ xem đặt `use_compositor` của 3D View; nút nét màu đặt Harmonic cho material có outline (Anime Character, Dask
  Cel, kiểu material) và bỏ qua material khác; panel vẽ đủ bốn nhóm.
- [ ] Code, PASS. Commit: `feat: an Illustration Finish panel sets the filter, its layers and colored lines`.

## Task 3: Mặt trời và khoảng lấy nét

**Files:** tạo `scripts/modules/dasktoon_finish/sun.py` (vị trí mặt trời trên ảnh, có ở trước camera không, hướng ánh
sáng trên ảnh, khoảng lấy nét tự động); handler đồng bộ trong `bl_ui/dasktoon_finish.py`; test.

- [ ] Test: Sun trước camera cho vị trí trong ảnh và cờ nhìn thấy; Sun sau camera tắt cờ; hướng ánh sáng trên ảnh khớp
  phía Sun; khoảng lấy nét theo lấy nét của camera, rồi theo object đang chọn; handler ghi vào node nhóm, không ghi
  lại khi giá trị không đổi.
- [ ] Code, PASS. Commit: `feat: the finish follows the scene's sun and focuses on the subject`.

## Task 4: Style

**Files:** tạo `scripts/modules/dasktoon_finish/styles.py` (năm style có sẵn, style người dùng JSON trong
`dasktoon/finish_styles`, biến `DASKTOON_FINISH_STYLES_DIR`); menu và operator trong `bl_ui/dasktoon_finish.py`; test.

- [ ] Test: style có sẵn đặt đúng thiết lập; lưu, đọc, ghi đè, xóa style người dùng; thiếu khóa thì mặc định; tên lạ
  thì tên file an toàn.
- [ ] Code, PASS. Commit: `feat: illustration finish styles, built in and the user's own`.

## Task 5: Render kiểm chứng và tinh chỉnh mặc định

**Files:** test `tests/python/dasktoon_finish_render_test.py` (CMake); chỉnh giá trị mặc định và style trong
`settings.py`, `styles.py` sau khi xem ảnh.

- [ ] Test (EEVEE nền, ảnh nhỏ, cảnh mẫu): mỗi lớp bật riêng đổi ảnh đúng hướng (không khí, glow, vignette, gradient,
  màu bóng, nét cọ, hậu cảnh mềm); Tổng = 0 như khi tắt.
- [ ] Render nhân vật mẫu với từng style, xem và chỉnh. Commit: `test: the illustration finish layers change a render
  as they should`.

## Task 6: Ảnh, báo cáo, kiểm tra

- [ ] Ảnh (en, vi): `40_finish_panel`, `41_finish_before_after`, `42_finish_camera_view`; công cụ
  `tools/dasktoon_finish_screenshots.py`.
- [ ] Toàn bộ suite; báo cáo `docs/superpowers/reports/2026-10-13-dasktoon-illustration-finish-report.md`; ledger,
  memory.
