# Báo cáo: sắp xếp lại giao diện DaskToon (phần 1)

- Nhánh: `dasktoon-ui-reorganization`, tách từ `dasktoon-master` (92cadb7).
- Spec: `docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md`
- Kế hoạch: `docs/superpowers/plans/2026-10-04-dasktoon-ui-reorganization.md` (13 task, chạy tự động, mỗi task một commit,
  chưa push).

## Tóm tắt

- Mọi tính năng DaskToon đã rời thanh bên N của 3D Viewport và các tab Render, Light. Mỗi tính năng nằm ở chỗ Blender vẫn
  đặt loại việc đó: Object Data, Shape Keys, menu Add, menu ⌄ của slot material, menu File.
- Đã bỏ các panel, nút và lệnh không có tác dụng, lặp lại chức năng của Blender, hoặc bị hỏng.
- Mọi chữ của DaskToon giờ là tiếng Anh, viết theo kiểu Blender và không có emoji.
- Khi chọn Preferences › Interface › Language = Tiếng Việt, giao diện hiện tiếng Việt. Bảng dịch có 791 mục, kể cả tên
  node, ô và thuộc tính của các node DaskToon viết bằng C++.
- Danh sách ngôn ngữ chỉ còn Automatic, English và Tiếng Việt.
- Light Bleed (0.70) và Hand Wobble (0.15) của outline là giá trị cố định, tự áp dụng.
- Hướng Sun của các node tự cập nhật theo Sun trong scene, kể cả khi Sun có animation. Không cần nút hay driver.
- Bản cài được đồng bộ với repo bằng `tools/dasktoon_sync_build.py`. Script chép file mới và xóa các file cũ không còn
  trong repo.

## Tìm ở đâu

| Tính năng | Trước | Bây giờ |
|---|---|---|
| Bóng mặt (Face Shading) | Thanh bên › DaskToon › Bóng mặt (+ Nâng cao) | Properties › Object Data › **Face Shading**. Panel hiện cả khi đang chọn khối trứng. |
| VRM, ARKit, Shape Axis | Thanh bên › tab Shape Axis và tab ARKit | Properties › Object Data › Shape Keys, 4 panel con: **Expression Sets**, **Expression Tools**, **Expression Preview**, **Controllers** |
| Zero All, Mirror (X-Axis) | Nút DaskToon | Lệnh có sẵn của Blender trong panel Shape Keys: **Flip** (Mirror Shape Key) trong menu ⌄; nút **✕** cuối hàng **Relative** (Clear Shape Keys) đưa mọi giá trị về 0. Expression Preview cũng có nút **Clear Values** |
| Hiệu ứng anime | Thanh bên › Anime Visual Effects | 3D Viewport › Add (Shift+A) › **Anime Effect**, chia nhóm Impact và Atmosphere. Thông số chỉnh trong Adjust Last Operation |
| Gộp material | Thanh bên › Material Optimizer | Properties › Material › menu ⌄ cạnh danh sách slot › **Combine Materials**. **Restore Original Slots** chỉ hiện khi có slot để khôi phục |
| Dự án | Thanh bên › Dự án | File › **DaskToon Project**: New Project, Open Project, Open Recent. Khi đang mở dự án có thêm Models, Export This Model, Reinstall Shaders và Open Project Folder |
| Outline | Properties › Material › DaskToon Outline, và trên node | Chỉ trên node Anime BSDF / Dask Cel. Material dùng outline kiểu cũ có lệnh **Remove DaskToon Outline** trong menu ⌄ của slot. **Prepare Outline for Games** tìm bằng F3 |
| Hướng Sun cho node | Nút Sync Sun (3 chỗ) | Tự động, cả khi Sun có animation |
| Engine Export, Shading Style, menu node DaskToon | — | Giữ nguyên chỗ cũ |

## Ảnh chụp

Ảnh chụp từ DaskToon với một cảnh mẫu: đầu nhân vật có Face Shading, bộ biểu cảm VRM 0.x, các controller do Auto Setup
tạo và một dự án tạm. Bản giao diện tiếng Việt có cùng tên file trong thư mục `ui-reorganization/vi/`. Các panel con của
Shape Keys mặc định đóng; trong ảnh chúng được mở sẵn.

