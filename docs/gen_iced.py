#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust iced 桌面框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_iced.py   (iced 0.13.x，函数式 run/application API)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust-iced桌面框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
ICE = ("#4338ca", "#eef2ff")   # iced indigo（主色）
STA = ("#0d9488", "#f0fdfa")   # state teal
MSG = ("#b45309", "#fffbeb")   # message amber
UPD = ("#0284c7", "#f0f9ff")   # update sky
VIE = ("#7c3aed", "#f5f3ff")   # view violet
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


def t(x, y, s, size=10, col="#1e293b", anchor="start", weight="400", font=SANS):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" '
            f'font-size="{size}" font-weight="{weight}" fill="{col}">{esc(s)}</text>')


def win(x, y, w, h, title, body_fill="#ffffff", bar=ICE[0]):
    """画一个桌面窗口 mockup：标题栏 + 三个红绿灯点 + 内容区。返回 (svg片段, 内容区左上/宽高)。"""
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


def pill(x, y, w, s, fill=ICE[0], tcol="#fff", h=26):
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2:.0f}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{y+h/2+3.5:.0f}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="11" font-weight="700" fill="{tcol}">{esc(s)}</text></g>')


def field(x, y, w, s, h=28, placeholder=True):
    col = "#94a3b8" if placeholder else "#1e293b"
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fff" '
            f'stroke="#cbd5e1" stroke-width="1.3"/>'
            f'<text x="{x+10}" y="{y+h/2+4:.0f}" font-family="{SANS}" font-size="11" fill="{col}">{esc(s)}</text></g>')


