# DaskToon: rig có bộ điều khiển, bảng mặt và ngực lắc — Thiết kế

Đưa vào DaskToon những gì đã làm tay trên nhân vật thật temp_2_1 (2026-11-05/06), thay cho rig hiện tại: lớp điều khiển
Rigify, bảng mặt bằng xương, xương ngực lắc. Bỏ phần tự đặt khớp; người dùng tự đặt các khớp, rồi một nút dựng tất cả.
Dựa trên rig anime (`2026-10-06-dasktoon-anime-rig-design.md`), vùng cơ thể (`2026-10-13-dasktoon-rig-regions-design.md`),
sửa chỗ gập (`2026-10-20-dasktoon-bend-fixes-design.md`), vai nâng theo tay
(`2026-10-14-dasktoon-shoulder-follow-design.md`). Thay `2026-10-14-dasktoon-auto-rig-design.md` mục 2 (tự rig); mục
3–5 (tư thế thử, Kiểm tra, giao diện Kiểm tra) giữ lại và sửa như §10.

Ba lỗi tìm thấy trên temp_2_1 (weight hỏng cả mô hình vì một mảnh xấu, khung bị ẩn rơi khỏi FBX, hình mẫu kéo thân và
tay) đã sửa riêng, không thuộc bản này.

## 1. Quyết định của người dùng (2026-11-06)

- Đưa cả sáu việc vào DaskToon: ba lỗi trên, **lớp điều khiển Rigify**, **bảng mặt bằng xương**, **xương ngực lắc**.
- **Bỏ chức năng tự rig** hiện tại.
- **Thay hẳn** (khuyên dùng): rig mới thay rig cũ, không giữ hai cách song song.
- Đặt khớp: **người dùng tự đặt hết**.

## 2. Luồng làm việc mới

1. Chọn các mô hình của nhân vật, **Thêm › Khung xương › Khung người anime**. Máy thêm khung mẫu cao bằng nhân vật, đứng
   giữa hai chân, thêm các mô hình làm phần (vai trò đoán theo tên như cũ), xoay nhân vật về −Y nếu nó quay hướng khác
   (giữ cách đoán hướng mặt của spec tự rig §2), rồi vào **Sửa khớp**. Thông báo: "Kéo các khớp vào giữa các khớp của
   nhân vật (bên phải đi theo bên trái), rồi bấm Dựng rig".
2. Người dùng kéo các khớp (§4).
3. **Dựng rig**: một nút làm tất cả (§5), rồi chạy Kiểm tra.
4. Xem các chỗ Kiểm tra báo, bấm các nút tư thế thử.
5. Làm hoạt hình bằng bộ điều khiển (§6) và bảng mặt (§8).

Không chọn mô hình thì Khung người anime chỉ thêm khung mẫu (cao 1,6, tại con trỏ 3D) như trước.

## 3. Bỏ đi

- Nút **Khớp theo các phần** (`dasktoon.rig_fit`) và `fit_to_parts`; đường "rig trong một lần" của Khung người anime.
- Cách tự đặt khớp: `skeleton.fit`, `body_shape.joints` cùng các hàm chỉ nó dùng, `sections.py`, `fingers.py` (tìm
  ngón tay). `body_shape.Shape` ở lại vì Nhận diện vùng dùng nó.
- Tự đổi phần dưới eo thành váy và tự đổi "mắt" không nằm trên đầu thành Quần áo (hai việc chỉ đường tự rig làm). Kiểm
  tra vẫn báo "trông như váy / tóc" kèm nút đổi như cũ.
- Nút **Tạo bảng rig 3D** (bảng bằng empty, chỉ là bản nháp, không điều khiển gì): bảng mặt §8 thay nó.
- Các phép thử của những phần trên; trang hướng dẫn nói về tự rig được viết lại (§12).

## 4. Đặt khớp bằng tay

- **Khung mẫu**: 55 xương chuẩn của Unity như nay (spec rig anime §4), tư thế chữ T, nhân theo chiều cao khung bao các mô
  hình (không kể phụ kiện ở xa), chân chạm sàn, đứng giữa khung bao theo X và Y.
