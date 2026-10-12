# DaskToon: bộ lọc hoàn thiện tranh (Illustration Finish)

- Ngày: 2026-10-13. Người dùng chọn (2026-10-13):
  - bộ lọc chỉ dùng **trong DaskToon** (viewport và render), không cho Unity;
  - kiểu **tranh được họa sĩ hoàn thiện kỹ**, đủ bốn nhóm: **ánh sáng tranh, màu tranh, chiều sâu, nét và chất**;
  - không theo một họa sĩ, **người dùng tự chỉnh**;
  - **ưu tiên chất lượng hoàn thiện tốt nhất**;
  - **duyệt spec trước** khi lập kế hoạch và code.

  Phần còn lại Claude tự chốt, ghi ở §12 để người dùng xem lại.
- Lộ trình: R, A, B, C đã merge; spec này là một tính năng mới chen trước R3 (mắt, miệng).

## 1. Mục tiêu

1. Bật một công tắc là ảnh của DaskToon (camera view lúc làm việc, render ảnh và video) có **lớp hoàn thiện như một
   bức illustration**:
   - ánh sáng mềm và có hơi thở;
   - màu có chủ ý: vùng tối ngả màu, vùng sáng ấm;
   - cảnh có chiều sâu không khí;
   - bề mặt có chất tranh.
2. Mỗi lớp hoàn thiện bật, tắt và chỉnh riêng được. Có sẵn vài **style** làm điểm xuất phát; người dùng **lưu style của
   mình** và dùng lại ở file khác.
3. Thấy kết quả **ngay trong camera view** (chế độ Rendered), không phải đợi render.

## 2. Phạm vi

| Có | Không (để sau hoặc không làm) |
|---|---|
| Nhóm node compositor "DaskToon Illustration Finish" với 12 lớp (§4) | Hiệu ứng tương tự trong Unity |
| Thiết lập lưu trong scene, panel trong Render Properties | Vẽ tay, tô thêm lên ảnh |
| Style có sẵn và style của người dùng (file JSON) | Nạp LUT `.cube` |
| Xem trực tiếp trong camera view | Hiệu ứng riêng cho từng object (trừ chiều sâu theo pass Depth) |
| Nút đặt nét màu Harmonic cho mọi material có outline | Nhiều view layer, tách lớp nhân vật và cảnh nền |

## 3. Cách làm: kết hợp material và compositor

Chất lượng tốt nhất có được khi mỗi việc làm ở đúng chỗ của nó:

- **Trong material toon (đã có, chỉ dùng lại):** những thứ cần biết chính xác đèn và hình 3D.
  - **Rim** (viền sáng theo hướng đèn): module Rim của Anime Character, Anime BSDF, Anime Cel.
  - **Shadow Color** (màu vùng bóng của từng vật liệu).
  - **Nét màu** (Outline Mode **Harmonic**: nét lấy màu theo Base Color, không đen đặc).

  Tính trong shader thì đúng theo từng đèn, có bóng đổ và không răng cưa. Làm lại trong compositor từ pass Normal chỉ là
  ước lượng, kém hơn.
- **Trong compositor (mới):** các lớp phủ lên cả bức tranh, giống layer họa sĩ thêm trong Clip Studio hay Photoshop sau
  khi tô màu. Compositor của Blender 5.2 chạy trên GPU với số thực đầy đủ, cả khi render lẫn trong viewport (đã kiểm:
  EEVEE đưa mọi pass, kể cả Depth, cho compositor của viewport).

Không viết hậu kỳ bằng C++: nó chỉ nhanh hơn chứ không đẹp hơn các node có sẵn, mà tốn nhiều công và xa code gốc.

## 4. Các lớp hoàn thiện

Xử lý theo thứ tự dưới đây, như chồng layer từ dưới lên. Mỗi lớp có công tắc riêng và một **Độ mạnh**. Kích thước tính
theo phần trăm chiều cao ảnh, nên camera view nhỏ và bản render lớn trông giống nhau.

