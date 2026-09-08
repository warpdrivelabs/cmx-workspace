// gen.mjs — 生成「cmx-flowengine × cmx-rulesengine 融合方案」报告的全部图。
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const DIR = dirname(fileURLToPath(import.meta.url))
const P = {
  surface: '#fcfcfb', plane: '#f4f4f1', ink: '#0b0b0b', ink2: '#52514e', muted: '#898781',
  grid: '#e1e0d9', base: '#c3c2b7', border: 'rgba(11,11,11,0.12)',
  blue: '#2a78d6', orange: '#eb6834', aqua: '#1baf7a', yellow: '#eda100',
  magenta: '#e87ba4', green: '#008300', violet: '#4a3aa7', red: '#e34948',
  good: '#0ca30c', warning: '#fab219', serious: '#ec835a', critical: '#d03b3b', blue550: '#1c5cab',
}
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
  <marker id="arrG" markerWidth="10" markerHeight="10" refX="7" refY="3.2" orient="auto"><path d="M0,0 L7,3.2 L0,6.4 Z" fill="${P.good}"/></marker>
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
    if (x + c.w > maxX && x > x0) { x = x0; y += lh }
    const c2 = chip(x, y, it, hue, o); out += c2.svg; x += c2.w + gap
  }
  return { svg: out, height: y + lh - y0 }
}
const titleBlk = (w, s, sub) => T(w / 2, 34, s, { size: 19, w: 800, anchor: 'middle' }) +
  (sub ? T(w / 2, 54, sub, { size: 12.5, fill: P.ink2, anchor: 'middle' }) : '')
const li = (x, y, hue, txt, o = {}) => `<circle cx="${x}" cy="${y - 4}" r="2.6" fill="${hue}"/>` + T(x + 10, y, txt, { size: o.size || 11, fill: o.fill || P.ink })

