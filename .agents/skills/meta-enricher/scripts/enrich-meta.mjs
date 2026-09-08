#!/usr/bin/env node
// 为 CMX 字典/单据元数据补全 edit / display / width / required / visible / frozen 等列属性。
// 严格按 packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js 的 EDIT_MODES 规范值域。
// 严格按 docs/表格组件编辑渲染体系与三元定义缺口分析.md 定义的 display 域结构。
// 运行：node enrich-meta.mjs <in> <out>  (幂等：已存在 edit/display 不覆盖)

import { readFile, writeFile } from 'node:fs/promises'
import { argv, exit } from 'node:process'

const inFile = argv[2]
const outFile = argv[3]
if (!inFile || !outFile) {
  console.error('Usage: node enrich-meta.mjs <in> <out>')
  exit(2)
}

// ---------- 规范值域（来自 cmx-field-uicontrol.js EDIT_MODES） ----------
const MODE = {
  TEXT:      'cmx-text-input',
  TEXTAREA:  'cmx-textarea-input',
  RICHTEXT:  'cmx-richtext-input',
  NUMBER:    'cmx-number-input',
  DATE:      'cmx-date-input',
  DATETIME:  'cmx-datetime-input',
  CHECKBOX:  'checkbox',
  SELECT:    'select',
  REF:       'ref',
  COMBO:     'combo',
  IGNITE:    'ignite-combo',
  DICTSEL:   'cmx-dict-select', // 数据字典选择
  IMAGE:     'image',
  VIDEO:     'video',
  READONLY:  'readonly',
  NONE:      'none',
}

// ---------- 状态字段 → badge + 默认配色 ----------
const DOC_STATUS_BADGE = {
  draft:      { text: '草稿',     color: '#7f7f7f' },
  posted:     { text: '已过账',   color: '#2b7a2b' },
  reversed:   { text: '已冲销',   color: '#a04545' },
  approved:   { text: '已审核',   color: '#1f6feb' },
  rejected:   { text: '已驳回',   color: '#a04545' },
  closed:     { text: '已关闭',   color: '#5a5a5a' },
  parked:     { text: '预制',     color: '#c47c00' },
  simulating: { text: '模拟',     color: '#6a4ea0' },
}

// ---------- edit.mode 推导 ----------
function pickEdit(field, ctx) {
  const dt = field.dataType
  const cap = (field.caption?.zh_CN || '').trim()
  const id = field.id
  const hasRef = !!field.refDict

  // 复选：TINYINT 且 caption 含「是否/启用/允许/标记」等
  if (dt === 'TINYINT' && /^(是否|启用|允许|标记)/.test(cap)) {
    return { mode: MODE.CHECKBOX }
  }

  // 主键：永远 readonly
  if (field.isPrimaryKey === 1 || id === 'id') {
    return { mode: MODE.READONLY }
  }

  // 系统审计字段：不可编辑
  if (/^(create_by|create_time|update_by|update_time|delete_flag|row_version|timestamp)$/.test(id)) {
    return { mode: MODE.NONE }
  }

  // 内部关系 ID（无 refDict 的 *_id/parent_id/upper_id/ancestor_id/descendant_id）→ readonly
  if (/(_id|parent_id|upper_id|ancestor_id|descendant_id)$/.test(id) && !hasRef) {
    return { mode: MODE.READONLY }
  }

  // 引用字典
  if (hasRef) {
    // 多值字段（types/required/optional/suppressed 列表）→ 多选字典
    if (/_types?$|required_fields|optional_fields|suppressed_fields|allowed_/.test(id)) {
      return { mode: MODE.DICTSEL, multiple: true }
    }
    // 自分级字典的 parent_id / 自引用：弹树选 → cmx-dict-select + parent
    if (id === 'parent_id' && ctx.selfHierarchy) {
      return { mode: MODE.DICTSEL, parent: id }
    }
    // 自分级字典（segment/fs_version/cons_org）→ 树形
    if (ctx.treeRefDicts?.includes(field.refDict)) {
      return { mode: MODE.DICTSEL, parent: 'parent_id' }
    }
    // 普通外键 → 字典选择（ref 缺编辑器，按缺口分析用 cmx-dict-select）
    return { mode: MODE.DICTSEL }
  }

  // 引用日期
  if (dt === 'DATE') return { mode: MODE.DATE }
  if (dt === 'DATETIME') return { mode: MODE.DATETIME }

  // 数字
  if (dt === 'INT' || dt === 'BIGINT' || dt === 'TINYINT' || dt === 'DECIMAL' || dt === 'NUMBER') {
    return { mode: MODE.NUMBER }
  }

  // 文本/多行
  if (dt === 'TEXT') {
    return { mode: field.fieldLength > 200 ? MODE.TEXTAREA : MODE.TEXTAREA }
  }

  // 显式枚举值 → 静态 select。enumValues 兼容 [{value,label}] 对象数组与 string[]/标量两种形态。
  if (Array.isArray(field.enumValues) && field.enumValues.length > 0) {
    return {
      mode: MODE.SELECT,
      options: field.enumValues.map((v) => (v && typeof v === 'object')
        ? { value: v.value, label: v.label != null ? v.label : v.value }
        : { value: v, label: String(v) }),
    }
  }

  return { mode: MODE.TEXT }
}

