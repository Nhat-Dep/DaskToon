# DaskToon: nhận diện vùng cơ thể và lọn gắn đầu (phần 1) — Báo cáo

Nhánh `dasktoon-rig-regions` (nối tiếp `dasktoon-real-model-fixes`). Spec
`docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md`, kế hoạch
`docs/superpowers/plans/2026-10-13-dasktoon-rig-regions.md`. Làm tự động theo yêu cầu, không push, không merge.

## 1. Vấn đề và kết quả

Lần thử trên mô hình thật cho thấy: giơ tay phải thì tai thỏ bị kéo xuống ngực, lọn tóc kéo ngang mặt, dây đeo bị kéo
ra. Bone Heat chia weight theo khoảng cách tới xương, mà xương Head của chibi là một đường mảnh giữa cái đầu rất to, nên
vai và cánh tay gần tai hơn Head.

Đo trên bản sao `tdt.blend` (file gốc không đổi, md5 như cũ), cùng quy trình như người dùng: Add › Anime Humanoid, thêm
mesh làm phần, Fit to Parts, bấm **Build Rig** (nút tự Nhận diện trước):

| | Trước (sau bốn lỗi đã sửa) | Bây giờ |
|---|---|---|
| Đỉnh da (gồm tóc, tai) có weight cánh tay, cách tay hơn 20 cm | 1 714 và 1 751 (hai bên, tới 0,79) | 0 (weight tay chỉ còn trên 1 101 đỉnh cẳng tay, bàn tay) |
| Đỉnh áo có weight cánh tay, cách tay hơn 20 cm | 303 / 343 | 3 mỗi bên, tới 0,09 (mép trên tay áo sát khớp vai) |
| Đỉnh áo có weight chân, cách chân hơn 20 cm | 185 | 20 (quanh khớp hông, phần pha) |
| Lọn | không có | 49 mảnh gắn đầu gom thành 5 lọn, cứng theo đầu |
| Build | 2,1–2,9 s | 4,4 s (thêm phần nhận diện) |

lr_shape (bản sao): tóc là mesh riêng bị đoán là Clothing (trước có 194 đỉnh theo cánh tay tới 0,39) nay thành một lọn
cứng theo đầu, không còn weight tay; không đỉnh nào cách tay hơn 20 cm có weight tay.

Ảnh (chỉ trên máy, không vào git, ở `docs/superpowers/reports/real-model/`):

- `7_rig_regions_before_after.png`: giơ tay, nhìn trước, 3/4, sau; trái là trước, phải là bây giờ.
- `8_regions_colors.png`: vùng đã nhận diện tô màu (trước, sau): đầu vàng (cả tai, tóc), thân xanh dương, tay trái đỏ,
  tay phải cam, chân trái xanh lá, chân phải tím.

## 2. Đã làm gì

- `dasktoon_rig/regions.py` (mới): sáu vùng, độ rộng thân, tay, chân đọc từ bóng nhìn trước; mỗi đỉnh của phần Body,
  Clothing về vùng gần nhất tính từ bề mặt; mảnh gắn đầu (đỉnh trên khớp cổ, đáy trên khớp hông, không bao quanh cổ) về
  vùng đầu và gom thành lọn.
- Vùng lưu ở lớp màu `DaskToon Region` của mesh (không thành màu mặc định nên vật liệu không đổi); không bao giờ vào FBX.
- Lọn là phần (nhóm đỉnh `DT_Lock …`, Phụ kiện cứng trên Head); đổi sang Tóc là lắc. Nhận diện lại giữ vai trò và thiết
  lập của lọn cũ; lọn bạn tự làm thì giữ nguyên.
- Build: xương tay, chân chỉ giữ weight trong vùng của chi (mép làm mềm 3 vòng đỉnh), pha quanh khớp vai, hông trên mảnh có
  phần của chi; xương vai chỉ giữ quanh chính nó, không trên đầu.
- Giao diện, panel **Regions** (Vùng) trong Anime Rig: **Recognize** (Nhận diện; hỏi trước khi tô lại), **Show Regions**
  (Xem vùng), sáu nút tô từng vùng (vào Vertex Paint với bảng màu "DaskToon Regions", khi đang tô thì panel mesh có sáu
  nút và **Done Painting**); **Highlight Part** (Làm sáng phần) trong panel Parts; **Lock from Selection** (Lọn từ chỗ
  chọn) trong panel mesh khi Edit Mode: tách hoặc gộp lọn.

## 3. Quyết định tôi đã đưa ra (tự động)

