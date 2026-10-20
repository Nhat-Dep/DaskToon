# Báo cáo: Hướng dẫn để người mới làm model anime đúng (2026-10-20)

Bạn hỏi: "có thể tạo cơ chế hướng dẫn để 1 người mới cũng có thể làm model anime đúng?" Bạn chọn: kiểm tra model,
các bước làm từng bước, trang hướng dẫn để đọc (không có model mẫu). "Đúng" nghĩa là các công cụ tự động của
DaskToon (tự gắn khung, sửa chỗ gập, biểu cảm, shader, xuất sang Unity) chạy được mà không phải sửa tay. Chỗ đặt: thanh
bên của khung nhìn 3D. Thiết kế: `docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md`.

## Đã làm

Thẻ **Hướng Dẫn** ở thanh bên khung nhìn 3D (bấm **N**), có hai khung:

- **Kiểm tra model**: bấm là xem nhân vật đang chọn (không chọn gì thì xem mọi lưới đang hiện). Có 19 mục, chia bốn
  nhóm: Tư thế đứng, Lưới, Vật liệu, Sau khi gắn khung. Mỗi mục có một dấu (✓ ổn, ⚠ nên sửa, ✗ phải sửa, đồng hồ là chờ
  gắn khung) và một câu nói vì sao. 13 mục có nút **Sửa**: DaskToon tự sửa rồi kiểm tra lại. Nút **?** mở trang hướng
  dẫn đúng chỗ nói về mục đó.
- **Từng bước**: 9 bước, từ Tạo model, Cơ thể, Đầu và mặt, Tóc, Quần áo, Vật liệu, Gắn khung, Biểu cảm đến Unity. Bước
  xong có dấu ✓. Bước đầu tiên chưa xong thì mở ra, gồm lời khuyên, các mục kiểm tra của bước, nút chính của bước và
  nút **Đọc hướng dẫn**. Bước Unity tính là xong khi đã chạy **Xuất sang engine**.
- **Trang hướng dẫn** mở trong trình duyệt, không cần mạng. Có tiếng Việt và tiếng Anh, trang nào theo đúng ngôn ngữ
  giao diện. Mỗi bước một trang, mỗi mục kiểm tra một đoạn: làm gì, vì sao DaskToon cần, xem ở đâu trong Blender. Hình
  được dựng từ nhân vật thử, không dùng nhân vật của bạn. Các trang gọi menu của Blender đúng bằng tên tiếng Việt
  Blender hiện (Tập Tin, Khung Rối, Xuất Khẩu…).

Ảnh chụp trong cửa sổ thật (tiếng Việt, nhân vật thử, công cụ `tools/dasktoon_guide_screenshots.py`):

- `model-guide/vi/102_model_check.png`: Kiểm tra model của một nhân vật lơ lửng 0,3 m trên sàn: mục "Bàn chân cách sàn"
  có nút **Sửa**; các mục sau khi gắn khung đang chờ.
- `model-guide/vi/103_step_by_step.png`: sau khi bấm Sửa, sáu bước đầu đã xong, bước 7. Gắn khung đang mở.
- `model-guide/vi/104_page_body.png`: trang "2. Cơ thể" bằng tiếng Việt.

## Thử trên model thật

Chạy Kiểm tra model trên bản sao của 7 nhân vật của bạn (đã gắn khung từ trước; không lưu đè tệp nào). Mỗi model mất
dưới 1,5 giây.

| Model | Cần sửa trước | Sau khi bấm mọi nút Sửa |
|---|---|---|
| filie | mặt hơn 4 cạnh, shader, vật liệu thừa, chưa có chớp mắt, Kiểm tra khung | còn Kiểm tra khung |
| lr | lệch giữa 0,20 m, tay thấp, mặt hơn 4 cạnh, shader, vật liệu thừa, biểu cảm trống, Kiểm tra khung | còn tay thấp, Kiểm tra khung |
| luna | lệch giữa 0,17 m, tay thấp, mặt hơn 4 cạnh, shader, chưa có chớp mắt, Kiểm tra khung | còn tay thấp, Kiểm tra khung |
| pl1 | mặt hơn 4 cạnh, shader, vật liệu thừa, chưa có chớp mắt, Kiểm tra khung | còn Kiểm tra khung |
| rg2 | lệch giữa 0,38 m, shader, chưa có chớp mắt, Kiểm tra khung | còn Kiểm tra khung |
| rgg | lệch giữa 0,40 m, shader, chưa có chớp mắt, Kiểm tra khung | còn Kiểm tra khung |
| tdt | lệch giữa 0,20 m, tay thấp, shader, biểu cảm trống | còn tay thấp |

