# Ghi chú của người viết trang Hướng dẫn

Mỗi đợt một mục: các trang đã viết, câu hỏi, chỗ không chắc, lỗi thấy trong DaskToon (xem `rules.md` mục 7).

## Đợt 1

### Các trang đã viết
- `features.html` (vi và en): Trang mục lục các chức năng riêng của DaskToon, xếp theo nhóm và dẫn tới các trang hiện có trong Đợt 1 (`outline.html`, `face-shading.html`).
- `index.html` (vi và en): Đã thêm một dòng dẫn tới `features.html` ngay sau danh sách 9 bước.
- `outline.html` (vi và en): Hướng dẫn chức năng viền anime (bật viền, chỉnh màu và độ dày, viền màu tự động cho mọi vật liệu, chuẩn bị dữ liệu UV cho game engine, gỡ viền).
- `face-shading.html` (vi và en): Hướng dẫn bóng mặt anime bằng khối trứng (tạo bóng mặt, tinh chỉnh 4 thanh trượt giữ bóng mũi/cằm, chọn và dịch chuyển khối trứng proxy trong khung nhìn, căn lại khối trứng, gỡ bóng mặt).
- `tools/dasktoon_feature_pictures.py`: Đoạn mã tự động kết xuất ảnh minh họa từ nhân vật thử nghiệm trong `tests/python/`.
- `pages/pictures/outline.png` và `face-shading.png`: Ảnh kết xuất trước và sau khi dùng chức năng (kích thước 608x400, dung lượng dưới 300 KB).

### Câu hỏi và chỗ không chắc
- Trong `features.html`: Tuân theo quy tắc "Chỉ đưa vào trang đã có" để tránh lỗi liên kết hỏng, Đợt 1 chỉ liệt kê nhóm "Shader và hình" với hai trang đã viết. Các đề mục nhóm khác (`Bắt đầu`, `Tô vẽ và UV`, `Rig`, `Biểu cảm`, `Hoạt hình`, `Xuất`) sẽ lần lượt xuất hiện ở các đợt tiếp theo khi các trang tương ứng được tạo.
- Tên nút giao diện: Trên node Anime BSDF, ô chọn bật viền mang nhãn tiếng Anh là `Outline` (tiếng Việt dịch là `Vẽ Nét Viền` theo bộ từ điển Blender), trong khi trên node Đổ bóng cel nhãn là `Use Outline` (`Dùng viền`). Đã kiểm tra cả hai đều hợp lệ trong danh mục giao diện của từng ngôn ngữ.
- Tên bộ điều chỉnh: Các bộ điều chỉnh `DaskToon Outline` và `DaskToon Face Shading` do hệ thống Geometry Nodes tự sinh, không phải là nhãn thuộc tính hay nút bấm giao diện đăng ký trong RNA, nên được trình bày dưới dạng `<code>` thay vì `<b>` để phù hợp với định dạng mã và kiểm tra giao diện.

### Lỗi thấy trong DaskToon
- Nhận thấy cảnh báo `DeprecationWarning: 'Material.use_nodes' is expected to be removed in Blender 6.0` xuất hiện từ `tests/python/dasktoon_guide_checks_test.py:48` và `scripts/modules/dasktoon_guide/checks.py:209`. Đây là cảnh báo chuyển tiếp API của Blender hướng tới phiên bản 6.0.

### Claude soát Đợt 1 (2026-10-22)

Đạt: đúng khuôn, ngắn, đủ hai thứ tiếng, chỉ sửa tệp được phép, lệnh kiểm tra sạch, phép thử qua. Đã sửa:

- Viền: vật liệu đi kèm tên `<tên vật liệu>.Outline` (không phải `.Outline`); "Nét màu cho mọi material" là nút trong
  bảng Hoàn thiện tranh (thẻ Tính Chất của Cảnh), không phải F3.
- Bóng mặt: khối trứng ôm khuôn mặt (không phải cả đầu); Diện Tích Bao Phủ là mức thay pháp tuyến bằng pháp tuyến khối
  trứng, Suy Giảm Dần là độ mềm chỗ mặt giáp cổ và tai; bỏ câu "trở lại hoàn toàn sạch sẽ".
- Hai ảnh hỏng (dựng bằng Workbench; ảnh bóng mặt không thấy khác biệt) bị gỡ; làm lại ở Đợt 2.

Trả lời câu hỏi: dùng `<code>` cho tên bộ điều chỉnh là đúng, nay đã ghi vào `rules.md`. Cảnh báo `Material.use_nodes`
là của Blender 6.0, chưa cần làm gì.

### Claude làm Đợt 2 (2026-10-22)

Trang: shader, nodes, finish, paint, unwrap, project, interface, và ảnh outline, face-shading làm lại bằng EEVEE (`tools/dasktoon_feature_pictures.py`). Tên nút tiếng Việt lấy đúng như giao diện hiện: Blender thắng khi nó có bản dịch riêng (ví dụ AO hiện "THTMT", Ambient "Môi trường", Light "Nguồn/Ánh Sáng/Đèn"), nên vài tên đọc lạ; các tên đó là của Blender, không sửa được trong trang.
