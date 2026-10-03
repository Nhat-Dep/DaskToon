# DaskToon: Engine Export sang Unity 6 URP và Dự án DaskToon (Dự án 2)

- Ngày: 2026-10-03
- Trạng thái: chờ duyệt
- Phụ thuộc: Dự án 1 (`docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`, mục 8 là hợp đồng giữa hai
  dự án). Nhánh `dasktoon-unity-export` tách ra từ `dasktoon-shading-outline`.
- Làm theo **hai giai đoạn**:
  - **A. Engine Export:** export model, material và shader sang Unity.
  - **B. Dự án DaskToon:** một dự án gồm nhiều model, gắn với một project Unity. Giai đoạn B dùng lại A.

## 1. Mục tiêu

- **A:** chạy một lệnh *Engine Export*, kéo thư mục kết quả vào Unity 6 (URP 17.5), hoặc ghi thẳng vào project Unity, là có
  ngay nhân vật với material **giống render EEVEE của DaskToon nhiều nhất có thể**. Không phải gán material hay thông số bằng tay.
- **B:** làm việc theo dự án. Một thư mục chứa các file `.blend` của cùng một dự án được gắn với một project engine. Shader
  được cài vào project đó một lần, và mọi lần export sau đi thẳng vào project đó.

Tiêu chí theo thứ tự ưu tiên:
1. **Giống node nhất có thể:** cùng công thức, cùng thông số, cùng texture.
2. **Tự động:** không có bước làm tay trong Unity, ngoài việc kéo thư mục (chỉ khi không ghi thẳng vào project).
3. **Phù hợp cho game:** outline được vẽ trong shader nên không nhân đôi mesh; các module tắt thì không tốn chi phí.

## 2. Phạm vi

**Trong phạm vi**
- **A:**
  - Operator *Engine Export*: chọn engine, xuất model FBX, xuất material và shader, đích là thư mục hoặc project Unity.
  - Bộ chuyển đổi material (đọc graph, map giá trị, copy texture, bake, texture dải màu), chuẩn bị dữ liệu outline.
  - Ghi `.mat`, `.meta` (cả `.meta` của FBX có gán material), cài và cập nhật shader, báo cáo.
  - Shader URP cho **Anime BSDF, Anime Cel (kèm lớp Angel Ring của mẫu tóc), Anime Eye, Dask Cel**. Mỗi shader có pass
    outline với màu nét theo Dask Outline.
- **B:**
  - Tạo dự án, nhận diện dự án từ vị trí file `.blend`.
  - File `dasktoon_project.json`, cài shader khi tạo dự án.
  - Panel *DaskToon › Dự án*, danh sách dự án gần đây.
  - Engine Export tự dùng đích của dự án.
- Test headless trong DaskToon, và test trong Unity 6000.5 ở chế độ batchmode trên một project tạm.

**Ngoài phạm vi**
- Unreal và Godot (có trong danh sách engine nhưng ghi "sắp có"), Built-in RP, HDRP, Unity 7 (thêm lớp adapter sau).
- Model dạng glTF hoặc VRM.
- Các node khác (Manga, nhóm vật liệu, Face Shadow, Anime Rim đứng riêng), node group, Mix Shader.
- Giá trị có keyframe hoặc driver (lấy giá trị ở frame hiện tại).
- Đèn, camera và thiết lập scene.
- Độ dày outline cố định theo pixel màn hình.
- **Dự án:** export hàng loạt mọi model, nhiều engine trong một dự án, template dự án, đổi tên hoặc di chuyển dự án.

## 3. Luồng sử dụng

**Giai đoạn A, khi không có dự án:**
1. Vào *File › Export › Engine Export…* mở trình chọn thư mục của Blender, kèm bảng tùy chọn:
   ```
   Engine:   [Unity 6 (URP) ▾]       (Unreal 5, Godot 4: "sắp có")
   Model:    [FBX ▾]                 (FBX / Không xuất model)
             ☑ Chỉ object đang chọn  ☑ Kèm animation
   Material: ☑ Xuất material và shader
             Bake: [1024] px  [16] sample
   ```
