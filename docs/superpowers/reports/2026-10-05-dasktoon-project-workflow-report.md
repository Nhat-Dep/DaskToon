# Báo cáo: quy trình hướng dự án DaskToon (phần 2)

- Nhánh: `dasktoon-project-workflow`, tách từ `dasktoon-ui-reorganization` (Phần 1, chưa merge).
- Spec: `docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md`
- Kế hoạch: `docs/superpowers/plans/2026-10-05-dasktoon-project-workflow.md` (10 task, chạy tự động, mỗi task một commit,
  chưa push).
- Bản cài `D:\build_windows_x64_vc17_Release\bin\Release` đã được build lại và đồng bộ, dùng được ngay.

## Tóm tắt

- DaskToon giờ làm việc theo dự án. Mở DaskToon là thấy màn hình đầu hai cột: dự án bên trái, model của dự án đang chọn
  bên phải.
- Tạo mới là tạo model trong một dự án. Mở và lưu đều đi qua dự án, dù bằng menu File, phím tắt, tìm bằng F3 hay hộp
  thoại hỏi lưu khi thoát.
- File `.blend` nằm ngoài mọi dự án vẫn mở được, nhưng chỉ là **bản nháp**. Lưu bản nháp thì phải chọn dự án; model được
  lưu vào `Models/` của dự án đó, file gốc không bị ghi đè.
- Dự án tự chứa đủ texture: khi lưu, ảnh nằm ngoài dự án được chép vào `Textures/` và đường dẫn ảnh thành đường dẫn tương
  đối.
- Tạo dự án không cần Unity. Gắn Unity sau trong Project Settings; shader được cài khi gắn.
- Script, add-on và test vẫn mở và lưu như Blender: lõi chỉ chuyển hướng khi lệnh được gọi từ giao diện.

## Cách dùng

**Màn hình đầu.** Khi chưa có dự án nào, cột phải ghi "Create or open a project" và New Model bị mờ:

![Màn hình đầu khi chưa có dự án](project-workflow/en/11_start_screen_empty.png)

Khi đã có dự án: dự án đang chọn có dấu tròn đặc. Bấm một dự án khác thì màn hình mở lại với các model của dự án đó.
Continue as Draft đóng màn hình đầu và giữ cảnh đang mở như một bản nháp:

![Màn hình đầu với dự án Hero](project-workflow/en/12_start_screen.png)

**Menu File.** New Project…, New Model…, Open…, Open Recent, Models, các lệnh Save, và menu con Project ở cuối. Phím tắt
hiện đúng như Blender, kể cả **Ctrl N** cạnh New Model…:

![Menu File](project-workflow/en/13_file_menu.png)

**File › Project:** tên dự án, engine, phiên bản shader đã cài, Project Settings…, Export This Model, Reinstall Shaders,
Open Project Folder:

![File › Project](project-workflow/en/09_file_project.png)

**New Project.** Location mặc định là chỗ đặt dự án lần trước, lần đầu là `Documents/DaskToon Projects`. Unity Project để
trống được. Bấm OK thì DaskToon tạo `<Location>/<Name>/` với `dasktoon_project.json`, `Models/`, `Textures/`, rồi mở ngay
hộp thoại New Model:

![New Project](project-workflow/en/14_new_project.png)

**New Model.** Model được lưu ngay thành `Models/<Name>.blend` và thành file đang mở. Start From có bốn lựa chọn:
- **DaskToon Scene**: cảnh trống có một Sun, một camera nhìn vào gốc tọa độ, engine DaskToon Anime, view Standard;
- **Empty Scene**: cảnh trống hoàn toàn;
- **Current Scene**: lưu chính cảnh đang mở làm model mới;
- **Copy of Model**: bắt đầu từ bản sao một model khác của dự án.

![New Model](project-workflow/en/15_new_model.png)

**Bản nháp.** Thanh trên cùng, trước ô chọn scene, ghi "Draft (not in a project)". Khi đang mở một model, nhãn này thành
"Hero › Hero_Armor". Ctrl+S trên bản nháp mở hộp thoại Save to Project:

