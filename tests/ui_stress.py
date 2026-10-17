#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""界面与浏览器扩展压力测试（需要 playwright：pip install playwright && playwright install chromium）

1 界面渲染      80 个任务 + 15 个账号 + 30 个已打开，连续渲染 400 次：耗时、DOM 节点、内存是否增长
2 三种视图      侧边栏 / 弹出 / 灵动岛 在同样负载下无报错；灵动岛展开收起消息正确
3 设置页        切换模式、隐藏账号、设主账号、调整顺序、保存密钥、专注 —— 发出的消息正确
4 扩展端到端    真实扩展 + 8 个国产 AI 网站同时生成 + Claude 额度接口
"""
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from playwright.sync_api import sync_playwright  # noqa: E402

from core import Store, make_server  # noqa: E402

results = {}


def report(key, ok, detail):
    results[key] = ok
    print(f"  {'✓' if ok else '✗'} {detail}")


def fake_claude(port=8443):
    """本机 HTTPS 假 claude.ai：扩展的请求走真实网络路径（Playwright 的请求拦截对扩展内容脚本发出的请求无效）。"""
    d = tempfile.mkdtemp()
    cert, key = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert, "-days", "2",
                    "-subj", "/CN=claude.ai", "-addext", "subjectAltName=DNS:claude.ai"], capture_output=True, check=True)
    seen = {"cookie": None}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/organizations":
                seen["cookie"] = self.headers.get("Cookie")
                body, ct = json.dumps([{"uuid": "o1", "name": "Kevin's Organization"}]), "application/json"
            elif self.path == "/api/organizations/o1/usage":
                body, ct = json.dumps({"five_hour": {"utilization": 63, "resets_at": "2030-01-01T00:00:00Z"}, "seven_day": {"utilization": 41}}), "application/json"
            else:
                body, ct = "<title>周报 - Claude</title><div data-is-streaming='false'>x</div>", "text/html; charset=utf-8"
            b = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Set-Cookie", "sessionKey=test; Secure; Path=/")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    c.load_cert_chain(cert, key)
    srv.socket = c.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return seen


def big_store():
    s, now = Store(), time.time()
    sites = ["https://claude.ai/chat/", "https://chat.deepseek.com/a/chat/s/", "https://www.kimi.com/chat/", "https://www.doubao.com/chat/"]
    for i in range(110):
        u = sites[i % 4] + str(i)
        s.apply_ext_event({"session": f"ext:{i}", "tab_id": i, "kind": "probe", "url": u, "title": f"会话 {i}", "probe": {"busy": False, "n": 10, "count": 2, "est": 5}}, now - 2)
        if i < 60:
            s.apply_ext_event({"session": f"ext:{i}", "tab_id": i, "kind": "probe", "url": u, "probe": {"busy": True, "n": 400, "count": 3, "est": 200}}, now)
    for i in range(20):
        s.apply_agent_event({"session": f"claude-code:{i}", "source": "claude-code", "state": "working", "title": "proj", "subtitle": f"任务 {i}", "tokens_out": 100 * i}, "hook", now)
    s.apply_quota([{"id": f"claude:o{i}", "provider": "claude", "name": f"账号 {i}", "windows": [
        {"key": "five_hour", "label": "5 小时", "util": (i * 7) % 100, "resets_at": now + 3600}, {"key": "seven_day", "label": "本周", "util": 40}]} for i in range(15)])
    s.ui = {"companion": True}
    return s


def main():
    actions = []
    store = big_store()
    make_server(store, port=47911, ui_dir=os.path.join(ROOT, "app", "ui"), on_action=lambda a: actions.append(a))
    base = "http://127.0.0.1:47911"
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ---------------------------------------------------------- 1
        print("\n━━ 1 界面渲染")
        pg = b.new_page(viewport={"width": 340, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/?view=sidebar")
        pg.wait_for_timeout(1500)
        state = json.dumps(store.view())
        pg.evaluate("window.__S = " + state)
        res = pg.evaluate("""() => {
          const S = window.__S, times = [];
          const n0 = document.getElementsByTagName('*').length;
          const h0 = performance.memory ? performance.memory.usedJSHeapSize : 0;
          for (let i = 0; i < 400; i++) {
            const v = JSON.parse(JSON.stringify(S));
            v.rows.forEach((r, j) => { r.elapsed += i; r.tokens = (r.tokens || 0) + i * 7; r.state = (i + j) % 17 === 0 ? 'done' : r.state; });
            if (i % 50 === 0) v.rows = v.rows.slice(0, 40 + (i % 3) * 20);
            v.accounts.forEach((a) => a.windows.forEach((w) => { w.util = (w.util + i) % 100; }));
            const t = performance.now(); window.render(v); times.push(performance.now() - t);
          }
          window.render(S);
          const n1 = document.getElementsByTagName('*').length;
          const h1 = performance.memory ? performance.memory.usedJSHeapSize : 0;
          times.sort((a, b) => a - b);
          return { avg: times.reduce((a, b) => a + b) / times.length, p95: times[Math.floor(times.length * .95)], n0, n1, h0, h1 };
        }""")
        report("ui_render_speed", res["p95"] < 30, f"80 个任务 + 15 个账号 + 30 个已打开，连续 400 次刷新：平均 {res['avg']:.1f} ms，p95 {res['p95']:.1f} ms")
        report("ui_dom_leak", abs(res["n1"] - res["n0"]) < 50, f"DOM 节点 {res['n0']} → {res['n1']}（恢复到同样数据后应基本不变）")
        pg.evaluate("() => { if (window.gc) window.gc(); }")
        report("ui_errors", not errs, f"脚本错误 {len(errs)} 个" + (f"（{errs[0][:80]}）" if errs else ""))
        # ---------------------------------------------------------- 2
        print("\n━━ 2 三种视图")
        for view in ("popover", "island"):
            e2, pg2 = [], b.new_page(viewport={"width": 400, "height": 800})
            pg2.on("pageerror", lambda e: e2.append(str(e)))
            pg2.goto(base + f"/?view={view}&ih=37&ww=92&nw=190")
            pg2.wait_for_timeout(1500)
            if view == "island":
                actions.clear()
                pg2.hover("#isl")
                pg2.wait_for_timeout(300)
                pg2.mouse.move(5, 700)
                pg2.wait_for_timeout(300)
                pg2.click("#isl")
                pg2.wait_for_timeout(300)
                kinds = [(a.get("type"), a.get("on")) for a in actions if a.get("type", "").startswith("island")]
                ok = ("island-hover", True) in kinds and ("island-hover", False) in kinds and ("island-click", None) in kinds
                report("island_protocol", ok, f"灵动岛悬停 / 离开 / 点击消息：{kinds}")
                pct = pg2.inner_text(".wing.r .pct")
                report("island_primary", pct.endswith("%"), f"灵动岛右侧显示主账号额度：{pct}")
                modes_ok = True
                for mode in ("left", "right", "none", "wings"):
                    pg2.evaluate(f"window.islandLayout({{ih: 37, lw: 110, rw: 110, mode: '{mode}'}})")
                    vis = pg2.evaluate("""() => [...document.querySelectorAll('#isl .pct')].filter((e) => e.offsetParent !== null && e.textContent).length""")
                    hgt = pg2.evaluate("document.getElementById('isl').getBoundingClientRect().height")
                    modes_ok &= vis == (0 if mode == "none" else 1) and abs(hgt - 37) < 0.5
                report("island_modes", modes_ok, "四种布局：两侧 / 只左 / 只右各显示一次额度，只占刘海时不显示；高度始终等于菜单栏")
                pd = b.new_page(viewport={"width": 380, "height": 800})
                ed = []
                pd.on("pageerror", lambda e: ed.append(str(e)))
                pd.goto(base + "/?view=drop")
                pd.wait_for_timeout(1200)
                lines = pd.eval_on_selector_all(".qline", "els => els.length")
                report("drop_view", lines >= 10 and not ed, f"下拉面板：{lines} 个账号行，脚本错误 {len(ed)} 个")
            else:
                pg2.click("[data-sw='1']")
                pg2.wait_for_timeout(300)
                sw = [a for a in actions if a.get("type") == "settings" and "popover_account" in (a.get("patch") or {})]
                report("popover_switch", bool(sw), f"弹出视图切换账号 → {sw[-1]['patch'] if sw else '无消息'}")
            report(f"view_{view}_errors", not e2, f"{view} 视图脚本错误 {len(e2)} 个" + (f"（{e2[0][:80]}）" if e2 else ""))
        # ---------------------------------------------------------- 3
        print("\n━━ 3 设置页")
        e3, ps = [], b.new_page(viewport={"width": 620, "height": 900})
        ps.on("pageerror", lambda e: e3.append(str(e)))
        store.ui = {"mode": "island", "platform": "mac", "modes_available": ["island", "menubar", "sidebar"], "companion": True, "clients_on": True}
        ps.goto(base + "/ui/settings.html")
        ps.wait_for_timeout(1500)
        actions.clear()
        ps.click("[data-side='left']")
        ps.click("[data-mode='sidebar']")
        ps.locator("[data-show='claude:o3']").uncheck()
        ps.click("[data-primary='claude:o5']")
        ps.click("[data-mv='1'][data-i='0']")
        ps.fill("#k-deepseek", "sk-test-123")
        ps.click("[data-save='deepseek']")
        ps.click("label:has([data-ui='quota_claude_code']) span")
        ps.click("[data-focus='60']")
        ps.wait_for_timeout(500)
        got = {a["type"] + ":" + ",".join(sorted((a.get("patch") or {}).keys())) for a in actions}
        want = {"settings:mode", "settings:hidden", "settings:primary", "settings:order", "secret:", "settings:quota_claude_code", "focus:", "settings:island_side"}
        report("settings_actions", want <= got, f"设置页发出的消息：{sorted(got)}")
        sec = [a for a in actions if a["type"] == "secret"]
        report("settings_secret", sec and sec[0]["value"] == "sk-test-123" and ps.input_value("#k-deepseek") == "",
               "保存密钥后输入框清空，密钥只通过一次消息发送")
        order = [a for a in actions if "order" in (a.get("patch") or {})]
        report("settings_order", order and order[0]["patch"]["order"][:2] == ["claude:o1", "claude:o0"], f"下移第一个账号后的顺序：{order[0]['patch']['order'][:3] if order else None}")
        report("settings_errors", not e3, f"设置页脚本错误 {len(e3)} 个" + (f"（{e3[0][:80]}）" if e3 else ""))
        b.close()

    # ---------------------------------------------------------- 4
    print("\n━━ 4 扩展端到端（8 个国产网站同时生成 + Claude 额度）")
    fin = []
    s4 = Store(on_finish=lambda r: fin.append(r["label"]))
    make_server(s4, port=47823)
    s4.start_ticker()
    page = """<title>{t}</title><body><div id=log><div class="markdown-body">上一条回复</div></div><script>
      setTimeout(() => {{ const d = document.createElement('div'); d.className = 'markdown-body'; document.getElementById('log').append(d);
        const b = document.createElement('{tag}'); {attr}; b.textContent = '{label}'; document.body.append(b);
        let k = 0; const iv = setInterval(() => {{ d.textContent += '正在生成的内容，'; if (++k > {steps}) {{ clearInterval(iv); b.remove(); }} }}, 200); }}, 1200);
      </script></body>"""
    sites = [  # (网址, 标题, 停止按钮的写法)
        ("https://chat.deepseek.com/a/chat/s/1", "DeepSeek", "div", "b.className='ds-stop-btn'", "■"),
        ("https://www.kimi.com/chat/1", "Kimi", "button", "b.setAttribute('aria-label','停止生成')", ""),
        ("https://www.doubao.com/chat/1", "豆包", "div", "b.setAttribute('role','button')", "停止生成"),
        ("https://chat.qwen.ai/c/1", "Qwen", "button", "b.title='停止'", "■"),
        ("https://yuanbao.tencent.com/chat/1", "元宝", "div", "b.setAttribute('role','button')", "停止回答"),
        ("https://yiyan.baidu.com/chat/1", "文心一言", "span", "b.className='x'", ""),
        ("https://chatglm.cn/main/1", "智谱清言", "button", "b.className='stop-generating'", ""),
        ("https://xinghuo.xfyun.cn/desk/1", "讯飞星火", "button", "", "停止输出"),
    ]
    seen = fake_claude()
    with sync_playwright() as p:
        ext = os.path.join(ROOT, "extension")
        ctx = p.chromium.launch_persistent_context("/tmp/aiw-ui-stress", headless=True, channel="chromium", ignore_https_errors=True, args=[
            "--headless=new", "--disable-features=DisableLoadExtensionCommandLineSwitch", "--ignore-certificate-errors",
            "--host-resolver-rules=MAP claude.ai 127.0.0.1:8443",
            f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
        for i, (u, t, tag, attr, label) in enumerate(sites):
            host = u.split("/")[2]
            html = page.format(t=t, tag=tag, attr=attr, label=label, steps=20 + i * 3)
            ctx.route(f"https://{host}/**", (lambda h: lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=h))(html))
        pages = []
        for u, *_ in sites:
            pg = ctx.new_page()
            pg.goto(u)
            pages.append(pg)
        cp = ctx.new_page()
        cp.goto("https://claude.ai/chat/q")
        seen_working = set()
        t0 = time.time()
        while time.time() - t0 < 28:
            time.sleep(0.5)
            for r in s4.view()["rows"]:
                if r["state"] == "working":
                    seen_working.add(r["label"])
            if len(fin) >= len(sites):
                break
        labels = [t for _, t, *_ in sites]
        name = {"DeepSeek": "DeepSeek", "Kimi": "Kimi", "豆包": "豆包", "Qwen": "通义千问", "元宝": "元宝", "文心一言": "文心一言",
                "智谱清言": "智谱清言", "讯飞星火": "讯飞星火"}
        missing_w = [l for l in labels if name[l] not in seen_working]
        missing_f = [l for l in labels if name[l] not in fin]
        dups = sorted({x for x in fin if fin.count(x) > 1})
        report("ext_working", not missing_w, f"8 个网站识别到生成中：{8 - len(missing_w)}/8" + (f"（未识别：{missing_w}）" if missing_w else ""))
        report("ext_finished", not missing_f and not dups, f"完成提醒：{8 - len(missing_f)}/8，重复 {len(dups)}" + (f"（缺：{missing_f}）" if missing_f else ""))
        t1 = time.time()
        while time.time() - t1 < 8 and not [a for a in s4.view()["accounts"] if a["provider"] == "claude"]:
            time.sleep(0.5)
        print(f"  （Claude 页面打开后 {time.time() - t0:.1f} 秒，额度请求是否到达本机假服务器：{seen['cookie'] is not None}）")
        acc = [a for a in s4.view()["accounts"] if a["provider"] == "claude"]
        report("ext_quota", acc and acc[0]["headline"] == "63%" and acc[0]["name"] == "Kevin", f"Claude 额度：{[(a['name'], a['headline']) for a in acc]}")
        ctx.close()

    bad = [k for k, v in results.items() if not v]
    print(f"\n总计 {len(results)} 项，通过 {len(results) - len(bad)} 项" + (f"；未通过：{', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
