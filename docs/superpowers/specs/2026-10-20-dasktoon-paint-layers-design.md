# Tô vẽ anime: lớp vẽ trong ảnh, bắt đầu bằng một nút, bút và đổ màu (2026-10-20)

Người dùng hỏi nâng cấp "cái vẽ texture hiện tại ở bảng blender nhưng chưa sửa gì": chế độ Texture Paint của Blender,
DaskToon chưa đụng tới. Họ tô màu phẳng theo mảng, vẽ chi tiết và hoa văn, vẽ mặt (mắt trên mảnh mắt, má hồng); vẽ cả
trên model 3D lẫn trên ảnh phẳng. Chọn: bắt đầu tô vẽ bằng một nút, lớp vẽ, bút và đổ màu kiểu anime (má hồng theo
biểu cảm để sau). Lớp vẽ: **nằm trong chính ảnh** (sửa lõi vẽ C++), không phải các ảnh xếp chồng trong vật liệu. Sau
đó "tự động trong vài tiếng tới".

## 1. Đã đo trước khi thiết kế

- `paint.add_texture_paint_slot` (C++, `paint_image_proj.cc`) chỉ nối ảnh mới vào Principled BSDF và lấy màu mặc định
  từ một Principled. Vật liệu mới của DaskToon dùng shader anime, nên ảnh mới không nối vào đâu: vẽ mà nhân vật không đổi.
- Blender không có lớp vẽ. Đổ màu (Fill) trên model 3D chỉ đổ cả vật thể hoặc các mặt đang chọn; trên ảnh phẳng thì đổ
  theo vùng cùng màu (ngưỡng).
- Mọi kiểu vẽ (model 3D, ảnh phẳng, đổ màu, tô chuyển màu) làm mới ảnh qua một hàm chung `imapaint_image_update`, và
  lấy điểm ảnh để vẽ ở bốn chỗ: `project_paint_build_proj_ima`, `paint_2d_new_stroke`, `paint_2d_bucket_fill`,
  `paint_2d_gradient_fill`. Hoàn tác khôi phục điểm ảnh trong `image_undo.cc`.
- Xuất sang Unity chép nguyên ảnh nối thẳng vào shader, và "nướng" những gì phức tạp hơn.

## 2. Lớp vẽ trong ảnh

Người dùng thấy: mỗi ảnh có thể có **Lớp vẽ** (danh sách: tên, mắt bật/tắt, độ đậm, kiểu hoà trộn, lớp đang chọn). Vẽ
ở đâu (model 3D, ảnh phẳng, đổ màu, tô chuyển màu) thì nét vẽ vào **lớp đang chọn**; những gì thấy được (khung nhìn
3D, khung xem ảnh, ảnh kết xuất, bản xuất Unity, lưu ra tệp) là **ảnh gộp**, chính là ảnh đó. Vật liệu vẫn chỉ có một
nút ảnh.

- Kiểu hoà trộn: Thường, Nhân, Cộng, Sáng (Screen), Phủ (Overlay). Gộp theo cách của phần mềm vẽ 2D, trên giá trị
  điểm ảnh như đang lưu (ảnh 8 bit: giá trị sRGB 0..1; ảnh số thực: giá trị tuyến tính), alpha thẳng.
- Thêm lớp lần đầu trên ảnh chưa có lớp: điểm ảnh hiện có thành lớp **Nền**, lớp mới trong suốt nằm trên.
- Các nút: Thêm lớp, Nhân đôi, Xoá, Lên, Xuống, Gộp xuống, Làm phẳng (bỏ mọi lớp, giữ ảnh gộp).
- Dữ liệu: thuộc tính Python của ảnh (`Image.dasktoon_layers`, `Image.dasktoon_layer_index`), lưu trong system
  properties; mỗi lớp trỏ tới một ảnh ẩn (tên bắt đầu bằng dấu chấm), cùng cỡ, cùng kiểu 8 bit hoặc số thực, cùng không
  gian màu với ảnh gộp. Không đổi cấu trúc DNA của Blender.
- C++ (`editors/sculpt_paint/mesh/paint_image_layers.cc`) đọc dữ liệu đó:
  - **ảnh đích**: ảnh có lớp thì nét vẽ vào ảnh của lớp đang chọn; bốn chỗ lấy điểm ảnh ở mục 1 dùng ảnh đích;
  - **gộp vùng**: sau mỗi bước vẽ, `imapaint_image_update` gộp lại vùng vừa vẽ của mọi ảnh có lớp đó, rồi làm mới
    ảnh gộp trên GPU;
  - **hoàn tác**: sau khi khôi phục điểm ảnh, gộp lại toàn bộ các ảnh có lớp;
  - **toán tử** `paint.dasktoon_layers_composite(image=...)` gộp lại cả ảnh, cho Python dùng (thêm, xoá lớp, đổi độ
    đậm...). Chỉ một cách gộp, ở C++.
