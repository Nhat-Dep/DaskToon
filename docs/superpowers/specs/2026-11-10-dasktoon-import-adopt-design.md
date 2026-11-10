# Nhập MMD và .uemodel thành nhân vật DaskToon (2026-11-10)

Yêu cầu: "sửa chức năng import mmd và uemodel để nó tự động cho dasktoon". Trước đây hai bộ nhập chỉ đưa mô hình vào
như nguồn của nó (khung xương MMD với hàng trăm xương phụ và vật lý; khung Unreal kiểu Bip001), nên các công cụ DaskToon
(Hướng dẫn, Hoạt hình, đung đưa, biểu cảm, Xuất sang engine) không dùng được ngay.

## 1. Kết quả

Sau Tệp › Nhập (hoặc kéo thả tệp vào cửa sổ 3D) với ô **Nhân vật DaskToon** bật sẵn:

- nhân vật đứng giữa cảnh, chân trên sàn, quay mặt ra trước (-Y), mọi phép biến đổi đã áp vào dữ liệu;
- khung xương là khung chuẩn DaskToon (tên Unity), khớp đặt đúng chỗ xương gốc, **trọng số gốc của mô hình được giữ**
  (không tính lại bằng nhiệt như Dựng rig);
- tóc, váy, ruy-băng là chuỗi đung đưa DaskToon (ràng buộc Spring) với vật va chạm quanh thân;
- biểu cảm mang tên DaskToon hiểu; vật liệu dùng shader DaskToon có ảnh màu gốc.

Đối tượng › Biến thành nhân vật DaskToon làm điều tương tự cho mô hình đã nhập từ trước.

Ô riêng **Shader DaskToon** (bật sẵn, người dùng hỏi thêm cùng ngày): mọi vật liệu của mô hình nhận shader DaskToon
ngay sau khi nhập, kể cả khi tắt "Nhân vật DaskToon" hay khung xương lạ không chuyển được (mô hình đồ vật). Khối vật lý
và khớp của MMD Tools (khi nhập kèm vật lý) không bị đụng tới.

Ô **Viền ngoài** (tắt sẵn, người dùng hỏi cùng ngày): vật liệu nhập vào không có viền. Lý do đo được: vỏ viền ghép vào
một lưới có hàng trăm nhóm đỉnh (mỗi xương một nhóm) chép từng nhóm thành một mảng cho mọi đỉnh — Hsin (92 nghìn đỉnh,
705 nhóm) mất 3,3 giây/khung có viền, 0,026 giây/khung không viền. Màu viền (ảnh màu làm tối) vẫn được nối sẵn, nên
bật viền sau cho từng material thì viền đúng màu.

## 2. Nhập MMD (dasktoon_import/mmd.py)

MMD Tools đọc lưới, khung xương, hình mẫu; **không** nhập vật lý (rigid body) vì đung đưa DaskToon thay nó. Tệp .pmx/.pmd
được đọc lại để biết xương nào do vật lý động (rigid body chế độ 1, 2) di chuyển: đó là xương đung đưa. Mục nhập mô hình
của MMD Tools trong menu và trình thả tệp .pmx của nó nhường cho DaskToon (VMD, VPD vẫn của MMD Tools).

## 3. Nhận diện xương (dasktoon_import/bones.py)

Tên cho biết bên và loại xương theo cách đặt tên của MMD (tiếng Nhật, 左/右, có tên tiếng Nhật gốc làm tên phụ),
3ds Max Biped, Unreal, Mixamo, VRoid và chính DaskToon. Hình dáng quyết định phần còn lại:

- cột sống: các xương loại "spine" trên đường từ cổ xuống, theo thứ tự treo; 1 xương → Spine, 2 → Spine, Chest,
  ≥3 → đầu, giữa, cuối;
