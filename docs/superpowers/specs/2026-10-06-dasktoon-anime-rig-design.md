# DaskToon: rig anime (R)

- Ngày: 2026-10-06
- Trạng thái: hướng làm và thiết kế do Claude tự chốt khi người dùng giao "tự động trong 3 tiếng" (2026-10-06 16:44).
  Các câu hỏi trước đó người dùng đã trả lời trong chat (§16). Người dùng duyệt lại spec này khi quay lại.
- Nhánh: `dasktoon-anime-rig`, tách từ `dasktoon-project-workflow` (`5857d6a4619`, Phần 2 chưa merge)
- Lộ trình hoạt hình: **R (rig) → A (tab Animation gọn) → B (clip cho Unity) → C (nhịp anime + bộ lọc hành động nhanh)**.
  Spec này chỉ là R. Ba kế hoạch nối tiếp: R1 → R2 → R3.

## 1. Mục tiêu

Người dùng tự dựng nhân vật anime trong DaskToon (không lấy từ VRoid hay Mixamo) và muốn rig nhanh, không phải học hết
công cụ rig của Blender. Ba việc khó nhất với họ: vẽ weight; tóc, váy, phụ kiện; mắt và miệng kiểu anime.

Kết quả mong muốn:

1. **Khung xương chuẩn có sẵn.** Thêm một bộ xương người đặt tên theo Unity Humanoid / VRM, khớp sẵn với chiều cao
   nhân vật. Người dùng chỉ chỉnh vị trí khớp (đối xứng trái phải).
2. **Rig theo vai trò của từng phần.** Người dùng nói phần nào là thân, quần áo, phụ kiện, tóc, váy; DaskToon tự sinh
   xương phụ và tự vẽ weight. Phần có thể là cả một object, một material, hay một vùng chọn, nên dùng được cho nhân vật
   tách nhiều object lẫn nhân vật gộp một mesh.
3. **Tóc, váy lắc tự nhiên** (R2) ở cả hai nơi: xem trước và bake trong DaskToon, và một script spring bone chạy trong
   Unity với cùng thông số.
4. **Mắt và miệng anime** (R3): mắt nhìn theo một điểm (mắt cầu xoay bằng xương, mắt phẳng dịch UV), miệng có xương
   hàm, lip sync từ file giọng nói, miệng vẽ 2D đổi hình, và nối vào shape key và controller sẵn có.
5. **Không cần add-on hay package ngoài**, không dùng driver kiểu script (driver bắt bật Auto Run Python Scripts, xem
   Phần 1 §5).

## 2. Phạm vi

**Trong phạm vi** (chia ba kế hoạch):

- **R1, khung và weight:** khung xương chuẩn và lệnh thêm; dữ liệu phần và vai trò; sinh chuỗi xương tóc và váy; weight
  theo vai trò; dọn weight cho Unity; giao diện trong Properties; Engine Export xuất Humanoid khi có khung chuẩn.
- **R2, lắc:** thông số lắc theo phần; collider tự sinh từ thân; mô phỏng trong DaskToon (xem trước, bộ nhớ đệm, bake);
  script spring bone C# và trình import cài vào dự án Unity; file mô tả rig xuất cạnh FBX.
- **R3, mắt và miệng:** điểm nhìn và xương mắt; mắt phẳng dịch UV; vùng hàm; lip sync từ âm thanh; miệng 2D theo bảng
  ô; các script Unity tương ứng.

**Ngoài phạm vi:**

- IK, FK/IK switch, control rig kiểu Rigify (tab Animation và việc tạo dáng nằm ở A).
- Tự nhận khớp từ hình mesh (người dùng tự kéo khớp; DaskToon chỉ khớp theo chiều cao).
- Import VRM/VRoid, xuất file `.vrm`.
- Vật lý vải thật (cloth sim) cho váy; váy dùng chuỗi xương lắc.
- Clip, Animator Controller, đưa đường cong thuộc tính tùy biến vào clip Unity: thuộc B.

## 3. Khái niệm

