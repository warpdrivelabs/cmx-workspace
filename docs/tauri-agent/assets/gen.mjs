// gen.mjs — 「为什么 Tauri 是构建智能体(Agent)的最佳选择」全部配图。
// 自包含浅色卡片 SVG，CVD-安全调色板，复用 onto-topology/gen.mjs 的 helper 风格。
// 用法: node assets/gen.mjs → 写出 fig-*.svg
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const DIR = dirname(fileURLToPath(import.meta.url))

const P = {
  surface: '#fcfcfb', plane: '#f4f4f1', ink: '#0b0b0b', ink2: '#52514e', muted: '#898781',
  grid: '#e1e0d9', base: '#c3c2b7', border: 'rgba(11,11,11,0.12)',
  rust: '#c65a2e', blue: '#2a78d6', aqua: '#1baf7a', yellow: '#eda100',
  violet: '#6446c8', magenta: '#e87ba4', green: '#008300', red: '#e34948',
  good: '#0ca30c', warning: '#fab219', critical: '#d03b3b',
}
// 主色语义：Rust 内核=rust(锈橙) · Webview UI=blue · 本地/工具=aqua · 安全=violet
const FONT = "system-ui,-apple-system,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
const MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const wOf = (s, per = 11) => [...String(s)].reduce((a, c) => a + (/[\x00-\xff]/.test(c) ? per * 0.58 : per), 0)
const T = (x, y, s, o = {}) => {
  const { size = 13, w = 400, fill = P.ink, anchor = 'start', op = 1, mono = false } = o
  return `<text x="${x}" y="${y}" font-family="${mono ? MONO : FONT}" font-size="${size}" font-weight="${w}" fill="${fill}" text-anchor="${anchor}" opacity="${op}">${esc(s)}</text>`
}
const R = (x, y, w, h, o = {}) => {
  const { rx = 10, fill = 'none', stroke = 'none', sw = 1, fop = 1, sop = 1, dash = '' } = o
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" fill-opacity="${fop}" stroke="${stroke}" stroke-opacity="${sop}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`
}
const LINE = (x1, y1, x2, y2, o = {}) => {
  const { stroke = P.muted, sw = 1.5, dash = '', marker = true, mk = 'arr' } = o
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}${marker ? ` marker-end="url(#${mk})"` : ''}/>`
}
const PATH = (d, o = {}) => {
  const { stroke = P.muted, sw = 1.5, dash = '', marker = true, fill = 'none', mk = 'arr' } = o
  return `<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}${marker ? ` marker-end="url(#${mk})"` : ''}/>`
}
const card = (w, h) => R(0, 0, w, h, { rx: 16, fill: P.surface, stroke: P.border, sw: 1 })
const defs = `<defs>
  <marker id="arr" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6 Z" fill="${P.muted}"/></marker>
  <marker id="arrR" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.rust}"/></marker>
  <marker id="arrB" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.blue}"/></marker>
  <marker id="arrA" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.aqua}"/></marker>
  <marker id="arrV" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.violet}"/></marker>
</defs>`
const doc = (w, h, body) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img">${defs}${card(w, h)}${body}</svg>`
const titleBlk = (w, s, sub) => T(w / 2, 34, s, { size: 19, w: 800, anchor: 'middle' }) + (sub ? T(w / 2, 55, sub, { size: 12.5, fill: P.ink2, anchor: 'middle' }) : '')
const band = (x, y, w, h, hue, title, sub, loc) => {
  let s = R(x, y, w, h, { rx: 10, fill: hue, fop: 0.10, stroke: hue, sop: 0.32, sw: 1 })
  s += R(x, y, 4, h, { rx: 2, fill: hue })
  s += T(x + 18, y + (sub ? h / 2 - 4 : h / 2 + 5), title, { size: 14.5, w: 700 })
  if (sub) s += T(x + 18, y + h / 2 + 15, sub, { size: 11.5, fill: P.ink2 })
  if (loc) s += T(x + w - 14, y + h / 2 + 5, loc, { size: 11.5, fill: hue, anchor: 'end', mono: true })
  return s
}
const cell = (x, y, w, h, hue, title, sub) => {
  let s = R(x, y, w, h, { rx: 9, fill: hue, fop: 0.10, stroke: hue, sop: 0.30, sw: 1 })
  s += R(x, y, 4, h, { rx: 2, fill: hue })
  s += T(x + w / 2 + 2, y + (sub ? h / 2 - 2 : h / 2 + 4), title, { size: 12, w: 700, anchor: 'middle' })
  if (sub) s += T(x + w / 2 + 2, y + h / 2 + 13, sub, { size: 9.5, fill: P.ink2, anchor: 'middle' })
  return s
}
const chip = (x, y, label, hue, o = {}) => {
  const { size = 11, pad = 11, h = 22 } = o
  const w = Math.round(wOf(label, size) + pad * 2)
  let s = R(x, y, w, h, { rx: h / 2, fill: hue, fop: 0.13, stroke: hue, sop: 0.34, sw: 1 })
  s += `<circle cx="${x + pad - 2}" cy="${y + h / 2}" r="3" fill="${hue}"/>`
  s += T(x + pad + 5, y + h / 2 + 4, label, { size, fill: P.ink })
  return { svg: s, w }
}
const ST = { ok: P.good, warn: P.warning, no: P.red, dim: P.muted }
const GLY = { ok: '✓', warn: '!', no: '✕', dim: '–' }
const statusCell = (x, y, w, st, txt) => {
  const hue = ST[st], h = 24
  let s = R(x, y, w, h, { rx: 7, fill: hue, fop: st === 'dim' ? 0.07 : 0.13, stroke: hue, sop: st === 'dim' ? 0.3 : 0.36, sw: 1 })
  s += `<circle cx="${x + 13}" cy="${y + h / 2}" r="7.5" fill="${hue}"/>`
  s += T(x + 13, y + h / 2 + 4, GLY[st], { size: 10.5, w: 800, anchor: 'middle', fill: '#fff' })
  s += T(x + 27, y + h / 2 + 4.5, txt, { size: 11, fill: st === 'dim' ? P.ink2 : P.ink })
  return s
}
const disc = (cx, cy, r, hue, label, sub) => {
  let s = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${hue}" fill-opacity="0.12" stroke="${hue}" stroke-opacity="0.55" stroke-width="1.5"/>`
  s += T(cx, cy - (sub ? 2 : -5), label, { size: 12.5, w: 800, anchor: 'middle', fill: hue })
  if (sub) s += T(cx, cy + 14, sub, { size: 10, anchor: 'middle', fill: P.ink2 })
  return s
}

