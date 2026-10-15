// 后台：把各标签页的状态转发给本机的“AI 活动”小组件（127.0.0.1:47823），
// 并执行小组件发回的指令（点击条目时切换到对应标签页）。
const ENDPOINT = "http://127.0.0.1:47823/event";
const BADGE = { working: ["…", "#0A84FF"], waiting: ["?", "#FF9F0A"], done: ["✓", "#30D158"],
                error: ["!", "#FF453A"], stopped: ["■", "#8E8E93"] };

async function post(ev) {
  try {
    const r = await fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(ev) });
    chrome.action.setTitle({ title: "AI 活动：已连接桌面小组件" });
    const data = await r.json().catch(() => ({}));
    for (const c of data.cmd || []) run(c);
  } catch (e) {
    chrome.action.setTitle({ title: "AI 活动：桌面小组件未运行" });
  }
}

async function run(c) {
  if (c.type !== "focus") return;
  try {
    const tab = await chrome.tabs.update(c.tab, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true, drawAttention: true });
  } catch (e) { /* 标签页已关闭 */ }
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (!msg || !msg.__aiw || !sender.tab) return;
  const tabId = sender.tab.id;
  post({ ...msg.event, session: `ext:${tabId}`, tab_id: tabId, url: msg.event.url || sender.tab.url });
  const b = BADGE[msg.event.state];
  if (b) {
    chrome.action.setBadgeText({ tabId, text: b[0] });
    chrome.action.setBadgeBackgroundColor({ tabId, color: b[1] });
  }
});

chrome.tabs.onRemoved.addListener((tabId) => post({ session: `ext:${tabId}`, state: "remove" }));
chrome.runtime.onStartup.addListener(() => post({ session: "ext:hello", kind: "hello" }));
chrome.runtime.onInstalled.addListener(() => post({ session: "ext:hello", kind: "hello" }));
