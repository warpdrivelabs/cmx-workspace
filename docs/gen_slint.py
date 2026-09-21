#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust Slint 桌面框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_slint.py   (slint 1.17.x：声明式 .slint DSL，编译期生成；桌面→MCU)
"""
import base64
import html
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260920_Rust-slint桌面框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
SLN = ("#7c3aed", "#f5f3ff")   # slint violet（主色，与横评一致）
DSL = ("#0d9488", "#f0fdfa")   # .slint DSL 青
RS = ("#c2410c", "#fff7ed")    # Rust 橙
PROP = ("#0284c7", "#f0f9ff")  # 属性 天蓝
CB = ("#b45309", "#fffbeb")    # 回调 琥珀
MCU = ("#15803d", "#f0fdf4")   # 嵌入式 绿
LIC = ("#4338ca", "#eef2ff")   # 许可 靛
DAN = ("#dc2626", "#fef2f2")   # danger red
GRY = ("#475569", "#f1f5f9")   # slate
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


def win(x, y, w, h, title, body_fill="#ffffff", bar=SLN[0]):
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


def pill(x, y, w, s, fill=SLN[0], tcol="#fff", h=26):
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


def codepanel(x, y, w, h, lines, base_x=None, y0=None):
    base_x = x + 17 if base_x is None else base_x
    y0 = y + 45 if y0 is None else y0
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{CODEBG}"/>',
           f'<circle cx="{x+21}" cy="{y+21}" r="4.5" fill="#ff5f57"/>'
           f'<circle cx="{x+35}" cy="{y+21}" r="4.5" fill="#febc2e"/>'
           f'<circle cx="{x+49}" cy="{y+21}" r="4.5" fill="#28c840"/>']
    for i, s in enumerate(lines):
        indent = len(s) - len(s.lstrip(' '))
        xx = base_x + indent * 7.0
        out.append(f'<text x="{xx:.0f}" y="{y0 + i*20}" font-family="{MONO}" font-size="12" fill="{CODEFG}">{esc(s.lstrip(" "))}</text>')
    return "".join(out)


def slug(t_):
    out = []
    for ch in t_.lower():
        if ch == ' ':
            out.append('-')
        elif ch == '-' or ch.isalnum():
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- FIG 1 声明式编译期生成
def fig_codegen():
    W, H = 940, 420
    b = []
    b.append(box(70, 66, 320, 116, "app.slint（声明式 UI）", [
        "export component … inherits Window", "property 属性 + <=> 绑定",
        "布局 + callback 回调声明", "← 设计器 / live-preview 可直接改"], DSL))
    b.append(box(550, 66, 320, 116, "main.rs（业务逻辑）", [
        "let ui = AppWindow::new()?;", "ui.on_xxx(...) 处理回调",
        "ui.set_xxx(...) 喂数据 / get 读", "ui.run()?"], RS))
    b.append(arrow(230, 182, 380, 232, "编译期", DSL[0]))
    b.append(arrow(710, 182, 560, 232, "include_modules!", RS[0]))
    b.append(box(320, 232, 300, 58, "build.rs · slint_build::compile()", [
        "把 .slint 生成 Rust 代码（无运行时解释）"], SLN))
    b.append(arrow(470, 290, 470, 320))
    b.append(box(330, 320, 280, 50, "原生二进制（编译期已定型）", [], GRY))
    b.append(caption(W, 398, "设计（.slint）与逻辑（Rust）物理分离，类 QML；build.rs 编译期把 DSL 变成 Rust——运行时无解释开销，且 .slint 可被可视化设计器/预览器直接编辑"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 .slint 解剖
def fig_dsl():
    W, H = 940, 440
    b = []
    lines = [
        'import { Button, VerticalBox }',
        '  from "std-widgets.slint";',
        '',
        'export component AppWindow',
        '        inherits Window {',
        '    in-out property <int> count: 0;',
        '    callback increase();',
        '',
        '    VerticalBox {',
        '        Text { text: "计数: \\{root.count}"; }',
        '        Button {',
        '            text: "加一";',
        '            clicked => { root.increase(); }',
        '        }',
        '    }',
        '}',
    ]
    b.append(codepanel(45, 55, 545, 350, lines))
    calls = [
        (108, 108, "导入标准控件", DSL[0]),
        (148, 152, "根组件 inherits Window", SLN[0]),
        (188, 196, "属性 property + 初值", PROP[0]),
        (208, 240, "回调 callback 声明", CB[0]),
        (288, 292, "布局容器 VerticalBox", RS[0]),
        (308, 336, '插值 \\{root.count}', MCU[0]),
        (368, 380, "事件绑定 clicked =>", DAN[0]),
    ]
    for line_y, cy, lab, cc in calls:
        b.append(arrow(590, line_y, 636, cy, "", cc))
        b.append(f'<rect x="640" y="{cy-13}" width="270" height="26" rx="6" fill="#fff" stroke="{cc}" stroke-width="1.4"/>')
        b.append(t(652, cy + 4, lab, 11, "#1e293b", "start", "700"))
    b.append(caption(W, 424, ".slint 是声明式 DSL：import 控件、component 定义、property 属性、callback 回调、布局容器、\\{} 插值、=> 事件绑定——编译期生成 Rust，非字符串"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 DSL↔Rust 桥
def fig_bridge():
    W, H = 940, 410
    b = []
    b.append(box(60, 66, 330, 150, "app.slint 声明", [
        "in-out property <int> count;", "callback increase();", "",
        "Button {", "  clicked => { root.increase(); }", "}"], DSL))
    b.append(box(560, 66, 330, 150, "main.rs 驱动", [
        "ui.get_count() / ui.set_count(v)", "  ← 属性的 getter / setter", "",
        "ui.on_increase(move || { … })", "  ← 回调处理器", "let weak = ui.as_weak();"], RS))
    b.append(arrow(390, 108, 560, 108, "属性↔get/set", PROP[0]))
    b.append(arrow(390, 168, 560, 168, "回调→on_ 处理", CB[0]))
    b.append(box(230, 258, 480, 84, "⚠ 回调闭包捕获 Weak，别捕获强引用", [
        "ui.on_x(move || { let ui = weak.upgrade().unwrap(); … })",
        "捕获强引用 → 组件 ↔ 闭包 循环引用 → 内存泄漏（Slint 头号坑）"], DAN))
    b.append(caption(W, 384, "DSL 与 Rust 的桥：属性 ↔ get/set 双向、callback ↔ on_ 处理器（命名 - 变 _）。铁律：回调里用 as_weak() 的弱句柄，upgrade 后再用"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 模型与列表
def fig_model():
    W, H = 940, 400
    b = []
    b.append(box(60, 66, 350, 140, "Rust 侧：VecModel", [
        "let m = Rc::new(VecModel::default());", "ui.set_todos(m.clone().into());",
        "m.push(item)  ·  m.set_vec(v)", "m.row_data(i) / m.set_row_data(i, x)", "m.remove(i)"], RS))
    b.append(box(540, 66, 350, 140, ".slint 侧：for … in model", [
        "in property <[TodoItem]> todos;", "ListView {", "  for it in root.todos:",
        "    HorizontalBox { CheckBox … }", "}"], DSL))
    b.append(arrow(410, 120, 540, 120, "set_todos(m.into())", DSL[0]))
    b.append(box(230, 246, 480, 84, "⚠ ModelRc 不是 Send", [
        "跨线程改模型：只把 Weak 送进线程，回主线程改——",
        "ui.as_weak() → upgrade_in_event_loop(move |ui| { …改模型… })"], DAN))
    b.append(caption(W, 376, "动态列表 = 模型驱动：Rust 建 VecModel、set 给属性，.slint 用 for…in 遍历渲染；模型非 Send，跨线程必须回事件循环里改"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 主题
def fig_theme():
    W, H = 940, 430
    b = []
    b.append(win(50, 50, 205, 205, "Light", "#ffffff", SLN[0]))
    b.append(t(70, 92, "标题", 14, "#1e1e1e", "start", "700"))
    b.append(chip(70, 104, 76, "确定", SLN[0], "#fff", 26))
    b.append(field(155, 104, 82, "输入…", 26))
    b.append(f'<rect x="70" y="146" width="16" height="16" rx="3" fill="{SLN[0]}"/>')
    b.append(f'<path d="M 73 154 l 3 3 l 6 -7" stroke="#fff" stroke-width="2" fill="none"/>')
    b.append(t(94, 159, "选项", 11, "#1e1e1e"))
    b.append(t(70, 210, "正文文本", 11, "#64748b"))
    b.append(win(295, 50, 205, 205, "Dark", "#202124", "#3a3145"))
    b.append(t(315, 92, "标题", 14, "#e8e8e8", "start", "700"))
    b.append(chip(315, 104, 76, "确定", "#a78bfa", "#1a1523", 26))
    b.append(field(400, 104, 82, "输入…", 26, bg="#2f2f34", border="#555", fg="#9aa0a6"))
    b.append(f'<rect x="315" y="146" width="16" height="16" rx="3" fill="#a78bfa"/>')
    b.append(f'<path d="M 318 154 l 3 3 l 6 -7" stroke="#1a1523" stroke-width="2" fill="none"/>')
    b.append(t(339, 159, "选项", 11, "#e8e8e8"))
    b.append(t(315, 210, "正文文本", 11, "#9aa0a6"))
    b.append(arrow(255, 152, 295, 152, "切换", SLN[0]))
    b.append(box(550, 50, 350, 120, "Palette + Style（主题真源）", [
        "内置风格：Fluent / Material / Cupertino /",
        "        Cosmic / native（各带 -light/-dark）",
        "Palette.background / .foreground / .accent…"], SLN))
    b.append(t(550, 196, "从 Palette 取色（示意）:", 11, "#334155", "start", "700"))
    sw = [("background", "#ffffff"), ("foreground", "#1e1e1e"), ("accent", SLN[0]),
          ("border", "#cbd5e1"), ("error", "#dc2626")]
    xx = 550
    for name, cc in sw:
        b.append(f'<rect x="{xx}" y="206" width="64" height="34" rx="6" fill="{cc}" stroke="#cbd5e1" stroke-width="1"/>')
        b.append(t(xx + 32, 259, name, 8, "#64748b", "middle", "400", MONO))
        xx += 70
    b.append(box(180, 300, 580, 74, "禁硬编码色值（对齐 CMX 硬约束）", [
        "✔ 用 Palette.accent-background / Palette.foreground 派生",
        "✘ 别写死 #7c3aed —— 换 style / 明暗就掉队、对比崩坏"], DAN))
    b.append(caption(W, 402, "选一套 style（Fluent/Material/…）定基调，颜色从 Palette 派生、随明暗切换——与 CMX「双主题通路、禁硬编码色值」同款要求"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 多渲染器+MCU
def fig_mcu():
    W, H = 940, 440
    b = []
    b.append(box(360, 50, 220, 52, "一份 .slint 源", ["同一套 UI 声明"], SLN))
    b.append(arrow(470, 102, 470, 124))
    # 三渲染器
    b.append(box(60, 124, 250, 66, "Skia 渲染器", ["GPU 直绘，桌面/高端设备", "观感最精细"], PROP))
    b.append(box(345, 124, 250, 66, "FemtoVG 渲染器", ["OpenGL/GLES", "中端设备"], DSL))
    b.append(box(630, 124, 250, 66, "软件渲染器", ["纯 CPU 光栅化", "无 GPU 也能跑"], MCU))
    b.append(arrow(185, 190, 300, 240, "", PROP[0]))
    b.append(arrow(470, 190, 470, 240, "", DSL[0]))
    b.append(arrow(755, 190, 640, 240, "", MCU[0]))
    # 下沉链
    b.append(box(120, 240, 220, 60, "桌面（Win/mac/Linux）", ["GPU 渲染，功能全"], GRY))
    b.append(arrow(340, 270, 400, 270, "下沉", MCU[0]))
    b.append(box(400, 240, 200, 60, "嵌入式 Linux", ["工控 HMI / 车机"], GRY))
    b.append(arrow(600, 270, 660, 270, "再下沉", MCU[0]))
    b.append(box(660, 240, 240, 60, "MCU（no_std）", ["STM32/ESP32，数百 KB RAM", "软件渲染 + 平台适配层"], MCU))
    b.append(box(230, 340, 480, 42, "★ 杀手锏：五框架里唯一能 no_std 跑上单片机的", [], SLN))
    b.append(caption(W, 414, "同一份 .slint，换渲染器后端即从桌面 GPU 一路下沉到嵌入式 Linux、乃至数百 KB RAM 的 MCU——iced/egui/Dioxus/Tauri 都到不了这一层"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 7 许可三选一
def fig_license():
    W, H = 940, 420
    b = []
    b.append(box(360, 46, 220, 44, "你的 Slint 应用要发布成？", [], GRY))
    b.append(box(60, 150, 250, 96, "① 开源应用", [
        "整体开源即可免费", "含嵌入式设备", "", "→ GPLv3"], MCU))
    b.append(box(345, 150, 250, 96, "② 闭源：桌面/移动/Web", [
        "免费，含商用闭源", "条件：保留", "「Made with Slint」归属", "→ Royalty-Free 免版税"], LIC))
    b.append(box(630, 150, 250, 96, "③ 闭源 + 嵌入式发货", [
        "设备端闭源出货", "必须付费（按设备计费）", "或回到 GPL", "→ Commercial 商业许可"], CB))
    b.append(arrow(400, 90, 185, 150, "开源", MCU[0]))
    b.append(arrow(470, 90, 470, 150, "闭源·非嵌入式", LIC[0]))
    b.append(arrow(540, 90, 755, 150, "闭源·嵌入式", CB[0]))
    b.append(box(150, 300, 640, 60, "决策提示", [
        "企业内部工具 / 桌面产品：走 Royalty-Free，免费（保留归属声明即可）",
        "唯一会碰收费闸门的组合 = 「闭源 + 嵌入式设备发货」；含官方付费技术支持"], SLN))
    b.append(caption(W, 398, "Slint 独有的三许可：开源→GPL；闭源桌面/移动/Web→免版税（免费+归属）；闭源嵌入式发货→商业（付费）。选型必须把这条算进去"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 8 Todo 界面
def fig_todo():
    W, H = 640, 450
    b = []
    b.append(win(80, 40, 480, 370, "Todos — Slint"))
    b.append(t(105, 84, "待办事项", 16, "#0f172a", "start", "700"))
    b.append(field(105, 100, 320, "要做点什么？", 32))
    b.append(pill(438, 102, 96, "添加", SLN[0], "#fff", 28))
    b.append(f'<line x1="105" y1="150" x2="534" y2="150" stroke="#e2e8f0" stroke-width="1.4"/>')
    items = [("写 slint 使用说明", True), ("画 8 张 SVG 图", True), ("跑 gen_slint.py 校验", False)]
    yy = 166
    for txt_, done in items:
        if done:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="4" fill="{SLN[0]}"/>')
            b.append(f'<path d="M 116 {yy+10} l 4 4 l 8 -9" stroke="#fff" stroke-width="2.2" fill="none"/>')
            b.append(f'<text x="142" y="{yy+15}" font-family="{SANS}" font-size="12.5" fill="#94a3b8" '
                     f'text-decoration="line-through">{esc(txt_)}</text>')
        else:
            b.append(f'<rect x="112" y="{yy}" width="20" height="20" rx="4" fill="#fff" stroke="#94a3b8" stroke-width="1.8"/>')
            b.append(t(142, yy + 15, txt_, 12.5, "#1e293b"))
        b.append(chip(494, yy - 2, 40, "删除", DAN[1], DAN[0], 24))
        yy += 42
    b.append(f'<line x1="105" y1="306" x2="534" y2="306" stroke="#e2e8f0" stroke-width="1.4"/>')
    b.append(t(112, 330, "共 3 项 · 已完成 2 项", 12, "#64748b", "start", "700"))
    b.append(t(105, 396, "类原生控件观感（Fluent 风）；上面这一屏 = 第 13 节完整代码的产物", 9.5, "#94a3b8", "start"))
    b.append(caption(W, 434, "第 13 节完整代码的成品：LineEdit + ListView（勾选/删除）+ 计数，UI 在 .slint、逻辑在 Rust"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_codegen(), "图1：声明式 DSL 编译期生成")
IMG2 = b64img(fig_dsl(), "图2：.slint 语言解剖")
IMG3 = b64img(fig_bridge(), "图3：DSL ↔ Rust 桥")
IMG4 = b64img(fig_model(), "图4：模型与列表")
IMG5 = b64img(fig_theme(), "图5：主题与 Palette")
IMG6 = b64img(fig_mcu(), "图6：多渲染器与下沉 MCU")
IMG7 = b64img(fig_license(), "图7：许可三选一")
IMG8 = b64img(fig_todo(), "图8：Todo 应用界面")

SEC = [
    "一、Slint 是什么：声明式 DSL，编译期生成",
    "二、安装与第一个程序",
    "三、.slint 语言：组件 · 属性 · 布局",
    "四、属性与数据绑定：in/out/in-out · 双向绑定",
    "五、回调与 Rust 集成：DSL 声明 ↔ Rust 处理",
    "六、内置控件与标准布局",
    "七、全局单例与逻辑组织",
    "八、模型与列表：VecModel · ListView",
    "九、主题与样式：Palette · 明暗",
    "十、多渲染器与嵌入式：no_std 下沉 MCU",
    "十一、live-preview 与工具链",
    "十二、许可证三选一：GPL / 免版税 / 商业",
    "十三、完整实例：待办事项 Todo",
    "十四、常见坑速查",
    "十五、与 CMX 工作区的呼应",
    "十六、版本与参考资源",
]


def main():
    D = []
    A = D.append
    A("# Rust Slint 桌面框架详细使用说明")
    A("")
    A("> **定位**：Slint 是**声明式 `.slint` DSL** 驱动的原生 UI 框架——UI 用一门专门的标记语言写（类 QML），`build.rs` 在**编译期把它生成 Rust 代码**，逻辑用 Rust 写，**设计与逻辑物理分离**。创始团队出自 Qt/QML，目标就是「现代 Qt」。")
    A("> **杀手锏**：多渲染器（Skia / FemtoVG / 软件），**唯一能 `no_std` 下沉到 MCU（单片机）** 的 Rust GUI；Rust/C++/JS/Python 四语言绑定；live-preview 即改即见。")
    A("> **版本基线（2026-09）**：Slint **1.17.x**。1.x 有明确的语义化版本纪律，比多数 0.x 框架稳。")
    A("> **要单独看的一条**：**许可三选一**（GPLv3 / 免版税 / 商业）——桌面/移动/Web 走免版税免费，**只有「闭源 + 嵌入式发货」才收费**（第 12 节）。")
    A("> **一句话取舍**：给「有设计师协作、有嵌入式野心、想要类 Qt 工作流」的团队；短板是要学一门 DSL、许可有决策成本、社区规模小于另外四家。")
    A("> **图**：8 张内嵌 base64 SVG。所有易变 API 处均标注「以 docs.rs 对应版本为准」。")
    A("")
    A("> 姊妹篇：iced（Elm·自绘）、egui（立即模式·自绘）、Dioxus（组件/信号·WebView）三份使用说明 + `docs/20260920_Rust桌面GUI框架横评.md`（五框架横评）。")
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
    A("Slint 的世界观和另外四家都不同——**UI 不用宿主语言写，而用一门专门的声明式 DSL 写**：")
    A("")
    A("- **`.slint` 文件**：声明式描述 UI（组件、属性、布局、绑定、回调），类似 QML。**设计师、可视化设计器、live-preview 都能直接编辑它**。")
    A("- **`build.rs`**：用 `slint-build` 在**编译期**把 `.slint` **生成 Rust 代码**（不是运行时解释）——所以没有解释开销，且类型安全。")
    A("- **Rust 侧**：写业务逻辑，通过生成的 `AppWindow::new()` / `get_*` / `set_*` / `on_*` 与 UI 交互。")
    A("")
    A("> 核心价值是**设计与逻辑的物理分离**（类 Qt/QML 工作流）：UI 描述独立成文件，可被工具链可视化编辑、可被设计师改，逻辑代码不受污染。这对「有设计协作、UI 迭代频繁」的团队是实打实的好处；代价是你得**多学一门 DSL**。")
    A("")
    A("> 与本系列另外三位的分野：iced/egui **自绘**、用 Rust 写 UI；Dioxus 用 Rust RSX、桌面走 WebView；**Slint 用独立 DSL、编译期生成、自绘（Skia/软件），且能下沉到 MCU**——这是它最独特的地方（第 10 节）。")
    A("")
    # 二
    A(f"## {SEC[1]}")
    A("")
    A("三个文件：`.slint`（UI）、`build.rs`（编译期生成）、`main.rs`（逻辑）。`Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[dependencies]
slint = "1.17"

[build-dependencies]
slint-build = "1.17"''')
    A("```")
    A("")
    A("`ui/app-window.slint`——声明 UI：")
    A("")
    A("```slint")
    A(r'''import { Button, VerticalBox, HorizontalBox } from "std-widgets.slint";

export component AppWindow inherits Window {
    in-out property <int> counter: 0;      // 属性（带初值），Rust 可读可写
    callback increase();                   // 回调，交给 Rust 处理
    callback decrease();

    VerticalBox {
        Text { text: "计数: \{root.counter}"; font-size: 24px; }
        HorizontalBox {
            Button { text: "-"; clicked => { root.decrease(); } }
            Button { text: "+"; clicked => { root.increase(); } }
        }
    }
}''')
    A("```")
    A("")
    A("`build.rs`——编译期把 `.slint` 变成 Rust：")
    A("")
    A("```rust")
    A(r'''fn main() {
    slint_build::compile("ui/app-window.slint").unwrap();
}''')
    A("```")
    A("")
    A("`src/main.rs`——写逻辑：")
    A("")
    A("```rust")
    A(r'''slint::include_modules!();   // 拉入 build.rs 生成的代码（AppWindow 就来自这里）

fn main() -> Result<(), slint::PlatformError> {
    let ui = AppWindow::new()?;

    // 注册回调：捕获 Weak 句柄，避免闭包与组件循环引用而泄漏
    let weak = ui.as_weak();
    ui.on_increase(move || {
        let ui = weak.upgrade().unwrap();
        ui.set_counter(ui.get_counter() + 1);   // getter + setter（属性名 - 变 _）
    });
    let weak = ui.as_weak();
    ui.on_decrease(move || {
        let ui = weak.upgrade().unwrap();
        ui.set_counter(ui.get_counter() - 1);
    });

    ui.run()
}''')
    A("```")
    A("")
    A("`cargo run` 即见窗口。对比另外三家：iced 四件套、egui 每帧 `update`、Dioxus 组件/信号——**Slint 是「DSL 声明界面 + Rust 处理回调」**，UI 和逻辑在不同文件、不同语言。中文默认能显示（自绘但内置字体处理，复杂场景仍可配字体）。")
    A("")
    # 三
    A(f"## {SEC[2]}")
    A("")
    A(IMG2)
    A("")
    A("`.slint` 是一门小而专的声明式语言。要素：")
    A("")
    A("```slint")
    A(r'''// 导入标准控件
import { Button, LineEdit, VerticalBox } from "std-widgets.slint";

// 自定义可复用组件
component LabeledInput inherits HorizontalBox {
    in property <string> label;
    in-out property <string> value;
    Text { text: root.label; }
    LineEdit { text <=> root.value; }        // <=> 双向绑定
}

// 结构体（会生成对应的 Rust struct）
struct Person { name: string, age: int }

// 导出的主组件
export component MainWindow inherits Window {
    preferred-width: 400px;
    preferred-height: 300px;

    in-out property <string> username;

    VerticalBox {
        LabeledInput { label: "用户名"; value <=> root.username; }
        Text { text: "你好, \{root.username}"; }   // \{} 插值
    }
}''')
    A("```")
    A("")
    A("| 语法 | 说明 |")
    A("|---|---|")
    A("| `component X inherits Y { }` | 定义组件（继承 Window / 布局 / 其它组件） |")
    A("| `property <类型> 名: 初值;` | 属性；类型有 `int/float/string/bool/color/length/[T]` 等 |")
    A("| `struct S { … }` | 结构体，生成对应 Rust `struct` |")
    A("| `callback foo(参数);` | 回调声明 |")
    A("| `属性: 表达式;` | 绑定（表达式变，属性自动更新——响应式） |")
    A("| `a <=> b` | 双向绑定 |")
    A(r'| `"…\{expr}…"` | 字符串插值 |')
    A("| `//` `/* */` | 注释 |")
    A("")
    A(r'> `-` 和 `_` 在 `.slint` 里等价（`request-increase` == `request_increase`），但生成到 Rust 时统一变 `_`（`on_request_increase`）。属性绑定是**响应式**的：`Text { text: "\{a + b}" }` 里 `a` 或 `b` 变，文本自动重算。')
    A("")
    # 四
    A(f"## {SEC[3]}")
    A("")
    A("属性有**方向**，决定 Rust 侧能读还是能写：")
    A("")
    A("```slint")
    A(r'''export component W inherits Window {
    in property <string> title;      // 输入：Rust set，组件内只读（有 set_title）
    out property <bool> is-valid;     // 输出：组件内算，Rust 读（有 get_is_valid）
    in-out property <int> count;      // 双向：Rust 可读可写（get + set）
    property <int> internal: 0;       // 无方向 = 私有，仅组件内部用（Rust 看不到）

    // 绑定：is-valid 由 title 推导，title 一变自动重算（响应式）
    is-valid: root.title != "";
}''')
    A("```")
    A("")
    A("| 方向 | Rust 侧 | 用途 |")
    A("|---|---|---|")
    A("| `in` | 只 `set_x()` | 外部喂数据给 UI（如标题、列表） |")
    A("| `out` | 只 `get_x()` | UI 算出结果给外部（如校验结果） |")
    A("| `in-out` | `get` + `set` | 双向（如输入框内容） |")
    A("| 无方向 | 不可见 | 组件内部私有状态 |")
    A("")
    A("**双向绑定 `<=>`** 是减少样板的利器——控件和属性自动同步，不用手写回调：")
    A("")
    A("```slint")
    A(r'''in-out property <string> name;
LineEdit { text <=> root.name; }     // 输入框改 → name 改；name 改 → 输入框改''')
    A("```")
    A("")
    A("> 绑定是 Slint「声明式」的精髓：你声明「谁等于谁的函数」，值一变，依赖它的全部自动更新——和 Dioxus 信号异曲同工，但写在 DSL 里、编译期定型。")
    A("")
    # 五
    A(f"## {SEC[4]}")
    A("")
    A(IMG3)
    A("")
    A("回调（callback）是 UI 通知 Rust「发生了事」的通道：`.slint` **声明**，Rust 用 `on_*` **处理**。")
    A("")
    A("```slint")
    A(r'''export component W inherits Window {
    callback increase();                 // 无参
    callback name-edited(string);        // 带参
    callback validate(string) -> bool;   // 带返回值

    LineEdit { edited(text) => { root.name-edited(text); } }
    Button { clicked => { root.increase(); } }
}''')
    A("```")
    A("")
    A("```rust")
    A(r'''let weak = ui.as_weak();
ui.on_increase(move || {
    let ui = weak.upgrade().unwrap();    // 弱句柄升级
    ui.set_counter(ui.get_counter() + 1);
});

ui.on_name_edited(move |text| {          // 参数按声明顺序传入（- 变 _）
    println!("输入变成: {text}");
});

ui.on_validate(|text| !text.is_empty()); // 带返回值的回调''')
    A("```")
    A("")
    A("**Rust 集成三件套 + 一条铁律**：")
    A("")
    A("- `slint::include_modules!()`（配 `build.rs`）或内联 `slint::slint!{ … }` 宏引入生成代码。")
    A("- 属性：`get_x()` / `set_x(v)`；回调：`on_x(closure)`；命名里的 `-` 到 Rust 全变 `_`。")
    A("- **铁律：回调闭包里用 `ui.as_weak()` 的弱句柄，`upgrade()` 后再用**。捕获强引用 `ui` 会造成「组件 ↔ 闭包」循环引用 → **内存泄漏**（这是 Slint 的头号坑）。")
    A("- **线程**：事件循环必须在主线程；组件也要在主线程创建。跨线程更新见第 8 节。")
    A("")
    # 六
    A(f"## {SEC[5]}")
    A("")
    A("`std-widgets.slint` 提供一套跨平台控件，配合布局容器用：")
    A("")
    A("```slint")
    A(r'''import {
    Button, LineEdit, TextEdit, CheckBox, Switch, Slider, SpinBox,
    ComboBox, ListView, StandardListView, ScrollView, ProgressIndicator,
    VerticalBox, HorizontalBox, GridBox, GroupBox, TabWidget
} from "std-widgets.slint";

export component W inherits Window {
    VerticalBox {
        LineEdit { placeholder-text: "搜索…"; }
        HorizontalBox {
            CheckBox { text: "记住我"; }
            Switch { checked: true; }
        }
        Slider { minimum: 0; maximum: 100; value: 50; }
        ComboBox { model: ["苹果", "梨", "橙"]; }
        Button { text: "提交"; primary: true; }
    }
}''')
    A("```")
    A("")
    A("| 控件 | 布局 |")
    A("|---|---|")
    A("| `Button`（`primary`） / `LineEdit` / `TextEdit` | `VerticalBox` 竖排 |")
    A("| `CheckBox` / `Switch` / `Slider` / `SpinBox` | `HorizontalBox` 横排 |")
    A("| `ComboBox` / `ListView` / `StandardListView` | `GridBox` 网格 |")
    A("| `ScrollView` / `TabWidget` / `GroupBox` | `Spacer` 弹性占位 |")
    A("| `ProgressIndicator` | 手写 `Rectangle` + `x/y/width/height` 绝对定位 |")
    A("")
    A("> 布局容器（`*Box`）自动排布并响应窗口缩放；也能用 `Rectangle` + 几何属性做像素级绝对定位。控件外观随选定的 style（Fluent/Material/…）变（第 9 节）。")
    A("")
    # 七
    A(f"## {SEC[6]}")
    A("")
    A("跨组件共享状态用 **全局单例 `global`**，避免层层传属性：")
    A("")
    A("```slint")
    A(r'''// 定义一个全局单例
export global AppState {
    in-out property <string> user;
    in-out property <bool> dark-mode;
    callback logout();
}

export component W inherits Window {
    Text { text: "当前用户: \{AppState.user}"; }        // 任意组件直接引用
    Button { text: "退出"; clicked => { AppState.logout(); } }
}''')
    A("```")
    A("")
    A("```rust")
    A(r'''use slint::ComponentHandle;

let ui = AppWindow::new()?;
// 通过 global::<T>() 访问全局单例
ui.global::<AppState>().set_user("张三".into());
ui.global::<AppState>().on_logout(move || { /* … */ });''')
    A("```")
    A("")
    A("> `global` 适合放「整个应用的状态与命令」（当前用户、主题、路由）。组织大型 UI 时：拆多个 `.slint` 文件（`import` 复用组件）、用 `global` 管全局态、用 `struct` + 模型管数据——DSL 侧就有一套完整的模块化手段。")
    A("")
    # 八
    A(f"## {SEC[7]}")
    A("")
    A(IMG4)
    A("")
    A("动态列表用**模型（Model）**驱动：Rust 建 `VecModel`、set 给属性，`.slint` 用 `for … in` 遍历。")
    A("")
    A("```slint")
    A(r'''struct TodoItem { id: int, text: string, done: bool }

export component W inherits Window {
    in property <[TodoItem]> todos;        // 列表属性
    callback toggle(int);

    ListView {
        for item in root.todos: HorizontalBox {
            CheckBox { checked: item.done; toggled => { root.toggle(item.id); } }
            Text { text: item.text; }
        }
    }
}''')
    A("```")
    A("")
    A("```rust")
    A(r'''use slint::{VecModel, ModelRc};
use std::rc::Rc;

let ui = W::new()?;
let todos = Rc::new(VecModel::<TodoItem>::default());
ui.set_todos(todos.clone().into());        // Rc<VecModel> -> ModelRc（.into()）

todos.push(TodoItem { id: 1, text: "买菜".into(), done: false });  // 增
todos.set_row_data(0, updated_item);                              // 改
todos.remove(0);                                                  // 删
// 这些改动会自动通知 UI 刷新（Model 通知机制）''')
    A("```")
    A("")
    A("| 操作 | API |")
    A("|---|---|")
    A("| 建模型 | `Rc::new(VecModel::default())` |")
    A("| 绑到属性 | `ui.set_x(model.clone().into())` |")
    A("| 增 / 删 | `model.push(x)` / `model.remove(i)` |")
    A("| 读 / 改某行 | `model.row_data(i)` / `model.set_row_data(i, x)` |")
    A("| 整体替换 | `model.set_vec(vec)` |")
    A("")
    A("> **跨线程铁律**：`ModelRc` **不是 `Send`**，只能在主线程用。后台线程算完数据，**只把 `ui.as_weak()` 送进线程**，回到 `weak.upgrade_in_event_loop(move |ui| { …改模型… })` 里改——直接把 `Rc<VecModel>` move 进线程会编译报错。")
    A("")
    # 九
    A(f"## {SEC[8]}")
    A("")
    A(IMG5)
    A("")
    A("Slint 的外观由**选定的 style** + **`Palette` 全局调色板**决定：")
    A("")
    A("- **Style**（编译期选）：`fluent` / `material` / `cupertino` / `cosmic` / `native`，各带 `-light` / `-dark`。控件长相随之变。")
    A("- **`Palette`**：内置全局调色板（`Palette.background` / `.foreground` / `.accent-background` …），控件和你的自定义元素都应**从它取色**。")
    A("")
    A("```slint")
    A(r'''export component W inherits Window {
    // ✔ 从 Palette 派生颜色，随 style / 明暗自动适配
    Rectangle {
        background: Palette.accent-background;
        Text { text: "标题"; color: Palette.accent-foreground; }
    }
    // ✘ 别写死：background: #7c3aed;  —— 换 style / 暗色就掉队
}''')
    A("```")
    A("")
    A("选 style 的两种方式：")
    A("")
    A("```rust")
    A(r'''// build.rs 里指定
slint_build::compile_with_config(
    "ui/app.slint",
    slint_build::CompilerConfiguration::new().with_style("fluent-dark".into()),
).unwrap();
// 或运行时用环境变量 SLINT_STYLE=material-light cargo run''')
    A("```")
    A("")
    A("> **对齐 CMX 硬约束 #4（双主题通路、禁硬编码色值）**：Slint 里同理——颜色一律从 `Palette` 派生，明暗随 style 切换。写死色值的后果就是换主题/换 style 后对比度崩坏。这条与 iced/egui 的自绘取色、Dioxus 的 CSS 变量，本质是同一个要求。")
    A("")
    # 十
    A(f"## {SEC[9]}")
    A("")
    A(IMG6)
    A("")
    A("**这是 Slint 相对另外四家的独门能力**：同一份 `.slint`，换渲染器后端就能从桌面一路下沉到单片机。")
    A("")
    A("- **三渲染器**：`Skia`（GPU，桌面/高端，最精细）、`FemtoVG`（OpenGL/GLES，中端）、`software`（纯 CPU 光栅化，无 GPU 也能跑）。用 feature 选：")
    A("")
    A("```toml")
    A(r'''slint = { version = "1.17", features = ["renderer-skia"] }
# 或 renderer-femtovg / renderer-software；嵌入式再加 no_std 相关配置''')
    A("```")
    A("")
    A("- **下沉链**：桌面（GPU）→ 嵌入式 Linux（工控 HMI / 车机）→ **MCU（`no_std`，STM32/ESP32 级，数百 KB RAM，软件渲染 + 自定义平台适配层）**。")
    A("- **杀手锏**：**五框架里唯一能 `no_std` 跑上单片机的**——iced / egui / Dioxus / Tauri 全都到不了这一层。做工业 HMI、车机、白电、仪器面板，这是 Slint 的独家主场。")
    A("")
    A("> 嵌入式做法：`no_std` + `renderer-software` + 实现 `slint::platform::Platform`（提供显示缓冲、时间、输入）。官方有 MCU 板级示例（STM32、ESP32、树莓派 Pico 等）。这也是 Slint 有商业公司背书、按设备收费的底气所在（第 12 节）。")
    A("")
    # 十一
    A(f"## {SEC[10]}")
    A("")
    A("Slint 的工具链是它「设计协作」卖点的兑现：")
    A("")
    A("| 工具 | 用途 |")
    A("|---|---|")
    A("| **VS Code 扩展** | `.slint` 语法高亮 + **live-preview（即改即见）** + 补全 |")
    A("| **SlintPad** | 浏览器里在线写 `.slint` 即时预览（slintpad.com） |")
    A("| **`slint-viewer`** | 命令行直接预览一个 `.slint` 文件 |")
    A("| **设计器（Slint Designer）** | 可视化拖拽编辑 `.slint`（面向设计师） |")
    A("| **Figma 导入** | 从 Figma 设计稿生成 `.slint`（官方插件） |")
    A("")
    A("> **live-preview 是它对 iced 的代差**：改 `.slint` 里的 UI，预览器**即刻刷新**，不用重编 Rust（逻辑没变时）。这让 UI 迭代很快——是「设计与逻辑分离」在开发体验上的直接兑现。逻辑改动仍要重编。")
    A("")
    # 十二
    A(f"## {SEC[11]}")
    A("")
    A(IMG7)
    A("")
    A("**这一节可能直接决定你能不能用它**——Slint 是本系列唯一非纯宽松许可的框架，**三选一**：")
    A("")
    A("| 许可 | 适用 | 代价 |")
    A("|---|---|---|")
    A("| **GPLv3** | 应用整体开源（含嵌入式） | 你的应用也得开源 |")
    A("| **Royalty-Free（免版税）** | **桌面 / 移动 / Web，含闭源商用** | 保留「Made with Slint」归属声明 |")
    A("| **Commercial（商业）** | **闭源 + 嵌入式设备发货** | 按设备计费；含官方付费支持 |")
    A("")
    A("决策提示：")
    A("")
    A("- **企业内部工具 / 桌面产品**：走 **Royalty-Free**，免费，保留一行归属声明即可——绝大多数团队走这条。")
    A("- **要开源**：GPLv3，免费，含嵌入式。")
    A("- **唯一会碰收费闸门的组合 = 「闭源 + 嵌入式设备发货」**：要么买商业许可（按设备计费，官方公布过 1 美元/台级起步的方案），要么回到 GPL。")
    A("")
    A("> 一句话：**桌面/Web 场景 Slint 免费可商用**（保留归属）；**只有闭源硬件出货这一种情况要付费**。选型时把这条和「你会不会做嵌入式发货」一起想清楚。")
    A("")
    # 十三
    A(f"## {SEC[12]}")
    A("")
    A(IMG8)
    A("")
    A("把前面的概念串起来——待办事项应用。`ui/todo.slint`（UI）：")
    A("")
    A("```slint")
    A(r'''import { Button, LineEdit, CheckBox, ListView, VerticalBox, HorizontalBox } from "std-widgets.slint";

struct TodoItem { id: int, text: string, done: bool }

export component TodoWindow inherits Window {
    preferred-width: 460px;
    preferred-height: 420px;

    in property <[TodoItem]> todos;
    in-out property <string> input;
    callback add();
    callback toggle(int);
    callback remove(int);

    VerticalBox {
        Text { text: "待办事项"; font-size: 22px; }
        HorizontalBox {
            LineEdit {
                placeholder-text: "要做点什么？";
                text <=> root.input;                 // 双向绑定
                accepted => { root.add(); }          // 回车提交
            }
            Button { text: "添加"; clicked => { root.add(); } }
        }
        ListView {
            for item in root.todos: HorizontalBox {
                CheckBox { checked: item.done; toggled => { root.toggle(item.id); } }
                Text { text: item.text; horizontal-stretch: 1; }
                Button { text: "删除"; clicked => { root.remove(item.id); } }
            }
        }
    }
}''')
    A("```")
    A("")
    A("`src/main.rs`（逻辑）：")
    A("")
    A("```rust")
    A(r'''slint::include_modules!();
use slint::{Model, VecModel};
use std::rc::Rc;

fn main() -> Result<(), slint::PlatformError> {
    let ui = TodoWindow::new()?;
    let todos = Rc::new(VecModel::<TodoItem>::default());
    ui.set_todos(todos.clone().into());
    let mut next_id = 0;

    // 添加
    let weak = ui.as_weak();
    let model = todos.clone();
    ui.on_add(move || {
        let ui = weak.upgrade().unwrap();
        let text = ui.get_input();
        if !text.trim().is_empty() {
            model.push(TodoItem { id: next_id, text: text.trim().into(), done: false });
            next_id += 1;
            ui.set_input(Default::default());
        }
    });

    // 勾选
    let model = todos.clone();
    ui.on_toggle(move |id| {
        for i in 0..model.row_count() {
            let mut it = model.row_data(i).unwrap();
            if it.id == id { it.done = !it.done; model.set_row_data(i, it); break; }
        }
    });

    // 删除
    let model = todos.clone();
    ui.on_remove(move |id| {
        for i in 0..model.row_count() {
            if model.row_data(i).unwrap().id == id { model.remove(i); break; }
        }
    });

    ui.run()
}''')
    A("```")
    A("")
    A("这段覆盖了：**属性 + 双向绑定、callback 声明与 `on_*` 处理、Weak 句柄、VecModel 增删改、`for…in` 列表**——就是图 8 那个界面。UI 全在 `.slint`、逻辑全在 Rust，物理分离。")
    A("")
    # 十四
    A(f"## {SEC[13]}")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 回调捕获强引用 `ui` | 内存泄漏（组件不释放） | 用 `ui.as_weak()` + `upgrade()`（Slint 头号坑） |")
    A("| 把 `Rc<VecModel>` move 进线程 | 编译报错「不是 Send」 | 送 `Weak`，`upgrade_in_event_loop` 里改模型 |")
    A("| 忘了 `build.rs` / `include_modules!` | 找不到 `AppWindow` | 两者配套：build 编译 .slint，include 拉进来 |")
    A("| 属性方向选错 | Rust 没有 `set_x` / `get_x` | 要 Rust 写用 `in`/`in-out`，要读用 `out`/`in-out` |")
    A("| 事件循环不在主线程 | 崩溃 / 卡住 | `ui.run()` 与组件创建都在主线程 |")
    A("| 以为免费随便用 | 闭源嵌入式发货侵权 | 该场景需商业许可或 GPL（第 12 节） |")
    A("| DSL 里 `-` 和 `_` 混用困惑 | 其实等价 | 生成到 Rust 统一 `_`（`on_request_x`） |")
    A("| 只改 Rust 期待热更 UI | UI 没变 | UI 改在 .slint 才有 live-preview；逻辑改要重编 |")
    A("")
    # 十五
    A(f"## {SEC[14]}")
    A("")
    A("对照本工作区（元数据驱动企业平台，前端以 Web 资产为主）：")
    A("")
    A("1. **Slint 在本仓当下无强对口场景**。横评（`docs/20260920_Rust桌面GUI框架横评.md`）结论：本仓**无嵌入式诉求**，Slint 的杀手锏（下沉 MCU）用不上；面向用户的桌面产品首选 **Tauri 2**（复用 `frontend/` 资产），内部诊断面板选 **egui**。Slint 的 DSL 设计协作、类 Qt 工作流，与 CMX 当前以 Web 为主的形态不重叠。")
    A("2. **它的独家价值在「设备端」**：如果 CMX 未来延伸出**工控终端、车间专用设备、仪器面板**这类**嵌入式 UI**，Slint 是**唯一**能从桌面下沉到 MCU 的选项——届时它没有竞品。")
    A("3. **双主题纪律一致**：Slint 从 `Palette` 派生颜色、随 style 切明暗，正是 CMX 硬约束 #4 在 DSL 框架里的等价表达（第 9 节）。")
    A("4. **许可要留意**：企业内部/桌面走免版税免费；只有「闭源 + 设备发货」才需商业许可——若真做设备端产品，这笔账要提前算（第 12 节）。")
    A("")
    A("> 与本系列的分工：**iced=可演进的自绘桌面产品；egui=最快出活的内部工具；Dioxus=前端背景全 Rust 多端（WebView）；Slint=设计协作 + 嵌入式下沉（唯一到 MCU）**。五者主场清晰，Slint 在 CMX 语境下是「未来若做设备端 UI」的唯一候选。")
    A("")
    # 十六
    A(f"## {SEC[15]}")
    A("")
    A("**版本基线（2026-09）**：Slint **1.17.x**。1.x 遵循语义化版本、迭代克制，是本系列里**稳定性承诺最强**的之一（对比 iced/Dioxus 的 0.x 破坏性变更）。背后是商业公司 **SixtyFPS GmbH**，有付费支持。")
    A("")
    A("| 资源 | 地址 | 说明 |")
    A("|---|---|---|")
    A("| 官网 & 文档 | slint.dev · docs.slint.dev | 教程 + `.slint` 语言参考 + Rust API |")
    A("| API 文档 | docs.rs/slint | **锁定你的版本看** |")
    A("| 在线试玩 | slintpad.com | 浏览器里写 `.slint` 即时预览 |")
    A("| 源码 & 示例 | github.com/slint-ui/slint（`examples/`、`demos/`） | 桌面 + MCU 板级示例都有 |")
    A("| 许可说明 | slint.dev（licensing） | 三许可细则，选型必读 |")
    A("| 工具 | VS Code 扩展「Slint」 | live-preview 即改即见 |")
    A("")
    A("> 学习路径建议：装 VS Code 「Slint」扩展、打开官方 `examples/`，**边改 `.slint` 边看 live-preview**——这是 Slint 最高效的学法（所见即所写）。逻辑侧照本文各节对 Rust API。遇到 API 对不上，认准你锁定版本的 docs.rs。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **Slint = 现代 Qt 的 Rust 答卷**：声明式 `.slint` DSL 编译期生成、设计与逻辑物理分离、live-preview 即改即见、多渲染器，且**唯一能 no_std 下沉到单片机**。给「有设计协作、有嵌入式野心、要类 Qt 工作流」的团队；代价是学一门 DSL、许可三选一有决策成本。桌面/Web 免费可商用，只有闭源硬件发货才付费——想清楚你要不要那份「从桌面一直下沉到 MCU」的能力。")
    A("")
    A("> 参考：slint.dev、docs.slint.dev 与 docs.rs/slint、github.com/slint-ui/slint（examples）、slintpad.com。版本以 2026-09 的 1.17.x 线为准；凡涉及具体 API，请以你锁定版本的 docs.rs / 语言参考为准，勿跨版本照抄。")

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
