// 由 tools/gen_extension_sites.py 根据 app/sites.py 生成，请勿手改
self.AIW_SITES = {
 "claude.ai": {
  "id": "claude",
  "label": "Claude",
  "stop": [
   "button[aria-label=\"Stop response\"]",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [
   "[data-is-streaming=\"true\"]"
  ],
  "msg": [
   "[data-is-streaming]",
   ".font-claude-response",
   ".font-claude-message",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ],
  "quota": "claude"
 },
 "chatgpt.com": {
  "id": "chatgpt",
  "label": "ChatGPT",
  "stop": [
   "[data-testid=\"stop-button\"]",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[data-message-author-role=\"assistant\"]",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chat.openai.com": {
  "id": "chatgpt",
  "label": "ChatGPT",
  "stop": [
   "[data-testid=\"stop-button\"]",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[data-message-author-role=\"assistant\"]",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "gemini.google.com": {
  "id": "gemini",
  "label": "Gemini",
  "stop": [
   "button.stop",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "model-response message-content",
   "model-response",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "grok.com": {
  "id": "grok",
  "label": "Grok",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".message-bubble",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chat.mistral.ai": {
  "id": "mistral",
  "label": "Le Chat",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "perplexity.ai": {
  "id": "perplexity",
  "label": "Perplexity",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chat.deepseek.com": {
  "id": "deepseek",
  "label": "DeepSeek",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".ds-markdown",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "kimi.com": {
  "id": "kimi",
  "label": "Kimi",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".segment-assistant",
   ".markdown-container",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "kimi.moonshot.cn": {
  "id": "kimi",
  "label": "Kimi",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".segment-assistant",
   ".markdown-container",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "doubao.com": {
  "id": "doubao",
  "label": "豆包",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[data-testid=\"receive_message\"]",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chat.qwen.ai": {
  "id": "qwen",
  "label": "通义千问",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".qwen-markdown",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "tongyi.com": {
  "id": "qwen",
  "label": "通义千问",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".qwen-markdown",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "qianwen.com": {
  "id": "qwen",
  "label": "通义千问",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".qwen-markdown",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "yuanbao.tencent.com": {
  "id": "yuanbao",
  "label": "元宝",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   ".agent-chat__speech-text",
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "yiyan.baidu.com": {
  "id": "yiyan",
  "label": "文心一言",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chatglm.cn": {
  "id": "chatglm",
  "label": "智谱清言",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "xinghuo.xfyun.cn": {
  "id": "xinghuo",
  "label": "讯飞星火",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "hailuoai.com": {
  "id": "minimax",
  "label": "MiniMax",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "chat.minimaxi.com": {
  "id": "minimax",
  "label": "MiniMax",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "ying.baichuan-ai.com": {
  "id": "baichuan",
  "label": "百小应",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "yuewen.cn": {
  "id": "stepfun",
  "label": "跃问",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "tiangong.cn": {
  "id": "tiangong",
  "label": "天工",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "n.cn": {
  "id": "nami",
  "label": "纳米 AI",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 },
 "metaso.cn": {
  "id": "metaso",
  "label": "秘塔",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "button[title*=\"停止\"]",
   "[data-testid*=\"stop\" i]",
   "[class*=\"stop-btn\" i]",
   "[class*=\"stopBtn\"]",
   "[class*=\"stop-button\" i]",
   "[class*=\"stopButton\"]",
   "[class*=\"stop-generat\" i]",
   "[class*=\"stopGenerat\"]",
   "[class*=\"stop_generat\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 }
};
self.AIW_GENERIC_STOP = ["button[aria-label*=\"Stop\" i]", "button[aria-label*=\"\u505c\u6b62\"]", "button[title*=\"\u505c\u6b62\"]", "[data-testid*=\"stop\" i]", "[class*=\"stop-btn\" i]", "[class*=\"stopBtn\"]", "[class*=\"stop-button\" i]", "[class*=\"stopButton\"]", "[class*=\"stop-generat\" i]", "[class*=\"stopGenerat\"]", "[class*=\"stop_generat\" i]"];
self.AIW_STOP_WORDS = ["停止", "停止生成", "停止回答", "停止输出", "停止响应", "中止", "中止生成", "暂停生成", "stop", "stop generating", "stop response", "stop streaming"];
self.AIW_TITLE_SUFFIX = /\s*[-–—|]\s*(Claude|ChatGPT|Gemini|Google Gemini|DeepSeek|Kimi.*|豆包.*|Grok|Qwen.*|通义.*|腾讯元宝.*|元宝.*|Le Chat.*|Perplexity|文心一言|智谱清言.*|讯飞星火.*|跃问|天工.*|秘塔.*|纳米.*)\s*$/i;
