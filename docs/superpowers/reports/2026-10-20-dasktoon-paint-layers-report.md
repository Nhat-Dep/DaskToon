# Báo cáo: Tô vẽ anime — lớp vẽ trong ảnh, bắt đầu bằng một nút, bút và đổ màu (2026-10-20)

Bạn muốn nâng cấp chế độ tô vẽ ảnh (Texture Paint) của Blender, phần DaskToon chưa sửa gì. Bạn tô màu phẳng theo mảng,
vẽ chi tiết và hoa văn, vẽ mặt (mắt trên mảnh mắt, má hồng), vẽ cả trên model 3D lẫn trên ảnh phẳng. Bạn chọn ba phần:
bắt đầu tô vẽ bằng một nút, lớp vẽ, bút và đổ màu kiểu anime. Lớp vẽ làm theo hướng **nằm trong chính ảnh**. Sau đó
bạn giao "tự động trong vài tiếng tới". Thiết kế: `docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md`.

## Đã làm

**Lớp vẽ trong ảnh** (sửa lõi vẽ bằng C++):

- Mỗi ảnh có thể có **Lớp vẽ**: danh sách lớp, mắt bật/tắt, độ đậm, năm kiểu hoà trộn (Thường, Nhân, Cộng, Sáng,
  Phủ). Có các nút Thêm, Xoá, Lên, Xuống, Nhân đôi, Gộp xuống, Làm phẳng.
- Vẽ ở đâu thì nét cũng vào **lớp đang chọn**: trên model 3D, trên ảnh phẳng, đổ màu, tô chuyển màu.
- Những gì bạn thấy chính là ảnh gộp: ở khung nhìn 3D, ở khung xem ảnh, khi kết xuất, khi xuất sang Unity, khi lưu ra
  tệp. Vật liệu vẫn chỉ có một nút ảnh.
- Mỗi nét vẽ chỉ gộp lại đúng vùng vừa vẽ, nên vẽ vẫn mượt. Hoàn tác trả lại cả lớp lẫn ảnh gộp.
- Lần đầu thêm lớp, hình đang có thành lớp **Nền**, nên ảnh không đổi.
- Danh sách lớp nằm ngay trong khung của Blender, không thêm thẻ riêng:
  - ô bật lên **Texture Slots** ở thanh đầu khung nhìn 3D, chế độ tô vẽ (ô mang tên ảnh đang vẽ, ví dụ "Màu da");
  - khung **Hình Ảnh** ở thanh bên của khung xem ảnh.

**Bắt đầu tô vẽ** (menu của danh sách vật liệu, hoặc trong Texture Slots khi chưa có ô nào). Một nút làm hết:

1. tạo bản đồ UV nếu lưới chưa có;
2. mỗi vật liệu anime có một ảnh 2048 × 2048 tô sẵn màu của nó, nối vào Màu nền của shader;
3. thêm ba bút anime, chuyển sang chế độ tô vẽ, chọn bút Nét anime.

Đã sửa thêm một lỗi của Blender: nút **Thêm ô tô vẽ** trước đây chỉ nối vào shader Principled, nên với vật liệu DaskToon
(shader anime) ảnh mới không nối vào đâu. Nay nó nối vào Màu nền của shader anime.

**Bút và đổ màu**:

- Ba bút nằm trong tệp: **Anime Pen** (nét cứng, đều, không mờ mép), **Anime Blush** (phun mềm, nhạt) và **Anime Fill**.
- Công cụ **Đổ màu mảng** trên thanh công cụ: bấm vào một mảnh của model (ống tay, chiếc giày) thì mảnh đó được đổ kín
  màu bút trên lớp đang chọn. Khi bật Face Mask thì công cụ đổ các mặt đang chọn. Thanh đầu của công cụ có ô chọn màu và
  tên lớp sẽ nhận màu.
- Công cụ dùng chính nét đổ màu của Blender, nên đổ vào đúng lớp, tràn qua đường nối, và hoàn tác được như mọi nét vẽ.

**Không mất hình**: khi lưu tệp, ảnh đã vẽ được lưu theo.

- Ảnh có tệp trên đĩa thì ghi vào tệp đó.
- Ảnh không có tệp, và mọi ảnh lớp, thì gói vào tệp .blend.

Trang Hướng dẫn **6. Vật liệu** có thêm đoạn **Tô vẽ**.

Ảnh chụp trong cửa sổ thật (tiếng Việt, nhân vật thử, công cụ `tools/dasktoon_paint_screenshots.py`):

- `paint-layers/vi/110_texture_slots.png`: sau Bắt đầu tô vẽ, lớp "Lines" có một nét đỏ; ô bật lên Texture Slots đang
  mở, trong đó có Lớp vẽ (Lines, Cơ Sở), Hoà trộn, Độ Đục và ba nút.
- `paint-layers/vi/111_fill_part.png`: công cụ Đổ màu mảng, bấm vào cẳng chân trái, đổ màu xanh; thanh đầu có ô màu và
  tên lớp "Lines".
- `paint-layers/vi/112_image_editor.png`: cùng ảnh trong khung xem ảnh, thẻ Hình Ảnh với Lớp vẽ.

## Kiểm tra

Cả bộ kiểm tra DaskToon đạt: 83 tệp, kể cả các tệp Unity. Lần chạy này dự án Unity dùng để thử (trong thư mục tạm) bị
hỏng bộ đệm gói. Tôi xoá thư mục Library của nó rồi chạy lại các tệp Unity, tất cả qua. Như mọi lần, phải khôi phục tệp
mẫu rồi chạy lại shading và upgrade.

