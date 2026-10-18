# DaskToon: nhịp anime và bộ lọc hành động nhanh (C)

- Ngày: 2026-10-13. Người dùng chọn (2026-10-13): nhịp anime giữ ở **cả DaskToon và Unity**; hiệu ứng hành động nhanh
  **render trong DaskToon trước** (Unity để sau); **một spec chung**; làm **tự động như B**. Phần còn lại Claude tự chốt,
  ghi ở §11 để người dùng xem lại.
- Lộ trình: R, A (tab Animation), B (clip) đã xong; **C** (spec này); R3 mắt và miệng sau.

## 1. Mục tiêu

1. **Nhịp anime**: clip chạy on 1s, 2s, 3s, 4s hoặc **giữ** (đứng hình), đổi nhịp giữa chừng trong một clip (anime hay
   chuyển từ 2s sang 1s ở đoạn nhanh). Thấy đúng khi xem trước, render, và trong game Unity (không bị nội suy mượt lại).
2. **Onion skin**: thấy mờ dáng của nhân vật ở các key trước và sau, ngay trong viewport.
3. **Bộ lọc hành động nhanh**: phần nào của nhân vật chuyển động nhanh thì tự có **smear** (kéo dài thân về phía sau),
   **afterimage** (bóng mờ ở các khung trước) và **speed lines** (vệt chuyển động); đứng yên thì không có gì. Thấy khi xem
   trước và render trong DaskToon.

## 2. Phạm vi

| Có | Không (để sau) |
|---|---|
| Bảng nhịp của clip, tính nhịp ngay lúc Blender tính animation (C++) | Lắc tóc/váy đi theo nhịp (lắc vẫn tính mỗi khung) |
| Popover Timing trong header timeline nhân vật | Bảng nhịp cho object không phải nhân vật |
| Clip có nhịp sang Unity giữ bậc thang | Hiệu ứng hành động nhanh trong Unity |
| Onion skin cho mesh của nhân vật | Onion skin cho Grease Pencil (Blender đã có) |
| Bộ lọc hành động nhanh bằng Geometry Nodes, cài cho cả nhân vật | Chỉnh tay từng vệt, từng bóng mờ |

## 3. Nhịp anime trong DaskToon

- **Bảng nhịp** của một clip: `Action.dasktoon_timing`, danh sách (khung, nhịp), nhịp ∈ {1, 2, 3, 4, Giữ}. Từ khung của
  một dòng cho tới dòng sau, clip chạy theo nhịp đó; trước dòng đầu là 1s. Clip không có bảng thì như Blender.
- **Cách tính** (C++, `anim_sys.cc`, chỗ Blender tính action đang dùng của một ID): thời điểm t trong một đoạn bắt đầu ở
  khung f với nhịp n > 1 được thay bằng `f + floor((t − f) / n) · n`; nhịp Giữ thay bằng f; nhịp 1 giữ nguyên t (cả khung
  lẻ của motion blur). Áp cho cả action, nên xương, shape key, controller của clip cùng nhịp. NLA không đổi.
- Hệ quả: tua, phát, render, xuất FBX đều thấy nhịp mà không phải bake; key gốc không bị sửa, đổi nhịp bao nhiêu lần cũng
  được.
- **Key Pose** khi clip có nhịp: key vào khung vẽ của nhịp hiện tại (khung đầu bước), đúng dáng đang thấy; báo "Keyed the
  pose of %s at frame %d".

## 4. Giao diện nhịp

Header timeline nhân vật, sau phần clip: nút **Timing** (popover), chữ trên nút là nhịp tại khung hiện tại ("2s", "Hold").

- Danh sách các dòng của clip đang dùng: khung, nhịp (chọn 1s/2s/3s/4s/Hold), nút xóa.
- **Set Timing Here** (`dasktoon.timing_set`, nhịp chọn sẵn): thêm hoặc sửa dòng ở khung hiện tại.
- Chưa có clip/action thì popover ghi "Key a pose first".

## 5. Nhịp anime trong Unity

- Clip có bảng nhịp (ít nhất một dòng nhịp khác 1) xuất như B (bake từng khung, nên giá trị đã giữ đúng nhịp), meta thêm
  dấu `DaskToonStepped` trong `userData` và tắt nén animation.
