# DaskToon: lõi đổ bóng tùy biến và hệ thống outline mới (Dự án 1)

- Ngày: 2026-10-03
- Trạng thái: chờ duyệt
- Phụ thuộc: không
- Dự án phụ thuộc vào spec này: Dự án 2, export material/shader sang Unity 6 URP (spec riêng, viết sau)

## 1. Bối cảnh và mục tiêu

DaskToon cần export được material nhân vật sang Unity với kết quả giống nhất có thể (Dự án 2). Khi rà soát
các node nhân vật, nhóm phát hiện nhiều input không có tác dụng ngay trong DaskToon. Ngoài ra, hệ thống outline
hiện tại (Solidify cộng handler Python) làm FBX mất shape key, chèn slot material vô hạn vào mesh dùng chung,
và chạy lại toàn bộ mỗi lần depsgraph cập nhật. Dự án 1 sửa các node và làm lại outline **trước**, để Dự án 2
port từ một nền đúng.

Mọi thay đổi trên node phải đạt ba tiêu chí do người dùng đặt ra:

1. **Tự chỉnh style đổ bóng:** mỗi người có một style bóng riêng, và node giúp họ đưa style đó vào shader 3D dễ dàng.
2. **Ánh sáng giống tranh vẽ hoặc anime**, không giống render thực tế.
3. **Dễ thao tác:** chỉ hiện các điều khiển có tác dụng với lựa chọn hiện tại, có preset để bắt đầu.

### Bằng chứng đã đo (bản build `DaskToon.exe`, 2026-08-23)

| Thử nghiệm | Kết quả |
|---|---|
| Mix Shader, factor 1 (không phải hằng số), giữa Anime BSDF/Dask Cel và màu đen | Vẫn ra đủ màu, lẽ ra phải đen |
| Anime BSDF, Alpha = 0, film trong suốt | Pixel đen đục (alpha = 1) |
| FBX export (Apply Modifiers bật) khi mesh có modifier Geometry Nodes | UV còn, **mất toàn bộ shape key** |
| FBX export khi mesh có Solidify outline hiện tại | **Mất toàn bộ shape key** |
| FBX export khi normal outline ghi thành UV map thật | UV và shape key đều còn |
| 201 linked duplicate có outline | Mesh dùng chung bị chèn 202 slot, sinh ra 201 material `_DaskOutline` |

## 2. Phạm vi

**Trong phạm vi**
- Lõi đổ bóng dùng chung, hai chế độ (Đơn giản và Dải đổ bóng), cho Anime BSDF, Anime Cel và Dask Cel.
- Preset style có sẵn, lưu style của người dùng, chuyển từ Đơn giản sang Dải.
- Sửa Anime Cel (cel và specular thật), sửa Alpha của Anime BSDF, sửa lỗi weight trong Mix Shader ở 8 node.
- Ambient Mode và Light Mode hoạt động thật trên Anime Cel và Anime BSDF (dùng chung), kèm sửa lỗi
  `light_blend_mode` ghi đè cờ module của Anime BSDF.
- Hệ thống outline mới bằng Geometry Nodes: theo từng material, độ dày theo từng đỉnh (Light Bleed, Hand Wobble, mask).
- Dữ liệu outline cho game (UV map `DT_OutlineN`, `DT_OutlineW`).
- Tự động nâng cấp file cũ khi mở.
- Test tự động và ảnh so sánh để duyệt bằng mắt.

**Ngoài phạm vi**
- Export Unity (Dự án 2).
- Độ dày outline cố định theo pixel màn hình.
- Shadow 2 và Rim cho Anime Cel. Specular cho Anime BSDF và Dask Cel.
- Hướng sáng cố định (0.5, 0.8, 0.6) trong phần màu "glow" của Dask Outline: giữ nguyên.
- Node group, node Manga, nhóm node vật liệu (Wood, Metal…).

## 3. Lõi đổ bóng dùng chung

### 3.1 Giá trị độ sáng

Cả ba node dùng cùng một giá trị, đúng như Anime BSDF và Dask Cel đang dùng:

```
light = max(r, g, b) của closure_eval(ClosureDiffuse{weight=1, color=1, N})
```

Anime Cel chuyển sang dùng giá trị này, thay cho cách "diffuse closure tô màu + 15% màu bóng" hiện tại.
Màu đèn được lấy từ cùng closure đó: `light_col = rgb`, và `light_norm = light_col / max(light, 0.001)`
(bằng `(1, 1, 1)` khi `light` ≤ 0.001). *Light Tint Strength* của Anime Cel giờ có cùng nghĩa như ở Anime BSDF:
đó là độ mạnh của lớp tint màu đèn (mục 3.10), chứ không còn là hệ số nhân vào ánh sáng.

Lưu ý: giá trị này gồm cả ánh sáng từ World. World càng sáng thì càng ít vùng tối. Đây là hành vi hiện có và
được giữ nguyên. Tooltip của *Shadow Threshold* phải ghi rõ điều này.

### 3.2 Chế độ Đơn giản (mặc định)

