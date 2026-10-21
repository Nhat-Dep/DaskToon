# Xuất sang Godot 4 (2026-10-20)

Người dùng hỏi "thêm export godot?", chọn "Đủ như Unity", duyệt thiết kế trong trò chuyện, "Duyệt, làm tự động". Máy có
Godot 4.7.2 (`D:\Godot_v4.7.2-stable_win64.exe\`); hai dự án Godot của người dùng (`D:\GodotGame`, `D:\gd`) không bị
ghi vào, thử trên một dự án tạm.

## 1. Godot 4.7.2 có sẵn (đã dò)

SpringBoneSimulator3D, SpringBoneCollisionSphere3D, SpringBoneCollisionCapsule3D, LookAtModifier3D,
CopyTransformModifier3D, ConvertTransformModifier3D, BoneTwistDisperser3D, TwoBoneIK3D, SkeletonProfileHumanoid. Phần
phải tự viết: shader anime (Godot Shading Language), sửa chỗ gập, mắt phẳng, miệng 2D.

## 2. Đích

Engine Export, Engine: **Godot 4**. Thư mục chọn nằm trong một dự án Godot (có `project.godot` ở đó hoặc ở trên) thì
ghi vào `<dự án>/DaskToon/` (Godot tự nhập khi được chuyển sang); không thì ghi `<thư mục>/<Tên>_Godot/DaskToon/` để
chép vào gốc dự án. Mọi đường dẫn trong tệp là `res://DaskToon/...`.

```
DaskToon/Shaders/     dasktoon_core.gdshaderinc, anime_bsdf.gdshader, anime_outline.gdshader, ... (chung)
DaskToon/Scripts/     dasktoon_import.gd (nhập), ... (chung)
DaskToon/<Tên>/<Tên>.glb, <Tên>.glb.import, <Tên>.dasktoon.json
DaskToon/<Tên>/Materials/<vật liệu>.tres
DaskToon/<Tên>/Textures/<vật liệu>_<ô>.png
```

## 3. Model và nhập

Model ghi bằng glTF nhị phân (bộ xuất glTF có sẵn của Blender): lưới, khung, biểu cảm (hình mẫu), đoạn chuyển động.
`<Tên>.glb.import` chỉ Godot dùng `dasktoon_import.gd` làm script sau khi nhập: script đọc `<Tên>.dasktoon.json`, thay
vật liệu từng mặt bằng vật liệu DaskToon theo tên, và (đợt 3) gắn lò xo, sửa chỗ gập, mắt, miệng. Người dùng kéo `.glb`
vào cảnh là có nhân vật đầy đủ.

## 4. Vật liệu và shader

Mỗi vật liệu DaskToon thành một ShaderMaterial `.tres`, giá trị và ảnh lấy từ phân tích vật liệu dùng chung với Unity
(`graph.analyze_material`), cùng tên thuộc tính đổi sang kiểu Godot (`_BaseColor` → `base_color`, `_DT_ShadowColor` →
`shadow_color`...). Shader viết lại từ `DaskToonCore.hlsl`: màu nền và màu bóng qua `varying` sang `light()`, mỗi đèn
cộng bóng anime vào `DIFFUSE_LIGHT`, ánh sáng môi trường tự tính (tắt ánh sáng môi trường mặc định). Viền: vật liệu
`next_pass` đẩy đỉnh theo pháp tuyến, cull mặt trước.

## 5. Đợt

1. Đích, glb, ảnh, vật liệu Anime BSDF và viền, script nhập gắn vật liệu; thử: dự án tạm, Godot nhập không cửa sổ, script
   Godot kiểm tra cảnh và vật liệu; ảnh chụp trong cửa sổ Godot.
2. Anime Cel, mắt, Dask Cel; khung xương, đoạn chuyển động (nhịp anime), biểu cảm.
3. Tóc đung đưa (SpringBoneSimulator3D và khối va chạm), sửa chỗ gập, mắt nhìn theo và mắt phẳng, miệng 2D.
4. Model thật, ảnh chụp, báo cáo.

## 6. Quyết định (tự động)

1. glTF thay cho FBX: là định dạng Godot nhập tốt nhất (biểu cảm, khung, chuyển động, nội suy bậc).
2. Script nhập thay cho cảnh `.tscn` dựng sẵn: không phụ thuộc tên nút Godot đặt khi nhập, và kéo `.glb` là đủ.
3. Bộ lò xo, nhìn theo... dùng nút có sẵn của Godot để người dùng chỉnh được bằng công cụ của Godot.
4. Đợt 1 chỉ có Anime BSDF: vật liệu loại khác dùng Anime BSDF với màu của chúng và báo trong báo cáo xuất.

Đợt 1, đo trên Godot 4.7.2 rồi quyết:

5. Nhiều đèn: Godot tính từng đèn riêng, không có bước sau cùng để tô bóng anime trên tổng ánh sáng như DaskToon. Mỗi
   đèn tô bóng với (ánh sáng World + đèn đó); kết quả sáng nhất được giữ. Một đèn thì đúng như DaskToon (đo: chênh tối đa
   0,017 trên ảnh sRGB, ngưỡng 0,03). Sai nếu cảnh có nhiều đèn cùng chiếu một chỗ: chỗ đó lấy đèn sáng nhất thay vì
   tổng.
6. Ánh sáng World đi vào tham số World Ambient của mỗi vật liệu (màu World × độ mạnh); ánh sáng môi trường của Godot tắt
   (`ambient_light_disabled`). Không ghi vào `project.godot` của người dùng.
7. Đèn: DirectionalLight3D energy = Sun ÷ π, màu đèn ghi dạng sRGB (đo: `LIGHT_COLOR` = màu × energy × π). Báo cáo xuất
   gợi ý con số này.
8. Godot không cho bật tắt cull và trong suốt theo vật liệu: mỗi kiểu là một tệp shader nhỏ
   (`anime_bsdf[_cull][_clip|_blend].gdshader`) cùng đọc `anime_bsdf.gdshaderinc`. Các module (Ramp, Ambient, Light,
   Rim, Grade) là công tắc trong vật liệu.
9. AO: Godot không cho shader tự viết đọc độ che khuất; module AO không vẽ gì, báo cáo xuất cảnh báo.
10. Tên vật liệu: bộ xuất glTF chỉ giữ tên khi xuất cả vật liệu (`export_materials='EXPORT'`, không kèm ảnh); vật liệu
    đó bị script nhập thay ngay.
11. Viền: Godot đọc TEXCOORD_2 trở đi vào CUSTOM0–2 (hai bản đồ một kênh) và glTF lật trục V; shader viền đọc lại đúng
    kênh và lật về (đo: hướng viền lệch dưới 2° so với DaskToon).
12. Thư mục `res://DaskToon` là của DaskToon: xuất lại ghi đè trong đó; riêng `<Tên>.glb.import` giữ những gì Godot đã
    ghi (uid, lựa chọn của người dùng), chỉ đặt lại dòng script nhập.
13. Dự án DaskToon gắn được project Godot (cần `project.godot`), cài shader vào `res://DaskToon`.

Đợt 2:

14. Anime Cel (kèm vòng sáng tóc), mắt anime, Dask Cel có shader riêng, cùng cách tô "đèn sáng nhất thắng" như Anime
    BSDF. So với DaskToon trên 20 quả cầu mẫu: chênh tối đa 0,017 (ảnh sRGB). Ảnh DaskToon được cắt ở mức 1 trước khi
    so, vì ảnh chụp Godot là ảnh màn hình (chỗ vượt trắng hiện trắng ở cả hai).
15. Clip: mỗi clip được phát rồi "nướng" từng khung hình (nhịp anime và ràng buộc xương nằm sẵn trong khoá), thành một
    hoạt cảnh tên clip trong `.glb`. Các clip được đặt ở những khoảng thời gian không chồng nhau khi xuất, vì bộ xuất glTF
    đọc biểu cảm của lưới mà khung xương điều khiển trong lúc phát track của khung xương (mọi track biểu cảm cùng phát);
    trong Godot mỗi clip vẫn bắt đầu từ 0 giây. Phần tóc, váy Godot tự đung đưa được giữ yên khi nướng, như Unity.
16. Godot lấy mẫu lại hoạt cảnh khi nhập: `animation/fps` của `.glb.import` đặt bằng fps của cảnh. Script nhập cho clip
    lặp thì lặp, clip có nhịp anime thì giữ hình từ khung này sang khung kia (nội suy NEAREST).
17. Lưới có bóng mặt: biểu cảm không đổi pháp tuyến (như Unity).
18. Biểu cảm sửa chỗ gập (`DT_Fix_*`) chưa chạy trong Godot cho tới đợt 3; không có bản đồ xương Humanoid của Godot (tên
    xương là tên chuẩn DaskToon).