Mọi nút Sửa đều chạy được trên cả 7 model. Hai mục còn lại không có nút Sửa, đúng như thiết kế. "Tay thấp" cần dang
tay ra khi dựng. "Kiểm tra khung" cần tự xem và tô lại trọng số ở những chỗ nó chỉ ra.

## Lỗi bắt được khi chụp trong cửa sổ thật

Chạy nền không thấy các lỗi này; chụp cửa sổ thật thì thấy. Tất cả đã sửa:

1. Tên bước bị bản dịch có sẵn của Blender đè lên: "Hair" hiện "Tóc/Lông", "Rigging" hiện "Dàn Dựng". Bản dịch của
   DaskToon chỉ được dùng khi Blender chưa dịch câu đó. Đã sửa: tên bước và tên nhóm dịch trong ngữ cảnh riêng của
   DaskToon. Vì cùng lý do, khung "Steps" (Blender dịch là "Số/Phân/Bước") đổi tên thành **Từng bước**.
2. Chữ trong ô của bước bị cắt mất bằng "…": ô nằm trong ô nên hẹp hơn, và các dòng sau bị thụt vào dù dòng đầu không
   có biểu tượng. Đã sửa: tính bề rộng theo ô, và chỉ thụt dòng khi có biểu tượng.
3. Năm dòng giống hệt nhau "Sau khi gắn khung". Đã sửa: mỗi dòng nói rõ mục nào đang chờ, ví dụ "Kiểm tra khung: sau
   khi gắn khung".

Thêm một chỗ thấy khi đọc mã: Windows bỏ phần "#mục" khi đưa đường dẫn tệp cho trình duyệt, nên nút **?** chỉ mở đầu
trang. Đã sửa: nút mở một trang nhỏ trong thư mục tạm, trang đó chuyển tiếp tới đúng mục.

## Quyết định tôi tự đưa ra

1. Mắt và miệng kiểm tra sau khi gắn khung: DaskToon tìm chúng theo khung của đầu, mà khung đó chỉ có khi đã gắn khung.
   Trang bước 3 vẫn giải thích cách dựng mắt từ trước. Nếu sai thì: người mới biết về mắt ở bước 8 thay vì bước 3.
2. Tay dang hay buông được đo bằng tỷ lệ bề ngang trên chiều cao. Nếu sai thì: váy rộng hoặc tóc to có thể che mất
   chuyện tay đang buông.
3. Mục vòng cạnh ở gối và khuỷu tay đo theo trọng số mà phần sửa chỗ gập dùng: cần ít nhất 8 điểm pha trộn qua mỗi khớp.
   Nếu sai thì: tay chân ít lưới mà vẫn gập đẹp cũng bị cảnh báo.
4. Không kiểm tra liên tục, chỉ kiểm tra khi bấm nút, vì có mục mất cả giây trên lưới lớn.
5. Thẻ Hướng Dẫn là thẻ DaskToon duy nhất ở thanh bên khung nhìn 3D, theo lựa chọn của bạn.
6. Mục "Tỷ lệ đều" thay cho "đã áp dụng biến đổi": xoay hoặc phóng to đều không làm hỏng công cụ nào; chỉ tỷ lệ kéo dãn
   hoặc số âm mới làm hỏng.
7. Khung "Từng bước" đặt tên tiếng Anh là "Step by Step", để tránh bản dịch sẵn có "Số/Phân/Bước".
8. Hình trong trang dựng ở kiểu nhìn Solid, đúng kiểu người mới thấy khi dựng, không có chữ trong hình. Chú thích nằm
   trong trang nên có cả hai thứ tiếng.

## Kiểm tra

- `dasktoon_guide_checks_test` (18 bài) kiểm từng mục: nhân vật thử đúng thì qua hết; mỗi lỗi thì đúng mục báo; bấm Sửa
  thì hết lỗi.
- `dasktoon_guide_ui_test` (10 bài) kiểm thẻ Hướng Dẫn, các nút và các trang. Bước nào cũng có trang ở cả hai thứ
  tiếng; mục kiểm tra nào cũng có đoạn trên trang của bước mình; hình và liên kết nào cũng có thật.
- Bộ kiểm tra thanh bên vẫn cấm mọi khung DaskToon khác ở thanh bên khung nhìn 3D.
- Cả bộ kiểm tra DaskToon đạt: 82 tệp, 774 bài, kể cả các tệp Unity. Như mọi lần, phải khôi phục tệp mẫu rồi chạy lại
  shading và upgrade.

## Còn lại

- Tóc dài: vẫn chờ model của bạn.
- Hình trong trang được dựng lại bằng `tools/dasktoon_guide_pictures.py` mỗi khi cần.
