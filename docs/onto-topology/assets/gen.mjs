// gen.mjs — 生成「企业本体拓扑架构方案（单一本体 vs 多本体）」的全部图。
// 自包含浅色卡片 SVG，CVD-安全调色板 + 复用 helper（沿用 cognitive-enterprise/gen.mjs 风格）。
// 用法: node assets/gen.mjs → 写出 fig-*.svg
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const DIR = dirname(fileURLToPath(import.meta.url))

const P = {
  surface: '#fcfcfb', plane: '#f4f4f1', ink: '#0b0b0b', ink2: '#52514e', muted: '#898781',
  grid: '#e1e0d9', base: '#c3c2b7', border: 'rgba(11,11,11,0.12)',
  blue: '#2a78d6', orange: '#eb6834', aqua: '#1baf7a', yellow: '#eda100',
  magenta: '#e87ba4', green: '#008300', violet: '#4a3aa7', red: '#e34948',
  good: '#0ca30c', warning: '#fab219', serious: '#ec835a', critical: '#d03b3b',
  blue100: '#cde2fb',
}
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
  <marker id="arrB" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.blue}"/></marker>
  <marker id="arrV" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.violet}"/></marker>
  <marker id="arrA" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.aqua}"/></marker>
  <marker id="arrR" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.red}"/></marker>
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
  s += T(x + w / 2 + 2, y + (sub ? h / 2 - 2 : h / 2 + 4), title, { size: 12.5, w: 700, anchor: 'middle' })
  if (sub) s += T(x + w / 2 + 2, y + h / 2 + 13, sub, { size: 10, fill: P.ink2, anchor: 'middle' })
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
const statusCell = (x, y, label, st, wFixed) => {
  const hue = ST[st], h = 24, w = wFixed || Math.round(wOf(label, 11.5) + 40)
  let s = R(x, y, w, h, { rx: 7, fill: hue, fop: st === 'dim' ? 0.07 : 0.13, stroke: hue, sop: st === 'dim' ? 0.3 : 0.36, sw: 1 })
  s += `<circle cx="${x + 13}" cy="${y + h / 2}" r="7.5" fill="${hue}"/>`
  s += T(x + 13, y + h / 2 + 4, GLY[st], { size: 10.5, w: 800, anchor: 'middle', fill: '#fff' })
  s += T(x + 27, y + h / 2 + 4.5, label, { size: 11.5, fill: st === 'dim' ? P.ink2 : P.ink })
  return { svg: s, w }
}
const disc = (cx, cy, r, hue, label, sub) => {
  let s = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${hue}" fill-opacity="0.12" stroke="${hue}" stroke-opacity="0.55" stroke-width="1.5"/>`
  s += T(cx, cy - (sub ? 2 : -5), label, { size: 12.5, w: 800, anchor: 'middle', fill: hue })
  if (sub) s += T(cx, cy + 14, sub, { size: 10, anchor: 'middle', fill: P.ink2 })
  return s
}
const dot = (cx, cy, r, hue, op = 0.9) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${hue}" fill-opacity="${op}"/>`