- `dasktoon_paint_layers_test` (11 bài, chạy nền) kiểm:
  - gộp đúng công thức cho cả năm kiểu hoà trộn, với hai độ đậm;
  - lớp ẩn không hiện; lớp đầu tiên giữ nguyên hình;
  - gộp xuống và làm phẳng giữ đúng những gì đang thấy; lên, xuống, xoá, nhân đôi; ảnh số thực;
  - Thêm ô tô vẽ nối vào shader anime;
  - Bắt đầu tô vẽ tạo UV, ảnh đúng màu, nối đúng chỗ, ba bút, chế độ tô vẽ, bút Nét anime;
  - lưu rồi mở lại tệp còn đủ ảnh, lớp và điểm ảnh;
  - Đổ màu mảng chọn đúng mảnh và đúng vật liệu.
- `dasktoon_paint_layers_window_test` (cửa sổ thật, chạy tay: `"$PY" tests/python/dasktoon_paint_layers_window_test.py
  "$DT"`) kiểm:
  - nét vẽ trên model 3D vào lớp đang chọn, lớp Nền không đổi, ảnh gộp đúng (sai lệch 0,002);
  - hoàn tác trả lại cả lớp lẫn ảnh;
  - nét vẽ trên ảnh phẳng vào lớp đang chọn;
  - bấm công cụ Đổ màu mảng lên tấm phẳng thì phủ kín 100%, lớp Nền không đổi, bút đang dùng được trả lại, Face Mask
    tắt lại.

## Quyết định tôi tự đưa ra

1. Lớp vẽ là dữ liệu DaskToon gắn vào ảnh; C++ chỉ đọc nó, không đổi cấu trúc tệp của Blender. Vì vậy tệp mở được ở
   Blender thường, nhưng ở đó chỉ thấy ảnh gộp.
2. Gộp trên giá trị điểm ảnh như đang lưu (ảnh 8 bit là giá trị sRGB), giống phần mềm vẽ 2D. Nhân và Cộng trên ảnh 8 bit
   vì vậy cho màu hơi khác cách gộp tuyến tính.
3. Lớp chỉ dành cho ảnh một ô (không UDIM); lớp khác cỡ thì bị bỏ qua khi gộp.
4. Nét vẽ vẫn vào lớp đang chọn kể cả khi lớp đó đang ẩn; danh sách lớp báo "lớp đang ẩn".
5. Danh sách lớp được vẽ thêm vào khung của Blender, không thành thẻ DaskToon riêng (luật giao diện 2026-10-04).
6. Ảnh mới 2048 × 2048, tự gói vào tệp nên không cần chọn chỗ lưu.
7. Ảnh có tệp trên đĩa thì lưu tệp .blend sẽ ghi đè tệp ảnh đó, như Lưu ảnh của Blender. Ảnh lớp luôn gói trong
   .blend.
8. Bút anime nằm trong tệp, không cài vào thư viện chung: đi theo tệp, không đụng thiết lập của bạn.
9. Gộp xuống cho ra lớp hoà trộn Thường; kết quả chỉ đúng tuyệt đối khi lớp dưới cũng là Thường.
10. Xoá lớp chỉ bỏ lớp khỏi danh sách; ảnh của lớp còn trong tệp tới lần lưu sau. Nhờ vậy hoàn tác lấy lại được lớp
    với nguyên điểm ảnh.

## Lỗi bắt được khi chạy trong cửa sổ thật

- Chạy nền không thử được nét vẽ thật, nên phép thử cửa sổ là nơi duy nhất kiểm phần C++. Phép thử đó qua ngay lần đầu
  chạy đủ.
- Khi chụp ảnh, một nét bút lan ra gần khắp người nhân vật thử. Lỗi không nằm ở lớp vẽ: bản đồ UV mặc định của nhân vật
  thử đặt mọi mặt chồng lên cùng một vùng ảnh. Người mới cũng có thể gặp chuyện này (xem phần Còn lại).
- Năm chỗ chỉ thấy khi chụp trong cửa sổ thật, đã sửa hết:
  1. Công cụ Đổ màu mảng không có ô chọn màu. Đã thêm ô chọn màu và tên lớp sẽ nhận màu.
  2. Đổ màu xong, công cụ tự nhảy về Bút: lúc trả lại bút cũ, Blender đổi luôn công cụ. Nay Đổ màu mảng được giữ.
  3. Bản dịch có sẵn của Blender hiện kiểu hoà trộn "Normal" thành "Pháp Tuyến" (pháp tuyến). Nay dịch riêng thành
     Thường, Nhân, Cộng, Sáng, Phủ.
  4. Hàng ba nút Nhân đôi, Gộp xuống, Làm phẳng bị cắt chữ. Nay mỗi nút một dòng.
  5. Đổ màu lem sang mảnh bên cạnh trên ảnh, vì Bắt đầu tô vẽ tự tạo UV để các mảnh sát nhau. Nay các mảnh cách nhau
     khoảng 20 điểm ảnh.

## Còn lại

- Kiểm tra model nên có thêm mục "UV chồng nhau": nét vẽ sẽ hiện ở nhiều chỗ cùng lúc.
- Má hồng theo biểu cảm (bạn để sau).
- Ở khung xem ảnh, công cụ Fill có sẵn của Blender (đổ theo vùng cùng màu) đã đổ vào lớp đang chọn. Chưa có công cụ đổ
  "theo vùng cùng màu" trên model 3D.
