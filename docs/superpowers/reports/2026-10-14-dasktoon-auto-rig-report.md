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

- Phép thử chỗ rách đo trên mesh như đã dựng, chưa qua modifier: nửa do Mirror sinh ra và lớp Subdivision không được
  đo (phép thử khớp thì có tính nửa Mirror). Lỗi tay áo của lr_shape chỉ thấy qua ảnh render.
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
- Tự rà soát cả nhánh sau đó (không dùng người rà soát khác) tìm thêm hai lỗi, đã sửa, mỗi lỗi có kiểm tra hỏng trước:
  thân dựng một nửa rồi dùng Mirror bị báo nhầm các khớp bên kia "nằm ngoài thân" (phép thử khớp nay tính cả nửa do
  Mirror sinh ra); nút Đổi vai trò với một phần đã mất mesh xóa hết lọn. Chạy lại các kiểm tra rig: đều qua.

## 7. Vai nâng theo tay (thêm sau, nhánh `dasktoon-shoulder-follow`)

Bạn hỏi vì sao vai trông "gãy" khi giơ tay. Câu trả lời là do rig, không phải do mô hình. Chỉ cánh tay trên xoay quanh
khớp vai, còn xương vai đứng yên, nên đỉnh vai bẹp và nách gập thành góc. Thiết kế:
`docs/superpowers/specs/2026-10-14-dasktoon-shoulder-follow-design.md`.

- Dựng rig nay cho xương vai tự nâng khi cánh tay giơ ngang:
  - bắt đầu khi tay ở 30° dưới đường ngang;
  - tới 35° khi tay thẳng đứng, nhịp khoảng 1 : 3,4 như vai người.
- Thanh trượt **Vai nâng theo tay** (0–1) nằm ở Rig anime › Khớp nối.
- Khóa hình vai bạn tự đặt vẫn có tác dụng; phần nâng được cộng thêm.
- Clip xuất ra FBX đã có sẵn góc nâng, nên Unity không cần gì thêm. Đã kiểm chứng bằng cách xuất rồi nhập lại, và chạy
  kiểm tra rig, clip trong Unity.
- Trên tdt (bản sao), tư thế Vẫy tay nâng vai 20,6°. So ở cùng độ cao cánh tay: đỉnh vai không còn bẹp, khấc ở nách
  nhỏ và mềm hơn rõ, nhưng nách vẫn còn một góc nhẹ. Phần đó thuộc về weight quanh đỉnh vai, có thể làm sau.
  Ảnh ở `real-model/10_shoulder_follow_off_on.png`, chỉ trên máy, không vào git.
- Tự rig trên tdt và lr_shape vẫn không thấy chỗ nào cần sửa.
- Hai lỗi gặp khi làm, đã sửa:
  - driver kiểu "Transform" gây vòng lặp phụ thuộc, nên driver đọc thẳng quaternion của cánh tay;
  - trục kiểu trục–góc bị trả về mặc định khi đưa xương về nghỉ, làm vai xoắn thay vì nâng.


## 8. Độ chính xác của rig (nhánh `dasktoon-rig-accuracy`)

Bạn yêu cầu làm rig thật chính xác trước khi làm tiếp. Mục Kiểm tra trên tdt và lr_shape báo "không có gì cần sửa",
nhưng đo kỹ thì có rách. Công cụ đo mới `tools/dasktoon_rig_accuracy.py` chạy trên bản sao đã tự rig và đo bốn thứ:

- khớp lệch khỏi giữa chi bao nhiêu (mặt cắt ngang qua khớp);
- cạnh lưới giãn bao nhiêu ở bốn tư thế thử (rách = dài ra hơn 2,5 lần và thêm hơn 0,3% chiều cao);
- trọng số hai bên trái, phải có giống nhau không;
- trọng số tay chân có lọt ra xa khỏi chi không.

Kết quả, trước khi sửa → sau khi sửa (tdt / lr_shape, cao 2,95):

| Đo | Trước | Sau |
|---|---|---|
| Hông lệch khỏi giữa đùi | 3,7–6,7 cm | 2,5 / 12 mm |
| Cổ chân lệch khỏi giữa cẳng chân | 3–11 cm | 4 / 6 mm |
| Cổ tay lệch khỏi giữa cẳng tay | 1–2 cm | 4 / 6 mm |
| Eo (cột sống) lệch khỏi giữa thân | 12 / 10 cm | 5,6 / 7,3 mm |
| Ngồi: chỗ giãn nặng nhất | 19× / 26×, dài thêm 11–16 cm | 2,2× / 2,3×, không cạnh nào rách |
| Giơ tay | 6× / 8,9× | 3,2× / 4,3× (7 cạnh, dài thêm 13 / 21 mm) |
| Quay đầu | 8,4× (tdt) | 1,7× / 2,0×, không cạnh nào rách |
| Trọng số lọt xa khỏi chi | 0 | 0 |

