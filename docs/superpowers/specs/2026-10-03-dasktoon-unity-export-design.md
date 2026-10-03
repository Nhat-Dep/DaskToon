# DaskToon: export material và shader sang Unity 6 URP (Dự án 2)

- Ngày: 2026-10-03
- Trạng thái: chờ duyệt
- Phụ thuộc: Dự án 1 (`docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`, mục 8 là hợp đồng giữa hai
  dự án). Nhánh `dasktoon-unity-export` tách ra từ `dasktoon-shading-outline`.

## 1. Mục tiêu

Một lệnh export trong DaskToon tạo ra **một file `.unitypackage`**. Import file này vào Unity 6 (URP 17.5) cho ra material
nhân vật **giống render EEVEE của DaskToon nhiều nhất có thể**, mà không phải dựng material bằng tay.

Tiêu chí theo thứ tự ưu tiên:
1. **Giống node nhất có thể:** cùng công thức, cùng thông số, cùng texture.
2. **Tự động:** không phải gán thông số hay texture bằng tay trong Unity.
3. **Phù hợp cho game:** outline được vẽ trong shader nên không nhân đôi mesh; các module tắt thì không tốn chi phí.

## 2. Phạm vi

**Trong phạm vi**
- Operator export trong DaskToon, bộ chuyển đổi (đọc graph, map giá trị, copy texture, bake, texture dải màu), bước chuẩn
  bị dữ liệu outline, bộ ghi `.unitypackage` (GUID, `.mat`, `.meta`) và báo cáo.
- Shader URP cho **Anime BSDF, Anime Cel (kèm lớp Angel Ring của mẫu tóc), Anime Eye, Dask Cel**. Mỗi shader có pass
  outline, với màu nét theo Dask Outline.
- Test headless trong DaskToon, và test trong Unity 6000.5 ở chế độ batchmode trên một project tạm.

**Ngoài phạm vi**
- Export FBX (người dùng tự làm), Unreal, Godot, Built-in RP, HDRP, Unity 7 (thêm lớp adapter sau).
- Các node khác (Manga, nhóm vật liệu, Face Shadow, Anime Rim đứng riêng), node group, Mix Shader.
- Giá trị có keyframe hoặc driver (lấy giá trị ở frame hiện tại).
- Export đèn, camera và thiết lập scene.
- Độ dày outline cố định theo pixel màn hình.

## 3. Luồng sử dụng

1. Trong DaskToon, vào *File › Export › DaskToon → Unity (.unitypackage)*, rồi chọn phạm vi (object đang chọn hoặc tất cả).
   Exporter:
   - chạy `dasktoon.outline_prepare_game_data` cho các mesh có outline, để ghi `DT_OutlineN/W` vào mesh;
   - xuất file `<tên file .blend>.unitypackage`;
   - hiện báo cáo.
2. **Sau đó** người dùng export FBX với *Apply Modifiers* **tắt**, để FBX mang theo `DT_OutlineN/W` và shape key.
   Báo cáo cảnh báo nếu mesh còn modifier khác ngoài Armature và DaskToon Outline.
