# DaskToon: shape key tự động (sửa chỗ gập, lấp biểu cảm, nặn mắt) — Báo cáo

Làm tự động đêm 2026-10-20 trên `dasktoon-master`, từng phần chạy thử đạt thì đẩy lên GitHub. Thiết kế:
`docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md` và
`docs/superpowers/specs/2026-10-20-dasktoon-auto-expressions-design.md`.

Mọi phép thử trên model thật đều làm trên bản sao (các file trong `D:\game` chỉ được đọc), hình chụp nhân vật không đưa
vào git.

## 1. Sửa chỗ gập (d166f52)

**Dựng rig** giờ tự tạo thêm 8 shape key `DT_Fix_...`: đầu gối (cẳng chân gập ra sau), khuỷu tay (cẳng tay gập ra
trước), hông (đùi đưa ra trước, tư thế ngồi), vai (hạ tay xuống; bỏ qua nếu tay vốn đã buông gần thẳng xuống), mỗi thứ
hai bên. Ở tư thế đó, đỉnh nằm giữa hai xương được xoay quanh khớp theo phần trọng số của nó, thay vì bị kéo thẳng
giữa hai vị trí, nên khớp không bị móp.

- Driver không cần Python: đọc góc "swing" của xương con so với xương cha. Đi dọc cung gập thì giá trị tăng đúng theo
  góc, gập sâu hơn thì giữ ở 1, đưa chân sang ngang hay ra sau thì về 0.
- Unity: rig.json có thêm `correctives`; script mới `DaskToonCorrective` tính cùng công thức trong LateUpdate (bộ
  script phiên bản 6). Bài kiểm tra Unity: 8 tư thế, trọng số Unity khớp driver DaskToon trong khoảng 0,01; hướng
  đúng theo chính bàn chân của model (gối ra sau, hông và khuỷu ra trước, vai xuống).
- **Key Pose** bỏ qua shape key do driver điều khiển.
- Tắt được bằng ô **Sửa chỗ gập** trong Rig anime › Khớp.

Trên tdt (bản sao), gập 90°: gối tròn lại, mông và hông đầy hơn, khe ở gấu quần khép lại; khuỷu và vai đổi ít (vùng
trộn trọng số ở đó hẹp). lr_shape (bản sao) cũng vậy: mặt trước gối tròn đầy, mông và đùi khi ngồi mượt hơn. Thời
gian thêm vào Dựng rig: 0,8 giây cho tdt (20 nghìn đỉnh).

## 2. Lấp biểu cảm còn trống (aec60ec)

Nút **Lấp biểu cảm còn trống** trong Hình mẫu › Bộ biểu cảm. Biểu cảm không dịch chuyển gì, hoặc dưới 15% mức thường
của lưới đó, được dựng từ những cái có:

- cùng biểu cảm nhưng tên chuẩn khác (VRM 0.x / 1.0 / VRoid / ARKit);
- "e" = nửa "a" + nửa "i";
- nháy từng mắt từ nháy hai mắt, và ngược lại;
- môi trên từ phần "i" nâng lên, môi dưới từ phần "a" hạ xuống.

"neutral" giữ trống (chuẩn VRM). Trên tdt: "e" (trước chỉ dịch 0,9 mm) thành miệng hé giữa "a" và "i";
"mouthUpperUp" ra rất nhẹ vì "i" của tdt gần như không nâng môi.

Bên trái/phải lấy theo rig của nhân vật (5faf0bb): filie quay mặt về +Y trong cảnh, nếu lấy theo trục X của lưới thì
"blink_L" sẽ nhắm nhầm mắt phải.

## 3. Nặn biểu cảm mắt (d212bf1, 7e55a7e)

Nút **Nặn biểu cảm mắt** cùng chỗ. Cả ba model chưa có shape key (pl1, RGforGame, filie) đều làm mắt bằng các mảnh rời
trước mặt (lòng trắng, tròng, mi). Nút tìm hai nhóm mảnh đó và tạo:

- **blink**: ép dẹt về một vạch ở 1/3 chiều cao;
- **blink_L**, **blink_R**: từng bên;
- **joy**: nhắm thành vòng cung "^^";
- **surprised**: to thêm 12%.

Da mặt ngay dưới mắt cũng co theo, vì pl1 vẽ lòng trắng lên da. Tóc và quần áo không bị động tới. Mặt có hốc mắt (kiểu
tdt) thì để nguyên.

Kết quả trên bản sao: cả ba nhắm thành vạch gọn, nháy một bên đúng bên, "^^" rõ ở pl1 và filie.

