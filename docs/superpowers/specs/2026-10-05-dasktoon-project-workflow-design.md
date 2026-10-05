# DaskToon: quy trình hướng dự án (Phần 2)

- Ngày: 2026-10-05
- Trạng thái: thiết kế đã được duyệt trong chat (7 câu hỏi, hướng làm, 3 phần thiết kế)
- Nhánh: `dasktoon-project-workflow`, tách từ `dasktoon-ui-reorganization` (`c98536dc5e7`, Phần 1 chưa merge)
- Phần 1: `docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md`. Dự án gốc:
  `docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md`, mục 7.

## 1. Mục tiêu

Dự án DaskToon là cửa duy nhất để làm việc với file. Người dùng mở DaskToon thì thấy dự án và model của dự án. Tạo mới là
tạo model trong một dự án, mở là mở dự án hoặc model, lưu là lưu vào dự án. Không còn New/Open/Save file `.blend` rời
theo kiểu Blender.

Kết quả mong muốn:

1. **Bắt buộc dự án.** Mọi file người dùng lưu đều nằm trong một dự án. File ngoài dự án mở được nhưng chỉ là **bản
   nháp**: lưu thì phải chọn dự án, file gốc không bị ghi đè.
2. **Màn hình đầu hai cột** (dự án | model) thay nội dung màn hình chào của Blender.
3. **Mọi đường mở/lưu người dùng chạm tới** đều đi qua dự án: menu File, phím tắt, tìm bằng F3, hộp thoại hỏi lưu khi
   thoát hoặc đổi file.
4. **Script vẫn mở/lưu như Blender**, để add-on, test và mã DaskToon vẫn chạy.
5. **Dự án tự chứa đủ texture**: ảnh nằm ngoài dự án được chép vào `Textures/` khi người dùng lưu.
6. **Dự án không cần Unity khi tạo**; gắn Unity sau.

DaskToon không còn đi theo Blender gốc, nên được sửa thẳng file Python và C++ của Blender khi cần.

## 2. Phạm vi

**Trong phạm vi:**
- thư viện `scripts/modules/dasktoon_project/`;
- giao diện `scripts/startup/bl_ui/dasktoon_project.py`;
- màn hình đầu (`WM_MT_splash` trong `scripts/startup/bl_operators/wm.py`);
- menu File và thanh trên cùng (`scripts/startup/bl_ui/space_topbar.py`);
- chặn trong lõi (`source/blender/windowmanager/intern/wm_files.cc`);
- bản dịch tiếng Việt, test, công cụ chụp ảnh `tools/dasktoon_ui_screenshots.py`.

**Ngoài phạm vi:**
- Chép vào dự án các thư viện `.blend` được Link từ ngoài dự án (Link/Append giữ như Blender).
- Đổi tên, xóa, di chuyển model ngay trong DaskToon (dùng Open Project Folder).
- Tự dời file của dự án cũ vào `Models/`.
- Unreal, Godot (vẫn "coming soon").
- Chép chuỗi ảnh (image sequence) vào dự án.

## 3. Khái niệm

| Khái niệm | Nghĩa |
|---|---|
| Dự án | Thư mục có `dasktoon_project.json` |
| Model | Một file `.blend` trong thư mục dự án. Model mới luôn ở `Models/<tên>.blend` |
| Bản nháp | Cảnh đang mở chưa thuộc dự án nào: chưa từng lưu, hoặc file `.blend` nằm ngoài mọi dự án |
| Dự án đang mở | Dự án chứa file đang mở (`find_project(bpy.data.filepath)`) |
| Dự án được chọn | Dự án đang mở; nếu đang là bản nháp thì là dự án chọn gần nhất trong phiên (màn hình đầu, Open Project, New Project); nếu chưa chọn thì dự án gần đây nhất |

## 4. Cấu trúc dự án và dữ liệu

```
<Tên dự án>/
  dasktoon_project.json
  Models/      model mới (<tên>.blend)
  Textures/    ảnh được chép vào khi lưu
```

- **`dasktoon_project.json`** giữ định dạng version 1 của Phần 1:
  `{"version": 1, "name": "Hero", "engines": [{"engine": "UNITY_URP", "path": "D:/Unity/Game"}]}`.
  `engines` được phép là `[]` khi chưa gắn Unity.
