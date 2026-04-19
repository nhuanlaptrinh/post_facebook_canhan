# Hướng dẫn thiết lập môi trường bằng PowerShell

# 1. Tạo môi trường ảo (Virtual Environment)
Write-Host "Đang tạo môi trường ảo..."
python -m venv venv

# 2. Kích hoạt môi trường (có thể sẽ cần bypass execution policy trên Windows)
Write-Host "Kích hoạt môi trường ảo..."
& .\venv\Scripts\Activate.ps1

# 3. Cài đặt các thư viện cần thiết từ file requirement.txt
Write-Host "Cài đặt thư viện..."
pip install -r requirement.txt

Write-Host "Thiết lập hoàn tất!"
