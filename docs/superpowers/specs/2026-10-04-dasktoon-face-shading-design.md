# DaskToon: bóng mặt anime bằng khối trứng (Face Shading)

- Ngày: 2026-10-04
- Trạng thái: thiết kế đã được duyệt trong chat (3 phần); người dùng chọn chạy **tự động**
- Nhánh: `dasktoon-face-shading`, tách từ `dasktoon-unity-export` (cần Engine Export của Dự án 2)
- Liên quan: Dự án 1 (lõi đổ bóng, outline Geometry Nodes), Dự án 2 (Engine Export sang Unity)

## 1. Mục tiêu

Bóng trên mặt nhân vật đang lem nhem theo hình khối mũi, má, hốc mắt. Mục tiêu:

- **Ranh giới sáng tối trên mặt cong mượt** như trên một quả trứng.
- **Vẫn giữ bóng mũi nhỏ và bóng dưới cằm gọn.**
- **Dễ thao tác:** bấm một nút cho DaskToon tự làm, rồi tinh chỉnh bằng thanh trượt và bằng cách kéo, xoay, co giãn một khối trứng
  trong viewport, thấy kết quả ngay.
- Bóng mặt đi theo khi nhân vật quay đầu, cử động; **ra giống khi export sang Unity**.

Cách làm: thay normal của vùng mặt bằng normal của một khối trứng (ellipsoid) ôm lấy đầu. Đây là kỹ thuật chuẩn của game anime 3D.
Mọi shader dựa trên normal (Anime BSDF, Anime Cel, Dask Cel và shader thường) đều hưởng lợi mà không phải sửa shader.

## 2. Phạm vi

**Trong phạm vi**
- Node group Geometry Nodes `DaskToon_FaceShading` và modifier **DaskToon Face Shading**.
- Tự căn khối trứng, tạo vertex group vùng mặt, gắn khối trứng vào xương đầu.
- Panel **DaskToon › Bóng mặt** thay panel "🎭 Anime Face Normal Studio"; công cụ cũ chuyển vào mục *Nâng cao*.
- Engine Export: ghi normal hình trứng ở tư thế nghỉ vào FBX, trả mesh về như cũ; `.meta` của FBX tắt blend shape normal.
- Test headless, ảnh duyệt, và một trường hợp trong bài so sánh render Unity.

**Ngoài phạm vi**
- Node Face Shadow (SDF) giữ nguyên, không sửa.
- Vẽ hình bóng theo góc đèn (SDF face map), bóng tóc đổ lên mặt.
- Sửa C++ hay GLSL của DaskToon; sửa shader Unity.
- Nhân vật nằm ngang hoặc quay mặt về +Y khi ở tư thế nghỉ (giả định: đứng thẳng, mặt hướng −Y như chuẩn Blender/VRM).

## 3. Trải nghiệm người dùng

Panel **DaskToon › Bóng mặt** (thanh bên viewport 3D, tab DaskToon), làm việc trên mesh đang chọn:

1. **Tạo bóng mặt anime**: tìm xương đầu, tạo vertex group `DT_Face`, đặt và căn khối trứng, thêm modifier.
2. **Chọn khối trứng**: chọn Empty khối trứng để kéo, xoay, co giãn; bóng cập nhật ngay trong viewport.
3. Bốn thanh trượt (là input của modifier):

| Thanh trượt | Input | Mặc định | Ý nghĩa |
|---|---|---|---|
| Độ phủ | `Coverage` | 1.0 | Mức thay normal bằng normal hình trứng |
| Vùng chuyển | `Falloff` | 0.3 | Độ mềm chỗ giáp mặt với cổ, tai (tính theo bán kính khối trứng) |
| Giữ bóng mũi | `Nose Keep` | 0.6 | Mũi giữ lại normal thật → còn bóng mũi nhỏ |
| Giữ bóng cằm | `Chin Keep` | 0.8 | Mặt dưới cằm giữ normal thật → đường bóng viền hàm gọn |

4. **Căn lại khối trứng**: chạy lại bước tự căn (vị trí, kích thước), giữ các thanh trượt.
5. **Gỡ bóng mặt**: xóa modifier, vertex group `DT_Face`, và khối trứng nếu không còn mesh nào dùng.
6. Mục *Nâng cao*: công cụ cũ "Fix Anime Face Normals" (ghi thẳng vào mesh), "Reset Normals", "Normal Lines". Nếu mesh đang có
   custom normal, panel nhắc dùng **Xóa normal tùy chỉnh cũ** (chính là Reset Normals) để bóng mũi, cằm dựa trên hình khối thật.

Dữ liệu lưới không bị sửa, ngoài vertex group `DT_Face`. Mesh hoặc object link từ thư viện: báo không làm được.

