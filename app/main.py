#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 活动 —— macOS 桌面小组件主程序。

原生部分（PyObjC）：毛玻璃圆角面板 + 透明 WKWebView 显示界面 + 菜单栏图标。
数据部分：core.Store 汇总 浏览器轮询 / Chrome 扩展 / hooks / Claude Code 本地记录。
"""
import json
import os
import plistlib
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import objc  # noqa: E402
from AppKit import (NSApplication, NSBezierPath, NSColor, NSImage, NSMenu,  # noqa: E402
                    NSMenuItem, NSPanel, NSScreen, NSSound, NSStatusBar, NSView,
                    NSVisualEffectView, NSAppearance, NSAlert)
from Foundation import NSMakeRect, NSMakeSize, NSObject, NSRunLoop, NSTimer, NSURL  # noqa: E402
from PyObjCTools import AppHelper  # noqa: E402
from WebKit import WKUserContentController, WKWebView, WKWebViewConfiguration  # noqa: E402

try:
    from Quartz import CGWindowLevelForKey, kCGDesktopIconWindowLevelKey
    DESKTOP_LEVEL = CGWindowLevelForKey(kCGDesktopIconWindowLevelKey) + 1
except Exception:
    DESKTOP_LEVEL = None

from browsers import BrowserPoller, focus_tab, open_app  # noqa: E402
from core import Store, make_server  # noqa: E402
from local_sources import LocalScanner  # noqa: E402

APP_NAME = "AI 活动"
WIDTH, HEADER_H, RADIUS = 340, 58, 22
FLOATING_LEVEL = 3
STYLE_BORDERLESS, STYLE_NONACTIVATING = 0, 1 << 7
BEHAVIOR = (1 << 0) | (1 << 4) | (1 << 6)   # 所有桌面空间可见 | 固定 | 不参与窗口切换
MATERIAL_POPOVER = 6
SUPPORT = os.path.expanduser("~/Library/Application Support/AIStatus")
CONFIG = os.path.join(SUPPORT, "config.json")
AGENT_PLIST = os.path.expanduser("~/Library/LaunchAgents/com.aistatus.widget.plist")
README = os.path.join(os.path.dirname(HERE), "README.md")


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


def round_mask(view, r):
    """给毛玻璃视图加圆角（官方推荐的 maskImage 方式，阴影也会跟着变圆）。"""
    try:
        def draw(rect):
            NSColor.blackColor().set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, r, r).fill()
            return True
        img = NSImage.imageWithSize_flipped_drawingHandler_(NSMakeSize(2 * r + 1, 2 * r + 1), False, draw)
        img.setCapInsets_((r, r, r, r))
        img.setResizingMode_(1)       # 拉伸
        view.setMaskImage_(img)
    except Exception:
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(r)
        view.layer().setMasksToBounds_(True)


class Panel(NSPanel):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


class DragStrip(NSView):
    """覆盖在标题区域上的透明视图，负责拖动窗口。"""

    def mouseDown_(self, event):
        self.window().performWindowDragWithEvent_(event)

    def acceptsFirstMouse_(self, event):
        return True


WKScriptMessageHandler = objc.protocolNamed("WKScriptMessageHandler")


class Bridge(NSObject, protocols=[WKScriptMessageHandler]):
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        try:
            msg = json.loads(str(message.body()))
        except Exception:
            return
        self.ctrl.handle(msg)


class Controller(NSObject):
    def init(self):
        self = objc.super(Controller, self).init()
        if self is None:
            return None
        self.cfg = load_config()
        self.store = None
        self.items = {}
        return self

    # ------------------------------------------------------------ 窗口
    @objc.python_method
    def build(self):
        vf = NSScreen.mainScreen().visibleFrame()
        h = 200
        x = self.cfg.get("x", vf.origin.x + vf.size.width - WIDTH - 18)
        top = self.cfg.get("top", vf.origin.y + vf.size.height - 14)
        panel = Panel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, top - h, WIDTH, h), STYLE_BORDERLESS | STYLE_NONACTIVATING, 2, False)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setReleasedWhenClosed_(False)
        panel.setCollectionBehavior_(BEHAVIOR)
        panel.setDelegate_(self)

        effect = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDTH, h))
        effect.setMaterial_(MATERIAL_POPOVER)
        effect.setBlendingMode_(0)          # 透出窗口后面的桌面
        effect.setState_(1)                 # 始终保持毛玻璃
        effect.setAutoresizingMask_(2 | 16)
        round_mask(effect, RADIUS)
        panel.setContentView_(effect)

        ucc = WKUserContentController.alloc().init()
        self.bridge = Bridge.alloc().init()
        self.bridge.ctrl = self
        ucc.addScriptMessageHandler_name_(self.bridge, "aiw")
        conf = WKWebViewConfiguration.alloc().init()
        conf.setUserContentController_(ucc)
        web = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, WIDTH, h), conf)
        web.setValue_forKey_(False, "drawsBackground")
        try:
            web.setUnderPageBackgroundColor_(NSColor.clearColor())
        except Exception:
            pass
        web.setAutoresizingMask_(2 | 16)
        web.setWantsLayer_(True)
        web.layer().setCornerRadius_(RADIUS)
        web.layer().setMasksToBounds_(True)
        effect.addSubview_(web)

        strip = DragStrip.alloc().initWithFrame_(NSMakeRect(0, h - HEADER_H, WIDTH, HEADER_H))
        strip.setAutoresizingMask_(2 | 8)   # 宽度跟随、始终贴顶
        effect.addSubview_(strip)

        page = NSURL.fileURLWithPath_(os.path.join(HERE, "ui", "index.html"))
        web.loadFileURL_allowingReadAccessToURL_(page, page.URLByDeletingLastPathComponent())

        self.panel, self.web = panel, web
        self.apply_level()
        self.apply_appearance()
        if self.cfg.get("visible", True):
            panel.orderFrontRegardless()
        self.build_status_item()

        timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(0.5, self, "tick:", None, True)
        NSRunLoop.currentRunLoop().addTimer_forMode_(timer, "NSRunLoopCommonModes")
        self.timer = timer

    @objc.python_method
    def set_height(self, h):
        vf = self.panel.screen().visibleFrame() if self.panel.screen() else NSScreen.mainScreen().visibleFrame()
        h = max(90, min(int(h), int(vf.size.height - 20)))
        f = self.panel.frame()
        if abs(f.size.height - h) < 1:
            return
        top = f.origin.y + f.size.height
        self.panel.setFrame_display_animate_(NSMakeRect(f.origin.x, top - h, f.size.width, h), True, True)
        self.panel.invalidateShadow()

    def windowDidMove_(self, note):
        f = self.panel.frame()
        self.cfg["x"], self.cfg["top"] = f.origin.x, f.origin.y + f.size.height
        save_config(self.cfg)

    # ------------------------------------------------------------ 刷新
    def tick_(self, timer):
        v = self.store.view()
        payload = json.dumps(json.dumps(v, ensure_ascii=False))
        self.web.evaluateJavaScript_completionHandler_(f"window.render && window.render({payload})", None)
        n = v["summary"]["working"]
        title = f" {n}" if n else ""
        btn = self.status.button()
        if btn.title() != title:
            btn.setTitle_(title)

    @objc.python_method
    def handle(self, msg):
        kind = msg.get("type")
        if kind == "height":
            self.set_height(msg.get("h") or 120)
        elif kind == "open":
            target = self.store.target_of(msg.get("key", ""))
            if target and target[0] == "tab":
                focus_tab(target[1], target[2])
            elif target and target[0] == "app":
                open_app(target[1])

    @objc.python_method
    def notify(self, row):
        if not self.cfg.get("sound", True):
            return
        snd = NSSound.soundNamed_("Glass")
        if snd:
            snd.play()
        state = {"done": "已完成", "error": "出错了", "stopped": "已停止"}.get(row["state"], "已结束")
        body = row.get("title") or row.get("place") or ""
        extra = []
        if row.get("tokens"):
            extra.append(f"{'≈' if row.get('est') else ''}{row['tokens']:,} tok")
        m, s = divmod(int(row.get("elapsed") or 0), 60)
        extra.append(f"用时 {m}:{s:02d}")
        script = (f"display notification {json.dumps(body[:80] + chr(10) + '，'.join(extra), ensure_ascii=False)} "
                  f"with title {json.dumps(row['label'] + ' ' + state, ensure_ascii=False)}")
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ------------------------------------------------------------ 菜单栏
    @objc.python_method
    def build_status_item(self):
        self.status = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        btn = self.status.button()
        img = None
        try:
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_("sparkles", APP_NAME)
        except Exception:
            pass
        if img:
            img.setTemplate_(True)
            btn.setImage_(img)
            btn.setImagePosition_(2)    # 图标在左、数字在右
        else:
            btn.setTitle_("✦")
        menu = NSMenu.alloc().init()
        self.items["show"] = self.add(menu, "显示小组件", "toggleWindow:")
        menu.addItem_(NSMenuItem.separatorItem())
        self.items["float"] = self.add(menu, "浮在所有窗口之上", "setFloating:")
        self.items["desktop"] = self.add(menu, "放在桌面上（像系统小组件）", "setDesktop:")
        menu.addItem_(NSMenuItem.separatorItem())
        sub = NSMenu.alloc().init()
        self.items["auto"] = self.add(sub, "跟随系统", "setAppearanceAuto:")
        self.items["dark"] = self.add(sub, "深色", "setAppearanceDark:")
        self.items["light"] = self.add(sub, "浅色", "setAppearanceLight:")
        app_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("外观", None, "")
        app_item.setSubmenu_(sub)
        menu.addItem_(app_item)
        self.items["sound"] = self.add(menu, "完成时提醒", "toggleSound:")
        self.items["login"] = self.add(menu, "登录时自动打开", "toggleLogin:")
        menu.addItem_(NSMenuItem.separatorItem())
        self.add(menu, "打开自动化权限设置…", "openPrivacy:")
        self.add(menu, "使用说明", "openReadme:")
        menu.addItem_(NSMenuItem.separatorItem())
        self.add(menu, f"退出 {APP_NAME}", "quit:", "q")
        menu.setDelegate_(self)
        self.status.setMenu_(menu)
        self.sync_menu()

    @objc.python_method
    def add(self, menu, title, action, key=""):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
        item.setTarget_(self)
        menu.addItem_(item)
        return item

    @objc.python_method
    def sync_menu(self):
        on = lambda b: 1 if b else 0  # noqa: E731
        self.items["show"].setState_(on(self.panel.isVisible()))
        desktop = self.cfg.get("level") == "desktop"
        self.items["float"].setState_(on(not desktop))
        self.items["desktop"].setState_(on(desktop))
        ap = self.cfg.get("appearance", "auto")
        for k in ("auto", "dark", "light"):
            self.items[k].setState_(on(ap == k))
        self.items["sound"].setState_(on(self.cfg.get("sound", True)))
        self.items["login"].setState_(on(os.path.exists(AGENT_PLIST)))

    def menuWillOpen_(self, menu):
        self.sync_menu()

    @objc.python_method
    def apply_level(self):
        if self.cfg.get("level") == "desktop" and DESKTOP_LEVEL is not None:
            self.panel.setLevel_(DESKTOP_LEVEL)
        else:
            self.panel.setLevel_(FLOATING_LEVEL)

    @objc.python_method
    def apply_appearance(self):
        name = {"dark": "NSAppearanceNameDarkAqua", "light": "NSAppearanceNameAqua"}.get(
            self.cfg.get("appearance", "auto"))
        NSApplication.sharedApplication().setAppearance_(NSAppearance.appearanceNamed_(name) if name else None)

    @objc.python_method
    def set_cfg(self, **kw):
        self.cfg.update(kw)
        save_config(self.cfg)
        self.sync_menu()

    def toggleWindow_(self, sender):
        if self.panel.isVisible():
            self.panel.orderOut_(None)
        else:
            self.panel.orderFrontRegardless()
        self.set_cfg(visible=bool(self.panel.isVisible()))

    def setFloating_(self, sender):
        self.set_cfg(level="float")
        self.apply_level()

    def setDesktop_(self, sender):
        self.set_cfg(level="desktop")
        self.apply_level()

    def setAppearanceAuto_(self, sender):
        self.set_cfg(appearance="auto")
        self.apply_appearance()

    def setAppearanceDark_(self, sender):
        self.set_cfg(appearance="dark")
        self.apply_appearance()

    def setAppearanceLight_(self, sender):
        self.set_cfg(appearance="light")
        self.apply_appearance()

    def toggleSound_(self, sender):
        self.set_cfg(sound=not self.cfg.get("sound", True))

    def toggleLogin_(self, sender):
        if os.path.exists(AGENT_PLIST):
            os.remove(AGENT_PLIST)
        else:
            os.makedirs(os.path.dirname(AGENT_PLIST), exist_ok=True)
            with open(AGENT_PLIST, "wb") as f:
                plistlib.dump({
                    "Label": "com.aistatus.widget",
                    "ProgramArguments": (["/usr/bin/open", "-a", os.environ["AISTATUS_APP"]]
                                         if os.environ.get("AISTATUS_APP")
                                         else [sys.executable, os.path.join(HERE, "main.py")]),
                    "RunAtLoad": True, "ProcessType": "Interactive",
                    "LimitLoadToSessionType": "Aqua",
                }, f)
        self.sync_menu()

    def openPrivacy_(self, sender):
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"])

    def openReadme_(self, sender):
        subprocess.Popen(["open", "-e", README])

    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)        # 不在程序坞显示图标，只有菜单栏
    store = Store()
    try:
        make_server(store)
    except OSError:
        alert = NSAlert.alloc().init()
        alert.setMessageText_(f"{APP_NAME} 已经在运行")
        alert.setInformativeText_("请在菜单栏找到 ✦ 图标。")
        alert.runModal()
        return
    ctrl = Controller.alloc().init()
    ctrl.store = store
    store.on_finish = lambda row: AppHelper.callAfter(ctrl.notify, row)
    BrowserPoller(store).start()
    LocalScanner(store).start()
    ctrl.build()
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
