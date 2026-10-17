# -*- coding: utf-8 -*-
"""AI 额度。

来源                          方式                                         默认
Claude 订阅（网页 / 桌面版共用） 已登录的 claude.ai 页面在页面内读取自己的用量   自动
Claude Code 订阅               读取本机 Claude Code 登录信息，查询订阅用量      关闭（需在设置中开启）
DeepSeek / Kimi API 余额       使用你填写的 API Key 调用官方余额接口           填写后开启

所有请求只在本机发出，结果只显示在本机窗口；任何失败都显示为“出错”，不会编造数字。
"""
import json
import math
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

CLAUDE_WINDOWS = {
    "five_hour": "5 小时", "seven_day": "本周", "seven_day_opus": "本周 Opus",
    "seven_day_sonnet": "本周 Sonnet", "seven_day_oauth_apps": "本周 · 应用",
}


def _ts(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) / (1000 if v > 1e12 else 1) if math.isfinite(v) else None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def parse_claude_usage_windows(usage):
    """{"five_hour": {"utilization": 23, "resets_at": "..."}, ...} → 窗口列表（百分比 0–100）。"""
    out = []
    if not isinstance(usage, dict):
        return out
    for key, w in usage.items():
        if not isinstance(key, str) or not isinstance(w, dict):
            continue
        u = w.get("utilization")
        if isinstance(u, bool) or not isinstance(u, (int, float)) or not math.isfinite(u):
            continue
        ra = _ts(w.get("resets_at"))
        out.append({"key": key[:40], "label": CLAUDE_WINDOWS.get(key, key.replace("_", " ")[:40]),
                    "util": max(0.0, min(100.0, float(u))), "resets_at": ra if ra is not None and math.isfinite(ra) else None})
    order = list(CLAUDE_WINDOWS)
    out.sort(key=lambda w: order.index(w["key"]) if w["key"] in order else 99)
    return out


def clean_org_name(name):
    n = (name if isinstance(name, str) else "").strip()[:80]
    for suf in ("'s Organization", "’s Organization", " 的组织"):
        if n.endswith(suf):
            n = n[: -len(suf)]
    return n or "Claude 账号"


def claude_accounts_from_page(orgs):
    """浏览器页面上报的 [{"uuid","name","usage"}] → 额度账号列表。"""
    out = []
    for o in orgs if isinstance(orgs, list) else []:
        if not isinstance(o, dict) or not isinstance(o.get("uuid"), str) or not o["uuid"]:
            continue
        wins = parse_claude_usage_windows(o.get("usage"))
        if not wins:
            continue
        out.append({"id": f"claude:{o['uuid']}", "provider": "claude", "name": clean_org_name(o.get("name")),
                    "windows": wins, "source": "web"})
    return out


# ---------------------------------------------------------------- HTTP 小工具
def _get_json(url, headers, timeout=8):
    req = urllib.request.Request(url, headers=dict({"User-Agent": "AIStatus/1.5", "Accept": "application/json"},
                                                   **headers))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _err(e):
    if isinstance(e, urllib.error.HTTPError):
        return {401: "登录已失效", 403: "没有权限"}.get(e.code, f"请求失败（{e.code}）")
    if isinstance(e, (urllib.error.URLError, TimeoutError, OSError)):
        return "网络不可用"
    return "数据格式变化"


