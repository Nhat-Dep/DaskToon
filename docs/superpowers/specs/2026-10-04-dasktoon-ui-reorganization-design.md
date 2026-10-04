# DaskToon: sắp xếp lại giao diện (Phần 1)

- Ngày: 2026-10-04
- Trạng thái: thiết kế đã được duyệt trong chat (3 phần và hai chỉnh sửa về Material, Outline)
- Nhánh: `dasktoon-ui-reorganization`, tách từ `dasktoon-master` (`92cadb7926e`)
- Phần 2 (sau): Dự án thay cho quản lý file (màn hình chào, menu File). Không thuộc spec này.

## 1. Mục tiêu

Người dùng thấy giao diện DaskToon sắp xếp không hợp lý và có nhiều phần thừa. Kiểm kê ngày 2026-10-04 cho thấy:

- Tính năng rải ở 3 tab thanh bên viewport (DaskToon, ARKit, Shape Axis), 8 panel tab Render, tab Material, tab Light và
  các menu.
- "DaskToon Anime Engine" là EEVEE đổi tên (`dasktoon_anime_engine.cc` dựng `eevee::Instance`). Các thanh trượt trong 5
  panel Render của nó (Cel-Shading, Line Art, Hard Shadows, Manga Screen-tones, Animation Stepping) không được code nào đọc.
- Nút hỏng ("Apply Basic Toon Material" gọi operator không tồn tại), nút trùng (preset ở 2 nơi, "Sync Sun" ở 3 nơi,
  "Add Line Art" ở 2 nơi, "Zero All" ở 3 nơi), panel lặp lại cài đặt EEVEE, Light Groups không có tác dụng.
- Bản cài (thư mục build) còn file không có trong repo, trong đó một panel Light Groups cũ đè lên panel mới.

Kết quả mong muốn:

1. **Mỗi tính năng nằm đúng nơi Blender vốn đặt loại việc đó**: thiết lập theo dữ liệu nằm trong tab Properties của dữ
   liệu đó, tạo đối tượng nằm trong menu Add, việc với file nằm trong menu File, việc với node nằm trong Shader Editor.
   Thanh bên viewport không còn tab DaskToon.
2. **Không còn nút không có tác dụng, nút hỏng, nút trùng.**
3. **Chữ gốc tiếng Anh; chọn Tiếng Việt trong Preferences thì DaskToon hiện tiếng Việt**; danh sách ngôn ngữ chỉ còn
   Automatic, English, Tiếng Việt.
4. **Bản cài khớp đúng repo**, và có cách đồng bộ không để sót file.

## 2. Phạm vi

**Trong phạm vi**: các module Python giao diện của DaskToon trong `scripts/startup` và `scripts/modules/dasktoon_export`,
bản dịch tiếng Việt, `locale/languages` và `locale/po`, script đồng bộ bản cài, test.

**Ngoài phạm vi**:
- Phần 2: dự án thay cho quản lý file. Trong lúc chờ, menu File › DaskToon Project giữ mọi chức năng của panel Dự án.
- Sửa C++/GLSL, shader Unity, tên engine "DaskToon Anime Engine".
- Làm thật các tính năng chỉ có thanh trượt giả (bước hoạt hình, screentone…): nếu cần sẽ là dự án riêng.
- Nhánh `feature/uv-optimizer` của người dùng.

## 3. Vị trí mới của từng tính năng

