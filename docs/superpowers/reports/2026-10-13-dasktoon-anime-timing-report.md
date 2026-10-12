# DaskToon: nhịp anime và bộ lọc hành động nhanh (C), báo cáo

- Ngày: 2026-10-13. Người dùng giao "tiến hành lên kế hoạch C" và chọn: nhịp anime cho cả DaskToon và Unity, hiệu ứng
  render trong DaskToon trước, một spec chung, làm tự động như B.
- Nhánh: `dasktoon-anime-timing`, tách từ `dasktoon-clips` (`0b7a00e9310`), nên chồng lên bốn nhánh trước. Chưa push,
  chưa merge.
- Spec: `docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-13-dasktoon-anime-timing.md`.

## 1. Đã làm được gì

| Phần | Nội dung |
|---|---|
| Nhịp anime | Mỗi clip có bảng nhịp: từ một khung, clip chạy **1s, 2s, 3s, 4s** (mỗi hình giữ 1 đến 4 khung) hoặc **Giữ** (đứng yên ở khung đó), tới dòng kế tiếp. Nhịp tính ngay trong lõi C++ lúc đánh giá action (`anim_sys.cc`), nên xương, shape key và khung lẻ (motion blur) đều theo nhịp, cả khi render. Clip không có bảng thì như cũ |
| Giao diện nhịp | Nút **Timing** trong header timeline nhân vật hiện nhịp ở khung hiện tại ("2s", "Giữ"); popover có các nút đặt nhịp từ khung này và danh sách dòng nhịp (xóa được). **Key Pose** key vào khung vẽ của nhịp (ví dụ đứng ở khung 16 khi chạy 2s từ khung 1 thì key vào khung 15, đúng dáng đang thấy) |
| Nhịp trong Unity | Clip có nhịp được đánh dấu `DaskToonStepped` và tắt nén animation; script `DaskToonClipImporter` (phiên bản script 4) đặt mọi key của clip thành tiếp tuyến **Constant**, nên game đổi dáng đúng ở khung vẽ, giữa hai khung vẽ không nội suy. `userData` nay chứa nhiều dấu, cách nhau bởi dấu cách |
| Onion skin | Nút **Bóc Vỏ Hành** (Onion Skin) và popover (số bóng trước, sau; độ đậm). Bóng là dáng mọi mesh của nhân vật ở các **khung có key** trước (đỏ) và sau (xanh dương) khung hiện tại, càng xa càng mờ, vẽ trong mọi 3D Viewport. Dừng tay một nhịp ngắn thì DaskToon tạm nhảy tới các khung đó, chép hình, trả về khung cũ; đang phát thì ẩn bóng |
| Hành động nhanh | Nút **Hành động nhanh** (Fast Action) và popover (ngưỡng tốc độ, kéo nhòe, số bóng lưu, độ đậm và màu bóng lưu, mật độ, độ dài và màu vệt). Bật thì mọi mesh của nhân vật có modifier Geometry Nodes "DaskToon Fast Action" ở cuối: chỗ nào nhanh hơn ngưỡng thì mặt sau **bị kéo nhòe** về phía khung trước, hiện tối đa 3 **bóng lưu** của các khung trước (chỉ phần nhanh, trong suốt, cũ hơn thì mờ hơn), và **vệt tốc độ** kéo lùi. Tắt thì modifier tắt. Hiệu ứng không vào FBX |

Cách dùng:

1. Tab **Animation**, chọn một phần của nhân vật, chọn clip.
2. Đứng ở khung muốn đổi nhịp, mở **Timing**, bấm 2s (hoặc 3s, 4s, Giữ). Key bằng **Key Pose** như thường.
3. Bật **Bóc Vỏ Hành** để thấy dáng ở key trước và sau khi đặt dáng ở giữa.
4. Bật **Hành động nhanh** để xem smear, bóng lưu và vệt ở những khung chuyển động nhanh; với nhịp anime, hiệu ứng chỉ
   hiện ở khung đổi hình. Mô phỏng chạy từ khung đầu, nên phát (hoặc bước từng khung) từ đầu clip.
5. **Engine Export**: clip có nhịp trong Unity đổi dáng đúng khung vẽ.

## 2. Kiểm thử

- `dasktoon_timing_test.py` (9 test): 2s/3s/4s/Giữ và đổi nhịp giữa clip (vị trí xương và giá trị shape key ở từng khung),
  khung lẻ, clip không bảng như cũ, operator và nhãn nút, popover, Key Pose vào khung vẽ.
- `dasktoon_onion_test.py` (9 test): khung bóng theo key (gần trước), với nhịp anime thì khung vẽ đang thấy không thành
  bóng, chép hình ở khung khác trong hệ tọa độ thế giới, khung, lựa chọn và giá trị animation như cũ sau khi chép, phát
  hiện thay đổi chưa key, không chép khi còn thay đổi chưa key (giữ thay đổi), nhân vật không có animation, tắt, popover.
- `dasktoon_fast_action_test.py` (7 test): khối lập phương lướt 14,4 m/s rồi dừng: lúc nhanh có hai bóng lưu và material
  bóng lưu, mặt sau bị kéo nhòe còn mặt trước giữ nguyên, có vệt tốc độ dài phía sau; dừng lâu thì hình như mesh gốc;
  thiết lập đổi đầu vào modifier và màu material; tắt và bật; chỉ mesh của nhân vật; chạy được khi giao diện tiếng Việt;
  popover.