# ---------------------------------------------------------------- Claude Code
def claude_code_token():
    """读取 Claude Code 自己保存的登录信息（macOS 钥匙串 / 其他系统 ~/.claude/.credentials.json）。"""
    raw = None
    if sys.platform == "darwin":
        try:
            raw = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            raw = None
    if not raw:
        p = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
        try:
            with open(p, encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            return None, "未找到 Claude Code 登录信息"
    try:
        data = json.loads(raw)
        tok = (data.get("claudeAiOauth") or {}).get("accessToken")
        exp = _ts((data.get("claudeAiOauth") or {}).get("expiresAt"))
    except (ValueError, AttributeError):
        return None, "登录信息格式变化"
    if not tok:
        return None, "Claude Code 未用订阅账号登录"
    if exp and exp < time.time():
        return None, "登录已过期，请在 Claude Code 里重新登录"
    return tok, None


def fetch_claude_code():
    tok, err = claude_code_token()
    base = {"id": "claude-code", "provider": "claude-code", "name": "Claude Code", "source": "api"}
    if not tok:
        return dict(base, error=err)
    try:
        data = _get_json("https://api.anthropic.com/api/oauth/usage",
                         {"Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20"})
    except Exception as e:  # noqa: BLE001
        return dict(base, error=_err(e))
    wins = parse_claude_usage_windows(data)
    return dict(base, windows=wins) if wins else dict(base, error="数据格式变化")


# ---------------------------------------------------------------- API 余额
def fetch_deepseek(key):
    base = {"id": "deepseek-api", "provider": "deepseek", "name": "DeepSeek API", "source": "api"}
    try:
        data = _get_json("https://api.deepseek.com/user/balance", {"Authorization": f"Bearer {key}"})
        infos = data.get("balance_infos") or []
        info = next((i for i in infos if i.get("currency") == "CNY"), infos[0] if infos else None)
        if not info:
            return dict(base, error="数据格式变化")
        return dict(base, balance={"amount": float(info.get("total_balance")), "currency": info.get("currency")})
    except Exception as e:  # noqa: BLE001
        return dict(base, error=_err(e))


def fetch_moonshot(key):
    base = {"id": "moonshot-api", "provider": "moonshot", "name": "Kimi API", "source": "api"}
    try:
        data = _get_json("https://api.moonshot.cn/v1/users/me/balance", {"Authorization": f"Bearer {key}"})
        d = data.get("data") or {}
        if "available_balance" not in d:
            return dict(base, error="数据格式变化")
        return dict(base, balance={"amount": float(d["available_balance"]), "currency": "CNY"})
    except Exception as e:  # noqa: BLE001
        return dict(base, error=_err(e))


# ---------------------------------------------------------------- 本机密钥保存
SERVICE = "AIStatus"


def secret_get(name, fallback_dir):
    if sys.platform == "darwin":
        try:
            r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or None
        except Exception:
            return None
    try:
        with open(os.path.join(fallback_dir, "secrets.json"), encoding="utf-8") as f:
            return json.load(f).get(name) or None
    except (OSError, ValueError):
        return None


def secret_set(name, value, fallback_dir):
    """macOS 存入钥匙串；Windows 存在只有当前用户可访问的本机目录。value 为空表示删除。"""
    if sys.platform == "darwin":
        if value:
            subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE, "-a", name, "-w", value],
                           capture_output=True, timeout=10)
        else:
            subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", name],
                           capture_output=True, timeout=10)
        return
    os.makedirs(fallback_dir, exist_ok=True)
    p = os.path.join(fallback_dir, "secrets.json")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)


class QuotaPoller(threading.Thread):
    """定时查询可选的额度来源。cfg() 返回当前设置；store.apply_quota 接收结果。"""

    def __init__(self, store, cfg, secret_dir):
        super().__init__(daemon=True)
        self.store, self.cfg, self.dir = store, cfg, secret_dir
        self.next = {}
        self.wake = threading.Event()

    def refresh_now(self):
        self.next.clear()
        self.wake.set()

    def _due(self, name, every):
        now = time.time()
        if now >= self.next.get(name, 0):
            self.next[name] = now + every
            return True
        return False

    def run(self):
        while True:
            try:
                c = self.cfg()
                out = []
                if c.get("quota_claude_code") and self._due("cc", 180):
                    out.append(fetch_claude_code())
                for name, fn, acc in (("deepseek", fetch_deepseek, "deepseek-api"),
                                      ("moonshot", fetch_moonshot, "moonshot-api")):
                    if self._due(name, 300):
                        key = secret_get(name, self.dir)
                        if key:
                            out.append(fn(key))
                        else:
                            self.store.remove_account(acc)
                if not c.get("quota_claude_code"):
                    self.store.remove_account("claude-code")
                if out:
                    self.store.apply_quota(out)
            except Exception:
                pass
            self.wake.wait(15)
            self.wake.clear()