- ngón tay: ba khớp đầu tiên của mỗi ngón theo thứ tự treo (bỏ đốt bàn tay của UE5 vì tên không khớp, bỏ "đầu ngón");
- bên trái của nhân vật là +X: tên ngược với vị trí thì đổi lại;
- xương đôi (MMD 足 và 足D) cùng chỗ: khớp lấy từ cái gần gốc, trọng số gộp cả hai.

Thiếu xương bắt buộc (skeleton.REQUIRED) thì báo lỗi **trước khi thay đổi gì** — mô hình giữ nguyên.

## 4. Khung mới và trọng số (dasktoon_import/adopt.py)

- Hips ở giữa hai đầu đùi; xương cột sống thiếu chèn theo tỷ lệ mẫu; đuôi xương ở đầu xương kế, không có thì theo
  đuôi xương gốc, không thì nối dài xương cha.
- Trọng số của một xương gốc đi về: xương DaskToon mang tên đó; chính nó nếu được giữ (đung đưa, hoặc nằm giữa chuỗi
  đung đưa và thân); nếu MMD cho nó xoay theo xương khác một phần f (xoắn tay, trợ khuỷu) thì f về xương DaskToon của
  xương kia, 1−f về của xương cha; còn lại về xương DaskToon của xương cha. Mỗi đỉnh tối đa 4 trọng số, tổng 1
  (như weights.tidy, làm dạng thưa: mô hình 100 nghìn đỉnh × 600 xương mà làm ma trận đầy là hàng GB).
- Không có thông tin vật lý (.uemodel): xương đung đưa là các xương có trọng số, không mang tên DaskToon, không phải
  xương xoắn, nằm trong chuỗi ≥2; xương có từ hai chuỗi con trở lên (mũ với các ruy-băng) đứng yên.
- Chuỗi đánh dấu như chuỗi Dựng rig tạo (dt_part), mỗi chuỗi một đường thẳng; vật va chạm tính như Dựng rig từ đỉnh
  thân. Thông số đung đưa mặc định của DaskToon.

## 5. Biểu cảm (dasktoon_import/faces.py)

Đổi tên: あいうえお → A I U E O, まばたき/E_Close → Blink. Nháy mắt thành Blink_L / Blink_R theo **phía các đỉnh
thật sự di chuyển**, không theo tên (hai mô hình MMD thật đặt "右" ngược nhau). Joy, Angry, Sorrow, Fun, Surprised là
hình mẫu mới cộng lông mày + mắt + miệng có sẵn của mô hình (cần ít nhất 2 trong 3). Hình mẫu mới tạo phải đặt về 0:
trong bản lõi này một hình mẫu mới bắt đầu ở mức 1.

## 6. Vật liệu, đứng, dọn

- Shader DaskToon cho mọi vật liệu (dasktoon_material_convert). Sửa chung: nhóm nút của MMD Tools nhận Ambient,
  Diffuse trước ảnh màu; giờ chọn ô màu có ảnh nối vào trước, rồi ô màu có nối, rồi ô đầu; Alpha lấy từ ô "alpha" có
  nối.
- Sửa chung ở Kiểm tra mô hình: một Anime BSDF nằm trong cây nút mà không nối ra đầu ra (vật liệu mới của MMD Tools
  có sẵn một cái) không còn được tính là "đã dùng shader DaskToon".
- Đứng: các sửa của Kiểm tra mô hình (hướng, cỡ khi lệch xa, sàn, giữa) rồi áp mọi phép biến đổi.
- Bỏ: đối tượng gốc rỗng của MMD Tools, hình mẫu mmd_sdef_*, khung xương gốc.

## 7. Lỗi có sẵn tìm thấy và sửa

- Bộ nhập .uemodel bật mọi hình mẫu ở mức 1 (mặt nát vì 87 biểu cảm cùng lúc). Kiểm tra cũ chỉ so toạ độ trong hình
  mẫu, không xem giá trị và lưới hiện ra; nay kiểm tra cả hai.

## 8. Quyết định tôi tự chọn

1. Giữ trọng số gốc thay vì dựng lại bằng Dựng rig: mô hình game/MMD có trọng số do người làm, tốt hơn trọng số nhiệt;
   ghi nhớ trước đó cho thấy tự rig hỏng trên mô hình xé từ game.