![Save to Project](project-workflow/en/16_save_to_project.png)

**Texture.** Mọi lần lưu từ giao diện đều chép trước vào `Textures/` các ảnh nằm ngoài dự án: Save, Save to Project, Save
Model As, Save Copy, Save Incremental, nút Save của hộp thoại hỏi lưu. Tên trùng mà nội dung khác thì thêm `_1`, `_2`…;
file giống hệt từng byte thì dùng lại; ảnh UDIM chép đủ mọi tile. Chuỗi ảnh và ảnh mất file chỉ được cảnh báo. Thanh trạng
thái báo, ví dụ, "Copied 3 textures into Textures/".

**Gắn Unity sau.** Dự án chưa gắn Unity ghi "Engine: not linked". Export This Model hoặc Reinstall Shaders khi chưa gắn sẽ mở
Project Settings; gắn xong (OK) thì lệnh ban đầu tự chạy tiếp.

Bản giao diện tiếng Việt có cùng tên ảnh trong `project-workflow/vi/`. Menu con Project hiện là "Dự án", không phải "Phóng
Chiếu" như bản dịch có sẵn của Blender (xem phần quyết định).

## Khác Blender ở đâu

| Thao tác | Blender | DaskToon bây giờ |
|---|---|---|
| Ctrl+N | Menu New File (template) | Menu New: New Model…, New Project… |
| Ctrl+O | Hộp chọn file `.blend` | Hộp chọn file của DaskToon: `.blend` hoặc `dasktoon_project.json`, mở sẵn ở `Models/` của dự án đang chọn |
| Shift+Ctrl+O | File gần đây | Model gần đây (tối đa 10), rồi dự án gần đây (tối đa 8) |
| Ctrl+S | Lưu tại chỗ, file mới thì hỏi chỗ lưu | Model: chép texture rồi lưu tại chỗ. Bản nháp: Save to Project |
| Shift+Ctrl+S | Save As (hộp chọn file) | Save Model As: lưu thành `Models/<tên>.blend` trong cùng dự án |
| Ctrl+Alt+S | Save Incremental (`Hero1.blend`) | Save Incremental (`Hero_001.blend`, `Hero_002.blend`…), mờ khi đang là bản nháp |
| Hộp thoại hỏi lưu, nút Save | Lưu tại chỗ | Model: lưu qua dự án rồi làm tiếp. Bản nháp: mở Save to Project và dừng việc đang làm; lưu xong thì làm lại |
| Màn hình đầu | New File, Recent Files, link web; bấm không đóng | Dự án và model; bấm một mục là đóng |

Kéo thả, nhấp đúp và mở từ dòng lệnh vẫn mở file ngay: file trong dự án là model, file ngoài dự án là bản nháp.

## Thay đổi C++ và lý do

| File | Thay đổi | Vì sao |
|---|---|---|
| `wm_files.cc` | Thuộc tính ẩn `use_project_redirect` cho `wm.read_homefile`, `wm.open_mainfile`, `wm.save_mainfile`, `wm.save_as_mainfile`; khi được *invoke* thì chuyển sang lệnh DaskToon tương ứng | Bắt được mọi đường của người dùng (menu, phím tắt, F3, cả keymap Industry Compatible) mà không sửa file keymap; exec không bị chuyển nên script vẫn như Blender |
| `wm_files.cc` | Thuộc tính ẩn `post_read_operator` cho `wm.read_homefile`, `wm.open_mainfile` | New Model (DaskToon Scene, Empty, Copy) gọi lệnh của Blender để Blender tự hỏi lưu, rồi hoàn tất trong file mới. Bấm Cancel thì không có model nào bị tạo dở |
| `wm_files.cc` | Nút Save của hộp thoại hỏi lưu gọi `dasktoon.project_save` | Lưu khi thoát hay khi mở file khác cũng đi qua dự án và chép texture |
| `wm_splash_screen.cc` | Màn hình đầu không còn giữ mở sau khi bấm (Quick Setup vẫn giữ) | Python không đóng được popup; trước đây bấm một dự án sẽ chồng thêm một màn hình đầu |
| `space_topbar.cc` | Bỏ menu C++ Open Recent (đã có bản Python); vẽ lại thanh trên cùng khi lưu hoặc mở file | Python không thay được menu C++ cùng tên; trước đây nhãn "Draft" không đổi sau khi lưu |
| `interface.cc` | Mục New Model… hiện phím tắt Ctrl N của menu New | Chữ phím tắt chỉ lấy được từ keymap, mà spec cấm sửa keymap và muốn Ctrl+N mở menu New |