- **Thư mục cấu hình DaskToon** (`config_dir()`, ghi đè bằng `DASKTOON_CONFIG_DIR` khi test):
  - `recent_projects.json`: tối đa 8 dự án (đã có);
  - `recent_models.json`: tối đa 10 model, mới nhất trước. Model được thêm khi mở hoặc lưu;
  - `settings.json`: `{"project_location": "<thư mục>"}`, nơi đặt dự án lần trước.
- **Danh sách model của dự án:**
  - file trong `Models/` trước, theo tên;
  - rồi tới các `.blend` khác trong dự án, kèm đường dẫn tương đối (dự án cũ để `.blend` ở gốc);
  - bỏ qua `.blend1`, thư mục ẩn, thư mục cache của Unity, và `Textures/`.
- **Dự án cũ** (tạo ở Phần 1, có `.blend` ở gốc, `engines` có Unity):
  - mở và dùng như thường;
  - DaskToon tạo `Models/` và `Textures/` khi cần (lúc tạo model mới hoặc chép texture);
  - không dời file cũ.

## 5. Màn hình đầu

`WM_MT_splash` vẽ màn hình đầu của DaskToon (ảnh đầu do C++ vẽ, giữ nguyên). Menu Help › Splash Screen cũng hiện màn
hình này. Màn hình Quick Setup lần chạy đầu của Blender giữ nguyên.

```
┌─────────── (ảnh DaskToon) ───────────┐
│ Projects          │ Hero              │
│  New Project…     │  New Model…       │
│  Open Project…    │  Hero             │
│  Recent           │  Hero_Armor       │
│  ▸ Hero           │  Sword            │
│    School Girl    │                   │
├───────────────────┴───────────────────┤
│ Recover Last Session  Continue as Draft│
└───────────────────────────────────────┘
```

- **Cột trái:** New Project…, Open Project…, nhãn "Recent", tối đa 8 dự án gần đây. Dự án được chọn có dấu. Bấm một
  dự án khác thì nó thành dự án được chọn và màn hình mở lại với cột phải của dự án đó.
- **Cột phải:**
  - tên dự án được chọn;
  - New Model…;
  - danh sách model; bấm là mở (có hỏi lưu nếu file đang mở có thay đổi).
  - Chưa có dự án nào: cột phải ghi "Create or open a project" và New Model bị mờ.
- **Dưới cùng:** Recover Last Session; **Continue as Draft** (đóng màn hình, cảnh hiện tại là bản nháp).
- Bỏ khỏi màn hình đầu: New File (General và template ứng dụng), Recent Files, Open…, các link web của Blender.

## 6. Lệnh của dự án

