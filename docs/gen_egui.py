#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust egui 桌面框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_egui.py   (egui / eframe 0.36.x，立即模式，edition 2024)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust-egui桌面框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
TEA = ("#0d9488", "#f0fdfa")   # egui teal（主色，与横评一致）
IMM = ("#c2410c", "#fff7ed")   # immediate 橙
RET = ("#4338ca", "#eef2ff")   # retained 靛（iced 对照）
CTX = ("#0284c7", "#f0f9ff")   # Context 天蓝
UI = ("#7c3aed", "#f5f3ff")    # Ui 紫
RSP = ("#b45309", "#fffbeb")   # Response 琥珀
GRN = ("#15803d", "#f0fdf4")   # green
DAN = ("#dc2626", "#fef2f2")   # danger red
GRY = ("#475569", "#f1f5f9")   # slate

# egui 默认暗色主题 mockup 用色
DBG = "#1e1e1e"
DWIDGET = "#3a3a3a"
DTEXT = "#dcdcdc"
DWEAK = "#8a8a8a"
DACCENT = "#529cca"


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


def win(x, y, w, h, title, body_fill="#ffffff", bar=TEA[0]):
    """桌面窗口 mockup：标题栏 + 三个红绿灯点 + 内容区。"""
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


def pill(x, y, w, s, fill=TEA[0], tcol="#fff", h=26):
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2:.0f}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{y+h/2+3.5:.0f}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="11" font-weight="700" fill="{tcol}">{esc(s)}</text></g>')


def chip(x, y, w, s, fill, tcol, h=26, r=6):
    """方角一点的按钮（egui 观感偏方）。"""
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'
            f'<text x="{x+w/2}" y="{y+h/2+3.5:.0f}" text-anchor="middle" font-family="{SANS}" '
            f'font-size="11" font-weight="600" fill="{tcol}">{esc(s)}</text></g>')


def field(x, y, w, s, h=28, placeholder=True, bg="#fff", border="#cbd5e1", fg=None):
    col = fg if fg else ("#94a3b8" if placeholder else "#1e293b")
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{bg}" '
            f'stroke="{border}" stroke-width="1.3"/>'
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