## Kiểm thử

- Toàn bộ test DaskToon trong `tests/python/CMakeLists.txt`: **34 file, 303 test, tất cả OK**. Trước phần này: 30 file,
  244 test. Test mới:
  - thư viện dự án: không cần Unity, `Models/`/`Textures/`, dự án cũ, thứ tự model, tên, model gần đây, `settings.json`,
    gắn Unity sau;
  - chép texture: chép và đổi sang đường dẫn tương đối, trùng tên, trùng hệt, trùng chỉ khác hoa thường, UDIM, video, chuỗi
    ảnh, file mất, ảnh packed/tạo trong Blender/thư viện/trong dự án, ảnh đang vẽ dở;
  - lõi: bốn lệnh có công tắc chuyển hướng; exec vẫn lưu, mở, đọc như Blender khi lệnh DaskToon đang đăng ký;
    `post_read_operator` chạy sau khi đọc và không chạy khi đọc lỗi;
  - New Model với bốn cảnh khởi đầu, tên trùng, ký tự lạ, tên tiếng Việt, khi `Models/` bị chặn, khi chưa có dự án;
  - bản nháp, Save to Project (file gốc giữ nguyên từng byte), Save, Save Model As, Save Copy, Save Incremental, Open,
    model gần đây, model mất file dự án thành bản nháp;
  - giao diện: màn hình đầu hai trạng thái, menu File, menu New, Open Recent, Project, Models, nhãn thanh trên cùng, khớp
    phím tắt giữa menu File và keymap Blender/Industry Compatible, bản dịch cả cho các lớp Blender đã viết lại.
- **Test có cửa sổ** (`tests/python/dasktoon_project_window_test.py`, chạy riêng vì cần màn hình): OK. Nó bấm phím thật:
  - Ctrl+N mở menu New của DaskToon;
  - Ctrl+O mở hộp chọn file của DaskToon;
  - Ctrl+S trên bản nháp mở Save to Project, và file nháp giữ nguyên;
  - hộp thoại hỏi lưu với model: Save lưu model rồi mới mở model khác;
  - hộp thoại hỏi lưu với bản nháp: Save mở Save to Project và dừng việc mở file;
  - Ctrl+Q: Save lưu model rồi thoát.

  Lệnh chạy: `"$PY" tests/python/dasktoon_project_window_test.py "$DT"`.
- **Thử bằng mô phỏng chuột:**
  - bấm một dự án khác trên màn hình đầu thì màn hình mở lại với model của dự án đó;
  - bấm Continue as Draft thì màn hình đóng hẳn, không còn bản nào chồng bên dưới;
  - nhãn thanh trên cùng đổi từ "Draft (not in a project)" sang "Beta › Topbar" ngay sau khi lưu vào dự án.
- **Ảnh chụp** bản tiếng Anh và tiếng Việt (ở trên).

## Quyết định tự đưa ra

Kế hoạch đã chọn sẵn những chỗ spec để ngỏ (bảng "Quyết định của kế hoạch" ở cuối kế hoạch). Tóm lại:

| Quyết định | Cái giá nếu sai |
|---|---|
| Sửa thêm 3 file C++ ngoài `wm_files.cc` (màn hình đầu, Open Recent và thanh trên cùng, chữ Ctrl N) | Ba chỗ lệch thêm khỏi Blender gốc khi cập nhật Blender |
| Thêm thuộc tính `post_read_operator` để New Model hoàn tất sau hộp thoại hỏi lưu của Blender | Một thuộc tính C++ mới phải giữ khi cập nhật Blender |
| Save Incremental đặt `Hero_001.blend` theo spec, không theo `Hero1.blend` của Blender | Khác thói quen của người quen Blender |
| Menu Project dùng ngữ cảnh dịch riêng "DaskToon" | Không |
| Lưu sang file mới (Save to Project, Save Model As, Save Copy, Current Scene) không hiện hộp thoại "lưu ảnh đã sửa" của Blender; DaskToon cảnh báo tên ảnh có nét vẽ chưa lưu | Người dùng phải tự lưu ảnh đó (Image › Save) |
| Models, Project và Engine Export dùng dự án được chọn, kể cả khi đang là bản nháp (dự án chọn gần nhất, hoặc dự án gần đây nhất) | Export This Model từ một bản nháp xuất vào Unity của dự án đó |
| Model gần đây được ghi khi mở hoặc lưu file, bỏ qua khi chạy nền | Không |
| Để trống Unity Project trong Project Settings là bỏ gắn | Lỡ xóa ô thì phải gắn lại |

Quyết định phát sinh khi làm:

| Quyết định | Vì sao | Cái giá nếu sai |
|---|---|---|
| Làm ngay trên nhánh, không tạo worktree riêng | Thư mục build duy nhất gắn với `D:\DaskToon` | Không |
| Kiểm tra "có người dùng để hỏi" bằng `bpy.app.background` cộng với có cửa sổ | Khi chạy nền vẫn có một cửa sổ trong context và Blender chạy execute thay cho invoke. Nếu không kiểm, New Project sẽ tự tạo model, còn Export sẽ chạy Project Settings với ô trống | Không (trong giao diện, cả hai điều kiện đều đúng) |
| Test có cửa sổ tìm lại cửa sổ sau mỗi lần đọc file và tự đánh dấu file đã sửa | Bản đầu giữ cửa sổ cũ nên DaskToon crash khi mô phỏng phím sau khi mở file khác. Lệnh gọi từ script cũng không đánh dấu file đã sửa, nên hộp thoại hỏi lưu không hiện | Không (chỉ là test) |
| Công cụ chụp ảnh đổi thư mục ra thành đường dẫn tuyệt đối; chờ màn hình vẽ xong và bỏ qua thanh trạng thái khi cắt ảnh popup | `Image.save()` của Blender báo thành công nhưng không ghi gì với đường dẫn tương đối kiểu này; ảnh cắt bị dính cả viewport | Không |

## Còn để lại

- Ngoài phạm vi theo spec: chép thư viện `.blend` được Link vào dự án; đổi tên, xóa, di chuyển model ngay trong DaskToon;
  tự dời file của dự án cũ vào `Models/`; Unreal, Godot; chép chuỗi ảnh.
- Bản dịch có sẵn của Blender cho vài chữ không hẳn đúng nghĩa ở đây:
  - "Open Recent" thành "Mở Tập Tin Gần Đây", trong khi menu giờ liệt kê model và dự án;
  - ô Engine trong Project Settings thành "Động Cơ" (đã vậy từ Phần 1).
- Tên model trong ô chọn Copy of Model có thể bị dịch nếu trùng một chữ có sẵn trong bản dịch của Blender (hiếm).
- Test có cửa sổ không nằm trong danh sách CMake vì cần màn hình.

## Việc cần làm

- Mở DaskToon từ bản cài như thường. Lần đầu sẽ thấy màn hình đầu chưa có dự án: bấm New Project để bắt đầu.
- Chọn merge, mở PR hay giữ nhánh. Phần 1 (`dasktoon-ui-reorganization`) chưa merge và nhánh này nằm trên nó: merge Phần 1
  trước, hoặc merge cả hai cùng lúc.
