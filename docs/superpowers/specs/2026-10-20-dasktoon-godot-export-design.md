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
