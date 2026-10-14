# DaskToon: thử trên mô hình thật và bốn lỗi đã sửa — Báo cáo

Nhánh `dasktoon-real-model-fixes` (từ `dasktoon-anime-rig-r3`), kế hoạch
`docs/superpowers/plans/2026-10-13-dasktoon-real-model-fixes.md`. Không push, không merge.

## 1. Thử trên gì, thử thế nào

- Mô hình: `D:\game\lagote rabina\tdt.blend` (nhân vật chibi cao 2,95 m, tư thế chữ A, da và váy là hai mesh; da không
  có phần thân dưới váy). Fit còn được thử trên `lr_shape.blend` (cùng nhân vật, 8 mesh, quần thay váy).
- Mọi bước làm trên **bản sao** trong thư mục tạm: mở file gốc rồi "Save As" ngay sang bản sao (để đường dẫn texture
  được đổi theo), không lưu lại file gốc. Đã kiểm tra: `tdt.blend` gốc giữ nguyên (md5 như trước, ngày sửa 5/10).
- Quy trình như người dùng: Add › Anime Humanoid, thêm các mesh làm phần (vai trò đoán theo tên), **Fit to Parts tự
  động** (lần trước phải sửa khớp bằng tay), Build Rig, clip Talk (khẩu hình từ file giọng nói), clip Wave (giơ tay
  phải, vẽ on twos, lặp), render, Engine Export vào project Unity tạm của harness, Unity đọc lại.

## 2. Kết quả, trước và sau

| Lỗi tìm ra lần trước | Trước | Sau |
|---|---|---|
| Clip dính tư thế của clip khác | Talk giữ cánh tay Wave đang giơ; trong `@Talk.fbx` khung đầu RightUpperArm w = 0,574 | Talk ở khung 1 tay về nghỉ; `@Talk.fbx` w = 1,000; `@Wave.fbx` vẫn giơ (w nhỏ nhất 0,643) |
| Fit to Parts theo hộp bao | Tay chữ T ngang tai, khớp tay cách bàn tay 0,7–0,87 m; cột sống lùi sau lưng 0,3 m (hộp tính cả tai, tóc) | Tay theo ống tay xuống tới bàn tay: khớp cổ tay, đầu ngón cách bề mặt 0,5–2,2 cm (tdt và lr_shape); cột sống trong thân; hai bên đối xứng |
| Weight áo theo cánh tay | Giơ tay kéo cả mảng váy: 1026 trên 1773 đỉnh thân váy có weight cánh tay trên > 0,2 | 152 đỉnh, đều ở hai bên ngực ngay dưới vai (z 1,8–2,09), chỗ weight tự động vốn pha với cánh tay |
| Hành động nhanh theo m/s tuyệt đối | Nhân vật cao 2,95 m vượt ngưỡng khắp nơi, vệt phủ cả tay và váy (ngưỡng phải hạ tay xuống 1,0 mới thấy rõ chỗ nhanh) | Thiết lập mặc định: ngưỡng và độ dày vệt nhân 2,95 / 1,6; vệt chỉ ở bàn tay đang vung |

Thêm: Unity nhận model Humanoid hợp lệ; Talk dài 10,1 s; Wave lặp, tiếp tuyến hằng (on twos). Fit mất 0,3–0,6 s,
Build 2–3 s. Khẩu hình vẫn chạy (5 shape key nguyên âm).

## 3. Ảnh so sánh

Ảnh có nhân vật của bạn nên **không đưa vào git** (VS Code Sync đẩy thẳng lên GitHub): nằm ở
`docs/superpowers/reports/real-model/`, thư mục này được bỏ qua bằng `.git/info/exclude` (chỉ trên máy này).

- `1_fit_front_before_after.png`: khung xương nhìn từ trước, trái là Fit cũ (hộp bao), phải là Fit mới.
- `2_fit_side_before_after.png`: nhìn từ bên: cột sống cũ sau lưng, mới trong thân; hai chân trùng nhau (đối xứng).
- `3_wave_before_after.png`: clip Wave khung 5, trái là lần thử trước (khớp đã sửa tay, weight cũ), phải là bây giờ.
- `4_fast_action_before_after.png`: hành động nhanh khung 5, trái ngưỡng 1,0 và mật độ 0,15, phải thiết lập mặc định.
- `5_talk_after.png`: clip Talk khung 1, 69, 105.

## 4. Đã sửa gì

1. **Clip** (`dasktoon_animation/clips.py`): khi dùng một clip, những gì clip khác của nhân vật key mà clip này không key
   về nghỉ: biến đổi của xương, giá trị shape key, custom property (như `dt_mouth`). Cái không clip nào key giữ nguyên.
   Xuất clip dùng đúng hàm này nên file FBX sạch.
2. **Fit to Parts** (`dasktoon_rig/body_shape.py`, mới): đọc bóng nhìn từ trước của các phần Body và Clothing. Tâm thân
   theo trung vị đỉnh. Đi từ đầu ngón tay (hoặc đế chân) dọc bóng tới chỗ bóng nở ra (chạm thân): đoạn đi qua cho đường
   tay, chân. Khuôn tay chân được xoay, co giãn lên đó; cột sống giãn giữa hông và vai tìm được (hợp đầu to chibi). Hai
   bên lấy trung bình với bên kia lật qua, nên khung đối xứng. Không tìm được thì giữ khuôn cũ. Khi ghi khớp, X-Axis
   Mirror tạm tắt (nó lật mỗi bên quanh giữa armature, không phải giữa nhân vật: lỗi có từ trước).
