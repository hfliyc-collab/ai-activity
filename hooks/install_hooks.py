#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键把小组件的 hooks 写进 Cursor 和 Claude Code 的用户级配置（会先备份原文件）。

    python install_hooks.py              # 两个都装
    python install_hooks.py cursor       # 只装 Cursor
    python install_hooks.py claude-code  # 只装 Claude Code
    python install_hooks.py --uninstall  # 移除（同样会备份）

只增删本工具自己的条目（命令里含 agent_hook.py），其他 hooks 原样保留。
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "agent_hook.py")
MARK = "agent_hook.py"

CURSOR_FILE = os.path.expanduser(os.path.join("~", ".cursor", "hooks.json"))
CLAUDE_FILE = os.path.expanduser(os.path.join("~", ".claude", "settings.json"))

CURSOR_EVENTS = [("beforeSubmitPrompt", "start"), ("afterAgentResponse", "text"),
                 ("afterFileEdit", "progress"), ("afterShellExecution", "progress"),
                 ("stop", "stop")]
CLAUDE_EVENTS = [("UserPromptSubmit", "start", None), ("PostToolUse", "progress", "*"),
                 ("Notification", "waiting", None), ("Stop", "stop", None)]


def _arg(path):
    if sys.platform == "win32":
        # 正斜杠 + 无空格时不加引号：cmd、PowerShell、Git Bash 都能直接运行
        path = path.replace("\\", "/")
        return f'"{path}"' if " " in path else path
    return f'"{path}"'


def command(src, phase):
    return f"{_arg(sys.executable)} {_arg(HOOK)} {src} {phase}"


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError as e:
        sys.exit(f"{path} 不是合法 JSON，请先手动修好再运行：{e}")
    backup = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, backup)
    print(f"  已备份 → {backup}")
    return data


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def setup_cursor(remove=False):
    print(f"Cursor：{CURSOR_FILE}")
    data = load(CURSOR_FILE)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    for event, phase in CURSOR_EVENTS:
        kept = [h for h in hooks.get(event, []) if MARK not in json.dumps(h)]
        if not remove:
            kept.append({"command": command("cursor", phase)})
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    save(CURSOR_FILE, data)
    print("  完成。重启 Cursor 后生效。")


def setup_claude_code(remove=False):
    print(f"Claude Code：{CLAUDE_FILE}")
    data = load(CLAUDE_FILE)
    hooks = data.setdefault("hooks", {})
    for event, phase, matcher in CLAUDE_EVENTS:
        kept = [g for g in hooks.get(event, []) if MARK not in json.dumps(g)]
        if not remove:
            group = {"hooks": [{"type": "command", "command": command("claude-code", phase)}]}
            if matcher:
                group = {"matcher": matcher, **group}
            kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop("hooks", None)
    save(CLAUDE_FILE, data)
    print("  完成。新开的 Claude Code 会话生效。")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    remove = "--uninstall" in sys.argv
    targets = args or ["cursor", "claude-code"]
    for t in targets:
        if t == "cursor":
            setup_cursor(remove)
        elif t == "claude-code":
            setup_claude_code(remove)
        else:
            sys.exit(f"不认识的目标：{t}（可选 cursor / claude-code）")


if __name__ == "__main__":
    main()
