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
