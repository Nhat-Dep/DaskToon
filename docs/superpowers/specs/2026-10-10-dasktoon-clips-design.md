# DaskToon: clip cho Unity (B)

- Ngày: 2026-10-10. Người dùng chọn (2026-10-10): **mỗi clip một action**, làm **tự động như A**. Các phần còn lại Claude
  tự chốt, ghi ở §10 để người dùng xem lại.
- Lộ trình: R (xong), A tab Animation (xong), **B** (spec này), C nhịp anime, R3 mắt và miệng.

## 1. Mục tiêu

Một nhân vật có nhiều clip (Idle, Walk, Attack…). Mỗi clip giữ cả thân (xương) lẫn mặt (shape key, controller biểu cảm).
Trong timeline nhân vật của tab Animation, người dùng tạo, chuyển, đổi tên, bật lặp clip. Engine Export đưa mỗi clip sang
Unity thành một AnimationClip đúng tên, đúng cờ lặp, có cả chuyển động thân và biểu cảm mặt.

Hiện tại: mỗi object có action riêng (xương một action, shape key một action), FBX ghi mỗi action thành một take, nên trong
Unity thân và mặt nằm ở hai clip khác nhau và không clip nào lặp.

## 2. Phạm vi

| Có | Không |
|---|---|
| Clip = một Action có slot cho mọi thành phần của nhân vật | Chỉnh clip đã import từ ngoài |
| Menu clip, tên, Loop, New, Delete trong header timeline nhân vật | Animator Controller, chuyển tiếp giữa clip trong Unity |
| Chuyển clip cho cả nhân vật một lần; khoảng xem trước theo clip | Root motion, sự kiện animation |
| Gộp animation có sẵn thành clip đầu tiên | Nhịp anime, onion skin (C) |
| Xuất mỗi clip thành `<Model>@<Clip>.fbx` kèm meta, báo cáo, test Unity thật | |

## 3. Clip là gì

- **Clip = một Action** (Blender 5.2 có slot): một slot cho armature, một slot cho Key (shape key) của mỗi mesh thuộc nhân
  vật, một slot cho mỗi object có controller biểu cảm. Chuyển clip là gán Action đó cho mọi thành phần; Blender tự chọn slot
  theo tên, và tự tạo slot khi key lần đầu.
- **Thuộc nhân vật nào**: thuộc tính mới `Action.dasktoon_character` (con trỏ tới object armature, giữ được khi đổi tên).
  Clip của một nhân vật là các Action trỏ tới armature của nó, xếp theo tên.
- **Lặp**: cờ có sẵn của Blender `Action.use_cyclic` ("Cyclic Animation"), hiện trong header với chữ "Loop".
- **Khoảng khung**: `Action.frame_range` (khoảng đặt tay nếu người dùng bật, không thì theo key).
- Nhân vật theo định nghĩa của A (`dasktoon_animation.character`): armature, object có nó trong chuỗi cha, object có
  modifier Armature trỏ tới nó.

## 4. Giao diện

Header timeline nhân vật (khi Whole Character bật, sau Key Pose), cho nhân vật của object đang active (không có thì nhân
vật đầu tiên đang có phần được chọn):

```
[Key Pose] [Walk ▾] [Walk____] [Loop] [+]
```

- **Menu clip** (`DASKTOON_MT_character_clips`): các clip của nhân vật (chọn để chuyển), rồi **New Clip**, **Delete Clip**.
  Chưa có clip nào thì nút menu ghi "No Clip".
- **Tên**: ô sửa tên của clip đang dùng (tên Action).
- **Loop**: công tắc `use_cyclic` của clip đang dùng.
- **+** (`dasktoon.clip_new`): clip mới, rỗng, đặt tên "Clip", "Clip.001"…; nhân vật chuyển sang nó.
- **Chuyển clip** (`dasktoon.clip_use`): gán clip cho mọi thành phần; bật khoảng xem trước của scene theo khoảng khung của
  clip (clip rỗng thì giữ nguyên).
- **Delete Clip** (`dasktoon.clip_delete`, hỏi xác nhận): xóa Action; nhân vật chuyển sang clip đầu tiên còn lại, hết clip
  thì bỏ action khỏi các thành phần.

## 5. Animation có sẵn

Khi nhân vật chưa có clip nào mà các thành phần đã có animation (ví dụ key bằng Key Pose của A: xương một action, shape key
một action), lần đầu bấm **+** hoặc mở menu và chọn New Clip thì DaskToon gom animation hiện tại của mọi thành phần vào một
clip mới tên "Clip" (chép F-curve vào slot của từng thành phần), gán clip đó, rồi mới tạo clip rỗng như yêu cầu. Action cũ
không bị xóa.

