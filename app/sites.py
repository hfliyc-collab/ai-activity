# -*- coding: utf-8 -*-
"""网站、桌面客户端与本地工具的定义。新增网站或客户端只需要在这里加一项。

网站字段
  stop       “停止生成”按钮的选择器，出现即视为正在生成
  streaming  页面自带的“正在流式输出”标记
  msg        AI 回复消息的选择器，取最后一条统计字数；字数在增长也视为正在生成
  quota      可读取订阅额度的站点（目前只有 claude）

所有网站另外都会检查：可见按钮的文字 / 无障碍名称是否为 STOP_WORDS 之一。
"""
from urllib.parse import urlsplit

GENERIC_STOP = ['button[aria-label*="Stop" i]', 'button[aria-label*="停止"]', 'button[title*="停止"]',
                '[data-testid*="stop" i]', '[class*="stop-btn" i]', '[class*="stopBtn"]',
                '[class*="stop-button" i]', '[class*="stopButton"]', '[class*="stop-generat" i]',
                '[class*="stopGenerat"]', '[class*="stop_generat" i]']
GENERIC_MSG = ['[class*="markdown"]', '[class*="prose"]']
# 按钮文字或无障碍名称完全等于以下之一时，视为“正在生成”（网页与桌面客户端通用）
STOP_WORDS = ["停止", "停止生成", "停止回答", "停止输出", "停止响应", "中止", "中止生成", "暂停生成",
              "stop", "stop generating", "stop response", "stop streaming"]


def _s(id, label, glyph, tint, hosts, stop=None, streaming=None, msg=None, **kw):
    d = dict(id=id, label=label, glyph=glyph, tint=tint, hosts=hosts,
             stop=(stop or []) + GENERIC_STOP, streaming=streaming or [], msg=(msg or []) + GENERIC_MSG)
    d.update(kw)
    return d


SITES = [
    _s("claude", "Claude", "C", ["#E8916E", "#C9663F"], ["claude.ai"],
       stop=['button[aria-label="Stop response"]'], streaming=['[data-is-streaming="true"]'],
       msg=['[data-is-streaming]', '.font-claude-response', '.font-claude-message'], quota="claude"),
    _s("chatgpt", "ChatGPT", "G", ["#3BC79B", "#0E8A68"], ["chatgpt.com", "chat.openai.com"],
       stop=['[data-testid="stop-button"]'], msg=['[data-message-author-role="assistant"]']),
    _s("gemini", "Gemini", "✦", ["#6AA2FF", "#8A6BE0"], ["gemini.google.com"],
       stop=['button.stop'], msg=['model-response message-content', 'model-response']),
    _s("grok", "Grok", "X", ["#6B6F78", "#30333A"], ["grok.com"], msg=['.message-bubble']),
    _s("mistral", "Le Chat", "M", ["#FF9A55", "#E9631C"], ["chat.mistral.ai"]),
    _s("perplexity", "Perplexity", "P", ["#4DB8C4", "#1F8591"], ["perplexity.ai"]),
    # ---- 国产
    _s("deepseek", "DeepSeek", "D", ["#6F8BFF", "#3F5BE8"], ["chat.deepseek.com"], msg=['.ds-markdown']),
    _s("kimi", "Kimi", "K", ["#5B6478", "#2E3442"], ["kimi.com", "kimi.moonshot.cn"],
       msg=['.segment-assistant', '.markdown-container']),
    _s("doubao", "豆包", "豆", ["#5C8DFF", "#3367E6"], ["doubao.com"],
       msg=['[data-testid="receive_message"]']),
    _s("qwen", "通义千问", "通", ["#8B86FF", "#5B55E0"], ["chat.qwen.ai", "tongyi.com", "qianwen.com"],
       msg=['.qwen-markdown']),
    _s("yuanbao", "元宝", "元", ["#4FD08E", "#1E9E62"], ["yuanbao.tencent.com"],
       msg=['.agent-chat__speech-text']),
    _s("yiyan", "文心一言", "文", ["#4E7BFF", "#2848C9"], ["yiyan.baidu.com"]),
    _s("chatglm", "智谱清言", "清", ["#4C6EF5", "#2F3FB8"], ["chatglm.cn"]),
    _s("xinghuo", "讯飞星火", "星", ["#3D8BFF", "#1F5FD1"], ["xinghuo.xfyun.cn"]),
    _s("minimax", "MiniMax", "海", ["#FF6B8B", "#D8345C"], ["hailuoai.com", "chat.minimaxi.com"]),
    _s("baichuan", "百小应", "百", ["#FF9F43", "#E06C0E"], ["ying.baichuan-ai.com"]),
    _s("stepfun", "跃问", "跃", ["#5AC8FA", "#2A8FD0"], ["yuewen.cn"]),
    _s("tiangong", "天工", "天", ["#7B61FF", "#4F35D1"], ["tiangong.cn"]),
    _s("nami", "纳米 AI", "纳", ["#34C759", "#1C8F3D"], ["n.cn"]),
    _s("metaso", "秘塔", "秘", ["#5E6AD2", "#3A44A8"], ["metaso.cn"]),
]