// ---------- display 推导 ----------
// display.mode 合法值：['','text','number','badge','link','icon']（来自 cmx-field-schema.js 的 display.mode options；actions 属页面级不涉及）
//   注：'actions'（操作列）属页面级配置，不在元数据 display.mode 值域内。
//   text  → 原样字符串（format 子项由用户手动配 date/datetime 模板）
//   number→ 数值列（脚本只补 decimalDigits/thousandSeparator/zeroAsBlank/negativeColor，
//                   format 子项留给用户手动配 thousands/percent/currency:¥/date:YYYY-MM-DD）
//   badge → 徽章（status 等状态字段 + badgeMap）
//   link  → 链接
//   icon  → 图标
//
// 幂等性说明：display.format 在 number / text 模式下都属于「用户自定义区」，
// 一旦写入会被视为「用户已配置」，再跑脚本会保持不变。所以脚本不主动写 format。
function pickDisplay(field) {
  const dt = field.dataType
  const cap = (field.caption?.zh_CN || '').trim()
  const id = field.id

  // 主键 / 内部关系 ID → 默认 text（visible 放顶层）
  if (id === 'id' || field.isPrimaryKey === 1) {
    return { mode: 'text' }
  }
  if (/(_id|parent_id|upper_id|ancestor_id|descendant_id)$/.test(id) && dt === 'BIGINT' && !field.refDict) {
    return { mode: 'text' }
  }

  // 状态字段 → badge（仅非 TINYINT：TINYINT 多为 0/1 布尔，走 text 即可，
  // 业务单据状态通常是 VARCHAR/INT，如 doc_status=draft/posted/reversed）
  if (dt !== 'TINYINT' && (id === 'doc_status' || /_status$|status$|batch_status|state$/.test(id))) {
    return { mode: 'badge', badgeMap: DOC_STATUS_BADGE, align: 'center' }
  }

  // 日期 / 日期时间
  if (dt === 'DATE') {
    return { mode: 'text', format: 'date:YYYY-MM-DD', align: 'center' }
  }
  if (dt === 'DATETIME') {
    return { mode: 'text', format: 'datetime:YYYY-MM-DD HH:mm:ss', align: 'center' }
  }

  // 数值
  if (dt === 'DECIMAL' || dt === 'NUMBER') {
    return pickNumberDisplay(field, cap, id)
  }

  // 整数
  if (dt === 'BIGINT' || dt === 'INT') {
    if (/^(line_no|sort_no|sort_key|level_no|is_leaf|depth|period_no|fiscal_year|行号|序号|期间号)$/.test(id)) {
      return { mode: 'number', decimalDigits: 0, thousandSeparator: true, align: 'right' }
    }
    return { mode: 'text', align: 'left' }
  }

  // TINYINT(0/1)
  if (dt === 'TINYINT') {
    return { mode: 'text', align: 'center' }
  }

  // 长文本
  if (dt === 'TEXT') {
    return { mode: 'text', align: 'left' }
  }

  // 默认
  return { mode: 'text', align: 'left' }
}

