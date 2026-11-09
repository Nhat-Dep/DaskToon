# DaskToon: Rung mềm (bộ biến đổi Jiggle) — Thiết kế

Ngày 2026-11-10. Người dùng hỏi: "thêm vật lý jiggle, kiểu một vật va chạm với cái bánh pudding". Đã chọn (câu hỏi):
dùng cho **cả đồ vật mềm lẫn phần mềm trên người**, làm **bộ biến đổi mới trong lõi** (không bake, như lò xo xương),
**chỉ trong DaskToon** (không cần Unity/Godot), và **làm luôn va chạm với chính mình** (tay nhân vật ấn vào bụng/má
của nó). Sau đó "Duyệt" ở chế độ tự động: các chi tiết dưới đây do Claude quyết, ghi ở §10.

## 1. Người dùng thấy gì

- Bộ biến đổi **Rung mềm** (tên gốc `Jiggle`, kiểu `JIGGLE`), ở menu Thêm bộ biến đổi › Biến dạng.
- Nút **Thêm rung mềm** trong menu chuột phải của vật (chế độ Vật và chế độ Chỉnh sửa):
  - Chế độ Chỉnh sửa, có chọn đỉnh: tạo nhóm đỉnh `DT_Jiggle` từ vùng chọn, mép mờ dần ra ngoài (§6), mẫu theo vật
    (có khung xương: "Thịt mềm"; không: "Bánh pudding").
  - Chế độ Vật, vật không có khung xương: cả vật rung, mẫu "Bánh pudding", bật **Giữ đáy**.
  - Chế độ Vật, vật có khung xương mà không chọn vùng: báo "Chọn vùng cần rung trong chế độ Chỉnh sửa".
  - Đặt ngay sau bộ biến đổi xương / Shape Key cuối cùng, trước các bộ biến đổi tạo hình (Subdivision, viền...).
  - Có khung xương DaskToon: gắn khung xương và chép vật va chạm của rig, thêm hai vật va chạm bàn tay (§5).
- Nút **Cho vật này va chạm**: bật Va chạm (Collision) cho các vật đang chọn.
- Bảng của bộ biến đổi: Mẫu (menu), Nhóm đỉnh, Giữ đáy; Rung: Tốc độ rung, Độ tắt dần, Độ lan, Giữ thể tích, Theo
  chuyển động, Độ chính xác; Va chạm: Bộ sưu tập, Khoảng cách, Khung xương, số vật va chạm của khung xương.
- Mẫu: Bánh pudding, Thạch, Ngực, Thịt mềm (bụng, đùi), Má.

## 2. Cách tính (mỗi khung hình)

Mọi thứ tính trong không gian thế giới. `g_i` là chỗ của đỉnh sau các bộ biến đổi trước (đích), `w_i` ∈ [0, 1] là độ
tự do (nhóm đỉnh × Giữ đáy). `w_i = 0`: đỉnh đi đúng theo đích. Mỗi khung chia thành `n` bước nhỏ (Độ chính xác),
đích nội suy thẳng từ khung trước tới khung này.

1. **Theo chuyển động** `f`: trước khi bước, dời mọi đỉnh thêm `f × (g_mới − g_cũ)`; f = 1 thì vật chỉ rung khi bị
   chạm, f = 0 thì phần mềm chạy trễ hết cỡ.
2. **Lò xo về đích** (bán ẩn): `a = −ω_i²(p − g) − 2ζω_i(v − v_g)`, `ω = 2π × Tốc độ rung`, `ω_i² = ω² / w_i` (đỉnh ít
   tự do thì cứng hơn), kẹp `ω_i h ≤ 1,5` cho khỏi nổ. `v_g` là vận tốc của đích: vật đi đều thì không bị cản.
3. **Độ lan**: kéo độ lệch `d_i = p_i − g_i` về trung bình độ lệch của các đỉnh kề (theo cạnh), nhân `w_i`. Chỗ lõm lan
   ra thành hõm tròn, sóng chạy trên mặt.