// ════════ 图1 · 三种模式对比（Hero）════════
function figThreePatterns () {
  const W = 990, H = 470
  let b = titleBlk(W, '三种本体拓扑模式', '企业系统里"建几个本体"的三条路：大一统 / 孤立多本体 / 联邦式单一本体')
  const pw = (W - 40 - 2 * 22) / 3, y0 = 82, ph = 340
  const px = (i) => 40 + i * (pw + 22)
  // Panel A — 单一大一统
  let ax = px(0)
  b += R(ax, y0, pw, ph, { rx: 12, fill: P.orange, fop: 0.05, stroke: P.orange, sop: 0.28, sw: 1 })
  b += band(ax + 12, y0 + 12, pw - 24, 40, P.orange, '① 单一大一统', 'One Monolith')
  const acx = ax + pw / 2, acy = y0 + 175
  b += `<circle cx="${acx}" cy="${acy}" r="90" fill="${P.orange}" fill-opacity="0.08" stroke="${P.orange}" stroke-opacity="0.5" stroke-width="1.5"/>`
  // 塞满小点（拥挤）
  const seed = [[- 55, -30], [-30, -55], [0, -62], [30, -52], [55, -28], [-62, 5], [-40, 30], [-10, 45], [22, 42], [50, 22], [62, -2], [-20, -20], [15, -15], [0, 10], [35, 5], [-35, -2], [10, 25], [-15, 60], [45, 55], [-50, 48]]
  for (const [dx, dy] of seed) b += dot(acx + dx, acy + dy, 7, P.orange, 0.5)
  b += T(acx, y0 + ph - 74, '所有实体挤进一个无边界模型', { size: 11, fill: P.ink2, anchor: 'middle' })
  let ay = y0 + ph - 58
  for (const [lab, st] of [['语义天然一致', 'ok'], ['演进僵化·人人可改', 'no'], ['大图性能差', 'no']]) { const c = statusCell(ax + 16, ay, lab, st, pw - 32); b += c.svg; ay += 30 }
  // Panel B — 孤立多本体
  let bx = px(1)
  b += R(bx, y0, pw, ph, { rx: 12, fill: P.red, fop: 0.05, stroke: P.red, sop: 0.28, sw: 1 })
  b += band(bx + 12, y0 + 12, pw - 24, 40, P.red, '② 孤立多本体', 'Fragmented Silos')
  const bcy = y0 + 130
  const silos = [[bx + pw / 2 - 78, bcy, '财务'], [bx + pw / 2 + 6, bcy - 22, 'CRM'], [bx + pw / 2 - 34, bcy + 58, '物流']]
  for (const [cx, cy, nm] of silos) { b += disc(cx + 34, cy, 32, P.red, nm, 'Customer') }
  // 断裂的连线
  b += LINE(bx + pw / 2 - 44, bcy, bx + pw / 2 + 12, bcy - 22, { stroke: P.red, dash: '3 4', marker: false, sw: 1.4 })
  b += T(bx + pw / 2 - 6, bcy - 4, '✕', { size: 16, w: 800, anchor: 'middle', fill: P.red })
  b += T(bx + pw / 2, y0 + ph - 74, '"Customer"在各域含义不同、无法 join', { size: 10.5, fill: P.ink2, anchor: 'middle' })
  let by = y0 + ph - 58
  for (const [lab, st] of [['领域自治·各自演进', 'ok'], ['语义割裂·主数据重复', 'no'], ['无法跨域连接分析', 'no']]) { const c = statusCell(bx + 16, by, lab, st, pw - 32); b += c.svg; by += 30 }
  // Panel C — 联邦式单一本体（推荐）
  let cx = px(2)
  b += R(cx, y0, pw, ph, { rx: 12, fill: P.violet, fop: 0.06, stroke: P.violet, sop: 0.42, sw: 1.6 })
  b += band(cx + 12, y0 + 12, pw - 24, 40, P.violet, '③ 联邦式单一本体', 'Federated Single', '推荐')
  const ccx = cx + pw / 2, ccy = y0 + 150
  // 核心 hub + 领域 spoke
  const spokes = [[-70, -46, '财务'], [72, -46, '销售'], [-84, 34, 'HR'], [84, 34, '供应链'], [0, 78, '生产']]
  for (const [dx, dy] of spokes) b += LINE(ccx, ccy, ccx + dx, ccy + dy, { stroke: P.violet, sw: 1.4, marker: false, dash: '' })
  for (const [dx, dy, nm] of spokes) b += disc(ccx + dx, ccy + dy, 26, P.blue, nm)
  b += `<circle cx="${ccx}" cy="${ccy}" r="34" fill="${P.violet}" fill-opacity="0.16" stroke="${P.violet}" stroke-opacity="0.7" stroke-width="2"/>`
  b += T(ccx, ccy - 2, '核心域', { size: 12, w: 800, anchor: 'middle', fill: P.violet })
  b += T(ccx, ccy + 13, '共享主数据', { size: 9, anchor: 'middle', fill: P.ink2 })
  let cy2 = y0 + ph - 58
  for (const [lab, st] of [['统一语义·可跨域连接', 'ok'], ['领域自治·分区治理', 'ok'], ['核心只定义一次', 'ok']]) { const c = statusCell(cx + 16, cy2, lab, st, pw - 32); b += c.svg; cy2 += 30 }
  return doc(W, H, b)
}