2. Exporter chạy `dasktoon.outline_prepare_game_data` cho các mesh có outline, rồi ghi ra đích (mục 4).
3. Hiện báo cáo, gồm cả cường độ đèn gợi ý.
4. Nếu đích là thư mục bình thường thì kéo thư mục `<Tên>_Unity` vào cửa sổ Project của Unity. Nếu đích là project Unity
   thì chỉ cần chuyển sang Unity, Unity sẽ tự import.
5. Đặt Directional Light trong Unity theo gợi ý: **cường độ = Sun strength ÷ π**. Ambient lấy đúng bằng màu World.

**Giai đoạn B, theo dự án:**
1. Vào *File › Dự án DaskToon › Tạo dự án…*, nhập tên, thư mục dự án, engine và đường dẫn project Unity. Lệnh này tạo
   thư mục, ghi `dasktoon_project.json`, cài shader vào project Unity, và lưu file `.blend` hiện tại vào thư mục dự án nếu
   người dùng chọn.
2. Mọi file `.blend` nằm trong thư mục dự án (kể cả trong thư mục con) thuộc dự án đó. Khi mở *Engine Export*, đích và
   engine được điền sẵn theo dự án.
3. Panel *DaskToon › Dự án* có danh sách model, nút **Mở**, **Export model này** và **Cài lại shader**.

## 4. Đích export và bố cục file

**Nhận diện project Unity:** đi ngược lên từ thư mục được chọn, tìm thư mục chứa cả `Assets/` và `ProjectSettings/`.
Nếu tìm thấy thì dùng chế độ **PROJECT**, không thì dùng chế độ **FOLDER**.

| Chế độ | Gốc ghi file | Shader |
|---|---|---|
| PROJECT | `<Project Unity>/Assets/DaskToon/` | Ghi vào `Shaders/` khi chưa có hoặc khi phiên bản cũ hơn |
| FOLDER | `<thư mục chọn>/<Tên>_Unity/` | Luôn ghi vào `Shaders/` |

Bố cục bên trong gốc ghi file (giống nhau ở cả hai chế độ):
```
Shaders/   DaskToonCore.hlsl, DaskToonURP.hlsl, DaskToonOutline.hlsl,
           AnimeBSDF.shader, AnimeCel.shader, AnimeEye.shader, DaskCel.shader,
           DaskToonShaders.version
<Tên>/Model/       <Tên>.fbx
<Tên>/Materials/   <material>.mat
<Tên>/Textures/    <material>_<input>.png|.exr, <material>_Ramp.png
README.txt         chỉ có ở chế độ FOLDER: cách dùng và cường độ đèn
```
- `<Tên>` là tên file `.blend` (bỏ đuôi). Nếu file chưa lưu thì dùng `Untitled`.
- Mọi file đều có `.meta` đi kèm, thư mục cũng có `.meta` (`folderAsset: yes`).
- Ở chế độ FOLDER, kéo thư mục của nhân vật thứ hai vào cùng project sẽ làm Unity báo trùng GUID shader. Material vẫn
  chạy đúng, và README hướng dẫn dùng chế độ PROJECT hoặc Dự án để tránh việc này.

**GUID**
- Shader: hằng số cố định trong code, nên mọi lần export đều trỏ tới cùng một bộ shader.
- Model, material, texture: `md5("dasktoon:<Tên>:<đường dẫn tương đối>")`. Export lại sẽ ghi đè đúng asset cũ. Báo cáo
  nhắc rằng chỉnh sửa tay trên các asset này trong Unity sẽ bị ghi đè.

**`DaskToonShaders.version`:** file chứa phiên bản shader (số nguyên, ban đầu là 1). Ở chế độ PROJECT và khi cài shader
cho dự án, shader chỉ được ghi khi file này không có, hoặc phiên bản trong đó nhỏ hơn phiên bản của DaskToon.

**FBX**
- Gọi `export_scene.fbx` với:
  - `use_mesh_modifiers=False` (giữ shape key, không đưa lớp vỏ outline vào FBX);
  - `axis_forward='-Z'`, `axis_up='Y'`, `apply_scale_options='FBX_SCALE_ALL'`;
  - `add_leaf_bones=False`, `use_armature_deform_only=True`, `mesh_smooth_type='FACE'`;
  - `bake_anim` theo tùy chọn "Kèm animation";
  - `object_types` gồm Armature, Mesh và Empty.
