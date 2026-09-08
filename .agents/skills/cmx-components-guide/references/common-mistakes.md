# 组件使用高频陷阱清单

> 何时读：**每次使用 cmx-data-comp 组件（CmxDataSet / cmx-dict-select / cmx-revo-grid 等）前必读**，以及任何 html-pages / native-pages 业务页开发前必读。这 5 个陷阱是历次审查中重复出现、必须规避的红线。

> 源码：
> - `packages/cmx-data-comp/src/lib/cmx-data-set.js`
> - `packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js`
> - `packages/cmx-data-comp/src/lib/cmx-message-dialog.js`
> - `../../../../cmx-portal-manager`
> - `frontend-conventions.md`

---

## 一、陷阱总览

| # | 陷阱 | 一句话正确做法 |
| --- | --- | --- |
| 1 | CmxDataSet ID 列随机生成值 | `setRows` 前按 idCol 重塑 id |
| 2 | `alert()` 滥用 | 改用 `showCmxMessage` / `cmxWarn` 等 |
| 3 | `escHtml` / `escAttr` 内联定义 | 从 `escape.js` import |
| 4 | `EDIT_MODES` 硬编码 | 引用 `cmx-field-uicontrol.js` 常量 |
| 5 | `base-dct.js` ↔ `dict-base-*.html` 双份实现 | 保留 `base-dct.js`，删除重复 |
| 6 | barrel 静态 import 重型组件污染首屏 | spreadjs/spreadsheet 已懒注册，新增重型组件勿加 `import './...'` 到 barrel 顶部 |

---

## 二、陷阱 1：CmxDataSet ID 列随机生成值

### 根因

`CmxDataSet.addRow()` 在 `data.id` 为 `undefined` 时，会自动生成一个占位 id：

```js
// packages/cmx-data-comp/src/lib/cmx-data-set.js 第 82 行
addRow(data = {}, children = {}) {
  const id  = data.id ?? `r${Math.random().toString(36).slice(2, 9)}`
  const row = new CmxRowSet({ ...data, id }, {}, this)
  // ...
}
```

`setRows(dataArray)` 内部循环调用 `addRow(plain)`，当原始行对象没有 `id` 字段（只有业务主键如 `dict_id` / `code`）时，每行都会被塞入 `r1a2b3c4` 类随机串作为 id。

### 触发场景

`cmx-dict-select` 的 help 弹层有两条路径直接 `setRows(items)` 而未做 id 重映射：

1. **help grid 路径**（`_loadHelpGrid`）：搜索返回的字典行直接灌入临时 DataSet，若行对象无 `id` 字段，grid 的 ID 列会显示随机串。

```js
// cmx-dict-select.js _loadHelpGrid
async _loadHelpGrid (grid, filter) {
  const items = await searchAsync(src, filter.keyword || '', { ...filter })
  const ds = new CmxDataSet({ datasetId: 'dict-help-grid' })
  ds.setRows(Array.isArray(items) ? items : [])   // ⚠️ 未按 idCol 重塑 id
  grid.setDataSet(ds)
}
```

2. **help tree 路径**（`_buildHelpTree`）：分类/分组树节点同样直接 `setRows(nodes)`。

```js
// cmx-dict-select.js _buildHelpTree
.then((nodes) => {
  treeDs.setRows(Array.isArray(nodes) ? nodes : [])  // ⚠️ 节点 id 字段名可能不是 'id'
  tree.setDataSet(treeDs)
})
```

### 表现

help grid 的 ID 列显示 `r1a2b3c4` 类随机串，而非业务主键值。

### 正确做法

`setRows` 前先按 `idCol` 重塑 id，确保业务主键落到 `id` 字段：

```js
const idCol = this._cfg.idCol  // 例如 'dict_id'
const fixed = items.map(r => ({ ...r, id: r[idCol] ?? r.id }))
ds.setRows(fixed)
```

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| 直接 `ds.setRows(items)`，行对象无 `id` 字段 | `setRows` 前 `items.map(r => ({ ...r, id: r[idCol] ?? r.id }))` | `addRow` 对 `data.id` 为 `undefined` 的行自动生成 `r${随机}` 占位 id，污染 ID 列 |
| 假设后端返回的行一定带 `id` 字段 | 用配置的 `idCol` 显式映射 | 字典主键列名各异（`dict_id` / `code` / `org_id`），只有 `idCol` 是权威映射 |
| tree 节点直接 `setRows(nodes)` 不做映射 | 节点对象的 `id` 字段须与 treeview 的 `id-member` 对齐 | `cmx-web-treeview` 按配置的 id 字段取节点标识，缺失会随机化 |

