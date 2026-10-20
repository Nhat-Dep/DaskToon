# Bộ ảnh kiểu game: Tóc, Thân, Mặt (phần 1) (2026-10-20)

Người dùng hỏi UV đã tối ưu cho texture chưa, rồi nói rõ: "đầu ra của texture và UV khi export cũng giống các model của
các game lớn", "kiểu Wuwa với Zzz". Các game đó: ít bộ ảnh theo bộ phận (Tóc, Thân, Mặt), mỗi bộ một ô UV xếp kín,
mảng đứng thẳng, độ nét đều, mặt nét hơn, đối xứng chồng nhau; mỗi bộ có ảnh màu, ảnh điều khiển nhiều kênh, dải màu
bóng; mặt có ảnh bóng mặt. Chia bốn phần; người dùng chọn "chỉ phần 1 trước, tính sau": bộ ảnh theo bộ phận và UV kiểu
game. Thiết kế duyệt trong trò chuyện, "Duyệt, làm tự động". Dựa trên Trải UV anime
(`2026-10-20-dasktoon-anime-unwrap-design.md`).

## 1. Bộ ảnh

Nhân vật có khung DaskToon. Mỗi mặt lưới thuộc một bộ:

- **Tóc**: đỉnh thuộc phần có vai trò Tóc của khung (cả các lọn).
- **Mặt**: mặt có nhãn đầu (vùng đầu của cơ thể, các mảnh trên đầu như mắt, miệng, lông mày), không phải tóc.
- **Thân**: mọi mặt còn lại (da, quần áo, giày, phụ kiện).

Không có khung thì không chia bộ: Trải UV anime làm như trước (theo vật liệu).

## 2. UV kiểu game

Như Trải UV anime (đường cắt, trải ít méo, đối xứng) và thêm:

1. **Mảng đứng thẳng**: mỗi mảng xoay để hướng lên của nhân vật chỉ lên trên ảnh (tay: vai ở trên, bàn tay ở dưới);
   xếp không xoay nữa.
2. **Một ô UV mỗi bộ**, gồm mọi vật liệu và mọi lưới của bộ.
3. **Độ nét**: Tóc và Thân cùng một độ nét (điểm ảnh trên mét); Mặt gấp đôi. Bộ cần nhiều nhất trong Tóc và Thân được
   2048; cỡ mỗi bộ là luỹ thừa của 2 đủ cho độ nét đó (256 đến 2048). Khe giữa mảng 8 điểm ảnh của đúng cỡ đó.

## 3. Ảnh màu chung

Mỗi bộ một ảnh màu `<khung> <Bộ> Color` đúng cỡ. Mỗi mặt lưới được tô màu nền vật liệu của nó: ảnh nối vào Màu nền
thì lấy theo UV cũ, từng điểm ảnh; màu phẳng thì tô phẳng. Rồi ô Màu nền của mỗi vật liệu đọc ảnh chung (nút ảnh mới;
nút cũ giữ lại, không nối). Ảnh ở các ô khác được chuyển sang UV mới như Trải UV anime.

Mặt đang dùng chung vật liệu với phần thuộc bộ Thân thì được tách sang bản sao vật liệu `<tên> Face`.

## 4. Giao diện

Trải UV anime thêm lựa chọn **Ảnh**: *Theo bộ phận (kiểu game)*, mặc định khi có khung; *Theo vật liệu* như trước.

## 5. Kiểm thử

Chạy nền trên nhân vật thử của vùng cơ thể, thêm một lọn tóc (vai trò Tóc) và vật liệu khác màu:

- mặt lưới vào đúng bộ;
- mỗi bộ trong ô, không chồng nhau ngoài tay chân đối xứng;
- mảng đứng thẳng;
- mặt nét gấp đôi thân (tính cả cỡ ảnh);
- cỡ ảnh là luỹ thừa của 2;
- ảnh màu chung đúng màu từng vật liệu;
- Màu nền nối ảnh chung;
- mặt tách vật liệu.

Model thật: xem tận mắt như lần trước.

## 6. Quyết định (tự động)

1. Không có khung thì không chia bộ: Tóc và Mặt chỉ biết được qua khung.
2. Màu nền lấy từ ảnh nối thẳng, hoặc ảnh đầu tiên phía trước nó, hoặc nút màu RGB; còn lại là màu của ô. Chưa nướng các
   chuỗi nút màu phức tạp.
3. Cỡ ảnh làm tròn lên luỹ thừa của 2: độ nét không bao giờ thấp hơn mức chung, có thể cao hơn tới hai lần.
4. Mặt nét gấp đôi thân, thay cho 1,5 lần của Trải UV anime theo vật liệu.
5. Bàn chân, mảng phẳng có hướng lên không rõ thì giữ hướng sau khi trải.
