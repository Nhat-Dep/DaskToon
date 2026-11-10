# DaskToon: Rig cơ khí, phần 1 (mảnh cứng, khớp, chân IK, ngắm) — Thiết kế

Ngày 2026-11-10. Người dùng hỏi: "có thể thêm khả năng rig cơ khí ko". Đã chọn (câu hỏi): **chi tiết máy, vũ khí /
đạo cụ, robot / mecha / giáp**; mô hình **tự dựng lẫn nhập từ file**; robot **chủ yếu dáng khác người** (nhện, tháp
pháo...); dựng **bằng tay với công cụ nhanh** (không tự đoán cả con); điều khiển: **tay quay từng khớp, loại khớp + giới
hạn góc, chân IK bám đất, ngắm theo mục tiêu**; **chưa cần xuất Unity/Godot**. Cách gắn: **A — một bộ xương, mỗi mảnh
100% vào một khớp** (đã duyệt). Phần 1 của §1 (công cụ nhấp) đã trình bày; sau đó "ok tự động đến 8h": các chi tiết còn
lại do Claude quyết, ghi ở §11.

Chia ba phần, mỗi phần một thiết kế: **1. mảnh cứng** (tài liệu này), **2. chi tiết máy** (pít-tông, bánh răng, bản
lề kéo nhau, cần gạt), **3. vũ khí / đạo cụ** (cầm tay, đổi tay, cò, nòng giật — dùng lại phần 2).

## 1. Người dùng thấy gì

- **Vật › Tạo rig máy** (menu Vật của khung nhìn 3D) và nút cùng tên trong bảng **Rig cơ khí** của lưới (thẻ Dữ liệu
  vật): các lưới đang chọn thành một máy. Tạo bộ xương "‹tên› Máy" với một khớp **Root** ở giữa đáy hộp bao, mọi đỉnh
  gắn 100% vào Root (= "chưa gắn"), mỗi lưới có bộ biến đổi Armature (đặt đầu ngăn xếp, trước viền DaskToon).
- Bảng **Rig cơ khí** trong thẻ Dữ liệu của bộ xương máy (bảng Anime Rig không hiện trên bộ xương máy):
  - **Dựng**: nút **Thêm khớp** (công cụ §2), dòng "Còn N mảnh chưa gắn", **Làm cứng các mảnh** (§6).
  - **Khớp đang chọn** (xương đang chọn): Loại khớp (Bản lề / Khớp cầu / Trượt / Cố định), Giới hạn (bật/tắt),
    Nhỏ nhất / Lớn nhất (độ hoặc mét), **Gỡ khớp**.
  - **Chân IK**: mỗi chân một hàng: thanh IK / FK, **Về IK**, **Về FK**; nút **Thêm chân IK** (xương đang chọn là bàn
    chân), **Gỡ chân IK**.
  - **Ngắm**: mỗi điểm ngắm một hàng với thanh Ngắm; nút **Thêm điểm ngắm** (xương đang chọn là nòng / mắt), **Gỡ
    điểm ngắm**.
- Bảng **Rig cơ khí** của lưới (khi lưới thuộc một máy): **Mảnh từ vùng chọn** (chế độ Chỉnh sửa: các mặt đang chọn
  thành một mảnh riêng).

## 2. Công cụ Thêm khớp (modal, trong khung nhìn 3D)

Trong lúc dùng công cụ, bộ xương ở tư thế nghỉ (`pose_position = REST`, trả lại khi thoát); các mảnh chưa gắn tô đỏ
nhạt, mảnh đang chọn cam, mảnh cha xanh, tâm quay là một chấm với đường trục.

1. **Nhấp một mảnh** → chọn nó (Shift+nhấp thêm / bớt mảnh vào cùng một khớp). Nhấp một mảnh đã gắn khớp → chọn khớp
   đó để sửa (đổi cha, dời tâm, đổi trục / loại).
2. **Nhấp mảnh cha** (bấm **P** hoặc nhấp lần hai sau khi đã chọn mảnh), nhấp chỗ trống = Root. Mảnh cha chưa gắn thì
   được gắn trước thành khớp cầu tự do dưới Root (báo trên dòng trạng thái).
