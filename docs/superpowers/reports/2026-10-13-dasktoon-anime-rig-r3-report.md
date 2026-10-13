# DaskToon: rig anime R3 (mắt và miệng), báo cáo

- Ngày: 2026-10-13. Người dùng chọn R3 là việc tiếp theo, đọc kế hoạch rồi nói "tự động".
- Nhánh: `dasktoon-anime-rig-r3`, tách từ `dasktoon-master` (`0f2ef5a2b32`). Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` mục 10 (đã duyệt cùng spec R). Kế hoạch:
  `docs/superpowers/plans/2026-10-13-dasktoon-anime-rig-r3.md`.

## 1. Đã làm được gì

| Phần | Nội dung |
|---|---|
| Ánh mắt | Build Rig thêm xương `LookTarget` trước mặt (làm một lần; build lại giữ chỗ người làm hoạt hình đã đặt) và cho `LeftEye`, `RightEye` nhìn theo nó, giới hạn ngang ±30°, dọc ±20° (chỉnh trong panel con **Ánh mắt**). Mắt cầu (phần Accessory gắn xương mắt) đã chạy từ R1 |
| Ba vai trò phần mới | **Hàm** (Jaw), **Mắt phẳng** (Flat Eye), **Miệng 2D** (2D Mouth), có thiết lập riêng trong panel Parts. Phần tên "iris", "pupil" được đoán là Mắt phẳng |
| Hàm | Phần Jaw theo xương `Jaw`; hai vòng cạnh quanh nó hòa dần vào mặt (2/3 rồi 1/3), nên há miệng không rách mặt |
| Mắt phẳng | Tròng mắt vẽ trên mặt trượt trên UV khi mắt xoay: modifier UV Warp chỉ trên đỉnh của phần, độ dịch lấy từ driver đọc góc xoay của xương mắt (biểu thức đơn giản, không cần Auto Run). Range âm thì trượt ngược lại |
| Miệng 2D | Material của phần chọn một ô trong atlas (số hàng × số cột, đếm từ góc trên trái; quy ước: ô 0 ngậm, rồi A, I, U, E, O) theo thuộc tính `dt_mouth` của object. Xương `MouthCell` (deform, không weight) mang số ô sang FBX qua driver |
| Lip sync | Shape Keys › Expression Tools › **Khẩu hình từ âm thanh**: đọc file giọng nói (hoặc strip âm thanh đầu tiên của Sequencer), tìm độ to và hai formant thấp nhất mỗi khung (LPC bằng numpy), chấm 5 nguyên âm, rồi key shape key nguyên âm (tên VRM, VRoid, chữ thường, tiếng Nhật), xương hàm và `dt_mouth`, vào clip đang dùng. Im lặng thì ngậm miệng |
| Unity | Rig file phiên bản 2 ghi mắt phẳng và miệng 2D; importer gắn `DaskToonFlatEye` và `DaskToonMouthAtlas`. Bốn shader DaskToon có thêm thuộc tính "UV Transform" (shader phiên bản 2). Mắt phẳng trong Unity trượt **đúng bằng** trong DaskToon (sai khác dưới 1e-7). Clip Humanoid giữ đường cong của `MouthCell`. Script phiên bản 5 |

Cách dùng:

1. Thêm phần cho mesh: chọn vai trò Hàm (thường là vertex group cằm), Mắt phẳng (tròng mắt nằm riêng một material) hoặc
   Miệng 2D (material có atlas). Bấm **Build Rig**.
2. Dời `LookTarget` để mắt nhìn theo. Key `dt_mouth` trên object miệng, hoặc dùng **Khẩu hình từ âm thanh**.
3. **Engine Export**: Unity tự gắn script cho mắt và miệng.

## 2. Kiểm thử

- `dasktoon_rig_face_test.py` (20 test):
  - vai trò mới;
  - ánh mắt: `LookTarget`, constraint, nhìn theo trong giới hạn, build lại;
  - hàm: các vòng cạnh, há miệng chỉ cằm chạy;
  - mắt phẳng: modifier và driver không cần Python, UV trượt đúng −range × sin góc khi nhìn trái và nhìn lên, range âm,
    build lại, đổi vai trò;
  - miệng 2D: công thức ô, node atlas, `MouthCell` theo `dt_mouth`, build lại, đổi vai trò, material không có texture;
  - panel.
- `dasktoon_rig_mouth_render_test.py`: render EEVEE, `dt_mouth` 0 đến 3 cho đúng màu từng ô.
- `dasktoon_lipsync_test.py` (6 test):
  - giọng tổng hợp: ít nhất 80 % khung đúng nguyên âm, khung im lặng ngậm;
  - 3 phút stereo 48 kHz xử lý dưới 10 giây;
  - key vào clip;
  - nhận tên shape key;
  - không có gì để key thì báo lỗi;
  - lấy strip âm thanh đầu tiên.
- Xuất: rig file phiên bản 2; nhân vật chỉ có mắt phẳng vẫn có rig file; shader có UV Transform; mắt ở tư thế nghỉ
  khi ghi model.
- **Unity thật** `dasktoon_unity_face_test.py`:
  - có hai component đúng xương, đúng renderer;
  - nhìn trái 20° cho độ dịch −0,1 × sin 20°, nhìn lên 10° cho −0,1 × sin 10°, lúc nghỉ bằng 0;
  - scale `MouthCell` 4 thì ô 3;
  - clip có đường cong scale của `MouthCell`.

  Test Unity clips, rig, model, shaders chạy lại: qua.
- Toàn bộ suite CMake: 57 file (550 test) đều qua.

## 3. Ảnh chụp

`docs/superpowers/reports/anime-rig-r3/en|vi/`:

- `50_face_parts.png`: panel Parts với phần Mắt phẳng (Side, Range) và panel con Ánh mắt.
- `51_gaze.png`: mặt ở Material Preview: `LookTarget` phía trước, rồi dời sang trái nhân vật, lưới tròng mắt trượt theo.
- `52_mouth_2d.png`: miệng 2D với `dt_mouth` 0 rồi 1: đổi sang ô khác của atlas.
- `53_lip_sync.png`: hộp thoại Khẩu hình từ âm thanh.

## 4. Quyết định Claude tự chốt (cần xem lại)

1. **Ba chỗ khác spec, ghi trong kế hoạch:**
   - key lip sync vào clip đang dùng;
   - ô miệng sang Unity qua xương `MouthCell`, vì FBX không xuất animation của custom property;
   - shader Unity thêm "UV Transform", vì chúng không dùng tiling/offset của texture.
2. **Mắt phẳng dùng driver thay vì hai xương phụ như spec.** Một UV Warp giữa hai xương dịch U theo +X nhưng V ngược
   +Z, nên không thể cho cả U và V cùng theo ánh mắt. Driver đọc góc xoay của xương mắt (bỏ qua xoắn quanh trục mắt).
3. Hàm: phần của xương hàm ở hai vòng cạnh là 2/3 và 1/3 trước bước dọn weight cho Unity; dọn xong (tối đa 4 xương mỗi
   đỉnh) nó nhích lên khoảng 0,68 đến 0,73.
4. Hàm há bằng cách xoay quanh trục X của xương tối đa 20°. Miệng 2D hiện ô của nguyên âm mạnh nhất khi miệng mở từ 0,15
   trở lên.
5. Tròng mắt hay miệng là mesh riêng (không nằm trên thân) thì bám xương `Head`.
6. **FBX model ghi với mắt ở tư thế nghỉ** (tắt tạm constraint nhìn), khi model không kèm animation. Unity đo góc xoay
   từ tư thế nó nhập; với `LookTarget` mặc định hai mắt hơi chụm 3,4°. Clip vẫn mang ánh mắt.
7. **Importer cho mỗi file clip một mask gồm mọi transform** khi chuyển nó sang Humanoid. Không có mask, Unity bỏ
   đường cong của xương ngoài avatar như `MouthCell`.
8. Unity tính hướng "trái nhân vật" (từ mắt phải sang mắt trái) và "lên" trong khung nghỉ của xương mắt lúc nhập, không
   dựa vào quy ước trục của FBX.
9. Panel con tên **Gaze** (Ánh mắt), không phải "Look", vì bản dịch chung của Blender cho "Look" là Look của Color
   Management.

## 5. Giới hạn

- Trong Unity, "UV Transform" dời mọi texture của material. Vì vậy tròng mắt cần nằm riêng một material, như spec giả
  định; texture khác trong material miệng 2D cũng dời theo atlas.
- Lip sync dựa trên formant nên hợp với giọng rõ, ít nhạc nền. Nguyên âm của giọng thật lệch so với bảng formant chuẩn.
- Model xuất kèm animation mà không có clip: mắt trong model không ở tư thế nghỉ, nên tròng mắt trong Unity lệch nhẹ.

Khi làm (ledger):

- Rà cuối (tự rà, không có reviewer riêng) tìm ra và sửa hai lỗi:
  - xuất một armature ngoài view layer bị lỗi, vì nó không có pose;
  - phần thôi là miệng 2D vẫn giữ node atlas trong material.
- Dự án Unity tạm giữ script phiên bản 5 từ lần chạy trước nên không cài lại importer đã sửa; xóa thư mục Scripts của dự
  án tạm thì chạy đúng. Người dùng thật luôn được cài khi phiên bản tăng.