- Báo cáo liệt kê các mesh còn modifier khác ngoài Armature và DaskToon Outline, vì modifier đó không được áp dụng.
- **`.meta` của FBX** (ModelImporter):
  - `externalObjects` gán mỗi material theo tên tới file `.mat` đã xuất, với
    `{type: UnityEngine:Material, assembly: UnityEngine.CoreModule}` và `{fileID: 2100000, guid, type: 2}`;
  - nhập blend shape và normal của blend shape;
  - normal theo kiểu Import, tangent theo kiểu Calculate MikkTSpace;
  - `importAnimation` theo tùy chọn.
  - Giá trị số của các enum được xác nhận bằng bài test import trong Unity.

**`.mat`:** YAML theo định dạng Material `serializedVersion: 8` của Unity, gồm:
- `m_Shader {fileID: 4800000, guid, type: 3}` và `m_ValidKeywords` (đã sắp xếp).
- `m_CustomRenderQueue`: −1, hoặc 3000 nếu Transparent.
- `stringTagMap` (RenderType), và `disabledShaderPasses` (ghi `SRPDefaultUnlit` khi outline tắt).
- `m_SavedProperties` (`m_TexEnvs`, `m_Ints`, `m_Floats`, `m_Colors`).

**Màu:** Blender lưu linear, còn property kiểu Color trong Unity lưu sRGB. Writer đổi linear sang sRGB bằng hàm piecewise
chuẩn, dùng được cả với giá trị lớn hơn 1. Project Unity phải ở Linear color space (mặc định của URP); báo cáo có nhắc.

**`.meta` của texture** (TextureImporter):

| Loại | sRGB | Loại texture | Wrap | Filter | Mipmap | Nén |
|---|---|---|---|---|---|---|
| Màu (copy hoặc bake) | 1 | Default | Repeat | Bilinear | Có | High Quality |
| Số liệu (mask, ngưỡng) | 0 | Default | Repeat | Bilinear | Có | Không nén |
| Normal map | 0 | Normal map | Repeat | Bilinear | Có | High Quality |
| Dải màu | 1 | Default | Clamp | Point nếu CONSTANT, còn lại Bilinear | Không | Không nén |

**Texture dải màu:** ảnh PNG 256×1, pixel *i* lấy `ColorRamp.evaluate((i + 0.5) / 256)`.

## 5. Bộ chuyển đổi trong DaskToon (giai đoạn A)

**Vị trí code**
- Thư viện: `scripts/modules/dasktoon_export/` (thuần Python, test được độc lập).
- Giao diện: `scripts/startup/bl_ui/dasktoon_engine_export.py` (operator `export_scene.dasktoon_engine`, mục menu
  *File › Export › Engine Export…*).
- Nguồn shader Unity: `scripts/modules/dasktoon_export/unity_urp/`. Thư mục này được cài đặt cùng các script.

| Module | Trách nhiệm |
|---|---|
| `targets.py` | `ExportTarget(engine, mode, root, name)`: nhận diện project Unity, tính gốc ghi file, nhớ và đọc đích đã dùng của từng file `.blend` (`scene["dasktoon_engine_target"]`) |
| `shaders_install.py` | `install_shaders(target) -> bool`: ghi shader, `.meta` và file phiên bản; không ghi nếu đã cập nhật |
| `model_fbx.py` | Gọi FBX exporter và ghi `.meta` của FBX |
| `node_maps.py` | Bảng map cho mỗi node: input → property Unity, enum → float, cờ module → keyword |
| `graph.py` | Đọc material, trả về `MaterialSpec` (shader, giá trị, nguồn texture, keyword, render state, outline, cảnh báo) |
| `bake.py` | Bake nhánh node bằng Cycles *Emit* trên object, mesh và material tạm |
| `textures.py` | Copy hoặc lưu lại ảnh, tạo texture dải màu, chọn PNG hay EXR |
| `unity_yaml.py` | Ghi `.mat` và mọi loại `.meta` |
| `report.py` | Báo cáo (Text datablock, popup, README, gợi ý đèn) |
| `__init__.py` | `export_model(context, target, objects, options) -> Report` |

