# -*- coding: utf-8 -*-
"""本地来源：
  - Claude Code：直接读 ~/.claude/projects 下的会话记录，即使没装 hooks 也能看到状态和真实 token
  - 进程识别：Cursor、Claude / ChatGPT 桌面版、Claude Code 命令行是否在运行
"""
import glob
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

IS_WIN = sys.platform == "win32"

from sites import APPS

CC_ROOT = os.path.expanduser("~/.claude/projects")
LOOKBACK = 30 * 60       # 只看 30 分钟内有更新的会话
TAIL_BYTES = 512 * 1024


def _ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _is_prompt(e):
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "text" for x in c) \
        and not any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c)


def _prompt_text(e):
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")


def read_tail_entries(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > TAIL_BYTES:
            f.seek(size - TAIL_BYTES)
        raw = f.read().decode("utf-8", "replace")
    lines = raw.splitlines()
    if size > TAIL_BYTES and lines:
        lines = lines[1:]
    out = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") in ("user", "assistant") and not e.get("isSidechain") and not e.get("isMeta"):
            out.append(e)
    return out


def analyze_claude_code(entries, mtime, now):
    """根据会话记录推断当前状态。返回事件 dict（不含 session）。"""
    if not entries:
        return None
    start = 0
    for i, e in enumerate(entries):
        if e.get("type") == "user" and _is_prompt(e) and "[Request interrupted" not in _prompt_text(e):
            start = i
    prompt = entries[start] if entries[start].get("type") == "user" else None

    per_msg, model, cwd = {}, "", ""
    for i, e in enumerate(entries[start:]):
        cwd = e.get("cwd") or cwd
        m = e.get("message") or {}
        if e.get("type") == "assistant" and isinstance(m.get("usage"), dict):
            per_msg[m.get("id") or i] = m["usage"]
            model = m.get("model") or model
    out = sum(int(u.get("output_tokens") or 0) for u in per_msg.values())
    ctx = 0
    if per_msg:
        last_u = list(per_msg.values())[-1]
        ctx = sum(int(last_u.get(k) or 0) for k in
                  ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))

    last = entries[-1]
    age = now - mtime
    note, state = "", "working"
    if last.get("type") == "user":
        state = "stopped" if "[Request interrupted" in _prompt_text(last) else "working"
    else:
        m = last.get("message") or {}
        blocks = [b for b in (m.get("content") or []) if isinstance(b, dict)]
        kinds = {b.get("type") for b in blocks}
        if last.get("isApiErrorMessage"):
            state = "error"
        elif "tool_use" in kinds:
            tool = next(b.get("name") for b in blocks if b.get("type") == "tool_use")
            note = f"正在执行 {tool}"
        elif "text" in kinds and (m.get("stop_reason") in ("end_turn", "stop_sequence", "max_tokens")
                                  or age > 15):
            state = "done"
    if state == "working" and age > 10 * 60:
        state, note = "stopped", "长时间没有活动"

    ev = {"state": state, "note": note, "model": model, "est": False,
          "title": os.path.basename(cwd.rstrip("/")) if cwd else "",
          "subtitle": " ".join(_prompt_text(prompt).split())[:60] if prompt else ""}
    if per_msg:
        ev["tokens_out"], ev["tokens_in"] = out, ctx
    st = _ts(prompt.get("timestamp")) if prompt else None
    if st:
        ev["started_at"] = st * 1000
    if state in ("done", "error", "stopped"):
        ev["finished_at"] = mtime
    return ev


class LocalScanner(threading.Thread):
    def __init__(self, store):
        super().__init__(daemon=True)
        self.store = store
        self.last_sig = {}

    def run(self):
        while True:
            try:
                self.scan_claude_code()
                self.scan_processes()
            except Exception as e:
                self.store.set_notice("_local", "error", str(e)[:200])
            time.sleep(1.5)

    def scan_claude_code(self):
        now = time.time()
        for path in glob.glob(os.path.join(CC_ROOT, "*", "*.jsonl")):
            name = os.path.basename(path)
            if name.startswith("agent-"):
                continue
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if now - mtime > LOOKBACK:
                continue
            key = "claude-code:" + name[:-6]
            cached = self.last_sig.get(key)          # (mtime, state, tokens, note)
            # 文件没变、上次也不是“进行中”（不会因时间推移而变化）时跳过
            if cached and cached[0] == mtime and cached[1] != "working":
                continue
            try:
                ev = analyze_claude_code(read_tail_entries(path), mtime, now)
            except OSError:
                continue
            if not ev:
                continue
            sig = (mtime, ev["state"], ev.get("tokens_out"), ev.get("note"))
            self.last_sig[key] = sig
            if cached and cached[1:] == sig[1:]:
                continue
            ev.update(session=key, source="claude-code")
            self.store.apply_agent_event(ev, origin="scanner")

    def scan_processes(self):
        if IS_WIN:
            paths = win_process_paths()
            running = {k for k, rule in WIN_APPS.items() if any(rule(p) for p in paths)}
            names = {os.path.basename(p) for p in paths}
            self.store.set_running_apps(running)
            self.store.set_running_browsers({v for k, v in WIN_BROWSERS.items() if k in names})
            return
        try:
            out = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True,
                                 timeout=5).stdout.splitlines()
        except Exception:
            return
        running = set()
        for a in APPS:
            if a.get("match") and any(a["match"] in line for line in out):
                running.add(a["id"])
            if a.get("match_comm") and any(os.path.basename(line.strip()) == a["match_comm"]
                                           for line in out):
                running.add(a["id"])
        self.store.set_running_apps(running)


# ---------------------------------------------------------------- Windows 进程识别
WIN_APPS = {
    "cursor": lambda p: p.endswith("\\cursor.exe"),
    "claude-app": lambda p: p.endswith("\\claude.exe") and "anthropicclaude" in p,
    "chatgpt-app": lambda p: p.endswith("\\chatgpt.exe"),
    "claude-code": lambda p: p.endswith("\\claude.exe") and "anthropicclaude" not in p,
}
WIN_BROWSERS = {"chrome.exe": "Chrome", "msedge.exe": "Edge", "brave.exe": "Brave"}


def win_process_paths():
    """列出所有进程的可执行文件完整路径（小写）。只用 ctypes，不需要额外安装。"""
    import ctypes
    from ctypes import wintypes
    psapi = ctypes.WinDLL("psapi")
    k32 = ctypes.WinDLL("kernel32")
    psapi.EnumProcesses.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
                                    ctypes.POINTER(wintypes.DWORD)]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                               ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    pids = (wintypes.DWORD * 8192)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(needed)):
        return []
    out, buf = [], ctypes.create_unicode_buffer(1024)
    for pid in pids[: needed.value // ctypes.sizeof(wintypes.DWORD)]:
        if not pid:
            continue
        h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            continue
        try:
            size = wintypes.DWORD(len(buf))
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                out.append(buf.value.lower())
        finally:
            k32.CloseHandle(h)
    return out