// ════════ 图2 · 多维对比矩阵 ════════
function figComparison () {
  const dims = [
    ['语义一致 / 可连接', 'no', 'no', 'ok', '一个"客户"的唯一含义，跨域可 join'],
    ['主数据唯一', 'warn', 'no', 'ok', '共享实体只定义一次，不重复'],
    ['领域自治 / 并行开发', 'no', 'ok', 'ok', '各领域团队独立建模、发布'],
    ['性能与规模', 'no', 'ok', 'ok', '大图/大查询是否可分区加载'],
    ['治理 / 权限边界', 'warn', 'warn', 'ok', '按域授权、变更影响可控'],
    ['演进 / 重构成本', 'no', 'warn', 'ok', '改一处不牵动全局'],
  ]
  const W = 940, rowH = 34, top = 96, H = top + dims.length * rowH + 30
  let b = titleBlk(W, '三种模式 · 六维对比', '✓ 强   ! 一般   ✕ 弱')
  const c0 = 40, cLabelW = 300, colW = 150, gap = 12
  const cols = ['① 大一统', '② 孤立多本体', '③ 联邦式(推荐)']
  const colHue = [P.orange, P.red, P.violet]
  const cx = (i) => c0 + cLabelW + gap + i * (colW + gap)
  // 表头
  for (let i = 0; i < 3; i++) { b += R(cx(i), top - 34, colW, 26, { rx: 7, fill: colHue[i], fop: 0.12, stroke: colHue[i], sop: 0.34, sw: 1 }); b += T(cx(i) + colW / 2, top - 16, cols[i], { size: 11.5, w: 700, anchor: 'middle', fill: colHue[i] }) }
  dims.forEach((d, r) => {
    const y = top + r * rowH
    if (r % 2 === 0) b += R(c0, y, W - 80, rowH - 6, { rx: 6, fill: P.plane, fop: 0.7 })
    b += T(c0 + 12, y + 17, d[0], { size: 12.5, w: 600 })
    b += T(c0 + 12, y + 30, d[4], { size: 9.5, fill: P.muted })
    for (let i = 0; i < 3; i++) { const c = statusCell(cx(i), y + (rowH - 6) / 2 - 12, '', d[i + 1], colW); b += c.svg }
    // 居中 glyph 已由 statusCell 左对齐，覆盖一个居中大字
    for (let i = 0; i < 3; i++) { b += T(cx(i) + colW / 2 + 8, y + 18, ({ ok: '强', warn: '一般', no: '弱' })[d[i + 1]], { size: 11, w: 700, anchor: 'middle', fill: ST[d[i + 1]] }) }
  })
  return doc(W, H, b)
}

