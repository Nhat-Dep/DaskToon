# DaskToon: nhận diện vùng cơ thể và lọn gắn đầu — Thiết kế

Phần 1 của việc "tối ưu khả năng nhận diện rig" (người dùng yêu cầu 2026-10-13 sau lần thử trên mô hình thật). Người
dùng duyệt chia bốn phần, làm lần lượt:

1. **Vùng cơ thể và lọn gắn đầu** (spec này): sửa đúng lỗi thấy trong ảnh.
2. Váy và tóc dài: nhận ra trong mesh không đặt tên rõ, gợi ý vai trò Skirt, Hair.
3. Ngón tay: đặt khớp ngón theo hình bàn tay.
4. Mắt và miệng: tìm chỗ mắt, miệng; đặt xương mắt, hàm; gợi ý Mắt phẳng, Miệng 2D.

Spec gốc của rig: `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` (vai trò §5, Build §6).

## 1. Vấn đề

Thử trên bản sao `tdt.blend` (chibi cao 2,95 m, tai thỏ và tóc nằm chung mesh với da, váy không có da bên dưới), sau bốn
lỗi đã sửa: giơ tay phải thì tai thỏ bên phải bị kéo xuống ngực, lọn tóc kéo ngang mặt, dây đeo quần bị kéo ra. Nguyên
nhân: Bone Heat chia weight theo khoảng cách tới xương; xương Head của chibi là một đường mảnh giữa cái đầu rất to, nên
vai và cánh tay gần tai hơn Head. Đo: khoảng 1 750 đỉnh tóc, tai mỗi bên và khoảng 340 đỉnh áo có weight cánh tay dù
cách tay hơn 20 cm. Mẫu thử (prototype) hai quy tắc dưới đây đưa con số đó về 0 mà giữ 96% weight gần tay.

## 2. Quyết định của người dùng (2026-10-13)

- Tóc và tai chung mesh với da: **tôi chọn từng mảnh** (cứng theo đầu hay lắc).
- Mảnh hiện ra: **gom thành lọn**; mỗi lọn là một phần trong danh sách Parts, mặc định cứng theo đầu, đổi sang Hair là
  lắc; bấm lọn thì lọn sáng lên trên mô hình; có nút tách, gộp lọn từ chỗ đang chọn.
- Kết quả nhận diện: **tô màu vùng lên mô hình**; lưu bằng **màu đỉnh, sửa bằng Vertex Paint** với bảng màu có sẵn.
- Lúc chạy: **nút riêng "Recognize" (Nhận diện)**; nếu chưa bấm, **Build tự bù**.
- Làm tự động phần 1 (spec → plan → code), không push, không merge.

## 3. Vùng

### 3.1 Sáu vùng

| Vùng | Tên trong giao diện | Màu (sRGB) | Xương của vùng |
|---|---|---|---|
| `HEAD` | Head (Đầu) | vàng (1,0; 0,85; 0,2) | Head |
| `TORSO` | Torso (Thân) | xanh dương (0,25; 0,55; 1,0) | Hips, Spine, Chest, UpperChest, Neck |
| `ARM_L` | Left Arm (Tay trái) | đỏ (1,0; 0,3; 0,25) | LeftUpperArm, LeftLowerArm, LeftHand, các xương ngón trái |
| `ARM_R` | Right Arm (Tay phải) | cam (1,0; 0,6; 0,15) | như trên, bên phải |
| `LEG_L` | Left Leg (Chân trái) | xanh lá (0,3; 0,85; 0,35) | LeftUpperLeg, LeftLowerLeg, LeftFoot, LeftToes |
| `LEG_R` | Right Leg (Chân phải) | tím (0,7; 0,4; 0,95) | như trên, bên phải |

