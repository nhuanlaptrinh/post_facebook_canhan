# Mã Prompt Dùng Để Sinh Lệnh Chạy Task Scheduler Bằng PowerShell

Copy toàn bộ phần bên dưới gửi cho AI khi bạn cần thiết lập cron job bằng Windows Task Scheduler:

---

Bạn là một chuyên gia Windows System Admin xuất sắc. 
Tôi vừa code xong một script Python chạy tự động browser (Selenium) trên Windows. Tôi cần đưa file này lên Windows Task Scheduler để chạy theo lịch trình.

Hãy viết cho tôi MỘT ĐOẠN LỆNH POWERSHELL DUY NHẤT (dùng cmdlet `New-ScheduledTaskAction`, `New-ScheduledTaskTrigger`, `Register-ScheduledTask`) để tôi dán thẳng vào PowerShell (Run as Administrator) là hệ thống tự thiết lập Task Scheduler xong luôn.

⚡ CÁC QUY TẮC BẮT BUỘC KHI TẠO LỆNH:
1. Đừng tự chế đường dẫn. Hãy hỏi tôi cung cấp [Đường dẫn tuyệt đối thư mục dự án] và [Tên file Python] trước khi xuất code (trừ khi tôi đã nhập từ trước).
2. Lệnh gọi Python phải nhắm thẳng vào Python của môi trường ảo (ví dụ: D:\project\venv\Scripts\python.exe) thay vì python chung của máy.
3. Phải thiết lập Working Directory (Start In) đúng vào thư mục dự án.
4. Phải redirect output ra file log bằng cách bọc trong cmd /c với >> log_file.log 2>&1.
5. Nếu muốn chạy nhiều lần trong ngày (ví dụ mỗi 8 tiếng), hãy cấu hình Trigger với -RepetitionInterval.
6. Sau khi tạo xong, hãy thêm lệnh `Get-ScheduledTask -TaskName "TenTask"` để in ra xác nhận.

Tôi muốn chạy file này với lịch trình: [HÃY ĐIỀN THỜI GIAN VÀ ĐƯỜNG DẪN THƯ MỤC CỦA BẠN VÀO ĐÂY]. Hãy sinh code ra cho tôi!
