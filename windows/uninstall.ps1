# AI 活动 · Windows 卸载
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Dest = Join-Path $env:LOCALAPPDATA "AIStatus"
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*AIStatus*main_win.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$VPy = Join-Path $Dest "venv\Scripts\python.exe"
if (Test-Path $VPy) { & $VPy (Join-Path $Dest "hooks\install_hooks.py") --uninstall }
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "AIStatus" -ErrorAction SilentlyContinue
Remove-Item (Join-Path ([Environment]::GetFolderPath("Programs")) "AI 活动.lnk") -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item $Dest -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "已卸载。浏览器扩展需要在 chrome://extensions 或 edge://extensions 手动移除。" -ForegroundColor Green
