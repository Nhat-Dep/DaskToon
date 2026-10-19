# DaskToon: sửa lỗi khi đưa model có sẵn vào, và nhận diện rig phần 2 — Báo cáo

Nhánh `dasktoon-model-import-fixes` (từ `dasktoon-master` d8414b3), làm tự động ngày 2026-10-19. **Chưa gộp, chưa đẩy.**
Thiết kế: `docs/superpowers/specs/2026-10-19-dasktoon-model-import-fixes-design.md`.

Mọi phép thử trên model thật đều làm trên bản sao (các file trong `D:\game` chỉ được đọc), hình chụp nhân vật không đưa
vào git.

## 1. Ba lỗi theo thiết kế

| Việc | Commit | Kết quả |
|---|---|---|
| Hướng nhân vật | b967df7 | Bốt to (pl1: 12,4% chiều cao) vẫn đọc được hướng. Nhân vật quay ngang mà bàn chân không cho biết thì bản Kiểm tra báo "Nhân vật đang quay ngang" với hai nút **Xoay trái 90°** / **Xoay phải 90°** (xoay, khớp khung, dựng lại, kiểm tra lại). |
| Dùng shader DaskToon | 4f1b974 | Menu ⌄ của ô vật liệu: **Dùng shader DaskToon** (vật liệu đang chọn) và **… cho mọi object đang chọn**. Anime BSDF có viền, lấy màu hoặc texture cũ, màu bóng và màu viền tính từ màu nền; node cũ giữ lại, chỉ tháo ra. RG2 thật: 5 vật liệu, giữ texture. |
| Hành động nhanh khi render | 355d041 | Nút **Ghi sẵn** / **Ghi lại** / **Xoá bản ghi** trong bảng Hành động nhanh, kèm dòng trạng thái (chưa ghi / đã ghi / bản ghi cũ vì đã sửa sau khi ghi). Render đọc bản ghi nên ra đúng mà không cần phát trước. |

## 2. Nhận diện rig phần 2 (váy, tóc dài)

Thử lại trên 7 model thật (RGforGame, RG2, pl1, Luna, tdt, lr_shape, filie) đã lộ ra các lỗi dưới đây. Mỗi lỗi có một
bài kiểm tra tạo bằng mã, đỏ trước khi sửa và xanh sau khi sửa.

| Commit | Lỗi trên model thật | Sửa |
|---|---|---|
| bc49a05 | RGforGame, RG2: tay đặt ngang tai (vai 2,30 m thay vì 1,52 m). Ba nguyên nhân: tai thỏ rộng hơn tay; bím tóc buông đè lên tay; bàn tay mảnh thò ra ống tay áo rộng, chỗ phình ở cổ tay áo bị tưởng là thân. RGforGame còn quay về +X mà đế giày nằm giữa ống chân. | Chi chĩa lên quá 35° là tai, tìm tay thấp hơn. Bỏ lưới nằm trọn trên bàn tay khi lần theo tay. Sau bàn tay mảnh, một đoạn giữ bề rộng đều và hẹp hơn 20% chiều cao là ống tay áo, chưa phải thân. Mũi giày dài hơn gót (1,5% chiều cao) cũng cho biết hướng. |
| 4f9ab6c | Hông nằm ở gấu váy (RGforGame, RG2: 0,48 m) hoặc giữa đùi ở gấu quần short (Luna, lr_shape). | Nếu chân của lưới thân đứng chạm sàn thì lấy chân từ lưới thân. Háng mới: 0,94 / 0,94 / 1,71 / 1,40 m, đều kiểm bằng hình lưới thân. tdt không đổi vì da của nó không có chân riêng. |
| ceee29d | Đuôi bím tóc liền một mảnh với tóc (RG2) bị tô vùng tay, nên giơ tay thì kéo theo tóc. | Mảnh nằm trọn trên vai, có không quá 20% đỉnh thuộc tay, thì giao cả cho đầu. |
| 8e1ebe0 | Váy liền áo, áo khoác dài, áo có vạt xòe làm chung một lưới: cả lưới không phải váy nên bản Kiểm tra im lặng, phần dưới eo bị đùi kéo nhàu khi ngồi. | Bản Kiểm tra báo "Phần dưới eo của X trông như váy" với nút **Đổi phần đó thành Váy**. Nút tạo nhóm đỉnh "X Skirt" (các đỉnh dưới eo), thêm thành phần Váy, dựng lại, kiểm tra lại. RG2, RGforGame và Luna: hết chỗ giãn khi ngồi. |
| 8f057e0 | filie: cổ chân lệch 23 cm ra trước, nằm trên mu bàn chân; hai lỗi "bàn chân nằm ngoài thân". | Độ sâu cổ chân đọc ở ống chân, cao hơn cổ chân 15% chiều dài chân. |

