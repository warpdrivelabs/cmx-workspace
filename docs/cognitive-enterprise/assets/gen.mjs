// gen.mjs — 生成「认知型企业系统新范式（LLM × Agent × Ontology）」报告的全部图。
// 自包含浅色卡片 SVG，CVD-安全调色板 + 复用 helper。
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
  blue100: '#cde2fb', blue550: '#1c5cab',
}
// 三主色：本体=violet(世界模型) · LLM=blue(推理) · Agent=aqua(执行)
const FONT = "system-ui,-apple-system,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const wOf = (s, per = 11) => [...String(s)].reduce((a, c) => a + (/[\x00-\xff]/.test(c) ? per * 0.58 : per), 0)

const T = (x, y, s, o = {}) => {
  const { size = 13, w = 400, fill = P.ink, anchor = 'start', op = 1, mono = false } = o
  return `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${size}" font-weight="${w}" fill="${fill}" text-anchor="${anchor}" opacity="${op}"${mono ? ' font-variant-numeric="tabular-nums"' : ''}>${esc(s)}</text>`
}
const R = (x, y, w, h, o = {}) => {
  const { rx = 10, fill = 'none', stroke = 'none', sw = 1, fop = 1, sop = 1 } = o
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" fill-opacity="${fop}" stroke="${stroke}" stroke-opacity="${sop}" stroke-width="${sw}"/>`
}
const LINE = (x1, y1, x2, y2, o = {}) => {
  const { stroke = P.muted, sw = 1.5, dash = '', marker = true } = o
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}${marker ? ' marker-end="url(#arr)"' : ''}/>`
}
const PATH = (d, o = {}) => {
  const { stroke = P.muted, sw = 1.5, dash = '', marker = true, fill = 'none' } = o
  return `<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}${marker ? ' marker-end="url(#arr)"' : ''}/>`
}
const card = (w, h) => R(0, 0, w, h, { rx: 16, fill: P.surface, stroke: P.border, sw: 1 })
const defs = `<defs>
  <marker id="arr" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6 Z" fill="${P.muted}"/></marker>
  <marker id="arrB" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.blue}"/></marker>
  <marker id="arrV" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.violet}"/></marker>
  <marker id="arrA" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.aqua}"/></marker>
</defs>`
const doc = (w, h, body) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img">${defs}${card(w, h)}${body}</svg>`

