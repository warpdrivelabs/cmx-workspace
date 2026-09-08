# cmx-dict-select 组件配置手册

> 何时读：需要使用 `<cmx-dict-select>` 数据字典选择组件时——配置字典编码、列映射、help 弹层布局、监听选中事件、对接 dataSource 时必读。

> 源码：`packages/cmx-data-comp/src/components/cmx-dict-select.js`

---

## 一、组件概述

- **tag 名**：`<cmx-dict-select>`
- **形态**：一个 `<ui5-input>` 输入框 + 右侧按钮区（清除 / help / 可扩展 slot）。
- **交互链路**：
  1. 输入框获得焦点 → 自动下拉「最近选过」（MRU）。
  2. 输入时边输边搜（debounce），下拉切换为搜索结果。
  3. 鼠标 / 键盘（↑↓ Enter Esc）选择 → 选中值为 `CmxRowSet` 对象。
  4. clear 按钮清除选中值。
  5. help 按钮弹出 `<cmx-floating-dialog>`，按 `helpLayout` 三种布局展示。
- **helpLayout 三布局**：

| 布局 | 结构 | 适用 |
| --- | --- | --- |
| `classify` | 左分类树 + 右字典 grid | 字典按分类组织 |
| `group` | 左分组树 + 右字典 grid | 字典按分组组织 |
| `grid` | 仅字典 grid（`hierarchical=true` 时为 treegrid） | 无分类分组的扁平/分级字典 |

---

## 二、配置项全表

`configure(cfg)` 接受以下键（从 `this._cfg` 读取，可多次调用合并）：

| 键 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `dictCode` | string | `''` | 字典编码，用作 MRU 分桶 key 与默认列模型标题 |
| `idCol` | string | `'id'` | 行主键列名，选中值取此列 |
| `labelCol` | string | `'name'` | 显示名称列名，输入框展示此列 |
| `codeCol` | string | `''` | 编码列名；设置后输入框显示「编码-名称」 |
| `parentCol` | string | `'parent_id'` | 父节点列名，`hierarchical=true` 时 treegrid 按此建树 |
| `placeholder` | string | `'请输入或点击查询'` | 输入框占位文本 |
| `columns` | CmxColumn[] \| CmxColumnModel \| null | `null` | grid 列定义；为 null 时用 idCol+labelCol 生成默认两列 |
| `hierarchical` | boolean | `false` | 字典是否分级；true 时 help grid 走 treegrid |
| `helpLayout` | `'classify'` \| `'group'` \| `'grid'` | `'grid'` | help 弹层布局 |
| `showClear` | boolean | `true` | clear 按钮是否可见 |
| `dataSource` | object \| null | `null` | 字典数据源 `{ search, loadByKeys }` |
| `classifyTreeSource` | object \| null | `null` | classify 布局左侧分类树数据源 |
| `groupTreeSource` | object \| null | `null` | group 布局左侧分组树数据源 |
| `personalizationService` | object \| function \| null | `null` | MRU 后端个性化服务 `{ load, save }` |
| `mruMax` | number | `10` | MRU 最大条数 |
| `dictTitle` | string | — | help 对话框标题；默认「选择{dictCode}」 |
| `readonly` | boolean | `false` | 输入框只读 |
| `disabled` | boolean | `false` | 输入框禁用 |

### 三组易混字段

| 对比 | 区别 | 示例 |
| --- | --- | --- |
| `idCol` vs `labelCol` vs `codeCol` | `idCol`=主键（选中值）；`labelCol`=显示名；`codeCol`=编码（可选，设后显示「编码-名称」） | `{idCol:'dict_id', labelCol:'name', codeCol:'code'}` → 显示 `D001-物料A` |
| `dictCode` vs `idCol` | `dictCode`=字典业务编码（MRU 分桶 / 标题）；`idCol`=行数据主键列名 | `dictCode:'material'`，`idCol:'dict_id'` |
| `dataSource` vs `classifyTreeSource` / `groupTreeSource` | `dataSource`=右侧字典 grid 数据源（必填）；`classify/groupTreeSource`=左侧树数据源（仅对应布局需要） | classify 布局三者都要 |

---

## 三、HTML 属性

`observedAttributes`（属性变化会重新读配置并应用到 DOM）：

| 属性 | 对应配置键 | 说明 |
| --- | --- | --- |
| `dict-code` | `dictCode` | |
| `id-col` | `idCol` | |
| `label-col` | `labelCol` | |
| `code-col` | `codeCol` | |
| `parent-col` | `parentCol` | |
| `placeholder` | `placeholder` | |
| `help-layout` | `helpLayout` | |
| `show-clear` | `showClear` | 值为 `'false'` 时隐藏；存在属性即生效 |
| `hierarchical` | `hierarchical` | 值为 `'false'` 时关闭；存在属性即生效 |
| `readonly` | `readonly` | 存在属性即为 true |
| `disabled` | `disabled` | 存在属性即为 true |

