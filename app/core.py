# -*- coding: utf-8 -*-
"""聚合层：把浏览器轮询、Chrome 扩展、hooks、本地扫描的数据合并成统一的任务列表，
并生成给界面使用的视图数据。不依赖 macOS，可以单独测试。"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from sites import AGENTS, APPS, SITE_BY_ID, glyph_of, site_for_url

ACTIVE = ("working", "waiting")
FINISHED = ("done", "error", "stopped")
STATES = ACTIVE + FINISHED + ("idle",)
RECENT_SEC = 10 * 60          # 结束后在“刚完成”里停留的时间
AGENT_EXPIRE = 30 * 60
STALE_SEC = 180
MIN_NOTIFY_SEC = 3            # 短于这个时长的“任务”不弹通知（避免页面加载时误报）

TITLE_SUFFIXES = [" - Claude", " | Claude", " - ChatGPT", " - Gemini", " - Google Gemini",
                  " - DeepSeek", " - Kimi", " - 豆包", " - Grok", " - Qwen", " | Perplexity"]


def norm_url(u):
    s = urlsplit(u or "")
    return (s.netloc + s.path).rstrip("/").lower()


def clean_title(t, label=""):
    t = (t or "").strip()
    for suf in TITLE_SUFFIXES:
        if t.endswith(suf):
            t = t[: -len(suf)].strip()
    return "" if t.lower() in (label.lower(), "new chat", "新对话", "") else t


def _num(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


class Task:
    def __init__(self, key, kind, site):
        self.key, self.kind, self.site = key, kind, site
        self.label = ""
        self.title = self.subtitle = self.place = self.model = self.note = ""
        self.url = self.browser = ""
        self.state = "idle"
        self.tokens_out = self.tokens_in = None
        self.est = True
        self.util = None
        self.started = self.finished = None
        self.updated = time.time()
        self.flash_until = 0.0

    def apply(self, ev, now):
        """应用一条状态事件；返回 True 表示任务刚刚结束（用于通知）。"""
        prev = self.state
        st = ev.get("state") or prev
        if st not in STATES:
            st = prev
        if st in ACTIVE and prev not in ACTIVE:
            sa = ev.get("started_at")
            self.started = sa / 1000 if isinstance(sa, (int, float)) and sa > 1e12 else now
            self.finished = None
            self.tokens_out = self.tokens_in = None
            self.est, self.note, self.util = True, "", None
        for k in ("title", "subtitle", "model", "label"):
            if ev.get(k):
                setattr(self, k, str(ev[k])[:160])
        if "note" in ev:
            self.note = str(ev["note"] or "")[:120]
        if _num(ev.get("tokens_out")) is not None:
            self.tokens_out = _num(ev["tokens_out"])
        if _num(ev.get("tokens_add")):
            self.tokens_out = (self.tokens_out or 0) + _num(ev["tokens_add"])
        if _num(ev.get("tokens_in")) is not None:
            self.tokens_in = _num(ev["tokens_in"])
        if "est" in ev:
            self.est = bool(ev["est"])
        if isinstance(ev.get("util"), (int, float)):
            self.util = float(ev["util"])
        self.state, self.updated = st, now
        if self.started is None and st != "idle":
            sa = ev.get("started_at")
            self.started = sa / 1000 if isinstance(sa, (int, float)) and sa > 1e12 else now
        if st in FINISHED and prev not in FINISHED:
            self.finished = ev.get("finished_at") or now
            if prev in ACTIVE:
                self.flash_until = now + 6
                return True
        return False

    def elapsed(self, now):
        if self.started is None:
            return 0.0
        return max(0.0, (self.finished or now) - self.started)

    def row(self, now):
        glyph, tint = glyph_of(self.site)
        el = self.elapsed(now)
        stale = self.state == "working" and now - self.updated > STALE_SEC
        tps = None
        if self.state == "working" and self.tokens_out and el > 2:
            tps = round(self.tokens_out / el, 1)
        return {
            "key": self.key, "site": self.site, "label": self.label, "glyph": glyph, "tint": tint,
            "title": self.title, "subtitle": self.subtitle, "place": self.place,
            "state": self.state, "stale": stale, "elapsed": round(el, 1),
            "since_update": round(now - self.updated, 1),
            "finished_ago": round(now - self.finished, 1) if self.finished else None,
            "tokens": self.tokens_out, "est": self.est, "tps": tps, "ctx": self.tokens_in,
            "util": self.util, "model": self.model, "note": self.note,
            "flash": now < self.flash_until, "clickable": bool(self.url or self.kind == "app"),
        }


class WebTab:
    """单个网页标签的状态机。按时间判断，兼容固定轮询（macOS）和不定期上报（浏览器扩展）。"""
    QUIET = 2.4                    # 不忙且字数不再增长这么久，视为完成

    def __init__(self, key, site):
        self.task = Task(key, "web", site["id"])
        self.task.label = site["label"]
        self.last = None              # 上一次探测 (n, count, est)
        self.base = None              # 本轮开始前的 (n, count, est)
        self.calm = None              # 最近一次“没在增长”时的数值
        self.grow_at = []             # 最近几次增长的时间
        self.last_active = 0.0
        self.last_busy = False
        self.last_report = 0.0
        self.seen_by_poll = False
        self.via_ext = False
        self.tab_id = None
        self.ext_until = 0.0          # 扩展的流式数据在此之前接管状态
        self.probe_ok = False

    def on_probe(self, p, now):
        """返回需要应用到 task 的事件，或 None。"""
        n, cnt, est, busy = int(p.get("n") or 0), int(p.get("count") or 0), \
            int(p.get("est") or 0), bool(p.get("busy"))
        prev = self.last
        grew_text = prev is not None and n > prev[0] and cnt == prev[1] and prev[1] > 0
        grew_new = prev is not None and cnt > prev[1] and (busy or prev[1] > 0)
        grew = grew_text or grew_new
        self.last, self.last_busy, self.last_report = (n, cnt, est), busy, now
        t = self.task
        if grew_text or (grew_new and busy):
            self.grow_at = [x for x in self.grow_at if now - x < 4] + [now]
        if not grew and t.state not in ACTIVE:
            self.calm = self.last
        if busy or grew:
            self.last_active = now
        if now < self.ext_until:
            return None
        if t.state not in ACTIVE:
            recent = [x for x in self.grow_at if now - x < 4]
            if busy or len(recent) >= 2:
                self.base = (prev if busy else (self.calm or prev)) or (0, 0, 0)
                self.grow_at = []
                return {"state": "working", "tokens_out": self._tokens(), "est": True}
            return None
        if busy or grew:
            return {"state": "working", "tokens_out": self._tokens(), "est": True}
        return self.check_done(now)

    def check_done(self, now):
        if self.task.state == "working" and self.last is not None and not self.last_busy \
                and now - self.last_active >= self.QUIET and now >= self.ext_until:
            self.grow_at = []
            return {"state": "done", "tokens_out": self._tokens(), "est": True}
        return None

    def _tokens(self):
        n, cnt, est = self.last
        b = self.base or (0, 0, 0)
        return est if cnt != b[1] else max(0, est - b[2])


class Store:
    def __init__(self, on_finish=None):
        self.lock = threading.RLock()
        self.web = {}            # key → WebTab
        self.agents = {}         # key → Task
        self.ext_tabs = {}       # 扩展 tabId → web key
        self.hook_at = {}        # agent key → 最近一次 hook 事件时间
        self.running_apps = set()
        self.notices = {}
        self.on_finish = on_finish
        self.started = time.time()
        self.ext_seen = 0.0           # 最近一次收到浏览器扩展消息
        self.running_browsers = set() # Windows：正在运行的 Chromium 浏览器
        self.commands = []            # 发给浏览器扩展的指令（切换标签页）

    def start_ticker(self, interval=0.5):
        def loop():
            while True:
                time.sleep(interval)
                try:
                    self.tick()
                except Exception:
                    pass
        threading.Thread(target=loop, daemon=True).start()

    def tick(self, now=None):
        """时间驱动的检查：生成结束、长时间没有上报的扩展标签页。"""
        now = now or time.time()
        with self.lock:
            for key in list(self.web):
                wt = self.web[key]
                ev = wt.check_done(now)
                if ev and wt.task.apply(ev, now):
                    self._finished(wt.task, now)
                if wt.via_ext and not wt.seen_by_poll and wt.task.state not in ACTIVE \
                        and now - max(wt.last_report, wt.task.updated) > 150:
                    del self.web[key]

    def set_running_browsers(self, names):
        with self.lock:
            self.running_browsers = set(names)

    def take_commands(self):
        with self.lock:
            cmds, self.commands = self.commands, []
            return cmds

    # ---- 通知/权限提示
    def set_notice(self, name, kind, detail=""):
        with self.lock:
            self.notices[name] = {"name": name, "kind": kind, "detail": detail}

    def clear_notice(self, name):
        with self.lock:
            self.notices.pop(name, None)

    def _finished(self, task, now):
        if self.on_finish and task.elapsed(now) >= MIN_NOTIFY_SEC:
            try:
                self.on_finish(task.row(now))
            except Exception:
                pass

    # ---- 浏览器轮询
    def on_browser_poll(self, data, now, skipped=()):
        with self.lock:
            polled_browsers = set(data.get("status", {}))
            seen = set()
            for rec in data.get("tabs", []):
                site = SITE_BY_ID.get(rec.get("site"))
                if not site:
                    continue
                key = "web:" + norm_url(rec["url"])
                seen.add(key)
                wt = self.web.get(key)
                if wt is None:
                    wt = self.web[key] = WebTab(key, site)
                wt.seen_by_poll = True
                t = wt.task
                t.url, t.browser, t.place = rec["url"], rec["browser"], rec["browser"]
                title = clean_title((rec.get("probe") or {}).get("title") or rec.get("title"),
                                    site["label"])
                if title:
                    t.title = title
                p = rec.get("probe")
                if p and "err" not in p:
                    wt.probe_ok = True
                    ev = wt.on_probe(p, now)
                    if ev and t.apply(ev, now):
                        self._finished(t, now)
                elif not rec.get("skipped"):
                    wt.probe_ok = False
            for key in list(self.web):
                wt = self.web[key]
                if key not in seen and wt.seen_by_poll and wt.task.browser in polled_browsers \
                        and now > wt.ext_until:
                    del self.web[key]
                elif key not in seen and wt.task.browser and wt.task.browser not in polled_browsers \
                        and wt.seen_by_poll:
                    del self.web[key]   # 浏览器已退出

    def any_web_active(self):
        with self.lock:
            return any(w.task.state in ACTIVE for w in self.web.values())

    # ---- Chrome 扩展事件（session = "ext:<tabId>"）
    def apply_ext_event(self, ev, now=None):
        now = now or time.time()
        with self.lock:
            self.ext_seen = now
            tab_id = ev["session"]
            if ev.get("state") == "remove":
                key = self.ext_tabs.pop(tab_id, None)
                if key and key in self.web and not self.web[key].seen_by_poll:
                    del self.web[key]
                return
            if ev.get("kind") == "hello":
                return
            url = ev.get("url") or ""
            site = site_for_url(url)
            if not site:
                return
            key = "web:" + norm_url(url)
            old = self.ext_tabs.get(tab_id)
            if old and old != key and old in self.web and not self.web[old].seen_by_poll:
                moved = self.web.pop(old)          # 同一标签页换了网址（新对话发送后）：保留状态
                if key not in self.web:
                    moved.task.key = key
                    moved.task.url = url
                    self.web[key] = moved
            self.ext_tabs[tab_id] = key
            wt = self.web.get(key)
            if wt is None:
                wt = self.web[key] = WebTab(key, site)
            wt.via_ext = True
            wt.tab_id = ev.get("tab_id", wt.tab_id)
            t = wt.task
            if not wt.seen_by_poll:
                t.browser = t.place = ev.get("browser") or t.browser or "Chrome"
                t.url = url
            title = clean_title(ev.get("title"), site["label"])
            if ev.get("kind") == "probe":
                wt.probe_ok = True
                if title:
                    t.title = title
                e2 = wt.on_probe(ev.get("probe") or {}, now)
                if e2 and t.apply(e2, now):
                    self._finished(t, now)
                return
            wt.ext_until = now + 15
            ev = dict(ev)
            for k in ("kind", "probe", "tab_id", "browser", "url"):
                ev.pop(k, None)
            if title:
                ev["title"] = title
            else:
                ev.pop("title", None)
            if t.apply(ev, now):
                self._finished(t, now)

    # ---- hooks / 本地扫描
    def apply_agent_event(self, ev, origin="hook", now=None):
        now = now or time.time()
        with self.lock:
            key = str(ev["session"])
            if ev.get("state") == "remove":
                self.agents.pop(key, None)
                return
            src = ev.get("source") or key.split(":")[0]
            t = self.agents.get(key)
            if t is None:
                t = self.agents[key] = Task(key, "agent", src)
                t.label = (AGENTS.get(src) or {}).get("label") or ev.get("label") or src
            ev = dict(ev)
            if origin == "hook":
                self.hook_at[key] = now
            elif origin == "scanner":
                # hook 已报告结束，但扫描器看到的还是同一次写入：只更新数字，不改状态
                last_hook = self.hook_at.get(key, 0)
                if t.state in FINISHED and ev.get("state") in ACTIVE and \
                        (ev.get("finished_at") or now) - last_hook < 20 and now - last_hook < 20:
                    ev.pop("state", None)
                if t.state == "waiting" and ev.get("state") == "working" and now - last_hook < 600:
                    ev.pop("state", None)
            project = ev.pop("title", "") or ""
            prompt = ev.pop("subtitle", "") or ""
            if project:
                t.place = project
            if prompt:
                ev["title"] = prompt
            if t.apply(ev, now):
                self._finished(t, now)

    def set_running_apps(self, ids):
        with self.lock:
            self.running_apps = set(ids)

    # ---- 点击定位
    def target_of(self, key):
        with self.lock:
            if key in self.web:
                wt = self.web[key]
                if wt.seen_by_poll:
                    return ("tab", wt.task.browser, wt.task.url)
                if wt.tab_id is not None:
                    return ("ext", wt.tab_id)
                return None
            if key in self.agents:
                src = self.agents[key].site
                return ("app", "Cursor") if src == "cursor" else None
            if key.startswith("app:"):
                for a in APPS:
                    if a["id"] == key[4:] and a.get("open"):
                        return ("app", a["open"])
        return None

    # ---- 视图
    def queue_focus(self, tab_id):
        with self.lock:
            self.commands.append({"type": "focus", "tab": tab_id})

    def view(self, now=None):
        now = now or time.time()
        self.tick(now)
        with self.lock:
            rows, idle = [], []
            for wt in self.web.values():
                t = wt.task
                recent = t.state in FINISHED and t.finished and now - t.finished < RECENT_SEC
                if t.state in ACTIVE or recent:
                    rows.append(t.row(now))
                else:
                    g, tint = glyph_of(t.site)
                    idle.append({"key": t.key, "label": t.label, "glyph": g, "tint": tint,
                                 "place": t.browser, "title": t.title,
                                 "watch": wt.probe_ok or now < wt.ext_until + 600})
            for key in list(self.agents):
                t = self.agents[key]
                if t.state not in ACTIVE and now - t.updated > AGENT_EXPIRE:
                    del self.agents[key]
                    continue
                recent = t.state in FINISHED and t.finished and now - t.finished < RECENT_SEC
                if t.state in ACTIVE or recent:
                    r = t.row(now)
                    r["clickable"] = t.site == "cursor"
                    rows.append(r)
            shown_agents = {self.agents[k].site for k in self.agents}
            for a in APPS:
                if a["id"] in self.running_apps and a["id"] not in shown_agents:
                    g, tint = glyph_of(a["id"])
                    idle.append({"key": "app:" + a["id"], "label": a["label"], "glyph": g,
                                 "tint": tint, "place": "应用", "title": "", "watch": a["id"] in AGENTS})
            rows.sort(key=lambda r: (r["state"] not in ACTIVE,
                                     -(r["elapsed"] if r["state"] in ACTIVE else 0),
                                     r["finished_ago"] or 0))
            working = [r for r in rows if r["state"] in ACTIVE]
            return {
                "rows": rows, "idle": idle,
                "notices": [n for k, n in self.notices.items() if not k.startswith("_")] + (
                    [{"name": " / ".join(sorted(self.running_browsers)), "kind": "ext"}]
                    if self.running_browsers and now - self.ext_seen > 20 and now - self.started > 8 else []),
                "summary": {"working": len(working),
                            "tps": round(sum(r["tps"] or 0 for r in working), 1),
                            "tokens": sum(r["tokens"] or 0 for r in rows)},
                "now": now,
            }


# ---------------------------------------------------------------- 本机 HTTP 接口
def make_server(store, host="127.0.0.1", port=47823, ui_dir=None, on_action=None):
    """本机接口：
    POST /event   浏览器扩展、hooks、任何工具推送状态（扩展收到的回复里带待执行的指令）
    GET  /state   当前汇总数据
    GET  /        界面（Windows 版窗口直接加载这里）
    POST /action  界面上的操作（点击条目、窗口高度）
    """
    import mimetypes
    import os

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body=b"", ctype="application/json"):
            self.send_response(code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self):
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(min(n, 256 * 1024)) or b"{}")
            if not isinstance(data, dict):
                raise ValueError
            return data

        def do_OPTIONS(self):
            self._send(204)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path.startswith("/ping"):
                return self._send(200, b'{"ok":true}')
            if path.startswith("/state"):
                return self._send(200, json.dumps(store.view(), ensure_ascii=False).encode())
            if ui_dir and (path in ("/", "/ui", "/ui/") or path.startswith("/ui/")):
                name = "index.html" if path in ("/", "/ui", "/ui/") else path[4:]
                full = os.path.realpath(os.path.join(ui_dir, name))
                if full.startswith(os.path.realpath(ui_dir)) and os.path.isfile(full):
                    with open(full, "rb") as f:
                        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
                        if ctype.startswith("text/"):
                            ctype += "; charset=utf-8"
                        return self._send(200, f.read(), ctype)
            self._send(404)

        def do_POST(self):
            path = self.path.split("?")[0]
            try:
                data = self._json()
            except Exception:
                return self._send(400, b'{"ok":false}')
            if path.startswith("/action"):
                if on_action:
                    try:
                        on_action(data)
                    except Exception:
                        pass
                return self._send(200, b'{"ok":true}')
            if not path.startswith("/event") or not data.get("session"):
                return self._send(404)
            try:
                if str(data["session"]).startswith("ext:"):
                    store.apply_ext_event(data)
                    body = {"ok": True, "cmd": store.take_commands()}
                    return self._send(200, json.dumps(body).encode())
                store.apply_agent_event(data, origin="hook")
            except Exception:
                return self._send(400, b'{"ok":false}')
            self._send(200, b'{"ok":true}')

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