| # | Lớp | Nhóm | Làm gì | Thiết lập chính | Node chính |
|---|---|---|---|---|---|
| 1 | Màu bóng, màu sáng | Màu tranh | Vùng tối ngả về một màu (mặc định tím lam nhạt), vùng sáng ngả về màu nắng (vàng ấm), giữ trung tính ở giữa | Màu bóng, Màu sáng, Độ mạnh | Color Balance (Lift, Gain) |
| 2 | Bão hòa, tương phản | Màu tranh | Màu tươi và rõ khối hơn | Độ bão hòa, Tương phản | Hue/Saturation, Bright/Contrast |
| 3 | Nét cọ | Nét và chất | Gom chi tiết nhỏ thành mảng màu theo hướng nét, như tô bằng cọ | Kích thước cọ, Độ sắc, Độ mạnh | Kuwahara (Anisotropic) |
| 4 | Không khí | Chiều sâu | Vật càng xa càng nhòa về màu không khí (mặc định lấy từ màu world) | Bắt đầu, Kết thúc (m), Màu, Độ mạnh, Bầu trời (mức nhòa của nền trời) | pass Depth, Mix |
| 5 | Hậu cảnh mềm | Chiều sâu | Phần xa hơn khoảng lấy nét được làm mềm, nhân vật nổi lên | Khoảng lấy nét (mặc định: camera tới nhân vật đang chọn, hoặc lấy nét của camera), Độ mềm, Chuyển tiếp | pass Depth, Blur, Mix |
| 6 | Glow mềm | Ánh sáng tranh | Một bản mờ của tranh phủ kiểu Screen lên chính nó: ánh sáng lan nhẹ, màu dịu như phim anime chiếu rạp | Ngưỡng (từ cả tranh tới chỉ vùng sáng), Độ lan, Độ mạnh | Glare (Bloom), Blur, Mix Screen |
| 7 | Tia sáng | Ánh sáng tranh | Tia sáng tỏa từ vị trí mặt trời trên ảnh | Độ dài, Độ mạnh; tự tắt khi mặt trời ở sau camera | Glare (Sun Beams) |
| 8 | Viền sáng ngược sáng | Ánh sáng tranh | Ánh sáng của nền lấn nhẹ qua mép hình nhân vật (light wrap), bổ sung cho Rim trong material | Độ rộng, Độ mạnh | pass Depth (mép theo độ sâu), Blur, Mix |
| 9 | Gradient ánh sáng | Màu tranh | Phủ một dải màu từ phía nguồn sáng (ấm) sang phía đối diện (lạnh) kiểu Soft Light | Màu phía sáng, Màu phía tối, Góc (mặc định theo mặt trời), Độ mạnh | Image Coordinates, Color Ramp, Mix Soft Light |
| 10 | Vignette | Chiều sâu | Tối hoặc ngả màu nhẹ ở góc ảnh, dẫn mắt vào giữa | Kích thước, Độ mềm, Màu, Độ mạnh | Ellipse Mask, Blur, Mix |
| 11 | Quang sai màu | Nét và chất | Tách màu rất nhẹ ở rìa ảnh như ống kính | Độ mạnh | Lens Distortion (Dispersion) |
| 12 | Vân giấy | Nét và chất | Hạt và vân giấy rất nhẹ (tạo bằng noise, không cần file ảnh); tùy chọn đổi theo khung | Tỉ lệ, Độ mạnh, Đổi theo khung | Noise Texture, Mix Soft Light |

- Cuối cùng là **Tổng** (0 tới 1): trộn ảnh đã hoàn thiện với ảnh gốc, để giảm hoặc tăng cả bộ lọc bằng một thanh.
- **Mặt trời** (lớp 7, 9): lấy Sun của scene, giống phần đồng bộ mặt trời đã có (`dasktoon_sun_sync`). Hướng của nó được
  chiếu lên ảnh qua camera, rồi ghi vào đầu vào của nhóm node mỗi khi đèn, camera hay khung đổi. Scene không có Sun thì
  tia sáng tắt, gradient dùng góc chỉnh tay.
