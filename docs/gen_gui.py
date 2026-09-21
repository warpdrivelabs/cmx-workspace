#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust 桌面 GUI 框架横评》—— 内嵌 base64 SVG。
Run: python3 gen_gui.py   (iced 0.13 / egui 0.36 / Dioxus 0.7 / Tauri 2 / Slint 1.17)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust桌面GUI框架横评.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
ICE = ("#4338ca", "#eef2ff")   # iced indigo
EGU = ("#0d9488", "#f0fdfa")   # egui teal
DIO = ("#0284c7", "#f0f9ff")   # dioxus sky
TAU = ("#b45309", "#fffbeb")   # tauri amber
SLN = ("#7c3aed", "#f5f3ff")   # slint violet
GRY = ("#475569", "#f1f5f9")   # slate
DAN = ("#dc2626", "#fef2f2")   # danger red
GRN = ("#15803d", "#f0fdf4")   # green


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


def slug(t):
    """GitHub 风格锚点：保留 CJK/字母数字/连字符，空格转连字符，其余标点丢弃，不折叠连字符。"""
    out = []
    for ch in t.lower():
        if ch == ' ':
            out.append('-')
        elif ch == '-' or ch.isalnum():
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- FIG 1 定位象限
def fig_quad():
    W, H = 940, 470
    b = []
    cx, cy = 470, 235
    b.append(arrow(cx, cy, 890, cy, "", "#94a3b8", "0"))
    b.append(arrow(cx, cy, 50, cy, "", "#94a3b8", "0"))
    b.append(arrow(cx, cy, cx, 40, "", "#94a3b8", "0"))
    b.append(arrow(cx, cy, cx, 430, "", "#94a3b8", "0"))
    ax = f'font-family="{SANS}" font-size="11.5" font-weight="700" fill="#64748b"'
    b.append(f'<text x="880" y="{cy-10}" text-anchor="end" {ax}>Web 技术栈 / 系统 WebView →</text>')
    b.append(f'<text x="60" y="{cy-10}" {ax}>← 纯 Rust 自绘</text>')
    b.append(f'<text x="{cx+12}" y="52" {ax}>↑ 声明式 / 标记式 UI</text>')
    b.append(f'<text x="{cx+12}" y="424" {ax}>↓ 程序式 / 立即模式</text>')
    b.append(box(90, 82, 200, 58, "Slint 1.17", [".slint DSL · 编译期生成", "自绘：Skia / FemtoVG / 软件"], SLN))
    b.append(box(240, 152, 200, 58, "iced 0.13", ["Elm：Message/update/view", "自绘：wgpu + tiny-skia"], ICE))
    b.append(box(120, 310, 200, 58, "egui 0.36", ["立即模式：每帧即代码", "自绘：wgpu / glow"], EGU))
    b.append(box(520, 152, 210, 58, "Dioxus 0.7", ["RSX + 信号（React 式）", "桌面=WebView；Blitz 自绘实验"], DIO))
    b.append(box(710, 78, 210, 58, "Tauri 2", ["前端=任意 Web 框架", "渲染=系统 WebView"], TAU))
    b.append(caption(W, 456, "横轴＝画 UI 的方式（自绘 ↔ WebView）；纵轴＝写 UI 的方式（程序式 ↔ 声明式）。没有全能王，位置即取舍"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 渲染路线
def fig_render():
    W, H = 940, 430
    b = []
    lane = f'font-family="{MONO}" font-size="13" font-weight="700"'
    # 路线 A：系统 WebView
    b.append(f'<rect x="30" y="40" width="280" height="330" rx="12" fill="{TAU[1]}" stroke="{TAU[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="170" y="66" text-anchor="middle" {lane} fill="{TAU[0]}">路线 A：系统 WebView</text>')
    b.append(box(50, 84, 240, 62, "Tauri 2 · Dioxus(桌面现状)", ["UI 用 HTML/CSS/JS 或 WASM", "逻辑在 Rust 进程"], TAU))
    b.append(arrow(170, 146, 170, 172))
    b.append(box(50, 172, 240, 62, "wry / tao", ["WebView2(Win) · WKWebView(mac)", "WebKitGTK(Linux)"], GRY))
    b.append(arrow(170, 234, 170, 260))
    b.append(box(50, 260, 240, 48, "系统浏览器引擎渲染", ["排版/字体/IME 全由系统提供"], GRY))
    b.append(f'<text x="170" y="336" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{TAU[0]}">✔ 包体最小（不带浏览器引擎）</text>')
    b.append(f'<text x="170" y="354" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{TAU[0]}">✘ 三平台渲染细节有差异</text>')
    # 路线 B：GPU 自绘
    b.append(f'<rect x="330" y="40" width="280" height="330" rx="12" fill="{ICE[1]}" stroke="{ICE[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="470" y="66" text-anchor="middle" {lane} fill="{ICE[0]}">路线 B：GPU 自绘</text>')
    b.append(box(350, 84, 240, 62, "iced · egui · Slint · Blitz(实验)", ["框架自己排版、自己出几何", "egui 输出三角网格，渲染器无关"], ICE))
    b.append(arrow(470, 146, 470, 172))
    b.append(box(350, 172, 240, 62, "wgpu / OpenGL / Skia / FemtoVG", ["iced=wgpu · egui=wgpu/glow", "Slint=Skia/FemtoVG"], GRY))
    b.append(arrow(470, 234, 470, 260))
    b.append(box(350, 260, 240, 48, "GPU 直绘", ["三平台像素级一致"], GRY))
    b.append(f'<text x="470" y="336" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{ICE[0]}">✔ 观感一致 · 无 JS 桥 · 帧率可控</text>')
    b.append(f'<text x="470" y="354" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{ICE[0]}">✘ 字体/IME/无障碍要框架自己扛</text>')
    # 路线 C：软件渲染
    b.append(f'<rect x="630" y="40" width="280" height="330" rx="12" fill="{SLN[1]}" stroke="{SLN[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="770" y="66" text-anchor="middle" {lane} fill="{SLN[0]}">路线 C：软件渲染</text>')
    b.append(box(650, 84, 240, 62, "iced(tiny-skia) · Slint(software)", ["同一份 UI 代码", "切到 CPU 光栅化后端"], SLN))
    b.append(arrow(770, 146, 770, 172))
    b.append(box(650, 172, 240, 62, "纯 CPU 光栅化", ["无 GPU / 无驱动也能跑", "虚拟机 · 远程桌面 · 老设备"], GRY))
    b.append(arrow(770, 234, 770, 260))
    b.append(box(650, 260, 240, 48, "嵌入式 / MCU", ["Slint 可 no_std 跑上微控制器"], GRY))
    b.append(f'<text x="770" y="336" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{SLN[0]}">✔ 兜底与下沉能力（工控/HMI）</text>')
    b.append(f'<text x="770" y="354" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{SLN[0]}">✘ 复杂动画/大面积重绘吃 CPU</text>')
    b.append(caption(W, 408, "同一框架可有多条后端：iced = wgpu + tiny-skia；Slint = Skia / FemtoVG / 软件；Tauri 则完全托付给系统 WebView"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 编程范式
def fig_paradigm():
    W, H = 940, 400
    b = []
    b.append(box(30, 40, 210, 128, "Elm 单向数据流（iced）", [
        "view(状态) → 界面",
        "交互 → 产生 Message",
        "update(状态, Msg) 改状态",
        "↻ 回到 view，循环往复",
        "状态变更全部可追溯"], ICE))
    b.append(box(262, 40, 210, 128, "立即模式（egui）", [
        "每帧把 UI 代码重跑一遍",
        "if ui.button().clicked()",
        "无回调、无 diff、无绑定",
        "状态就是你手里的变量",
        "↻ 界面 = 本帧代码的输出"], EGU))
    b.append(box(494, 40, 210, 128, "组件 + 信号（Dioxus）", [
        "组件 = fn() → Element",
        "RSX 宏，写法 ≈ JSX",
        "use_signal 持有状态",
        "改信号 → 只重渲染读它的",
        "React 心智，Rust 类型"], DIO))
    b.append(box(726, 40, 190, 128, "声明式 DSL（Slint）", [
        ".slint 声明 UI + 属性绑定",
        "编译期生成 Rust/C++ 代码",
        "运行时按绑定增量更新",
        "设计与逻辑分离（类 QML）",
        "设计器/预览器可直接改"], SLN))
    b.append(box(180, 220, 580, 66, "Tauri 2：不定义 UI 范式", [
        "范式由你选的前端框架决定（React/Vue/Svelte/Leptos/Dioxus…）",
        "Rust 侧只暴露 command / 事件 / Channel，UI 状态管理完全是前端的事"], TAU))
    b.append(arrow(135, 168, 380, 220, "", ICE[0]))
    b.append(arrow(367, 168, 440, 220, "", EGU[0]))
    b.append(arrow(599, 168, 520, 220, "", DIO[0]))
    b.append(arrow(821, 168, 610, 220, "", SLN[0]))
    b.append(caption(W, 330, "四种「写 UI」的世界观都能落在 Tauri 的壳里（前端随便选）；反过来 iced/egui/Slint 则自带窗口，无需壳"))
    b.append(caption(W, 360, "选范式≈选团队心智：函数式可追溯选 Elm；快糙猛选立即模式；前端背景选 RSX；设计协作选 DSL"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 Tauri 2 架构
def fig_tauri():
    W, H = 940, 430
    b = []
    b.append(box(70, 34, 380, 78, "前端（WebView 进程）", [
        "HTML/CSS/JS：React · Vue · Svelte · 原生",
        "或 Rust→WASM：Leptos · Yew · Dioxus",
        "调用 @tauri-apps/api"], TAU))
    b.append(box(490, 34, 380, 78, "打包产物（tauri build）", [
        "Windows: msi / nsis    macOS: dmg / app",
        "Linux: deb / rpm / AppImage",
        "移动端: apk / aab · ipa（cargo-mobile2）"], GRY))
    b.append(box(190, 152, 560, 64, "IPC v2", [
        "invoke(command) · 事件 event · Channel（流式推送）",
        "Raw Payload：二进制载荷直传，大数据不再被 JSON 序列化卡脖子"], DIO))
    b.append(box(70, 256, 500, 78, "Rust Core 进程", [
        "#[tauri::command] 业务命令 · 窗口/托盘/菜单/快捷键",
        "插件生态：fs · shell · dialog · notification · updater …",
        "多窗口 · 单实例 · 深链接"], ICE))
    b.append(box(610, 256, 260, 78, "安全模型", [
        "capabilities / permissions：",
        "每窗口显式声明可用能力",
        "默认拒绝 + CSP 注入"], DAN))
    b.append(arrow(260, 112, 380, 152, "调用/订阅", TAU[0]))
    b.append(arrow(470, 216, 320, 256, "分发到命令", ICE[0]))
    b.append(arrow(570, 296, 610, 296, "校验", DAN[0]))
    b.append(f'<text x="470" y="372" text-anchor="middle" font-family="{SANS}" font-size="11" fill="#475569">系统 WebView：WebView2（Win，Chromium 内核） · WKWebView（macOS/iOS） · WebKitGTK（Linux）——不打包浏览器，包体因此极小</text>')
    b.append(caption(W, 404, "Tauri 与其余四者不是一类东西：它是「壳 + IPC + 安全 + 打包」，UI 交给 Web；Dioxus 桌面今天也跑在同款 wry/tao 底座上"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 平台矩阵
def fig_matrix():
    W, H = 940, 392
    b = []
    cols = ["Windows", "macOS", "Linux", "Android", "iOS", "Web", "嵌入式/MCU"]
    rows = [
        ("iced 0.13", ICE, ["●", "●", "●", "○", "○", "◐", "○"]),
        ("egui 0.36", EGU, ["●", "●", "●", "◐", "◐", "●", "◐"]),
        ("Dioxus 0.7", DIO, ["●", "●", "●", "●", "●", "●", "○"]),
        ("Tauri 2", TAU, ["●", "●", "●", "●", "●", "—", "○"]),
        ("Slint 1.17", SLN, ["●", "●", "●", "◐", "◐", "◐", "●"]),
    ]
    gcol = {"●": "#15803d", "◐": "#b45309", "○": "#94a3b8", "—": "#64748b"}
    x0, cw, rh, y0 = 190, 100, 44, 92
    b.append(f'<text x="470" y="46" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="700" fill="#334155">五框架 × 七平台支持矩阵（2026）</text>')
    for j, c in enumerate(cols):
        b.append(f'<text x="{x0 + j*cw + cw//2}" y="{y0 - 14}" text-anchor="middle" font-family="{MONO}" font-size="10.5" font-weight="700" fill="#475569">{esc(c)}</text>')
    for i, (name, col, cells) in enumerate(rows):
        y = y0 + i * rh
        st, fl = col
        b.append(f'<g><rect x="40" y="{y}" width="140" height="{rh-10}" rx="6" fill="{st}"/>'
                 f'<text x="110" y="{y + 21}" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="700" fill="#fff">{esc(name)}</text></g>')
        for j, g in enumerate(cells):
            b.append(f'<g><rect x="{x0 + j*cw + 6}" y="{y}" width="{cw-12}" height="{rh-10}" rx="6" fill="#fff" stroke="#e2e8f0" stroke-width="1"/>'
                     f'<text x="{x0 + j*cw + cw//2}" y="{y + 23}" text-anchor="middle" font-family="{SANS}" font-size="15" font-weight="700" fill="{gcol[g]}">{esc(g)}</text></g>')
    b.append(f'<text x="470" y="330" text-anchor="middle" font-family="{SANS}" font-size="11" fill="#475569">● 官方稳定支持　◐ 实验 / 预览　○ 不支持　— 不适用（Tauri 本身就是把 Web 装进壳）</text>')
    b.append(caption(W, 360, "移动端「稳定」今天只有 Tauri 2 与 Dioxus；嵌入式/MCU 是 Slint 独有；egui 的 Web 是一级公民；iced 官方无移动端"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 决策树
def fig_decide():
    W, H = 940, 470
    b = []
    b.append(box(350, 26, 240, 40, "要做 Rust 桌面应用，选哪个？", [], GRY))
    b.append(box(310, 98, 320, 50, "团队用 / 想用 Web 技术栈？", ["（HTML/CSS + 前端框架经验）"], GRY))
    b.append(arrow(470, 66, 470, 98))
    b.append(box(620, 180, 280, 50, "UI 也想全用 Rust 写？", ["（不想碰 JS/TS）"], GRY))
    b.append(arrow(560, 148, 700, 180, "是", GRN[0]))
    b.append(box(40, 180, 320, 50, "目标含嵌入式 / MCU？", ["或需要商业支持 / 类 Qt 工作流"], GRY))
    b.append(arrow(380, 148, 240, 180, "否", DAN[0]))
    b.append(box(690, 262, 220, 56, "Dioxus 0.7", ["RSX 全 Rust · 桌面/移动/网页", "Subsecond 热补丁"], DIO))
    b.append(arrow(790, 230, 800, 262, "是", GRN[0]))
    b.append(box(440, 262, 220, 56, "Tauri 2", ["任意前端 + Rust 后端", "移动端稳定 · 包体最小"], TAU))
    b.append(arrow(700, 230, 560, 262, "否", DAN[0]))
    b.append(box(40, 262, 220, 56, "Slint 1.17", ["嵌入式一级 · 软件渲染", "注意三许可模式"], SLN))
    b.append(arrow(160, 230, 150, 262, "是", GRN[0]))
    b.append(box(120, 356, 340, 50, "内部工具 / 调试面板 / 快速出活？", ["（观感其次，效率第一）"], GRY))
    b.append(arrow(250, 230, 290, 356, "否", DAN[0]))
    b.append(box(520, 352, 190, 56, "egui 0.36", ["立即模式 · 上手最快", "游戏/引擎内嵌友好"], EGU))
    b.append(arrow(460, 380, 520, 380, "是", GRN[0]))
    b.append(box(740, 352, 180, 56, "iced 0.13", ["Elm 式桌面应用", "COSMIC 桌面同款"], ICE))
    b.append(arrow(710, 380, 740, 380, "否", DAN[0]))
    b.append(caption(W, 442, "先问技术栈，再问目标平台，最后问应用气质；组合亦常见——egui 嵌进游戏引擎、Dioxus 当 Tauri 的前端"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_quad(), "图1：五框架定位象限")
IMG2 = b64img(fig_render(), "图2：三条渲染路线")
IMG3 = b64img(fig_paradigm(), "图3：编程范式对比")
IMG4 = b64img(fig_tauri(), "图4：Tauri 2 架构")
IMG5 = b64img(fig_matrix(), "图5：平台支持矩阵")
IMG6 = b64img(fig_decide(), "图6：选型决策树")

SEC = [
    "一、横评总览：先给结论",
    "二、五框架画像",
    "三、渲染路线对比：WebView vs 自绘",
    "四、编程范式对比：同一个计数器的五种写法",
    "五、Tauri 2 单独拆解：它和其余四个不是一类东西",
    "六、跨平台能力矩阵",
    "七、性能与资源占用：只谈量级，诚实标注",
    "八、中文 IME、可访问性与文本渲染",
    "九、许可证与商业模式",
    "十、开发体验：热重载、工具链与学习曲线",
    "十一、生态与成熟度",
    "十二、选型决策树与场景建议",
    "十三、与 CMX 工作区的落地呼应",
]


def main():
    D = []
    A = D.append
    A("# Rust 桌面 GUI 框架横评：iced · egui · Dioxus · Tauri 2 · Slint")
    A("")
    A("> **一句话**：五个都能做出生产级桌面应用，但它们回答的是**不同的问题**——egui 回答「怎么最快画出工具」，iced 回答「怎么用 Elm 心智做纯 Rust 应用」，Dioxus 回答「怎么用 React 心智写全 Rust 跨端」，Tauri 2 回答「怎么把成熟的 Web 前端装进最小的原生壳」，Slint 回答「怎么一份 UI 从桌面下沉到 MCU」。")
    A("> **版本基线（2026-09）**：iced **0.13.x**（0.14 开发中）· egui/eframe **0.36.x** · Dioxus **0.7.x** · Tauri **2.x**（2.0 于 2024-10 稳定）· Slint **1.17.x**。")
    A("> **图**：6 张内嵌 base64 SVG，无外部依赖。所有性能类说法只给量级并标注来源可靠度，不伪造 benchmark。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    for i, t in enumerate(SEC, 1):
        A(f"{i}. [{t}](#{slug(t)})")
    A("")
    A("---")
    A("")
    # 一
    A(f"## {SEC[0]}")
    A("")
    A(IMG1)
    A("")
    A("**一行版结论**（细节在后面十二节展开）：")
    A("")
    A("| 你的诉求 | 选它 | 为什么 |")
    A("|---|---|---|")
    A("| 内部工具 / 调试面板 / 游戏工具，最快出活 | **egui** | 立即模式零仪式感，一个函数就是一个界面 |")
    A("| 纯 Rust 桌面应用，要架构可长期演进 | **iced** | Elm 单向数据流，状态变更可追溯；COSMIC 桌面验证过体量 |")
    A("| 复用 Web 前端团队 / 已有 Web 资产，要移动端 | **Tauri 2** | 前端随便选，包体最小，移动端稳定，安全模型完备 |")
    A("| 全 Rust 但想要 React 心智，网页/桌面/移动一把梭 | **Dioxus** | RSX + 信号 + 全栈 server functions + 热补丁 |")
    A("| 嵌入式 / 工控 HMI / 类 Qt 工作流 / 要商业支持 | **Slint** | 唯一能 no_std 下沉到 MCU 的；DSL 设计协作友好 |")
    A("")
    A("五维总表：")
    A("")
    A("| 维度 | iced 0.13 | egui 0.36 | Dioxus 0.7 | Tauri 2 | Slint 1.17 |")
    A("|---|---|---|---|---|---|")
    A("| UI 范式 | Elm（保留模式） | 立即模式 | RSX + 信号（React 式） | 由前端框架决定 | 声明式 `.slint` DSL |")
    A("| 渲染 | 自绘：wgpu + tiny-skia | 自绘：wgpu / glow | 桌面=系统 WebView；Blitz 自绘实验 | 系统 WebView | 自绘：Skia / FemtoVG / 软件 |")
    A("| UI 语言 | Rust | Rust | Rust（RSX 宏） | HTML/CSS/JS 或 Rust→WASM | `.slint` + Rust/C++/JS/Python |")
    A("| 移动端 | 无官方 | 实验 | 官方支持 | 稳定（iOS/Android） | 预览 |")
    A("| Web | 实验 | 一级（WASM） | 一级 | 不适用（自身即壳） | 预览（WASM） |")
    A("| 嵌入式/MCU | 否 | 需自行集成 | 否 | 否 | **一级（no_std）** |")
    A("| 许可 | MIT | MIT/Apache-2.0 | MIT/Apache-2.0 | MIT/Apache-2.0 | GPLv3 / 免版税 / 商业 三选一 |")
    A("| 代表 | System76 COSMIC 桌面 | rerun、海量 Rust 工具 | 自家全栈应用生态 | 大量商业跨端应用 | 工业 HMI、车机、白电 |")
    A("")
    # 二
    A(f"## {SEC[1]}")
    A("")
    A("### iced：Elm 的 Rust 化身")
    A("")
    A("- **定位**：受 Elm 启发的纯 Rust GUI 库——`状态 + Message + update + view` 四件套，界面是状态的纯函数。")
    A("- **亮点**：架构最「正」，大型应用不易腐化；wgpu 渲染 + tiny-skia 软件兜底；被 System76 选为 **COSMIC 桌面环境**（整个 Linux 桌面！）的 UI 框架，体量已被验证。")
    A("- **短板**：官方自称 **experimental**，API 每个 0.x 版本都可能大改；文档长期只有 book + 示例；无官方移动端；无障碍支持不完整。")
    A("- **气质**：给「愿意读源码、想把应用写成一门架构」的 Rust 原教旨主义者。")
    A("")
    A("### egui：立即模式的效率怪物")
    A("")
    A("- **定位**：立即模式 GUI——每帧重跑一遍 UI 代码，界面就是代码此刻的输出；`eframe` 提供开箱窗口壳。")
    A("- **亮点**：心智负担全场最低（无回调无绑定无 diff）；渲染器无关（输出三角网格，wgpu/glow/自定义皆可），因此能嵌进任何游戏引擎/wgpu 应用；Web(WASM) 是一级公民；AccessKit 无障碍默认启用（Windows/macOS）；0.36 起要求 Rust edition 2024。")
    A("- **短板**：默认观感是「调试 UI」风（可主题化但要花功夫）；复杂自适应布局（flexbox/grid 级）能力弱；文本排版对复杂文种支持有限。")
    A("- **气质**：工具人之选——十分钟出一个能用的面板，是它的主场。")
    A("")
    A("### Dioxus：React 心智，Rust 身体")
    A("")
    A("- **定位**：组件 + RSX（≈JSX）+ 细粒度信号；一份代码目标 Web/桌面/移动/全栈。")
    A("- **亮点**：0.7 的 **Subsecond 热补丁**能热替换 Rust 代码（不只前端资源）；`use_signal` 细粒度更新；全栈 server functions（Axum 底座）；桌面/移动官方支持；风投支持（YC），迭代极快。")
    A("- **短板**：桌面渲染现状 = 系统 WebView（wry/tao，与 Tauri 同底座），自研 **Blitz/Dioxus Native**（WGPU 直渲 HTML/CSS，Taffy 布局）仍是实验品；框架年轻，版本间破坏性变更常见。")
    A("- **气质**：给「前端背景、想 all-in Rust、能接受追新」的团队。")
    A("")
    A("### Tauri 2：最小的壳，最大的自由")
    A("")
    A("- **定位**：不是 GUI 工具包，是**应用外壳**——UI 交给系统 WebView 里的任意 Web 前端，逻辑放 Rust 进程，中间是 IPC。")
    A("- **亮点**：包体最小（不带浏览器引擎，安装包常见个位数 MB）；2.0 起 iOS/Android 稳定；IPC v2 支持二进制 Raw Payload 与 Channel；capabilities/permissions 安全模型 + CSP；插件生态最丰富。")
    A("- **短板**：三平台 WebView 内核不同（WebView2/WKWebView/WebKitGTK），渲染细节与可用 Web API 有差异，Linux 的 WebKitGTK 是常见坑位；性能上限受 WebView 与 JS 桥制约。")
    A("- **气质**：Electron 的正统继承人，减去 150MB 的 Chromium。")
    A("")
    A("### Slint：从桌面下沉到单片机")
    A("")
    A("- **定位**：声明式 `.slint` DSL 编译为原生代码；创始团队出自 Qt/QML，目标就是「现代 Qt」。")
    A("- **亮点**：**唯一**能 no_std 跑上 MCU 的（数百 KB RAM 级设备可用软件渲染器）；Skia/FemtoVG/软件三渲染器；Rust/C++/JS/Python 四语言绑定；live-preview 即改即见；有商业公司背书与付费支持。")
    A("- **短板**：要学一门 DSL；许可三选一有决策成本（嵌入式发货要么 GPL 要么付费）；社区规模小于其余四者。")
    A("- **气质**：给「有设计师协作、有嵌入式野心、想要 Qt 式工作流」的团队。")
    A("")
    # 三
    A(f"## {SEC[2]}")
    A("")
    A(IMG2)
    A("")
    A("三条路线的本质取舍：")
    A("")
    A("| | 系统 WebView（Tauri / Dioxus 桌面现状） | GPU 自绘（iced / egui / Slint） | 软件渲染（iced tiny-skia / Slint software） |")
    A("|---|---|---|---|")
    A("| 排版/字体/IME | 系统浏览器引擎全包，**最省心** | 框架自己实现，能力参差 | 同左 |")
    A("| 跨平台一致性 | 三平台内核不同，**有差异** | 像素级一致 | 像素级一致 |")
    A("| 包体 | 极小（引擎在系统里） | 中（带渲染栈与字体处理） | 中 |")
    A("| 性能上限 | 受 WebView + JS 桥制约 | 直控 GPU，上限最高 | CPU 光栅化，够用但别做重动画 |")
    A("| 无 GPU 环境 | WebView 自己会退化 | 需软件后端兜底 | **天生为此而生** |")
    A("| CSS 生态复用 | ✔ 全量复用 | ✘（Blitz 实验性支持 HTML/CSS） | ✘ |")
    A("")
    A("> 一个常被忽略的事实：**Dioxus 桌面今天与 Tauri 用的是同一个 WebView 底座（wry/tao）**。两者的差异不在渲染，而在「UI 用什么语言写」（Rust RSX vs 任意 Web 前端）。Dioxus 押注的未来是 Blitz——用 WGPU 直渲 HTML/CSS（Taffy 布局引擎），成了它就同时拥有 Web 生态与自绘一致性，但今天它还是实验品。")
    A("")
    # 四
    A(f"## {SEC[3]}")
    A("")
    A(IMG3)
    A("")
    A("同一个「计数器」，五种世界观。依赖基线：")
    A("")
    A("```toml")
    A(r'''# 各框架最小依赖（五选一）
iced   = "0.13"
eframe = "0.36"                                      # egui 应用壳
dioxus = { version = "0.7", features = ["desktop"] }
tauri  = "2"                                         # 另需 build 依赖 tauri-build
slint  = "1.17"                                      # 另需 build 依赖 slint-build''')
    A("```")
    A("")
    A("**iced —— Elm 四件套**（0.13 的极简入口）：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{button, column, text};
use iced::Element;

#[derive(Default)]
struct Counter { value: i64 }

#[derive(Debug, Clone, Copy)]
enum Message { Inc, Dec }

fn update(c: &mut Counter, m: Message) {
    match m { Message::Inc => c.value += 1, Message::Dec => c.value -= 1 }
}

fn view(c: &Counter) -> Element<'_, Message> {
    column![
        button("+").on_press(Message::Inc),
        text(c.value).size(40),
        button("-").on_press(Message::Dec),
    ].into()
}

fn main() -> iced::Result {
    iced::run("Counter", update, view)   // 状态默认 Default::default()
}''')
    A("```")
    A("")
    A("**egui —— 立即模式**（界面 = 每帧代码的输出）：")
    A("")
    A("```rust")
    A(r'''struct App { value: i64 }

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _f: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Counter");
            ui.horizontal(|ui| {
                if ui.button("−").clicked() { self.value -= 1; }   // 无回调：当帧判断
                ui.label(self.value.to_string());
                if ui.button("+").clicked() { self.value += 1; }
            });
        });
    }
}

fn main() -> eframe::Result {
    eframe::run_native("Counter", Default::default(),
        Box::new(|_cc| Ok(Box::new(App { value: 0 }))))
}''')
    A("```")
    A("")
    A("**Dioxus —— RSX + 信号**（写法≈React，类型是 Rust）：")
    A("")
    A("```rust")
    A(r'''use dioxus::prelude::*;

fn main() { dioxus::launch(app); }

fn app() -> Element {
    let mut count = use_signal(|| 0);
    rsx! {
        h1 { "计数: {count}" }
        button { onclick: move |_| count += 1, "+1" }
        button { onclick: move |_| count -= 1, "-1" }
    }
}''')
    A("```")
    A("")
    A("**Slint —— DSL 声明 + Rust 驱动**（UI 与逻辑物理分离）：")
    A("")
    A("```slint")
    A(r'''// ui/counter.slint
import { Button, VerticalBox } from "std-widgets.slint";

export component Counter inherits Window {
    in-out property <int> value: 0;
    VerticalBox {
        Text { text: "计数: " + root.value; font-size: 24px; }
        Button { text: "+1"; clicked => { root.value += 1; } }
        Button { text: "-1"; clicked => { root.value -= 1; } }
    }
}''')
    A("```")
    A("")
    A("```rust")
    A(r'''slint::include_modules!();   // build.rs 里 slint_build::compile("ui/counter.slint")

fn main() -> Result<(), slint::PlatformError> {
    let ui = Counter::new()?;
    ui.run()
}''')
    A("```")
    A("")
    A("**Tauri 2 —— command + 前端**（UI 在 Web 侧，Rust 只暴露能力）：")
    A("")
    A("```rust")
    A(r'''#[tauri::command]
fn add(current: i64, delta: i64) -> i64 { current + delta }

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![add])
        .run(tauri::generate_context!())
        .expect("run tauri app");
}''')
    A("```")
    A("")
    A("```js")
    A(r'''// 前端任意框架里（计数状态本身就放前端）
import { invoke } from '@tauri-apps/api/core';
const next = await invoke('add', { current: 0, delta: 1 });''')
    A("```")
    A("")
    A("> 五段代码放在一起，差异一目了然：iced 把**状态流**放在台面上；egui 把**帧**放在台面上；Dioxus 把**组件**放在台面上；Slint 把**界面描述**放在台面上；Tauri 把**进程边界**放在台面上。")
    A("")
    # 五
    A(f"## {SEC[4]}")
    A("")
    A(IMG4)
    A("")
    A("把 Tauri 2 和另外四个放一张表里横比，容易得出错误结论——它其实是**另一层**的东西：")
    A("")
    A("- **它不画 UI**：渲染整个托付给系统 WebView；你甚至可以把 **Dioxus / Leptos / Yew 当 Tauri 的前端**，二者是组合关系不是竞争关系。")
    A("- **IPC v2 是 2.0 的核心升级**：`invoke` 命令 + 事件 + **Channel**（Rust→前端流式推送）；**Raw Payload** 允许二进制直传，绕开 JSON 序列化——大文件/图像场景不再卡桥。")
    A("- **安全模型是它对 Electron 的代差**：每个窗口按 **capabilities** 显式声明能用哪些 **permissions**（文件系统、shell、通知…），默认拒绝，外加 CSP 注入；插件也纳入同一权限体系。")
    A("- **移动端在 2.0 转正**：iOS/Android 与桌面共用一套项目结构（`cargo-mobile2` 底座），`tauri ios/android dev` 直接起模拟器。")
    A("- **代价也要写清楚**：WebKitGTK（Linux）与另两家内核行为差异是最大槽点来源；前端↔Rust 每次过桥都有序列化/调度成本，高频小消息要合批。")
    A("")
    # 六
    A(f"## {SEC[5]}")
    A("")
    A(IMG5)
    A("")
    A("几条矩阵之外的注脚：")
    A("")
    A("- **iced 的 Web 后端**长期处于实验/半维护状态，别按一级能力规划。")
    A("- **egui 的移动端**能跑（eframe 有 Android 支持路径）但属于「自己动手」级；它的 Web(WASM) 反而是最成熟的自绘方案之一。")
    A("- **Dioxus 移动端**是官方叙事的一部分（一份代码五端），但生态年轻，深度依赖原生能力时要有写平台胶水的准备。")
    A("- **Slint 的嵌入式**是真·一级：官方演示能在 **ESP32 / STM32 级 MCU**（数百 KB RAM + 软件渲染）上跑完整 UI，这是其余四家完全没有的维度。")
    A("- **桌面三平台**五家都稳，差别在细节：自绘系（iced/egui/Slint）三平台像素一致；WebView 系（Tauri/Dioxus）要为 Safari 系/WebKitGTK 留兼容性测试预算。")
    A("")
    # 七
    A(f"## {SEC[6]}")
    A("")
    A("性能横评是重灾区——网上流传的对比多数拿「hello world 包体」说事。这里只给**量级与机制解释**，并标注可靠度：")
    A("")
    A("| 指标 | WebView 路线（Tauri/Dioxus 桌面） | 自绘路线（iced/egui/Slint） | 可靠度 |")
    A("|---|---|---|---|")
    A("| 安装包体 | **个位数 MB** 常见（引擎在系统里） | 约 **5–20MB**（带渲染栈；strip + release 后） | 官方口径 + 社区实测量级 |")
    A("| 内存 | 页面内存 + WebView 共享库；**显著低于 Electron**（官方称比 Electron 省一半以上很常见） | 通常更低（无 JS 引擎/DOM） | ⚠️ 因应用差异巨大，只可比量级 |")
    A("| 冷启动 | WebView 初始化有可感知成本（Windows 上 WebView2 首启尤甚） | 基本即开即用 | 社区共识，无权威对拍 |")
    A("| 运行帧率上限 | 受 DOM/JS 制约，重可视化需 canvas/WebGL | 直控 GPU，60/120fps 可控；egui 默认**按需重绘**并不烧 CPU | 机制推导 |")
    A("| 对照背景板 | Electron 安装包常见 **80–150MB**、内存以数百 MB 起步 | — | 公开常识量级 |")
    A("")
    A("> ⚠️ **三个诚实声明**：其一，没有任何一家发布过五框架同条件对拍，本文不编造数字；其二，「Tauri 包小」的前提是系统有 WebView（Windows 老系统需分发 WebView2 Runtime，约 100MB+ 的在线/离线引导，装完全局共享）；其三，立即模式≠费电，egui 在无交互时不重绘。")
    A("")
    # 八
    A(f"## {SEC[7]}")
    A("")
    A("对中文团队，这一节可能比性能更该看：")
    A("")
    A("| 能力 | iced | egui | Dioxus | Tauri 2 | Slint |")
    A("|---|---|---|---|---|---|")
    A("| 中文 IME | winit 系历史痛点，近年改进但仍有候选框定位等毛边 | 同 winit 系，桌面基本可用 | WebView 提供，**省心** | WebView 提供，**省心** | 支持，成熟度视后端 |")
    A("| CJK 字体 | 需自带/指定字体，注意包体 | 需自带字体（默认字体不含 CJK） | 系统字体栈全套 | 系统字体栈全套 | 需配置字体，嵌入式场景可裁剪字库 |")
    A("| 复杂排版（换行/竖排/RTL） | 有限 | 有限（复杂文种是已知短板） | 浏览器级，**最强** | 浏览器级，**最强** | 中等 |")
    A("| 无障碍 | AccessKit 集成**未完成**（长期 issue） | **AccessKit 默认启用**（Win/mac；Web 端无） | WebView=ARIA；Blitz 部分 | **浏览器级 ARIA，最完整** | 桌面后端接入 AccessKit，组件带 accessible 属性 |")
    A("")
    A("> 结论很直白：**输入法和排版要「零操心」，选 WebView 路线**；自绘路线里 egui/Slint 的无障碍已可用，iced 这块最弱。做政企/无障碍合规项目，这一行可能直接否掉候选。")
    A("")
    # 九
    A(f"## {SEC[8]}")
    A("")
    A("| 框架 | 许可 | 商业含义 |")
    A("|---|---|---|")
    A("| iced | MIT | 随便用 |")
    A("| egui | MIT OR Apache-2.0 | 随便用 |")
    A("| Dioxus | MIT OR Apache-2.0 | 随便用（公司靠云服务/部署赚钱） |")
    A("| Tauri 2 | MIT OR Apache-2.0 | 随便用（基金会治理 + CrabNebula 商业服务） |")
    A("| Slint | **GPLv3 / Royalty-Free / 商业** 三选一 | 见下 |")
    A("")
    A("Slint 的三选一要单独讲清楚：")
    A("")
    A("1. **GPLv3**：应用整体开源即可免费，含嵌入式。")
    A("2. **Royalty-Free 许可**：**桌面 / 移动 / Web 应用免费，含商用闭源**，条件是保留「Made with Slint」归属声明——多数桌面团队走这条即可。")
    A("3. **商业许可**：闭源**嵌入式设备发货**必须走这条（按设备计费，官方公布过 1 美元/台级起步的方案）或回到 GPL；含付费支持。")
    A("")
    A("> 决策提示：企业内部工具五家全部免费无忧；**只有「闭源 + 嵌入式发货」这个组合会碰到 Slint 的收费闸门**。")
    A("")
    # 十
    A(f"## {SEC[9]}")
    A("")
    A("| 维度 | iced | egui | Dioxus | Tauri 2 | Slint |")
    A("|---|---|---|---|---|---|")
    A("| 热重载 | 无官方 | 不太需要（编译快 + 立即模式） | **Subsecond 热补丁**：连 Rust 逻辑都能热换 | 前端 Vite HMR 秒级；Rust 侧需重编 | **live-preview**：`.slint` 即改即见 |")
    A("| 脚手架 | 无（看 examples） | 无需 | `dx new / dx serve` | `create-tauri-app` + `tauri dev` 一条龙 | VSCode 扩展 + SlintPad 在线玩 |")
    A("| 调试 | Rust 调试器 | 自带 inspector（`ctx.debug…`） | 浏览器 DevTools + Rust | **浏览器 DevTools 全套** + Rust | 预览器 + Rust/C++ 调试器 |")
    A("| 学习曲线 | 中高（Elm 心智 + API 变动） | **最低** | 低（前端背景）/中（纯后端背景） | 低（会 Web 就会）+ Rust 命令层 | 中（学 DSL，但 DSL 本身简单） |")
    A("| 文档 | 偏薄（book + 示例） | 好（docs.rs + demo 站） | 好且新 | **最全**（官网指南成体系） | 好（官方教程 + 参考完整） |")
    A("")
    A("> DX 的分水岭在「改一行 UI 要等多久」：Dioxus（热补丁）、Slint（预览器）、Tauri（HMR）是秒级；egui 靠编译快 + 心智简单硬拉平；iced 改一行等一次全量编译，大项目里最疼。")
    A("")
    # 十一
    A(f"## {SEC[10]}")
    A("")
    A("| 框架 | GitHub star 量级（2026，粗略） | 背后是谁 | 生产背书 |")
    A("|---|---|---|---|")
    A("| Tauri 2 | ≈ 9 万+，五者最高 | Tauri 基金会（Commons Conservancy）+ CrabNebula | 大量商业桌面应用；生态插件最多 |")
    A("| Dioxus | ≈ 3 万 | Dioxus Labs（YC 融资） | 自家全栈生态，增速最快 |")
    A("| iced | ≈ 2.5–3 万 | 社区 + System76 深度投入 | **COSMIC 桌面环境**整套 UI |")
    A("| egui | ≈ 2.5–3 万 | emilk 主导 + rerun 公司反哺 | rerun 可视化、无数内部工具、游戏引擎标配调试 UI |")
    A("| Slint | ≈ 2 万 | SixtyFPS GmbH（商业公司） | 工业 HMI / 车机 / 白电等嵌入式出货 |")
    A("")
    A("成熟度的另一面是**稳定性承诺**：Tauri 2 与 Slint 1.x 有明确的语义化版本纪律；egui 每年数个 0.x 版但迁移说明详尽；Dioxus 迭代最快、破坏性变更也最多；iced 官方直言 experimental，0.x 之间 API 会大改——**把「升级成本」计入选型**，而不只看今天好不好用。")
    A("")
    # 十二
    A(f"## {SEC[11]}")
    A("")
    A(IMG6)
    A("")
    A("按场景落到人：")
    A("")
    A("- **运维面板 / 抓包器 / 性能分析器 / 游戏编辑器**：egui。立即模式对「数据每帧都在变」的界面是降维打击。")
    A("- **面向最终用户的桌面产品，团队有前端**：Tauri 2。UI 质感天花板最高（就是 Web 的天花板），设计资源全能复用。")
    A("- **同上，但团队想只写 Rust**：Dioxus（接受追新）或 iced（接受手工与编译等待，换架构稳）。")
    A("- **嵌入式 HMI / 车机 / 仪器面板，顺带出个桌面版**：Slint，没有第二个答案。")
    A("- **组合拳也常见**：egui 嵌进 wgpu/游戏引擎当调试层；Dioxus 作为 Tauri 的前端（全 Rust + Tauri 的插件/打包/安全）；Slint 桌面版验证 UI、同一份 `.slint` 下沉到设备。")
    A("")
    # 十三
    A(f"## {SEC[12]}")
    A("")
    A("对照本工作区（元数据驱动企业平台，前端已有成体系的 Web 资产）：")
    A("")
    A("1. **`cmx-agent`（桌面智能体）若要长出 GUI**：首选 **Tauri 2**——`frontend/` 已是成熟 npm workspace，UI5/Tabler 组件、双主题（`--sap*` 变量 + `data-cmx-skin`）等资产可**原样复用**进 WebView，符合「页面/组件双主题通路兼容」硬约束；Rust 侧与现有 crate 直接同仓编译。")
    A("2. **引擎类内部诊断工具**（如 flow/report 引擎的本地调试面板）：**egui** 最划算——单二进制、无前端构建链、`cargo run` 即用，且不进产品线，观感要求低。")
    A("3. **Dioxus** 值得放进观察名单：若未来希望「门户小工具类页面」也统一成 Rust，全栈 server functions 与 CMX 的 axum 后端天然同族；但当下其桌面=WebView，与 Tauri 相比并无渲染优势，追新成本要算。")
    A("4. **Slint/iced 暂无对口场景**：本仓无嵌入式诉求（Slint 的杀手锏用不上）；iced 的 Elm 架构优势在「长寿命重交互桌面产品」，与 CMX 当前以 Web 为主的形态不重叠。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **五个框架其实是五个问题的答案：egui 答「多快」，iced 答「多正」，Dioxus 答「多全」，Tauri 答「多轻」，Slint 答「多深」。** 先想清楚你的问题是哪一个，答案自然浮出来——而对一个已有 Web 资产的团队，Tauri 2 往往是把存量变现的最短路径。")
    A("")
    A("> 参考：iced.rs 与 book.iced.rs、github.com/emilk/egui 与 egui.rs、dioxuslabs.com（0.7 发布说明 / Blitz / Subsecond）、v2.tauri.app（IPC / capabilities / mobile 指南）、slint.dev（licensing / embedded / 渲染器文档）、System76 COSMIC 公告。版本以 2026-09 各官方文档为准；star 数与体积/内存均为量级说法，选型前请以当期实测为准。")
    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    # ---- 自校验 ----
    fences = txt.count("```")
    assert fences % 2 == 0, f"代码围栏不平衡: {fences}"
    anchors = [slug(t) for t in SEC]
    heads = [slug(ln[3:]) for ln in txt.splitlines() if ln.startswith("## ") and ln != "## 目录"]
    missing = [a for a in anchors if a not in heads]
    assert not missing, f"目录锚点缺失: {missing}"
    print("output :", OUT)
    print("bytes  :", os.path.getsize(OUT), f"({os.path.getsize(OUT)/1024:.1f} KB)")
    print("svg    : 6 张（生成时已逐张 XML 校验）")
    print("fences :", fences, "(balanced)")
    print("anchors:", len(anchors), "/", len(anchors), "全部命中")


if __name__ == "__main__":
    main()