2. Làm khung mới rồi xoá khung gốc, thay vì đổi tên trong khung gốc: khung MMD đầy xương điều khiển, IK, ràng buộc.
3. Xương phụ không đung đưa gộp vào xương DaskToon (không giữ riêng): khi diễn bằng khung người chúng chuyển động như nhau,
   khung xuất sang Unity gọn hơn.
4. Đổi tên hình mẫu thay vì sao chép (chuyển động VMD theo tên tiếng Nhật không dùng được nữa vì khung MMD đã bỏ).
5. "Nhân vật DaskToon" bật mặc định; tắt thì nhập như cũ.

## 9. Còn lại

- Viền ngoài trên mô hình nhiều xương vẫn chậm khi bật: chỗ tốn là bước Join vỏ với lưới gốc (chép nhóm đỉnh),
  không phải gộp đỉnh/tìm đỉnh gần nhất. Thử nhanh: để vỏ làm bản thể (Geometry to Instance) thay vì ghép, 3,1 → 0,07
  giây/khung. Chưa làm: cần xem Hành động nhanh, kiểm tra viền và xuất engine có dựa vào vỏ nằm chung lưới không.
- Váy/áo choàng dài nhiều xương bay mạnh khi di chuyển nhanh với thông số mặc định; có thể lấy giảm chấn từ vật lý MMD.
- Venti (tệp tải về) tên ảnh trong .pmx khác tên tệp trên đĩa nên mất màu — lỗi của bản tải, MMD Tools cũng vậy.
- Vật liệu do bộ nhập .uemodel làm trông nhạt hơn bản MMD của cùng nhân vật.

## 10. Tóc không tự biến dạng khi đứng yên (người dùng yêu cầu cùng ngày)

"Phần tóc khi rig không nên tự ý biến dạng so với lúc chưa rig hoặc rig gốc khi import". Đo trên Phoebe: đứng yên,
bật đung đưa, sau 30 khung tóc/váy lệch tới 360 mm (.pmx) và 151 mm (.uemodel), 15 nghìn đỉnh. Nguyên nhân là va
chạm, không phải trọng lực: gốc chuỗi tóc nằm sẵn trong khối va chạm của đầu/thân nên bị đẩy văng ngay từ khung đầu.

Sửa chung trong dasktoon_rig/sway.py (cả chuỗi do Dựng rig tạo): mỗi khớp của chuỗi nhận khối va chạm thu nhỏ vừa đủ
để không chạm đuôi khớp đó ở tư thế nghỉ; khớp nào lúc nghỉ đã nằm trong khối thì bỏ khối đó. Sau sửa: lệch 0 mm;
khi chuyển động tóc vẫn va vào thân. Kiểm tra cũ không bắt được vì nhân vật mẫu có chuỗi nằm ngoài khối va chạm; kiểm
tra nhập nay cho tóc mọc từ trong đầu và đòi đứng yên giữ nguyên hình.

Còn lại: Unity và Godot dùng chung một khối va chạm (một bán kính) cho mọi chuỗi, nên trong engine tóc vẫn có thể bị
đẩy lúc đứng yên; cần xuất kèm bán kính/bỏ qua theo từng khớp và sửa script của hai engine.

## 11. Điều khiển và bảng mặt khi nhập (người dùng chọn cùng ngày)

Ô **Điều khiển** (bật sẵn) ở hộp nhập: nhân vật nhập vào có luôn lớp điều khiển Rigify và bảng mặt
(docs/superpowers/specs/2026-11-06-dasktoon-rig-controls-design.md §17). Khung thiếu khớp Rigify cần (ví dụ không có
ngón) thì nhập vẫn xong, báo "Không gắn được điều khiển: …". Anaxa, Shorekeeper, Phoebe .uemodel: thêm điều khiển
1,5–2,5 giây, tư thế nghỉ không xê dịch.