- **Sửa khớp**: vào chế độ chỉnh khung, bật soi gương theo X (kéo một bên, bên kia theo), chỉ hiện các xương của khung
  chuẩn và xương ngực (nếu có), vẽ đè lên mô hình, hiện tên xương. Trước khi vào, nút **gỡ lớp điều khiển** (xương Rigify, xương phụ, bảng mặt;
  §6.6): lớp đó dựng theo khớp cũ, để lại thì ở chế độ tạo dáng mô hình bị kéo về khớp cũ. Khóa hoạt hình trên bộ điều
  khiển vẫn nằm trong clip; Dựng rig làm lại bộ điều khiển cùng tên nên chúng chạy lại. Thông báo: "Đã gỡ bộ điều khiển
  để sửa khớp; bấm Dựng rig khi xong".
- Người dùng tự vào chế độ chỉnh khung (phím Tab) mà không qua nút: Kiểm tra báo "Khớp đã đổi sau lần dựng rig cuối"
  kèm nút **Dựng rig** (§10).
- Ngón tay, mắt, hàm cũng do người dùng đặt (khung mẫu đặt sẵn theo tỉ lệ).

## 5. Dựng rig

Nút **Dựng rig** (`dasktoon.rig_build`) làm theo thứ tự, mỗi lần đều làm lại từ đầu:

1. **Kiểm tra trước** như spec rig anime §6.1, thêm: một khớp bên trái (tay, chân) nằm ở nửa bên phải nhân vật (so với
   giữa hông) thì dừng, báo "Khớp LeftUpperArm nằm bên phải nhân vật: bên trái của khung là bên trái nhân vật". Rigify
   không bật được (bản build thiếu nó) thì dừng, báo lỗi.
2. **Nhận diện** vùng và lọn khi chưa từng nhận diện (như nay).
3. **Gỡ lớp điều khiển cũ** nếu có (§6.6).
4. Chuỗi tóc và váy, weight (kể cả cách giải lại theo từng mảnh khi cả mô hình hỏng), sửa chỗ gập: như nay.
5. **Xương ngực** khi bật (§9).
6. **Lớp điều khiển Rigify** (§6).
7. **Vai nâng theo tay** trên lớp điều khiển (§7).
8. **Bảng mặt** khi bật và có hình mẫu biểu cảm (§8).
9. **Kiểm tra** luôn chạy sau khi dựng (nay chỉ chạy khi đang có danh sách), vì Dựng rig giờ là nút chính.

Lỗi ở bước nào thì dừng và báo, khung chuẩn và weight đã làm vẫn giữ. Thanh tiến độ của cửa sổ chạy theo các bước.

## 6. Lớp điều khiển (Rigify)

### 6.1 Khung mẫu Rigify theo khớp của người dùng

Máy thêm khung người mẫu của Rigify, giữ các xương cần, đặt mỗi xương đúng đầu, đuôi, độ xoay (roll) của xương DaskToon
tương ứng:

| Rigify | DaskToon |
|---|---|
| spine, spine.001, spine.002, spine.003 | Hips, Spine, Chest, UpperChest |
| spine.004 + spine.005 (chia đôi) | Neck |
| spine.006 | Head |
| shoulder, upper_arm, forearm, hand (.L/.R) | Shoulder, UpperArm, LowerArm, Hand (Left/Right) |
| thigh, shin, foot, toe | UpperLeg, LowerLeg, Foot, Toes |
| thumb, f_index, f_middle, f_ring, f_pinky .01–.03 | Thumb, Index, Middle, Ring, Little Proximal/Intermediate/Distal |

- palm.01–04: từ cổ tay tới gốc từng ngón (bắt đầu ở 30% quãng đó).
- heel.02 (trục kiễng gót): ở sàn, ngang mép sau bàn chân của phần Cơ thể quanh cổ chân; không tìm thấy thì sau cổ
  chân 2% chiều cao. Rộng 2,75% chiều cao.
- Chỗ Rigify nối liền hai xương mà khung DaskToon để hở (vài mm), đầu xương con dời về đuôi xương cha. Xương DaskToon
  không đổi, chỉ khung mẫu Rigify.
- Mắt, hàm, chuỗi tóc váy, ngực: không thuộc Rigify; chúng là con của xương DaskToon nên đi theo.

### 6.2 Tạo và nhập vào khung DaskToon