- Script `Editor/DaskToonClipImporter.cs` (cài cùng các script khác, phiên bản script 4): với file clip có dấu, đặt mọi key
  của mọi đường cong của clip thành tiếp tuyến **Constant**, nên game đổi dáng đúng ở khung vẽ, không nội suy giữa hai khung.
  `userData` có thể chứa nhiều dấu (cách nhau bởi dấu cách); `DaskToonAvatarImporter` đọc theo dấu.

## 6. Onion skin

- Công tắc **Onion Skin** trong header timeline nhân vật (popover: số bóng trước, sau, mặc định 1 và 1; độ mờ).
- Bóng là dáng của mọi mesh thuộc nhân vật ở các **khung có key** trước và sau khung hiện tại (của clip đang dùng), vẽ trong
  mọi 3D Viewport: trước tô đỏ, sau tô xanh, càng xa càng mờ.
- Cách làm: sau khi khung hoặc animation đổi và người dùng dừng tay một nhịp ngắn (không làm lúc đang phát), DaskToon tạm
  nhảy tới các khung đó, chép hình mesh đã tính, trả về khung cũ, rồi vẽ bằng `gpu` (mặt mờ, có depth). Lúc đang phát thì ẩn
  bóng.

## 7. Bộ lọc hành động nhanh

- Nhóm node Geometry Nodes **DaskToon Fast Action** (dựng bằng Python), là modifier cuối cùng của mỗi mesh thuộc nhân vật.
  Một **Simulation Zone** giữ hình của các khung trước, nên vận tốc mỗi đỉnh = (vị trí − vị trí khung trước) / thời gian
  khung.
- Chỉ đỉnh có tốc độ trên **ngưỡng** (m/s) mới có hiệu ứng:
  - **Smear**: đỉnh ở mặt sau theo hướng chuyển động bị kéo về phía vị trí cũ theo **độ smear**;
  - **Afterimage**: tối đa 3 bản sao hình của các khung trước, chỉ phần nhanh, material trong suốt màu **afterimage**, bản
    càng cũ càng mờ;
  - **Speed lines**: từ một phần các đỉnh nhanh (**mật độ**), vệt từ vị trí hiện tại lùi theo hướng ngược chuyển động, dài
    theo tốc độ × **độ dài**, material **màu vệt**.
- Thiết lập theo nhân vật: `Armature.dasktoon_fast_action` (bật/tắt, ngưỡng, smear, số afterimage, độ mờ, màu, mật độ và độ
  dài vệt, màu vệt). Popover **Fast Action** trong header timeline nhân vật; bật thì gắn modifier cho mọi mesh của nhân vật,
  tắt thì tắt modifier; đổi thiết lập thì cập nhật mọi modifier.
  *Bổ sung 2026-10-13 (thử trên mô hình thật):* ngưỡng và độ dày vệt tính cho nhân vật cao 1,6 m, nhân theo chiều cao nhân
  vật (mesh ở tư thế nghỉ) / 1,6; độ dài vệt là thời gian nên tự theo tốc độ; mật độ vệt mặc định 0,08 (trước 0,15).
- Hiệu ứng nằm trong modifier, không vào FBX (Engine Export không áp modifier), nên Unity không bị ảnh hưởng.
- Với nhịp anime: lúc giữ dáng vận tốc bằng 0, nên hiệu ứng chỉ hiện ở khung đổi dáng, đúng kiểu smear frame của anime.

## 8. Thành phần và file

| Thành phần | File |
|---|---|
| Tính nhịp | `source/blender/blenkernel/intern/anim_sys.cc` (đọc `dasktoon_timing` trong `system_properties` của action) |
| Bảng nhịp, Key Pose theo nhịp | `scripts/modules/dasktoon_animation/timing.py`; `bl_ui/dasktoon_animation.py` (thuộc tính, popover, operator) |
| Onion skin | `scripts/modules/dasktoon_animation/onion.py` (chọn khung, chép hình); vẽ và hẹn giờ trong `bl_ui/dasktoon_animation.py` |
| Hành động nhanh | `scripts/modules/dasktoon_animation/fast_action.py` (nhóm node, material, gắn cho nhân vật) |
| Unity | `dasktoon_export` (dấu, tắt nén), `unity_scripts/Editor/DaskToonClipImporter.cs`, `scripts_install.py` (phiên bản 4) |
| Bản dịch | `dasktoon_translations.py` |