Trái, phải là của nhân vật (trái ở +X), như tên xương. Xương vai (LeftShoulder, RightShoulder), mắt và hàm không
dùng để chia vùng. Mắt, hàm không bị giới hạn theo vùng; xương vai bị giới hạn như tay (§5) nhưng pha quanh chính
nó (*bổ sung khi làm*: nhân vật thử cho tai có 36% weight xương vai).

### 3.2 Lưu và đọc

- Lớp màu `DaskToon Region` (miền đỉnh, byte) trên mỗi mesh có phần Body hoặc Clothing. Khi tạo, lớp này không thành màu
  mặc định của mesh (`default_color_name` giữ như trước), để vật liệu đọc màu đỉnh không đổi.
- Đọc: mỗi đỉnh lấy vùng có màu gần nhất. Màu gần trắng hoặc gần đen (đỉnh mới thêm sau khi nhận diện, lớp vừa tạo) là
  **tự động**: vùng được tính lúc cần, không ghi vào lớp.
- Chỉ đỉnh thuộc phần Body, Clothing có vùng; đỉnh của phần khác (Hair, Skirt, Accessory, mặt) không dùng vùng.

### 3.3 Tự nhận diện

Tính ở tư thế nghỉ (pose của rig tạm đặt về Rest), vị trí đỉnh như weight: mesh gốc, không shape key, không modifier.

1. Đỉnh thuộc **mảnh gắn đầu** (§4) là `HEAD`.
2. Đỉnh còn lại: vùng có khoảng cách nhỏ nhất, đo từ bề mặt: khoảng cách tới xương gần nhất của vùng **trừ nửa bề rộng**
   của chỗ đó. Nửa bề rộng đọc từ bóng nhìn từ trước của các phần Body và Clothing (`body_shape`): tay, chân là nửa bề
   rộng chi tìm được; mỗi xương thân là nửa bề rộng đoạn bóng chạy qua giữa thân ở độ cao giữa xương, riêng UpperChest
   và Neck không quá nửa bề rộng lớn nhất của Hips, Spine, Chest (ở ngang vai, bóng thân dính vào tay nên rộng giả).
   Không đọc được thì lấy 0,03 (tay), 0,05 (chân), 0,1 (thân) của chiều cao nhân vật.

## 4. Mảnh gắn đầu và lọn

### 4.1 Mảnh gắn đầu

Mảnh là một nhóm đỉnh nối nhau bằng cạnh, trong các đỉnh thuộc phần Body, Clothing của một mesh. Mảnh gắn đầu khi:

- điểm cao nhất của nó cao hơn khớp cổ (đầu xương Head);
- điểm thấp nhất cao hơn khớp hông (đầu xương Hips), tức không phải cả lớp da;
- nó **không bao quanh cổ**: trong các đỉnh của nó cách độ cao khớp cổ dưới 0,05 chiều cao, thiếu ít nhất một trong bốn
  phía (trái, phải, trước, sau) của khớp cổ. Da mặt và cổ bao quanh cổ nên vẫn theo weight tự động, cổ còn cong được.

### 4.2 Lọn

- Mảnh gắn đầu cách nhau dưới 0,005 chiều cao (hai đỉnh gần nhất) gom thành một lọn.
- Bên của lọn theo trọng tâm: lệch khỏi giữa thân dưới 0,02 chiều cao là giữa (M), còn lại L hoặc R. Tên `Lock L1`,
  `Lock L2`, … đánh số từ trên xuống mỗi bên.
- Mỗi lọn là một **phần**: phạm vi Vertex Group (nhóm `DT_Lock L1`, weight 1), vai trò Accessory, xương Head (cứng theo
  đầu), đánh dấu "do Nhận diện tạo". Người dùng đổi vai trò sang Hair thì lọn có chuỗi xương lắc như mọi phần Hair.
- Đỉnh của lọn được tô vùng `HEAD`.

### 4.3 Nhận diện lại