| Tính năng | Hiện ở | Vị trí mới |
|---|---|---|
| Bóng mặt (Face Shading) | Thanh bên › DaskToon › Bóng mặt (+ Nâng cao) | Properties › Object Data của mesh: panel `DATA_PT_dasktoon_face_shading` "Face Shading". Khi khối trứng (Empty) đang chọn, tab Object Data của nó hiện cùng panel cho mesh dùng khối trứng đó |
| ARKit, VRM, Shape Axis | Thanh bên › tab ARKit và tab Shape Axis (3 panel) | Properties › Object Data › Shape Keys: 4 panel con `bl_parent_id = "DATA_PT_shape_keys"`, mặc định đóng: **Expression Sets**, **Expression Tools**, **Expression Preview**, **Controllers** (§3.2) |
| Hiệu ứng anime | Thanh bên › DaskToon › Anime Visual Effects | Viewport › Add (Shift+A) › menu con **Anime Effect** (11 mục, chia nhóm Impact và Atmosphere); thông số chỉnh trong Adjust Last Operation |
| Gộp material | Thanh bên › DaskToon › Material Optimizer | Properties › Material › menu ⌄ cạnh danh sách slot (`MATERIAL_MT_context_menu`): **Combine Materials**, **Restore Original Slots** (chỉ hiện khi có gì để khôi phục) |
| Dự án | Thanh bên › DaskToon › Dự án và File › Dự án DaskToon | Chỉ File › **DaskToon Project** ▸: New, Open, Open Recent ▸; khi đang mở dự án: danh sách model (mở), Export This Model, Reinstall Shaders, Open Project Folder |
| Engine Export | File › Export › Engine Export | Giữ nguyên |
| Shading Style, node DaskToon | Shader Editor (menu Shading Style, Add › DaskToon Anime) | Giữ nguyên |
| Outline | Node Anime BSDF / Dask Cel và Properties › Material › DaskToon Outline | Chỉ trên node (bật/tắt, Width, Color, Lighting Mix, Outline Mode). Light Bleed và Hand Wobble tự động (§4) |
| Hướng Sun cho node | Nút "Sync Sun" (3 nơi) gắn driver kiểu script | Tự đồng bộ (§5) |

### 3.1 Panel Face Shading

Giữ nguyên nội dung panel bóng mặt hiện có (Set Up Face Shading; Select Proxy; 4 thanh trượt; Fit Proxy; Remove Face
Shading), chỉ chuyển chỗ và đổi chữ (§6). Gợi ý "mesh còn custom normal cũ" gọi lệnh có sẵn của Blender
`mesh.customdata_custom_splitnormals_clear` ("Clear Custom Split Normals Data"). Mục *Nâng cao* bị bỏ (§3.3).

### 3.2 Bốn panel con của Shape Keys

| Panel con | Nội dung (lấy từ 3 panel cũ) |
|---|---|
| Expression Sets | Khởi tạo VRM 0.x / VRM 1.0; trạng thái ARKit 52 (đếm theo vùng); Synthesize ARKit 52 from VRM; Initialize 52 ARKit Placeholders; Convert Naming |
| Expression Tools | Split Active (L / R); Bake Current Expression to New Key; Remove Empty Keys |
| Expression Preview | Thẻ tham chiếu VRM và ARKit với nút thử trên model; Blink Test, Speech Loop |
| Controllers | Toàn bộ Shape Axis: HUD, Reset Group / Reset All / Keyframe, auto setup (VRM/VRoid, VRM Emotions, AIUEO, Blink, Ears & Tail), danh sách nhóm và mapping, Generate 3D Rig Board |

Các nút "Zero All" / "Reset" (3 nơi) và "Mirror (X-Axis)" bị bỏ cùng operator `dasktoon.vrm_zero_all_shapes`,
`dasktoon.vrm_mirror_shape_key`: menu ⌄ của Shape Keys đã có **Clear Shape Key Values** và **Mirror Shape Key** của
Blender. Thẻ tham chiếu dùng lệnh Clear Shape Key Values của Blender để trả về.

### 3.3 Bỏ hẳn