Miệng vẽ trên da (pl1): nút đọc ảnh da mặt qua UV để tìm vệt miệng, rồi cho **joy** nhếch hai khoé lên thành nụ
cười. Phải đọc trên lưới đã chia nhỏ (Subdivision) và chỉ lấy phần nhìn thấy từ phía trước, vì pl1 có khoang miệng màu
hồng nằm khuất sau mặt. Miệng há ("a") không làm được với miệng vẽ: kéo giãn vệt vẽ chỉ làm nó biến mất (đã thử). Với
miệng vẽ, dùng **miệng 2D** sẵn có cho A I U E O.

## 4. Bản build bằng Visual Studio 2026

Build lại toàn bộ DaskToon bằng VS 2026 vào thư mục mới `D:\build_windows_x64_vc18_Release`, mất khoảng 1 tiếng,
không lỗi. Thư mục cũ (vc17) giữ nguyên.

Nhờ vậy nhánh để riêng `dasktoon-spring-collide-on-reset` (lò xo đẩy ra khỏi vùng va chạm ngay ở khung đầu) lần đầu
được build và thử:

- RG2 (bản sao) ngồi ở khung đầu: bản cũ có 4 điểm của váy nằm trong đùi (sâu nhất 4,9 cm), bản mới không còn điểm
  nào; váy phủ lên đùi thay vì xuyên qua.
- Bài kiểm tra viết sẵn trên nhánh hóa ra sai: khối va chạm đi đúng qua trục, kết quả C++ bị đọc sau khi lò xo đã tạm
  tắt, và đòi ra hẳn trong khi đẩy xong còn giữ độ dài xương. Mã C++ thì đúng.
- Đã sửa bài kiểm tra: bản cũ trượt, bản mới đạt. Bài "váy sau gần như đứng yên" nay chỉ xét dải trong khoảng ±30°
  quanh chính sau lưng.
- Đã gộp master vào nhánh, cả bộ kiểm tra đạt trên bản VS 2026, đã đẩy lên GitHub (0807fb6).
- **Chưa gộp vào master**: chờ bạn quyết. Bản cài VS 2026 hiện đang chứa bản sửa này; bản vc17 không có.

## Các quyết định đã tự chọn

| Quyết định | Nếu sai thì sao |
|---|---|
| Mỗi khớp một tư thế sửa (90°; vai: tay xuống), giữ ở 1 khi gập sâu hơn | Quỳ sâu trông như gập 90°; thêm tư thế sau |
| Hình sửa là "xoay theo phần trọng số", không nặn tay | Khuỷu tay ít thay đổi trên lưới có vùng trộn hẹp |
| Khuỷu gập ra trước, gối ra sau, hông ra trước | Rig quy ước khác thì phần sửa không bật, không làm hỏng hình |
| Sửa chỗ gập bật sẵn, chạy trong Dựng rig | Dựng lại sẽ ghi đè nếu đã sửa tay các shape key đó |
| "Gần như trống" (dưới 15%) cũng tính là trống | Shape key cố ý làm nhẹ có thể bị thay; nút hoàn tác được và có báo tên |
| Nặn mắt bằng ép dẹt, kéo cả da dưới mắt | Quanh mắt nhắm hơi phẳng đi (thấy dưới đèn studio, không thấy với đổ bóng toon) |
| Lấp và nặn là nút bấm, không tự chạy khi gắn khung | Phải bấm tay một lần |
| Miệng: chỉ nụ cười cho joy khi miệng vẽ trên da; không làm miệng há | A I U E O vẫn cần nặn tay hoặc dùng miệng 2D |

## Kiểm tra

Cả bộ kiểm tra DaskToon đạt (chạy lại shading/upgrade sau khi khôi phục tệp mẫu, như mọi lần). Unity: smoke, rig,
face, clips, model và correctives đều đạt. Bài kiểm tra mới: `dasktoon_rig_correctives_test`,
`dasktoon_unity_correctives_test`, `dasktoon_expressions_fill_test`, `dasktoon_expressions_eyes_test`.

Giao diện chụp trong cửa sổ thật (tiếng Việt, nhân vật mẫu; công cụ `tools/dasktoon_auto_shape_keys_screenshots.py`):

- `auto-shape-keys/vi/100_bend_fixes.png`: Rig anime › Khớp nối với ô **Sửa chỗ gập**, gối trái đang gập.
- `auto-shape-keys/vi/101_expression_sets.png`: Hình mẫu › Bộ biểu cảm với **Lấp biểu cảm còn trống** và **Nặn
  biểu cảm mắt**; joy đang bật.

Lần chụp này bắt được một lỗi mà chạy nền không thấy: trong DaskToon 5.2, shape key mới tạo có giá trị 1, nên sau
khi nặn mọi biểu cảm đều bật cùng lúc (và sang Unity sẽ ở mức 100). Đã sửa: shape key do hai nút tạo hoặc lấp đều về 0.