- **Nét màu**: panel có nút "Nét màu cho mọi material". Nút này đặt Outline Mode = Harmonic cho mọi material có outline
  trong file, có Undo. Bộ lọc không tự đổi material.

## 5. Style

- Thiết lập của bộ lọc nằm trong scene (`Scene.dasktoon_finish`), nên được lưu cùng file `.blend`.
- **Style có sẵn** (điểm xuất phát; chọn style thì đặt mọi thiết lập):
  - **Mặc định**: cân bằng, mọi lớp nhẹ;
  - **Nắng sớm**: ấm, glow mềm, không khí sáng;
  - **Hoàng hôn**: cam và tím, tia sáng rõ, gradient mạnh;
  - **Đêm**: lam, glow quanh vùng sáng, vignette;
  - **Màu nước**: nét cọ, vân giấy, tương phản thấp.
- **Style của người dùng**: Lưu, Xóa, Ghi đè, giống Shading Styles. Mỗi style là một file JSON trong thư mục cấu hình
  `dasktoon/finish_styles`; biến môi trường `DASKTOON_FINISH_STYLES_DIR` đổi thư mục (dùng cho test). Style lưu mọi
  thiết lập của §4 và số phiên bản; thiết lập mới về sau mà style cũ không có thì lấy mặc định.

## 6. Giao diện

- Panel **Illustration Finish** trong Render Properties, cho engine DaskToon Anime và EEVEE:
  - **header**: công tắc bật bộ lọc;
  - **thân panel**:
    - **Tổng**;
    - hàng Style (menu, Lưu, Xóa);
    - **Xem trong viewport** (Tắt / Camera view / Luôn), mặc định Camera view;
    - nút **Nét màu cho mọi material**;
  - **bốn panel con** theo nhóm: Màu tranh, Chiều sâu, Ánh sáng tranh, Nét và chất. Mỗi lớp có ô bật và các thanh chỉnh.
- Bật bộ lọc thì các 3D Viewport đang ở camera view với chế độ Rendered hiện bộ lọc ngay. Tab Animation đã để camera
  view ở chế độ Rendered.
- Bản dịch tiếng Việt cho mọi chữ.

## 7. Compositor của scene

- Scene **chưa có** compositor: DaskToon tạo node tree "DaskToon Compositor" (Render Layers → Illustration Finish →
  Group Output) và gán cho scene.
- Scene **đã có** compositor của người dùng: không động vào. Panel báo "Scene đã có compositor riêng" và có nút **Thêm
  vào compositor**, chèn nhóm Illustration Finish ngay trước đầu ra.
- Tắt bộ lọc thì node nhóm bị **mute** (ảnh đi thẳng qua), không xóa, nên chỉnh sửa của người dùng trong tree còn nguyên.
- Bật bộ lọc thì pass **Depth** của view layer được bật (lớp 4, 5, 8 cần nó).
- Engine Export không bị ảnh hưởng (compositor chỉ áp lên ảnh render).

## 8. Thành phần và file

| Thành phần | File |
|---|---|
| Dựng nhóm node, gắn vào compositor, pass, mặt trời | `scripts/modules/dasktoon_finish/` (`nodes.py`, `scene.py`, `sun.py`) |
| Style có sẵn và của người dùng | `scripts/modules/dasktoon_finish/styles.py` |
| Thiết lập, panel, operator, đồng bộ | `scripts/startup/bl_ui/dasktoon_finish.py` |
| Bản dịch | `dasktoon_translations.py` |

Tên socket và tên mục do code tạo được đặt lại bằng tiếng Anh ngay sau khi tạo, vì giao diện tiếng Việt dịch dữ liệu
mới (bài học từ bộ lọc hành động nhanh).

## 9. Kiểm thử