// ════════ 图1 · 封面：智能体外壳三层 ════════
function figHero () {
  const W = 980, H = 468
  let b = titleBlk(W, 'Tauri = 智能体的理想外壳', 'Rust 内核(神经与手) + 系统 Webview(脸) + 原生 OS 触达(行动力) —— 一体三面')
  const x = 40, w = W - 80, y0 = 82
  // 三层横带
  const layers = [
    [P.blue, 'Webview UI 层 · 脸', 'HTML/CSS/JS/任意前端框架 —— 对话/审批/可视化，Web 生态即拿即用', 68],
    [P.rust, 'Rust 内核层 · 神经系统 + 大脑干', 'Agent 循环 · 工具执行器 · LLM 客户端 · tokio 异步 · 内存安全 · 权限闸门', 92],
    [P.aqua, '原生 OS 层 · 手与感官', '文件系统 · Shell · 系统托盘 · 全局热键 · 通知 · Sidecar 本地模型 · MCP', 68],
  ]
  let y = y0
  const hue2 = [P.blue, P.rust, P.aqua]
  layers.forEach(([hue, t, d, h], i) => {
    b += R(x, y, w, h, { rx: 12, fill: hue, fop: i === 1 ? 0.12 : 0.08, stroke: hue, sop: i === 1 ? 0.5 : 0.34, sw: i === 1 ? 1.8 : 1.1 })
    b += R(x, y, 5, h, { rx: 2, fill: hue })
    b += T(x + 20, y + 27, t, { size: 14.5, w: 800, fill: hue })
    b += T(x + 20, y + 48, d, { size: 11.5, fill: P.ink2 })
    if (i === 1) {
      // 内核里塞几个能力 chip
      let cx2 = x + 20, cy2 = y + 62
      for (const c of ['perceive→plan→act', 'tool exec', 'stream tokens', 'HITL 审批']) { const ch = chip(cx2, cy2, c, P.rust, { size: 9.5, h: 19 }); b += ch.svg; cx2 += ch.w + 7 }
    }
    // 层间 IPC 双箭头
    if (i < 2) { const my = y + h + 9; b += LINE(W / 2 - 60, my, W / 2 - 60, my + 0.1, { marker: false }); b += `<text x="${W / 2}" y="${my + 4}" font-family="${MONO}" font-size="10.5" fill="${P.muted}" text-anchor="middle">▲ IPC 命令 / 事件 ▼</text>` }
    y += h + 22
  })
  return doc(W, H, b)
}