function pickNumberDisplay(field, cap, id) {
  const isRate = /(汇率|比例|率)/.test(cap)
  const isPct = /%$/.test(cap) || /(percent|percentage|ownership)/.test(id)
  const isQty = /(数量|件数|张数|天数|期数|层级|期间号|period_no|qty)/.test(cap + id)
  const decimals = Math.max(0, field.decimalDigits ?? 2)

  if (isRate) {
    return {
      mode: 'number',
      decimalDigits: decimals,
      thousandSeparator: false,
      negativeColor: true,
      align: 'right',
    }
  }
  if (isPct) {
    // format:'percent:N' 留给用户手动配（不在脚本里硬写）
    return {
      mode: 'number',
      decimalDigits: decimals,
      align: 'right',
    }
  }
  if (isQty) {
    return {
      mode: 'number',
      decimalDigits: 0,
      thousandSeparator: true,
      align: 'right',
    }
  }
  // 默认金额样式：format:'thousands' 留给用户手动配
  return {
    mode: 'number',
    decimalDigits: decimals,
    thousandSeparator: true,
    zeroAsBlank: true,
    negativeColor: true,
    align: 'right',
  }
}

// ---------- 顶层列属性 ----------
function pickWidth(field) {
  const dt = field.dataType
  const cap = (field.caption?.zh_CN || '').trim()
  const id = field.id

  if (dt === 'DATE') return '130px'
  if (dt === 'DATETIME') return '160px'
  if (dt === 'TINYINT') return '90px'
  if (dt === 'BIGINT') {
    if (/(_id|parent_id|upper_id|ancestor_id|descendant_id)$/.test(id)) return '100px'
    return '120px'
  }
  if (dt === 'INT') return '90px'
  if (dt === 'DECIMAL' || dt === 'NUMBER') {
    if (/(汇率|比例|率|%$)/.test(cap + id)) return '110px'
    return '140px'
  }
  if (dt === 'TEXT') return '280px'
  if (id === 'code' || /_code$|code$/.test(id)) return '140px'
  if (id === 'name' || /_name$/.test(id)) return '180px'
  if (id === 'doc_no' || /_no$|doc_no/.test(id)) return '160px'
  return '140px'
}

function isRequired(field, ctx) {
  const dt = field.dataType
  const id = field.id
  if (field.isPrimaryKey === 1) return false
  if (id === 'parent_id' || id === 'upper_id') return false
  if (id === 'id') return false
  if (/^(create|update)_(by|time)$/.test(id) || id === 'delete_flag') return false
  if (ctx.uniqueKeys?.some((k) => k.includes(id))) return true
  if (['code', 'name', 'doc_no', 'doc_status'].includes(id)) return true
  if (field.nullable === false && !/^(create_by|create_time|delete_flag)$/.test(id)) return true
  return false
}

function pickVisible(field) {
  const id = field.id
  const dt = field.dataType
  if (id === 'id' ) return false
  if (/(_id|parent_id|upper_id|ancestor_id|descendant_id)$/.test(id) && dt === 'BIGINT' && !field.refDict) {
    return false
  }
  return undefined // 默认可见
}

function pickFrozen(field) {
  if (field.isPrimaryKey === 1) return 'left'
  return undefined
}