Số chỗ cần xem sau khi tự gắn khung:

| Model | Trước | Sau |
|---|---|---|
| tdt | 0 | 0 |
| lr_shape | 2 | 2 (vẫn là chỗ áo giãn khi giơ tay) |
| filie | 0 | 2 (giãn khi ngồi; hai lỗi bàn chân đã hết) |
| RG2 | 6 | 12, còn 9 sau khi bấm nút váy |
| RGforGame | 17 | 11, còn 9 sau khi bấm nút váy |

Với RG2 và RGforGame, con số tăng vì tay và hông giờ đã đúng chỗ, nên tư thế thử mới lộ ra các chỗ trước đây bị khung sai
che mất: ống tay áo kiểu kimono bị ép dẹt khi giơ tay, cổ nằm ngoài thân. Xem mục 4.

## 3. Quyết định tôi đã đưa ra (cần bạn xác nhận)

1. Nhân vật quay ngang mà không biết trái hay phải: chỉ báo kèm nút xoay, không đoán.
2. Shader: màu bóng và màu viền tính từ màu nền (nhân với một màu cố định).
3. Nút Dùng shader DaskToon nằm trong menu ⌄ của ô vật liệu (cạnh Gộp material), không nằm trong bảng Anime Rig.
4. Hành động nhanh: **không** tự phát qua các khung khi bấm render (có thể làm treo hoặc đổi cảnh ngoài ý muốn). Chỉ có
   nút Ghi sẵn và lời nhắc.
5. Các ngưỡng nhận diện: tai chĩa lên > 35°; ống tay áo giữ bề rộng trong ±50% và hẹp hơn 20% chiều cao; mũi giày dài
   hơn gót 1,5%; mảnh trên vai có ≤ 20% đỉnh thuộc tay thì thuộc đầu; cổ chân đọc ở ống chân, cao 15% chiều dài chân.
   Nếu sai, vài nhân vật lạ vẫn bị nhận nhầm, nhưng bản Kiểm tra sẽ báo.
6. Phần váy dưới eo: eo là đầu xương Spine. Bản Kiểm tra chỉ báo, không tự đổi. Váy có xương riêng giữ thẳng ở tư thế
   thử, nên khi ngồi đùi xuyên qua mặt trước váy (lò xo và va chạm chỉ chạy khi phát).

## 4. Chưa làm, hoặc làm chưa xong

- **Tóc dài**: không model nào của bạn có tóc dài (tóc đều trên vai), nên chưa có gì để thử. Bạn có model tóc dài nào không?
- **Cổ chibi**: RGforGame/RG2 báo "Cổ nằm ngoài thân". Cổ và đầu đang theo tỷ lệ khung mẫu (đầu xương Head ở 1,97 m,
  trong khi đáy đầu khoảng 1,68 m). Tôi đã thử cắt lệch khỏi giữa xương: RGforGame vẫn báo, còn ngực của tdt bị xê dịch
  2 cm, nên tôi bỏ. Nên làm việc này cùng phần 4 (đầu, mắt, miệng).
- **Ống tay áo rộng** (kimono) bị ép dẹt khi giơ tay. Đây là chuyện trọng số quần áo rộng, có từ trước.
- Mắt của chibi đầu to (RGforGame) đặt cao hơn mắt thật. Việc này thuộc phần 4.

## 5. Kiểm tra

Toàn bộ bộ thử của nhánh: 67 file, 674 bài, đều đạt (hai bài shading/upgrade đạt sau khi khôi phục dữ liệu thử mà bài
shading baseline ghi đè — chuyện đã biết). Bảy bài thử Unity đều đạt (sau khi xoá thư mục Library hỏng của dự án thử).

## 6. Nhận diện rig phần 3: ngón tay (commit 6ce8459)