- Giao diện nằm trong khung của Blender, không thêm khung DaskToon ở thanh bên: danh sách lớp được vẽ thêm vào cuối
  khung **Texture Slots** (chế độ Texture Paint, cả ô bật lên ở thanh trên) cho ảnh của ô đang chọn, và cuối khung
  **Image** của khung xem ảnh cho ảnh đang xem.

## 3. Bắt đầu tô vẽ bằng một nút

**Bắt đầu tô vẽ** (`dasktoon.paint_start`), ở menu ô vật liệu (cạnh Dùng shader DaskToon) và trong khung Texture Slots
khi chưa có ô nào: với lưới đang chọn,

1. chưa có bản đồ UV thì tạo bằng Phóng Chiếu UV Thông Minh;
2. mỗi vật liệu mà mặt lưới dùng, có shader anime mà Màu nền chưa nối ảnh: tạo ảnh 2048 × 2048, tô sẵn Màu nền của
   shader, nối vào Màu nền;
3. thêm bút anime vào tệp (mục 4), chuyển sang chế độ Texture Paint, chọn bút Nét anime.

Sửa C++: `paint.add_texture_paint_slot` nối Màu nền vào shader anime (Anime BSDF, Dask Cel) khi vật liệu không có
Principled, và lấy màu mặc định từ đó.

**Không mất hình**: khi lưu tệp, ảnh đã vẽ mà chưa lưu được lưu theo: ảnh có tệp trên đĩa thì ghi vào tệp đó; ảnh
không có tệp, và mọi ảnh lớp, thì gói vào tệp .blend.

## 4. Bút và đổ màu kiểu anime

- Bút (thêm vào tệp, dùng được như bút của Blender): **Nét anime** (nét cứng, đều, không mờ mép), **Má hồng** (phun mềm,
  nhạt), **Đổ màu** (kiểu Fill của Blender).
- Công cụ **Đổ màu mảng** trên thanh công cụ của Texture Paint: bấm vào model thì đổ màu bút kín mảnh rời dưới con trỏ
  (chỉ các mặt cùng vật liệu); khi bật Face Mask thì đổ kín các mặt đang chọn. Đổ vào lớp đang chọn, tràn ra mép 2 điểm
  ảnh (không tràn sang mặt khác) để không hở đường nối.
- Trên ảnh phẳng, Fill của Blender (đổ theo vùng cùng màu) đã đổ vào lớp đang chọn nhờ mục 2.

## 5. Kiểm thử

- Chạy nền (`dasktoon_paint_layers_test`): gộp đúng công thức cho từng kiểu hoà trộn, độ đậm, lớp ẩn; thêm lớp đầu
  tiên giữ nguyên ảnh; gộp xuống, làm phẳng; Bắt đầu tô vẽ nối đúng shader anime với đúng màu; Add Texture Paint Slot
  nối vào shader anime; Đổ màu mảng chỉ đổ mảnh đó; lưu tệp gói ảnh lớp; bút được thêm.
- Cửa sổ thật (`dasktoon_paint_layers_window_test`, như phép thử dự án, không nằm trong CMake): nét vẽ trên model 3D và
  trên ảnh phẳng vào lớp đang chọn, lớp khác không đổi, ảnh gộp đổi đúng; hoàn tác trả lại cả lớp lẫn ảnh gộp.

## 6. Quyết định (tự động)

1. Lớp vẽ là dữ liệu Python gắn vào ảnh, C++ chỉ đọc: không đổi DNA (tệp cũ, tệp mới mở được ở Blender thường), và
   biên dịch lại ít. Cái giá nếu sai: Blender thường mở tệp thì chỉ thấy ảnh gộp, không thấy lớp.
2. Gộp trên giá trị điểm ảnh như đang lưu (8 bit là sRGB), như phần mềm vẽ 2D. Cái giá: Nhân, Cộng trên ảnh 8 bit cho
   màu hơi khác cách gộp tuyến tính.
3. Lớp chỉ cho ảnh một ô (không UDIM); lớp khác cỡ ảnh gộp thì bị bỏ qua khi gộp.
4. Nét vẽ vào lớp đang chọn kể cả khi lớp đó đang ẩn; danh sách lớp báo "lớp đang ẩn".
5. Danh sách lớp vẽ thêm vào khung Texture Slots và khung Image của Blender, không thành khung DaskToon riêng ở thanh
   bên (luật giao diện 2026-10-04).
6. Ảnh mới 2048 × 2048: đủ nét cho nhân vật cao 1,6 m tới cả thân; ảnh tự gói vào tệp nên không cần chọn chỗ lưu.
7. Ảnh có tệp trên đĩa thì lưu tệp .blend sẽ ghi đè tệp ảnh đó (như Lưu ảnh của Blender); ảnh lớp luôn gói trong
   .blend. Cái giá: ai muốn giữ ảnh gốc phải sao chép trước.
8. Bút anime nằm trong tệp (tài sản của tệp), không cài vào thư viện chung: đi theo tệp, không đụng thiết lập người
   dùng.
