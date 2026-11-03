# Thử DaskToon dưới mắt người mới

Ngày 2026-11-03. Vai thử: người có mắt thẩm mỹ, biết vẽ, chưa từng dùng phần mềm đồ họa.

Cách làm: mở DaskToon trong cửa sổ thật, màn hình 1920×1080, cấu hình trắng tinh, giao diện tiếng Việt, rồi đi tìm từng việc
bằng menu như người mới. Nhân vật thử là nhân vật của bộ test, không phải model của người dùng.

Giới hạn: đây là tôi đóng vai, không phải người mới thật. Chưa thử: rê chuột đọc chú thích, dựng model từ đầu, hộp thoại xuất
file, bút vẽ bảng. Người thật chắc chắn sẽ vấp thêm chỗ khác.

## Kết luận

Tính năng đủ, nhưng không có chỗ nào nói "việc tiếp theo là gì". Tám việc chính nằm ở tám nơi khác nhau, vì quy tắc năm 2026-10-04
là "đặt đúng chỗ Blender vốn đặt": hợp với người đã biết Blender, không hợp với người mới.

Không nên dời hết mọi thứ. Nên biến bảng **Hướng dẫn** có sẵn thành trang chính: mở sẵn, mỗi bước có nút bấm thật, không kẹt vì
cảnh báo. Các nút cũ giữ nguyên chỗ, người đã quen không mất gì.

## Những chỗ người mới bị kẹt

| # | Chuyện xảy ra | Bằng chứng |
|---|---|---|
| 1 | Sau khi dựng khung, nhân vật đang chọn là bộ xương. Bấm thẻ Modeling hoặc UV Editing là vào thẳng chế độ sửa khớp, kéo chuột là hỏng xương | [ảnh](newcomer-walkthrough/modeling_after_rig.png) |
| 2 | Bấm vào một lưới rồi dựng khung: nút báo xong với 1 trên 6 lưới, không nhắc gì về 5 lưới còn lại. Phần Kiểm tra báo 13 chỗ như "Vai trái nằm ngoài thân", sai nguyên nhân | [ảnh](newcomer-walkthrough/rig_one_of_six.png) |
| 3 | Chưa chọn gì mà dựng khung: một bộ xương nhỏ hiện trong khối vuông, kèm lời dặn ba việc phải làm tay. Trong khi **Kiểm tra model** chưa chọn gì thì tự lấy mọi lưới đang hiện | Chạy thử, `rig_add_humanoid` |
| 4 | Người vẽ bấm thẻ Texture Paint rồi tô: không có nét nào, chỉ một dòng nhỏ dưới đáy "Phát hiện thấy thiếu Các UV, Nguyên Vật Liệu, Chất Liệu". **Bắt đầu tô vẽ** nằm ở thẻ Vật liệu › ⌄, và xám khi lưới chưa có vật liệu | [ảnh](newcomer-walkthrough/paint_first_stroke.png) |
| 5 | Hướng dẫn kẹt: đã dựng khung xong vẫn đứng ở bước 2, vì một cảnh báo không sửa được cũng tính là chưa xong. Bước 3 và 4 lại có dấu tích | [ảnh](newcomer-walkthrough/guide_stuck.png) |
| 6 | Bước 6 (Vật liệu) và 7 (Gắn khung), hai bước quan trọng nhất, không có nút, chỉ có chữ chỉ đường. Thao tác thì đã có sẵn | `dasktoon_guide/steps.py` |
| 7 | **Hướng dẫn**, phần làm riêng cho người mới, nằm ở thanh bên đang đóng; muốn mở phải biết phím N hoặc thấy mũi tên nhỏ | Thanh bên mặc định tắt |
| 8 | Lần mở đầu hỏi 5 mục gồm Bố Trí Phím, Chuột Lựa Chọn, Hành Động của phím cách, rồi vào thẳng khối vuông. Màn hình có **Dự án** chỉ hiện từ lần mở thứ hai | Chạy thử với cấu hình mới |

## Đường đi hiện tại của từng việc

