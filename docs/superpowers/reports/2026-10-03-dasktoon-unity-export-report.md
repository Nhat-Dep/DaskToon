# Báo cáo: Engine Export sang Unity 6 URP và Dự án DaskToon (Dự án 2)

- Nhánh: `dasktoon-unity-export` (chưa push, chưa merge; xếp chồng lên nhánh Dự án 1)
- Kế hoạch: `docs/superpowers/plans/2026-10-03-dasktoon-unity-export.md`
- Spec: `docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md`
- Ảnh so sánh DaskToon và Unity: `docs/superpowers/reports/2026-10-03-unity-compare.png`

## Kết quả

**Cả 13 task đã xong. 22 file test đều PASS**: 8 file của Dự án 1, 10 file headless của Dự án 2, và 4 file chạy trong
Unity 6000.5.4f1 thật (batchmode, trên một project tạm ở `%TEMP%\dasktoon_unity_test`; project của bạn trong `D:\Unity`
không bị đụng tới). Dự án này không sửa C++ hay GLSL nên không cần build lại DaskToon.

| Task | Nội dung | Kết quả |
|---|---|---|
| 1 | Chạy Unity batchmode trên project tạm | ✅ License, URP 17.5, Linear và đọc pixel đều chạy |
| 2 | Ghi `.mat` và các loại `.meta` của Unity | ✅ |
| 3 | Nhận diện project Unity, ghi file không đè file của bạn | ✅ |
| 4 | Shader URP (lõi port từ GLSL, lớp URP, pass outline, 4 shader) và bộ cài shader | ✅ 480 biến thể biên dịch không lỗi (D3D11 và Vulkan) |
| 5 | Đọc graph node thành thông số material | ✅ |
| 6 | Texture dải màu, copy ảnh, bake bằng Cycles | ✅ |
| 7 | Xuất FBX giữ shape key và `DT_OutlineN/W` | ✅ |
| 8 | Ghép toàn bộ export, báo cáo, kiểm tra FBX trong Unity | ✅ |
| 9 | *File › Export › Engine Export…* | ✅ |
| 10 | So sánh render DaskToon và Unity | ✅ |
| 11 | Thư viện Dự án DaskToon | ✅ |
| 12 | Menu và panel Dự án, Engine Export tự trỏ vào dự án | ✅ |
| 13 | Đăng ký test, chạy toàn bộ, báo cáo | ✅ |

## Kiểm chứng trong Unity

- **FBX:** Unity tự gán đúng material đã xuất (không cần Search and Remap), giữ blend shape, đúng trục (đỉnh đầu Blender
  `z = 1` thành `y = 1` trong Unity). Normal outline giải nén từ `DT_OutlineN` theo khung tangent của chính Unity khớp normal
  DaskToon tính sẵn ở **cả 323/323 đỉnh, lệch tối đa 0°**. Vậy MikkTSpace của Unity khớp Blender, không cần phương án dự phòng.
- **Render:** cùng một cảnh (Sun 3.0 màu ấm, World tối), Unity đặt Directional = 3 ÷ π. Sai số tối đa trên giá trị sRGB, ngưỡng 0.03:

| Trường hợp | Sai số | Trường hợp | Sai số |
|---|---|---|---|
| Anime BSDF đơn giản | 0.0001 | Anime Cel đơn giản | 0.001 |
| + Ambient màu riêng | 0.0001 | Anime Cel dải "Anime 2 tông" | 0.0014 |
| + Ambient theo World | 0.025 | Tóc (Anime Cel + Angel Ring) | 0.0013 |
| + Light Overlay | 0.0008 | Anime Eye | 0.0003 |
| + Light Multiply | 0.0023 | Dask Cel đơn giản | 0.0002 |
| + Rim | 0.0081 | Dask Cel dải "Manga" | 0.0002 |
| + Grade | 0.0002 | Outline màu riêng: độ dày / màu | 1.0 px / 0.0001 |
| Dải "Anime 3 tông" | 0.0023 | Outline Harmonic + Light Bleed: độ dày / màu | 1.5 px / 0.004 |
| Dải "Mềm như vẽ" | 0.0125 | AO, specular của Anime Cel (chỉ báo số) | 0.0094 / 0.001 |

  Ranh giới sáng tối lệch nhau dưới 1 pixel, nên các điểm nằm đúng trên ranh giới không tính vào sai số. Độ dày outline lệch
  0.5–1.5 px vì EEVEE làm mờ cạnh (film filter), còn Unity không khử răng cưa; hình dạng giống nhau (mỏng ở phía được chiếu sáng).

## Cách dùng

**Engine Export:** *File › Export › Engine Export…*, chọn engine Unity 6 (URP), FBX hay không, "Chỉ object đang chọn",
"Kèm animation", bake. Chọn thư mục:
- Nếu thư mục nằm trong một project Unity (có `Assets/` và `ProjectSettings/`), DaskToon ghi thẳng vào `Assets/DaskToon/`.
  Chuyển sang Unity là thấy.
