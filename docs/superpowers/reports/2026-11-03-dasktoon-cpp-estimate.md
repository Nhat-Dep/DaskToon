# Chuyển sang C++ thì nhanh hơn bao nhiêu, nhẹ hơn bao nhiêu

Ngày 2026-11-03. Đo trên bản sao Encore, Evita, Violet và cảnh trend; bản build VS 2026, Release.

## Cách đo

Mỗi việc chạy hai lần trong DaskToon chạy nền:

1. Không đo gì: lấy thời gian thật.
2. Có `sys.monitoring` (PEP 669) theo dõi mọi lần gọi vào thứ không phải hàm Python, cho tới khi nó trả về: lệnh và hàm của Blender,
   numpy, zlib, Cycles. Lần chạy này cho biết thời gian nằm trong phần đã biên dịch.

Phần còn lại của thời gian thật là phần Python: mã DaskToon, phần Python của numpy, hàm có sẵn như `len` hay `dict.get`. Chỉ phần này
nhanh lên được khi chuyển sang C++.

Phần Python này gồm cả phép tính numpy viết thẳng trong biểu thức và việc đọc thuộc tính qua RNA, vốn không qua lệnh gọi nên không
tách ra được. Vì vậy cột "tối đa" là trần. Cột "C++ ×3" và "C++ ×10" giả định phần Python nhanh lên 3 hoặc 10 lần, còn phần đã biên dịch
giữ nguyên.

cProfile cho số sai ở đây: lời gọi hàm RNA (như `frame_set` hay `ray_cast`) và phép tính numpy viết thẳng bị tính vào hàm Python bao
quanh. Lần đo đầu cũng trộn thời gian của kịch bản đo vào DaskToon, vì đường dẫn thư mục tạm có chữ "DaskToon". Không dùng các số đó.

## Kết quả

Đơn vị: giây.

| Việc | Model | Hiện tại | Đã biên dịch | Python | C++ ×3 | C++ ×10 | Tối đa |
|---|---|---|---|---|---|---|---|
| Kiểm tra khung | Evita | 3,97 | 1,54 | 61% | 2,35 | 1,78 | 1,54 |
| Biểu cảm tự động | Encore | 1,23 | 0,30 | 75% | 0,61 | 0,39 | 0,30 |
| | Evita | 2,84 | 0,91 | 68% | 1,56 | 1,10 | 0,91 |
| | Violet | 1,50 | 0,55 | 63% | 0,87 | 0,65 | 0,55 |
| Khung người anime | Encore | 6,85 | 2,40 | 65% | 3,88 | 2,85 | 2,40 |
| | Evita | 13,88 | 4,66 | 66% | 7,73 | 5,58 | 4,66 |
| | Violet | 6,91 | 2,41 | 65% | 3,91 | 2,86 | 2,41 |
| Trải UV anime | Encore | 32,4 | 9,8 | 70% | 17,3 | 12,1 | 9,8 |
| | Violet | 21,9 | 7,8 | 64% | 12,5 | 9,2 | 7,8 |
| Xuất sang Unity | Encore | 131 | 105,5 | 19% | 114 | 108 | 105,5 |
| | Violet | 26,6 | 16,6 | 38% | 19,9 | 17,6 | 16,6 |
| | Evita | 27,9 | khoảng 18,7 | khoảng 33% | khoảng 21,8 | khoảng 19,6 | khoảng 18,7 |
| Phát lại cảnh trend, mỗi khung hình | 5 nhân vật | 0,115 | 0,115 | 0% | 0,115 | 0,115 | 0,115 |
| Vẽ lại bảng Biểu cảm | | 0,003 | | | | | |

Khi xuất Encore, 87 giây là Cycles nướng màu (`_cycles.bake`, `reset`, `free`) và 10 giây là zlib nén PNG; cả hai đã là C/C++. Số của
Evita là ước tính: lần đo chi tiết chỉ chạy cho Encore và Violet, nên phần nướng màu của Evita lấy theo tỉ lệ của Violet.

