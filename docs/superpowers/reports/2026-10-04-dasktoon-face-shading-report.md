# Báo cáo: bóng mặt anime bằng khối trứng (Face Shading)

- Ngày: 2026-10-04
- Nhánh: `dasktoon-face-shading` (tách từ `dasktoon-unity-export`, chưa push, chưa merge)
- Spec: `docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md`
- Kế hoạch: `docs/superpowers/plans/2026-10-04-dasktoon-face-shading.md`
- Chạy: tự động, inline, commit từng task; rà soát cuối là **tự rà** (không có reviewer độc lập)

## 1. Đã làm được gì

Bóng trên mặt giờ đi theo một **khối trứng** ôm lấy đầu thay vì theo từng chỗ lồi lõm của mũi, má, hốc mắt:

- Ranh giới sáng tối trên mặt cong mượt.
- Vẫn còn bóng mũi nhỏ và bóng dưới cằm.
- Khối trứng gắn vào xương đầu nên bóng đi theo khi quay đầu.
- Export sang Unity ra giống trong DaskToon.

Không sửa shader nào: Anime BSDF, Anime Cel, Dask Cel và shader thường đều hưởng lợi vì chỉ normal của mặt thay đổi.

## 2. Cách dùng

Panel **DaskToon › Bóng mặt** ở thanh bên viewport 3D (phím N, tab DaskToon):

1. Chọn mesh nhân vật, bấm **Tạo bóng mặt anime**. DaskToon sẽ:
   - tìm xương đầu;
   - tạo vertex group `DT_Face` (mảnh da mặt);
   - đặt một khối trứng (Empty hình cầu) gắn vào xương đầu;
   - thêm modifier **DaskToon Face Shading**.
2. Chỉnh bằng 4 thanh trượt:
   - **Độ phủ**: mức thay normal;
   - **Vùng chuyển**: độ mềm chỗ giáp cổ, tai;
   - **Giữ bóng mũi**;
   - **Giữ bóng cằm**.

   Hoặc bấm **Chọn khối trứng** rồi kéo, xoay, co giãn nó (G / R / S); bóng cập nhật ngay.
3. **Căn lại khối trứng** đặt lại vị trí và kích thước, giữ nguyên thanh trượt. **Gỡ bóng mặt** xóa sạch.
4. Công cụ cũ ("Fix Anime Face Normals", Reset Normals, Normal Lines) nằm trong mục **Nâng cao**.

**Nhân vật không có rig (như tdt):** vào Edit Mode, chọn vùng đầu (có thể chọn cả tóc), rồi bấm **Tạo bóng mặt anime**.
DaskToon tự lọc lấy mảnh da mặt. Khối trứng khi đó gắn vào chính mesh.

**Nếu panel báo "Mesh còn custom normal cũ":** bấm **Xóa normal tùy chỉnh cũ**. Lý do: bóng mũi và cằm được giữ lại từ
normal hiện có của mesh, nên custom normal cũ (ví dụ từ công cụ cũ hay từ file VRM/FBX) sẽ thay cho hình khối thật.
Mesh `Circle` của tdt đang có custom normal như vậy.

**Export:** Engine Export tự ghi normal hình trứng ở **tư thế nghỉ** vào FBX rồi trả mesh về nguyên trạng. Không cần Apply
modifier. File `.meta` của FBX tắt normal của blend shape (xem mục 6).

## 3. Đã kiểm chứng

| Hạng mục | Kết quả |
|---|---|
| Toàn bộ test DaskToon (21 file trong `tests/python/CMakeLists.txt`) | **193/193 OK** |
| Test mới: node group / tạo-căn-gỡ-panel-outline / export | 12 / 27 / 9 test |
| Node group so với công thức spec tính bằng numpy | lệch tối đa 0.0004° (ngưỡng 1°) |
| Unity 6000.5.4f1, so render: trường hợp `face_shading` | **lệch 0.0001** trên 43 điểm (ngưỡng 0.03) |
| Unity, hai trường hợp outline sau khi đổi lõi outline | 1.0 px / 0.0001 và 1.5 px / 0.004, **y hệt Dự án 2** |
| Unity, nhập FBX (model test) | OK |
| Nhập lại FBX trong DaskToon | normal ≤ 1° so với normal tư thế nghỉ; khi đang tạo dáng, normal lệch trung bình 29° nên test phân biệt được |