- Lọn do Nhận diện tạo bị thay. Lọn mới trùng từ một nửa số đỉnh trở lên với một lọn cũ thì giữ vai trò và thiết lập của
  lọn cũ (xương, số xương, độ cứng, trọng lực, cản, bán kính, cách lắc trong Unity).
- Đỉnh đã thuộc phần do người dùng tạo (không đánh dấu) với vai trò khác Body, Clothing thì không vào lọn mới.
- Vùng đã tô bị ghi đè (nút hỏi trước).

### 4.4 Lọn từ chỗ chọn

Trong Edit Mode của mesh: các đỉnh đang chọn, mở rộng ra cả mảnh của chúng, thành một lọn mới (vai trò Accessory, xương
Head); chúng rời khỏi các lọn khác; lọn nào hết đỉnh thì bị xóa. Một nút cho cả tách (chọn một phần lọn) và gộp (chọn mảnh
của nhiều lọn).

## 5. Build

- Với đỉnh thuộc phần Body, Clothing, sau weight tự động hoặc chép từ Body, xương của mỗi chi chỉ giữ weight × `keep`:
  - trong vùng của chi: `keep` = 1;
  - ra khỏi vùng, `keep` giảm mượt theo **khoảng cách dọc bề mặt lưới** tới vùng chi, từ 1 về 0 trên một dải rộng
    3,5% chiều cao nhân vật (đường cong smoothstep);
  - mảnh không nối với vùng chi (tai, lọn tóc, dây đeo) và đỉnh vùng Đầu: 0.
  - *Sửa 2026-10-14 (độ chính xác)*: trước đây là `member` làm mềm 3 lượt (vài mm trên lưới dày) cộng một hình cầu
    pha quanh khớp gốc rộng 3 × nửa bề rộng chi đo từ hình chiếu. Lối cũ cắt gắt chỗ pha tự nhiên của Bone Heat giữa
    chi và thân: khi đo bằng công cụ `tools/dasktoon_rig_accuracy.py`, hông của tdt khi Ngồi rách 19 lần, lr 26 lần;
    vai khi Giơ tay rách 6–9 lần; bỏ hẳn giới hạn thì chỉ còn 2–3 lần. Đo dọc bề mặt nên eo cạnh cẳng tay đang buông
    vẫn không theo tay (hai bên không nối nhau qua khe hở), và bề rộng chi đo từ hình chiếu (tay lr chỉ 2,7 cm vì tay áo
    là mesh riêng) không còn quyết định gì.
- Xương vai (LeftShoulder, RightShoulder) giữ trọn weight trong khoảng 0,6 lần chiều dài của nó quanh đoạn xương vai,
  giảm mượt về 0 ở 1,3 lần chiều dài, trên mọi mảnh trừ đỉnh vùng Đầu (*sửa 2026-10-14*: trước đây tính theo bề rộng
  tay đo từ hình chiếu).
- Phần weight bị bỏ dồn cho các **xương nhà** mà đỉnh đang có, theo tỉ lệ của chúng:
  - đỉnh vùng chi: xương của chính chi đó;
  - đỉnh vùng thân: chỉ các xương thân (Hips đến Neck), không phải xương Đầu (*sửa 2026-10-14*: cổ áo sau gáy của tdt
    mất phần vai, phần đó dồn hết cho xương Đầu, nên cổ áo xoay theo đầu);
  - đỉnh vùng Đầu: các xương không chi nào giữ.
  Đỉnh không có xương nhà nào thì cho xương nhà gần nhất (cùng cách đo từ bề mặt). Đỉnh không còn weight nào cũng vậy.
  (*Bổ sung khi làm tự rig*: trước đây phần bị bỏ được chia lại cho mọi xương còn lại cho tổng 1, nên đỉnh eo chỉ có
  weight tay, giữ lại 3%, lại thành 100% tay; mục Kiểm tra thấy eo nhân vật thử rách khi giơ tay.)