// ════════ 图2 · Tauri vs Electron vs Web vs 原生 对比矩阵 ════════
function figCompare () {
  const dims = [
    ['本地工具执行(shell/fs/进程)', 'ok', 'warn', 'no', 'ok', 'Agent 要"动手"——原生执行是刚需'],
    ['安全权限边界(能力/沙箱)', 'ok', 'warn', 'warn', 'no', '危险动作要能授权+隔离(HITL)'],
    ['安装包体积', 'ok', 'no', 'ok', 'warn', 'Tauri ~5-10MB / Electron ~150MB'],
    ['内存占用', 'ok', 'no', 'ok', 'warn', '省内存 → 与本地模型共存'],
    ['本地推理(candle/llama.cpp)', 'ok', 'no', 'no', 'warn', 'Rust 原生跑模型 / Sidecar'],
    ['异步长任务(Agent 循环)', 'ok', 'warn', 'no', 'warn', 'tokio 并发 · 流式回传'],
    ['前端生态 / UI 迭代速度', 'ok', 'ok', 'ok', 'no', 'Web 技术栈 · 任意框架'],
    ['跨平台(桌面+移动)', 'ok', 'warn', 'warn', 'warn', 'v2: Win/mac/Linux + iOS/Android'],
  ]
  const cols = ['Tauri(Rust)', 'Electron(Node)', '纯 Web/PWA', '原生(Qt/Swift)']
  const colHue = [P.rust, P.blue, P.aqua, P.muted]
  const W = 980, rowH = 34, top = 100, c0 = 40, cLabelW = 268, colW = 148, gap = 10
  const H = top + dims.length * rowH + 24
  let b = titleBlk(W, '智能体工作负载 · 四栈对比', '✓ 强   ! 一般   ✕ 弱')
  const cx = (i) => c0 + cLabelW + gap + i * (colW + gap)
  for (let i = 0; i < 4; i++) { b += R(cx(i), top - 32, colW, 26, { rx: 7, fill: colHue[i], fop: i === 0 ? 0.16 : 0.1, stroke: colHue[i], sop: i === 0 ? 0.5 : 0.32, sw: i === 0 ? 1.6 : 1 }); b += T(cx(i) + colW / 2, top - 14, cols[i], { size: 11, w: 700, anchor: 'middle', fill: colHue[i] }) }
  dims.forEach((d, r) => {
    const y = top + r * rowH
    if (r % 2 === 0) b += R(c0, y, W - 80, rowH - 6, { rx: 6, fill: P.plane, fop: 0.7 })
    b += T(c0 + 12, y + 16, d[0], { size: 12, w: 600 })
    b += T(c0 + 12, y + 29, d[5], { size: 9, fill: P.muted })
    for (let i = 0; i < 4; i++) {
      const st = d[i + 1], word = ({ ok: '强', warn: '一般', no: '弱' })[st]
      b += statusCell(cx(i), y + (rowH - 6) / 2 - 12, colW, st, '')
      b += T(cx(i) + colW / 2 + 8, y + 18, word, { size: 11, w: 700, anchor: 'middle', fill: ST[st] })
    }
  })
  return doc(W, H, b)
}

