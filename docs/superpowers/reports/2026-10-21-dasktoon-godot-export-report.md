# Báo cáo: Xuất sang Godot 4 (2026-10-21)

Bạn hỏi "thêm export godot?", chọn "Đủ như Unity", rồi duyệt thiết kế và cho làm tự động. Thiết kế và các quyết định:
`docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md` (28 quyết định, có ghi lý do và cái giá nếu sai).

## Cách dùng

1. Tệp › Xuất › **Xuất sang engine…**, mục Engine chọn **Godot 4**.
2. Chọn thư mục:
   - nằm trong một dự án Godot (có `project.godot`): DaskToon ghi thẳng vào `res://DaskToon` của dự án đó;
   - thư mục khác: DaskToon tạo `<Tên>_Godot/DaskToon`, bạn chép thư mục `DaskToon` vào gốc dự án Godot.
3. Mở dự án trong Godot. Godot tự nhập; kéo `DaskToon/<Tên>/<Tên>.glb` vào cảnh là có nhân vật đầy đủ.
4. Đặt đèn như báo cáo xuất gợi ý: DirectionalLight3D, energy = độ mạnh Sun ÷ π.

Dự án DaskToon cũng gắn được dự án Godot (**Cài đặt dự án**, mục Engine chọn Godot 4).

Cần Godot 4.4 trở lên, bộ vẽ Forward+ hoặc Mobile. Đã thử với Godot 4.7.2.

## Godot nhận được gì

- **Model** dạng glTF (.glb): lưới, khung xương, biểu cảm. Các lưới của nhân vật được gộp làm một như khi xuất Unity.
- **Vật liệu DaskToon**: Anime BSDF, Anime Cel (kèm vòng sáng trên tóc), mắt anime, Dask Cel, và **viền**. Mỗi vật liệu là
  một tệp `.tres` chỉnh được trong Godot; ảnh tô đi kèm.
- **Ánh sáng môi trường**: màu World của cảnh DaskToon được ghi vào từng vật liệu (mục World Ambient), không dùng ánh
  sáng môi trường của Godot.
- **Clip**: mỗi clip thành một hoạt cảnh trong AnimationPlayer, cùng tên. Clip lặp thì lặp; clip có **nhịp anime** (vẽ
  hai, vẽ ba…) thì giữ hình đúng từng khung.
- **Biểu cảm** đang bật trong DaskToon thì cũng bật trong Godot.
- **Tóc, váy lắc**: dùng bộ lò xo có sẵn của Godot với đúng các số của DaskToon và các khối va chạm. Tuỳ chọn "Lắc trong
  Unity" đổi tên thành **Lắc trong game** vì dùng cho cả Godot.
- **Sửa chỗ gập** (gối, khuỷu, hông, vai), **mắt phẳng** (tròng mắt trượt theo xương mắt) và **miệng 2D** (đổi ô
  miệng): một script của DaskToon chạy trên khung xương.

## Kiểm tra

**20 quả cầu mẫu** (bộ dùng khi so với Unity), chụp trong DaskToon và trong Godot:
`docs/superpowers/reports/2026-10-21-godot-compare.png` (cột trái DaskToon, giữa Godot, phải là chỗ khác nhau phóng to
5 lần). Chênh lệch màu lớn nhất 0,017 trên thang 0–1, ngưỡng cho phép 0,03. Viền khớp độ dày và màu.

**Sửa chỗ gập**: 11 tư thế (gối, hông, khuỷu, vai, gập sâu), trọng số trong Godot lệch với DaskToon dưới 0,01.

**Mắt phẳng, miệng 2D**: quay mắt sang trái 20° và lên 10°, tròng mắt trượt đúng con số của bài thử Unity; ô miệng 3
hiện đúng.

**Clip**: clip đi bộ vẽ hai giữ mỗi hình đúng hai khung; biểu cảm của clip này không lọt sang clip khác.

**Model thật**: bản sao của luna (tóc, váy lắc) và tdt (ảnh tô thật, bóng mặt). Mỗi nhân vật đổi mọi vật liệu sang
shader anime, thêm một clip "Sway" (người lắc qua lại, vẽ hai), xuất vào một dự án Godot tạm. Ảnh so sánh chỉ để trong
máy (ngoài git):

