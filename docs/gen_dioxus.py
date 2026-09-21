#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust Dioxus 桌面框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_dioxus.py   (dioxus 0.7.x：组件 + RSX + 信号；桌面 = 系统 WebView)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust-dioxus桌面框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
DIO = ("#0284c7", "#f0f9ff")   # dioxus sky（主色，与横评一致）
CMP = ("#7c3aed", "#f5f3ff")   # component 紫
SIG = ("#0d9488", "#f0fdfa")   # signal 青
RSX = ("#c2410c", "#fff7ed")   # rsx 橙
WEB = ("#b45309", "#fffbeb")   # webview 琥珀
SRV = ("#4338ca", "#eef2ff")   # server/fullstack 靛
GRN = ("#15803d", "#f0fdf4")   # green
DAN = ("#dc2626", "#fef2f2")   # danger red
GRY = ("#475569", "#f1f5f9")   # slate
CODEBG = "#1e293b"
CODEFG = "#d6deeb"


def esc(s):
    return html.escape(str(s), quote=True)


def b64img(svg_str, alt):
    ET.fromstring(svg_str)  # 生成即校验：XML 不平衡直接抛错
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


def win(x, y, w, h, title, body_fill="#ffffff", bar=DIO[0]):
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


def pill(x, y, w, s, fill=DIO[0], tcol="#fff", h=26):
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