Giữ đúng công thức hiện tại của Anime BSDF, nên material cũ không đổi look:

```
s_soft = max(Softness, 0.001)
s_min  = clamp(Threshold - s_soft/2, 0, 1)
s_max  = clamp(Threshold + s_soft/2, s_min + 0.0001, 1)
cel    = smoothstep(s_min, s_max, light)
auto_shadow  = Base × Shadow × 1.25
final_shadow = length(Shadow) > 0.001 ? mix(Shadow, auto_shadow, 0.75) : Base × 0.5
color  = mix(final_shadow, Base, cel)
```

### 3.3 Chế độ Dải đổ bóng

```
t     = clamp(light + 0.5 - Threshold, 0, 1)    // Threshold 0.5 là trung tính; cao hơn thì nhiều bóng hơn
tint  = Ramp(t).rgb                              // lấy mẫu giống node ColorRamp
color = Base × tint
cel   = clamp((lum(tint) - lum(Ramp(0))) / max(lum(Ramp(1)) - lum(Ramp(0)), 0.0001), 0, 1)
```

- `cel` là mức sáng tương đối trên dải. Các module phía sau dùng nó (Ambient "chỉ vùng bóng", Light Tint),
  nên mask của chúng đi theo đúng các bậc trên dải, kể cả khi dải có mép cứng.
- `lum` dùng hệ số luminance của OCIO, giống node RGB to BW.
- Cách lấy mẫu: interpolation CONSTANT thì lấy texel gần nhất (như `valtorgb_nearest`), các kiểu còn lại lấy
  tuyến tính (như `valtorgb`). Bảng màu tạo bằng `BKE_colorband_evaluate_table_rgba`, rồi đưa lên GPU qua `GPU_color_band`.
- Ở chế độ này, *Shadow Color* và *Shadow Softness* bị ẩn. *Shadow Threshold* vẫn hiện và nhận texture để vẽ tay
  vùng dễ hoặc khó bị bóng.

### 3.4 Tích hợp vào từng node

| Node | Thay đổi |
|---|---|
| Anime BSDF | Phần 2 của GLSL (cel 2 tông) được thay bằng lời gọi lõi. Các module Ambient, Light, AO, Rim, Grade giữ nguyên và dùng `cel` của lõi. |
| Dask Cel | Phần 1 đến 3 được thay bằng lõi. Phần viền tối theo góc nhìn (*Use Outline*) giữ nguyên. |
| Anime Cel | Pipeline mới: `shadow_amb` = Ambient Mode (3.10) áp lên *Shadow Color* với màu ambient, hệ số `ambient_blend × ambient_color.a`. `lit_col` giữ cách tính cũ. Gọi lõi với `Base = lit_col`, `Shadow = shadow_amb`. Sau đó áp Light Mode (3.10) lên phía sáng, `color = mix(color, light_mode(color), cel)`. Cuối cùng cộng specular (3.6) rồi xuất emission. Output *Color* trả về màu cuối đã đổ bóng, nên preset Tóc giờ có bóng thật. |

Hàm lõi nằm trong một file GLSL mới, `gpu_shader_material_dasktoon_shading_lib.glsl`, được cả ba node include.
Các hàm `rgb_to_hsv` và `hsv_to_rgb` đang bị chép lại ở nhiều file được gom về đây.

### 3.5 Dữ liệu, RNA và giao diện

- **Lưu dải màu:** cả ba node dùng storage `"ColorBand"` (cùng cách node ColorRamp:
  `node_type_storage(ntype, "ColorBand", node_free_standard_storage, node_copy_standard_storage)`).
  Node mới được khởi tạo với dải của preset "Anime 2 tông".
- **Node từ file cũ có `storage == NULL`.** Mọi chỗ đọc (vẽ giao diện, GPU, RNA) phải xử lý được NULL. Khi
  người dùng chuyển sang chế độ Dải mà storage vẫn NULL, RNA update tạo storage mới. Ở chế độ Đơn giản, GPU dùng
  một bảng mặc định, để hàm GLSL lúc nào cũng nhận được texture.
- **Cờ chế độ và enum** được lưu trong các bit của `custom1/custom2`, kèm hàm get/set RNA riêng (giống cách Anime BSDF
  đang đóng gói hai enum vào `custom1`). Không thêm struct DNA mới.

  | Node | `custom1` | `custom2` |
  |---|---|---|
  | Anime BSDF | bit 0–3 `ambient_mode`, bit 4–7 `outline_tint_mode` (như cũ), **bit 8–11 `light_blend_mode` (chuyển từ `custom2`)** | bit 0–5 cờ module (như cũ), **bit 6 chế độ Dải** |
  | Anime Cel | **`ambient_mode`** (mới) | **bit 0–3 `light_blend_mode`** (mới), **bit 8 chế độ Dải** |
  | Dask Cel | `outline_tint_mode` (như cũ) | **bit 0 chế độ Dải** |

  Đã kiểm chứng trên bản build: Anime Cel hiện **không có** RNA `ambient_mode` và `light_blend_mode`, dù `draw_buttons`
  có gọi tới, nên hai dropdown này chưa bao giờ hiện ra. Ở Anime BSDF, `light_blend_mode` đang ánh xạ vào **toàn bộ**
  `custom2`: đặt giá trị `HUE` sẽ xóa các cờ module (đã thấy Rim bị tắt). Việc chuyển sang `custom1` bit 8–11 sửa lỗi này.