**Face Shading**, cuối tab Properties › Object Data của mesh:

![Face Shading trong Object Data](ui-reorganization/en/01_face_shading.png)

Cùng panel khi đang chọn khối trứng:

![Face Shading của khối trứng](ui-reorganization/en/02_face_shading_proxy.png)

**Shape Keys › Expression Sets và Expression Tools.** Nút **✕** cuối hàng Relative là Clear Shape Keys của Blender:

![Expression Sets và Expression Tools](ui-reorganization/en/03_shape_keys_sets_tools.png)

**Shape Keys › Expression Preview:**

![Expression Preview](ui-reorganization/en/04_shape_keys_preview.png)

**Shape Keys › Controllers:**

![Controllers](ui-reorganization/en/05_shape_keys_controllers.png)

**Menu ⌄ của Shape Keys** (Shape Key Specials của Blender). **Flip** là lệnh Mirror Shape Key:

![Shape Key Specials](ui-reorganization/en/06_shape_key_specials.png)

**Outline và Shading Style trên node Anime BSDF** (Shader Editor). Bật ô Outline thì hiện Outline Mode, Outline Width,
Outline Color và Outline Lighting Mix. Ở chế độ Ramp có menu Style:

![Outline trên node](ui-reorganization/en/07_outline_on_node.png)

**3D Viewport › Add (Shift+A) › Anime Effect:**

![Add › Anime Effect](ui-reorganization/en/08_add_anime_effect.png)

**File › DaskToon Project**, khi đang mở dự án:

![File › DaskToon Project](ui-reorganization/en/09_file_dasktoon_project.png)

**Properties › Material › menu ⌄ cạnh danh sách slot.** Restore Original Slots hiện ra sau khi đã gộp:

![Menu slot material](ui-reorganization/en/10_material_slot_menu.png)

## Đã bỏ và vì sao

| Đã bỏ | Lý do |
|---|---|
| Các panel DaskToon trong tab Render, nhóm cài đặt `scene.dasktoon_engine`, hai lệnh Setup Lighting và Setup Line Art | Các thanh trượt không có tác dụng (DASKTOON_ANIME là EEVEE đổi tên). Line Art của Grease Pencil bị bỏ theo yêu cầu |
| Panel DaskToon trong tab Light | Lặp lại thuộc tính đèn của EEVEE dưới tên khác |
| Light Groups | Chỉ liệt kê đèn, không gán nhóm nào cho shader |
| DaskToon Suite, Anime Shader Nodes, Activate Engine | Engine chọn ở tab Render; nút "Apply Basic Toon Material" bị hỏng; chèn node đã có trong Shader Editor › Add |
| Preset anime, lệnh chèn node, Sync Sun, node group Python kiểu cũ | Preset làm trực tiếp trên node; Sync Sun được thay bằng tự đồng bộ |
| Fix Anime Face Normals, Reset Normals, Normal Lines, panel Nâng cao | Face Shading thay thế. Blender đã có Clear Custom Split Normals Data và overlay hiện normal |
| Panel DaskToon Outline trong tab Material | Outline đã chỉnh trên node |
| Mục "DaskToon: Spherize Face Normals" trong Edit Mesh › Normals | Gọi tới lệnh đã bỏ |
| Zero All Shape Keys, Mirror Shape Key của DaskToon | Trùng lệnh của Blender |
| Bộ lọc danh mục và ô tìm kiếm của Controllers, preset auto setup "ARKit 52", nút X cạnh từng thanh trượt | Bộ lọc và ô tìm không lọc gì; preset ARKit 52 không có mã xử lý; nút X đặt lại cả nhóm chứ không riêng thanh trượt đó |
| 48 ngôn ngữ ngoài English và Tiếng Việt | Theo yêu cầu: chỉ giữ Anh và Việt |

## Lỗi có sẵn phát hiện khi chuyển chỗ, đã sửa

- **File › DaskToon Project chưa từng hiện ra.** Lớp menu thiếu `bl_idname`, nên lúc vẽ mục này bị lỗi và Blender lặng lẽ
  bỏ qua.
