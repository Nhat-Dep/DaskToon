# DaskToon: rig anime R1 và R2, báo cáo

- Ngày: 2026-10-06, làm tự động khi người dùng giao "tự động trong 3 tiếng" (từ 16:44), rồi "tiếp tục".
- Nhánh: `dasktoon-anime-rig`, tách từ `dasktoon-project-workflow` (`5857d6a4619`). Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-06-dasktoon-anime-rig-r1.md`, `docs/superpowers/plans/2026-10-06-dasktoon-anime-rig-r2.md`.
- R2 ở đây là phần lắc **trong DaskToon**; phần Unity của R2 (script spring bone C#, file `.rig.json`, spec §9.5) chưa làm.

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
- Toàn bộ bộ test DaskToon trong CMake đều qua: sau R1 là 40 file (370 test), sau R2 là 42 file (392 test), cộng script
  baseline.
- Kiểm tra trong cửa sổ thật (`tools/dasktoon_rig_screenshots.py`): thêm khung qua menu, Build Rig bằng operator cả từ
  viewport lẫn từ Properties editor, tạo dáng, chụp ảnh tiếng Anh và tiếng Việt.

## 3. Ảnh chụp

Trong `docs/superpowers/reports/anime-rig/en/` và `.../vi/`:

| Ảnh | Nội dung |
|---|---|
| `21_add_armature_menu.png` | Add › Armature có **Anime Humanoid** |
| `22_rest.png` | Nhân vật thử nhìn từ bên phải, sau Build Rig |
| `23_posed.png` | Tạo dáng: chuỗi tóc cong ra sau, dải váy trước và sau xòe ra, áo theo ngực |
| `24_rig_panel.png` | Panel Anime Rig trong Object Data của armature, phần váy đang chọn: Parts, Sway, Colliders (đóng), Build |
| `25_sway.png` | R2: hông lướt sang phải từ khung 1 tới 6; ở khung 8 váy còn trễ lại và xòe ngược chiều (Live Sway) |

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

## 6. R2: lắc trong DaskToon

| Phần | Nội dung |
|---|---|
| Bộ giải | `dasktoon_rig/spring.py`: spring bone kiểu VRM bằng numpy thuần (quán tính, Drag, Stiffness kéo về tư thế đang animate, Gravity, giữ chiều dài xương, đẩy đuôi ra khỏi capsule). Viết riêng để sau này dịch y hệt sang C# cho Unity |
| Lắc trực tiếp | `dasktoon_rig/sway.py`: trước khi animation của khung chạy, xương chuỗi về tư thế nghỉ (nên keyframe của người dùng là tư thế gốc, xương không key thì ở rest); sau đó bộ giải bước một nhịp `fps_base / fps` và ghi góc xoay vào xương. Không dùng driver |
| Bộ nhớ đệm | Lưu trạng thái theo khung: quay lại khung đã qua ra đúng như cũ; về khung đầu scene thì hết lắc; nhảy tới thì tính tiếp từ khung gần nhất (tối đa 300 khung). Sửa keyframe, đổi thông số, Build lại thì bỏ bộ nhớ đệm |
| Collider | Build Rig sinh capsule dọc 14 xương thân (Head, Neck, ngực, Spine, Hips, tay, chân); bán kính = 0,9 × khoảng cách trung bình từ xương tới các đỉnh Body theo xương đó |
| Bake Sway | Ghi keyframe xoay cho mọi xương chuỗi trên khoảng khung của scene (thay key xoay cũ của chúng), rồi tắt Live Sway để keyframe phát đúng như lúc xem trực tiếp |
| Giao diện | Panel con **Sway** (Live Sway, Stiffness, Gravity, Drag, Radius của phần tóc/váy đang chọn, Bake Sway) và panel con **Colliders** (đóng sẵn, chỉnh bán kính từng capsule). "Chains" có bản Việt riêng "Số chuỗi" (bản của Blender nghĩa là dây chuyền) |

Kiểm thử R2: `dasktoon_rig_spring_test.py` (8 test), `dasktoon_rig_sway_test.py` (10 test: hông lướt thì váy lắc, về khung đầu
thì hết, quay lại khung ra như cũ, đuôi xương sau khi Blender tính lại khớp với bộ giải tới 1e-4, Live Sway tắt thì không đụng
xương, xương có key là tư thế gốc, đổi thông số bỏ bộ nhớ đệm, Bake khớp lúc xem trực tiếp, Bake hai lần không cộng dồn),
thêm test collider và panel Sway. Toàn bộ suite xem §2.

Quyết định khi làm R2:

- Radius mặc định là hằng số 0,03 m (spec ghi 2% chiều cao khung, gần bằng với nhân vật 1,6 m).
- Chưa thêm **Sway in Unity** (spec §9.1): chưa có phần Unity thì nút này không có tác dụng (quy tắc Phần 1).
- So quaternion lưu bằng float32 với sai số 1e-6.
- Sau khi chụp ảnh: đổi bản dịch "Chains" và tách danh sách collider sang panel con.

Review R2 (tự review): không có lỗi Critical/Important. Để lại (Minor):

- dời object rig mà không đặt key thì bộ nhớ đệm cũ, khung sau giật một nhịp;
- bán kính collider không đổi theo khi scale object rig sau Build;
- render animation vẫn lắc qua handler, nhưng để chắc chắn khi render cuối hay xuất Unity thì nên Bake Sway trước.

Lưu ý cho Unity hiện nay: khi Engine Export xuất animation, lắc trực tiếp cũng chạy trong lúc FBX bake từng khung, nên clip
trong Unity đã có chuyển động lắc (như bake). Script lắc chạy trong Unity là việc của R2b.

## 7. Còn lại

- **R2b**: phần Unity của lắc (spec §9.5): `DaskToonSpringBone.cs`, collider, trình import đọc `<Model>.rig.json`, thuộc
  tính **Sway in Unity**, test bằng Unity 6000.5 (đã có harness).
- **R3 mắt và miệng** (spec §10).
- **A**: tab Animation gọn, tiếp từ phần thiết kế 2 (bộ lọc "cả nhân vật"). Sau đó B, C.
- Nhánh `dasktoon-project-workflow` (Phần 2) vẫn chờ người dùng chọn merge / PR / giữ.