**Các mẫu graph hỗ trợ** (Reroute được đi xuyên qua):
1. Material Output.Surface nhận từ output BSDF của một trong bốn node.
2. **Mẫu tóc:** `Emission(Color ← Mix[RGBA, ADD](A ← AnimeCel.Color, B ← AngelRing.Color, Factor ← AngelRing.Fac))`.
   Mẫu này cho ra shader AnimeCel kèm keyword `_DT_ANGEL_RING` cùng các thông số Angel Ring. Strength của Emission thành `_DT_EmissionStrength`.

Material không khớp mẫu nào bị bỏ qua và ghi cảnh báo. Trong Unity, các material này giữ material mặc định do FBX tạo
ra, và báo cáo liệt kê chúng. Material `<tên>.Outline` của Dự án 1 chỉ là nguồn thông số outline, không được xuất thành
material riêng.

**Nguồn giá trị của mỗi input** (chỉ xét input đang hiện):

| Trường hợp | Xử lý |
|---|---|
| Không có link | Lấy giá trị |
| Image Texture (output Color) cắm thẳng, UV mặc định hoặc node UV Map trỏ tới **UV map đầu tiên**, projection Flat | Copy file ảnh; giá trị nhân của input = 1 |
| Normal Map (Tangent, UV map đầu tiên) ← Image Texture | Copy làm normal map, kèm Strength |
| Nhánh không phụ thuộc ánh sáng hay góc nhìn | Bake ra texture |
| Nhánh có Shader to RGB, Layer Weight, Fresnel, Light Path, Ambient Occlusion, Camera Data, Geometry (Incoming, Backfacing), Texture Coordinate (Window, Camera, Reflection), node DaskToon, hoặc socket kiểu shader | Không bake được: dùng giá trị đang đặt và cảnh báo |

**Bake**
- Làm trên object, mesh (bản copy, chỉ giữ các mặt dùng material đó) và material tạm; dùng **UV map đầu tiên**.
- Cycles Emit, margin 16 px. Độ phân giải là ảnh lớn nhất trong nhánh, hoặc giá trị mặc định 1024. Số sample mặc định 16.
- Xóa đồ tạm trong `try/finally`.
- Input màu lưu PNG sRGB. Input số lưu PNG Non-Color. Giá trị ngoài khoảng 0–1 lưu EXR.

**Thiết lập material**

| DaskToon | Unity |
|---|---|
| `surface_render_method = BLENDED` | Transparent: queue 3000, SrcAlpha / OneMinusSrcAlpha, ZWrite tắt |
| DITHERED và Alpha có link hoặc nhỏ hơn 1 | Alpha Clip (`_DT_ALPHATEST_ON`, cutoff 0.5) |
| `use_backface_culling` | `_Cull` = Back, còn lại Off |

**Outline** (theo `find_source` của Dự án 1)
- Material bật outline thì có keyword `_DT_OUTLINE` và pass outline được bật.
- Thông số outline lấy từ node chính và material `.Outline`: Width (mét), Light Bleed, Hand Wobble, Tint Mode, Outline
  Color (giá trị, hoặc texture qua copy hay bake), Tint Darkness, Tint Saturation Boost, Lighting Mix.
- Base Color cho chế độ Harmonic dùng chung texture hoặc giá trị Base Color của material.
- Chỉ số kênh UV của `DT_OutlineN` và `DT_OutlineW` lấy theo thứ tự UV map của mesh dùng material đó, ghi vào
  `_DT_OutlineUV` và `_DT_OutlineWUV`. Nếu nhiều mesh dùng chung material mà thứ tự UV khác nhau thì ghi cảnh báo.

**Báo cáo**
- Gồm: chế độ và đường dẫn đích, shader đã cài hay đã đủ mới, số material đã xuất, input đã bake, các cảnh báo, các mesh
  đã ghi `DT_OutlineN/W`, các modifier không được áp dụng.
- Cường độ đèn gợi ý tính từ Sun đầu tiên trong scene, ví dụ: "Sun 3.0 → Directional 0.955".
- Ở chế độ FOLDER, nội dung báo cáo cũng được ghi vào `README.txt`.

## 6. Shader Unity (URP 17.5)