---

## 三、陷阱 2：alert() 滥用

### 现状

html-pages 的 gl 目录 22 个文件中出现 **213 次** `alert()`，严重违反 `frontend-conventions.md` 第三节红线。

### 红线依据

`frontend-conventions.md` 第三节红线表明确禁止：

| 禁止 | 替代 |
| --- | --- |
| 原生 `alert()` / `confirm()` / `prompt()` | `showCmxMessage`（信息类）/ `CmxFloatingDialog`（确认/表单类） |

ESLint `no-restricted-syntax`（error 级）已强制该红线，提交前 `npx eslint "src/**/*.js"` 必须 0 error。

### 正确做法

从 `cmx-data-comp` 导入消息函数（源码位于 `packages/cmx-data-comp/src/lib/cmx-message-dialog.js`）：

```js
import { showCmxMessage, cmxInfo, cmxWarn, cmxError } from 'cmx-data-comp'

// 错误 ❌
alert('保存成功')
alert('请先选择一行数据')
alert('删除失败：' + err.message)

// 正确 ✅
cmxInfo('保存成功')
cmxWarn('请先选择一行数据')
cmxError('删除失败：' + err.message)

// 或用通用函数自定义
showCmxMessage({ level: 'success', message: '保存成功' })
```

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| 业务校验用 `alert('请先选择...')` | `cmxWarn('请先选择...')` | `alert` 阻塞 UI 线程、样式不统一、无法被框架管理，且触发 ESLint error |
| 成功提示用 `alert('保存成功')` | `cmxInfo('保存成功')` 或 `showCmxMessage({ level:'success', message })` | 消息组件统一走 UI5 主题，支持自动消失、堆叠 |
| 错误信息用 `alert(err.message)` | `cmxError(err.message)` | 错误应可展开堆栈、可复制，原生 alert 无此能力 |
| 确认操作用 `confirm('确认删除?')` | 用 `CmxFloatingDialog` 弹确认框 | `confirm` 同样被红线禁止，且无法自定义按钮/图标 |

---

## 四、陷阱 3：escHtml / escAttr 内联定义

### 现状

native-pages 下有 **7 处**内联定义 `esc` / `escHtml` / `escAttr` 函数，各自实现还不完全一致（转义字符集合有差异）。

### 红线依据

`frontend-conventions.md` 第二节 3（转义） + ESLint `no-restricted-syntax`（error 级）强制：

- 第二节场景 5：HTML / 属性转义必须用 `escHtml` / `escAttr` / `escAttrHtml`。
- ESLint：禁止内联定义这三个函数，必须 `import`。
- 唯一豁免：`src/lib/escape.js`（权威定义所在）。

权威实现在 `../../../../cmx-portal-manager`：

```js
// 文本节点上下文（不转 "）
export function escHtml (s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
// 属性值上下文（必须转 "）
export function escAttr (s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
```

### 正确做法

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| 文件顶部内联 `function esc(s){...}` | `import { escHtml, escAttr } from 'CMXPortalManager/src/lib/escape.js'` | 内联实现字符集漂移（漏转 `&` 或 `"`），ESLint error 级拦截 |
| native-pages 走 importmap 无法直接 import 路径 | 通过 `globalThis.__cmxDataComp` 取用挂载的转义函数 | native-pages host 已把 cmx-data-comp 能力挂到全局，无需重复定义 |
| 拼接 HTML 用 `el.innerHTML = \`<span>${name}</span>\`` | `el.innerHTML = \`<span>${escHtml(name)}</span>\`` | 未转义的用户/动态数据可导致 XSS |

native-pages 走 importmap 的场景（2026-08-31 B-01 起 barrel 真的导出了这两个函数，经 `lib/cmx-page-helpers.js`，语义为最严格五字符集合，详见 `page-helpers.md`）：

```js
// native-pages 中（不走 ESM import）
const { escHtml, escAttr } = globalThis.__cmxDataComp
el.innerHTML = `<option value="${escAttr(v.id)}">${escHtml(v.name)}</option>`
```

---

## 五、陷阱 4：EDIT_MODES 硬编码

### 现状

