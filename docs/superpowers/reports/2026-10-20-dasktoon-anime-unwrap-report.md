# Báo cáo: Trải UV anime (2026-10-20)

Bạn hỏi "có thể tối ưu khả năng trải UV?". Bạn chọn bốn mục tiêu:

- dễ tô vẽ: mỗi bộ phận một mảng, đường cắt ở chỗ khuất, ít méo;
- nét hơn ở chỗ quan trọng;
- đối xứng tiết kiệm chỗ cho tay, chân, giày (mặt, thân, tóc, áo giữ nguyên);
- UV kín hơn cho game.

Model đã tô thì chuyển ảnh sang UV mới và giữ UV cũ. Bạn duyệt thiết kế rồi giao tự động. Thiết kế:
`docs/superpowers/specs/2026-10-20-dasktoon-anime-unwrap-design.md`.

## Đã làm

Nút **Trải UV anime** nằm ở menu UV của chế độ biên soạn (phím U) và ở menu ô vật liệu. Bắt đầu tô vẽ và nút Sửa của
mục UV trong Kiểm tra model cũng dùng nó, thay cho Phóng Chiếu UV Thông Minh. Khi bấm, DaskToon làm bảy bước:

1. **Tìm bộ phận.** Lưới có khung DaskToon thì lấy đầu, thân, hai tay, hai chân từ vùng cơ thể của khung. Mảnh rời (tóc,
   mảnh mắt, quần áo riêng) là bộ phận riêng.
2. **Cắt ở chỗ khuất:**
   - giữa các bộ phận (cổ, vai, hông);
   - đầu cắt một đường dọc sau gáy, nên **mặt liền một mảng**;
   - thân cắt giữa lưng;
   - tay cắt mặt dưới, chân cắt mặt trong;
   - lọn tóc và quần áo cắt phía sau.
   Đường cắt đi theo cạnh, càng lộ ra trước càng tránh.
3. **Trải ít méo**, bằng cách "Ít kéo dãn nhất" của Blender. Mảng nào cách đó trải hỏng thì trải lại bằng cách thường.
4. **Mặt nét hơn:** sau khi cân đều độ nét, các mảng của đầu (cả mảnh mắt) to gấp 1,5 lần.
5. **Đối xứng:** tay, chân bên phải (cả giày, ống tay nằm trong vùng tay chân) chồng khít lên bên trái khi lưới đối xứng
   đúng. Phần nào không đối xứng thì để riêng.
6. **Xếp kín:** mỗi vật liệu một ảnh, khe giữa các mảng khoảng 8 điểm ảnh. Nút Trải UV anime mặc định **Xếp thật kín**
   (theo đúng hình từng mảng, chậm); Bắt đầu tô vẽ và nút Sửa xếp theo hình chữ nhật bao (nhanh).
7. **Giữ hình đã vẽ:** UV cũ đổi tên thành "<tên> Old". Mọi ảnh của vật liệu (cả các lớp vẽ) được chuyển từng điểm ảnh
   sang UV mới, giữ cả phần trong suốt, tràn mép 4 điểm ảnh.

Ảnh chụp trong cửa sổ thật (tiếng Việt, nhân vật thử, `tools/dasktoon_uv_screenshots.py`):

- `anime-unwrap/vi/120_uv_menu.png`: menu UV với **Trải UV anime**;
- `anime-unwrap/vi/121_anime_unwrap.png`: sau khi trải, khung UV bên trái, khung nhìn 3D bên phải.

## Thử trên model thật

Chạy trên bản sao 7 nhân vật của bạn (không lưu đè). Không model nào lỗi. Kết quả với Xếp thật kín:

| Model | Lưới | Mặt lưới | Thời gian | Số mảng | Mặt đối xứng | Phần ảnh được dùng |
|---|---|---|---|---|---|---|
| filie | 12 | 7 416 | 68 s | 77 | 1 199 | 97% |
| lr | 8 | 18 592 | 63 s | 105 | 3 395 | 96% |
| luna | 11 | 30 605 | 78 s | 82 | 944 | 78% |
| pl1 | 4 | 6 073 | 24 s | 43 | 0 | 89% |
| rg2 | 5 | 23 476 | 51 s | 44 | 3 139 | 92% |
| rgg | 5 | 12 080 | 50 s | 43 | 0 | 92% |
| tdt | 2 | 19 291 | 36 s | 96 | 3 038 | 78% |