# 桌面客户端：通过系统无障碍接口（macOS 辅助功能 / Windows UI Automation）读取按钮和文字
# names：macOS 应用名或 Windows 可执行文件名中包含的关键字（小写比较）
CLIENTS = [
    dict(id="kimi-app", label="Kimi 客户端", glyph="K", tint=["#5B6478", "#2E3442"], names=["kimi"]),
    dict(id="doubao-app", label="豆包客户端", glyph="豆", tint=["#5C8DFF", "#3367E6"], names=["豆包", "doubao"]),
    dict(id="yuanbao-app", label="元宝客户端", glyph="元", tint=["#4FD08E", "#1E9E62"], names=["元宝", "yuanbao"]),
    dict(id="qwen-app", label="通义客户端", glyph="通", tint=["#8B86FF", "#5B55E0"],
         names=["通义", "千问", "tongyi", "qwen"]),
    dict(id="chatglm-app", label="智谱清言客户端", glyph="清", tint=["#4C6EF5", "#2F3FB8"],
         names=["智谱清言", "chatglm", "zhipu"]),
    dict(id="wenxin-app", label="文小言客户端", glyph="文", tint=["#4E7BFF", "#2848C9"],
         names=["文小言", "文心", "wenxiaoyan", "yiyan"]),
    dict(id="deepseek-app", label="DeepSeek 客户端", glyph="D", tint=["#6F8BFF", "#3F5BE8"], names=["deepseek"]),
    dict(id="chatgpt-app", label="ChatGPT 桌面版", glyph="G", tint=["#3BC79B", "#0E8A68"], names=["chatgpt"]),
    dict(id="claude-app", label="Claude 桌面版", glyph="C", tint=["#E8916E", "#C9663F"], names=["claude"],
         exclude=["claude code", "claude-code"]),
]

# 本地工具（hooks / 本地记录）
AGENTS = {
    "claude-code": dict(label="Claude Code", glyph="›_", tint=["#E8916E", "#B4532E"]),
    "cursor": dict(label="Cursor", glyph="⌘", tint=["#5A5F6B", "#1E2128"]),
}
# 只识别“是否打开”的应用（macOS 进程路径）
APPS = [
    dict(id="cursor", label="Cursor", match="/Cursor.app/Contents/MacOS/Cursor", open="Cursor"),
    dict(id="claude-code", label="Claude Code", match_comm="claude", open=None),
]

# 额度账号的提供方
PROVIDERS = {
    "claude": dict(label="Claude 订阅", glyph="C", tint=["#E8916E", "#C9663F"]),
    "claude-code": dict(label="Claude Code 订阅", glyph="›_", tint=["#E8916E", "#B4532E"]),
    "deepseek": dict(label="DeepSeek API 余额", glyph="D", tint=["#6F8BFF", "#3F5BE8"]),
    "moonshot": dict(label="Kimi API 余额", glyph="K", tint=["#5B6478", "#2E3442"]),
}

SITE_BY_ID = {s["id"]: s for s in SITES}
CLIENT_BY_ID = {c["id"]: c for c in CLIENTS}


def site_for_url(url):
    host = (urlsplit(url or "").hostname or "").lower()
    for s in SITES:
        for h in s["hosts"]:
            if host == h or host.endswith("." + h):
                return s
    return None


def client_for_name(name):
    n = (name or "").lower()
    for c in CLIENTS:
        if any(x in n for x in c.get("exclude", [])):
            continue
        if any(k in n for k in c["names"]):
            return c
    return None


def glyph_of(kind_id):
    s = SITE_BY_ID.get(kind_id) or AGENTS.get(kind_id) or CLIENT_BY_ID.get(kind_id) or PROVIDERS.get(kind_id)
    if not s:
        for a in APPS:
            if a["id"] == kind_id:
                s = a
    s = s or {}
    return s.get("glyph") or (kind_id[:1].upper() if kind_id else "?"), \
        s.get("tint") or ["#7C8594", "#4A515E"]
