#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust Tauri 2 桌面框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_tauri.py   (tauri 2.x：应用外壳 = 系统 WebView 前端 + Rust 后端 + IPC)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust-tauri桌面框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
TAU = ("#b45309", "#fffbeb")    # tauri amber（主色，与横评一致）
FE = ("#0284c7", "#f0f9ff")     # frontend 天蓝
CORE = ("#4338ca", "#eef2ff")   # Rust core 靛
IPC = ("#7c3aed", "#f5f3ff")    # IPC 紫
SEC = ("#dc2626", "#fef2f2")    # security 红
WV = ("#0d9488", "#f0fdfa")     # webview 青
GRN = ("#15803d", "#f0fdf4")    # green
GRY = ("#475569", "#f1f5f9")    # slate
CODEBG = "#1e293b"
CODEFG = "#d6deeb"


def esc(s):
    return html.escape(str(s), quote=True)


def b64img(svg_str, alt):
    ET.fromstring(svg_str)
    b = base64.b64encode(svg_str.encode("utf-8")).decode("ascii")
    return ('<p align="center"><img alt="' + esc(alt) + '" '
            'style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" '
            'src="data:image/svg+xml;base64,' + b + '"></p>')


MARK = ('<marker id="a" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker>')


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
            f'<defs>{MARK}</defs><rect width="{w}" height="{h}" fill="{BG}"/>' + body + '</svg>')


def box(x, y, w, h, title, lines, col, tcol="#fff"):
    st, fl = col
    out = ['<g>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fl}" stroke="{st}" stroke-width="1.7"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="8" fill="{st}"/>',
           f'<rect x="{x}" y="{y+14}" width="{w}" height="8" fill="{st}"/>',
           f'<text x="{x+10}" y="{y+16}" font-family="{MONO}" font-size="11.5" font-weight="700" fill="{tcol}">{esc(title)}</text>']
    yy = y + 22 + 14
    for ln in lines:
        out.append(f'<text x="{x+10}" y="{yy}" font-family="{SANS}" font-size="10" fill="#1e293b">{esc(ln)}</text>')
        yy += 14
    out.append('</g>')
    return "".join(out)


def arrow(x1, y1, x2, y2, label="", col="#64748b", dash="5 3", curve=False):
    if curve:
        d = f"M {x1} {y1} C {x1} {(y1+y2)/2} {x2} {(y1+y2)/2} {x2} {y2}"
    else:
        d = f"M {x1} {y1} L {x2} {y2}"
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    out = ['<g>', f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" '
           f'stroke-dasharray="{dash}" marker-end="url(#a)"/>']
    if label:
        lw = 6.6 * len(label) + 12
        out.append(f'<rect x="{mx-lw/2:.0f}" y="{my-9:.0f}" width="{lw}" height="16" rx="4" fill="#fff" '
                   f'fill-opacity="0.95" stroke="#cbd5e1" stroke-width="0.7"/>')
        out.append(f'<text x="{mx:.0f}" y="{my+3:.0f}" text-anchor="middle" font-family="{MONO}" '
                   f'font-size="9" fill="#334155">{esc(label)}</text>')
    out.append('</g>')
    return "".join(out)


def caption(w, y, text):
    return (f'<text x="{w/2:.0f}" y="{y}" text-anchor="middle" font-family="{SANS}" font-size="12.5" '
            f'fill="#334155">{esc(text)}</text>')


def t(x, y, s, size=10, col="#1e293b", anchor="start", weight="400", font=SANS):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" '
            f'font-size="{size}" font-weight="{weight}" fill="{col}">{esc(s)}</text>')


def win(x, y, w, h, title, body_fill="#ffffff", bar=TAU[0]):
    out = ['<g>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{body_fill}" stroke="#cbd5e1" stroke-width="1.4"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="9" fill="{bar}"/>',
           f'<rect x="{x}" y="{y+17}" width="{w}" height="9" fill="{bar}"/>']
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{x+15+i*15}" cy="{y+13}" r="4.5" fill="{c}"/>')
    out.append(f'<text x="{x+w/2}" y="{y+17}" text-anchor="middle" font-family="{MONO}" '
               f'font-size="11" font-weight="700" fill="#fff">{esc(title)}</text>')
    out.append('</g>')
    return "".join(out)


def pill(x, y, w, s, fill=TAU[0], tcol="#fff", h=26):
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2:.0f}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{y+h/2+3.5:.0f}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="11" font-weight="700" fill="{tcol}">{esc(s)}</text></g>')


def chip(x, y, w, s, fill, tcol, h=26, r=6):
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{y+h/2+3.5:.0f}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="11" font-weight="600" fill="{tcol}">{esc(s)}</text></g>')


def field(x, y, w, s, h=28, placeholder=True, bg="#fff", border="#cbd5e1", fg=None):
    col = fg if fg else ("#94a3b8" if placeholder else "#1e293b")
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{bg}" '
            f'stroke="{border}" stroke-width="1.3"/>'
            f'<text x="{x+10}" y="{y+h/2+4:.0f}" font-family="{SANS}" font-size="11" fill="{col}">{esc(s)}</text></g>')


