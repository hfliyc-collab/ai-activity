// 运行在页面环境（MAIN world）：包装 window.fetch，复制一份 text/event-stream
// 响应流在旁边读，统计输出字符、估算 token，读出接口自带的 usage / 用量信息。
// 只把统计数字发给扩展，不发送任何对话内容。
(() => {
  if (window.__aiwInstalled) return;
  window.__aiwInstalled = true;

  const CJK = /[\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]/g;
  const origFetch = window.fetch;

  // 从一条 SSE JSON 里取出“新增的文字”，兼容几种常见格式
  function extractText(o) {
    if (!o || typeof o !== "object") return "";
    if (o.type === "content_block_delta" && o.delta) {                       // Anthropic / Claude
      return (o.delta.text || "") + (o.delta.thinking || "") + (o.delta.partial_json || "");
    }
    if (Array.isArray(o.choices)) {                                           // OpenAI 兼容（Qwen、Kimi 等）
      return o.choices.map((c) => (c.delta && ((c.delta.content || "") + (c.delta.reasoning_content || ""))) || "").join("");
    }
    if (typeof o.completion === "string") return o.completion;              // 旧版 Claude
    if (o.event === "cmpl" && typeof o.text === "string") return o.text;      // Kimi
    if (typeof o.v === "string" && (o.o === undefined || /append/i.test(o.o))) return o.v;  // ChatGPT / DeepSeek 增量补丁
    if (Array.isArray(o.v)) return o.v.map(extractText).join("");
    return "";
  }

  function findUsage(o, depth = 0) {
    if (!o || typeof o !== "object" || depth > 4) return null;
    if (o.usage && typeof o.usage === "object") {
      const u = o.usage;
      const out = u.output_tokens ?? u.completion_tokens;
      const inp = u.input_tokens ?? u.prompt_tokens;
      if (typeof out === "number" || typeof inp === "number") return { output: out || 0, input: inp || 0 };
    }
    for (const v of Object.values(o)) {
      if (v && typeof v === "object") { const r = findUsage(v, depth + 1); if (r) return r; }
    }
    return null;
  }

  // claude.ai 的 message_limit 事件里带有用量比例（字段名含 utilization），取最大值
  function findUtil(o, depth = 0) {
    if (!o || typeof o !== "object" || depth > 6) return null;
    let best = null;
    for (const [k, v] of Object.entries(o)) {
      let r = null;
      if (typeof v === "number" && /utili[sz]ation/i.test(k)) r = v <= 1 ? v * 100 : v;
      else if (v && typeof v === "object") r = findUtil(v, depth + 1);
      if (r != null) best = best == null ? r : Math.max(best, r);
    }
    return best;
  }

  async function watch(stream) {
    const reader = stream.getReader();
    const dec = new TextDecoder();
    let buf = "", chars = 0, cjk = 0, t0 = 0, last = 0;
    let usage = null, model = null, util = null, phaseEnd = "end";

    const emit = (phase) => {
      if (usage && usage.output && usage.output < 1) usage = null;
      window.postMessage({
        __aiw: "stream", phase, t0, est: cjk + Math.ceil((chars - cjk) / 4),
        usage, model, util,
      }, "*");
    };

    const handle = (block) => {
      const data = block.split(/\r?\n/).filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).replace(/^ /, "")).join("\n");
      if (!data || data === "[DONE]") return;
      let o;
      try { o = JSON.parse(data); } catch (e) { return; }
      if (o.type === "message_start" && o.message && o.message.model) model = o.message.model;
      else if (typeof o.model === "string" && !model) model = o.model;
      if (o.type === "message_limit") { const u = findUtil(o); if (u != null) util = u; }
      if (o.type === "error" || o.error) phaseEnd = "error";
      const u = findUsage(o);
      if (u) usage = { output: Math.max(u.output, (usage && usage.output) || 0), input: u.input || (usage && usage.input) || 0 };
      const t = extractText(o);
      if (t) {
        if (!t0) { t0 = Date.now(); last = t0; emit("start"); }
        chars += t.length;
        cjk += (t.match(CJK) || []).length;
      }
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split(/\r?\n\r?\n/);
        buf = parts.pop();
        parts.forEach(handle);
        if (t0 && Date.now() - last > 400) { last = Date.now(); emit("progress"); }
      }
      if (buf.trim()) handle(buf);
    } catch (e) {
      phaseEnd = e && e.name === "AbortError" ? "stopped" : "error";
    }
    if (t0) emit(phaseEnd);
  }

  window.fetch = async function (...args) {
    const res = await origFetch.apply(this, args);
    try {
      const ct = res.headers.get("content-type") || "";
      if (res.body && ct.includes("text/event-stream")) {
        const [mine, theirs] = res.body.tee();
        watch(mine);
        const copy = new Response(theirs, { status: res.status, statusText: res.statusText, headers: res.headers });
        Object.defineProperty(copy, "url", { value: res.url });
        Object.defineProperty(copy, "redirected", { value: res.redirected });
        return copy;
      }
    } catch (e) { /* 出任何问题都原样返回，不影响网页 */ }
    return res;
  };
})();