| Bỏ | Lý do / thay bằng |
|---|---|
| Tab Render: `DASKTOON_RENDER_PT_header`, `_cel_shading`, `_lineart`, `_shadows`, `_manga`, `_animation`, `_presets`, nhóm thuộc tính `scene.dasktoon_engine`, operator `dasktoon.setup_lighting`, `dasktoon.setup_lineart` | Thanh trượt không có tác dụng; Line Art bị bỏ theo người dùng; Add › Light › Sun có sẵn. **Giữ** đoạn code thêm `DASKTOON_ANIME` vào `COMPAT_ENGINES` của các panel EEVEE |
| Tab Light: `DATA_PT_DaskToon_light_npr` | Lặp lại thuộc tính đèn EEVEE với tên khác |
| Light Groups: `scripts/startup/dasktoon_light_groups.py` | Chỉ liệt kê đèn, không gán nhóm cho shader |
| `properties_dasktoon.py` (DaskToon Suite, Anime Shader Nodes, `dasktoon.activate_engine`) | Chọn engine ở tab Render; nút hỏng; chèn node có ở Shader Editor › Add |
| `dasktoon_anime_nodes.py` (preset `dasktoon.setup_anime_preset`, `node.dasktoon_add_anime_node`, `dasktoon.link_sun_direction`, các node group Python kiểu cũ) | Preset: làm trong node editor (người dùng); chèn node: Shader Editor › Add; Sync Sun: tự động. Hai hàm `_sync_outline_socket`, `_sync_outline_node_subgraph` mà outline và upgrade đang dùng được chuyển sang `dasktoon_outline.py` |
| `dasktoon_face_normals.py` (Fix Anime Face Normals, Reset Normals, Normal Lines) và panel *Nâng cao* | Face Shading thay thế; Blender có sẵn Clear Custom Split Normals Data và nút hiện normal (overlay) |
| Panel `MATERIAL_PT_dasktoon_outline`, operator `dasktoon.outline_toggle_material` | Outline làm trên node. Lệnh `dasktoon.outline_prepare_game_data` giữ lại (tìm qua F3), vì Engine Export đã tự gọi |
| Panel thanh bên `VIEW3D_PT_dasktoon_anime_fx`, `DASKTOON_PT_material_combiner`, `VIEW3D_PT_dasktoon_project`, `DASKTOON_PT_face_shading`, `DASKTOON_PT_face_shading_advanced`, `DASKTOON_PT_shape_axis_panel`, `DASKTOON_PT_vrm_toolset_panel`, `DASKTOON_PT_arkit_studio_panel` | Chuyển chỗ như bảng §3 |

## 4. Outline: Light Bleed và Hand Wobble tự động

- Hai thông số mô phỏng nét mực thật (mảnh đi ở phía được chiếu sáng, dao động như ngòi bút). Chúng được **cố định** ở
  mức mặc định đang dùng của node Dask Outline: **Light Bleed = 0.70**, **Hand Wobble = 0.15**. Không còn nút chỉnh.
- Bộ đồng bộ outline ghi hai giá trị này vào material `<tên>.Outline` của mọi outline và dùng chúng khi dựng vỏ Geometry
  Nodes. Engine Export đọc từ material đó như hiện tại, nên Unity nhận đúng hai giá trị; shader Unity không đổi.
- File cũ đã chỉnh tay hai giá trị: được đưa về mức chuẩn ở lần đồng bộ đầu tiên khi mở file.
- **Outline cho material không có node DaskToon** (kiểu đánh dấu `mat["dasktoon_outline"]`): không còn bật được từ giao
  diện. File cũ vẫn hiện outline như trước. Menu ⌄ của slot hiện **Remove DaskToon Outline** chỉ khi material đang chọn
  có dấu đó, để tắt được.

## 5. Hướng Sun tự đồng bộ

- Module mới `bl_ui/dasktoon_sun_sync.py`: handler `depsgraph_update_post` (và sau khi mở file) lấy Sun đầu tiên đang
  hiện trong scene (cùng quy tắc `find_sun` của outline), tính hướng như lệnh cũ (`matrix_world.to_3x3() @ (0, 0, 1)`),
  và ghi vào mọi ô vào **"Light Vector" chưa nối dây** của node trong mọi material (hiện có ở `ShaderNodeAnimeFaceShadow`).
- Chỉ ghi khi giá trị khác thật (sai khác > 1e-6) và chỉ khi Sun hoặc material thay đổi, để không biên dịch lại shader
  liên tục. Không dùng driver; xóa driver cũ do "Sync Sun" tạo trên các ô đó (driver kiểu script cần bật Auto Run).
- Không có Sun: không ghi gì.

## 6. Tên gọi và bản dịch

### 6.1 Chữ gốc tiếng Anh

- Mọi chữ hiển thị của DaskToon (tên panel, menu, lệnh, mô tả, tên thuộc tính, mục enum, nhãn trong `layout`, thông báo
  `report`, thông báo lỗi, báo cáo Engine Export và `README.txt`) viết bằng tiếng Anh, theo kiểu Blender: viết hoa chữ
  đầu mỗi từ ở tên, câu thường ở mô tả, **không emoji**, dùng icon có sẵn của Blender.
