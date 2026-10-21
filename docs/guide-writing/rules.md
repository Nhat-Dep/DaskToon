# Quy tắc cho người viết trang Hướng dẫn (Antigravity hoặc trợ lý khác)

Bạn viết các trang Hướng dẫn chức năng của DaskToon theo `docs/guide-writing/pages.md`. Mỗi lần được giao **một đợt**
trong đó. DaskToon là bản Blender 5.2 sửa riêng cho nhân vật anime; dự án ở `D:\DaskToon`, nhánh `dasktoon-master`.

## 1. Không bao giờ làm

- Không mở để sửa, không lưu đè, không xoá bất cứ gì trong `D:\game`, `D:\Unity`, `D:\GodotGame`, `D:\gd`. Đó là model
  và dự án thật của người dùng.
- Không dùng model của người dùng để làm ảnh. Ảnh chỉ làm từ nhân vật thử trong `tests/python` (xem mục 5).
- Không `git push`, không `git reset`, `git clean`, `git rebase`, `git commit --amend`, không đổi nhánh.
- Không sửa tệp nào ngoài danh sách ở mục 2. Thấy lỗi trong mã, thiếu bản dịch, phép thử hỏng: ghi vào
  `docs/guide-writing/notes.md`, đừng tự sửa.
- Không làm việc khi Claude Code đang làm trong `D:\DaskToon` (người dùng sẽ báo).

## 2. Tệp được sửa

- `scripts/modules/dasktoon_guide/pages/en/*.html`, `pages/vi/*.html` (trang mới của đợt, `features.html`, một dòng
  trong `index.html`)
- `scripts/modules/dasktoon_guide/pages/pictures/*.png` (ảnh mới, không sửa ảnh cũ)
- `tools/dasktoon_feature_pictures.py` (đoạn mã làm ảnh, tạo ở đợt đầu cần ảnh)
- `docs/guide-writing/notes.md`

## 3. Tìm hiểu chức năng

- Đọc cột "Đọc" của trang trong `pages.md`. **Mã là đúng nhất**: tên nút lấy từ `bl_label`, `text=` và tên thuộc tính
  trong `scripts/startup/bl_ui/dasktoon_*.py`; bản thiết kế (`docs/superpowers/specs/`) có chỗ đã đổi sau này.
- Tên tiếng Việt của nút lấy từ `scripts/startup/bl_ui/dasktoon_translations.py` (bảng `VI`, `VI_CONTEXT`); tên của chính
  Blender lấy theo bản dịch của Blender (lệnh kiểm tra ở mục 6 biết cả hai).
- Chỉ viết điều mã làm thật. Không chắc thì bỏ ra và ghi câu hỏi vào `notes.md`.

## 4. Viết trang

Đọc trước hai trang mẫu: `pages/vi/rig.html` và `pages/vi/materials.html` (và bản `en`), rồi viết theo đúng kiểu đó.

Khung một trang (`NAME` là tên tệp; trang tiếng Anh: `lang="en"`, "‹ All Features", liên kết `../vi/NAME.html` chữ
"Tiếng Việt"):

```html
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tên trang — Hướng dẫn DaskToon</title>
<link rel="stylesheet" href="../guide.css">
</head>
<body>
<main>
<nav><a href="features.html">‹ Mọi chức năng</a> <a href="../en/NAME.html">English</a></nav>
<h1>Tên trang</h1>
<p class="lead">Một hai câu: chức năng này dùng để làm gì.</p>
<figure><img src="../pictures/NAME.png" alt="Ảnh cho thấy gì."><figcaption>Ảnh cho thấy gì.</figcaption></figure>
<section id="phan-mot">
<h2>Tên phần</h2>
<p>...</p>
</section>
</main>
</body>
</html>
```

- `features.html` cùng khung, `<nav>` chỉ có `<a href="index.html">‹ Hướng dẫn</a>` và liên kết sang thứ tiếng kia. Các
  trang xếp theo nhóm (`<h2>`): Bắt đầu; Shader và hình; Tô vẽ và UV; Rig; Biểu cảm; Hoạt hình; Xuất. Mỗi trang một dòng
  `<li><a href="NAME.html">Tên trang</a>: một câu</li>`. Chỉ đưa vào trang đã có.
