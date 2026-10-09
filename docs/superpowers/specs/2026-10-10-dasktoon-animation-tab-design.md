# DaskToon: tab Animation gọn cho nhân vật anime (A)

- Ngày: 2026-10-10. Trạng thái: phần 1 (bố cục), phần 2 (timeline "cả nhân vật") và cách làm 1 **người dùng đã duyệt**
  (2026-10-06 → 2026-10-10); phần 3 (Key Pose và phím I), phần 4 (thay tab khi mở file), phần 5 (chừa chỗ cho B, C) **Claude
  tự chốt** khi người dùng giao "tự động" (2026-10-10), cần người dùng xem lại (§11).
- Thứ tự lộ trình: rig anime R (xong), **A** (spec này), B (clip cho Unity), C (nhịp anime và bộ lọc hành động nhanh), R3.

## 1. Mục tiêu

Nhân vật dựng trong DaskToon có thân (armature) và mặt (shape key, controller biểu cảm) nằm ở những object khác nhau. Trong
tab Animation của Blender, muốn thấy và key cả hai phải chọn đủ mọi object, timeline thì tách khỏi Dope Sheet. Mục tiêu:

1. Mở tab Animation là có ngay bố cục để làm animation nhân vật: nhìn qua camera, viewport để tạo dáng, Properties, một
   timeline duy nhất.
2. Chọn bất kỳ phần nào của nhân vật (armature, mặt, tóc), timeline hiện **cả nhân vật**: mọi xương, shape key, controller.
3. Một nút **Key Pose** (và phím I) key cả dáng: mọi xương và mọi biểu cảm mặt, cùng lúc.
4. File cũ mở ra cũng có tab mới; ngoài tab Animation, Blender như cũ.

## 2. Phạm vi

| Có | Không (để sau) |
|---|---|
| Tab Animation mới (file mẫu `.blend` do script dựng) | Clip cho Unity (B) |
| Công tắc "Whole Character" trong bộ lọc Dope Sheet (C++) | Vẽ on twos/threes, giữ khung, onion skin, bộ lọc hành động nhanh (C) |
| Keying set "DaskToon Character", nút Key Pose, phím I key cả nhân vật | Mắt, miệng (R3) |
| Thay tab Animation khi mở file (hàm C++ thay workspace) | Đổi các tab khác của Blender |
| Bản Việt, test, ảnh chụp | |

## 3. Bố cục (phần 1, đã duyệt)

| Ô | Nội dung |
|---|---|
| Camera view (trái, trên) | 3D Viewport nhìn qua camera của cảnh, hiển thị **Rendered** để thấy đúng look anime; ẩn toolbar và gizmo |
| Viewport chính (giữa) | 3D Viewport nhìn tự do, **có toolbar** để chọn và xoay xương; HUD biểu cảm hiện ở đây khi bật |
| Properties (phải, cả chiều cao) | Mở sẵn tab **Object Data**: chọn mesh mặt thì thấy Shape Keys, Expression Preview, Controllers; chọn armature thì thấy Anime Rig và Bone/Pose |
| Timeline nhân vật (dưới) | Một Dope Sheet: chân trang có nút phát (sẵn có trong Blender 5.2), header có **Key Pose** và công tắc **Whole Character** (bật) |
| Bỏ khỏi tab | Outliner. Graph Editor, NLA không có sẵn; vẫn mở được bằng nút chọn loại editor ở góc mỗi ô |

Tab gốc của Blender 5.2 đã gần như vậy (camera trái trên, viewport giữa, Dope Sheet dưới có nút phát, Outliner và Properties
bên phải; workspace ở Pose Mode). File mẫu dựng từ tab gốc: đóng Outliner (Properties chiếm cả cột phải), Properties sang
Object Data, camera view Rendered, viewport chính có toolbar, Dope Sheet bật Whole Character. Workspace giữ Pose Mode như
Blender.

## 4. Timeline "cả nhân vật" (phần 2, đã duyệt)

- **Nhân vật**: một armature, cộng mọi object có nó trong chuỗi cha (tóc, phụ kiện, vũ khí gắn vào xương), cộng mọi object có
  modifier Armature trỏ tới nó. Một object có thể thuộc nhiều nhân vật (mesh có hai modifier Armature).
- **Công tắc mới "Whole Character"** trong header Dope Sheet, cạnh "Only Show Selected" (và trong popover Filters). Tab
  Animation mới bật sẵn; mọi editor khác tắt sẵn, nên Blender ở đó như cũ.
- **Khi bật**, một object được hiện nếu nó đang được chọn, hoặc thuộc một nhân vật có ít nhất một thành phần đang được chọn:
  chọn mesh mặt thì hiện cả xương; chọn armature thì hiện cả shape key và controller của mesh.
