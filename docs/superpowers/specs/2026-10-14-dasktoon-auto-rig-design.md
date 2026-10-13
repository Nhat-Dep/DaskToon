# DaskToon: tự rig một nút và mục Kiểm tra — Thiết kế

Cho người không chuyên đồ họa: chọn nhân vật, bấm một lần là có rig, rồi máy chỉ ra chỗ cần xem kèm nút sửa. Dựa trên rig
anime (`docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md`), khớp theo hình và vùng cơ thể
(`docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md`).

## 1. Quyết định của người dùng (2026-10-14)

- Cách dẫn: **một nút rồi kiểm tra** (không phải từng bước).
- Chỗ đặt: mục **Khung người anime** trong menu Thêm › Khung xương **thành nút tự rig**; không thêm mục riêng.
- Thử tư thế: **nút cho từng tư thế**.
- Kiểm tra ba loại lỗi: **khớp lệch ra ngoài thân**, **chỗ bị kéo giãn**, **vai trò có vẻ sai**.
- Làm tự động (thiết kế, kế hoạch, code), không đẩy lên GitHub, không gộp nhánh.

## 2. Tự rig

Thêm › Khung xương › Khung người anime (`dasktoon.rig_add_humanoid`):

- **Có mô hình đang chọn**: thêm khung, thêm các mô hình làm phần (vai trò đoán như cũ), khớp theo hình, Nhận diện vùng và
  lọn, Dựng rig, rồi Kiểm tra (§4). Bảng Properties của cửa sổ chuyển sang thẻ dữ liệu của khung xương (nơi có mục Rig
  anime). Thông báo: đã dựng rig, xem mục Kiểm tra. Dựng rig lỗi (ví dụ mô hình bị chia sẻ dữ liệu) thì vẫn giữ khung và
  báo lỗi như nút Dựng rig.
- **Không chọn mô hình**: chỉ thêm khung như trước.

## 3. Tư thế thử

Năm nút: **Giơ tay**, **Ngồi**, **Quay đầu**, **Vẫy tay**, **Về nghỉ**. Dáng đặt thẳng lên xương (không khóa hình, không
tạo clip; đổi khung hình thì hoạt hình của bạn hiện lại như cũ). Góc tính quanh khớp, theo hướng thế giới, từ tư thế
nghỉ:

| Tư thế | Xương và góc |
|---|---|
| Giơ tay | Cánh tay trên hai bên xoay lên 110° quanh trục trước sau |
| Ngồi | Đùi hai bên gập ra trước 90°; cẳng chân gập lại 90° (về thẳng đứng) |
| Quay đầu | Đầu quay sang trái 45° quanh trục đứng |
| Vẫy tay | Cánh tay trên phải giơ 100°, cẳng tay phải vẫy 30° |
| Về nghỉ | Mọi xương về nghỉ |

## 4. Kiểm tra

Chạy sau khi tự rig và khi bấm **Kiểm tra lại**. Kết quả lưu trên rig (danh sách chỗ cần xem), mở lại file vẫn còn.

### 4.1 Khớp lệch ra ngoài thân

Các khớp: vai, khuỷu tay, cổ tay, hông, đầu gối, cổ chân (hai bên), gốc cổ, khớp đầu. Một khớp ở **trong thân** khi trong
sáu tia bắn từ nó theo sáu hướng (±X, ±Y, ±Z) có ít nhất bốn tia trúng bề mặt các phần Body, Clothing (mô hình hở ở cổ
tay áo, cổ áo nên không đòi cả sáu). Khớp ngoài thân thì báo "Cổ tay trái nằm ngoài thân", nút **Sửa**: vào chỉnh khớp,
khớp đó được chọn sẵn.

### 4.2 Chỗ bị kéo giãn

Với mỗi tư thế thử (trừ Về nghỉ), máy tính vị trí đỉnh của mọi phần bằng chính weight và tư thế xương (như modifier
Armature, không cần vẽ lại cảnh). Một cạnh lưới **bị kéo giãn** khi dài ra hơn 2,5 lần. Các cạnh kéo giãn nối nhau là một
chỗ; chỗ có từ 3 cạnh trở lên thì báo, theo vùng của nó: "Đầu bị kéo giãn ở tư thế Giơ tay (Body)". Nút **Xem**: đặt tư
thế đó và làm sáng chỗ đó (vẽ ở vị trí đã biến dạng); nút **Tô vùng**: tô vùng trên mô hình đó.

Không bắt được: một mảnh rời đi theo nhầm xương mà không bị kéo giãn (nó dời cả khối). Vùng cơ thể (spec vùng §5) đã chặn
phần lớn trường hợp này.

### 4.3 Vai trò có vẻ sai

Đoán theo hình, cho phần cả mô hình (phạm vi Cả object) đang là **Quần áo**:

- **Trông như tóc**: điểm cao nhất trên khớp đầu, điểm thấp nhất dưới khớp đầu (thõng xuống) nhưng trên khớp hông, và
  không bao quanh cổ (như mảnh gắn đầu, spec vùng §4.1). Mũ (nằm hết trên khớp đầu) không bị báo.
- **Trông như váy**: từ 80% đỉnh trở lên nằm giữa đầu gối và eo (đầu xương Spine), bao quanh hông (có đỉnh ở cả bốn phía
  quanh trục hông ở giữa độ cao), dải đáy có đỉnh ngay trước hoặc sau chính giữa (không tách thành hai ống như quần), và
  loe xuống (bán kính trung bình ở dải đáy lớn hơn dải đỉnh ít nhất 10%).

Báo "Circle.003 trông như váy", nút **Đổi thành Váy** (hay **Đổi thành Tóc**): đổi vai trò, dựng lại, kiểm tra lại.

## 5. Giao diện

Mục con **Kiểm tra** đứng đầu mục Rig anime (trước Khớp nối):

- hàng nút tư thế;
- trạng thái: "Chưa kiểm tra", "Không thấy chỗ nào cần sửa", hoặc danh sách chỗ cần xem (mỗi dòng: câu, nút);
- **Kiểm tra lại**, **Xong** (xóa danh sách, tắt chỗ đang làm sáng).

Chữ mới có bản Việt; tên khớp, vùng, tư thế trong câu cũng dịch.

## 6. Ngoài phạm vi

Tự sửa mà không hỏi; tư thế thử do người dùng tự định nghĩa; kiểm tra mặt (mắt, miệng); bắt mảnh rời đi theo nhầm xương
(§4.2).

## 7. Kiểm tra tự động

- Nhân vật thử chibi (của test vùng): tự rig từ menu cho rig dựng xong, mục Kiểm tra không báo gì; dời cổ tay trái ra
  ngoài thì báo đúng khớp đó; cho nửa tai theo xương tay thì báo kéo giãn ở Giơ tay, vùng Đầu; đặt mô hình váy (ống loe
  quanh hông) và tóc (dải thõng sau đầu) là Quần áo thì báo đúng hai vai trò; nút đổi vai trò dựng lại.
- Tư thế thử: Giơ tay đưa bàn tay lên cao hơn vai; Về nghỉ trả mọi xương về nghỉ; không tạo khóa hình.
- Giao diện: mục Kiểm tra vẽ đủ nút; mọi biểu tượng có thật; bản Việt.
- Mô hình thật: bản sao tdt, lr_shape: tự rig, đọc danh sách, chụp một ảnh mục Kiểm tra (một ngôn ngữ).
