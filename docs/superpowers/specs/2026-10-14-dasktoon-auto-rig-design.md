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
- **Hướng mặt** (thêm sau khi đo trên mô hình thật: lr_shape quay mặt về +Y nên khung bị dựng ngược, bên trái thành bên
  phải, gối gập ra trước). Trước khi khớp (cả ở nút Khớp theo các phần), bàn chân cho biết nhân vật quay về đâu: lấy đế
  chân (3% chiều cao sát sàn) so với cẳng chân ngay trên (6–12%), chia hai chân theo chiều chúng dàn ra. Chỉ tin khi cả
  hai chân cùng vươn quá cẳng chân ít nhất 1% chiều cao, lệch nhau không quá 45°, và mọi điểm đế chân nằm trong 12%
  chiều cao quanh cẳng chân (gấu váy dài hay bệ đứng thì không phải bàn chân). Nhân vật quay về +Y, +X hay −X (lệch
  không quá 30°) thì được xoay tại chỗ, quanh điểm giữa hai chân, để mặt nhìn về −Y như khung xương và Unity cần, kèm
  cảnh báo nói đã xoay bao nhiêu độ. Chỉ xoay các mô hình gốc trong số các phần (vật treo dưới chúng đi theo). Không rõ
  thì giữ nguyên. Đo: tdt vươn 2,8% chiều cao về −Y (giữ nguyên), lr 4,1% về +Y (xoay 180°). Điểm đế chân xa nhất của
  cả hai cách cẳng chân 8,5%.

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
Armature, không cần vẽ lại cảnh). Một cạnh lưới **bị kéo giãn** khi dài ra hơn 2,5 lần **và** hai đầu của nó theo những
xương cách nhau từ 4 bậc trở lên trong cây xương (*bổ sung khi làm*: khớp gập bình thường như nách, mông, gáy cũng kéo da
dài ra nhiều, nhưng giữa hai xương kề nhau; tai nửa theo đầu nửa theo tay thì giữa đầu và cánh tay, cách nhau 4 bậc),
**hoặc** dài ra hơn 2,5 lần và thêm hơn 2% chiều cao nhân vật dù giữa hai xương kề nhau (*sửa 2026-10-14*: hông tdt và
lr rách 19 và 26 lần khi Ngồi, dài thêm 11–16 cm, mà mục Kiểm tra không báo; khớp gập thường trên hai mô hình đó dài thêm
tối đa 2 cm. Nhân vật thử bằng các ống cắm vào thân nay được báo gốc tay, đùi trong rách 7 và 20 cm). Các
cạnh kéo giãn nối nhau, hay cách nhau dưới 5% chiều cao nhân vật (một vết rách có thể tách một vòng đỉnh làm hai), là một
chỗ; chỗ có từ 3 cạnh trở lên thì báo, theo vùng của nó: "Đầu bị kéo giãn ở tư thế Giơ tay (Body)". Nút **Xem**: đặt tư
thế đó và làm sáng chỗ đó (vẽ ở vị trí đã biến dạng); nút **Tô vùng**: tô vùng trên mô hình đó.

Không bắt được: một mảnh rời đi theo nhầm xương mà không bị kéo giãn (nó dời cả khối). Vùng cơ thể (spec vùng §5) đã chặn
phần lớn trường hợp này.

### 4.3 Vai trò có vẻ sai

Đoán theo hình, cho phần cả mô hình (phạm vi Cả object) đang là **Quần áo**:

- **Trông như tóc**: điểm cao nhất trên khớp đầu, điểm thấp nhất dưới khớp đầu (thõng xuống) nhưng trên khớp hông, và
  không bao quanh cổ (như mảnh gắn đầu, spec vùng §4.1). Mũ (nằm hết trên khớp đầu) không bị báo.
- **Trông như váy**: từ 80% đỉnh trở lên nằm giữa đầu gối và eo (đầu xương Spine), bao quanh hông (có đỉnh ở cả bốn phía
  quanh trục hông ở giữa độ cao), dải đáy là một vòng bao quanh trục hông (điểm gần trục nhất cách trục ít nhất nửa bán
  kính trung bình; hai ống quần thì mặt trong sát trục), và loe xuống (bán kính trung bình ở dải đáy lớn hơn dải đỉnh ít
  nhất 10%).

Báo "Circle.003 trông như váy", nút **Đổi thành Váy** (hay **Đổi thành Tóc**): đổi vai trò, dựng lại, kiểm tra lại.

## 5. Giao diện

Mục con **Kiểm tra** đứng đầu mục Rig anime (trước Khớp nối):

- hàng nút tư thế;
- trạng thái: "Chưa kiểm tra", "Không thấy chỗ nào cần sửa", hoặc danh sách chỗ cần xem (mỗi dòng: câu, nút);
- **Kiểm tra lại**, **Xong** (xóa danh sách, tắt chỗ đang làm sáng).

*Bổ sung khi làm*:

- Mỗi chỗ cần xem là một ô: câu và nút. Nút **Tô vùng** chỉ có khi chỗ đó nằm trên phần Cơ thể hay Quần áo, vì chỉ hai
  vai trò này có vùng.
- Chỗ đang xem được vẽ màu cam, xuyên qua mọi thứ (vì nó có thể nằm trong thân). Nó chỉ hiện khi rig còn ở đúng tư thế
  đó; bấm Tô vùng vẫn thấy nó trên mô hình đang tô.
- Phần đang chọn trong danh sách Các phần được làm sáng ở tư thế nghỉ, nên chỉ vẽ khi rig đang ở tư thế nghỉ.
- **Dựng rig** chạy lại Kiểm tra khi đang có danh sách, vì danh sách cũ là của rig trước lần dựng.
- **Đổi thành Tóc/Váy** bỏ các lọn mà Nhận diện đã tạo trên mô hình đó, vì mảnh của nó không còn là lọn của Cơ thể
  hay Quần áo.

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