3. Trong Unity:
   - Import gói.
   - Đặt FBX vào `Assets/DaskToon/<tên>/`.
   - Trong tab Materials của FBX, bấm *Search and Remap* (Naming: *From Model's Material*, Search: *Local Materials Folder*).
4. Đặt Directional Light trong Unity theo gợi ý của báo cáo: **cường độ = Sun strength ÷ π**. Ambient lấy đúng bằng màu World.

## 4. Định dạng gói `.unitypackage`

- Gói là file tar.gz. Mỗi asset gồm ba entry: `<guid>/asset`, `<guid>/asset.meta` và `<guid>/pathname` (chứa đường
  dẫn `Assets/...`). Thư mục cũng có entry riêng (`folderAsset: yes`), để GUID của thư mục ổn định giữa các lần export.
- Bố cục:
  ```
  Assets/DaskToon/Shaders/            DaskToonCore.hlsl, DaskToonURP.hlsl, DaskToonOutline.hlsl,
                                      AnimeBSDF.shader, AnimeCel.shader, AnimeEye.shader, DaskCel.shader
  Assets/DaskToon/<Tên>/Materials/    <material>.mat
  Assets/DaskToon/<Tên>/Textures/     <material>_<input>.png|.exr, <material>_Ramp.png
  ```
  `<Tên>` là tên file `.blend` (bỏ đuôi). Nếu file chưa lưu thì dùng `Untitled`.
- **GUID:**
  - Shader: hằng số cố định trong code. Mọi gói dùng chung một bộ shader, và gói mới ghi đè bản cũ.
  - Material và texture: `md5("dasktoon:<Tên>:<đường dẫn tương đối>")`. Export lại sẽ ghi đè đúng asset cũ trong
    Unity. Báo cáo nhắc rằng chỉnh sửa tay trên material đó trong Unity sẽ bị ghi đè.
- **`.mat`:** YAML theo định dạng Material `serializedVersion: 8` của Unity, gồm:
  - `m_Shader {fileID: 4800000, guid, type: 3}` và `m_ValidKeywords` (đã sắp xếp).
  - `m_CustomRenderQueue`: −1, hoặc 3000 nếu Transparent.
  - `stringTagMap` (RenderType), và `disabledShaderPasses` (ghi `SRPDefaultUnlit` khi outline tắt).
  - `m_SavedProperties` (`m_TexEnvs`, `m_Ints`, `m_Floats`, `m_Colors`).
  - Không cần khối AssetVersion của URP; Unity tự thêm khi import.
- **Màu:** Blender lưu linear, còn property kiểu Color trong Unity lưu sRGB (Unity tự đổi về linear khi project ở Linear
  color space). Writer đổi linear sang sRGB bằng hàm piecewise chuẩn, dùng được cả với giá trị lớn hơn 1. Báo cáo nhắc
  rằng project Unity phải ở Linear color space (mặc định của URP).
- **`.meta` của texture** (TextureImporter):

  | Loại | sRGB | Loại texture | Wrap | Filter | Mipmap | Nén |
  |---|---|---|---|---|---|---|
  | Màu (copy hoặc bake) | 1 | Default | Repeat | Bilinear | Có | High Quality |
  | Số liệu (mask, ngưỡng) | 0 | Default | Repeat | Bilinear | Có | Không nén |
  | Normal map | 0 | Normal map | Repeat | Bilinear | Có | High Quality |
  | Dải màu | 1 | Default | Clamp | Point nếu CONSTANT, còn lại Bilinear | Không | Không nén |

- **Texture dải màu:** ảnh PNG 256×1, pixel *i* lấy `ColorRamp.evaluate((i + 0.5) / 256)`. Sai khác so với bảng 257 mẫu
  của Blender không quá 1/256 trên trục t.

## 5. Bộ chuyển đổi trong DaskToon

**Vị trí code**
- Thư viện: `scripts/modules/dasktoon_export/` (thuần Python, test được độc lập).
- Đăng ký giao diện: `scripts/startup/bl_ui/dasktoon_unity_export.py` (operator `export_scene.dasktoon_unity`, mục menu
  *File › Export*).
- Nguồn shader Unity: `scripts/modules/dasktoon_export/unity_urp/`. Thư mục này được cài đặt cùng các script.

| Module | Trách nhiệm |
|---|---|
| `node_maps.py` | Bảng map cho mỗi node: input → property Unity (kiểu, slot texture, có phải màu không), enum → float, cờ module → keyword |
| `graph.py` | Đọc material, trả về `MaterialSpec` (shader, giá trị, nguồn texture, keyword, render state, outline, cảnh báo) |
| `bake.py` | Bake nhánh node bằng Cycles *Emit* trên object, mesh và material tạm |
| `textures.py` | Copy hoặc lưu lại ảnh, tạo texture dải màu, chọn PNG hay EXR |
| `unity_yaml.py` | Ghi `.mat` và `.meta` |
| `unitypackage.py` | Ghi gói tar.gz, tính GUID |
| `report.py` | Báo cáo (Text datablock, popup, gợi ý đèn) |
| `__init__.py` | `export_unity_package(context, filepath, objects, options) -> Report` |

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
- Gồm: số material đã xuất, input đã bake, các cảnh báo, các mesh đã ghi `DT_OutlineN/W`, các modifier cần tắt trước khi
  export FBX.
- Cường độ đèn gợi ý tính từ Sun đầu tiên trong scene, ví dụ: "Sun 3.0 → Directional 0.955".

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
khi không có UV) đổi qua `DT_BlenderToUnityDir` và `DT_UnityToBlenderPos`. Phép đổi được **kiểm chứng ở bước test đầu tiên**
với FBX export bằng trục mặc định của Blender.

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

