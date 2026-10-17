<div align="center">

# ✦ AI 活动

**一个 macOS / Windows 桌面小组件，把你所有 AI 的工作状态汇总到一处。**

浏览器里的 Claude、ChatGPT、Gemini、Kimi、DeepSeek，加上 Cursor 和 Claude Code，<br>
谁在生成、谁在等你确认、谁刚做完，一眼看清。发完消息，就可以去做别的事了。

![Version 1.5](https://img.shields.io/badge/version-1.5-111111)
![macOS 12+](https://img.shields.io/badge/macOS-12%2B-black?logo=apple)
![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Local only](https://img.shields.io/badge/数据-只在本机-blue)

<img src="docs/preview-island.png" width="700" alt="刘海模式：常驻灵动岛，悬停展开">

<img src="docs/preview-modes.png" width="760" alt="侧边栏（深色、浅色）与菜单栏弹出">

[English](#english) · [安装](#安装) · [工作原理](#工作原理) · [常见问题](#常见问题)

</div>

---

## 为什么做这个

同时用好几个 AI 已经是常态：网页里让 Claude 改稿，ChatGPT 查资料，Cursor 在写代码，终端里 Claude Code 在跑任务。问题是它们都需要你**盯着**：切过去看一眼还在生成，切回来，过一会儿再切过去，才发现早就做完了，或者 Agent 卡在等你点“允许”已经五分钟。

**AI 活动** 把这些状态收进桌面角落的一个小窗口，并在任务完成时通知你。你不用再来回切换窗口确认进度。

## 功能

- 🏝 **三种显示方式**：**刘海**（贴着刘海的灵动岛，常驻活动指示和额度百分比，悬停展开）、**菜单栏**（图标旁显示额度，点击查看一个账号）、**侧边栏**（同时排列已选账号，可拖到任意显示器）。Windows 上是侧边栏和托盘
- 📊 **AI 额度一眼就知道**：Claude 订阅的 5 小时 / 每周用量、Claude Code 订阅用量、DeepSeek 和 Kimi 的 API 余额；按自己的习惯勾选账号、拖动排序、设主账号
- 🔍 **自动发现**：自动识别浏览器里打开的 AI 网站和正在运行的 AI 客户端，无需逐个配置
- 🖥 **桌面客户端也能监测**：Kimi、豆包、元宝、通义、智谱清言、文小言、DeepSeek、ChatGPT、Claude 等客户端的生成状态
- ⚡ **实时状态**：生成中 / 等你确认 / 已完成 / 出错 / 已停止，附用时、token 数和生成速度
- 🔔 **完成提醒**：系统通知加提示音；页面刷新、加载历史、思考停顿都不会误报
- 🌙 **专注模式**：临时隐藏 15 分钟、1 小时、3 小时或 5 小时，期间不提醒，随时从菜单栏恢复
- 🐦 **绘本伙伴（可选）**：一只原创小麻雀，空闲打盹、生成时啄键盘、等你确认时探头、完成时跳一下
- 🧑‍💻 **编程 Agent**：Claude Code 显示真实 token、上下文、正在执行的工具，需要授权时立即标橙；Cursor 显示任务进度
- 🖱 **一键跳转**：点击任意条目，切到对应的标签页或应用
- 🔒 **只在本机**：位置、外观、账号选择都保存在本机；不上传任何对话内容

### 支持的来源

| 来源 | 识别方式 | 能看到 |
|---|---|---|
| Claude · ChatGPT · Gemini · Grok · Le Chat · Perplexity<br>DeepSeek · Kimi · 豆包 · 通义千问 · 元宝 · 文心一言 · 智谱清言 · 讯飞星火 · MiniMax · 百小应 · 跃问 · 天工 · 纳米 AI · 秘塔 | macOS：系统自动化（Safari 与 Chromium 系浏览器）<br>Windows：浏览器扩展（Chrome、Edge、Brave） | 状态、用时、token 估算、速度；点击跳回标签页 |
| 同上，装了浏览器扩展时 | 扩展旁路读取流式响应 | 更精确的 token 数；Claude 用量百分比 |
| Claude Code | 读取本地会话记录 + hooks | 真实 token、上下文、当前工具、待授权 |
| Cursor | hooks（安装时自动配置） | 状态、用时、token 估算、任务标题 |
| Kimi · 豆包 · 元宝 · 通义 · 智谱清言 · 文小言 · DeepSeek · ChatGPT · Claude **客户端** | 系统无障碍接口（macOS 辅助功能 / Windows UI Automation） | 状态、用时；点击切到该应用 |
| Cursor | 进程检测 | 列入“已打开” |

## 安装

### macOS

需要 **macOS 12 或更新版本**（系统自带的 Python 3.9+ 即可）。

```bash
git clone https://github.com/hfliyc-collab/ai-activity.git
cd ai-activity
./install.sh
```

> 国内网络可使用镜像：`PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ./install.sh`

安装脚本会：建立独立的 Python 环境并安装 PyObjC；生成 `~/Applications/AI 活动.app`；检测到 Cursor / Claude Code 时自动接入 hooks（原配置先备份）；然后启动。菜单栏会出现 ✦ 图标。

**首次运行：三个权限（各开一次）**

1. **允许控制浏览器**：系统弹窗询问“AI 活动”是否可以控制 Safari / Chrome 时，点“允许”。
2. **Safari**：设置（⌘,）› 高级 › 勾选“显示网页开发者功能”；设置顶部会多出 **开发者** 标签页，在“自动化”里勾选“允许来自 Apple 事件的 JavaScript”。
   <sub>Safari 16 及以前：开发 菜单 › 允许来自 Apple 事件的 JavaScript</sub>
3. **Chrome**：菜单栏 显示 › 开发者 › 勾选“允许来自 Apple 事件的 JavaScript”。Arc、Edge、Brave 位置类似。

缺少某项权限时，小组件仍能识别你打开了哪些 AI，并会在窗口内提示如何开启。想要更精确的 token 数，可以另外安装下文的浏览器扩展（可选）。

### Windows

需要 **Windows 10 或 11**，以及 Chrome、Edge 或 Brave 浏览器。

1. 下载本仓库（右上角 Code › Download ZIP）并解压，或者 `git clone`。
2. 双击根目录的 **`install.bat`**。
   脚本会自动：找到或安装 Python 3.12；安装依赖（pywebview、pystray、Pillow）；检查 WebView2 运行库；接入 Cursor / Claude Code；在开始菜单创建“AI 活动”；然后启动。桌面右上角出现小组件，任务栏右下角托盘区出现 ✦ 图标。
3. **安装浏览器扩展**（Windows 上读取网页状态必须用它）：
   - 在 Chrome 地址栏打开 `chrome://extensions`（Edge 是 `edge://extensions`）
   - 打开“开发者模式”（Edge 叫“开发人员模式”）
   - 点“加载已解压的扩展程序”，选择 `%LOCALAPPDATA%\AIStatus\extension`（安装结束时会自动打开这个文件夹）
   - 刷新已经打开的 AI 网页
4. 接入了 Cursor 的话，重启一次 Cursor。

> 国内网络可先在 PowerShell 里执行 `$env:PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"`，再运行 `windows\install.ps1`。

托盘图标右键菜单：显示 / 隐藏小组件、始终置顶、完成时提醒、开机自动启动、打开扩展文件夹、退出。

### 浏览器扩展说明

扩展在 Windows 上是必装项，在 macOS 上是可选项。它只在 AI 网站上运行，只把状态数字和网页标题发给本机的小组件（`127.0.0.1`），不读取、不发送对话内容。它还负责“点击条目跳回对应标签页”。

### 卸载

- macOS：`./uninstall.sh`
- Windows：双击 `uninstall.bat`

都会移除程序、开机启动项，以及 Cursor / Claude Code 里本工具的 hooks（其他 hooks 保留）。浏览器扩展需在扩展管理页手动移除。

## 使用

| 操作 | 效果 |
|---|---|
| 拖动顶部标题区 | 移动窗口，位置会被记住 |
| 点击条目或标签 | 跳到对应标签页 / 应用 |
| 菜单栏 ✦（macOS）/ 托盘 ✦（Windows） | 显示进行中的任务数；切换置顶、完成提醒、开机启动等 |

图标外圈彩色光环旋转 = 正在生成；橙色呼吸 = 等你确认；绿色勾 = 完成。完成的任务保留 10 分钟，之后收进“已打开”。

## 显示方式与额度

在设置（菜单栏 ✦ › 设置…，Windows 在托盘菜单里）中切换：

| 方式 | 平时 | 交互 |
|---|---|---|
| 刘海（macOS） | 刘海两侧：活动指示、进行中的数量和主账号额度，例如 63%。会实时测量菜单栏，只用确实测到是空着的位置：右边被图标占满就全部放到左边；两边都没有确认的空位时，岛只占刘海本身（看不见），额度改为显示在菜单栏 ✦ 图标旁。常驻时绝不伸到菜单栏下方，也绝不遮挡已有图标。也可以在 菜单栏 ✦ › 刘海内容位置 里固定在左侧或右侧 | 悬停在菜单栏下方展开全部账号和任务，离开自动收起；点击可固定 |
| 菜单栏（macOS） | 菜单栏图标旁显示主账号额度 | 点击弹出一个账号的详情，左右切换其他账号 |
| 侧边栏 | 毛玻璃窗口，同时排列所有已选账号和任务 | 拖到任意显示器，位置会记住 |
| 托盘（Windows） | 托盘图标直接画出额度数字，按用量变蓝 / 橙 / 红 | 点击弹出一个账号的详情 |

**额度来源**

| 账号 | 方式 | 默认 |
|---|---|---|
| Claude 订阅（网页、桌面版共用） | 已登录的 claude.ai 页面在页面内读取自己的用量 | 自动（打开过 claude.ai 即可） |
| Claude Code 订阅 | 读取本机 Claude Code 的登录信息查询用量 | 关闭，需要在设置中开启 |
| DeepSeek / Kimi API 余额 | 你填写的 API Key 调用官方余额接口；macOS 存入钥匙串 | 填写后开启 |

ChatGPT、Gemini、Cursor、豆包等目前没有可靠的官方额度接口，只显示工作状态，不显示估算的额度。额度请求失败时保留上次成功的数据并标注原因。

**专注**：菜单栏 ✦ › 专注一会儿，选 15 分钟 / 1 小时 / 3 小时 / 5 小时。期间所有窗口隐藏、不弹提醒，菜单栏图标变成月亮并显示剩余时间；点“立即显示”随时恢复，重启后仍然有效。

**桌面客户端**：macOS 需要在 系统设置 › 隐私与安全性 › 辅助功能 中允许一次“AI 活动”（设置页有直达按钮）。程序只读取窗口底部最近的一段文字长度和按钮名称来判断状态，不保存、不发送任何文字。

<img src="docs/preview-settings.png" width="420" alt="设置页">

## 工作原理

```mermaid
flowchart LR
    subgraph 浏览器
      S[Safari 标签页 · macOS]
      C[Chrome / Edge 等标签页]
      X[浏览器扩展 · Windows 必装]
    end
    subgraph 本地工具
      CC[Claude Code 会话记录]
      H[Cursor / Claude Code hooks]
      P[进程列表]
    end
    S & C -- AppleScript 只读探测 · macOS --> A
    C -.-> X
    X -- 127.0.0.1 --> A
    H -- 127.0.0.1 --> A
    CC --> A
    P --> A
    A[聚合层 core.py] --> UI[macOS：毛玻璃窗口 PyObjC<br>Windows：WebView2 窗口 pywebview]
    A --> N[系统通知]
```

**网页与客户端状态**由两条线索共同判断：是否出现“停止生成”一类按钮（按选择器或按钮文字识别），以及最新回复的字数是否仍在增长。见过停止按钮的页面，完成时立即提醒；只能看字数的页面，判完成后再等 8 秒才提醒，如果期间又开始输出，就算作同一个任务继续，这样 AI 中途“思考”停顿不会被误判。探测只返回数字，不返回对话内容。

**token 数**：标 `≈` 的为估算（中日韩文字约 1 字 1 token，其他约 4 字符 1 token，误差通常在一到三成），适合看进度和速度；不带 `≈` 的为真实值，来自 Claude Code 本地记录或接口返回的用量字段。

### 项目结构

```
app/
  main.py           macOS：原生窗口、菜单栏、通知（PyObjC）
  core.py           聚合层与状态机、本机 HTTP 接口（两个系统共用，可单独测试）
  browsers.py       浏览器标签页发现与探测（JXA）
  local_sources.py  Claude Code 会话记录解析、进程检测（macOS / Windows）
  sites.py          网站与客户端定义：新增网站或客户端只改这里
  clients.py        桌面客户端监测（macOS 辅助功能 / Windows UI Automation）
  quota.py          额度：解析与可选的查询（Claude Code、DeepSeek、Kimi）
  ui/settings.html  设置页
  ui/index.html     界面；直接用浏览器打开会显示演示数据
windows/
  main_win.py       Windows：pywebview 窗口、托盘图标、开机启动
  notify_win.py     Windows 系统通知
  install.ps1       Windows 安装脚本（由 install.bat 调用）
hooks/              Cursor / Claude Code hooks 与一键安装脚本
extension/          浏览器扩展（Windows 必装，macOS 可选）
tools/              由 app/sites.py 生成扩展的站点表
tests/              压力测试
install.sh / install.bat        一键安装（macOS / Windows）
uninstall.sh / uninstall.bat    卸载
```

## 扩展

**新增网站**：在 `app/sites.py` 的 `SITES` 里加一项（域名、“停止”按钮选择器、回复消息选择器），运行 `python tools/gen_extension_sites.py` 同步到浏览器扩展，再重新安装。

**接入任何工具**：能发 HTTP 请求就能接入。

```bash
curl -X POST http://127.0.0.1:47823/event -H "Content-Type: application/json" \
  -d '{"session":"job-1","label":"批处理","state":"working","title":"转换 200 个文件"}'
# 结束时：state 改为 "done"，可附 "tokens_out": 1200, "est": false
```

查看当前汇总数据：`curl http://127.0.0.1:47823/state`

## 隐私

- 只监听 `127.0.0.1`；除了你开启的额度查询（Claude Code、DeepSeek、Kimi 官方接口），不发起任何外部网络请求
- 网页探测脚本只读，只返回字数与状态
- 任务标题来自网页标题或你在 Agent 里的提问，只显示在本机窗口
- 修改 Cursor / Claude Code 配置前自动备份，卸载时只移除本工具的条目

## 常见问题

<details><summary><b>窗口一直显示“正在查找打开的 AI…”</b></summary>

确认已允许“AI 活动”控制浏览器：系统设置 › 隐私与安全性 › 自动化（菜单栏图标里有直达入口）。
</details>

<details><summary><b>网页明明在生成，却显示在“已打开”里</b></summary>

通常是“允许来自 Apple 事件的 JavaScript”没开，窗口里会有橙色提示。也可能是网站改版，欢迎提 Issue，或直接更新 <code>app/sites.py</code> 里的选择器。
</details>

<details><summary><b>Cursor 没有显示</b></summary>

安装后需重启一次 Cursor。hooks 只覆盖 Agent / Chat，Tab 补全不计入。
</details>

<details><summary><b>Claude Code 一直显示“生成中”</b></summary>

超过 10 分钟没有任何活动会自动标记为已停止；安装 hooks 后，结束会即时显示。
</details>

<details><summary><b>Windows：双击 install.bat 被系统拦截</b></summary>

从网上下载的压缩包会被标记。右键压缩包 › 属性 › 勾选“解除锁定”后重新解压；或者在弹出的“Windows 已保护你的电脑”里点“更多信息 › 仍要运行”。
</details>

<details><summary><b>Windows：小组件提示“还没装连接扩展”</b></summary>

按“安装 › Windows”第 3 步加载 `%LOCALAPPDATA%\AIStatus\extension`，然后刷新 AI 网页。扩展更新后也需要在扩展管理页点一下“重新加载”。
</details>

<details><summary><b>Windows：窗口一片空白</b></summary>

通常是缺少 WebView2 运行库，从 https://go.microsoft.com/fwlink/p/?LinkId=2124703 安装后重新打开“AI 活动”。
</details>

<details><summary><b>刘海模式遮挡了菜单栏图标</b></summary>

1. 在 系统设置 › 隐私与安全性 › 辅助功能 里允许“AI 活动”，这样它才能读到应用菜单和图标的准确位置。
2. 如果你确定刘海左侧是空的：菜单栏 ✦ › 刘海内容位置 › 固定在刘海左侧。
3. 请点 菜单栏 ✦ › 刘海内容位置 › 复制菜单栏诊断信息，把内容贴到 Issue 里。它只包含图标的位置和宽度，不含任何文字。
</details>

<details><summary><b>启动后没有反应</b></summary>

运行下面的命令可以看到报错信息，欢迎附在 Issue 里：

```bash
# macOS
~/Library/Application\ Support/AIStatus/venv/bin/python ~/Library/Application\ Support/AIStatus/app/main.py
```

```powershell
# Windows（PowerShell）
& "$env:LOCALAPPDATA\AIStatus\venv\Scripts\python.exe" "$env:LOCALAPPDATA\AIStatus\windows\main_win.py"
```
</details>

## 测试

```bash
python tests/stress_test.py   # 后端：接口吞吐、规模、并发、模糊测试、内存、判断准确率
python tests/ui_stress.py     # 界面与扩展：渲染压力、三种视图、设置页、8 个国产网站同时生成、Claude 额度（需要 playwright）
```

当前结果：后端 14 项、界面与扩展 17 项全部通过。灵动岛在 3 万种随机菜单栏上（其中 1.3 万次模拟测量失败）：遮挡图标 0 次、伸到菜单栏下方 0 次。32 路并发 12,800 次请求零失败（p99 约 72 ms）；500 个标签页时生成一次视图约 2 ms；3 万组随机输入无异常；6 万轮打开关闭内存稳定；400 次模拟生成提前误判 0、重复提醒 0。

已知局限：只能靠字数判断、又没有停止按钮的网站，如果 AI 可见输出不足 3 秒就进入很长的静默，按设计不会提醒（避免页面刷新被误报）。桌面客户端的读取方式和刘海的实际位置需要在真机上验证，欢迎反馈。

## 参与贡献

最需要帮助的是**网站选择器**：各家 AI 网站改版频繁，如果某个网站识别不准，请在 Issue 里写明网站名和现象，或直接提交对 `app/sites.py` 的修改。

本地调试界面：用浏览器打开 `app/ui/index.html` 即可看到演示数据。聚合逻辑 `core.py` 不依赖具体系统，可以在任何系统上写测试。

## 致谢

开发过程中参考了这些开源项目的思路：
[she-llac/claude-counter](https://github.com/she-llac/claude-counter) ·
[lugia19/Claude-Usage-Extension](https://github.com/lugia19/Claude-Usage-Extension) ·
[bozdemir/claude-usage-widget](https://github.com/bozdemir/claude-usage-widget)

本项目与 Anthropic、OpenAI、Google、Anysphere（Cursor）等公司无关，相关名称仅用于说明兼容性。

## License

[MIT](LICENSE)

---

<a name="english"></a>

## English

**AI Activity** is a desktop widget for macOS and Windows that shows, at a glance, what all your AI tools are doing: Claude, ChatGPT, Gemini, Kimi, DeepSeek and more in Safari or Chrome, plus Cursor and Claude Code.

- Auto-detects open AI tabs across Safari, Chrome, Arc, Edge and Brave
- Live states (working / needs you / done), elapsed time, token counts and speed
- Real token and context numbers for Claude Code; Cursor via hooks
- Notifies you when a task finishes; click any item to jump to its tab
- Native vibrancy window, follows light/dark mode, floats or sits on the desktop
- Runs entirely on your Mac; no conversation content is read out or sent anywhere

```bash
git clone https://github.com/hfliyc-collab/ai-activity.git && cd ai-activity && ./install.sh
```

macOS 12+: run `./install.sh`; on first run, allow Automation access to your browsers and enable “Allow JavaScript from Apple Events” in Safari (Settings › Developer) and Chrome (View › Developer).

Windows 10/11: double-click `install.bat`, then load the unpacked extension from `%LOCALAPPDATA%\AIStatus\extension` in `chrome://extensions` or `edge://extensions` (required on Windows, optional on macOS).