**Ảnh duyệt:** `docs/superpowers/reports/2026-10-04-face-shading-review.png`. Có 3 cột, mỗi cột một góc đèn Sun.

| Hàng | Nội dung | Nhận xét |
|---|---|---|
| 1 | Đầu thử gồ ghề (gò má, cung mày, môi, cằm, nhiễu), chưa có bóng mặt | Bóng lem nhem |
| 2 | Đầu thử, có bóng mặt | Bóng mượt hơn; chính giữa mặt vẫn còn vài cục, xem mục 6 |
| 3 | tdt, chưa có bóng mặt | |
| 4 | tdt, có bóng mặt | Đèn trước-phải: mặt sáng đều, mất vệt mũi. Đèn bên: mặt vào bóng đều, mất vệt sáng dưới mắt. Đèn trước-trái: ranh giới cong hơn |

`tdt.blend` chỉ được mở để render, không lưu (mốc thời gian vẫn là 2026-10-03 23:51).

## 4. Các quyết định mình tự đưa ra

Mỗi dòng gồm: quyết định, lý do, và cái giá nếu sai.

1. **Lõi outline lên phiên bản 2.**
   - Thay đổi: vỏ outline đẩy theo normal hình học (True Normal) và được tô bằng normal đảo của nguồn.
   - Lý do: node Normal trả về custom normal, nên khi Face Shading đứng trước outline thì vỏ ở vùng mặt sẽ lệch theo normal
     hình trứng, trong khi Unity đẩy theo `DT_OutlineN`. Ngoài ra Flip Faces không đảo custom normal, còn pass outline của
     Unity tô bằng `-normal`.
   - Cái giá: outline của những mesh vốn đã có custom normal đổi hướng và màu trong DaskToon (về phía cái Unity vẽ). Với mesh
     không có custom normal, kết quả không đổi (đã đo trong Unity).
2. **Gán lại node group sau khi ghi input của modifier từ Python.**
   - Lý do: bản 5.2 này không tự tính lại và không dựng lại quan hệ depsgraph khi input bị ghi từ Python (đã kiểm chứng).
   - Cái giá: thêm một lần tag depsgraph.
3. **Chỉ dùng vùng chọn khi đang ở Edit Mode.**
   - Lý do: ở Object Mode, vùng chọn lưu trong mesh thường là "tất cả".
   - Cái giá: phải vào Edit Mode mới dùng được phương án dự phòng.
4. **Không có xương đầu thì khối trứng gắn vào chính mesh.**
   - Lý do: spec không nói gắn vào đâu.
   - Cái giá: phải tự gắn lại nếu muốn khác.
5. **Nhận ra khối trứng có sẵn bằng dấu riêng và parent, không bằng tên.**
   - Lý do: đổi tên armature không được sinh khối trứng thứ hai.
   - Cái giá: không thấy.
6. **Vùng chuyển nhỏ nhất là 0.01.**
   - Lý do: Map Range chia cho 0 khi Vùng chuyển = 0, sẽ làm bóng trứng tràn khắp `DT_Face`.
   - Cái giá: không có điểm cắt cứng tuyệt đối.
7. **Căn lại giữ `DT_Face` như người dùng đã tô.**
   - Thay đổi: chỉ dựng lại `DT_Face` khi nó trống.
   - Cái giá: một `DT_Face` cũ, sai vẫn điều khiển việc căn cho tới khi xóa.
8. **Node group có input `Mask Name` (mặc định `DT_Face`) mà panel không hiện.**
   - Lý do: để trỏ sang vertex group tự tô từ panel modifier.
   - Cái giá: thêm một ô trong panel modifier.