- **RNA:** `shading_mode` (enum `SIMPLE`/`RAMP`) và `shading_ramp` (con trỏ tới ColorBand, như `color_ramp` của ColorRamp).
- **Node chỉ hiện các thứ có tác dụng** (`draw_buttons`):
  ```
  Shading: [Đơn giản | Dải đổ bóng]            (enum dạng nút)
  (khi là Dải)
  Style: [menu ▾]  [Lưu style của tôi]  [Chuyển từ Đơn giản]
  <template_color_ramp>
  ```
  Socket ẩn hoặc hiện bằng `.available(...)` theo cờ chế độ, giống cách các module của Anime BSDF đang làm.
- **Anime Cel:** thêm RNA cho hai dropdown `ambient_mode` và `light_blend_mode`, rồi truyền sang GLSL (mục 3.10).
- **Anime BSDF:** `light_blend_mode` được vẽ trong giao diện ngay dưới công tắc Light, và chỉ hiện khi module Light đang bật.

### 3.6 Specular của Anime Cel

Lấy theo bản node-group cũ (`get_or_create_cel_shader_group`):

```
g     = lum(closure_to_rgba(closure_eval(ClosureReflection{weight=1, color=1, N, roughness=0.05})).rgb)
s_min = 1 - SpecularSize
spec  = clamp((g - s_min) / max(SpecularSoftness, 0.0001), 0, 1)     // Map Range tuyến tính, có clamp
color = color + SpecularColor.rgb × spec                              // Mix ADD
```

Hàm GPU của Anime Cel phải bật thêm cờ `GPU_MATFLAG_GLOSSY` và `GPU_MATFLAG_SHADER_TO_RGBA`.

### 3.7 Preset và style của người dùng

- File mới: `scripts/startup/bl_ui/dasktoon_shading_styles.py`.
- **Preset có sẵn.** Đây là giá trị khởi đầu, sẽ được chỉnh lại qua lượt duyệt bằng mắt (mục 7.5):

  | Tên | Interpolation | Các điểm màu (vị trí: màu tint, linear) |
  |---|---|---|
  | Anime 2 tông | CONSTANT | 0.0: (0.80, 0.62, 0.66) · 0.5: (1, 1, 1) |
  | Anime 3 tông | CONSTANT | 0.0: (0.55, 0.42, 0.52) · 0.3: (0.82, 0.66, 0.70) · 0.55: (1, 1, 1) |
  | Mềm như vẽ | EASE | 0.2: (0.72, 0.58, 0.66) · 0.7: (1, 1, 1) |
  | Da anime (viền ấm) | CONSTANT | 0.0: (0.82, 0.62, 0.64) · 0.47: (1.0, 0.55, 0.50) · 0.53: (1, 1, 1) |
  | Manga | CONSTANT | 0.0: (0.10, 0.10, 0.10) · 0.5: (1, 1, 1) |

- **Style của người dùng** được lưu thành JSON tại
  `bpy.utils.user_resource('CONFIG', path="dasktoon/shading_styles", create=True)/<tên>.json`:
  ```json
  {"version": 1, "name": "Style của tôi", "interpolation": "CONSTANT",
   "stops": [[0.0, [0.8, 0.62, 0.66, 1.0]], [0.5, [1, 1, 1, 1]]]}
  ```
- **Operator** (đều chạy trên `context.active_node`, và chỉ chạy khi node đó là một trong ba node trên):
  - `dasktoon.shading_style_apply(name)`
  - `dasktoon.shading_style_save(name)`: hỏi tên, xác nhận trước khi ghi đè.
  - `dasktoon.shading_style_delete(name)`: chỉ cho style của người dùng.
  - `dasktoon.shading_ramp_from_simple`: tạo dải EASE với hai điểm, tại `0.5 - Softness/2` (màu tint) và
    `0.5 + Softness/2` (màu trắng). Ở chế độ Dải, `t = light + 0.5 - Threshold`, nên ranh giới `light = Threshold`
    luôn rơi vào `t = 0.5`. EASE gần với `smoothstep` của chế độ Đơn giản. `tint = clamp(final_shadow / max(Base, 0.01), 0, 1)` tính từ giá trị
    socket. Nếu socket đang có link thì dùng `Base = (0.8, 0.8, 0.8)`. Sau đó bật chế độ Dải và báo cho người dùng
    biết đây là chuyển gần đúng.
- **Menu** `NODE_MT_dasktoon_shading_styles`: các preset có sẵn, một đường kẻ, rồi các style của người dùng.

### 3.8 Sửa Alpha của Anime BSDF