| Từ | Nghĩa |
|---|---|
| Khung chuẩn | Armature có đủ 15 xương bắt buộc của Unity Humanoid với đúng tên (§4.2) |
| Phần (part) | Một tập đỉnh của một mesh: cả object, các mặt mang một material, hoặc một vertex group |
| Vai trò | Cách phần được rig: Body, Clothing, Accessory, Hair, Skirt (R3 thêm Jaw, Flat Eye, 2D Mouth) |
| Mảnh | Một khối đỉnh nối liền nhau (loose part) trong một phần |
| Chuỗi | Dãy xương sinh tự động cho một mảnh tóc hoặc một dải váy, gắn vào một xương của khung |
| Dựng rig (Build) | Lệnh sinh lại mọi chuỗi và vẽ lại weight của mọi phần |
| Xương sinh | Xương do Build tạo, mang custom property `dt_part` = tên phần |

## 4. Khung xương chuẩn (R1)

### 4.1 Hình dáng

- **55 xương**, tên `PascalCase` đúng tên `HumanBodyBones` của Unity (cũng là tên VRM viết hoa chữ đầu). Trái/phải
  bằng tiền tố `Left`/`Right`, nên Flip Names và X-Axis Mirror của Blender hiểu được.
- Thân: `Hips` → `Spine` → `Chest` → `UpperChest` → `Neck` → `Head` → `LeftEye`, `RightEye`, `Jaw`.
- Tay (mỗi bên): `UpperChest` → `LeftShoulder` → `LeftUpperArm` → `LeftLowerArm` → `LeftHand` → 5 ngón × 3 đốt
  (`LeftThumbProximal/Intermediate/Distal`, `LeftIndex…`, `LeftMiddle…`, `LeftRing…`, `LeftLittle…`).
- Chân (mỗi bên): `Hips` → `LeftUpperLeg` → `LeftLowerLeg` → `LeftFoot` → `LeftToes`.
- **T-pose**, mặt nhìn về −Y, bên trái nhân vật ở +X, chân chạm z = 0. Tỉ lệ nhân vật anime khoảng 6,5 đầu (đầu cao
  0,15 chiều cao). Khuỷu hơi lùi ra sau, gối hơi đưa ra trước, để IK sau này biết hướng gập.
- Mắt hướng ra trước; `Jaw` từ dưới tai chéo xuống cằm.
- Bảng tọa độ nằm trong code (`dasktoon_rig/skeleton.py`), tính theo chiều cao 1, rồi nhân với chiều cao nhân vật.

### 4.2 Xương bắt buộc

`Hips`, `Spine`, `Head`, `LeftUpperArm`, `LeftLowerArm`, `LeftHand`, `RightUpperArm`, `RightLowerArm`, `RightHand`,
`LeftUpperLeg`, `LeftLowerLeg`, `LeftFoot`, `RightUpperLeg`, `RightLowerLeg`, `RightFoot`: đủ 15 xương này thì armature
là **khung chuẩn**, kể cả khi người dùng xóa ngón, mắt, hàm hay các xương tùy chọn khác.

### 4.3 Thêm khung

- **Add › Armature › Anime Humanoid** (`dasktoon.rig_add_humanoid`, nối vào `VIEW3D_MT_armature_add`, nên Add hiện
  menu con Armature).
- Đang chọn mesh thì khung khớp với chúng: chiều cao = chiều cao hộp bao (world) của các mesh, chân ở đáy hộp, tâm
  X/Y ở tâm hộp. Không chọn mesh: cao 1,6 m, đặt tại 3D cursor.
- Các mesh đang chọn thành **phần** của rig (§5.3, đoán vai trò theo tên).
- Armature mới: `show_in_front`, bật **X-Axis Mirror** khi sửa khớp, được chọn và active. Thông báo: "Fit the joints in
  Edit Mode, then press Build Rig in Properties › Object Data".
- **Fit to Parts** (panel con Joints): khớp lại khung theo các mesh của phần; thay vị trí khớp hiện có (hỏi xác
  nhận); không tạo lại xương người dùng đã xóa; không dời object armature (mesh đã gắn không bị kéo theo).

## 5. Phần và vai trò (R1)

### 5.1 Dữ liệu

Trên dữ liệu armature: `bpy.types.Armature.dasktoon_rig` (PropertyGroup `DaskRig`):

| Thuộc tính | Kiểu | Ý nghĩa |
|---|---|---|
| `parts` | Collection `DaskRigPart` | Các phần |
| `active_part_index` | Int | Dòng đang chọn trong danh sách |

`DaskRigPart`:

| Thuộc tính | Kiểu | Mặc định | Ý nghĩa |
|---|---|---|---|
| `name` | String | tên object | Tên phần, cũng là tiền tố tên xương sinh |
| `object` | Pointer Object (chỉ mesh) | | Mesh chứa phần |
| `scope` | Enum `OBJECT` / `MATERIAL` / `VERTEX_GROUP` | `OBJECT` | Cả object, các mặt mang material, hay vertex group |
| `material` | String | | Tên material khi `scope = MATERIAL` |
| `vertex_group` | String | | Tên vertex group khi `scope = VERTEX_GROUP` (đỉnh có weight > 0) |
| `role` | Enum | đoán theo tên | `BODY`, `CLOTHING`, `ACCESSORY`, `HAIR`, `SKIRT` |
| `bone` | String | rỗng = tự động | Xương gắn: Hair → `Head`, Skirt → `Hips`, Accessory → xương gần tâm phần nhất |
| `bone_count` | Int 1–12 | 4 (Skirt 3) | Số xương mỗi chuỗi |
| `chain_count` | Int 3–24 | 8 | Số dải quanh váy |

Phần lưu theo tên material và tên vertex group, nên đổi tên material/group thì phần mất chỗ dựa; Build báo lỗi đúng tên.

### 5.2 Vai trò

| Vai trò | Rig thế nào |
|---|---|
| **Body** | Weight tự động (bone heat của Blender) theo các xương Deform của rig, trừ xương sinh, `LeftEye`, `RightEye`, `Jaw` (tạm tắt Deform trong lúc tính) |
| **Clothing** | Chép weight từ bề mặt Body gần nhất: điểm gần nhất trên tam giác Body, nội suy theo tọa độ trọng tâm |
| **Accessory** | Cứng: toàn bộ weight 1 cho một xương (kính, kẹp tóc, mắt cầu gắn `LeftEye`/`RightEye`) |
| **Hair** | Mỗi mảnh dài thành một chuỗi `bone_count` xương gắn vào `bone`; mảnh ngắn/bè (mũ tóc) thành Accessory trên `bone` |
| **Skirt** | `chain_count` dải quanh trục đứng, mỗi dải `bone_count` xương gắn vào `bone` |

Một đỉnh thuộc nhiều phần: vai trò sau thắng theo thứ tự Body < Clothing < Accessory < Hair < Skirt (cụ thể thắng chung);
cùng vai trò thì phần đứng sau trong danh sách thắng.

### 5.3 Đoán vai trò

Theo tên object (hoặc tên material với phần theo material), không phân biệt hoa thường, bỏ dấu tiếng Việt trước khi so
(`Tóc` → `toc`), khớp từ khóa:

| Vai trò | Từ khóa |
|---|---|
| Hair | `hair`, `bang(s)`, `fringe`, `ponytail`, `twintail(s)`, `tail(s)`, `ahoge`, `braid`, `toc`, `kami`, `髪` |
| Skirt | `skirt`, `vay`, `スカート` |
| Accessory | `eye(s)`, `eyeball`, `glass(es)`, `ribbon`, `hairpin`, `clip`, `earring`, `hat`, `cap`, `bow`, `目` |
| Clothing | `cloth(es)`, `shirt`, `tshirt`, `jacket`, `coat`, `dress`, `pant(s)`, `shoe(s)`, `sock(s)`, `glove(s)`, `uniform`, `服` |
| Body | `body`, `skin`, `face`, `head`, `体` |

Không khớp từ nào: mesh cao nhất (hộp bao) là Body nếu rig chưa có Body, còn lại là Clothing. So khớp theo từ (tách theo
ký tự không phải chữ cái và theo chỗ đổi chữ thường sang hoa), nên `Hat` không làm `Chatty` thành Accessory. Từ tiếng
Việt ngắn dễ trùng (`ao`, `mat`, `than`, `quan`) không dùng. Vai trò khớp trước trong bảng thắng.

## 6. Dựng rig (R1)

Lệnh **Build Rig** (`dasktoon.rig_build`) chạy trong Object Mode, làm lại từ đầu mỗi lần, và là một bước undo.

### 6.1 Kiểm tra trước

Báo lỗi và **không đổi gì** khi: armature không phải khung chuẩn (liệt kê xương thiếu); armature hoặc mesh đang ẩn; không
có phần; phần trỏ tới
object không còn hoặc không phải mesh; material/vertex group của phần không có trên mesh hoặc không có đỉnh nào; có
Clothing mà không có Body; mesh dùng chung dữ liệu với mesh khác (weight nằm trên dữ liệu mesh); mesh hoặc armature link
từ thư viện.

