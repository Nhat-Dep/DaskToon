# Báo cáo: lõi đổ bóng tùy biến và outline mới (Dự án 1)

- Nhánh: `dasktoon-shading-outline` (chưa push, chưa merge)
- Kế hoạch: `docs/superpowers/plans/2026-10-03-dasktoon-shading-outline.md`
- Spec: `docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`
- Ảnh để duyệt: `docs/superpowers/reports/2026-10-03-dasktoon-review-sheet.png`

Các thay đổi chưa commit của bạn (`dasktoon_init.py`, `dasktoon_ai_bridge.py`, `tools/dasktoon_mcp_server.py`) được giữ
nguyên. Mình không đụng tới và không commit chúng.

## Kết quả

**Cả 11 task đã xong. 45 test tự động trong 8 file đều PASS** trên bản build hiện tại
(`D:\build_windows_x64_vc17_Release\bin\Release\DaskToon.exe`, đã cài đặt sẵn mọi thay đổi).

| Task | Nội dung | Kết quả |
|---|---|---|
| 1 | Hạ tầng test, fixture file cũ, kiểm chứng nền tảng | ✅ Cả hai giả định nền tảng đều đúng |
| 2 | Sửa weight của Mix Shader (8 node) và Alpha của Anime BSDF | ✅ |
| 3 | Lõi GLSL dùng chung, refactor chế độ Đơn giản | ✅ Khớp 37 ảnh baseline chụp trước refactor |
| 4 | Dải màu, RNA, giao diện, GPU; Light Mode cho Anime BSDF | ✅ |
| 5 | Anime Cel: cel thật, specular toon, Ambient/Light Mode | ✅ |
| 6 | Preset và "Lưu style của tôi" | ✅ |
| 7 | Dựng Geometry Nodes cho outline | ✅ |
| 8 | Đồng bộ outline theo material, gỡ handler Solidify cũ | ✅ |
| 9 | Dữ liệu outline cho game (`DT_OutlineN/W`) | ✅ |
| 10 | Tự động nâng cấp file cũ khi mở | ✅ |
| 11 | Ảnh duyệt, đăng ký test với CMake, báo cáo | ✅ |

## Thử nhanh trong DaskToon

1. Mở `D:\build_windows_x64_vc17_Release\bin\Release\DaskToon.exe`.
2. Tạo material có **Anime BSDF**. Trên node có công tắc **Shading: Simple | Ramp**. Chọn **Ramp** sẽ hiện menu
   **Style**, nút **Lưu style của tôi** và **Chuyển từ Đơn giản**, cùng dải màu.
3. Bật checkbox **Outline** trên node. Trong *Properties › Material* có panel **DaskToon Outline** để chỉnh Light Bleed,
   Hand Wobble, Tint Mode, và nút **Chuẩn bị outline cho game**.
4. Mở một file `.blend` cũ có outline: DaskToon tự nâng cấp và hiện popup báo cáo.

## Những việc cần bạn làm

1. **Duyệt ảnh** `2026-10-03-dasktoon-review-sheet.png`. Hàng 1 là chế độ Đơn giản; hàng 2–6 là các preset (Anime 2 tông,
   Anime 3 tông, Mềm như vẽ, Da anime, Manga) ở ba góc Sun; hàng cuối là outline (thường, Light Bleed 1, Hand Wobble 1).
   Màu của từng preset có thể chỉnh trong `scripts/startup/bl_ui/dasktoon_shading_styles.py`.
2. **Kiểm tra giao diện node trong DaskToon thật**, vì chế độ headless không xem được UI.
3. **Xem lại công thức 5 Light Mode** (spec mục 3.10). Trước đây chưa node nào cài đặt chúng, nên mình đã tự định nghĩa.
4. **Mặc định của node Dask Outline** là Light Bleed 0.7 và Hand Wobble 0.15, nên mọi outline mới đều mỏng dần phía được
   chiếu sáng và hơi gợn. Nếu bạn muốn nét đều làm mặc định thì báo mình.
5. Quyết định **merge nhánh** khi đã hài lòng.

## Lỗi có sẵn được phát hiện và sửa trong lúc làm