native-pages 下有 **3 处**硬编码 `EDIT_MODES` 常量，且值域不全，缺少 `ref` / `combo` / `ignite-combo` / `image` / `video` / `readonly` / `none` 等控件类型。

### 权威值域

`packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js` 确立**唯一规范值域** `EDIT_MODES`（共 16 项）：

```js
export const EDIT_MODES = Object.freeze([
  'cmx-text-input', 'cmx-textarea-input', 'cmx-richtext-input',
  'cmx-number-input', 'cmx-date-input', 'cmx-datetime-input',
  'checkbox', 'select', 'ref', 'combo', 'ignite-combo',
  'cmx-dict-select', 'image', 'video', 'readonly', 'none',
])
```

### 正确做法

```js
// 错误 ❌ - 硬编码且值域不全
const EDIT_MODES = ['input', 'textarea', 'number', 'date', 'select', 'checkbox']

// 正确 ✅ - 引用唯一规范值域
import { EDIT_MODES, EDIT_MODE_LABELS, toEditMode } from 'cmx-data-comp'
// 或直接从源文件
import { EDIT_MODES } from 'packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js'
```

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| 自定义 `EDIT_MODES = [...]` 且只列 6 项 | `import { EDIT_MODES }` 引用 16 项全集 | 硬编码值域不全，导致 `ref`/`combo`/`image` 等字段无法配置录入控件 |
| 用 `'input'` 等非规范值 | 用 `'cmx-text-input'` 等规范值 | `toEditMode()` 对非规范值降级为 fallback，自造值会被静默丢弃 |
| 下拉标签手写中文映射 | `import { EDIT_MODE_LABELS }` | 标签与值域同源，避免新增加控件时标签漏更新 |

---

## 六、陷阱 5：base-dct.js ↔ dict-base-*.html 双份实现

### 现状

native-pages 下同一套逻辑存在两份实现：

- `base-dct.js`（native 模块）：定义 `DATA_TYPES` / `EDIT_MODES` / `esc` / `apiJson` / `setPath` / `optionHtml` 等。
- `dict-base-*.html`：内联了同样的 `DATA_TYPES` / `EDIT_MODES` / `esc` / `apiJson` / `setPath` / `optionHtml`。

### 红线依据

`frontend-conventions.md` 总则第 2 条：

> **同一逻辑只允许存在一份实现。** 如果两个类需要同一套方法，抽成 `src/lib/*.js` 的普通函数 `export`，两边 `import` 调用；**禁止各自内联一份**。

### 正确做法

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| `dict-base-*.html` 内联 `esc`/`EDIT_MODES`/`apiJson` 等 | 删除 html 内联定义，改为引用 `base-dct.js` | 两份实现必然漂移（见陷阱 3/4），修一处漏另一处 |
| `base-dct.js` 自己又内联 `esc`/`EDIT_MODES` | `base-dct.js` 内部也应 import 权威源（`escape.js` / `cmx-field-uicontrol.js`） | `base-dct.js` 是 native 模块聚合层，不是权威定义层，不能再造一份 |
| 保留 html 副本"以防万一" | 删除 `dict-base-*.html` 或改为纯引用 | 保留即意味着有人会改它而不改 js，最终两份不一致 |

**收敛路径**：保留 `base-dct.js` 作为 native 模块聚合层（其内部 import 权威源），删除 `dict-base-*.html` 中的重复逻辑或将其改为 `<script type="module">` 引用 `base-dct.js`。

---

## 七、容易踩的坑（汇总）

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| `setRows(items)` 时 items 无 `id` 字段 | `items.map(r => ({...r, id: r[idCol] ?? r.id}))` 再 setRows | `addRow` 对无 id 行生成 `r${随机}` 占位，污染 ID 列 |
| 业务页用 `alert()` / `confirm()` | `cmxInfo` / `cmxWarn` / `cmxError` / `CmxFloatingDialog` | 红线禁止，ESLint error 拦截 |
| 文件内联 `escHtml` / `escAttr` | `import { escHtml, escAttr } from 'escape.js'` | 内联实现漂移 + ESLint error |
| 硬编码 `EDIT_MODES` 且值域不全 | `import { EDIT_MODES }` 引用 16 项全集 | 自造值被 `toEditMode` 降级，新控件无法配置 |
| `base-dct.js` 与 `dict-base-*.html` 各存一份 | 保留 js 模块，删除 html 重复 | 双份实现必然漂移，违反"同一逻辑一份实现" |