# ---------------------------------------------------------------- FIG 1 立即 vs 保留
def fig_modes():
    W, H = 940, 480
    b = []
    # 左：保留模式
    b.append(f'<rect x="40" y="45" width="410" height="405" rx="12" fill="{RET[1]}" stroke="{RET[0]}" stroke-width="1.8"/>')
    b.append(t(245, 68, "保留模式 Retained（iced · DOM）", 13, RET[0], "middle", "700", MONO))
    b.append(box(70, 84, 350, 46, "① 构建部件树（一次）", ["UI 建成对象树，常驻内存"], RET))
    b.append(arrow(245, 130, 245, 152))
    b.append(box(70, 152, 350, 46, "② 事件 → Message", ["交互转成消息"], RET))
    b.append(arrow(245, 198, 245, 220))
    b.append(box(70, 220, 350, 46, "③ update 改状态", ["集中改状态"], RET))
    b.append(arrow(245, 266, 245, 288))
    b.append(box(70, 288, 350, 46, "④ diff + 局部更新树", ["只补变化的节点，再绘制"], RET))
    b.append(arrow(70, 311, 55, 311, "", RET[0]))
    b.append(arrow(55, 311, 55, 107, "", RET[0]))
    b.append(arrow(55, 107, 70, 107, "循环", RET[0]))
    b.append(t(245, 360, "部件是对象、跨帧存活；有树、有 diff、有回调", 10.5, RET[0], "middle"))
    b.append(t(245, 380, "改一处 → 只更新那一处", 10.5, "#64748b", "middle"))
    # 右：立即模式
    b.append(f'<rect x="490" y="45" width="410" height="405" rx="12" fill="{IMM[1]}" stroke="{IMM[0]}" stroke-width="1.8"/>')
    b.append(t(695, 68, "立即模式 Immediate（egui）", 13, IMM[0], "middle", "700", MONO))
    b.append(box(510, 84, 370, 46, "每一帧：从头把 UI 代码跑一遍", ["update(ctx) 被反复调用"], IMM))
    b.append(arrow(695, 130, 695, 152))
    b.append(box(510, 152, 370, 62, "逐行调用部件函数", [
        'ui.button("+") → 立即画出 + 返回 Response',
        "if resp.clicked() { self.value += 1 }"], IMM))
    b.append(arrow(695, 214, 695, 236))
    b.append(box(510, 236, 370, 46, "输出：这一帧的图形（三角网格）", ["交给 GPU；不保留任何部件对象"], IMM))
    b.append(arrow(695, 282, 695, 304))
    b.append(box(510, 304, 370, 40, "下一帧：全部从零再来", [], IMM))
    b.append(arrow(880, 324, 895, 324, "", IMM[0]))
    b.append(arrow(895, 324, 895, 107, "", IMM[0]))
    b.append(arrow(895, 107, 880, 107, "循环", IMM[0]))
    b.append(t(695, 375, "没有树、没有 diff、没有回调；状态就是你手里的变量", 10.5, IMM[0], "middle"))
    b.append(caption(W, 468, "同一个界面，两种世界观：保留模式建一棵树反复增量更新；立即模式每帧把 UI 当函数重跑一遍，界面 = 本帧代码的输出"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 每帧循环
def fig_frame():
    W, H = 940, 430
    b = []
    b.append(box(360, 46, 220, 52, "eframe 事件循环", ["每帧调 App::update(ctx)"], TEA))
    b.append(arrow(470, 98, 470, 124))
    b.append(box(340, 124, 260, 52, "CentralPanel::show(|ui|…)", ["开一块绘制区域 Ui"], CTX))
    b.append(arrow(470, 176, 470, 202))
    b.append(box(320, 202, 300, 86, "你的 UI 代码逐行跑", [
        "读 &mut self.state 直接用",
        "ui.button() 画出 + 返回 Response",
        "if clicked { 改 self.state }"], IMM))
    b.append(arrow(470, 288, 470, 314))
    b.append(box(360, 314, 220, 46, "输出本帧图形 → GPU", [], GRY))
    # 左：App 状态
    b.append(box(50, 200, 210, 92, "你的 App 结构体", [
        "self.value / self.items…", "所有状态就住这儿", "（无 Message、无外部 store）"], TEA))
    b.append(arrow(260, 232, 320, 232, "读", TEA[0]))
    b.append(arrow(320, 258, 260, 258, "写", TEA[0]))
    # 右：重绘时机
    b.append(box(660, 200, 230, 92, "重绘时机（按需）", [
        "有交互/动画 → 画下一帧", "空闲 → 不重绘（0 CPU）", "request_repaint() 主动唤醒"], GRN))
    b.append(arrow(620, 245, 660, 245, "", GRN[0]))
    # 循环回边
    b.append(arrow(360, 337, 300, 337, "", TEA[0]))
    b.append(arrow(300, 337, 300, 72, "", TEA[0]))
    b.append(arrow(300, 72, 360, 72, "下一帧", TEA[0]))
    b.append(caption(W, 400, "「每帧重跑」不等于「每帧重绘」：egui 空闲时根本不画，0 CPU；一旦有输入/动画/request_repaint 才渲染下一帧"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 三大对象
def fig_objects():
    W, H = 940, 360
    b = []
    b.append(box(50, 90, 260, 190, "egui::Context（全局中枢）", [
        "整个 app 只有一个：", "· 输入 input · 记忆 memory", "· 字体 fonts · 风格 style",
        "· request_repaint()", "· 开面板 / 开窗口", "跨线程可 clone（内部 Arc）"], CTX))
    b.append(arrow(310, 150, 360, 150, "show", CTX[0]))
    b.append(box(360, 90, 260, 190, "egui::Ui（一块区域）", [
        "往里 add 部件的容器：", "· 自带游标，自动排布", "· horizontal / vertical / grid",
        "· 作为闭包参数传进来", "  |ui| { ui.button(..) }", "· 可再切子区域（嵌套）"], UI))
    b.append(arrow(620, 150, 670, 150, "调用", UI[0]))
    b.append(box(670, 90, 220, 190, "Response（本帧结果）", [
        "每次部件调用的返回值：", "· clicked() / hovered()", "· changed() / dragged()",
        "· lost_focus() / rect", "描述「这一帧发生了", "  什么」，下一帧作废"], RSP))
    b.append(caption(W, 320, "三对象各司其职：Context 是全局中枢，Ui 是你往里塞部件的区域，Response 是部件本帧的即时反馈——记住 Response 只对当前这一帧有效"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 面板布局
def fig_panels():
    W, H = 940, 430
    b = []
    b.append(win(40, 46, 600, 348, "egui 应用窗口"))
    # top panel（菜单栏）
    b.append(f'<rect x="56" y="88" width="568" height="30" rx="4" fill="{GRY[1]}" stroke="{GRY[0]}" stroke-width="1.1"/>')
    b.append(t(66, 108, "TopBottomPanel::top  →  菜单栏：文件  编辑  视图", 10.5, GRY[0], "start", "700", MONO))
    # left side panel
    b.append(f'<rect x="56" y="124" width="150" height="222" rx="4" fill="{CTX[1]}" stroke="{CTX[0]}" stroke-width="1.1"/>')
    b.append(t(131, 228, "SidePanel", 11, CTX[0], "middle", "700", MONO))
    b.append(t(131, 246, "::left", 10, CTX[0], "middle", "400", MONO))
    b.append(t(131, 264, "导航 / 工具", 9.5, "#64748b", "middle"))
    # central
    b.append(f'<rect x="212" y="124" width="412" height="222" rx="4" fill="{TEA[1]}" stroke="{TEA[0]}" stroke-width="1.4"/>')
    b.append(t(418, 150, "CentralPanel", 12, TEA[0], "middle", "700", MONO))
    b.append(t(418, 168, "最后放，吃掉剩余空间", 10, "#64748b", "middle"))
    # 浮动窗口
    b.append(f'<rect x="360" y="196" width="200" height="120" rx="7" fill="#fff" stroke="{UI[0]}" stroke-width="1.6"/>')
    b.append(f'<rect x="360" y="196" width="200" height="22" rx="7" fill="{UI[0]}"/>')
    b.append(f'<rect x="360" y="210" width="200" height="8" fill="{UI[0]}"/>')
    b.append(t(460, 211, "Window『设置』", 10, "#fff", "middle", "700", MONO))
    b.append(t(460, 248, "可拖动 / 可缩放的浮窗", 9.5, "#64748b", "middle"))
    b.append(t(460, 268, "Area 也浮在最上层", 9.5, "#64748b", "middle"))
    # bottom panel
    b.append(f'<rect x="56" y="352" width="568" height="30" rx="4" fill="{GRY[1]}" stroke="{GRY[0]}" stroke-width="1.1"/>')
    b.append(t(66, 371, "TopBottomPanel::bottom  →  状态栏", 10.5, GRY[0], "start", "700", MONO))
    # 右侧图例
    b.append(box(670, 70, 230, 190, "放置顺序＝抢占顺序", [
        "面板按调用顺序抢空间：", "① top / bottom / side 各占边", "② CentralPanel 最后吃剩余",
        "③ Window / Area 浮在最上", "", "⚠ CentralPanel 必须最后放", "  否则它会先占满整窗"], IMM))
    b.append(caption(W, 414, "egui 布局的第一课：面板按「调用顺序」依次从窗口边缘抢空间，CentralPanel 永远最后放、吃掉剩下的中间区；浮窗与 Area 叠在最上层"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 Widget 画廊
def fig_widgets():
    W, H = 940, 500
    b = []
    b.append(win(30, 40, 880, 430, "egui 常用部件画廊"))
    cells = [
        ("button", 'btn', 'if ui.button("保存").clicked()', "按钮→Response"),
        ("label / heading", 'lbl', 'ui.heading(..) / ui.label(..)', "文本"),
        ("text_edit", 'edit', 'ui.text_edit_singleline(&mut s)', "输入框"),
        ("checkbox", 'chk', 'ui.checkbox(&mut b, "记住我")', "复选框"),
        ("radio_value", 'radio', 'ui.radio_value(&mut c, A, "甲")', "单选"),
        ("Slider", 'slider', 'ui.add(Slider::new(&mut v,0..=100))', "滑块"),
        ("DragValue", 'drag', 'ui.add(DragValue::new(&mut v))', "拖动改数"),
        ("ComboBox", 'combo', 'ComboBox::from_label(..)', "下拉"),
        ("ProgressBar", 'prog', 'ui.add(ProgressBar::new(0.6))', "进度"),
        ("selectable_value", 'sel', 'ui.selectable_value(..)', "分段选择"),
        ("collapsing", 'coll', 'ui.collapsing("更多",|ui|{..})', "折叠面板"),
        ("separator / spinner", 'misc', 'ui.separator() · ui.spinner()', "分隔/加载"),
    ]
    x0, y0, cw, ch = 55, 85, 215, 128
    for i, (name, kind, code, desc) in enumerate(cells):
        cx = x0 + (i % 4) * cw
        cy = y0 + (i // 4) * ch
        b.append(f'<rect x="{cx}" y="{cy}" width="{cw-15}" height="{ch-16}" rx="8" fill="#fff" stroke="#e2e8f0" stroke-width="1.2"/>')
        b.append(t(cx + 12, cy + 20, name, 11.5, TEA[0], "start", "700", MONO))
        mx, my = cx + 12, cy + 34
        if kind == 'btn':
            b.append(chip(mx, my, 82, "保存", TEA[0], "#fff", 26))
        elif kind == 'lbl':
            b.append(t(mx, my + 15, "标题 Heading", 14, "#0f172a", "start", "700"))
            b.append(t(mx, my + 32, "正文 label", 11, "#475569"))
        elif kind == 'edit':
            b.append(field(mx, my, 170, "输入…", 26))
        elif kind == 'chk':
            b.append(f'<rect x="{mx}" y="{my+2}" width="18" height="18" rx="4" fill="{TEA[0]}"/>')
            b.append(f'<path d="M {mx+4} {my+11} l 4 4 l 7 -8" stroke="#fff" stroke-width="2" fill="none"/>')
            b.append(t(mx + 26, my + 15, "记住我", 12, "#1e293b"))
        elif kind == 'radio':
            b.append(f'<circle cx="{mx+9}" cy="{my+11}" r="8" fill="#fff" stroke="{TEA[0]}" stroke-width="2"/>')
            b.append(f'<circle cx="{mx+9}" cy="{my+11}" r="4" fill="{TEA[0]}"/>')
            b.append(t(mx + 24, my + 15, "甲", 12, "#1e293b"))
            b.append(f'<circle cx="{mx+70}" cy="{my+11}" r="8" fill="#fff" stroke="#94a3b8" stroke-width="2"/>')
            b.append(t(mx + 85, my + 15, "乙", 12, "#64748b"))
        elif kind == 'slider':
            b.append(f'<rect x="{mx}" y="{my+9}" width="150" height="5" rx="2.5" fill="#e2e8f0"/>')
            b.append(f'<rect x="{mx}" y="{my+9}" width="95" height="5" rx="2.5" fill="{TEA[0]}"/>')
            b.append(f'<circle cx="{mx+95}" cy="{my+11}" r="9" fill="{TEA[0]}"/>')
            b.append(t(mx + 158, my + 15, "62", 10, "#64748b"))
        elif kind == 'drag':
            b.append(f'<rect x="{mx}" y="{my}" width="90" height="26" rx="6" fill="{TEA[1]}" stroke="{TEA[0]}" stroke-width="1.3"/>')
            b.append(t(mx + 45, my + 17, "◄ 42 ►", 11, TEA[0], "middle", "700", MONO))
        elif kind == 'combo':
            b.append(f'<rect x="{mx}" y="{my}" width="150" height="28" rx="6" fill="#fff" stroke="#cbd5e1" stroke-width="1.3"/>')
            b.append(t(mx + 10, my + 18, "选项 A", 11, "#1e293b"))
            b.append(f'<path d="M {mx+132} {my+11} l 8 0 l -4 6 z" fill="#64748b"/>')
        elif kind == 'prog':
            b.append(f'<rect x="{mx}" y="{my+6}" width="170" height="12" rx="6" fill="#e2e8f0"/>')
            b.append(f'<rect x="{mx}" y="{my+6}" width="102" height="12" rx="6" fill="{GRN[0]}"/>')
            b.append(t(mx + 176, my + 16, "60%", 10, "#64748b"))
        elif kind == 'sel':
            for k, (lab, on) in enumerate([("日", False), ("周", True), ("月", False)]):
                fx = mx + k * 52
                fill = TEA[0] if on else "#f1f5f9"
                tc = "#fff" if on else "#475569"
                b.append(f'<rect x="{fx}" y="{my}" width="48" height="26" rx="6" fill="{fill}" stroke="#cbd5e1" stroke-width="1"/>')
                b.append(t(fx + 24, my + 17, lab, 11, tc, "middle", "600"))
        elif kind == 'coll':
            b.append(f'<path d="M {mx} {my+6} l 8 5 l -8 5 z" fill="{TEA[0]}"/>')
            b.append(t(mx + 14, my + 15, "更多设置", 12, "#1e293b", "start", "700"))
            b.append(f'<line x1="{mx}" y1="{my+28}" x2="{mx+150}" y2="{my+28}" stroke="#e2e8f0" stroke-width="1"/>')
        elif kind == 'misc':
            b.append(f'<line x1="{mx}" y1="{my+8}" x2="{mx+150}" y2="{my+8}" stroke="#cbd5e1" stroke-width="2"/>')
            b.append(f'<circle cx="{mx+16}" cy="{my+30}" r="9" fill="none" stroke="{TEA[0]}" stroke-width="2.5" stroke-dasharray="30 12"/>')
            b.append(t(mx + 34, my + 34, "spinner", 10.5, "#64748b"))
        b.append(t(cx + 12, cy + ch - 26, code, 8.4, "#475569", "start", "400", MONO))
        b.append(t(cx + 12, cy + ch - 13, "→ " + desc, 9.5, "#94a3b8", "start"))
    b.append(caption(W, 490, "egui 部件都是 ui 的方法或 ui.add(Widget::new(..))；调用即绘制，返回 Response 让你当场判断点击/改动——没有「先声明再绑定」这回事"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 按需重绘+线程
def fig_repaint():
    W, H = 940, 420
    b = []
    b.append(box(60, 56, 380, 92, "egui 默认按需重绘", [
        "空闲 → 不画下一帧（0 CPU 占用）",
        "有输入 / 动画 / request_repaint → 才重绘",
        "所以立即模式并不 = 一直烧 CPU"], GRN))
    b.append(box(500, 56, 380, 92, "常见误解澄清", [
        "「每帧重跑 UI 代码」≠「每帧一定重绘」",
        "不动就休眠；要持续动画才 60fps",
        "重活别放 update：会卡住这一帧"], IMM))
    # 后台线程
    b.append(box(60, 210, 250, 130, "UI 线程（egui）", [
        "每帧非阻塞收结果：",
        "if let Ok(m) = self.rx",
        "        .try_recv() {",
        "    self.data = m;", "}", "把 data 画出来"], CTX))
    b.append(box(630, 210, 250, 130, "后台线程", [
        "let ctx = ctx.clone();",
        "thread::spawn(move || {",
        "  let r = 重活();",
        "  tx.send(r).ok();",
        "  ctx.request_repaint(); // 唤醒", "});"], RSP))
    b.append(arrow(630, 250, 310, 250, "① clone(Context) 交给线程", CTX[0]))
    b.append(arrow(630, 300, 310, 300, "② tx.send → rx；request_repaint 唤醒重绘", RSP[0]))
    b.append(caption(W, 398, "后台线程做重活，做完 tx.send 结果并 ctx.request_repaint() 唤醒 UI；UI 每帧用 try_recv 非阻塞取——Context 是 Arc，clone 极便宜"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 7 明暗主题
def fig_theme():
    W, H = 940, 430
    b = []
    # 暗色窗（egui 默认）
    b.append(win(50, 50, 210, 210, "Dark（egui 默认）", DBG, "#333333"))
    b.append(t(70, 96, "标题 Heading", 14, DTEXT, "start", "700"))
    b.append(chip(70, 110, 80, "保存", DACCENT, "#0b1a24", 26))
    b.append(field(160, 110, 78, "输入…", 26, bg=DWIDGET, border="#555", fg=DWEAK))
    b.append(f'<rect x="70" y="150" width="16" height="16" rx="4" fill="{DACCENT}"/>')
    b.append(f'<path d="M 73 158 l 3 3 l 6 -7" stroke="#0b1a24" stroke-width="2" fill="none"/>')
    b.append(t(94, 163, "记住我", 11, DTEXT))
    b.append(f'<rect x="70" y="182" width="168" height="6" rx="3" fill="#4a4a4a"/>')
    b.append(f'<rect x="70" y="182" width="100" height="6" rx="3" fill="{DACCENT}"/>')
    b.append(f'<circle cx="170" cy="185" r="7" fill="{DACCENT}"/>')
    b.append(t(70, 218, "正文 label", 11, DWEAK))
    # 亮色窗
    b.append(win(300, 50, 210, 210, "Light", "#f0f0f0", "#d0d0d0"))
    b.append(t(320, 96, "标题 Heading", 14, "#1e1e1e", "start", "700"))
    b.append(chip(320, 110, 80, "保存", "#3b82f6", "#fff", 26))
    b.append(field(410, 110, 78, "输入…", 26, bg="#fff", border="#c0c0c0"))
    b.append(f'<rect x="320" y="150" width="16" height="16" rx="4" fill="#3b82f6"/>')
    b.append(f'<path d="M 323 158 l 3 3 l 6 -7" stroke="#fff" stroke-width="2" fill="none"/>')
    b.append(t(344, 163, "记住我", 11, "#1e1e1e"))
    b.append(f'<rect x="320" y="182" width="168" height="6" rx="3" fill="#c8c8c8"/>')
    b.append(f'<rect x="320" y="182" width="100" height="6" rx="3" fill="#3b82f6"/>')
    b.append(f'<circle cx="420" cy="185" r="7" fill="#3b82f6"/>')
    b.append(t(320, 218, "正文 label", 11, "#666"))
    b.append(arrow(260, 155, 300, 155, "切换", TEA[0]))
    b.append(t(280, 285, "同一份 UI 代码", 10.5, "#64748b", "middle"))
    # 右：Visuals / Style
    b.append(box(560, 50, 340, 118, "Visuals / Style（主题真源）", [
        "ctx.set_visuals(Visuals::dark());   // 默认",
        "ctx.set_visuals(Visuals::light());",
        "或 ctx.set_theme(Theme::Dark)（新版）"], TEA))
    b.append(t(560, 195, "从 Visuals 取色（示意）:", 11, "#334155", "start", "700"))
    sw = [("window_fill", DBG), ("selection", DACCENT), ("hyperlink", "#90caf9"),
          ("warn", "#ffcc00"), ("error", "#ff5555")]
    xx = 560
    for name, cc in sw:
        b.append(f'<rect x="{xx}" y="205" width="62" height="34" rx="6" fill="{cc}" stroke="#cbd5e1" stroke-width="1"/>')
        b.append(t(xx + 31, 258, name, 8, "#64748b", "middle", "400", MONO))
        xx += 68
    b.append(box(180, 300, 580, 74, "禁硬编码色值（对齐 CMX 硬约束）", [
        "✔ 从 ui.visuals() 取：visuals.selection.bg_fill · visuals.text_color()",
        "✘ 别写死 Color32::from_rgb(82,156,202) —— 换明暗主题就掉队、对比崩坏"], DAN))
    b.append(caption(W, 402, "egui 默认就是暗色；一句 set_visuals 切换明暗，UI 代码不动——因为部件颜色都从 Visuals 取，而非写死（这正是 CMX 双主题通路的同款要求）"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 8 Todo 界面
def fig_todo():
    W, H = 640, 450
    b = []
    b.append(win(80, 40, 480, 370, "Todos — egui", DBG, "#333333"))
    b.append(t(105, 84, "待办事项", 16, DTEXT, "start", "700"))
    # 输入行
    b.append(field(105, 100, 320, "要做点什么？（回车添加）", 32, bg=DWIDGET, border="#555", fg=DWEAK))
    b.append(chip(438, 102, 96, "添加", DACCENT, "#0b1a24", 28))
    b.append(f'<line x1="105" y1="150" x2="534" y2="150" stroke="#3a3a3a" stroke-width="1.4"/>')
    items = [("写 egui 使用说明", True), ("画 8 张 SVG 图", True), ("跑 gen_egui.py 校验", False)]
    yy = 166
    for txt_, done in items:
        if done:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="{DACCENT}"/>')
            b.append(f'<path d="M 116 {yy+10} l 4 4 l 8 -9" stroke="#0b1a24" stroke-width="2.2" fill="none"/>')
            b.append(f'<text x="142" y="{yy+15}" font-family="{SANS}" font-size="12.5" fill="{DWEAK}" '
                     f'text-decoration="line-through">{esc(txt_)}</text>')
        else:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="5" fill="{DWIDGET}" stroke="#666" stroke-width="1.6"/>')
            b.append(t(142, yy + 15, txt_, 12.5, DTEXT))
        b.append(chip(500, yy - 2, 30, "🗑", DWIDGET, DTEXT, 24))
        yy += 42
    b.append(f'<line x1="105" y1="306" x2="534" y2="306" stroke="#3a3a3a" stroke-width="1.4"/>')
    b.append(t(112, 330, "共 3 项 · 已完成 2 项", 12, DWEAK, "start", "700"))
    b.append(t(105, 396, "深色为 egui 默认观感；上面这一屏 = 第 13 节完整代码的产物", 9.5, "#94a3b8", "start"))
    b.append(caption(W, 434, "第 13 节完整代码的成品：输入行 + 滚动列表（勾选/删除）+ 计数，约 60 行"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_modes(), "图1：立即模式 vs 保留模式")
IMG2 = b64img(fig_frame(), "图2：egui 每帧循环")
IMG3 = b64img(fig_objects(), "图3：Context · Ui · Response 三对象")
IMG4 = b64img(fig_panels(), "图4：面板与窗口布局")
IMG5 = b64img(fig_widgets(), "图5：常用 Widget 画廊")
IMG6 = b64img(fig_repaint(), "图6：按需重绘与后台线程")
IMG7 = b64img(fig_theme(), "图7：明暗主题 Visuals")
IMG8 = b64img(fig_todo(), "图8：Todo 应用界面")

SEC = [
    "一、egui 是什么：一张图看懂立即模式",
    "二、安装与第一个程序",
    "三、立即模式心智：每帧重跑、Response、状态自持",
    "四、eframe 应用外壳：App 与 run_native",
    "五、三大对象：Context · Ui · Response",
    "六、面板与窗口：CentralPanel · SidePanel · Window",
    "七、Widget 速查：常用部件一览",
    "八、Ui 内布局：horizontal · grid · columns",
    "九、状态住哪：立即模式的状态管理",
    "十、按需重绘与后台线程：request_repaint",
    "十一、样式与主题：Visuals 与明暗",
    "十二、中文字体：FontDefinitions 必知的坑",
    "十三、完整实例：待办事项 Todo",
    "十四、常见坑速查",
    "十五、与 CMX 工作区的呼应",
    "十六、版本与参考资源",
]


def main():
    D = []
    A = D.append
    A("# Rust egui 桌面框架详细使用说明")
    A("")
    A("> **定位**：egui（读作 “e-gooey”）是纯 Rust 的**立即模式**（immediate mode）GUI——**每一帧把 UI 代码从头跑一遍，界面就是代码此刻的输出**；无回调、无数据绑定、无虚拟树 diff。`eframe` 提供开箱即用的窗口壳。渲染器无关（输出三角网格，wgpu/glow/自定义皆可），因此能嵌进任何游戏引擎；Web(WASM) 是一级公民；AccessKit 无障碍在桌面默认启用。")
    A("> **版本基线（2026-09）**：egui / eframe **0.36.x**（当前 0.36.2）；0.36 起要求 **Rust edition 2024**。egui 每年数个 0.x 版，迁移说明详尽。")
    A("> **一句话取舍**：给「最快出活的工具人」——十分钟撸一个能用的面板是它的主场；短板是默认观感偏「调试 UI」风、复杂自适应布局（flex/grid 级）偏弱、复杂文种排版有限。")
    A("> **图**：8 张内嵌 base64 SVG，无外部依赖。所有易变 API 处均标注「以 docs.rs 对应版本为准」。")
    A("")
    A("> 姊妹篇：`docs/20260920_Rust-iced桌面框架使用说明.md`（Elm 保留模式，正好与本文的立即模式对照）、`docs/20260920_Rust桌面GUI框架横评.md`（五框架横评）。")
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
    A("理解 egui 只需先分清**两种世界观**：")
    A("")
    A("- **保留模式（Retained）**——iced / 浏览器 DOM 是代表：先把界面建成一棵**部件对象树**常驻内存，交互变成消息、改状态后 **diff** 出变化再局部更新那棵树。部件是对象，跨帧存活。")
    A("- **立即模式（Immediate）**——egui 的路子：**没有树**。每一帧，你的 UI 代码从头到尾跑一遍，每调用一个部件函数就「立即画出来」并返回一个 `Response`；这一帧结束，部件对象就没了，下一帧全部从零再来。")
    A("")
    A("于是 egui 的「事件处理」不是回调、不是消息，而是**就地判断**：")
    A("")
    A("```rust")
    A(r'''if ui.button("+").clicked() {
    self.value += 1;          // 点击处理就写在按钮旁边，读改状态直接用变量
}''')
    A("```")
    A("")
    A("> 立即模式源自游戏——每帧都重画整个画面。它的最大好处是**心智负担极低**：没有回调地狱、没有状态与视图不同步、没有 diff 的黑盒。界面永远等于「本帧这段代码的输出」，所见即所写。代价是它更适合中小型、强交互的工具界面；超大型、强调架构分层的应用，保留模式（如 iced）更从容。")
    A("")
    # 二
    A(f"## {SEC[1]}")
    A("")
    A("`Cargo.toml`——通常用 `eframe`（它把 egui + 窗口 + 事件 + 渲染后端打包好）：")
    A("")
    A("```toml")
    A(r'''[dependencies]
eframe = "0.36"      # = egui 本体 + 窗口/事件/渲染，一站式（默认 glow 渲染器）
# 只想要 egui 本体（嵌进已有 wgpu / 游戏引擎时）：
# egui = "0.36"
# 常用 feature：eframe = { version = "0.36", features = ["wgpu", "persistence"] }''')
    A("```")
    A("")
    A("`src/main.rs`——一个能跑的最小计数器，**全文如下**：")
    A("")
    A("```rust")
    A(r'''use eframe::egui;   // eframe 里 re-export 了 egui

fn main() -> eframe::Result {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        "计数器",
        options,
        // app 创建闭包：返回 Ok(Box::new(app))
        Box::new(|_cc| Ok(Box::new(Counter::default()))),
    )
}

#[derive(Default)]
struct Counter {
    value: i64,   // 状态就是普通字段，住在你自己的结构体里
}

impl eframe::App for Counter {
    // 这个方法每帧被调用一次
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("计数器");
            ui.horizontal(|ui| {
                if ui.button("-").clicked() { self.value -= 1; }
                ui.label(self.value.to_string());
                if ui.button("+").clicked() { self.value += 1; }
            });
        });
    }
}''')
    A("```")
    A("")
    A("`cargo run` 即见窗口。对比 iced 的四件套（State/Message/update/view），egui 这里**只有一个 `update`**：状态是结构体字段，界面就在 `update` 里当场画、当场处理点击。**注意**：默认字体不含中文，`ui.label(\"中文\")` 会显示成豆腐块——中文字体见第 12 节。")
    A("")
    # 三
    A(f"## {SEC[2]}")
    A("")
    A(IMG2)
    A("")
    A("立即模式有三条心智要牢记：")
    A("")
    A("**① 每帧从头重跑**：`App::update` 每帧被调一次，里面的 UI 代码全量重新执行。所以别在 `update` 里做重活（读大文件、跑网络）——那会卡住这一帧（解决办法见第 10 节）。")
    A("")
    A("**② 部件调用即绘制、返回 `Response`**：没有「先创建按钮对象、再绑定回调」。你调用 `ui.button(..)`，它当场画出来并返回一个 `Response`，你**立刻**问它这一帧发生了什么：")
    A("")
    A("```rust")
    A(r'''let resp = ui.button("提交");
if resp.clicked()   { /* 本帧被点击 */ }
if resp.hovered()   { /* 鼠标悬停中 */ }

// 输入类部件用 .changed() 判断值有没有变
let resp = ui.add(egui::Slider::new(&mut self.volume, 0..=100));
if resp.changed() { /* 音量被拖动了 */ }''')
    A("```")
    A("")
    A("**③ 状态由你自持**：egui 不提供 store / 信号 / 消息。状态就是你 `App` 结构体里的字段，部件通过 `&mut` 直接读写它（`ui.checkbox(&mut self.on, ..)` 会直接改 `self.on`）。数据流因此短到极致——**没有中间层**。")
    A("")
    A("> 一句话对比：iced 把「状态怎么变」抽象成 Message + update 一个口子（可追溯）；egui 则把它摊平成「变量 + 就地 if」（最直接）。前者利于大型架构，后者利于快速出活。")
    A("")
    # 四
    A(f"## {SEC[3]}")
    A("")
    A("`eframe` 是 egui 的官方应用外壳，负责建窗口、连渲染后端、驱动每帧的 `update`。核心是 `App` trait 和 `run_native`：")
    A("")
    A("```rust")
    A(r'''use eframe::egui;

struct MyApp { /* 你的全部状态 */ }

impl MyApp {
    // 用 CreationContext 做启动初始化（装字体、恢复持久化状态、拿 GL 上下文…）
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        // setup_custom_fonts(&cc.egui_ctx);   // 见第 12 节
        // if let Some(storage) = cc.storage { /* 恢复上次状态，需 persistence feature */ }
        Self { /* … */ }
    }
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| { ui.label("hi"); });
    }

    // 可选：自动保存状态（需 persistence feature）
    // fn save(&mut self, storage: &mut dyn eframe::Storage) { /* … */ }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        // 窗口配置走 ViewportBuilder（旧的 initial_window_size 早已移除）
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([900.0, 600.0])
            .with_min_inner_size([400.0, 300.0]),
        ..Default::default()
    };
    eframe::run_native(
        "我的应用",
        options,
        Box::new(|cc| Ok(Box::new(MyApp::new(cc)))),
    )
}''')
    A("```")
    A("")
    A("| 要素 | 作用 |")
    A("|---|---|")
    A("| `eframe::App` trait | 只需实现 `update`；`save`/`on_exit`/`clear_color` 等都是可选 |")
    A("| `CreationContext` | 启动上下文：`egui_ctx`（装字体/风格）、`storage`（持久化）、`gl`/`wgpu_render_state`（自定义渲染） |")
    A("| `NativeOptions` | 窗口/后端配置；窗口属性走 `ViewportBuilder` |")
    A("| `run_native(name, opts, creator)` | 起原生窗口；`creator` 返回 `Ok(Box::new(app))`，`main` 返回 `eframe::Result` |")
    A("| `eframe::WebRunner` | 编到 WASM 跑网页版（egui 的 Web 是一级公民） |")
    A("")
    A("> 想把 egui 嵌进**已有的 wgpu / 游戏引擎**（不用 eframe 的窗口）：直接用 `egui` + `egui-winit` + `egui-wgpu`，自己驱动 `ctx.run(raw_input, |ctx| {…})` 拿到三角网格再交给你的渲染器。这正是 egui「渲染器无关」的价值。")
    A("")
    # 五
    A(f"## {SEC[4]}")
    A("")
    A(IMG3)
    A("")
    A("egui 的 API 几乎都围绕这三个对象：")
    A("")
    A("- **`egui::Context`**：整个 app 的中枢，全局唯一。管输入、记忆（`Memory`）、字体、风格；`ctx.request_repaint()` 请求重绘；面板/窗口都从它开：`CentralPanel::default().show(ctx, …)`。它内部是 `Arc`，**可跨线程 `clone`**（第 10 节用得上）。")
    A("- **`egui::Ui`**：一块可以往里塞部件的**区域**，带一个自动前进的游标。你几乎所有代码都写在某个 `|ui| { … }` 闭包里，对 `ui` 调方法加部件。`ui` 可以再切出子区域（`ui.horizontal`、`ui.group`…）。")
    A("- **`Response`**：每次部件调用的返回值，描述**这一帧**该部件发生了什么（`clicked`/`hovered`/`changed`/`dragged`/`rect`…）。它只对当前帧有效。")
    A("")
    A("```rust")
    A(r'''egui::CentralPanel::default().show(ctx, |ui| {   // ctx 开区域，给你一个 ui
    let resp = ui.button("点我");                    // 对 ui 加部件，拿 Response
    if resp.clicked() {
        ctx.request_repaint();                       // 通过 ctx 请求下一帧
    }
});''')
    A("```")
    A("")
    A("> 还有一个常被忽略的 `ui.input(|i| …)`：读当前帧的原始输入（按键、指针、滚轮）。例如判断回车：`ui.input(|i| i.key_pressed(egui::Key::Enter))`。")
    A("")
    # 六
    A(f"## {SEC[5]}")
    A("")
    A(IMG4)
    A("")
    A("egui 用**面板**切分窗口，用**窗口/浮层**做叠加。关键规则：**面板按调用顺序，从窗口边缘依次抢占空间，`CentralPanel` 必须最后放、吃掉剩余的中间区**。")
    A("")
    A("```rust")
    A(r'''fn update(&mut self, ctx: &egui::Context, _f: &mut eframe::Frame) {
    // ① 顶部菜单栏
    egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
        egui::menu::bar(ui, |ui| {
            ui.menu_button("文件", |ui| {
                if ui.button("打开").clicked() { /* … */ ui.close_menu(); }
            });
        });
    });

    // ② 左侧栏（可拖动改宽）
    egui::SidePanel::left("side").resizable(true).show(ctx, |ui| {
        ui.heading("导航");
    });

    // ③ 底部状态栏
    egui::TopBottomPanel::bottom("status").show(ctx, |ui| {
        ui.label("就绪");
    });

    // ④ 中央区：最后放，占掉剩余空间
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.label("主内容");
    });

    // ⑤ 浮动窗口（叠在最上层，可开关/拖动）
    egui::Window::new("设置").open(&mut self.show_settings).show(ctx, |ui| {
        ui.checkbox(&mut self.dark, "深色模式");
    });
}''')
    A("```")
    A("")
    A("| 容器 | 用途 |")
    A("|---|---|")
    A("| `TopBottomPanel::top/bottom` | 顶部菜单栏、底部状态栏 |")
    A("| `SidePanel::left/right` | 侧边栏（可 `.resizable(true)` 拖宽） |")
    A("| `CentralPanel` | 主内容区，**最后放**，吃掉剩余空间 |")
    A("| `Window` | 可拖动/缩放/开关的浮动窗口 |")
    A("| `Area` | 无边框自由浮层（做 HUD、tooltip 底座） |")
    A("| `egui::menu::bar` / `ui.menu_button` | 菜单栏 / 下拉菜单 |")
    A("")
    A("> ⚠ **顺序陷阱**：如果把 `CentralPanel` 写在 `SidePanel` 前面，中央区会先占满整窗，侧栏就被挤没了。记住：**边缘面板先声明，`CentralPanel` 永远最后**。")
    A("")
    # 七
    A(f"## {SEC[6]}")
    A("")
    A(IMG5)
    A("")
    A("部件要么是 `ui` 的便捷方法，要么用 `ui.add(SomeWidget::new(..))`。都是**调用即绘制、返回 `Response`**：")
    A("")
    A("```rust")
    A(r'''// 文本
ui.heading("大标题");
ui.label("普通文本");
ui.label(egui::RichText::new("红色加粗").color(egui::Color32::RED).strong());

// 按钮 / 复选 / 单选
if ui.button("保存").clicked() { /* … */ }
ui.checkbox(&mut self.remember, "记住我");
ui.radio_value(&mut self.choice, Choice::A, "选项 A");   // 点了就把 choice 设成 A

// 输入框
ui.text_edit_singleline(&mut self.name);
ui.text_edit_multiline(&mut self.notes);

// 数值：滑块 / 拖动 / 下拉
ui.add(egui::Slider::new(&mut self.volume, 0..=100).text("音量"));
ui.add(egui::DragValue::new(&mut self.count).speed(1.0));
egui::ComboBox::from_label("水果")
    .selected_text(format!("{:?}", self.fruit))
    .show_ui(ui, |ui| {
        ui.selectable_value(&mut self.fruit, Fruit::Apple, "苹果");
        ui.selectable_value(&mut self.fruit, Fruit::Pear,  "梨");
    });

// 进度 / 折叠 / 分隔 / 链接
ui.add(egui::ProgressBar::new(0.6).show_percentage());
ui.collapsing("更多设置", |ui| { ui.label("藏在里面"); });
ui.separator();
ui.hyperlink_to("egui 官网", "https://egui.rs");''')
    A("```")
    A("")
    A("| 部件 | 关键点 |")
    A("|---|---|")
    A("| `ui.label` / `ui.heading` / `RichText` | 文本；`RichText` 加颜色/粗体/删除线/字号 |")
    A("| `ui.button` / `ui.small_button` | 返回 `Response`，`.clicked()` 判断 |")
    A("| `ui.checkbox(&mut bool, ..)` | 直接改传入的 bool |")
    A("| `ui.radio_value` / `ui.selectable_value` | 点击即把目标变量设为该值 |")
    A("| `Slider` / `DragValue` | 数值输入；`ui.add(..)` 加，`.changed()` 判断 |")
    A("| `ComboBox` | 下拉；`.show_ui` 里放 `selectable_value` |")
    A("| `ProgressBar` / `Spinner` | 进度 / 转圈 |")
    A("| `ui.collapsing` / `CollapsingHeader` | 可折叠分组 |")
    A("| `ui.image` | 图片（配 `egui_extras` 的图片加载器） |")
    A("")
    A("> egui 用**表情/符号**当图标很常见（如 🗑 📁 ⚙），因为默认自带一套符号字体；要更专业的图标字体自行 `set_fonts` 注入。")
    A("")
    # 八
    A(f"## {SEC[7]}")
    A("")
    A("`Ui` 默认从上到下堆叠部件。要改排布，用布局方法（也都是闭包）：")
    A("")
    A("```rust")
    A(r'''// 横排 / 竖排
ui.horizontal(|ui| { ui.label("名字："); ui.text_edit_singleline(&mut self.name); });
ui.vertical(|ui| { ui.label("A"); ui.label("B"); });
ui.horizontal_wrapped(|ui| { /* 排满自动换行 */ });

// 等宽分栏
ui.columns(3, |cols| {
    cols[0].label("左");
    cols[1].label("中");
    cols[2].label("右");
});

// 网格（标签+控件成对，最适合表单）
egui::Grid::new("form").num_columns(2).striped(true).show(ui, |ui| {
    ui.label("用户名");  ui.text_edit_singleline(&mut self.user);  ui.end_row();
    ui.label("密码");    ui.text_edit_singleline(&mut self.pass);  ui.end_row();
});

// 自定义对齐：靠右放一个按钮
ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
    if ui.button("删除").clicked() { /* … */ }
});

// 滚动区 + 分组框
egui::ScrollArea::vertical().show(ui, |ui| {
    ui.group(|ui| { ui.label("带边框的一组"); });
});''')
    A("```")
    A("")
    A("| 方法 | 用途 |")
    A("|---|---|")
    A("| `ui.horizontal` / `ui.vertical` | 横排 / 竖排 |")
    A("| `ui.horizontal_wrapped` | 横排排满自动换行 |")
    A("| `ui.columns(n, |cols| …)` | n 个等宽列 |")
    A("| `egui::Grid` | 网格/表单（`.striped(true)` 斑马纹） |")
    A("| `ui.with_layout(Layout, …)` | 改变主轴方向与对齐（如靠右） |")
    A("| `egui::ScrollArea` | 滚动区域 |")
    A("| `ui.group` / `ui.scope` | 带边框分组 / 隔离样式 |")
    A("| `ui.add_space(px)` / `ui.separator()` | 空隙 / 分隔线 |")
    A("")
    A("> 间距/内边距等在 `ctx.style_mut(|s| s.spacing.item_spacing = egui::vec2(8.0, 6.0))` 里全局调；egui 的布局是「即时流式」的，没有 CSS flex/grid 那么强，复杂自适应界面要多用 `Grid` + `with_layout` 拼。")
    A("")
    # 九
    A(f"## {SEC[8]}")
    A("")
    A("立即模式下「状态住哪」是最该想清楚的：")
    A("")
    A("**① 首选：住在你的 `App` 结构体里**（99% 的情况）。它跨帧存活，部件用 `&mut` 直接读写。")
    A("")
    A("```rust")
    A(r'''struct MyApp {
    name: String,        // text_edit 直接改它
    volume: u8,          // slider 直接改它
    items: Vec<Item>,    // 列表
}''')
    A("```")
    A("")
    A("**② 少数「纯 UI 临时态」可交给 egui 记忆**（如某折叠块开没开、某弹窗显不显示）。egui 用 `Id` 给部件记忆，多数内置部件（`CollapsingHeader`、`Window::open`）自动管好；需要手动时用 `ui.memory_mut(|m| …)` 或 `ui.data_mut(|d| …)` 按 `Id` 存取。")
    A("")
    A("```rust")
    A(r'''// 手动存一个跨帧的临时布尔（按 Id）
let id = egui::Id::new("my_toggle");
let mut open = ui.data_mut(|d| d.get_temp::<bool>(id).unwrap_or(false));
ui.checkbox(&mut open, "展开");
ui.data_mut(|d| d.insert_temp(id, open));''')
    A("```")
    A("")
    A("**③ 别做的事**：不要每帧 `new` 一个大结构体当状态（会丢失）——立即模式只重跑 UI 代码，**不重建你的 App**；真正的持久数据一律放 `App` 字段（或外置存储）。")
    A("")
    A("> 对齐 CMX「集群无状态」的思路：egui 的 App 状态是**单机 UI 态**，业务持久数据仍应外置（DB/Redis），别把 `App` 字段当持久层。")
    A("")
    # 十
    A(f"## {SEC[9]}")
    A("")
    A(IMG6)
    A("")
    A("**先破一个误解**：立即模式「每帧重跑 UI 代码」≠「每帧都重绘」。egui **默认按需重绘**——空闲时根本不画下一帧，CPU 占用为 0；只有发生输入、动画，或你主动 `request_repaint()` 时才渲染。所以它并不费电。")
    A("")
    A("需要持续刷新（时钟、动画、进度）时主动请求：")
    A("")
    A("```rust")
    A(r'''ctx.request_repaint();                                   // 请求「尽快再来一帧」
ctx.request_repaint_after(std::time::Duration::from_secs(1)); // 最多 1 秒后再来一帧''')
    A("```")
    A("")
    A("**重活不能放在 `update` 里**（会卡住这一帧）——丢给后台线程，做完用 `request_repaint` 唤醒 UI：")
    A("")
    A("```rust")
    A(r'''use std::sync::mpsc;

struct MyApp { rx: mpsc::Receiver<String>, data: String }

// 点击时启动后台任务
if ui.button("加载").clicked() {
    let (tx, rx) = mpsc::channel();
    self.rx = rx;
    let ctx = ctx.clone();                 // Context 是 Arc，clone 极便宜
    std::thread::spawn(move || {
        let result = heavy_work();          // 耗时活儿：网络/IO/计算
        let _ = tx.send(result);
        ctx.request_repaint();              // 唤醒 UI 去取结果
    });
}

// 每帧非阻塞地取结果（千万别在 UI 线程 recv() 阻塞）
if let Ok(msg) = self.rx.try_recv() {
    self.data = msg;
}''')
    A("```")
    A("")
    A("> 要点：① `ctx.clone()` 把上下文交给线程（内部 `Arc`）；② 线程做完 `tx.send` + `ctx.request_repaint()`；③ UI 线程每帧 `try_recv()` 非阻塞取。异步运行时（tokio）同理——把 `JoinHandle`/channel 存进 `App`，完成时 `request_repaint`。")
    A("")
    # 十一
    A(f"## {SEC[10]}")
    A("")
    A(IMG7)
    A("")
    A("egui **默认就是暗色**。切换明暗只需一句，UI 代码一行不改：")
    A("")
    A("```rust")
    A(r'''ctx.set_visuals(egui::Visuals::dark());    // 暗（默认）
ctx.set_visuals(egui::Visuals::light());   // 亮
// 新版也可：ctx.set_theme(egui::Theme::Light);

// 细调某些颜色/圆角（从默认 Visuals 改，别整套写死）
let mut visuals = egui::Visuals::dark();
visuals.selection.bg_fill = egui::Color32::from_rgb(0x2d, 0x5c, 0x88);
ctx.set_visuals(visuals);

// 全局风格（间距、圆角、字号映射…）
ctx.style_mut(|style| {
    style.spacing.item_spacing = egui::vec2(8.0, 6.0);
});''')
    A("```")
    A("")
    A("给部件临时改色用 `RichText` / 部件自带方法，取色则**从当前 `Visuals` 派生**，而不是写死：")
    A("")
    A("```rust")
    A(r'''let visuals = ui.visuals();                       // 当前主题的调色板
let accent = visuals.selection.bg_fill;          // 主题里的强调色
let text   = visuals.text_color();               // 主题里的正文色
ui.label(egui::RichText::new("强调").color(accent));
// ✘ 反例：ui.label(RichText::new("x").color(Color32::from_rgb(82,156,202)))  // 写死→换主题就掉队''')
    A("```")
    A("")
    A("> **对齐 CMX 硬约束 #4（双主题通路、禁硬编码色值）**：egui 里同理——颜色一律从 `ui.visuals()` 取，`set_visuals` 一处切换全局明暗。写死 `Color32::from_rgb(...)` 的后果就是换主题后对比度崩坏、暗色刺眼。自绘 GUI 和 Web 在这条上是同一个道理。")
    A("")
    # 十二
    A(f"## {SEC[11]}")
    A("")
    A("**这是中文团队用 egui 的头号坑**：egui 默认字体不含 CJK，`ui.label(\"中文\")` 直接豆腐块。必须在启动时用 `FontDefinitions` 注入中文字体并挂到字体族最前。")
    A("")
    A("```rust")
    A(r'''use eframe::egui;

fn setup_custom_fonts(ctx: &egui::Context) {
    let mut fonts = egui::FontDefinitions::default();

    // ① 注册字体数据（放个 .otf/.ttf，如思源黑体/苹方子集）
    //    0.36 里 FontData 需用 Arc 包裹
    fonts.font_data.insert(
        "cjk".to_owned(),
        std::sync::Arc::new(egui::FontData::from_static(include_bytes!(
            "../fonts/NotoSansSC.otf"
        ))),
    );

    // ② 挂到 Proportional（正文）字体族的最前面，才会优先用它渲染中文
    fonts.families
        .entry(egui::FontFamily::Proportional)
        .or_default()
        .insert(0, "cjk".to_owned());
    // 等宽族也加上（可选）
    fonts.families
        .entry(egui::FontFamily::Monospace)
        .or_default()
        .push("cjk".to_owned());

    ctx.set_fonts(fonts);   // ③ 生效
}

// 在 App::new 里调用一次：
// fn new(cc: &eframe::CreationContext<'_>) -> Self {
//     setup_custom_fonts(&cc.egui_ctx);
//     Self::default()
// }''')
    A("```")
    A("")
    A("要点与其他坑：")
    A("")
    A("- **字体要嵌 → 包体变大**：完整 CJK 字体几 MB 到十几 MB；生产可用 `pyftsubset` 等子集化到常用字。")
    A("- **必须 `insert(0, ..)` 到族最前**：只 `push` 到末尾，中文仍会被前面的拉丁字体「抢」到而回退成豆腐块。")
    A("- **中文输入法（IME）**：egui 基于 winit，桌面基本可用；复杂候选/预编辑仍要在目标平台实测。")
    A("- **`FontData` 的 `Arc` 包裹**是较新版本（含 0.36）的写法；老教程可能没有 `Arc::new` —— 以 docs.rs 对应版本为准。")
    A("")
    A("> 一句话：**中文 egui 应用的第一件事，就是在 `App::new` 里 `setup_custom_fonts`**。不做这步，后面全是方块。")
    A("")
    # 十三
    A(f"## {SEC[12]}")
    A("")
    A(IMG8)
    A("")
    A("把前面所有概念串起来——一个可编译的待办事项应用：")
    A("")
    A("```rust")
    A(r'''use eframe::egui;

fn main() -> eframe::Result {
    eframe::run_native(
        "Todos — egui",
        eframe::NativeOptions::default(),
        Box::new(|_cc| Ok(Box::<TodoApp>::default())),
    )
}

#[derive(Default)]
struct TodoApp {
    input: String,
    items: Vec<Item>,
}

struct Item {
    text: String,
    done: bool,
}

impl eframe::App for TodoApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("待办事项");

            // 输入行：文本框 + 添加按钮；回车也能提交
            ui.horizontal(|ui| {
                let resp = ui.text_edit_singleline(&mut self.input);
                let entered =
                    resp.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
                if (ui.button("添加").clicked() || entered)
                    && !self.input.trim().is_empty()
                {
                    self.items.push(Item {
                        text: self.input.trim().to_owned(),
                        done: false,
                    });
                    self.input.clear();
                }
            });

            ui.separator();

            // 列表：立即模式下不能边遍历边删，先记下要删的下标，循环后再删
            let mut delete: Option<usize> = None;
            egui::ScrollArea::vertical().show(ui, |ui| {
                for (i, item) in self.items.iter_mut().enumerate() {
                    ui.horizontal(|ui| {
                        ui.checkbox(&mut item.done, "");
                        if item.done {
                            ui.label(egui::RichText::new(&item.text).strikethrough().weak());
                        } else {
                            ui.label(&item.text);
                        }
                        if ui.button("🗑").clicked() {
                            delete = Some(i);
                        }
                    });
                }
            });
            if let Some(i) = delete {
                self.items.remove(i);
            }

            ui.separator();
            let done = self.items.iter().filter(|it| it.done).count();
            ui.label(format!("共 {} 项 · 已完成 {}", self.items.len(), done));
        });
    }
}''')
    A("```")
    A("")
    A("这 ~60 行覆盖了：**App 状态自持、每帧重跑、`Response.clicked()`/`lost_focus()`、`ui.input` 读回车、`ScrollArea`、`RichText` 删除线、以及立即模式的「延迟删除」惯用法**（不能边 `iter_mut` 边 `remove`，先记下标循环后再删）——就是图 8 那个界面。生产版记得在 `App::new` 里装中文字体（第 12 节）。")
    A("")
    # 十四
    A(f"## {SEC[13]}")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 中文显示成方块 | `ui.label(\"中文\")` 全是 □ | `setup_custom_fonts` + `insert(0, ..)`（第 12 节） |")
    A("| `CentralPanel` 放最前 | 侧栏/顶栏被挤没 | 边缘面板先声明，`CentralPanel` 最后放 |")
    A("| 边遍历边删列表 | 借用冲突/panic | 先记 `Option<usize>`，循环后再 `remove` |")
    A("| 在 `update` 里跑重活 | 界面卡顿掉帧 | 丢后台线程 + `request_repaint`（第 10 节） |")
    A("| UI 线程 `rx.recv()` 阻塞 | 整个界面冻住 | 每帧 `try_recv()` 非阻塞取 |")
    A("| 后台数据不刷新 | 线程算完界面没反应 | 线程结束调 `ctx.request_repaint()` |")
    A("| 每帧 new 状态结构体 | 状态每帧被重置 | 状态放 `App` 字段，别在 `update` 里重建 |")
    A("| 硬编码颜色 | 换明暗主题掉队/刺眼 | 从 `ui.visuals()` 取色（第 11 节） |")
    A("| 期待「按钮对象」持久 | 找不到地方绑回调 | 立即模式无对象；`if ui.button().clicked()` 就地处理 |")
    A("| 忘了 `Ok(...)` 包裹 | `run_native` 类型不匹配 | creator 返回 `Ok(Box::new(app))` |")
    A("")
    # 十五
    A(f"## {SEC[14]}")
    A("")
    A("对照本工作区（元数据驱动企业平台，前端以 Web 资产为主）：")
    A("")
    A("1. **egui 在本仓最对口的场景 = 引擎类内部诊断/调试面板**。横评（`docs/20260920_Rust桌面GUI框架横评.md`）结论：flow/report/model 等引擎若要个本地调试面板，**egui 最划算**——单二进制、无前端构建链、`cargo run` 即用，且不进产品线、观感要求低。立即模式对「数据每帧都在变」的监控/诊断界面是**降维打击**。")
    A("2. **面向最终用户的桌面产品仍首选 Tauri 2**（复用 `frontend/` 的 UI5/Tabler 与双主题资产），egui 的默认观感偏工具风，不适合做门户级产品 UI。二者不冲突：egui 管「给开发者/运维看的内部工具」，Tauri 管「给业务用户看的产品」。")
    A("3. **禁硬编码色值这条纪律照搬**：egui 从 `ui.visuals()` 取色、`set_visuals` 一处切明暗，正是 CMX 硬约束 #4 在自绘 GUI 里的等价表达。")
    A("4. **状态观念一致**：egui 的 `App` 字段是单机 UI 态，业务持久数据仍外置（DB/Redis），与 CMX「集群无状态」不矛盾——别把 UI 态当持久层。")
    A("")
    A("> 与 iced 的分工（对照姊妹篇）：**要架构可长期演进的纯 Rust 桌面产品 → iced（Elm）；要最快糊一个内部工具/诊断面板 → egui（立即模式）**。同为自绘、同为纯 Rust，气质迥异。")
    A("")
    # 十六
    A(f"## {SEC[15]}")
    A("")
    A("**版本基线（2026-09）**：egui / eframe **0.36.x**（当前 0.36.2），0.36 起要求 **Rust edition 2024**。egui 每年发数个 0.x 版，**0.x 之间有破坏性变更**，但官方迁移说明（CHANGELOG）很详尽，升级成本可控。")
    A("")
    A("| 资源 | 地址 | 说明 |")
    A("|---|---|---|")
    A("| 官网 & 在线 Demo | egui.rs | 首页就是 WASM 版实时 demo，所有部件可当场玩 |")
    A("| API 文档 | docs.rs/egui · docs.rs/eframe | **锁定你的版本看**，一切以此为准 |")
    A("| 源码 & 示例 | github.com/emilk/egui | `examples/`、`egui_demo_app`（demo 全家桶源码） |")
    A("| 生态扩展 | `egui_extras`（表格/图片/日期）、`egui_plot`（绘图）、`egui_dock`（停靠面板） | 官方/社区常用扩展 |")
    A("| 生产案例 | rerun（可视化）、无数 Rust 内部工具、游戏引擎调试 UI | egui 的主场 |")
    A("")
    A("> 学习路径建议：**直接打开 egui.rs 首页的在线 demo，边点边看它对应的源码**（`egui_demo_lib` 里每个面板都有 “source code” 链接）。这是 egui 最高效的学法——所见即所写，demo 即教程。遇到 API 对不上，认准你锁定版本的 docs.rs。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **egui = 立即模式的效率怪物**：每帧把 UI 代码重跑一遍，界面就是代码此刻的输出；状态是你手里的变量，事件是 `if ui.button().clicked()` 的就地判断——没有树、没有 diff、没有回调。它给的是「十分钟出一个能用面板」的爽快，是内部工具、诊断面板、游戏调试 UI 的不二之选。想清楚你要的是这份「快」，它就是最省心的那个。")
    A("")
    A("> 参考：egui.rs（在线 demo）、docs.rs/egui 与 docs.rs/eframe、github.com/emilk/egui（examples / demo）。版本以 2026-09 的 0.36.x 线为准；凡涉及具体方法签名，请以你锁定版本的 docs.rs 为准，勿跨版本照抄。")

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