Đã sửa (mỗi phần có kiểm tra hỏng trước rồi mới qua):

1. **Giữ tay chân trong vùng của chúng** nay giảm dần dọc bề mặt lưới trên dải 9% chiều cao, không cắt gắt nữa. Thử
   3,5%, 6%, 9%; dải hẹp làm mông rách khi Ngồi.
2. **Khớp tay chân nằm trên đường giữa của chi**, tìm từ mặt cắt ngang. Trước đây độ sâu lấy từ mọi đỉnh gần đó, gồm cả
   tóc buông sau hông và gót giày.
3. **Nhân vật quay lưng được xoay lại** (lr_shape quay mặt về +Y): bàn chân cho biết hướng mặt (§2).
4. **Cột sống đi qua giữa thân** theo mặt cắt từng đốt. Tóc dài sau lưng từng kéo cả cột sống lùi 10–12 cm. Cổ để nghiêng
   theo đường nối giữa ngực với giữa cổ.
5. **Vùng đầu không lấn xuống ngực** nữa, và **xương Đầu chỉ giữ trọng số quanh đầu**. Đầu chibi to từng chiếm đỉnh
   ngực, làm gốc tay rách và dây đeo trên áo xoay theo đầu.
6. **Trọng số hai bên giống hệt nhau** ở chỗ mô hình đối xứng đúng từng đỉnh (Bone Heat cho hai bên hơi khác nhau).
7. **Mục Kiểm tra bắt được chỗ rách rộng giữa hai xương kề nhau** (dài thêm hơn 2% chiều cao). Trước đây hông rách 11–16
   cm mà không báo.

Quyết định tôi tự đưa ra:

- Dải giảm dần 9% chiều cao: rộng nhất mà chưa làm tay chân kéo theo bụng hay lưng. Nếu sai: mông, vai trên mô hình lưới
  thưa khác có thể vẫn giãn, hoặc bụng nhích theo đùi một chút.
- Cổ để nghiêng (giữa cổ lệch 3 cm khỏi tâm cổ) thay vì đúng tâm: dựng cổ thẳng đúng tâm thì Quay đầu làm tóc sau gáy
  rách 13–26 cạnh, cổ nghiêng thì không cạnh nào. Nếu sai: cổ xoay quanh trục hơi lùi sau.
- Chỉ ghép cặp đối xứng đúng vị trí: ghép gần đúng (3–6 mm) làm vai áo tdt rách 4,9–7,4 lần. Nếu sai: chỗ mô hình lệch
  vài mm (cổ áo tdt) vẫn hơi khác hai bên (2,5% cặp đỉnh lệch hơn 0,1).
- Xoay nhân vật tự động khi cả hai bàn chân chỉ rõ cùng một hướng; không rõ thì để nguyên. Nếu sai: một nhân vật bị xoay
  nhầm. Cảnh báo luôn nói đã xoay bao nhiêu độ, và Ctrl+Z hoàn tác được.
- Ngưỡng "rách rộng" của mục Kiểm tra là 2% chiều cao: khớp gập thường trên hai mô hình chỉ làm da dài thêm tối đa 2 cm.
  Nếu sai: bỏ sót chỗ rách vừa vừa, hoặc báo nhầm khớp gập mạnh.

Giới hạn còn lại, nên làm sau:

- **Da xuyên qua áo khi giơ tay** (thấy trên lr_shape ở sườn dưới nách). Áo lr dựng một nửa, lưới thưa, làm mịn bằng
  Subdivision sau Armature. Áo đã chép trọng số từ da (93% đỉnh áo), nhưng mặt áo làm mịn co vào ở nách. Cách chữa
  thường dùng là ẩn phần da nằm dưới áo. Nên làm thành một tính năng riêng.
- Vai, nách khi giơ tay vẫn giãn 3–4 lần trên một mảnh áo (dài thêm 1–2 cm).
- Chỗ nối cổ với đầu vẫn theo tỉ lệ cố định của khung mẫu. Chibi đầu rất to (đầu chiếm hơn một phần tư chiều cao) thì đỉnh
  cổ nằm lọt vào trong đầu. Nên đo từ chỗ cổ hẹp nhất.
- Công cụ đo đo cổ bằng mặt cắt nằm ngang; cắt xiên theo đốt cổ nghiêng thì đường cắt chạy vào hàm.

Kiểm tra tự động: toàn bộ 67 tệp, 647 kiểm tra (gồm 7 tệp chạy Unity 6000.5). Tự rà soát cả nhánh (không dùng người rà
soát khác) tìm thêm một lỗi: bước soi gương trọng số đụng cả những đỉnh không thuộc phần nào, nên trọng số bạn tự vẽ ở
đó có thể bị đổi. Đã sửa: nay chỉ soi gương đỉnh thuộc phần. Lỗi này có kiểm tra hỏng trước rồi mới qua, và các kiểm
tra rig chạy lại đều qua.