Thiết kế: `docs/superpowers/specs/2026-10-19-dasktoon-rig-fingers-design.md`. Bàn tay của lưới Thân được trải lên mặt
phẳng lòng bàn tay. Năm điểm xa cổ tay nhất là đầu ngón; đi ngược từ mỗi đầu ngón tới chỗ phình ra là gốc ngón; ngón phía
trước là ngón cái. Ba đốt nằm trên đường từ gốc tới đầu ngón (45% / 75%), hai tay lấy trung bình đối xứng. Không thấy đủ
5 ngón thì giữ ngón của khung mẫu.

- Nhận được ngón: tdt, lr_shape, filie, RG2, Luna. pl1 giữ khung mẫu.
- Thử gập mỗi đốt 40° trên filie và lr_shape: lưới đi theo đúng từng ngón, không rách.
- Số chỗ cần xem của 6 model không đổi. Bài thử rig, xuất file và rig Unity đều đạt.
- Đã đăng ký thêm vào CMake 5 bài thử trước đây chưa có: check, regions, shoulder, fingers, material convert.

Quyết định cần bạn xác nhận: chỉ đọc lưới Thân (găng tay đi theo xương tìm được trên da); ngón cái là ngón phía trước
nhân vật, nên tay ngửa lòng bàn tay sẽ nhận sai; tỷ lệ đốt 45% / 30% / 25%; tìm không ra thì giữ khung mẫu và không báo.

## 7. Nhận diện rig phần 4: đầu, cổ, mắt

| Commit | Lỗi trên model thật | Sửa |
|---|---|---|
| f6faf70 | Khớp đầu theo tỷ lệ khung mẫu: nằm giữa cái đầu to của chibi (RG2, RGforGame), mắt lên tận trán, cổ ra trước cổ họng ("Cổ nằm ngoài thân"). | Từ vai trở lên, chỗ hẹp nhất của hình nhìn trước của lưới Thân là cổ, nếu phía trên (đầu) và phía dưới (vai) đều phình ra gấp 1,5 lần, và đầu rộng ít nhất 2,5 lần cổ. Chân cổ và đáy đầu thành hai mốc mới để kéo giãn khung mẫu, nên mắt, hàm và đỉnh đầu tự chia theo tỷ lệ trong cái đầu thật. Da không có thân (tdt) hoặc đầu dính vai thì giữ như cũ. |
| 0a45ece | Lưới hai con mắt ("mat" ở Luna và filie) bị coi là quần áo, hoặc gắn cứng vào xương đầu, nên không đảo mắt được. | "mat" (mắt) được nhận là phụ kiện mắt. Khớp mắt đặt vào tâm phụ kiện mắt hoặc mắt dẹt ở mỗi bên. Khi dựng, mỗi mảnh của phụ kiện mắt đi theo xương mắt cùng bên. Thử thật: cả hai mắt đảo theo điểm nhìn; mắt filie xoay quanh đúng tâm (lệch 1–2 mm). |

Kết quả đầu/cổ: hết "Cổ nằm ngoài thân" ở RG2 và RGforGame. Khi quay đầu, RG2 xoay quanh cổ thay vì quanh giữa đầu. filie
có thêm mục "Cylinder.002 trông như tóc"; mục này đúng, vì đó là các lọn tóc xoăn hai bên má (trước đây khớp đầu cao nên
không nhận ra).

Quyết định cần bạn xác nhận: các ngưỡng cổ (hẹp hơn 40% đầu, phình 1,5 lần, tìm trong 35% đầu tiên tính từ vai lên);
từ "mat" luôn hiểu là mắt (theo cách bạn đặt tên: toc, vay, ao, giay, tat); lông mi ("mi") vẫn là quần áo, đi theo đầu.
Miệng: đã có từ R3 (hàm, miệng 2D); khớp hàm giờ đi theo đầu mới, chưa làm gì thêm.

Kiểm tra sau phần 3–4: bộ thử đầy đủ 681 bài, đều đạt (shading/upgrade đạt sau khi khôi phục dữ liệu thử). Unity 7/7 đạt.

## 8. Trả lời của bạn về các quyết định (2026-10-19)