4. **Giữ thể tích** theo từng mảnh liền (theo cạnh): `V` tính theo tam giác (định lý phân kỳ), đích là thể tích của
   đích. Bù bằng cách đẩy các đỉnh tự do theo pháp tuyến (gradient của V, trọng số `w_i`), nhân Giữ thể tích.
5. **Va chạm** (§5): đẩy đỉnh ra ngoài vật va chạm, cách mặt `Khoảng cách`.
6. Vận tốc `v = (p − p_trước)/h`.

An toàn: đích nhảy xa hơn đường chéo hộp bao của vật trong một khung (cắt cảnh, dịch chỗ) thì bắt đầu lại; độ lệch
`|p − g|` kẹp ở 25% đường chéo trước khi va chạm.

## 3. Bộ nhớ khung hình (không bake)

Như ràng buộc lò xo: bộ nhớ chung, khóa theo UID phiên của vật gốc + tên bộ biến đổi.

- Khung đầu cảnh: luôn bắt đầu lại (đỉnh ở đích, đứng yên).
- Khung kế tiếp của một khung đã tính đúng: một bước, "đúng".
- Đã có khung này, "đúng", cùng đầu vào: dùng lại (kéo lùi thời gian ra y như cũ).
- Nhảy cóc: đi tiếp từ trạng thái gần nhất phía trước (tối đa 300 khung), đích nội suy từ đó tới đích hiện tại:
  "gần đúng". Lần sau chạy liền qua khung đó thì tính lại cho đúng.
- Đầu vào khác (sửa hoạt hình, sửa thanh chỉnh, khác số đỉnh): xóa và bắt đầu lại ở khung này.
- Giữ: khung vừa tính, khung trước nó, và mốc mỗi 10 khung (tối đa 32 mốc, bỏ mốc xa khung hiện tại nhất).
- Khung lẻ (làm mờ chuyển động): nội suy từ khung nguyên trước theo vận tốc, không ghi bộ nhớ.

## 4. Chỗ nào rung

- Nhóm đỉnh (có nút đảo). Không đặt nhóm: mọi đỉnh tự do.
- **Giữ đáy**: nhân thêm `t = (z − z_min)/(z_max − z_min)` theo trục Z của vật (từ hình đầu vào), đáy đứng yên.

## 5. Va chạm

- **Vật có Va chạm (Collision)** trong cảnh, hoặc chỉ trong Bộ sưu tập nếu đặt. Dùng tam giác của vật va chạm ở
  khung hiện tại. Đỉnh ở phía trong (theo pháp tuyến của tam giác gần nhất) hoặc gần hơn Khoảng cách thì đẩy ra.
  Đỉnh mà **đích** đã nằm trong vật va chạm thì bỏ qua vật đó (bánh hơi lún vào đĩa không bị bắn lên).
- **Khung xương** (va chạm với chính mình): các khối trụ tròn đầu (capsule) dọc xương, bán kính theo đơn vị khung
  xương (như lò xo). Mỗi vật va chạm: xương đầu, xương cuối (trống = cùng xương), bán kính.
  - Bỏ qua khối của xương đang kéo đỉnh đó (nhóm đỉnh trùng tên xương, trọng số > 0,05): ngực không bị khối Chest
    đẩy, bụng không bị khối Spine đẩy.
  - Bỏ qua khối mà đích đã nằm trong.
  - Thêm rung mềm chép vật va chạm của rig (`rig.data.dasktoon_rig.colliders`) và thêm hai khối **bàn tay** (từ đầu
    xương Hand tới đầu ngón dài nhất; bán kính = 0,9 × khoảng cách trung bình của các đỉnh thuộc bàn tay tới trục,
    không có thì 0,35 × chiều dài bàn tay). Dựng rig lại thì đồng bộ lại.