- `dasktoon_finish_test.py`:
  - **Nhóm node và thiết lập**:
    - nhóm dựng được (cả khi giao diện tiếng Việt);
    - thiết lập ghi đúng vào đầu vào của nhóm;
    - tắt thì mute;
    - pass Depth được bật.
  - **Compositor của scene**:
    - scene trống thì có tree mới;
    - tree của người dùng không bị đổi;
    - nút Thêm vào compositor chèn trước đầu ra.
  - **Style**:
    - style có sẵn đặt đúng thiết lập;
    - lưu, đọc, xóa style người dùng (thư mục tạm);
    - style thiếu thiết lập thì dùng mặc định.
  - **Mặt trời**:
    - Sun trước camera thì có vị trí trên ảnh;
    - Sun sau camera thì tia sáng tắt.
  - **Nét màu**: nút đặt Harmonic cho material có outline, bỏ qua material khác.
- `dasktoon_finish_render_test.py`: render nền (EEVEE, ảnh nhỏ) một cảnh mẫu (mặt phẳng gần, mặt phẳng xa, quả cầu
  phát sáng, Sun). Mỗi lớp bật riêng phải đổi ảnh đúng hướng:
  - **không khí**: mặt phẳng xa gần màu không khí hơn mặt phẳng gần;
  - **glow**: quanh quả cầu sáng hơn;
  - **vignette**: góc tối hơn giữa;
  - **gradient**: phía sáng ấm hơn phía tối;
  - **màu bóng**: vùng tối ngả về màu bóng;
  - **Tổng = 0** thì ảnh như khi tắt.
- Ảnh chụp tiếng Anh và tiếng Việt: panel; cùng một cảnh trước và sau bộ lọc; camera view có bộ lọc trong tab
  Animation.

## 10. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Nét cọ (Kuwahara) và blur lớn làm camera view chậm | Kích thước theo tỉ lệ ảnh, nên viewport nhỏ thì nhẹ hơn; đo khung hình mỗi giây trong ảnh chụp kiểm tra; ghi kết quả vào báo cáo |
| Viền sáng ngược sáng lấy mép theo độ sâu nên chỉ gần đúng | Giữ độ rộng nhỏ; Rim trong material vẫn là viền sáng chính |
| Nền trời có độ sâu rất lớn nên bị nhòa hết | Thanh **Bầu trời** riêng cho mức nhòa của nền (mặc định thấp) |
| API compositor của Blender 5.x đổi (socket dạng menu, node group cho scene) | Thăm dò khi lập kế hoạch; test dựng nhóm chạy trên chính bản build |
| Style của người dùng tạo bằng phiên bản cũ | Số phiên bản trong file; thiếu thì lấy mặc định |

## 11. Ngoài phạm vi, có thể làm sau

- Bộ lọc tương tự trong Unity (post-processing URP).
- Nạp LUT `.cube`.
- Tách nhân vật và cảnh nền để chỉnh riêng (Cryptomatte).

## 12. Nhật ký quyết định

| Quyết định | Ai chốt |
|---|---|
| Chỉ trong DaskToon | Người dùng |
| Đủ bốn nhóm: ánh sáng tranh, màu tranh, chiều sâu, nét và chất | Người dùng |
| Không theo một họa sĩ, người dùng tự chỉnh | Người dùng |
| Ưu tiên chất lượng; duyệt spec trước | Người dùng |
| Kết hợp: Rim, Shadow Color, nét Harmonic để trong material (dùng lại); 12 lớp phủ trong compositor; không C++ | Claude (chờ duyệt) |
| Thứ tự và danh sách 12 lớp (§4), kích thước theo tỉ lệ chiều cao ảnh, thanh Tổng | Claude (chờ duyệt) |
| Năm style có sẵn: Mặc định, Nắng sớm, Hoàng hôn, Đêm, Màu nước; style người dùng là file JSON như Shading Styles | Claude (chờ duyệt) |
| Panel trong Render Properties; mặc định chỉ hiện trong camera view | Claude (chờ duyệt) |
| Không động vào compositor của người dùng, chỉ chèn khi bấm nút; tắt thì mute | Claude (chờ duyệt) |
| Mặt trời lấy từ Sun của scene, chiếu lên ảnh qua camera | Claude (chờ duyệt) |
| Nét màu là một nút đổi material (có Undo), không tự động | Claude (chờ duyệt) |