- `docs/superpowers/reports/real-model/godot/luna_dasktoon_vs_godot.png`
- `docs/superpowers/reports/real-model/godot/tdt_dasktoon_vs_godot.png`

Thứ tự trong mỗi ảnh: DaskToon nhìn trước, Godot nhìn trước, Godot đang lắc, Godot nhìn chéo. Đo vài điểm trên luna (mặt,
váy, tóc, chân): chênh 0–3 trên 255.

**Lỗi tìm ra trên model thật, đã sửa và có phép thử:**

1. Lần nhập đầu tiên, Godot nhập model trước ảnh, nên vật liệu mất ảnh (báo lỗi "Failed loading resource"). Nay script
   nhập gắn vật liệu theo đường dẫn, Godot tự nạp khi mở model.
2. tdt đang để mắt hơi nhắm ("blink" 0,419); Godot bỏ qua giá trị đó và mở mắt. Nay biểu cảm đang bật được đặt lại.
3. Khối va chạm của tóc nằm lệch xuống nửa xương, vì Godot không lưu độ dời của nó lúc nhập. Nay script của DaskToon
   đặt lại khi game chạy.
4. Hai lọn tóc của luna mọc từ đỉnh đầu, nằm trong khối va chạm của đầu: bộ lò xo của Godot hất chúng văng 35 cm, vắt
   ngang mặt (Live Sway của DaskToon để chúng rủ yên). Nay lọn nào mọc từ trong khối nào thì bỏ qua khối đó. Lọn lệch
   nhiều nhất giờ là 16 cm.

Trong lúc làm cũng sửa: Godot tự "nén" hoạt cảnh khi nhập và bỏ mất khung (ô miệng 1, 3, 4 thành 1, 3, 3); nay tắt việc
nén cho model của DaskToon.

## Chưa giống DaskToon

- **Nhiều đèn chiếu cùng một chỗ**: Godot tính từng đèn riêng; chỗ đó lấy màu của đèn sáng nhất, không cộng như DaskToon.
  Một đèn thì giống hệt.
- **AO** (tối ở góc khuất) không vẽ được: Godot không cho shader tự viết đọc độ che khuất. Báo cáo xuất có cảnh báo.
- **Bóng đổ**: bóng tóc đổ lên mặt trong Godot nhạt hơn EEVEE (tdt). Tắt bóng đổ ở cả hai thì mặt gần như giống nhau.
- **Lọn số 6 của luna** lệch 16 cm do khối va chạm của cổ, DaskToon lệch 4 cm.
- Mắt trái tdt dưới tóc mái hơi khác màu; chưa rõ lý do.
- Chưa có mắt nhìn theo mục tiêu (bản Unity cũng chưa có; có thể tự thêm nút LookAtModifier3D của Godot) và chưa có bản
  đồ xương Humanoid của Godot.
- Chưa thử bộ vẽ Compatibility của Godot.

## Sau báo cáo: màu luna

Bạn hỏi "màu luna?": luna trong Godot (và trong DaskToon sau khi bấm Dùng shader DaskToon) xám hơn bản gốc. Godot đúng
như DaskToon; chỗ mất màu là nút đổi shader, vì nó chỉ lấy ảnh màu, bỏ qua hai nhóm nút toon của luna (nhân màu với chính
nó). Đã sửa nút này: chuỗi nút riêng được chép lại với ánh sáng của cảnh cho Màu nền và Màu bóng. Luna gốc đổi shader
xong gần như trùng bản gốc (chênh trung vị 4/255). Ảnh trong máy:
`docs/superpowers/reports/real-model/godot/luna_original_vs_converted.png`.

## Phép thử

- `dasktoon_godot_export_test` (20 bài): đích, tệp, vật liệu, ảnh, viền, cull và trong suốt, báo cáo, gộp lưới, biểu cảm;
  Godot nhập thật, gắn đúng vật liệu, không lỗi nạp ảnh, hướng viền khớp DaskToon dưới 2°.
- `dasktoon_godot_clips_test` (6 bài): clip, nhịp anime, lặp, biểu cảm, không nén mất khung.
- `dasktoon_godot_rig_test` (7 bài): lò xo, khối va chạm, sửa chỗ gập, mắt phẳng, miệng 2D.
- `dasktoon_godot_render_test`: so 20 quả cầu với DaskToon (Godot mở một cửa sổ nhỏ để vẽ).
- Toàn bộ 89 tệp phép thử qua.