- **Xương**: hiện mọi xương của nhân vật, không chỉ xương đang chọn (Key Pose key cả dáng). Dòng armature thu gọn được.
- **Trường hợp khác**: object không thuộc nhân vật nào (camera, đạo cụ rời) chỉ hiện khi đang được chọn, như "Only Show
  Selected"; chọn nhiều nhân vật thì hiện tất cả; không chọn gì thì timeline trống, như Blender. Những gì "Only Show
  Selected" ẩn (cache file, annotation, movie clip) thì Whole Character cũng ẩn.
- **Cách làm**: cờ mới `ADS_FILTER_WHOLE_CHARACTER` trong `filterflag2` (`DNA_action_types.h`); kiểm trong `anim_filter.cc`
  ở mức object (`animdata_filter_base_is_ok`, với tập armature của các nhân vật đang có thành phần được chọn, tính một lần mỗi
  lượt lọc) và mức xương (`skip_fcurve_selected_data`: bỏ kiểm tra xương được chọn). Khi cờ bật, các chỗ khác coi như "Only
  Show Selected" đang bật. RNA: `DopeSheet.show_whole_character`. Graph Editor và NLA dùng chung bộ lọc nên cũng dùng được;
  nút chỉ đặt trong Dope Sheet (và popover Filters của nó).

## 5. Key Pose và phím I (phần 3, Claude chốt)

- **Keying set "DaskToon Character"** (Python, `KeyingSetInfo`, cùng định nghĩa nhân vật ở §4):
  - với mỗi nhân vật có thành phần đang chọn: mọi xương của armature (vị trí nếu xương không nối và không khóa, xoay theo
    rotation mode, scale, thuộc tính B-Bone và custom property, như keying set "Whole Character" của Blender); mọi shape key
    (trừ Basis) của các mesh thuộc nhân vật; tay cầm của mọi controller biểu cảm (`dask_shape_controllers.groups[i]
    .handle_x/handle_y`);
  - object đang chọn không thuộc nhân vật nào: vị trí, xoay, scale của object (như mặc định của Blender).
- **Nút Key Pose** (`dasktoon.key_pose`, icon keyframe `KEY_HLT`): trong header Dope Sheet khi Whole Character bật (nên chỉ thấy trong tab
  Animation mới, trừ khi người dùng tự bật). Key bằng keying set trên tại khung hiện tại; báo "Keyed the pose of %s" (tên
  các nhân vật, hoặc object). Không có gì đang chọn thì báo "Select a part of a character to key its pose".
- **Phím I**: mỗi khi mở file, scene nào chưa có keying set đang dùng thì lấy "DaskToon Character", nên I trong viewport key
  cả nhân vật (Blender: có keying set đang dùng thì I dùng nó). Scene đã có keying set người dùng chọn thì giữ. Người dùng đổi
  ở popover Keying như Blender.
- Xương chuỗi tóc/váy cũng được key: key của chúng là tư thế gốc của lắc (spec rig §9.4); Bake Sway vẫn thay đường cong xoay
  của chúng như cũ.

## 6. Thay tab Animation khi mở file (phần 4, Claude chốt)

- **File mẫu** `scripts/startup/bl_ui/dasktoon_animation.blend`: chỉ có workspace "Animation" (và screen của nó), mang
  custom property `dasktoon_animation_template` = số phiên bản (bắt đầu 1). Dựng bằng `tools/dasktoon_build_animation_tab.py`
  từ tab Animation gốc của Blender (§3), ghi bằng `bpy.data.libraries.write`; dựng lại được giống hệt.
- **Khi mở file** (handler `load_post`, chạy cả lúc khởi động và New): nếu file có workspace "Animation" mà chưa có property
  trên, hoặc phiên bản cũ hơn file mẫu, thì:
  1. nạp workspace từ file mẫu (`bpy.data.libraries.load`, không làm file thành "đã sửa");
  2. gọi hàm C++ mới **`bpy.data.workspaces.replace(old, new)`**: đặt `new` vào đúng vị trí tab của `old`, cửa sổ nào đang
     mở `old` thì chuyển sang `new`, xóa `old`, đặt cho `new` tên của `old`; giữ nguyên trạng thái "đã lưu" của file.
- File không có tab "Animation" (người dùng đã xóa) thì không thêm lại. Tab đã đúng phiên bản thì không đụng, nên người dùng
  chỉnh kích thước ô thì vẫn giữ.
- Cùng handler đặt keying set mặc định của scene (§5).
- Chạy nền (script, test) cũng thay, cho cùng kết quả.

## 7. Chừa chỗ cho B và C (phần 5, Claude chốt)

- Header của timeline nhân vật vẽ phần DaskToon trong một hàm (`draw_character_header(layout, context)`) mà B thêm ô chọn
  clip, C thêm menu nhịp (on twos/threes, onion skin, hành động nhanh) mà không sửa lại bố cục.
- Đổi bố cục sau này: dựng lại file mẫu với phiên bản lớn hơn; file mở ra sẽ được thay tab một lần nữa.
- Định nghĩa nhân vật (Python `dasktoon_animation.character`) dùng chung cho keying set, B (clip theo nhân vật) và C.

## 8. Thành phần và file

