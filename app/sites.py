# -*- coding: utf-8 -*-
"""网站与本地应用的定义。新增网站只需要在 SITES 里加一项。

stop       “停止生成”按钮的选择器，出现即视为正在生成
streaming  页面自带的“正在流式输出”标记
msg        AI 回复消息的选择器，取最后一条统计字数；字数在增长也视为正在生成
"""
from urllib.parse import urlsplit

GENERIC_STOP = ['button[aria-label*="Stop" i]', 'button[aria-label*="停止"]',
                '[data-testid*="stop" i]']
GENERIC_MSG = ['[class*="markdown"]', '[class*="prose"]']

SITES = [
    dict(id="claude", label="Claude", glyph="C", tint=["#E8916E", "#C9663F"],
         hosts=["claude.ai"],
         stop=['button[aria-label="Stop response"]'] + GENERIC_STOP,
         streaming=['[data-is-streaming="true"]'],
         msg=['[data-is-streaming]', '.font-claude-response', '.font-claude-message']),
    dict(id="chatgpt", label="ChatGPT", glyph="G", tint=["#3BC79B", "#0E8A68"],
         hosts=["chatgpt.com", "chat.openai.com"],
         stop=['[data-testid="stop-button"]'] + GENERIC_STOP, streaming=[],
         msg=['[data-message-author-role="assistant"]']),
    dict(id="gemini", label="Gemini", glyph="✦", tint=["#6AA2FF", "#8A6BE0"],
         hosts=["gemini.google.com"],
         stop=['button.stop', 'button[aria-label*="Stop" i]', 'button[aria-label*="停止"]'],
         streaming=[], msg=['model-response message-content', 'model-response']),
    dict(id="deepseek", label="DeepSeek", glyph="D", tint=["#6F8BFF", "#3F5BE8"],
         hosts=["chat.deepseek.com"], stop=GENERIC_STOP, streaming=[],
         msg=['.ds-markdown']),
    dict(id="kimi", label="Kimi", glyph="K", tint=["#5B6478", "#2E3442"],
         hosts=["kimi.moonshot.cn", "kimi.com"], stop=GENERIC_STOP, streaming=[],
         msg=['.segment-assistant', '.markdown-container']),
    dict(id="doubao", label="豆包", glyph="豆", tint=["#5C8DFF", "#3367E6"],
         hosts=["doubao.com"], stop=GENERIC_STOP, streaming=[],
         msg=['[data-testid="receive_message"]']),
    dict(id="qwen", label="Qwen", glyph="Q", tint=["#8B86FF", "#5B55E0"],
         hosts=["chat.qwen.ai", "tongyi.com", "qianwen.com"], stop=GENERIC_STOP,
         streaming=[], msg=['.qwen-markdown']),
    dict(id="yuanbao", label="元宝", glyph="元", tint=["#4FD08E", "#1E9E62"],
         hosts=["yuanbao.tencent.com"], stop=GENERIC_STOP, streaming=[],
         msg=['.agent-chat__speech-text']),
    dict(id="grok", label="Grok", glyph="X", tint=["#6B6F78", "#30333A"],
         hosts=["grok.com"], stop=GENERIC_STOP, streaming=[], msg=['.message-bubble']),
    dict(id="mistral", label="Le Chat", glyph="M", tint=["#FF9A55", "#E9631C"],
         hosts=["chat.mistral.ai"], stop=GENERIC_STOP, streaming=[], msg=[]),
    dict(id="perplexity", label="Perplexity", glyph="P", tint=["#4DB8C4", "#1F8591"],
         hosts=["perplexity.ai"], stop=GENERIC_STOP, streaming=[], msg=[]),
]
for _s in SITES:
    _s["msg"] = _s["msg"] + GENERIC_MSG

# 本地工具（通过 hooks / 本地记录 / 进程识别）
AGENTS = {
    "claude-code": dict(label="Claude Code", glyph="›_", tint=["#E8916E", "#B4532E"]),
    "cursor": dict(label="Cursor", glyph="⌘", tint=["#5A5F6B", "#1E2128"]),
}
# 桌面应用：只能识别“已打开”，用于聚合视图中的状态条
APPS = [
    dict(id="cursor", label="Cursor", match="/Cursor.app/Contents/MacOS/Cursor", open="Cursor"),
    dict(id="claude-app", label="Claude 桌面版", match="/Claude.app/Contents/MacOS/Claude",
         open="Claude", glyph="C", tint=["#E8916E", "#C9663F"]),
    dict(id="chatgpt-app", label="ChatGPT 桌面版", match="/ChatGPT.app/Contents/MacOS/ChatGPT",
         open="ChatGPT", glyph="G", tint=["#3BC79B", "#0E8A68"]),
    dict(id="claude-code", label="Claude Code", match_comm="claude", open=None),
]

SITE_BY_ID = {s["id"]: s for s in SITES}


def site_for_url(url):
    host = (urlsplit(url or "").hostname or "").lower()
    for s in SITES:
        for h in s["hosts"]:
            if host == h or host.endswith("." + h):
                return s
    return None


def glyph_of(kind_id):
    s = SITE_BY_ID.get(kind_id) or AGENTS.get(kind_id)
    if not s:
        for a in APPS:
            if a["id"] == kind_id:
                s = a
    s = s or {}
    return s.get("glyph") or (kind_id[:1].upper() if kind_id else "?"), \
        s.get("tint") or ["#7C8594", "#4A515E"]