## 6. Mép mờ của vùng chọn

Trọng số 1 trong vùng chọn, ra ngoài giảm dần theo khoảng cách trên mặt (theo cạnh) tới 0 ở khoảng `0,5 ×` bán kính
vùng (bán kính = khoảng cách lớn nhất từ tâm vùng tới đỉnh chọn), đường cong mượt (smoothstep).

## 7. Mẫu

| Mẫu | Tốc độ rung (Hz) | Tắt dần | Lan | Thể tích | Theo chuyển động | Giữ đáy |
|---|---|---|---|---|---|---|
| Bánh pudding | 3,0 | 0,12 | 0,6 | 0,8 | 0,0 | bật |
| Thạch | 5,0 | 0,08 | 0,4 | 0,6 | 0,0 | bật |
| Ngực | 2,5 | 0,18 | 0,5 | 0,5 | 0,3 | tắt |
| Thịt mềm | 3,5 | 0,25 | 0,5 | 0,5 | 0,5 | tắt |
| Má | 5,0 | 0,3 | 0,5 | 0,3 | 0,6 | tắt |

## 8. Không làm

Unity/Godot; tự va chạm giữa các đỉnh của cùng lưới (chỉ khối xương); trọng lực; vật va chạm cong bên trong lõm sâu
(chỉ tam giác gần nhất); chế độ Chỉnh sửa (bộ biến đổi tắt khi chỉnh sửa).

## 9. Kiểm tra

Tự động (`tests/python/dasktoon_jiggle_test.py`):
- Bánh pudding đứng yên, không gì chạm: không đổi (sai lệch < 1e-5).
- Quả bóng rơi vào: lõm xuống (hơn 30% độ lún của bóng), đỉnh của bánh nảy lên quá chỗ cũ sau khi bóng rời đi, rồi lặng
  (< 2% sau 4 giây); thể tích giữ trong 10% lúc bị ấn khi Giữ thể tích = 1; đáy (Giữ đáy) không đổi.
- Kéo lùi tới một khung đã tính: y hệt. Nhảy cóc rồi chạy liền: khớp kết quả chạy liền.
- Trọng số 0 đi đúng theo đích; vật dịch theo hoạt hình với Theo chuyển động 0 thì phần trên trễ rồi rung.
- Va chạm khung xương: khối bàn tay ấn vào bụng thì lõm; khối của xương kéo đỉnh không đẩy đỉnh đó.
- Thêm rung mềm: nhóm đỉnh, mép mờ, vị trí trong chồng bộ biến đổi, vật va chạm từ rig + bàn tay.
- Lưu/mở tệp .blend giữ thiết lập và vật va chạm.

Trên mô hình thật: bản sao của nhân vật, rung ngực/bụng khi chạy nhảy, tay chạm má; một nhân vật khác để đối chiếu.

## 10. Quyết định của Claude (chế độ tự động)

1. Tên giao diện "Rung mềm"; tên gốc "Jiggle".
2. Độ lan dùng làm mượt độ lệch, không dùng giữ độ dài cạnh (giữ độ dài không truyền được vết lõm vuông góc mặt).
3. Độ tự do vào làm độ cứng (`ω²/w`) chứ không trộn kết quả cuối, để va chạm vẫn đúng ở mép vùng.
4. Vật va chạm lưới: dùng tam giác cuối khung, không nội suy trong khung (đủ cho vật thường; vật rất nhanh có thể xuyên).
5. Bộ nhớ chỉ giữ mốc mỗi 10 khung để không ăn quá nhiều RAM trên lưới dày.
6. Va chạm khung xương lưu trong bộ biến đổi (danh sách xương + bán kính), Python đồng bộ từ rig, như lò xo xương.
7. Bàn tay chỉ là vật va chạm của rung mềm, không thêm vào vật va chạm của lò xo tóc/váy (không đổi hành vi cũ).
