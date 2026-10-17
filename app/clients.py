# -*- coding: utf-8 -*-
"""桌面客户端监测（Kimi、豆包、元宝、通义、智谱清言、文小言、DeepSeek、ChatGPT、Claude 等）。

浏览器里的方法读不到独立应用，所以这里改用系统无障碍接口：
  macOS    辅助功能（Accessibility），需要在 系统设置 › 隐私与安全性 › 辅助功能 里允许一次
  Windows  UI Automation，无需额外授权

读取方式：从窗口底部（最新回复、输入框、停止按钮所在处）开始反向遍历，收集最近的一段文字
和按钮名称；看到“停止生成”一类按钮，或最近文字持续增长，就判定为正在生成。
只在本机读取，不保存、不发送任何文字内容，只把长度交给状态机。
"""
import sys
import threading
import time

from sites import CLIENTS, STOP_WORDS, client_for_name

TAIL_TEXTS = 80          # 收集最近这么多段文字
NODE_CAP = 1500          # 每个窗口最多访问的节点数
BUDGET = 0.7             # 每个窗口最多花费的秒数
CJK = range(0x3000, 0xA000)
_STOP = {w.lower() for w in STOP_WORDS}


def is_stop_label(text):
    t = (text or "").strip().lower()
    for sep in ("(", "（", "⌘", "esc"):
        if sep in t:
            t = t.split(sep)[0].strip()
    return t in _STOP