**Ba lớp**
- `DaskToonCore.hlsl`: port đúng các hàm `dt_*` và công thức của từng node (Dự án 1, mục 3). Không phụ thuộc URP. Các hàm
  nhận một struct `DTLighting` (ánh sáng diffuse tại N, tại hướng "lên", màu đèn, độ sáng glossy, AO).
- `DaskToonURP.hlsl`: file duy nhất gọi API URP. Nó gom ánh sáng diffuse theo đúng ý nghĩa của `closure_eval(diffuse)`:
  ```
  diffuse(N) = mainLight.color × saturate(N·L) × distanceAtten × shadowAtten
             + Σ additionalLights (Lambert, theo vòng lặp đèn Forward+)
             + SampleSH(N)          (cộng APV nếu project bật)
  ```
  Nó cũng tính glossy cho specular toon (GGX của các đèn với perceptual roughness 0.05, cộng phản xạ môi trường) và AO
  (SSAO của URP nếu bật, không thì bằng 1).
- `DaskToonOutline.hlsl`: vertex và fragment của pass outline.

**Đổi trục:** các công thức dùng hướng thế giới của Blender (hướng "lên" cho Ambient, Angel Ring, vị trí trong Anime Eye
khi không có UV) đổi qua `DT_BlenderToUnityDir` và `DT_UnityToBlenderPos`. Phép đổi được kiểm chứng ở bước test đầu tiên
trong Unity, với FBX export bằng thiết lập ở mục 4.

**Property:** dùng `_BaseColor` và `_BaseMap` theo quy ước của URP; các property khác có tiền tố `_DT_`. Mỗi input nhận
được texture có bộ ba: giá trị `_DT_<Input>`, texture `_DT_<Input>Map` và cờ `_DT_<Input>MapOn`. Shader chỉ lấy mẫu texture
khi cờ bật (nhánh điều kiện theo material). Mọi texture dùng chung sampler inline, để không vượt giới hạn 16 sampler.

**Keyword** (`shader_feature_local`): `_DT_RAMP`, `_DT_AMBIENT`, `_DT_LIGHT`, `_DT_AO`, `_DT_RIM`, `_DT_GRADE`,
`_DT_OUTLINE`, `_DT_ANGEL_RING`, `_DT_ALPHATEST_ON`, `_DT_NORMALMAP`. Các enum (Ambient Mode, Light Mode, Outline Tint Mode)
truyền dạng float.

**Các pass của mỗi shader**
- `UniversalForward`: shading chính.
- `SRPDefaultUnlit`: outline. Cull Front; đỉnh được đẩy ra trong không gian thế giới:
  ```
  n_ts   = oct_decode(uv[_DT_OutlineUV])
  N_ws   = normalize(T_ws × n_ts.x + B_ws × n_ts.y + N_ws × n_ts.z)   (khung tangent đã skin của Unity)
  width  = W × light_thin(N_ws · L_main) × (1 + 0.25 × wobble × f(uv0 × 12)) × uv[_DT_OutlineWUV].x
  P_ws  += N_ws × width
  ```
  `light_thin` và `f` lấy đúng công thức ở mục 4.3 spec Dự án 1. Màu nét dùng công thức Dask Outline (Custom, Harmonic,
  Light Reactive, Lighting Mix).
- `ShadowCaster`, `DepthOnly`, `DepthNormals`: pass DepthNormals cần cho SSAO.

**Render state** (`_SrcBlend`, `_DstBlend`, `_ZWrite`, `_Cull`, `_AlphaClip`) đặt qua property, theo cách URP vẫn làm.

## 7. Dự án DaskToon (giai đoạn B)

**`dasktoon_project.json`** đặt ở gốc thư mục dự án:
```json
{"version": 1, "name": "Dự án của tôi",
 "engines": [{"engine": "UNITY_URP", "path": "D:/Unity/9mare"}]}
```
`engines` là một danh sách để sau này hỗ trợ nhiều engine. Bản này chỉ dùng phần tử đầu tiên.