Một lượt dùng điển hình trên Encore (khung người, Biểu cảm tự động, Trải UV, xuất) mất 171,5 giây. Chuyển hết sang C++ còn khoảng 136
giây nếu phần Python nhanh gấp 3, khoảng 123 giây nếu gấp 10: bớt 21 đến 28%.

## Một thay đổi một dòng, không cần C++

Nướng màu đang dùng 16 lượt mỗi điểm ảnh (`bake_samples = 16`). Xuất Encore với 16, 4 và 1 lượt, rồi so mọi ảnh PNG đã xuất:

| Lượt | Xuất | Nướng màu (39 lần) | Sai khác trung bình so với 16 | Chỗ lệch nhất |
|---|---|---|---|---|
| 16 | 155,5 | 121,1 | | |
| 4 | 106,2 | 68,8 | 0,01 / 255 | 22 / 255, vài điểm sát mép |
| 1 | 77,9 | 45,1 | 0,03 / 255 | 32 / 255 |

Riêng lượt này, xuất 16 lượt mất 155 giây thay vì 131 như lần đo trước; máy chạy không đều giữa các lần.

Hạ xuống 4 lượt bớt 32% thời gian xuất, và ngang với việc chuyển hết DaskToon sang C++ cho cả lượt dùng. Ở 1 lượt vẫn còn khoảng
1,1 giây mỗi lần nướng; ẩn các vật thể khác trong lúc nướng không đổi được con số này (71 so với 69 giây, ảnh giống hệt), nên phí đó
nằm trong mỗi lần Cycles khởi động.

## Dung lượng

- Mã Python của DaskToon: 1,21 MB trong 104 file, 27.225 dòng. Trong đó 12.573 dòng là giao diện ở `bl_ui`, phần Blender bắt buộc viết
  bằng Python.
- Bản cài: 829 MB. Chuyển hết sang C++ bớt nhiều nhất 1,21 MB (0,15%), mà mã máy tương ứng lại vào chương trình. Coi như không đổi.
- Python (152 MB) vẫn phải giữ: toàn bộ giao diện Blender và các trình xuất FBX, glTF viết bằng Python.
- Không liên quan tới C++, gói Python đang mang thừa: pip 11 MB, Cython 10 MB, setuptools 5 MB, mesonbuild 5 MB (đồ để build), cùng
  pxr 27 MB và MaterialX 6 MB (đi với USD, xem báo cáo người mới). Tổng 64 MB.

## Nên làm gì

1. Hạ `bake_samples` xuống 4. Cách này bớt nhiều nhất cho ít công nhất.
2. Không chuyển cả DaskToon sang C++: khoảng 14.600 dòng logic, mỗi lần sửa phải build lại, đổi lại chỉ bớt 21 đến 28%.
3. Nếu muốn nhanh hơn nữa, chỉ viết lại vài vòng lặp nóng nhất, bằng numpy hoặc C++. Theo cProfile:
   - `transfer.draw`, `_sample`, `bleed`: tô lại ảnh theo UV, 13 giây trên Evita.
   - `unwrap._area3`: 9,6 giây trên Violet.
   - `body_shape._grow` và `walk`, `correctives.child_share`: phần lớn thời gian của khung người.
   - `eye_shapes._joined`: gom mảnh rời của mắt.

## Lỗi tìm thấy khi đo

Xuất Violet hỏng: vải hai mặt (hai mặt trùng chỗ, quay ngược nhau) làm tổng hướng viền bằng 0, chia cho 0 ra NaN, và trình xuất FBX từ
chối. Đã sửa trong `dasktoon_outline_gamedata.py`: góc nào như vậy thì đẩy viền theo mặt của chính nó. Phép thử
`test_two_sided_sheet_has_a_direction` và `test_zero_encodes_to_the_surface_normal` báo lỗi trên mã cũ, qua trên mã mới; Violet xuất
được.