def slug(t_):
    out = []
    for ch in t_.lower():
        if ch == ' ':
            out.append('-')
        elif ch == '-' or ch.isalnum():
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- FIG 1 应用外壳架构
def fig_arch():
    W, H = 940, 430
    b = []
    b.append(box(70, 60, 330, 96, "前端（WebView 进程）", [
        "HTML/CSS/JS：React · Vue · Svelte…", "或 Rust→WASM：Leptos · Yew · Dioxus",
        "调 @tauri-apps/api 与后端通信"], FE))
    b.append(box(540, 60, 330, 96, "Rust Core 进程", [
        "#[tauri::command] 业务逻辑", "窗口/托盘/菜单/文件/网络/DB",
        "插件生态 · 完整系统能力"], CORE))
    b.append(arrow(400, 92, 540, 92, "invoke / 事件", IPC[0]))
    b.append(arrow(540, 122, 400, 122, "返回 / 推送", IPC[0]))
    b.append(t(470, 178, "IPC（进程边界）", 11, IPC[0], "middle", "700", MONO))
    b.append(box(70, 220, 360, 74, "Tauri：用系统 WebView", [
        "不打包浏览器引擎（借系统的）", "安装包常见个位数 MB"], TAU))
    b.append(box(540, 220, 330, 74, "Electron（对照）", [
        "打包整个 Chromium + Node", "包体 80–150MB 起，内存数百 MB"], GRY))
    b.append(t(470, 260, "VS", 15, "#94a3b8", "middle", "700"))
    b.append(caption(W, 340, "Tauri 不是 GUI 工具包，而是「壳 + IPC + 安全 + 打包」：UI 交给系统 WebView 里的任意 Web 前端，逻辑放 Rust 进程"))
    b.append(caption(W, 362, "一句话：Electron 的正统继承人，减去 150MB 的 Chromium"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 双进程+IPC
def fig_ipc():
    W, H = 940, 420
    b = []
    b.append(box(60, 70, 250, 260, "前端（WebView）", [
        "任意 Web 框架 / WASM", "", "· invoke('cmd', args)",
        "· listen('evt', cb)", "· emit('evt', data)", "· new Channel()", "",
        "UI 状态可在前端", "或全交给 Rust"], FE))
    b.append(box(630, 70, 250, 260, "Rust Core", [
        "#[tauri::command] fns", "", "· 返回值（JSON）",
        "· app.emit(...)", "· Channel.send(...)", "· State / 插件 / 系统能力", "",
        "重活/密钥/文件", "都在这一侧"], CORE))
    b.append(arrow(310, 110, 630, 110, "① Command：invoke → #[command] → 返回", IPC[0]))
    b.append(arrow(630, 165, 310, 165, "", IPC[0]))
    b.append(arrow(310, 165, 630, 165, "② Event：emit / listen（双向广播）", IPC[0]))
    b.append(arrow(630, 235, 310, 235, "③ Channel：Rust → 前端 流式推送", WV[0]))
    b.append(arrow(310, 290, 630, 290, "④ Raw Payload：二进制直传（绕 JSON）", TAU[0]))
    b.append(caption(W, 372, "四种 IPC：Command（请求/响应）、Event（广播订阅）、Channel（流式推送）、Raw Payload（二进制不走 JSON，大文件/图像不卡桥）"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 命令流
def fig_command():
    W, H = 940, 380
    b = []
    b.append(box(50, 90, 250, 90, "前端 JS/TS", [
        "import { invoke }", "  from '@tauri-apps/api/core';",
        "await invoke('greet',", "  { firstName: '张三' })"], FE))
    b.append(box(360, 90, 220, 90, "IPC 序列化", [
        "参数 → JSON", "命令名路由", "（args 用 camelCase）"], IPC))
    b.append(box(640, 90, 250, 90, "Rust 命令", [
        "#[tauri::command]", "fn greet(first_name: String,",
        "  state: State<T>)", "  -> Result<String, String>"], CORE))
    b.append(arrow(300, 120, 360, 120, "调用", FE[0]))
    b.append(arrow(580, 120, 640, 120, "路由", IPC[0]))
    b.append(arrow(640, 210, 300, 210, "返回值（JSON）→ Promise resolve", GRN[0]))
    b.append(box(140, 255, 660, 74, "两条硬规则 + 一个便利", [
        "· 参数在 JS 侧用 camelCase（Rust first_name ↔ JS firstName）；返回值必须能 JSON 序列化",
        "· 特殊参数 State / Window / AppHandle 由宏自动注入，前端看不见（放普通参数之前）"], TAU))
    b.append(caption(W, 356, "命令 = 注册进 generate_handler! 的 Rust 函数；前端 invoke 名字调用、await 拿返回。可失败就返回 Result<T, String>"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 事件与 Channel
def fig_event():
    W, H = 940, 400
    b = []
    # 事件双向
    b.append(box(70, 60, 250, 80, "Rust", ["app.emit(\"progress\", 50)", "app.emit_to(\"main\", …)"], CORE))
    b.append(box(620, 60, 250, 80, "前端", ["listen('progress', cb)", "emit('front-evt', data)"], FE))
    b.append(arrow(320, 88, 620, 88, "emit → listen（广播）", IPC[0]))
    b.append(arrow(620, 118, 320, 118, "前端也能 emit（双向）", IPC[0]))
    # Channel 流式
    b.append(box(70, 200, 250, 80, "Rust 命令", ["on_progress: Channel<u32>", "on_progress.send(p)  循环"], CORE))
    b.append(box(620, 200, 250, 80, "前端", ["ch.onmessage = p => …", "invoke('dl', { onProgress: ch })"], FE))
    for i in range(5):
        xx = 330 + i * 56
        b.append(arrow(xx, 240, xx + 40, 240, "", WV[0], "2 2"))
    b.append(t(470, 300, "Channel：Rust → 前端 连续流（进度/日志/大数据分片）", 11, WV[0], "middle", "700"))
    b.append(caption(W, 356, "Command 是一问一答；Event 是广播订阅（双向）；Channel 是单向流式推送——按「一次性调用 / 持续通知 / 连续流」三种场景选"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 安全模型
def fig_security():
    W, H = 940, 450
    b = []
    b.append(box(310, 44, 320, 40, "默认拒绝（Default-Deny）", [], SEC))
    b.append(t(470, 100, "没显式授予的能力，前端一律调不到", 11, SEC[0], "middle", "700"))
    b.append(box(120, 130, 700, 66, "Capabilities（能力文件）", [
        "src-tauri/capabilities/*.json：把「权限」绑到具体窗口/WebView（按 label）",
        "\"windows\": [\"main\"], \"permissions\": [ … ], \"platforms\": [\"android\",\"iOS\"]"], TAU))
    b.append(arrow(470, 196, 470, 214))
    b.append(box(120, 214, 340, 66, "Permissions（权限）", [
        "命令级开关：allow-/deny-", "core:default 是基线",
        "（不给则连命令都调不了）"], CORE))
    b.append(box(480, 214, 340, 66, "Scopes（作用域）", [
        "参数级校验：路径/域名白名单", "如 fs 只放行 $APPDATA/**",
        "http 只放行 *.example.com"], IPC))
    b.append(box(150, 310, 640, 68, "对 Electron 的代差", [
        "Electron 渲染进程默认能力很大；Tauri 默认全禁、逐项显式授予 + CSP 注入，",
        "插件也纳入同一权限体系——最小权限，企业合规友好"], GRN))
    b.append(caption(W, 402, "三层：Capabilities 绑窗口、Permissions 开命令、Scopes 限参数；全默认拒绝。这套安全模型是 Tauri 相对 Electron 的核心代差"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 前端随便选
def fig_frontend():
    W, H = 940, 410
    b = []
    b.append(box(380, 180, 180, 84, "Tauri 壳", ["系统 WebView", "+ Rust 后端", "+ IPC + 打包"], TAU))
    b.append(box(70, 58, 220, 72, "JS/TS 框架", ["React · Vue · Svelte", "Solid · Angular · 原生"], FE))
    b.append(box(650, 58, 230, 72, "Rust → WASM", ["Leptos · Yew", "Dioxus（全 Rust 前端）"], CORE))
    b.append(box(70, 300, 220, 72, "静态站点生成器", ["Next/Nuxt/SvelteKit", "（SSG 产物）"], WV))
    b.append(box(650, 300, 230, 72, "任意 CSS 生态", ["Tailwind · UI 组件库", "现成设计系统"], GRN))
    b.append(arrow(380, 205, 290, 100, "", FE[0]))
    b.append(arrow(560, 205, 650, 100, "", CORE[0]))
    b.append(arrow(380, 240, 290, 330, "", WV[0]))
    b.append(arrow(560, 240, 650, 330, "", GRN[0]))
    b.append(caption(W, 392, "Tauri 不规定 UI 范式：前端框架随便选，Web 资产/设计系统全量复用；甚至 Dioxus/Leptos 也能当它的前端——组合而非竞争"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 7 多端
def fig_multi():
    W, H = 940, 410
    b = []
    b.append(box(385, 175, 170, 80, "一个 Tauri 项目", ["同一套前端", "+ Rust 核心"], TAU))
    b.append(box(70, 56, 240, 78, "桌面", [
        "Win / macOS / Linux", "msi·nsis / dmg·app / deb·rpm·AppImage"], FE))
    b.append(box(640, 56, 240, 78, "移动（2.0 转正）", [
        "iOS / Android", "tauri ios/android dev"], CORE))
    b.append(box(70, 300, 240, 72, "开发", [
        "tauri dev（前端 HMR", "+ Rust 重编）"], WV))
    b.append(box(640, 300, 240, 72, "打包", [
        "tauri build", "apk / aab · ipa · 桌面安装包"], GRN))
    b.append(arrow(385, 200, 310, 100, "desktop", FE[0]))
    b.append(arrow(555, 200, 640, 100, "mobile", CORE[0]))
    b.append(arrow(385, 235, 310, 330, "dev", WV[0]))
    b.append(arrow(555, 235, 640, 330, "build", GRN[0]))
    b.append(caption(W, 392, "Tauri 2 把桌面与移动统一进一套项目结构（cargo-mobile2 底座）；iOS/Android 在 2.0 稳定转正——五框架里移动端最成熟的之一"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 8 Todo 界面
def fig_todo():
    W, H = 640, 460
    b = []
    b.append(win(80, 40, 480, 380, "Todos — Tauri"))
    b.append(t(105, 84, "待办事项", 16, "#0f172a", "start", "700"))
    b.append(field(105, 100, 320, "要做点什么？", 32))
    b.append(pill(438, 102, 96, "添加", TAU[0], "#fff", 28))
    b.append(f'<line x1="105" y1="150" x2="534" y2="150" stroke="#e2e8f0" stroke-width="1.4"/>')
    items = [("写 tauri 使用说明", True), ("画 8 张 SVG 图", True), ("跑 gen_tauri.py 校验", False)]
    yy = 166
    for txt_, done in items:
        if done:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="{TAU[0]}"/>')
            b.append(f'<path d="M 116 {yy+10} l 4 4 l 8 -9" stroke="#fff" stroke-width="2.2" fill="none"/>')
            b.append(f'<text x="142" y="{yy+15}" font-family="{SANS}" font-size="12.5" fill="#94a3b8" '
                     f'text-decoration="line-through">{esc(txt_)}</text>')
        else:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="#fff" stroke="#94a3b8" stroke-width="1.8"/>')
            b.append(t(142, yy + 15, txt_, 12.5, "#1e293b"))
        b.append(chip(494, yy - 2, 40, "删除", SEC[1], SEC[0], 24))
        yy += 42
    b.append(f'<line x1="105" y1="306" x2="534" y2="306" stroke="#e2e8f0" stroke-width="1.4"/>')
    b.append(t(112, 330, "共 3 项 · 已完成 2 项", 12, "#64748b", "start", "700"))
    b.append(t(105, 388, "前端渲染（任意 Web 框架），数据/逻辑在 Rust——经 invoke 通信", 9.5, "#94a3b8", "start"))
    b.append(caption(W, 434, "第 13 节成品：Web 前端做视图 + Rust 命令持状态，invoke 往返；UI 可复用任意 Web 资产"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_arch(), "图1：Tauri 应用外壳架构")
IMG2 = b64img(fig_ipc(), "图2：双进程与四种 IPC")
IMG3 = b64img(fig_command(), "图3：命令流 invoke↔command")
IMG4 = b64img(fig_event(), "图4：事件与 Channel")
IMG5 = b64img(fig_security(), "图5：capabilities 安全模型")
IMG6 = b64img(fig_frontend(), "图6：前端随便选")
IMG7 = b64img(fig_multi(), "图7：一个项目多端")
IMG8 = b64img(fig_todo(), "图8：Todo 应用界面")

SECS = [
    "一、Tauri 是什么：不是 GUI 库，是应用外壳",
    "二、安装与第一个程序",
    "三、架构：双进程 + IPC",
    "四、命令 Commands：tauri::command ↔ invoke",
    "五、特殊参数与状态：Window · AppHandle · State",
    "六、事件与 Channel：广播与流式推送",
    "七、安全模型：capabilities · permissions · scopes",
    "八、前端随便选：任意 Web 框架",
    "九、系统 WebView：三平台内核与差异",
    "十、插件生态：fs · shell · dialog · updater",
    "十一、打包与分发",
    "十二、移动端：iOS / Android",
    "十三、完整实例：待办事项 Todo",
    "十四、常见坑速查",
    "十五、与 CMX 工作区的呼应",
    "十六、版本与参考资源",
]


def main():
    D = []
    A = D.append
    A("# Rust Tauri 2 桌面框架详细使用说明")
    A("")
    A("> **定位**：Tauri **不是 GUI 工具包，是应用外壳**——UI 交给**系统 WebView** 里的**任意 Web 前端**（React/Vue/Svelte，或 Rust→WASM 的 Leptos/Yew/Dioxus），逻辑放 **Rust 进程**，中间用 **IPC**（命令/事件/Channel/二进制）通信。一句话：**Electron 的正统继承人，减去 150MB 的 Chromium**。")
    A("> **和前四位不是一类东西**：iced/egui 自绘、Dioxus 桌面走 WebView、Slint 用 DSL——它们都「画 UI」；Tauri **不画 UI**，它管「壳 + IPC + 安全 + 打包」，渲染整个托付给系统 WebView。")
    A("> **版本基线（2026-09）**：Tauri **2.x**（2.0 于 2024-10 稳定）。亮点：iOS/Android 转正、IPC v2（Channel + Raw Payload）、capabilities/permissions 安全模型。")
    A("> **一句话取舍**：给「复用 Web 前端团队/已有 Web 资产、要最小包体、要移动端、要企业级安全」的团队——**对已有 Web 资产的团队，它往往是把存量变现的最短路径**。短板：三平台 WebView 内核不同、性能上限受 WebView 制约。")
    A("> **图**：8 张内嵌 base64 SVG。所有易变 API 处均标注「以官方文档对应版本为准」。")
    A("")
    A("> 姊妹篇：iced（Elm·自绘）、egui（立即·自绘）、Dioxus（组件/信号·WebView）、Slint（DSL·可下沉 MCU）四份使用说明 + `docs/20260920_Rust桌面GUI框架横评.md`（五框架横评）。**本篇是与 CMX 最对口的一个（第 15 节）。**")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    for i, s in enumerate(SECS, 1):
        A(f"{i}. [{s}](#{slug(s)})")
    A("")
    A("---")
    A("")
    # 一
    A(f"## {SECS[0]}")
    A("")
    A(IMG1)
    A("")
    A("把 Tauri 和另外四个放一起横比，容易得出错误结论——它其实是**另一层**的东西：")
    A("")
    A("- **它不画 UI**：渲染整个交给系统 WebView（Windows 的 WebView2 / macOS 的 WKWebView / Linux 的 WebKitGTK）。你写的 UI 就是**普通网页**。")
    A("- **两个进程**：前端（WebView）跑 UI；Rust Core 跑逻辑、碰系统能力（文件/网络/DB/密钥）；中间隔着 **IPC** 进程边界。")
    A("- **包体最小**：不打包浏览器引擎（借系统的），安装包常见**个位数 MB**——对照 Electron 打包整个 Chromium+Node 的 80–150MB。")
    A("- **前端随便选**：React/Vue/Svelte/Solid/原生，甚至 **Dioxus/Leptos**（Rust→WASM）都能当它的前端（第 8 节）。")
    A("")
    A("> 所以正确的心智是：**Tauri = 壳 + IPC + 安全 + 打包**。UI 质感的天花板 = Web 的天花板（很高），设计资源全量复用；代价是渲染受系统 WebView 制约、三平台有内核差异（第 9 节）。")
    A("")
    # 二
    A(f"## {SECS[1]}")
    A("")
    A("用官方脚手架起项目（选前端框架、包管理器）：")
    A("")
    A("```bash")
    A(r'''npm create tauri-app@latest       # 或 cargo install create-tauri-app && cargo create-tauri-app
cd my-app
npm install
npm run tauri dev                 # 开发：前端 HMR + Rust 重编，一条龙
npm run tauri build               # 出安装包''')
    A("```")
    A("")
    A("项目结构：前端在根目录（任意 Web 项目），Rust 在 `src-tauri/`。`src-tauri/Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }

[build-dependencies]
tauri-build = "2"''')
    A("```")
    A("")
    A("`src-tauri/src/lib.rs`——定义命令 + 启动（2.x 脚手架把 app 放 `lib.rs` 的 `run()`，便于移动端复用）：")
    A("")
    A("```rust")
    A(r'''// 一个命令 = 一个带 #[tauri::command] 的普通 Rust 函数
#[tauri::command]
fn greet(name: &str) -> String {
    format!("你好, {name}!")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]   // 移动端入口
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet])   // 注册命令（只能一次调用）
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}''')
    A("```")
    A("")
    A("`src-tauri/src/main.rs` 只是转调：")
    A("")
    A("```rust")
    A(r'''fn main() {
    app_lib::run();   // app_lib 是你 crate 的名字（见 Cargo.toml）
}''')
    A("```")
    A("")
    A("前端里调用这个命令（任意框架，这里用原生 JS）：")
    A("")
    A("```javascript")
    A(r'''import { invoke } from '@tauri-apps/api/core';   // v2 从 /core 导入（不是 v1 的 /tauri）

const msg = await invoke('greet', { name: '世界' });   // 按命令名调用，await 拿返回
console.log(msg);   // 你好, 世界!''')
    A("```")
    A("")
    A("> 对比前四家：它们让你用 Rust（或 DSL）**写 UI**；Tauri 让你写**网页**做 UI、写 **Rust 命令**做逻辑，两者用 `invoke` 连起来。中文/IME/排版全由系统 WebView 提供，**省心**（同 Dioxus 桌面）。")
    A("")
    # 三
    A(f"## {SECS[2]}")
    A("")
    A(IMG2)
    A("")
    A("Tauri 的核心是**两个进程 + 四种 IPC**：")
    A("")
    A("| IPC | 方向 | 场景 |")
    A("|---|---|---|")
    A("| **Command** | 前端 → Rust → 返回 | 一问一答：调用后端能力、取数据 |")
    A("| **Event**（`emit`/`listen`） | 双向广播 | 通知：状态变更、后台完成、前端广播 |")
    A("| **Channel** | Rust → 前端 流式 | 连续推送：下载进度、日志流、大数据分片 |")
    A("| **Raw Payload** | 二进制直传 | 大文件/图像：绕开 JSON 序列化，不卡桥 |")
    A("")
    A("> **进程边界要记牢**：前端碰不到文件系统、密钥、DB——这些都在 Rust 侧，前端只能**经 IPC 请求**。这既是架构约束，也是安全边界（第 7 节）。高频小消息记得合批，别一帧几百次 `invoke`。")
    A("")
    # 四
    A(f"## {SECS[3]}")
    A("")
    A(IMG3)
    A("")
    A("命令是最常用的 IPC：**带 `#[tauri::command]` 的 Rust 函数**，注册进 `generate_handler!`，前端 `invoke` 调用。")
    A("")
    A("```rust")
    A(r'''use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct User { name: String, age: u32 }

// 返回值必须能 JSON 序列化
#[tauri::command]
fn get_user(id: u32) -> User {
    User { name: "张三".into(), age: 30 }
}

// 可失败的命令返回 Result<T, E>（E 通常用 String，前端拿到 reject）
#[tauri::command]
async fn read_config(path: String) -> Result<String, String> {
    tokio::fs::read_to_string(&path).await.map_err(|e| e.to_string())
}''')
    A("```")
    A("")
    A("```javascript")
    A(r'''import { invoke } from '@tauri-apps/api/core';

const user = await invoke('get_user', { id: 1 });          // { name, age }

try {
    const cfg = await invoke('read_config', { path: '/etc/app.toml' });
} catch (err) {
    console.error('命令失败:', err);   // Result 的 Err 变成 JS 异常
}''')
    A("```")
    A("")
    A("三条要点：")
    A("")
    A("- **只能一次 `generate_handler!`**：所有命令写进同一个宏调用里（多次调用只有最后一个生效）。")
    A("- **参数名 camelCase**：Rust 的 `first_name` 前端要写 `firstName`。")
    A("- **无编译期检查**：命令忘了注册、前端名字写错，都是**运行时静默失败**——排查 IPC 问题先查这两处。")
    A("")
    # 五
    A(f"## {SECS[4]}")
    A("")
    A("命令可以声明**特殊参数**，由宏自动注入、对前端不可见——用来拿窗口句柄、App 句柄、共享状态：")
    A("")
    A("```rust")
    A(r'''use std::sync::Mutex;

#[derive(Default)]
struct AppState { count: i64 }

// 特殊参数放普通参数之前；前端看不到它们
#[tauri::command]
fn bump(delta: i64, state: tauri::State<Mutex<AppState>>, window: tauri::Window) -> i64 {
    let mut s = state.lock().unwrap();
    s.count += delta;
    println!("来自窗口: {}", window.label());
    s.count
}

pub fn run() {
    tauri::Builder::default()
        .manage(Mutex::new(AppState::default()))   // 注册全局状态
        .invoke_handler(tauri::generate_handler![bump])
        .run(tauri::generate_context!())
        .unwrap();
}''')
    A("```")
    A("")
    A("| 特殊参数 | 作用 |")
    A("|---|---|")
    A("| `tauri::State<T>` | 全局共享状态（需先 `.manage(T)`）；可变态用 `Mutex`/`RwLock` |")
    A("| `tauri::Window` / `WebviewWindow` | 触发命令的窗口句柄 |")
    A("| `tauri::AppHandle` | 全局 App 句柄（发事件、开窗、访问插件） |")
    A("")
    A("> 状态管理原则：只读配置**不用锁**；要改用 `std::sync::Mutex`（读多写少换 `RwLock`）；要和后台线程共享用 `State<'_, Arc<T>>`。异步命令若借用了 `State`/`&str`，返回类型要写成 `Result<T, E>`（生命周期约束）。")
    A("")
    # 六
    A(f"## {SECS[5]}")
    A("")
    A(IMG4)
    A("")
    A("命令是一问一答；要**主动通知**或**流式推送**，用事件和 Channel。")
    A("")
    A("**事件（广播/订阅，双向）**：")
    A("")
    A("```rust")
    A(r'''use tauri::{AppHandle, Emitter};

#[tauri::command]
fn start_job(app: AppHandle) {
    app.emit("progress", 50).unwrap();            // 广播给所有监听者
    app.emit_to("main", "job-done", "ok").unwrap();  // 只发给 label=main 的窗口
}''')
    A("```")
    A("")
    A("```javascript")
    A(r'''import { listen, emit } from '@tauri-apps/api/event';

const unlisten = await listen('progress', (e) => console.log('进度', e.payload));
await emit('front-event', { hello: 'rust' });   // 前端也能发事件
// 不用了记得 unlisten()''')
    A("```")
    A("")
    A("**Channel（Rust → 前端，流式）**——适合进度、日志、大数据分片：")
    A("")
    A("```rust")
    A(r'''use tauri::ipc::Channel;

#[tauri::command]
fn download(url: String, on_progress: Channel<u32>) {
    for p in (0..=100).step_by(10) {
        on_progress.send(p).unwrap();   // 连续往前端推
    }
}''')
    A("```")
    A("")
    A("```javascript")
    A(r'''import { Channel, invoke } from '@tauri-apps/api/core';

const ch = new Channel();
ch.onmessage = (p) => console.log('已下载', p, '%');
await invoke('download', { url: '...', onProgress: ch });''')
    A("```")
    A("")
    A("> 选型口诀：**一次性调用 → Command；持续通知/多方订阅 → Event；单向连续流 → Channel**。三者覆盖了前后端通信的绝大多数场景。")
    A("")
    # 七
    A(f"## {SECS[6]}")
    A("")
    A(IMG5)
    A("")
    A("**这是 Tauri 相对 Electron 的核心代差**：v2 用 **capabilities / permissions / scopes** 三层、**默认拒绝**的访问控制取代了 v1 的 allowlist。")
    A("")
    A("- **Permissions（权限）**：命令级开关（`allow-*` / `deny-*`）。基线是 **`core:default`**——**不给它，前端连命令都调不了**。")
    A("- **Scopes（作用域）**：参数级校验，如 `fs` 只放行 `$APPDATA/**`、`http` 只放行 `*.example.com`。")
    A("- **Capabilities（能力）**：把权限**绑到具体窗口/WebView**（按 `label`），JSON/TOML 放 `src-tauri/capabilities/`。")
    A("")
    A("```json")
    A(r'''// src-tauri/capabilities/default.json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "主窗口能力",
  "windows": ["main"],
  "permissions": [
    "core:default",              // 基线：IPC 调用 + 事件 + 窗口基础
    "dialog:allow-open",         // 插件权限：允许打开文件对话框
    "fs:allow-read-text-file"    // 只给读文本文件
  ],
  "platforms": ["windows", "macOS", "linux"]
}''')
    A("```")
    A("")
    A("| 层 | 管什么 | 例子 |")
    A("|---|---|---|")
    A("| Capabilities | 哪个窗口能用哪些权限 | `\"windows\": [\"main\"]` |")
    A("| Permissions | 允许/禁止哪些命令 | `core:default` · `fs:allow-read-text-file` |")
    A("| Scopes | 命令能操作哪些资源 | 路径 `$APPDATA/**` · 域名 `*.example.com` |")
    A("")
    A("> **默认全禁、逐项显式授予**（外加 CSP 注入），插件也纳入同一体系——最小权限、企业合规友好。**无编译期检查**：加了插件忘了加权限 → 运行时静默失败或报权限错（这是 v2 头号坑）。注意：core 权限要带 `core:` 前缀（`core:event:default`）。")
    A("")
    # 八
    A(f"## {SECS[7]}")
    A("")
    A(IMG6)
    A("")
    A("Tauri **不规定 UI 范式**——它只提供壳和 IPC，前端你随便选：")
    A("")
    A("- **JS/TS 框架**：React、Vue、Svelte、Solid、Angular，或原生。任意 CSS 生态（Tailwind、组件库、现成设计系统）全量复用。")
    A("- **Rust → WASM**：Leptos、Yew，甚至 **Dioxus**——想全 Rust 也行。")
    A("- **静态站点生成器**：Next/Nuxt/SvelteKit 的 SSG 产物直接装进去。")
    A("")
    A("```javascript")
    A(r'''// tauri.conf.json 里只需告诉它前端怎么起、产物在哪
{
  "build": {
    "frontendDist": "../dist",           // 前端构建产物目录
    "devUrl": "http://localhost:5173",   // 开发服务器（Vite 等）
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  }
}''')
    A("```")
    A("")
    A("> 关键认知：**Dioxus / Leptos 与 Tauri 是组合关系，不是竞争**。你可以用 Dioxus 写全 Rust 前端，再套上 Tauri 的壳（拿到它的插件、打包、安全、移动端）。「选 Tauri」和「选前端框架」是两个独立决定。")
    A("")
    # 九
    A(f"## {SECS[8]}")
    A("")
    A("Tauri 用**系统自带的 WebView**，不打包引擎——这是包体小的原因，也是最大槽点来源：")
    A("")
    A("| 平台 | WebView 内核 |")
    A("|---|---|")
    A("| Windows | **WebView2**（Chromium 内核；老系统需分发 WebView2 Runtime） |")
    A("| macOS / iOS | **WKWebView**（Safari 内核） |")
    A("| Linux | **WebKitGTK**（常见坑位：依赖/兼容性） |")
    A("| Android | **Android System WebView** |")
    A("")
    A("要点与坑：")
    A("")
    A("- **三平台内核不同 → CSS/JS 行为有差异**，要留跨平台测试预算；Linux 的 WebKitGTK 是最常见麻烦点。")
    A("- **中文/IME/复杂排版省心**：系统浏览器引擎全包（同 Dioxus 桌面），没有 iced/egui 的字体坑。")
    A("- **性能上限受 WebView 制约**：重可视化用 canvas/WebGL；高频 IPC 要合批。")
    A("- **包体前提**：Windows 老系统需要 WebView2 Runtime（在线/离线引导，装完全局共享）。")
    A("")
    A("> 这一节的取舍和 Dioxus 桌面完全同类（都基于系统 WebView）；区别只在「UI 用 JS 还是 Rust 写」。要像素级三平台一致，得选自绘系（iced/egui/Slint）。")
    A("")
    # 十
    A(f"## {SECS[9]}")
    A("")
    A("Tauri 的系统能力大多以**官方插件**提供，按需装（`tauri add` 会同时装 Rust crate、JS 包、权限脚手架）：")
    A("")
    A("```bash")
    A(r'''npm run tauri add dialog        # 文件对话框
npm run tauri add fs            # 文件系统
npm run tauri add http          # HTTP 客户端
npm run tauri add notification  # 系统通知
npm run tauri add updater       # 自动更新''')
    A("```")
    A("")
    A("```javascript")
    A(r'''import { open } from '@tauri-apps/plugin-dialog';
import { readTextFile } from '@tauri-apps/plugin-fs';

const path = await open({ multiple: false });          // 弹出选文件
if (path) {
    const text = await readTextFile(path);             // 读它（需 fs 权限 + scope）
}''')
    A("```")
    A("")
    A("| 常用官方插件 | 能力 |")
    A("|---|---|")
    A("| `dialog` / `fs` | 文件对话框 / 文件系统 |")
    A("| `http` / `websocket` | 网络请求 / WS |")
    A("| `notification` / `shell` | 系统通知 / 执行命令 |")
    A("| `updater` / `store` | 自动更新 / 键值持久化 |")
    A("| `sql` / `stronghold` | 数据库 / 加密存储 |")
    A("")
    A("> 装插件后**别忘了在 capability 里加它的权限**（如 `dialog:allow-open`），否则前端调用会失败（第 7 节的头号坑）。插件生态是 Tauri 相对自绘框架的一大优势——大量系统集成开箱即用。")
    A("")
    # 十一
    A(f"## {SECS[10]}")
    A("")
    A("`tauri build` 一键出各平台安装包：")
    A("")
    A("| 平台 | 产物 |")
    A("|---|---|")
    A("| Windows | `.msi`（WiX） · `.exe`（NSIS） |")
    A("| macOS | `.dmg` · `.app`（支持签名/公证） |")
    A("| Linux | `.deb` · `.rpm` · `.AppImage` |")
    A("| iOS / Android | `.ipa` · `.apk` / `.aab` |")
    A("")
    A("```bash")
    A(r'''npm run tauri build                      # 当前平台安装包
npm run tauri build -- --target universal-apple-darwin   # macOS 通用二进制
# 更新器：配好签名密钥后，build 产出带签名的更新包 + latest.json''')
    A("```")
    A("")
    A("> 包体常见**个位数 MB**（不含浏览器引擎）。配合 `updater` 插件可做**增量自动更新**。签名/公证（尤其 macOS）要提前准备证书——这是发布环节的必做项。")
    A("")
    # 十二
    A(f"## {SECS[11]}")
    A("")
    A(IMG7)
    A("")
    A("**移动端在 Tauri 2.0 转正**：iOS / Android 与桌面**共用一套项目结构**（`cargo-mobile2` 底座）。")
    A("")
    A("```bash")
    A(r'''npm run tauri ios init          # 初始化 iOS 工程
npm run tauri android init      # 初始化 Android 工程
npm run tauri ios dev           # 起 iOS 模拟器/真机（前端 + Rust）
npm run tauri android dev       # 起安卓模拟器/真机
npm run tauri android build     # 出 apk / aab''')
    A("```")
    A("")
    A("要点：")
    A("")
    A("- **一套前端 + 一套 Rust 命令**，桌面与移动共享；平台差异用 `#[cfg(mobile)]` / capability 的 `platforms` 字段区分。")
    A("- **移动专属能力**（NFC、条码、生物识别…）由对应插件提供；capability 里按平台授权。")
    A("- **注意**：并非所有 core API 都在移动端可用；Android 上 iframe 与主窗难区分，远程源访问要格外小心。")
    A("")
    A("> 五框架里**移动端最成熟的就是 Tauri 2 和 Dioxus**；若 CMX 未来要「桌面 + 移动」同源，Tauri 是稳妥选择。")
    A("")
    # 十三
    A(f"## {SECS[12]}")
    A("")
    A(IMG8)
    A("")
    A("Tauri 的典型分工：**前端做视图，Rust 命令持状态/逻辑**。下面让 Rust 侧用 `State` 存待办，前端纯调 `invoke`。`src-tauri/src/lib.rs`：")
    A("")
    A("```rust")
    A(r'''use std::sync::Mutex;
use serde::{Serialize, Deserialize};

#[derive(Clone, Serialize, Deserialize)]
struct Todo { id: u64, text: String, done: bool }

#[derive(Default)]
struct Store { items: Vec<Todo>, next_id: u64 }

#[tauri::command]
fn list_todos(state: tauri::State<Mutex<Store>>) -> Vec<Todo> {
    state.lock().unwrap().items.clone()
}

#[tauri::command]
fn add_todo(text: String, state: tauri::State<Mutex<Store>>) -> Vec<Todo> {
    let mut s = state.lock().unwrap();
    let id = s.next_id;
    s.next_id += 1;
    s.items.push(Todo { id, text, done: false });
    s.items.clone()
}

#[tauri::command]
fn toggle_todo(id: u64, state: tauri::State<Mutex<Store>>) -> Vec<Todo> {
    let mut s = state.lock().unwrap();
    if let Some(t) = s.items.iter_mut().find(|t| t.id == id) { t.done = !t.done; }
    s.items.clone()
}

#[tauri::command]
fn remove_todo(id: u64, state: tauri::State<Mutex<Store>>) -> Vec<Todo> {
    let mut s = state.lock().unwrap();
    s.items.retain(|t| t.id != id);
    s.items.clone()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Mutex::new(Store::default()))
        .invoke_handler(tauri::generate_handler![list_todos, add_todo, toggle_todo, remove_todo])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}''')
    A("```")
    A("")
    A("前端（原生 JS，换任意框架同理）：")
    A("")
    A("```javascript")
    A(r'''import { invoke } from '@tauri-apps/api/core';

let todos = [];
const render = () => { /* 用 todos 重绘列表（React/Vue 里就是 setState） */ };

async function refresh()      { todos = await invoke('list_todos');            render(); }
async function add(text)      { todos = await invoke('add_todo', { text });    render(); }
async function toggle(id)     { todos = await invoke('toggle_todo', { id });   render(); }
async function remove(id)     { todos = await invoke('remove_todo', { id });   render(); }

refresh();   // 启动时拉一次''')
    A("```")
    A("")
    A("这套结构清楚展示了 Tauri 的分工：**状态与逻辑在 Rust（可持久化、可碰 DB/密钥），视图在前端（复用任意 Web 资产），二者经 `invoke` 往返**——就是图 8 那个界面。想把 UI 状态放前端也行（那 Rust 只提供必要的系统能力命令）。")
    A("")
    # 十四
    A(f"## {SECS[13]}")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 命令没注册 / 名字写错 | 前端 invoke 静默失败 | 查 `generate_handler!` 是否含它、名字是否一致 |")
    A("| 参数用了 snake_case | 参数收不到 | JS 侧一律 camelCase（`first_name`→`firstName`） |")
    A("| 忘了给权限 | 插件/命令调用报权限错 | capability 里加对应 permission（如 `dialog:allow-open`） |")
    A("| 没有 `core:default` | 前端连命令都调不了 | capability 的 permissions 加 `core:default` |")
    A("| `generate_handler!` 调多次 | 只有最后一个生效 | 所有命令写进同一个宏调用 |")
    A("| v1 的 import 路径 | 找不到 invoke | v2 从 `@tauri-apps/api/core` 导入 |")
    A("| Linux 白屏/跑不起 | 缺 WebKitGTK 依赖 | 装系统 WebKitGTK 开发库；留跨平台测试 |")
    A("| 高频 invoke | 卡顿 | 合批；大数据用 Channel / Raw Payload |")
    A("| 期待像素级三平台一致 | WebView 内核有差异 | 那是自绘系的活；Tauri 要为各 WebView 测兼容 |")
    A("| 返回了非 Serialize 类型 | 编译/序列化报错 | 命令返回值必须能 JSON 序列化 |")
    A("")
    # 十五
    A(f"## {SECS[14]}")
    A("")
    A("**本篇是与 CMX 最对口的一个**。对照本工作区（元数据驱动企业平台，前端已是成熟 npm workspace）：")
    A("")
    A("1. **`cmx-agent`（桌面智能体）若要长出 GUI：首选 Tauri 2**。横评（`docs/20260920_Rust桌面GUI框架横评.md`）的结论在这里落地——`frontend/` 已是成熟的 npm workspace（包名 `cmx-monorepo`），**UI5/Tabler 组件、双主题（`--sap*` 变量 + `data-cmx-skin`）等资产可原样复用进 WebView**，天然满足硬约束 #4（双主题通路兼容）。")
    A("2. **Rust 侧与现有 crate 同仓编译**：`cmx-agent` 已是 Rust 项目，Tauri 的命令层可直接调用平台既有能力，无需另起技术栈。")
    A("3. **IPC v2 适配企业数据量**：报表/图像/大结果集用 **Channel 流式**或 **Raw Payload 二进制**，绕开 JSON 序列化瓶颈。")
    A("4. **安全模型契合企业合规**：capabilities/permissions/scopes 的**最小权限、默认拒绝**，正是企业客户端该有的姿态。")
    A("5. **移动端有路**：若未来要 `cmx-agent` 移动版，Tauri 2 桌面/移动同源。")
    A("6. **可与 Dioxus 组合**：若想「前端也全 Rust」，用 Dioxus/Leptos 当 Tauri 前端（见 Dioxus 篇），兼得全 Rust 与 Tauri 的壳能力。")
    A("")
    A("> 五框架在 CMX 语境的定位：**Tauri = 面向用户的桌面产品首选（复用 Web 资产）；egui = 内部诊断面板；Dioxus = 未来若要 Rust 全栈前端；iced = 长寿命自绘产品；Slint = 未来若做嵌入式设备端**。当下最可能先落地的，就是 Tauri。")
    A("")
    # 十六
    A(f"## {SECS[15]}")
    A("")
    A("**版本基线（2026-09）**：Tauri **2.x**（2.0 于 2024-10 稳定，经 Radically Open Security 独立审计）。语义化版本纪律良好，是本系列里稳定性承诺最强的之一。")
    A("")
    A("| 资源 | 地址 | 说明 |")
    A("|---|---|---|")
    A("| 官网 & 指南 | v2.tauri.app | **成体系的官方文档**（本系列最全） |")
    A("| API（Rust） | docs.rs/tauri | 锁定你的版本看 |")
    A("| API（JS） | v2.tauri.app（`@tauri-apps/api`） | invoke/event/window… |")
    A("| 脚手架 | `npm create tauri-app@latest` | 选前端框架一键起 |")
    A("| 插件 | v2.tauri.app/plugin | 官方插件清单与权限 |")
    A("| 安全 | v2.tauri.app/security | capabilities/permissions/scopes 详解 |")
    A("")
    A("> 学习路径建议：`npm create tauri-app@latest` 选你熟悉的前端框架起项目，跑通 `greet` 命令，再依次接 State、事件、一个插件（如 dialog）、配 capability——每一步都对照本文。遇到「调用没反应」，**九成是命令没注册或权限没给**（第 14 节）。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **Tauri = 最小的壳，最大的自由**：不画 UI，只管「系统 WebView 前端 + Rust 后端 + IPC + 安全 + 打包」；前端随便选、包体个位数 MB、移动端转正、安全模型完备——Electron 的正统继承人减去 150MB Chromium。对**已有 Web 资产**的团队（比如 CMX），它是把存量变现的最短路径；代价是渲染受系统 WebView 制约、三平台要测兼容。")
    A("")
    A("> 参考：v2.tauri.app（指南/安全/插件/移动）、docs.rs/tauri。版本以 2026-09 的 2.x 线为准；凡涉及具体 API 与权限标识，请以官方对应版本文档为准，勿照抄 v1 教程（v2 的 import 路径、安全模型、移动端均有大改）。")

    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)

    # ---- 自校验 ----
    fences = txt.count("```")
    assert fences % 2 == 0, f"代码围栏不平衡: {fences}"
    n_img = txt.count("data:image/svg+xml;base64,")
    assert n_img == 8, f"图片数应为 8，实为 {n_img}"
    anchors = [slug(s) for s in SECS]
    heads = [slug(ln[3:]) for ln in txt.splitlines() if ln.startswith("## ") and ln != "## 目录"]
    missing = [a for a in anchors if a not in heads]
    assert not missing, f"目录锚点缺失: {missing}"
    print("output :", OUT)
    print("bytes  :", os.path.getsize(OUT), f"({os.path.getsize(OUT)/1024:.1f} KB)")
    print("svg    : 8 张（生成时已逐张 XML 校验）")
    print("images :", n_img, "(embedded base64)")
    print("fences :", fences, "(balanced)")
    print("anchors:", len(anchors), "/", len(anchors), "全部命中")


if __name__ == "__main__":
    main()
