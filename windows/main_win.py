#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 活动 —— Windows 桌面小组件主程序。

窗口：pywebview（WebView2）无边框窗口，Windows 11 下自带系统圆角和阴影，加载本机接口提供的界面。
托盘：pystray，代替 macOS 的菜单栏图标。
数据：与 macOS 版共用 app/core.py、app/local_sources.py；网页状态来自浏览器扩展。
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
from PIL import Image, ImageDraw  # noqa: E402

from core import Store, make_server  # noqa: E402
from local_sources import WIN_APPS, LocalScanner, win_process_paths  # noqa: E402
from notify_win import toast  # noqa: E402

TITLE = "AI 活动"
WIDTH = 340
PORT = 47823
SUPPORT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "AIStatus")
CONFIG = os.path.join(SUPPORT, "config.json")
EXT_DIR = os.path.join(ROOT, "extension")
README_URL = "https://github.com/hfliyc-collab/ai-activity#windows"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "AIStatus"
APP_EXE = {"Cursor": "cursor", "Claude": "claude-app", "ChatGPT": "chatgpt-app"}


def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(SUPPORT, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def system_is_dark():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return True


def pythonw():
    d = os.path.dirname(sys.executable)
    w = os.path.join(d, "pythonw.exe")
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
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ,
                              f'"{pythonw()}" "{os.path.abspath(__file__)}"')
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def hide_from_taskbar(title):
    """把窗口设为工具窗口：不出现在任务栏和 Alt+Tab 里。"""
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
        ex = user32.GetWindowLongPtrW(hwnd, -20)
        ex = (ex | 0x80) & ~0x40000            # WS_EX_TOOLWINDOW，去掉 WS_EX_APPWINDOW
        user32.ShowWindow(hwnd, 0)
        user32.SetWindowLongPtrW(hwnd, -20, ex)
        user32.ShowWindow(hwnd, 8)              # SW_SHOWNA：显示但不抢焦点
    except Exception:
        pass


def open_app(name):
    rule = WIN_APPS.get(APP_EXE.get(name, ""))
    if not rule:
        return
    for p in win_process_paths():
        if rule(p):
            subprocess.Popen([p], creationflags=0x00000008)   # 已运行的应用会切到前台
            return


def tray_image():
    """托盘图标：四角星（与界面里的 ✦ 一致）。"""
    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r, w = s / 2, s * 0.46, s * 0.12
    pts = [(c, c - r), (c + w, c - w), (c + r, c), (c + w, c + w),
           (c, c + r), (c - w, c + w), (c - r, c), (c - w, c - w)]
    d.polygon(pts, fill=(163, 92, 255, 255))
    return img