1. Kế hoạch viết ngắn, code viết trong bước TDD. *Nếu sai:* ít được xem trước khi code.
2. Độ rộng tay, chân lấy trung bình hai bên (vùng đối xứng như khung). *Nếu sai:* trang phục lệch hai bên bị đo đối xứng.
3. Tên lọn để tiếng Anh (`Lock L1`), như tên xương sinh ra. *Nếu sai:* giao diện tiếng Việt thấy tên phần tiếng Anh.
4. Lớp vùng không thành màu đang xem hay mặc định của mesh. *Nếu sai:* muốn xem vùng phải bấm Xem vùng.
5. Xương vai cũng bị giới hạn (tai trong nhân vật thử có 36% weight vai): chỉ giữ quanh chính nó, trên mọi mảnh (dây vắt
   qua vai vẫn theo vai), không trên đầu. *Nếu sai:* nhún vai kéo ít phần ngực xa xương vai hơn.
6. Phần pha quanh khớp chỉ trên mảnh có phần của chi (lọn tóc trước vai trong nhân vật thử từng giữ 15% weight tay). *Nếu
   sai:* một mảnh cổ áo rời chạm vai không pha với tay.
7. Hàng weight sau khi giới hạn chia lại cho tổng 1 (vòng hàm R3 cần thế). *Nếu sai:* chưa thấy rủi ro.
8. Phần nhận diện trong Build chạy sau khi gắn mesh vào rig: chạy trước đó (sau khi tạo driver của miệng 2D) làm driver
   không chạy, chưa tìm ra nguyên nhân; có chú thích trong code. *Nếu sai:* sắp xếp lại sau này có thể làm hỏng driver.
9. Lọn bạn làm từ chỗ chọn là của bạn: Nhận diện lại không thay, không lấy mảnh của nó. *Nếu sai:* muốn quay về lọn tự
   động thì xóa lọn của bạn trước.
10. Chọn vùng bằng sáu nút có màu thay vì danh sách thả xuống (một lần bấm, kiêm chú giải). *Nếu sai:* panel dài hơn.
11. Làm sáng phần vẽ ở tư thế nghỉ, ẩn khi đang phát animation. *Nếu sai:* rig đang tạo dáng thì chỗ sáng nằm ở tư thế
    nghỉ.
12. Xem vùng đổi mọi khung 3D của file và lớp đang xem của mọi mesh có vùng, rồi trả lại. *Nếu sai:* khung 3D ở workspace
    khác cũng đổi trong lúc bật.

## 4. Lỗi tìm ra khi tự xem lại, đã sửa (mỗi lỗi có test thấy hỏng trước)

- Làm sáng phần tính lại ở mọi khung hình armature biến dạng mesh (chậm khi phát): nay chỉ khi dữ liệu mesh đổi.
- Xem vùng trả nhầm cách tô cũ sau khi mở file khác (địa chỉ khung cũ bị dùng lại).
- Build, Nhận diện, Tô vùng gặp khung không chuẩn (thiếu Hips) thì lỗi Python thay vì báo "không phải khung chuẩn".
- Nhận diện có thể đặt tên lọn trùng tên lọn bạn đã làm (hai phần Tóc trùng tên sẽ sinh xương trùng).

## 5. Còn lại

- Ảnh giao diện chụp trong cửa sổ thật (nhân vật thử, không phải mô hình của bạn), tiếng Việt và tiếng Anh, ở
  `docs/superpowers/reports/rig-regions/vi` và `.../en`, công cụ `tools/dasktoon_rig_regions_screenshots.py`:
  `60_regions_panel` (danh sách Parts có lọn, panel Vùng), `61_show_regions` (Xem vùng), `62_highlight` (lọn tai trái
  sáng lên), `63_paint_regions` (đang tô tay trái: panel mesh có sáu nút và Tô xong). Chạy cửa sổ thật tìm ra ba lỗi mà
  test chạy nền không thấy, đã sửa: tên biểu tượng màu của Blender 5.2 là `STRIP_COLOR_xx` (tên cũ làm panel Vùng không vẽ
  được; nay có test kiểm tra mọi biểu tượng có thật); Xem vùng đổi lớp màu đang xem mà khung 3D không vẽ lại; phần làm
  sáng bị chính mặt lưới che (nay vẽ nhích về phía người xem).
- lr_shape: bốn lọn trên mesh thân (L1, L2, R1, R2) là mắt, lông mày; chúng cứng theo đầu như trước. Phần 4 (mắt, miệng)
  sẽ nhận ra chúng.
- Tên lọn tiếng Anh; cột sống tdt hơi ra trước (từ lần trước).

## 6. Test

Toàn bộ test Python: 58 file, 585 test, đều đạt. Mới: `dasktoon_rig_regions_test.py` (18 test: vùng, lọn, độ rộng, lớp
màu, nhận diện lại, lọn từ chỗ chọn, giới hạn weight trong Build, nút Build tự nhận diện); thêm vào
`dasktoon_rig_ui_test.py` (panel Vùng, Nhận diện, Tô vùng, Xem vùng, làm sáng, khung không chuẩn, Lọn từ chỗ chọn) và
`dasktoon_export_fbx_test.py` (lớp vùng không vào FBX).
