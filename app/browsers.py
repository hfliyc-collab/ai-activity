# -*- coding: utf-8 -*-
"""通过 macOS 自动化（JXA）读取 Safari / Chrome / Arc / Edge / Brave 里打开的 AI 网页。

一次 osascript 调用完成：找出所有 AI 标签页 → 在每个标签页里跑一段只读的探测脚本
（看“停止”按钮、最后一条回复的字数）。网页内容不会离开本机，探测脚本只返回数字。

需要的权限：
  - 自动化：首次运行时系统会询问“是否允许控制 Safari / Chrome”，点允许
  - Safari：设置 → 高级 → 勾选“显示网页开发者功能”，然后 开发 → 允许来自 Apple 事件的 JavaScript
  - Chrome：菜单 显示 → 开发者 → 允许来自 Apple 事件的 JavaScript
    （或者安装 extension 文件夹里的扩展，二选一；扩展的 token 数更准）
"""
import json
import os
import subprocess
import tempfile
import threading
import time

from sites import SITES, STOP_WORDS

BROWSERS = [("Safari", "safari"), ("Google Chrome", "chromium"), ("Arc", "chromium"),
            ("Microsoft Edge", "chromium"), ("Brave Browser", "chromium"),
            ("Google Chrome Canary", "chromium")]

PROBE_TEMPLATE = r"""(function(){try{
var C=__CFG__;
function vis(e){return !!(e&&(e.offsetParent!==null||e.getClientRects().length));}
function stopWord(t){t=String(t||'').trim().toLowerCase();var i=t.search(/[(（]/);if(i>0)t=t.slice(0,i).trim();return C.words.indexOf(t)>=0;}
var busy=false,i,j,els;
for(i=0;i<C.stop.length&&!busy;i++){try{els=document.querySelectorAll(C.stop[i]);for(j=0;j<els.length;j++){if(vis(els[j])){busy=true;break;}}}catch(e){}}
for(i=0;i<C.streaming.length&&!busy;i++){try{if(document.querySelector(C.streaming[i]))busy=true;}catch(e){}}
if(!busy){els=document.querySelectorAll('button,[role="button"]');for(j=0;j<els.length&&j<400;j++){var b=els[j];if((stopWord(b.getAttribute('aria-label'))||stopWord(b.getAttribute('title'))||(b.innerText&&b.innerText.length<12&&stopWord(b.innerText)))&&vis(b)){busy=true;break;}}}
var list=[];for(i=0;i<C.msg.length;i++){try{els=document.querySelectorAll(C.msg[i]);if(els.length){list=els;break;}}catch(e){}}
var last=list.length?list[list.length-1]:null,t=last?(last.innerText||last.textContent||''):'';
var cjk=(t.match(/[\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]/g)||[]).length;
var out={busy:busy,n:t.length,est:cjk+Math.ceil((t.length-cjk)/4),count:list.length,title:document.title};
if(C.quota==='claude'){var Q=window.__aiwQ||(window.__aiwQ={t:0});
 if(Q.ready){out.quota=Q.ready;Q.ready=null;}
 if(Date.now()-Q.t>60000){Q.t=Date.now();
  fetch('/api/organizations',{credentials:'include'}).then(function(r){return r.ok?r.json():[];}).then(function(orgs){
   orgs=(Array.isArray(orgs)?orgs:[]).slice(0,4);
   return Promise.all(orgs.map(function(o){return fetch('/api/organizations/'+o.uuid+'/usage',{credentials:'include'})
    .then(function(r){return r.ok?r.json():null;}).then(function(u){return {uuid:o.uuid,name:o.name,usage:u};}).catch(function(){return null;});}));
  }).then(function(list){Q.ready=list.filter(function(x){return x&&x.usage;});}).catch(function(){});}}
return JSON.stringify(out);
}catch(e){return JSON.stringify({err:String(e).slice(0,100)});}})()"""