9. **Thiếu khối trứng thì không chặn trong Geometry Nodes.**
   - Thay đổi: panel báo "Chưa có khối trứng".
   - Lý do: thiếu khối trứng nghĩa là một quả cầu 1 m quanh gốc object; với nhân vật gốc ở chân thì không ảnh hưởng.
   - Cái giá: mesh chỉ có đầu, gốc ở đầu, sẽ có normal hình cầu cho tới khi Căn lại.
10. **Tạo và Căn lại tính ở tư thế nghỉ.**
    - Lý do: căn trên đầu đang quay sẽ đặt sai khối trứng.
    - Cái giá: không thấy.
11. **"Bật" khi export nghĩa là modifier hiện trong viewport.**
    - Lý do: export đánh giá depsgraph viewport, thấy gì ghi nấy.
    - Cái giá: modifier chỉ bật khi render sẽ không được export.
12. **Hai chốt chặn cho việc chọn mảnh da mặt.** Đây là sai lệch thật so với spec 5.3, phát hiện khi chạy trên tdt.
    - Vấn đề: quy tắc spec "đỉnh nhô trước nhất ở dải giữa" chọn trúng một lọn tóc mái, nên khối trứng chỉ rộng 3 cm.
    - Thay đổi: ưu tiên mảnh có nhiều đỉnh bị shape key biểu cảm làm dịch chuyển nhất; bỏ qua các mảnh hẹp hơn ¼ bề rộng đầu.
    - Cái giá: nếu tóc có shape key riêng và nhiều đỉnh dịch chuyển hơn mặt thì sẽ chọn nhầm tóc; khi đó tô lại `DT_Face`.
13. **Ảnh duyệt có hai phần chỉ dành cho script ảnh duyệt, không phải code sản phẩm.**
    - tdt không có rig, nên script giả lập việc người dùng chọn vùng đầu: lấy mọi đỉnh từ đỉnh thấp nhất mà shape key biểu
      cảm làm dịch chuyển trở lên.
    - Đầu thử được làm gồ ghề, vì đầu thử gốc gần như là quả trứng nên ảnh trước và sau trông như nhau.
14. **Sửa hàm dựng đầu thử.** `create_uvsphere` dùng lại slot đỉnh đã giải phóng, làm đỉnh tóc xen lẫn đỉnh da. Giờ dựng hai
    phần riêng rồi ghép lại. Chỉ ảnh hưởng test.
15. **Thanh trượt cập nhật ngay trong giao diện: kết luận từ đọc code, chưa bấm thử.**
    - Lý do tin được: thuộc tính runtime có cờ IDPROPERTY nên sửa trong giao diện sẽ tag GEOMETRY.
    - Cái giá nếu sai: phải xoay viewport mới thấy thay đổi.
16. **Giữ nguyên công thức spec coi mọi chỗ nhô ra trong nón ±37° phía trước là "mũi".**
    - Hệ quả: môi, giữa cung mày, giữa cằm giữ lại 60% normal thật ở mức Giữ bóng mũi mặc định. Thấy được ở hàng 2 của ảnh
      duyệt.
    - Cái giá: muốn vùng miệng sạch hơn thì phải giảm Giữ bóng mũi, và bóng mũi cũng nhạt theo.

Ngoài ra kế hoạch đếm sai số test ở 3 chỗ; không thiếu test nào.

## 5. Rà soát cuối và sửa

Mình tự rà toàn nhánh. Đây là tự rà của chính người viết code, yếu hơn một reviewer độc lập; bạn quyết định có cần thêm
một lượt review trước khi merge không.

**Đã sửa**, mỗi lỗi có test đỏ trước, xanh sau:

- Vùng chọn không có đỉnh nào ở dải giữa (ví dụ chỉ chọn hai mắt) trước đây văng lỗi Python; giờ báo
  "Không thấy da mặt ở giữa vùng đầu…".