// ════════ 图3 · 联邦式分层架构 ════════
function figFederatedArch () {
  const W = 960, H = 560
  let b = titleBlk(W, '联邦式单一本体 · 分层架构', '一个逻辑本体 · 核心共享 + 领域自治 + 应用消费 · 物理可分')
  const x = 40, w = W - 80
  // L1 应用/项目层
  let y = 80
  b += band(x, y, w, 56, P.aqua, '① 应用 / 项目层  Application Scope', '客户360 · 关账工作台 · 风控看板 —— 只组合、不改本体定义（Workshop/OSDK 消费）')
  // 三个应用小卡
  const appY = y + 66
  const apps = ['客户 360', '关账联动', '库存分析', '风控看板']
  const aw = (w - 3 * 12) / 4
  apps.forEach((a, i) => { b += cell(x + i * (aw + 12), appY, aw, 30, P.aqua, a) })
  // L2 领域本体层（bounded contexts）
  y = appY + 46
  b += band(x, y, w, 40, P.blue, '② 领域本体层  Domain Ontologies · 受限上下文', null, 'namespace = DAM')
  const domY = y + 50
  const doms = [['财务域', 'fi'], ['销售域', 'crm'], ['供应链域', 'scm'], ['生产域', 'mfg'], ['人力域', 'hr']]
  const dw = (w - 4 * 12) / 5
  doms.forEach(([nm, code], i) => {
    const dx = x + i * (dw + 12)
    b += R(dx, domY, dw, 74, { rx: 10, fill: P.blue, fop: 0.08, stroke: P.blue, sop: 0.34, sw: 1 })
    b += T(dx + dw / 2, domY + 22, nm, { size: 12.5, w: 700, anchor: 'middle', fill: P.blue })
    b += T(dx + dw / 2, domY + 38, code, { size: 9.5, anchor: 'middle', fill: P.muted, mono: true })
    b += T(dx + dw / 2, domY + 56, '对象·关系·动作', { size: 8.8, anchor: 'middle', fill: P.ink2 })
    // 引用核心（下箭头到 L3）
    b += LINE(dx + dw / 2, domY + 74, dx + dw / 2, domY + 96, { stroke: P.violet, sw: 1.3, mk: 'arrV' })
  })
  // L3 核心域
  y = domY + 98
  b += R(x, y, w, 66, { rx: 10, fill: P.violet, fop: 0.10, stroke: P.violet, sop: 0.5, sw: 1.6 })
  b += R(x, y, 4, 66, { rx: 2, fill: P.violet })
  b += T(x + 18, y + 26, '③ 核心域 / 企业内核  Enterprise Core (Kernel)', { size: 14.5, w: 800, fill: P.violet })
  b += T(x + 18, y + 46, '共享主数据(客户/供应商/商品/组织/员工) · 参照数据(币种/科目/单位) · 共享接口 —— 全局只定义一次，各域引用', { size: 11, fill: P.ink2 })
  const coreEnt = ['客户', '供应商', '商品', '组织', '员工', '币种', '会计科目']
  let ex = x + 18, ey = y + 54
  for (const e of coreEnt) { const c = chip(ex, ey - 12, e, P.violet, { size: 10, h: 20 }); b += c.svg; ex += c.w + 7 }
  // L4 数据集成
  y = y + 78
  b += band(x, y, w, 40, P.yellow, '④ 数据集成层  O3 Funnel', 'ERP/CRM/外部源 → 映射 → 灌入对象实例（隔离区 + 同步）', 'source→object')
  // L5 物理存储
  y = y + 50
  b += band(x, y, w, 40, P.muted, '⑤ 物理存储  Physical', 'db-per-tenant · schema-per-domain —— 逻辑单一、物理可分（性能/隔离/合规）', 'PG')
  return doc(W, H, b)
}