- Rigify tạo khung điều khiển, rồi khung đó được **nhập vào chính khung DaskToon** (một khung, một clip, như cũ).
- Mỗi xương DaskToon có trong bảng §6.1 có một xương phụ `DTH-<tên>` (đầu, đuôi, độ xoay của nó) làm con của xương
  `ORG-` tương ứng của Rigify; xương DaskToon chép biến đổi của xương phụ (ràng buộc Copy Transforms "DT Follow
  Rigify"). Thứ tự cha con của khung DaskToon giữ nguyên, nên Unity nhận khung như cũ.
- Chỉ các xương DaskToon làm biến dạng mô hình; mọi xương Rigify và xương phụ không biến dạng, nên không vào FBX (xuất
  chỉ lấy xương biến dạng) và không vào Godot.
- Xương LookTarget (điểm nhìn) làm con của xương gốc `root` của Rigify.
- Khung mẫu Rigify bị xóa sau khi tạo. Văn bản `rig_ui.py` Rigify sinh ra cũng bị xóa (§6.4).

### 6.3 Nhóm xương và màu

- Hiện: các nhóm điều khiển của Rigify (thân, tay, chân, ngón, gốc), tên dịch trong mục Điều khiển (§6.5).
- Ẩn: "Khung (biến dạng)" (xương DaskToon theo Rigify), "Xương phụ" (DTH-, xương nâng vai, BreastSway), "Tóc và váy".
  Người dùng tự bật nếu muốn tạo dáng tóc bằng tay.
- Thêm: "Bảng mặt" (§8), "Ngực" (§9).

### 6.4 Không cần chạy script trong file

Rigify đặt bảng điều khiển của nó vào một script trong file; DaskToon (như Blender) mặc định không tự chạy script trong
file, nên mở lại file sẽ mất bảng đó và hiện dòng cảnh báo. DaskToon tự có mục **Điều khiển** (§6.5) làm việc của bảng
đó, nên script bị xóa. Mọi ràng buộc, driver Rigify cần đều là driver đơn giản, chạy được khi không chạy script.

### 6.5 Mục Điều khiển (Rig anime › Điều khiển)

- Mỗi tay, mỗi chân một hàng: thanh **IK/FK** (thuộc tính IK_FK của Rigify), nút **IK theo FK** và **FK theo IK** (đặt
  bộ điều khiển bên này vào đúng dáng bên kia đang có, để chuyển không bị giật; tự viết trong DaskToon, không dùng script
  của Rigify).
- Bật tắt các nhóm xương điều khiển, tên tiếng Việt: Thân, Thân (tinh chỉnh), Tay trái IK, Tay trái FK, ..., Ngón tay,
  Gốc, Bảng mặt, Ngực.
- Rig chưa có lớp điều khiển: dòng "Rig này chưa có bộ điều khiển: bấm Dựng rig".

### 6.6 Gỡ lớp điều khiển

Xóa: xương Rigify, `DTH-`, `FB_`/`FBF_`, các ràng buộc "DT Follow Rigify", driver của Rigify trên khung, driver của bảng
mặt trên hình mẫu, chữ của bảng mặt, các mô hình dáng xương (WGT) của chúng. Không xóa: khung DaskToon, weight, chuỗi,
xương ngực, hình mẫu, khóa hoạt hình. Dùng ở bước 3 của Dựng rig và ở nút Sửa khớp.

### 6.7 Rigify

DaskToon có sẵn Rigify (nằm trong các add-on đi kèm). Dựng rig bật nó cho phiên làm việc nếu đang tắt (không ghi vào
thiết lập người dùng).

## 7. Vai nâng theo tay trên lớp điều khiển

Nay xương nâng vai đọc góc quay riêng của cánh tay trên. Có Rigify, xương DaskToon chỉ chép theo nên góc riêng của nó
luôn bằng không; vai không nâng. Thay vào đó:

- Lực nâng đặt lên xương vai của Rigify (`ORG-shoulder`), nên cả cánh tay đi theo vai như cũ.
- Khi tay ở FK: đọc góc quay riêng của bộ điều khiển `upper_arm_fk` (cùng cách như nay, không vòng lặp).
- Khi tay ở IK: một xương phụ ở khớp vai, con của ngực, nhắm vào bộ điều khiển bàn tay IK; đọc hướng của nó (không phụ
  thuộc vai, nên không vòng lặp).
- Hai cách trộn theo thanh IK/FK. Mức nâng (bắt đầu 30° dưới ngang, tối đa 35° khi tay thẳng lên) và thanh **Vai nâng
  theo tay** như nay.

## 8. Bảng mặt

### 8.1 Khi nào có

Ô **Bảng mặt** (bật sẵn) ở mục Khớp. Dựng rig làm bảng khi một phần Cơ thể hay phần mặt có ít nhất một hình mẫu trùng tên
trong bảng §8.2. Nhiều mô hình cùng có một tên (mặt, lông mày, lông mi tách riêng) thì một nút điều khiển tất cả.

### 8.2 Bố cục

Ba cột nút kéo hai chiều (mỗi hướng một hình mẫu) và các hàng thanh trượt (kéo lên):

| Nút | Nhãn | Lên / xuống / ra ngoài / vào trong |
|---|---|---|
| Mày phải, mày trái | Mày P, Mày T | nhướng / cau / giận / lo |
| Mắt phải, mắt trái | Mắt P, Mắt T | mở to / nhắm / sắc / rũ |
| Nhìn | Nhìn | nhìn lên / xuống / trái / phải (theo hình mẫu nhìn, xét chiều con ngươi thật sự dịch) |
| Miệng | Miệng | khóe lên / khóe xuống / rộng / chu |

Hàng thanh trượt: A I U E O; Vui, Giận, Buồn, Dịu, Ngạc nhiên; Đỏ má, Lưỡi, Mắt tim, Mắt sao, Cười toe. Mỗi ô nhận vài
tên: tên VRM, tên DaskToon tự tạo (Tự tạo biểu cảm), tên VRoid (`Fcl_`), chữ cái đơn, tiếng Nhật (như lip sync đang
nhận). Hình mẫu không có thì ô đó không hiện. Hình mẫu khác ngoài bảng vẫn chỉnh trong danh sách hình mẫu như cũ.

### 8.3 Xương

- `FB_Board` con của bộ điều khiển đầu (theo đầu), đứng cạnh đầu phía bên trái nhân vật, hơi trước mặt; kích thước theo
  chiều cao nhân vật (temp_2_1 cao 1,6: cách giữa 0,27, trước đầu 0,10, cao hơn khớp đầu 0,06; bảng rộng 0,15, cao 0,27).
- Mỗi nút: khung `FBF_<tên>` (không chọn được) và núm `FB_<tên>` con của khung. Núm chỉ dời trong mặt phẳng bảng (thanh
  trượt chỉ lên), giới hạn 0,012 (theo chiều cao), khóa xoay và co giãn.
- Màu: khung một màu, núm một màu nổi; nhóm xương "Bảng mặt".

### 8.4 Driver

Mỗi hướng của núm lái một hình mẫu: `clamp(v / 0.012, 0, 1)` (hay `-v`), `v` là vị trí núm theo trục đó. Biểu thức đơn
giản nên chạy khi không chạy script. Chiều cao khác 1,6 thì số 0,012 nhân theo.

### 8.5 Chữ

Mỗi nút một dòng chữ 3D trên bảng (đi theo bảng), theo ngôn ngữ giao diện lúc dựng; tiêu đề "BIỂU CẢM". Không hiện khi
render, không chọn được, vẽ đè.

### 8.6 Các công cụ đang đặt giá trị hình mẫu

Hình mẫu có driver thì giá trị riêng và khóa của nó không còn tác dụng. Nên khi hình mẫu do bảng lái:

- **Thử biểu cảm**, **Về mặt nghỉ**, xem trước trực tiếp, thử biểu cảm trên mô hình: đặt núm thay vì đặt giá trị.
- **Lip sync**: đặt khóa lên núm các thanh A I U E O (cùng clip như nay).
- **Bộ điều khiển** (HUD) của mô hình đó: không dùng được, mục của nó báo "Mặt này điều khiển bằng bảng mặt (Rig anime)".
  Mô hình không có bảng mặt vẫn dùng HUD như cũ.
- Khóa đã có trên giá trị hình mẫu (trước khi có bảng): Dựng rig chuyển sang núm khi hình mẫu chỉ do một hướng của một
  núm lái; báo số khóa đã chuyển.

### 8.7 Xuất

Unity: FBX ghi giá trị mọi hình mẫu theo từng khung hình, gồm giá trị do driver lái. Godot: hình mẫu do bảng lái được tính
là có hoạt hình (nay chỉ tính hình mẫu có khóa). Xương bảng mặt không biến dạng nên không được xuất.

## 9. Xương ngực lắc

### 9.1 Bật

Ô **Xương ngực** ở mục Khớp, tắt sẵn. Bật mà không thấy ngực nhô (§9.2) thì không tạo, báo "Không thấy ngực nhô ra, không
tạo xương ngực".

### 9.2 Chỗ đặt

- Đã có xương `LeftBreast`/`RightBreast` (người dùng đã đặt hay lần dựng trước): giữ đúng chỗ đó.
- Chưa có: tìm đỉnh ngực trên phần Cơ thể: trong khoảng cao từ đầu xương Chest tới đầu xương Neck, phía trước khung,
  cách giữa 10–70% nửa bề ngang vai; mỗi bên điểm nhô ra trước nhất; lấy trung bình hai bên (đối xứng).
- **Thành ngực**: mặt cong trơn khớp với da quanh hai bầu ngực (bỏ vùng bầu ngực). Đỉnh nhô khỏi thành ngực ít hơn 1,5%
  chiều cao thì coi là không có ngực.
- Mỗi bên hai xương: `<Bên>BreastSway` (ẩn, con của Chest, từ thành ngực tới đỉnh) và trên nó `<Bên>Breast` (biến dạng,
  bộ điều khiển: dời, xoay, co giãn).

### 9.3 Weight

Phần nhô khỏi thành ngực, mờ dần ra ngoài viền bầu ngực (viền bầu dục quanh đỉnh, rộng hơn phía ngoài và phía trên);
weight của cánh tay trên bầu ngực chuyển về Chest. Như đã làm trên temp_2_1.

### 9.4 Lắc

- BreastSway có ràng buộc lò xo của DaskToon: độ cứng 1,5, cản 0,3, trọng lực 0, bán kính 0,015 (theo chiều cao), không
  collider. Đã thử trên temp_2_1.
- **Lắc trực tiếp** bật tắt nó như các chuỗi; **Bake chuyển động lắc** gồm cả ngực.
- Unity: ghi vào tệp rig (`.rig.json`) như một chuỗi một xương của phần "Ngực", để Unity lắc giống hệt; **Lắc trong
  game** (chạy trong game / đã bake) như các chuỗi.

## 10. Kiểm tra và tư thế thử

- Tư thế thử đặt dáng lên **bộ điều khiển FK** (chuyển các tay chân sang FK); **Về nghỉ** đưa mọi bộ điều khiển và núm
  bảng mặt về nghỉ, trả thanh IK/FK về như trước khi thử.
- Rig chưa có lớp điều khiển: tư thế thử đặt thẳng lên khung như nay.
- Thêm chỗ cần xem: "Khớp đã đổi sau lần dựng rig cuối" (xương DaskToon lệch khỏi xương phụ của nó), nút **Dựng rig**.
- Các chỗ khác (khớp ngoài thân, chỗ bị kéo giãn, vai trò có vẻ sai, hình mẫu kéo thân) giữ nguyên. Khớp ngoài thân nay
  quan trọng hơn vì người dùng tự đặt khớp.

## 11. File cũ

- Rig dựng bằng cách cũ (không có lớp điều khiển) vẫn chạy như khung thường cho tới khi bấm Dựng rig.
- Clip có khóa trên xương khung (cách cũ): sau khi dựng, khung theo bộ điều khiển nên các khóa đó không còn tác dụng.
  Dựng rig cảnh báo: "Clip <tên> có khóa trên xương khung; khung giờ đi theo bộ điều khiển nên các khóa này không còn tác
  dụng". Chuyển khóa sang bộ điều khiển: ngoài phạm vi (§13).
- temp_2_1 (đã làm tay với cùng tên xương `DTH-`, `FB_`, `FBF_`, `<Bên>Breast`): Dựng rig làm lại bằng DaskToon, khóa
  trên các bộ điều khiển đó chạy lại.

## 12. Giao diện và hướng dẫn

Mục **Rig anime** của khung xương:

- **Kiểm tra** (như nay).
- **Khớp**: **Sửa khớp**; Vai nâng theo tay; Sửa chỗ gập; **Bảng mặt**; **Xương ngực**. (Bỏ Khớp theo các phần.)
- **Điều khiển** (mới, §6.5).
- Các phần, Phụ kiện, Biểu cảm, Vùng, Ánh mắt, Lắc, Collider, Dựng rig: như nay.

Menu Thêm › Khung xương › Khung người anime: chú thích mới "Thêm khung người chuẩn; chọn mô hình trước thì khung cao bằng
nhân vật và các mô hình thành phần của rig". Chữ mới đều có bản Việt. Trang hướng dẫn (vi, en) về rig viết lại theo luồng
§2; trang Bộ điều khiển nói thêm bảng mặt.

## 13. Ngoài phạm vi

- Chuyển khóa cũ trên xương khung sang bộ điều khiển.
- Rig mặt của Rigify (xương mặt): mặt anime dùng hình mẫu và bảng mặt.
- Đổi cha của bộ điều khiển (ví dụ tay IK theo gốc / theo ngực) mà không giật: thanh đổi cha của Rigify vẫn dùng được
  nhưng đổi thì bộ điều khiển nhảy.
- Thêm tư thế thử (ngồi xổm, đá chân, vặn mình).

## 14. Kiểm thử

- Mỗi phần có phép thử riêng trên nhân vật dựng trong phép thử (như các phép thử rig hiện có): khung mẫu theo chiều cao;
  Sửa khớp gỡ lớp điều khiển; kiểm tra trái phải; lớp Rigify (xương DaskToon theo bộ điều khiển, chỉ xương DaskToon biến
  dạng, không còn script, IK theo FK / FK theo IK đưa tay về đúng chỗ trong 1 mm); vai nâng ở cả FK và IK; bảng mặt (mỗi
  hướng đúng hình mẫu, thiếu hình mẫu thì không có ô, công cụ đặt núm, lip sync khóa núm); ngực (đỉnh đúng chỗ, giữ chỗ
  người dùng đặt, không có ngực thì không tạo, lắc rồi về); xuất FBX chỉ có xương biến dạng và có hoạt hình của bộ điều
  khiển; Godot có giá trị hình mẫu do bảng lái.
- Unity: nhân vật dựng rig mới nhập vào Unity, khung người (Humanoid) hợp lệ, clip chạy, ngực lắc.
- Mô hình thật: temp_2_1 (bản sao) và mười nhân vật giữ riêng để thử: đặt khớp bằng một tệp khớp đã lưu (thay tay người
  dùng), Dựng rig, các tư thế khó đã dùng trên temp_2_1, bảng mặt kéo hết các núm, đo thân và tay không bị hình mẫu kéo.
- Toàn bộ bộ kiểm tra phải qua trước khi đẩy lên.

## 15. Chia giai đoạn

Mỗi giai đoạn một kế hoạch riêng, xong giai đoạn nào đẩy lên giai đoạn đó:

1. **Khớp và bộ điều khiển**: bỏ tự rig (§3), đặt khớp bằng tay (§4), Dựng rig mới (§5), lớp Rigify (§6), vai nâng (§7),
   tư thế thử và Kiểm tra (§10), file cũ (§11), giao diện và hướng dẫn phần này (§12), xuất.
2. **Bảng mặt** (§8) cùng các công cụ biểu cảm, lip sync, HUD, xuất Godot.
3. **Ngực lắc** (§9) cùng Unity.

## 16. Rủi ro

- Rigify đổi theo phiên bản Blender: DaskToon dùng bản đi kèm 5.2; phép thử bắt chỗ đổi.
- Dựng rig lâu hơn vài giây (Rigify tạo khung); temp_2_1 hiện mất 58 giây.
- Phát lại chậm hơn vì thêm nhiều xương và ràng buộc; đo trên temp_2_1, nếu chậm hơn 30% thì xem lại.
- Nhập khung Rigify vào khung DaskToon phải giữ driver của Rigify (đã đúng trên temp_2_1); phép thử kiểm.