Tính từ lúc nhân vật đã nằm trong cảnh.

| Việc | Đường đi | Ghi chú |
|---|---|---|
| Dùng shader | Chọn hết › thẻ Vật liệu › ⌄ › Dùng shader DaskToon cho mọi đối tượng đang chọn | Thẻ Vật liệu là icon thứ 14, không có chữ |
| Trải UV | Thẻ Vật liệu › ⌄ › Trải UV anime | Cùng menu ⌄ |
| Tô màu | Thẻ Vật liệu › ⌄ › Bắt đầu tô vẽ | Không nằm ở thẻ Texture Paint |
| Dựng khung | Chọn hết › Thêm › Khung Rối › Khung người anime | Không ai đoán ra "Khung Rối" |
| Biểu cảm | Bấm lưới › icon tam giác xanh › Hình Mẫu › Biểu cảm tự động | Có cả ở Rig anime, khoảng trang thứ ba |
| Hoạt họa | Thẻ Animation | Nhân vật nhỏ xíu, chưa phóng tới |
| Hoàn thiện tranh | Thẻ Cảnh (icon thứ 5) | |
| Xuất sang game | Tập Tin › Xuất Khẩu › mục thứ 8 trên 11 | Nằm giữa STL và glTF |

Con số về độ rối:

- 11 thẻ trên cùng, vẫn tiếng Anh khi giao diện tiếng Việt; luồng DaskToon chỉ cần 3 đến 4 thẻ.
- 14 icon không chữ ở cột Thuộc tính.
- 10 mục con của Rig anime đều mở sẵn, cuộn hơn ba màn hình mới hết.
- 20 dòng trong menu Tập Tin.

Thẻ Shading mở ra trình duyệt file đang trỏ vào thư mục tài liệu của máy, và nếu đang chọn bộ xương thì không có gì để làm.

## Đề xuất

### Nhóm 1: gỡ bẫy, không đổi cấu trúc

1. Bấm Modeling hoặc UV Editing khi đang chọn bộ xương thì đưa về lưới cơ thể, không vào sửa xương.
2. **Khung người anime**: chưa chọn gì thì lấy mọi lưới đang hiện, cùng quy tắc với **Kiểm tra model**. Chọn thiếu thì nói rõ còn
   bao nhiêu lưới chưa chọn.
3. Thêm **Bắt đầu tô vẽ** ngay trong thẻ Texture Paint, và nút tự tạo vật liệu nếu lưới chưa có.
4. Hướng dẫn chỉ dừng ở lỗi ✗, cảnh báo ⚠ không giữ chân. Thêm nút cho bước 6 và 7. Đổi bước 9 "Unity" thành "Xuất sang game" vì
   đã có cả Godot.
5. Sửa chữ sai hoặc cũ:
   - "A I U E O: nặn "a" hoặc dùng Miệng 2D": nay nút đã tự làm được khi miệng có khe môi.
   - "Sẵn sàng 0 trên 13: bấm một nút để thử" trong khi mọi nút đều xám.
   - Câu bị cắt "Chọn nhân vật, hoặ... mọi lưới đang hiện".
6. Lần đầu vào Animation hoặc Texture Paint thì phóng tới nhân vật.
7. Lần mở đầu chỉ hỏi ngôn ngữ, xong vào màn hình **Dự án**.
8. Bỏ dấu ⚠ ở "Bản nháp (chưa thuộc dự án)": đây là trạng thái bình thường, không phải lỗi.

### Nhóm 2: tối giản và dời chỗ

1. Mở sẵn thanh bên ở thẻ **Hướng dẫn** trong Layout.
2. Cột icon từ 14 xuống khoảng 7: ẩn Lớp Xem, Bộ Sưu Tập, Hạt, Vật Lý, Ràng Buộc. Phần mềm có sẵn công tắc cho từng thẻ, và lấy lại được
   ở mũi tên ⌄ cuối cột.
