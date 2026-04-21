$ErrorActionPreference = "Stop"

$projectDir = "d:\100.Skills\post_facebook_canhan"
$pythonExe  = "C:\Users\nhuan\AppData\Local\Programs\Python\Python313\python.exe"
$scriptFile = ".agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py"

Write-Host "Python exe: $pythonExe"
Write-Host "Project dir: $projectDir"

# Xóa task cũ nếu tồn tại
Unregister-ScheduledTask -TaskName "Auto Post Facebook Every 5 Mins" -Confirm:$false -ErrorAction SilentlyContinue

# Action
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptFile `
    -WorkingDirectory $projectDir

# Trigger: chạy ngay sau 10 giây, lặp mỗi 5 phút trong 10 năm
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 4) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

# Đăng ký - KHÔNG dùng RunLevel Highest, không cần quyền Admin
Register-ScheduledTask `
    -TaskName   "Auto Post Facebook Every 5 Mins" `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Description "Tu dong dang bai Facebook tu Google Sheet moi 5 phut" `
    -Force

Write-Host ""
Write-Host "✅ Dang ky Task Scheduler THANH CONG!" -ForegroundColor Green
Write-Host "   Task: 'Auto Post Facebook Every 5 Mins' se chay moi 5 phut."
Start-Sleep -Seconds 3