def slug(t_):
    """GitHub 风格锚点：保留 CJK/字母数字/连字符，空格转连字符，其余标点丢弃，不折叠连字符。"""
    out = []
    for ch in t_.lower():
        if ch == ' ':
            out.append('-')
        elif ch == '-' or ch.isalnum():
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- FIG 1 TEA 循环
def fig_tea():
    W, H = 900, 430
    b = []
    b.append(box(70, 70, 210, 92, "State（状态）", [
        "你的应用数据结构体", "唯一真源，改它才改界面"], STA))
    b.append(box(620, 70, 210, 92, "view（视图）", [
        "fn(&State) -> Element", "状态的纯函数，只读不改状态"], VIE))
    b.append(box(620, 270, 210, 92, "Message（消息）", [
        "描述「发生了什么」的枚举", "点击/输入/异步完成都产生它"], MSG))
    b.append(box(70, 270, 210, 92, "update（更新）", [
        "fn(&mut State, Message)", "唯一能改状态的地方"], UPD))
    b.append(arrow(280, 116, 620, 116, "① 渲染出界面", STA[0]))
    b.append(arrow(725, 162, 725, 270, "② 交互→消息", VIE[0]))
    b.append(arrow(620, 316, 280, 316, "③ 分发给 update", MSG[0]))
    b.append(arrow(175, 270, 175, 162, "④ 改状态→重画", UPD[0]))
    b.append(t(450, 205, "界面 = f(状态)", 20, ICE[0], "middle", "700", MONO))
    b.append(t(450, 230, "单向数据流 · 状态变更全程可追溯", 12, "#64748b", "middle"))
    b.append(caption(W, 405, "The Elm Architecture（TEA）：状态是唯一真源，界面是它的纯函数；一切改动经 update 一个口子，可追溯、可测试"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 计数器映射
def fig_counter():
    W, H = 920, 380
    b = []
    # 左：窗口 mockup
    b.append(win(50, 70, 190, 250, "Counter"))
    b.append(pill(105, 100, 80, "+", ICE[0], "#fff", 34))
    b.append(t(145, 200, "42", 46, "#0f172a", "middle", "700", MONO))
    b.append(pill(105, 250, 80, "−", GRY[0], "#fff", 34))
    # 中列：Message / update
    b.append(box(330, 80, 230, 66, "Message", ["enum Message { Inc, Dec }"], MSG))
    b.append(box(330, 190, 230, 84, "update", ["Inc => c.value += 1", "Dec => c.value -= 1"], UPD))
    # 右列：State / view
    b.append(box(630, 80, 240, 66, "State", ["struct Counter { value: i64 }"], STA))
    b.append(box(630, 190, 240, 84, "view", [
        'button("+").on_press(Inc)', 'text(c.value) · button("-")…'], VIE))
    # 箭头链：按钮 → Message → update → State → view
    b.append(arrow(240, 110, 330, 105, "点+", MSG[0]))
    b.append(arrow(240, 260, 330, 135, "点-", MSG[0]))
    b.append(arrow(445, 146, 445, 190, "触发", UPD[0]))
    b.append(arrow(560, 210, 645, 146, "改 value", STA[0], curve=True))
    b.append(arrow(750, 146, 750, 190, "读 value", VIE[0]))
    b.append(caption(W, 352, "点按钮 → 产生 Message → update 改 value → State 变 → view 读 value 重新渲染出 42；view 只读、update 只改，数据单向流动"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 运行时全景
def fig_runtime():
    W, H = 940, 440
    b = []
    # 中间核心循环（虚线框）
    b.append(f'<rect x="330" y="40" width="280" height="360" rx="14" fill="#f8fafc" '
             f'stroke="{ICE[0]}" stroke-width="1.8" stroke-dasharray="7 4"/>')
    b.append(t(470, 62, "iced 运行时核心循环", 12.5, ICE[0], "middle", "700", MONO))
    b.append(box(360, 76, 220, 52, "State", ["应用状态"], STA))
    b.append(box(360, 156, 220, 52, "view → 部件树", ["渲染 & 命中测试"], VIE))
    b.append(box(360, 236, 220, 52, "Message 消息队列", ["谁都往这里投递"], MSG))
    b.append(box(360, 316, 220, 52, "update", ["改状态 · 可返回 Task"], UPD))
    b.append(arrow(470, 128, 470, 156))
    b.append(arrow(470, 208, 470, 236))
    b.append(arrow(470, 288, 470, 316))
    b.append(arrow(360, 342, 300, 342, "", UPD[0]))
    b.append(arrow(300, 342, 300, 102, "", UPD[0]))
    b.append(arrow(300, 102, 360, 102, "改状态→重画", UPD[0]))
    # 左：Subscription
    b.append(box(40, 150, 240, 150, "Subscription（持续事件源）", [
        "time::every 定时器", "keyboard 键鼠事件", "网络/WebSocket 流", "mpsc channel 外部推送",
        "", "→ 源源不断产出 Message"], GRN))
    b.append(arrow(280, 258, 360, 258, "订阅→消息", GRN[0]))
    # 右：Task
    b.append(box(660, 150, 240, 150, "Task（一次性副作用）", [
        "Task::perform(future, Msg)", "HTTP 请求 / 读文件 / 计时", "异步在 executor 上跑",
        "完成后把结果包成 Message", "", "→ 回投到消息队列"], MSG))
    b.append(arrow(580, 342, 660, 300, "update 返回 Task", MSG[0], curve=True))
    b.append(arrow(660, 220, 580, 262, "完成→消息", MSG[0], curve=True))
    b.append(caption(W, 424, "核心循环之外的两个输入口：Subscription 是「持续订阅的事件流」，Task 是「一次性异步副作用」——都以产出 Message 的方式回到循环"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 布局系统
def fig_layout():
    W, H = 940, 430
    b = []
    # 左：窗口布局 mockup
    b.append(win(40, 50, 470, 330, "布局：Column 套 Row"))
    # 标题栏区
    b.append(f'<rect x="56" y="92" width="438" height="40" rx="5" fill="{ICE[1]}" stroke="{ICE[0]}" stroke-width="1.2"/>')
    b.append(t(66, 116, "Header  ·  Row { height: Fixed(40), width: Fill }", 10.5, ICE[0], "start", "700", MONO))
    # body：sidebar + content
    b.append(f'<rect x="56" y="142" width="120" height="180" rx="5" fill="{STA[1]}" stroke="{STA[0]}" stroke-width="1.2"/>')
    b.append(t(116, 228, "Sidebar", 11, STA[0], "middle", "700", MONO))
    b.append(t(116, 246, "Fixed(120)", 9.5, "#64748b", "middle", "400", MONO))
    b.append(f'<rect x="184" y="142" width="310" height="180" rx="5" fill="{VIE[1]}" stroke="{VIE[0]}" stroke-width="1.2"/>')
    b.append(t(339, 228, "Content", 11, VIE[0], "middle", "700", MONO))
    b.append(t(339, 246, "width: Fill（吃掉剩余）", 9.5, "#64748b", "middle", "400", MONO))
    # status bar
    b.append(f'<rect x="56" y="332" width="438" height="34" rx="5" fill="{GRY[1]}" stroke="{GRY[0]}" stroke-width="1.2"/>')
    b.append(t(66, 353, "Footer · Row { padding: 8, spacing: 12 }", 10.5, GRY[0], "start", "700", MONO))
    # 右：Length 速查
    b.append(box(540, 50, 360, 200, "Length：部件怎么占空间", [
        "Fill              占满父容器剩余空间",
        "FillPortion(n)    按比例分（2 拿 1 的两倍）",
        "Fixed(px)         固定像素",
        "Shrink            恰好裹住内容（默认）",
        "",
        "Row  横向排 · Column 纵向排",
        "Container         单子居中/加边/背景",
        "Space / Rule      占位 / 分割线"], ICE))
    # FillPortion 比例小图
    b.append(t(540, 285, "FillPortion 分配示意（1 : 2 : 1）:", 11, "#334155", "start", "700"))
    xx = 540
    for w_, lab, cc in ((90, "1", STA), (180, "2", ICE), (90, "1", VIE)):
        b.append(f'<rect x="{xx}" y="298" width="{w_}" height="34" rx="5" fill="{cc[1]}" stroke="{cc[0]}" stroke-width="1.3"/>')
        b.append(t(xx + w_ / 2, 320, lab, 13, cc[0], "middle", "700", MONO))
        xx += w_ + 5
    b.append(t(540, 358, "对齐 .align_x/.align_y · 间距 .spacing · 内边距 .padding", 10, "#475569", "start"))
    b.append(caption(W, 408, "布局三板斧：Row/Column 排方向，Length 定占用，spacing/padding/align 调间距与对齐——没有 CSS，全用 Rust 组合表达"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 Widget 画廊
def fig_widgets():
    W, H = 940, 500
    b = []
    b.append(win(30, 40, 880, 430, "iced::widget 常用部件画廊"))
    cells = [
        # (col,row, 画法, 代码, 说明)
        ("button",    'pill',   'button("保存").on_press(M)',   "可点按钮"),
        ("text",      'text',   'text("普通文本").size(16)',     "文本标签"),
        ("text_input", 'field', 'text_input("提示", &v)',        "单行输入"),
        ("checkbox",  'check',  'checkbox("记住我", b)',          "复选框"),
        ("radio",     'radio',  'radio("A", V::A, sel, M)',       "单选"),
        ("toggler",   'toggle', 'toggler(on).on_toggle(M)',       "开关"),
        ("slider",    'slider', 'slider(0..=100, v, M)',          "滑块"),
        ("pick_list", 'pick',   'pick_list(opts, sel, M)',        "下拉选择"),
        ("progress_bar", 'prog', 'progress_bar(0.0..=1.0, v)',    "进度条"),
        ("container", 'cont',   'container(x).padding(10)',       "容器/加边"),
        ("scrollable", 'scroll', 'scrollable(long_col)',          "滚动区"),
        ("tooltip/svg", 'media', 'image / svg / tooltip',         "图像/提示"),
    ]
    x0, y0, cw, ch = 55, 85, 215, 128
    for i, (name, kind, code, desc) in enumerate(cells):
        cx = x0 + (i % 4) * cw
        cy = y0 + (i // 4) * ch
        b.append(f'<rect x="{cx}" y="{cy}" width="{cw-15}" height="{ch-16}" rx="8" fill="#fff" stroke="#e2e8f0" stroke-width="1.2"/>')
        b.append(t(cx + 12, cy + 20, name + "()", 11.5, ICE[0], "start", "700", MONO))
        mx, my = cx + 12, cy + 34
        # 各部件迷你画法
        if kind == 'pill':
            b.append(pill(mx, my, 78, "保存", ICE[0], "#fff", 24))
        elif kind == 'text':
            b.append(t(mx, my + 16, "普通文本 Abc", 15, "#0f172a", "start", "400"))
        elif kind == 'field':
            b.append(field(mx, my, 170, "提示文字…", 26))
        elif kind == 'check':
            b.append(f'<rect x="{mx}" y="{my+2}" width="18" height="18" rx="4" fill="{ICE[0]}"/>')
            b.append(f'<path d="M {mx+4} {my+11} l 4 4 l 7 -8" stroke="#fff" stroke-width="2" fill="none"/>')
            b.append(t(mx + 26, my + 15, "记住我", 12, "#1e293b"))
        elif kind == 'radio':
            b.append(f'<circle cx="{mx+9}" cy="{my+11}" r="8" fill="#fff" stroke="{ICE[0]}" stroke-width="2"/>')
            b.append(f'<circle cx="{mx+9}" cy="{my+11}" r="4" fill="{ICE[0]}"/>')
            b.append(t(mx + 24, my + 15, "选项 A", 12, "#1e293b"))
            b.append(f'<circle cx="{mx+95}" cy="{my+11}" r="8" fill="#fff" stroke="#94a3b8" stroke-width="2"/>')
            b.append(t(mx + 110, my + 15, "B", 12, "#64748b"))
        elif kind == 'toggle':
            b.append(f'<rect x="{mx}" y="{my+3}" width="42" height="20" rx="10" fill="{GRN[0]}"/>')
            b.append(f'<circle cx="{mx+32}" cy="{my+13}" r="8" fill="#fff"/>')
            b.append(t(mx + 52, my + 17, "启用", 12, "#1e293b"))
        elif kind == 'slider':
            b.append(f'<rect x="{mx}" y="{my+9}" width="150" height="5" rx="2.5" fill="#e2e8f0"/>')
            b.append(f'<rect x="{mx}" y="{my+9}" width="95" height="5" rx="2.5" fill="{ICE[0]}"/>')
            b.append(f'<circle cx="{mx+95}" cy="{my+11}" r="9" fill="{ICE[0]}"/>')
        elif kind == 'pick':
            b.append(field(mx, my, 150, "选一个 ▾", 26, placeholder=False))
        elif kind == 'prog':
            b.append(f'<rect x="{mx}" y="{my+6}" width="170" height="12" rx="6" fill="#e2e8f0"/>')
            b.append(f'<rect x="{mx}" y="{my+6}" width="102" height="12" rx="6" fill="{GRN[0]}"/>')
            b.append(t(mx + 176, my + 16, "60%", 10, "#64748b"))
        elif kind == 'cont':
            b.append(f'<rect x="{mx}" y="{my}" width="120" height="52" rx="6" fill="{ICE[1]}" stroke="{ICE[0]}" stroke-width="1.3"/>')
            b.append(t(mx + 60, my + 30, "内容居中", 11, ICE[0], "middle"))
        elif kind == 'scroll':
            b.append(f'<rect x="{mx}" y="{my}" width="150" height="54" rx="6" fill="#fff" stroke="#cbd5e1" stroke-width="1.2"/>')
            for k in range(3):
                b.append(t(mx + 8, my + 16 + k * 15, f"第 {k+1} 行……", 10, "#64748b"))
            b.append(f'<rect x="{mx+140}" y="{my+4}" width="5" height="22" rx="2.5" fill="{ICE[0]}"/>')
        elif kind == 'media':
            b.append(f'<rect x="{mx}" y="{my}" width="52" height="52" rx="6" fill="{VIE[1]}" stroke="{VIE[0]}" stroke-width="1.3"/>')
            b.append(f'<circle cx="{mx+18}" cy="{my+20}" r="7" fill="{VIE[0]}"/>')
            b.append(f'<path d="M {mx+8} {my+46} l 14 -16 l 10 10 l 8 -8 l 12 14 z" fill="{VIE[0]}"/>')
            b.append(t(mx + 62, my + 30, "image/svg", 10.5, "#64748b"))
        b.append(t(cx + 12, cy + ch - 26, code, 8.6, "#475569", "start", "400", MONO))
        b.append(t(cx + 12, cy + ch - 13, "→ " + desc, 9.5, "#94a3b8", "start"))
    b.append(caption(W, 490, "iced::widget 里每个部件都是一个函数，返回值链式配置（.on_press/.size/.padding/.style…），最后 .into() 成 Element"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 双主题
def fig_theme():
    W, H = 940, 440
    b = []
    # 亮色窗
    b.append(win(50, 50, 200, 210, "Light", "#ffffff", ICE[0]))
    b.append(pill(90, 90, 120, "+1", ICE[0], "#fff", 30))
    b.append(t(150, 160, "42", 34, "#0f172a", "middle", "700", MONO))
    b.append(pill(90, 200, 120, "-1", "#64748b", "#fff", 30))
    # 暗色窗
    b.append(win(300, 50, 200, 210, "Dark", "#1a1b26", "#24283b"))
    b.append(pill(340, 90, 120, "+1", "#7aa2f7", "#1a1b26", 30))
    b.append(t(400, 160, "42", 34, "#c0caf5", "middle", "700", MONO))
    b.append(pill(340, 200, 120, "-1", "#414868", "#c0caf5", 30))
    b.append(arrow(250, 155, 300, 155, ".theme()", ICE[0]))
    b.append(t(275, 285, "同一份 view 代码", 10.5, "#64748b", "middle"))
    # 右：palette 色板
    b.append(box(560, 50, 340, 118, "Theme → extended_palette()", [
        "内置：Light / Dark / Dracula / Nord /",
        "TokyoNight / Catppuccin / SolarizedLight …",
        "或自定义 Palette（背景/主色/文字/成功/危险）"], ICE))
    # 色板
    sw = [("background", "#ffffff"), ("primary", "#4338ca"), ("success", "#15803d"),
          ("danger", "#dc2626"), ("text", "#0f172a")]
    b.append(t(560, 195, "palette 五类角色色（示意）:", 11, "#334155", "start", "700"))
    xx = 560
    for name, cc in sw:
        b.append(f'<rect x="{xx}" y="205" width="62" height="34" rx="6" fill="{cc}" stroke="#cbd5e1" stroke-width="1"/>')
        b.append(t(xx + 31, 258, name, 8.5, "#64748b", "middle", "400", MONO))
        xx += 68
    b.append(box(180, 300, 580, 74, "禁硬编码色值（对齐 CMX 硬约束）", [
        "✔ 从 theme.extended_palette() 派生：palette.primary.strong.color",
        "✘ 别写死 Color::from_rgb(0.26, 0.22, 0.79) —— 一换主题就掉队、暗色下刺眼"], DAN))
    b.append(caption(W, 402, "换主题只改 .theme() 回调，view 一行不动：因为部件颜色都从 Theme 的 palette 派生，而非写死——这正是 CMX「双主题通路」的同款要求"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 7 组件组合
def fig_compose():
    W, H = 940, 420
    b = []
    b.append(f'<rect x="40" y="44" width="860" height="300" rx="14" fill="#f8fafc" stroke="{ICE[0]}" stroke-width="1.8"/>')
    b.append(t(60, 68, "父 App：struct App { left: Counter, right: Timer }   enum Message { Left(c::Msg), Right(t::Msg) }",
               11, ICE[0], "start", "700", MONO))
    # 两个子组件盒
    b.append(box(90, 92, 300, 120, "子组件 Counter（自带一套四件套）", [
        "struct Counter { value }",
        "enum Msg { Inc, Dec }",
        "fn update(&mut, Msg)",
        "fn view(&) -> Element<'_, Msg>"], STA))
    b.append(box(550, 92, 300, 120, "子组件 Timer（自带一套四件套）", [
        "struct Timer { elapsed }",
        "enum Msg { Tick }",
        "fn update(&mut, Msg)",
        "fn view(&) -> Element<'_, Msg>"], VIE))
    # 父 lane
    b.append(box(300, 258, 340, 62, "父 update / view", [
        "view: self.left.view().map(Message::Left)",
        "update: Message::Left(m) => self.left.update(m)"], UPD))
    b.append(arrow(250, 212, 330, 258, ".map(Message::Left)", STA[0]))
    b.append(arrow(360, 258, 280, 212, "", STA[0], curve=True))
    b.append(arrow(690, 212, 610, 258, ".map(Message::Right)", VIE[0]))
    b.append(arrow(580, 258, 660, 212, "", VIE[0], curve=True))
    b.append(caption(W, 378, "组件化=把「四件套」按子模块复制，子 Message 用 Element::map 包进父 Message；父 update 用 match 拆包再分发。层层如此，应用可无限组合"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 8 Todo 界面
def fig_todo():
    W, H = 640, 440
    b = []
    b.append(win(80, 40, 480, 360, "Todos — iced"))
    # 输入行
    b.append(field(105, 92, 320, "要做点什么？", 34))
    b.append(pill(438, 95, 96, "添加", ICE[0], "#fff", 28))
    # 分割线
    b.append(f'<line x1="105" y1="142" x2="534" y2="142" stroke="#e2e8f0" stroke-width="1.4"/>')
    items = [("写 iced 使用说明", True), ("画 8 张 SVG 图", True), ("跑 gen_iced.py 校验", False)]
    yy = 158
    for txt_, done in items:
        # checkbox
        if done:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="{GRN[0]}"/>')
            b.append(f'<path d="M 116 {yy+10} l 4 4 l 8 -9" stroke="#fff" stroke-width="2.2" fill="none"/>')
            b.append(f'<text x="142" y="{yy+15}" font-family="{SANS}" font-size="12.5" fill="#94a3b8" '
                     f'text-decoration="line-through">{esc(txt_)}</text>')
        else:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="#fff" stroke="#94a3b8" stroke-width="1.8"/>')
            b.append(t(142, yy + 15, txt_, 12.5, "#1e293b"))
        b.append(pill(486, yy - 3, 44, "删", DAN[0], "#fff", 24))
        yy += 42
    # 计数行
    b.append(f'<line x1="105" y1="298" x2="534" y2="298" stroke="#e2e8f0" stroke-width="1.4"/>')
    b.append(t(112, 322, "共 3 项 · 已完成 2 项", 12, "#64748b", "start", "700"))
    b.append(pill(430, 310, 104, "清除已完成", "#64748b", "#fff", 26))
    b.append(caption(W, 424, "第 13 节的完整实例成品：输入框 + 添加 + 列表（复选框/删除）+ 计数。约 60 行可编译代码即得此界面"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_tea(), "图1：Elm 架构（TEA）循环")
IMG2 = b64img(fig_counter(), "图2：计数器 UI 与四件套映射")
IMG3 = b64img(fig_runtime(), "图3：iced 运行时全景（Task + Subscription）")
IMG4 = b64img(fig_layout(), "图4：布局系统")
IMG5 = b64img(fig_widgets(), "图5：常用 Widget 画廊")
IMG6 = b64img(fig_theme(), "图6：双主题与调色板")
IMG7 = b64img(fig_compose(), "图7：组件组合与消息嵌套")
IMG8 = b64img(fig_todo(), "图8：Todo 应用界面")

SEC = [
    "一、iced 是什么：一张图看懂 Elm 架构",
    "二、安装与第一个程序",
    "三、四件套详解：State · Message · update · view",
    "四、两套入口：iced::run 与 iced::application",
    "五、Widget 速查：常用部件一览",
    "六、布局系统：Row · Column · Container · Length",
    "七、样式与主题：Theme 与调色板",
    "八、副作用与异步：Task",
    "九、外部事件：Subscription",
    "十、组件化：拆分模块与消息嵌套",
    "十一、Canvas 自定义绘制",
    "十二、中文字体与输入法：必须知道的坑",
    "十三、完整实例：待办事项 Todo",
    "十四、常见坑速查",
    "十五、与 CMX 工作区的呼应",
    "十六、版本与参考资源",
]


def main():
    D = []
    A = D.append
    A("# Rust iced 桌面框架详细使用说明")
    A("")
    A("> **定位**：iced 是**受 Elm 启发的纯 Rust GUI 库**——用 `State + Message + update + view` 四件套写界面，界面是状态的纯函数，数据单向流动、状态变更全程可追溯。自绘（wgpu + tiny-skia 软件兜底），被 System76 选为整个 **COSMIC 桌面环境**的 UI 框架，体量已被验证。")
    A("> **版本基线（2026-09）**：iced **0.13.x**（0.14 开发中）。本文用 **0.13 的函数式 API**（`iced::run` / `iced::application`）——它已取代旧的 `Sandbox` / `Application` trait 写法（第四节给对照）。")
    A("> **一句话取舍**：给「愿意用 Rust 把桌面应用写成一门可长期演进的架构」的人；短板是官方自称 experimental、0.x 间 API 会大改、编译偏慢、无官方移动端、中文要自带字体。")
    A("> **图**：8 张内嵌 base64 SVG，无外部依赖。所有易变 API 处均标注「以 docs.rs 对应版本为准」。")
    A("")
    A("> 姊妹篇：横向对比见 `docs/20260920_Rust桌面GUI框架横评.md`（iced vs egui vs Dioxus vs Tauri vs Slint）。本文是 iced 单框架的 how-to 深挖。")
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
    A("iced 只有一个核心思想，理解它就理解了全部——**界面是状态的纯函数**：")
    A("")
    A("- **State（状态）**：一个普通结构体，装着应用的全部数据。它是**唯一真源**。")
    A("- **view（视图）**：`fn(&State) -> Element<Message>`。读状态，产出这一刻该长什么样。**只读，绝不改状态**。")
    A("- **Message（消息）**：一个枚举，描述「发生了什么」（按了按钮、输入了字、异步请求回来了）。")
    A("- **update（更新）**：`fn(&mut State, Message)`。收到消息，改状态。**这是全应用唯一能改状态的地方**。")
    A("")
    A("循环往复：`view` 画出界面 → 用户交互产生 `Message` → `update` 改 `State` → 状态变了，`iced` 自动重新调 `view` 重画。你永远不用手动「刷新界面」，只管把状态改对。")
    A("")
    A("> 这套模式（The Elm Architecture, TEA）的最大价值：**状态从哪来、被谁改、怎么变，全程可追溯**。所有变更收敛到 `update` 一个口子，天然好测试、好调试、好推理——大型应用不易腐化，这也是 COSMIC 敢用它做整个桌面的原因。")
    A("")
    # 二
    A(f"## {SEC[1]}")
    A("")
    A("新建项目，`Cargo.toml` 加依赖：")
    A("")
    A("```toml")
    A(r'''[dependencies]
iced = "0.13"

# 按需开 feature（可选）：
# iced = { version = "0.13", features = [
#   "tokio",    # 用 tokio 作 async executor（配合 Task::perform 跑 HTTP/IO）
#   "image",    # image(...) 部件
#   "svg",      # svg(...) 部件
#   "canvas",   # 自定义 2D 绘制（第 11 节）
#   "debug",    # F12 调出布局调试面板
#   "markdown", "highlighter",  # 富文本/代码高亮
# ] }''')
    A("```")
    A("")
    A("`src/main.rs`——一个能编译能跑的最小计数器，**全文就这些**：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{button, column, text, Column};

// ① State：应用状态（这里用 Default 生成初始值 value = 0）
#[derive(Default)]
struct Counter {
    value: i64,
}

// ② Message：会发生的事
#[derive(Debug, Clone, Copy)]
enum Message {
    Increment,
    Decrement,
}

// ③ update：收到消息改状态（本例不需要副作用，返回 ()）
fn update(counter: &mut Counter, message: Message) {
    match message {
        Message::Increment => counter.value += 1,
        Message::Decrement => counter.value -= 1,
    }
}

// ④ view：状态 -> 界面
fn view(counter: &Counter) -> Column<'_, Message> {
    column![
        button("+").on_press(Message::Increment),
        text(counter.value).size(50),
        button("-").on_press(Message::Decrement),
    ]
    .padding(20)
    .spacing(10)
}

fn main() -> iced::Result {
    // 标题 + update + view，三者一交，窗口就起来了
    iced::run("计数器", update, view)
}''')
    A("```")
    A("")
    A("`cargo run` 就能看到窗口。`iced::run` 是最短入口：它要求 `State: Default`（用默认值初始化），`Message: Debug + Send + 'static`。**注意**：默认字体不含中文，`text(\"中文\")` 会显示成豆腐块——先跑通英文，中文字体见第 12 节。")
    A("")
    # 三
    A(f"## {SEC[2]}")
    A("")
    A(IMG2)
    A("")
    A("把上面计数器的四件套拆开看，各自的边界要牢记：")
    A("")
    A("**① State**——纯数据，不含 UI：")
    A("")
    A("```rust")
    A(r'''#[derive(Default)]
struct Counter { value: i64 }   // 想加字段就加，它就是你的「单一数据源」''')
    A("```")
    A("")
    A("**② Message**——尽量用「发生了什么」命名，而非「该怎么做」：")
    A("")
    A("```rust")
    A(r'''#[derive(Debug, Clone)]
enum Message {
    Increment,                 // 好：描述事件
    Decrement,
    InputChanged(String),      // 携带数据的消息（输入框内容变了）
    Submitted,
}
// 约束：至少 Clone + Send + 'static；含数据也要能 Clone''')
    A("```")
    A("")
    A("**③ update**——唯一改状态处；需要副作用（异步/IO）时返回 `Task`（第 8 节），否则返回 `()`：")
    A("")
    A("```rust")
    A(r'''fn update(state: &mut Counter, message: Message) {
    match message {
        Message::Increment => state.value += 1,
        Message::Decrement => state.value -= 1,
        _ => {}
    }
    // 想跑异步就把签名改成 -> Task<Message>，见第 8 节
}''')
    A("```")
    A("")
    A("**④ view**——状态的纯函数，**每次状态变都会被重新调用**（所以别在里面做重活/改状态）：")
    A("")
    A("```rust")
    A(r'''fn view(state: &Counter) -> iced::Element<'_, Message> {
    column![
        button("+").on_press(Message::Increment),
        text(state.value).size(50),
        button("-").on_press(Message::Decrement),
    ]
    .into()   // 返回 Element 时用 .into()；返回具体的 Column 时可省
}''')
    A("```")
    A("")
    A("> `Element<'a, Message>` 是所有部件的统一「装箱」类型。`view` 可以返回具体类型（如 `Column`）也可以 `.into()` 成 `Element`。带生命周期 `'a` 是因为部件可能借用了 `state` 里的数据。")
    A("")
    # 四
    A(f"## {SEC[3]}")
    A("")
    A("`iced::run` 够简单但能配的东西少。要设主题、订阅、窗口大小、带初始 `Task`，用 `iced::application` 这个 **builder**：")
    A("")
    A("```rust")
    A(r'''use iced::{Task, Theme, window};

fn main() -> iced::Result {
    iced::application("我的应用", update, view)
        .theme(|_state| Theme::TokyoNight)     // 主题（可根据状态动态返回）
        .subscription(subscription)            // 订阅外部事件（第 9 节）
        .window_size((900.0, 600.0))           // 初始窗口尺寸
        .antialiasing(true)
        .run()
}

// 如果初始状态不能靠 Default，或启动就要跑一个 Task：
fn main() -> iced::Result {
    iced::application("我的应用", update, view)
        .run_with(|| {
            let state = MyApp::new();
            let boot = Task::perform(load_config(), Message::Loaded);  // 启动即加载
            (state, boot)
        })
}''')
    A("```")
    A("")
    A("几个入口的关系：")
    A("")
    A("| 入口 | 何时用 | 备注 |")
    A("|---|---|---|")
    A("| `iced::run(title, update, view)` | 最简单，`State: Default` | 内部就是 `application(..).run()` |")
    A("| `iced::application(title, update, view)` | 要 theme/subscription/window/初始 Task | builder，链式配置后 `.run()` / `.run_with()` |")
    A("| `iced::daemon(...)` | **多窗口**应用 | 管理窗口集合，`view` 按 `window::Id` 分发 |")
    A("")
    A("**与旧写法对照**（0.12 及更早的教程里常见，0.13 已不推荐）：")
    A("")
    A("```rust")
    A(r'''// 旧：impl Sandbox / impl Application（trait 风格）—— 0.13 起改成上面的函数式
// trait Sandbox { type Message; fn new()->Self; fn title(&self)->String;
//                 fn update(&mut self, m: Message); fn view(&self)->Element<Message>; }
// 迁移：把 trait 的四个方法拆成自由函数 update/view + iced::run/application 即可。
// （Application trait 仍在底层存在，但日常写业务用函数式入口更省样板）''')
    A("```")
    A("")
    A("> 版本提示：`run` / `application` 的**具体方法名与签名在 0.13.x 内也微调过**（如 `.window_size` 与 `window::Settings` 的关系、`run_with` 的闭包返回）。落地时以你锁定版本的 docs.rs 为准，别照抄跨版本教程。")
    A("")
    # 五
    A(f"## {SEC[4]}")
    A("")
    A(IMG5)
    A("")
    A("所有部件都在 `iced::widget` 下，**每个都是一个函数**，返回值链式配置。最常用的一批：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{
    button, text, text_input, checkbox, radio, toggler,
    slider, pick_list, progress_bar, container, scrollable,
    column, row, Space, horizontal_rule,
};

// 文本 & 按钮
text("普通文本").size(16);
button("保存").on_press(Message::Save);          // 不给 on_press = 禁用态

// 输入框：(占位符, 当前值) + 回调
text_input("请输入…", &state.input)
    .on_input(Message::InputChanged)             // 每次输入
    .on_submit(Message::Submit);                 // 回车

// 勾选 / 单选 / 开关
checkbox("记住我", state.remember).on_toggle(Message::ToggleRemember);
radio("选项 A", Choice::A, state.choice, Message::ChoicePicked);
toggler(state.on).label("启用").on_toggle(Message::Toggled);

// 滑块 / 下拉 / 进度
slider(0..=100, state.volume, Message::VolumeChanged);
pick_list(&Fruit::ALL[..], state.fruit, Message::FruitPicked);
progress_bar(0.0..=1.0, state.progress);''')
    A("```")
    A("")
    A("常用部件速查：")
    A("")
    A("| 部件 | 作用 | 关键方法 |")
    A("|---|---|---|")
    A("| `text` / `text!` | 文本 | `.size()` `.color()` `.font()` |")
    A("| `button` | 按钮 | `.on_press(Msg)`（省则禁用）`.style()` |")
    A("| `text_input` | 单行输入 | `.on_input()` `.on_submit()` `.secure(true)` |")
    A("| `checkbox` / `toggler` | 复选 / 开关 | `.on_toggle(Msg)` |")
    A("| `radio` | 单选 | `radio(label, value, selected, Msg)` |")
    A("| `slider` / `vertical_slider` | 滑块 | `slider(range, value, Msg).step(..)` |")
    A("| `pick_list` / `combo_box` | 下拉 / 可搜索下拉 | `pick_list(options, selected, Msg)` |")
    A("| `progress_bar` | 进度 | `progress_bar(range, value)` |")
    A("| `image` / `svg` | 位图 / 矢量图 | 需 `image` / `svg` feature |")
    A("| `container` | 单子容器 | `.padding()` `.center(Fill)` `.style()` |")
    A("| `scrollable` | 滚动区 | 包住溢出内容 |")
    A("| `Space` / `Rule` | 占位 / 分割线 | `Space::with_height()` `horizontal_rule(1)` |")
    A("")
    A("> 布局容器 `column!` / `row!` 是宏（元素数量可变），也有函数版 `column(vec)` / `row(vec)` 用于动态列表（第 13 节 Todo 就用它遍历渲染）。")
    A("")
    # 六
    A(f"## {SEC[5]}")
    A("")
    A(IMG4)
    A("")
    A("iced **没有 CSS**，布局全靠 `Row` / `Column` / `Container` 三种容器 + `Length` 组合表达。")
    A("")
    A("**方向：`Row` 横排、`Column` 纵排**，都能设 `spacing`（子元素间距）、`padding`（内边距）、对齐：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{row, column, container};
use iced::{Center, Fill, Fixed};

row![left, middle, right]
    .spacing(12)                 // 子元素之间 12px
    .padding(16)                 // 四周内边距
    .align_y(Center);            // 交叉轴（纵向）居中

column![header, body, footer]
    .spacing(8)
    .align_x(Center);            // 交叉轴（横向）居中''')
    A("```")
    A("")
    A("**占用空间：`Length`** 决定一个部件横/纵向占多少：")
    A("")
    A("```rust")
    A(r'''use iced::{Length, Fill, Shrink};

element.width(Fill);                        // 占满父容器剩余
element.width(Length::FillPortion(2));      // 与其他 FillPortion 按比例分
element.width(Length::Fixed(240.0));        // 固定 240px
element.width(Shrink);                      // 恰好裹住内容（多数部件默认）

// 居中一个东西：Container 撑满 + 内部居中
container(my_widget)
    .width(Fill).height(Fill)
    .center_x(Fill).center_y(Fill);         // 或新版 .center(Fill) 一次搞定''')
    A("```")
    A("")
    A("| `Length` | 含义 |")
    A("|---|---|")
    A("| `Fill` | 占满父容器给的剩余空间 |")
    A("| `FillPortion(n)` | 多个一起时按权重 `n` 瓜分（`2` 是 `1` 的两倍宽） |")
    A("| `Fixed(px)` | 固定像素 |")
    A("| `Shrink` | 恰好包住内容（大多数部件的默认） |")
    A("")
    A("> 便捷常量：`iced` 顶层 re-export 了 `Fill` / `Shrink` / `Center` / `Left` / `Right` / `Top` / `Bottom`，省得每次写 `Length::Fill` / `alignment::Horizontal::Center`。这些 re-export 也随版本增补，缺了就用全名。")
    A("")
    # 七
    A(f"## {SEC[6]}")
    A("")
    A(IMG6)
    A("")
    A("iced 的主题系统由 `Theme` 承载一套 `Palette`（调色板），部件的**样式函数**从 palette 取色——所以换主题时 `view` 一行不用动。")
    A("")
    A("**设主题**（`application` 的 `.theme()` 回调，可依状态动态返回）：")
    A("")
    A("```rust")
    A(r'''use iced::Theme;

iced::application("app", update, view)
    .theme(|state| if state.dark { Theme::Dark } else { Theme::Light })
    .run()

// 内置主题很多：Light / Dark / Dracula / Nord / SolarizedLight /
//               TokyoNight / CatppuccinMocha / GruvboxDark …''')
    A("```")
    A("")
    A("**部件样式**：内置了一批语义化样式函数，直接传给 `.style()`：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{button, text};

button("主操作").on_press(M).style(button::primary);
button("危险操作").on_press(M).style(button::danger);   // 还有 secondary/success/text
text("警告").style(text::danger);''')
    A("```")
    A("")
    A("**自定义样式**：一个 `fn(&Theme, Status) -> Style`，颜色**必须从 `theme.extended_palette()` 派生**：")
    A("")
    A("```rust")
    A(r'''use iced::widget::button;
use iced::{Theme, Border};

fn my_button(theme: &Theme, status: button::Status) -> button::Style {
    let palette = theme.extended_palette();          // ← 从主题取色，不写死
    let base = button::Style {
        background: Some(palette.primary.strong.color.into()),
        text_color: palette.primary.strong.text,
        border: Border { radius: 8.0.into(), ..Default::default() },
        ..Default::default()
    };
    match status {
        button::Status::Hovered => button::Style {
            background: Some(palette.primary.base.color.into()),
            ..base
        },
        _ => base,
    }
}
// 用：button("x").on_press(M).style(my_button)
// 注意：Style 的具体字段名/结构随版本有别，以 docs.rs 对应版本为准。''')
    A("```")
    A("")
    A("> **对齐 CMX 硬约束 #4（页面/组件双主题兼容，禁硬编码色值）**：iced 里同理——颜色一律走 `extended_palette()` 派生，**绝不** `Color::from_rgb(...)` 写死。写死的后果就是一换暗色主题整片掉队、对比度崩坏。这条在自绘 GUI 里和在 Web 里是同一个道理。")
    A("")
    # 八
    A(f"## {SEC[7]}")
    A("")
    A(IMG3)
    A("")
    A("`update` 里不能直接 `.await`——异步/IO 这类**副作用**要交给 `Task`（0.12 及以前叫 `Command`，0.13 改名 `Task`）。让 `update` 返回 `Task<Message>`：iced 在后台 executor 上跑它，完成后把结果**包成一条新 Message 再投回 `update`**。")
    A("")
    A("```rust")
    A(r'''use iced::Task;

#[derive(Debug, Clone)]
enum Message {
    Refresh,
    Loaded(Result<String, String>),   // 异步结果作为一条消息回来
}

fn update(state: &mut App, message: Message) -> Task<Message> {
    match message {
        Message::Refresh => {
            state.loading = true;
            // 发起异步：future 跑完 → 用 Message::Loaded 包住结果回投
            Task::perform(fetch_data(), Message::Loaded)
        }
        Message::Loaded(result) => {
            state.loading = false;
            state.data = result.ok();
            Task::none()                // 无后续副作用
        }
    }
}

async fn fetch_data() -> Result<String, String> {
    // 需开 "tokio" feature；示意用 reqwest
    // reqwest::get("https://example.com").await...
    Ok("hello".into())
}''')
    A("```")
    A("")
    A("`Task` 的常用构造：")
    A("")
    A("| 构造 | 作用 |")
    A("|---|---|")
    A("| `Task::none()` | 什么都不做（同步分支用它收尾） |")
    A("| `Task::perform(future, Msg)` | 跑一个 `Future`，结果 `map` 成 `Msg` 回投 |")
    A("| `Task::batch([t1, t2])` | 并发跑多个 Task |")
    A("| `Task::done(Msg)` | 立刻投一条消息（不经异步） |")
    A("| 部件动作（如 `text_input::focus(id)`） | 命令式操作 UI（聚焦/滚动等）也返回 Task |")
    A("")
    A("> 关键心智：**副作用不在 `update` 里同步执行，而是「声明一个 Task 交给运行时」**。这保持了 `update` 本身是快速、可预测的纯状态转移——异步结果最终也只是「又一条 Message」。想跑 Task 必须开 executor feature（如 `tokio`）。")
    A("")
    # 九
    A(f"## {SEC[8]}")
    A("")
    A("`Task` 是「发起一次就结束」的一次性副作用；**持续的外部事件流**（定时器 tick、键盘、WebSocket、后台线程推送）用 `Subscription`。它挂在 `application` 的 `.subscription()` 上，iced 按你返回的订阅**持续把事件转成 Message**。")
    A("")
    A("```rust")
    A(r'''use iced::{Subscription, keyboard, time};
use std::time::Duration;

fn subscription(state: &App) -> Subscription<Message> {
    let mut subs = vec![
        // 每秒一个 tick（做时钟/轮询/动画）
        time::every(Duration::from_secs(1)).map(|_| Message::Tick),
        // 键盘按下
        keyboard::on_key_press(|key, _modifiers| match key {
            keyboard::Key::Named(keyboard::key::Named::Escape) => Some(Message::Escape),
            _ => None,
        }),
    ];

    // 订阅可依状态开关：暂停时就不订定时器
    if state.paused {
        subs.retain(|_| false);
    }
    Subscription::batch(subs)
}''')
    A("```")
    A("")
    A("典型订阅源：")
    A("")
    A("| 来源 | 用途 |")
    A("|---|---|")
    A("| `time::every(Duration)` | 定时器：时钟、轮询、逐帧动画 |")
    A("| `keyboard::on_key_press` / `on_key_release` | 全局键盘 |")
    A("| `Subscription::run(...)` / `channel` | 把任意 `Stream` / 后台线程（mpsc）接进来（如 WebSocket、日志流） |")
    A("| `Subscription::batch([...])` | 合并多个订阅 |")
    A("")
    A("> `Task` vs `Subscription` 一句话分野：**一次性异步结果 → `Task`；持续不断的事件流 → `Subscription`**。前者你「主动发起」，后者你「声明订阅、被动接收」。二者产物都是 Message，最终都回到 `update`。")
    A("")
    # 十
    A(f"## {SEC[9]}")
    A("")
    A(IMG7)
    A("")
    A("iced 没有「组件」黑魔法——**组件化就是把「四件套」按子模块复制一份**，再用 `Element::map` 把子模块的 `Message` 包进父 `Message`。")
    A("")
    A("```rust")
    A(r'''// ---- 子模块 counter.rs：自带一套 state/message/update/view ----
#[derive(Default)]
pub struct Counter { value: i64 }

#[derive(Debug, Clone, Copy)]
pub enum Message { Inc, Dec }

impl Counter {
    pub fn update(&mut self, message: Message) {
        match message { Message::Inc => self.value += 1, Message::Dec => self.value -= 1 }
    }
    pub fn view(&self) -> iced::Element<'_, Message> {
        iced::widget::row![
            iced::widget::button("-").on_press(Message::Dec),
            iced::widget::text(self.value),
            iced::widget::button("+").on_press(Message::Inc),
        ].into()
    }
}

// ---- 父 App：把子 Message 嵌进自己的 Message ----
#[derive(Default)]
struct App { left: Counter, right: Counter }

#[derive(Debug, Clone, Copy)]
enum Message {
    Left(counter::Message),      // 包住左计数器的消息
    Right(counter::Message),
}

fn update(app: &mut App, message: Message) {
    match message {
        Message::Left(m)  => app.left.update(m),    // 拆包，下发给对应子模块
        Message::Right(m) => app.right.update(m),
    }
}

fn view(app: &App) -> iced::Element<'_, Message> {
    iced::widget::column![
        app.left.view().map(Message::Left),        // 子 Element 的消息 .map 成父消息
        app.right.view().map(Message::Right),
    ].into()
}''')
    A("```")
    A("")
    A("> `Element::map(f)` 是组合的关键：它把 `Element<'a, 子Msg>` 变成 `Element<'a, 父Msg>`（用 `f` 把子消息包成父消息）。父只需在 `update` 里 `match` 拆包、下发给对应子模块的 `update`。**层层如此**，应用可以无限嵌套组合，每层都保持自己那套清晰的四件套。")
    A("")
    # 十一
    A(f"## {SEC[10]}")
    A("")
    A("要画表格线、图表、流程图、签名板这类**自定义 2D 图形**，用 `canvas`（需开 `canvas` feature）。实现 `canvas::Program` trait 的 `draw`：")
    A("")
    A("```rust")
    A(r'''use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Stroke};
use iced::{Color, Fill, Point, Rectangle, Renderer, Theme};

struct Graph;

impl<Message> canvas::Program<Message> for Graph {
    type State = ();

    fn draw(&self, _state: &(), renderer: &Renderer, theme: &Theme,
            bounds: Rectangle, _cursor: iced::mouse::Cursor) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());
        let palette = theme.extended_palette();               // 依旧从主题取色

        // 画一个圆
        let circle = Path::circle(frame.center(), 40.0);
        frame.fill(&circle, palette.primary.strong.color);

        // 画一条折线
        let line = Path::line(Point::new(10.0, 10.0), Point::new(200.0, 120.0));
        frame.stroke(&line, Stroke::default().with_width(2.0)
            .with_color(palette.secondary.base.color));

        vec![frame.into_geometry()]
    }
}

// 在 view 里当普通部件用：
// Canvas::new(Graph).width(Fill).height(Fill)''')
    A("```")
    A("")
    A("> `Program` 还有 `update`（处理 canvas 内的鼠标/键盘，可产出 `Message`）和 `mouse_interaction`（自定义光标）。`State` 关联类型用于 canvas 自己的内部状态（如正在拖拽的点）。复杂图形建议缓存 `Geometry` 避免每帧重建。方法签名随版本有别，以 docs.rs 为准。")
    A("")
    # 十二
    A(f"## {SEC[11]}")
    A("")
    A("**这是中文团队用 iced 的第一个坑**：iced 内置字体不含 CJK 字形，`text(\"中文\")` 直接显示成豆腐块（□□）。必须自己带一个中文字体并设为默认。")
    A("")
    A("```rust")
    A(r'''use iced::Font;

// 把字体文件打进二进制（放个 .ttf/.otf，如思源黑体/苹方子集）
const FONT_BYTES: &[u8] = include_bytes!("../fonts/SourceHanSansSC.otf");
const CJK: Font = Font::with_name("Source Han Sans SC");

fn main() -> iced::Result {
    iced::application("中文应用", update, view)
        .font(FONT_BYTES)          // ① 注册字体数据（可多次，注册多个字体）
        .default_font(CJK)         // ② 设为全局默认，之后 text("中文") 才正常
        .run()
}

// 也可只给某个部件指定字体：text("标题").font(CJK)''')
    A("```")
    A("")
    A("要点与其他坑：")
    A("")
    A("- **字体要嵌 = 包体变大**：完整 CJK 字体几 MB 到十几 MB；生产可用子集化工具（如 `pyftsubset`）裁到常用字。")
    A("- **中文输入法（IME）**：iced 基于 winit，近年 IME 支持有改进，但候选框定位/预编辑等仍可能有毛边；做重输入的中文应用要实测目标平台。")
    A("- **复杂排版**（竖排/复杂换行/RTL）能力有限——重排版需求这是 iced 相对 WebView 路线的短板。")
    A("- **`.font()` 只注册、`.default_font()` 才生效**：只注册不设默认，`text` 仍用内置字体，照样豆腐块。")
    A("")
    A("> 一句话：**中文 iced 应用的第一件事，是 `.font()` + `.default_font()` 把中文字体装上**。这一步没做，后面全是方块。")
    A("")
    # 十三
    A(f"## {SEC[12]}")
    A("")
    A(IMG8)
    A("")
    A("把前面所有概念串起来——一个可编译的待办事项应用（输入 + 添加 + 勾选完成 + 删除 + 计数）：")
    A("")
    A("```rust")
    A(r'''use iced::widget::{button, checkbox, column, row, scrollable, text, text_input, Space};
use iced::{Center, Element, Fill};

#[derive(Default)]
struct Todos {
    input: String,      // 输入框当前内容
    items: Vec<Item>,   // 待办列表
    next_id: u64,
}

struct Item {
    id: u64,
    text: String,
    done: bool,
}

#[derive(Debug, Clone)]
enum Message {
    InputChanged(String),   // 输入框变化
    Add,                    // 添加一条
    Toggle(u64),            // 勾选/取消某条
    Delete(u64),            // 删除某条
    ClearDone,              // 清除已完成
}

fn update(state: &mut Todos, message: Message) {
    match message {
        Message::InputChanged(v) => state.input = v,
        Message::Add => {
            let text = state.input.trim().to_string();
            if !text.is_empty() {
                state.items.push(Item { id: state.next_id, text, done: false });
                state.next_id += 1;
                state.input.clear();
            }
        }
        Message::Toggle(id) => {
            if let Some(it) = state.items.iter_mut().find(|it| it.id == id) {
                it.done = !it.done;
            }
        }
        Message::Delete(id) => state.items.retain(|it| it.id != id),
        Message::ClearDone => state.items.retain(|it| !it.done),
    }
}

fn view(state: &Todos) -> Element<'_, Message> {
    // 顶部：输入框 + 添加按钮
    let input_row = row![
        text_input("要做点什么？", &state.input)
            .on_input(Message::InputChanged)
            .on_submit(Message::Add),
        button("添加").on_press(Message::Add),
    ]
    .spacing(10);

    // 列表：用函数版 column(...) 遍历动态渲染每一项
    let list = column(
        state.items.iter().map(|item| {
            row![
                checkbox("", item.done).on_toggle(move |_| Message::Toggle(item.id)),
                text(&item.text).width(Fill),
                button("删").on_press(Message::Delete(item.id)).style(button::danger),
            ]
            .spacing(10)
            .align_y(Center)
            .into()
        }),
    )
    .spacing(8);

    let done = state.items.iter().filter(|it| it.done).count();
    let footer = row![
        text(format!("共 {} 项 · 已完成 {}", state.items.len(), done)),
        Space::with_width(Fill),
        button("清除已完成").on_press(Message::ClearDone),
    ]
    .align_y(Center);

    column![input_row, scrollable(list).height(Fill), footer]
        .spacing(16)
        .padding(20)
        .max_width(520)
        .into()
}

fn main() -> iced::Result {
    // 生产里记得 .font()/.default_font() 装中文字体（第 12 节）
    iced::application("Todos — iced", update, view)
        .theme(|_| iced::Theme::TokyoNight)
        .run()
}''')
    A("```")
    A("")
    A("这 ~70 行覆盖了：**状态建模、携带数据的 Message、动态列表渲染（函数版 `column`）、闭包捕获 `id`、`Fill` 撑开、`scrollable` 滚动、主题**——就是图 8 那个界面。想加异步（比如存到后端），把 `update` 改成返回 `Task`、`Message::Add` 分支里发 `Task::perform` 即可（第 8 节）。")
    A("")
    # 十四
    A(f"## {SEC[13]}")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 中文显示成方块 | `text(\"中文\")` 全是 □ | `.font(include_bytes!)` + `.default_font()`（第 12 节） |")
    A("| 按钮点不动 | 按钮灰着没反应 | 没给 `.on_press(Msg)` = 禁用态；补上回调 |")
    A("| 在 `view` 里改状态 | 借用冲突/编译不过 | `view` 只读；改状态只能在 `update` |")
    A("| 想在 `update` 里 `.await` | 编译报错 | 用 `Task::perform(future, Msg)`，别直接 await |")
    A("| Task 不执行 | `perform` 了没反应 | 没开 executor feature（如 `tokio`） |")
    A("| 动态列表用错宏 | `column!` 塞 Vec 报错 | 变长列表用函数版 `column(iter)` / `row(iter)` |")
    A("| 换主题颜色不变/暗色刺眼 | 硬编码了颜色 | 从 `theme.extended_palette()` 派生（第 7 节） |")
    A("| 定时/流事件不来 | 只发了一次就没了 | 持续事件用 `Subscription`，不是 `Task` |")
    A("| 照抄教程编译不过 | 方法名/签名对不上 | 0.x API 跨版本会变，认准锁定版本的 docs.rs |")
    A("| 改一行 UI 等半天 | 编译慢 | iced 无官方热重载；用 `cargo check` 迭代、拆 crate、开 `debug` 面板 |")
    A("")
    # 十五
    A(f"## {SEC[14]}")
    A("")
    A("对照本工作区（元数据驱动企业平台，前端已有成体系 Web 资产）：")
    A("")
    A("1. **iced 在本仓暂无强对口场景**：横评（`docs/20260920_Rust桌面GUI框架横评.md`）的结论是——`cmx-agent`（桌面智能体）若长 GUI，首选 **Tauri 2**（复用 `frontend/` 的 UI5/Tabler 与双主题资产）；引擎类本地诊断面板选 **egui**（`cargo run` 即用）。iced 的强项在「长寿命、重交互、要架构可演进的纯 Rust 桌面产品」，与 CMX 当前以 Web 为主的形态不重叠。")
    A("2. **但 iced 的一条工程纪律与 CMX 完全同频**：**禁硬编码色值、颜色从主题 palette 派生**（第 7 节）——这正是 CMX 硬约束 #4「页面/组件双主题通路兼容（UI5 + Neo）」在自绘 GUI 里的等价表达。无论 Web 还是 iced，「主题即真源、部件不写死色」是同一条规矩。")
    A("3. **Elm 单向数据流的心智可迁移**：`State → view → Message → update` 的可追溯性，与 CMX 后端「状态外置、变更可审计」的取向一致；即便不落地 iced，这套心智对写前端状态管理也有参考价值。")
    A("4. **若未来确有纯 Rust 桌面小工具需求**（不依赖现有 Web 资产、要单二进制分发），iced 是稳妥选项——但要把「编译慢、0.x API 易变、中文字体要自带」计入成本。")
    A("")
    # 十六
    A(f"## {SEC[15]}")
    A("")
    A("**版本基线（2026-09）**：iced **0.13.x**，0.14 开发中。iced 官方自称 **experimental**，**0.x 版本之间 API 会有破坏性变更**——升级前务必读 CHANGELOG。")
    A("")
    A("| 资源 | 地址 | 说明 |")
    A("|---|---|---|")
    A("| 官网 | iced.rs | 总入口 |")
    A("| 官方指南 | book.iced.rs | The Iced Book（架构与教程） |")
    A("| API 文档 | docs.rs/iced | **锁定你的版本看**，一切以此为准 |")
    A("| 源码 & 示例 | github.com/iced-rs/iced（`examples/` 目录） | **最好的学习资料**：todos / clock / websocket / game_of_life / pane_grid 等几十个可跑范例 |")
    A("| 生态 | github.com/iced-rs/awesome-iced | 第三方部件/工具集 |")
    A("| 生产案例 | System76 COSMIC 桌面 | 用 iced 做的整套 Linux 桌面环境 |")
    A("")
    A("> 学习路径建议：**先跑通官方 `examples/` 里的 `todos` 和 `clock`**（正好覆盖本文的四件套 + Task + Subscription），再回头对照本文各节展开。遇到 API 对不上，第一反应是「看我锁定版本的 docs.rs」，而不是怀疑教程——0.x 的锅多半在版本漂移。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **iced = 用 Rust 写 Elm**：`State + Message + update + view` 四件套，界面是状态的纯函数，单向数据流、状态可追溯；副作用交给 `Task`、外部事件流交给 `Subscription`、组件靠 `Element::map` 层层组合。它给的是「把桌面应用写成一门可长期演进的架构」——代价是编译慢、API 尚在演进、中文要自带字体。想清楚要的是这份「正」，它就是纯 Rust 桌面的稳妥答案。")
    A("")
    A("> 参考：iced.rs、book.iced.rs、docs.rs/iced、github.com/iced-rs/iced（examples）、System76 COSMIC。版本以 2026-09 的 0.13.x 线为准；凡涉及具体方法签名，请以你锁定版本的 docs.rs 为准，勿跨版本照抄。")

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