3. Rig anime chỉ mở sẵn Kiểm tra, Các phần, Biểu cảm; bảy mục còn lại đóng.
4. **Kiểm tra model** chỉ liệt kê mục cần sửa, phần đã ổn gom thành một dòng, thêm nút **Sửa tất cả**.
5. Đưa **Xuất sang game** lên thẳng menu Tập Tin. Gom Kết Nối, Bổ Sung Thêm, Xem Trước Dữ Liệu, Dữ Liệu Bên Ngoài, Dọn Dẹp vào một mục
   con.
6. Thẻ trên cùng còn 4 thẻ theo thứ tự công việc, tên tiếng Việt: Dựng, Tô màu, Hoạt họa, Tranh; phần còn lại lấy lại ở nút +.
7. Đưa Rig anime lên đầu thẻ của bộ xương, trên các mục của Blender.

### Nhóm 3: thống nhất từ ngữ

| Đang thấy | Nên là |
|---|---|
| Nguyên Vật Liệu, Chất Liệu, Vật liệu, material | Vật liệu |
| Khung Rối, Rig anime, Gắn khung, Khung người anime | Bộ xương, Bộ xương anime |
| Xuất Khẩu, Kết Xuất, Xuất sang engine | Xuất file, Xuất hình, Xuất sang game |
| Hình Mẫu | Hình biểu cảm |
| Bóc Vỏ Hành | Hiện khung trước sau |
| Khóa cả dáng | Lưu dáng |
| Sắp Đặt Nhanh Trống | Cài đặt nhanh |
| Sắp Đặt về Khung Khóa Hóa | Cách lưu khung |

Các chữ gốc của Blender sửa trong `locale/po/vi.po`, chữ của DaskToon sửa trong `dasktoon_translations.py`. Trang hướng dẫn phải đổi theo;
`tools/dasktoon_guide_check.py` sẽ bắt tên nào lệch.

## Cần người dùng quyết

Ba việc đảo ngược quyết định đã duyệt:

1. **Rig anime lên đầu thẻ** (nhóm 2, mục 7): ngày 2026-10-10 đã chốt để ở cuối thẻ.
2. **Mở sẵn Hướng dẫn** (nhóm 2, mục 1): spec 2026-10-04 muốn thanh bên không có DaskToon, và Hướng dẫn là ngoại lệ duy nhất, nhưng khi đó
   nó vẫn đóng.
3. **Bớt thẻ và icon** (nhóm 2, mục 2 và 6): người đã biết Blender tốn thêm một lần bấm. Có thể gộp thành một công tắc "Giao diện đơn
   giản", mặc định bật.

Việc đổi tên thẻ trên cùng là việc lớn nhất: tên thẻ là dữ liệu trong file, và phần Animation đang tìm thẻ theo tên.

## Bỏ bớt nếu chỉ làm nhân vật anime

Câu hỏi của người dùng cùng ngày. Đã dò mã DaskToon dùng phần nào của Blender, phần nào được bản build bật, và mỗi phần nặng bao
nhiêu. Bản cài hiện nặng 829 MB: chương trình 93 MB, Python 152 MB, thư viện đi kèm 322 MB.

### Phải giữ, dù trông không liên quan

| Phần | DaskToon dùng nó để |
|---|---|
| Cycles | Nướng màu khi xuất sang Unity và Godot (`dasktoon_export/bake.py`), có phép thử riêng |
| Geometry Nodes | Viền, bóng mặt, hiệu ứng hành động nhanh (có cả vùng mô phỏng) |
| Compositor | Hoàn thiện tranh: 13 loại node, gồm Kuwahara, Glare, Lens Distortion |
| Hạt (particles) | Hiệu ứng anime dạng không khí: bong bóng, cánh hoa, tia lửa |
| Sequencer | Nói khớp âm lấy giọng từ dải âm thanh |
| FFmpeg | Xuất video |
| OpenSubdiv | Lưới chia mịn (pl1 dùng) |
| EEVEE | Chính là engine DaskToon Anime |
| Python, numpy | Phần lớn DaskToon viết bằng Python |

### Gỡ khỏi bản build: không mã DaskToon và không phép thử nào dùng