- **Nút HUD của Shape Axis chỉ chạy được khi bấm từ 3D Viewport.** Bấm ở chỗ khác thì báo "View3D not found". Giờ bấm ở
  Properties thì HUD mở trong 3D Viewport của cùng cửa sổ, và bấm lần nữa thì đóng (trước đây bấm lần hai lại mở thêm
  một HUD).
- **Material link từ thư viện giữ Light Bleed 0.25 cũ khi export.** Giờ export luôn ghi giá trị cố định, nên Unity khớp với
  Blender.
- **Kiểm tra bản cài dùng `filecmp` cho kết quả sai 4 lần trên 5.** `filecmp` coi hai file là giống nhau khi trùng kích
  thước và thời điểm sửa. Giờ so từng byte.
- **Menu Anime Effect (và panel cũ trước đó) vẽ lỗi ở mục Fire Embers.** Icon `FIRE` không có trong Blender 5.2, nên
  Blender ngừng vẽ ở đó và hai mục cuối không hiện. Lỗi này lộ ra khi chụp ảnh giao diện thật; test cũ dùng layout giả
  nên không bắt được. Đã đổi icon và thêm test kiểm mọi tên icon của DaskToon.

## Kiểm thử

- Toàn bộ 30 mục test DaskToon trong `tests/python/CMakeLists.txt`: 244 test, tất cả OK, chạy lại sau lượt sửa cuối.
  Riêng shading baseline chạy khoảng 6 phút.
- Test mới của phần này:
  - bản cài khớp repo;
  - danh sách ngôn ngữ;
  - panel và lệnh đã bỏ không còn đăng ký;
  - không còn panel DaskToon nào ở thanh bên hay tab Render;
  - bản dịch: mọi chữ hiển thị của mọi file DaskToon đều có bản dịch, chữ gốc là tiếng Anh không emoji, không có chữ ghép
    lúc chạy;
  - tên node, ô và thuộc tính của các node C++ đều có bản dịch;
  - tự đồng bộ Sun;
  - Light Bleed và Hand Wobble cố định;
  - các menu và panel mới (Anime Effect, gộp material, 4 panel Shape Keys, HUD, File › DaskToon Project).
  - mọi tên icon trong bảng Anime Effect và trong các `icon=` của DaskToon đều có trong Blender.
- Unity 6 (6000.5.4f1): `dasktoon_unity_render_test.py` OK và `dasktoon_unity_model_test.py` OK.
  - Test render so 20 ca giữa DaskToon và Unity. Cel và diffuse lệch tối đa 0.025, dưới ngưỡng 0.03.
  - Hai ca outline dùng Light Bleed 0.70 và Hand Wobble 0.15 cố định:

    | Ca | Lệch bề rộng (ngưỡng 1.5 px) | Lệch màu (ngưỡng 0.08) | Nét mỏng nhất |
    |---|---|---|---|
    | outline_custom | 1.5 px | 0.0124 | 2.0 px |
    | outline_harmonic | 1.5 px | 0.004 | 2.0 px |

  - Lần chạy đầu, Unity báo lỗi biên dịch ngay trong gói URP. Project test nằm trong `%TEMP%\dasktoon_unity_test` và đã
    mất phần lớn file `.meta` trong `Library/PackageCache`, nhiều khả năng do Windows dọn file tạm. Sau khi xóa thư mục
    `Library` của project test để Unity import lại, cả hai test đều qua. Lỗi này không liên quan tới thay đổi của nhánh.
- Ảnh duyệt (`tests/python/dasktoon_visual_review.py`):
  - Simple và 5 kiểu đổ bóng có sẵn hiển thị đúng ở cả 3 góc Sun.
  - Hàng outline cuối có viền liền, không đứt nét ở cả 3 góc Sun.

## Duyệt cuối

Tôi tự duyệt toàn bộ mã của nhánh, không dùng người duyệt riêng, vì phiên làm việc này không được tạo agent khi bạn chưa
yêu cầu. Người viết tự duyệt thì dễ bỏ sót hơn người duyệt mới, nên bạn quyết định có cần duyệt thêm trước khi merge hay
không.

