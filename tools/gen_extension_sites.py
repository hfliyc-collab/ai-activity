#!/usr/bin/env python3
"""由 app/sites.py 生成 extension/sites.js 和 manifest.json 的 matches，保证两端站点定义一致。
修改 app/sites.py 后运行：python tools/gen_extension_sites.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from sites import GENERIC_STOP, SITES  # noqa: E402

table = {}
matches = []
for s in SITES:
    for h in s["hosts"]:
        table[h] = {k: s[k] for k in ("id", "label", "stop", "streaming", "msg")}
        matches += [f"https://{h}/*", f"https://www.{h}/*"] if h.count(".") == 1 else [f"https://{h}/*"]

js = ("// 由 tools/gen_extension_sites.py 根据 app/sites.py 生成，请勿手改\n"
      f"self.AIW_SITES = {json.dumps(table, ensure_ascii=False, indent=1)};\n"
      f"self.AIW_GENERIC_STOP = {json.dumps(GENERIC_STOP)};\n"
      "self.AIW_TITLE_SUFFIX = /\\s*[-–—|]\\s*(Claude|ChatGPT|Gemini|Google Gemini|DeepSeek|Kimi.*|豆包.*|Grok|Qwen.*|通义.*|腾讯元宝.*|元宝.*|Le Chat.*|Perplexity)\\s*$/i;\n")
with open(os.path.join(ROOT, "extension", "sites.js"), "w", encoding="utf-8") as f:
    f.write(js)

mp = os.path.join(ROOT, "extension", "manifest.json")
m = json.load(open(mp, encoding="utf-8"))
for cs in m["content_scripts"]:
    cs["matches"] = sorted(set(matches))
json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{len(table)} hosts, {len(set(matches))} match patterns")