```
result = closure_add(closure_eval(ClosureTransparency{weight = w × (1 - a), transmittance = 1, holdout = 0}),
                     closure_eval(ClosureEmission{weight = w × a, emission = surface_color}))
```

Làm giống `gpu_shader_material_anime_glass.glsl`. Ở đây `a = clamp(Alpha, 0, 1)` và `w = weight`.

### 3.9 Sửa weight trong Mix Shader

Ở 8 file sau, dòng `float w = (weight > 0.0001f) ? weight : 1.0f;` được đổi thành `float w = weight;`:
`anime_character`, `artist_line_modulation`, `dask_ambient`, `dask_ao`, `dask_cel`, `dask_grade`, `dask_light`, `dask_outline`.

### 3.10 Ambient Mode và Light Mode dùng chung

Hai hàm trong `gpu_shader_material_dasktoon_shading_lib.glsl`, được Anime BSDF và Anime Cel dùng chung.

**Ambient Mode** `dt_ambient_mode(a, b, mode)`, với `a` là màu cần đổi và `b` là màu ambient. Lấy nguyên công thức
phần 3 của GLSL Anime BSDF hiện tại:

| Giá trị | Tên | Kết quả |
|---|---|---|
| 0 | OVERLAY | `mix(2ab, 1 - 2(1-a)(1-b), step(0.5, a))` |
| 1 | HUE | `a` lấy hue của `b` |
| 2 | HUE_SAT | `a` lấy hue của `b`, saturation = `mix(s_a, s_b, 0.65)` |
| 3 | SAT | `a` lấy saturation của `b` |
| 4 | VAL | `a` lấy value của `b` |
| 5 | MULTIPLY | `a × b` |
| 6 | MIX | `b` |

Node nào gọi hàm này thì tự trộn kết quả với `a` theo hệ số riêng của node đó (Anime BSDF: `amb_fac × mask`;
Anime Cel: `ambient_blend × ambient_color.a`).

**Light Mode** `dt_light_mode(c, light_col, light_norm, strength, mode)`. Hiện chưa node nào cài đặt các chế độ này
(kể cả Dask Light, node chỉ nhận giá trị mà không dùng), nên công thức dưới đây do nhóm định nghĩa. Ký hiệu
`s = clamp(strength, 0, 2)` và `Ls = mix((1, 1, 1), light_norm, s)`.

| Giá trị | Tên | Kết quả |
|---|---|---|
| 0 | OVERLAY | `overlay(c, Ls)`, đúng như module Light của Anime BSDF hiện nay |
| 1 | HUE | `mix(c, c_với_hue_của_đèn, clamp(s, 0, 1) × sat(light_norm))`. Đèn trắng không đổi màu. |
| 2 | MULTIPLY | `c × Ls` |
| 3 | ADD | `c + (light_col - min3(light_col)) × s`. Chỉ cộng phần có màu của đèn, nên đèn trắng không làm cháy sáng. |
| 4 | PURE_CEL | `c`, không đổi màu theo đèn |

Ở Anime BSDF, module Light dùng `dt_light_mode` thay cho overlay cố định, với `strength = Light Tint Strength`.
Kết quả vẫn được trộn với hệ số `light_factor × cel` như cũ. Giá trị mặc định OVERLAY cho ra đúng look hiện tại.

**Mặc định cho node mới:** Anime Cel dùng `HUE_SAT` cho Ambient (gần nhất với cách đổi hue cũ) và `OVERLAY` cho Light.
Anime Cel từ file cũ được nâng cấp như ở mục 6.

## 4. Hệ thống outline mới

### 4.1 Outline thuộc về material

Một material bật outline khi có một trong ba nguồn sau:
1. Một node Anime BSDF trong material có `use_outline = True`.
2. Một node Dask Cel có socket *Use Outline* bằng True. Nếu socket có link thì đọc `default_value`.
3. Checkbox **Outline** trong panel DaskToon. Checkbox này dành cho material không có hai node trên và được lưu
   thành custom property `dasktoon_outline` trên material.

### 4.2 Material đi kèm `<tên>.Outline`

- Được tạo tự động khi material bật outline. Bên trong là node Dask Outline nối vào Material Output.
- Thiết lập: `use_backface_culling = True`, `use_backface_culling_shadow = True`.
- **Đồng bộ một chiều, từ node chính sang material `.Outline`** (khi material có Anime BSDF hoặc Dask Cel):
  - *Outline Color* (giá trị hoặc nhánh node, dùng lại `_sync_outline_socket`)
  - *Outline Lighting Mix*
  - *Outline Mode* → `tint_mode`. Hai giá trị cùng thang 0, 1, 2 (Custom, Harmonic, Light Reactive).
  - *Base Color* → *Base Color* của Dask Outline. Trước đây không đồng bộ, nên chế độ Harmonic tính sai màu.
- **Điều khiển nâng cao chỉnh trực tiếp trong `.Outline`:** Tint Darkness, Tint Saturation Boost, Light Bleed, Hand Wobble.
  Với material thuộc nguồn số 3, *Outline Width* và *Outline Color* cũng được chỉnh ở đây.