- Xuất: meta clip có nhịp có `DaskToonStepped` và `animationCompression: 0`, clip không nhịp như cũ (test xuất clip và
  test YAML).
- **Unity thật** `dasktoon_unity_clips_test.py`: mọi key của clip Walk (2s) có tiếp tuyến Constant, giá trị blend shape ở
  giữa khung 2 và 3 bằng giá trị khung 2; clip Wave (không nhịp) không bị đổi. Test Unity rig và model chạy lại: qua.
- Toàn bộ suite CMake: 52 file (491 test) đều qua.
- Chạy thật trong cửa sổ DaskToon: hẹn giờ onion skin chép bóng sau khi dừng tay, shader vẽ bóng hoạt động; render Eevee
  của bộ lọc hành động nhanh ra smear, bóng lưu và vệt.

## 3. Ảnh chụp

`docs/superpowers/reports/animation-tab/en|vi/`:

- `33_timing.png`: popover Timing, clip Walk chạy 2s từ khung 1 và 3s từ khung 7.
- `34_onion_skin.png`: khung 3 của clip Swing (thân trên nghiêng sang bên từ khung 1 tới khung 5), bóng đỏ là dáng khung 1,
  bóng xanh là dáng khung 5.
- `35_fast_action.png`: camera view (Rendered) ở khung 4 của Swing: thân trên bị kéo nhòe và để lại bóng lưu.

Ảnh 30 đến 32 giữ như cũ; nếu chụp lại thì header timeline có thêm nút Timing, Bóc Vỏ Hành và Hành động nhanh.

## 4. Quyết định Claude tự chốt (cần xem lại)

1. **Nhịp tính trong C++** (thời gian đánh giá của action đang dùng được làm tròn xuống khung vẽ), không bake key. Lý do:
   key gốc giữ nguyên, đổi nhịp tức thì, áp cho mọi thứ clip điều khiển. Giới hạn: chỉ action đang dùng, không áp cho
   strip NLA.
2. Bảng nhịp lưu trong action (`Action.dasktoon_timing`), nên mỗi clip một bảng và đi theo clip.
3. Key Pose key vào khung vẽ của nhịp, không vào khung hiện tại.
4. Unity: clip có nhịp dùng tiếp tuyến Constant (FBX vẫn bake mọi khung) thay vì bỏ bớt khung.
5. Onion skin dựa trên **khung có key**, không theo khung vẽ đều; bóng sau tô **xanh dương** (spec ghi "xanh").
6. Onion skin không chép khi còn thuộc tính có animation mà giá trị khác key (người dùng đang đặt dáng chưa key), vì nhảy
   khung sẽ làm mất thay đổi đó; thuộc tính có driver không tính. Lúc ấy bóng cũ vẫn hiện tới khi key hoặc đổi khung.
   Cũng không chép khi đang phát hay có operator modal đang chạy (đang kéo, xoay…).
7. Onion skin giữ tối đa 16 khung đã chép, xóa khi key hoặc mesh đổi. Bóng vẽ lùi ra sau 0,1% khoảng cách tới camera để
   chỗ trùng với mesh thì mesh thắng (không bị sọc).
8. Hành động nhanh: vận tốc tính trong hệ tọa độ thế giới (nên di chuyển cả object cũng tính); trạng thái mô phỏng là đám
   điểm (vị trí bây giờ và 3 khung trước) để bộ nhớ đệm mỗi khung nhỏ; độ mờ của bóng lưu cố định 1, 2/3, 1/3 (nhân với
   độ đậm); vệt là ống 4 cạnh dày 4 mm (độ dày không có trong popover); material bóng lưu và vệt riêng cho mỗi nhân vật.

## 5. Giới hạn và rủi ro

- Hành động nhanh dùng Simulation Zone: chỉ tính khi đi tới từng khung liên tiếp từ khung đầu; nhảy tới khung chưa tính
  thì chưa có hiệu ứng, đổi thiết lập thì tính lại từ đầu. Bộ nhớ đệm khoảng 48 byte mỗi đỉnh mỗi khung (mesh 50.000 đỉnh,
  250 khung: khoảng 600 MB).
- Onion skin nhảy khung để chép hình; chuỗi lắc (Spring) của tóc, váy có thể bị đặt lại khi nhảy, nên bóng có thể không
  có độ lắc (chưa kiểm).
- Trong Geometry Nodes của Blender 5.2, Join Geometry xếp đầu vào ngược thứ tự nối, nên mesh gốc không nằm đầu danh sách
  đỉnh; không ảnh hưởng hiển thị.

Khi làm (ledger):

- Bản tiếng Việt: Blender dịch tên socket và tên mục trạng thái Simulation Zone mới tạo khi giao diện dịch dữ liệu mới,
  nên lần đầu Hành động nhanh không bật được trong giao diện tiếng Việt (ảnh chụp tiếng Việt phát hiện ra). Đã sửa (đặt lại
  tên tiếng Anh) và thêm test.
- Bóng onion skin trùng mặt với mesh hiện tại bị sọc (z-fighting); đã sửa bằng shader riêng đẩy độ sâu.
- Test Unity lần đầu không chạy được vì package cache của dự án Unity tạm bị hỏng; xóa `Library` của dự án tạm rồi chạy
  lại.