```html
<cmx-dict-select
  dict-code="material"
  id-col="dict_id"
  label-col="name"
  help-layout="grid"
  hierarchical
></cmx-dict-select>
```

---

## 四、API 方法

| 方法 | 参数 | 返回值 | 用途 |
| --- | --- | --- | --- |
| `configure(cfg)` | 配置对象 | `this`（链式） | 合并配置；可多次调用；已渲染时同步刷新 DOM |
| `setDataSource(ds)` | 数据源对象 | `this` | 单独设置 `dataSource` |
| `setColumns(cols)` | 列定义数组/模型 | `this` | 单独设置 `columns` |
| `setValue(id, opts)` | `id`, `{ silent?, displayText?, rowData? }` | `Promise<this>` | 按 id 设置选中值；异步回查行对象用于显示 |
| `getValue()` | 无 | `string\|null` | 当前选中 id |
| `getSelectedRow()` | 无 | `CmxRowSet\|null` | 当前选中行（CmxRowSet） |
| `clearValue(opts)` | `{ silent? }` | `this` | 清除选中值 |
| `openHelp()` | 无 | `Promise<CmxRowSet\|null>` | 打开 help 对话框，返回选中行 |

```js
// 链式配置
el.configure({ dictCode: 'material', idCol: 'dict_id', labelCol: 'name' })
  .setDataSource(ds)
  .setColumns(cols)

// 程序化设值（带预加载数据避免一次回查）
await el.setValue('M001', { rowData: { dict_id:'M001', name:'物料A' } })

// 读取
const id  = el.getValue()
const row = el.getSelectedRow()
```

---

## 五、事件

所有事件 `bubbles: true, composed: true`。

| 事件名 | detail 结构 | 触发时机 |
| --- | --- | --- |
| `cmx-dict-change` | `{ id, row, plain, text, dictCode, idCol }` | 选中或清除值时 |
| `cmx-dict-open` | 无 | 打开下拉（MRU）时 |
| `cmx-dict-help` | `{ layout }` | 打开 help 对话框时 |

### detail 字段说明

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `string\|null` | 当前选中 id |
| `row` | `CmxRowSet\|null` | 选中行对象（CmxRowSet） |
| `plain` | `object\|null` | 选中行的纯对象快照（`row.toPlainObject()`），含字典所有列 |
| `text` | `string` | 当前显示文本 |
| `dictCode` | `string` | 字典编码 |
| `idCol` | `string` | 主键列名 |

### 重点：plain 字段

`plain` 是选中行的纯对象快照，由 `row.toPlainObject()` 生成，包含字典所有列。**用于回写字典各列到宿主 CmxDataSet**——监听 `cmx-dict-change` 时，从 `plain` 取各列值写回宿主行，而非只取 id。

```js
el.addEventListener('cmx-dict-change', (e) => {
  const { id, plain, dictCode, idCol } = e.detail
  if (!plain) {
    // 清除：把宿主行对应字段置空
    hostRow.setValues({ material_id: '', material_name: '', material_code: '' })
    return
  }
  // 选中：把字典各列回写到宿主 DataSet
  hostRow.setValues({
    material_id:   plain.dict_id,
    material_name: plain.name,
    material_code: plain.code,
  })
})
```

---

## 六、slot

| slot | 用途 |
| --- | --- |
| `actions` | 追加扩展按钮到按钮区尾部（help 按钮之后） |

```html
<cmx-dict-select dict-code="material">
  <ui5-button slot="actions" icon="add" design="Transparent" tooltip="新增"></ui5-button>
</cmx-dict-select>
```

---

## 七、dataSource 契约

`dataSource` 须实现以下方法：

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `search(query, opts)` | `(string, object) => Promise<items[]>` | 按关键字搜索；opts 透传分类/分组过滤等上下文 |
| `loadByKeys(keys)` | `(string[]) => Promise<items[]>` | 按 id 批量回查（`setValue` 异步回查时调用） |

- `keyField` 约定为 `idCol`，`labelField` 约定为 `labelCol`。
- 返回的 `items` 为普通对象数组，字段名须与 `idCol` / `labelCol` / `columns` 对齐。
- 详细数据源模式见 `data-source-patterns.md`。

```js
const ds = {
  async search(query, opts = {}) {
    const res = await fetch(`/api/dict/material?q=${encodeURIComponent(query)}`)
    return res.json()
  },
  async loadByKeys(keys) {
    const res = await fetch('/api/dict/material/by-keys', {
      method: 'POST',
      body: JSON.stringify({ keys }),
    })
    return res.json()
  },
}
```

---

## 八、MRU 机制