| Lệnh | bl_idname | Việc làm |
|---|---|---|
| New Project… | `dasktoon.project_create` | Hộp thoại: **Name**, **Location** (mặc định là nơi đặt lần trước, hoặc `Documents/DaskToon Projects`), **Unity Project** (không bắt buộc). Tạo `<Location>/<Name>/` cùng `dasktoon_project.json`, `Models/`, `Textures/`. Có Unity thì cài shader. Thêm vào dự án gần đây, đặt làm dự án được chọn, rồi mở hộp thoại New Model với tên gợi ý bằng tên dự án |
| Open Project… | `dasktoon.project_open` | Chọn `dasktoon_project.json` (hoặc thư mục dự án). Đặt làm dự án được chọn, thêm vào gần đây, mở màn hình đầu với dự án đó |
| (chọn dự án ở màn hình đầu) | `dasktoon.project_select` | Như Open Project nhưng không mở hộp chọn file |
| Open… | `dasktoon.open` | Hộp chọn file `.blend` hoặc `dasktoon_project.json`. `.blend` trong dự án thì mở như model; `.blend` ngoài dự án thì mở làm bản nháp; `.json` thì như Open Project. Có hỏi lưu file đang mở |
| (mở model) | `dasktoon.project_open_model` | Mở một model của dự án, có hỏi lưu file đang mở (đã có) |
| New Model… | `dasktoon.model_new` | Cần dự án được chọn; chưa có thì mở New Project. Hộp thoại: **Name** và **Start From**: DaskToon Scene (mặc định), Empty Scene, Current Scene, Copy of Model (kèm ô chọn model). Model được lưu ngay thành `Models/<Name>.blend` rồi là file đang mở. Trùng tên thì báo lỗi |
| Save | `dasktoon.project_save` | Model trong dự án: chép texture (mục 10) rồi lưu tại chỗ. Bản nháp: mở hộp thoại Save to Project (bên dưới) |
| Save to Project | `dasktoon.save_to_project` | Hộp thoại cho bản nháp: **Project** (dự án được chọn và các dự án gần đây) và **Name** (gợi ý bằng tên file nháp, hoặc "Untitled"). Lưu bản sao vào `Models/<Name>.blend`, chép texture, và file đó thành file đang mở. File nháp gốc không bị đụng. Chưa có dự án nào thì mở New Project, sau đó New Model chọn sẵn Current Scene |
| Save Model As… | `dasktoon.model_save_as` | Lưu thành `Models/<Name>.blend` trong cùng dự án rồi chuyển sang file đó. Bản nháp thì như Save |
| Save Copy… | `dasktoon.model_save_copy` | Ghi bản sao `Models/<Name>.blend`, vẫn ở file hiện tại. Bản nháp thì mờ |
| Save Incremental | `dasktoon.model_save_incremental` | Như Save Incremental của Blender (`<tên>_001.blend` cạnh file), có chép texture. Bản nháp thì mờ |
| Project Settings… | `dasktoon.project_settings` | Đổi **Name**, chọn **Engine** và **Unity Project** (kiểm tra có `Assets/` và `ProjectSettings/`). Gắn hoặc đổi Unity thì cài shader vào đó |
| Export This Model | `dasktoon.project_export` | Như Phần 1. Dự án chưa gắn Unity thì mở Project Settings trước, gắn xong mới export |
| Reinstall Shaders | `dasktoon.project_reinstall_shaders` | Như Phần 1, cùng cách xử lý khi chưa gắn Unity |
| Open Project Folder | `dasktoon.project_open_folder` | Như Phần 1 |
| Continue as Draft | `dasktoon.continue_as_draft` | Đóng màn hình đầu, không làm gì khác |

**Cảnh khởi đầu của New Model:**
- **DaskToon Scene:**
  - cảnh trống, không có khối lập phương;
  - một Sun (để bóng mặt và Light Vector tự đồng bộ) và một camera nhìn vào gốc tọa độ;
  - engine DaskToon Anime, color management Standard.
- **Empty Scene:** cảnh trống hoàn toàn (`read_homefile(use_empty=True)`).
- **Current Scene:** lưu chính cảnh đang mở làm model mới. Được chọn sẵn khi đang ở bản nháp mà bản nháp là một file
  ngoài dự án hoặc có thay đổi chưa lưu. Cảnh trống lúc mới mở DaskToon thì chọn sẵn DaskToon Scene.
- **Copy of Model:** chép file của một model có sẵn trong dự án thành `Models/<Name>.blend` rồi mở.

## 7. Menu File, menu New, Open Recent, thanh trên cùng

**`TOPBAR_MT_file`** viết lại:

```
New Project…
New Model…                 Ctrl N
Open…                      Ctrl O
Open Recent              ▸ Shift Ctrl O
Models                   ▸   (model của dự án đang mở)
Revert
Recover                  ▸
─
Save                       Ctrl S
Save Model As…             Shift Ctrl S
Save Copy…
Save Incremental           Ctrl Alt S
─
Link… / Append… / Data Previews ▸
─
Import ▸ / Export ▸ (Engine Export vẫn ở đây) / Export All Collections
─
External Data ▸ / Clean Up ▸
─
Project                  ▸   Project Settings…, Export This Model, Reinstall Shaders, Open Project Folder
Defaults                 ▸
─
Quit
```

- Các mục hiện đúng phím tắt như sơ đồ trên, kể cả khi mục gọi lệnh DaskToon. Kế hoạch chọn cách làm, ví dụ để mục gọi
  lệnh gốc ở chế độ invoke (lõi chuyển hướng) với chữ của DaskToon.