| Quyết định | Trả lời |
|---|---|
| Hành động nhanh khi render | **Đổi**: tự ghi sẵn khi bấm render |
| Chỗ đặt nút Dùng shader DaskToon | Giữ: menu ⌄ của ô vật liệu |
| Màu bóng của shader | Giữ: tối hơn, hơi lạnh |
| Nhân vật quay ngang, không rõ trái/phải | Giữ: chỉ báo, kèm nút xoay |
| Phần dưới eo trông như váy | **Đổi**: tự đổi thành Váy khi gắn khung |
| Không nhận được đủ 5 ngón | Giữ: ngón khung mẫu, không báo |
| Ngón cái | Giữ: ngón phía trước là ngón cái |
| Lưới tên "mat" | **Đổi**: chỉ là mắt khi nằm trên đầu |

## 9. Lượt làm tiếp theo (đêm 2026-10-19 → 20)

Làm thẳng trên nhánh chính, mỗi việc xong và chạy thử đạt thì đẩy lên GitHub.

| Commit | Việc |
|---|---|
| 848a708 | **Render tự ghi sẵn Hành động nhanh** (F12, Ctrl F12, menu Render). Bản ghi bị coi là cũ khi đổi cài đặt, đổi khoảng khung, hoặc **sửa hoạt cảnh sau khi ghi** (lưu "dấu vân tay" của các khoá và bảng nhịp). Render từ dòng lệnh vẫn cần bấm Ghi sẵn trước. |
| 2071454 | **Tự gắn khung tự đổi phần dưới eo giống váy thành Váy**. **"mat" chỉ là mắt khi nằm trên đầu** và gồm các mảnh nhỏ; viết có dấu "mặt" (khuôn mặt) thì không bao giờ là mắt. |
| 5929b74 | **Thử trong cửa sổ thật** (ảnh ở `import-fixes/vi`): mọi nút chạy đúng. Sửa chữ bị cắt: câu dài trong bản Kiểm tra tự xuống dòng, bảng Hành động nhanh rộng hơn. "object" → "đối tượng". |
| 8abe03b | **Váy xoè theo đùi khi ngồi** kể cả khi không phát: mỗi dải váy chép xoay của đùi cùng bên (trước 0,8, bên 0,45, sau 0,1), đặt trước ràng buộc lò xo. RG2, RGforGame, Luna ngồi: váy phủ lên đùi. |
| f65427d | **Thử trọn quy trình trên RG2** (tự gắn khung → Kiểm tra → Dùng shader DaskToon → clip Wave bằng Khoá tư thế, nhịp hai khung, Hành động nhanh → Render → Engine Export → Unity). Tìm và sửa 4 lỗi: xuất FBX hỏng khi đã ghi sẵn; Khoá tư thế khoá cả xương tóc/váy (Unity sẽ đung đưa hai lần) và xương phụ của vai; hoạt cảnh rác của bộ khung cũ thành clip "Clip" thừa; báo cáo xuất liệt kê Hành động nhanh như bộ sửa cần áp. Unity: khung người hợp lệ, clip Wave lặp 1 giây, nhịp hai khung. |

Việc "tay áo rộng bị dẹt": không cần sửa thêm. Tấm dẹt đó chính là đuôi bím tóc bị kéo theo tay, đã sửa ở ceee29d.

**Chưa xong, cần bạn quyết:** sửa C++ cho xương lò xo (lúc bắt đầu lại cũng đẩy ra khỏi chân) nằm ở nhánh
`dasktoon-spring-collide-on-reset`, chưa gộp. Lý do: máy không còn Visual Studio 2022, chỉ còn bản 18 (2026). Dựng
riêng một thư viện bằng bộ biên dịch mới rồi trộn với thư viện cũ thì DaskToon bị sập, nên tôi đã khôi phục bản cũ.
Muốn dựng thì phải cài lại Visual Studio 2022 Build Tools, hoặc dựng lại toàn bộ bằng Visual Studio 2026 (vài giờ).
Phần váy theo đùi ở trên đã giải quyết việc váy khi ngồi mà không cần dựng lại.

**Còn thấy, chưa làm:** RG2 có bộ làm mượt "Auto Smooth" trên từng lưới, không vào FBX (báo cáo xuất có ghi).

Kiểm tra cuối: bộ thử đầy đủ 694 bài đạt (shading/upgrade đạt sau khi khôi phục dữ liệu thử), Unity 7/7 đạt.
