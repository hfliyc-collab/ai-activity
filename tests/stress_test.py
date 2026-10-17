#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后端压力测试：python tests/stress_test.py

1 接口吞吐与延迟   多线程混合请求（扩展探测、流式状态、额度、hooks、畸形请求、读取状态）
2 规模             大量标签页 / Agent / 客户端 / 账号时生成视图的耗时与数据量
3 并发             多线程同时写入、读取、定时检查，统计异常
4 模糊测试         随机结构的输入喂给所有入口，统计未捕获的异常
5 内存             反复打开关闭标签页，检查是否回收
6 判断准确率       随机模拟生成过程（含不规则上报、思考停顿、页面加载噪声、滚动历史）
7 客户端读取       大型无障碍树的汇总耗时
"""
import json
import os
import random
import statistics
import sys
import threading
import time
import tracemalloc
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from clients import summarize  # noqa: E402
from core import Store, make_server  # noqa: E402
from island_layout import layout as fit_island, pill_frame  # noqa: E402

SITES = ["https://claude.ai/chat/", "https://chatgpt.com/c/", "https://gemini.google.com/app/", "https://chat.deepseek.com/a/chat/s/",
         "https://www.kimi.com/chat/", "https://www.doubao.com/chat/", "https://chat.qwen.ai/c/", "https://yuanbao.tencent.com/chat/",
         "https://yiyan.baidu.com/chat/", "https://chatglm.cn/main/"]
results = {}


def section(name):
    print(f"\n━━ {name}")


def report(key, ok, detail):
    results[key] = ok
    print(f"  {'✓' if ok else '✗'} {detail}")


# ---------------------------------------------------------------- 1
def http_load(port=47901, threads=32, per_thread=400):
    section("1 接口吞吐与延迟")
    store = Store()
    make_server(store, port=port)
    store.start_ticker()
    url = f"http://127.0.0.1:{port}"
    lat, errors, bad_ok, lock = [], [], [0], threading.Lock()
    rnd = random.Random(1)

    def body(i):
        r = rnd.random()
        tab = i % 300
        if r < 0.45:
            return "/event", {"session": f"ext:{tab}", "tab_id": tab, "kind": "probe", "url": SITES[tab % 10] + str(tab),
                              "title": f"会话 {tab}", "probe": {"busy": rnd.random() < .3, "n": rnd.randint(0, 5000), "count": 3, "est": 900}}
        if r < 0.6:
            return "/event", {"session": f"ext:{tab}", "url": SITES[tab % 10] + str(tab), "state": rnd.choice(["working", "done"]),
                              "tokens_out": rnd.randint(0, 9000), "est": True}
        if r < 0.65:
            return "/event", {"session": "ext:q", "kind": "quota", "orgs": [{"uuid": "o1", "name": "K", "usage": {"five_hour": {"utilization": rnd.random() * 100}}}]}
        if r < 0.8:
            return "/event", {"session": f"claude-code:s{tab % 40}", "source": "claude-code", "state": rnd.choice(["working", "waiting", "done"]),
                              "tokens_add": 10, "title": "proj"}
        if r < 0.9:
            return "/state", None
        return "/event", "BAD"

    def worker(t):
        for i in range(per_thread):
            path, data = body(t * per_thread + i)
            t0 = time.perf_counter()
            try:
                if data is None:
                    urllib.request.urlopen(url + path, timeout=10).read()
                else:
                    raw = b"{not json" if data == "BAD" else json.dumps(data).encode()
                    req = urllib.request.Request(url + path, data=raw, headers={"Content-Type": "application/json"})
                    try:
                        urllib.request.urlopen(req, timeout=10).read()
                        if data == "BAD":
                            with lock:
                                bad_ok[0] += 1
                    except urllib.error.HTTPError as e:
                        if not (data == "BAD" and e.code == 400):
                            raise
                with lock:
                    lat.append(time.perf_counter() - t0)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append(repr(e)[:80])

    t0 = time.perf_counter()
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    dur = time.perf_counter() - t0
    n = threads * per_thread
    lat.sort()
    p50, p99 = lat[len(lat) // 2] * 1000, lat[int(len(lat) * .99)] * 1000
    report("http_errors", not errors, f"{n} 个请求，{threads} 个并发线程：失败 {len(errors)} 个" + (f"（如 {errors[0]}）" if errors else ""))
    report("http_bad_rejected", bad_ok[0] == 0, f"畸形请求全部被拒绝（误收 {bad_ok[0]} 个）")
    report("http_speed", n / dur > 300 and p99 < 250, f"吞吐 {n / dur:.0f} 次/秒，延迟 p50 {p50:.1f} ms，p99 {p99:.1f} ms")
    v = store.view()
    report("http_state_sane", len(v["rows"]) + len(v["idle"]) <= 300 + 40, f"结束后汇总：{len(v['rows'])} 行任务，{len(v['idle'])} 个已打开")


# ---------------------------------------------------------------- 2
def scale():
    section("2 规模")
    s, now = Store(), time.time()
    for i in range(500):
        s.apply_ext_event({"session": f"ext:{i}", "tab_id": i, "kind": "probe", "url": SITES[i % 10] + str(i), "title": f"会话{i}",
                           "probe": {"busy": i % 3 == 0, "n": 100 + i, "count": 2, "est": 50}}, now - 1)
        s.apply_ext_event({"session": f"ext:{i}", "tab_id": i, "kind": "probe", "url": SITES[i % 10] + str(i),
                           "probe": {"busy": i % 3 == 0, "n": 300 + i, "count": 2, "est": 120}}, now)
    for i in range(200):
        s.apply_agent_event({"session": f"claude-code:{i}", "source": "claude-code", "state": "working", "title": "p", "subtitle": "任务"}, "hook", now)
    s.on_clients([{"cid": "kimi-app", "pid": i, "title": "Kimi", "probe": {"busy": True, "n": 10, "count": 1, "est": 5}} for i in range(50)], now)
    s.apply_quota([{"id": f"a{i}", "provider": "claude", "name": f"账号{i}", "windows": [{"key": "five_hour", "label": "5 小时", "util": i * 5}]} for i in range(20)])
    times = []
    for _ in range(30):
        t0 = time.perf_counter()
        v = s.view()
        times.append(time.perf_counter() - t0)
    size = len(json.dumps(v, ensure_ascii=False).encode())
    avg, mx = statistics.mean(times) * 1000, max(times) * 1000
    report("scale_view", mx < 100, f"500 标签页 + 200 Agent + 50 客户端 + 20 账号：生成视图平均 {avg:.1f} ms，最慢 {mx:.1f} ms，数据 {size / 1024:.0f} KB")


# ---------------------------------------------------------------- 3
def concurrency(seconds=8):
    section("3 并发")
    s, stop, errs = Store(), threading.Event(), []

    def guard(fn):
        def run():
            r = random.Random()
            while not stop.is_set():
                try:
                    fn(r)
                except Exception as e:  # noqa: BLE001
                    errs.append(repr(e)[:120])
        return run

    def w_ext(r):
        i = r.randint(0, 80)
        if r.random() < .05:
            s.apply_ext_event({"session": f"ext:{i}", "state": "remove"})
        else:
            s.apply_ext_event({"session": f"ext:{i}", "tab_id": i, "kind": "probe", "url": SITES[i % 10] + str(r.randint(0, 3)),
                               "probe": {"busy": r.random() < .4, "n": r.randint(0, 900), "count": r.randint(0, 4), "est": 9}})

    def w_agent(r):
        s.apply_agent_event({"session": f"cursor:{r.randint(0, 30)}", "source": "cursor", "state": r.choice(["working", "done", "remove"]), "tokens_add": 3})

    def w_client(r):
        s.on_clients([{"cid": r.choice(["kimi-app", "doubao-app"]), "pid": p, "probe": {"busy": r.random() < .5, "n": r.randint(0, 99), "count": 1, "est": 1}}
                      for p in range(r.randint(0, 6))])

    def w_quota(r):
        s.apply_quota([{"id": f"q{r.randint(0, 5)}", "provider": "claude", "windows": [{"key": "five_hour", "util": r.random() * 100}]}])
        s.set_prefs({"order": [f"q{i}" for i in r.sample(range(6), 6)], "hidden": [], "primary": "q1"})

    def r_view(r):
        json.dumps(s.view())
        s.tick()

    fns = [w_ext] * 4 + [w_agent] * 2 + [w_client, w_quota] + [r_view] * 2
    ts = [threading.Thread(target=guard(f)) for f in fns]
    [t.start() for t in ts]
    time.sleep(seconds)
    stop.set()
    [t.join() for t in ts]
    report("concurrency", not errs, f"{len(ts)} 个线程同时读写 {seconds} 秒：异常 {len(errs)} 个" + (f"（如 {errs[0]}）" if errs else ""))


# ---------------------------------------------------------------- 4
def fuzz(n=30000):
    section("4 模糊测试")
    r = random.Random(7)
    atoms = [None, True, 0, -1, 1e308, float("nan"), "", "x" * 5000, "ext:1", "claude-code:1", [], {}, "working", "done", "remove",
             "probe", "quota", "https://claude.ai/chat/1", "javascript:alert(1)", "\u0000", "😀"]

    def val(d=0):
        k = r.random()
        if d > 3 or k < .5:
            return r.choice(atoms)
        if k < .75:
            return [val(d + 1) for _ in range(r.randint(0, 4))]
        return {r.choice(["session", "state", "url", "kind", "probe", "orgs", "usage", "n", "busy", "tokens_out", "tokens_add",
                          "started_at", "title", "uuid", "five_hour", "utilization", "cid", "pid"]): val(d + 1) for _ in range(r.randint(0, 6))}

    s, crashes = Store(), {}
    for _ in range(n):
        ev = val()
        if not isinstance(ev, dict):
            ev = {"session": r.choice(["ext:1", "claude-code:2", "x"]), "x": ev}
        ev.setdefault("session", r.choice(["ext:1", "ext:2", "cursor:3"]))
        for name, fn in (("ext", lambda: s.apply_ext_event(ev)), ("agent", lambda: s.apply_agent_event(ev)),
                         ("quota", lambda: s.apply_quota(val())), ("clients", lambda: s.on_clients(val() if r.random() < .5 else [ev])),
                         ("view", lambda: json.dumps(s.view(), allow_nan=False))):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                crashes.setdefault(name, (0, repr(e)[:100]))
                crashes[name] = (crashes[name][0] + 1, crashes[name][1])
    report("fuzz", not crashes, f"{n} 组随机输入 × 5 个入口：" + ("全部正常处理" if not crashes else
                                                              "；".join(f"{k} 出错 {c} 次（{m}）" for k, (c, m) in crashes.items())))
    return crashes


# ---------------------------------------------------------------- 5
def memory(rounds=20000):
    section("5 内存")
    s = Store()
    tracemalloc.start()
    base = None
    for i in range(rounds):
        tab = i % 200
        s.apply_ext_event({"session": f"ext:{tab}", "tab_id": tab, "kind": "probe", "url": SITES[tab % 10] + str(i), "probe": {"n": 1, "count": 1}})
        if i % 2:
            s.apply_ext_event({"session": f"ext:{tab}", "state": "remove"})
        s.on_clients([{"cid": "kimi-app", "pid": i, "probe": None}])
        s.apply_agent_event({"session": f"cursor:{i}", "source": "cursor", "state": "done"}, now=time.time() - 4000)
        if i == 2000:
            s.view()
            base = tracemalloc.get_traced_memory()[0]
    s.view()
    cur = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    grow = (cur - base) / 1024
    report("memory", len(s.web) <= 200 and len(s.clients) <= 1 and len(s.agents) < 50 and grow < 2048,
           f"{rounds} 次打开/关闭/切换：标签页 {len(s.web)}，客户端 {len(s.clients)}，Agent {len(s.agents)}，内存增长 {grow:.0f} KB")


# ---------------------------------------------------------------- 6
def accuracy(sessions=400, seed=3):
    """模拟时间里同时运行定时检查（和真实程序一样每 0.5 秒一次），避免只在上报时才检查而掩盖问题。"""
    section("6 判断准确率（模拟时间，含每 0.5 秒的定时检查）")
    cases = [("有停止按钮的网页", True, False, 0.0), ("只能看字数的网页", False, False, 0.0),
             ("桌面客户端（有停止按钮）", True, True, 0.0),
             ("只能看字数 + 中途静默思考 3–10 秒（已知局限）", False, False, 0.25)]
    for kind, busy_capable, app, silent_p in cases:
        r = random.Random(seed)
        fin, s = [], Store(on_finish=lambda row: fin.append(row["key"]))
        clock = [1000.0]
        early = missed = dup = noise_start = 0

        def advance(dt):
            end = clock[0] + dt
            while clock[0] + 0.5 < end:
                clock[0] += 0.5
                s.tick(clock[0])
            clock[0] = end

        for k in range(sessions):
            key_url = f"https://chat.deepseek.com/a/chat/s/{k}"
            n, cnt = 200, 3

            def probe(busy, n, cnt):
                p = {"busy": busy, "n": n, "count": cnt, "est": n // 2}
                if app:
                    s.on_clients([{"cid": "kimi-app", "pid": k, "probe": p}], clock[0])
                else:
                    s.apply_ext_event({"session": f"ext:{k}", "tab_id": k, "kind": "probe", "url": key_url, "probe": p}, clock[0])
                s.tick(clock[0])
            for _ in range(r.randint(0, 3)):           # 页面加载 / 滚动历史的噪声
                cnt += r.randint(0, 3) if not app else 0
                n += r.randint(0, 40) if app else 0
                probe(False, n, cnt)
                advance(r.uniform(0.3, 1.0))
            key = f"client:kimi-app:{k}" if app else "web:" + key_url.split("//")[1]
            obj = s.clients.get(key) if app else s.web.get(key)
            if obj and obj.task.state == "working":
                noise_start += 1
            before = len(fin)
            cnt += 1
            t_end = clock[0] + r.uniform(3, 40)
            silent_at = clock[0] + r.uniform(1, 2) if r.random() < silent_p else None
            while clock[0] < t_end:
                n += r.randint(5, 60)
                probe(busy_capable, n, cnt)
                gap = r.uniform(0.2, 1.2) + (r.uniform(0, 1.0) if r.random() < .08 else 0)
                if silent_at and clock[0] >= silent_at:
                    gap, silent_at = r.uniform(3, 10), None
                advance(gap)
            split = len(fin) > before
            for _ in range(8):
                probe(False, n, cnt)
                advance(r.uniform(0.4, 1.4))
            advance(12)                                 # 等待可能延后的提醒
            got = len(fin) - before
            if split and got >= 2:
                early += 1
            elif got == 0:
                missed += 1
            elif got > 1:
                dup += 1
        known = "已知局限" in kind
        ok = known or (early <= sessions * .02 and missed <= sessions * .02 and dup == 0 and noise_start <= sessions * .02)
        report(f"acc_{kind}", ok, f"{kind}：{sessions} 次生成，提前判完成 {early}，漏判 {missed}，重复提醒 {dup}，噪声误开始 {noise_start}")


# ---------------------------------------------------------------- 7
def client_tree():
    section("7 客户端读取")
    nodes = []
    for i in range(1500):
        nodes.append({"role": "AXStaticText", "value": "这是一段很长的中文回复内容 with English " * 3})
        if i % 50 == 0:
            nodes.append({"role": "AXButton", "title": "复制", "desc": ""})
    nodes.insert(700, {"role": "AXButton", "title": "停止生成", "desc": ""})
    t0 = time.perf_counter()
    for _ in range(50):
        p = summarize(nodes)
    ms = (time.perf_counter() - t0) / 50 * 1000
    report("client_summary", p["busy"] and ms < 20, f"1500 个节点的窗口：汇总 {ms:.2f} ms，识别到停止按钮：{p['busy']}，只取最近 {p['count']} 段文字")


# ---------------------------------------------------------------- 8
def island_fit(n=30000, seed=11):
    """随机菜单栏 + 模拟测量失败，检查三条硬性规则：
    1 岛永远不伸到菜单栏下方   2 永远不遮挡任何图标或菜单（包括没测到的）   3 放不下时只占刘海本身"""
    section("8 灵动岛避让（随机菜单栏 + 模拟测量失败）")
    r = random.Random(seed)
    covered = below = outside = 0
    counts, fails = {}, {"左侧没测到": 0, "右侧没测到": 0, "两侧都没测到": 0}
    TOP, IH = 1000, 37
    for _ in range(n):
        sw = r.choice([1440, 1512, 1728, 1800, 2560])
        nw = r.choice([0, 180, 185, 200])
        cx = sw / 2
        nl, nr = cx - nw / 2, cx + nw / 2
        menus = [(0, r.uniform(80, cx - 2))]
        right, x = [], (r.uniform(nr, nr + 300) if r.random() < .6 else nr + r.uniform(0, 12))
        while x < sw - 20:
            w = r.uniform(18, 140)
            right.append((x, min(sw, x + w)))
            x += w + r.uniform(4, 14)
        lk, rk = r.random() < .75, r.random() < .75
        key = "两侧都没测到" if not lk and not rk else "左侧没测到" if not lk else "右侧没测到" if not rk else None
        if key:
            fails[key] += 1
        seen = (menus if lk else []) + (right if rk else [])
        lay = fit_island(nl, nr, 0, sw, seen, left_known=lk, right_known=rk)
        counts[lay["mode"]] = counts.get(lay["mode"], 0) + 1
        fr = pill_frame(lay, nl, nr, TOP, IH)
        if fr is None:
            continue
        px, py, pw, ph = fr
        if py < TOP - IH - 0.01 or ph > IH + 0.01:
            below += 1
        if lay["mode"] == "none" and (px < nl - 0.01 or px + pw > nr + 0.01):
            outside += 1
        real = menus + right
        if any(a1 > a0 and any(o0 < a1 and o1 > a0 for o0, o1 in real) for a0, a1 in [(px, min(nl, px + pw)), (max(nr, px), px + pw)]):
            covered += 1
    report("island_fit", covered == 0 and below == 0 and outside == 0,
           f"{n} 种随机菜单栏（其中测量失败 {sum(fails.values())} 次）：遮挡图标 {covered} 次，伸到菜单栏下方 {below} 次，"
           f"放不下时超出刘海 {outside} 次；布局分布 {counts}")


if __name__ == "__main__":
    t0 = time.time()
    http_load()
    scale()
    concurrency()
    fuzz()
    memory()
    accuracy()
    client_tree()
    island_fit()
    bad = [k for k, v in results.items() if not v]
    print(f"\n总计 {len(results)} 项，通过 {len(results) - len(bad)} 项，用时 {time.time() - t0:.0f} 秒" + (f"；未通过：{', '.join(bad)}" if bad else ""))
    sys.exit(1 if bad else 0)