3. **Đoán khớp** (§3): tâm quay, trục, loại. **Kéo chuột** (giữ G hoặc kéo chuột trái trên chấm) dời tâm trên mặt
   phẳng nhìn; **X / Y / Z** đặt trục theo trục thế giới, **A** về trục tự đoán; **T** đổi loại khớp.
4. **Enter / Space**: tạo khớp (§4). Mảnh vừa gắn thành mảnh cha mặc định cho lần sau — nhấp liền đùi → ống → bàn
   chân. **Backspace**: gỡ khớp vừa tạo. **Esc / chuột phải**: thoát.

Dòng trạng thái (header) ghi bước đang làm và phím. Logic nằm ở `dasktoon_machine.tool.ToolState` (thử được không cần
chuột); toán tử modal chỉ đổi sự kiện thành lời gọi.

## 3. Mảnh và đoán khớp

**Mảnh**: thuộc tính số nguyên `dt_piece` trên đỉnh. Giá trị 0 = chưa có; khi dùng công cụ, đỉnh 0 được chia theo
cụm liền cạnh và nhận số mới. **Mảnh từ vùng chọn** đặt số mới cho đỉnh của các mặt đang chọn. Một khớp có thể giữ
nhiều mảnh.

**Đoán khớp** giữa mảnh con C và mảnh cha P (vị trí nghỉ, không gian thế giới):
- Điểm tiếp xúc: đỉnh của C cách mặt P không quá `max(2% đường chéo C, 1,5 × khoảng nhỏ nhất)`. Không có điểm nào
  (hở) → điểm giữa cặp điểm gần nhau nhất, khớp cầu.
- PCA của điểm tiếp xúc (trị riêng λ1 ≥ λ2 ≥ λ3, trục e1, e2, e3):
  - **Trụ / vòng**: với mỗi trục e, khoảng cách điểm tới đường thẳng qua trọng tâm theo e có hệ số biến thiên < 0,2 và
    bán kính > 0 → **bản lề** quanh e, tâm = trọng tâm (vòng trục bánh xe, chốt bản lề). Chọn e có hệ số nhỏ nhất.
  - **Thẳng**: λ2 < 0,05 λ1 → bản lề quanh e1 (chốt mảnh, mép bản lề).
  - **Phẳng**: λ3 < 0,05 λ2 → bản lề quanh e3 (mâm xoay, tháp pháo trên tấm).
  - Còn lại → **khớp cầu** tại trọng tâm.
- Không có cha (Root) → khớp cầu tại trọng tâm mảnh.

## 4. Khớp = một xương

- Tên xương: tên lưới khi mảnh là cả lưới, nếu không tên vật liệu chiếm nhiều mặt nhất, nếu không "Part"; thêm số khi
  trùng. Người dùng đổi tên tùy ý.
- **Đầu xương** = tâm quay. **Trục X của xương = trục quay** của bản lề; với khớp trượt **trục Y = hướng trượt**.
- **Hướng Y** (trong mặt phẳng ⊥ X với bản lề): tới tâm quay của khớp con nếu có đúng một con, nếu không tới điểm xa
  nhất của mảnh (chiếu lên mặt phẳng ⊥ X). Độ dài = khoảng đó, ít nhất 5% đường chéo mảnh. Thêm con thì xương cha được
  xoay lại theo luật này (lúc dựng, chưa có hoạt hình).
- Trọng lượng: nhóm đỉnh tên xương, 1,0 trên mọi đỉnh của các mảnh; các đỉnh đó bị bỏ khỏi mọi nhóm xương máy khác.
- Gỡ khớp: mảnh về khớp cha, khớp con nối vào khớp cha.
- Loại khớp (đặt lên xương tư thế, đổi được bất cứ lúc nào):
  - **Bản lề**: Euler XYZ, khóa quay Y Z, khóa dời; IK khóa Y Z (`lock_ik_y/z`); giới hạn = Limit Rotation X (cục bộ,
    `use_transform_limit`) và `ik_min_x/ik_max_x`.
  - **Khớp cầu**: Quaternion, khóa dời; không giới hạn ở phần 1.
  - **Trượt**: khóa quay; khóa dời X Z; giới hạn = Limit Location Y; IK khóa cả ba.
  - **Cố định**: khóa hết.