3. **Weight áo** (`dasktoon_rig/weights.py`): đỉnh áo cách Body tới 2% chiều cao Body thì chép Body như cũ; xa hơn thì pha
   dần sang weight tự động tính trên chính phần áo (trên một bản sao), từ 4% trở lên dùng hẳn.
4. **Hành động nhanh** (`dasktoon_animation/fast_action.py`): ngưỡng và độ dày vệt tính cho nhân vật cao 1,6 m, nhân theo
   chiều cao nhân vật lúc nghỉ; độ dài vệt là thời gian nên tự theo tốc độ; mật độ vệt mặc định 0,08 (trước 0,15).

## 5. Quyết định tôi đã đưa ra (tự động)

- Clip: chỉ đưa về nghỉ xương, shape key, custom property; vị trí của chính object (ví dụ cái mũ) giữ nguyên dù clip khác
  key nó, vì không có "nghỉ" rõ ràng cho chỗ đứng của object. *Nếu sai:* một vật được key trong một clip giữ chỗ cuối ở
  clip khác.
- Clip: chọn lại đúng clip đang dùng (hay tạo clip mới, trống) cũng đưa về nghỉ, để màn hình và file xuất chỉ phụ thuộc
  clip. *Nếu sai:* chỉnh tay chưa key trên một xương mà clip khác có key sẽ mất khi chọn lại clip.
- Fit: đọc tay chân từ bóng nhìn trước thay cho "dải đỉnh ngoài vai + PCA" như kế hoạch, vì dải cố định cần biết trước
  vai rộng và cao bao nhiêu, mà chibi không giống khuôn. *Nếu sai:* tay ép sát thân không tìm được, giữ tay khuôn.
- Fit: hông đặt cao hơn chỗ chân chạm thân 10% chiều dài chân (trên tdt đó là mép váy, đáy chậu thật bị che). *Nếu sai:*
  đùi gập lệch vài cm; Edit Joints sửa được.
- Fit: tìm được một bên thì bên kia lấy đối xứng; tìm được cả hai thì lấy trung bình đối xứng. *Nếu sai:* nhân vật dựng
  lệch hai bên ở tư thế nghỉ được khớp đối xứng.
- Weight áo: **bỏ** quy tắc "tam giác cùng hướng" đã duyệt. Đo trên tdt cho thấy nguyên nhân khác: da không có phần thân
  dưới váy, váy chép weight từ da cổ, vai cách 14–42 cm. Quy tắc cùng hướng không đổi gì trên tdt và làm tóc của
  lr_shape tệ hơn. Thay bằng quy tắc theo khoảng cách ở trên. *Nếu sai:* áo phồng xa da (tay áo bồng) dùng weight tự động
  của chính nó thay vì chép da tay.
- Weight áo: bỏ cảnh báo "không có bề mặt Body để chép weight" (các đỉnh đó giờ có weight tự động).
- Hành động nhanh: không nhân độ dài vệt (là thời gian); chiều cao lấy theo hộp bao các mesh lúc nghỉ, đọc khi đổi thiết
  lập hoặc bật; không tăng phiên bản node group.

## 6. Còn lại, chưa sửa

- lr_shape: mesh tóc `NurbsPath.005` được đoán vai trò Clothing (tên không gợi tóc). Với quy tắc mới nó dùng weight tự
  động của chính nó, 194 đỉnh gần thân có tới 0,39 weight cánh tay. Đặt vai trò Hair (hoặc Accessory) là hết.
- tdt: cột sống nằm ở nửa trước của thân (trung vị đỉnh bị chi tiết mặt trước váy kéo ra trước).
- Vệt tốc độ trên bàn tay vẫn dày khi tay vung mạnh on twos: mật độ tính theo số đỉnh, mesh dày đỉnh thì nhiều vệt.
- Material.014 (dùng node group) vẫn không xuất sang Unity (đã biết từ lần trước, không thuộc bốn lỗi).
- 292 đỉnh da tdt không được bone heat giải, nhận xương gần nhất (đều ở đầu, vô hại, như lần trước).

## 7. Test

- Mới, đều thấy hỏng trước khi sửa: `dasktoon_clips_test` (chuyển clip đưa về nghỉ), `dasktoon_export_clips_test` (mỗi
  file clip bắt đầu từ nghỉ), `dasktoon_rig_skeleton_test` (chibi chữ A; hai bên đối xứng), `dasktoon_rig_ui_test` (gậy
  là Accessory không thành tay), `dasktoon_rig_build_test` (váy không có da bên dưới; áo sát da vẫn chép),
  `dasktoon_fast_action_test` (theo cỡ nhân vật).
- Toàn bộ test Python của DaskToon trên nhánh này: 57 file, 558 test, đều đạt (R3 có 550, thêm 8 test mới).
- Unity (project tạm của harness): model Humanoid hợp lệ, hai clip đọc đúng (mục 2).
