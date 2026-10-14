# DaskToon: vai nâng theo tay — Thiết kế

Người dùng hỏi (2026-10-14, kèm ảnh cắt từ tư thế vẫy tay): "là do model hay rig nó vai gãy?". Trả lời: do rig. Khi giơ
tay chỉ cánh tay trên xoay quanh khớp vai, xương vai (xương đòn) đứng yên, nên đỉnh vai bẹp và nách thành góc gập. Render
cận vai của tdt cho thấy nâng thêm xương vai khoảng 25° khi tay giơ cao thì nách mềm, vai tròn. "Giữ thể tích" của
modifier Armature gần như không đổi gì (và Unity không dùng). Người dùng giao: "tự lm" (tự quyết, tự làm).

## 1. Hành vi

- Khi cánh tay trên giơ quá một độ cao, xương vai cùng bên tự nâng lên. Góc nâng tăng đều theo độ cao của cánh tay:
  - bắt đầu khi cánh tay ở 30° dưới đường ngang;
  - tới **35°** khi tay giơ thẳng đứng;
  - tỉ lệ khoảng 1 : 3,4, gần nhịp vai thật (xương bả vai xoay khoảng một phần ba cánh tay).
- Tư thế nghỉ không đổi: với nhân vật tư thế T (tay ngang sẵn), vai bắt đầu nâng ngay khi tay giơ lên.
- Chỉ phần **giơ sang ngang** được tính. Tay xoay quanh chính nó hay đưa ra trước, ra sau không làm vai nâng.
- Khóa hình bạn đặt cho xương vai vẫn có tác dụng; phần tự nâng được cộng thêm vào.
- Một thanh trượt **Vai nâng theo tay** (0–1, mặc định 1) trong mục Rig anime › Khớp nối. 0 là tắt.

## 2. Cách làm

- Mỗi bên một xương phụ ẩn `LeftShoulderLift`, `RightShoulderLift`:
  - cùng tư thế nghỉ với xương vai, cùng cha;
  - không biến dạng mesh, không vào FBX;
  - mang dấu riêng nên Dựng rig không xóa nó.
- Một driver xoay xương phụ quanh trục nâng vai.
  - Driver đọc góc giơ ngang của cánh tay trên từ chính giá trị xoay của cánh tay đó (không gồm cha), nên không thành
    vòng lặp với xương vai là cha của cánh tay.
  - Biểu thức chỉ dùng phép tính và `min`, `max`, nên chạy được cả trong file chưa cho phép chạy script.
- Xương vai có ràng buộc Copy Rotation `DaskToon Shoulder Follow`:
  - chép xoay của xương phụ, trong không gian cục bộ, cộng trước phần khóa hình;
  - độ ảnh hưởng là giá trị Vai nâng theo tay.
- Trục giơ của cánh tay và trục nâng của vai được tính lúc Dựng rig, từ tư thế nghỉ (hướng xương và trục lên của rig).
- Dựng rig tạo hoặc cập nhật tất cả các thứ trên; dựng lại không nhân đôi.

## 3. Unity và mục Kiểm tra

- Xuất clip ghi lại tư thế đã tính xong từng khung hình, nên xương vai trong FBX có sẵn góc nâng. Unity không cần
  ràng buộc nào.
- Tư thế thử của mục Kiểm tra (Giơ tay, Vẫy tay) tự có vai nâng, vì biến dạng được tính từ tư thế đã có ràng buộc.

## 4. Ngoài phạm vi

- Chỉnh weight quanh đỉnh vai: đo lại sau khi có vai nâng, chưa cần thì để sau.
- Vai nâng khi đưa tay ra trước hoặc ra sau.
- Hoạt hình làm thẳng trong Unity: Unity tự xử lý vai theo cách của nó.

## 5. Kiểm tra tự động

- Giơ tay thì vai nâng đúng góc (ví dụ Giơ tay của nhân vật thử: khoảng 26°) và về nghỉ thì hết.
- Thanh trượt 0 thì không nâng, 0,5 thì nâng một nửa; khóa hình vai vẫn tác dụng.
- Biểu thức driver là biểu thức đơn giản (không cần Python); dựng lại không nhân đôi xương phụ, ràng buộc, driver.
- Xuất FBX có hoạt hình rồi nhập lại: xương vai trong file có góc nâng ở khung hình tay giơ; xương phụ không có trong file.
- Giao diện: thanh trượt trong mục Khớp nối, có bản Việt.