- Hình điều khiển (custom shape, bộ sưu tập ẩn "DT Machine Shapes"): bản lề = vòng quanh trục X, khớp cầu = ba vòng,
  trượt = mũi tên theo Y, cỡ theo mảnh. Màu theo loại (nhóm xương).
- Dữ liệu: `Bone.dasktoon_joint` (PropertyGroup: kind, use_limit, min, max; cập nhật thì đặt lại khóa / ràng buộc).
  Bộ xương: `Armature.dasktoon_machine` (is_machine, legs, aims).

## 5. Chân IK và ngắm

**Chân IK** (xương đang chọn = bàn chân F, cha của nó = ống S):
- Chuỗi: từ S đi lên tới trước tổ tiên đầu tiên có ≥ 2 con hoặc là Root (chân nhện: đùi + ống, gốc là thân); ít nhất 1.
- Xương đích "IK ‹F›" (không biến dạng, con của Root) ở đầu F, hướng như F, hình hộp. Ràng buộc IK trên S (đích = IK
  ‹F›, chain_count = độ dài chuỗi, không pole: các bản lề khóa IK nên mặt phẳng chân cố định). F có Copy Rotation thế
  giới từ đích (bàn chân giữ hướng của đích, bám phẳng đất).
- Thuộc tính `IK_FK` (0 = IK, 1 = FK) trên xương đích, driver đặt độ ảnh hưởng của IK và Copy Rotation = 1 − IK_FK.
- **Về FK**: đọc ma trận nhìn thấy của chuỗi + F, chuyển FK, đặt lại từ trên xuống. **Về IK**: đặt đích theo ma trận
  nhìn thấy của F, chuyển IK.

**Ngắm** (xương đang chọn = nòng B):
- Điểm mũi M = điểm xa nhất của mảnh B tính từ tâm quay B. Chuỗi ngắm: B và các tổ tiên liên tiếp là bản lề hoặc khớp
  cầu, dừng ở xương có ≥ 2 con hoặc Root, tối đa 3 xương.
- Mỗi xương trong chuỗi được xoay lại (lúc dựng) cho Y hướng về M (chiếu ⊥ X với bản lề). Ràng buộc: bản lề = Locked
  Track (khóa X, bám Y), khớp cầu = Damped Track (Y), đặt trước giới hạn.
- Xương đích "Aim ‹B›" (con của Root) trên tia đầu B → M, cách đầu B gấp 4 lần |M − B|; hình cầu.
- Thuộc tính `Aim` (0..1) trên đích, driver độ ảnh hưởng.

## 6. Mô hình nhập có sẵn xương

**Làm cứng các mảnh** (bộ xương bất kỳ có lưới gắn): bộ xương thành máy (is_machine), Root = xương gốc đầu tiên. Mỗi
mảnh (cụm liền cạnh / `dt_piece`): cộng trọng lượng theo nhóm xương trên các đỉnh của mảnh, cả mảnh 100% vào nhóm lớn
nhất. Mảnh có nhóm lớn nhất < 60% tổng → báo "N mảnh bị nhiều khớp chia nhau" và chọn chúng trong chế độ Chỉnh sửa để
người dùng tách bằng **Mảnh từ vùng chọn** rồi gắn lại bằng công cụ.

## 7. Mã

- `scripts/modules/dasktoon_machine/`: `__init__.py` (create, is_machine, rig_of_mesh), `pieces.py` (dt_piece, cụm,
  bắn tia chọn mảnh, từ vùng chọn, làm cứng), `joints.py` (đoán, thêm / gỡ / đổi cha / dời tâm, loại, giới hạn, hướng
  xương, trọng lượng), `shapes.py` (hình điều khiển), `legs.py` (IK, snap), `aim.py`, `tool.py` (ToolState).
- `scripts/startup/bl_ui/dasktoon_machine.py`: PropertyGroup, toán tử, công cụ modal + vẽ, bảng; đăng ký trong
  `bl_ui/__init__.py`; tiếng Việt trong `dasktoon_translations.py`.