## 4. Tính normal (Geometry Nodes)

Modifier **DaskToon Face Shading** (node group dùng chung `DaskToon_FaceShading`, có số phiên bản như outline), đặt **sau Armature
và trước DaskToon Outline**. Nó tính cho từng góc mặt lưới (domain Corner), trong không gian object:

```
M      = ma trận của khối trứng so với object (Object Info, Relative), L = phần 3×3 của M
q      = M⁻¹ · P            (P: vị trí điểm; khối trứng là mặt cầu đơn vị trong không gian này)
r      = |q|,  d = q / r
n_e    = normalize((L⁻¹)ᵀ · d)                       normal của khối trứng qua điểm đó
down   = normalize(L · (0, 0, −1))                    hướng xuống của khối trứng
region = DT_Face(P) × (1 − smoothstep(1, 1 + Falloff, r))
nose   = smoothstep(0.80, 0.95, −d.y) × smoothstep(0.02, 0.08, r − 1)      phía trước và nhô ra khỏi trứng
chin   = smoothstep(0.25, 0.55, −d.z) × smoothstep(0.35, 0.70, N₀ · down)  nửa dưới và normal thật hướng xuống
w      = Coverage × region × (1 − Nose Keep × nose) × (1 − Chin Keep × chin)
N      = normalize(mix(N₀, n_e, w))
```

- `N₀` là normal hiện có của góc (kể cả custom normal sẵn có). `DT_Face` thiếu thì coi như 0 (không đổi gì).
- Ghi bằng node **Set Mesh Normal** (chế độ Free, domain Corner).
- Khối trứng đọc qua Object Info nên kéo khối trứng là cập nhật ngay. Shape key được tính trước modifier nên biểu cảm không làm
  bóng mặt lem trở lại. Khối trứng gắn vào xương đầu nên bóng đi theo khi quay đầu.

## 5. Tự căn khối trứng

1. **Armature và xương đầu**: lấy armature từ modifier Armature đầu tiên (hoặc parent kiểu armature). Tìm xương theo thứ tự:
   tên đúng (không phân biệt hoa thường) `head`, `j_bip_c_head`, `mixamorig:head`, `頭`; sau đó tên chứa `head` nhưng không chứa
   `end`, `top`, `tip`, `nub`.
2. **Đỉnh của đầu**: các đỉnh có trọng số ≥ 0.5 trong vertex group cùng tên xương đầu. Nếu không có armature, không thấy xương hoặc
   không có đỉnh nào: dùng các đỉnh đang chọn (Edit Mode). Không có cả hai: báo lỗi, hướng dẫn chọn vùng mặt trong Edit Mode.
3. **Vùng da mặt**: trong các đỉnh của đầu, lấy những đỉnh có `|x − tâm_x| ≤ 0.25 × chiều rộng`; đỉnh có `y` nhỏ nhất (nhô ra trước
   nhất, thường là chóp mũi) xác định **mảnh lưới liền** (nối nhau qua cạnh) là da mặt. Toàn bộ mảnh đó được ghi vào `DT_Face` với
   trọng số 1. Tóc, mắt, lông mày, lông mi, răng là mảnh riêng nên bị loại. Vùng chuyển (§4) giới hạn ảnh hưởng ở cổ và thân.
4. **Kích thước** (đỉnh của đầu thuộc mảnh da mặt, toạ độ world):
   - `rx` = nửa chiều rộng, `rz` = nửa chiều cao, tâm x và z ở giữa khung bao.
   - `y_front` = phân vị 5% của y (mặt trước, bỏ chóp mũi), `ry = max(nửa chiều sâu, 0.85 × rx)`, tâm y = `y_front + ry`.
5. **Khối trứng**: Empty hiển thị dạng cầu (display size 1), scale `(rx, ry, rz)`, không render, tên `DT_FaceProxy::<armature>:<xương>`
   (hoặc `DT_FaceProxy::<object>` khi không có xương), cùng collection với mesh, gắn vào xương đầu (giữ nguyên vị trí world).
   **Mỗi xương đầu một khối trứng**: mesh thứ hai cùng xương đầu dùng lại khối trứng có sẵn (không căn lại).
6. Mesh object lưu khối trứng ở ID property `dasktoon_face_proxy`; modifier lưu nó ở input `Proxy`.

## 6. Export sang Unity

Trong `export_model`, **trước** bước ghi `DT_OutlineN/W`, với mỗi mesh có modifier Face Shading đang bật (mỗi mesh data một lần):

1. Lưu dữ liệu thô của attribute `custom_normal` (hoặc ghi nhớ là không có).
2. Tạm thời: mọi armature đang deform các mesh export chuyển sang **Rest Position**; object bật *Shape Key Lock* trên Basis; tắt hiển
   thị các modifier đứng sau Face Shading. Đánh giá depsgraph, đọc normal góc của mesh đã đánh giá.