- Menu **DaskToon Project** của Phần 1 được thay bằng các mục trên.
  `TOPBAR_MT_dasktoon_project_recent` và `TOPBAR_MT_dasktoon_project_models` dùng lại cho Open Recent và Models.
- **`TOPBAR_MT_file_new`** (Ctrl+N mở menu này) chỉ còn New Model… và New Project….
- **`TOPBAR_MT_file_open_recent`** (Shift+Ctrl+O): model gần đây trước, rồi dự án gần đây, mỗi nhóm có nhãn.
- **Thanh trên cùng** (`TOPBAR_HT_upper_bar.draw_right`), trước ô chọn scene, có một nhãn:
  - mở model của dự án: "Hero › Hero_Armor", icon thư mục;
  - bản nháp: "Draft (not in a project)", icon cảnh báo.

## 8. Chặn trong lõi (C++)

Trong `wm_files.cc`:

1. Thêm thuộc tính ẩn `use_project_redirect` (bool, mặc định `true`, `PROP_HIDDEN | PROP_SKIP_SAVE`) cho
   `WM_OT_read_homefile`, `WM_OT_open_mainfile`, `WM_OT_save_mainfile`, `WM_OT_save_as_mainfile`.
2. Trong hàm **invoke** của bốn lệnh, nếu `use_project_redirect` bật và lệnh DaskToon tương ứng đã đăng ký thì gọi lệnh
   DaskToon ở chế độ invoke, chuyển kèm các thuộc tính liên quan, rồi kết thúc lệnh gốc:

   | Lệnh gốc | Chuyển sang | Điều kiện |
   |---|---|---|
   | `wm.read_homefile` | `dasktoon.model_new` | luôn luôn |
   | `wm.open_mainfile` | `dasktoon.open` | chỉ khi lệnh gốc sẽ mở hộp chọn file (chưa có đường dẫn, hoặc `display_file_selector` bật) |
   | `wm.save_mainfile` | `dasktoon.project_save` | luôn luôn; `incremental` bật thì sang `dasktoon.model_save_incremental` |
   | `wm.save_as_mainfile` | `dasktoon.model_save_as` | `copy` bật thì sang `dasktoon.model_save_copy` |

3. **Hộp thoại hỏi lưu** khi thoát, mở file khác hoặc tạo mới (`wm_block_file_close_save`): nếu `dasktoon.project_save`
   đã đăng ký thì nút Save gọi nó ở chế độ exec.
   - Model trong dự án: lưu (có chép texture) rồi việc đang làm (thoát, mở file) chạy tiếp.
   - Bản nháp: lệnh mở hộp thoại Save to Project và trả về hủy, nên việc đang làm dừng lại. Người dùng lưu xong làm lại
     thao tác, giống Blender với file chưa từng lưu.
4. **Exec không bị chuyển hướng.** Script, add-on, test và mã DaskToon gọi các lệnh này ở chế độ exec với đường dẫn cụ
   thể, nên vẫn chạy như Blender.
   - Khi DaskToon cần hộp thoại hỏi lưu của Blender, nó gọi lệnh gốc ở chế độ invoke với `use_project_redirect=False`.
     Ví dụ khi mở một model có sẵn: `wm.open_mainfile` với đường dẫn và `display_file_selector=False`.
   - Nhờ vậy không có vòng lặp chuyển hướng.
5. Chạy nền (`-b`) và dòng lệnh không có invoke nên không đổi gì.

## 9. Bản nháp

- **Khi nào là bản nháp:**
  - Cảnh mới lúc mở DaskToon (bấm Continue as Draft hoặc đóng màn hình đầu).
  - File mở từ dòng lệnh, kéo thả, nhấp đúp hoặc Open… mà nằm ngoài mọi dự án.
- **Thanh trên cùng** ghi "Draft (not in a project)".
- **Lưu bản nháp:**
  - Save, Save Model As và nút Save của hộp thoại hỏi lưu đều đi qua Save to Project.
  - File gốc ngoài dự án không bao giờ bị ghi đè qua giao diện.
  - Save Copy và Save Incremental bị mờ.
