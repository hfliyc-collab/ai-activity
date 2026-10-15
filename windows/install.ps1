# AI 活动 · Windows 一键安装
# 用法：双击仓库根目录的 install.bat
# 国内网络慢：先在 PowerShell 里执行  $env:PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"  再运行本脚本
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Src  = Split-Path -Parent $PSScriptRoot
$Dest = Join-Path $env:LOCALAPPDATA "AIStatus"
function Say($m)  { Write-Host $m -ForegroundColor Cyan }
function Fail($m) { Write-Host $m -ForegroundColor Red; exit 1 }

# 1. 找 Python（优先 3.12）
function Find-Python {
  foreach ($v in "3.12", "3.13", "3.11", "3.10") {
    try {
      $p = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() }
    } catch {}
  }
  foreach ($c in "python", "python3") {
    try {
      $p = & $c -c "import sys; print(sys.executable if sys.version_info >= (3, 10) else '')" 2>$null
      if ($LASTEXITCODE -eq 0 -and $p -and $p.Trim() -and ($p -notmatch "WindowsApps")) { return $p.Trim() }
    } catch {}
  }
  return $null
}
$Py = Find-Python
if (-not $Py) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail "没有找到 Python 3.10 以上版本。请到 https://www.python.org/downloads/ 安装 Python 3.12（勾选 Add to PATH），再重新运行。"
  }
  Say "没有找到合适的 Python，正在通过 winget 安装 Python 3.12…"
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
  $Py = Find-Python
  if (-not $Py) { Fail "Python 安装后仍未找到，请重新打开窗口再运行一次 install.bat。" }
}
Say "使用 Python：$Py"

# 2. 停掉正在运行的旧版本，复制程序
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*AIStatus*main_win.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Say "安装到：$Dest"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
foreach ($d in "app", "windows", "hooks", "extension") {
  $t = Join-Path $Dest $d
  if (Test-Path $t) { Remove-Item $t -Recurse -Force }
  Copy-Item (Join-Path $Src $d) $t -Recurse
}
Copy-Item (Join-Path $Src "README.md") $Dest -Force

# 3. 虚拟环境与依赖
$Venv = Join-Path $Dest "venv"
$VPy  = Join-Path $Venv "Scripts\python.exe"
$VPyw = Join-Path $Venv "Scripts\pythonw.exe"
if (-not (Test-Path $VPy)) { & $Py -m venv $Venv }
if (-not (Test-Path $VPy)) { Fail "创建 Python 虚拟环境失败。" }
Say "安装依赖（pywebview、pystray、Pillow），首次约 1 分钟…"
& $VPy -m pip install -q --disable-pip-version-check --upgrade pip
& $VPy -m pip install -q --disable-pip-version-check pywebview pystray pillow
if ($LASTEXITCODE -ne 0) { Fail "依赖安装失败。若你的 Python 版本很新，请安装 Python 3.12 后重试。" }

# 4. WebView2 运行库（Windows 11 自带；Windows 10 可能需要安装）
$wvKey = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
$wv = @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$wvKey",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$wvKey",
        "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$wvKey") | Where-Object { Test-Path $_ }
if (-not $wv) {
  Say "未检测到 Microsoft Edge WebView2 运行库，正在打开下载页，安装后再运行一次 install.bat。"
  Start-Process "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
}

# 5. 接入 Claude Code / Cursor（检测到才装，原配置会先备份）
$targets = @()
if ((Test-Path "$HOME\.claude") -or (Get-Command claude -ErrorAction SilentlyContinue)) { $targets += "claude-code" }
if ((Test-Path "$HOME\.cursor") -or (Test-Path "$env:LOCALAPPDATA\Programs\cursor")) { $targets += "cursor" }
if ($targets.Count -gt 0) {
  Say ("接入：" + ($targets -join "、"))
  & $VPy (Join-Path $Dest "hooks\install_hooks.py") @targets
}

# 6. 开始菜单快捷方式（可以在开始菜单搜索“AI 活动”）
$Main = Join-Path $Dest "windows\main_win.py"
$Ico  = Join-Path $Dest "windows\aistatus.ico"
& $VPy -c "import sys; sys.path.insert(0, r'$Dest\windows'); sys.path.insert(0, r'$Dest\app'); from main_win import tray_image; tray_image().save(r'$Ico', sizes=[(16,16),(32,32),(48,48),(64,64)])" 2>$null
$Lnk = Join-Path ([Environment]::GetFolderPath("Programs")) "AI 活动.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($Lnk)
$s.TargetPath = $VPyw
$s.Arguments = '"' + $Main + '"'
$s.WorkingDirectory = $Dest
$s.Description = "AI 活动：汇总所有 AI 的工作状态"
if (Test-Path $Ico) { $s.IconLocation = $Ico }
$s.Save()

# 7. 启动
Start-Process $VPyw -ArgumentList ('"' + $Main + '"') -WorkingDirectory $Dest
Write-Host ""
Write-Host "安装完成。桌面右上角会出现小组件，任务栏右下角托盘区有 ✦ 图标。" -ForegroundColor Green
Write-Host ""
Write-Host "最后一步：安装浏览器扩展（Windows 上读取网页状态必须用它）"
Write-Host "  1. 在 Chrome 地址栏打开 chrome://extensions （Edge 是 edge://extensions）"
Write-Host "  2. 打开右上角“开发者模式”（Edge 在左侧，叫“开发人员模式”）"
Write-Host "  3. 点“加载已解压的扩展程序”，选择刚刚打开的这个文件夹："
Write-Host "     $Dest\extension" -ForegroundColor Yellow
Write-Host "  4. 刷新已经打开的 AI 网页"
Write-Host ""
if ($targets -contains "cursor") { Write-Host "已接入 Cursor：请重启一次 Cursor。" }
Start-Process explorer.exe (Join-Path $Dest "extension")