- Khi material tắt outline, material `.Outline` được giữ lại (không tự xóa), để không mất các chỉnh sửa nâng cao.

### 4.3 Modifier Geometry Nodes "DaskToon Outline"

- Được thêm vào **cuối stack** (sau Armature) của mọi object mesh có ít nhất một material bật outline, và được gỡ
  khi không còn material nào bật. Mỗi object có một node group sinh tự động, `DT_Outline::<object>`, trỏ tới node
  group lõi dùng chung `DaskToon_OutlineCore`.
- Luồng xử lý:
  ```
  Geometry vào ─┬──────────────────────────────────────────────────────────┐
                └─ giữ mặt có material bật outline → Flip Faces             │
                   → Set Position(offset = N_điểm × width_điểm / scale_obj) │
                   → Set Material (slot i: material_index == i → mat_i.Outline)
                   → Join Geometry ←───────────────────────────────────────┘ → Geometry ra
  ```
  - Mesh gốc đi qua nguyên vẹn. **Không có thao tác nào ghi vào mesh data.**
  - `N_điểm` là normal **sau khi gộp các đỉnh trùng vị trí**: lấy một bản sao, chạy Merge by Distance (1e-5 m),
    lấy normal của điểm, rồi dùng Sample Nearest để đưa về từng đỉnh của mesh gốc. Bước này cần thiết vì model
    nhập từ VRM, glTF hay FBX thường bị tách đỉnh ở đường nối UV và cạnh cứng. Nếu không gộp, lớp vỏ sẽ nứt ở
    những chỗ đó. Cách gộp này cũng khớp với cách tính `DT_OutlineN` ở mục 5.
  - Chia cho `scale_obj` để độ dày tính theo mét trong thế giới, bất kể object có scale bao nhiêu.
- Độ dày theo từng đỉnh:
  ```
  W, bleed, wobble       = Index Switch theo material_index (bảng do bộ đồng bộ ghi), trung bình hóa về miền Point
  hl                     = dot(N_world, L_sun) × 0.5 + 0.5
  light_thin             = 1 - clamp((hl - 0.55) / 0.45, 0, 1) × bleed × 0.75
  f(uv)                  = sin(2u) × cos(3v) + 0.5 × sin(6.28v),  với (u, v) = UV map đầu tiên × 12
  width                  = W × light_thin × (1 + 0.25 × wobble × f(uv)) × mask
  ```
  - `W` lấy *Outline Width* của node chính. Nếu material thuộc nguồn số 3 thì lấy *Outline Width* của Dask Outline trong `.Outline`.
  - `bleed` và `wobble` lấy *Light Bleed* và *Hand Wobble* của Dask Outline trong `.Outline`.
  - Hệ số 12 thay cho 120 trong GLSL cũ, vì giờ hàm được lấy mẫu theo đỉnh chứ không theo pixel. Hệ số này sẽ được
    chỉnh qua lượt duyệt bằng mắt.
  - `L_sun` lấy từ input object *Sun* của modifier (Object Info → rotation). Bộ đồng bộ tự gán Sun đầu tiên đang
    hiện trong scene. Nếu không có Sun thì dùng `normalize(0.5, 0.8, 0.6)`.
  - `mask` là Named Attribute dạng float trên miền Point, tên do bộ đồng bộ chọn theo thứ tự ưu tiên:
    `Outline_Weight, outline_weight, DaskOutline_Mask, Outline_Mask, Outline_Width, outline_mask`.
    Nếu không có attribute nào thì `mask = 1`.

### 4.4 Bộ đồng bộ

- Thay hoàn toàn `dasktoon_vrm_outline_auto_sync`.
- Gồm một handler `depsgraph_update_post` và một handler `load_post`, đều có `@persistent`.
- Handler chỉ quan tâm các update thuộc Material, ShaderNodeTree và Object/Mesh, và **bỏ qua update chỉ đổi transform**.
- Với mỗi object bị ảnh hưởng, handler tính một **chữ ký**: danh sách material theo slot, cộng các tham số outline
  của từng slot, cộng Sun, cộng tên mask. Chữ ký được so với bộ nhớ đệm. **Chỉ khi khác** thì mới ghi bảng giá trị
  vào node group, đồng bộ material `.Outline` và thêm hoặc gỡ modifier.
- Mọi lệnh ghi đều so sánh trước khi ghi. Vì vậy các lần cập nhật do chính handler gây ra sẽ hội tụ về
  "không có gì để làm", không tạo vòng lặp.
