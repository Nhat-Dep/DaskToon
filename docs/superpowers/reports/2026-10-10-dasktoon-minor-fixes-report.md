# DaskToon: sửa các lỗi nhỏ còn lại và cảnh báo scale, báo cáo

- Ngày: 2026-10-10, làm tự động sau khi người dùng duyệt "sửa hết các lỗi nhỏ đã biết" và "thêm cảnh báo mesh scale âm/không
  đều" (spec rig §16 mục 4, 6).
- Nhánh: `dasktoon-minor-fixes`, tách từ `dasktoon-spring-constraint` (`f328c25ca55`), nên nằm chồng lên nhánh constraint
  Spring. Chưa push, chưa merge.
- Kế hoạch: `docs/superpowers/plans/2026-10-10-dasktoon-minor-fixes.md`.

## 1. Đã sửa

Rig trong DaskToon:

| Lỗi | Sửa | Test |
|---|---|---|
| Bấm Fit to Parts trong Edit Mode thì armature về Object Mode | Xong việc thì object đang active trở lại mode cũ của nó | `test_fit_in_edit_mode_stays_in_edit_mode` |
| Danh sách phần lặp tên object khi trùng tên phần ("Body Body") | Tên object chỉ hiện khi khác tên phần | `test_parts_list_names_the_object_only_when_it_differs` |
| Mesh thân quay mặt vào trong làm weight tự động chọn sai xương mà không báo gì | Build Rig cảnh báo: "Body: the faces of the body point inward…" | `MeshWarningTest` |
| Chưa cảnh báo mesh có scale âm hay không đều (spec §12) | Build Rig cảnh báo cho mọi mesh của các phần: "… has a negative or non-uniform scale: apply its scale (Object › Apply › Scale) before building and exporting to Unity" | `MeshWarningTest` |
| Dời rig mà không đặt key thì giật một nhịp; bán kính collider không theo scale của rig | Đã hết nhờ constraint Spring (báo cáo rig §8) | trong `dasktoon_spring_constraint_test.py` |

Lắc trong Unity:

| Lỗi | Sửa | Test |
|---|---|---|
| Game tạm dừng (`Time.deltaTime = 0`) thì tóc còn trôi theo quán tính | Bước có `dt <= 0` không làm gì | `pausedDrift` trong Unity thật |
| Thêm file `.rig.json` sau model mà không xuất lại thì Unity không import lại model | Trình import có `OnPostprocessAllAssets`: file rig đến một mình thì import lại model bên cạnh; model đến cùng lượt thì tự đọc file | `CheckLateRig` trong Unity thật |
| Bản script cũ đã cài trong project Unity | `SCRIPTS_VERSION` lên 2, nên lần xuất sau thay bản 1 | `test_older_scripts_are_replaced`; project thử chuyển từ 1 lên 2 |

Phần 2 (dự án):

| Lỗi | Sửa | Test |
|---|---|---|
| Màn hình đầu và Open Recent gọi dự án theo tên thư mục, dự án đổi tên vẫn hiện tên cũ | Hiện tên lưu trong `dasktoon_project.json`; file không đọc được thì tên thư mục | `test_recent_lists_show_the_project_name`, `test_project_label_is_the_name_or_the_folder` |
| Nhãn thanh trên cùng đọc lại `dasktoon_project.json` mỗi lần vẽ | `load()` nhớ lần đọc cuối theo thời điểm sửa và kích thước file; DaskToon lưu file thì bỏ bản nhớ. Danh sách gần đây và các menu cũng hưởng | `test_load_reads_the_file_again_only_when_it_changed`, `test_loaded_projects_are_copies` |
| Ctrl+Alt+S (Save Incremental) trên bản nháp không làm gì, không báo gì | Save Incremental và Save Copy luôn chạy được và báo "This file is a draft: save it into a project first"; menu File vẫn làm mờ hai mục này | `test_copy_and_incremental_on_a_draft_say_why` |

Chữ mới có bản Việt (3 mục).

## 2. Kiểm thử

- Toàn bộ suite CMake: 44 file (429 test) đều qua, cộng script nạp module.
- Test Unity thật (Unity 6000.5.4f1): rig (thêm `pausedDrift` và `CheckLateRig`) và model qua. Trước khi sửa, chạy test với
  script cũ thì đỏ đúng chỗ: tóc trôi 2,3e-5 m sau một bước dừng; file rig thêm sau cho 0 spring bone thay vì 9.
- Test cảnh báo mới được chạy đỏ trước khi viết code, trên nhân vật thử (tách và gộp: không cảnh báo nào; Body lật mặt:
  đúng một cảnh báo; Skirt scale không đều và Ribbon scale âm: đúng hai cảnh báo).
- Chụp lại `24_rig_panel.png` (tiếng Anh, tiếng Việt) trong `docs/superpowers/reports/anime-rig/`: danh sách phần không còn
  tên lặp.

## 3. Quyết định Claude tự chốt

- **Cách nhận ra mặt quay vào trong**: tỉ lệ thể tích có dấu trên tổng thể tích không dấu của các tam giác thuộc phần Body, ở
  world, quanh tâm của chúng. Đo trên nhân vật thử: mặt hướng ra cho khoảng +1,0 (kể cả ống hở hai đầu), lật mặt cho −1,0,
  thẻ tóc phẳng gần 0. Ngưỡng cảnh báo −0,5. Chỉ xét phần Body, vì chỉ Body dùng weight tự động (bone heat).
- Mesh có scale âm không xét mặt quay vào trong: soi gương thì pháp tuyến tính ở world lật lại, và cách chữa là Apply Scale,
  điều mà cảnh báo scale đã nói.
- Bộ nhớ file dự án đặt trong module dự án (không chỉ ở thanh trên), trả bản sao để chỗ gọi sửa rồi không lưu không làm hỏng
  bản nhớ. Góc khuất: file bị sửa bên ngoài hai lần, cùng kích thước, trong cùng một nhịp đồng hồ của hệ thống tệp thì lần sau
  chưa thấy, cho tới lần đổi kế tiếp.
- "Model và file rig đến cùng lượt thì không import hai lần" dựa vào danh sách `importedAssets` của Unity; không có test đếm số
  lần import.

## 4. Review (tự review)

Phiên này không tạo subagent khi người dùng chưa yêu cầu, nên đây là tự review, yếu hơn một reviewer độc lập.

- Không có lỗi Critical/Important.
- Để lại (Minor): nếu object active trước đó không vào lại được mode cũ (ví dụ vừa bị ẩn) thì Fit to Parts đã khớp xong
  nhưng báo lỗi lúc trả mode.

## 5. Còn lại

- Hai nhánh chờ người dùng chọn merge, mở PR hay giữ: `dasktoon-spring-constraint` (constraint Spring), rồi
  `dasktoon-minor-fixes` (chồng lên nó).
- Tiếp theo theo thứ tự đã duyệt: **A**, tab Animation gọn (tiếp từ phần thiết kế 3: Key Pose và keying set), rồi **R3** mắt
  và miệng, B, C.