// ════════ 图1 · 现状 ════════
function figCurrent () {
  const W = 980, H = 508
  let b = titleBlk(W, '现状 · 两个独立引擎，各有决策能力，尚无连接',
    'cmx-flowengine 与 cmx-rulesengine 均已就绪、架构同源，但今天没有任何代码级联系')
  const pw = 420, lx = 34, rx = W - 34 - pw
  // 左 flow
  b += R(lx, 74, pw, 356, { rx: 12, fill: P.aqua, fop: 0.06, stroke: P.aqua, sop: 0.34, sw: 1.3 })
  b += R(lx, 74, pw, 5, { rx: 2, fill: P.aqua })
  b += T(lx + 16, 104, 'cmx-flowengine', { size: 15, w: 800, fill: P.aqua })
  b += T(lx + pw - 16, 104, ':8091', { size: 11, anchor: 'end', fill: P.muted, mono: true })
  b += T(lx + 16, 123, '令牌持久化流程引擎 · 12 crate', { size: 11, fill: P.ink2 })
  b += R(lx + 14, 136, pw - 28, 96, { rx: 9, fill: P.warning, fop: 0.09, stroke: P.warning, sop: 0.3, sw: 1 })
  b += T(lx + 26, 158, '内置决策：businessRuleTask', { size: 12, w: 800, fill: P.serious })
  b += li(lx + 28, 180, P.warning, '自带 DecisionTable · 仅 FIRST / COLLECT 两策略', { fill: P.ink })
  b += li(lx + 28, 200, P.warning, 'cmx_flow_decision 表 · 引擎内硬编码 evaluate', { fill: P.ink })
  b += li(lx + 28, 220, P.warning, '无图 · 无 gap/overlap · 无归因 trace', { fill: P.ink2 })
  b += li(lx + 26, 258, P.aqua, '表达式：自研 ${..} DSL（expr.rs · ~21 内建 · 无时间/区间）', { size: 10.8 })
  b += li(lx + 26, 280, P.aqua, '注入接缝：RuntimeStore/JavaDelegate/Clock/AssigneeResolver…', { size: 10.8 })
  b += li(lx + 26, 302, P.aqua, '出站：HttpDelegate 经 cmx-service-rpc（X-API-Key + 用户令牌）', { size: 10.8 })
  b += li(lx + 26, 324, P.aqua, '前端：自带 decision-designer（FIRST/COLLECT）+ ops 查看页', { size: 10.8 })
  b += R(lx + 14, 344, pw - 28, 70, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(lx + 26, 366, '注：decision-viewer.js 自陈「编辑应归 cmx-rulesengine，', { size: 10, fill: P.ink2 })
  b += T(lx + 26, 382, '此处仅 flow 侧运维视图」——收敛意图已潜伏于代码', { size: 10, fill: P.ink2 })
  b += T(lx + 26, 402, '前端网格「机制」曾借鉴 rules，但数据层各自独立', { size: 10, fill: P.muted })
  // 右 rules
  b += R(rx, 74, pw, 356, { rx: 12, fill: P.violet, fop: 0.06, stroke: P.violet, sop: 0.34, sw: 1.3 })
  b += R(rx, 74, pw, 5, { rx: 2, fill: P.violet })
  b += T(rx + 16, 104, 'cmx-rulesengine', { size: 15, w: 800, fill: P.violet })
  b += T(rx + pw - 16, 104, ':8094', { size: 11, anchor: 'end', fill: P.muted, mono: true })
  b += T(rx + 16, 123, '无状态微秒级决策/规则引擎 · 6 crate', { size: 11, fill: P.ink2 })
  b += R(rx + 14, 136, pw - 28, 96, { rx: 9, fill: P.good, fop: 0.08, stroke: P.good, sop: 0.3, sw: 1 })
  b += T(rx + 26, 158, '完整决策：JDM 图 + 决策表', { size: 12, w: 800, fill: P.green })
  b += li(rx + 28, 180, P.good, '11 DMN 命中策略 · 决策图 DAG（拓扑+防环）', { fill: P.ink })
  b += li(rx + 28, 200, P.good, 'gap/overlap 完备性分析 · 逐节点失败归因 trace', { fill: P.ink })
  b += li(rx + 28, 220, P.good, '子决策递归 · Rhai 脚本四载体（判定侧永远 FEEL）', { fill: P.ink })
  b += li(rx + 26, 258, P.violet, '表达式：自研 Pratt S-FEEL（expr.rs · 25 内建 · 区间/成员）', { size: 10.8 })
  b += li(rx + 26, 280, P.violet, 'Headless：/api/rules/v1/* · SSE · OpenAPI · db-per-tenant', { size: 10.8 })
  b += li(rx + 26, 302, P.violet, '可嵌：model+engine+feel 为 leaf（零 DB/infra，可 wasm）', { size: 10.8 })
  b += li(rx + 26, 324, P.violet, '前端：决策表设计器 + 决策图可视设计器 + 仿真台 + 审计', { size: 10.8 })
  b += R(rx + 14, 344, pw - 28, 70, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(rx + 26, 366, '同源：同 Rust edition 2024 · 工具链 1.97.1 · 均 Apache-2.0', { size: 10, fill: P.ink2 })
  b += T(rx + 26, 382, '同栈：共用 cmx-database-pg / cmx-core / cmx-web-chassis', { size: 10, fill: P.ink2 })
  b += T(rx + 26, 402, '同法：一芯多壳 · db-per-tenant · center_client / Nacos', { size: 10, fill: P.muted })
  // 中间「无连接」
  const mx = lx + pw + (rx - lx - pw) / 2
  b += LINE(mx, 150, mx, 400, { stroke: P.critical, sw: 1.4, dash: '5 5', marker: false })
  b += `<circle cx="${mx}" cy="248" r="26" fill="${P.critical}" fill-opacity="0.10" stroke="${P.critical}" stroke-opacity="0.5" stroke-width="1.4"/>`
  b += T(mx, 244, '✗', { size: 18, w: 800, anchor: 'middle', fill: P.critical })
  b += T(mx, 285, '尚无', { size: 11, w: 800, anchor: 'middle', fill: P.critical })
  b += T(mx, 300, '连接', { size: 11, w: 800, anchor: 'middle', fill: P.critical })
  // 底部落差
  b += R(34, 442, W - 68, 0, { rx: 0 })
  return doc(W, H, b)
}

// ════════ 图2 · 三条接入路径 ════════
function figOptions () {
  const W = 980, H = 560
  const x = 34, w = W - 68
  let b = titleBlk(W, '三条接入路径 · 各有取舍',
    'flow 侧接缝已具备；从「零核改」到「最语义化」到「跨进程」，按需选择')
  const opts = [
    [P.aqua, 'A · serviceTask + HttpDelegate', '零引擎改动 · 今天即可', [
      ['flow 节点', 'serviceTask'], ['经', 'RulesEngineDelegate 适配器'], ['调', 'POST /decisions/{key}/evaluate'], ['变量↔input/output 映射', ''],
    ], ['✓ 最快最低风险 · 复用 cmx-service-rpc 鉴权', '✓ 可同步/异步(SKIP-LOCKED)/外部worker', '! 需新增适配器 + 服务目录项', '! businessRuleTask 语义要靠约定'], 'ok'],
    [P.blue, 'B · DecisionProvider 注入接缝', '中等改动 · 最干净语义', [
      ['flow 节点', 'businessRuleTask'], ['经', '新 DecisionProvider trait'], ['默认', '内置(向后兼容)'], ['规则后端', 'HTTP 或 内嵌'],
    ], ['✓ 与 AssigneeResolver/SubflowRouter 同构', '✓ 保留单节点·变量进出语义', '✓ decision_key 直接指向 rules', '! 需在引擎唯一调用点引入 trait'], 'ok'],
    [P.violet, 'C · external-worker 按 topic', '跨进程 · 规则自持', [
      ['flow 节点', 'serviceTask type=external-worker'], ['topic', 'rules-eval'], ['规则侧', 'worker 拉取 acquire_async_jobs'], ['回调', 'complete / fail'],
    ], ['✓ 规则在自己进程内跑', '✓ SKIP-LOCKED 可靠 + 重试/死信', '! 需规则侧起 worker', '! 链路最长、延迟最高'], 'warn'],
  ]
  const cw = (w - 2 * 14) / 3
  opts.forEach((o, i) => {
    const cx = x + i * (cw + 14)
    b += R(cx, 74, cw, 420, { rx: 12, fill: o[0], fop: 0.06, stroke: o[0], sop: 0.34, sw: 1.3 })
    b += R(cx, 74, cw, 5, { rx: 2, fill: o[0] })
    b += T(cx + 14, 100, o[1], { size: 12.5, w: 800, fill: o[0] })
    b += T(cx + 14, 122, o[2], { size: 10, fill: P.ink2 })
    // 流水小节点
    let yy = 148
    o[3].forEach((step) => {
      b += R(cx + 14, yy, cw - 28, 34, { rx: 7, fill: P.plane, stroke: P.border, sw: 1 })
      b += T(cx + 24, yy + 15, step[0], { size: 9.5, w: 700, fill: o[0] })
      b += T(cx + 24, yy + 28, step[1], { size: 9.5, fill: P.ink, mono: /[A-Za-z]/.test(step[1]) && !/[一-鿿]/.test(step[1]) })
      yy += 40
    })
    // 取舍
    b += LINE(cx + 14, yy + 4, cx + cw - 14, yy + 4, { marker: false, stroke: o[0], sw: 0.8, dash: '3 3' })
    o[4].forEach((t, j) => {
      const isPro = t.startsWith('✓')
      b += T(cx + 16, yy + 24 + j * 18, t, { size: 9.6, fill: isPro ? P.green : P.serious })
    })
  })
  // 底部：+ 内嵌库选项
  b += R(x, 504, w, 0, { rx: 0 })
  return doc(W, H, b)
}

// ════════ 图3 · 推荐目标架构 ════════
function figTarget () {
  const W = 980, H = 540
  const x = 40, w = W - 80
  let b = titleBlk(W, '推荐目标架构 · DecisionProvider 接缝 + HTTP 优先',
    'rules 成为决策的「真相之源」；flow 经统一接缝调用；两种后端可切换；trace 回写流程历史')
  // flow 侧
  b += R(x, 76, 300, 250, { rx: 12, fill: P.aqua, fop: 0.06, stroke: P.aqua, sop: 0.34, sw: 1.3 })
  b += R(x, 76, 300, 5, { rx: 2, fill: P.aqua })
  b += T(x + 16, 104, 'cmx-flowengine', { size: 14, w: 800, fill: P.aqua })
  b += cell(x + 16, 118, 268, 44, P.aqua, 'businessRuleTask', 'decision_key → rules 决策')
  b += LINE(x + 150, 162, x + 150, 178, { marker: true })
  b += R(x + 16, 180, 268, 60, { rx: 9, fill: P.blue, fop: 0.12, stroke: P.blue, sop: 0.4, sw: 1.4 })
  b += T(x + 150, 202, '① 新接缝：DecisionProvider', { size: 12, w: 800, anchor: 'middle', fill: P.blue550 })
  b += T(x + 150, 222, '注入式(同 AssigneeResolver/SubflowRouter)', { size: 9.5, anchor: 'middle', fill: P.ink2 })
  b += R(x + 16, 250, 130, 60, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 81, 270, 'Http 后端', { size: 10.5, w: 800, anchor: 'middle', fill: P.blue })
  b += T(x + 81, 286, '默认·独立部署', { size: 8.6, anchor: 'middle', fill: P.ink2 })
  b += T(x + 81, 300, '可独立扩缩/版本', { size: 8.6, anchor: 'middle', fill: P.muted })
  b += R(x + 154, 250, 130, 60, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 219, 270, '内嵌后端', { size: 10.5, w: 800, anchor: 'middle', fill: P.violet })
  b += T(x + 219, 286, '可选·µs 级/离线', { size: 8.6, anchor: 'middle', fill: P.ink2 })
  b += T(x + 219, 300, 'path 依赖 leaf 三件套', { size: 8.6, anchor: 'middle', fill: P.muted })
  // 中间调用
  b += PATH(`M${x + 300},210 C${x + 340},210 ${x + 360},210 ${x + 400},210`, { stroke: P.good, sw: 2, marker: true })
  b += T(x + 350, 198, 'evaluate', { size: 10, w: 700, anchor: 'middle', fill: P.good })
  b += T(x + 350, 228, '②', { size: 12, w: 800, anchor: 'middle', fill: P.good })
  // rules 侧
  const rx = x + 404
  b += R(rx, 76, w - 404, 250, { rx: 12, fill: P.violet, fop: 0.06, stroke: P.violet, sop: 0.34, sw: 1.3 })
  b += R(rx, 76, w - 404, 5, { rx: 2, fill: P.violet })
  b += T(rx + 16, 104, 'cmx-rulesengine · 决策真相之源', { size: 14, w: 800, fill: P.violet })
  b += cell(rx + 16, 118, w - 404 - 32, 40, P.violet, 'POST /api/rules/v1/decisions/{key}/evaluate', '{input} → {output, trace, logId, timingUs}')
  const feats = ['JDM 图 + 11 命中策略', 'S-FEEL', 'gap/overlap', '逐节点 trace', '发布/版本/激活', 'db-per-tenant', '决策表+图设计器', '仿真台+审计']
  b += chipFlow(rx + 16, 172, rx + w - 404 - 16, feats, P.violet, { size: 10 }).svg
  b += R(rx + 16, 250, w - 404 - 32, 60, { rx: 9, fill: P.good, fop: 0.08, stroke: P.good, sop: 0.3, sw: 1 })
  b += T(rx + 28, 272, '设计态：决策在 rules 设计器编写（表+图+FEEL+仿真）', { size: 10, w: 700, fill: P.green })
  b += T(rx + 28, 290, 'flow 节点仅「选一个 decision_key」；flow 自带 designer 降级为选择器/查看', { size: 9.5, fill: P.ink2 })
  // 回写 trace（独立整条，不压线）
  b += R(x, 338, w, 28, { rx: 8, fill: P.magenta, fop: 0.10, stroke: P.magenta, sop: 0.32, sw: 1 })
  b += T(x + 16, 356, '③ 回写', { size: 11, w: 800, fill: P.magenta })
  b += T(x + 74, 356, 'rules 返回的 logId + 归因 trace 存入 flow 实例/变量历史 → 决策在流程内可解释、可审计、可回放', { size: 10.5, fill: P.ink2 })
  // 底部鉴权/租户
  b += R(x, 376, w, 56, { rx: 10, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 16, 397, '协议已就位：flow 的出站鉴权（X-API-Key 映射租户 + X-Delegated-User-Token 归属真人）正是 rules /evaluate 接受的头。', { size: 10.3, w: 600, fill: P.ink2 })
  b += T(x + 16, 416, '租户：两侧均 db-per-tenant，租户名须对齐（flow tenant → rules X-Tenant / api-key 映射）；业务失败=HTTP 200 且 code≠0，须按 code 判。', { size: 10.3, fill: P.muted })
  // 关键结论
  b += R(x, 442, w, 72, { rx: 10, fill: P.ink, fop: 1 })
  b += T(x + 20, 466, '为什么选 B(接缝) + HTTP 优先：rules 保持决策系统之源（独立部署/扩缩/版本/审计），flow 只借一个接缝；', { size: 11, w: 600, fill: '#e8f0fc' })
  b += T(x + 20, 487, '内嵌后端留给「µs 级/离线/边缘」场景。A(delegate) 作为 P1 最小可用先落地，B 为最终形态，二者不冲突、可平滑演进。', { size: 11, w: 600, fill: '#e8f0fc' })
  return doc(W, H, b)
}

// ════════ 图4 · 调用契约与映射 ════════
function figMapping () {
  const W = 980, H = 470
  const x = 40, w = W - 80
  let b = titleBlk(W, '调用契约 · flow 变量 ↔ rules facts 的一次往返',
    '集成的关键就是这层「映射适配」——两侧协议已高度对齐，只差一个转换器')
  // 左 flow 变量
  b += R(x, 78, 230, 150, { rx: 11, fill: P.aqua, fop: 0.08, stroke: P.aqua, sop: 0.34, sw: 1.2 })
  b += R(x, 78, 230, 4, { rx: 2, fill: P.aqua })
  b += T(x + 16, 100, 'flow 实例变量', { size: 12, w: 800, fill: P.aqua })
  b += T(x + 16, 118, '(Variables · JSON)', { size: 9.5, fill: P.muted, mono: true })
  b += R(x + 14, 128, 202, 88, { rx: 7, fill: P.surface, stroke: P.border, sw: 1 })
  b += T(x + 24, 148, '{ "amount": 5000,', { size: 10, fill: P.ink, mono: true })
  b += T(x + 24, 166, '  "country": "CN",', { size: 10, fill: P.ink, mono: true })
  b += T(x + 24, 184, '  "level": "gold" }', { size: 10, fill: P.ink, mono: true })
  b += T(x + 24, 206, '来自网关/前序节点/单据', { size: 9, fill: P.muted })
  // 适配器（中）
  b += R(x + 262, 78, w - 524, 150, { rx: 12, fill: P.blue, fop: 0.10, stroke: P.blue, sop: 0.4, sw: 1.4 })
  b += R(x + 262, 78, w - 524, 5, { rx: 2, fill: P.blue })
  b += T(x + 262 + (w - 524) / 2, 102, '映射适配器', { size: 12.5, w: 800, anchor: 'middle', fill: P.blue550 })
  b += T(x + 262 + (w - 524) / 2, 120, 'DecisionProvider / Delegate', { size: 9, anchor: 'middle', fill: P.ink2, mono: true })
  const mid = x + 262 + (w - 524) / 2
  b += T(mid, 146, '① 选变量子集 → input', { size: 10, anchor: 'middle', fill: P.ink })
  b += T(mid, 165, '② 附 X-Tenant / X-API-Key', { size: 10, anchor: 'middle', fill: P.ink })
  b += T(mid, 184, '③ 解 ApiResp(code==0?)', { size: 10, anchor: 'middle', fill: P.ink })
  b += T(mid, 203, '④ output → merge 回变量', { size: 10, anchor: 'middle', fill: P.ink })
  // 右 rules
  b += R(x + w - 230, 78, 230, 150, { rx: 11, fill: P.violet, fop: 0.08, stroke: P.violet, sop: 0.34, sw: 1.2 })
  b += R(x + w - 230, 78, 230, 4, { rx: 2, fill: P.violet })
  b += T(x + w - 214, 100, 'rules /evaluate', { size: 12, w: 800, fill: P.violet })
  b += T(x + w - 214, 118, '(input → output+trace)', { size: 9.5, fill: P.muted, mono: true })
  b += R(x + w - 216, 128, 202, 88, { rx: 7, fill: P.surface, stroke: P.border, sw: 1 })
  b += T(x + w - 206, 148, 'input: {amount,country', { size: 9.5, fill: P.ink, mono: true })
  b += T(x + w - 206, 166, '       ,level}', { size: 9.5, fill: P.ink, mono: true })
  b += T(x + w - 206, 186, '→ output:{discount,', { size: 9.5, fill: P.green, mono: true })
  b += T(x + w - 206, 202, '   tier} + trace + logId', { size: 9.5, fill: P.green, mono: true })
  // 箭头
  b += PATH(`M${x + 230},150 L${x + 260},150`, { stroke: P.blue, sw: 2, marker: true })
  b += PATH(`M${x + 262 + (w - 524)},150 L${x + w - 232},150`, { stroke: P.good, sw: 2, marker: true })
  b += T((x + 230 + x + 262) / 2 + 8, 138, 'facts', { size: 8.5, anchor: 'middle', fill: P.blue })
  b += PATH(`M${x + w - 232},196 L${x + 262 + (w - 524)},196`, { stroke: P.magenta, sw: 1.6, marker: true, dash: '4 3' })
  b += PATH(`M${x + 260},196 L${x + 232},196`, { stroke: P.magenta, sw: 1.6, marker: true, dash: '4 3' })
  b += T(mid, 236, 'output + logId + trace 回流', { size: 9, anchor: 'middle', fill: P.magenta })
  // 差异与对策（全宽单列，避免串行重叠）
  const gy = 258
  b += R(x, gy, w, 152, { rx: 11, fill: P.warning, fop: 0.06, stroke: P.warning, sop: 0.28, sw: 1.2 })
  b += T(x + 16, gy + 24, '需在契约里定清的四件事（皆有现成对策，非阻塞）', { size: 12.5, w: 800, fill: P.serious })
  const items = [
    ['表达式语言不通用', 'flow ${a>b} vs rules FEEL if/then —— 但两侧只交换 JSON、各自解析各自 DSL，运行期天然规避；作者态各用各的设计器'],
    ['决策标识与版本', '约定 decision_key 命名空间；HTTP 只评「激活版」，要钉住具体版本走内嵌库或新增带版本的评估路由'],
    ['租户对齐', '两侧均 db-per-tenant，flow 的 tenant 必须能映射到 rules 的 X-Tenant / api-key→租户（否则查不到决策）'],
    ['失败与超时', 'rules 业务失败 = HTTP 200 且 code≠0；映射为 flow 决策错误→Incident/错误边界；重规则走异步 serviceTask / 外部 worker'],
  ]
  items.forEach((it, i) => {
    const yy = gy + 48 + i * 26
    b += `<circle cx="${x + 20}" cy="${yy - 4}" r="2.6" fill="${P.serious}"/>`
    b += T(x + 30, yy, it[0] + '：', { size: 10.2, w: 800, fill: P.ink })
    b += T(x + 30 + wOf(it[0] + '：', 10.2), yy, it[1], { size: 9.6, fill: P.ink2 })
  })
  return doc(W, H, b)
}

// ════════ 图5 · 分阶段落地路线 ════════
function figRoadmap () {
  const W = 980, H = 452
  const x = 40, w = W - 80
  let b = titleBlk(W, '分阶段落地路线 · 每步独立可验证、可回退',
    'P0 只对齐契约不写码；P1 零核改先跑通；P2 落地最终接缝；P3/P4 收敛设计态与可选内嵌')
  const phases = [
    [P.muted, 'P0', '契约对齐', '不写码', ['租户名映射', 'decision_key 命名空间', '变量↔input/output 映射', '错误/超时/回写策略', '定 HTTP 优先']],
    [P.aqua, 'P1', '最小可用', '零引擎改动', ['RulesEngineDelegate 适配器', 'serviceTask 调 rules', '同步先跑通一条链', 'cmx-service-rpc 服务目录项', '证明闭环·无核风险']],
    [P.blue, 'P2', '语义化接缝', '中等·最终形态', ['引入 DecisionProvider trait', '默认内置(兼容)', 'HttpRules 后端按 key', 'logId+trace 回写历史', '弃用/降级内置决策表']],
    [P.green, 'P3', '设计态融合', '前端', ['flow 节点选 rules 决策', '作者在 rules 设计器', 'flow designer 降为选择器', '门户可跳转 rules 编辑', '仿真/审计归 rules']],
    [P.violet, 'P4', '可选增强', '按需', ['内嵌后端(µs/离线)', '异步/外部worker 跑重规则', '版本钉住', '数据权限接入', '灰度扩自主度']],
  ]
  const n = phases.length, cw = (w - (n - 1) * 12) / n
  phases.forEach((p, i) => {
    const cx = x + i * (cw + 12)
    b += R(cx, 76, cw, 322, { rx: 12, fill: p[0], fop: 0.08, stroke: p[0], sop: 0.34, sw: 1.3 })
    b += R(cx, 76, cw, 5, { rx: 2, fill: p[0] })
    b += `<circle cx="${cx + 28}" cy="${104}" r="16" fill="${p[0]}" fill-opacity="0.18" stroke="${p[0]}" stroke-opacity="0.5"/>`
    b += T(cx + 28, 109, p[1], { size: 13, w: 800, anchor: 'middle', fill: p[0] })
    b += T(cx + 52, 100, p[2], { size: 12, w: 800, fill: P.ink })
    b += T(cx + 52, 116, p[3], { size: 9, fill: p[0] })
    b += LINE(cx + 14, 128, cx + cw - 14, 128, { marker: false, stroke: p[0], sw: 0.8, dash: '3 3' })
    p[4].forEach((it, j) => {
      const yy = 150 + j * 32
      const last = j === p[4].length - 1
      b += `<circle cx="${cx + 20}" cy="${yy - 4}" r="2.4" fill="${last ? p[0] : P.muted}"/>`
      // 换行
      const maxw = cw - 38
      if (wOf(it, 9.8) > maxw) {
        const midc = Math.ceil(it.length * maxw / wOf(it, 9.8))
        b += T(cx + 30, yy - 5, it.slice(0, midc), { size: 9.6, w: last ? 700 : 400, fill: last ? p[0] : P.ink })
        b += T(cx + 30, yy + 8, it.slice(midc), { size: 9.6, w: last ? 700 : 400, fill: last ? p[0] : P.ink })
      } else {
        b += T(cx + 30, yy, it, { size: 9.8, w: last ? 700 : 400, fill: last ? p[0] : P.ink })
      }
    })
    if (i < n - 1) b += LINE(cx + cw + 1, 230, cx + cw + 11, 230, { stroke: P.muted, sw: 1.4 })
  })
  // 底部原则
  b += R(x, 410, w, 0, { rx: 0 })
  return doc(W, H, b)
}

// ════════ 图6 · 方案A 运行时调用序列 ════════
function figARuntime () {
  const W = 980, H = 600
  const x = 40, w = W - 80
  let b = titleBlk(W, '方案A · 运行时调用序列（HTTP 默认）',
    '一个 rules 决策 = 一个 serviceTask + RulesEngineDelegate；businessRuleTask 保留为轻量兜底')
  // 两层分工
  const hw = (w - 16) / 2
  b += R(x, 74, hw, 58, { rx: 10, fill: P.aqua, fop: 0.10, stroke: P.aqua, sop: 0.36, sw: 1.3 })
  b += R(x, 74, 4, 58, { rx: 2, fill: P.aqua })
  b += T(x + 16, 96, '真决策：serviceTask + RulesEngineDelegate', { size: 12, w: 800, fill: P.aqua })
  b += T(x + 16, 115, '→ cmx-rulesengine（11 策略 / JDM 图 / FEEL / trace）· 跨服务 HTTP', { size: 10, fill: P.ink2 })
  b += R(x + hw + 16, 74, hw, 58, { rx: 10, fill: P.warning, fop: 0.10, stroke: P.warning, sop: 0.34, sw: 1.2 })
  b += R(x + hw + 16, 74, 4, 58, { rx: 2, fill: P.warning })
  b += T(x + hw + 32, 96, '轻量兜底：businessRuleTask + 内置 DecisionTable', { size: 12, w: 800, fill: P.serious })
  b += T(x + hw + 32, 115, '→ 简单内联决策（FIRST/COLLECT）· 同进程 · 原样保留、不动', { size: 10, fill: P.ink2 })
  // 序列 6 步
  const steps = [
    ['令牌到达 serviceTask', 'delegate="rules:creditScoring"（同步；重规则加 flowable:async="true"）'],
    ['RulesEngineDelegate.execute(ctx)', '读实例变量 → input（P1 默认全量；裁子集为后续优化）'],
    ['cmx-service-rpc → POST /api/rules/v1/decisions/{key}/evaluate', '自动带 X-API-Key + X-Delegated-User-Token；附 X-Tenant · body {input, options{trace,log}}'],
    ['rules 评估「激活版」', '返回 ApiResp{ code, data:{ output, logId, trace, timingUs } }'],
    ['判 code==0 → ctx.variables.merge(output)', '并把 logId / trace 存入 __decisions 变量 → 决策在流程内可解释、可审计'],
    ['令牌 choose_target 续流', '决策结果驱动后续网关 / 节点'],
  ]
  let y = 150
  steps.forEach((s, i) => {
    b += R(x, y, w, 40, { rx: 8, fill: i === 4 ? P.good : P.blue, fop: i === 4 ? 0.08 : 0.05, stroke: i === 4 ? P.good : P.blue, sop: 0.26, sw: 1 })
    b += `<circle cx="${x + 22}" cy="${y + 20}" r="13" fill="${i === 4 ? P.good : P.blue}" fill-opacity="0.16" stroke="${i === 4 ? P.good : P.blue}" stroke-opacity="0.5"/>`
    b += T(x + 22, y + 25, String(i + 1), { size: 12, w: 800, anchor: 'middle', fill: i === 4 ? P.green : P.blue550 })
    b += T(x + 44, y + 18, s[0], { size: 11.5, w: 800, fill: P.ink })
    b += T(x + 44, y + 33, s[1], { size: 9.4, fill: P.ink2 })
    if (i < steps.length - 1) b += LINE(x + 22, y + 40, x + 22, y + 46, { stroke: P.muted, sw: 1.2 })
    y += 46
  })
  // 错误与超时
  y += 6
  b += R(x, y, w, 80, { rx: 10, fill: P.critical, fop: 0.06, stroke: P.critical, sop: 0.28, sw: 1.2 })
  b += T(x + 16, y + 22, '错误与超时处理（按 code / HTTP / 模式分流）', { size: 12, w: 800, fill: P.critical })
  b += T(x + 16, y + 43, '· 业务失败（HTTP 200 且 code≠0）→ DelegateError::Bpmn{code:"decisionFailed"} → 错误边界事件（业务可捕获、走补偿路径）', { size: 9.8, fill: P.ink2 })
  b += T(x + 16, y + 60, '· 未知 key(404)/鉴权(401)/配置错 → Generic → Incident（运维重试）　·　超时/连接失败 → 同步:Incident；异步:SKIP-LOCKED 重试(3×/30s)→死信', { size: 9.8, fill: P.ink2 })
  return doc(W, H, b)
}

// ════════ 图7 · 错误 × 模式 处理矩阵 ════════
function figAMatrix () {
  const W = 940, H = 384
  const x = 40
  let b = titleBlk(W, '错误 × 执行模式 · 处理矩阵',
    '同一决策调用，按「返回类型 × 同步/异步」决定落到续流 / 错误边界 / Incident / 死信')
  const rows = [
    ['成功（code==0）', ['merge output + 续流', 'ok'], ['merge output + 续流', 'ok']],
    ['业务失败（HTTP 200, code≠0）', ['Bpmn → 错误边界', 'warn'], ['Bpmn → 错误边界*', 'warn']],
    ['未知 key（HTTP 404）', ['Generic → Incident', 'no'], ['Incident', 'no']],
    ['鉴权失败（HTTP 401）', ['Generic → Incident', 'no'], ['Incident', 'no']],
    ['超时 / 连接失败', ['Generic → Incident', 'no'], ['自动重试(3×/30s)→死信', 'warn']],
  ]
  const dimW = 300, cw = (W - 2 * x - dimW) / 2, headY = 74, rowH = 40, y0 = headY + 34
  b += R(x, headY, dimW, 30, { rx: 6, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 12, headY + 20, '返回类型 ＼ 执行模式', { size: 11, w: 800, fill: P.ink2 })
  ;[['同步 serviceTask', P.aqua], ['异步 serviceTask（flowable:async）', P.violet]].forEach((h, i) => {
    const cx = x + dimW + i * cw
    b += R(cx + 2, headY, cw - 4, 30, { rx: 6, fill: h[1], fop: 0.14, stroke: h[1], sop: 0.36, sw: 1 })
    b += T(cx + cw / 2, headY + 20, h[0], { size: 11, w: 800, anchor: 'middle', fill: h[1] })
  })
  const gT = { ok: P.good, warn: P.warning, no: P.critical }
  rows.forEach((r, ri) => {
    const ry = y0 + ri * rowH
    b += R(x, ry, dimW, rowH - 4, { rx: 6, fill: P.plane, stroke: P.border, sw: 1 })
    b += T(x + 12, ry + rowH / 2, r[0], { size: 10.5, w: 700, fill: P.ink })
    for (let c = 0; c < 2; c++) {
      const [txt, g] = r[c + 1], cx = x + dimW + c * cw, hue = gT[g]
      b += R(cx + 2, ry, cw - 4, rowH - 4, { rx: 6, fill: hue, fop: g === 'no' ? 0.08 : 0.14, stroke: hue, sop: 0.34, sw: 1 })
      b += R(cx + 2, ry, 3, rowH - 4, { rx: 1.5, fill: hue })
      b += T(cx + cw / 2 + 2, ry + rowH / 2, txt, { size: 10, w: 600, anchor: 'middle', fill: P.ink })
    }
  })
  const ny = y0 + rows.length * rowH + 8
  b += R(x, ny, W - 2 * x, 34, { rx: 8, fill: P.plane, stroke: P.border, sw: 1 })
  b += T(x + 14, ny + 15, '* 异步模式下 delegate 失败默认走「重试/死信」而非错误边界（引擎约定）；若需异步业务失败也走错误边界，需在 P2 接缝层显式路由。', { size: 9.6, fill: P.ink2 })
  b += T(x + 14, ny + 29, '超时阈值走 cmx-service-rpc 配置（建议 2–5s）；大图/Rhai 重规则一律用 flowable:async 以免阻塞令牌线程。', { size: 9.6, fill: P.muted })
  return doc(W, H, b)
}

// ════════ 图8 · 四项决策定案 + 配置基线 ════════
function figADecisions () {
  const W = 980, H = 486
  const x = 40, w = W - 80
  let b = titleBlk(W, '四项决策定案 · P1 配置基线（按推荐值敲定）',
    '开放项全部收敛；本设计进入「实现就绪」—— 改动集中在 flow 侧一个适配器 + 一段装配 + 配置')
  const rows = [
    ['1', '租户契约', 'rules off 模式 + flow 出站带 X-Tenant', '单/默认租户零配置即通；多租户或生产再切 api-key→租户映射'],
    ['2', '业务失败落点', 'DelegateError::Bpmn{ code:"decisionFailed" }', '可挂错误边界优雅接住(转人工/补偿)；无边界则自然回落 Incident'],
    ['3', 'decisionKey 暴露', '随定义加载/部署自动扫描 rules: 前缀注册', '免人工维护 allowlist；覆盖启动装载与运行时热部署'],
    ['4', 'trace 回写粒度', '默认只存 logId（可 =full 存全量）', 'rules 侧已按 log:true 存全量 trace，flow 存 logId 作指针即可、省空间'],
  ]
  let y = 76
  rows.forEach((r) => {
    b += R(x, y, w, 58, { rx: 9, fill: P.good, fop: 0.05, stroke: P.good, sop: 0.24, sw: 1 })
    b += `<circle cx="${x + 24}" cy="${y + 29}" r="14" fill="${P.good}" fill-opacity="0.16" stroke="${P.good}" stroke-opacity="0.5"/>`
    b += T(x + 24, y + 34, r[0], { size: 13, w: 800, anchor: 'middle', fill: P.green })
    b += T(x + 48, y + 25, r[1], { size: 11.5, w: 800, fill: P.ink })
    b += T(x + 48, y + 44, '定案', { size: 9, w: 700, fill: P.green })
    // 定案值框
    b += R(x + 190, y + 10, 372, 38, { rx: 7, fill: P.good, fop: 0.13, stroke: P.good, sop: 0.34, sw: 1 })
    b += T(x + 202, y + 33, r[2], { size: 10.6, w: 700, fill: P.green })
    // 理由
    b += T(x + 578, y + 25, '理由', { size: 8.6, w: 700, fill: P.muted })
    b += T(x + 578, y + 42, r[3], { size: 9.4, fill: P.ink2 })
    y += 66
  })
  // 配置基线
  b += R(x, y + 4, w, 132, { rx: 10, fill: P.ink, fop: 1 })
  b += T(x + 20, y + 28, '配置基线（P1 · 默认关闭，置 http 即启用）', { size: 12.5, w: 800, fill: '#e8f0fc' })
  const cfg = [
    'FLOW_RULES_MODE=http          # 出厂 off（零回归）；http 启用集成',
    'FLOW_RULES_SERVICE=rules      # cmx-service-rpc 服务目录键',
    'FLOW_RULES_TRACE_PERSIST=logid',
    '[service_rpc.services]  rules = { url = "http://…:8094", discovery = "cmx-rulesengine" }',
    'rules 侧：auth.mode=off（P1）；flow 出站附 X-Tenant=<当前租户>（+ 自动带 X-API-Key / 用户令牌）',
  ]
  cfg.forEach((c, i) => b += T(x + 22, y + 52 + i * 16, c, { size: 10, fill: i < 4 ? '#a7c4e8' : '#94a3b8', mono: true }))
  return doc(W, H, b)
}

const FIGS = { 'fig-current': figCurrent, 'fig-options': figOptions, 'fig-target': figTarget, 'fig-mapping': figMapping, 'fig-roadmap': figRoadmap, 'fig-a-runtime': figARuntime, 'fig-a-matrix': figAMatrix, 'fig-a-decisions': figADecisions }

function main () {
  for (const [k, fn] of Object.entries(FIGS)) {
    const svg = fn(); writeFileSync(join(DIR, `${k}.svg`), svg)
    console.log(`wrote ${k}.svg (${(svg.length / 1024).toFixed(1)} KiB)`)
  }
}
main()