3. Nếu số góc của mesh đánh giá khác mesh gốc (có modifier đổi topology trước Face Shading, như Mirror, Subdivision): bỏ qua mesh đó,
   cảnh báo nên Apply modifier đó trước.
4. Ghi normal đọc được thành custom normal của mesh gốc (`normals_split_custom_set`). Khôi phục ngay armature, shape key, modifier.
5. Sau khi xuất FBX (kể cả khi lỗi): trả attribute `custom_normal` về dữ liệu đã lưu, hoặc xóa nó nếu trước đó không có.

- Báo cáo ghi các mesh đã ghi bóng mặt. Modifier Face Shading **không** bị liệt kê là "modifier không được áp dụng".
- `.meta` của FBX đặt `blendShapeNormalImportMode: 2` (None) khi có mesh dùng bóng mặt: normal của shape key do Blender ghi là chênh
  lệch normal hình học; Unity cộng vào normal hình trứng thì khi biểu cảm bóng mặt sẽ lem lại. Cái giá: các blend shape khác trong
  cùng file cũng không đổi normal.
- Shader Unity không đổi. `DT_OutlineN` được ghi sau bước 4 nên khung tangent của DaskToon và Unity tính trên cùng bộ normal.

## 7. Tương thích

- Outline: modifier outline luôn đứng cuối (bộ đồng bộ của Dự án 1 tự dời nó xuống cuối); Face Shading chèn ngay trước nó.
- Công cụ cũ vẫn hoạt động; panel cũ bị thay bằng panel mới (công cụ cũ trong *Nâng cao*).
- Không có dữ liệu cũ cần nâng cấp.

## 8. Kiểm thử

**Headless trong DaskToon** (đầu thử: UV sphere có mũi nhô ra, hốc mắt lõm, một mảnh tóc riêng, armature có xương `Head`):

| Nhóm | Nội dung |
|---|---|
| Node group | Vùng mặt có normal khớp `n_e` tính bằng Python (lệch ≤ 1°); ngoài `1 + Falloff` không đổi; Coverage 0 không đổi; Nose Keep giữ normal mũi; Chin Keep giữ normal dưới cằm; di chuyển khối trứng làm normal đổi |
| Tự căn | Tìm xương đầu theo nhiều kiểu tên; `DT_Face` chứa mặt, không chứa mảnh tóc; khối trứng gắn đúng xương; hai mesh dùng chung khối trứng; dự phòng bằng đỉnh đang chọn; báo lỗi khi không có gì; gỡ xóa sạch |
| Thứ tự modifier | Face Shading đứng trước outline; bộ đồng bộ outline không làm xáo trộn |
| Export | Nhập lại FBX thấy normal hình trứng ở tư thế nghỉ; mesh gốc được trả y nguyên (có và không có custom normal trước đó); `.meta` blend shape normal = None; cảnh báo khi có modifier đổi topology; không bị liệt kê là modifier không áp dụng |

**Ảnh duyệt**: đầu thử trước/sau ở 3 góc Sun, và nhân vật tdt trước/sau.

**Unity**: thêm trường hợp "đầu thử có bóng mặt" vào `dasktoon_unity_render_test.py`, lệch ≤ 0.03 như các trường hợp khác.

## 9. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| `DT_Face` tự động bắt nhầm mảnh (mặt dính liền tóc) | Vùng chuyển giới hạn theo khối trứng; người dùng có thể tô lại vertex group |
| Normal node trong Geometry Nodes đọc custom normal khác dự kiến | Kiểm chứng ở task đầu; nếu khác thì đọc `N₀` từ attribute |
| Outline (Dự án 1) đổi hướng đẩy ở vùng mặt vì đọc normal sau Face Shading | Kiểm tra trong test; nếu đổi thì ghi lại và báo cáo |
| Ghi tạm normal khi export làm hỏng mesh nếu lỗi giữa chừng | Khôi phục trong `finally`, có test |

## 10. Nhật ký quyết định

| Quyết định | Nguồn |
|---|---|
| Hướng A: khối trứng điều khiển normal mặt | Người dùng |
| Ranh giới cong mượt, giữ bóng mũi và cằm | Người dùng |
| Thao tác: một nút + thanh trượt + kéo khối trứng | Người dùng |
| Chạy tự động, tự quyết và ghi báo cáo | Người dùng ("tự động") |
| Một khối trứng cho mỗi xương đầu; Empty dạng cầu | Nhóm |
| Export ghi normal tư thế nghỉ tạm thời; blend shape normal = None | Nhóm |
