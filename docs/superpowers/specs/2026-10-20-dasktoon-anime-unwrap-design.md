# Trải UV anime (2026-10-20)

Người dùng hỏi "có thể tối ưu khả năng trải UV?". Chọn mục tiêu: dễ tô vẽ (mỗi bộ phận một mảng, đường cắt ở chỗ khuất,
ít méo), nét hơn ở chỗ quan trọng, đối xứng tiết kiệm chỗ (tay, chân, giày; mặt, thân, tóc, áo giữ nguyên), UV kín hơn
cho game; model đã tô thì chuyển ảnh sang UV mới, giữ UV cũ. Duyệt thiết kế trong trò chuyện, "Duyệt, làm tự động".

## 1. Hiện trạng

Bắt đầu tô vẽ, nút Sửa của mục UV trong Kiểm tra model và bộ gộp vật liệu đều chỉ gọi Phóng Chiếu UV Thông Minh: cắt
theo góc gập, không biết bộ phận, nhiều mảng vụn, đường cắt có thể qua mặt, mặt không được ưu tiên điểm ảnh.

## 2. Trải UV anime (`dasktoon.uv_unwrap_anime`)

Ở menu UV của chế độ biên soạn và menu ô vật liệu; Bắt đầu tô vẽ và nút Sửa UV dùng nó cho lưới chưa có UV. Làm trên
các lưới đang chọn (hoặc lưới đang hoạt động), từng bước:

1. **Nhãn mặt.** Lưới có khung DaskToon: đầu, thân, tay, chân theo vùng cơ thể của khung (`regions.analyse`). Không có
   khung: chỉ theo mảnh rời (ruling 1). Mảnh rời của lưới khác (tóc, mảnh mắt) là nhãn riêng. Mặt lấy nhãn nhiều nhất
   trong các đỉnh của nó.
2. **Đường cắt.** Cạnh giữa hai mặt khác nhãn là đường cắt. Trong mỗi nhóm cùng nhãn và liền nhau: nhóm kín (không
   biên) hoặc hình ống (từ hai vòng biên) được cắt thêm một đường dọc theo trục dài của nhóm, đi ở phía khuất: sau lưng
   (+Y) cho đầu, thân, tóc, quần áo; mặt dưới (−Z) cho tay; mặt trong (về phía x = 0) cho chân. Đường cắt là đường ngắn
   nhất trên các cạnh, giá mỗi cạnh tăng theo độ "lộ" của nó (ruling 2). Đầu cắt dọc sau gáy, nên mặt liền một mảng.
3. **Trải** bằng "Ít kéo dãn nhất" (SLIM) của Blender, lấp lỗ.
4. **Điểm ảnh theo độ quan trọng.** Cân đều độ nét các mảng, rồi phóng mảng mặt (nhãn đầu, mặt hướng ra trước) 1,5 lần,
   thu mảng khuất (mặt hướng xuống dưới ở đáy chân, như lòng bàn chân) còn một nửa.
5. **Đối xứng.** Mặt thuộc tay, chân (cả giày, găng, ống tay trong vùng tay chân) bên phải có cặp đối xứng ở bên trái
   (đỉnh ở x đối nhau, sai số 0,1% chiều cao) thì lấy đúng UV của cặp: hai bên chồng khít. Không đủ cặp thì để riêng.
6. **Xếp kín.** Mỗi vật liệu một ảnh: mặt dùng chung vật liệu (kể cả từ nhiều lưới) xếp chung, theo đúng hình mảng, cho
   xoay, khe 8 điểm ảnh ở cỡ 2048 (0,004). Mảng bên phải đã chồng lên bên trái không xếp riêng.
7. **Ảnh cũ.** Lưới đã có UV mà vật liệu nối ảnh vào shader: UV cũ giữ tên cũ (đổi thành "<tên> Old"), UV mới làm UV
   hoạt động và UV kết xuất; mọi ảnh nối vào shader anime và mọi ảnh lớp của chúng được chuyển từng điểm ảnh sang UV mới
   (mỗi tam giác của UV mới lấy màu ở chỗ tương ứng của UV cũ, kể cả alpha); nút ảnh dùng UV hoạt động nên tự theo UV mới.

## 3. Kiểm thử

Chạy nền (`dasktoon_uv_unwrap_test`): trên nhân vật thử của vùng cơ thể (có khung): không mảng nào chồng nhau ngoài cặp
đối xứng; mặt là một mảng; đường cắt ở đầu nằm sau; tay chân phải chồng khít bên trái; mặt nét hơn thân (mật độ điểm
ảnh); phần ảnh được dùng; chuyển ảnh giữ màu tại các điểm trên bề mặt; nhiều lưới cùng vật liệu xếp chung không chồng.
Model thật (bản sao): đo số mảng, phần ảnh được dùng, độ nét mặt so với thân, thời gian. Ảnh chụp cửa sổ thật.

## 4. Quyết định (tự động)

1. Không có khung thì chỉ nhãn theo mảnh rời, không tự ước lượng bộ xương ngầm như đã nói trong trò chuyện: ước lượng
   ngầm cần chạy cả bộ tự gắn khung trên bản sao (vài giây đến mười giây), để sau. Cái giá: lưới liền một khối chưa gắn
   khung chỉ được cắt dọc một đường, tay chân không thành mảng riêng.
2. Đường cắt phía khuất theo hướng cố định của nhân vật đứng chuẩn (quay ra −Y), đúng điều Kiểm tra model đòi hỏi.
3. Mặt nét gấp 1,5 lần, lòng bàn chân và mặt dưới cùng một nửa; khe 8 điểm ảnh: đủ cho mipmap của game, vẫn kín.
4. Bắt đầu tô vẽ trước đây để khe 20 điểm ảnh cho nét đổ màu không lem; nay khe 8 điểm ảnh và nét lem của Blender (Bleed)
   đặt 4 điểm ảnh khi Bắt đầu tô vẽ.
5. Xếp theo đúng hình mảng chỉ khi bấm Trải UV anime (ô "Xếp thật kín", mặc định bật): trên model thật mất 24 đến 78 s,
   hình bao lồi còn chậm hơn; Bắt đầu tô vẽ và nút Sửa xếp theo hình chữ nhật bao (4 đến 11 s, kém kín vài phần trăm).
6. Đường cắt mới thay mọi đường cắt cũ; chỗ tay chân phải chồng lên trái, khi chuyển ảnh cũ thì hình bên trái được giữ.
7. Ruling 3 thu hẹp: mặt gấp 1,5 lần; chưa thu nhỏ lòng bàn chân (chưa là mảng riêng).