## 6. Xuất sang Unity

- Nhân vật có clip (armature mà Engine Export tìm thấy, như file rig của R2b): **FBX model không có animation**; mỗi clip
  thành một file `<Model>@<Clip>.fbx` trong thư mục Model, cùng bộ object với model.
- Ghi một clip: gán clip cho mọi thành phần, đặt khoảng khung của scene theo clip, bake một take (tên take là tên scene),
  chuỗi lắc Runtime bị mute như khi ghi model (R2b); xong thì trả lại clip, khoảng khung, mute như cũ.
- Meta của mỗi file clip: `importAnimation: 1`, một mục `clipAnimations`: `name` = tên clip, `takeName` = tên scene,
  `firstFrame`/`lastFrame` = khoảng khung của clip, `loopTime` = cờ lặp; avatar chép từ model (`avatarSetup: 2`, nguồn là
  avatar của FBX model). Không tạo material.
- **Humanoid** (phát hiện khi làm B): Unity tự ghép xương thì bỏ sót hai tay của khung DaskToon, avatar của model không
  phải Humanoid nên clip không chép được. Model Humanoid nay ghi Generic kèm `userData: DaskToonHumanoid`, file clip ghi
  Generic kèm `DaskToonHumanoidClip`. Script `Editor/DaskToonAvatarImporter.cs` (phiên bản script 3; Engine Export cài nó
  cả khi model không có chuỗi lắc) dựng mô tả Humanoid từ cây xương Unity đã import, chuyển model sang Humanoid và import
  lại, rồi cho các file clip của nó chép avatar đó. Không có script thì mọi thứ ở Generic, không báo lỗi.
- Không có clip thì như cũ (một FBX, `include_animation` quyết định có animation hay không). `include_animation` tắt thì
  không ghi file clip.
- Báo cáo xuất có dòng "Clips: Idle, Walk (loop) …".

## 7. Bản dịch

Mọi chữ mới có bản tiếng Việt; tên clip là dữ liệu, không dịch.

## 8. Kiểm thử

- `dasktoon_clips_test.py` (nền): tạo, chuyển (cả armature lẫn Key nhận clip, key mới vào đúng clip), đổi tên, Loop, xóa,
  gom animation có sẵn (F-curve của xương và shape key có trong clip đầu), khoảng xem trước, header (menu, tên, Loop).
- `dasktoon_export_clips_test.py` (nền): xuất nhân vật hai clip → model không animation, hai file `@`, meta đúng tên, khoảng,
  lặp, avatar nguồn; không có clip thì như cũ.
- Unity thật (`dasktoon_unity_clips_test.py`): mỗi file `@` có đúng một AnimationClip tên clip, `isLooping` đúng, độ dài đúng,
  có đường cong `blendShape.Smile`.
- Ảnh chụp: header timeline với menu clip mở.

## 9. Rủi ro

| Rủi ro | Giảm |
|---|---|
| Nhiều file FBX, mỗi file chép lại mesh | Đổi lại được lắc giữa các clip không lẫn vào nhau và thân với mặt cùng một clip; ghi chú trong báo cáo |
| Avatar chép từ model sai fileID | Test Unity kiểm clip import được và có đường cong |
| Gom animation cũ sai đường cong | Test so F-curve trước và sau |

## 10. Nhật ký quyết định

| Quyết định | Ai |
|---|---|
| Mỗi clip một action | Người dùng |
| Làm tự động | Người dùng |
| Thuộc nhân vật bằng con trỏ `Action.dasktoon_character`; lặp bằng `use_cyclic` của Blender | Claude (chờ xem lại) |
| Mỗi clip một file `<Model>@<Clip>.fbx`, model không animation (một FBX nhiều take không giữ được thân và mặt chung một take; một take cắt khúc thì lắc của clip trước tràn sang clip sau) | Claude (chờ xem lại) |
| Gom animation có sẵn thành clip "Clip" khi tạo clip đầu tiên | Claude (chờ xem lại) |
| Chuyển clip thì bật khoảng xem trước theo clip | Claude (chờ xem lại) |
| Avatar Humanoid do script DaskToon dựng trong Unity (model ghi Generic kèm dấu), vì Unity tự ghép thì bỏ sót xương; tính tư thế T từ Blender sẽ phải lặp lại phép đổi trục của FBX | Claude (chờ xem lại) |