- Bảng Anime Rig: poll bỏ qua bộ xương máy.

## 8. Không làm (phần 1)

Tự đoán cả con máy; giới hạn khớp cầu; pole cho IK; xuất Unity/Godot; pít-tông, bánh răng, cần gạt (phần 2); vũ khí
cầm tay (phần 3); đổi hướng xương khi đã có hoạt hình (chỉ đúng lúc dựng).

## 9. Kiểm tra (`tests/python/dasktoon_machine_test.py`, máy giả lập)

Máy giả: thân hộp; tháp pháo trụ đặt phẳng trên thân; nòng có chốt trụ xuyên qua tai tháp; hai chân đùi–ống–bàn, khớp
hông là chốt trụ; một bánh xe là lưới riêng có lỗ trục. Không tên, không số của mô hình thật nào.
- Tạo: Root, mọi đỉnh ở Root, Armature đứng đầu, đếm mảnh chưa gắn.
- Mảnh: cụm liền, từ vùng chọn tách được, bắn tia trúng đúng mảnh.
- Đoán: tháp pháo bản lề trục Z ở tâm mâm; nòng bản lề theo chốt; hông theo chốt; bánh xe theo lỗ; tiếp xúc khối → cầu;
  hở → cầu ở giữa.
- Thêm khớp: trọng lượng đúng; tư thế nghỉ lệch 0; quay bản lề → mảnh đi cứng (khoảng cách giữ nguyên, mảnh khác đứng
  yên); trục X của xương đúng trục quay.
- Loại / giới hạn: bản lề chỉ quay X, giới hạn kẹp; trượt đi theo Y, kẹp; cố định không nhúc nhích.
- Gỡ khớp, đổi cha, dời tâm; ToolState đi hết một chân bằng chuỗi nhấp.
- Chân IK: đích dời → đầu bàn chân tới đích (< 1 mm khi với tới), gối chỉ quay quanh trục bản lề, bàn chân giữ hướng;
  Về FK / Về IK giữ nguyên tư thế.
- Ngắm: dời đích → hướng nòng lệch < 2° (trong giới hạn), giới hạn được tôn trọng.
- Làm cứng: lưới da pha trọng lượng → mỗi mảnh một nhóm 1,0; mảnh chia đều bị báo.
- Bảng vẽ không lỗi; dịch đủ tiếng Việt.

## 10. Thử trên mô hình thật

Sau khi xong: một mô hình máy có sẵn (nếu tìm thấy trong máy người dùng) hoặc mô hình dựng nhanh, ảnh chụp tư thế.

## 11. Quyết định của Claude (chế độ tự động)

1. Khớp đặt bằng xương (cách A) với **trục X = trục bản lề**, **Y = trượt**: theo quy ước gập của Blender, giới hạn
   chỉ một trục.
2. Mảnh lưu bằng thuộc tính đỉnh `dt_piece` (không tách vật) — giữ viền, vật liệu; vùng chọn tách được trong một khối.
3. Mảnh "chưa gắn" = đang ở Root; Root không nhận mảnh nào chủ ý (nhấp chỗ trống tạo khớp mới dưới Root).
4. Đoán khớp bằng PCA của vùng tiếp xúc (trụ / thẳng / phẳng / khối), ngưỡng theo cỡ mảnh.
5. Hướng xương theo khớp con duy nhất để IK chuẩn; được xoay lại lúc dựng.
6. IK không pole, dựa vào khóa IK của bản lề; bàn chân giữ hướng đích.
7. Ngắm bằng Locked Track trên bản lề, Damped Track trên khớp cầu; xương ngắm được xoay cho Y hướng mũi.
8. Bảng riêng "Rig cơ khí", bảng Anime Rig ẩn trên bộ xương máy; vào từ menu Vật và bảng lưới.
9. Tên xương lấy từ dữ liệu người dùng (lưới / vật liệu), Root giữ tên tiếng Anh như các xương DaskToon khác.
10. Gỡ khớp vừa tạo bằng Backspace trong công cụ; Ctrl+Z sau khi thoát hoàn tác cả lần dùng công cụ.