POLL_SCRIPT = r"""
var CFG = __CFG__;
function siteOf(url){
  var m=/^https?:\/\/([^\/?#:]+)/i.exec(url||''); if(!m) return null;
  var h=m[1].toLowerCase();
  for (var i=0;i<CFG.sites.length;i++){var s=CFG.sites[i];
    for (var k=0;k<s.hosts.length;k++){var d=s.hosts[k]; if(h===d||h.slice(-d.length-1)==='.'+d) return s;}}
  return null;
}
function grab(app, kind){
  var prop = kind==='safari' ? 'name' : 'title';
  try { return {u: app.windows.tabs.url(), t: app.windows.tabs[prop]()}; }
  catch(e) {
    var u=[], t=[], n=app.windows.length;
    for (var i=0;i<n;i++){ try{ u.push(app.windows[i].tabs.url()); t.push(app.windows[i].tabs[prop]()); } catch(e2){ u.push([]); t.push([]); } }
    return {u:u, t:t};
  }
}
function run(argv){
  var skip=(argv[0]||'').split('|'), out={tabs:[], status:{}};
  for (var b=0;b<CFG.browsers.length;b++){
    var name=CFG.browsers[b][0], kind=CFG.browsers[b][1], app;
    try { app=Application(name); if(!app.running()) continue; } catch(e){ continue; }
    var g, act=[];
    try { g=grab(app, kind); } catch(e){ out.status[name]='automation:'+String(e).slice(0,200); continue; }
    out.status[name]='ok';
    try { act = kind==='safari' ? app.windows.currentTab.index() : app.windows.activeTabIndex(); } catch(e){}
    var probe = skip.indexOf(name)<0;
    for (var wi=0; wi<g.u.length; wi++){
      var wu=g.u[wi]||[];
      for (var ti=0; ti<wu.length; ti++){
        var s=siteOf(wu[ti]); if(!s) continue;
        var rec={browser:name, url:wu[ti], site:s.id, title:(g.t[wi]||[])[ti]||'', active: act[wi]===ti+1};
        if (probe){
          try {
            var tab=app.windows[wi].tabs[ti];
            var r = kind==='safari' ? app.doJavaScript(s.probe, {in: tab}) : tab.execute({javascript: s.probe});
            rec.probe = r ? JSON.parse(r) : null;
          } catch(e) {
            var msg=String(e);
            if (/JavaScript|Apple ?Event|AppleScript/i.test(msg)) { out.status[name]='js:'+msg.slice(0,200); probe=false; }
            else rec.err=msg.slice(0,120);
          }
        } else rec.skipped=true;
        out.tabs.push(rec);
      }
    }
  }
  return JSON.stringify(out);
}
"""

FOCUS_SCRIPT = r"""
function run(argv){
  var name=argv[0], url=argv[1], app=Application(name), safari=(name==='Safari');
  var urls=app.windows.tabs.url();
  for (var wi=0; wi<urls.length; wi++){ var wu=urls[wi]||[];
    for (var ti=0; ti<wu.length; ti++){ if (wu[ti]===url){
      var w=app.windows[wi];
      if (safari) { w.currentTab = w.tabs[ti]; } else { w.activeTabIndex = ti+1; }
      try { w.index = 1; } catch(e){}
      app.activate(); return 'ok';
    }}}
  app.activate(); return 'notfound';
}
"""


def _probe_for(site):
    cfg = {k: site[k] for k in ("stop", "streaming", "msg")}
    cfg["words"] = [w.lower() for w in STOP_WORDS]
    cfg["quota"] = site.get("quota")
    return PROBE_TEMPLATE.replace("__CFG__", json.dumps(cfg, ensure_ascii=True))


def build_poll_script():
    cfg = {"browsers": BROWSERS,
           "sites": [{"id": s["id"], "hosts": s["hosts"], "probe": _probe_for(s)} for s in SITES]}
    return POLL_SCRIPT.replace("__CFG__", json.dumps(cfg, ensure_ascii=True))


class BrowserPoller(threading.Thread):
    """后台线程：定时轮询浏览器，把结果交给 store.on_browser_poll。"""

    def __init__(self, store):
        super().__init__(daemon=True)
        self.store = store
        self.no_probe_until = {}      # 浏览器未开启 JS 权限时，30 秒内不再尝试
        d = tempfile.mkdtemp(prefix="aistatus-")
        self.script = os.path.join(d, "poll.js")
        with open(self.script, "w", encoding="utf-8") as f:
            f.write(build_poll_script())

    def run(self):
        while True:
            t0 = time.time()
            try:
                self.poll_once()
            except Exception as e:  # 保持线程存活
                self.store.set_notice("_poller", "error", str(e)[:200])
            fast = self.store.any_web_active()
            time.sleep(max(0.3, (1.2 if fast else 2.5) - (time.time() - t0)))

    def poll_once(self):
        now = time.time()
        skip = [b for b, until in self.no_probe_until.items() if until > now]
        p = subprocess.run(["osascript", "-l", "JavaScript", self.script, "|".join(skip)],
                           capture_output=True, text=True, timeout=20)
        if p.returncode != 0 or not p.stdout.strip():
            return
        data = json.loads(p.stdout)
        for browser, st in data.get("status", {}).items():
            if st.startswith("js:"):
                self.no_probe_until[browser] = now + 30
                self.store.set_notice(browser, "js")
            elif st.startswith("automation:"):
                self.store.set_notice(browser, "automation")
            elif browser not in skip:
                self.store.clear_notice(browser)
        self.store.on_browser_poll(data, now, skipped=set(skip))


def focus_tab(browser, url):
    subprocess.Popen(["osascript", "-l", "JavaScript", "-e", FOCUS_SCRIPT, browser, url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_app(name):
    subprocess.Popen(["open", "-a", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