// ---------- dict-select 的 editSettings 推导 ----------
// 参考 field-edit-display-modes.md §cmx-dict-select（14 个属性）。
// 脚本只补「确定且必要」的 5 个；其余 9 个属于用户配置区（有合理默认或业务自选），不主动写。
//   ✅ 脚本补：helpLayout / hierarchical / dictTitle / showClear / idCol
//   ❌ 不写（用户配置区）：
//     - displayMode（auto/value/code/label/code-label/field）—— 业务自选展示样式
//     - displayTemplate（如 '${code} - ${name}'）—— 配 displayMode 用
//     - idCol/codeCol/labelCol/parentCol —— 大部分字典默认 id/code/name/parent_id 足够
//     - valueField/displayField —— 默认 idCol/labelCol
//     - mruMax/dropdownWidth/dropdownMaxHeight —— UI 尺寸，有默认值 10/480px/360px
//     - placeholder —— 可选，用户按需配
//
// ⚠️ idCol 是「条件补」：当 refDict 指向的字典是 baseFieldSet=dictionaryCommonNoIDFields
// （即该字典物理表没有 id 列、code 即主键）时，必须把 idCol 显式设为 'code'，
// 否则 <cmx-dict-select> 按默认 'id' 查会取不到值。其余字典 idCol 走默认 'id'，脚本不主动写。
function pickDictEditSettings(field, ctx) {
  const cap = (field.caption?.zh_CN || '').trim()
  const isHierarchical = ctx.treeRefDicts?.includes(field.refDict)
  const isRequired = field.required === true || field.edit?.required === true
  const refBaseFS = ctx.baseFieldSets?.get(field.refDict)
  const isRefNoID = refBaseFS === 'dictionaryCommonNoIDFields'

  const es = {}
  // 帮助布局：自分级字典 → grid（treegrid），否则 classify（左分类树+右 grid）
  // grid 适合纯层级数据（段/会计年度变式/合并组织），classify 适合业务字典（科目/客户/供应商）
  es.helpLayout = isHierarchical ? 'grid' : 'classify'
  if (isHierarchical) es.hierarchical = true

  // 主键列：refDict 是 NoID 字典（无 id 列）→ 补 'code'。已有值不覆盖（保留用户意图）
  if (isRefNoID && !es.idCol && field.editSettings?.idCol === undefined) {
    es.idCol = 'code'
  }

  // 字典标题：用 caption 生成（如"选择国家"）
  if (cap) es.dictTitle = `选择${cap}`

  // 清除按钮：非必填时显示（提升体验）
  if (!isRequired) es.showClear = true

  return es
}

// 录入控件值域（同步自 cmx-field-uicontrol.js EDIT_MODES）
const EDIT_MODES_SET = new Set(Object.values(MODE))

function isLegalEditMode (m) {
  return m && EDIT_MODES_SET.has(m)
}

function isLegalDisplayMode (m) {
  // cmx-field-schema.js display.mode options 合法值：'' text number badge link icon
  // 注：'actions'（操作列）属页面级配置，不在元数据 display.mode 值域内
  return !m || m === '' || m === 'text' || m === 'number' || m === 'badge' || m === 'link' || m === 'icon'
}

// ---------- 字段化处理 ----------
function enrichField(field, ctx) {
  // edit 块：源数据 edit.mode 不在合法值域时也重写
  if (!field.edit || !isLegalEditMode(field.edit.mode)) {
    field.edit = pickEdit(field, ctx) || field.edit
  }
  // display 块
  if (!field.display || !isLegalDisplayMode(field.display.mode)) {
    field.display = pickDisplay(field) || field.display
  }
  // editSettings 块：edit.mode='cmx-dict-select' 时维护
  //   - 整体为空 → 全新生成
  //   - 已存在 → 仅补缺失的 idCol（针对 NoID 字典的 refDict），其余属性不覆盖
  if (field.edit?.mode === 'cmx-dict-select') {
    if (!field.editSettings) {
      const es = pickDictEditSettings(field, ctx)
      if (es && Object.keys(es).length > 0) field.editSettings = es
    } else if (field.editSettings.idCol === undefined) {
      // 已存在 editSettings 但缺 idCol：refDict 是 NoID 字典时必须补 'code'
      const refBaseFS = ctx.baseFieldSets?.get(field.refDict)
      if (refBaseFS === 'dictionaryCommonNoIDFields') {
        field.editSettings.idCol = 'code'
      }
    }
  }
  // 顶层列属性
  if (field.width === undefined) field.width = pickWidth(field)
  if (field.frozen === undefined) {
    const fz = pickFrozen(field)
    if (fz !== undefined) field.frozen = fz
  }
  if (field.required === undefined) field.required = isRequired(field, ctx)
  const v = pickVisible(field)
  if (v !== undefined && field.visible === undefined) field.visible = v
  // align：优先 display.align，否则保持不动
  if (field.align === undefined && field.display?.align) {
    field.align = field.display.align
  }
  // required 同步进 edit 块
  if (field.required === true && field.edit) {
    field.edit.required = true
  }
  return field
}