- **Dữ liệu tạm:** tự lưu (autosave) và Recover Last Session giữ như Blender, ghi vào thư mục tạm của Blender.

## 10. Chép texture vào dự án

Chạy trước mọi lần lưu của người dùng: Save, Save to Project, Save Model As, Save Copy, Save Incremental, nút Save của
hộp thoại hỏi lưu. Lưu bằng script và tự lưu (autosave) không chép.

- **Ảnh được chép:** ảnh có nguồn là file (`FILE`, `MOVIE`) hoặc UDIM (`TILED`), có file thật trên đĩa, và nằm ngoài
  thư mục dự án.
- **Bỏ qua (không báo):** ảnh packed, ảnh tạo trong Blender chưa có file, ảnh của thư viện link, ảnh đã nằm trong dự án.
- **Đích:** `Textures/<tên file>`.
  - Trùng tên mà nội dung khác thì thêm hậu tố `_1`, `_2`…
  - Đã có bản giống hệt từng byte thì dùng lại.
  - UDIM: chép mọi tile theo mẫu `<UDIM>`.
- Sau khi chép, đường dẫn ảnh được đổi thành đường dẫn tương đối tới file `.blend` sẽ lưu.
- **Chỉ cảnh báo, không chép:** chuỗi ảnh (`SEQUENCE`) và ảnh mất file nguồn.
- **Báo cáo:**
  - Thông báo ở thanh trạng thái, ví dụ "Copied 3 textures into Textures/".
  - Mỗi cảnh báo là một dòng report.

## 11. Gắn Unity sau

- Dự án tạo không có Unity thì `engines` là `[]`. Menu và màn hình đầu ghi "Engine: not linked".
- Project Settings… kiểm tra đường dẫn Unity như Phần 1, lưu vào `engines`, và cài shader khi gắn hoặc đổi.
- Export This Model và Reinstall Shaders khi chưa gắn Unity thì mở Project Settings. Sau khi gắn xong (OK), lệnh ban
  đầu tự chạy tiếp.
- Engine Export (File › Export) vẫn chạy như Phần 1. Dự án chưa gắn Unity thì nó dùng chế độ thư mục thường.

## 12. Trường hợp đặc biệt và lỗi

| Trường hợp | Xử lý |
|---|---|
| Tạo dự án trong thư mục đã có file | Cho phép; các `.blend` sẵn có thành model |
| Thư mục đã là một dự án | Báo lỗi, không tạo |
| Tên dự án hoặc model có ký tự không hợp lệ | Thay bằng `_` (`safe_name`) |
| Tên model trùng (không phân biệt hoa thường) | Báo lỗi; không ghi đè model có sẵn |
| Dự án gần đây đã bị xóa hoặc dời | Không hiện trong danh sách (đã có) |
| Model gần đây không còn | Không hiện trong danh sách |
| Thư mục dự án không ghi được | Lỗi lưu của Blender, báo ra như thường |
| Bản nháp có ảnh đang sửa (painted) chưa lưu | Lần lưu đầu vào dự án dùng exec nên không có hộp thoại "lưu ảnh đã sửa" của Blender; DaskToon cảnh báo tên các ảnh này |

## 13. Bản dịch

Mọi chữ mới là tiếng Anh theo quy tắc Phần 1 (mục 6), có bản dịch tiếng Việt trong `dasktoon_translations.py`. Các test
bản dịch của Phần 1 phủ luôn các file mới và file đã sửa.

## 14. Kiểm thử

**Test nền** (thêm vào danh sách CMake, chạy bằng bộ test hiện có):
- **Thư viện:**
  - tạo dự án không có Unity; cấu trúc `Models/` và `Textures/`;
  - dự án cũ (`.blend` ở gốc);
  - thứ tự danh sách model;
  - model gần đây;
  - `settings.json`;
  - gắn Unity sau và cài shader.
- **New Model:**
  - đủ bốn cảnh khởi đầu (DaskToon Scene có Sun, camera, engine; Empty trống; Current giữ cảnh; Copy chép đúng file);
  - tên trùng;
  - ký tự lạ.
