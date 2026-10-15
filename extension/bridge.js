// 内容脚本（隔离环境）：
// 1. 定期在页面里做只读探测（停止按钮是否出现、最后一条回复的字数），交给桌面小组件判断状态
// 2. 转发 inject.js 统计到的流式数据（更精确的 token 数）
// 只发送数字和网页标题，不发送对话内容。
(() => {
  const host = location.hostname.replace(/^www\./, "");
  const site = (self.AIW_SITES || {})[host];
  if (!site) return;
  const brands = ((navigator.userAgentData && navigator.userAgentData.brands) || []).map((b) => b.brand).join(" ");
  const browser = navigator.brave ? "Brave" : /Edge/i.test(brands) ? "Edge" : "Chrome";
  const title = () => (document.title || "").replace(self.AIW_TITLE_SUFFIX, "").trim();
  const CJK = /[\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]/g;

  function send(event) {
    try {
      chrome.runtime.sendMessage({ __aiw: 1, event: { source: site.id, label: site.label, browser, url: location.href, title: title(), ...event } })
        .catch(() => {});
    } catch (e) { /* 扩展重新加载后，刷新页面即可恢复 */ }
  }

  function visible(el) { return !!(el && (el.offsetParent !== null || el.getClientRects().length)); }
  function probe() {
    let busy = false;
    for (const sel of site.stop) {
      try { if ([...document.querySelectorAll(sel)].some(visible)) { busy = true; break; } } catch (e) { /* 无效选择器 */ }
    }
    for (const sel of site.streaming) {
      try { if (!busy && document.querySelector(sel)) busy = true; } catch (e) { /* 无效选择器 */ }
    }
    let list = [];
    for (const sel of site.msg) {
      try { const els = document.querySelectorAll(sel); if (els.length) { list = els; break; } } catch (e) { /* 无效选择器 */ }
    }
    const last = list.length ? list[list.length - 1] : null;
    const text = last ? (last.innerText || last.textContent || "") : "";
    const cjk = (text.match(CJK) || []).length;
    return { busy, n: text.length, est: cjk + Math.ceil((text.length - cjk) / 4), count: list.length };
  }

  let lastSent = 0;
  function report() {
    lastSent = Date.now();
    send({ kind: "probe", probe: probe() });
  }
  setInterval(report, 1200);
  // 后台标签页的定时器会被浏览器放慢；页面内容变化时立即补报一次
  new MutationObserver(() => { if (Date.now() - lastSent > 450) report(); })
    .observe(document.documentElement, { subtree: true, childList: true, characterData: true });
  setTimeout(report, 300);

  window.addEventListener("message", (e) => {
    const d = e.data;
    if (e.source !== window || !d || d.__aiw !== "stream") return;
    const state = { start: "working", progress: "working", end: "done", stopped: "stopped" }[d.phase] || "error";
    const real = d.usage && d.usage.output;
    send({
      state, started_at: d.t0, tokens_out: real ? d.usage.output : d.est, est: !real,
      tokens_in: (d.usage && d.usage.input) || undefined, model: d.model || undefined,
      util: typeof d.util === "number" ? d.util : undefined,
    });
  });
})();