- Nếu không, DaskToon tạo `<tên file>_Unity/` kèm `README.txt`. Kéo cả thư mục đó vào cửa sổ Project của Unity.

Sau khi export, popup và Text "DaskToon Engine Export Report" ghi lại cường độ đèn gợi ý (ví dụ "Sun 3.0 → Directional 0.955"),
màu Ambient, material bị bỏ qua, input đã bake và các cảnh báo.

**Dự án:** *File › Dự án DaskToon › Tạo dự án…* (tên, thư mục dự án, project Unity, có lưu file hiện tại vào dự án hay không).
DaskToon cài shader vào project Unity ngay lúc đó. Panel *DaskToon › Dự án* trong thanh bên của viewport 3D liệt kê các file
`.blend` của dự án, có nút **Mở**, **Export model này**, **Cài lại shader**, **Mở thư mục dự án**. Khi file `.blend` nằm trong
dự án, Engine Export tự trỏ vào project Unity của dự án.

## Những việc cần bạn làm

1. **Xem ảnh** `2026-10-03-unity-compare.png`: mỗi hàng là DaskToon | Unity | độ lệch × 5.
2. **Quyết định về lỗi tóc sáng gấp đôi trong DaskToon** (xem mục dưới).
3. **Mở thử trong DaskToon thật** hộp thoại Engine Export và panel Dự án (chế độ headless không kiểm tra được giao diện).
4. **Thử với nhân vật thật của bạn** (có xương, animation, texture) trong một project Unity *bản sao*. Test tự động chỉ dùng quả cầu.
5. Quyết định **merge nhánh** (Dự án 1 trước, rồi Dự án 2).

## Lỗi có sẵn của DaskToon phát hiện trong lúc làm

**Preset tóc (HAIR) sáng gấp đôi.** Preset nối *Anime Cel › Color → Mix (Add) → Emission*. EEVEE vẫn tính closure của node
Anime Cel dù output BSDF của nó không nối đi đâu, nhân với socket Weight ẩn của node, mà socket này mặc định là 1 (Angel Ring
và Anime Eye mặc định là 0). Kết quả: màu cel bị cộng hai lần, tóc gần như trắng toát. Lỗi này có từ trước Dự án 1.
Để Unity giống DaskToon, shader Unity cộng đúng phần thừa đó, lấy theo giá trị Weight. Nếu sau này bạn sửa DaskToon (đổi Weight
về 0, hoặc cho node bỏ closure khi output BSDF không được nối), chỉ cần export lại là Unity theo kịp. Mình đề xuất sửa trong một
việc riêng, vì nó làm thay đổi màu của các material tóc đã có.

**Lỗ hổng AI Bridge** (cho phép chạy code từ xa qua cổng 9998, commit `b9dbe7997f9`) vẫn chưa sửa.

## Các quyết định mình đã tự đưa ra

1. **Input của module đang tắt vẫn được ghi giá trị vào `.mat`.** Trong bản build này, `node.inputs["tên"]` bỏ qua socket bị ẩn,
   nên exporter duyệt từng socket. Nếu sai: chỉ thừa vài thông số.
2. **Test dùng Principled BSDF làm material "không hỗ trợ"**, vì material mới của DaskToon mặc định là Anime BSDF. Chỉ ảnh hưởng test.
3. **Kiểm tra FBX trong Unity lấy renderer duy nhất** khi Unity gộp FBX một object vào gốc prefab mang tên file. Chỉ ảnh hưởng test.
4. **Mục menu được thêm qua class Python của `space_topbar`.** `bl_ui` đăng ký module của mình trước `space_topbar` rồi nuốt lỗi,
   nên nếu dùng `bpy.types` thì mục *Engine Export…* và *Dự án DaskToon* âm thầm không hiện. Không có cái giá nào nếu sai.
5. **Test menu so khớp theo tên module và tên hàm**, vì exporter nào cũng đặt tên `menu_func_export`. Chỉ ảnh hưởng test.
6. **Lúc so render, tắt SRP Batcher trong project tạm.** Ở batchmode, nhiều lần render liên tiếp với batcher bật dùng lại dữ liệu
   material cũ; chính shader Lit của URP cũng bị (emission tràn sang kênh xanh). Game chạy từng frame bình thường nên không bị.
   Chỉ ảnh hưởng test.
7. **Bỏ qua điểm nằm trên ranh giới sáng tối khi so render**, và trượt nếu còn dưới 60% điểm. Nếu sai: một khác biệt chỉ nằm ở
   ranh giới sẽ chỉ thấy trên ảnh so sánh.
