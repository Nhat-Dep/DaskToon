# DaskToon: tab Animation gọn (A), báo cáo

- Ngày: 2026-10-10, làm tự động sau khi người dùng giao "tự động".
- Nhánh: `dasktoon-animation-tab`, tách từ `dasktoon-minor-fixes` (`8983b341a40`), nên nằm chồng lên hai nhánh constraint
  Spring và sửa lỗi nhỏ. Chưa push, chưa merge.
- Spec: `docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md`. Phần 1 (bố cục), phần 2 (timeline "cả nhân
  vật") và cách làm đã được người dùng duyệt. Phần 3–5 do Claude tự chốt, cần người dùng xem lại (§4 dưới đây).
- Kế hoạch: `docs/superpowers/plans/2026-10-10-dasktoon-animation-tab.md`.

## 1. Đã làm được gì

| Phần | Nội dung |
|---|---|
| Tab Animation mới | Camera view bên trái (Rendered), viewport chính có toolbar, Properties cả cột phải ở tab Object Data, một Dope Sheet ở dưới: chân trang có nút phát, header có **Key Pose** và công tắc **Whole Character**. Bỏ Outliner. Workspace giữ Pose Mode như tab gốc của Blender |
| Whole Character (C++) | Công tắc mới trong bộ lọc Dope Sheet (`DopeSheet.show_whole_character`, icon armature, cạnh Only Show Selected). Chọn bất kỳ phần nào của nhân vật (armature, object con của nó, mesh nó điều khiển) thì timeline hiện cả nhân vật, mọi xương. Object không thuộc nhân vật nào chỉ hiện khi được chọn. Tập nhân vật được tính một lần mỗi lượt lọc. Graph Editor và NLA dùng chung cờ này; nút chỉ có ở Dope Sheet |
| Key Pose và phím I | Keying set **DaskToon Character**: mọi xương (như "Whole Character" của Blender), mọi shape key trừ Basis, mọi tay cầm controller biểu cảm của nhân vật có phần đang chọn; object khác đang chọn thì vị trí, xoay, scale. **Key Pose** key đúng những thứ đó ở khung hiện tại, chạy được từ mọi editor. Scene chưa có keying set thì nhận keying set này khi mở file, nên phím I key cả thân lẫn mặt |
| Thay tab khi mở file | Tab nằm trong `scripts/startup/bl_ui/dasktoon_animation.blend`, do `tools/dasktoon_build_animation_tab.py` dựng từ tab gốc của Blender. Mỗi khi mở file (cả lúc khởi động và New): tab Animation của Blender hoặc tab DaskToon phiên bản cũ được thay; tab đúng phiên bản thì giữ (ô người dùng đã kéo cỡ vẫn nguyên); tab đã bị xóa thì không thêm lại; file không bị đánh dấu "đã sửa" |
| Hàm C++ mới | `bpy.data.workspaces.replace(old, new)`: `new` vào đúng vị trí tab của `old`, cửa sổ nào đang mở `old` thì chuyển sang `new`, `old` bị xóa và `new` lấy tên của nó, file giữ trạng thái "đã lưu" |
| Tiếng Việt | Mọi chữ mới có bản dịch ("Khóa cả dáng", "Nhân vật DaskToon", mô tả công tắc, các thông báo) |

Cách dùng:

1. Mở tab **Animation**.
2. Chọn bất kỳ phần nào của nhân vật (bấm vào mặt cũng được). Timeline hiện cả xương lẫn shape key.
3. Tạo dáng, rồi bấm **Key Pose** trong header timeline (hoặc phím I trong viewport).

## 2. Kiểm thử

- 3 file test mới:
  - `dasktoon_animation_filter_test.py` (10 test): chọn mặt thì hiện cả nhân vật, hiện mọi xương, object rời chỉ hiện khi
    chọn, hai nhân vật, không chọn gì thì trống, tắt cờ thì như Blender, công tắc trong header, bản dịch;
  - `dasktoon_animation_keying_test.py` (7 test): thành viên nhân vật, Key Pose key đủ thứ, object rời, keying set chạy qua
    Blender từ 3D Viewport, keying set mặc định của scene, nút trong header;
  - `dasktoon_animation_tab_test.py` (8 test): tab sau khi khởi động, thay tab cũ mà file vẫn "sạch", giữ tab đúng phiên
    bản, tab bị xóa không quay lại, keying set khi mở file, file mẫu chỉ có workspace, `workspaces.replace`.
- Toàn bộ suite CMake: 47 file (454 test) đều qua, cộng script nạp module.
- Trong cửa sổ thật: file lưu khi cửa sổ đang ở tab Animation cũ, mở lại thì cửa sổ ở tab mới, không "đã sửa" (đường chuyển
  cửa sổ của hàm C++).

## 3. Ảnh chụp

Trong `docs/superpowers/reports/animation-tab/en/` và `.../vi/` (`tools/dasktoon_animation_screenshots.py`):

| Ảnh | Nội dung |
|---|---|
| `30_animation_tab.png` | Cả cửa sổ ở khung 6: camera view, viewport chính, Properties tab Object Data của mesh thân (shape key Smile), timeline nhân vật; chân trang có keying set "DaskToon Character" |
| `31_character_timeline.png` | Riêng Dope Sheet: nút Key Pose trong header; chỉ chọn mesh thân mà vẫn có dòng Rig (key xương) và Key (shape key), key ở khung 1 và 12 |

## 4. Quyết định Claude tự chốt (cần xem lại)

Thiết kế:

1. Key Pose key mọi xương, mọi shape key (trừ Basis), mọi controller; object rời key vị trí/xoay/scale. Object con như tóc
   gắn xương hay vũ khí thì không key transform của chúng.
2. Key Pose chỉ hiện khi Whole Character bật (tức là trong tab Animation mới).
3. Phím I dùng "DaskToon Character" cho scene chưa có keying set; scene đã có keying set khác thì giữ.
4. Thay tab bằng hàm C++ (thao tác workspace của Blender chỉ áp dụng cho tab đang mở và đổi tab có độ trễ, nên handler mở
   file không dùng được). Tab đúng phiên bản thì giữ; tab bị xóa thì không thêm lại.
5. Workspace giữ Pose Mode như tab gốc của Blender. Hệ quả: armature đang active được coi là đang ở Pose Mode, và Whole
   Character tính nó là phần đang chọn.

Khi làm (ledger):

- **Lệch spec, giữ ý của spec:** Blender đặt mọi viewport đang Rendered về Solid khi đọc file ("render có thể nặng"), nên file
  mẫu không giữ được Rendered. Handler mở file đặt lại Rendered cho ô camera của tab DaskToon khi ô đó đang Solid; nếu
  người dùng chọn kiểu hiển thị khác thì giữ.
- Toán tử chèn key theo keying set của Blender cần một editor trong context, nên Key Pose tự key theo đúng danh sách của
  keying set (một lớp dùng chung cho cả hai).
- Công cụ dựng file mẫu phải chạy trong cửa sổ thật: đóng ô (`area_close`) bị treo khi chạy nền. Bật/tắt vùng (toolbar) từ
  timer làm Blender crash vì thiếu cửa sổ trong context, nên các thiết lập được đặt trong `temp_override` có cửa sổ.
- Trong Blender 5.2, module tiện ích keying set tên là `_keyingsets_utils`.
- Thứ tự khi mở file: handler `load_post` chạy trước khi Blender khởi tạo undo, nên Ctrl+Z không đưa tab cũ trở lại.

## 5. Review (tự review)

Phiên này không tạo subagent khi người dùng chưa yêu cầu, nên đây là tự review, yếu hơn một reviewer độc lập.

- Không có lỗi Critical/Important.
- Để lại (Minor):
  - mỗi lần mở file, ô camera của tab DaskToon về Rendered nếu đang Solid; scene rất nặng thì có thể chậm lúc mở;
  - Key Pose key cả xương chuỗi tóc/váy: key của chúng là tư thế gốc của lắc (đúng spec rig), nhưng timeline nhiều dòng hơn;
  - tên tab tìm theo "Animation": file đã đổi tên tab này thì không được thay.

## 6. Còn lại

- Ba nhánh xếp chồng chờ người dùng chọn merge, mở PR hay giữ: `dasktoon-spring-constraint`, rồi `dasktoon-minor-fixes`,
  rồi `dasktoon-animation-tab`.
- Người dùng xem lại các quyết định ở §4.
- Tiếp theo: R3 (mắt, miệng), B (clip cho Unity: ô chọn clip sẽ thêm vào cùng header), C (nhịp anime, onion skin, bộ lọc hành
  động nhanh: menu sẽ thêm vào cùng header).