// ════════ 图4 · DAM 命名空间划分 ════════
function figDam () {
  const W = 940, H = 430
  let b = titleBlk(W, 'DAM 三级命名空间 = 本体分区键', 'Domain ▸ Application ▸ Module —— 一套编码同时驱动"分区治理"与"大图分域折叠"')
  const x = 40, y0 = 84
  // 三列：Domain / Application / Module
  const colW = 190, gap = 60
  const cxs = [x + 30, x + 30 + colW + gap, x + 30 + 2 * (colW + gap)]
  const heads = [['Domain 领域', P.violet], ['Application 应用', P.blue], ['Module 模块 = 分区', P.aqua]]
  heads.forEach(([h, hue], i) => { b += R(cxs[i], y0, colW, 30, { rx: 8, fill: hue, fop: 0.12, stroke: hue, sop: 0.34, sw: 1 }); b += T(cxs[i] + colW / 2, y0 + 20, h, { size: 12, w: 700, anchor: 'middle', fill: hue }) })
  // 树：fi → cmxfico → {gl, ar, ap}；scm → wms → {inv, ship}
  const rows = [
    ['fi 财务', ['cmxfico 会计核算'], [['gl 总账', 'ar 应收', 'ap 应付']]],
    ['scm 供应链', ['wms 仓储'], [['inv 库存', 'ship 发运']]],
  ]
  let y = y0 + 48
  const modHue = P.aqua
  rows.forEach(([dom, apps, mods]) => {
    const domY = y
    const domCard = R(cxs[0], y, colW, 44, { rx: 9, fill: P.violet, fop: 0.09, stroke: P.violet, sop: 0.34, sw: 1 })
    b += domCard + T(cxs[0] + colW / 2, y + 27, dom, { size: 12, w: 700, anchor: 'middle', fill: P.violet })
    // application
    const app = apps[0]
    const appY = y
    b += R(cxs[1], appY, colW, 44, { rx: 9, fill: P.blue, fop: 0.09, stroke: P.blue, sop: 0.34, sw: 1 })
    b += T(cxs[1] + colW / 2, appY + 27, app, { size: 12, w: 700, anchor: 'middle', fill: P.blue })
    b += LINE(cxs[0] + colW, y + 22, cxs[1], appY + 22, { stroke: P.violet, sw: 1.2, marker: false })
    // modules
    const ms = mods[0]
    const mh = 34, mgap = 10
    ms.forEach((m, j) => {
      const my = y + j * (mh + mgap)
      b += R(cxs[2], my, colW, mh, { rx: 8, fill: modHue, fop: 0.1, stroke: modHue, sop: 0.36, sw: 1 })
      b += T(cxs[2] + 14, my + 22, m, { size: 11.5, w: 600, anchor: 'start' })
      b += T(cxs[2] + colW - 12, my + 22, '⬡', { size: 12, anchor: 'end', fill: modHue })
      b += LINE(cxs[1] + colW, appY + 22, cxs[2], my + mh / 2, { stroke: P.blue, sw: 1.1, marker: false })
    })
    y += Math.max(60, ms.length * (mh + mgap) + 18)
  })
  b += T(cxs[2] + colW / 2, H - 26, '每个 Module = 一个受限上下文(bounded context) = 图上一个可折叠域盒', { size: 10.5, anchor: 'middle', fill: P.ink2 })
  b += T(cxs[0] + colW / 2, H - 26, '⬡ = 该模块内的对象/关系/动作子图', { size: 10.5, anchor: 'middle', fill: P.muted })
  return doc(W, H, b)
}