Hai lỗi mức Important đã sửa. Mỗi lỗi có test thấy đỏ trước khi sửa, xanh sau khi sửa, rồi chạy lại toàn bộ test:

1. **Sun có animation không còn kéo theo bóng mặt khi phát hoặc render animation.** Khi đổi khung hình, Blender chạy
   handler `frame_change_post` chứ không chạy `depsgraph_update_post`, trong khi driver Sync Sun cũ chạy ở mọi khung.
   Đã thêm handler cho lúc đổi khung. Handler đọc Sun đã đánh giá, nên đúng cả khi render. Khi hướng Sun không đổi, nó
   chỉ tốn một phép so sánh. Test: `test_animated_sun_turns_materials_on_frame_change`.
2. **HUD mở từ Properties nhận cả sự kiện của editor khác.** Ví dụ bấm I khi chuột đang trên một ô ở Properties thì HUD
   chèn keyframe cho tay cầm của nó thay vì cho ô đó; chuột phải ở đâu cũng đóng HUD và làm mất cú bấm. Giờ HUD chỉ xử
   lý sự kiện khi chuột nằm trong 3D Viewport của nó, trừ lúc đang kéo. Test:
   `test_hud_leaves_events_over_other_editors_alone`.

Việc nhỏ để lại (chưa sửa):

- Nếu đóng 3D Viewport đang chạy HUD, HUD bị lỗi và vẫn coi là đang mở cho tới khi bấm nút một lần nữa.
- Chưa có test kiểm mỗi câu dịch giữ đủ các chỗ `%s`/`%d` của câu gốc. Tôi đã kiểm bằng tay: 791 mục đều khớp.
- `bl_ui/__init__.py` vẫn tự thêm DASKTOON_ANIME vào các panel EEVEE, trùng việc của `engine_dasktoon_anime.register()`.
  Không gây lỗi.
- Độ lệch bề rộng outline với Unity đúng bằng ngưỡng 1.5 px. Test vẫn qua nhưng không còn khoảng dư.
- Project Unity dùng cho test nằm trong `%TEMP%`, nơi Windows có thể dọn mất file. Có thể đặt biến
  `DASKTOON_UNITY_PROJECT` trỏ sang thư mục khác.

## Quyết định tôi tự đưa ra (kèm cái giá nếu sai)

**Lúc lập kế hoạch**

1. Bảng dịch không viết trong kế hoạch mà soạn khi làm. Test phủ bản dịch là tiêu chí xong. Cái giá nếu sai: không có, vì
   test bắt buộc.
2. Mỗi mục dịch đăng ký cho cả ngữ cảnh "*" và "Operator". Cái giá: một chữ có thể dùng cách dịch của tên lệnh ở chỗ cần
   danh từ.
3. Chữ nào vi.po của Blender đã dịch thì giữ cách dịch của Blender. Cái giá: vài từ chung dùng chữ của Blender.
4. Tự viết bộ trích chữ bằng `ast`, vì bản build không có `bl_i18n_utils`. Cái giá: một mẫu chữ bộ trích bỏ sót sẽ không
   được test.
5. Script đồng bộ xóa `dasktoon_uv_optimizer.py` khỏi bản cài, vì master không nạp file này; nó vẫn nằm ở nhánh
   `feature/uv-optimizer`. Cái giá: phải chép lại khi làm nhánh đó.
6. Tên ô vào của modifier Face Shading (Coverage, Falloff…) không dịch, vì đó là tên socket của node group (dữ liệu người
   dùng). Panel Face Shading đã có nhãn dịch. Cái giá: modifier panel vẫn tiếng Anh.
7. Panel Face Shading nằm cuối tab Object Data. Cái giá: phải cuộn thêm một chút.
8. Nhóm trạng thái ARKit theo đúng danh sách thật: mắt 14, hàm và miệng 27, lông mày 5, má, mũi và lưỡi 6. Cách cắt cũ đếm
   nhầm browDownLeft vào nhóm miệng.

**Lúc làm**