**Code:** thư viện `scripts/modules/dasktoon_project/` (`project.py`: đọc, ghi, nhận diện, danh sách gần đây). Giao diện ở
`scripts/startup/bl_ui/dasktoon_project.py`.
- `find_project(blend_path) -> Project | None`: đi ngược lên từ thư mục chứa file `.blend`, tìm `dasktoon_project.json`.
- `create_project(name, folder, engine, engine_path, save_current) -> Project`:
  - tạo thư mục và file json;
  - kiểm tra `engine_path` là project Unity (có `Assets/` và `ProjectSettings/`), nếu không thì báo lỗi;
  - gọi `install_shaders` ở chế độ PROJECT;
  - nếu chọn thì lưu file `.blend` hiện tại vào `<folder>/<tên file>.blend`;
  - thêm dự án vào danh sách gần đây.
- `project_models(project) -> list[path]`: mọi file `.blend` trong thư mục dự án, bỏ qua `.blend1` và thư mục ẩn.
- **Danh sách gần đây:** tối đa 8 dự án, lưu ở `bpy.utils.user_resource('CONFIG', path="dasktoon/recent_projects.json")`.
  Biến môi trường `DASKTOON_CONFIG_DIR` ghi đè đường dẫn khi chạy test.

**Giao diện**
- *File › Dự án DaskToon*:
  - **Tạo dự án…**: hộp thoại nhập tên, thư mục dự án, engine (Unity 6 URP), đường dẫn project Unity, và ô "Lưu file
    hiện tại vào dự án".
  - **Mở dự án…**: chọn file `dasktoon_project.json`; panel hiện dự án đó.
  - **Dự án đang mở** là dự án chứa file `.blend` hiện tại. Nếu file không thuộc dự án nào thì dùng dự án vừa mở bằng
    *Mở dự án…*, chỉ nhớ trong phiên làm việc hiện tại. Mở một model của dự án sẽ đưa file đó vào dự án, nên quy tắc
    thứ nhất lại áp dụng.
- **Panel *DaskToon › Dự án*** trong thanh bên của viewport 3D:
  - Có dự án: tên, engine và đường dẫn, phiên bản shader đã cài; danh sách model kèm nút **Mở** (hỏi lưu nếu file đang
    sửa); nút **Export model này** (chạy Engine Export với đích của dự án, không mở hộp chọn thư mục), **Cài lại shader**,
    **Mở thư mục dự án**.
  - Chưa có dự án: nút Tạo dự án, Mở dự án, và danh sách dự án gần đây.
- **Engine Export:** nếu file `.blend` thuộc một dự án thì engine và đích được điền sẵn, đi thẳng vào chế độ PROJECT. Người
  dùng vẫn đổi được trong hộp thoại.

## 8. Kiểm thử

**Headless trong DaskToon**

| Nhóm | Nội dung |
|---|---|
| `targets` | Nhận diện project Unity giả (thư mục tạm có `Assets/` và `ProjectSettings/`); chế độ PROJECT và FOLDER; nhớ đích theo file `.blend` |
| `shaders_install` | Ghi lần đầu; lần sau không ghi lại; phiên bản mới thì ghi đè |
| `model_fbx` | FBX có shape key, `DT_OutlineN/W`, và không có lớp vỏ outline; `.meta` gán đúng GUID material theo tên |
| `graph` | Mỗi node; mẫu tóc; Reroute; texture cắm thẳng; Mapping (phải bake); nhánh phụ thuộc ánh sáng (phải cảnh báo); Transparent và Alpha Clip; outline và chỉ số kênh UV |
| `yaml` | So `.mat` và `.meta` với mẫu chuẩn (golden) |
| `layout` | Cây thư mục ở cả hai chế độ, có `.meta` cho thư mục, GUID giống nhau giữa hai lần export, README |
| `textures`, `bake` | Pixel của texture dải màu; đổi linear sang sRGB; chọn PNG hay EXR; nhánh bake khớp giá trị; dữ liệu người dùng không đổi |
| `project` | Tạo dự án (json, shader đã cài, file `.blend` đã lưu); nhận diện từ thư mục con; danh sách model; danh sách gần đây (tối đa 8); Engine Export của dự án ghi đúng vào project Unity giả |

**Trong Unity 6000.5.4f1, batchmode** (`tests/unity/`)
- Project tạm được tạo trong thư mục tạm, **không đụng tới project của người dùng**:
  - Manifest có `com.unity.render-pipelines.universal 17.5.0`, lấy từ bản có sẵn trong máy.
  - Linear color space.
  - URP Asset được tạo bằng script editor.