- Mã định danh giữ nguyên (`dasktoon.*`, tên class trừ các class bị bỏ/đổi chỗ, tên thuộc tính lưu trong file), để phím
  tắt, script và file cũ vẫn dùng được.
- Tên chính: panel *Face Shading*, *Expression Sets*, *Expression Tools*, *Expression Preview*, *Controllers*; menu
  *DaskToon Project*, *Anime Effect*, *Shading Style*; lệnh *Set Up Face Shading*, *Select Proxy*, *Fit Proxy*,
  *Remove Face Shading*, *Combine Materials*, *Restore Original Slots*, *Remove DaskToon Outline*; thanh trượt
  *Coverage*, *Falloff*, *Keep Nose Shadow*, *Keep Chin Shadow*.

### 6.2 Bản dịch tiếng Việt

- Một module `bl_ui/dasktoon_translations.py` chứa bảng `{"vi_VN": {(ngữ cảnh, chữ gốc): chữ Việt}}`, đăng ký bằng
  `bpy.app.translations.register` khi khởi động.
- Phủ: mọi chữ ở §6.1, và cả **tên node, tên ô, tên thuộc tính, mục enum của các node DaskToon** (định nghĩa trong C++,
  vd. Anime BSDF, Shadow Color, Outline Mode).
- Đúng **ngữ cảnh dịch** của Blender: tên lệnh dùng ngữ cảnh `Operator`, phần lớn còn lại dùng `*`; ô node và thuộc tính
  có ngữ cảnh riêng thì dùng đúng ngữ cảnh đó.
- Thông báo động (có biến) dịch mẫu trước rồi mới điền biến (`pgettext_rpt` / `pgettext_tip`).
- Hiện tiếng Việt khi Preferences › Interface › Language = Tiếng Việt (với các mục Translate đang bật như mặc định).

## 7. Danh sách ngôn ngữ

- `locale/languages` chỉ giữ 3 dòng: `0:Automatic`, `1:English (US)`, `41:Vietnamese - Tiếng Việt` (giữ nguyên ID và
  phần chú thích đầu file).
- Xóa 48 file `locale/po/*.po` trừ `vi.po`. Bản build tự biên dịch mọi `.po` trong thư mục đó nên lần build sau chỉ còn
  tiếng Việt.
- Bản cài hiện tại: thay `datafiles/locale/languages` và xóa 48 thư mục ngôn ngữ tương ứng trong `datafiles/locale`.
- Cái giá: cập nhật từ Blender gốc sẽ báo xung đột ở các `.po` đã xóa; cách xử lý là giữ việc xóa.

## 8. Bản cài khớp repo

- Script `tools/dasktoon_sync_build.py <thư mục 5.2 của bản cài>`: làm cho `scripts/startup`, `scripts/modules` và
  `datafiles/locale/languages` của bản cài giống hệt repo (chép file mới/khác, xóa file `.py` và thư mục không có trong
  repo, bỏ qua `__pycache__`); có `--dry-run` liệt kê trước. Không đụng các thư mục khác (addons, datafiles khác).
- Lần đầu chạy sẽ xóa các file sót đã thấy: `goo_engine_light_groups.py`, `bl_app_templates_system/DaskToon_Anime`,
  `bl_app_templates_system/Unity_Engine`, `bl_ui/engine_unity.py`, `bl_ui/unity_shader_graph.py`,
  `bl_ui/dasktoon_uv_optimizer.py` (file này vẫn còn trong nhánh `feature/uv-optimizer`).
- Từ nay đồng bộ bằng script này thay cho `cp -r`.

## 9. File .blend cũ

| Dữ liệu cũ | Xử lý |
|---|---|
| `scene.dasktoon_engine` (cài đặt Render giả) | Không đăng ký nữa; dữ liệu nằm im trong file, không lỗi |
| Light Bleed / Hand Wobble đã chỉnh tay | Đưa về 0.70 / 0.15 khi đồng bộ outline |
| Material đánh dấu outline không có node DaskToon | Vẫn có outline; tắt bằng Remove DaskToon Outline |
| Driver "Sync Sun" trên ô Light Vector | Xóa và thay bằng tự đồng bộ |
| Dữ liệu Shape Axis, thẻ tham chiếu, ARKit/VRM | Giữ nguyên, chỉ giao diện chuyển chỗ |
| Node group Python kiểu cũ đã có trong file | Giữ nguyên trong file (không còn lệnh tạo mới) |
| Custom normal từ công cụ normal cũ | Panel Face Shading nhắc Clear Custom Split Normals Data |

