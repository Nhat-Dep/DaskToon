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

Kết quả trên bản sao: cả ba nhắm thành vạch gọn, nháy một bên đúng bên, "^^" rõ ở pl1 và filie. Miệng chưa làm: pl1
vẽ miệng, filie miệng là mảnh nhỏ. Với miệng vẽ phẳng, dùng **miệng 2D** sẵn có.

## 4. Bản build bằng Visual Studio 2026

Build lại toàn bộ DaskToon bằng VS 2026 vào thư mục mới `D:\build_windows_x64_vc18_Release`, mất khoảng 1 tiếng,
không lỗi. Bản này chạy được các bài kiểm tra (gồm cả constraint lò xo C++). Thư mục cũ (vc17) giữ nguyên.

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
| Chỉ mắt, chưa làm miệng | Miệng vẫn cần nặn tay hoặc dùng miệng 2D |

## Kiểm tra

Cả bộ kiểm tra DaskToon đạt (chạy lại shading/upgrade sau khi khôi phục tệp mẫu, như mọi lần). Unity: smoke, rig,
face, clips, model và correctives đều đạt. Bài kiểm tra mới: `dasktoon_rig_correctives_test`,
`dasktoon_unity_correctives_test`, `dasktoon_expressions_fill_test`, `dasktoon_expressions_eyes_test`.

Chưa làm: chụp giao diện trong cửa sổ thật (ô **Sửa chỗ gập**, hai nút mới). Màn hình đã tắt trong đêm. Đây chỉ là một
ô và hai nút đặt vào các bảng có sẵn, bài kiểm tra bố cục đã chạy qua.
