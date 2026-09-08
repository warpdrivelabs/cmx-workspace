#!/usr/bin/env node
// 校验 CMX 字典/单据元数据文件，所有 edit.mode / display.mode 必须在规范值域内，
// 并校验 NoID 字典的 idField / refDict 指向 NoID 字典时的 editSettings.idCol。
//
// 规范源：
//   edit.mode    → packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js (EDIT_MODES, 16 值)
//   display.mode → packages/cmx-data-comp/src/lib/cmx-field-schema.js 的 display.mode options（元数据侧不含 actions 页面级）
//   注：actions（操作列）属页面级配置，不在元数据 display.mode 值域内；元数据中出现 actions 视为非法。
//   idField/idCol → enrich-meta.mjs 的 NoID 规则（baseFieldSet=dictionaryCommonNoIDFields → 主键是 code）
//
// 用法：node verify-meta.mjs <file1.json> [file2.json ...]
// 退出码：0=全通过，1=有错误

import { readFile } from 'node:fs/promises'
import { argv, exit } from 'node:process'

const EDIT_MODES = new Set([
  'cmx-text-input', 'cmx-textarea-input', 'cmx-richtext-input', 'cmx-number-input',
  'cmx-date-input', 'cmx-datetime-input', 'checkbox', 'select', 'ref', 'combo',
  'ignite-combo', 'cmx-dict-select',
  'image', 'video', 'readonly', 'none',
])
const DISPLAY_MODES = new Set(['', 'text', 'number', 'badge', 'link', 'icon'])  // actions 属页面级配置，不在元数据值域
const NOID_FIELDSET = 'dictionaryCommonNoIDFields'

const files = argv.slice(2)
if (!files.length) {
  console.error('Usage: node verify-meta.mjs <file1.json> [file2.json ...]')
  exit(2)
}

let totalBadE = 0
let totalBadD = 0
let totalBadIdField = 0
let totalBadIdCol = 0
let totalFields = 0
const summary = []

for (const f of files) {
  let d
  try {
    d = JSON.parse(await readFile(f, 'utf8'))
  } catch (e) {
    console.error('✗ JSON parse failed:', f, e.message)
    totalBadE++
    continue
  }

  // 构建 dictCode → baseFieldSet 映射（供 idCol 校验用）
  const baseFieldSets = new Map()
  for (const t of (d.dictionaryTables || [])) {
    const dm = t.dictMeta || {}
    if (dm.dictCode && t.baseFieldSet) {
      baseFieldSets.set(dm.dictCode, t.baseFieldSet)
    }
  }

  let badE = 0
  let badD = 0
  let badIdField = 0
  let badIdCol = 0
  let fields = 0
  let numMode = 0
  const errors = []

  // 校验单个字段：edit.mode / display.mode / editSettings.idCol
  const scan = (fd, ctx) => {
    fields++
    const m = fd.edit && fd.edit.mode
    if (m && !EDIT_MODES.has(m)) {
      badE++
      errors.push({ type: 'EDIT', ctx, id: fd.id, value: m })
    }
    const dm = fd.display && fd.display.mode
    if (dm != null && dm !== '' && !DISPLAY_MODES.has(dm)) {
      badD++
      errors.push({ type: 'DISPLAY', ctx, id: fd.id, value: dm })
    }
    if (dm === 'number') numMode++

    // editSettings.idCol 校验：refDict 指向 NoID 字典时必须 'code'
    if (m === 'cmx-dict-select' && fd.refDict) {
      const refFS = baseFieldSets.get(fd.refDict)
      if (refFS === NOID_FIELDSET) {
        const idCol = fd.editSettings?.idCol
        if (idCol !== 'code') {
          badIdCol++
          errors.push({ type: 'IDCOL', ctx, id: fd.id, value: idCol ?? '<missing>', expect: 'code', refDict: fd.refDict })
        }
      }
    }
  }

  // 1) fieldSets
  for (const fs of Object.values(d.fieldSets || {})) {
    if (fs && Array.isArray(fs.fields)) for (const fd of fs.fields) scan(fd, fs.name || 'fieldSet')
  }
  // 2) dictionaryTables：先校 dictMeta.idField，再校字段
  for (const t of (d.dictionaryTables || [])) {
    const dm = t.dictMeta || {}
    const dictCode = dm.dictCode || t.tableName || 'table'
    // idField 校验：NoID 字典必须 'code'
    if (t.baseFieldSet === NOID_FIELDSET) {
      if (dm.idField !== 'code') {
        badIdField++
        errors.push({ type: 'IDFIELD', ctx: dictCode, id: 'dictMeta.idField', value: dm.idField ?? '<missing>', expect: 'code' })
      }
    }
    for (const fd of (t.fields || [])) scan(fd, dictCode)
  }
  // 3) voucherTables
  for (const t of (d.voucherTables || [])) {
    for (const fd of (t.fields || [])) scan(fd, t.tableName || 'table')
  }

  totalBadE += badE
  totalBadD += badD
  totalBadIdField += badIdField
  totalBadIdCol += badIdCol
  totalFields += fields
  summary.push({ file: f, fields, badE, badD, badIdField, badIdCol, numMode, errors })
}

// 打印报告
for (const s of summary) {
  const tag = (s.badE || s.badD || s.badIdField || s.badIdCol) ? '✗' : '✔'
  console.log(`${tag} ${s.file}: fields=${s.fields} badEdit=${s.badE} badDisplay=${s.badD} badIdField=${s.badIdField} badIdCol=${s.badIdCol} numberMode=${s.numMode}`)
  for (const e of s.errors) {
    if (e.type === 'IDFIELD') {
      console.log(`    [${e.type}] ${e.id} => ${e.value} (期望 ${e.expect})`)
    } else if (e.type === 'IDCOL') {
      console.log(`    [${e.type}] ${e.ctx}.${e.id} => ${e.value} (refDict=${e.refDict} 期望 ${e.expect})`)
    } else {
      console.log(`    [${e.type}] ${e.ctx}.${e.id} => ${e.value}`)
    }
  }
}

console.log('\n=== 汇总 ===')
console.log('总字段数:', totalFields)
console.log('不合法 edit.mode:', totalBadE)
console.log('不合法 display.mode:', totalBadD)
console.log('NoID 字典 idField 错误:', totalBadIdField)
console.log('NoID refDict 的 idCol 错误:', totalBadIdCol)
exit((totalBadE || totalBadD || totalBadIdField || totalBadIdCol) ? 1 : 0)