- **Bản nháp:**
  - nhận biết file ngoài dự án và cảnh chưa lưu;
  - Save to Project lưu bản sao vào `Models/`, file gốc giữ nguyên từng byte.
- **Chép texture:**
  - ảnh ngoài dự án được chép và đổi sang đường dẫn tương đối;
  - trùng tên khác nội dung; trùng hệt;
  - UDIM; chuỗi ảnh và file mất chỉ cảnh báo;
  - packed, ảnh tạo trong Blender, ảnh thư viện, ảnh trong dự án bị bỏ qua.
- **Giao diện:**
  - màn hình đầu ở hai trạng thái;
  - menu File, menu New, Open Recent;
  - nhãn thanh trên cùng;
  - bản dịch.
- **Lõi (gọi trực tiếp, không cần cửa sổ):**
  - bốn lệnh có thuộc tính `use_project_redirect`;
  - gọi exec với đường dẫn vẫn lưu/mở như Blender khi lệnh DaskToon đang đăng ký.

**Test có cửa sổ** (event simulation như công cụ chụp ảnh; chạy riêng, không nằm trong bộ test nền vì cần màn hình):
- Ctrl+S với bản nháp ra hộp thoại Save to Project.
- Ctrl+O ra hộp chọn file của DaskToon.
- Ctrl+N ra menu New của DaskToon.
- Hộp thoại hỏi lưu khi thoát lưu model vào dự án, và không ghi đè file rời gốc.

**Ảnh:** công cụ chụp ảnh thêm màn hình đầu, menu File và các hộp thoại New Project, New Model, Save to Project.

## 15. Build và nhánh

- Sửa `wm_files.cc` nên phải build lại DaskToon bằng thư mục build hiện có, rồi đồng bộ script bằng
  `tools/dasktoon_sync_build.py`.
- Nhánh `dasktoon-project-workflow` tách từ `dasktoon-ui-reorganization`. Nếu Phần 1 được merge trước thì nhánh này
  rebase lên `dasktoon-master`.

## 16. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Vòng lặp chuyển hướng (lệnh DaskToon gọi lại lệnh gốc) | Chỉ chuyển hướng ở invoke; DaskToon gọi lệnh gốc bằng exec hoặc `use_project_redirect=False`; có test |
| Add-on gọi `wm.save_mainfile('INVOKE_DEFAULT')` bị chuyển sang lưu dự án | Chấp nhận: đó là đường của người dùng |
| Bản nháp: nút Save khi thoát dừng việc thoát lại | Giống Blender với file chưa từng lưu; người dùng thoát lại sau khi lưu |
| Hộp thoại "lưu ảnh đã sửa" không hiện ở lần lưu đầu của bản nháp | DaskToon cảnh báo tên các ảnh đang sửa chưa lưu (mục 12) |
| Chép texture lớn làm lưu chậm | Chỉ chép lần đầu; lần sau ảnh đã nằm trong dự án nên bị bỏ qua |
| Phần 1 chưa merge | Làm trên nhánh tách từ Phần 1; rebase nếu cần |

## 17. Nhật ký quyết định

| Câu hỏi | Quyết định |
|---|---|
| Còn được mở/tạo file `.blend` rời không | Bắt buộc dự án |
| Tạo dự án có bắt buộc Unity không | Không; gắn sau |
| Sắp xếp file trong dự án | Thư mục cố định `Models/`, `Textures/` |
| Cảnh khởi đầu của New Model | Chọn khi tạo: DaskToon Scene, Empty, Current, Copy of Model |
| Mở file ngoài dự án | Mở làm bản nháp; lưu thì chọn dự án; file gốc giữ nguyên |
| Texture ngoài dự án | Tự chép vào `Textures/` khi lưu |
| Màn hình đầu | Hai cột: dự án \| model |
| Hướng làm | Chặn trong lõi C++ khi người dùng mở/lưu; script không bị chặn (DaskToon không còn đi theo Blender gốc) |
| Phím tắt | Không sửa file keymap: chặn ở invoke bắt được Ctrl+O/S và Shift+Ctrl+S; Ctrl+N và Shift+Ctrl+O mở menu Python được viết lại. Keymap Industry Compatible cũng được hưởng |
