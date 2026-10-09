# DaskToon: clip cho Unity (B), báo cáo

- Ngày: 2026-10-10. Người dùng giao "làm B" và chọn: mỗi clip một action, làm tự động như A.
- Nhánh: `dasktoon-clips`, tách từ `dasktoon-animation-tab` (`6c3d986b3ed`), nên chồng lên ba nhánh trước. Chưa push,
  chưa merge.
- Spec: `docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-10-dasktoon-clips.md`.

## 1. Đã làm được gì

| Phần | Nội dung |
|---|---|
| Clip | Mỗi clip là một Action, có slot cho mọi thành phần của nhân vật (armature, object của nhân vật, Key shape key của mesh), nên thân và mặt đi chung một clip. Clip biết nó thuộc nhân vật nào (`Action.dasktoon_character`); Loop là cờ "Cyclic Animation" có sẵn của Blender. Clip không dùng tới vẫn được lưu trong file |
| Giao diện | Header timeline nhân vật (tab Animation): **menu clip** (chuyển clip, Clip mới, Xóa clip), ô **tên**, nút **Loop**, nút **+**. Chuyển clip là đổi cho cả nhân vật, và khoảng xem trước theo clip |
| Animation có sẵn | Nhân vật chưa có clip mà đã có key (ví dụ key bằng Key Pose của A) thì lần đầu tạo clip, animation đó thành clip "Clip"; action cũ vẫn giữ |
| Xuất sang Unity | Nhân vật có clip: FBX model không kèm animation, mỗi clip thành `<Model>@<Clip>.fbx` (bake một take theo khoảng khung của clip, chuỗi lắc Runtime bị mute như khi ghi model). Meta cắt take thành một clip đúng tên, khoảng, cờ lặp, dùng avatar của model. Báo cáo xuất có dòng "Clips: Walk (loop), Wave". Không có clip thì như cũ |
| Avatar Humanoid (sửa lỗi có từ R1) | Unity tự ghép xương thì bỏ sót hai tay của khung DaskToon (13/55 xương), avatar không phải Humanoid, và clip Humanoid không import được. Nay script `DaskToonAvatarImporter` dựng mô tả Humanoid từ cây xương Unity đã import, chuyển model sang Humanoid và import lại, rồi cho các file clip chép avatar đó (phiên bản script 3) |

Cách dùng:

1. Tab **Animation**, chọn một phần của nhân vật.
2. Bấm **+** trong header timeline để có clip mới, đặt tên (Idle, Walk…), bật **Loop** nếu cần, rồi key như thường.
3. Chuyển giữa các clip bằng menu clip.
4. **Engine Export**: trong Unity mỗi clip là một file `Model@Clip.fbx` chứa một AnimationClip cùng tên.

## 2. Kiểm thử

- `dasktoon_clips_test.py` (8 test): clip gán cho mọi thành phần, key mới vào đúng clip, gom animation có sẵn, chuyển clip
  và khoảng xem trước, Loop, xóa clip, operator và header, bản dịch.
- `dasktoon_export_clips_test.py` (3 test): model không animation, hai file `@` với meta đúng tên, take, khoảng, lặp, avatar
  nguồn, dấu Humanoid; xuất xong mọi thứ như cũ; không có clip thì như cũ; tắt animation thì không có file clip.
- **Unity thật** `dasktoon_unity_clips_test.py`: avatar của model là Humanoid hợp lệ; mỗi file `@` có đúng một
  AnimationClip đúng tên, cờ lặp, độ dài (11/24 giây và 15/24 giây), chuyển động Humanoid, có đường cong blend shape.
- Test Unity rig và model chạy lại sau khi thêm trình import avatar: qua.
- Toàn bộ suite CMake: 49 file (465 test) đều qua.

## 3. Ảnh chụp

`docs/superpowers/reports/animation-tab/en|vi/32_clips.png`: header timeline nhân vật với menu clip đang mở (Walk, Wave,
Clip mới, Xóa clip), ô tên Walk và nút Loop đang bật.

## 4. Quyết định Claude tự chốt (cần xem lại)

1. Clip thuộc nhân vật qua con trỏ `Action.dasktoon_character`; Loop dùng cờ Cyclic Animation của Blender.
2. **Mỗi clip một file `Model@Clip.fbx`**, model không kèm animation. Lý do: một FBX nhiều take của Blender ghi mỗi action
   của mỗi object thành một take riêng (thân và mặt tách nhau); còn một take dài cắt khúc thì lắc của clip trước tràn sang
   clip sau. Đổi lại: nhiều file hơn, mỗi file chép lại mesh.
3. Gom animation có sẵn thành clip "Clip" khi tạo clip đầu tiên.
4. Chuyển clip thì đặt khoảng xem trước theo clip.
5. Avatar Humanoid do script DaskToon dựng trong Unity (model ghi Generic kèm dấu rồi được chuyển). Lý do: Unity tự ghép
   thì bỏ sót xương; còn tự tính tư thế T từ Blender thì phải lặp lại đúng phép đổi trục của FBX. Hệ quả: lần import đầu,
   Unity import model hai lần; nếu project không có script DaskToon thì model ở Generic, không báo lỗi.

Khi làm (ledger):

- Lỗi avatar Humanoid là lỗi có từ R1: test Unity của rig không kiểm avatar. Đã thêm kiểm tra vào test clip.
- Trong test Unity, đọc avatar ngay trong phiên vừa import lại có thể ra đối tượng cũ; test giải phóng asset đã nạp trước
  khi đọc. Logic chuyển clip của sản phẩm đã kiểm là chạy đúng ngay trong một phiên.
- Shape key có một key duy nhất là đường cong phẳng, bị bộ xuất FBX bỏ; dữ liệu test key Smile ở hai khung.

## 5. Review (tự review)

Phiên này không tạo subagent khi người dùng chưa yêu cầu, nên đây là tự review, yếu hơn một reviewer độc lập.

- Không có lỗi Critical/Important còn lại (lỗi avatar Humanoid đã sửa ở trên).
- Để lại (Minor):
  - nút menu clip bị cắt chữ khi header timeline chật;
  - model có dấu `DaskToonHumanoid` mà người dùng tự đổi sang Generic trong Unity thì lần import sau bị chuyển lại sang
    Humanoid;
  - cảnh báo "Identifier uniqueness violation" của các component lò xo (có từ R2b) hiện lại ở mỗi lần import model.

## 6. Còn lại

- Bốn nhánh xếp chồng chờ người dùng chọn merge, mở PR hay giữ: `dasktoon-spring-constraint` → `dasktoon-minor-fixes` →
  `dasktoon-animation-tab` → `dasktoon-clips`.
- Người dùng xem lại các quyết định ở §4 của báo cáo này và của báo cáo A.
- Tiếp theo: C (nhịp anime, onion skin, bộ lọc hành động nhanh), R3 (mắt, miệng).