# ---------------------------------------------------------------- FIG 1 三支柱
def fig_pillars():
    W, H = 940, 420
    b = []
    b.append(box(70, 66, 250, 156, "组件 Component", [
        "fn() -> Element", "· 就是个函数，返回 UI", "· #[component] 声明 Props",
        "· 可嵌套组合成组件树", "", "≈ React 组件"], CMP))
    b.append(box(345, 66, 250, 156, "RSX", [
        "声明式 UI（≈ JSX）", "rsx! { div { \"…\" } }", "· 元素 / 属性 / 子节点",
        "· 文本插值 {signal}", "· for / if 直接内联", "· 编译期检查，非字符串"], RSX))
    b.append(box(620, 66, 250, 156, "信号 Signal", [
        "响应式状态", "use_signal(|| 0)", "· 读 = 订阅，改 = 通知",
        "· Copy，随便传/进闭包", "· 细粒度：只重渲读它的", ""], SIG))
    b.append(arrow(195, 222, 360, 262, "", CMP[0]))
    b.append(arrow(470, 222, 470, 262, "", RSX[0]))
    b.append(arrow(745, 222, 580, 262, "", SIG[0]))
    b.append(box(230, 262, 480, 74, "React 的心智，Rust 的身体", [
        "组件 + Props + Hooks 的写法你会觉得眼熟；但状态用「信号」、",
        "更新靠「订阅」——不是虚拟 DOM 全树 diff，而是精确更新读了信号的那几处"], DIO))
    b.append(caption(W, 396, "Dioxus 三支柱：组件（函数）、RSX（声明 UI）、信号（响应式状态）。前端背景者上手极快，代价是框架年轻、版本间破坏性变更偏多"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 RSX 解剖
def fig_rsx():
    W, H = 940, 450
    b = []
    # 代码面板（深色）
    b.append(f'<rect x="45" y="55" width="545" height="350" rx="10" fill="{CODEBG}"/>')
    b.append(f'<circle cx="66" cy="76" r="4.5" fill="#ff5f57"/><circle cx="80" cy="76" r="4.5" fill="#febc2e"/><circle cx="94" cy="76" r="4.5" fill="#28c840"/>')
    lines = [
        (65, "rsx! {"),
        (85, "    div {"),
        (105, '        class: "card",'),
        (125, '        h1 { "计数: {count}" }'),
        (145, "        button {"),
        (165, "            onclick: move |_| count += 1,"),
        (185, '            "加一"'),
        (205, "        }"),
        (225, "        for t in todos.read().iter() {"),
        (245, '            li { key: "{t.id}", "{t.text}" }'),
        (265, "        }"),
        (285, "        if count() > 5 {"),
        (305, '            p { "多了！" }'),
        (325, "        }"),
        (345, "    }"),
        (365, "}"),
    ]
    for yy, s in lines:
        indent = len(s) - len(s.lstrip(' '))          # SVG 会折叠前导空格，改用 x 偏移还原缩进
        x = 62 + indent * 7.0
        b.append(f'<text x="{x:.0f}" y="{yy+35}" font-family="{MONO}" font-size="12" fill="{CODEFG}">{esc(s.lstrip(" "))}</text>')
    # 右侧标注
    calls = [
        (120, 122, "元素 / 组件", CMP[0]),
        (140, 160, "属性  key: value", DIO[0]),
        (160, 200, "文本插值 {signal}", SIG[0]),
        (200, 240, "事件  move |_| …", RSX[0]),
        (260, 290, "循环  for … {}", WEB[0]),
        (320, 340, "条件  if … {}", GRN[0]),
    ]
    for line_y, cy, lab, cc in calls:
        b.append(arrow(590, line_y, 636, cy, "", cc))
        b.append(f'<rect x="640" y="{cy-13}" width="250" height="26" rx="6" fill="#fff" stroke="{cc}" stroke-width="1.4"/>')
        b.append(t(652, cy + 4, lab, 11, "#1e293b", "start", "700"))
    b.append(caption(W, 432, "RSX 是编译期宏，不是字符串模板：元素/属性/子节点像 HTML，{signal} 插值、for/if 直接内联，且全程有 Rust 类型检查"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 信号细粒度
def fig_signal():
    W, H = 940, 400
    b = []
    b.append(box(60, 150, 190, 92, "Signal  count", [
        "use_signal(|| 0)", "改：count += 1", "（Copy，可到处传）"], SIG))
    b.append(box(350, 60, 210, 72, "组件 A", ["读了 count()", "→ count 变则重跑 ✓"], GRN))
    b.append(box(350, 158, 210, 72, "组件 B", ["也读了 count()", "→ 重跑 ✓"], GRN))
    b.append(box(350, 256, 210, 72, "组件 C", ["没读 count", "→ 不重跑 ✗（省了）"], GRY))
    b.append(arrow(250, 175, 350, 100, "订阅", SIG[0]))
    b.append(arrow(250, 196, 350, 194, "订阅", SIG[0]))
    b.append(arrow(250, 217, 350, 288, "无订阅", "#94a3b8", "2 4"))
    b.append(box(610, 120, 290, 150, "细粒度响应式", [
        "· 订阅发生在「读」的那一刻", "· 改信号 → 只通知读了它的组件",
        "· 没读的组件完全不重跑", "· 无需虚拟 DOM 全树 diff",
        "", "→ 天然的「精确更新」"], DIO))
    b.append(caption(W, 372, "关键机制：订阅在「读」处建立、更新只发给订阅者。这让 Dioxus 不靠全树 diff 也能精确更新——与 React 的心智像，机制更省"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 use_resource
def fig_resource():
    W, H = 940, 390
    b = []
    b.append(box(320, 46, 300, 66, "use_resource(|| async {…})", [
        "组件里发起异步任务；首帧立即返回", "任务在后台跑，读它的地方会订阅"], DIO))
    b.append(arrow(430, 112, 245, 150, "pending"))
    b.append(box(120, 150, 210, 74, "None", [
        "首次：还没结果", "rsx 里显示「加载中…」"], GRY))
    b.append(box(400, 150, 220, 74, "Some(Ok(data))", [
        "完成：拿到数据", "自动重渲染显示出来"], GRN))
    b.append(box(400, 258, 220, 66, "Some(Err(e))", [
        "失败：显示错误信息"], DAN))
    b.append(box(690, 150, 210, 74, ".restart()", [
        "手动重跑（如刷新按钮）", "依赖变化也会自动重跑"], WEB))
    b.append(arrow(330, 187, 400, 187, "await 完成", GRN[0]))
    b.append(arrow(240, 224, 470, 258, "出错", DAN[0]))
    b.append(arrow(620, 187, 690, 187, "", WEB[0]))
    b.append(arrow(795, 150, 560, 100, "重跑", WEB[0], curve=True))
    b.append(caption(W, 366, "读 resource 会订阅它：异步任务一完成，rsx 自动重渲染，无需手动 setState；.restart() 或依赖变化触发重跑"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 桌面=WebView
def fig_webview():
    W, H = 940, 458
    b = []
    # 中间管线
    pipe = [
        (60, "你的 RSX + 组件（Rust）", ["signal 驱动的声明式 UI"], CMP),
        (138, "VirtualDom（Rust 侧）", ["虚拟节点树 + 信号精确 diff"], DIO),
        (216, "dioxus-desktop", ["把变更喂给 WebView"], SIG),
        (294, "wry / tao", ["跨平台 WebView + 窗口封装"], GRY),
        (372, "系统 WebView 渲染", ["WebView2 · WKWebView · WebKitGTK"], WEB),
    ]
    for i, (yy, title, ln, col) in enumerate(pipe):
        b.append(box(300, yy, 340, 60, title, ln, col))
        if i < len(pipe) - 1:
            b.append(arrow(470, yy + 60, 470, yy + 78))
    # 右：与 Tauri 同底座
    b.append(box(670, 70, 250, 130, "与 Tauri 同底座", [
        "桌面渲染今天 = 系统 WebView，", "和 Tauri 用同一套 wry / tao。",
        "", "差异不在渲染，在：", "UI 全用 Rust RSX 写，", "而非 JS/HTML/前端框架"], WEB))
    # 左：Blitz 实验
    b.append(box(20, 240, 250, 130, "Blitz / Dioxus Native", [
        "（实验中的自绘路线）", "用 WGPU 直渲 HTML/CSS，",
        "Taffy 做布局引擎。", "成了才摆脱三平台", "WebView 差异——", "但目前仍是实验品"], CMP))
    b.append(box(670, 240, 250, 100, "Web 目标", [
        "同一份组件编到 WASM，", "直接跑在浏览器里", "（无 WebView 中间层）"], SRV))
    b.append(caption(W, 448, "诚实拆解：Dioxus 桌面的渲染今天托付给系统 WebView（与 Tauri 同底座），差异化在「UI 全用 Rust 写」；自绘的 Blitz 是未来、尚实验"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 样式与资源
def fig_style():
    W, H = 940, 400
    b = []
    b.append(box(50, 62, 290, 76, 'asset!("/assets/main.css")', [
        "编译期登记静态资源", "产出带哈希的 Asset 路径"], DIO))
    b.append(arrow(340, 100, 400, 100, "", RSX[0]))
    b.append(box(400, 62, 300, 76, "document::Stylesheet { href }", [
        "把 CSS 注入文档 <head>", "全局样式即刻生效"], RSX))
    b.append(box(50, 186, 400, 140, "主题 = CSS（Web 生态原样复用）", [
        "· class 切换：div { class: \"{theme}\" }",
        "· CSS 变量：color: var(--accent)",
        "· 媒体查询：@media (prefers-color-scheme: dark)",
        "· 内联样式：div { style: \"padding: 16px\" }",
        "· 也能上 Tailwind / 任意 CSS 框架"], SIG))
    b.append(box(500, 186, 400, 140, "对齐 CMX 双主题（硬约束 #4）", [
        "因为桌面就是 WebView，Web 那套照搬：",
        "· CMX 的 --sap* 变量可原样用",
        "· data-cmx-skin / data-cmx-skin-tone 切肤",
        "· 与 Tauri 前端复用同一套设计资产",
        "→ 天然满足「双主题通路兼容」"], GRN))
    b.append(caption(W, 376, "样式就是 CSS：asset! 登记 + Stylesheet 注入，主题走 class/CSS 变量/媒体查询。因为是 Web，CMX 现有的双主题资产可原样复用"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 7 一份代码多端
def fig_multi():
    W, H = 940, 430
    b = []
    b.append(box(385, 178, 170, 84, "你的组件", [
        "RSX + 信号", "一份代码", "（组件可跨端复用）"], DIO))
    b.append(box(70, 60, 210, 74, "Web（WASM）", [
        "编到 WebAssembly", "浏览器直接跑"], SRV))
    b.append(box(660, 60, 220, 74, "桌面（WebView）", [
        "wry / tao，本文重点", "三平台原生窗口"], WEB))
    b.append(box(70, 300, 210, 74, "移动（iOS/Android）", [
        "dx serve --platform android", "官方支持"], SIG))
    b.append(box(660, 300, 220, 74, "全栈（server functions）", [
        "#[server] 前后端同源", "Axum 底座"], CMP))
    b.append(arrow(385, 200, 280, 110, "web", SRV[0]))
    b.append(arrow(555, 200, 660, 110, "desktop", WEB[0]))
    b.append(arrow(385, 240, 280, 330, "mobile", SIG[0]))
    b.append(arrow(555, 240, 660, 330, "server", CMP[0]))
    b.append(caption(W, 406, "一份组件代码，dx serve 换 --platform 即切目标（web/desktop/android…）；server functions 让前后端写在同一个 crate 里，同源调用"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 8 Todo 界面
def fig_todo():
    W, H = 640, 450
    b = []
    b.append(win(80, 40, 480, 370, "Todos — Dioxus"))
    b.append(t(105, 84, "待办事项", 16, "#0f172a", "start", "700"))
    b.append(field(105, 100, 320, "要做点什么？（回车添加）", 32))
    b.append(pill(438, 102, 96, "添加", DIO[0], "#fff", 28))
    b.append(f'<line x1="105" y1="150" x2="534" y2="150" stroke="#e2e8f0" stroke-width="1.4"/>')
    items = [("写 dioxus 使用说明", True), ("画 8 张 SVG 图", True), ("跑 gen_dioxus.py 校验", False)]
    yy = 166
    for txt_, done in items:
        if done:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="{DIO[0]}"/>')
            b.append(f'<path d="M 116 {yy+10} l 4 4 l 8 -9" stroke="#fff" stroke-width="2.2" fill="none"/>')
            b.append(f'<text x="142" y="{yy+15}" font-family="{SANS}" font-size="12.5" fill="#94a3b8" '
                     f'text-decoration="line-through">{esc(txt_)}</text>')
        else:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="#fff" stroke="#94a3b8" stroke-width="1.8"/>')
            b.append(t(142, yy + 15, txt_, 12.5, "#1e293b"))
        b.append(chip(494, yy - 2, 40, "删除", DAN[1], DAN[0], 24))
        yy += 42
    b.append(f'<line x1="105" y1="306" x2="534" y2="306" stroke="#e2e8f0" stroke-width="1.4"/>')
    b.append(t(112, 330, "共 3 项 · 已完成 2 项", 12, "#64748b", "start", "700"))
    b.append(t(105, 396, "干净的 Web 观感（桌面就是 WebView）；上面这一屏 = 第 13 节完整代码的产物", 9.5, "#94a3b8", "start"))
    b.append(caption(W, 434, "第 13 节完整代码的成品：输入行 + 列表（勾选/删除）+ 计数，约 60 行 RSX"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_pillars(), "图1：Dioxus 三支柱（组件+RSX+信号）")
IMG2 = b64img(fig_rsx(), "图2：RSX 解剖")
IMG3 = b64img(fig_signal(), "图3：信号细粒度响应式")
IMG4 = b64img(fig_resource(), "图4：use_resource 异步生命周期")
IMG5 = b64img(fig_webview(), "图5：桌面 = 系统 WebView")
IMG6 = b64img(fig_style(), "图6：样式与资源")
IMG7 = b64img(fig_multi(), "图7：一份代码多端")
IMG8 = b64img(fig_todo(), "图8：Todo 应用界面")

SEC = [
    "一、Dioxus 是什么：组件 + RSX + 信号",
    "二、安装与第一个程序",
    "三、RSX：用 Rust 写 JSX",
    "四、组件与 Props",
    "五、信号 Signals：细粒度响应式",
    "六、事件与受控输入",
    "七、派生与共享：use_memo · use_effect · use_context",
    "八、异步：use_resource",
    "九、桌面 = 系统 WebView：与 Tauri 同底座",
    "十、中文与 WebView：省心处与真正的坑",
    "十一、样式与资源：CSS · asset! · 双主题",
    "十二、一份代码多端：Web/桌面/移动/全栈",
    "十三、完整实例：待办事项 Todo",
    "十四、常见坑速查",
    "十五、与 CMX 工作区的呼应",
    "十六、版本与参考资源",
]


def main():
    D = []
    A = D.append
    A("# Rust Dioxus 桌面框架详细使用说明")
    A("")
    A("> **定位**：Dioxus 是**组件 + RSX + 信号**的全 Rust 跨端 UI 框架——用 React 的心智（组件 / Props / Hooks），但状态用**信号**、更新靠**订阅**（细粒度、非虚拟 DOM 全树 diff）。**一份代码目标 Web / 桌面 / 移动 / 全栈**。")
    A("> **诚实前提**：**Dioxus 桌面今天 = 系统 WebView**（wry/tao，与 Tauri 同底座），并非 iced/egui 那样的自绘；差异在「UI 全用 Rust RSX 写」而非 JS/HTML。自研的 **Blitz/Dioxus Native**（WGPU 直渲 HTML/CSS）是未来方向、仍属实验。")
    A("> **版本基线（2026-09）**：Dioxus **0.7.x**（dioxus-desktop 0.7.x）。0.7 带来 **Subsecond 热补丁**（连 Rust 逻辑都能热替换）。框架年轻、迭代极快，**版本间破坏性变更偏多**。")
    A("> **一句话取舍**：给「前端背景、想 all-in Rust、能接受追新」的团队；桌面渲染现状与 Tauri 无本质区别，选它多半是为了「全 Rust + 一份代码多端」。")
    A("> **图**：8 张内嵌 base64 SVG。所有易变 API 处均标注「以 docs.rs 对应版本为准」。")
    A("")
    A("> 姊妹篇：`docs/20260920_Rust-iced桌面框架使用说明.md`（Elm 保留模式·自绘）、`docs/20260920_Rust-egui桌面框架使用说明.md`（立即模式·自绘）、`docs/20260920_Rust桌面GUI框架横评.md`（五框架横评）。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    for i, s in enumerate(SEC, 1):
        A(f"{i}. [{s}](#{slug(s)})")
    A("")
    A("---")
    A("")
    # 一
    A(f"## {SEC[0]}")
    A("")
    A(IMG1)
    A("")
    A("Dioxus 只有三个核心概念，凑齐就懂大半：")
    A("")
    A("- **组件 Component**：一个返回 `Element` 的普通函数（`fn App() -> Element`）。可带 Props、可嵌套组合成组件树——就是 React 组件的心智。")
    A("- **RSX**：声明 UI 的宏（`rsx! { … }`），写法接近 JSX，但是**编译期宏、有类型检查**，不是字符串模板。")
    A("- **信号 Signal**：响应式状态（`use_signal(|| 0)`）。**读它就订阅它，改它就通知订阅者**——只重新渲染读了这个信号的组件，天然细粒度。")
    A("")
    A("> 与 React 的最大不同：React 靠虚拟 DOM 全树 diff 找变化；Dioxus 靠**信号订阅**精确定位——改一个信号，框架直接知道该更新哪几处，不用比对整棵树。心智像 React，机制更省。")
    A("")
    A("> 与本系列另外两位的不同：iced 是 **Elm 保留模式**、egui 是**立即模式**，两者都**自绘**；Dioxus 是**组件/信号**，且桌面**走 WebView**（第 9 节详解）。三种世界观各有主场。")
    A("")
    # 二
    A(f"## {SEC[1]}")
    A("")
    A("`Cargo.toml`——桌面目标开 `desktop` feature：")
    A("")
    A("```toml")
    A(r'''[dependencies]
dioxus = { version = "0.7", features = ["desktop"] }
# 换目标只改 feature：web / mobile / fullstack

# 推荐装 CLI（热重载/多端构建）：cargo binstall dioxus-cli  → 命令是 dx''')
    A("```")
    A("")
    A("`src/main.rs`——最小计数器，**全文如下**：")
    A("")
    A("```rust")
    A(r'''use dioxus::prelude::*;

fn main() {
    dioxus::launch(App);        // 启动一个组件
}

// 组件 = 返回 Element 的函数（约定用大驼峰命名，rsx 才认它是组件）
fn App() -> Element {
    // 信号：响应式状态。要改就加 mut
    let mut count = use_signal(|| 0);

    rsx! {
        h1 { "计数: {count}" }                        // 读 count → 订阅；count 变这里自动更新
        button { onclick: move |_| count += 1, "加一" }
        button { onclick: move |_| count -= 1, "减一" }
    }
}''')
    A("```")
    A("")
    A("`dx serve` 跑起来（带热重载），或 `cargo run`。对比 iced 的四件套、egui 的每帧 `update`，Dioxus 这里是**组件 + 信号**：状态是 `use_signal`，界面是 `rsx!`，点击直接 `count += 1` 改信号，读了它的地方自动刷新。")
    A("")
    A("> 好消息：因为桌面是 WebView，**中文默认就能显示**（系统浏览器引擎提供字体），没有 iced/egui 那种「先装中文字体」的坑（第 10 节展开这个反转）。")
    A("")
    # 三
    A(f"## {SEC[2]}")
    A("")
    A(IMG2)
    A("")
    A("`rsx!` 是声明 UI 的宏，长得像 JSX/HTML，但**是编译期宏、带 Rust 类型检查**。要素：")
    A("")
    A("```rust")
    A(r'''rsx! {
    // 元素：名字 + 花括号；属性写 key: value，子节点直接嵌套
    div {
        class: "card",
        id: "main",

        // 文本 + 插值：{signal} / {表达式} 直接插进字符串
        h1 { "计数: {count}" }
        p { "两倍是 {count() * 2}" }

        // 事件：on 开头，值是闭包
        button {
            onclick: move |_| count += 1,
            "加一"                                // 子节点也可以是纯文本
        }

        // 循环：for 直接写在 rsx 里；列表项给稳定的 key
        for todo in todos.read().iter() {
            li { key: "{todo.id}", "{todo.text}" }
        }

        // 条件：if / else 也直接内联
        if count() > 5 {
            p { class: "warn", "有点多了！" }
        }
    }
}''')
    A("```")
    A("")
    A("| 语法 | 说明 |")
    A("|---|---|")
    A("| `div { … }` | 元素；小写=HTML 元素，大写=组件（`MyComp { … }`） |")
    A("| `class: \"x\"`, `onclick: …` | 属性 / 事件，写成 `key: value` |")
    A("| `\"文本 {signal}\"` | 文本子节点 + 插值（`{}` 里可放信号或表达式） |")
    A("| `for x in it { … }` | 列表渲染；每项建议给 `key` |")
    A("| `if cond { … } else { … }` | 条件渲染 |")
    A("| `{ 表达式 }` | 内联任意返回 `Element` 的 Rust 表达式 |")
    A("")
    A("> `rsx!` 全程走 Rust 类型系统：属性名拼错、信号类型不对，**编译期就报错**——这是它比「字符串模板」强的地方。`dx serve` 下改 rsx 还能热重载即时看到。")
    A("")
    # 四
    A(f"## {SEC[3]}")
    A("")
    A("组件就是**返回 `Element` 的函数**。要接收参数（Props），用 `#[component]` 宏把函数参数变成属性：")
    A("")
    A("```rust")
    A(r'''use dioxus::prelude::*;

// 用 #[component]：函数参数即 Props
#[component]
fn Greeting(name: String, count: i32) -> Element {
    rsx! { p { "你好 {name}，这是第 {count} 次" } }
}

// 父组件里像写 HTML 标签一样用它（大驼峰名）
fn App() -> Element {
    rsx! {
        Greeting { name: "张三".to_string(), count: 1 }
        Greeting { name: "李四".to_string(), count: 2 }
    }
}

// 需要更多控制（默认值/可选）时，手写 Props 结构体：
#[derive(Props, PartialEq, Clone)]
struct CardProps {
    title: String,
    #[props(default = false)]     // 可选属性带默认值
    highlighted: bool,
    children: Element,            // 接收子节点（类似 slot）
}

#[component]
fn Card(props: CardProps) -> Element {
    rsx! {
        div { class: if props.highlighted { "card hot" } else { "card" },
            h3 { "{props.title}" }
            {props.children}                        // 渲染传进来的子节点
        }
    }
}''')
    A("```")
    A("")
    A("要点：")
    A("")
    A("- **组件名用大驼峰**（`Greeting`），`rsx!` 靠大小写区分「组件」与「HTML 元素」。")
    A("- **`children: Element`** 让组件接收子节点（`Card { Foo {} }` 里的 `Foo {}`），类似插槽。")
    A("- Props 需要 `PartialEq`：Dioxus 靠它判断属性变没变、要不要重渲子组件。")
    A("")
    # 五
    A(f"## {SEC[4]}")
    A("")
    A(IMG3)
    A("")
    A("信号是 Dioxus 状态管理的核心。三件事记牢：**读=订阅、改=通知、Copy=随便传**。")
    A("")
    A("```rust")
    A(r'''let mut count = use_signal(|| 0);

// —— 读 ——（在组件/rsx 里读 = 订阅它，之后它变你就重渲）
let now = count();          // 调用语法，最常用
let now = *count.read();    // 显式读

// —— 改 ——
count += 1;                 // 运算符
count.set(10);              // 直接设
count.write().push(x);      // 拿可变引用改内部（如 Vec/结构体）
*count.write() += 1;        // 显式写

// —— Copy ——：信号是 Copy，可直接传给子组件、丢进闭包/async，无需 clone
let doubled = use_memo(move || count() * 2);   // 派生信号
spawn(async move { count += 1; });             // 异步里也能用''')
    A("```")
    A("")
    A("**细粒度响应式**是它的精髓：")
    A("")
    A("- **订阅发生在「读」处**：某组件读了 `count`，`count` 变时**只有它**（及其它读者）重跑；没读的组件纹丝不动。")
    A("- 因此**没有虚拟 DOM 全树 diff**——框架直接知道该更新谁。大列表、深层树里这很省。")
    A("- 只读场景给子组件传 `ReadSignal<T>`（只读信号），读写场景传 `Signal<T>`。")
    A("")
    A("> 对比：iced 每次 `view` 重建整棵界面描述；egui 每帧重跑整个 UI；Dioxus 只重跑「读了变化信号」的组件——三者更新粒度递减，Dioxus 这点最接近 React 但更精确。")
    A("")
    # 六
    A(f"## {SEC[5]}")
    A("")
    A("事件处理器是 `on*` 属性 + 闭包；受控输入把信号和输入框双向绑起来：")
    A("")
    A("```rust")
    A(r'''let mut name = use_signal(String::new);

rsx! {
    input {
        value: "{name}",                        // 信号 → 输入框（受控）
        oninput: move |e| name.set(e.value()),  // 输入框 → 信号
        onkeydown: move |e| {
            if e.key() == Key::Enter { /* 提交 */ }
        },
    }
    p { "你好, {name}" }                          // name 一变，这里自动更新

    // 常见事件：onclick / ondoubleclick / onmouseenter / onchange / onsubmit …
    button {
        onclick: move |e| {
            e.stop_propagation();                // 事件对象有 DOM 那套方法
            name.set(String::new());
        },
        "清空"
    }
}''')
    A("```")
    A("")
    A("| 事件 | 取值 |")
    A("|---|---|")
    A("| `oninput` / `onchange` | `e.value()` 拿输入内容 |")
    A("| `onclick` / `onmouse*` | `e.stop_propagation()` / 坐标等 |")
    A("| `onkeydown` / `onkeyup` | `e.key()`（`Key::Enter` 等） |")
    A("| `onsubmit` | 表单提交（配 `prevent_default`） |")
    A("")
    A("> 因为渲染层是 WebView，事件对象就是**浏览器那套语义**（`value()`/`key()`/`stop_propagation()`…），前端经验可直接迁移。")
    A("")
    # 七
    A(f"## {SEC[6]}")
    A("")
    A("除了 `use_signal`，常用 Hook 还有派生、副作用、跨组件共享：")
    A("")
    A("```rust")
    A(r'''// use_memo：派生值，依赖（这里是 count）变了才重算，结果本身也是信号
let doubled = use_memo(move || count() * 2);

// use_effect：副作用，依赖自动追踪；读了谁、谁变就重跑
use_effect(move || {
    println!("count 变成了 {}", count());       // 日志/订阅外部/同步 DOM 等
});

// use_context_provider / use_context：跨层级共享状态，免 prop drilling
#[derive(Clone, Copy)]
struct Theme(Signal<bool>);                     // 建议用 newtype 包一层（按类型取）

fn App() -> Element {
    use_context_provider(|| Theme(Signal::new(false)));  // 父：提供
    rsx! { Child {} }
}

fn Child() -> Element {
    let theme = use_context::<Theme>();          // 子：任意深度取用
    rsx! { p { "暗色模式: {theme.0}" } }
}''')
    A("```")
    A("")
    A("| Hook | 用途 |")
    A("|---|---|")
    A("| `use_signal` | 响应式状态（最常用） |")
    A("| `use_memo` | 派生值（依赖变才重算） |")
    A("| `use_effect` | 副作用（依赖自动追踪） |")
    A("| `use_resource` | 异步数据（第 8 节） |")
    A("| `use_context_provider` / `use_context` | 跨组件共享，免逐层传参 |")
    A("| `use_future` / `spawn` | 起一个后台异步任务 |")
    A("")
    A("> Context 按**类型**（TypeId）索引，所以要存多个同底类型（如多个 `String`），各用一个 newtype 包起来区分。")
    A("")
    # 八
    A(f"## {SEC[7]}")
    A("")
    A(IMG4)
    A("")
    A("异步拉数据用 `use_resource`：组件里发起，任务后台跑，**结果一到自动重渲**——读它就订阅它。")
    A("")
    A("```rust")
    A(r'''fn UserCard() -> Element {
    // 发起异步任务；返回一个 Resource，读它会订阅
    let mut user = use_resource(move || async move {
        reqwest::get("https://api.example.com/user")
            .await?
            .text()
            .await
    });

    rsx! {
        // 读 resource：None=还在跑，Some(Ok)=成功，Some(Err)=失败
        match &*user.read() {
            Some(Ok(text)) => rsx! { p { "用户：{text}" } },
            Some(Err(e))   => rsx! { p { class: "err", "出错：{e}" } },
            None           => rsx! { p { "加载中…" } },
        }
        button { onclick: move |_| user.restart(), "刷新" }   // 手动重跑
    }
}''')
    A("```")
    A("")
    A("要点：")
    A("")
    A("- `use_resource(|| async { … })` **首帧立即返回**（值为 `None`），任务在后台异步跑，完成后自动触发重渲。")
    A("- 读到的是 `Option<Result<T, E>>`：`None` 加载中、`Some(Ok)` 成功、`Some(Err)` 失败。")
    A("- **依赖自动追踪**：闭包里读了别的信号，那个信号变时 resource 会**自动重跑**；也可手动 `.restart()`。")
    A("- 全栈项目里，把这里的 `reqwest::get` 换成 `#[server]` 服务端函数即可前后端同源（第 12 节）。")
    A("")
    A("> `match` 内联在 rsx 里的写法随版本略有差异，个别版本更推荐 `if let` 或把分支抽成函数——以你锁定版本的 docs.rs / 指南为准。")
    A("")
    # 九
    A(f"## {SEC[8]}")
    A("")
    A(IMG5)
    A("")
    A("**这是选型前必须看清的一节**：Dioxus **桌面今天的渲染 = 系统 WebView**，与 Tauri **同底座**（wry/tao）。")
    A("")
    A("- 你的 RSX/组件在 **Rust 侧**跑，维护一棵 VirtualDom，信号驱动精确 diff；变更喂给 `dioxus-desktop` → `wry/tao` → **系统 WebView**（Windows 的 WebView2 / macOS 的 WKWebView / Linux 的 WebKitGTK）渲染。")
    A("- **与 Tauri 的真正区别不在渲染，而在「UI 用什么写」**：Dioxus 用 **Rust RSX**，Tauri 用**任意 Web 前端**（React/Vue/Svelte，或 Leptos/Yew）。二者甚至可组合——**Dioxus 可以当 Tauri 的前端**。")
    A("- **自绘是未来、非现在**：Dioxus 押注的 **Blitz/Dioxus Native**（用 WGPU 直渲 HTML/CSS、Taffy 布局）成熟后才能摆脱三平台 WebView 差异，但目前仍是实验品。")
    A("- **Web 目标**则没有 WebView 中间层：同一份组件编到 WASM 直接跑浏览器。")
    A("")
    A("> 一句诚实话：如果你冲着「像 iced/egui 那样的纯自绘、像素级跨平台一致」来，**Dioxus 桌面今天给不了**——它给的是「全 Rust 写 UI + 一份代码多端 + WebView 渲染」。想清楚要的是哪一个。")
    A("")
    # 十
    A(f"## {SEC[9]}")
    A("")
    A("iced/egui 那节讲「怎么装中文字体」，到 Dioxus 这里**反转了**——因为渲染是 WebView：")
    A("")
    A("**省心的地方（WebView 白送）**：")
    A("")
    A("- **中文默认就显示**：系统浏览器引擎自带完整字体栈，`\"中文\"` 直接正常，**无需 `set_fonts` / 打包字体**。")
    A("- **输入法（IME）成熟**：候选框、预编辑全由系统 WebView 处理，中文输入体验最省心。")
    A("- **复杂排版最强**：换行、竖排、RTL、`emoji`——浏览器级排版能力全都有。")
    A("- **CSS 生态全量复用**：Flexbox/Grid、动画、任意 CSS 框架照单全收。")
    A("")
    A("**真正的坑（转移到 WebView 跨平台差异）**：")
    A("")
    A("| 坑 | 说明 |")
    A("|---|---|")
    A("| 三平台内核不同 | WebView2 / WKWebView / WebKitGTK，CSS/JS 行为有差异 |")
    A("| Linux 是重灾区 | WebKitGTK 兼容性/依赖是常见坑位，要留测试预算 |")
    A("| 包体依赖系统 WebView | 包很小（不带引擎），但 Windows 老系统需分发 WebView2 Runtime |")
    A("| 性能上限受 WebView 制约 | 虽无 JS 桥（UI 逻辑是 Rust），渲染仍是 WebView 天花板 |")
    A("")
    A("> 一句话：**Dioxus 把 iced/egui 的「字体坑」换成了「WebView 跨平台一致性坑」**。中文/IME/排版省心了，但三平台 WebView 内核差异要专门测——这和 Tauri 是同一类烦恼。")
    A("")
    # 十一
    A(f"## {SEC[10]}")
    A("")
    A(IMG6)
    A("")
    A("Dioxus 的样式**就是 CSS**（因为渲染是 WebView）。静态资源用 `asset!` 登记、`Stylesheet` 注入：")
    A("")
    A("```rust")
    A(r'''use dioxus::prelude::*;

// asset!：编译期登记资源，产出带哈希的路径（自动进产物）
static MAIN_CSS: Asset = asset!("/assets/main.css");

fn App() -> Element {
    rsx! {
        document::Stylesheet { href: MAIN_CSS }     // 注入全局样式表

        // 主题：完全走 CSS 那套
        div {
            class: "card",                          // 类名切换
            style: "padding: 16px",                 // 内联样式
            "内容"
        }
    }
}''')
    A("```")
    A("")
    A("主题切换有多种 Web 惯用法，任选：")
    A("")
    A("- **class 切换**：`div { class: \"{theme}\" }`，配一套 `.dark { … }` CSS。")
    A("- **CSS 变量**：`color: var(--accent)`，切主题只改根变量。")
    A("- **媒体查询**：`@media (prefers-color-scheme: dark)` 跟随系统。")
    A("- 也能直接上 **Tailwind / 任意 CSS 框架**。")
    A("")
    A("> **对齐 CMX 硬约束 #4（双主题通路、禁硬编码色值）**：因为桌面就是 WebView，**CMX 现有的 `--sap*` 变量、`data-cmx-skin` / `data-cmx-skin-tone` 切肤那一整套可原样复用**（和给 Tauri 做前端时一模一样）——这也是 Dioxus 相对 iced/egui 在「双主题合规」上的天然便利：不用像自绘框架那样从 palette 手动派生，直接用你已有的 CSS 主题体系。")
    A("")
    # 十二
    A(f"## {SEC[11]}")
    A("")
    A(IMG7)
    A("")
    A("Dioxus 的招牌是**一份组件代码、多端目标**——切目标基本只改 `dx serve --platform`：")
    A("")
    A("```bash")
    A(r'''dx serve                       # 默认平台（按 Cargo.toml feature）
dx serve --platform desktop    # 桌面（WebView）
dx serve --platform web        # 网页（WASM）
dx serve --platform android    # 安卓模拟器/真机
dx build --release --platform desktop   # 出包''')
    A("```")
    A("")
    A("| 目标 | 渲染 / 形态 | 成熟度 |")
    A("|---|---|---|")
    A("| **Web** | 编到 WASM，浏览器直接跑 | 一级 |")
    A("| **桌面** | 系统 WebView（wry/tao） | 官方支持（本文重点） |")
    A("| **移动** | iOS / Android | 官方支持，生态较年轻 |")
    A("| **全栈** | `#[server]` 服务端函数（Axum 底座） | 一级 |")
    A("")
    A("全栈的 `#[server]` 让**前后端写在同一个 crate**、同源调用：")
    A("")
    A("```rust")
    A(r'''// 这个函数只在服务端执行；客户端「像调普通 async 函数」一样调用它
#[server]
async fn save_todo(text: String) -> Result<(), ServerFnError> {
    // 只有服务端能碰 DB / 密钥
    db::insert(&text).await?;
    Ok(())
}

// 组件里（客户端）直接 await 它，框架负责生成 RPC
fn AddButton(text: String) -> Element {
    rsx! {
        button {
            onclick: move |_| {
                let text = text.clone();
                async move { let _ = save_todo(text).await; }
            },
            "保存到服务器"
        }
    }
}''')
    A("```")
    A("")
    A("> 这套 server functions 与 CMX 后端天然同族——**Dioxus 全栈的底座就是 Axum**，和 CMX 各引擎（axum）是一门技术。这也是它值得放进 CMX 观察名单的主要理由（第 15 节）。")
    A("")
    # 十三
    A(f"## {SEC[12]}")
    A("")
    A(IMG8)
    A("")
    A("把前面的概念串起来——一个可编译的待办事项应用：")
    A("")
    A("```rust")
    A(r'''use dioxus::prelude::*;

fn main() {
    dioxus::launch(App);
}

#[derive(Clone, PartialEq)]
struct Todo {
    id: u64,
    text: String,
    done: bool,
}

// 信号是 Copy，可原样传进普通函数（这样两个事件处理器能复用同一段逻辑）
fn add_todo(mut input: Signal<String>, mut items: Signal<Vec<Todo>>, mut next_id: Signal<u64>) {
    let text = input().trim().to_string();
    if !text.is_empty() {
        items.write().push(Todo { id: next_id(), text, done: false });
        next_id.set(next_id() + 1);
        input.set(String::new());
    }
}

fn App() -> Element {
    let input = use_signal(String::new);
    let items = use_signal(Vec::<Todo>::new);
    let next_id = use_signal(|| 0u64);

    rsx! {
        h1 { "待办事项" }

        div {
            input {
                value: "{input}",
                oninput: move |e| input.clone().set(e.value()),
                onkeydown: move |e| if e.key() == Key::Enter { add_todo(input, items, next_id); },
            }
            button { onclick: move |_| add_todo(input, items, next_id), "添加" }
        }

        ul {
            for item in items.read().iter() {
                li { key: "{item.id}",
                    input {
                        r#type: "checkbox",
                        checked: item.done,
                        // item.id 是 Copy，被闭包按值捕获；items 是 Copy 信号
                        onchange: move |_| {
                            let mut items = items;
                            if let Some(t) = items.write().iter_mut().find(|t| t.id == item.id) {
                                t.done = !t.done;
                            }
                        },
                    }
                    span { "{item.text}" }
                    button {
                        onclick: move |_| { let mut items = items; items.write().retain(|t| t.id != item.id); },
                        "删除"
                    }
                }
            }
        }

        p { "共 {items().len()} 项 · 已完成 {items().iter().filter(|t| t.done).count()}" }
    }
}''')
    A("```")
    A("")
    A("这段覆盖了：**信号状态、`oninput` 受控输入、回车提交、`for` 列表 + `key`、闭包按值捕获 Copy 信号、`items.write()` 改集合**——就是图 8 那个界面。想接后端？把新增/删除换成 `#[server]` 函数即可（第 12 节）。中文无需额外处理（WebView 自带，第 10 节）。")
    A("")
    # 十四
    A(f"## {SEC[13]}")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 组件名用小写 | rsx 把它当 HTML 元素，渲染不出来 | 组件一律大驼峰（`MyComp`） |")
    A("| 改了信号界面不动 | 那个组件根本没「读」它 | 订阅在读处；确保渲染里读了该信号 |")
    A("| 列表少写 `key` | 增删时错位/状态串味 | `for` 项给稳定 `key: \"{id}\"` |")
    A("| 闭包里 `clone` 报错/繁琐 | 以为信号要 clone | 信号是 Copy，直接传/捕获即可 |")
    A("| Props 没 `PartialEq` | 编译报错或无法判断重渲 | Props `#[derive(Props, PartialEq, Clone)]` |")
    A("| Linux 跑不起来/白屏 | 缺 WebKitGTK 依赖 | 装系统 WebKitGTK 开发库；留跨平台测试 |")
    A("| 以为是自绘、追求像素一致 | 三平台观感有差异 | 桌面=WebView，与 Tauri 同类；差异要测 |")
    A("| 照抄旧教程编译不过 | 0.4/0.5 API 差异大 | 认准 0.7 的 docs.rs / 指南，别跨版本抄 |")
    A("| `dx` 命令找不到 | 没装 CLI | `cargo binstall dioxus-cli`（命令是 `dx`） |")
    A("")
    # 十五
    A(f"## {SEC[14]}")
    A("")
    A("对照本工作区（元数据驱动企业平台，前端以 Web 资产为主）：")
    A("")
    A("1. **Dioxus 值得放进观察名单，但当下非首选**。横评（`docs/20260920_Rust桌面GUI框架横评.md`）结论：面向最终用户的桌面产品**首选 Tauri 2**（直接复用 `frontend/` 的 UI5/Tabler 与双主题资产）；Dioxus 桌面今天 = WebView，**与 Tauri 相比无渲染优势**，选它主要为「UI 也全用 Rust 写」。")
    A("2. **它的独特价值 = 全栈同族**：`#[server]` 服务端函数的底座是 **Axum**，与 CMX 各引擎（axum）是一门技术。若未来希望「门户小工具类页面」也统一成 Rust、且前后端同源，Dioxus 全栈是顺理成章的路径。")
    A("3. **双主题零成本对齐**：因为是 WebView，CMX 的 `--sap*` 变量 + `data-cmx-skin` 切肤体系**可原样复用**，天然满足硬约束 #4（第 11 节）——这点与给 Tauri 做前端完全一致。")
    A("4. **中文/IME 省心**：WebView 自带，无自绘框架的字体坑（第 10 节）。")
    A("5. **组合而非二选一**：Dioxus 甚至可作为 **Tauri 的前端**（全 Rust RSX + Tauri 的插件/打包/安全模型），这是很多团队的实际用法。")
    A("")
    A("> 与本系列的分工：**iced=架构可演进的自绘桌面产品；egui=最快出活的内部工具/诊断面板；Dioxus=前端背景、想全 Rust 一份代码多端（桌面走 WebView）**。三者主场不同，Dioxus 在 CMX 语境下更多是「未来若要 Rust 全栈前端」的候选。")
    A("")
    # 十六
    A(f"## {SEC[15]}")
    A("")
    A("**版本基线（2026-09）**：Dioxus **0.7.x**。亮点是 **Subsecond 热补丁**（连 Rust 逻辑都能热替换，不只前端资源）。Dioxus **迭代极快、破坏性变更也最多**（0.4→0.5→0.6→0.7 每次 API 都有明显变化）——**把「升级成本」计入选型**，认准你锁定版本的文档。")
    A("")
    A("| 资源 | 地址 | 说明 |")
    A("|---|---|---|")
    A("| 官网 & 指南 | dioxuslabs.com（learn/0.7） | **按版本号的 Guide**，教程成体系 |")
    A("| API 文档 | docs.rs/dioxus | **锁定你的版本看**，一切以此为准 |")
    A("| 源码 & 示例 | github.com/DioxusLabs/dioxus（`examples/`） | todos / router / fullstack 等可跑范例 |")
    A("| CLI | `dx`（cargo binstall dioxus-cli） | `dx new` 脚手架、`dx serve` 热重载 |")
    A("| 迁移 | dioxuslabs.com/learn/0.7/migration | 升级到 0.7 的破坏性变更清单 |")
    A("")
    A("> 学习路径建议：`dx new` 生成模板，跑官方 `examples/` 里的 `todos` 与 `fullstack`（正好覆盖本文的信号 + server functions），再回头对照各节。遇到 API 对不上，第一反应是「看 0.7 的 docs.rs / Guide」——Dioxus 的锅九成是版本漂移。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **Dioxus = React 心智、Rust 身体、一份代码多端**：组件 + RSX + 信号，读即订阅、改即精确更新；桌面今天走系统 WebView（与 Tauri 同底座，中文/IME 省心、但要吃三平台差异），自绘的 Blitz 是未来。给「前端背景、想 all-in Rust、愿意追新」的团队；在 CMX 语境里，它更是「未来若要 Rust 全栈前端」的候选，而非当下替代 Tauri 的理由。")
    A("")
    A("> 参考：dioxuslabs.com（learn/0.7、blog）、docs.rs/dioxus 与 docs.rs/dioxus-desktop、github.com/DioxusLabs/dioxus（examples）。版本以 2026-09 的 0.7.x 线为准；凡涉及具体 API，请以你锁定版本的 docs.rs / Guide 为准，勿跨版本照抄。")

    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)

    # ---- 自校验 ----
    fences = txt.count("```")
    assert fences % 2 == 0, f"代码围栏不平衡: {fences}"
    n_img = txt.count("data:image/svg+xml;base64,")
    assert n_img == 8, f"图片数应为 8，实为 {n_img}"
    anchors = [slug(s) for s in SEC]
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
