# Báo cáo: Bộ ảnh kiểu game Tóc, Thân, Mặt (phần 1) (2026-10-20)

Bạn hỏi UV đã tối ưu cho texture chưa, rồi nói rõ: muốn đầu ra texture và UV khi xuất giống model của các game lớn,
"kiểu Wuwa với Zzz". Tôi chia việc thành bốn phần; bạn chọn làm phần 1 trước: **bộ ảnh theo bộ phận và UV kiểu game**.
Thiết kế: `docs/superpowers/specs/2026-10-20-dasktoon-game-texture-sets-design.md`.

## Đã làm

Nút **Trải UV anime** có thêm lựa chọn **Ảnh**:

- **Theo bộ phận (kiểu game)**, mặc định;
- **Theo vật liệu**, như trước.

Cần nhân vật có khung DaskToon; không có khung thì nút tự trải theo vật liệu và báo cho bạn biết.

**Ba bộ ảnh:**

- **Tóc:** phần Tóc của khung, và mọi mảnh khác trên đầu (chỏm tóc, lọn tóc, tai thỏ, nơ, kẹp).
- **Mặt:** da đầu (mảnh nối xuống cổ hoặc chứa cằm) và các mảnh nhỏ trước mặt (mắt, lông mày, miệng).
- **Thân:** mọi thứ còn lại.

Một vật liệu dùng ở nhiều bộ được sao chép thành "<tên> Face", "<tên> Hair"…, vì mỗi vật liệu chỉ đọc được một ảnh.

**UV kiểu game:**

- Mỗi bộ một ô UV.
- Xếp hai lượt: các mảng lớn (mặt, thân, tay chân) đứng thẳng và giữ chỗ; các mảng nhỏ xếp vào khe, được xoay 90°.
- Tay chân, giày bên phải vẫn chồng lên bên trái.
- Tóc và Thân cùng độ nét; Mặt nét gấp đôi. Cỡ ảnh là luỹ thừa của 2 (256–2048), theo diện tích từng bộ.
- Khe giữa các mảng 8 điểm ảnh theo đúng cỡ ảnh.

**Ảnh màu chung:** mỗi bộ một ảnh `<khung> Hair/Body/Face Color`. Màu nền của từng vật liệu được vẽ vào đúng chỗ (ảnh
thì chuyển từng điểm ảnh, màu phẳng thì tô phẳng), và ô Màu nền của mọi vật liệu trong bộ đọc ảnh chung này.

## Thử trên model thật

Bản sao 7 nhân vật, lấy mọi lưới đang hiện, sau khi đổi mọi vật liệu sang shader anime như bước 6 của Hướng dẫn.

Mỗi vật liệu được tô một ảnh thử trên UV cũ. Ảnh chụp "trước" và "sau" qua shader thật (EEVEE): nếu ảnh màu chung đúng
thì hai ảnh trùng nhau. Ảnh chỉ để trong máy, ở `docs/superpowers/reports/real-model/game-sets/` (ngoài git):

- `<model>_tight_1_before_after.png`: trước và sau;
- `<model>_tight_2_<bộ>.png`: ba ảnh màu chung;
- `<model>_tight_3_checker_front_back.png`: ô bàn cờ.

Kết quả, xếp thật kín:

| Model | Thời gian | Cỡ ảnh Tóc / Thân / Mặt | Phần ô được dùng Tóc / Thân / Mặt | Điểm ảnh khác đi sau khi chuyển |
|---|---|---|---|---|
| tdt | 76 s | 2048 / 2048 / 2048 | 56% / 60% / 55% | 3,1% |
| filie | 45 s | 2048 / 2048 / 2048 | 25% / 56% / 62% | 1,0% |
| lr | 72 s | 2048 / 2048 / 2048 | 56% / 65% / 76% | 1,8% |
| luna | 135 s | 1024 / 2048 / 2048 | 48% / 54% / 66% | 1,9% |
| pl1 | 39 s | 256 / 2048 / 2048 | 21% / 63% / 54% | 3,8% |
| rg2 | 78 s | 1024 / 2048 / 2048 | 54% / 65% / 68% | 8,1% |
| rgg | 77 s | 512 / 2048 / 2048 | 49% / 59% / 64% | 5,5% |

