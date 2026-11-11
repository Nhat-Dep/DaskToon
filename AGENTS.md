# Quy tắc cho trợ lý lập trình (Antigravity, Gemini và các trợ lý khác) trong DaskToon

DaskToon là một bản tách từ Blender 5.2 (thư mục cài đặt `5.2`), thêm phần hoạt hình anime: đổ bóng kiểu cel, rig,
biểu cảm, xuất sang Unity/VTuber. Đây là dự án cá nhân; một trợ lý khác (Claude Code) cũng làm việc **trong cùng thư
mục này**. Trả lời người dùng bằng tiếng Việt dễ hiểu, ít thuật ngữ tiếng Anh, dùng tên nút tiếng Việt mà giao diện
DaskToon hiển thị.

## 1. Không đoán — kiểm tra trước khi dùng

Hiểu biết sẵn có về Blender không đủ: DaskToon đã đổi và thêm rất nhiều thứ, còn API của Blender 5.x cũng khác các bản
cũ. Mỗi tên hàm, toán tử (`bpy.ops.*`), thuộc tính, loại nút, tên ô nhập, tên tệp hay đường dẫn phải được **xác nhận
trước khi viết vào mã**:

- Tìm trong mã nguồn: `scripts/` (Python), `source/` (C++). Không tìm thấy thì coi như không có.
- Hoặc hỏi thẳng chương trình đã dựng (chạy nền, không mở cửa sổ):
  ```bash
  D:/build_windows_x64_vc18_Release/bin/Release/DaskToon.exe --background --factory-startup \
    --python-expr "import bpy; n = bpy.data.materials.new('x'); n.use_nodes = True; \
  print([i.name for i in n.node_tree.nodes.new('ShaderNodeAnimeCharacter').inputs])"
  ```
- Đọc tệp trước khi sửa nó; đọc hàm trước khi gọi nó. Không nhớ chắc nội dung một tệp thì đọc lại.
- Bẫy đã gặp: nút `ShaderNodeAnimeCharacter` có các mô-đun bật/tắt (`use_ambient`, `use_light`, `use_ao`, `use_rim`,
  `use_outline`, `use_grade`). Khi mô-đun tắt, các ô của nó (ví dụ `Rim Color`, `Rim Factor`) vẫn có trong danh sách
  nhưng `node.inputs["Rim Color"]` báo không tìm thấy. Bật mô-đun trước; xem ô dùng được bằng
  `[i.name for i in node.inputs if i.enabled]`. Không có ô `Rim Intensity`.
- Máy chủ MCP `dasktoon` (`tools/dasktoon_mcp_server.py`) chạy DaskToon **nền**: nó không thấy cửa sổ DaskToon đang
  mở. Muốn làm trên một tệp thì truyền `blend_file`; muốn giữ thay đổi thì truyền `save_as` (một đường dẫn **mới**).
  Câu trả lời ghi rõ `file` (tệp đã đọc) và `saved_to`; `saved_to` rỗng nghĩa là **không có gì được lưu**.
- Không bịa kết quả: chỉ nói "đã chạy", "kiểm tra đã qua", "đã sửa" khi vừa thấy kết quả đó trong lượt này, và chép
  dòng kết quả thật vào câu trả lời. Chưa chạy được thì nói rõ là chưa chạy.
- Không chắc người dùng muốn gì thì hỏi, đừng tự chọn một hướng lớn rồi làm luôn.

## 2. Cấu trúc dự án

| Chỗ | Nội dung |
| --- | --- |
| `scripts/startup/bl_ui/dasktoon_*.py` | Bảng, nút, toán tử giao diện của DaskToon |
| `scripts/modules/dasktoon_*/` | Phần xử lý (rig, biểu cảm, xuất, dlive, máy móc…) |
| `scripts/startup/bl_ui/dasktoon_translations.py` | Bản dịch tiếng Việt của mọi chữ trên giao diện |
| `source/` | Mã C++ (nút đổ bóng, bộ sửa đổi, lõi) |
| `tests/python/dasktoon_*_test.py` | Kiểm tra tự động (unittest, chạy trong DaskToon) |
| `docs/superpowers/specs/`, `plans/`, `reports/` | Bản thiết kế, kế hoạch, báo cáo theo ngày `YYYY-MM-DD-ten.md` |
| `tools/` | Công cụ: chạy kiểm tra, đồng bộ bản cài, máy chủ MCP |

Tìm một phần cũ có sẵn làm việc giống thế và theo cách nó làm (cách đặt tên, cách viết kiểm tra, cách dịch) trước khi
viết phần mới.

## 3. Dựng và kiểm tra

- **Chỉ dùng** bản dựng Visual Studio 2026: `D:/build_windows_x64_vc18_Release`. Thư mục `..._vc17_Release` đã cũ và
  hỏng, không dùng.
- Sửa Python thì **không cần** dựng lại C++; tệp chạy kiểm tra tự chép `scripts/` sang bản cài trước khi chạy.
- Chạy kiểm tra (Git Bash, từ gốc dự án):
  ```bash
  tools/dasktoon_run_tests.sh dasktoon_machine_test dasktoon_translations_test
  tools/dasktoon_run_tests.sh --all     # toàn bộ, lâu
  ```
