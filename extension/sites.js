// 由 tools/gen_extension_sites.py 根据 app/sites.py 生成，请勿手改
self.AIW_SITES = {
 "claude.ai": {
  "id": "claude",
  "label": "Claude",
  "stop": [
   "button[aria-label=\"Stop response\"]",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "[data-testid*=\"stop\" i]"
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
  ]
 },
 "chatgpt.com": {
  "id": "chatgpt",
  "label": "ChatGPT",
  "stop": [
   "[data-testid=\"stop-button\"]",
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "[data-testid*=\"stop\" i]"
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
   "[data-testid*=\"stop\" i]"
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
   "button[aria-label*=\"停止\"]"
  ],
  "streaming": [],
  "msg": [
   "model-response message-content",
   "model-response",
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
   "[data-testid*=\"stop\" i]"
  ],
  "streaming": [],
  "msg": [
   ".ds-markdown",
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
   "[data-testid*=\"stop\" i]"
  ],
  "streaming": [],
  "msg": [
   ".segment-assistant",
   ".markdown-container",
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
   "[data-testid*=\"stop\" i]"
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
   "[data-testid*=\"stop\" i]"
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
  "label": "Qwen",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "[data-testid*=\"stop\" i]"
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
  "label": "Qwen",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "[data-testid*=\"stop\" i]"
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
  "label": "Qwen",
  "stop": [
   "button[aria-label*=\"Stop\" i]",
   "button[aria-label*=\"停止\"]",
   "[data-testid*=\"stop\" i]"
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
   "[data-testid*=\"stop\" i]"
  ],
  "streaming": [],
  "msg": [
   ".agent-chat__speech-text",
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
   "[data-testid*=\"stop\" i]"
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
   "[data-testid*=\"stop\" i]"
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
   "[data-testid*=\"stop\" i]"
  ],
  "streaming": [],
  "msg": [
   "[class*=\"markdown\"]",
   "[class*=\"prose\"]"
  ]
 }
};
self.AIW_GENERIC_STOP = ["button[aria-label*=\"Stop\" i]", "button[aria-label*=\"\u505c\u6b62\"]", "[data-testid*=\"stop\" i]"];
self.AIW_TITLE_SUFFIX = /\s*[-–—|]\s*(Claude|ChatGPT|Gemini|Google Gemini|DeepSeek|Kimi.*|豆包.*|Grok|Qwen.*|通义.*|腾讯元宝.*|元宝.*|Le Chat.*|Perplexity)\s*$/i;