### 6.2 Các bước

1. Xóa mọi xương sinh của lần trước (xương có `dt_part`).
2. Sinh chuỗi Hair và Skirt (§6.3, §6.4) trong Edit Mode của armature; mỗi xương sinh mang `dt_part`, Deform bật, cha
   là xương gắn.
3. Mỗi mesh có phần: thêm modifier Armature trỏ tới rig nếu chưa có; làm con của rig (giữ nguyên vị trí) nếu chưa.
4. Vẽ weight theo vai trò (§5.2), ghi đè weight cũ của các đỉnh thuộc phần, theo các xương của rig. Vertex group không
   trùng tên xương (vd. vertex group làm phần) không bị đụng.
5. Dọn weight trên mọi đỉnh đã vẽ: bỏ weight < 0,01, giữ 4 weight lớn nhất (Unity mặc định 4 xương mỗi đỉnh), chuẩn
   hóa tổng = 1.
6. Báo cáo: "Built N bones in M chains, weights on K objects", kèm cảnh báo (§12).

Mọi tọa độ tính ở **tư thế nghỉ** (rest): tọa độ đỉnh gốc (không shape key, không modifier) nhân `matrix_world`, xương
theo `matrix_local` của rig.

### 6.3 Chuỗi tóc

Cho mỗi mảnh của phần Hair:

1. Mảnh có dưới 4 đỉnh, hoặc **bè** (độ trải theo trục chính PCA < 1,5 × độ trải theo trục thứ hai, vd. mũ tóc) thành
   Accessory trên xương gắn.
2. **Gốc**: các đỉnh có khoảng cách tới đoạn thẳng của xương gắn ≤ `dmin + 10% (dmax − dmin)`: phần tóc nằm sát đầu, theo
   hẳn xương gắn.
3. **Khoảng cách trắc địa** từ gốc, đi theo cạnh mesh (Dijkstra). Chiều dài mảnh L = khoảng cách lớn nhất.
4. **Khớp** k = 0…N (N = `bone_count`): khớp 0 là tâm các đỉnh gốc nằm ở mép vùng gốc (có cạnh nối ra ngoài); khớp k là
   tâm các đỉnh có khoảng cách trong khoảng k·L/N ± L/(4N); khớp N là tâm 5% đỉnh xa nhất; khoảng trống thì nội suy từ
   hai khớp bên cạnh.
5. **Weight**: u = d/L·N. Xương thứ j (1…N) đạt đỉnh ở u = j, xương gắn đạt đỉnh ở u = 0; weight hình nón
   `max(0, 1 − |u − tâm|)`. Gốc dính hẳn vào đầu, đuôi theo xương cuối.
6. **Tên**: một mảnh: `<Phần>_<k>`; nhiều mảnh: `<Phần><i>_<k>`, mảnh đánh số theo X từ phải nhân vật (−X) sang trái
   (+X).

### 6.4 Chuỗi váy

1. Trục đứng qua tâm (X, Y) của phần; đỉnh trên z_top, đáy z_bot.
2. Dải c (0…C−1) ở góc θ_c = −90° + 360°·c/C: dải 0 ở chính giữa phía trước (−Y), đánh số ngược chiều kim đồng hồ nhìn
   từ trên (sang trái nhân vật trước).
3. Khớp k = 0…N ở độ cao z_k = z_top − k·(z_top − z_bot)/N, bán kính = bán kính trung bình của đỉnh trong cung ±180°/C
   quanh θ_c và dải cao ±Δz/2 (không có đỉnh thì lấy vòng đầy đủ ở độ cao đó).
4. Weight: chia cho hai dải gần nhất theo góc (tuyến tính), nhân với weight hình nón theo u = (z_top − z)/(z_top −
   z_bot)·N như tóc; xương gắn (`Hips`) đạt đỉnh ở u = 0.
5. Tên: `<Phần><c+1>_<k>`.

## 7. Giao diện (R1)

Theo quy tắc Phần 1: thiết lập theo dữ liệu nằm trong tab Properties của dữ liệu đó, tạo đối tượng trong menu Add, không
có panel DaskToon ở thanh bên viewport.

### 7.1 Properties › Object Data của armature: panel **Anime Rig**