- Dựng C++ (chỉ khi sửa `source/`): **ít luồng, ưu tiên thấp**, nếu không máy bị đứng:
  ```powershell
  $p = Start-Process cmake -ArgumentList '--build','D:/build_windows_x64_vc18_Release','--config','Release','--target','install','--','-m:2','-p:CL_MPCount=2' -PassThru -NoNewWindow
  $p.PriorityClass = 'BelowNormal'
  ```
  Không dùng `-m` hay `/m` không kèm số. Sửa một tệp đầu chung (ví dụ `UI_icons.hh`) có thể mất 30–45 phút.
- Nếu dựng báo thiếu `CMakeLists.txt` ở gốc: khôi phục bằng `git show HEAD:CMakeLists.txt > CMakeLists.txt`.
- Không có Python hệ thống; dùng `D:/build_windows_x64_vc18_Release/bin/Release/5.2/python/bin/python.exe`.

## 4. Cách sửa lỗi và viết kiểm tra

- Viết hoặc sửa kiểm tra trước, thấy nó **thất bại** trên mã cũ, rồi mới sửa chức năng cho nó qua.
- **Sửa chức năng, không sửa riêng tệp kiểm tra cho qua.** Chỉ đổi một kiểm tra khi chính nó sai, và nói rõ vì sao.
- Một mô hình thật chỉ cho biết chức năng sai ở đâu. Sửa theo hình dạng đo được, ngưỡng tính theo kích thước;
  **không bao giờ** dùng tên hay con số riêng của một mô hình. Kiểm tra dùng mô hình tổng hợp có cùng cái khó.
  Hỏi: vì sao kiểm tra cũ không bắt được lỗi này? rồi làm kiểm tra khó hơn ở đúng điểm đó.
- Mọi chữ mới trên giao diện (nhãn, gợi ý, thông báo) phải có bản dịch trong `dasktoon_translations.py`, và tệp mới
  có chữ giao diện phải được thêm vào danh sách trong `tests/python/dasktoon_translations_test.py`.
- Trước khi báo xong: chạy kiểm tra của phần đã sửa **và** `dasktoon_translations_test`, tất cả phải qua.

## 5. Làm chung thư mục với Claude Code

Hai trợ lý cùng sửa một thư mục, nên:

- Bắt đầu mỗi việc bằng `git status` và đọc `.agents/dang_lam.md` (bảng "đang làm"). Tệp nào đang có thay đổi chưa
  commit mà không phải do bạn làm thì đó là việc dở của người khác: **không sửa, không hoàn tác, không commit hộ.**
- Ghi một dòng vào `.agents/dang_lam.md` khi bắt đầu (ai, làm gì, những tệp/thư mục nào, từ lúc nào) và xóa dòng đó
  khi xong. Thấy phần mình cần đụng đang có người làm thì báo người dùng, đừng làm chồng lên.
- Commit chỉ những tệp của mình, gọi tên từng tệp: `git add đường/dẫn/tệp`. Không dùng `git add -A`, `git add .`,
  `git commit -a`.
- Cấm: `git reset --hard`, `git checkout -- …`, `git restore` (trừ `--staged`), `git stash`, `git clean -f`,
  `git push --force`, `git rebase`, xóa nhánh, tạo worktree. (Một móc lệnh trong `.agents/hooks.json` chặn các lệnh này.)
- Làm thẳng trong `D:\DaskToon` trên nhánh `dasktoon-master`; không tạo thư mục worktree khác.
- Thông điệp commit theo kiểu đang có: `feat(phan): …`, `fix(phan): …`, `test(phan): …`, `docs(phan): …` (tiếng Anh,
  nói chức năng làm được gì). Cuối thông điệp thêm dòng `Co-Authored-By: Antigravity <noreply@google.com>`.
- **Đẩy lên GitHub (`git push`) chỉ khi người dùng bảo.**

## 6. Tệp của người dùng

- Mô hình nhân vật thật của người dùng (trong `D:\game\…`, `Documents\DaskToon Projects\…`): không bao giờ lưu đè tệp
  gốc. Mở tệp gốc rồi `bpy.ops.wm.save_as_mainfile(filepath=bản_sao)` ngay (chép tệp thường làm hỏng đường dẫn ảnh,
  hình hiện màu tím). Sửa trên tệp của người dùng thì giữ một bản sao lưu bên cạnh.
- Không commit ảnh chụp/kết xuất nhân vật của người dùng hay tệp `.blend` của họ vào dự án (dự án được đẩy công khai).
- Không ghi vào các dự án Unity trong `D:\Unity\` nếu người dùng không bảo.
- Tệp tạm, ảnh thử, kịch bản thử để ngoài dự án (thư mục tạm của hệ thống), không để ở gốc `D:\DaskToon`.

## 7. Tắt màn hình

Máy là laptop: tắt màn hình làm máy ngủ và dừng mọi việc đang chạy. Với việc dài, nhắc người dùng đừng tắt màn hình.