def summarize(nodes):
    """nodes: 可迭代的 {"role","title","desc","value"}（已按“从底部开始”的顺序）。"""
    busy, texts = False, []
    for nd in nodes:
        role = nd.get("role", "")
        if role in ("AXButton", "ButtonControl", "AXMenuButton", "SplitButtonControl"):
            if is_stop_label(nd.get("title")) or is_stop_label(nd.get("desc")):
                busy = True
        elif role in ("AXStaticText", "TextControl") and len(texts) < TAIL_TEXTS:
            v = nd.get("value") or nd.get("title") or ""
            if v:
                texts.append(v)
    n = sum(len(t) for t in texts)
    cjk = sum(1 for t in texts for ch in t if ord(ch) in CJK)
    return {"busy": busy, "n": n, "count": len(texts), "est": cjk + (n - cjk + 3) // 4}


INPUT_ROLES = {"AXTextArea", "AXTextField", "AXComboBox", "EditControl"}


# ---------------------------------------------------------------- macOS
def mac_trusted(prompt=False):
    try:
        import ApplicationServices as AS
        return bool(AS.AXIsProcessTrustedWithOptions({AS.kAXTrustedCheckOptionPrompt: bool(prompt)}))
    except Exception:
        return False


def mac_running():
    from AppKit import NSWorkspace
    out = []
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        try:
            if app.activationPolicy() != 0:          # 只看普通应用，跳过辅助进程
                continue
            name = str(app.localizedName() or "")
            bid = str(app.bundleIdentifier() or "")
            c = client_for_name(name) or client_for_name(bid)
            if c:
                out.append((c, int(app.processIdentifier()), name))
        except Exception:
            continue
    return out


def _mac_nodes(pid):
    import ApplicationServices as AS
    app = AS.AXUIElementCreateApplication(pid)
    AS.AXUIElementSetAttributeValue(app, "AXManualAccessibility", True)   # Electron 应用需要这一步
    err, wins = AS.AXUIElementCopyAttributeValue(app, "AXWindows", None)
    if err != 0 or not wins:
        return None, ""
    title = ""
    err, t = AS.AXUIElementCopyAttributeValue(wins[0], "AXTitle", None)
    if err == 0 and isinstance(t, str):
        title = t
    attrs = ["AXRole", "AXTitle", "AXDescription", "AXValue", "AXChildren"]
    stack, nodes, t0, texts = [wins[0]], [], time.time(), 0
    while stack and len(nodes) < NODE_CAP and time.time() - t0 < BUDGET and texts < TAIL_TEXTS:
        el = stack.pop()
        err, vals = AS.AXUIElementCopyMultipleAttributeValues(el, attrs, 0, None)
        if err != 0 or vals is None:
            continue
        vals = list(vals) + [None] * 5
        nd = {"role": vals[0] if isinstance(vals[0], str) else "",
              "title": vals[1] if isinstance(vals[1], str) else "",
              "desc": vals[2] if isinstance(vals[2], str) else "",
              "value": vals[3] if isinstance(vals[3], str) else ""}
        nodes.append(nd)
        if nd["role"] == "AXStaticText" and nd["value"]:
            texts += 1
        if nd["role"] in INPUT_ROLES:
            continue
        kids = vals[4]
        if kids is not None and not isinstance(kids, str):
            try:
                stack.extend(list(kids))                 # 后入先出：先访问最后一个子节点（窗口底部）
            except TypeError:
                pass
    return nodes, title


def mac_activate(pid):
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(int(pid))
        if app:
            app.activateWithOptions_(1 << 1)             # NSApplicationActivateIgnoringOtherApps
    except Exception:
        pass


# ---------------------------------------------------------------- Windows
def win_running():
    from local_sources import win_processes
    out, seen = [], set()
    for pid, path in win_processes():
        base = path.rsplit("\\", 1)[-1]
        if not base.endswith(".exe"):
            continue
        c = client_for_name(base[:-4])
        if not c:
            continue
        if c["id"] == "claude-app" and "anthropicclaude" not in path:
            continue                                     # 命令行版 Claude Code 不是桌面客户端
        out.append((c, pid, base))
        seen.add(pid)
    return out


def win_windows(pids):
    """返回 {pid: (hwnd, title)}：每个进程面积最大的可见顶层窗口。"""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = {}
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in pids:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        area = (r.right - r.left) * (r.bottom - r.top)
        if area > 0 and (pid.value not in found or area > found[pid.value][2]):
            found[pid.value] = (hwnd, buf.value, area)
        return True
    user32.EnumWindows(proc(cb), 0)
    return {k: (v[0], v[1]) for k, v in found.items()}


def _win_nodes(hwnd):
    import uiautomation as auto
    root = auto.ControlFromHandle(hwnd)
    if not root:
        return None
    stack, nodes, t0, texts = [root], [], time.time(), 0
    while stack and len(nodes) < NODE_CAP and time.time() - t0 < BUDGET and texts < TAIL_TEXTS:
        ctl = stack.pop()
        try:
            role, name = ctl.ControlTypeName, ctl.Name or ""
        except Exception:
            continue
        nodes.append({"role": role, "title": name, "desc": "", "value": name if role == "TextControl" else ""})
        if role == "TextControl" and name:
            texts += 1
        if role in INPUT_ROLES:
            continue
        try:
            stack.extend(ctl.GetChildren())
        except Exception:
            pass
    return nodes


def win_activate(pid):
    try:
        import ctypes
        w = win_windows({int(pid)}).get(int(pid))
        if w:
            ctypes.windll.user32.ShowWindow(w[0], 9)      # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(w[0])
    except Exception:
        pass


# ---------------------------------------------------------------- 扫描线程
class ClientScanner(threading.Thread):
    """enabled() 返回是否开启客户端监测；关闭时只识别“已打开”，不读取界面。"""

    def __init__(self, store, enabled=lambda: True, interval=None):
        super().__init__(daemon=True)
        self.store, self.enabled = store, enabled
        self.win = sys.platform == "win32"
        self.interval = interval or (3.0 if self.win else 2.0)

    def run(self):
        if self.win:
            try:
                import uiautomation as auto
                with auto.UIAutomationInitializerInThread(debug=False):
                    self._loop()
                return
            except ImportError:
                pass
        self._loop()

    def _loop(self):
        while True:
            t0 = time.time()
            try:
                self.scan()
            except Exception as e:  # noqa: BLE001
                self.store.set_notice("_clients", "error", str(e)[:200])
            time.sleep(max(0.5, self.interval - (time.time() - t0)))

    def scan(self):
        running = win_running() if self.win else mac_running()
        on = self.enabled()
        items = []
        if self.win:
            hw = win_windows({pid for _, pid, _ in running}) if running else {}
            for c, pid, name in running:
                if pid not in hw:
                    continue                             # 没有窗口的辅助进程
                hwnd, title = hw[pid]
                probe = None
                if on:
                    try:
                        nodes = _win_nodes(hwnd)
                        probe = summarize(nodes) if nodes else None
                    except Exception:
                        probe = None
                items.append({"cid": c["id"], "pid": pid, "title": title, "probe": probe})
        else:
            trusted = mac_trusted(False)
            if running and on and not trusted:
                self.store.set_notice("accessibility", "ax")
            else:
                self.store.clear_notice("accessibility")
            for c, pid, name in running[:8]:
                probe, title = None, ""
                if on and trusted:
                    try:
                        nodes, title = _mac_nodes(pid)
                        probe = summarize(nodes) if nodes else None
                    except Exception:
                        probe = None
                items.append({"cid": c["id"], "pid": pid, "title": title, "probe": probe})
        self.store.on_clients(items)