| Lỗi | Hậu quả trước đây |
|---|---|
| `.available(lambda)` thực ra là `available(true)` | Tính năng "ẩn/hiện socket theo checkbox module" của Anime BSDF chưa từng hoạt động |
| Artist Line Modulation dùng `g_data.camera_pos` (không tồn tại) | Node luôn hiện màu tím báo lỗi |
| Anime Cel nối world normal vào socket Specular Softness | Normal của Anime Cel sai |
| Anime Cel thiếu RNA `ambient_mode`, `light_blend_mode` | Hai dropdown không bao giờ hiện |
| `light_blend_mode` của Anime BSDF ghi đè toàn bộ `custom2` | Đổi Light Mode làm tắt các module (đã thấy Rim bị tắt) |
| `outline_tint_mode_set` xóa các bit cao của `custom1` | Sẽ xóa Light Mode mới |
| Dask Cel đọc thuộc tính RNA `use_outline` không tồn tại | Dropdown Outline Mode của Dask Cel không bao giờ hiện |
| Mix Shader: `weight > 0.0001 ? weight : 1.0` ở 8 node | Node bị "trộn mất" vẫn hiện đầy đủ |
| Alpha của Anime BSDF chỉ làm tối màu | Không có trong suốt |
| Outline Solidify + FBX "Apply Modifiers" | **FBX mất toàn bộ shape key** |
| Handler outline cũ trên mesh dùng chung | Mỗi linked duplicate chèn thêm một slot material |

## Các quyết định mình đã tự đưa ra (chi tiết trong ledger)

1. **Không dùng git worktree**, vì bản build duy nhất trỏ tới `D:/DaskToon`. Làm trên nhánh riêng là đủ tách biệt.
2. **Fixture outline cũ dùng 20 linked duplicate** (22 slot), không phải 200, để file nhỏ.
3. **Hai file `.blend` fixture và ảnh duyệt** được lưu qua Git LFS, theo `.gitattributes` có sẵn.
4. **Bảng màu mặc định truyền lên GPU** được cấp phát bằng `MEM_new_array_zeroed`, vì `GPU_color_band` giải phóng bằng `MEM_delete`.
5. **Sửa luôn Artist Line Modulation** (không biên dịch được), vì không thể kiểm chứng bản sửa weight của nó nếu chưa sửa.
6. **Gộp build của Task 2 và 3, và gộp commit của Task 4 và 5**, vì mỗi lần build tốn 2–11 phút và hai task dùng chung file RNA.
7. **Ẩn/hiện socket bằng `updatefunc`**, áp dụng cho chế độ Dải và cả 6 module của Anime BSDF, để tính năng đã quảng
   cáo hoạt động đúng.
8. **Storage dải màu là tùy chọn** với 3 node DaskToon. Không có điều này, mọi node trong file cũ sẽ thành Undefined.
9. **Nâng giới hạn tham số hàm GLSL từ 36 lên 48**, vì Anime BSDF giờ cần 39 tham số. Trước khi nâng, các tham số thừa
   bị bỏ âm thầm và làm hỏng mọi shader.
10. **Module trong `bl_ui` khai báo `classes`**, còn `register()` chỉ dùng cho handler, theo đúng quy ước của `bl_ui`.
11. **Join Geometry:** nối link lớp vỏ trước, để mesh gốc giữ thứ tự đỉnh ở đầu (có test kiểm tra).
12. **Đồng bộ lại object khi sửa material `.Outline`.** Đây là lỗ hổng mình tự phát hiện, đã có test.
13. **Dấu `dt_outline_sig` lưu dạng dict**, vì ID property dạng mảng không chứa được chuỗi.
14. **"Chuyển từ Đơn giản" đặt điểm dải ở `0.5 ± Softness/2`.** Spec ban đầu ghi `Threshold ± ...`, nhưng như vậy là sai
    với công thức của chế độ Dải. Spec đã được sửa.

## Giới hạn và việc chưa làm

- **Review cuối là tự review.** Mình không chạy reviewer độc lập (subagent), vì bạn chưa yêu cầu dùng subagent. Muốn có
  thêm một lượt review độc lập trước khi merge thì bảo mình.
- **Dự án 2 (export sang Unity) chưa bắt đầu**, đúng như đã thống nhất.
- Mesh có ngon (mặt nhiều hơn 4 cạnh) phải Triangulate trước khi chạy "Chuẩn bị outline cho game".
- Sửa vị trí đỉnh mà không đổi topology thì dấu `dt_outline_sig` không nhận ra dữ liệu outline đã cũ.

## Đo đạc

| Build | Thời gian | Ghi chú |
|---|---|---|
| 2 | 3m46s | Task 2 |
| 3 | 3m17s | Task 2 + 3 |
| 4 | 11m39s | Lỗi: thiếu `node_util.hh` (header RNA đổi nên biên dịch lại nhiều) |
| 5 | 10m28s | Lỗi: `LISTBASE_FOREACH_INDEX` không có trong codebase này |
| 6 | 1m47s | Task 4 + 5 |
| 7 | 1m18s | Nâng `MAX_PARAMETER` |
| 8 | 1m25s | `updatefunc` cho socket |
| 9 | 1m15s | Storage tùy chọn khi đọc file |

## Chạy lại toàn bộ test

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
for t in platform_test shading_test shading_baseline shading_styles_test outline_nodes_test outline_sync_test outline_gamedata_test upgrade_test; do
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_$t.py >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
```