| Thành phần | File |
|---|---|
| Cờ lọc, bộ lọc | `source/blender/makesdna/DNA_action_types.h`, `source/blender/editors/animation/anim_filter.cc`, `source/blender/editors/include/ED_anim_api.hh` (dữ liệu lọc tạm) |
| RNA | `source/blender/makesrna/intern/rna_action.cc` (`show_whole_character`), `source/blender/makesrna/intern/rna_main_api.cc` (`BlendDataWorkSpaces.replace`) |
| Header Dope Sheet | `scripts/startup/bl_ui/space_dopesheet.py` (công tắc, nút Key Pose qua hàm DaskToon) |
| Module DaskToon | `scripts/modules/dasktoon_animation/` (`character.py`: nhân vật; `keying.py`: keying set; `tab.py`: thay tab, keying set mặc định) |
| Giao diện, đăng ký | `scripts/startup/bl_ui/dasktoon_animation.py` (operator Key Pose, header, handler, đăng ký keying set) |
| File mẫu, công cụ | `scripts/startup/bl_ui/dasktoon_animation.blend` (`tools/dasktoon_sync_build.py` vốn chép mọi file trong `scripts`), `tools/dasktoon_build_animation_tab.py` |
| Bản dịch | `scripts/startup/bl_ui/dasktoon_translations.py` |

## 9. Kiểm thử

Test nền (`--background --factory-startup`), đăng ký trong `tests/python/CMakeLists.txt`:

- `dasktoon_animation_filter_test.py`: dựng hai nhân vật (armature, mesh có modifier Armature với shape key, tóc là con của
  xương) và một đạo cụ rời, mỗi thứ có key; bỏ chọn mọi key, chạy `action.select_all` trong ô Dope Sheet của screen
  Animation (qua `temp_override`), xem key của ai được chọn: chọn mesh mặt thì cả xương (kể cả xương không chọn) và shape key
  của nhân vật đó; đạo cụ chỉ khi được chọn; hai nhân vật; không chọn gì thì không có; cờ tắt thì như Blender.
- `dasktoon_animation_keying_test.py`: keying set key đủ xương, shape key, controller của nhân vật; object rời key vị trí,
  xoay, scale; Key Pose báo đúng; scene không có keying set thì lấy "DaskToon Character", có rồi thì giữ.
- `dasktoon_animation_tab_test.py`: file mẫu đúng cấu trúc (§3); mở file có tab Animation của Blender thì tab được thay, giữ
  vị trí, tên "Animation", file không "đã sửa"; tab đã đúng phiên bản thì không thay; file không có tab thì không thêm;
  `workspaces.replace` báo lỗi khi hai workspace là một.
- Giao diện: header Dope Sheet có công tắc; Key Pose chỉ hiện khi công tắc bật; bản Việt đủ.
- Ảnh chụp trong cửa sổ thật (tiếng Anh, tiếng Việt): tab Animation với nhân vật thử có key ở xương và mặt.

## 10. Rủi ro

| Rủi ro | Giảm |
|---|---|
| Thay tab làm file "đã sửa", đóng file bị hỏi lưu dù chưa đụng gì | Nạp bằng `libraries.load` (đã thử: không đổi trạng thái); `replace` giữ trạng thái "đã lưu"; test kiểm `is_dirty` |
| Undo lần đầu đưa tab cũ trở lại | Kiểm thứ tự handler và bước undo đầu tiên khi làm; nếu cần, thay tab trước khi bước undo đầu được ghi |
| File mẫu nhị phân lệch khi Blender đổi định dạng screen | Dựng lại bằng script; test kiểm cấu trúc file mẫu |
| Phím I đổi hành vi so với Blender | Chỉ khi scene chưa có keying set; đổi lại được ở popover Keying |
| Tính tập nhân vật mỗi lần vẽ timeline | Một lượt qua các object của view layer mỗi lần lọc, chỉ khi cờ bật |

## 11. Nhật ký quyết định

| Quyết định | Ai |
|---|---|
| Thay tab Animation của Blender (không thêm tab mới); bố cục §3 | Người dùng (phần 1) |
| Timeline "cả nhân vật": định nghĩa, công tắc, hành vi §4 | Người dùng (phần 2) |
| Cách làm 1: workspace mẫu `.blend` + cờ lọc C++ + keying set Python | Người dùng |
| Keying set key mọi xương, shape key, controller; object rời key vị trí/xoay/scale; Key Pose chỉ hiện khi Whole Character bật | Claude (chờ xem lại) |
| Phím I dùng "DaskToon Character" khi scene chưa có keying set | Claude (chờ xem lại) |
| Thay tab bằng hàm C++ `bpy.data.workspaces.replace` (thao tác workspace của Blender chỉ áp dụng cho tab đang mở, và đổi tab có độ trễ); tab đúng phiên bản thì giữ; tab bị xóa thì không thêm | Claude (chờ xem lại) |
| Workspace giữ Pose Mode như tab gốc của Blender | Claude (chờ xem lại) |
