#!/bin/bash
# AI 活动 · macOS 一键安装
# 用法：在终端里进入本文件夹，执行  ./install.sh
# 国内网络慢可以加镜像：PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ./install.sh
set -eo pipefail

[[ "$(uname)" == "Darwin" ]] || { echo "只支持 macOS"; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/Application Support/AIStatus"
APP="$HOME/Applications/AI 活动.app"

say() { printf "\033[1m%s\033[0m\n" "$*"; }

# 1. 找 Python 3.9+
PY=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [[ -x "$c" ]] && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[[ -n "$PY" ]] || { echo "没有找到 Python 3.9+。执行 xcode-select --install 安装命令行工具后重试。"; exit 1; }
say "使用 Python：$PY ($("$PY" -V 2>&1))"

# 2. 复制程序
say "安装到：$DEST"
mkdir -p "$DEST"
rm -rf "$DEST/app" "$DEST/hooks" "$DEST/extension"
cp -R "$SRC/app" "$SRC/hooks" "$SRC/extension" "$DEST/"
cp "$SRC/README.md" "$DEST/README.md"

# 3. 虚拟环境 + PyObjC
if [[ ! -x "$DEST/venv/bin/python" ]]; then "$PY" -m venv "$DEST/venv"; fi
say "安装 PyObjC（首次约 1 分钟）…"
"$DEST/venv/bin/python" -m pip install -q --upgrade pip
"$DEST/venv/bin/python" -m pip install -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz pyobjc-framework-ApplicationServices

# 4. 生成 “AI 活动.app”（权限弹窗会显示这个名字，也能用聚焦搜索打开）
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>AI 活动</string>
  <key>CFBundleDisplayName</key><string>AI 活动</string>
  <key>CFBundleIdentifier</key><string>com.aistatus.widget</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.5</string>
  <key>CFBundleVersion</key><string>1.5</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSAppleEventsUsageDescription</key><string>读取浏览器里打开的 AI 网页的工作状态，并在点击时切换到对应标签页。</string>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launcher" << LAUNCH
#!/bin/bash
export AISTATUS_APP="$APP"
exec "$DEST/venv/bin/python" "$DEST/app/main.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/launcher"
say "已生成应用：$APP"

# 5. 接入 Cursor / Claude Code（检测到才装）
TARGETS=()
[[ -d "$HOME/.claude" ]] || command -v claude >/dev/null 2>&1 && TARGETS+=("claude-code")
[[ -d "$HOME/.cursor" || -d "/Applications/Cursor.app" ]] && TARGETS+=("cursor")
if (( ${#TARGETS[@]} )); then
  say "接入：${TARGETS[*]}"
  "$DEST/venv/bin/python" "$DEST/hooks/install_hooks.py" "${TARGETS[@]}"
fi

# 6. 启动
pkill -f "$DEST/app/main.py" 2>/dev/null || true
open "$APP"
cat << DONE

✅ 安装完成，菜单栏会出现 ✦ 图标，桌面右上角出现小组件。

接下来（各做一次）：
  • 系统会询问“AI 活动”想控制 Safari / Chrome —— 点“允许”
  • Safari：设置 › 高级 › 勾选“显示网页开发者功能”；设置窗口里会多出“开发者”标签页，
    在其中勾选“允许来自 Apple 事件的 JavaScript”
  • Chrome：显示 › 开发者 › 勾选“允许来自 Apple 事件的 JavaScript”
    （可选）想要更准的 token 数：chrome://extensions → 开发者模式 → 加载已解压的扩展程序 → 选择
    $DEST/extension
  • 已接入 Cursor 的话，重启一次 Cursor

DONE
