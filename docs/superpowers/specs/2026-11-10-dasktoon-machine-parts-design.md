# DaskToon: Rig cơ khí, phần 2 (pít-tông, nối khớp: bánh răng, cần gạt) — Thiết kế

Ngày 2026-11-10, chế độ tự động (người dùng: "ok tự động đến 8h"). Phần 1:
`2026-11-10-dasktoon-machine-rig-design.md` (mảnh cứng, khớp, chân IK, ngắm). Người dùng đã chọn **chi tiết máy:
pít-tông và xi-lanh tự co duỗi theo khớp, bánh răng ăn khớp nhau, bản lề cửa / nắp, cần gạt**. Bản lề và giới hạn đã
có ở phần 1; phần này thêm hai thứ dựa trên các khớp đó. Mọi quyết định do Claude, ghi ở §6.

## 1. Người dùng thấy gì

Bảng **Rig cơ khí** có thêm hai mục con:

- **Pít-tông**: danh sách các pít-tông (xi-lanh ↔ cần đẩy, nút gỡ). Nút **Nối thành pít-tông**: chọn hai khớp (chế
  độ Tư thế: khớp đang chọn là xi-lanh, khớp chọn kèm là cần đẩy). Gợi ý: "Gắn khớp cho xi-lanh và cần đẩy trước (công
  cụ đoán chốt), rồi chọn cả hai".
- **Khớp nối**: danh sách (khớp dẫn → khớp theo, tỉ lệ sửa được, nút gỡ). Nút **Nối khớp**: khớp đang chọn là khớp
  dẫn, các khớp chọn kèm là khớp theo.

## 2. Pít-tông

Hai khớp X (xi-lanh, con của khớp A) và R (cần đẩy, con của khớp B ≠ A). Tâm của chúng là hai chốt.

- Hai xương phụ ẩn (không biến dạng, bộ sưu tập "Machine Helpers"): `MCH-<X>` con của B đặt ở đầu R, `MCH-<R>` con
  của A đặt ở đầu X. Không có vòng phụ thuộc: mỗi xương phụ chỉ theo cha của nó.
- X và R được xoay lại lúc dựng cho trục Y nhìn vào nhau (X nhìn tới đầu R, R nhìn tới đầu X), giữ trục X (trục khớp)
  vuông góc nếu được; Damped Track (Y) của X tới `MCH-<X>`, của R tới `MCH-<R>`. Loại khớp của X, R thành Cố định (người
  dùng không xoay tay chúng); hình điều khiển ẩn.
- Thuộc tính `dt_piston` trên X = tên R. Gỡ: bỏ ràng buộc, xương phụ, trả loại khớp cũ (Bản lề).
- Lỗi: hai khớp cùng cha ("Xi-lanh và cần đẩy phải gắn vào hai khớp khác nhau"), không đủ hai khớp được chọn.

## 3. Khớp nối (bánh răng, xích, cần gạt)

Khớp dẫn D, khớp theo F (bản lề hoặc trượt, không phải khớp cầu / cố định).

- Giá trị: bản lề = góc quay X (Euler), trượt = dời X. F.giá trị = tỉ lệ × D.giá trị, bằng driver biểu thức đơn
  giản `v * r` (`v` = giá trị của D, `r` = thuộc tính `dt_link_ratio` của F) — không cần cho phép chạy Python.
- **Tỉ lệ tự tính** khi cả hai là bản lề có trục song song (lệch < 10°) hoặc vuông góc (bánh răng côn):
  - bán kính r của mỗi khớp = khoảng xa nhất từ trục tới các đỉnh của mảnh (quanh trục).
  - **Ăn khớp** (hai mảnh chạm nhau, hoặc khoảng cách hai trục ≤ 1,1 × (r_D + r_F)): tỉ lệ = −r_D / r_F (quay ngược).
  - **Không chạm** (xích, dây đai, bánh xe cùng xe): tỉ lệ = r_D / r_F (cùng chiều).
  - Trục song song nhưng ngược hướng (X của F = −X của D) → đổi dấu, để chiều quay thật đúng như trên.
  - Còn lại (bản lề ↔ trượt: cần gạt, thanh răng; trục chéo): tỉ lệ 1, người dùng sửa.
- Thuộc tính `dt_link` trên F = tên D. F bị khóa quay tay (driver điều khiển). Gỡ: xóa driver, bỏ thuộc tính.
- Lỗi: nối vào chính nó, F đã có khớp dẫn, vòng (D theo F).

## 4. Mã

- `scripts/modules/dasktoon_machine/linkage.py`: `piston_add/remove/pistons`, `link_add/remove/links`, `ratio`.
- `bl_ui/dasktoon_machine.py`: toán tử + hai bảng con; tiếng Việt.
- Gỡ khớp (phần 1) gỡ luôn pít-tông / khớp nối dùng nó.

## 5. Kiểm thử (`tests/python/dasktoon_machine_test.py`, máy giả)

- Pít-tông: thêm vào máy giả một chân có xi-lanh (ống trụ có chốt trên thân) và cần đẩy (thanh trụ có chốt trên đùi).
  Gập đùi → xi-lanh và cần đẩy vẫn nằm trên một đường (trục Y của hai xương song song, ngược chiều, < 0,5°), chốt
  không rời (đầu xương xi-lanh vẫn ở chỗ cũ trên thân), phần trùng của cần trong xi-lanh đổi theo; tư thế nghỉ lệch 0.
- Bánh răng: hai bánh răng trụ chạm nhau bán kính 0,1 và 0,05 → tỉ lệ −2; quay D 30° → F quay −60°. Bánh xe cùng xe (không
  chạm) → tỉ lệ +1. Bản lề ↔ trượt → 1. Sửa `dt_link_ratio` → driver theo. Vòng bị chặn.
- Gỡ khớp dẫn → khớp nối gỡ theo.
- Bảng vẽ không lỗi; dịch đủ.

## 6. Quyết định của Claude

1. Pít-tông dựng từ **hai khớp có sẵn** thay vì công cụ riêng: dùng lại công cụ nhấp và phần đoán chốt của phần 1.
2. Xương phụ kiểu Rigify (đích đặt trên khớp cha của bên kia) để không có vòng phụ thuộc.
3. Khớp nối bằng driver biểu thức đơn giản với tỉ lệ là một thuộc tính sửa được — không cần cho phép script.
4. Ăn khớp đoán bằng chạm nhau / khoảng cách trục ≤ 1,1 × tổng bán kính; ngược lại coi là xích / cùng xe.
5. Không làm (phần 2): liên kết bốn khâu khép kín, xích xe tăng chạy quanh bánh, bánh răng đếm răng (dùng bán kính).