- Export bằng chế độ PROJECT vào project tạm, rồi chạy script C# `DaskToonTests.Run` qua `-executeMethod`:
  1. Mọi shader biên dịch không lỗi (`ShaderUtil.GetShaderMessages`).
  2. FBX tự nhận đúng material qua `externalObjects`, và có blend shape.
  3. **Bước kiểm chứng đầu tiên:** hướng trục và normal giải nén từ `DT_OutlineN` khớp giá trị DaskToon tính sẵn.
  4. Render một quả cầu dưới Directional Light (cường độ = Sun ÷ π) và ambient bằng màu World, cho từng node, preset và
     module. Ghi pixel tại các điểm cố định ra JSON.
- Python so sánh với render của cùng cảnh trong DaskToon. Sai số cho phép: cel và diffuse ≤ 0.03. Vùng specular và AO
  chỉ báo con số, không chấm đạt hay trượt.
- Ghép ảnh DaskToon và Unity cạnh nhau để người dùng duyệt.
- **Giao diện** (hộp thoại Engine Export, panel Dự án) do người dùng kiểm tra trong DaskToon thật.

## 9. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Unity batchmode cần license và GPU (không dùng `-nographics`) | Kiểm chứng ở bước đầu của kế hoạch; nếu không chạy được thì hướng dẫn chạy tay |
| MikkTSpace của Unity khác Blender | Bước kiểm chứng đầu tiên trong Unity. Nếu lệch, lưu normal outline trong không gian object kèm cảnh báo về skinning |
| Unity không chấp nhận `.mat` hoặc `.meta` tối giản, hoặc giá trị enum của ModelImporter sai | Test import; bổ sung trường theo bản Unity tự sinh ra |
| Ghi vào project Unity đang mở | Unity tự import lại khi được focus; báo cáo nhắc chuyển sang Unity. Không bao giờ xóa file của người dùng; chỉ ghi đè file do DaskToon tạo (nhận ra nhờ GUID của DaskToon) |
| Modifier khác (Mirror, Subdivision) không được áp dụng vì Apply Modifiers tắt | Báo cáo liệt kê; người dùng áp dụng trước khi export |
| Specular, AO và ánh sáng gián tiếp khác EEVEE | Ghi sai số riêng từng phần trong báo cáo |
| Người dùng giữ cường độ đèn như Blender nên Unity sáng gấp π lần | Báo cáo tính sẵn cường độ gợi ý |
| Export lại ghi đè chỉnh sửa tay trong Unity | Báo cáo nhắc trước |

## 10. Nhật ký quyết định

| Quyết định | Nguồn |
|---|---|
| Unity 6 URP 17.5 trước, Unity 7 sau | Người dùng |
| Giống node nhất có thể | Người dùng |
| Bake texture có trong v1 | Người dùng |
| Outline là pass trong shader, dùng `DT_OutlineN/W` | Người dùng (chọn nét dày mỏng thật) |
| **Engine Export** có hộp thoại: chọn engine, chọn xuất model FBX, xuất ra thư mục để kéo vào | Người dùng (thay cho gói `.unitypackage` không có FBX) |
| Ghi thẳng vào project Unity nếu thư mục chọn nằm trong project | Người dùng chấp nhận đề xuất |
| Gộp hệ thống Dự án vào dự án 2, chia hai giai đoạn A và B | Người dùng |
| Viết spec để người dùng đọc trước khi lập kế hoạch | Người dùng |
| Exporter tự ghi `DT_OutlineN/W` trước khi xuất | Nhóm, để người dùng không quên bước này |
| FBX xuất với Apply Modifiers tắt; `.meta` gán sẵn material | Nhóm, giữ shape key và bỏ bước Search and Remap |
| GUID của model, material và texture tính bằng hash tên; shader có GUID cố định và file phiên bản | Nhóm |
| Thư viện nằm trong `scripts/modules/`, phần giao diện trong `bl_ui` | Nhóm, để thư viện test được độc lập |
| Danh sách gần đây tối đa 8 dự án, lưu trong thư mục cấu hình của người dùng | Nhóm |
| Kiểm chứng trong Unity trên project tạm, dùng URP có sẵn trong máy | Nhóm |