| Phần | Làm gì | Tiết kiệm |
|---|---|---|
| USD, Hydra, MaterialX | Định dạng trao đổi của xưởng phim | 48 MB |
| OSL | Viết shader bằng mã cho Cycles; nướng màu không cần | 72 MB |
| OpenImageDenoise | Khử nhiễu ảnh Cycles và node Denoise; Hoàn thiện tranh không dùng | 63 MB |
| Embree | Tăng tốc Cycles; nướng màu chạy được không có nó, chậm hơn chút | 26 MB |
| oneAPI | Chạy Cycles trên card Intel | 6 MB |
| libmv (tracking) | Bám điểm trong video | 5 MB |
| OpenVDB, NanoVDB, Mantaflow, Ocean | Khói, lửa, nước, biển mô phỏng | 4 MB thư viện, phần còn lại trong chương trình |
| Alembic | Trao đổi hoạt cảnh nướng sẵn | trong chương trình |
| Freestyle | Vẽ nét kiểu cũ khi render; viền DaskToon thay thế | trong chương trình |
| Bullet | Vật thể cứng va chạm; lắc lư DaskToon tự làm | trong chương trình |
| OpenXR, chuột 3D, xuất PDF và SVG của bút chì dầu, dò ảnh thành nét | Kính VR, thiết bị riêng, bút chì dầu | trong chương trình |

Cộng phần đo được: khoảng 224 MB trên 829 MB (27%), chưa tính phần chương trình nhỏ lại và thời gian build ngắn đi (chưa đo). Chỉ
cần đổi tùy chọn của bản build, không sửa mã Blender, nên lần cập nhật Blender sau không bị xung đột. Sau khi đổi phải build lại
toàn bộ và chạy hết phép thử, cả Unity và Godot.

Gỡ khỏi bản cài các phần bổ trợ: hydra_storm, viewport_vr_preview, io_anim_bvh, io_curve_svg, rigify (trùng với khung DaskToon),
pose_library (đang chen bảng "Kiến Tạo Tài Sản Tư Thế" vào thẻ Animation), ui_translate, node_wrangler. Ít dung lượng nhưng bớt
rối.

### Chỉ ẩn khỏi giao diện

Bút chì dầu là phần lõi, không gỡ được bằng tùy chọn build; Cycles phải giữ cho việc nướng màu. Cả hai chỉ nên ẩn:

- Menu Thêm từ 17 mục còn 6: Lưới, Bộ xương, Hình ảnh (tranh tham chiếu), Nguồn sáng, Máy quay, Hiệu ứng anime. Ẩn Đường cong, Bề mặt,
  Siêu cầu, Văn bản, Mây điểm, Thể tích, Bút chì dầu, Lưới rào, Trống rỗng, Đầu dò ánh sáng, Loa, Trường lực, Thực thể bộ sưu tập.
  Đường cong hay dùng làm tóc, nhưng khung tự động chỉ nhận lưới, nên vẫn phải đổi sang lưới.
- Chọn engine: chỉ hiện DaskToon Anime.
- Nhập và xuất: chỉ giữ FBX, glTF, OBJ và Xuất sang game.
- Thẻ trên cùng: ẩn Sculpting, UV Editing, Rendering, Compositing, Geometry Nodes, Scripting; còn Layout, Modeling, Texture Paint,
  Animation, Shading.
- Cột icon: ẩn Lớp Xem, Bộ Sưu Tập, Ràng Buộc của vật thể, Hạt, Vật Lý, Kết Cấu. Ràng buộc lắc lư nằm ở thẻ của xương nên không mất.
- Thẻ Vật thể: ẩn Mỹ Thuật Đường Nét (Line Art đã bỏ ngày 2026-10-04) và Thực Thể Hóa.

Nên làm phần ẩn trước, dưới một công tắc "Giao diện đơn giản" bật sẵn, tắt đi thì hiện lại đủ (xem mục 3 ở phần trên). Phần gỡ khỏi
build chỉ đáng làm khi đóng gói DaskToon cho người khác tải.