8. **Test Unity luôn cài lại shader vào project tạm**, vì chế độ PROJECT giữ bản phiên bản 1 đã cài. Chỉ ảnh hưởng test.
9. **Unity tái hiện lỗi tóc sáng gấp đôi** (mục trên), lấy theo Weight ẩn. Nếu bạn muốn tóc đúng thay vì giống DaskToon hiện tại:
   sửa Weight hoặc node rồi export lại.
10. **Mục *Dự án DaskToon* trong menu File** dùng cùng cách đăng ký với điểm 4.
11. **Lỗi giả định "material link từ thư viện làm export lỗi"** không xảy ra (Blender cho Python sửa dữ liệu link trong bộ nhớ).
    Test vẫn giữ lại để chặn hồi quy.
12. **Giới hạn số texture mỗi pass**: chỉ các input hay dùng texture mới nhận texture trong Unity (Anime BSDF: 11 input, cộng normal
    map và dải màu; pass outline có thêm màu nét và Base Color riêng), để vừa 16 texture unit của GLES và Metal đời cũ. Input khác có nối node sẽ dùng giá trị và có cảnh báo.

## Review cuối

Đây là **tự review** (mình không chạy reviewer độc lập vì bạn chưa yêu cầu dùng subagent). Lượt review tìm ra và đã sửa, mỗi lỗi
có test chạy đỏ trước khi sửa:

1. **Mất dữ liệu:** *Tạo dự án* với "Lưu file hiện tại vào dự án" ghi đè lên một file `.blend` khác cùng tên đã có trong thư mục.
   Giờ DaskToon báo lỗi và không tạo gì.
2. Panel Dự án quét toàn bộ cây thư mục mỗi 2 giây. Nếu project Unity nằm trong thư mục dự án, thư mục `Library` hàng chục nghìn
   file sẽ làm giao diện giật. Giờ bỏ qua `Library/Temp/Logs/...` và giới hạn độ sâu.
3. Một mesh không ghi được dữ liệu outline (ví dụ đã đủ 8 UV map) làm hỏng cả lần export. Giờ chỉ báo lỗi mesh đó.
4. Armature nằm trong collection bị loại trừ làm hỏng xuất FBX. Giờ để nó ra ngoài FBX và cảnh báo.
5. Pass outline của Unity mới chỉ được biên dịch, chưa được render. Đã thêm hai trường hợp outline vào bài so sánh (kết quả ở bảng trên).

Những điểm nhỏ để lại sau:
- Engine Export không có Undo riêng, nên các UV map `DT_OutlineN/W` và material `.Outline` nó thêm gộp vào bước Undo kế tiếp.
- Không có thanh tiến trình khi bake; bake ảnh 4K, 16 sample sẽ làm DaskToon đứng một lúc.
- Trong Unity, material DaskToon bỏ qua đèn phụ tính theo đỉnh, light layer và light cookie.
- Base Color của outline đi qua nhánh bake thì bị bake hai lần.
- `DT_OutlineN` là normal tư thế nghỉ, nên khi blend shape làm méo mesh, outline trong Unity không bám theo như lớp vỏ của DaskToon.
- Ở chế độ PROJECT, shader bị xóa trong Unity chỉ được ghi lại bằng nút **Cài lại shader** hoặc khi xóa `DaskToonShaders.version`.
- Ghi PNG bằng Python thuần ở mức nén 9 nên chậm với ảnh bake 4K.

## Giới hạn

- Chỉ hỗ trợ Unity 6 URP 17.5. Unreal 5 và Godot 4 hiện trong danh sách nhưng báo "sắp có".
- Mẫu graph được hỗ trợ: Material Output nối thẳng Anime BSDF, Anime Cel, Anime Eye, Dask Cel (đi xuyên Reroute), và mẫu tóc.
  Material khác giữ material mặc định của FBX và có tên trong báo cáo.
- AO trong Unity lấy từ SSAO của URP (bán kính là thiết lập chung, không theo AO Distance); specular toon của Anime Cel dùng GGX
  nên vùng sáng hơi khác EEVEE.
- Project Unity phải dùng Linear color space. Export lại sẽ ghi đè mọi chỉnh sửa tay trên các asset DaskToon tạo ra.

## Chạy lại toàn bộ test

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
for t in platform_test shading_test shading_baseline shading_styles_test outline_nodes_test outline_sync_test outline_gamedata_test upgrade_test export_yaml_test export_targets_test export_shaders_test export_graph_test export_textures_test export_fbx_test export_layout_test engine_export_ui_test project_test project_ui_test unity_smoke_test unity_shaders_test unity_model_test unity_render_test; do
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_$t.py >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
```
Bốn test `unity_*` cần Unity 6000.5.4f1 (đường dẫn khác thì đặt biến `DASKTOON_UNITY`); lần đầu tạo project tạm mất khoảng 3 phút.
Mười test headless của Dự án 2 đã được đăng ký với CMake.