- Phần ảnh được dùng ở bảng tính chung mọi vật liệu trên một ô, nên chỉ là ước lượng.
- Gần hết thời gian là bước xếp theo đúng hình mảng. Xếp theo hình chữ nhật bao chỉ mất 4 s (pl1) và 11 s (tdt), nhưng
  kém kín hơn: 86% thay vì 89%, 71% thay vì 78%.
- Xếp theo hình bao lồi lại còn chậm hơn (125 s trên pl1), nên không dùng.
- pl1 và rgg không có mặt đối xứng: tay chân hai bên của chúng không trùng nhau đúng từng điểm.
- Ở model mà mặt và thân dùng chung một ảnh (pl1, luna), mặt nét gấp 1,4 đến 1,5 lần thân. Ở model mà mặt có vật liệu
  riêng, hai ảnh xếp riêng, nên phép so này không có nghĩa.

## Kiểm tra

- `dasktoon_uv_unwrap_test` (10 bài). Trên nhân vật thử có khung:
  - mọi mặt nằm trong ô; không mảng nào chồng nhau, trừ tay chân phải nằm khít trên trái;
  - đường cắt của đầu nằm phía sau;
  - mặt nét hơn thân 1,3 lần trở lên;
  - ảnh được dùng trên 45%.
- Không có khung: các mảnh rời tách đúng.
- Nút giữ UV cũ, và chạy được từ chế độ biên soạn.
- Chuyển ảnh trên mặt cầu: màu tại các điểm gần như giữ nguyên (sai lệch giữa dưới 0,03); các lớp chuyển theo.
- Phép thử cũ của Bắt đầu tô vẽ và Kiểm tra model vẫn qua với cách trải mới.

## Lỗi bắt được trong cửa sổ thật

Bấm Trải UV anime từ menu UV của chế độ biên soạn, đúng chỗ đặt nút, thì báo lỗi. Lý do: Blender không cho tạo bản đồ
UV mới khi lưới đang biên soạn. Chạy nền không thấy lỗi này. Đã sửa (ra khỏi chế độ biên soạn trước khi làm, xong thì
quay lại) và thêm phép thử.

## Quyết định tôi tự đưa ra

1. Chưa gắn khung thì chỉ chia theo mảnh rời, chưa tự ước lượng bộ xương ngầm như đã nói lúc trao đổi: việc đó phải
   chạy cả bộ tự gắn khung trên bản sao. Cái giá: lưới liền một khối chưa gắn khung chỉ được cắt một đường dọc, tay chân
   chưa thành mảng riêng.
2. Phía khuất tính theo hướng đứng chuẩn của nhân vật (quay ra −Y), đúng điều Kiểm tra model đòi hỏi. Phía của mỗi điểm
   tính theo vị trí quanh trục bộ phận, không theo hướng mặt lưới (lưới người mới có thể quay mặt ngược).
3. Mặt gấp 1,5 lần. Chưa thu nhỏ lòng bàn chân, vì nó chưa thành mảng riêng.
4. Khe 8 điểm ảnh, nét tràn khi tô vẽ (Bleed) 4 điểm ảnh (Bắt đầu tô vẽ đặt sẵn).
5. Nút Trải UV anime mặc định xếp thật kín (chậm, tới cả phút); Bắt đầu tô vẽ và nút Sửa xếp nhanh. Cái giá: hai cách
   cho ảnh kín khác nhau vài phần trăm.
6. Đường cắt mới thay mọi đường cắt cũ của lưới.
7. Chỗ tay chân phải chồng lên trái, khi chuyển ảnh cũ, hình bên trái được giữ.

## Còn lại

- Ước lượng bộ xương ngầm cho lưới chưa gắn khung.
- Thu nhỏ lòng bàn chân, trong miệng (cần tách chúng thành mảng riêng).
- Kiểm tra model chưa có mục "UV chồng nhau" (mục còn treo từ phần tô vẽ). Nay phải tính cả chỗ chồng có chủ ý của tay
  chân đối xứng.
- Bước xếp thật kín chậm trên model lớn: có thể chạy ngầm kèm thanh tiến độ.