## 7. Kiểm thử

**Headless trong DaskToon** (`tests/python/dasktoon_unity_export_*_test.py`)
- `graph`: mỗi node; mẫu tóc; Reroute; texture cắm thẳng; Mapping (phải bake); nhánh phụ thuộc ánh sáng (phải cảnh báo);
  Transparent và Alpha Clip; outline và chỉ số kênh UV.
- `yaml`: so `.mat` và `.meta` với mẫu chuẩn (golden).
- `unitypackage`: cấu trúc tar, GUID xác định và giống nhau giữa hai lần export, entry thư mục.
- `textures`: giá trị pixel của texture dải màu; đổi linear sang sRGB; quy tắc chọn PNG hay EXR.
- `bake`: một nhánh procedural sau khi bake phải khớp giá trị của chính nó (đánh giá tại tâm các mặt); dữ liệu của người
  dùng không bị đổi.

**Trong Unity 6000.5.4f1, batchmode** (`tests/unity/`, không nằm trong gói)
- Project tạm được tạo trong thư mục tạm, **không đụng tới project của người dùng**:
  - Manifest có `com.unity.render-pipelines.universal 17.5.0`, lấy từ bản có sẵn trong máy.
  - Linear color space.
  - URP Asset được tạo bằng script editor.
- Script C# `DaskToonTests.Run` (gọi qua `-executeMethod`):
  1. Import gói.
  2. Kiểm tra mọi shader biên dịch không lỗi (`ShaderUtil.GetShaderMessages`), và material trỏ đúng shader và texture.
  3. **Bước kiểm chứng đầu tiên:** import một FBX mẫu export từ DaskToon, rồi so hướng trục và normal giải nén từ
     `DT_OutlineN` với giá trị DaskToon tính sẵn.
  4. Render một quả cầu dưới Directional Light (cường độ = Sun ÷ π) và ambient bằng màu World, cho từng node, preset và
     module. Ghi pixel tại các điểm cố định ra JSON.
- Python so sánh với render của cùng cảnh trong DaskToon. Sai số cho phép: cel và diffuse ≤ 0.03. Vùng specular và AO
  chỉ báo con số, không chấm đạt hay trượt.
- Ghép ảnh DaskToon và Unity cạnh nhau để người dùng duyệt.

## 8. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Unity batchmode cần license và GPU (không dùng `-nographics`) | Kiểm chứng ở bước đầu của kế hoạch; nếu không chạy được thì hướng dẫn chạy tay |
| MikkTSpace của Unity khác Blender | Bước kiểm chứng đầu tiên trong Unity. Nếu lệch, lưu normal outline trong không gian object kèm cảnh báo về skinning |
| Unity không chấp nhận `.mat` hoặc `.meta` tối giản | Test import; bổ sung trường theo bản Unity tự sinh ra |
| Specular, AO và ánh sáng gián tiếp khác EEVEE | Ghi sai số riêng từng phần trong báo cáo |
| Người dùng giữ cường độ đèn như Blender nên Unity sáng gấp π lần | Báo cáo tính sẵn cường độ gợi ý |
| Export lại ghi đè chỉnh sửa tay trong Unity | Báo cáo nhắc trước |

## 9. Nhật ký quyết định

| Quyết định | Nguồn |
|---|---|
| Unity 6 URP 17.5 trước, Unity 7 sau | Người dùng |
| Một file `.unitypackage`, chỉ gồm material và shader, không có FBX | Người dùng |
| Bake texture có trong v1 | Người dùng |
| Giống node nhất có thể | Người dùng |
| Outline là pass trong shader, dùng `DT_OutlineN/W` | Người dùng (chọn nét dày mỏng thật) |
| Viết spec để người dùng đọc trước khi lập kế hoạch | Người dùng |
| Exporter tự ghi `DT_OutlineN/W` trước khi xuất | Nhóm, để người dùng không quên bước này |
| GUID của material và texture tính bằng hash tên, nên export lại sẽ ghi đè | Nhóm |
| Thư viện nằm trong `scripts/modules/dasktoon_export/`, phần UI trong `bl_ui` | Nhóm, để thư viện test được độc lập |
| Kiểm chứng trong Unity trên project tạm, dùng URP có sẵn trong máy | Nhóm |