class App:
    def __init__(self):
        self.cfg = load_config()
        self.store = Store(on_finish=self.on_finish)
        self.window = None
        self.icon = None
        self.height = 200
        self.max_h = 900
        self.visible = self.cfg.get("visible", True)
        self._save_timer = None

    # ---------------------------------------------------------------- 数据
    def on_action(self, a):
        kind = a.get("type")
        if kind == "height":
            self.set_height(a.get("h"))
        elif kind == "open":
            target = self.store.target_of(a.get("key", ""))
            if target and target[0] == "ext":
                self.store.queue_focus(target[1])
            elif target and target[0] == "app":
                open_app(target[1])

    def on_finish(self, row):
        if not self.cfg.get("sound", True):
            return
        state = {"done": "已完成", "error": "出错了", "stopped": "已停止"}.get(row["state"], "已结束")
        extra = []
        if row.get("tokens"):
            extra.append(f"{'≈' if row.get('est') else ''}{row['tokens']:,} tok")
        m, s = divmod(int(row.get("elapsed") or 0), 60)
        extra.append(f"用时 {m}:{s:02d}")
        body = (row.get("title") or row.get("place") or "") + "\n" + "，".join(extra)
        toast(f"{row['label']} {state}", body.strip())

    # ---------------------------------------------------------------- 窗口
    def set_height(self, h):
        try:
            h = max(90, min(int(h or 120), self.max_h))
        except (TypeError, ValueError):
            return
        if abs(h - self.height) < 2 or not self.window:
            return
        self.height = h
        self.window.resize(WIDTH, h)

    def on_moved(self, x, y):
        self.cfg["x"], self.cfg["y"] = x, y
        if self._save_timer:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(0.6, save_config, args=(self.cfg,))
        self._save_timer.start()

    def on_shown(self):
        time.sleep(0.3)
        if self.cfg.get("hide_taskbar", True):
            hide_from_taskbar(TITLE)
        if not self.visible:
            self.window.hide()

    def on_closed(self):
        if self.icon:
            self.icon.stop()

    # ---------------------------------------------------------------- 托盘
    def toggle_window(self):
        self.visible = not self.visible
        (self.window.show if self.visible else self.window.hide)()
        if self.visible and self.cfg.get("hide_taskbar", True):
            hide_from_taskbar(TITLE)
        self.cfg["visible"] = self.visible
        save_config(self.cfg)

    def toggle_top(self):
        self.cfg["on_top"] = not self.cfg.get("on_top", True)
        self.window.on_top = self.cfg["on_top"]
        save_config(self.cfg)

    def toggle_sound(self):
        self.cfg["sound"] = not self.cfg.get("sound", True)
        save_config(self.cfg)

    def toggle_startup(self):
        set_startup(not startup_enabled())

    def quit(self):
        if self.icon:
            self.icon.stop()
        self.window.destroy()

    def build_tray(self):
        I = pystray.MenuItem
        menu = pystray.Menu(
            I("显示小组件", lambda: self.toggle_window(), checked=lambda i: self.visible, default=True),
            I("始终置顶", lambda: self.toggle_top(), checked=lambda i: self.cfg.get("on_top", True)),
            I("完成时提醒", lambda: self.toggle_sound(), checked=lambda i: self.cfg.get("sound", True)),
            I("开机自动启动", lambda: self.toggle_startup(), checked=lambda i: startup_enabled()),
            pystray.Menu.SEPARATOR,
            I("打开浏览器扩展文件夹", lambda: os.startfile(EXT_DIR)),
            I("使用说明", lambda: webbrowser.open(README_URL)),
            pystray.Menu.SEPARATOR,
            I(f"退出 {TITLE}", lambda: self.quit()),
        )
        self.icon = pystray.Icon("AIStatusTray", tray_image(), TITLE, menu)
        self.icon.run_detached()

        def update_title():
            while True:
                time.sleep(2)
                try:
                    n = self.store.view()["summary"]["working"]
                    self.icon.title = f"{TITLE}：{n} 个进行中" if n else f"{TITLE}：空闲"
                except Exception:
                    pass
        threading.Thread(target=update_title, daemon=True).start()

    # ---------------------------------------------------------------- 启动
    def run(self):
        try:
            make_server(self.store, port=PORT, ui_dir=os.path.join(ROOT, "app", "ui"),
                        on_action=self.on_action)
        except OSError:
            ctypes.windll.user32.MessageBoxW(None, "AI 活动已经在运行，请在任务栏右下角的托盘区找到 ✦ 图标。",
                                             TITLE, 0x40)
            return
        self.store.start_ticker()
        LocalScanner(self.store).start()

        try:
            s0 = webview.screens[0]
            sw, sh, sx, sy = s0.width, s0.height, s0.x, s0.y
        except Exception:
            sw, sh, sx, sy = 1920, 1080, 0, 0
        self.max_h = sh - 100
        x = self.cfg.get("x", sx + sw - WIDTH - 24)
        y = self.cfg.get("y", sy + 24)
        dark = system_is_dark()
        self.window = webview.create_window(
            TITLE, f"http://127.0.0.1:{PORT}/?platform=win",
            width=WIDTH, height=self.height, x=x, y=y, resizable=False,
            frameless=True, easy_drag=False, shadow=True,
            on_top=self.cfg.get("on_top", True),
            background_color="#202020" if dark else "#F3F3F3",
        )
        self.window.events.moved += self.on_moved
        self.window.events.shown += self.on_shown
        self.window.events.closed += self.on_closed
        self.build_tray()
        webview.start()
        os._exit(0)


if __name__ == "__main__":
    App().run()
