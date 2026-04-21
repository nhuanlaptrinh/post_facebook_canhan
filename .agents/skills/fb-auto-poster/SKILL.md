---
name: Facebook Auto Poster Tool
description: Kỹ năng quản lý, thiết lập và chạy dự án tự động đăng bài lên Facebook cá nhân thông qua Python Selenium, Google Sheets, và Windows Task Scheduler.
---

# 🤖 Facebook Auto Poster

Skill này cung cấp kiến thức và hướng dẫn tiêu chuẩn để vận hành hoặc tùy biến script `OpenFBV2POST.py` trong dự án. Dự án cho phép tự động lấy nội dung từ Google Sheets và đăng lên trang cá nhân Facebook sử dụng Selenium.

## 📂 Kiến trúc dự án
- **File chính:** `scripts/OpenFBV2POST.py` - Chứa toàn bộ logic đọc sheet, khởi tạo Chrome driver, điều khiển bằng Selenium để đăng ảnh và chữ.
- **Cấu hình Google:** `prn8n-457809-2aa9c8e5f6d4.json` - Service account key để kết nối Google Sheets API.
- **Thư mục Chrome Profile:** `facebook-chrome-profile/` - Được lấy từ **thư mục hiện hành (working directory)** để lưu trữ session đăng nhập. Tính năng này giúp bạn dễ dàng chạy và quản lý profile theo từng thư mục hoặc dự án riêng biệt.
- **Thư mục ảnh:** `images/` - Chứa file ảnh để upload lên bài viết.

## ⚙️ Yêu cầu & Cài đặt môi trường
Đảm bảo đã chạy môi trường ảo (venv) trên Windows và cài đặt các thư viện:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirement.txt
```

*Các thư viện quan trọng:* `selenium`, `gspread`, `pandas`, `oauth2client`...

## 🚀 Các chế độ chạy (Execution Modes)

Dự án hỗ trợ hai chế độ chạy chính:

1. **Chế độ đăng nhập lần đầu (Login Only):**
   Chạy chế độ này lần đầu tiên mặt để hệ thống lưu cookie phiên làm việc vào `facebook-chrome-profile`. Bạn có thể giải quyết các checkpoint (nếu có).
   ```powershell
   python .agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py --login-only
   ```
   
2. **Chế độ chạy tự động bình thường:**
   Tự động phát hiện phiên đăng nhập, đọc bài viết có trạng thái `UNAPPROVED` (chưa duyệt/chưa đăng) từ Google Sheet, thực hiện đăng lên Facebook và đánh dấu lại thành `APPROVED`. (Chỉ đăng 1 bài mỗi lần chạy).
   *(Lưu ý: Nếu chưa có Chrome Profile, lệnh này sẽ tự động chuyển sang Chế độ Đăng nhập lần đầu giúp bạn).*
   ```powershell
   python .agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py
   ```

## 📅 Thiết lập Lịch trình Đăng Bài Hàng Ngày (Task Scheduler)

Để tự động hóa hoàn toàn việc đăng bài lên Facebook mỗi ngày, dự án cần kết hợp cài đặt lịch chạy qua Windows Task Scheduler.

### 💡 Mẹo dành cho Agent (AI) để lấy quyền Admin
Vì Agent thường chạy bằng quyền Standard User (không có quyền cài đặt Task Scheduler), Agent CÓ THỂ ép hệ thống hiển thị hộp thoại xác nhận quyền quản trị (UAC) cho người dùng bằng câu lệnh sau:
```powershell
powershell -c "Start-Process powershell -Verb runAs -ArgumentList '-ExecutionPolicy Bypass -File \"<Đường_dẫn_tuyệt_đối_đến_file_setup>.ps1\"'"
```
Khi Agent chạy lệnh này qua `run_command`, người dùng sẽ nhận được popup UAC trên màn hình. Khi người dùng bấm "Yes", đoạn script cài đặt lịch (ví dụ `setup_4mins.ps1`) sẽ được chạy thành công bằng quyền Admin!

### 1. Nguyên tắc cốt lõi khi chạy ngầm
- Hệ thống làm việc lấy chuẩn từ **thư mục hiện hành** (Working Directory) để lưu profile trình duyệt (`facebook-chrome-profile`), nhận diện ảnh tải lên (`images`) cũng như cấu hình bảo mật Google.
- **Lưu ý quan trọng**: Đảm bảo bạn đã đặt file cấu hình Google Credential JSON (VD: `prn8n-xxxx.json`) vào ngay chính thư mục gốc mà bạn thiết lập làm Working Directory.
- Sử dụng **đường dẫn tuyệt đối** tới file thực thi Python trong môi trường ảo (ví dụ: `C:\path\to\your\venv\Scripts\python.exe`).
- Bắt buộc phải thiết lập **thư mục làm việc** (Start in/Working Directory) để script đọc đúng cấu hình.

### 2. Cài đặt tự động bằng PowerShell
Mở Windows PowerShell tại thư mục làm việc hiện hành (nơi chứa file cấu hình) với quyền Administrator và chạy lệnh sau:

```powershell
# Thiết lập linh hoạt lấy trực tiếp đường dẫn thư mục hiện tại
$projectDir = (Get-Location).Path
$pythonExe = "$projectDir\venv\Scripts\python.exe"
$scriptFile = ".agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py"

# Tạo Action và Trigger
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptFile -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Daily -At 8am

# Đăng ký Task vào hệ thống chạy ẩn
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Auto Post Facebook DaiLy" -Description "Tự động đăng bài Facebook từ Google Sheet mỗi ngày" -RunLevel Highest
```

### 3. Cài đặt thủ công (Giao diện UI)
Nếu không dùng PowerShell, bạn tạo task với các cấu hình sau:
- **Trigger:** Daily, thiết lập thời gian mong muốn (vd: 08:00 AM).
- **Action:** Start a program.
  - *Program/script:* `<Đường_dẫn_tới_thư_mục_của_bạn>\venv\Scripts\python.exe`
  - *Add arguments:* `.agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py`
  - *Start in:* `<Đường_dẫn_tới_thư_mục_của_bạn>\`
## 🐞 Xử lý lỗi (Troubleshooting)

- **Lỗi không click được Upload Ảnh:** Do Facebook cập nhật giao diện modal. Code hiện tại dùng trick kích hoạt `input[type='file']` bị ẩn thông qua Javascript.
- **Lỗi không đăng nhập được/Checkpoint:** Thư mục profile có thể bị lỗi, hãy thử xóa thư mục `facebook-chrome-profile` và chạy lại với cờ lệnh `--login-only`.
- **Lỗi không thấy Chrome:** Script ưu tiên tìm Chrome ở các đường dẫn truyền thống của Windows, nếu Chrome bản Portable cần sửa mảng `possible_paths` trong hàm `find_chrome_binary()`.

## 📎 Phụ lục liên kết
* Xem mã mẫu về dữ liệu data sheet tại: `examples/sheet_data_model.csv`
* Lệnh PowerShell setup tự động môi trường nằm tại: `scripts/setup_env.ps1`
