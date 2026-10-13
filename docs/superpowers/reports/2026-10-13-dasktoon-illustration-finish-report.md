# DaskToon: bộ lọc hoàn thiện tranh (Illustration Finish), báo cáo

- Ngày: 2026-10-13. Người dùng hỏi về một compositor filter để lên màu và ánh sáng như một bức tranh 2D, rồi chọn:
  chỉ dùng trong DaskToon, kiểu tranh được họa sĩ hoàn thiện kỹ với đủ bốn nhóm (ánh sáng tranh, màu tranh, chiều sâu,
  nét và chất), không theo một họa sĩ mà người dùng tự chỉnh, ưu tiên chất lượng, duyệt spec trước. Sau khi đọc spec,
  người dùng nói "tự động".
- Nhánh: `dasktoon-illustration-finish`, tách từ `dasktoon-master` (`fe739401377`). Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-13-dasktoon-illustration-finish-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-13-dasktoon-illustration-finish.md`.

## 1. Đã làm được gì

| Phần | Nội dung |
|---|---|
| Bộ lọc | Nhóm node compositor "DaskToon Illustration Finish" với 12 lớp xếp như layer của họa sĩ: màu vùng tối và vùng sáng, nét cọ (Kuwahara), không khí theo khoảng cách, hậu cảnh mềm, glow mềm (bloom), tia sáng từ mặt trời, viền sáng ngược sáng, gradient ánh sáng, bão hòa và tương phản, vignette, quang sai màu, vân giấy; cuối cùng là **Độ mạnh chung** |
| Cách làm | Mọi lớp làm trên **màu như mắt thấy** (sRGB trong khoảng 0 đến 1), như họa sĩ làm trên màn hình; ảnh được đổi sang sRGB ở đầu nhóm và đổi về ở cuối. Lớp nào tắt thì không có node trong nhóm, nên không tốn gì; kéo thanh chỉnh chỉ đổi đầu vào, không dựng lại |
| Mặt trời và lấy nét | Tia sáng tỏa từ chỗ Sun của scene nằm trên ảnh (tắt khi Sun ở sau camera); gradient ánh sáng đi từ phía Sun; hậu cảnh mềm lấy nét theo camera, nếu không thì vào object đang chọn. Tự cập nhật khi Sun, camera, lựa chọn hay khung đổi |
| Style | 5 style có sẵn làm điểm xuất phát: Mặc định, Nắng sớm, Hoàng hôn, Đêm, Màu nước. Style của bạn lưu thành file JSON trong thư mục cấu hình, dùng ở mọi file, giống Shading Styles |
| Giao diện | Panel **Hoàn thiện tranh** trong **Properties › Scene** (DaskToon Anime và EEVEE): công tắc, style, độ mạnh chung, hiện trong viewport (tắt, camera view, luôn), nút **Nét màu cho mọi material** (đặt Auto Harmonic cho mọi material có outline), bốn nhóm lớp. Bản tiếng Việt đầy đủ |
| Compositor của scene | Scene chưa có compositor thì DaskToon tạo "DaskToon Compositor"; compositor bạn tự làm thì không bị động vào, chỉ chèn khi bấm **Thêm vào compositor**; tắt bộ lọc thì node bị mute, không bị xóa. Pass Depth được bật tự động |

Cách dùng:

1. Properties › tab **Scene**, bật **Hoàn thiện tranh**.
2. Chọn một style, rồi chỉnh từng lớp trong bốn nhóm. Camera view (chế độ Rendered) hiện kết quả ngay.
3. Muốn nét viền ăn màu theo vật liệu: bấm **Nét màu cho mọi material**.
4. Ưng thì bấm **+** để lưu thành style của bạn.

## 2. Kiểm thử

- `dasktoon_finish_test.py` (22 test):
  - nhóm node: đầu vào theo bảng thiết lập; chỉ có lớp đang bật; không dựng lại khi lớp không đổi; dựng được khi giao
    diện tiếng Việt;
  - compositor của scene: tạo khi chưa có, để nguyên của người dùng, chèn trước đầu ra, mute khi tắt, pass Depth;
  - thiết lập: ghi vào node, bật/tắt lớp dựng lại nhóm, chế độ viewport, thêm vào compositor của người dùng, nét màu cho
    Anime Character và Dask Cel, các panel;
  - mặt trời: Sun trước và sau camera, hướng ánh sáng, lấy nét theo camera và object, handler chỉ ghi khi giá trị đổi;
  - style: style có sẵn, áp dụng, lưu, ghi đè, xóa, file cũ thiếu thiết lập, tên lạ.
- `dasktoon_finish_render_test.py` (8 test, render EEVEE thật): mỗi lớp bật riêng đổi ảnh đúng hướng (khối xa nhòa vào
  không khí hơn khối gần, quả cầu sáng có glow, góc tối, phía trên ấm hơn khi ánh sáng từ trên, vùng tối ngả màu bóng,
  nét cọ và hậu cảnh mềm đổi ảnh, chỗ lấy nét giữ nguyên); không lớp nào bật thì như ảnh gốc khi hiển thị; Độ mạnh
  chung = 0 thì đúng ảnh gốc.
- Toàn bộ suite CMake: 54 file (521 test) đều qua. Lần chạy đầu bắt được panel nằm ở tab Render, trái luật giao diện; đã
  chuyển sang tab Scene (mục 4.8).
- Tốc độ: camera view 559×554 trong tab Animation vẽ lại mất khoảng 6 đến 9 ms khi bật bộ lọc (khoảng 1 ms khi tắt),
  tức vẫn trên 100 khung mỗi giây.

## 3. Ảnh chụp

`docs/superpowers/reports/illustration-finish/en|vi/`:

- `40_finish_panel.png`: panel trong Properties › Scene, nhóm Màu tranh đang mở.
- `41_finish_before_after.png`: cùng một cảnh, trái là ảnh render gốc, phải là style Mặc định.
- `42_finish_camera_view.png`: camera view trong tab Animation hiện bộ lọc trực tiếp.
- `43_finish_styles.png`: ảnh gốc và 5 style.

Cảnh mẫu là nhân vật thử của rig (thân hình trụ, không có tay) với material toon, nên ảnh cho thấy cách bộ lọc tác động
chứ chưa phải một bức tranh đẹp; trên nhân vật thật hiệu ứng sẽ rõ hơn.

## 4. Quyết định Claude tự chốt (cần xem lại)

1. **Kết hợp material và compositor**: viền sáng (Rim), màu bóng và nét Harmonic để trong material toon (đã có, dùng
   lại); 12 lớp phủ làm trong compositor; không viết C++.
2. **Làm trên màu như mắt thấy** (sRGB 0 đến 1). Compositor làm việc với giá trị tuyến tính; Soft Light, Screen và tương
   phản quanh xám giữa vốn dành cho màu như mắt thấy, nên tính trên giá trị tuyến tính thì vùng tối bị nát và điểm sáng
   HDR thành màu xanh. Vì view transform của DaskToon là Standard, phần trên 1 vốn không hiện.
3. Sau khi render nhân vật trong một cảnh sáng, ảnh bị **mờ sữa** vì lớp nào cũng làm sáng thêm. Nên:
   - màu vùng sáng chỉ đổi sắc chứ không làm sáng;
   - glow chỉ lan phần sáng vượt ngưỡng (mặc định 0,8);
   - tia sáng chỉ phát từ chỗ rất sáng;
   - **bão hòa và tương phản đặt sau các lớp ánh sáng** (như layer chỉnh màu trên cùng), khác thứ tự ghi trong spec;
   - không khí bắt đầu từ 10 m, vignette mềm hơn.
4. Tương phản tính bằng phép trộn về xám giữa, không dùng node Brightness/Contrast: trên GPU node này làm một màu tối
   thành đen ở Contrast 8.
5. Bật/tắt lớp thì dựng lại nhóm node (lớp tắt không tốn gì); nhóm do DaskToon quản lý, chỉnh tay trong nhóm sẽ mất khi
   dựng lại.
6. Năm style và giá trị của chúng. Style **Đêm** chỉ là cách lên màu: cảnh ban ngày không thành ban đêm.
7. Màu không khí mặc định là một màu xanh nhạt cố định, không lấy từ màu world như spec viết (màu world có thể là cả một
   cây node).
8. **Panel nằm trong tab Scene, không phải tab Render như spec viết**: luật giao diện đã duyệt (spec sắp xếp lại giao
   diện, mục 3) giữ tab Render không có panel DaskToon, và test giao diện kiểm luật đó; bộ lọc là dữ liệu của scene nên
   ở tab Scene. Nhóm Màu tranh mở sẵn, ba nhóm kia đóng. Nhãn riêng ("Độ mạnh chung", "Màu vùng
   tối", "Màu vùng sáng", "Chiều sâu tranh") thay cho chữ chung của Blender, vì bản dịch chung của Blender sai nghĩa ở
   đây.

## 5. Giới hạn

- Viền sáng ngược sáng lấy mép theo độ sâu, nên chỉ gần đúng; Rim trong material vẫn là viền sáng chính.
- Hậu cảnh mềm là làm mờ theo khoảng cách, không phải bokeh ống kính.
- Bộ lọc chỉ có trong DaskToon (viewport và render), không sang Unity.

Khi làm (ledger):

- Lần render đầu, quả cầu phát sáng thành màu xanh và vùng tối thành đen: hai lỗi do làm trên giá trị tuyến tính và do
  node Brightness/Contrast; đã sửa như mục 4.2 và 4.4.
- Test bản dịch không bắt được chuỗi trong bảng thiết lập (truyền qua biến), nên nhãn và mô tả trong bảng được đánh
  dấu `n_()` và file được đưa vào danh sách kiểm tra.
