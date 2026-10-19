# DaskToon: nhận diện rig phần 3, ngón tay — Thiết kế

Làm tự động ngày 2026-10-19 (người dùng giao "tự làm liên tục, cần hỏi thì ghi lại"). Các quyết định dưới đây là của
Claude, chờ người dùng xem lại.

## Chuyện gì xảy ra

Tự gắn khung đặt ngón tay theo khung mẫu: cả cánh tay mẫu được xoay và co giãn cho đầu ngón giữa trùng đầu bàn tay tìm
được, rồi các khớp tay được đưa vào giữa tay. Trên model thật (filie, lr_shape, chụp gần bàn tay trái):

- xương ngón cái chĩa ra ngoài bàn tay, xa ngón cái thật;
- bốn ngón còn lại ngắn hơn ngón thật, đầu xương không tới đầu ngón;
- ngón nào cũng thẳng theo khung mẫu, không theo hướng ngón thật đang xòe.

## Cách làm

1. **Bàn tay**: các đỉnh của lưới Thân nằm phía trước cổ tay (theo hướng cẳng tay), không xa hơn 1,6 lần chiều dài bàn tay
   mẫu. Ba trục chính của chúng: dọc bàn tay (gần hướng cẳng tay nhất), ngang lòng bàn tay, và bề dày (trục mỏng nhất).
2. **Hình bàn tay**: các đỉnh và tam giác được trải lên mặt phẳng lòng bàn tay rồi vẽ thành lưới điểm ảnh, cùng cách vẽ
   hình nhìn trước của thân (`body_shape`).
3. **Đầu ngón**: đi từ chỗ cổ tay trên hình; đầu ngón là những điểm xa nhất so với xung quanh (cực đại cục bộ của quãng
   đường đi). Cần đúng 5 đầu ngón cách nhau rõ.
4. **Gốc ngón**: từ mỗi đầu ngón đi ngược lại cho tới chỗ bề rộng phình ra (ngón nối vào lòng bàn tay), cùng cách tìm tay
   chân của `body_shape.Shape.limb`.
5. **Ngón nào**: xếp theo hướng ngang lòng bàn tay; đầu bên phía trước nhân vật (−Y) là ngón cái, rồi trỏ, giữa, áp út,
   út.
6. **Khớp**: trên đường từ gốc tới đầu ngón, khớp đốt 1 ở gốc, đốt 2 ở 45%, đốt 3 ở 75%, đầu đốt 3 ở đầu ngón. Độ sâu
   (theo bề dày) là giữa bề dày bàn tay quanh điểm đó.
7. **Đối xứng**: tìm cả hai tay rồi lấy trung bình (một bên lật qua), vì rig đối xứng. Chỉ một tay tìm được thì tay kia
   lật theo.
8. **Không chắc thì để nguyên**: không đủ 5 ngón (tay nắm, găng tay liền ngón, tay chibi tròn), hoặc ngón quá ngắn hay quá
   dài so với bàn tay, thì ngón giữ như hiện nay.

## Quyết định (cần hỏi lại)

- Chỉ đọc lưới Thân (da), không đọc găng tay hay quần áo. Găng tay là lưới riêng sẽ đi theo xương tìm được trên da.
- Ngón cái là ngón phía trước nhân vật: đúng với tư thế chữ T và chữ A úp lòng bàn tay xuống, là cách dựng model phổ biến.
  Tay ngửa lòng bàn tay thì sai.
- Tỷ lệ đốt 45% / 30% / 25%.
- Tìm không ra thì im lặng giữ khung mẫu, không thêm mục vào bản Kiểm tra (để sau).
