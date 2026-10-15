#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor / Claude Code 的 hook 脚本：把 Agent 的开始、进度、结束推送到桌面小组件。

用法（由 hooks 配置调用，不用手动运行）：
    python agent_hook.py <cursor|claude-code> <start|progress|text|waiting|stop>

hook 的输入从 stdin 读取（JSON）。小组件没开时静默跳过，绝不影响 Agent 本身。
Claude Code 结束时会读取本地 transcript，得到真实的输出 token 和上下文大小；
Cursor 的 hooks 不提供 token 数，用 afterAgentResponse 的文本做估算。
对话文字只在本机用于计数，不会发送出去。
"""
import json
import os
import sys
import urllib.request

PORT = int(os.environ.get("AI_WIDGET_PORT", "47823"))
URL = f"http://127.0.0.1:{PORT}/event"
LABELS = {"cursor": "Cursor", "claude-code": "Claude Code"}


def post(ev):
    try:
        req = urllib.request.Request(URL, data=json.dumps(ev).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=0.8).read()
    except Exception:
        pass


def est_tokens(text):
    cjk = sum(1 for ch in text if "\u3000" <= ch <= "\u9fff" or "\uac00" <= ch <= "\ud7af"
              or "\uff00" <= ch <= "\uffef")
    return cjk + (len(text) - cjk + 3) // 4


def project_name(d):
    roots = d.get("workspace_roots") or []
    path = (roots[0] if roots else None) or d.get("cwd") or ""
    return os.path.basename(str(path).rstrip("/\\"))


def claude_code_usage(path):
    """读取 Claude Code transcript，统计最近一轮的输出 token 与上下文大小。"""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()[-5000:]
    except OSError:
        return {}
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except ValueError:
            pass
    start = 0
    for i, e in enumerate(entries):   # 最后一条“用户真正输入”的位置（排除工具结果）
        if e.get("type") != "user":
            continue
        c = (e.get("message") or {}).get("content")
        if isinstance(c, str) or (isinstance(c, list) and any(
                isinstance(x, dict) and x.get("type") == "text" for x in c)):
            start = i
    per_msg, model = {}, ""
    for i, e in enumerate(entries[start + 1:]):
        if e.get("type") != "assistant":
            continue
        m = e.get("message") or {}
        if isinstance(m.get("usage"), dict):
            per_msg[m.get("id") or i] = m["usage"]   # 同一条消息会写多行，取最后一次
            model = m.get("model") or model
    if not per_msg:
        return {}
    out = sum(int(u.get("output_tokens") or 0) for u in per_msg.values())
    last = list(per_msg.values())[-1]
    ctx = sum(int(last.get(k) or 0) for k in
              ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return {"tokens_out": out, "tokens_in": ctx, "est": False, "model": model}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "agent"
    phase = sys.argv[2] if len(sys.argv) > 2 else "progress"
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")   # Windows 管道默认不是 UTF-8
    try:
        d = json.loads(raw) if raw.strip() else {}
    except ValueError:
        d = {}

    sid = d.get("conversation_id") or d.get("session_id") or "default"
    ev = {"source": src, "label": LABELS.get(src, src), "session": f"{src}:{sid}",
          "title": project_name(d)}

    if phase == "start":
        ev["state"] = "working"
        prompt = " ".join(str(d.get("prompt") or "").split())
        if prompt:
            ev["subtitle"] = prompt[:60]     # 只在本机显示，作为任务标题
    elif phase == "progress":
        ev["state"] = "working"
        tool = d.get("tool_name") or ("编辑文件" if d.get("file_path") else "") \
            or ("终端命令" if d.get("command") else "")
        if tool:
            ev["note"] = f"刚执行 {tool}"
    elif phase == "text":
        ev["state"] = "working"
        ev["tokens_add"] = est_tokens(str(d.get("text") or ""))
        ev["est"] = True
    elif phase == "waiting":
        msg = str(d.get("message") or "")
        # Claude Code 空闲 60 秒也会发 Notification，那种不算“等你确认”
        if "permission" not in msg.lower() and "权限" not in msg:
            ev = None
        else:
            ev["state"], ev["note"] = "waiting", msg[:80]
    elif phase == "stop":
        status = str(d.get("status") or "completed")
        ev["state"] = {"aborted": "stopped", "error": "error"}.get(status, "done")
        if src == "claude-code" and d.get("transcript_path"):
            ev.update(claude_code_usage(d["transcript_path"]))

    if ev:
        post(ev)

    # Cursor 期望 hook 输出 JSON；Claude Code 的 UserPromptSubmit 输出会进入上下文，所以保持安静
    if src == "cursor":
        print(json.dumps({"continue": True}) if phase == "start" else "{}")


if __name__ == "__main__":
    main()
