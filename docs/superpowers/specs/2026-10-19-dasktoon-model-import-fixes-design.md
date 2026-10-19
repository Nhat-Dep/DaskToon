# DaskToon: ba lỗi khi đưa model có sẵn vào — Thiết kế (bản nháp, chờ duyệt)

Khi dựng cảnh mô phỏng từ các model trong `D:\game` (Luna, RG2, filie, pl1, RGforGame, tdt, lr), ba chỗ làm người dùng
phải tự xử lý bằng tay hoặc bằng kịch bản. Người dùng chọn sửa cả ba (2026-10-19) và để duyệt thiết kế trước khi viết mã.
Mỗi mục ghi: chuyện gì xảy ra, đã đo được gì, cách sửa đề xuất, và câu hỏi cần người dùng trả lời.

## 1. Hướng nhân vật

### Chuyện gì xảy ra

Tự gắn khung (Thêm › Armature › Anime Humanoid khi đang chọn mesh) tự quay nhân vật về hướng trước (-Y) nhờ
`dasktoon_rig/facing.py`. Module này đọc **bàn chân**: bàn chân vươn ra trước cổ chân. Khi thử model:

| Model | Hướng gốc | Bàn chân cho biết | Kết quả |
|---|---|---|---|
| RG2 | -Y | -Y | đúng, không xoay |
| Luna | +Y | +Y | đúng, xoay 180° |
| filie | +Y | +Y | đúng *khi mesh còn nguyên*; quay sai khi modifier Mirror bị lệch tâm (lỗi do kịch bản thử của tôi, không phải DaskToon) |
| **pl1** | **ngang (±X)** | **không đọc được** | **không xoay, khung xương dựng ngang người** |

pl1 đi bốt to và mặc áo khoác dài. Hai chân của nó tách nhau theo trục Y (tức là nó quay ngang), nhưng `feet()` trả về
"không biết", nên không xoay gì. Người dùng nhận được bộ khung lệch 90°, tay chân gập sai chiều, mà không có cảnh báo.

### Cách sửa đề xuất

1. **Tìm vì sao `feet()` bỏ cuộc với pl1** (bốt to hay vạt áo chạm sàn bị tính là đế giày) và nới điều kiện, có bài kiểm
   tra với một hình bốt to và áo dài tạo bằng mã.
2. **Dấu hiệu dự phòng khi bàn chân không rõ**: hai cẳng chân tách nhau theo trục nào thì đó là trục trái–phải, nên hướng
   mặt vuông góc với trục ấy. Để biết trước hay sau trên trục đó, xét thêm theo thứ tự:
   - mũi giày dài hơn gót;
   - ngực và mặt nhô về phía trước hơn lưng ở cùng độ cao;
   - đầu gối hơi khuỵu ra trước (nếu có).
3. **Khi vẫn không chắc**: không xoay bừa. Bảng Kiểm tra hiện cảnh báo "Không biết nhân vật quay hướng nào" kèm các nút
   **Xoay 90° trái / 90° phải / 180°**. Bấm thì dựng lại khung đúng hướng.
4. Thông báo sau khi tự xoay (đã có) giữ nguyên: "Nhân vật không quay về phía trước (-Y): đã xoay N° tại chỗ".

### Câu hỏi cho người dùng

- Khi không chắc, nên **chỉ cảnh báo kèm nút xoay** (đề xuất), hay **đoán theo dấu hiệu tốt nhất rồi báo** để người dùng
  sửa nếu sai?

## 2. Nút chuyển vật liệu sang shader DaskToon (Anime BSDF)

### Chuyện gì xảy ra

Model mang vào thường dùng Principled, Emission, Diffuse, hoặc nhóm nút tự làm (5 model thử dùng nhóm "ND_toon"). Muốn có
viền và bóng kiểu hoạt hình của DaskToon thì phải tự nối lại từng vật liệu. Lúc dựng cảnh, tôi phải viết kịch bản chuyển
41 vật liệu.

### Cách sửa đề xuất

- Nút **Chuyển sang shader DaskToon**, đặt ở hai chỗ:
  - Thuộc tính Vật liệu: chỉ vật liệu đang chọn;
  - bảng Anime Rig: mọi vật liệu của nhân vật (mesh gắn vào khung).