- Nếu ghi normal lỗi giữa chừng khi có nhiều mesh, các mesh đã ghi trước đó không được trả lại; giờ được trả lại.

**Để lại** (nhỏ, chưa sửa):

- Export chỉ material (không FBX) vẫn ghi rồi trả normal, và báo cáo export vẫn liệt kê dòng "Bóng mặt".
- Armature link từ thư viện không chuyển được sang Rest Position, nên mesh nó điều khiển sẽ được ghi bóng mặt theo tư thế
  hiện tại mà không cảnh báo.
- Nếu đã có một modifier khác (không phải Geometry Nodes) đặt đúng tên "DaskToon Face Shading", mỗi lần Tạo sẽ thêm một
  modifier ".001".
- Nếu sửa node group `DaskToon_FaceShading` và xóa mất một input (ví dụ Proxy), panel sẽ báo lỗi Python.

## 6. Giới hạn còn lại

- **Blend shape trong FBX không đổi normal.** `.meta` đặt `blendShapeNormalImportMode: 2` cho cả file khi có mesh dùng bóng
  mặt; nếu không, biểu cảm sẽ làm bóng mặt lem lại trong Unity. Các blend shape khác trong cùng file cũng không đổi normal.
- **Modifier đổi số đỉnh** (Mirror, Subdivision…) đứng trước Face Shading thì mesh đó không được ghi bóng mặt; export cảnh
  báo và gợi ý Apply.
- **Giả định nhân vật đứng thẳng, mặt hướng −Y** ở tư thế nghỉ (như spec).
- **Mới thử trên Unity 6000.5.4f1**, chưa thử trên project Unity 6.6 của bạn.

## 7. Bảo mật (nhắc lại)

Lỗ hổng **AI Bridge** (cổng 9998, commit `b9dbe7997f9`) vẫn **chưa sửa**: bất kỳ chương trình nào trên máy gửi tới cổng đó
đều chạy được code Python trong DaskToon. Nên sửa trước khi phát hành.

## 8. Việc bạn cần làm

1. Xem ảnh duyệt `docs/superpowers/reports/2026-10-04-face-shading-review.png`.
2. Thử trên tdt:
   - mở file, chọn `Circle`, vào Edit Mode, chọn vùng đầu, bấm **Tạo bóng mặt anime**;
   - bấm **Xóa normal tùy chỉnh cũ** nếu muốn bóng mũi, cằm theo hình khối thật;
   - kéo thử khối trứng và các thanh trượt.
3. Export lại tdt sang Unity. Bản sửa lỗi Shadow Color bị bake đen (commit `25ec498cfe4`) cũng cần export lại mới có tác dụng.
4. Chọn cách xử lý ba nhánh: `dasktoon-shading-outline` (Dự án 1), `dasktoon-unity-export` (Dự án 2) và
   `dasktoon-face-shading` (nhánh này, tách từ Dự án 2). Mỗi nhánh: merge cục bộ, push và mở PR, hoặc giữ nguyên.

## 9. Các commit

```
ff748b2dce0 fix: report a selection without a middle instead of crashing, and give back written meshes when the normal bake fails
782fdddaa48 test: compare face shading between DaskToon and Unity, and render a before/after review sheet
423a557803f fix: pick the face island by its expression shape keys and pass over narrow islands such as a lock of hair
034e7410c67 feat: export face shading to Unity as rest-pose ellipsoid normals and give the mesh back afterwards
d393e74297c fix: push the outline hull along geometric normals and shade it with the negated source normal (outline core v2)
a90686fd7e9 feat: add the DaskToon › Bóng mặt panel and operators; the old face normal tools move under Nâng cao
8af395e80ae feat: fit the face shading proxy to the head, write DT_Face, and set up, refit or remove face shading
58df36de716 feat: add the DaskToon_FaceShading Geometry Nodes group that leans face normals towards an ellipsoid proxy
72069c85dcb docs: add the implementation plan for anime face shading
28570ad8b72 docs: add the design spec for anime face shading driven by an egg-shaped proxy
```