- Vùng lấy từ lớp màu; đỉnh tự động được tính lúc Build. Lọn theo vai trò của nó (Accessory, Hair thắng Body, Clothing
  như spec rig §5.2).
- Nút **Build Rig**: nếu chưa mesh Body, Clothing nào có lớp vùng thì chạy Nhận diện trước (tô vùng, tạo lọn) rồi Build;
  thông báo có ghi điều đó. Hàm `build.build()` (script, test) không tự thêm phần, nhưng vẫn giới hạn weight theo vùng tính
  lúc đó.

## 6. Giao diện

Panel con **Regions** (Vùng) trong Anime Rig, sau Parts:

- **Recognize** (Nhận diện): tô vùng và tạo lọn; nếu đã có vùng thì hỏi trước "Tô lại vùng và tạo lại lọn? Chỗ bạn đã tô
  sẽ bị thay". Báo số lọn và số đỉnh mỗi vùng.
- **Show Regions** (Xem vùng): bật thì mọi khung 3D của cửa sổ chuyển sang Solid, tô theo màu đỉnh, lớp vùng là màu đang
  xem; tắt thì trả lại cách tô trước đó.
- **Paint Regions** (Tô vùng) với ô chọn vùng: chọn mesh của phần đang chọn (hoặc mesh Body đầu tiên), lớp vùng thành
  lớp đang tô, vào Vertex Paint với bảng màu "DaskToon Regions" và màu của vùng đã chọn, bật Xem vùng. Gợi ý: chọn mặt
  (Face Selection Masking) rồi Shift+K tô kín.
- Chú giải sáu màu.
- **Lock from Selection** (Lọn từ chỗ chọn): ở panel Anime Rig của mesh khi đang Edit Mode.
- **Highlight Part** (Làm sáng phần, mặc định bật) trong panel Parts: mặt của phần đang chọn được vẽ sáng lên trong khung
  3D, ở vị trí nghỉ, khi rig là object đang chọn.

Chữ mới có bản Việt.

## 7. Xuất sang Unity

Lớp vùng không bao giờ vào FBX: khi ghi FBX model, lớp `DaskToon Region` tạm bỏ rồi trả lại nguyên màu, cùng tên lớp
đang xem và lớp mặc định. Nhóm `DT_Lock …` không phải xương nên FBX không xuất.

## 8. Ngoài phạm vi phần này

Tự tạo chuỗi lắc cho lọn khi chưa ai chọn (người dùng chọn từng lọn); váy, tóc dài trong mesh không tên (phần 2); ngón
tay (phần 3); mắt, miệng (phần 4); vùng tay, chân riêng cho bàn tay, ngón tay.

## 9. Kiểm tra

- Nhân vật thử chibi chữ A trong một mesh Body: đầu to, tai thỏ là mảnh rời cạnh đầu thõng xuống ngang vai, một lọn tóc,
  áo (Clothing) có dây đeo trên ngực, giày rộng: Nhận diện cho đúng vùng ở các điểm đặc trưng; tai, lọn tóc thành lọn
  (đúng bên, tên); da mặt không thành lọn.
- Build: giơ tay thì tai, dây đeo không đi theo (weight tay bằng 0 ở đó); đỉnh trên tay giữ weight tay; giày giữ weight
  chân; tô một đỉnh tay áo sang Thân thì đỉnh đó hết weight tay.
- Nhận diện lại giữ vai trò Hair của lọn đã đổi; Lọn từ chỗ chọn tách và gộp đúng; lọn rỗng bị xóa.
- Xuất FBX: không có lớp màu vùng trong file; sau khi xuất, lớp vẫn còn, đủ màu.
- Giao diện: panel vẽ đủ nút; Xem vùng bật và trả lại; Tô vùng vào Vertex Paint với đúng lớp, màu; bản Việt.
- Mô hình thật (bản sao tdt, lr_shape): đếm lại đỉnh xa tay có weight tay; ảnh giơ tay trước, sau.