const band = (x, y, w, h, hue, title, sub, loc) => {
  let s = R(x, y, w, h, { rx: 10, fill: hue, fop: 0.10, stroke: hue, sop: 0.32, sw: 1 })
  s += R(x, y, 4, h, { rx: 2, fill: hue })
  s += T(x + 18, y + (sub ? h / 2 - 4 : h / 2 + 5), title, { size: 14.5, w: 700 })
  if (sub) s += T(x + 18, y + h / 2 + 15, sub, { size: 11.5, fill: P.ink2 })
  if (loc) s += T(x + w - 14, y + h / 2 + 5, loc, { size: 12, fill: P.muted, anchor: 'end', mono: true })
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
const chipFlow = (x0, y0, maxX, items, hue, o = {}) => {
  const { gap = 7, lh = 28 } = o
  let x = x0, y = y0, out = ''
  for (const it of items) {
    const c = chip(x, y, it, hue, o)
    if (x + c.w > maxX && x > x0) { x = x0; y += lh; }
    const c2 = chip(x, y, it, hue, o)
    out += c2.svg; x += c2.w + gap
  }
  return { svg: out, height: y + lh - y0 }
}
const titleBlk = (w, s, sub) => T(w / 2, 34, s, { size: 19, w: 800, anchor: 'middle' }) +
  (sub ? T(w / 2, 54, sub, { size: 12.5, fill: P.ink2, anchor: 'middle' }) : '')
const ST = { ok: P.good, warn: P.warning, no: P.muted }
const GLY = { ok: '✓', warn: '!', no: '–' }
const statusCell = (x, y, label, st, wFixed) => {
  const hue = ST[st], h = 24, w = wFixed || Math.round(wOf(label, 11.5) + 40)
  let s = R(x, y, w, h, { rx: 7, fill: hue, fop: st === 'no' ? 0.07 : 0.13, stroke: hue, sop: st === 'no' ? 0.3 : 0.36, sw: 1 })
  s += `<circle cx="${x + 13}" cy="${y + h / 2}" r="7.5" fill="${hue}"/>`
  s += T(x + 13, y + h / 2 + 4, GLY[st], { size: 11, w: 800, anchor: 'middle', fill: '#fff' })
  s += T(x + 27, y + h / 2 + 4.5, label, { size: 11.5, fill: st === 'no' ? P.ink2 : P.ink })
  return { svg: s, w }
}
// 圆形节点（用于三角/循环图）
const disc = (cx, cy, r, hue, label, sub) => {
  let s = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${hue}" fill-opacity="0.12" stroke="${hue}" stroke-opacity="0.5" stroke-width="1.5"/>`
  s += T(cx, cy - (sub ? 3 : -5), label, { size: 14, w: 800, anchor: 'middle', fill: hue })
  if (sub) s += T(cx, cy + 15, sub, { size: 10.5, anchor: 'middle', fill: P.ink2 })
  return s
}

// ════════ 图1 · 封面：三位一体 ════════
function figCover () {
  const W = 940, H = 420
  const x = 40, w = W - 80
  let b = titleBlk(W, '认知型企业系统新范式 · The Cognitive Enterprise',
    '本体接地(Ontology) × 大模型推理(LLM) × 智能体执行(Agent) —— 三位一体的有机组合')
  // 三支柱
  const cw = (w - 2 * 20) / 3
  const pil = [
    [P.violet, 'Ontology · 本体', '企业的世界模型', '什么存在 · 如何关联 · 何为真', '接地的真相底座'],
    [P.blue, 'LLM · 大模型', '推理与语言皮层', '理解意图 · 综合推理 · 解释', '流畅的思考器官'],
    [P.aqua, 'Agent · 智能体', '执行的中枢回路', '感知→决策→行动→记忆', '自主的行动闭环'],
  ]
  pil.forEach((p, i) => {
    const cx = x + i * (cw + 20)
    b += R(cx, 76, cw, 150, { rx: 14, fill: p[0], fop: 0.09, stroke: p[0], sop: 0.34, sw: 1.4 })
    b += R(cx, 76, cw, 5, { rx: 2, fill: p[0] })
    b += T(cx + cw / 2, 112, p[1], { size: 16, w: 800, anchor: 'middle', fill: p[0] })
    b += T(cx + cw / 2, 136, p[2], { size: 12.5, w: 700, anchor: 'middle', fill: P.ink })
    b += T(cx + cw / 2, 162, p[3], { size: 10.5, anchor: 'middle', fill: P.ink2 })
    b += R(cx + cw / 2 - 78, 182, 156, 28, { rx: 14, fill: p[0], fop: 0.14, stroke: p[0], sop: 0.3, sw: 1 })
    b += T(cx + cw / 2, 200, p[4], { size: 11, w: 700, anchor: 'middle', fill: p[0] })
  })
  // 核心论点条
  b += R(x, 244, w, 60, { rx: 12, fill: P.ink, fop: 1 })
  b += T(x + 24, 270, '论点：三者缺一皆残 —— 有本体无智能体=会想不会做；有智能体无本体=自信地做错；', { size: 12.5, w: 700, fill: '#e8f0fc' })
  b += T(x + 24, 291, '有大模型无二者=能说不能行。三者合一 → 接地 + 推理 + 行动 + 可信，跨过认知企业的门槛。', { size: 12.5, w: 700, fill: '#e8f0fc' })
  // 底部飞轮提示
  b += R(x, 318, w, 82, { rx: 12, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 20, 342, '决定性机制 · 写回飞轮（Write-back Flywheel）', { size: 13, w: 800, fill: P.ink })
  b += T(x + 20, 364, '智能体的每次行动都是对本体对象模型的一次「有类型、留血缘」的写操作 → 本体因此持续更新为最新真相', { size: 11.5, fill: P.ink2 })
  b += T(x + 20, 383, '→ 成为下一轮大模型推理更好的上下文 → 推理更准 → 行动更稳。企业的世界模型随系统运转越用越鲜活、越用越聪明。', { size: 11.5, fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图2 · 三系统的本质·能力·致命短板 ════════
function figTrinity () {
  const W = 960, H = 470
  const x = 34, w = W - 68
  let b = titleBlk(W, '三系统各自的本质 · 独特能力 · 致命短板',
    '每一个单独都强大却残缺；理解各自的「短板」，才理解为何必须三位一体')
  const cw = (w - 2 * 16) / 3
  const cols = [
    [P.violet, 'Ontology 本体', '世界模型 / 真相', '回答「什么是真、如何结构化」',
      ['实体/对象与关系的语义模型', '业务规则与不变量约束', '可执行的动作 schema', '权限、血缘与审计的锚点', '结构化、确定、可查询'],
      '短板：静态、不会推理、不会行动', '没有它 → 一切漂浮、脱离现实'],
    [P.blue, 'LLM 大模型', '推理 / 语言', '回答「这是什么意思、该考虑什么」',
      ['理解模糊的自然语言意图', '在非结构化语境中综合推理', '在语言与形式结构间翻译', '规划、解释、生成、归纳', '流畅、灵活、处理长尾'],
      '短板：会幻觉、无真相、无状态、不确定', '没有它 → 系统僵硬、不懂人话'],
    [P.aqua, 'Agent 智能体', '执行 / 行动', '回答「如何把事情做成」',
      ['感知→决策→行动→记忆循环', '调用工具/API、编排多步任务', '跨时间持久、带目标与记忆', '与人协作、可中断可恢复', '自主、能动、闭环'],
      '短板：无世界模型则盲、无推理则鲁莽', '没有它 → 只会说、不会做'],
  ]
  cols.forEach((c, i) => {
    const cx = x + i * (cw + 16)
    b += R(cx, 74, cw, 372, { rx: 12, fill: c[0], fop: 0.06, stroke: c[0], sop: 0.32, sw: 1.3 })
    b += R(cx, 74, cw, 5, { rx: 2, fill: c[0] })
    b += T(cx + 16, 104, c[1], { size: 15, w: 800, fill: c[0] })
    b += T(cx + 16, 124, c[2] + ' · ' + '', { size: 11.5, w: 700, fill: P.ink })
    b += T(cx + 16, 143, c[3], { size: 10.5, fill: P.ink2 })
    b += LINE(cx + 16, 152, cx + cw - 16, 152, { marker: false, stroke: c[0], sw: 0.8, dash: '3 3' })
    c[4].forEach((ln, j) => {
      const yy = 174 + j * 26
      b += `<circle cx="${cx + 22}" cy="${yy - 4}" r="2.5" fill="${c[0]}"/>`
      b += T(cx + 32, yy, ln, { size: 11, fill: P.ink })
    })
    // 短板框
    b += R(cx + 14, 316, cw - 28, 50, { rx: 8, fill: P.critical, fop: 0.07, stroke: P.critical, sop: 0.28, sw: 1 })
    b += T(cx + 24, 336, '✗ ' + c[5].split('：')[0] + '：', { size: 10.5, w: 800, fill: P.critical })
    b += T(cx + 24, 353, c[5].split('：')[1], { size: 10.5, fill: P.ink2 })
    // 缺失后果
    b += R(cx + 14, 374, cw - 28, 56, { rx: 8, fill: c[0], fop: 0.10, stroke: c[0], sop: 0.3, sw: 1 })
    b += T(cx + (cw - 28) / 2 + 14, 397, c[6].split(' → ')[0], { size: 11, w: 700, anchor: 'middle', fill: c[0] })
    b += T(cx + (cw - 28) / 2 + 14, 416, '→ ' + c[6].split(' → ')[1], { size: 10.5, anchor: 'middle', fill: P.ink2 })
  })
  return doc(W, H, b)
}

// ════════ 图3 · 两两组合为何仍然失败 ════════
function figPairs () {
  const W = 940, H = 460
  const x = 40, w = W - 80
  let b = titleBlk(W, '为何「缺一不可」· 两两组合的失败模式',
    '任取其二、缺其一，都退化成一种已知且不足的旧范式 —— 反证三者的必要性')
  const rows = [
    [P.blue, P.aqua, P.violet, 'LLM + Agent，缺 Ontology',
      '自信地做错事（Confident Hallucinated Action）',
      '智能体基于大模型「编造」的业务理解去行动：把不存在的「客户/订单」传给 API、用错实体、违反本可知的约束。',
      '≈ 无护栏的自主智能体 · 自主但妄想', '缺：接地的真相'],
    [P.violet, P.aqua, P.blue, 'Ontology + Agent，缺 LLM',
      '脆弱的确定性自动化（Brittle Scripted Automation）',
      '只能执行硬编码好的确定路径：无法处理歧义、新情况、自然语言意图；一遇长尾即断。这正是传统 RPA / BPM。',
      '≈ RPA / 工作流引擎 · 能干但僵硬', '缺：推理的灵活'],
    [P.violet, P.blue, P.aqua, 'Ontology + LLM，缺 Agent',
      '会思考却瘫痪（Wise but Paralyzed）',
      '能在接地的模型上优雅推理、准确回答，但只能产出文字：真正的执行仍要人来点按。这正是「只会答」的智能问答/副驾。',
      '≈ 语义搜索 / 只读 Copilot · 睿智但无手', '缺：行动的闭环'],
  ]
  let y = 74
  rows.forEach((r) => {
    const rh = 116
    b += R(x, y, w, rh, { rx: 11, fill: P.surface, stroke: P.border, sw: 1 })
    // 左侧两色圆（有的）+ 灰圆（缺的）
    const cxb = x + 46
    b += `<circle cx="${cxb}" cy="${y + 34}" r="17" fill="${r[0]}" fill-opacity="0.16" stroke="${r[0]}" stroke-opacity="0.5"/>`
    b += `<circle cx="${cxb + 30}" cy="${y + 34}" r="17" fill="${r[1]}" fill-opacity="0.16" stroke="${r[1]}" stroke-opacity="0.5"/>`
    b += `<circle cx="${cxb + 15}" cy="${y + 78}" r="17" fill="none" stroke="${P.critical}" stroke-opacity="0.5" stroke-dasharray="3 3"/>`
    b += T(cxb + 15, y + 82, '缺', { size: 11, w: 800, anchor: 'middle', fill: P.critical })
    // 右侧文本
    const tx = x + 108
    b += T(tx, y + 26, r[3], { size: 13.5, w: 800, fill: P.ink })
    b += R(tx, y + 36, Math.round(wOf(r[4], 12) + 24), 24, { rx: 7, fill: P.critical, fop: 0.10, stroke: P.critical, sop: 0.3, sw: 1 })
    b += T(tx + 12, y + 52, r[4], { size: 11.5, w: 700, fill: P.critical })
    b += T(tx, y + 78, r[5], { size: 11, fill: P.ink2 })
    b += T(tx, y + 98, r[6], { size: 10.5, w: 700, fill: P.muted })
    // 右端「缺什么」标签
    b += R(x + w - 150, y + 44, 134, 28, { rx: 14, fill: r[2], fop: 0.12, stroke: r[2], sop: 0.34, sw: 1 })
    b += T(x + w - 83, y + 62, r[7], { size: 11, w: 700, anchor: 'middle', fill: r[2] })
    y += rh + 12
  })
  return doc(W, H, b)
}

// ════════ 图4 · 分层参考架构 ════════
function figArch () {
  const W = 960, H = 620
  const x = 40, w = W - 80
  let b = titleBlk(W, '认知型企业 · 分层参考架构',
    '从交互到接地：六层堆叠，本体贯穿为纵向真相脊柱，治理为横向护栏')
  // L1 交互层
  let y = 74
  b += band(x, y, w, 46, P.magenta, '① 交互层 · Experience', '自然语言 · 对话/副驾 · 主动通知 · 人在环审批 · 富组件（表格/图/看板）回填', '人机接口')
  b += LINE(W / 2, y + 46, W / 2, y + 62, { stroke: P.muted })
  // L2 智能体层
  y = 138
  b += band(x, y, w, 60, P.aqua, '② 智能体编排层 · Agent Orchestration',
    '规划器 · 多智能体协作 · 工具调用 · 记忆(短期/长期/情节) · 任务队列 · 可中断可恢复 · 人在环闸门', '执行中枢')
  b += LINE(W / 2, y + 60, W / 2, y + 76, { stroke: P.muted })
  // L3 推理层
  y = 214
  b += band(x, y, w, 60, P.blue, '③ 推理层 · Reasoning (LLM)',
    '意图理解 · 规划分解 · NL↔结构 双向翻译 · RAG/GraphRAG · 函数/工具选择 · 解释与摘要 · 置信与不确定度', '思考皮层')
  b += LINE(W / 2, y + 60, W / 2, y + 76, { stroke: P.muted })
  // L4 语义接口层（关键接缝）
  y = 290
  b += R(x, y, w, 58, { rx: 10, fill: P.violet, fop: 0.14, stroke: P.violet, sop: 0.4, sw: 1.4 })
  b += R(x, y, 4, 58, { rx: 2, fill: P.violet })
  b += T(x + 18, y + 24, '④ 语义接口层 · Semantic Interface（关键接缝）', { size: 14, w: 800, fill: P.violet })
  b += T(x + 18, y + 44, '本体作为「工具目录 + 类型系统」暴露给智能体：对象/关系查询 · 受控动作(Action) · 约束校验 · 权限求解 · 血缘登记', { size: 11, fill: P.ink2 })
  b += LINE(W / 2, y + 58, W / 2, y + 74, { stroke: P.violet, sw: 2 })
  // L5 本体层
  y = 364
  b += band(x, y, w, 66, P.violet, '⑤ 本体层 · Ontology（世界模型 · 真相脊柱）',
    '对象类型/属性/关系 · 业务规则与不变量 · 动作 schema · 派生/函数 · 双库：om 定义(schema) + oo 实例(objects) · 版本与血缘', '接地底座')
  b += LINE(W / 2, y + 66, W / 2, y + 82, { stroke: P.muted })
  // L6 数据/系统层
  y = 446
  b += band(x, y, w, 52, P.orange, '⑥ 数据与系统层 · Data & Systems',
    'ERP/CRM/数据库/数据湖 · 外部 API/SaaS · 消息与事件 · 通过映射/同步管道投影为本体对象（Funnel）', '物理底盘')
  // 纵向脊柱 + 横向治理条
  b += R(x, 510, w, 92, { rx: 12, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 18, 534, '贯穿全栈的两条正交主线', { size: 13, w: 800, fill: P.ink })
  b += R(x + 18, 546, (w - 54) / 2, 44, { rx: 9, fill: P.violet, fop: 0.10, stroke: P.violet, sop: 0.3, sw: 1 })
  b += T(x + 32, 566, '纵向 · 本体真相脊柱', { size: 11.5, w: 800, fill: P.violet })
  b += T(x + 32, 583, '每层都以本体为共同词汇，消除各层「各说各话」', { size: 10, fill: P.ink2 })
  b += R(x + 18 + (w - 54) / 2 + 18, 546, (w - 54) / 2, 44, { rx: 9, fill: P.red, fop: 0.09, stroke: P.red, sop: 0.3, sw: 1 })
  b += T(x + 32 + (w - 54) / 2 + 18, 566, '横向 · 治理护栏（Governance）', { size: 11.5, w: 800, fill: P.red })
  b += T(x + 32 + (w - 54) / 2 + 18, 583, '身份/权限 · 策略 · 审计 · 血缘 · 评测 · 人在环 —— 每层执行', { size: 10, fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图5 · 写回飞轮（核心机制）════════
function figFlywheel () {
  const W = 920, H = 648
  const cx = W / 2, cy = 320, R0 = 172
  let b = titleBlk(W, '核心机制 · 写回飞轮（The Write-back Flywheel）',
    '本体不是只读的知识库，而是被智能体持续写入的活真相 —— 越运转越聪明')
  // 中心
  b += `<circle cx="${cx}" cy="${cy}" r="56" fill="${P.violet}" fill-opacity="0.10" stroke="${P.violet}" stroke-opacity="0.45" stroke-width="1.5"/>`
  b += T(cx, cy - 8, 'Ontology', { size: 15, w: 800, anchor: 'middle', fill: P.violet })
  b += T(cx, cy + 12, '活的世界模型', { size: 11, anchor: 'middle', fill: P.ink2 })
  b += T(cx, cy + 30, 'om 定义 · oo 实例', { size: 9.5, anchor: 'middle', fill: P.muted, mono: true })
  // 四工位（12/3/6/9点）：[x, y, color, 标题, 行1, 行2(括号), 方位]
  const stn = [
    [cx, cy - R0 - 4, P.blue, '① 接地推理', 'LLM 以本体为上下文', 'GraphRAG · 类型化事实', 'top'],
    [cx + R0 + 78, cy, P.aqua, '② 受控行动', '智能体调用本体 Action', '约束校验 · 权限求解', 'right'],
    [cx, cy + R0 + 4, P.green, '③ 有类型写回', '结果写回对象模型', '留血缘 · 事务 · 审计', 'bottom'],
    [cx - R0 - 78, cy, P.orange, '④ 真相更新', '世界模型即刻反映最新', '成为下轮更好上下文', 'left'],
  ]
  stn.forEach((s) => {
    const bw = 176, bh = 70
    let bx = s[0] - bw / 2, by = s[1] - bh / 2
    const pos = s[6]
    if (pos === 'top') by = s[1] - bh
    if (pos === 'bottom') by = s[1]
    if (pos === 'right') bx = s[0] - bw
    if (pos === 'left') bx = s[0]
    bx = Math.max(22, Math.min(bx, W - bw - 22))
    b += R(bx, by, bw, bh, { rx: 11, fill: s[2], fop: 0.10, stroke: s[2], sop: 0.4, sw: 1.3 })
    b += R(bx, by, 4, bh, { rx: 2, fill: s[2] })
    b += T(bx + bw / 2, by + 24, s[3], { size: 12.5, w: 800, anchor: 'middle', fill: s[2] })
    b += T(bx + bw / 2, by + 43, s[4], { size: 10, anchor: 'middle', fill: P.ink })
    b += T(bx + bw / 2, by + 59, s[5], { size: 9, anchor: 'middle', fill: P.muted })
  })
  // 弧形箭头（顺时针）
  const arc = (a1, a2, col) => {
    const rr = R0 + 2
    const p1 = [cx + rr * Math.cos(a1), cy + rr * Math.sin(a1)]
    const p2 = [cx + rr * Math.cos(a2), cy + rr * Math.sin(a2)]
    const mk = col === P.blue ? 'arrB' : col === P.aqua ? 'arrA' : col === P.violet ? 'arrV' : 'arr'
    return `<path d="M${p1[0]},${p1[1]} A${rr},${rr} 0 0 1 ${p2[0]},${p2[1]}" fill="none" stroke="${col}" stroke-width="2.4" stroke-opacity="0.7" marker-end="url(#${mk})"/>`
  }
  b += arc(-Math.PI / 2 + 0.34, 0 - 0.34, P.aqua)      // 12→3
  b += arc(0 + 0.34, Math.PI / 2 - 0.34, P.green)        // 3→6
  b += arc(Math.PI / 2 + 0.34, Math.PI - 0.34, P.orange) // 6→9
  b += arc(Math.PI + 0.34, -Math.PI / 2 - 0.34 + 2 * Math.PI, P.blue) // 9→12
  // 底部注解
  b += R(40, 584, W - 80, 48, { rx: 10, fill: P.ink, fop: 1 })
  b += T(60, 608, '对比传统 RAG（只读检索）：写回飞轮让「检索—推理—行动」闭环，把每一次业务操作沉淀为结构化真相，', { size: 11, w: 600, fill: '#e8f0fc' })
  b += T(60, 625, '形成数据复利。这是认知型企业「越用越聪明」的根本，也是它区别于「大模型套壳」的分水岭。', { size: 11, w: 600, fill: '#e8f0fc' })
  return doc(W, H, b)
}

// ════════ 图6 · 接地智能体的执行循环 ════════
function figLoop () {
  const W = 960, H = 486
  const x = 40, w = W - 80
  let b = titleBlk(W, '接地智能体的一次执行循环 · Grounded Agent Loop',
    '每一步都被本体「接地」、被治理「守门」—— 自主而不失控')
  const steps = [
    [P.magenta, '感知 Perceive', '接收 NL 意图 / 事件', '「给华东逾期客户做减免」'],
    [P.blue, '理解 Ground', 'LLM 对齐到本体术语', '解析为 客户/账期/减免动作'],
    [P.blue, '规划 Plan', '分解为动作序列', '查询→评估→提案→审批→执行'],
    [P.violet, '校验 Validate', '本体约束 + 权限求解', '不变量/黑名单/额度/RBAC'],
    [P.aqua, '行动 Act', '调用受控 Action', '事务写 + 副作用(Outbox)'],
    [P.green, '写回 Persist', '结果落对象模型', '留血缘 · 审计 · 触发事件'],
  ]
  const n = steps.length, gap = 12, bw = (w - (n - 1) * gap) / n, bh = 150, y0 = 82
  steps.forEach((s, i) => {
    const bx = x + i * (bw + gap)
    b += R(bx, y0, bw, bh, { rx: 11, fill: s[0], fop: 0.08, stroke: s[0], sop: 0.34, sw: 1.2 })
    b += R(bx, y0, bw, 4, { rx: 2, fill: s[0] })
    b += `<circle cx="${bx + bw / 2}" cy="${y0 + 30}" r="15" fill="${s[0]}" fill-opacity="0.16" stroke="${s[0]}" stroke-opacity="0.5"/>`
    b += T(bx + bw / 2, y0 + 35, String(i + 1), { size: 14, w: 800, anchor: 'middle', fill: s[0] })
    b += T(bx + bw / 2, y0 + 66, s[1].split(' ')[0], { size: 12.5, w: 800, anchor: 'middle', fill: P.ink })
    b += T(bx + bw / 2, y0 + 82, s[1].split(' ')[1], { size: 9, anchor: 'middle', fill: P.muted, mono: true })
    b += T(bx + bw / 2, y0 + 104, s[2], { size: 9.8, anchor: 'middle', fill: P.ink2 })
    // 例子
    b += R(bx + 8, y0 + 116, bw - 16, 26, { rx: 6, fill: P.plane, stroke: P.border, sw: 0.8 })
    b += T(bx + bw / 2, y0 + 133, s[3], { size: 8.6, anchor: 'middle', fill: P.ink2 })
    if (i < n - 1) b += LINE(bx + bw + 1, y0 + bh / 2, bx + bw + gap - 1, y0 + bh / 2, { stroke: P.muted, sw: 1.4 })
  })
  // 回环箭头
  b += PATH(`M${x + w - 40},${y0 + bh + 6} C${x + w - 40},${y0 + bh + 44} ${x + 40},${y0 + bh + 44} ${x + 40},${y0 + bh + 8}`, { stroke: P.green, sw: 1.8, marker: true })
  b += T(W / 2, y0 + bh + 40, '写回的新真相 → 成为下一次「感知/理解」的更优上下文（闭环）', { size: 10.5, w: 700, anchor: 'middle', fill: P.green })
  // 治理护栏条
  const gy = y0 + bh + 62
  b += R(x, gy, w, 74, { rx: 11, fill: P.red, fop: 0.06, stroke: P.red, sop: 0.28, sw: 1.2 })
  b += T(x + 16, gy + 24, '横切护栏 · 每一步都要过的治理关卡', { size: 12.5, w: 800, fill: P.red })
  const g = ['权限：本体求解可见/可写范围', '策略：高风险动作转人工审批', '不确定：低置信→澄清或升级', '审计：全链路留痕可回放', '预算：Token/调用/影响面配额', '回滚：失败补偿与幂等']
  b += chipFlow(x + 16, gy + 34, x + w - 16, g, P.red, { size: 10 }).svg
  return doc(W, H, b)
}

// ════════ 图7 · 端到端场景走查 ════════
function figScenario () {
  const W = 960, H = 560
  const x = 40, w = W - 80
  let b = titleBlk(W, '一个具体场景 · 三系统如何协奏',
    '「本月华东区逾期客户，按政策做减免并通知」—— 看本体/大模型/智能体如何各司其职、层层接力')
  // 泳道标签
  const lanes = [['LLM · 推理', P.blue], ['Ontology · 接地', P.violet], ['Agent · 执行', P.aqua], ['Human · 治理', P.magenta]]
  const laneY = [86, 200, 314, 428]
  lanes.forEach((l, i) => {
    b += R(x, laneY[i], 120, 96, { rx: 9, fill: l[1], fop: 0.12, stroke: l[1], sop: 0.34, sw: 1 })
    b += T(x + 60, laneY[i] + 44, l[0].split(' ')[0], { size: 13, w: 800, anchor: 'middle', fill: l[1] })
    b += T(x + 60, laneY[i] + 62, l[0].split(' ')[2] || l[0].split(' ')[1], { size: 10.5, anchor: 'middle', fill: P.ink2 })
  })
  // 步骤卡（跨泳道流转）：[laneIdx, colIdx, 标题, 说明]
  const gx = x + 132, gw = w - 132, colW = (gw - 4 * 12) / 5
  const stepPos = (col, lane) => [gx + col * (colW + 12), laneY[lane]]
  const S = [
    [0, 0, P.magenta, '意图输入', '业务员用自然语言下达指令'],
    [1, 0, P.blue, '意图解析', 'LLM 拆解：范围/动作/约束'],
    [1, 1, P.violet, '术语对齐', '映射到 客户/账期/区域/减免'],
    [2, 1, P.violet, '接地检索', 'GraphRAG 拉出候选对象集'],
    [2, 0, P.blue, '生成计划', 'LLM 排出多步动作序列'],
    [3, 1, P.violet, '约束校验', '黑名单/额度/政策不变量'],
    [3, 3, P.magenta, '人工审批', '超额度→人在环批准'],
    [4, 2, P.aqua, '执行动作', '批量调用减免 Action(事务)'],
    [4, 1, P.violet, '写回真相', '对象更新+血缘+触发通知'],
  ]
  // 连线顺序
  const order = [0, 1, 2, 3, 4, 5, 6, 7, 8]
  let prev = null
  const centers = {}
  S.forEach((s, idx) => {
    const [px, py] = stepPos(s[0], s[1])
    centers[idx] = [px + colW / 2, py + 48]
  })
  // 画连线（先画线后画卡）
  for (let i = 1; i < order.length; i++) {
    const a = centers[order[i - 1]], c = centers[order[i]]
    b += PATH(`M${a[0]},${a[1]} C${(a[0] + c[0]) / 2},${a[1]} ${(a[0] + c[0]) / 2},${c[1]} ${c[0]},${c[1]}`, { stroke: P.muted, sw: 1.3, marker: true })
  }
  S.forEach((s) => {
    const [px, py] = stepPos(s[0], s[1])
    b += R(px, py, colW, 96, { rx: 10, fill: s[2], fop: 0.10, stroke: s[2], sop: 0.36, sw: 1.1 })
    b += R(px, py, colW, 4, { rx: 2, fill: s[2] })
    b += T(px + colW / 2, py + 34, s[3], { size: 12, w: 800, anchor: 'middle', fill: s[2] })
    // 说明换行
    const words = s[4]
    b += T(px + colW / 2, py + 58, words.length > 11 ? words.slice(0, 11) : words, { size: 9.4, anchor: 'middle', fill: P.ink })
    if (words.length > 11) b += T(px + colW / 2, py + 73, words.slice(11), { size: 9.4, anchor: 'middle', fill: P.ink })
  })
  b += R(x, 536, w, 0, { rx: 0 }) // spacer
  return doc(W, H, b)
}

// ════════ 图8 · 认知型企业成熟度阶梯 ════════
function figMaturity () {
  const W = 940, H = 480
  const x = 40, w = W - 80
  let b = titleBlk(W, '成熟度阶梯 · 从「大模型套壳」到「认知型企业」',
    'L0→L4 逐级演进：每一级解决前一级的致命短板，本体与写回是跨越 L2 的分水岭')
  const levels = [
    [P.muted, 'L0', '孤立自动化', 'RPA / 规则脚本 · 硬编码路径', '会做但僵硬', 0],
    [P.yellow, 'L1', '语言助理', 'LLM 副驾 / 问答 · 无接地只读', '能说但会编', 1],
    [P.orange, 'L2', '接地问答', 'LLM + Ontology · GraphRAG 回答', '准确但无手', 2],
    [P.blue, 'L3', '接地智能体', '+ Agent 执行 · 受控动作 + 人在环', '会做且接地', 3],
    [P.violet, 'L4', '认知型企业', '+ 写回飞轮 · 自主编排 · 数据复利', '越用越聪明', 4],
  ]
  const n = levels.length, bw = (w - (n - 1) * 12) / n
  const baseY = 408, maxH = 252
  levels.forEach((l, i) => {
    const bx = x + i * (bw + 12)
    const bh = 146 + i * ((maxH - 146) / (n - 1))
    const by = baseY - bh
    b += R(bx, by, bw, bh, { rx: 11, fill: l[0], fop: 0.10, stroke: l[0], sop: 0.36, sw: 1.3 })
    b += R(bx, by, bw, 5, { rx: 2, fill: l[0] })
    b += `<circle cx="${bx + bw / 2}" cy="${by + 34}" r="17" fill="${l[0]}" fill-opacity="0.18" stroke="${l[0]}" stroke-opacity="0.5"/>`
    b += T(bx + bw / 2, by + 40, l[1], { size: 15, w: 800, anchor: 'middle', fill: l[0] })
    b += T(bx + bw / 2, by + 66, l[2], { size: 12, w: 800, anchor: 'middle', fill: P.ink })
    // 说明多行（紧贴标题下方）
    const parts = l[3].split(' · ')
    parts.forEach((p, j) => b += T(bx + bw / 2, by + 85 + j * 14, p, { size: 8.6, anchor: 'middle', fill: P.ink2 }))
    // 底部一句话状态（贴底）
    b += R(bx + 6, baseY - 30, bw - 12, 22, { rx: 6, fill: l[0], fop: 0.14, stroke: l[0], sop: 0.3, sw: 1 })
    b += T(bx + bw / 2, baseY - 15, l[4], { size: 10, w: 700, anchor: 'middle', fill: l[0] })
  })
  // 分水岭标注
  const divX = x + 3 * (bw + 12) - 6
  b += LINE(divX, 96, divX, baseY + 6, { stroke: P.violet, sw: 1.6, dash: '5 4', marker: false })
  b += R(divX - 96, 100, 192, 26, { rx: 13, fill: P.violet, fop: 0.14, stroke: P.violet, sop: 0.34, sw: 1 })
  b += T(divX, 117, '分水岭：本体接地 + 写回飞轮', { size: 10.5, w: 700, anchor: 'middle', fill: P.violet })
  // 底轴
  b += LINE(x, baseY + 6, x + w, baseY + 6, { stroke: P.base, sw: 1.5, marker: false })
  b += T(x, baseY + 26, '能力/自主度 →', { size: 10.5, w: 700, fill: P.muted })
  b += T(x + w, baseY + 26, '越往右：越自主、越接地、越可信、越有数据复利', { size: 10.5, anchor: 'end', fill: P.muted })
  return doc(W, H, b)
}

// ════════ 图9 · 与既有范式的对比 ════════
function figCompare () {
  const engines = [
    ['认知型企业', '本范式', true],
    ['RPA / BPM', '流程自动化', false],
    ['数据中台 / BI', '数据洞察', false],
    ['RAG 问答/副驾', 'LLM 应用', false],
    ['知识图谱', '语义资产', false],
  ]
  const rows = [
    ['接地的真相底座', [['✓ 本体世界模型', 'ok'], ['流程图/表单', 'warn'], ['数仓/指标', 'warn'], ['向量块(易漂)', 'no'], ['✓ 图谱(常只读)', 'warn']]],
    ['语言/意图理解', [['✓ LLM 推理', 'ok'], ['无', 'no'], ['无/弱', 'no'], ['✓ 强', 'ok'], ['弱', 'no']]],
    ['自主执行/行动', [['✓ 智能体闭环', 'ok'], ['✓ 确定脚本', 'warn'], ['只读洞察', 'no'], ['多为只读', 'no'], ['只读', 'no']]],
    ['处理歧义/长尾', [['✓ 推理灵活', 'ok'], ['✗ 一遇即断', 'no'], ['需人分析', 'no'], ['✓ 但会编', 'warn'], ['✗', 'no']]],
    ['写回/数据复利', [['✓ 写回飞轮', 'ok'], ['写业务库(无语义)', 'warn'], ['✗ 单向汇聚', 'no'], ['✗ 只读检索', 'no'], ['多为静态', 'no']]],
    ['治理/可审计', [['✓ 血缘+权限+审计', 'ok'], ['部分', 'warn'], ['✓ 数据治理', 'ok'], ['弱/黑盒', 'no'], ['部分', 'warn']]],
    ['越用越聪明', [['✓ 复利飞轮', 'ok'], ['✗ 静态', 'no'], ['✗ 需人迭代', 'no'], ['✗ 无沉淀', 'no'], ['✗ 需人维护', 'no']]],
  ]
  const W = 1040, x0 = 30, dimW = 132, ew = (W - 2 * x0 - dimW) / 5
  const headY = 74, headH = 50, rowH = 34, y0 = headY + headH + 6
  const H = y0 + rows.length * rowH + 48
  let b = titleBlk(W, '与既有企业范式的对比 · 为何是「新」模式',
    '不是替代，而是把四类既有能力在「本体 × 大模型 × 智能体」上重新组织并闭环')
  engines.forEach((e, i) => {
    const cx = x0 + dimW + i * ew
    const acc = e[2] ? P.violet : P.base
    b += R(cx + 2, headY, ew - 4, headH, { rx: 8, fill: acc, fop: e[2] ? 0.16 : 0.08, stroke: acc, sop: e[2] ? 0.44 : 0.22, sw: e[2] ? 1.5 : 1 })
    b += T(cx + ew / 2, headY + 22, e[0], { size: 12, w: 800, anchor: 'middle', fill: e[2] ? P.violet : P.ink })
    b += T(cx + ew / 2, headY + 39, e[1], { size: 9.5, anchor: 'middle', fill: P.ink2 })
  })
  b += T(x0 + dimW / 2, headY + 29, '能力维度', { size: 11.5, w: 800, anchor: 'middle', fill: P.ink2 })
  const gTint = { ok: P.good, warn: P.warning, no: P.muted }
  rows.forEach((r, ri) => {
    const ry = y0 + ri * rowH
    b += R(x0, ry, dimW, rowH - 3, { rx: 6, fill: P.plane, stroke: P.border, sw: 1 })
    b += T(x0 + 10, ry + rowH / 2 + 2, r[0], { size: 10.5, w: 700, fill: P.ink })
    r[1].forEach(([txt, g], ci) => {
      const cx = x0 + dimW + ci * ew
      const isSelf = ci === 0
      const hue = gTint[g]
      b += R(cx + 2, ry, ew - 4, rowH - 3, { rx: 6, fill: hue, fop: g === 'no' ? 0.07 : (isSelf ? 0.18 : 0.13), stroke: hue, sop: g === 'no' ? 0.28 : 0.36, sw: isSelf ? 1.3 : 1 })
      b += R(cx + 2, ry, 3, rowH - 3, { rx: 1.5, fill: hue })
      b += T(cx + ew / 2 + 2, ry + rowH / 2 + 2, txt, { size: 9.8, w: g === 'no' ? 400 : (isSelf ? 700 : 600), anchor: 'middle', fill: g === 'no' ? P.ink2 : P.ink })
    })
  })
  const ly = y0 + rows.length * rowH + 8
  b += R(x0, ly, W - 2 * x0, 30, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x0 + 14, ly + 19, '图例：', { size: 10.5, w: 700, fill: P.ink2 })
  let lx = x0 + 58
  ;[['强 / 具备', 'ok'], ['部分 / 受限', 'warn'], ['弱 / 无', 'no']].forEach(([lab, g]) => {
    const hue = gTint[g]
    b += R(lx, ly + 7, 15, 15, { rx: 4, fill: hue, fop: g === 'no' ? 0.1 : 0.16, stroke: hue, sop: 0.4, sw: 1 })
    b += T(lx + 21, ly + 19, lab, { size: 10.5, fill: P.ink2 }); lx += 34 + wOf(lab, 10.5)
  })
  b += T(W - x0 - 14, ly + 19, '认知型企业 = 唯一在「接地 + 推理 + 行动 + 复利」四轴同时为强的组合', { size: 10, anchor: 'end', w: 700, fill: P.violet })
  return doc(W, H, b)
}

// ════════ 图10 · 落地路线图 ════════
function figRoadmap () {
  const W = 960, H = 470
  const x = 40, w = W - 80
  let b = titleBlk(W, '落地路线图 · 从试点到认知型企业',
    '不必一步到位：先立本体骨架，再接大模型接地，最后放智能体行动 —— 每阶段独立产生价值')
  const phases = [
    [P.violet, '阶段 0 · 立本体骨架', '2–3 月', ['选高价值域(如信控/供应链)', '建对象类型/关系/规则', '接 1–2 个源系统投影', '定义受控 Action schema'], '产出：可查询的世界模型'],
    [P.blue, '阶段 1 · 大模型接地', '2–3 月', ['GraphRAG 接本体检索', 'NL↔本体术语双向翻译', '只读问答/副驾先上线', '建评测集与置信门槛'], '产出：准确的接地问答'],
    [P.aqua, '阶段 2 · 智能体行动', '3–4 月', ['单一高频动作先跑通', '约束校验 + 人在环闸门', '写回 + 血缘 + 审计', '灰度放开自主度'], '产出：端到端闭环智能体'],
    [P.green, '阶段 3 · 飞轮规模化', '持续', ['多智能体协作编排', '沉淀领域动作库', '数据复利度量与优化', '横向复制到更多域'], '产出：越用越聪明的组织'],
  ]
  const cw = (w - 3 * 14) / 4
  phases.forEach((p, i) => {
    const cx = x + i * (cw + 14)
    b += R(cx, 76, cw, 322, { rx: 12, fill: p[0], fop: 0.07, stroke: p[0], sop: 0.34, sw: 1.3 })
    b += R(cx, 76, cw, 5, { rx: 2, fill: p[0] })
    b += T(cx + 14, 104, p[1].split(' · ')[0], { size: 11.5, w: 800, fill: p[0] })
    b += T(cx + 14, 122, p[1].split(' · ')[1], { size: 12.5, w: 800, fill: P.ink })
    b += R(cx + cw - 62, 90, 48, 22, { rx: 11, fill: p[0], fop: 0.16, stroke: p[0], sop: 0.32, sw: 1 })
    b += T(cx + cw - 38, 105, p[2], { size: 10, w: 700, anchor: 'middle', fill: p[0] })
    b += LINE(cx + 14, 134, cx + cw - 14, 134, { marker: false, stroke: p[0], sw: 0.8, dash: '3 3' })
    p[3].forEach((it, j) => {
      const yy = 158 + j * 34
      b += `<circle cx="${cx + 20}" cy="${yy - 4}" r="2.5" fill="${p[0]}"/>`
      // 自动换行
      const maxw = cw - 40
      if (wOf(it, 10.5) > maxw) {
        const mid = Math.ceil(it.length * maxw / wOf(it, 10.5))
        b += T(cx + 30, yy - 6, it.slice(0, mid), { size: 10.3, fill: P.ink })
        b += T(cx + 30, yy + 8, it.slice(mid), { size: 10.3, fill: P.ink })
      } else {
        b += T(cx + 30, yy, it, { size: 10.5, fill: P.ink })
      }
    })
    b += R(cx + 10, 358, cw - 20, 30, { rx: 7, fill: p[0], fop: 0.13, stroke: p[0], sop: 0.3, sw: 1 })
    b += T(cx + cw / 2, 377, p[4], { size: 9.8, w: 700, anchor: 'middle', fill: p[0] })
    if (i < 3) b += LINE(cx + cw + 1, 230, cx + cw + 13, 230, { stroke: P.muted, sw: 1.4 })
  })
  // 底部原则
  b += R(x, 414, w, 42, { rx: 10, fill: P.ink, fop: 1 })
  b += T(x + 20, 431, '关键原则：本体先行（否则智能体无处接地）· 治理内建（非事后补）· 每阶段可独立交付价值（非瀑布）·', { size: 11, w: 600, fill: '#e8f0fc' })
  b += T(x + 20, 448, '从「人在环」到「人在环上」（Human-in → Human-on-the-loop）逐步放权，自主度随信任度增长。', { size: 11, w: 600, fill: '#e8f0fc' })
  return doc(W, H, b)
}

const FIGS = { 'fig-cover': figCover, 'fig-trinity': figTrinity, 'fig-pairs': figPairs, 'fig-arch': figArch, 'fig-flywheel': figFlywheel, 'fig-loop': figLoop, 'fig-scenario': figScenario, 'fig-maturity': figMaturity, 'fig-compare': figCompare, 'fig-roadmap': figRoadmap }

function main () {
  for (const [k, fn] of Object.entries(FIGS)) {
    const svg = fn()
    writeFileSync(join(DIR, `${k}.svg`), svg)
    console.log(`wrote ${k}.svg (${(svg.length / 1024).toFixed(1)} KiB)`)
  }
}
main()
