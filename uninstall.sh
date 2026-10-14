#!/bin/bash
# 卸载 AI 活动
DEST="$HOME/Library/Application Support/AIStatus"
APP="$HOME/Applications/AI 活动.app"
pkill -f "$DEST/app/main.py" 2>/dev/null
[[ -x "$DEST/venv/bin/python" ]] && "$DEST/venv/bin/python" "$DEST/hooks/install_hooks.py" --uninstall
rm -f "$HOME/Library/LaunchAgents/com.aistatus.widget.plist"
rm -rf "$APP" "$DEST"
echo "已卸载。Chrome 里的扩展需要在 chrome://extensions 手动移除。"
