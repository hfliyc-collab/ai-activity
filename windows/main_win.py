#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 活动 —— Windows 主程序。

显示方式（设置里切换；托盘图标始终保留，作为控制和“专注后恢复”的入口）：
  侧边栏  无边框窗口，同时排列已选账号和任务，可拖到任意显示器
  托盘    托盘图标直接显示主账号额度，点击弹出一个账号的详情
"""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, HERE)

import webview  # noqa: E402
import pystray  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from clients import ClientScanner, win_activate  # noqa: E402
from core import Store, make_server  # noqa: E402
from local_sources import WIN_APPS, LocalScanner, win_process_paths  # noqa: E402
from notify_win import toast  # noqa: E402
from quota import QuotaPoller, secret_get, secret_set  # noqa: E402

TITLE = "AI 活动"
POP_TITLE = "AI 活动 · 额度"
WIDTH = 340
PORT = 47823
BASE = f"http://127.0.0.1:{PORT}"
SUPPORT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "AIStatus")
CONFIG = os.path.join(SUPPORT, "config.json")
EXT_DIR = os.path.join(ROOT, "extension")
README_URL = "https://github.com/hfliyc-collab/ai-activity#windows"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "AIStatus"
FOCUS_CHOICES = [(15, "15 分钟"), (60, "1 小时"), (180, "3 小时"), (300, "5 小时")]
MODES = [("sidebar", "侧边栏"), ("tray", "托盘")]


def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(SUPPORT, exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG)


def system_is_dark():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return True


def pythonw():
    w = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return w if os.path.exists(w) else sys.executable


def startup_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_startup(on):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, f'"{pythonw()}" "{os.path.abspath(__file__)}"')
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def work_area():
    """主显示器的可用区域（去掉任务栏），逻辑像素。"""
    try:
        from ctypes import wintypes
        r = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        return r.left / scale, r.top / scale, r.right / scale, r.bottom / scale
    except Exception:
        return 0, 0, 1920, 1040


def virtual_screen():
    try:
        u = ctypes.windll.user32
        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        return (u.GetSystemMetrics(76) / scale, u.GetSystemMetrics(77) / scale,
                u.GetSystemMetrics(78) / scale, u.GetSystemMetrics(79) / scale)
    except Exception:
        return 0, 0, 1920, 1080


def hide_from_taskbar(title):
    try:
        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = ctypes.c_void_p
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        ex = (user32.GetWindowLongPtrW(hwnd, -20) | 0x80) & ~0x40000
        user32.ShowWindow(hwnd, 0)
        user32.SetWindowLongPtrW(hwnd, -20, ex)
        user32.ShowWindow(hwnd, 8)
    except Exception:
        pass


def open_app(name):
    rule = WIN_APPS.get({"Cursor": "cursor"}.get(name, ""))
    if rule:
        for p in win_process_paths():
            if rule(p):
                subprocess.Popen([p], creationflags=0x00000008)
                return


# ---------------------------------------------------------------- 托盘图标
def _font(size):
    for f in ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "msyhbd.ttc", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def tray_image(text=None, level="ok", moon=False):
    """托盘图标：有主账号时直接画出额度数字，否则画四角星；专注时画月亮。"""
    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if moon:
        d.ellipse((8, 8, 56, 56), fill=(255, 196, 70, 255))
        d.ellipse((22, 2, 66, 46), fill=(0, 0, 0, 0))
        return img
    if text:
        bg = {"ok": (10, 132, 255, 255), "mid": (255, 159, 10, 255), "high": (255, 69, 58, 255)}.get(level, (10, 132, 255, 255))
        d.rounded_rectangle((2, 2, 62, 62), radius=16, fill=bg)
        t = text[:3]
        f = _font(40 if len(t) <= 2 else 30)
        box = d.textbbox((0, 0), t, font=f)
        d.text(((s - (box[2] - box[0])) / 2 - box[0], (s - (box[3] - box[1])) / 2 - box[1]), t, font=f, fill=(255, 255, 255, 255))
        return img
    c, r, w = s / 2, s * 0.46, s * 0.12
    d.polygon([(c, c - r), (c + w, c - w), (c + r, c), (c + w, c + w), (c, c + r), (c - w, c + w), (c - r, c), (c - w, c - w)],
              fill=(163, 92, 255, 255))
    return img


class App:
    def __init__(self):
        self.cfg = load_config()
        self.cfg.setdefault("mode", "sidebar")
        self.cfg.setdefault("clients_on", True)
        self.store = Store(on_finish=self.on_finish)
        self.store.set_prefs(self.cfg.get("prefs", {}))
        self.secrets = {n: bool(secret_get(n, SUPPORT)) for n in ("deepseek", "moonshot")}
        self.main = self.pop = self.settings = None
        self.icon = None
        self.heights = {"sidebar": 200, "popover": 360}
        self._save_timer = None
        self._icon_key = None

    def focused(self):
        return time.time() < self.cfg.get("focus_until", 0)

    def set_cfg(self, **kw):
        self.cfg.update(kw)
        save_config(self.cfg)

    def ui_state(self):
        return {"mode": self.cfg.get("mode"), "platform": "win", "modes_available": [m for m, _ in MODES],
                "companion": self.cfg.get("companion", False), "clients_on": self.cfg.get("clients_on", True),
                "quota_claude_code": self.cfg.get("quota_claude_code", False), "sound": self.cfg.get("sound", True),
                "focus_until": self.cfg.get("focus_until", 0) if self.focused() else 0,
                "secrets": self.secrets, "ax_trusted": True}

    # ---------------------------------------------------------------- 消息
    def on_action(self, a):
        kind, view = a.get("type"), a.get("view")
        if kind == "height":
            h = max(90, min(int(a.get("h") or 120), 900))
            self.heights[view] = h
            if view == "sidebar" and self.main:
                self.main.resize(WIDTH, h)
            elif view == "popover" and self.pop and self.pop_visible:
                self.place_popup()
        elif kind == "open":
            t = self.store.target_of(a.get("key", ""))
            if t and t[0] == "ext":
                self.store.queue_focus(t[1])
            elif t and t[0] == "client":
                win_activate(t[2])
            elif t and t[0] == "app":
                open_app(t[1])
            if view == "popover":
                self.hide_popup()
        elif kind == "blur" and view == "popover":
            self.hide_popup()
        elif kind == "settings":
            patch = dict(a.get("patch") or {})
            prefs = {k: patch.pop(k) for k in ("order", "hidden", "primary", "popover_account") if k in patch}
            if prefs:
                self.cfg.setdefault("prefs", {}).update(prefs)
                self.store.set_prefs(self.cfg["prefs"])
            allowed = {"mode", "companion", "clients_on", "quota_claude_code", "sound"}
            self.set_cfg(**{k: v for k, v in patch.items() if k in allowed})
            if "mode" in patch:
                self.apply_mode()
            if "quota_claude_code" in patch:
                self.quota.refresh_now()
            self.refresh_tray()
        elif kind == "secret" and a.get("name") in ("deepseek", "moonshot"):
            secret_set(a["name"], (a.get("value") or "").strip(), SUPPORT)
            self.secrets[a["name"]] = bool(secret_get(a["name"], SUPPORT))
            self.quota.refresh_now()
        elif kind == "focus":
            self.focus(a.get("minutes") or 60)
        elif kind == "unfocus":
            self.unfocus()
        elif kind == "settings-open":
            self.hide_popup()
            self.open_settings()

    def on_finish(self, row):
        if not self.cfg.get("sound", True) or self.focused():
            return
        state = {"done": "已完成", "error": "出错了", "stopped": "已停止"}.get(row["state"], "已结束")
        extra = [f"{'≈' if row.get('est') else ''}{row['tokens']:,} tok"] if row.get("tokens") else []
        m, s = divmod(int(row.get("elapsed") or 0), 60)
        extra.append(f"用时 {m}:{s:02d}")
        toast(f"{row['label']} {state}", ((row.get("title") or row.get("place") or "") + "\n" + "，".join(extra)).strip())

    # ---------------------------------------------------------------- 窗口
    pop_visible = False

    def place_popup(self):
        l, t, r, b = work_area()
        h = self.heights.get("popover", 360)
        try:
            self.pop.resize(WIDTH, h)
            self.pop.move(int(r - WIDTH - 12), int(b - h - 12))
        except Exception:
            pass

    def show_popup(self):
        if not self.pop or self.focused():
            return
        self.place_popup()
        self.pop.show()
        self.pop_visible = True
        hide_from_taskbar(POP_TITLE)

    def hide_popup(self):
        if self.pop and self.pop_visible:
            self.pop.hide()
            self.pop_visible = False

    def toggle_popup(self):
        self.hide_popup() if self.pop_visible else self.show_popup()

    def apply_mode(self):
        hide = self.focused()
        if self.main:
            if hide or self.cfg.get("mode") != "sidebar":
                self.main.hide()
            else:
                self.main.show()
                hide_from_taskbar(TITLE)
        if hide or self.cfg.get("mode") != "tray":
            self.hide_popup()
        self.refresh_tray()

    def focus(self, minutes):
        self.set_cfg(focus_until=time.time() + int(minutes) * 60)
        self.apply_mode()

    def unfocus(self):
        self.set_cfg(focus_until=0)
        self.apply_mode()

    def open_settings(self):
        if self.settings:
            try:
                self.settings.show()
                self.settings.restore()
                return
            except Exception:
                self.settings = None
        self.settings = webview.create_window(f"{TITLE} · 设置", f"{BASE}/ui/settings.html?platform=win",
                                              width=640, height=800, background_color="#202020" if system_is_dark() else "#F5F5F7")

        def closed():
            self.settings = None
        self.settings.events.closed += closed

    def on_moved(self, x, y):
        self.cfg["x"], self.cfg["y"] = x, y
        if self._save_timer:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(0.6, save_config, args=(self.cfg,))
        self._save_timer.start()

    # ---------------------------------------------------------------- 托盘
    def refresh_tray(self):
        if not self.icon:
            return
        try:
            self.store.ui = self.ui_state()
            v = self.store.view()
            n, p = v["summary"]["working"], v.get("primary")
            if self.focused():
                key = ("moon",)
                left = int((self.cfg["focus_until"] - time.time()) / 60) + 1
                tip = f"{TITLE}：专注中，还剩 {left} 分钟"
            elif self.cfg.get("mode") == "tray" and p and p.get("headline", "—") != "—":
                num = p["headline"].rstrip("%").lstrip("¥$")
                key = ("num", num.split(".")[0], p.get("level", "ok"))
                tip = f"{TITLE}：{p['name']} {p['headline_label']} {p['headline']}" + (f"，{n} 个进行中" if n else "")
            else:
                key = ("star",)
                tip = f"{TITLE}：{n} 个进行中" if n else f"{TITLE}：空闲"
            if key != self._icon_key:
                self._icon_key = key
                self.icon.icon = tray_image(moon=True) if key[0] == "moon" else tray_image(key[1], key[2]) if key[0] == "num" else tray_image()
            self.icon.title = tip[:120]
            order = self.store.prefs.get("order", [])
            if order != self.cfg.get("prefs", {}).get("order"):
                self.cfg.setdefault("prefs", {})["order"] = list(order)
                save_config(self.cfg)
            self.icon.update_menu()
        except Exception:
            pass

    def build_tray(self):
        I, M = pystray.MenuItem, pystray.Menu

        def focus_item(mins, label):
            return I(label, lambda: self.focus(mins))

        def left_text(_):
            return f"专注中，还剩 {int((self.cfg.get('focus_until', 0) - time.time()) / 60) + 1} 分钟"

        def mode_item(mode, label):
            return I(label, lambda: (self.set_cfg(mode=mode), self.apply_mode()),
                     checked=lambda i: self.cfg.get("mode") == mode, radio=True)

        menu = M(
            I("弹出", lambda: self.on_tray_click(), default=True, visible=False),   # 托盘左键
            I(left_text, lambda: None, enabled=False, visible=lambda i: self.focused()),
            I("立即显示", lambda: self.unfocus(), visible=lambda i: self.focused()),
            I("专注一会儿（临时隐藏）", M(*[focus_item(m, l) for m, l in FOCUS_CHOICES]), visible=lambda i: not self.focused()),
            M.SEPARATOR,
            I("显示方式", M(*[mode_item(m, l) for m, l in MODES])),
            I("设置…", lambda: self.open_settings()),
            M.SEPARATOR,
            I("始终置顶", lambda: self.toggle_top(), checked=lambda i: self.cfg.get("on_top", True)),
            I("完成时提醒", lambda: self.set_cfg(sound=not self.cfg.get("sound", True)), checked=lambda i: self.cfg.get("sound", True)),
            I("开机自动启动", lambda: set_startup(not startup_enabled()), checked=lambda i: startup_enabled()),
            M.SEPARATOR,
            I("打开浏览器扩展文件夹", lambda: os.startfile(EXT_DIR)),
            I("使用说明", lambda: webbrowser.open(README_URL)),
            I(f"退出 {TITLE}", lambda: self.quit()),
        )
        self.icon = pystray.Icon("AIStatusTray", tray_image(), TITLE, menu)
        self.icon.run_detached()

        def loop():
            while True:
                time.sleep(2)
                if self.cfg.get("focus_until") and not self.focused():
                    self.unfocus()
                self.refresh_tray()
        threading.Thread(target=loop, daemon=True).start()

    def on_tray_click(self):
        if self.focused():
            return
        if self.cfg.get("mode") == "tray":
            self.toggle_popup()
        elif self.main:
            self.main.show()

    def toggle_top(self):
        self.set_cfg(on_top=not self.cfg.get("on_top", True))
        if self.main:
            self.main.on_top = self.cfg["on_top"]

    def quit(self):
        if self.icon:
            self.icon.stop()
        for w in (self.settings, self.pop, self.main):
            try:
                w and w.destroy()
            except Exception:
                pass

    # ---------------------------------------------------------------- 启动
    def run(self):
        try:
            make_server(self.store, port=PORT, ui_dir=os.path.join(ROOT, "app", "ui"), on_action=self.on_action)
        except OSError:
            ctypes.windll.user32.MessageBoxW(None, "AI 活动已经在运行，请在任务栏右下角找到它的托盘图标。", TITLE, 0x40)
            return
        self.store.ui = self.ui_state()
        self.store.start_ticker()
        LocalScanner(self.store).start()
        ClientScanner(self.store, enabled=lambda: self.cfg.get("clients_on", True)).start()
        self.quota = QuotaPoller(self.store, lambda: self.cfg, SUPPORT)
        self.quota.start()

        vx, vy, vw, vh = virtual_screen()
        l, t, r, b = work_area()
        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or not (vx <= x <= vx + vw - 60 and vy <= y <= vy + vh - 60):
            x, y = int(r - WIDTH - 24), int(t + 24)
        bg = "#202020" if system_is_dark() else "#F3F3F3"
        self.main = webview.create_window(TITLE, f"{BASE}/?view=sidebar&platform=win", width=WIDTH, height=200, x=x, y=y,
                                          resizable=False, frameless=True, easy_drag=False, shadow=True,
                                          on_top=self.cfg.get("on_top", True), background_color=bg,
                                          hidden=self.focused() or self.cfg.get("mode") != "sidebar")
        self.pop = webview.create_window(POP_TITLE, f"{BASE}/?view=popover&platform=win", width=WIDTH, height=360,
                                         resizable=False, frameless=True, easy_drag=False, shadow=True, on_top=True,
                                         background_color=bg, hidden=True)
        self.main.events.moved += self.on_moved
        self.main.events.shown += lambda: (time.sleep(0.3), hide_from_taskbar(TITLE))
        self.main.events.closed += lambda: self.icon and self.icon.stop()
        self.build_tray()
        webview.start()
        os._exit(0)


if __name__ == "__main__":
    App().run()