9. Task 1: thay `filecmp` bằng so từng byte (xem phần lỗi ở trên). Cái giá: không có.
10. Task 3: bỏ cả mục menu trong Edit Mesh › Normals gọi lệnh đã xóa. Chỉ chuyển `_sync_outline_socket` sang module
    outline; `_sync_outline_node_subgraph` chỉ phục vụ lệnh preset đã bỏ nên bỏ theo. Cái giá: không có.
11. Task 6: export tự ghi Light Bleed và Hand Wobble cố định, không đọc từ material phụ. Material phụ link từ thư viện
    không sửa được, nên vẫn giữ giá trị đã lưu. Cái giá: không có.
12. Task 6: test "chữ gốc là tiếng Anh" quét mọi chuỗi trong file, không chỉ chỗ hiển thị. Cái giá: không có.
13. Task 7: docstring của lớp Panel được Blender dùng làm mô tả panel, nên ghi chú cho lập trình viên chuyển thành comment.
    Cái giá: không có.
14. Task 8: thêm hai test chạy thật lệnh gộp và khôi phục material, vì module chưa có test nào chạy lệnh. Mục độ phân giải
    ghi "1024 × 1024", đọc giống nhau ở mọi ngôn ngữ. Cái giá: không có.
15. Task 9: kế hoạch đọc tên hiệu ứng qua `bl_rna` của lớp operator, nhưng trong Blender 5.2 chỗ đó không có thuộc tính của
    operator. Đổi sang `get_rna_type()`. Thêm test tạo đủ 11 hiệu ứng. Cái giá: không có.
16. Task 10: sửa nút HUD để chạy được từ Properties (xem phần lỗi ở trên). Cái giá: đường mở HUD từ Properties có unit
    test, nhưng chưa được thử trên giao diện thật.
17. Task 10: bỏ phần thừa của Controllers (xem bảng "Đã bỏ"). Convert Naming nay mở hộp thoại để chọn kiểu chuyển. Cái giá:
    file .blend cũ giữ hai thuộc tính không còn dùng dưới dạng dữ liệu thô, vô hại.
18. Task 10: nhóm ARKit thứ tư tên "Cheeks, Nose & Tongue", vì tongueOut thuộc nhóm này. Panel Shape Keys dùng đúng thuật ngữ
    tiếng Việt của Blender (hình mẫu, khung khóa, Cổng Nhìn 3D). Chữ của thẻ tham chiếu tự xuống dòng theo bề rộng
    panel. Cái giá: chỉ là cách chữ.
19. Task 11: khai báo `bl_idname` cho ba menu dự án (xem phần lỗi). Menu không hiện đường dẫn project Unity như panel cũ;
    Open Project Folder và Engine Export vẫn cho thấy. Cái giá: thiếu một dòng chữ.
20. Task 12: test node quét cả nhánh menu DaskToon Manga, và kiểm cả nhãn của menu. Cái giá: không có.
21. Task 12: không giữ bảng tên cũ cho Shading Style tiếng Việt. Không chỗ nào lưu tên style có sẵn: áp style chỉ ghi dải
    màu, còn style tự lưu vẫn giữ tên riêng. Cái giá: script nào gọi `get_style("Anime 3 tông")` sẽ nhận None.
22. Task 12: tên riêng giữ nguyên trong tiếng Việt: Anime BSDF, Manga BSDF, DaskToon Anime, DaskToon Manga, Manga.
    README.txt của Engine Export viết theo ngôn ngữ giao diện lúc export. Cái giá: chỉ là cách chữ.

## Việc bạn cần làm

1. Sau mỗi lần build, đồng bộ bản cài bằng script mới:
   `python tools/dasktoon_sync_build.py <thư mục 5.2 của bản build>`
   Không dùng `cp -r` nữa, vì cách đó không xóa file cũ.
2. Để xem bản dịch, chọn Preferences › Interface › Language = Tiếng Việt.
3. Mở DaskToon và thử bằng tay nút **Open Viewport HUD** trong Shape Keys › Controllers, vì test không chạy được giao diện
   thật.
4. Chọn cách xử lý nhánh: merge vào `dasktoon-master`, tạo PR, hoặc giữ nguyên. Nhánh chưa được push.
5. Phần 2 (dự án thay hẳn cách quản lý file cũ, ở màn hình chào và menu File) cần một spec riêng.
