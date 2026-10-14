# DaskToon: tự rig một nút và mục Kiểm tra — Báo cáo

Nhánh `dasktoon-auto-rig` (nối tiếp `dasktoon-rig-regions`). Spec
`docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md`, kế hoạch
`docs/superpowers/plans/2026-10-14-dasktoon-auto-rig.md`. Làm tự động theo yêu cầu, không push, không merge.

## 1. Kết quả

Chọn các mô hình của nhân vật, bấm **Thêm › Khung xương › Khung người anime**. Nút này thêm khung xương, khớp theo hình
nhân vật, nhận diện vùng và lọn, dựng rig, rồi chạy **Kiểm tra**. Bảng bên phải tự chuyển sang thẻ dữ liệu của khung
xương, nơi có mục Rig anime. Nếu không dựng được rig (ví dụ hai object dùng chung một mesh), khung xương vẫn còn, đã
khớp sẵn, và thông báo nói lý do.

Thử trên bản sao hai mô hình thật. Mở file gốc rồi lưu ngay sang bản sao; md5 hai file gốc trước và sau không đổi.

| | tdt | lr_shape |
|---|---|---|
| Thời gian một nút (thêm khung → kiểm tra xong) | 6,1 s | 9,8 s |
| Mục Kiểm tra lần đầu báo | Hai khuỷu tay nằm ngoài thân (8–9 mm trước mặt tay) | Hai khuỷu tay, hai đầu gối nằm ngoài thân (2–4 cm sau tay, chân) |
| Sau khi sửa bước khớp xương (mục 3) | Không thấy chỗ nào cần sửa | Không thấy chỗ nào cần sửa |

Mục Kiểm tra báo đúng cả sáu chỗ: đo bằng tia cho thấy các khớp đó thật sự nằm ngoài tay, chân. Nguyên nhân là bước
khớp xương đặt khuỷu và gối trên đường thẳng vai → bàn tay, hông → cổ chân, trong khi tay chân thật hơi cong. Đã sửa ở
bước khớp xương thay vì để người dùng tự kéo.

Tôi còn render bốn tư thế thử của hai bản sao và xem bằng mắt (ảnh chỉ để trên máy, không vào git). Ảnh của lr_shape cho
thấy một lỗi mà mục Kiểm tra không thấy: khi vẫy tay phải, tay áo **trái** bay ngang qua người. Đây là lỗi của bước Dựng
rig với modifier Mirror, đã sửa (mục 3). Sau khi sửa, cả bốn tư thế của hai mô hình không còn chỗ rách nhìn thấy được.

## 2. Mục Kiểm tra

![Mục Kiểm tra](auto-rig/70_check.png)

`auto-rig/70_check.png` (tiếng Việt, nhân vật thử, cửa sổ thật). Nhân vật thử của phần vùng cơ thể, có thêm một chiếc váy
loe và một lọn tóc sau đầu là mesh riêng, được chọn hết rồi bấm Khung người anime. Để ảnh có đủ ba loại dòng, sau đó
cổ tay trái được kéo ra ngoài bằng tay rồi bấm **Kiểm tra lại**, và bấm **Xem** ở chỗ rách đầu tiên.

- Đầu mục là **Tư thế thử**: Giơ tay, Ngồi, Quay đầu, Vẫy tay, Về nghỉ. Dáng được đặt thẳng lên xương: không khóa hình,
  không tạo clip, đổi khung hình thì hoạt hình của bạn hiện lại.
- Mỗi chỗ cần xem là một ô gồm câu và nút:
  - "Cổ tay trái nằm ngoài thân" có nút **Sửa**: vào chỉnh khớp với khớp đó chọn sẵn, bật đối xứng hai bên.
  - "Tay trái bị kéo giãn ở tư thế Giơ tay (Body)" có nút **Xem** (đặt tư thế đó và tô cam chỗ rách, như bên phải ảnh)
    và nút **Tô vùng** (mở Vertex Paint trên mesh đó với màu của vùng).
  - "Circle.008 trông như tóc" có nút **Đổi thành Tóc**: đổi vai trò, dựng lại, kiểm tra lại.
- Cuối mục là dòng "Sửa xong, bấm Dựng rig để kiểm tra lại", rồi hai nút **Kiểm tra lại** và **Xong** (xóa danh sách).

Hai dòng "Tay … bị kéo giãn ở tư thế Giơ tay" là lỗi thật của nhân vật thử: tay là ống cắm vào thân, Bone Heat cho vòng
đầu của ống theo ngực. Dòng "Thân bị kéo giãn ở tư thế Ngồi" do chiếc váy loe (xem mục 5).

## 3. Đã làm gì

- `dasktoon_rig/check.py` (mới): tư thế thử. Vị trí đỉnh trong mỗi tư thế được tính bằng weight, như modifier Armature.
  Ba loại kiểm tra:
  - khớp ngoài thân: ít hơn 4 trong 6 tia từ khớp trúng bề mặt Cơ thể, Quần áo;
  - chỗ rách: cạnh dài ra hơn 2,5 lần giữa hai xương cách nhau từ 4 bậc trở lên, mỗi chỗ từ 3 cạnh, các mẩu cách nhau
    dưới 5% chiều cao gộp làm một;
  - vai trò có vẻ sai: phần Quần áo trông như tóc hay váy.

  Danh sách lưu trên rig, mở lại file vẫn còn.
- `bl_ui/dasktoon_rig.py`: nút Khung người anime tự rig khi có mesh đang chọn; mục con **Kiểm tra** đứng đầu Rig anime;
  bảy nút mới (tư thế thử, Kiểm tra, Xong, Sửa, Xem, Tô vùng ở chỗ này, Đổi vai trò). **Dựng rig** chạy lại Kiểm tra khi
  đang có danh sách. Câu và tên khớp, vùng, tư thế đều có bản Việt.