Panel cha `DATA_PT_dasktoon_rig` "Anime Rig" (chỉ khi object active là armature), ba panel con `_joints`, `_parts`,
`_build`:

- **Joints** (không gọi là Skeleton vì Blender đã có panel Skeleton): dòng trạng thái (khung chuẩn, hoặc "Missing
  bones: …"); **Edit Joints** (vào Edit Mode, bật X-Axis Mirror); **Fit to Parts**.
- **Parts**: UIList các phần (icon theo vai trò, tên, object); nút **Add Selected Meshes** (mỗi mesh đang chọn thành một
  phần cả object), **Add Material Part** (chọn material trong các material của object phần đang chọn), Remove. Dưới danh
  sách: thiết lập của phần đang chọn: Object, Scope, Material/Vertex Group (ô tìm theo dữ liệu của mesh), Role, Bone
  (ô tìm theo xương của rig, rỗng = Automatic), Bones per Chain (Hair, Skirt), Chains (Skirt).
- **Build**: nút **Build Rig**; ghi chú "Build replaces the weights of every part".

### 7.2 Properties › Object Data của mesh: panel **Anime Rig**

Chỉ hiện khi mesh là phần của một rig, hoặc scene có khung chuẩn. Liệt kê các phần trên mesh này (vai trò, phạm vi) và
nút **Add Part from Selection** (Edit Mode: tạo vertex group `DT_<tên>` từ các đỉnh đang chọn và một phần
`VERTEX_GROUP`). Rig được tìm theo: rig có phần trên mesh này → modifier Armature → cha → khung chuẩn duy nhất trong
scene; vẫn không rõ thì lệnh hỏi chọn rig.

## 8. Unity cho R1

- Engine Export xuất FBX như hiện nay; xương sinh là xương Deform nên có trong FBX.
- **Humanoid**: khi armature xuất đi là khung chuẩn, `.meta` của model ghi `animationType: 3` (Humanoid) thay vì 2;
  `autoGenerateAvatarMappingIfUnspecified: 1` đã có, nên Unity tự ghép xương theo tên. Armature không chuẩn giữ Generic.
- Weight đã ≤ 4 xương mỗi đỉnh, khớp `maxBonesPerVertex: 4` trong `.meta`.

## 9. Lắc (R2)

### 9.1 Thông số

Thêm vào `DaskRigPart` (chỉ Hair và Skirt có): **Stiffness** (0–4, mặc định 1), **Gravity** (0–2, 0,2), **Drag** (0–1,
0,4), **Radius** (bán kính va chạm của mỗi khớp, mặc định 2% chiều cao khung), **Sway in Unity**: `RUNTIME` (script Unity
tính lại, mặc định) hoặc `BAKED` (dùng keyframe đã bake).

### 9.2 Collider

Build sinh collider trên khung: cầu ở `Head`; capsule dọc `Chest`, `UpperChest`, `Hips`, `LeftUpperLeg`,
`LeftLowerLeg`, `LeftUpperArm`, `LeftLowerArm` và bên phải. Bán kính = trung bình khoảng cách từ các đỉnh Body có weight
lớn nhất ở xương đó tới đoạn xương, × 0,9. Lưu trên `DaskRig.colliders` (xương, bán kính), chỉnh được trong panel con
**Sway** của Anime Rig; vẽ nét mảnh trong viewport khi panel Sway mở.

### 9.3 Thuật toán (giống hệt hai nơi)

Theo spring bone của VRM 0.x, bước thời gian cố định 1/fps. Mỗi xương chuỗi giữ vị trí đuôi hiện tại và trước đó:

```
next = cur + (cur − prev)·(1 − drag) + hướng_nghỉ·stiffness·dt + (0, 0, −1)·gravity·dt
next = head + normalize(next − head)·length          (giữ chiều dài)
mỗi collider: đẩy next ra ngoài (radius + bán kính collider), rồi giữ chiều dài lần nữa
xoay xương từ hướng nghỉ sang (next − head)
```

`hướng_nghỉ` là hướng của xương theo tư thế đã animate (keyframe của người dùng), nên lắc cộng thêm vào động tác.

### 9.4 Trong DaskToon

- Handler `frame_change_post` (handler của DaskToon, không phải driver): khung tăng 1 thì tính một bước; về khung đầu
  scene thì đặt lại; nhảy khung thì lấy từ **bộ nhớ đệm** theo khung, thiếu thì tính tiếp từ khung đã có gần nhất.
- Bộ nhớ đệm bỏ khi thông số, collider, khung xương hay animation của rig đổi.
- **Live Sway** (bật/tắt trên rig, mặc định bật).
- **Bake Sway**: ghi keyframe quay cho xương chuỗi trên khoảng khung của scene vào action đang dùng, thay key cũ của các
  xương đó trong khoảng; phần `RUNTIME` vẫn bake được để render trong DaskToon.

### 9.5 Trong Unity

- Engine Export cài vào `Assets/DaskToon/Scripts/` (GUID cố định, file phiên bản như shader):
  `Runtime/DaskToonSpringBone.cs`, `Runtime/DaskToonSpringCollider.cs`, `Editor/DaskToonRigImporter.cs`
  (`AssetPostprocessor`), kèm `.asmdef` cho Runtime và Editor.
- Mỗi model có rig ghi thêm `<Model>.rig.json` cạnh FBX: phiên bản, các chuỗi (tên xương theo thứ tự, thông số, chế độ
  Unity), các collider; tọa độ đổi sang hệ Unity.
- Lúc import, `DaskToonRigImporter.OnPostprocessModel` đọc file json cạnh FBX và gắn component vào prefab của model, nên
  kéo model vào scene là lắc.
- Khi xuất, chuỗi `RUNTIME` được tắt lắc trong lúc bake animation của FBX (để Unity không lắc hai lần); chuỗi `BAKED` giữ
  keyframe và Unity không gắn script cho chuỗi đó.

## 10. Mắt và miệng (R3)

### 10.1 Điểm nhìn

- Build thêm xương `LookTarget` (không Deform, con của `Head`, trước mặt một khoảng 0,5 m × tỉ lệ) và constraint Damped
  Track trên `LeftEye`/`RightEye` hướng vào nó, kèm Limit Rotation (±30° ngang, ±20° dọc, chỉnh được).
- Người dùng animate `LookTarget` (hoặc xoay thẳng xương mắt). FBX bake animation lấy tư thế đã tính constraint, nên
  Unity nhận chuyển động mắt dù không có constraint.
- **Mắt cầu**: phần Accessory gắn `LeftEye`/`RightEye` (đã chạy từ R1).

### 10.2 Mắt phẳng (dịch UV)

- Vai trò **Flat Eye** (phần theo material hoặc vertex group, tròng mắt nằm riêng một material), thông số **Range** (UV
  dịch tối đa) và **Side** (Left/Right).
- Trong DaskToon: modifier UV Warp trên mesh, giới hạn bằng vertex group của phần, từ xương phụ `LeftEyeUVRest` (con của
  `Head`) tới `LeftEyeUV` (con của `LeftEye`, đặt trước mắt, không kế thừa xoay); khoảng đặt xương và Scale của modifier
  chọn sao cho độ dịch = (sin yaw, sin pitch) × Range.
- Trong Unity: `DaskToonFlatEye.cs` đọc góc xoay của xương mắt mỗi khung và đặt độ dịch texture của material tròng mắt
  (MaterialPropertyBlock) theo cùng công thức.

### 10.3 Miệng

- **Vai trò Jaw**: phần (thường là vertex group cằm, hàm dưới) được weight 1 cho `Jaw`, viền làm mềm qua 2 vòng cạnh,
  phần còn lại theo `Head`.
- **Lip sync từ âm thanh** (`dasktoon.lip_sync_from_audio`, ở Shape Keys › Expression Tools): chọn file âm thanh (mặc
  định strip âm thanh đầu tiên của Sequencer), đọc mẫu bằng `aud`, mỗi khung tính âm lượng và formant F1/F2 (LPC bằng
  numpy), chấm độ giống 5 nguyên âm A I U E O, làm mượt, câm thì ngậm miệng. Ghi keyframe vào: shape key nguyên âm (tên
  VRM `aa ih ou ee oh`, VRoid `Fcl_MTH_A…`, hoặc `A I U E O` như preset AIUEO), xương `Jaw` nếu có phần Jaw, ô miệng 2D
  nếu có phần 2D Mouth. Chỉ dùng thư viện có sẵn trong bản cài.
- **Vai trò 2D Mouth**: material của phần nhận node group **DaskToon Mouth Atlas** (lưới ô hàng × cột, chọn ô theo số
  nguyên); số ô là custom property `dt_mouth` trên object, animate được, node Attribute (Object) đọc nó, không cần driver.
  Unity: `DaskToonMouthAtlas.cs` có trường `cell` animate được trong clip; đưa đường cong `dt_mouth` vào clip là việc
  của B.
- **Nối vào cái có sẵn**: controller AIUEO và Expression Preview vẫn điều khiển shape key như cũ; lip sync và shape key
  dùng chung tên nguyên âm.

## 11. Cấu trúc code

| File | Nội dung |
|---|---|
| `scripts/modules/dasktoon_rig/__init__.py` | |
| `scripts/modules/dasktoon_rig/skeleton.py` | Bảng 55 xương, `REQUIRED`, `missing_bones`, `is_humanoid`, `create_humanoid`, `fit` |
| `scripts/modules/dasktoon_rig/parts.py` | Vai trò, đoán vai trò, đỉnh của phần, mảnh (loose part), xương gắn tự động |
| `scripts/modules/dasktoon_rig/chains.py` | Toán thuần numpy: khoảng cách trắc địa, khớp và weight của chuỗi tóc, váy |
| `scripts/modules/dasktoon_rig/weights.py` | Bone heat, chép weight từ Body, weight cứng, ghi weight chuỗi, dọn weight |
| `scripts/modules/dasktoon_rig/build.py` | Kiểm tra, sinh chuỗi, gắn modifier, vẽ weight, báo cáo |
| `scripts/startup/bl_ui/dasktoon_rig.py` | PropertyGroup, operator, panel, mục menu Add |
| R2: `dasktoon_rig/spring.py`, `dasktoon_export/unity_scripts/*.cs`, `dasktoon_export/rig_json.py` | Mô phỏng, script Unity, file mô tả rig |
| R3: `dasktoon_rig/look.py`, `dasktoon_rig/lipsync.py`, `dasktoon_rig/mouth.py` | Điểm nhìn, lip sync, miệng 2D |

Module thư viện không import `bl_ui`; giao diện gọi thư viện. Toán chuỗi nhận mảng numpy để test không cần mesh thật.

## 12. Trường hợp đặc biệt và lỗi

| Trường hợp | Xử lý |
|---|---|
| Bone heat không tìm được nghiệm cho một số đỉnh Body | Các đỉnh đó lấy weight theo xương gần nhất (khoảng cách tới đoạn xương); cảnh báo số đỉnh |
| Mesh có modifier khác trước Armature (Mirror, Subdivision…) | Weight tính trên mesh gốc; modifier Armature được đặt sau Mirror nếu có, trước các modifier còn lại |
| Mesh có scale âm hoặc scale không đều | Vẫn chạy (tính ở world); cảnh báo nên Apply Scale trước khi xuất Unity |
| Mảnh tóc quá ít đỉnh (< 4) | Thành Accessory trên xương gắn |
| Váy không bao quanh trục (một mảnh vạt) | Vẫn chia dải theo góc; dải không có đỉnh nào thì không sinh |
| Tên phần trùng hoặc có ký tự lạ | Tên xương lấy phần chữ/số của tên phần; trùng thì thêm số |
| Người dùng tự sửa weight sau Build | Build lần sau ghi đè (ghi chú trong panel) |
| Đang ở Edit/Pose Mode | Build tự về Object Mode rồi trả lại mode cũ |

## 13. Bản dịch

Mọi chữ mới (panel, lệnh, thuộc tính, mục enum, thông báo) có bản tiếng Việt trong `dasktoon_translations.py`; test bản
dịch quét module mới. Tên xương không dịch.

## 14. Kiểm thử

Test nền (`--background --factory-startup`), đăng ký trong `tests/python/CMakeLists.txt`:

- `dasktoon_rig_skeleton_test.py`: 55 xương đúng tên và cha; đối xứng trái phải; chiều cao và vị trí theo hộp bao;
  `missing_bones`, `is_humanoid`; X-Axis Mirror bật.
- `dasktoon_rig_chains_test.py`: dải tóc thẳng và cong cho khớp theo thứ tự từ gốc tới đuôi, nằm trên dải; weight
  tổng 1, gốc theo xương gắn, đuôi theo xương cuối; mảnh ngắn thành cứng; váy hình nón cho đúng số dải, góc, bán kính.
- `dasktoon_rig_build_test.py`: nhân vật thử (thân trụ, áo, tóc, váy, phụ kiện; và cùng nhân vật gộp một mesh theo
  material/vertex group): xương sinh đúng tên; mọi đỉnh ≤ 4 weight, tổng 1; áo theo thân; Build lần hai không nhân đôi
  xương; lỗi (§6.1) không đổi gì; đỉnh thuộc hai phần theo thứ tự vai trò.
- `dasktoon_rig_ui_test.py`: panel vẽ đúng lệnh theo trạng thái; menu Add có Anime Humanoid; Add Part from Selection tạo
  vertex group và phần.
- Engine Export: `.meta` Humanoid khi khung chuẩn, Generic khi không.
- R2, R3 thêm test của mình (mô phỏng xác định: cùng đầu vào cho cùng kết quả; json; lip sync trên âm tổng hợp).

## 15. Build và nhánh

- R1 chỉ có Python: đồng bộ bản cài bằng `tools/dasktoon_sync_build.py`, không cần build C++.
- Mỗi task một commit trên `dasktoon-anime-rig`; không push, không merge khi người dùng chưa chọn.

## 16. Nhật ký quyết định

Người dùng trả lời trong chat (2026-10-06):

- Làm rig trước tab Animation, vì nhân vật tự dựng trong DaskToon.
- Một spec chung R1, R2, R3, ba kế hoạch nối tiếp.
- Khó nhất: weight; tóc, váy, phụ kiện; muốn có mắt và miệng anime.
- Nhân vật cả hai kiểu: nhiều object và một mesh gộp.
- Lắc ở cả DaskToon và Unity.
- Mắt cả hai kiểu: phẳng (dịch UV) và cầu (xoay xương).
- Miệng: xương hàm, lip sync từ giọng, miệng 2D, nối vào shape key và controller có sẵn.
- Khung chuẩn của DaskToon theo tên Unity Humanoid / VRM.

Claude tự chốt khi người dùng giao "tự động trong 3 tiếng":

1. **Hướng 1**: công cụ Python và dữ liệu animate được, không driver; spring bone viết bằng Python, chuyển sang C++ sau
   nếu chậm. Lý do: không phụ thuộc add-on/package ngoài, cùng một thuật toán hai nơi.
2. Phần lưu trên armature (một danh sách, một lệnh Build), panel chính ở Object Data của armature; mesh chỉ có panel nhỏ
   cho Add Part from Selection. Lý do: quy tắc Phần 1 cấm panel ở thanh bên viewport, và Build cần thấy mọi phần.
3. Vai trò thắng theo thứ tự cụ thể > chung, không theo thứ tự danh sách. Lý do: dễ đoán, không phụ thuộc thứ tự thêm.
4. Chuỗi tóc theo khoảng cách trắc địa trên mesh, không theo trục chính. Lý do: theo được lọn tóc cong.
5. Váy theo góc và độ cao quanh trục đứng. Lý do: đơn giản, đúng cho váy loe và váy ống.
6. Xuất Humanoid ngay ở R1 (đổi `animationType`). Lý do: đó là lý do có khung chuẩn; Unity tự ghép theo tên.
7. Tóc dạng mũ (ngắn, bè) thành cứng thay vì sinh chuỗi vô nghĩa; người dùng tách lọn bằng phần vertex group.
8. File mô tả rig `<Model>.rig.json` thay vì custom property trong FBX. Lý do: FBX của Blender không xuất custom property
   có animation, và json dễ đọc, dễ đổi phiên bản.

## 17. Rủi ro

| Rủi ro | Giảm |
|---|---|
| Bone heat lỗi với mesh hở, mesh nhiều mảnh | Rơi về xương gần nhất cho đỉnh thiếu weight, báo số đỉnh |
| Khung đặt theo hộp bao lệch với nhân vật tư thế A | Người dùng kéo khớp (X-Axis Mirror); Unity tự ép T-pose khi dựng Avatar |
| Unity không tự ghép Humanoid nếu người dùng đổi tên xương | `is_humanoid` kiểm tra đúng tên; không đủ thì xuất Generic như cũ |
| Mô phỏng Python chậm với rig lớn | Bộ nhớ đệm theo khung; tách riêng `spring.py` để chuyển sang C++ |
| Hai bản thuật toán (Python, C#) lệch nhau | Test so kết quả vài bước với số liệu cố định ghi trong test cả hai phía |
