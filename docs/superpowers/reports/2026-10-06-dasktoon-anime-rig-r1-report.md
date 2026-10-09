# DaskToon: rig anime R1, R2, R2b và constraint Spring, báo cáo

- Ngày: 2026-10-06, làm tự động khi người dùng giao "tự động trong 3 tiếng" (từ 16:44), rồi "tiếp tục".
- Nhánh: `dasktoon-anime-rig`, tách từ `dasktoon-project-workflow` (`5857d6a4619`). Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md`. Kế hoạch:
  `docs/superpowers/plans/2026-10-06-dasktoon-anime-rig-r1.md`, `...-r2.md` (lắc trong DaskToon), `...-r2b.md` (lắc trong
  Unity).

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
- Toàn bộ bộ test DaskToon trong CMake đều qua: sau R1 là 40 file (370 test), sau R2 là 42 file (392 test), sau R2b là 43
  file (404 test), cộng script baseline. Test Unity (ngoài CMake, chạy Unity 6000.5.4f1 thật): rig mới, model, shader đều
  qua.
- Kiểm tra trong cửa sổ thật (`tools/dasktoon_rig_screenshots.py`): thêm khung qua menu, Build Rig bằng operator cả từ
  viewport lẫn từ Properties editor, tạo dáng, chụp ảnh tiếng Anh và tiếng Việt.

## 3. Ảnh chụp

Trong `docs/superpowers/reports/anime-rig/en/` và `.../vi/`:

| Ảnh | Nội dung |
|---|---|
| `21_add_armature_menu.png` | Add › Armature có **Anime Humanoid** |
| `22_rest.png` | Nhân vật thử nhìn từ bên phải, sau Build Rig |
| `23_posed.png` | Tạo dáng: chuỗi tóc cong ra sau, dải váy trước và sau xòe ra, áo theo ngực (từ §8 xương chuỗi màu xanh: Blender tô như vậy xương có constraint) |
| `24_rig_panel.png` | Panel Anime Rig trong Object Data của armature, phần váy đang chọn: Parts, Sway, Colliders (đóng), Build |
| `25_sway.png` | R2: hông lướt sang phải từ khung 1 tới 6; ở khung 8 váy còn trễ lại và xòe ngược chiều (Live Sway; từ §8 là constraint Spring) |
| `26_spring_constraint.png` | §8: tab Bone Constraints của xương `Hair_2`, constraint Spring do Build Rig gắn, với thông số và collider |

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

  Cả bốn đã sửa ngày 2026-10-10: `docs/superpowers/reports/2026-10-10-dasktoon-minor-fixes-report.md`.

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

## 7. R2b: lắc trong Unity

| Phần | Nội dung |
|---|---|
| Lắc trong Unity | Mỗi phần tóc/váy có **Sway in Unity**: **Runtime** (mặc định, script của DaskToon cho lắc khi game chạy) hoặc **Baked** (Unity phát keyframe lắc đã bake) |
| File rig | Engine Export ghi `<Model>.rig.json` cạnh FBX: mỗi chuỗi (tên xương, độ dài, Stiffness, Gravity, Drag, Radius, chế độ Unity), mỗi collider (xương, bán kính, độ dài). Không cần tọa độ: đã thử trong Unity, trục +Y của xương sau khi import vẫn chỉ dọc xương như Blender |
| Script Unity | Cài vào `Assets/DaskToon/Scripts/` như shader (GUID cố định, file phiên bản, không ghi đè bản mới hơn): `DaskToonSpringBone.cs` (bản dịch từng dòng của `spring.py`), `DaskToonSpringCollider.cs`, `Editor/DaskToonRigImporter.cs` (lúc Unity import FBX, đọc json và gắn component vào prefab của model, nên kéo model vào scene là lắc) |
| FBX | Lúc ghi FBX, chuỗi Runtime về tư thế nghỉ và không lắc (Unity tự lắc), chuỗi Baked giữ lắc; ghi xong mọi thứ trở lại. Chuỗi Runtime mà đã có key lắc (Bake Sway) thì báo cáo cảnh báo "Unity would sway it twice" |
| Báo cáo, README | Dòng "Rig: … (DaskToon spring bones sway the hair and skirts in Unity)", trạng thái script; README của bản xuất ra thư mục dặn chỉ đưa thư mục Scripts vào một project Unity một lần |

Kiểm thử R2b: test Python của file rig, cài script, xuất (10 test trong `dasktoon_export_rig_test.py`, thêm test lắc/panel),
và **test trong Unity thật** `tests/python/dasktoon_unity_rig_test.py`: Unity biên dịch ba script, trình import gắn 9 spring
bone và 14 collider, xương con nằm trên trục +Y của xương cha (lệch 1,5e-8), và sau 20 bước đuôi xương trong Unity lệch so
với `spring.py` **9,4e-7 m**. Thử với kỳ vọng cố ý sai (Gravity +0,5) thì test báo lỗi (lệch 15 mm), nên test có tác dụng.

Ghi chú khi làm R2b:

- Project Unity tạm của harness (`%TEMP%\dasktoon_unity_test`) bị hỏng bộ nhớ gói (thiếu file `.meta`, NUnit bị bỏ qua, mọi
  test Unity lỗi biên dịch). Đã xóa `Library` của project tạm để Unity dựng lại; project của người dùng không bị đụng.
- `runtime_parts` ban đầu tính cả phần Body; test bắt được, đã sửa.
- Trình import chỉ phụ thuộc vào file rig khi file có thật.

Review R2b (tự review):

- **Đã sửa** (Important): bản xuất ra thư mục của hai nhân vật kéo vào cùng project Unity sẽ có hai bản các lớp C# và cả
  project không biên dịch được (shader trùng chỉ cảnh báo). README nay dặn chỉ đưa thư mục Scripts vào một lần; xuất thẳng
  vào project Unity hoặc dùng dự án DaskToon thì không gặp.
- **Để lại** (Minor): khi game tạm dừng (`Time.deltaTime = 0`) tóc còn trôi vài khung theo quán tính rồi mới đứng; thêm file
  rig sau mà không xuất lại thì Unity không tự import lại model. Cả hai đã sửa ngày 2026-10-10 (báo cáo sửa lỗi nhỏ).

## 8. Constraint Spring (C++)

- Ngày: 2026-10-10, sau khi người dùng duyệt (spec §16 "Người dùng duyệt (2026-10-10)": chuyển spring bone sang C++ ngay,
  thành một constraint mới trong depsgraph), làm tự động.
- Nhánh: `dasktoon-spring-constraint`, tách từ `dasktoon-master` (`240f2531ddf`). Chưa push, chưa merge.
- Kế hoạch: `docs/superpowers/plans/2026-10-10-dasktoon-spring-constraint.md` (spec §9.4 viết lại).

| Phần | Nội dung |
|---|---|
| Loại constraint mới | **Spring** (`CONSTRAINT_TYPE_SPRING`, `bSpringConstraint`): Stiffness, Gravity, Drag, Radius và danh sách **Colliders** (một xương của armature và bán kính). Lưu vào file, chép theo object, Python tạo được (`colliders.new()`, `colliders.clear()`, `clear_cache()`). Panel trong tab Bone Constraints, panel con Colliders; có tiếng Việt |
| Cách tính | Cùng công thức với `spring.py` và script Unity: quán tính, kéo về hướng đang tạo dáng, trọng lực, giữ chiều dài xương, đẩy đuôi ra khỏi capsule. Depsgraph tính constraint cùng tư thế, nên tua, render, xuất FBX đều có lắc mà không cần bake. Xương collider là target nên depsgraph tính chúng trước |
| Bộ nhớ đệm | Theo object và xương, mỗi khung một trạng thái kèm vị trí đầu xương và hướng của nó: cùng khung, cùng đầu vào thì ra như cũ; khung đầu scene luôn bắt đầu lại; đầu vào đổi (sửa key, dời rig) thì bắt đầu lại tại khung đó, không giật; khung mới tính tiếp từ khung gần nhất trước nó (tối đa 300 khung); thời điểm giữa hai khung (motion blur) đi tiếp từ khung nguyên trước đó theo vận tốc mà không đụng bộ nhớ đệm. Đổi thông số thì bỏ bộ nhớ đệm của object |
| Bán kính theo scale | Bán kính của constraint và collider theo đơn vị armature, nhân scale của object: scale rig ×2 thì khoảng cách tới collider ×2. Build Rig ghi bán kính collider theo đơn vị armature; `rig.json` nhân scale nên Unity vẫn nhận mét |
| Rig anime | Build Rig gắn constraint `DaskToon Spring` vào mọi xương chuỗi, thông số theo phần, collider theo rig. Đổi thông số hay Live Sway trong panel Sway thì constraint đổi theo (tắt Live Sway là mute). Bỏ các handler khung hình Python. Bake Sway ghi key từ tư thế constraint cho ra; Engine Export mute constraint của chuỗi Runtime trong lúc ghi FBX |

Ba Minor của R2 hết theo: dời rig không còn giật, bán kính đổi theo scale, render có lắc không cần bake.

Kiểm thử: `dasktoon_spring_constraint_test.py` (13 test: tạo, lưu rồi mở lại, chép, panel và bản dịch, khớp `spring.py` tới
1e-4 qua 12 khung, khung đầu, tua lại, đầu vào đổi, khung lẻ, mute và đổi thông số, collider đẩy ra, bán kính theo scale, không
còn handler); `dasktoon_rig_sway_test.py` viết lại (13 test) theo hướng xương thay cho góc xoay; test collider theo đơn vị
armature; test xuất (mute lúc ghi FBX, bán kính trong `rig.json` theo scale). Toàn bộ suite CMake: 44 file
(419 test) đều qua, cộng script nạp module; test Unity (rig, model, shader) qua.

Quyết định khi làm (ledger):

- Bản object đã tính (evaluated) có session UID 0, nên khóa bộ nhớ đệm dùng UID của bản gốc. Nếu không, mọi rig trùng tên
  xương dùng chung bộ nhớ đệm và `clear_cache()` không xóa được gì. Test bắt được.
- Khung đầu scene luôn bắt đầu lại (kế hoạch giữ khung đầu đã tính, làm lịch sử cũ còn sót).
- Build ghi bán kính collider thẳng vào ID property, rồi đồng bộ constraint một lần ở cuối (qua RNA thì 14 bán kính là 14
  lần đồng bộ cả rig).
- Mô tả bán kính collider của rig thêm "in armature units".
- Rig dựng trước thay đổi này chưa có constraint: bấm Build Rig lại, hoặc đổi một thông số lắc (ví dụ tắt rồi bật Live
  Sway), là có.
- Nhảy cóc nhiều khung: constraint bước từng xương k lần với đầu xương của khung cuối, còn `spring.py` bước cả chuỗi cùng
  nhau, nên kết quả hơi khác; phát tuần tự thì khớp.

Review (tự review):

- **Đã sửa** (Important): khung lẻ khi render có motion blur được làm tròn thành khung nguyên và ghi vào bộ nhớ đệm với đầu
  xương của khung lẻ; tới khung nguyên thật thì đầu vào khác nên lắc bắt đầu lại, render có motion blur gần như không lắc.
  Nay khung lẻ đi tiếp từ khung nguyên trước đó theo vận tốc và không ghi gì (test `test_subframes_leave_the_cache_alone`).
- **Để lại** (Minor): bộ nhớ đệm không xóa khi xóa object (vài chục byte mỗi xương mỗi khung, mất khi thoát); phát ngược thì
  không lắc (lắc chỉ tính tới).

## 9. Còn lại

- Các Minor còn lại và cảnh báo scale âm/không đều: đã sửa (`docs/superpowers/reports/2026-10-10-dasktoon-minor-fixes-report.md`).
- Tiếp: **A**, tab Animation gọn (tiếp từ phần thiết kế 3), rồi **R3** mắt và miệng (spec §10), B, C.