- Lỗi mục Kiểm tra tìm ra và đã sửa:
  1. **Eo theo cẳng tay** (nhân vật thử, tư thế Giơ tay). Khi giới hạn weight tay chân trong vùng của chúng, phần bị bỏ
     được chia lại cho tổng 1. Vì thế một đỉnh eo chỉ có weight tay, giữ lại 3%, lại thành 100% tay. Nay phần bị bỏ về
     **xương nhà** của đỉnh: đỉnh vùng chi về xương của chi đó, đỉnh thân, đầu về xương thân, đầu.
  2. **Khuỷu tay, đầu gối nằm ngoài tay chân** (tdt, lr_shape). Nay chúng nằm giữa bề dày tay chân, đo theo đường trước
     → sau qua mesh Cơ thể (không có da thì qua Quần áo), hai bên như nhau. Lớp viền "vỏ lật" (Solidify lật mặt, cách da
     vài mm, như trên tdt) không bị nhầm là tay chân.
  3. **Nửa soi gương đi theo xương bên kia** (lr_shape, thấy qua ảnh render). Blender chỉ đổi nhóm `Right…` thành
     `Left…` cho nửa do Mirror sinh ra khi mesh có sẵn nhóm `Left…`. Trước đây Dựng rig chỉ tạo nhóm cho xương có weight.
     Nay Dựng rig tạo nhóm bên kia và bật lật nhóm của Mirror (kèm cảnh báo).
  4. Khi làm nút Đổi thành Tóc: nhận diện lại với lọn nằm trên hai mesh để sót lọn cũ (biến vòng lặp che mất tham số).

## 4. Quyết định tôi tự đưa ra

Mỗi dòng là: quyết định — cái giá nếu sai.

- Báo chỗ rách chỉ khi hai xương cách nhau từ 4 bậc trở lên (khớp gập thường kéo da giữa hai xương kề nhau) — chỗ rách
  giữa ngực và cánh tay trên (3 bậc) không được báo.
- Kiểm tra "nhân vật đúng thì không báo gì" được thay bằng kiểm tra với weight đặt tay (gối gập, tai rách), vì weight tự
  động của nhân vật thử thật sự xấu. Kiểm tra tự rig trên nhân vật thử chờ đúng hai chỗ rách ở gốc tay — khi gốc tay có
  weight tốt hơn thì phải sửa kiểm tra.
- Gấu váy phải là một vòng quanh hông (điểm gần trục nhất cách trục ít nhất nửa bán kính trung bình) — váy rất hẹp ở
  gấu có thể không được nhận.
- Phần weight bị bỏ về xương nhà (mục 3.1) — weight gần ranh giới vùng khác trước một chút.
- Dựng rig chạy lại Kiểm tra khi đang có danh sách — Dựng rig chậm hơn với ai đã dùng Kiểm tra.
- Phần đang chọn chỉ được tô sáng khi rig ở tư thế nghỉ; chỗ đang xem chỉ hiện khi rig còn ở đúng tư thế đó — không thấy
  tô sáng phần ở khung hình có tư thế.
- Đổi thành Tóc/Váy bỏ các lọn mà Nhận diện đã tạo trên mesh đó — lọn bạn đã chỉnh trên mesh đó cũng mất.
- Nút Tô vùng chỉ có với chỗ nằm trên phần Cơ thể, Quần áo; chỗ đang xem tô cam xuyên qua mọi thứ.
- Khuỷu tay, đầu gối nằm giữa bề dày tay chân; khoảng mỏng hơn 1% chiều cao là lớp vỏ, không phải tay chân — tay chân
  mỏng hơn 1% chiều cao không được căn giữa.
- Tạo nhóm đỉnh bên kia và bật lật nhóm của Mirror khi dựng rig — mesh soi gương có thêm nhóm `Left…`/`Right…` rỗng.

## 5. Giới hạn đã biết, việc nên làm sau

- Mục Kiểm tra đo trên mesh như đã dựng, chưa qua modifier: nửa do Mirror sinh ra và lớp Subdivision không được đo.
  Lỗi tay áo của lr_shape chỉ thấy qua ảnh render.
- Một mảnh rời đi theo nhầm xương mà không bị kéo giãn (cả mảnh dời đi) không bị bắt (spec 4.2).
- **Váy loe không mang tên "váy"** (bị đoán là Quần áo) bị bước khớp xương coi là một phần thân. Hông bị đặt xuống ngang
  gấu váy. Mục Kiểm tra khi đó báo "Thân bị kéo giãn ở tư thế Ngồi" nhưng không báo "trông như váy", vì phép đoán váy
  dùng chính khớp hông đã lệch. Nên làm ở phần 2 của việc nhận diện (váy và tóc dài).
- Chuỗi xương tóc, váy không được soi gương: nếu mesh tóc, váy chỉ dựng một nửa rồi dùng Mirror, nửa kia đi theo cùng
  chuỗi xương.
- Ngưỡng (2,5 lần, 4 bậc, 4/6 tia, 1% chiều cao) mới thử trên nhân vật thử và hai mô hình. Cần thêm mô hình để chỉnh.

## 6. Kiểm tra tự động

- Kiểm tra mới: `dasktoon_rig_check_test` (9), Kiểm tra và tự rig trong `dasktoon_rig_ui_test` (38 tất cả), khuỷu gối
  trong `dasktoon_rig_skeleton_test` (13), xương nhà và lọn hai mesh trong `dasktoon_rig_regions_test` (20), nửa soi
  gương trong `dasktoon_rig_build_test` (27).
- Toàn bộ: 66 tệp, 622 kiểm tra đều qua (59 tệp thường và 7 tệp chạy Unity 6000.5).
