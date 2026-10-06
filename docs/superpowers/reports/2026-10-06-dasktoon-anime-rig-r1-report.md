# DaskToon: rig anime R1, báo cáo

- Ngày: 2026-10-06, làm tự động khi người dùng giao "tự động trong 3 tiếng" (từ 16:44).
- Nhánh: `dasktoon-anime-rig`, tách từ `dasktoon-project-workflow` (`5857d6a4619`). Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-06-dasktoon-anime-rig-r1.md`.

## 1. Đã làm được gì

R1 là phần khung xương và weight của rig anime:

| Phần | Nội dung |
|---|---|
| Khung xương chuẩn | **Add › Armature › Anime Humanoid**: 55 xương đúng tên `HumanBodyBones` của Unity (Hips, Spine, Chest, UpperChest, Neck, Head, mắt, hàm, vai, tay, 15 đốt ngón mỗi tay, chân), T-pose, mặt nhìn −Y. Đang chọn mesh thì khung khớp theo chiều cao của chúng và các mesh thành **phần** của rig. X-Axis Mirror bật sẵn để chỉnh khớp hai bên cùng lúc |
| Phần và vai trò | Mỗi phần là cả object, các mặt mang một material, hay một vertex group. Vai trò: **Body** (weight tự động), **Clothing** (chép weight từ bề mặt Body gần nhất), **Accessory** (gắn cứng vào một xương, tự chọn xương gần nhất, mắt cầu tự gắn `LeftEye`/`RightEye`), **Hair** (mỗi lọn dài một chuỗi xương gắn `Head`), **Skirt** (8 dải quanh `Hips`). Vai trò đoán theo tên (hair, tóc, skirt, váy, eye, shirt, body…) |
| Build Rig | Sinh chuỗi tóc và váy, gắn modifier Armature (đặt sau Mirror nếu có), làm con của rig mà không làm mesh nhảy chỗ, vẽ weight theo vai trò, rồi dọn weight cho Unity: tối đa 4 xương mỗi đỉnh, bỏ weight dưới 0,01, tổng bằng 1. Bấm lại bao nhiêu lần cũng được: xương sinh cũ bị thay, không nhân đôi |
| Giao diện | Properties › Object Data của armature: panel **Anime Rig** với ba panel con **Joints** (trạng thái khung, Edit Joints, Fit to Parts), **Parts** (danh sách, thêm mesh đang chọn, thêm phần theo material, thiết lập phần), **Build** (Build Rig). Object Data của mesh: panel **Anime Rig** liệt kê phần trên mesh đó và **Add Part from Selection** (Edit Mode) |
| Unity | Engine Export ghi `animationType: 3` (Humanoid) khi model có đúng một khung chuẩn, Unity tự ghép xương theo tên; không phải khung chuẩn thì vẫn Generic như cũ |
| Tiếng Việt | Mọi chữ mới có bản dịch (70 mục) |

Cách dùng, 4 bước:

1. Chọn các mesh của nhân vật, **Add › Armature › Anime Humanoid**.
2. **Edit Joints**, kéo khớp cho khớp với thân (hai bên đối xứng).
3. Xem lại vai trò trong **Parts**; nhân vật gộp một mesh thì thêm phần theo material, hoặc chọn đỉnh rồi
   **Add Part from Selection**.
4. **Build Rig**, chuyển sang Pose Mode để thử.

## 2. Kiểm thử

- 6 file test mới (`dasktoon_rig_*_test.py`, 68 test) và test xuất Humanoid; đăng ký trong `tests/python/CMakeLists.txt`.
- Toàn bộ 40 bộ test DaskToon trong CMake đều qua (370 test, cộng script baseline), chạy lại sau bản sửa của bước review.
- Kiểm tra trong cửa sổ thật (`tools/dasktoon_rig_screenshots.py`): thêm khung qua menu, Build Rig bằng operator cả từ
  viewport lẫn từ Properties editor, tạo dáng, chụp ảnh tiếng Anh và tiếng Việt.

## 3. Ảnh chụp

Trong `docs/superpowers/reports/anime-rig/en/` và `.../vi/`:

| Ảnh | Nội dung |
|---|---|
| `21_add_armature_menu.png` | Add › Armature có **Anime Humanoid** |
| `22_rest.png` | Nhân vật thử nhìn từ bên phải, sau Build Rig |
| `23_posed.png` | Tạo dáng: chuỗi tóc cong ra sau, dải váy trước và sau xòe ra, áo theo ngực |
| `24_rig_panel.png` | Panel Anime Rig trong Object Data của armature |

## 4. Quyết định Claude tự chốt

Thiết kế (người dùng chưa duyệt, cần xem lại spec §16):

1. Hướng làm: công cụ Python và dữ liệu animate được, không driver; spring bone (R2) viết Python, chuyển C++ sau nếu chậm.
2. Phần lưu trên armature, panel chính ở Object Data của armature; mesh chỉ có panel nhỏ cho Add Part from Selection.
3. Một đỉnh thuộc nhiều phần: vai trò cụ thể thắng (Body < Clothing < Accessory < Hair < Skirt).
4. Chuỗi tóc đi theo khoảng cách trắc địa trên mesh (theo được lọn cong); phần tóc nằm sát đầu theo hẳn `Head`; mảnh bè
   (mũ tóc) thành cứng.
5. Váy chia dải theo góc và độ cao quanh trục đứng.
6. Xuất Humanoid ngay ở R1.
7. Panel con đặt tên **Joints** (không trùng panel Skeleton/Pose của Blender).

Khi làm (ledger):

- Nhân vật thử có ống thân quay pháp tuyến vào trong, khiến bone heat của Blender chọn xương tay, chân thay vì xương sống;
  đã sửa dữ liệu test (code không đổi).
- Test áo bỏ `Head` khỏi danh sách cấm: weight `Head` ở cổ áo là weight thân ở độ cao đó.
- Test giao diện: chạy nền phải cập nhật view layer trước khi đọc `selected_objects`; PropertyGroup đã đăng ký không có
  trong `bpy.types`.
- Danh sách phần có tên hiển thị "Parts"; tên vertex group tạo trước khi gọi (quy tắc quét bản dịch).
- Thêm test xuất thật vào thư mục tạm để kiểm phần nối `humanoid` trong Engine Export.

## 5. Review cuối

Tự review (phiên này không tạo subagent khi người dùng chưa yêu cầu), nên yếu hơn một reviewer độc lập.

- **Đã sửa** (Important): phần Hair/Skirt chọn xương gắn là xương do Build sinh ra làm Build hỏng giữa chừng. Nay Build
  báo lỗi trước khi đổi gì ("bone … is made by Build Rig; pick a bone of the skeleton").
- **Để lại** (Minor):
  - bấm Fit to Parts trong Edit Mode thì armature về Object Mode;
  - chưa cảnh báo mesh có scale âm hay không đều (spec §12), dù kết quả vẫn đúng vì mọi tính toán ở world;
  - danh sách phần lặp tên object khi trùng tên phần;
  - mesh quay pháp tuyến vào trong cho weight tự động kém mà không có cảnh báo (giống Parent › With Automatic Weights
    của Blender).

## 6. Còn lại

- **R2 lắc** (spec §9): thông số lắc, collider, mô phỏng spring bone trong DaskToon (xem trước, bake), script Unity.
- **R3 mắt và miệng** (spec §10).
- **A**: tab Animation gọn, tiếp từ phần thiết kế 2 (bộ lọc "cả nhân vật"). Sau đó B, C.
- Nhánh `dasktoon-project-workflow` (Phần 2) vẫn chờ người dùng chọn merge / PR / giữ.