- `index.html`: thêm sau danh sách các bước một dòng `<p>Mọi chức năng riêng của DaskToon: <a
  href="features.html">Các chức năng</a>.</p>` (bản tiếng Anh: "Every feature of DaskToon of its own: <a
  href="features.html">Features</a>.").
- Ngắn: câu mở đầu 1–2 câu; 2–6 phần; mỗi phần tối đa 5 câu; cả trang khoảng 450 chữ trở xuống. Mỗi phần nói: dùng để
  làm gì, bấm ở đâu, làm thế nào, một điều cần biết (giới hạn, mẹo).
- `id` của phần viết thường, không dấu, nối bằng gạch ngang, **giống nhau ở hai thứ tiếng**. Hai bản có cùng phần và
  cùng ảnh.
- `<b>` **chỉ** cho tên nút, bảng, thẻ, menu đúng như giao diện hiện, ở đúng thứ tiếng của trang. Đường đi trong menu
  nối bằng ` › `: `<b>Thêm › Khung Rối › Khung người anime</b>`. Phím: `<kbd>Ctrl R</kbd>`. Tên tệp, thư mục, giá trị
  gõ vào: `<code>`.
- Tiếng Việt dễ hiểu, không chen từ tiếng Anh khi đã có từ Việt; dùng từ như các trang mẫu (lưới, khung xương, trọng
  số, vật liệu, bản đồ UV, nướng). Tên riêng giữ nguyên: DaskToon, Unity, Godot, VRM, ARKit.
- Bản tiếng Anh nói cùng nội dung, câu ngắn, rõ.

## 5. Ảnh (không bắt buộc, tối đa một ảnh một trang)

- Ảnh cho thấy kết quả của chức năng (trước và sau, vài khung cạnh nhau), **không chữ trong ảnh**, không chụp giao diện.
  Chỉ một bộ ảnh dùng cho cả hai thứ tiếng; chú thích dưới ảnh nói ảnh cho thấy gì.
- Làm bằng `tools/dasktoon_feature_pictures.py`, theo cách của `tools/dasktoon_guide_pictures.py` (dựng nhân vật thử
  từ `tests/python`, chụp, ghép các khung). Mỗi trang một hàm, chạy được riêng:
  `DaskToon.exe -b --factory-startup --python tools/dasktoon_feature_pictures.py -- outline`.
- PNG, rộng tối đa 1200 điểm ảnh, dưới 300 KB, lưu ở `pages/pictures/NAME.png`.

## 6. Kiểm tra trước khi giao (PowerShell, trong `D:\DaskToon`)

```powershell
$B = "D:\build_windows_x64_vc18_Release\bin\Release"
$env:DASKTOON_CONFIG_DIR = "$env:TEMP\dasktoon_guide_writer"
& "$B\5.2\python\bin\python.exe" tools\dasktoon_sync_build.py "$B\5.2"
& "$B\DaskToon.exe" -b --factory-startup --python tools\dasktoon_guide_check.py
& "$B\DaskToon.exe" -b --factory-startup --python-exit-code 1 --python tests\python\dasktoon_guide_ui_test.py
```

- Lệnh thứ ba in từng chỗ sai (`PROBLEM ...`) và `GUIDE CHECK: 0 problems` khi sạch. Phải sạch. Nó kiểm tra: trang có
  đủ hai thứ tiếng, `lang` đúng, có liên kết sang thứ tiếng kia, liên kết và ảnh có thật, hai bản cùng phần và cùng ảnh,
  mọi trang được dẫn tới từ `index.html`, mọi tên trong `<b>` là tên giao diện có thật ở thứ tiếng đó.
- Lệnh thứ tư phải kết thúc bằng `OK`.
- Mở vài trang trong trình duyệt xem có vỡ khung không.

## 7. Giao đợt

```powershell
git add scripts/modules/dasktoon_guide/pages tools/dasktoon_feature_pictures.py docs/guide-writing/notes.md
git commit -m "docs(guide): đợt N, <các trang>"
```

Không đẩy lên. Trong `notes.md`, thêm một mục cho đợt: các trang đã viết, câu hỏi, chỗ không chắc, lỗi thấy trong
DaskToon. Claude sẽ soát, chạy toàn bộ phép thử rồi đẩy lên GitHub.