## 10. Kiểm thử

**Headless trong DaskToon**:

| Nhóm | Nội dung |
|---|---|
| Vị trí | Mọi panel, menu, mục menu của DaskToon nằm đúng chỗ ở §3; không còn panel DaskToon nào ở thanh bên viewport (mọi tab), tab Render, tab Light; các class/operator ở §3.3 không còn đăng ký |
| Chức năng sau khi chuyển | Face Shading chạy từ panel mới (mesh và khối trứng); 4 panel con Shape Keys vẽ được; Add › Anime Effect có đủ 11 mục và tạo được hiệu ứng; Combine / Restore trong menu ⌄ Material; menu File › DaskToon Project có đủ lệnh của panel Dự án cũ |
| Outline | Light Bleed / Hand Wobble luôn 0.70 / 0.15 (kể cả file cũ đã chỉnh); Remove DaskToon Outline chỉ hiện với material đánh dấu kiểu cũ |
| Sun | Xoay Sun làm đổi Light Vector chưa nối dây; ô đã nối dây không bị đụng; không ghi khi không đổi; driver cũ bị xóa |
| Bản dịch | Mọi chữ DaskToon (Python và tên node/ô DaskToon) có bản dịch; khi ngôn ngữ là `vi_VN`, hàm dịch của Blender trả đúng chữ Việt cho mẫu chữ từ từng loại (panel, lệnh, thuộc tính, ô node, thông báo) |
| Ngôn ngữ | `locale/languages` có đúng 3 mục; `locale/po` chỉ còn `vi.po` |
| Bản cài | Script khởi động trong bản cài trùng khớp repo (không file sót); script đồng bộ xóa file thừa và chép file mới (thử trên thư mục tạm) |
| Test cũ | Cập nhật các test đang kiểm chữ tiếng Việt sang chữ gốc tiếng Anh; toàn bộ test DaskToon xanh |

**Unity**: chạy lại bài so sánh render và bài nhập FBX; các ca outline dùng Light Bleed / Hand Wobble cố định.

## 11. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Chữ có bản dịch nhưng không hiện tiếng Việt vì sai ngữ cảnh dịch | Test bản dịch kiểm đúng chữ hiển thị theo từng loại |
| Bỏ nhầm thứ còn được dùng | Trước khi xóa, tìm mọi nơi gọi (grep) và giữ phần đang được dùng (vd. `_sync_outline_socket`); test vị trí và chức năng |
| Tự đồng bộ Sun gây biên dịch shader liên tục | Chỉ ghi khi giá trị đổi; test đếm số lần ghi |
| Xung đột khi cập nhật Blender gốc ở `.po` đã xóa | Ghi trong báo cáo; giữ việc xóa |
| Người dùng chưa quen chỗ mới | Báo cáo có bảng "tìm ở đâu" |

## 12. Nhật ký quyết định

| Quyết định | Nguồn |
|---|---|
| Làm lại toàn bộ; mỗi tính năng nằm đúng chỗ của nó trong Blender | Người dùng |
| Bỏ Grease Pencil Line Art; giữ FX, gộp material, Shape Axis | Người dùng |
| Chữ gốc tiếng Anh, bản dịch tiếng Việt qua cài đặt ngôn ngữ; chỉ giữ Automatic, English, Tiếng Việt | Người dùng |
| Chia 2 phần, làm sắp xếp giao diện trước | Người dùng |
| Giữ module theo tính năng, chỉ đổi chỗ gắn giao diện | Người dùng (theo đề xuất) |
| Bỏ Preset và Outline khỏi tab Material, làm trên node; gộp material vào menu ⌄ | Người dùng |
| Light Bleed 0.70 / Hand Wobble 0.15 tự động, không nút chỉnh | Người dùng (đề xuất mức cụ thể) |
| Vị trí từng tính năng, danh sách bỏ hẳn, đồng bộ Sun tự động, script đồng bộ bản cài | Đề xuất, người dùng duyệt |