## 9. Kiểm thử

- `dasktoon_timing_test.py`: 2s/3s/Hold/đổi nhịp giữa clip (vị trí xương và giá trị shape key ở từng khung), khung lẻ, clip
  không bảng như cũ, Key Pose vào khung vẽ, popover.
- `dasktoon_onion_test.py`: khung bóng theo key, số bóng, hình mesh ở khung bóng khác khung hiện tại, khung hiện tại không
  đổi sau khi chép, bộ nhớ đệm.
- `dasktoon_fast_action_test.py`: khối lập phương lướt nhanh rồi dừng: lúc nhanh có đỉnh bị kéo, có bản sao, có vệt; lúc
  dừng thì không; thiết lập nhân vật đổi đầu vào của mọi modifier; bật/tắt.
- Xuất: meta clip có nhịp có dấu `DaskToonStepped`, nén tắt.
- Unity thật: clip có nhịp có tiếp tuyến Constant, giá trị giữa hai khung vẽ bằng giá trị khung vẽ trước.
- Ảnh chụp: popover Timing, onion skin, một khung có smear/afterimage/vệt.

## 10. Rủi ro

| Rủi ro | Giảm |
|---|---|
| Sửa đường tính animation lõi | Chỉ khi action có bảng nhịp; test so giá trị từng khung; không có bảng thì đi đường cũ |
| Key ở khung giữa hai khung vẽ không thấy ngay | Key Pose key vào khung vẽ; ghi chú trong popover |
| Onion skin chậm với mesh lớn | Chỉ tính khi dừng tay, giữ bộ nhớ đệm theo khung và clip |
| Simulation Zone cần chạy tuần tự | Render và phát chạy tuần tự; tua ngược dùng bộ nhớ đệm của Blender |
| Số đỉnh khác số đã nhớ (Subdivision render mịn hơn lúc xem, dùng chung bộ nhớ đệm với khung nhìn) | Không đỉnh nào nhanh ở khung đó, cả khi Blender lấy lại trạng thái đã nhớ (*sửa 2026-10-14*: cảnh đánh nhau thử trên lr_shape, áo chia 1 lần lúc xem, 2 lần lúc render, vệt và bóng mờ ghép nhầm đỉnh, xòe thành hình quạt từ khung đầu) |
| Lắc tóc/váy vẫn on 1s khi thân on 2s | Ghi rõ; làm tùy chọn sau |
| Viền DaskToon cũng tự xếp mình xuống cuối, mỗi lần mở file | *Sửa 2026-10-15* (cảnh đánh nhau 1 phút): viền đứng ngay trước Hành động nhanh. Đứng sau, viền mất ở các khung có bóng mờ (bóng mờ thêm vật liệu riêng vào lưới) |
| Render khi chưa phát clip trong khung nhìn (render từ dòng lệnh, hay F12 ngay sau khi mở file) | Chưa xử lý (*thấy 2026-10-14* khi render cảnh đánh nhau thử): render dùng những gì khung nhìn đã nhớ, chỉ có khung đầu, nên mọi chỗ đã rời chỗ ở khung đầu đều thành nhanh, bóng mờ hiện ở chỗ cũ. Phát clip một lần (hay bake) rồi render thì đúng. Nên làm: tự phát hoặc bake trước khi render |

## 11. Nhật ký quyết định

| Quyết định | Ai |
|---|---|
| Nhịp anime giữ ở cả DaskToon và Unity; hiệu ứng render DaskToon trước; một spec; tự động | Người dùng |
| Bảng nhịp theo clip, nhịp 1/2/3/4/Giữ, đổi nhịp giữa clip | Claude (chờ xem lại) |
| Tính nhịp trong C++ lúc tính action (không dùng modifier Stepped trên từng F-curve, vì phải gắn lại cho mọi đường cong mới và mọi slot) | Claude (chờ xem lại) |
| Unity: tiếp tuyến Constant đặt bởi script import, nén tắt | Claude (chờ xem lại) |
| Key Pose key vào khung vẽ khi có nhịp | Claude (chờ xem lại) |
| Onion skin theo khung có key, vẽ bằng Python `gpu`, tính khi dừng tay | Claude (chờ xem lại) |
| Hành động nhanh bằng Geometry Nodes + Simulation Zone, thiết lập theo nhân vật, modifier cuối | Claude (chờ xem lại) |