- Với mỗi vật liệu:
  - tìm nguồn màu theo thứ tự: texture hoặc màu đang nối vào Màu nền (Principled), Màu (Emission, Diffuse), ô màu đầu
    tiên của nhóm nút; không có thì lấy texture ảnh đầu tiên; không có nữa thì xám;
  - thêm một nút Anime BSDF, bật viền, nối màu đó vào Màu nền;
  - Màu bóng = màu đó nhân (0,78; 0,72; 0,86) (tối và hơi lạnh);
  - Màu viền = màu đó nhân 0,3;
  - nối Anime BSDF vào đầu ra;
  - nối cả độ trong suốt nếu shader cũ có nối Alpha.
- Nút cũ **giữ lại, không xóa**, chỉ ngắt khỏi đầu ra, nên muốn quay lại chỉ cần nối lại.
- Vật liệu đã dùng Anime BSDF hoặc Dask Cel thì bỏ qua.
- Báo kết quả, ví dụ "Đã chuyển 41 vật liệu, bỏ qua 1".
- Dùng chung phần đọc màu đã có trong `dasktoon_material_combiner.py`, chuyển ra module riêng để không lặp code.

Ảnh thử từ kịch bản: `docs/superpowers/reports/real-model/jjk/cast2_anime.png` (chỉ có trên máy).

### Câu hỏi cho người dùng

- Màu bóng: **tự tính từ màu nền** (đề xuất), hay **một màu bóng chung** người dùng chọn cho cả nhân vật?

## 3. Hiệu ứng hành động nhanh khi render

### Chuyện gì xảy ra

Hiệu ứng hành động nhanh (nhòe, bóng mờ, vệt tốc độ) tính từ các khung trước đó và nhớ trong bộ nhớ khi phát lại trong
khung nhìn. Render một khung chưa được phát qua thì ra hiệu ứng cũ hoặc sai, **không có cảnh báo**. Khi dựng cảnh đánh
nhau, tôi phải tự cho phát qua từng đoạn trước khi render. Render từ dòng lệnh cũng bị như vậy.

### Cách sửa đề xuất

- Nút **Ghi sẵn hiệu ứng** (Bake) trong bảng Hành động nhanh:
  - tính hiệu ứng cho cả dải khung của cảnh và ghi ra đĩa cạnh tệp .blend, dùng cơ chế ghi sẵn có sẵn của Simulation Zone;
  - render và mở lại tệp đều đọc phần đã ghi, nên luôn đúng, kể cả render từ dòng lệnh;
  - khi sửa chuyển động sau đó, bảng báo "Hiệu ứng đã ghi sẵn có thể cũ" và có nút ghi lại.
- Khi bấm render mà chưa ghi sẵn và hiệu ứng chưa được tính cho các khung sẽ render, DaskToon **tự cho phát qua** các khung
  cần thiết trước khi render:
  - render một khung: 8 khung trước nó;
  - render cả đoạn: từ 8 khung trước khung đầu.

  Đồng thời báo trên thanh trạng thái để người dùng biết vì sao render chậm hơn một chút.

### Câu hỏi cho người dùng

- Có muốn **tự phát qua trước khi render** (đề xuất), hay **chỉ cảnh báo** để người dùng tự bấm Ghi sẵn?

## 4. Kiểm tra

- Mỗi mục có bài kiểm tra tự động, viết trước mã và phải thấy thất bại trước:
  - nhân vật tạo bằng mã quay ngang, đi bốt to;
  - các loại vật liệu: Principled có texture, Emission, nhóm nút, có trong suốt;
  - render một khung chưa phát qua phải ra đúng như sau khi phát.
- Chạy lại trên bản sao các model thật (pl1, filie, Luna, RG2, tdt, lr) và xem ảnh render.
- Chạy đủ bộ kiểm tra (74 tệp) trước khi báo xong.

## 5. Thứ tự làm

1, rồi 2, rồi 3, mỗi mục một nhánh riêng tách từ nhánh chính. Mục 1 làm trước vì khung xương sai hướng làm hỏng mọi bước
sau.