**Lỗi đã sửa trong lúc thử (có phép thử):**

1. Tóc nằm chung lưới với cơ thể bị tính vào bộ Mặt (tdt). Nay vùng đầu được chia theo từng mảnh rời.
2. Một vật liệu dùng cho lưới thuộc hai bộ đọc nhầm ảnh của bộ kia (luna: áo và kẹp tóc chung một vật liệu). Nay vật
   liệu được tách trên cả nhân vật, không chỉ trong từng lưới.
3. Lọn tóc hình ống có nắp gập nắp lên chính nó. Nay khối kín được cắt thêm ở các cạnh gập gắt.
4. Ảnh rất phí chỗ khi mọi mảng đều không được xoay. Nay xếp hai lượt: Mặt của tdt từ 34% lên 55%, Thân của filie từ 50%
   lên 56%.

5. **Ảnh tô nằm trong tệp riêng mà Blender chưa nạp** bị coi như không có ảnh. tdt có ảnh tô thật cho da và quần áo,
   nhưng ảnh màu chung chỉ lấy màu mặc định (toàn màu da), và cả Trải UV anime theo vật liệu (đã đẩy lên trước đó) cũng
   không chuyển ảnh đó sang UV mới. Nay ảnh được tự nạp khi cần. Lỗi này lộ ra khi bạn hỏi vì sao ảnh "cầu vồng": màu cầu
   vồng là ảnh thử tôi tô lên để kiểm tra việc chuyển hình, và nó che mất việc ảnh thật bị bỏ qua. Ảnh màu thật của tdt sau
   khi sửa: `real-model/game-sets/tdt_real_colours_body.png`, `_face.png`, `_hair.png` (trong máy).

Ảnh chụp đầu tiên bằng Workbench trông như ảnh màu chung bị xáo trộn. Đó là do Workbench hiện nhầm một ảnh khác trong vật
liệu; chụp qua shader thật thì khớp. Phép so từng mặt lưới cũng cho thấy ảnh màu chung đúng ở 92–100% các mặt.

## Chưa đạt mức game lớn

- **Độ kín:** model game thường dùng 70–85% ô; ở đây Thân 54–65%, Mặt 54–76%, Tóc 21–56%. Tóc là chỗ yếu nhất khi có
  nhiều sợi mảnh, cong, phân nhánh (filie 25%, pl1 21%). Cách các game làm là **trải thẳng từng lọn tóc thành dải**.
- **Vài mặt lưới bị co dẹt** trên UV mới nên không lấy được màu (ngực áo của rg2: mảng đen). Đây là chỗ khác đi nhiều
  nhất của rg2 (8%).
- **Chậm:** 40 đến 135 giây mỗi nhân vật, chủ yếu ở bước xếp thật kín.
- **Phần đầu phía sau** của một số model (rg2) vẫn thành mảng lớn, méo, nằm cạnh mặt trong bộ Mặt.

## Kiểm tra

- `dasktoon_uv_sets_test` (10 bài), trên nhân vật thử có khung, thêm lọn tóc và vật liệu riêng màu:
  - mặt lưới vào đúng bộ;
  - mỗi bộ trong ô, không chồng nhau;
  - mảng đứng thẳng;
  - mặt nét gấp đôi;
  - cỡ ảnh là luỹ thừa của 2;
  - ảnh màu chung đúng màu, Màu nền đọc ảnh chung;
  - mặt tách vật liệu;
  - vật liệu dùng chung giữa hai bộ được tách;
  - tóc trong lưới cơ thể vào bộ Tóc, mảnh mắt vào bộ Mặt.
- `dasktoon_uv_unwrap_test` (16 bài) vẫn qua, thêm bài lọn tóc kín có nắp.
