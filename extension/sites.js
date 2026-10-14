// 站点配置：id/label 显示在小组件上；stop 是“停止生成”按钮的选择器，
// 在拦截不到流式请求时（比如 Gemini 不走 SSE）用它判断是否在生成。
// 新增站点：在这里加一项，并把域名加进 manifest.json 的两处 matches。
const AIW_GENERIC_STOP = [
  'button[aria-label*="Stop" i]', 'button[aria-label*="停止"]', 'button[data-testid*="stop" i]'
];

self.AIW_SITES = {
  "claude.ai":          { id: "claude",     label: "Claude",     stop: ['button[aria-label="Stop response"]', ...AIW_GENERIC_STOP] },
  "chatgpt.com":        { id: "chatgpt",    label: "ChatGPT",    stop: ['[data-testid="stop-button"]', ...AIW_GENERIC_STOP] },
  "chat.openai.com":    { id: "chatgpt",    label: "ChatGPT",    stop: ['[data-testid="stop-button"]', ...AIW_GENERIC_STOP] },
  "gemini.google.com":  { id: "gemini",     label: "Gemini",     stop: ['button.stop', 'button[aria-label*="Stop" i]', 'button[aria-label*="停止"]'] },
  "chat.deepseek.com":  { id: "deepseek",   label: "DeepSeek",   stop: AIW_GENERIC_STOP },
  "kimi.moonshot.cn":   { id: "kimi",       label: "Kimi",       stop: AIW_GENERIC_STOP },
  "kimi.com":           { id: "kimi",       label: "Kimi",       stop: AIW_GENERIC_STOP },
  "doubao.com":         { id: "doubao",     label: "豆包",        stop: AIW_GENERIC_STOP },
  "grok.com":           { id: "grok",       label: "Grok",       stop: AIW_GENERIC_STOP },
  "chat.qwen.ai":       { id: "qwen",       label: "Qwen",       stop: AIW_GENERIC_STOP },
  "tongyi.com":         { id: "tongyi",     label: "通义",        stop: AIW_GENERIC_STOP },
  "yuanbao.tencent.com":{ id: "yuanbao",    label: "元宝",        stop: AIW_GENERIC_STOP },
  "chat.mistral.ai":    { id: "mistral",    label: "Mistral",    stop: AIW_GENERIC_STOP },
  "perplexity.ai":      { id: "perplexity", label: "Perplexity", stop: AIW_GENERIC_STOP },
};
self.AIW_GENERIC_STOP = AIW_GENERIC_STOP;
// 去掉网页标题里的站点后缀，只留会话名
self.AIW_TITLE_SUFFIX = /\s*[-–—|]\s*(Claude|ChatGPT|Gemini|Google Gemini|DeepSeek|Kimi.*|豆包.*|Grok|Qwen.*|通义.*|腾讯元宝.*|元宝.*|Le Chat.*|Perplexity)\s*$/i;