// ════════ 图3 · 智能体应用解剖 ════════
function figAnatomy () {
  const W = 980, H = 520
  let b = titleBlk(W, '一个 Tauri 智能体应用的解剖', 'Webview 前端 ⇄ IPC ⇄ Rust 内核 ⇄ {本地模型 · 远程 API · MCP · OS 工具}')
  // 顶：Webview
  const x = 40, w = W - 80
  b += R(x, 76, w, 66, { rx: 12, fill: P.blue, fop: 0.08, stroke: P.blue, sop: 0.34, sw: 1.1 })
  b += R(x, 76, 5, 66, { rx: 2, fill: P.blue })
  b += T(x + 20, 100, 'Webview 前端  (WebView2 / WKWebView / WebKitGTK)', { size: 13.5, w: 800, fill: P.blue })
  b += T(x + 20, 120, '对话流 UI · 工具调用审批卡 · Trace 时间线 · 设置。任意前端框架，热更新迭代快。', { size: 11, fill: P.ink2 })
  // IPC 桥
  b += LINE(W / 2, 142, W / 2, 168, { mk: 'arrB', sw: 1.6 })
  b += R(W / 2 - 90, 150, 180, 22, { rx: 11, fill: P.surface, stroke: P.ink2, sop: 0.3, sw: 1 })
  b += T(W / 2, 165, 'IPC:  invoke / emit·listen', { size: 10.5, anchor: 'middle', fill: P.ink2, mono: true })
  b += LINE(W / 2, 172, W / 2, 190, { mk: 'arr', sw: 1.6, stroke: P.rust })
  // 中：Rust 内核（大盒，内含子模块）
  const ky = 190, kh = 150
  b += R(x, ky, w, kh, { rx: 12, fill: P.rust, fop: 0.09, stroke: P.rust, sop: 0.5, sw: 1.8 })
  b += R(x, ky, 5, kh, { rx: 2, fill: P.rust })
  b += T(x + 20, ky + 26, 'Rust 内核  ·  core process（可信、无沙箱、掌管一切）', { size: 14, w: 800, fill: P.rust })
  const mods = [
    ['Agent 循环', 'perceive→plan→act→observe', P.rust],
    ['工具执行器', 'shell·fs·http·code', P.aqua],
    ['LLM 客户端', 'stream / 重试 / 预算', P.violet],
    ['权限闸门', '能力校验 · HITL', P.violet],
    ['状态 / 记忆', 'sqlite · 向量 · KV', P.blue],
  ]
  const mw = (w - 40 - 4 * 12) / 5
  mods.forEach(([t, s, hue], i) => {
    const mx = x + 20 + i * (mw + 12)
    b += R(mx, ky + 40, mw, 88, { rx: 9, fill: hue, fop: 0.1, stroke: hue, sop: 0.36, sw: 1 })
    b += T(mx + mw / 2, ky + 66, t, { size: 11.5, w: 700, anchor: 'middle', fill: hue })
    // 子说明换行
    const words = s.split(/[ ·]/).filter(Boolean); let ly = ky + 84
    words.forEach((wd, k) => { if (k < 4) b += T(mx + mw / 2, ly + k * 12, wd, { size: 8.8, anchor: 'middle', fill: P.ink2 }) })
  })
  // 底：外部资源
  const by = ky + kh + 24
  b += T(x + 4, by - 6, '内核向下触达 ↓', { size: 10.5, fill: P.muted })
  const ext = [
    ['本地模型', 'candle / llama.cpp\nort(ONNX) / Sidecar', P.aqua],
    ['远程 LLM API', 'reqwest 流式\nOpenAI/Claude/…', P.violet],
    ['MCP 工具服务器', 'stdio / SSE\n标准工具协议', P.blue],
    ['操作系统', '文件·Shell·托盘\n热键·通知·剪贴板', P.rust],
  ]
  const ew = (w - 3 * 14) / 4
  ext.forEach(([t, s, hue], i) => {
    const ex = x + i * (ew + 14)
    b += R(ex, by, ew, 70, { rx: 10, fill: hue, fop: 0.08, stroke: hue, sop: 0.34, sw: 1 })
    b += T(ex + ew / 2, by + 24, t, { size: 12, w: 700, anchor: 'middle', fill: hue })
    s.split('\n').forEach((ln, k) => b += T(ex + ew / 2, by + 42 + k * 13, ln, { size: 9.3, anchor: 'middle', fill: P.ink2 }))
    b += LINE(ex + ew / 2, ky + kh, ex + ew / 2, by, { stroke: hue, sw: 1.2, mk: hue === P.rust ? 'arrR' : hue === P.aqua ? 'arrA' : hue === P.violet ? 'arrV' : 'arrB' })
  })
  return doc(W, H, b)
}

