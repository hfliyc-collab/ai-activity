// 隔离环境的内容脚本：把 inject.js 统计到的流式数据交给后台。
// （“停止按钮”检测已由桌面端通过 AppleScript 统一完成，这里只负责精确的 token 数。）
(() => {
  const host = location.hostname.replace(/^www\./, "");
  const site = (self.AIW_SITES || {})[host] || { id: host, label: host };
  const brands = (navigator.userAgentData && navigator.userAgentData.brands || []).map((b) => b.brand).join(" ");
  const browser = /Edge/i.test(brands) ? "Microsoft Edge" : /Brave/i.test(brands) ? "Brave Browser" : "Google Chrome";
  const title = () => (document.title || "").replace(self.AIW_TITLE_SUFFIX, "").trim();

  window.addEventListener("message", (e) => {
    const d = e.data;
    if (e.source !== window || !d || d.__aiw !== "stream") return;
    const state = { start: "working", progress: "working", end: "done", stopped: "stopped" }[d.phase] || "error";
    const real = d.usage && d.usage.output;
    const ev = {
      source: site.id, label: site.label, title: title(), url: location.href, browser, state,
      started_at: d.t0, tokens_out: real ? d.usage.output : d.est, est: !real,
      tokens_in: (d.usage && d.usage.input) || undefined, model: d.model || undefined,
      util: typeof d.util === "number" ? d.util : undefined,
    };
    try { chrome.runtime.sendMessage({ __aiw: 1, event: ev }).catch(() => {}); } catch (err) { /* 扩展重载后刷新页面即可 */ }
  });
})();
