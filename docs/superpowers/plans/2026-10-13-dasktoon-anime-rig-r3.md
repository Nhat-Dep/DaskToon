# Anime rig R3: mắt và miệng, kế hoạch

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nhân vật dựng bằng Anime Rig có mắt nhìn theo một điểm (mắt cầu xoay xương, mắt phẳng dịch UV), xương hàm,
miệng 2D đổi ô, và lip sync từ file giọng nói; tất cả chạy trong DaskToon và sang Unity.

**Architecture:** Ba vai trò phần mới (Jaw, Flat Eye, 2D Mouth) đi qua Build Rig như các vai trò cũ. Điểm nhìn là xương
`LookTarget` và constraint trên xương mắt. Mắt phẳng là modifier UV Warp giữa hai xương phụ. Miệng 2D là một node group
chọn ô trong material, đọc thuộc tính `dt_mouth` của object; một xương deform không weight `MouthCell` mang số ô sang FBX
qua driver. Lip sync phân tích âm thanh bằng numpy và ghi key vào clip đang dùng. Unity nhận mắt qua chuyển động xương
mắt đã bake, nhận ô miệng qua scale của `MouthCell`; hai script mới đặt thuộc tính UV mới `_DT_UVTransform` của shader
DaskToon.

**Tech Stack:** Python của Blender 5.2 trong DaskToon (bpy, numpy, aud), C# Unity (URP), HLSL shader của DaskToon.

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` mục 10 (R3), mục 11 (cấu trúc code), mục 16
(quyết định đã duyệt). Cập nhật so với spec (ghi lại trong báo cáo):

1. Key lip sync vào **clip đang dùng** của nhân vật (clip spec, B); nhịp anime (C) áp lên chúng như mọi key khác.
2. Bộ xuất FBX không xuất animation của custom property, nên ô miệng sang Unity qua **xương `MouthCell`** (scale Y =
   1 + ô), có driver không cần Python từ `dt_mouth`. Spec ghi "đưa đường cong `dt_mouth` vào clip là việc của B".
3. Shader Unity của DaskToon không dùng `_BaseMap_ST`, nên thêm thuộc tính **`_DT_UVTransform`** (xy tỉ lệ, zw độ
   dịch) cho mọi UV của material; `DaskToonFlatEye.cs` và `DaskToonMouthAtlas.cs` đặt nó bằng MaterialPropertyBlock.

## Global Constraints

- Chỉ dùng thư viện có sẵn trong bản cài: `numpy`, `aud` (đã thử: `aud.Sound(path).data()` cho mảng float32
  (mẫu, kênh)); không scipy.
- FBX xuất với `use_armature_deform_only=True`: xương phải sang Unity thì là xương deform; xương chỉ dùng trong
  DaskToon (`LookTarget`, xương UV) là không deform.
- Xương mắt `LeftEye`, `RightEye` và `Jaw` có sẵn trong khung chuẩn (`skeleton.FACE_BONES`), mắt hướng −Y.
- Chữ gốc tiếng Anh, có bản dịch tiếng Việt; docstring operator một dòng; tên socket hay mục do code tạo được đặt lại
  bằng tiếng Anh ngay sau khi tạo (giao diện tiếng Việt dịch dữ liệu mới).
- Không panel DaskToon trong tab Render hay thanh bên (test `dasktoon_ui_layout_test`).
- Script Unity do Engine Export ghi, GUID cố định, không `.asmdef`; tăng `SCRIPTS_VERSION` (lên 5) và `SHADER_VERSION`
  (lên 2).
- Test dùng thư mục tạm và `DASKTOON_CONFIG_DIR` tạm; không ghi vào dự án Unity trong `D:\Unity\`.
- Build Rig dựng lại được nhiều lần: mỗi lần cho đúng một bộ xương phụ, modifier, node, driver.

## Review Focus

1. **Âm thanh stereo 48 kHz dài** (vài phút): trộn về mono, phân tích theo khung bằng numpy, đủ nhanh (dưới 10 giây
   cho 3 phút âm thanh). Test ở Task 5.
2. **Mesh không có shape key nguyên âm và nhân vật không có Jaw hay 2D Mouth**: lip sync báo lỗi rõ, không ghi gì; chỉ
   có Jaw thì chỉ key Jaw. Test ở Task 5.
3. **Build Rig hai lần, hoặc đổi vai trò của phần**: không nhân đôi `LookTarget`, xương UV, UV Warp, node atlas, driver;
   phần đổi vai trò thì modifier và node cũ của nó bị bỏ. Test ở Task 1, 3, 4.
4. **Material miệng 2D không có Image Texture**: cảnh báo trong kết quả build, không chèn gì. Test ở Task 4.
5. **Clip Humanoid trong Unity giữ đường cong scale của `MouthCell`** (xương ngoài avatar): có binding
   `m_LocalScale.y` trên đường dẫn tới `MouthCell`. Test ở Task 6.

---

## Cấu trúc file

| File | Việc |
|---|---|
| `scripts/modules/dasktoon_rig/parts.py` | Thêm `JAW`, `FLAT_EYE`, `MOUTH_2D` vào `ROLES`; từ khóa đoán vai trò `FLAT_EYE` |
| `scripts/modules/dasktoon_rig/look.py` (mới) | `LookTarget`, constraint nhìn trên xương mắt |
| `scripts/modules/dasktoon_rig/eyes.py` (mới) | Mắt phẳng: xương UV, modifier UV Warp |
| `scripts/modules/dasktoon_rig/mouth.py` (mới) | Node group Mouth Atlas, chèn vào material, `MouthCell` và driver |
| `scripts/modules/dasktoon_rig/lipsync.py` (mới) | Đọc âm thanh, phân tích nguyên âm, ghi key |
| `scripts/modules/dasktoon_rig/build.py` | Gọi look/eyes/mouth; weight Jaw; loại xương phụ khỏi weight thân |
| `scripts/startup/bl_ui/dasktoon_rig.py` | Vai trò mới, thông số phần, giới hạn nhìn |
| `scripts/startup/bl_ui/dasktoon_shape_key_manager.py` | Operator và nút Lip Sync from Audio trong Expression Tools |
| `scripts/modules/dasktoon_export/rig_json.py` | Phiên bản 2: `flatEyes`, `mouths` |
| `scripts/modules/dasktoon_export/unity_urp/*.shader` | `_DT_UVTransform` |
| `scripts/modules/dasktoon_export/unity_scripts/DaskToonFlatEye.cs`, `DaskToonMouthAtlas.cs` (mới), `Editor/DaskToonRigImporter.cs` | Unity |

---

### Task 1: Vai trò mới và điểm nhìn

**Files:**
- Modify: `scripts/modules/dasktoon_rig/parts.py` (ROLES, WORDS), `scripts/startup/bl_ui/dasktoon_rig.py` (ROLE_ITEMS,
  `DaskRigPart`, `DaskRig`, panel phần), `scripts/modules/dasktoon_rig/build.py` (gọi `look.ensure`)
- Create: `scripts/modules/dasktoon_rig/look.py`
- Test: `tests/python/dasktoon_rig_face_test.py` (CMake, danh sách suite)

**Interfaces:**
- Produces:
  - `parts.ROLES = ('FLAT_EYE', 'MOUTH_2D', 'BODY', 'CLOTHING', 'ACCESSORY', 'HAIR', 'SKIRT', 'JAW')`: vai trò sau thắng
    đỉnh, nên mắt phẳng và miệng 2D nằm trên mesh thân vẫn giữ weight thân, còn Jaw thắng thân.
  - `parts.FACE_ROLES = ('FLAT_EYE', 'MOUTH_2D')`.
  - `ROLE_ITEMS` thêm `('JAW', "Jaw", ..., 'MESH_CAPSULE', 5)`, `('FLAT_EYE', "Flat Eye", ..., 'HIDE_OFF', 6)`,
    `('MOUTH_2D', "2D Mouth", ..., 'IMAGE', 7)`.
  - `DaskRigPart`: `eye_side` (`'AUTO'`, `'LEFT'`, `'RIGHT'`), `eye_range` (Float, mặc định 0.1, −1..1),
    `mouth_rows` (Int, 2, 1..8), `mouth_columns` (Int, 4, 1..8).
  - `DaskRig`: `look_yaw_limit` (Float ANGLE, 30°), `look_pitch_limit` (Float ANGLE, 20°).
  - `look.TARGET = "LookTarget"`, `look.FACE_MARK = "dt_face"`, `look.ensure(context, rig) -> bool` (False khi khung
    không có xương mắt), `look.TRACK = "DaskToon Look"`, `look.LIMIT = "DaskToon Look Limit"`.

- [ ] **Step 1: Viết test.** Trong `dasktoon_rig_face_test.py`, dùng `dasktoon_rig_fixtures` (`fx.character()`,
  `fx.rig_for()`, `ui.add_part`, `build.build`):
  - `test_new_roles`: `ROLE_ITEMS` có `JAW`, `FLAT_EYE`, `MOUTH_2D`; `parts.guess_role("Iris_L")` là `'FLAT_EYE'`.
  - `test_look_target`: sau Build Rig có đúng một xương `LookTarget` (không deform, cha `Head`, nằm trước mặt);
    `LeftEye`, `RightEye` có `DaskToon Look` (DAMPED_TRACK tới `LookTarget`, trục Y) và `DaskToon Look Limit`.
  - `test_eyes_follow_within_limits`: dời `LookTarget` sang trái nhân vật (+X) một chút thì đuôi `LeftEye` dời +X;
    dời rất xa thì góc lệch so với hướng nghỉ không quá `look_yaw_limit` + 0,5°.
  - `test_build_twice`: Build Rig hai lần vẫn một `LookTarget`, mỗi xương mắt một constraint mỗi loại; vị trí
    `LookTarget` người dùng đã dời được giữ.
- [ ] **Step 2: Chạy, thấy đỏ.** `bash rt.sh dasktoon_rig_face_test` → ImportError hoặc thiếu vai trò.
- [ ] **Step 3: Code.**
  - `look.ensure`: trong `skeleton.editing`, tạo `LookTarget` nếu chưa có: đầu ở giữa hai đầu xương mắt + (0, −0,5 × h /
    1,6, 0) theo không gian armature (h: chiều cao khung theo `skeleton`), đuôi dài 0,05 × h / 1,6 hướng −Y, cha `Head`,
    `use_deform = False`, `bone[FACE_MARK] = "look"`. Không đánh dấu `build.MARK` (Build không xóa nó).
  - Constraint: tìm theo tên, thiếu thì tạo; DAMPED_TRACK `target = rig`, `subtarget = TARGET`, `track_axis =
    'TRACK_Y'`; LIMIT_ROTATION `owner_space = 'LOCAL'`, `use_limit_x` (dọc) ±`look_pitch_limit`, `use_limit_z` (ngang)
    ±`look_yaw_limit`. `DaskRig.look_*` có update gọi `look.sync_limits(rig)`.
  - `build.build` gọi `look.ensure(context, rig)` sau `_make_bones`.
- [ ] **Step 4: Chạy, thấy xanh;** chạy lại `dasktoon_rig_build_test`, `dasktoon_rig_parts_test`.
- [ ] **Step 5: Commit** `feat: the anime rig's eyes look at a target, within limits`.

### Task 2: Xương hàm

**Files:**
- Modify: `scripts/modules/dasktoon_rig/build.py` (`_paint`), `scripts/modules/dasktoon_rig/parts.py` (`rings`)
- Test: `tests/python/dasktoon_rig_face_test.py`

**Interfaces:**
- Consumes: `parts.ROLES` có `JAW` (Task 1).
- Produces: `parts.rings(edges, vertices, count) -> list[np.ndarray]` (các vòng đỉnh lân cận ngoài `vertices`, vòng 1
  trước); `build.JAW_RINGS = (2 / 3, 1 / 3)`.

- [ ] **Step 1: Viết test** `test_jaw`: phần Jaw là vertex group "Chin" (đỉnh thân gần đuôi `Jaw`); sau Build Rig: đỉnh
  trong phần có weight `Jaw` = 1; vòng 1 có `Jaw` ≈ 2/3, vòng 2 ≈ 1/3 (±0,02), tổng weight mỗi đỉnh = 1; đỉnh xa có
  `Jaw` = 0; xoay `Jaw` 20° thì đỉnh cằm dời xuống, đỉnh trán đứng yên.
- [ ] **Step 2: Chạy, thấy đỏ.**
- [ ] **Step 3: Code.** Trong `_paint`, sau phần Body: với phần `JAW`, xóa weight đỉnh của phần rồi ghi `Jaw` = 1; với
  hai vòng ngoài (chỉ đỉnh thuộc Body), ma trận weight cũ × (1 − w) và cộng w vào cột `Jaw`, w lấy từ `JAW_RINGS`.
  `parts.rings` đi theo cạnh của mesh (dùng `local_edges`).
- [ ] **Step 4: Chạy, thấy xanh;** chạy lại các test rig.
- [ ] **Step 5: Commit** `feat: a Jaw part follows the jaw bone, blended over two rings of edges`.

### Task 3: Mắt phẳng

**Files:**
- Create: `scripts/modules/dasktoon_rig/eyes.py`
- Modify: `scripts/modules/dasktoon_rig/build.py` (gọi `eyes.apply`; dọn modifier cũ)
- Test: `tests/python/dasktoon_rig_face_test.py`

**Interfaces:**
- Consumes: `look.FACE_MARK`, `DaskRigPart.eye_side`, `eye_range` (Task 1).
- Produces: `eyes.MODIFIER_PREFIX = "DaskToon Flat Eye"`; `eyes.side_of(rig, part, vertices) -> 'LEFT' | 'RIGHT'`
  (AUTO: trung bình x trong không gian armature > 0 là trái nhân vật); `eyes.apply(context, rig, parts, owners,
  result)`; xương `LeftEyeUVRest`/`RightEyeUVRest` (cha `Head`) và `LeftEyeUV`/`RightEyeUV` (cha xương mắt,
  `use_inherit_rotation = False`), không deform, `bone[FACE_MARK] = "flat_eye"`.
- Hợp đồng (Unity dùng đúng công thức này ở Task 6): với f là hướng nhìn của xương mắt trong không gian `Head`
  (x: trái nhân vật, z: lên), độ dịch UV của tròng mắt là **(−range × f.x, −range × f.z)**: mắt nhìn sang trái nhân vật
  thì nội dung texture dời sang trái nhân vật trên mặt.

- [ ] **Step 1: Viết test** `test_flat_eye`: phần Flat Eye là một mặt phẳng nhỏ có UV, đặt trước mắt trái (vai trò
  `FLAT_EYE`, `eye_range` 0,1). Sau Build Rig: một modifier `DaskToon Flat Eye <phần>` kiểu UV_WARP giới hạn theo vertex
  group của phần; xoay `LeftEye` để f.x = sin 20° thì UV các đỉnh của phần (đọc từ mesh đã đánh giá) đổi
  −0,1 × sin 20° theo u (±1e-3), v không đổi; nhìn lên 10° thì v đổi −0,1 × sin 10°. Build hai lần vẫn một modifier
  và một cặp xương UV; đổi vai trò phần sang Accessory rồi build thì modifier biến mất.
- [ ] **Step 2: Chạy, thấy đỏ.**
- [ ] **Step 3: Code.** `eyes.apply`: tạo vertex group `DT_FlatEye_<phần>` khi phạm vi không phải vertex group; tạo
  hoặc cập nhật xương UV (đầu `<Side>EyeUV` = đầu xương mắt + hướng nhìn nghỉ × 1, đuôi dài 0,01; `<Side>EyeUVRest`
  trùng vị trí nghỉ); modifier UV_WARP `object_from/to = rig`, `bone_from = <Side>EyeUVRest`, `bone_to = <Side>EyeUV`,
  `vertex_group`, trục và `scale` chọn theo hợp đồng (scale = (range, range), dấu để thỏa test). Dọn mọi modifier có
  tiền tố `MODIFIER_PREFIX` trên các object của phần mà không còn phần Flat Eye tương ứng.
- [ ] **Step 4: Chạy, thấy xanh.**
- [ ] **Step 5: Commit** `feat: a flat eye's iris slides on its UVs as the eye looks around`.

### Task 4: Miệng 2D

**Files:**
- Create: `scripts/modules/dasktoon_rig/mouth.py`
- Modify: `scripts/modules/dasktoon_rig/build.py` (gọi `mouth.apply`; loại xương `FACE_MARK` khỏi weight thân và khỏi
  xương gần nhất của Accessory)
- Test: `tests/python/dasktoon_rig_face_test.py`, `tests/python/dasktoon_rig_mouth_render_test.py` (CMake)

**Interfaces:**
- Produces:
  - `mouth.GROUP = "DaskToon Mouth Atlas"`, `mouth.PROP = "dt_mouth"`, `mouth.CELL_BONE = "MouthCell"`,
    `mouth.NODE_MARK = "dt_mouth_atlas"`.
  - `mouth.CELLS = {"CLOSED": 0, "A": 1, "I": 2, "U": 3, "E": 4, "O": 5}` (quy ước vẽ atlas, ghi trong tooltip).
  - `mouth.cell_uv(uv, cell, rows, columns) -> (u, v)` (Python, cùng công thức với node group và Unity):
    `c = floor(cell + 0.5)`, `col = c mod columns`, `row = floor(c / columns)` (hàng 0 ở trên),
    `u' = (u + col) / columns`, `v' = (v + rows − 1 − row) / rows`.
  - `mouth.apply(context, rig, parts, owners, result)`.
- Driver: `pose.bones["MouthCell"].scale[1]` = `var + 1`, `var` là SINGLE_PROP đọc `["dt_mouth"]` của object phần
  (biểu thức đơn giản, không cần Auto Run). `MouthCell` deform, không weight, cha `Head`.

- [ ] **Step 1: Viết test.**
  - `test_mouth_parts` (`dasktoon_rig_face_test.py`): phần 2D Mouth trên material "Mouth" có Image Texture: sau Build
    Rig, mỗi Image Texture của material có đúng một node atlas (NODE_MARK) trước đầu vào Vector, Rows/Columns theo phần;
    object có `dt_mouth` = 0; có `MouthCell` (deform, không vertex group nào có weight cho nó); đặt `dt_mouth` = 3 rồi cập
    nhật thì scale Y của `MouthCell` đã đánh giá = 4. Build hai lần: vẫn một node mỗi texture, một driver. Material
    không có Image Texture: có cảnh báo trong `result.warnings`, không node nào.
  - `test_cell_uv`: `cell_uv((0.5, 0.5), 5, 2, 4) == (0.375, 0.25)`; ô 0 với 2 × 4 là `(0.125, 0.75)`.
  - `dasktoon_rig_mouth_render_test.py`: mặt phẳng trước camera, material emission đọc atlas 2 × 2 tạo bằng code (bốn
    màu); `dt_mouth` = 0, 1, 2, 3 cho màu điểm giữa ảnh đúng ô (EEVEE nền, ảnh 32 × 32).
- [ ] **Step 2: Chạy, thấy đỏ.**
- [ ] **Step 3: Code.** Node group shader: đầu vào `UV` (vector), `Cell`, `Rows`, `Columns` (float), đầu ra `UV`; tính
  bằng Math và Combine/Separate XYZ theo `cell_uv`. Chèn: nguồn UV cũ của Vector (hoặc node UV Map mới) → group →
  Vector; `Cell` từ node Attribute (OBJECT, `dt_mouth`). Đặt lại tên socket sau khi tạo. Build xóa node có NODE_MARK
  trước khi chèn lại và nối lại nguồn cũ.
- [ ] **Step 4: Chạy, thấy xanh.**
- [ ] **Step 5: Commit** `feat: a 2D mouth shows the cell of its atlas that dt_mouth picks`.

### Task 5: Lip sync từ âm thanh

**Files:**
- Create: `scripts/modules/dasktoon_rig/lipsync.py`
- Modify: `scripts/startup/bl_ui/dasktoon_shape_key_manager.py` (operator `DASKTOON_OT_lip_sync_from_audio`, nút trong
  Expression Tools), bản dịch
- Test: `tests/python/dasktoon_lipsync_test.py` (CMake)

**Interfaces:**
- Consumes: `mouth.PROP`, `mouth.CELLS` (Task 4), phần `JAW` (Task 2), `clips.current` (B).
- Produces:
  - `lipsync.VOWELS = ("A", "I", "U", "E", "O")`; `lipsync.FORMANTS = {"A": (800, 1200), "I": (300, 2300),
    "U": (350, 1300), "E": (500, 1900), "O": (500, 800)}` (Hz).
  - `lipsync.read(path) -> (np.ndarray mono float32, rate)`; `lipsync.analyse(samples, rate, fps) -> list[dict]` mỗi
    khung `{"open": 0..1, "A": .., "I": .., "U": .., "E": .., "O": ..}` (tổng nguyên âm = `open`).
  - `lipsync.vowel_keys(key) -> {vowel: KeyBlock}` theo tên VRM `aa ih ou ee oh`, VRoid `Fcl_MTH_A…`, `A I U E O`,
    `a i u e o`, `あ い う え お`.
  - `lipsync.apply(obj, rig, frames, start_frame, strength=1.0) -> {"shape_keys": n, "jaw": bool, "mouth": bool}`;
    `lipsync.JAW_OPEN = math.radians(20)`.
  - Operator `dasktoon.lip_sync_from_audio`: `filepath` (mặc định file của strip âm thanh đầu tiên trong Sequencer),
    `start_frame` (mặc định khung đầu của strip đó, không có thì khung đầu scene), `strength`.
- Phân tích: mỗi khung một cửa sổ Hann dài 2 / fps giây quanh khung; âm lượng RMS, chuẩn hóa theo phân vị 95; dưới 0,1
  là câm (ngậm). LPC bậc 10 trên tín hiệu đã hạ mẫu về 10 kHz (nội suy) và pre-emphasis 0,97, Levinson–Durbin, nghiệm
  bằng `np.roots`, formant là tần số > 90 Hz với băng thông < 400 Hz, hai cái thấp nhất là F1, F2. Điểm mỗi nguyên âm
  `exp(−((F1 − f1) / 250)² − ((F2 − f2) / 450)²)`, chuẩn hóa tổng 1, nhân `open`; làm mượt trung bình trượt 3 khung.

- [ ] **Step 1: Viết test.**
  - `test_vowels_from_synthetic_voice`: tổng hợp nguyên âm bằng chuỗi xung 120 Hz qua hai bộ cộng hưởng tại F1, F2 của
    từng nguyên âm (0,4 giây mỗi âm, xen 0,2 giây câm), 22 050 Hz; `analyse` ở 24 fps: ≥ 80 % khung của mỗi đoạn có
    nguyên âm lớn nhất đúng; khung câm có `open` < 0,05.
  - `test_stereo_48k_long`: cùng tín hiệu stereo 48 kHz dài 3 phút: chạy dưới 10 giây, số khung = 3 × 60 × 24.
  - `test_apply_keys_into_the_clip`: nhân vật thử có shape key `aa ih ou ee oh`, một clip "Talk": sau `apply`, các
    đường cong `key_blocks["aa"].value`… nằm trong clip "Talk"; có phần Jaw thì có key xoay `Jaw`; có phần 2D Mouth thì
    có key `["dt_mouth"]` mang số ô theo `CELLS`.
  - `test_nothing_to_key`: không shape key nguyên âm, không Jaw, không miệng 2D → operator báo lỗi, không key nào.
  - `test_operator_takes_the_first_sound_strip`: Sequencer có một strip âm thanh bắt đầu ở khung 10 → operator không
    đối số key từ khung 10.
- [ ] **Step 2: Chạy, thấy đỏ.**
- [ ] **Step 3: Code** theo Interfaces. Ghi key bằng `keyframe_insert` với `frame=`; Jaw: `rotation_mode` giữ nguyên,
  xoay quanh trục X cục bộ `open × JAW_OPEN × strength` (dấu để cằm đi xuống); miệng 2D: ô của nguyên âm lớn nhất, câm là
  `CLOSED`, key với nội suy CONSTANT.
- [ ] **Step 4: Chạy, thấy xanh;** thêm chuỗi vào bản dịch, chạy `dasktoon_translations_test`.
- [ ] **Step 5: Commit** `feat: lip sync from a voice file keys the vowels, the jaw and the 2D mouth`.

### Task 6: Unity

**Files:**
- Modify: `scripts/modules/dasktoon_export/rig_json.py` (VERSION 2, `flatEyes`, `mouths`; `rig_data` và `find_rig` có
  dữ liệu khi có chuỗi hoặc mắt phẳng hoặc miệng 2D), `scripts/modules/dasktoon_export/unity_urp/{AnimeBSDF,AnimeCel,
  AnimeEye,DaskCel}.shader`, `shaders_install.py` (SHADER_VERSION 2), `scripts_install.py` (SCRIPTS_VERSION 5, GUID
  mới), `unity_scripts/Editor/DaskToonRigImporter.cs`
- Create: `unity_scripts/DaskToonFlatEye.cs`, `unity_scripts/DaskToonMouthAtlas.cs`
- Test: `tests/python/dasktoon_export_rig_test.py`, `tests/python/dasktoon_unity_face_test.py` (mới),
  `tests/unity/Editor/DaskToonFaceTests.cs` (mới)

**Interfaces:**
- rig json v2: `"flatEyes": [{"object": tên mesh, "material": tên material, "side": "LEFT"|"RIGHT", "range": số}]`,
  `"mouths": [{"object", "material", "rows", "columns", "bone": "MouthCell"}]`. Importer nhận phiên bản 1 và 2.
- Shader: thuộc tính `_DT_UVTransform ("UV Transform", Vector) = (1, 1, 0, 0)`, có trong CBUFFER `UnityPerMaterial`;
  `float2 uv = input.uv0 * _DT_UVTransform.xy + _DT_UVTransform.zw;`.
- `DaskToonFlatEye`: `Transform eye, head; Renderer target; int materialIndex; float range; Vector3 restForward`
  (hướng nghỉ trong không gian head, lấy lúc Awake); `public Vector2 Offset()` theo hợp đồng Task 3; `LateUpdate` đặt
  `_DT_UVTransform = (1, 1, offset)`.
- `DaskToonMouthAtlas`: `Transform cellBone; Renderer target; int materialIndex; int rows, columns`;
  `public int Cell() => round(cellBone.localScale.y − 1)`; `LateUpdate` đặt `_DT_UVTransform` theo `cell_uv`:
  `(1 / columns, 1 / rows, col / columns, (rows − 1 − row) / rows)`.

- [ ] **Step 1: Viết test.**
  - `dasktoon_export_rig_test.py`: rig json v2 có `flatEyes`, `mouths` đúng; nhân vật chỉ có mắt phẳng (không chuỗi) vẫn
    có rig json; hai script mới được cài với GUID cố định; `SCRIPTS_VERSION` = 5, `SHADER_VERSION` = 2.
  - `DaskToonFaceTests.CheckFace` (Unity thật, dự án tạm): model có `DaskToonFlatEye` trên renderer của mặt, đúng mắt,
    material index, range; xoay mắt 20° sang trái nhân vật thì `Offset().x` ≈ −range × sin 20°; có `DaskToonMouthAtlas`;
    đặt scale Y của `MouthCell` = 4 thì `Cell()` = 3; clip `Model@Talk.fbx` có binding `m_LocalScale.y` trên đường dẫn
    tới `MouthCell`; shader DaskToon biên dịch không lỗi.
  - `dasktoon_unity_face_test.py` xuất nhân vật thử (Flat Eye, 2D Mouth, Jaw, clip Talk) và chạy `CheckFace`.
- [ ] **Step 2: Chạy, thấy đỏ.**
- [ ] **Step 3: Code** theo Interfaces; importer tìm renderer theo tên object, material index theo tên material (không
  thấy thì 0), xương theo tên.
- [ ] **Step 4: Chạy, thấy xanh;** chạy lại test Unity rig, model, shaders, clips.
- [ ] **Step 5: Commit** `feat: flat eyes and the 2D mouth work in Unity`.

### Task 7: Giao diện, ảnh, báo cáo

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (thông số theo vai trò: Flat Eye → Side, Range; 2D Mouth → Rows,
  Columns, ghi chú quy ước ô; panel con Look với hai giới hạn), bản dịch
- Create: ảnh trong `docs/superpowers/reports/anime-rig-r3/en|vi/`, báo cáo
  `docs/superpowers/reports/2026-10-13-dasktoon-anime-rig-r3-report.md`

- [ ] **Step 1: Viết test** (panel): `tu.draw` panel phần với phần Flat Eye có `eye_side`, `eye_range`; với 2D Mouth có
  `mouth_rows`, `mouth_columns`; panel Look có hai giới hạn.
- [ ] **Step 2: Chạy, thấy đỏ; code; chạy, thấy xanh;** `dasktoon_translations_test`, `dasktoon_ui_layout_test`.
- [ ] **Step 3: Ảnh** (en, vi): panel phần với vai trò mới; viewport mắt nhìn theo `LookTarget`; miệng 2D đổi ô; nút
  Lip Sync trong Expression Tools.
- [ ] **Step 4: Toàn bộ suite CMake, test Unity; báo cáo** (gồm ba cập nhật so với spec ở đầu kế hoạch).
- [ ] **Step 5: Commit** `docs: the anime rig R3 report, with screenshots of eyes, mouth and lip sync`.