- Linked duplicate: mỗi object có modifier riêng, còn mesh dùng chung thì không bị sửa (khắc phục lỗi #3).

### 4.5 Các thay đổi đi kèm

- Preset `OUTLINE` (`dasktoon.setup_anime_preset`) được viết lại: nó bật outline trên material đang active, thay vì
  tạo material riêng kèm Solidify.
- Gỡ bỏ code Solidify và code chèn slot `_DaskOutline`.

## 5. Dữ liệu outline cho game

Operator `dasktoon.outline_prepare_game_data`, chạy trên các object đang chọn, hoặc tất cả object có outline nếu
không chọn gì. Dự án 2 gọi operator này trước khi export.

1. **Normal đã làm mượt `s`:** gom các đỉnh trùng vị trí (lượng tử hóa 1e-5 m), rồi lấy trung bình normal của mặt,
   có trọng số theo góc tại đỉnh.
2. **Khung tangent của từng góc mặt:** gọi `mesh.calc_tangents(uvmap=uv_layers[0].name)`. Lưu ý dùng **UV map đầu tiên**,
   vì Unity xem nó là uv0, chứ không dùng UV map đang active render.
   Khung tangent gồm `T`, `N` (split normal) và `B = bitangent_sign × cross(N, T)`.
3. Đổi `s` sang không gian tangent: `n = (s·T, s·B, s·N)`. Sau đó nén octahedral:
   ```
   n /= |n.x| + |n.y| + |n.z|
   if n.z < 0: n.xy = (1 - |n.yx|) × sign(n.xy)        // sign(0) = +1
   UV = n.xy                                           // khoảng [-1, 1], ghi nguyên giá trị
   ```
4. Ghi vào UV map thật **`DT_OutlineN`**. Ghi giá trị *mask* (mục 4.3, mặc định 1) vào UV map thật **`DT_OutlineW`**
   (`x = mask`, `y = 0`). Lý do: vertex group không phải xương sẽ không đi qua FBX. Hai UV map này được tạo nếu chưa
   có, và cập nhật tại chỗ nếu đã có.
5. Ghi dấu vào mesh: custom property `dt_outline_sig = [số đỉnh, số góc mặt, tên uv0]`. Panel báo "dữ liệu outline
   đã cũ" khi dấu không khớp. Sửa vị trí đỉnh mà không đổi topology thì không bị phát hiện, và đây là giới hạn được chấp nhận.
6. Mesh không có UV map nào: bỏ qua và báo lỗi.

Đây là thao tác **duy nhất** ghi vào mesh. Nó chỉ chạy khi người dùng bấm hoặc khi export, và có Undo.

## 6. Tự động nâng cấp file cũ khi mở

**Đánh dấu phiên bản dữ liệu.** Một handler `save_pre` ghi `scene["dasktoon_data_version"] = 1` vào mọi scene.
Khi mở file, nếu có scene thiếu dấu này hoặc dấu nhỏ hơn 1, các bước nâng cấp node sau được chạy một lần:

- Anime Cel: đặt `ambient_mode = HUE_SAT` và `light_blend_mode = MULTIPLY`. MULTIPLY gần nhất với cách cũ
  (closure diffuse nhân màu đèn vào màu sáng).
- Anime BSDF: `custom2` của file cũ chỉ chứa cờ module. Bit 6 (chế độ Dải) chắc chắn bằng 0, nên không cần đổi.

Handler `load_post` (`@persistent`) cũng tìm dấu hiệu của hệ thống outline cũ: modifier SOLIDIFY tên `DaskToon_Outline` hoặc
`DaskToon_Outline_Solidify`, hoặc slot có material tên kết thúc bằng `_DaskOutline`. Với mỗi object nằm trong file
(object link từ thư viện thì bỏ qua và ghi vào báo cáo):

1. Đọc thiết lập cũ: độ dày của Solidify, và trong material `_DaskOutline` lấy `tint_mode`, Lighting Mix,
   Outline Color (giá trị hoặc nhánh node), Light Bleed, Hand Wobble, Tint Darkness, Saturation Boost.
2. Với mỗi material của object:
   - Nếu material có node chính (Anime BSDF hoặc Dask Cel), bật outline trên node đó. Nếu *Outline Width* đang là
     mặc định hoặc 0 thì gán độ dày cũ.
   - Nếu không có node chính, bật checkbox outline (nguồn số 3).
   - Chép thiết lập cũ vào material `.Outline`. Material dùng chung cho nhiều object thì object xét trước được giữ,
     xung đột ghi vào báo cáo.
3. Gỡ Solidify cũ. Gỡ **mọi** slot `_DaskOutline` bằng `mesh.materials.pop(index)`, đi từ cuối lên. Lệnh này tự
   dịch chỉ số material của các mặt.
4. Xóa các material `_DaskOutline` không còn ai dùng.
5. Chạy đồng bộ toàn bộ (mục 4.4).
6. **Báo cáo:**
   - Tạo Text datablock "DaskToon Upgrade Report".
   - Một timer chạy sau khi file mở xong sẽ hiện popup: "Đã nâng cấp outline: N object, M slot thừa đã dọn, K cảnh báo".

Thao tác này **không Undo được**. File trên ổ đĩa vẫn nguyên cho tới khi người dùng Save, và Blender giữ bản
`.blend1` khi lưu. Sau khi nâng cấp xong, file không còn dấu hiệu cũ nên lần mở sau sẽ không chạy lại.

## 7. Kiểm thử

- Test là các file `tests/python/dasktoon_*.py`, đăng ký bằng `add_blender_test` trong `tests/python/CMakeLists.txt`.
- Test chạy headless: `DaskToon.exe --background --factory-startup --python <test>`.
- Test render dùng EEVEE ở độ phân giải nhỏ và so sánh pixel ở giữa ảnh, giống các bài thử trong mục 1.

1. **Lõi đổ bóng**
   - Quét Sun strength từ 0 đến 4. Ở chế độ Đơn giản, pixel đổi từ màu bóng sang màu gốc tại đúng ngưỡng.
   - Ở chế độ Dải, màu ra bằng `Base × Ramp(t)` (sai số ≤ 1/255).
   - Ba node cho cùng màu khi cùng thiết lập.
   - Lưu style, nạp lại, xóa style.
   - "Chuyển từ Đơn giản": vị trí ranh giới lệch không quá `Softness`.
   - Node từ file cũ (`storage = NULL`) render được ở cả hai chế độ.
2. **Anime Cel:** ranh giới đổi theo *Threshold*. Specular xuất hiện và lớn dần theo *Size*.
   - Có RNA `ambient_mode` và `light_blend_mode`. Mỗi giá trị cho ra màu khác nhau, đúng theo bảng ở mục 3.10,
     với đèn có màu và ambient có màu.
   - Anime BSDF: đặt `light_blend_mode` không làm thay đổi bất kỳ cờ module nào (lỗi đã thấy ở mục 3.5).
3. **Sửa lỗi:** Alpha 0 cho pixel trong suốt (alpha < 0.01). Mix Shader với factor động bằng 1 ra màu đen ở cả 8 node.
4. **Outline**
   - Lớp vỏ chỉ có ở mặt dùng material bật outline. Material của lớp vỏ là `<tên>.Outline`.
   - Độ dày đỉnh, đo trên mesh đã đánh giá, giảm khi xoay Sun về phía đỉnh, nếu Light Bleed lớn hơn 0.
   - Wobble và mask có tác dụng.
   - Mesh bị tách đỉnh ở đường nối (giả lập model nhập từ VRM): các đỉnh của lớp vỏ có cùng vị trí phải được đẩy
     cùng hướng, nghĩa là lớp vỏ không nứt.
   - 200 linked duplicate: số slot của mesh không đổi.
   - Di chuyển object không kích hoạt việc ghi. Thời gian một lượt handler với 200 object dưới 5 ms.
   - Mesh data không bị sửa (so sánh trước và sau).
5. **Dữ liệu game**
   - `DT_OutlineN`, `DT_OutlineW` và shape key còn nguyên sau vòng FBX export (Apply Modifiers tắt) rồi import.
   - Giải nén octahedral cộng khung tangent cho ra lại `s` với sai số dưới 0.001.
6. **Nâng cấp:** tạo file kiểu cũ có Solidify và 200 slot thừa, lưu, rồi mở lại. Kết quả: không còn Solidify, không còn
   slot `_DaskOutline`, outline mới cùng màu và cùng độ dày, có báo cáo.
7. **Ảnh để duyệt bằng mắt** (không chấm tự động): một script render từng preset trên một nhân vật mẫu, ở chế độ
   Đơn giản và Dải, trước và sau khi sửa, rồi ghép thành một trang PNG cho người dùng duyệt.

## 8. Hợp đồng với Dự án 2 (export Unity)

Dự án 2 chỉ được dựa vào những điều sau. Nếu thay đổi bất kỳ điều nào thì phải cập nhật cả hai spec.

- **Công thức** ở mục 3.1 đến 3.3, 3.6 và 3.8. Shader URP port đúng những công thức này.
- **Dải màu** được lấy mẫu thành bảng theo cách của `BKE_colorband_evaluate_table_rgba`. Bên Python dùng
  `ColorRamp.evaluate()` để tạo texture 1D cho Unity.
- **Outline:** tham số theo từng material (W, bleed, wobble, màu, tint mode, lighting mix). Unity vẽ outline bằng một
  pass trong material: đẩy đỉnh theo `decode(DT_OutlineN)` trong khung tangent của Unity, với cùng công thức độ dày ở
  mục 4.3, `L` lấy từ Main Light, `mask` lấy từ `DT_OutlineW.x`.
- **Khung tangent:** Blender và Unity cùng dùng MikkTSpace trên uv0 và split normal. Dự án 2 phải kiểm chứng điều
  này bằng Unity batchmode.
- **FBX:** nhân vật có shape key phải export với Apply Modifiers tắt. Modifier outline vì thế không vào FBX.
  Dự án 2 sẽ thêm bước kiểm tra để nhắc.

## 9. Rủi ro và điểm cần kiểm chứng sớm

| Rủi ro | Cách xử lý |
|---|---|
| Set Material trong Geometry Nodes dùng material không có trong slot của object | Kiểm chứng ngay ở bước đầu của kế hoạch. Nếu không được thì chuyển sang dùng object outline riêng. |
| Anime Cel đổi look | Đã được người dùng chấp nhận. Có ảnh trước và sau để duyệt. |
| Nâng cấp tự động không Undo được | File gốc giữ nguyên tới khi Save, có `.blend1`, có báo cáo. |
| Đóng gói lại `custom1/custom2` của Anime Cel | Test đọc file cũ có đủ các giá trị enum. |
| Hiệu năng lớp vỏ Geometry Nodes trên mesh lớn (từ 100k tam giác) | Đo thời gian đánh giá modifier trong test hiệu năng. |
| World sáng làm mất vùng tối | Hành vi có sẵn, ghi vào tooltip. |

## 10. Nhật ký quyết định

| Quyết định | Nguồn |
|---|---|
| Engine đầu tiên là Unity 6 URP (17.5), cân nhắc Unity 7 sau | Người dùng |
| Phạm vi: nhân vật anime | Người dùng |
| Tiêu chí: giống node nhất có thể | Người dùng |
| Export chỉ gồm material và shader, FBX do người dùng tự export | Người dùng |
| Bake texture có trong v1 của Dự án 2 | Người dùng |
| Sửa node trước rồi mới port | Người dùng |
| Outline dày mỏng thật (Geometry Nodes ở DaskToon, pass outline ở Unity) | Người dùng |
| Ba tiêu chí: tự chỉnh style bóng, ánh sáng giống tranh vẽ, dễ thao tác | Người dùng |
| Hai chế độ đổ bóng (Đơn giản và Dải) | Người dùng |
| Cả ba node cel dùng chung lõi | Người dùng |
| Tự động nâng cấp file cũ khi mở | Người dùng |
| Normal outline ghi thành UV map thật, không dùng modifier | Nhóm, dựa trên test FBX ở mục 1 |
| Làm hai dropdown Ambient Mode và Light Mode của Anime Cel hoạt động thật | Người dùng |
| Công thức 5 Light Mode (mục 3.10) | Nhóm, vì chưa có node nào cài đặt; **người dùng xem lại** |
| Chuyển `light_blend_mode` của Anime BSDF sang `custom1` bit 8–11 và hiện trong giao diện | Nhóm, sửa lỗi ghi đè cờ module |
| Đánh dấu `dasktoon_data_version` trên scene để nâng cấp node một lần | Nhóm |
| Làm tự động trong khoảng 3 tiếng, nhánh riêng, commit từng bước, tự quyết chỗ chưa rõ và ghi vào báo cáo | Người dùng |
| Mask outline được ghi vào `DT_OutlineW` cho game | Nhóm, vì vertex group không đi qua FBX |
| Hệ số Wobble 12 (thay cho 120) | Nhóm, chỉnh qua lượt duyệt bằng mắt |
| Giữ material `.Outline` khi tắt outline | Nhóm, để không mất chỉnh sửa nâng cao |

## Phụ lục: các quyết định đã chốt cho Dự án 2

Ghi lại ở đây để không mất. Dự án 2 sẽ có spec riêng sau khi Dự án 1 xong.

- **Định dạng:** một file `.unitypackage` chứa Shaders, Materials và Textures, không có FBX. Người dùng import FBX rồi
  dùng *Search and Remap* (khuyên đặt FBX trong `Assets/DaskToon/<tên>/` và chọn *Local Materials Folder*).
- **Thư mục:** `Assets/DaskToon/Shaders/` (GUID cố định) và `Assets/DaskToon/<tên file .blend>/{Materials,Textures}`.
  GUID của material và texture tính bằng hash từ tên file `.blend` và tên material, để export lại sẽ ghi đè đúng chỗ.
- **Tên material giữ nguyên.** Màu được chuyển từ linear sang sRGB khi ghi `.mat`. Input màu dùng texture sRGB, input
  số dùng Non-Color. Giá trị ngoài 0–1 lưu EXR.
- **Converter:** `scripts/startup/dasktoon_export/` gồm `node_maps.py`, `graph.py`, `bake.py`, `unity/` và `__init__.py`.
  Texture cắm thẳng thì copy file. Nhánh không phụ thuộc ánh sáng thì bake bằng Cycles Emit trên object, mesh và
  material tạm (dữ liệu của người dùng không bị đụng tới). Nhánh phụ thuộc ánh sáng thì dùng giá trị đang đặt và cảnh báo.
- **Shader:** `DaskToonCore.hlsl` (không phụ thuộc URP), `DaskToonURP.hlsl` (file duy nhất gọi API URP), và một file
  `.shader` cho mỗi node. Outline là một pass trong shader (theo mục 8), không còn material Outline gán lên lớp vỏ.
- **Đơn vị:** Directional Light trong Unity = Sun strength ÷ π (đã đo: Sun 1 cho ra 0.3184). Ambient map 1:1.
  Đổi trục Z-up của Blender sang Y-up của Unity.
- **Kiểm thử:** dùng Unity 6000.5 có sẵn trên máy ở batchmode để import gói và biên dịch shader.