// ════════ 图5 · 跨域连接（单一语义、可 join）════════
function figCrossDomain () {
  const W = 940, H = 400
  let b = titleBlk(W, '跨域连接：一个"客户"，处处可 join', '核心实体唯一定义 · 各域对象经共享主键 / 接口指向它 —— 端到端可追溯')
  const cx = W / 2, cy = 235
  // 中心：核心客户
  b += `<circle cx="${cx}" cy="${cy}" r="52" fill="${P.violet}" fill-opacity="0.14" stroke="${P.violet}" stroke-opacity="0.7" stroke-width="2"/>`
  b += T(cx, cy - 6, '客户', { size: 15, w: 800, anchor: 'middle', fill: P.violet })
  b += T(cx, cy + 12, 'Core.Customer', { size: 9.5, anchor: 'middle', fill: P.ink2, mono: true })
  b += T(cx, cy + 26, '#C-1024', { size: 9, anchor: 'middle', fill: P.muted, mono: true })
  // 四周域对象
  const around = [
    [cx - 300, cy - 90, '销售订单', 'crm.Order', 'custId'],
    [cx + 300, cy - 90, '发运单', 'scm.Shipment', 'customer'],
    [cx - 300, cy + 90, '应收发票', 'fi.Invoice', 'partner'],
    [cx + 300, cy + 90, '服务工单', 'svc.Ticket', 'account'],
  ]
  const hue = P.blue
  around.forEach(([ox, oy, nm, api, fk]) => {
    b += R(ox - 88, oy - 26, 176, 54, { rx: 10, fill: hue, fop: 0.09, stroke: hue, sop: 0.36, sw: 1 })
    b += T(ox, oy - 6, nm, { size: 12.5, w: 700, anchor: 'middle', fill: hue })
    b += T(ox, oy + 11, api, { size: 9.5, anchor: 'middle', fill: P.ink2, mono: true })
    // 连到核心，标外键
    const towardX = ox < cx ? ox + 88 : ox - 88
    b += LINE(towardX, oy, cx + (ox < cx ? -52 : 52), cy + (oy < cy ? -30 : 30), { stroke: P.violet, sw: 1.5, mk: 'arrV' })
    const mx = (towardX + cx) / 2, my = (oy + cy) / 2
    b += R(mx - 34, my - 11, 68, 20, { rx: 10, fill: P.surface, stroke: P.violet, sop: 0.3, sw: 1 })
    b += T(mx, my + 3.5, '→ ' + fk, { size: 9.5, anchor: 'middle', fill: P.violet, mono: true })
  })
  b += T(cx, H - 20, 'Search-Around：从任一域对象出发，一跳到达同一个客户，再钻取到其它域 —— 这是"单一本体"的核心价值', { size: 10.5, anchor: 'middle', fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图6 · 选型决策树 ════════
function figDecision () {
  const W = 900, H = 500
  let b = titleBlk(W, '选型决策：放核心 · 建领域 · 只在应用层', '新实体 / 新需求进来时，往哪一层落')
  const box = (x, y, w, h, hue, t, sub) => {
    let s = R(x, y, w, h, { rx: 10, fill: hue, fop: 0.1, stroke: hue, sop: 0.4, sw: 1.3 })
    s += T(x + w / 2, y + (sub ? h / 2 - 3 : h / 2 + 4), t, { size: 12.5, w: 700, anchor: 'middle', fill: hue })
    if (sub) s += T(x + w / 2, y + h / 2 + 13, sub, { size: 9.5, anchor: 'middle', fill: P.ink2 })
    return s
  }
  const dia = (cx, cy, w, h, t) => {
    let s = `<path d="M${cx},${cy - h / 2} L${cx + w / 2},${cy} L${cx},${cy + h / 2} L${cx - w / 2},${cy} Z" fill="${P.yellow}" fill-opacity="0.12" stroke="${P.yellow}" stroke-opacity="0.55" stroke-width="1.3"/>`
    s += T(cx, cy + 4, t, { size: 11.5, w: 700, anchor: 'middle', fill: '#9a6a00' })
    return s
  }
  const lbl = (x, y, t, hue) => T(x, y, t, { size: 10.5, w: 700, fill: hue })
  const cxc = W / 2
  // Start
  b += box(cxc - 90, 74, 180, 40, P.ink2, '新实体 / 新需求')
  b += LINE(cxc, 114, cxc, 138, { marker: true })
  // Q1 被多个领域共享？
  b += dia(cxc, 168, 210, 66, '被 ≥2 个领域共享？')
  // yes -> 核心
  b += LINE(cxc - 105, 168, 210, 168, { marker: false }); b += LINE(210, 168, 210, 210, { mk: 'arrV' })
  b += lbl(cxc - 150, 160, '是', P.violet)
  b += box(120, 212, 180, 56, P.violet, '→ 放核心域', '主数据/参照/共享接口·唯一定义')
  // no -> Q2
  b += LINE(cxc, 201, cxc, 236, { marker: true })
  b += lbl(cxc + 10, 224, '否', P.ink2)
  b += dia(cxc, 288, 230, 66, '是稳定的业务对象/关系？')
  // yes -> 领域
  b += LINE(cxc + 115, 288, W - 130, 288, { marker: false }); b += LINE(W - 130, 288, W - 130, 330, { mk: 'arrB' })
  b += lbl(cxc + 130, 280, '是', P.blue)
  b += box(W - 300 + 90 - 20, 332, 200, 56, P.blue, '→ 建/扩领域本体', '该域 namespace 下建对象类型')
  // no -> 应用层
  b += LINE(cxc, 321, cxc, 356, { marker: true })
  b += lbl(cxc + 10, 344, '否 / 临时', P.ink2)
  b += box(cxc - 120, 358, 240, 56, P.aqua, '→ 只在应用/项目层组合', '用 Workshop/OSDK 组合，不落本体定义')
  // 侧注
  b += T(40, H - 22, '经验法则：能被别人复用的 → 往下沉（核心）；本域专有的 → 领域本体；一次性拼装 → 应用层。宁可先放领域，成熟后再上提核心。', { size: 10.5, fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图7 · 演进路径 ════════
function figRoadmap () {
  const W = 970, H = 300
  let b = titleBlk(W, '落地演进路径', '不要一次建大：先核心 + 一域跑通，再联邦扩张')
  const ph = [
    ['P0 · 核心内核', P.violet, '客户/供应商/商品/组织/员工 + 参照数据；定义共享接口。', '1 个核心 namespace'],
    ['P1 · 首个领域', P.blue, '选高价值域(如财务)建本体，引用核心；O3 灌真实数据；跑通 Search-Around。', 'core + 1 domain'],
    ['P2 · 多域联邦', P.aqua, '横向扩销售/供应链/HR；各域独立发布；跨域链路打通。', 'core + N domains'],
    ['P3 · 治理与联邦查询', P.orange, '分域权限(O6)、版本发布、跨域联邦查询、血缘与影响分析。', 'governance'],
  ]
  const n = ph.length, gap = 16, pw = (W - 80 - (n - 1) * gap) / n, y = 92, hgt = 150
  ph.forEach(([t, hue, d, tag], i) => {
    const px = 40 + i * (pw + gap)
    b += R(px, y, pw, hgt, { rx: 12, fill: hue, fop: 0.08, stroke: hue, sop: 0.36, sw: 1.2 })
    b += R(px, y, pw, 34, { rx: 12, fill: hue, fop: 0.16 })
    b += R(px, y + 22, pw, 12, { fill: hue, fop: 0.16 })
    b += T(px + 14, y + 22, t, { size: 12.5, w: 800, fill: hue })
    // 描述换行
    const words = d
    const lines = []
    let cur = ''
    for (const ch of words) { cur += ch; if (wOf(cur, 10.5) > pw - 28) { lines.push(cur); cur = '' } }
    if (cur) lines.push(cur)
    lines.slice(0, 5).forEach((ln, k) => b += T(px + 14, y + 54 + k * 15, ln, { size: 10.2, fill: P.ink2 }))
    const c = chip(px + 12, y + hgt - 30, tag, hue, { size: 9.5, h: 20 }); b += c.svg
    if (i < n - 1) b += LINE(px + pw + 2, y + hgt / 2, px + pw + gap - 2, y + hgt / 2, { stroke: hue, sw: 1.6, mk: 'arr' })
  })
  return doc(W, H, b)
}

const figs = {
  'three-patterns': figThreePatterns,
  'comparison': figComparison,
  'federated-arch': figFederatedArch,
  'dam-namespace': figDam,
  'cross-domain': figCrossDomain,
  'decision': figDecision,
  'roadmap': figRoadmap,
}
for (const [name, fn] of Object.entries(figs)) {
  const svg = fn()
  writeFileSync(join(DIR, `fig-${name}.svg`), svg)
  console.log(`fig-${name}.svg  ${(Buffer.byteLength(svg) / 1024).toFixed(1)} KiB`)
}
console.log('done:', Object.keys(figs).length, 'figs')
