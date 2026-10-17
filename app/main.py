#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 活动 —— macOS 主程序。

三种显示方式（设置里切换，菜单栏图标始终保留，作为控制和“专注后恢复”的入口）：
  刘海    贴着刘海的黑色灵动岛：左侧活动指示，右侧主账号额度；悬停展开
  菜单栏  菜单栏图标旁显示额度，点击弹出一个账号的详情，可左右切换
  侧边栏  毛玻璃窗口，同时排列已选账号和任务，可拖到任意显示器
"""
import json
import os
import plistlib
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import objc  # noqa: E402
from AppKit import (NSAlert, NSAppearance, NSApplication, NSBezierPath, NSColor, NSEvent, NSImage,  # noqa: E402
                    NSMenu, NSMenuItem, NSPanel, NSPopover, NSScreen, NSSound, NSStatusBar,
                    NSTrackingArea, NSView, NSViewController, NSVisualEffectView, NSWindow)
from Foundation import NSMakeRect, NSMakeSize, NSObject, NSRunLoop, NSTimer, NSURL  # noqa: E402
from PyObjCTools import AppHelper  # noqa: E402
from WebKit import WKUserContentController, WKWebView, WKWebViewConfiguration  # noqa: E402

try:
    from Foundation import NSRunLoopCommonModes
except ImportError:
    NSRunLoopCommonModes = "kCFRunLoopCommonModes"
try:
    from Quartz import CGWindowLevelForKey, kCGDesktopIconWindowLevelKey
    DESKTOP_LEVEL = CGWindowLevelForKey(kCGDesktopIconWindowLevelKey) + 1
except Exception:
    DESKTOP_LEVEL = None

from browsers import BrowserPoller, focus_tab, open_app  # noqa: E402
from clients import ClientScanner, mac_activate, mac_trusted  # noqa: E402
from core import Store, make_server  # noqa: E402
from island_layout import pill_frame  # noqa: E402
from island_layout import layout as fit_island  # noqa: E402
from local_sources import LocalScanner  # noqa: E402
from quota import QuotaPoller, secret_get, secret_set  # noqa: E402

APP_NAME = "AI 活动"
WIDTH, HEADER_H, RADIUS = 340, 58, 22
DROP_W, DROP_GAP = 380, 6
FLOATING_LEVEL, ISLAND_LEVEL = 3, 26
BORDERLESS, NONACTIVATING = 0, 1 << 7
BEHAVIOR = (1 << 0) | (1 << 4) | (1 << 6) | (1 << 8)
SUPPORT = os.path.expanduser("~/Library/Application Support/AIStatus")
CONFIG = os.path.join(SUPPORT, "config.json")
AGENT_PLIST = os.path.expanduser("~/Library/LaunchAgents/com.aistatus.widget.plist")
README = os.path.join(os.path.dirname(HERE), "README.md")
UI = os.path.join(HERE, "ui")
FOCUS_CHOICES = [(15, "15 分钟"), (60, "1 小时"), (180, "3 小时"), (300, "5 小时")]
MODES = [("island", "刘海"), ("menubar", "菜单栏"), ("sidebar", "侧边栏")]


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


def round_mask(view, r):
    try:
        def draw(rect):
            NSColor.blackColor().set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, r, r).fill()
            return True
        img = NSImage.imageWithSize_flipped_drawingHandler_(NSMakeSize(2 * r + 1, 2 * r + 1), False, draw)
        img.setCapInsets_((r, r, r, r))
        img.setResizingMode_(1)
        view.setMaskImage_(img)
    except Exception:
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(r)
        view.layer().setMasksToBounds_(True)


def symbol(name, fallback=None):
    try:
        img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, APP_NAME)
        if img:
            img.setTemplate_(True)
            return img
    except Exception:
        pass
    return fallback


def notch_screen():
    for s in NSScreen.screens():
        try:
            if s.safeAreaInsets().top > 0:
                return s
        except Exception:
            pass
    return NSScreen.mainScreen()


def notch_geometry(screen):
    """返回 (中心 x, 屏幕顶边 y, 刘海高度, 刘海宽度)。没有刘海时宽度为 0。"""
    f = screen.frame()
    cx, top = f.origin.x + f.size.width / 2, f.origin.y + f.size.height
    try:
        inset = screen.safeAreaInsets().top
    except Exception:
        inset = 0
    if inset > 0:
        try:
            nw = f.size.width - screen.auxiliaryTopLeftArea().size.width - screen.auxiliaryTopRightArea().size.width
        except Exception:
            nw = 200
        return cx, top, inset, max(0, nw)
    return cx, top, NSStatusBar.systemStatusBar().thickness() or 24, 0


def _ax_frame(AS, el):
    pt_t = getattr(AS, "kAXValueTypeCGPoint", getattr(AS, "kAXValueCGPointType", 1))
    sz_t = getattr(AS, "kAXValueTypeCGSize", getattr(AS, "kAXValueCGSizeType", 2))
    e1, pos = AS.AXUIElementCopyAttributeValue(el, "AXPosition", None)
    e2, size = AS.AXUIElementCopyAttributeValue(el, "AXSize", None)
    if e1 or e2 or pos is None or size is None:
        return None
    ok1, pt = AS.AXValueGetValue(pos, pt_t, None)
    ok2, sz = AS.AXValueGetValue(size, sz_t, None)
    return (pt.x, pt.y, sz.width, sz.height) if ok1 and ok2 else None


def menubar_obstacles(g):
    """测量菜单栏上已有元素，返回 (obstacles, left_known, right_known, diag)。
    状态栏图标：系统窗口列表（无需权限），失败时用辅助功能读取各应用的菜单栏图标；
    应用菜单：前台应用的辅助功能信息。时钟和控制中心总在右侧，右侧一个都没测到就视为测量失败。"""
    ih, notch_l, notch_r = g["ih"], g["nl"], g["nr"]
    top_cg = g["prim_h"] - (g["y"] + g["h"])                # 系统窗口列表的坐标原点在主屏左上角
    x_lo, x_hi = g["x"], g["x"] + g["w"]
    diag = {"time": time.strftime("%H:%M:%S"), "screen": [x_lo, g["y"], g["w"], g["h"]], "top_cg": top_cg, "ih": ih,
            "notch": [round(notch_l), round(notch_r)], "cg_items": [], "cg_rejected": 0, "ax_items": [], "menus_right": None}
    obs, me = [], os.getpid()
    try:
        from Quartz import CGWindowListCopyWindowInfo, kCGNullWindowID, kCGWindowListOptionOnScreenOnly
        for w in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID) or []:
            layer = int(w.get("kCGWindowLayer", 0))
            if layer not in (24, 25) or int(w.get("kCGWindowOwnerPID", 0)) == me:
                continue
            b = w.get("kCGWindowBounds") or {}
            x, y = float(b.get("X", 0)), float(b.get("Y", 0))
            ww, hh = float(b.get("Width", 0)), float(b.get("Height", 0))
            # 只要求窗口落在这块屏幕的菜单栏这一行、宽度像一个图标
            if not (top_cg - 4 <= y <= top_cg + ih) or not 0 < ww < 0.5 * g["w"] or hh > ih + 12 or x + ww < x_lo or x > x_hi:
                diag["cg_rejected"] += 1
                continue
            obs.append((x, x + ww))
            diag["cg_items"].append([round(x), round(ww), layer, str(w.get("kCGWindowOwnerName", ""))[:20]])
    except Exception as e:  # noqa: BLE001
        diag["cg_error"] = repr(e)[:120]
    trusted = mac_trusted(False)
    if trusted and not any(x0 >= notch_r - 4 for x0, _ in obs):
        try:                                                  # 备用：辅助功能读取各应用的菜单栏图标
            import ApplicationServices as AS
            from AppKit import NSWorkspace
            t_ax = time.time()
            for app in NSWorkspace.sharedWorkspace().runningApplications():
                if time.time() - t_ax > 0.3:                  # 最多花 0.3 秒，任何应用卡住都不影响菜单栏
                    diag["ax_truncated"] = True
                    break
                el = AS.AXUIElementCreateApplication(app.processIdentifier())
                AS.AXUIElementSetMessagingTimeout(el, 0.05)
                err, extras = AS.AXUIElementCopyAttributeValue(el, "AXExtrasMenuBar", None)
                if err != 0 or extras is None:
                    continue
                err, kids = AS.AXUIElementCopyAttributeValue(extras, "AXChildren", None)
                for k in (kids or []) if err == 0 else []:
                    fr = _ax_frame(AS, k)
                    if fr and x_lo <= fr[0] <= x_hi and abs(fr[1] - top_cg) < ih:
                        obs.append((fr[0], fr[0] + fr[2]))
                        diag["ax_items"].append([round(fr[0]), round(fr[2])])
        except Exception as e:  # noqa: BLE001
            diag["ax_error"] = repr(e)[:120]
    right_known = any(x0 >= notch_r - 4 for x0, _ in obs)
    left_known = False
    if trusted:
        try:
            import ApplicationServices as AS
            from AppKit import NSWorkspace
            front = NSWorkspace.sharedWorkspace().frontmostApplication()
            el = AS.AXUIElementCreateApplication(front.processIdentifier())
            AS.AXUIElementSetMessagingTimeout(el, 0.1)
            err, bar = AS.AXUIElementCopyAttributeValue(el, "AXMenuBar", None)
            if err == 0 and bar is not None:
                err, kids = AS.AXUIElementCopyAttributeValue(bar, "AXChildren", None)
                if err == 0:
                    left_known = True
                    right = None
                    for k in kids or []:
                        fr = _ax_frame(AS, k)
                        if fr and x_lo <= fr[0] <= x_hi and abs(fr[1] - top_cg) < ih:
                            right = max(right or x_lo, fr[0] + fr[2])
                    if right is not None:
                        obs.append((x_lo, right))
                        diag["menus_right"] = round(right)
        except Exception as e:  # noqa: BLE001
            diag["menu_error"] = repr(e)[:120]
    diag.update(trusted=trusted, left_known=left_known, right_known=right_known)
    return obs, left_known, right_known, diag


class IslandMeter(threading.Thread):
    """后台测量菜单栏（系统窗口列表、辅助功能），慢的读取不会卡住界面。"""

    def __init__(self):
        super().__init__(daemon=True)
        self.lock, self.wake = threading.Lock(), threading.Event()
        self.geo, self.result = None, None

    def request(self, geo):
        with self.lock:
            self.geo = dict(geo)
        self.wake.set()

    def latest(self, geo):
        with self.lock:
            r = self.result
        return r[1] if r and r[0] == geo else None          # 只用同一几何条件下测得的结果

    def run(self):
        while True:
            self.wake.wait(2.0)
            self.wake.clear()
            with self.lock:
                geo = dict(self.geo) if self.geo else None
            if not geo:
                continue
            try:
                res = menubar_obstacles(geo)
            except Exception as e:  # noqa: BLE001
                res = ([], False, False, {"error": repr(e)[:160]})
            with self.lock:
                self.result = (geo, res)


class Panel(NSPanel):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


class DragStrip(NSView):
    def mouseDown_(self, event):
        self.window().performWindowDragWithEvent_(event)

    def acceptsFirstMouse_(self, event):
        return True


class HoverView(NSView):
    """透明覆盖层：只负责感知鼠标进出（非活动窗口里网页收不到悬停事件），点击穿透给网页。"""

    def updateTrackingAreas(self):
        for a in list(self.trackingAreas()):
            self.removeTrackingArea_(a)
        opts = 0x01 | 0x80 | 0x200      # MouseEnteredAndExited | ActiveAlways | InVisibleRect
        self.addTrackingArea_(NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(self.bounds(), opts, self, None))
        objc.super(HoverView, self).updateTrackingAreas()

    def mouseEntered_(self, event):
        self.ctrl.island_hover(True)

    def mouseExited_(self, event):
        self.ctrl.island_hover(False)

    def mouseDown_(self, event):
        pass

    def hitTest_(self, point):
        return None


WKScriptMessageHandler = objc.protocolNamed("WKScriptMessageHandler")


class Bridge(NSObject, protocols=[WKScriptMessageHandler]):
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        try:
            msg = json.loads(str(message.body()))
        except Exception:
            return
        self.ctrl.handle(msg, self.surface)


class Controller(NSObject):
    def init(self):
        self = objc.super(Controller, self).init()
        if self is None:
            return None
        self.cfg = load_config()
        self.cfg.setdefault("mode", "island")
        self.cfg.setdefault("clients_on", True)
        self.store = None
        self.items = {}
        self.webs = {}
        self.bridges = []
        self.secrets = {}
        self.ax_cache = (0, False)
        return self

    # ------------------------------------------------------------ 通用
    @objc.python_method
    def make_web(self, surface, frame, page, query=""):
        ucc = WKUserContentController.alloc().init()
        br = Bridge.alloc().init()
        br.ctrl, br.surface = self, surface
        self.bridges.append(br)
        ucc.addScriptMessageHandler_name_(br, "aiw")
        conf = WKWebViewConfiguration.alloc().init()
        conf.setUserContentController_(ucc)
        web = WKWebView.alloc().initWithFrame_configuration_(frame, conf)
        web.setValue_forKey_(False, "drawsBackground")
        try:
            web.setUnderPageBackgroundColor_(NSColor.clearColor())
        except Exception:
            pass
        web.setAutoresizingMask_(2 | 16)
        url = NSURL.URLWithString_(NSURL.fileURLWithPath_(os.path.join(UI, page)).absoluteString() + query)
        web.loadFileURL_allowingReadAccessToURL_(url, NSURL.fileURLWithPath_(UI))
        self.webs[surface] = web
        return web

    @objc.python_method
    def focused(self):
        return time.time() < self.cfg.get("focus_until", 0)

    @objc.python_method
    def set_cfg(self, **kw):
        self.cfg.update(kw)
        save_config(self.cfg)

    # ------------------------------------------------------------ 侧边栏
    @objc.python_method
    def build_sidebar(self):
        h = 220
        x, top = self.cfg.get("x"), self.cfg.get("top")
        vf = NSScreen.mainScreen().visibleFrame()
        if x is None or not any(s.frame().origin.x <= x <= s.frame().origin.x + s.frame().size.width - 40 and
                                s.frame().origin.y + 60 <= top <= s.frame().origin.y + s.frame().size.height
                                for s in NSScreen.screens()):
            x, top = vf.origin.x + vf.size.width - WIDTH - 18, vf.origin.y + vf.size.height - 14
        p = Panel.alloc().initWithContentRect_styleMask_backing_defer_(NSMakeRect(x, top - h, WIDTH, h),
                                                                       BORDERLESS | NONACTIVATING, 2, False)
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setHidesOnDeactivate_(False)
        p.setReleasedWhenClosed_(False)
        p.setCollectionBehavior_(BEHAVIOR)
        p.setDelegate_(self)
        effect = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDTH, h))
        effect.setMaterial_(6)
        effect.setBlendingMode_(0)
        effect.setState_(1)
        effect.setAutoresizingMask_(2 | 16)
        round_mask(effect, RADIUS)
        p.setContentView_(effect)
        web = self.make_web("sidebar", NSMakeRect(0, 0, WIDTH, h), "index.html", "?view=sidebar")
        web.setWantsLayer_(True)
        web.layer().setCornerRadius_(RADIUS)
        web.layer().setMasksToBounds_(True)
        effect.addSubview_(web)
        strip = DragStrip.alloc().initWithFrame_(NSMakeRect(0, h - HEADER_H, WIDTH, HEADER_H))
        strip.setAutoresizingMask_(2 | 8)
        effect.addSubview_(strip)
        self.sidebar = p

    def windowDidMove_(self, note):
        if note.object() is getattr(self, "sidebar", None):
            f = self.sidebar.frame()
            self.set_cfg(x=f.origin.x, top=f.origin.y + f.size.height)

    # ------------------------------------------------------------ 刘海
    @objc.python_method
    def island_geo(self):
        """当前刘海几何（主线程读取 NSScreen），返回纯数字，供后台测量和布局使用。"""
        scr = notch_screen()
        cx, top, ih, nw = notch_geometry(scr)
        f = scr.frame()
        return {"x": f.origin.x, "y": f.origin.y, "w": f.size.width, "h": f.size.height,
                "prim_h": NSScreen.screens()[0].frame().size.height, "ih": ih,
                "nl": cx - nw / 2, "nr": cx + nw / 2, "top": top}

    @objc.python_method
    def fit(self):
        """用后台最近一次的测量结果计算布局；还没有结果时按“两侧都未确认”处理（只占刘海）。"""
        g = self.island_geo()
        self.meter.request(g)
        res = self.meter.latest(g)
        obs, lk, rk, diag = res if res else ([], False, False, {"pending": True})
        lay = fit_island(g["nl"], g["nr"], g["x"], g["x"] + g["w"], obs, lk, rk, self.cfg.get("island_side", "auto"))
        diag = dict(diag, layout=lay)
        self.isl_diag = diag
        return lay, (g["nl"], g["nr"], g["top"], g["ih"], g["x"], g["x"] + g["w"])

    @objc.python_method
    def make_panel(self, frame, level, shadow):
        p = Panel.alloc().initWithContentRect_styleMask_backing_defer_(frame, BORDERLESS | NONACTIVATING, 2, False)
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(shadow)
        p.setHidesOnDeactivate_(False)
        p.setReleasedWhenClosed_(False)
        p.setLevel_(level)
        p.setCollectionBehavior_(BEHAVIOR)
        return p

    @objc.python_method
    def build_island(self):
        self.meter = IslandMeter()
        self.meter.start()
        lay, geo = self.fit()
        nl, nr, top, ih = geo[:4]
        x, y, w, h = pill_frame(lay, nl, nr, top, ih) or (nl, top - ih, max(1, nr - nl), ih)
        pill = self.make_panel(NSMakeRect(x, y, w, h), ISLAND_LEVEL, False)
        host = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        pill.setContentView_(host)
        q = f"?view=island&ih={int(ih)}&lw={lay['lw']}&rw={lay['rw']}&mode={lay['mode']}"
        host.addSubview_(self.make_web("island", NSMakeRect(0, 0, w, h), "index.html", q))
        hv = HoverView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        hv.ctrl = self
        hv.setAutoresizingMask_(2 | 16)
        host.addSubview_(hv)
        self.island = pill
        drop = self.make_panel(NSMakeRect(0, 0, DROP_W, 300), ISLAND_LEVEL, True)
        dhost = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, DROP_W, 300))
        drop.setContentView_(dhost)
        dweb = self.make_web("drop", NSMakeRect(0, 0, DROP_W, 300), "index.html", "?view=drop")
        dweb.setWantsLayer_(True)
        dweb.layer().setCornerRadius_(22)
        dweb.layer().setMasksToBounds_(True)
        dhost.addSubview_(dweb)
        dhv = HoverView.alloc().initWithFrame_(NSMakeRect(0, 0, DROP_W, 300))
        dhv.ctrl = self
        dhv.setAutoresizingMask_(2 | 16)
        dhost.addSubview_(dhv)
        self.drop = drop
        self.drop_h, self.pinned, self.collapse_timer = 300, False, None
        self.isl_key, self.isl_lay, self.isl_geo = None, lay, geo
        self.relayout_island(force=True)

    @objc.python_method
    def relayout_island(self, force=False):
        lay, geo = self.fit()
        nl, nr, top, ih = geo[:4]
        key = (lay["mode"], lay["lw"], lay["rw"], round(nl), round(nr), round(top), round(ih))
        if key != self.isl_key or force:
            if key != self.isl_key:
                self.log_island()
            self.isl_key, self.isl_lay, self.isl_geo = key, lay, geo
            fr = pill_frame(lay, nl, nr, top, ih)
            if fr is None:                                   # 没有刘海、两侧也没空位：不显示岛
                self.island.orderOut_(None)
            else:
                self.island.setFrame_display_(NSMakeRect(*fr), True)
                if self.cfg.get("mode") == "island" and not self.focused():
                    self.island.orderFrontRegardless()
            if self.drop.isVisible():
                self.place_drop()
            self.update_status()
        js = json.dumps({"ih": ih, "lw": lay["lw"], "rw": lay["rw"], "mode": lay["mode"]})
        self.webs["island"].evaluateJavaScript_completionHandler_(f"window.islandLayout && window.islandLayout({js})", None)

    @objc.python_method
    def log_island(self):
        try:
            os.makedirs(SUPPORT, exist_ok=True)
            with open(os.path.join(SUPPORT, "island.log"), "a", encoding="utf-8") as fh:
                fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + json.dumps(getattr(self, "isl_diag", {}), ensure_ascii=False) + "\n")
        except OSError:
            pass

    def copyDiag_(self, sender):
        from AppKit import NSPasteboard
        g = self.island_geo()
        self.meter.request(g)
        for _ in range(20):                                  # 最多等 1 秒拿到这次的测量结果
            if self.meter.latest(g):
                break
            time.sleep(0.05)
        self.relayout_island(force=True)
        text = json.dumps(getattr(self, "isl_diag", {}), ensure_ascii=False, indent=1)
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, "public.utf8-plain-text")
        alert = NSAlert.alloc().init()
        alert.setMessageText_("菜单栏诊断信息已复制")
        alert.setInformativeText_("可以直接粘贴发给开发者。内容只有菜单栏图标的位置和宽度，不含任何文字或窗口内容。")
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        alert.runModal()

    def setSide_(self, sender):
        self.set_cfg(island_side=str(sender.representedObject()))
        self.relayout_island(force=True)

    def appActivated_(self, note):
        if self.cfg.get("mode") == "island":
            self.relayout_island()

    def screensChanged_(self, note):
        self.relayout_island(force=True)

    @objc.python_method
    def place_drop(self):
        nl, nr, top, ih, sl, sr = self.isl_geo
        bottom = top - ih
        cx = (nl + nr) / 2
        x = min(max(cx - DROP_W / 2, sl + 8), sr - DROP_W - 8)
        h = self.drop_h
        self.drop.setFrame_display_(NSMakeRect(x, bottom - DROP_GAP - h, DROP_W, h), True)

    @objc.python_method
    def show_drop(self):
        if self.focused() or self.cfg.get("mode") != "island":
            return
        self.place_drop()
        if not self.drop.isVisible():
            self.drop.orderFrontRegardless()
            self.push()

    @objc.python_method
    def mouse_in_island(self):
        p = NSEvent.mouseLocation()
        for w in (self.island, self.drop):
            if w.isVisible():
                f = w.frame()
                if f.origin.x <= p.x <= f.origin.x + f.size.width and f.origin.y <= p.y <= f.origin.y + f.size.height:
                    return True
        return False

    @objc.python_method
    def island_hover(self, on):
        if self.collapse_timer:
            self.collapse_timer.invalidate()
            self.collapse_timer = None
        if on:
            self.show_drop()
        elif not self.pinned:
            self.collapse_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.45, self, "collapseDrop:", None, False)

    def collapseDrop_(self, timer):
        self.collapse_timer = None
        if not self.pinned and not self.mouse_in_island():
            self.drop.orderOut_(None)

    # ------------------------------------------------------------ 菜单栏弹出
    @objc.python_method
    def build_popover(self):
        pop = NSPopover.alloc().init()
        pop.setBehavior_(1)                      # 点击其他地方自动关闭
        vc = NSViewController.alloc().init()
        vc.setView_(self.make_web("popover", NSMakeRect(0, 0, WIDTH, 360), "index.html", "?view=popover"))
        pop.setContentViewController_(vc)
        pop.setContentSize_(NSMakeSize(WIDTH, 360))
        self.popover = pop

    @objc.python_method
    def toggle_popover(self):
        if self.popover.isShown():
            self.popover.close()
        else:
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            btn = self.status.button()
            self.popover.showRelativeToRect_ofView_preferredEdge_(btn.bounds(), btn, 1)

    # ------------------------------------------------------------ 设置窗口
    @objc.python_method
    def open_settings(self):
        if not hasattr(self, "settings_win"):
            w = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(NSMakeRect(0, 0, 620, 780), 1 | 2 | 4, 2, False)
            w.setTitle_(f"{APP_NAME} · 设置")
            w.setReleasedWhenClosed_(False)
            w.center()
            w.setContentView_(self.make_web("settings", NSMakeRect(0, 0, 620, 780), "settings.html"))
            self.settings_win = w
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.settings_win.makeKeyAndOrderFront_(None)
        self.push()

    # ------------------------------------------------------------ 模式与专注
    @objc.python_method
    def apply_mode(self):
        mode, hide = self.cfg.get("mode", "island"), self.focused()
        if hide or mode != "sidebar":
            self.sidebar.orderOut_(None)
        else:
            self.sidebar.setLevel_(DESKTOP_LEVEL if self.cfg.get("level") == "desktop" and DESKTOP_LEVEL else FLOATING_LEVEL)
            self.sidebar.orderFrontRegardless()
        if hide or mode != "island":
            self.island.orderOut_(None)
            self.drop.orderOut_(None)
            self.pinned = False
        else:
            self.relayout_island(force=True)
        if (hide or mode != "menubar") and self.popover.isShown():
            self.popover.close()
        self.update_status()

    @objc.python_method
    def focus(self, minutes):
        self.set_cfg(focus_until=time.time() + int(minutes) * 60)
        self.apply_mode()

    @objc.python_method
    def unfocus(self):
        self.set_cfg(focus_until=0)
        self.apply_mode()

    # ------------------------------------------------------------ 刷新
    @objc.python_method
    def ui_state(self):
        now = time.time()
        if now - self.ax_cache[0] > 5:
            self.ax_cache = (now, mac_trusted(False))
        return {"mode": self.cfg.get("mode", "island"), "platform": "mac", "modes_available": [m for m, _ in MODES],
                "companion": self.cfg.get("companion", False), "clients_on": self.cfg.get("clients_on", True),
                "quota_claude_code": self.cfg.get("quota_claude_code", False),
                "appearance": self.cfg.get("appearance", "auto"), "sound": self.cfg.get("sound", True),
                "island_side": self.cfg.get("island_side", "auto"),
                "focus_until": self.cfg.get("focus_until", 0) if self.focused() else 0,
                "secrets": self.secrets, "ax_trusted": self.ax_cache[1]}

    @objc.python_method
    def push(self):
        self.store.ui = self.ui_state()
        v = self.store.view()
        payload = json.dumps(json.dumps(v, ensure_ascii=False))
        visible = {"sidebar": self.sidebar.isVisible(), "island": self.island.isVisible(), "drop": self.drop.isVisible(),
                   "popover": self.popover.isShown(),
                   "settings": hasattr(self, "settings_win") and self.settings_win.isVisible()}
        for name, web in self.webs.items():
            if visible.get(name):
                web.evaluateJavaScript_completionHandler_(f"window.render && window.render({payload})", None)
        self.last_view = v
        order = self.store.prefs.get("order", [])
        if order != self.cfg.get("prefs", {}).get("order"):
            self.cfg.setdefault("prefs", {})["order"] = list(order)
            save_config(self.cfg)

    def tick_(self, timer):
        try:
            self.ticks = getattr(self, "ticks", 0) + 1
            if self.ticks % 4 == 0 and self.cfg.get("mode") == "island" and not self.focused():
                self.relayout_island()                      # 每 2 秒重新测量菜单栏，图标增减或变宽时自动避让
            if self.cfg.get("focus_until") and not self.focused():
                self.unfocus()
            self.push()
            self.update_status()
        except Exception as e:
            print("refresh error:", e, file=sys.stderr)

    @objc.python_method
    def update_status(self):
        btn = self.status.button()
        v = getattr(self, "last_view", None) or {}
        if self.focused():
            img, left = symbol("moon.fill"), int((self.cfg["focus_until"] - time.time()) / 60) + 1
            title = f" {left} 分"
        else:
            img = symbol("sparkles")
            n = (v.get("summary") or {}).get("working", 0)
            p = v.get("primary")
            island_full = self.cfg.get("mode") == "island" and getattr(self, "isl_lay", {}).get("mode") == "none"
            if (self.cfg.get("mode") == "menubar" or island_full) and p:
                title = f" {p['headline']}" + (f" · {n}" if n else "")
            else:
                title = f" {n}" if n else ""
        if img and btn.image() is not img:
            btn.setImage_(img)
            btn.setImagePosition_(2)
        if btn.title() != title:
            btn.setTitle_(title)

    # ------------------------------------------------------------ 消息
    @objc.python_method
    def handle(self, msg, surface):
        kind = msg.get("type")
        if kind == "height":
            h = max(90, min(int(msg.get("h") or 120), 900))
            if surface == "sidebar":
                f = self.sidebar.frame()
                if abs(f.size.height - h) >= 1:
                    top = f.origin.y + f.size.height
                    self.sidebar.setFrame_display_animate_(NSMakeRect(f.origin.x, top - h, f.size.width, h), True, True)
                    self.sidebar.invalidateShadow()
            elif surface == "popover":
                self.popover.setContentSize_(NSMakeSize(WIDTH, h))
            elif surface == "drop":
                self.drop_h = h
                if self.drop.isVisible():
                    self.place_drop()
        elif kind == "island-hover":
            self.island_hover(bool(msg.get("on")))
        elif kind == "island-click":
            self.pinned = not self.pinned
            self.show_drop() if self.pinned else self.drop.orderOut_(None)
        elif kind == "open":
            t = self.store.target_of(msg.get("key", ""))
            if not t:
                return
            if t[0] == "tab":
                focus_tab(t[1], t[2])
            elif t[0] == "app":
                open_app(t[1])
            elif t[0] == "client":
                mac_activate(t[2])
            elif t[0] == "ext":
                self.store.queue_focus(t[1])
            if surface == "popover":
                self.popover.close()
            if surface == "drop":
                self.pinned = False
                self.drop.orderOut_(None)
        elif kind == "settings":
            patch = msg.get("patch") or {}
            prefs = {k: patch.pop(k) for k in ("order", "hidden", "primary", "popover_account") if k in patch}
            if prefs:
                self.cfg.setdefault("prefs", {}).update(prefs)
                self.store.set_prefs(self.cfg["prefs"])
            allowed = {"mode", "companion", "clients_on", "quota_claude_code", "appearance", "sound", "island_side"}
            self.set_cfg(**{k: v for k, v in patch.items() if k in allowed})
            if "appearance" in patch:
                self.apply_appearance()
            if "mode" in patch:
                self.apply_mode()
            if "island_side" in patch:
                self.relayout_island(force=True)
            if patch.get("clients_on"):
                mac_trusted(True)
            if "quota_claude_code" in patch:
                self.quota.refresh_now()
            self.push()
        elif kind == "secret":
            name = msg.get("name")
            if name in ("deepseek", "moonshot"):
                secret_set(name, (msg.get("value") or "").strip(), SUPPORT)
                self.secrets[name] = bool(secret_get(name, SUPPORT))
                self.quota.refresh_now()
        elif kind == "focus":
            self.focus(msg.get("minutes") or 60)
        elif kind == "unfocus":
            self.unfocus()
        elif kind == "settings-open":
            if surface == "popover":
                self.popover.close()
            if surface == "drop":
                self.pinned = False
                self.drop.orderOut_(None)
            self.open_settings()
        elif kind == "open-ax":
            mac_trusted(True)
            subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])

    @objc.python_method
    def notify(self, row):
        if not self.cfg.get("sound", True) or self.focused():
            return
        snd = NSSound.soundNamed_("Glass")
        if snd:
            snd.play()
        state = {"done": "已完成", "error": "出错了", "stopped": "已停止"}.get(row["state"], "已结束")
        extra = [f"{'≈' if row.get('est') else ''}{row['tokens']:,} tok"] if row.get("tokens") else []
        m, s = divmod(int(row.get("elapsed") or 0), 60)
        extra.append(f"用时 {m}:{s:02d}")
        body = (row.get("title") or row.get("place") or "")[:80] + "\n" + "，".join(extra)
        script = (f"display notification {json.dumps(body, ensure_ascii=False)} "
                  f"with title {json.dumps(row['label'] + ' ' + state, ensure_ascii=False)}")
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ------------------------------------------------------------ 菜单栏图标与菜单
    @objc.python_method
    def build_status_item(self):
        self.status = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        btn = self.status.button()
        btn.setImage_(symbol("sparkles"))
        btn.setImagePosition_(2)
        btn.setTarget_(self)
        btn.setAction_("statusClicked:")
        btn.sendActionOn_((1 << 2) | (1 << 4))   # 左键、右键抬起
        self.menu = NSMenu.alloc().init()
        self.menu.setDelegate_(self)

    def statusClicked_(self, sender):
        ev = NSApplication.sharedApplication().currentEvent()
        right = ev is not None and (ev.type() == 4 or (ev.modifierFlags() & (1 << 18)))
        if self.cfg.get("mode") == "menubar" and not right and not self.focused():
            self.toggle_popover()
            return
        self.rebuild_menu()
        self.status.setMenu_(self.menu)
        self.status.button().performClick_(None)
        self.status.setMenu_(None)

    @objc.python_method
    def add(self, menu, title, action, state=None, rep=None, key=""):
        it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
        if action:
            it.setTarget_(self)
        if state is not None:
            it.setState_(1 if state else 0)
        if rep is not None:
            it.setRepresentedObject_(rep)
        if not action:
            it.setEnabled_(False)
        menu.addItem_(it)
        return it

    @objc.python_method
    def submenu(self, menu, title):
        sub = NSMenu.alloc().init()
        it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        it.setSubmenu_(sub)
        menu.addItem_(it)
        return sub

    @objc.python_method
    def rebuild_menu(self):
        m = self.menu
        m.removeAllItems()
        if self.focused():
            left = int((self.cfg["focus_until"] - time.time()) / 60) + 1
            self.add(m, f"专注中，还剩 {left} 分钟", None)
            self.add(m, "立即显示", "unfocus:")
        else:
            sub = self.submenu(m, "专注一会儿（临时隐藏）")
            for mins, label in FOCUS_CHOICES:
                self.add(sub, label, "focusFor:", rep=mins)
        m.addItem_(NSMenuItem.separatorItem())
        sub = self.submenu(m, "显示方式")
        for mode, label in MODES:
            self.add(sub, label, "setMode:", state=self.cfg.get("mode") == mode, rep=mode)
        if self.cfg.get("mode") == "sidebar":
            sub.addItem_(NSMenuItem.separatorItem())
            self.add(sub, "侧边栏放在桌面层（像系统小组件）", "toggleDesktop:", state=self.cfg.get("level") == "desktop")
        if self.cfg.get("mode") == "island":
            side = self.submenu(m, "刘海内容位置")
            for k, label in (("auto", "自动避让图标"), ("left", "固定在刘海左侧"), ("right", "固定在刘海右侧")):
                self.add(side, label, "setSide:", state=self.cfg.get("island_side", "auto") == k, rep=k)
            side.addItem_(NSMenuItem.separatorItem())
            self.add(side, "复制菜单栏诊断信息", "copyDiag:")
        self.add(m, "设置…", "openSettings:", key=",")
        m.addItem_(NSMenuItem.separatorItem())
        sub = self.submenu(m, "外观")
        for k, label in (("auto", "跟随系统"), ("dark", "深色"), ("light", "浅色")):
            self.add(sub, label, "setAppearance:", state=self.cfg.get("appearance", "auto") == k, rep=k)
        self.add(m, "完成时提醒", "toggleSound:", state=self.cfg.get("sound", True))
        self.add(m, "登录时自动打开", "toggleLogin:", state=os.path.exists(AGENT_PLIST))
        m.addItem_(NSMenuItem.separatorItem())
        self.add(m, "打开自动化权限设置…", "openPrivacy:")
        self.add(m, "打开辅助功能权限设置…", "openAX:")
        self.add(m, "使用说明", "openReadme:")
        m.addItem_(NSMenuItem.separatorItem())
        self.add(m, f"退出 {APP_NAME}", "quit:", key="q")

    def focusFor_(self, sender):
        self.focus(int(sender.representedObject()))

    def unfocus_(self, sender):
        self.unfocus()

    def setMode_(self, sender):
        self.set_cfg(mode=str(sender.representedObject()))
        self.apply_mode()

    def toggleDesktop_(self, sender):
        self.set_cfg(level="float" if self.cfg.get("level") == "desktop" else "desktop")
        self.apply_mode()

    def openSettings_(self, sender):
        self.open_settings()

    def setAppearance_(self, sender):
        self.set_cfg(appearance=str(sender.representedObject()))
        self.apply_appearance()

    @objc.python_method
    def apply_appearance(self):
        name = {"dark": "NSAppearanceNameDarkAqua", "light": "NSAppearanceNameAqua"}.get(self.cfg.get("appearance", "auto"))
        NSApplication.sharedApplication().setAppearance_(NSAppearance.appearanceNamed_(name) if name else None)

    def toggleSound_(self, sender):
        self.set_cfg(sound=not self.cfg.get("sound", True))

    def toggleLogin_(self, sender):
        if os.path.exists(AGENT_PLIST):
            os.remove(AGENT_PLIST)
            return
        os.makedirs(os.path.dirname(AGENT_PLIST), exist_ok=True)
        args = (["/usr/bin/open", "-a", os.environ["AISTATUS_APP"]] if os.environ.get("AISTATUS_APP")
                else [sys.executable, os.path.join(HERE, "main.py")])
        with open(AGENT_PLIST, "wb") as f:
            plistlib.dump({"Label": "com.aistatus.widget", "ProgramArguments": args, "RunAtLoad": True,
                           "ProcessType": "Interactive", "LimitLoadToSessionType": "Aqua"}, f)

    def openPrivacy_(self, sender):
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"])

    def openAX_(self, sender):
        mac_trusted(True)
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])

    def openReadme_(self, sender):
        subprocess.Popen(["open", "-e", README])

    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)

    # ------------------------------------------------------------ 启动
    @objc.python_method
    def build(self):
        self.store.set_prefs(self.cfg.get("prefs", {}))
        for n in ("deepseek", "moonshot"):
            self.secrets[n] = bool(secret_get(n, SUPPORT))
        self.build_status_item()
        self.build_sidebar()
        self.build_island()
        self.build_popover()
        self.apply_appearance()
        self.apply_mode()
        from AppKit import NSNotificationCenter, NSWorkspace
        NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
            self, "appActivated:", "NSWorkspaceDidActivateApplicationNotification", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "screensChanged:", "NSApplicationDidChangeScreenParametersNotification", None)
        timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(0.5, self, "tick:", None, True)
        NSRunLoop.currentRunLoop().addTimer_forMode_(timer, NSRunLoopCommonModes)
        self.timer = timer


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)
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
    store.start_ticker()
    BrowserPoller(store).start()
    LocalScanner(store).start()
    ClientScanner(store, enabled=lambda: ctrl.cfg.get("clients_on", True)).start()
    ctrl.quota = QuotaPoller(store, lambda: ctrl.cfg, SUPPORT)
    ctrl.quota.start()
    ctrl.build()
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