- **存储**：本地 `localStorage`（按 `dictCode` 分桶）+ 可选后端个性化（`personalizationService`）。
- **分桶**：以 `dictCode` 为 key 隔离不同字典的最近选择记录。
- **容量**：`mruMax`（默认 10）控制每个桶最大条数，超出时淘汰最旧。
- **后端合并**：打开下拉时先展示本地 MRU，异步合并后端个性化结果。
- **清除**：下拉头部「清除全部」按钮清空当前桶；行内清除图标移除单行。

```js
// 后端个性化服务（可选）
const personalizationService = {
  async load() { /* 返回后端存储的 MRU 列表 */ },
  async save(list) { /* 持久化 MRU 列表到后端 */ },
}
el.configure({ dictCode: 'material', personalizationService, mruMax: 20 })
```

---

## 九、ID 随机值陷阱

`cmx-dict-select` 的 help 弹层 grid 路径（`_loadHelpGrid`）直接 `setRows(items)`，若 `dataSource.search` 返回的行对象没有 `id` 字段（只有 `idCol` 指向的业务主键），`CmxDataSet.addRow()` 会自动生成 `r${随机}` 占位 id，导致 help grid 的 ID 列显示随机串。

**修复建议**（help grid 路径）：在 `_loadHelpGrid` 中 `setRows` 前按 `idCol` 重塑：

```js
async _loadHelpGrid (grid, filter) {
  const items = await searchAsync(src, filter.keyword || '', { ...filter })
  const ds = new CmxDataSet({ datasetId: 'dict-help-grid' })
  const idCol = this._cfg.idCol
  // ✅ 按 idCol 重塑 id，避免 addRow 生成随机占位 id
  const fixed = (Array.isArray(items) ? items : []).map(r => ({ ...r, id: r[idCol] ?? r.id }))
  ds.setRows(fixed)
  grid.setDataSet(ds)
}
```

> 详细分析与其它路径（help tree）见 `common-mistakes.md` 陷阱 1。

---

## 十、典型用法

```js
import 'cmx-data-comp/components/cmx-dict-select.js'

// 1. 创建并配置
const el = document.createElement('cmx-dict-select')
el.configure({
  dictCode: 'material',
  idCol: 'dict_id',
  labelCol: 'name',
  codeCol: 'code',
  parentCol: 'parent_id',
  hierarchical: false,
  helpLayout: 'classify',
  showClear: true,
  mruMax: 15,
  dictTitle: '选择物料',
  columns: [
    { id: 'code', caption: '编码', type: 'text', width: 120 },
    { id: 'name', caption: '名称', type: 'text' },
  ],
  dataSource: {
    async search(query, opts = {}) {
      const r = await fetch(`/api/dict/material?q=${encodeURIComponent(query)}`)
      return r.json()
    },
    async loadByKeys(keys) {
      const r = await fetch('/api/dict/material/by-keys', {
        method: 'POST', body: JSON.stringify({ keys }),
      })
      return r.json()
    },
  },
  classifyTreeSource: {
    async search() {
      const r = await fetch('/api/dict/material/classify')
      return r.json()
    },
  },
})

// 2. 监听选中事件——用 plain 回写宿主各列
el.addEventListener('cmx-dict-change', (e) => {
  const { id, plain, text } = e.detail
  if (!plain) {
    hostRow.setValues({ material_id: '', material_name: '', material_code: '' })
    return
  }
  hostRow.setValues({
    material_id:   plain.dict_id,
    material_name: plain.name,
    material_code: plain.code,
  })
})

// 3. 挂载
document.querySelector('#field-material').appendChild(el)

// 4. 程序化回填（编辑场景）
await el.setValue('M001', {
  rowData: { dict_id: 'M001', name: '物料A', code: 'D001' },
})

// 5. 程序化打开 help
const row = await el.openHelp()
```

---

## 容易踩的坑

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| `dataSource.search` 返回行无 `id` 字段，help grid ID 列显示随机串 | `setRows` 前 `items.map(r => ({...r, id: r[idCol] ?? r.id}))` | `addRow` 对无 id 行生成 `r${随机}` 占位 |
| 监听 `cmx-dict-change` 只取 `detail.id`，丢失字典其它列 | 用 `detail.plain` 回写宿主各列 | `plain` 是选中行全字段快照，用于回写字典各列 |
| `idCol` / `labelCol` / `codeCol` 配错导致显示异常 | 按「idCol=主键、labelCol=显示名、codeCol=编码」对齐 | 三者职责不同，配反则选中值或显示文本错误 |
| `classify` 布局只配 `dataSource` 忘配 `classifyTreeSource` | 三者都配（dataSource + classifyTreeSource） | 左侧树无数据源时空白 |
| `setValue` 未传 `rowData`，触发额外 `loadByKeys` 回查 | 编辑回填时传 `rowData` 避免网络请求 | 有预加载数据时应直接复用 |