// ════════ 图4 · 能力/权限安全模型（HITL）════════
function figSecurity () {
  const W = 940, H = 430
  let b = titleBlk(W, '为什么智能体尤其需要 Tauri 的权限模型', '智能体会"自主执行动作"——危险 → 必须有能力边界 + 人在环审批(HITL)')
  // 左：LLM 想调用的工具（不可信意图）
  const lx = 60, ly = 96
  b += R(lx, ly, 240, 130, { rx: 12, fill: P.violet, fop: 0.08, stroke: P.violet, sop: 0.34, sw: 1 })
  b += T(lx + 120, ly + 26, 'LLM 决策(不可信意图)', { size: 12.5, w: 700, anchor: 'middle', fill: P.violet })
  const calls = ['run("rm -rf /tmp/x")', 'fs.write(cfg)', 'http.post(api)']
  calls.forEach((c, i) => { b += R(lx + 16, ly + 42 + i * 28, 208, 22, { rx: 6, fill: P.surface, stroke: P.violet, sop: 0.25, sw: 1 }); b += T(lx + 24, ly + 57 + i * 28, c, { size: 10, fill: P.ink2, mono: true }) })
  // 中：能力闸门
  const gx = 370, gw = 200
  b += R(gx, ly - 4, gw, 200, { rx: 12, fill: P.rust, fop: 0.1, stroke: P.rust, sop: 0.5, sw: 1.8 })
  b += T(gx + gw / 2, ly + 22, '能力闸门', { size: 14, w: 800, anchor: 'middle', fill: P.rust })
  b += T(gx + gw / 2, ly + 40, 'Capabilities · Isolation', { size: 9.5, anchor: 'middle', fill: P.ink2, mono: true })
  const gates = [['允许清单(allowlist)', 'ok'], ['作用域 scope 限定', 'ok'], ['CSP + 隔离模式', 'ok'], ['危险动作→人工确认', 'warn']]
  gates.forEach(([t, st], i) => { b += statusCell(gx + 14, ly + 54 + i * 30, gw - 28, st, t) })
  b += LINE(lx + 240, ly + 65, gx, ly + 65, { stroke: P.violet, sw: 1.5, mk: 'arrV' })
  // 右：执行 or 拒绝 or 审批
  const rx = 660, rw = W - rx - 40
  b += R(rx, ly, rw, 58, { rx: 10, fill: P.good, fop: 0.1, stroke: P.good, sop: 0.4, sw: 1 })
  b += T(rx + rw / 2, ly + 25, '✓ 授权 → 执行', { size: 12, w: 700, anchor: 'middle', fill: P.good })
  b += T(rx + rw / 2, ly + 43, 'Rust 原生安全执行', { size: 9.5, anchor: 'middle', fill: P.ink2 })
  b += R(rx, ly + 70, rw, 58, { rx: 10, fill: P.warning, fop: 0.12, stroke: P.warning, sop: 0.44, sw: 1 })
  b += T(rx + rw / 2, ly + 95, '⏸ 高危 → HITL 审批卡', { size: 12, w: 700, anchor: 'middle', fill: '#9a6a00' })
  b += T(rx + rw / 2, ly + 113, 'Webview 弹确认，用户点批准', { size: 9.5, anchor: 'middle', fill: P.ink2 })
  b += R(rx, ly + 140, rw, 52, { rx: 10, fill: P.red, fop: 0.1, stroke: P.red, sop: 0.4, sw: 1 })
  b += T(rx + rw / 2, ly + 165, '✕ 越权 → 拒绝', { size: 12, w: 700, anchor: 'middle', fill: P.red })
  b += T(rx + rw / 2, ly + 182, '不在能力范围，编译期/运行期拦', { size: 9.3, anchor: 'middle', fill: P.ink2 })
  b += LINE(gx + gw, ly + 40, rx, ly + 28, { stroke: P.good, sw: 1.4, mk: 'arr' })
  b += LINE(gx + gw, ly + 96, rx, ly + 96, { stroke: P.warning, sw: 1.4, mk: 'arr' })
  b += LINE(gx + gw, ly + 150, rx, ly + 165, { stroke: P.red, sw: 1.4, mk: 'arr' })
  b += T(W / 2, H - 20, 'Web/Electron 默认无此边界——给自主 Agent 开"裸执行"权限风险极高；Tauri 把它做进了框架', { size: 10.5, anchor: 'middle', fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图5 · Agent 循环 + 流式回传 ════════
function figLoop () {
  const W = 940, H = 380
  let b = titleBlk(W, 'tokio 异步 Agent 循环 · 流式回传 UI', 'Rust 内核跑长任务循环，逐 token / 逐步进度经事件推给 Webview —— 丝滑聊天 UX')
  const cx = 300, cy = 220, r = 108
  // 四阶段环
  const steps = [['感知 Perceive', -90, P.blue], ['规划 Plan', 0, P.violet], ['行动 Act(工具)', 90, P.aqua], ['观察 Observe', 180, P.rust]]
  steps.forEach(([t, ang, hue]) => {
    const a = ang * Math.PI / 180
    const nx = cx + r * Math.cos(a), ny = cy + r * Math.sin(a)
    b += disc(nx, ny, 44, hue, '', '')
    b += T(nx, ny + 4, t, { size: 11, w: 700, anchor: 'middle', fill: hue })
  })
  // 环箭头
  for (let i = 0; i < 4; i++) {
    const a0 = (steps[i][1] + 22) * Math.PI / 180, a1 = (steps[(i + 1) % 4][1] - 22) * Math.PI / 180
    const rr = r
    const x0 = cx + rr * Math.cos(a0), y0 = cy + rr * Math.sin(a0), x1 = cx + rr * Math.cos(a1), y1 = cy + rr * Math.sin(a1)
    b += PATH(`M${x0},${y0} A${rr},${rr} 0 0 1 ${x1},${y1}`, { stroke: P.muted, sw: 1.6, mk: 'arr' })
  }
  b += T(cx, cy - 2, 'while', { size: 13, w: 800, anchor: 'middle', fill: P.ink })
  b += T(cx, cy + 15, '!done', { size: 11, anchor: 'middle', fill: P.muted, mono: true })
  // 右：流式事件到 UI
  const px = 520, pw = W - px - 40
  b += R(px, 96, pw, 232, { rx: 12, fill: P.blue, fop: 0.06, stroke: P.blue, sop: 0.3, sw: 1 })
  b += T(px + 18, 122, 'emit → Webview 事件流', { size: 12.5, w: 700, fill: P.blue })
  const evs = [
    ['token', '逐字上屏(打字机)', P.violet],
    ['tool:start', '"正在读取文件…"', P.aqua],
    ['tool:progress', '进度条 / 部分结果', P.aqua],
    ['approval:need', '弹审批卡(HITL)', P.warning],
    ['trace', '推理步骤时间线', P.rust],
    ['done', '本轮完成', P.good],
  ]
  evs.forEach(([e, d, hue], i) => {
    const ey = 138 + i * 30
    b += R(px + 18, ey, 128, 22, { rx: 6, fill: hue, fop: 0.14, stroke: hue, sop: 0.34, sw: 1 })
    b += T(px + 26, ey + 15, e, { size: 10, fill: hue, mono: true, w: 700 })
    b += T(px + 158, ey + 15, d, { size: 10.5, fill: P.ink2 })
  })
  b += LINE(cx + 120, cy - 40, px, 150, { stroke: P.blue, sw: 1.4, mk: 'arrB' })
  return doc(W, H, b)
}

// ════════ 图6 · 推理部署三档 ════════
function figInference () {
  const W = 960, H = 340
  let b = titleBlk(W, '推理部署：本地 · 远程 · 混合，任选', 'Rust 一栈通吃三档，Sidecar 监管本地引擎，无需换技术栈')
  const cw = (W - 80 - 2 * 18) / 3, y = 84, h = 200
  const cards = [
    [P.aqua, '本地推理', 'On-device', ['candle (纯 Rust 张量)', 'llama.cpp / mistral.rs', 'ort — ONNX Runtime', 'Sidecar: 打包 ollama'], '隐私 · 离线 · 零 API 费', 'privacy-first'],
    [P.violet, '远程 API', 'Cloud', ['reqwest 流式 SSE', 'OpenAI / Claude / …', '统一重试 · 预算 · 限流', '密钥留在 Rust 侧'], '最强能力 · 免本地算力', 'max-capability'],
    [P.blue, '混合路由', 'Hybrid', ['小任务→本地模型', '难任务→云端大模型', '离线降级 · 成本优化', '一套内核动态切'], '成本/能力/隐私三平衡', 'best-of-both'],
  ]
  cards.forEach(([hue, t, en, items, foot, tag], i) => {
    const x = 40 + i * (cw + 18)
    b += R(x, y, cw, h, { rx: 12, fill: hue, fop: 0.08, stroke: hue, sop: 0.38, sw: i === 2 ? 1.6 : 1.1 })
    b += R(x, y, cw, 40, { rx: 12, fill: hue, fop: 0.15 })
    b += R(x, y + 28, cw, 12, { fill: hue, fop: 0.15 })
    b += T(x + 16, y + 20, t, { size: 13.5, w: 800, fill: hue })
    b += T(x + cw - 14, y + 20, en, { size: 10, anchor: 'end', fill: hue, mono: true })
    items.forEach((it, k) => { b += `<circle cx="${x + 20}" cy="${y + 60 + k * 24}" r="2.5" fill="${hue}"/>`; b += T(x + 30, y + 64 + k * 24, it, { size: 10.5, fill: P.ink }) })
    b += R(x + 12, y + h - 34, cw - 24, 24, { rx: 7, fill: hue, fop: 0.12 })
    b += T(x + cw / 2, y + h - 18, foot, { size: 10, w: 600, anchor: 'middle', fill: P.ink2 })
  })
  return doc(W, H, b)
}

// ════════ 图7 · 体积/内存对比 + 分发 ════════
function figFootprint () {
  const W = 960, H = 360
  let b = titleBlk(W, '轻量足迹 → 与本地模型共存 · 一次构建全平台分发', '省下的内存与磁盘，正好留给本地大模型')
  // 左：条形图 体积
  const bx = 60, by = 100, bw = 360, rowH = 44
  b += T(bx, by - 12, '安装包体积 (约)', { size: 12, w: 700, fill: P.ink })
  const bars = [['Tauri', 8, P.rust], ['原生 Qt', 40, P.muted], ['Electron', 150, P.blue]]
  const maxV = 150, scale = bw / maxV
  bars.forEach(([t, v, hue], i) => {
    const y = by + i * rowH
    b += T(bx, y + 20, t, { size: 11.5, w: 600 })
    b += R(bx + 78, y + 6, Math.max(v * scale, 14), 22, { rx: 6, fill: hue, fop: 0.75 })
    b += T(bx + 78 + Math.max(v * scale, 14) + 8, y + 22, v + ' MB', { size: 11, w: 700, fill: hue, mono: true })
  })
  b += T(bx, by + 3 * rowH + 18, '内存占用同理：Tauri 用系统 Webview，无捆绑 Chromium', { size: 10, fill: P.ink2 })
  b += T(bx, by + 3 * rowH + 34, '→ 更多 RAM 留给 candle/llama.cpp 本地推理', { size: 10, fill: P.aqua, w: 600 })
  // 右：一次构建多平台
  const rx = 500, rw = W - rx - 40
  b += R(rx, 92, rw, 210, { rx: 12, fill: P.aqua, fop: 0.06, stroke: P.aqua, sop: 0.3, sw: 1 })
  b += T(rx + rw / 2, 118, '一套代码 · 全平台分发', { size: 13, w: 800, anchor: 'middle', fill: P.aqua })
  const plats = ['Windows', 'macOS', 'Linux', 'iOS *', 'Android *']
  const pw = (rw - 40 - 2 * 12) / 3
  plats.forEach((pl, i) => {
    const px = rx + 20 + (i % 3) * (pw + 12), py = 138 + Math.floor(i / 3) * 42
    b += R(px, py, pw, 32, { rx: 8, fill: P.aqua, fop: 0.12, stroke: P.aqua, sop: 0.34, sw: 1 })
    b += T(px + pw / 2, py + 21, pl, { size: 11, w: 600, anchor: 'middle', fill: P.ink })
  })
  b += T(rx + rw / 2, 240, '* 移动端 = Tauri v2 能力', { size: 9.5, anchor: 'middle', fill: P.muted })
  b += T(rx + rw / 2, 268, '系统托盘 · 全局热键 · 自更新', { size: 10.5, anchor: 'middle', fill: P.ink2 })
  b += T(rx + rw / 2, 285, '→ 常驻后台的 Agent 天生契合', { size: 10.5, w: 600, anchor: 'middle', fill: P.aqua })
  return doc(W, H, b)
}

// ════════ 图8 · 取舍与何时不选 ════════
function figTradeoffs () {
  const W = 940, H = 300
  let b = titleBlk(W, '诚实的取舍 · 何时不选 Tauri', '强主张也要讲边界——技术选型看场景')
  const colW = (W - 80 - 20) / 2
  // 左：代价
  let x = 40, y = 84
  b += band(x, y, colW, 36, P.warning, '需要权衡的代价', null)
  const cons = [
    'Webview 跨平台有差异(各系统内核不同，需测)',
    '生态/组件不如 Electron 成熟(但在快速追赶)',
    'Rust 学习曲线(换来安全与性能)',
    '重度依赖成熟 npm 桌面库时可能缺对应件',
  ]
  cons.forEach((c, i) => { b += `<circle cx="${x + 14}" cy="${y + 58 + i * 32}" r="3" fill="${P.warning}"/>`; b += T(x + 26, y + 62 + i * 32, c, { size: 11, fill: P.ink }) })
  // 右：何时选别的
  x = 40 + colW + 20
  b += band(x, y, colW, 36, P.muted, '这些场景可选别的', null)
  const alt = [
    '纯云端、无本地动作 → 纯 Web/PWA 足够',
    '团队全 JS、已重度绑定 Node 桌面生态 → Electron',
    '需极致原生 UI 观感、单平台 → 原生(Swift/Qt)',
    '只是个聊天框、不执行工具 → 网页即可',
  ]
  alt.forEach((c, i) => { b += `<circle cx="${x + 14}" cy="${y + 58 + i * 32}" r="3" fill="${P.muted}"/>`; b += T(x + 26, y + 62 + i * 32, c, { size: 11, fill: P.ink }) })
  b += T(W / 2, H - 18, '结论：只要 Agent 需要"在本地安全地动手 + 跑/接模型 + 轻量常驻"，Tauri 就是当下最优解', { size: 11, w: 600, anchor: 'middle', fill: P.rust })
  return doc(W, H, b)
}

const figs = {
  'hero': figHero,
  'compare': figCompare,
  'anatomy': figAnatomy,
  'security': figSecurity,
  'loop': figLoop,
  'inference': figInference,
  'footprint': figFootprint,
  'tradeoffs': figTradeoffs,
}
for (const [name, fn] of Object.entries(figs)) {
  const svg = fn()
  writeFileSync(join(DIR, `fig-${name}.svg`), svg)
  console.log(`fig-${name}.svg  ${(Buffer.byteLength(svg) / 1024).toFixed(1)} KiB`)
}
console.log('done:', Object.keys(figs).length, 'figs')