// 构建全局上下文：从所有 dct 字典的 dictMeta 提取 baseFieldSet 映射。
// 供 pickDictEditSettings 决定 idCol 用。
function buildGlobalDictCtx(data) {
  const baseFieldSets = new Map()
  for (const t of data.dictionaryTables || []) {
    const dm = t.dictMeta || {}
    if (dm.dictCode && t.baseFieldSet) {
      baseFieldSets.set(dm.dictCode, t.baseFieldSet)
    }
  }
  return { baseFieldSets }
}

// 修正 dictMeta：当 baseFieldSet=dictionaryCommonNoIDFields 时，
//   - idField 必须是 'code'（该字段集不含 id 列，物理表主键是 code）
//   - 已有值不覆盖（保留用户手工意图）
function fixDictMeta(table) {
  if (table.baseFieldSet !== 'dictionaryCommonNoIDFields') return false
  const dm = table.dictMeta || {}
  if (dm.idField === 'id' || dm.idField === undefined) {
    dm.idField = 'code'
    return true
  }
  return false
}

function enrichDctTable(table, globalCtx) {
  const ctx = {
    uniqueKeys: (table.uniqueKeys || []).flat(),
    // DCT 表也可能引用其它自分级字典（segment/fs_version/cons_org），统一识别为树形
    treeRefDicts: ['segment', 'fs_version', 'cons_org'],
    baseFieldSets: globalCtx.baseFieldSets,
    selfHierarchy: !!table.dictMeta?.selfHierarchy,
  }
  if (ctx.selfHierarchy && table.dictMeta?.dictCode) {
    ctx.treeRefDicts.push(table.dictMeta.dictCode)
  }
  table.fields = (table.fields || []).map((f) => enrichField(f, ctx))
  return table
}

function enrichDocTable(table, globalCtx) {
  const ctx = {
    uniqueKeys: [],
    treeRefDicts: ['segment', 'fs_version', 'cons_org'],
    baseFieldSets: globalCtx.baseFieldSets,
  }
  table.fields = (table.fields || []).map((f) => enrichField(f, ctx))
  return table
}

function enrichBaseFieldSet(fs, globalCtx) {
  // base fieldSet 可能含 segment/fs_version/cons_org 引用（共享字段集）
  const ctx = {
    uniqueKeys: [],
    treeRefDicts: ['segment', 'fs_version', 'cons_org'],
    baseFieldSets: globalCtx.baseFieldSets,
  }
  fs.fields = (fs.fields || []).map((f) => enrichField(f, ctx))
  return fs
}

// ---------- 主流程 ----------
const raw = await readFile(inFile, 'utf8')
const data = JSON.parse(raw)

let tableCount = 0
let fieldCount = 0
let baseSetCount = 0
let fixedDictMeta = 0

// 构建跨表全局 ctx（在 enrich 任何表之前完成）
const globalCtx = buildGlobalDictCtx(data)

if (data.dictionaryTables) {
  for (const t of data.dictionaryTables) {
    if (fixDictMeta(t)) fixedDictMeta++
    enrichDctTable(t, globalCtx)
    tableCount++
    fieldCount += (t.fields || []).length
  }
}
if (data.voucherTables) {
  for (const t of data.voucherTables) {
    enrichDocTable(t, globalCtx)
    tableCount++
    fieldCount += (t.fields || []).length
  }
}
if (data.fieldSets && typeof data.fieldSets === 'object') {
  for (const [name, fs] of Object.entries(data.fieldSets)) {
    if (fs && Array.isArray(fs.fields)) {
      enrichBaseFieldSet(fs, globalCtx)
      baseSetCount++
      fieldCount += fs.fields.length
    }
  }
}

data.updatedAt = new Date().toISOString()
await writeFile(outFile, JSON.stringify(data, null, 2) + '\n', 'utf8')
console.log(`✔ ${inFile} → ${outFile}: tables=${tableCount} fieldSets=${baseSetCount} fields=${fieldCount} fixedDictMeta=${fixedDictMeta}`)
