# 表单组件：cmx-ui5-form / cmx-master-slave-config

> 何时读：需要单行编辑表单（字段编辑 + 校验）时；需要声明式主从协调器（form+grid 联动、聚合、级联）时；查 setColumnModel / setDataSet / validate 用法时；字段类型如何映射编辑器时；元数据模型（DOC/DCT/FLC）如何绑定列模型时。

> 源码：
> - `packages/cmx-data-comp/src/components/cmx-ui5-form.js`
> - `packages/cmx-data-comp/src/components/cmx-master-slave-config.js`
> - `packages/cmx-data-comp/src/lib/cmx-master-slave.js`（协调器实现）
> - `packages/cmx-data-comp/src/lib/init-page-models.js`（元数据绑定）

---

## 一、cmx-ui5-form（主表单）

基于 UI5 Form 的单行编辑表单 Web Component。字段定义只能来自 `CmxColumnModel`（运行时 `setColumnModel(model)`，声明式 `data-cmx-model-id`）。无统一 `configure()`，通过多个 setter 配置。

- **tag**：`<cmx-ui5-form>`（兼容旧标签 `<cmx-form>`）
- **字段类型**：由 `CmxColumnModel` 经 `CmxColumnAdapter.toCmxFormGrouped(model)` 转出的 `field.type` 决定（底层对应列的 `edit.mode`）。

### 1.1 API

| 方法 | 签名 | 说明 |
|------|------|------|
| `setColumnModel(model)` | `(CmxColumnModel) => void` | **唯一字段定义入口**；订阅 `columns-changed` 自动重渲染字段 |
| `setLayout(layout)` | `(string) => void` | 响应式列布局，默认 `'S1 M2 L3 XL3'` |
| `setHeaderText(text)` | `(string) => void` | 表单标题 |
| `setDataSet(dsOrRow, opts?)` | `(CmxDataSet \| rowObj, {currentRowId?}) => void` | 绑定 CmxDataSet（游标驱动）或单行对象 |
| `getData()` | `() => rowObj` | 浅拷贝返回当前行 |
| `validate()` | `() => { valid, errors }` | 逐字段校验，失败标红并派发 `cmx-ui5-form-invalid` |
| `clearValidation()` | `() => void` | 清除所有字段错误态 |
| `setEditable(flag)` | `(boolean) => this` | 表单整体编辑态（字段自身 readonly 仍优先） |
| `isEditable()` | `() => boolean` | 当前是否可编辑 |
| `setSkinStyles(cssText, layer)` | `(string, 'neo'\|'page'\|'custom') => this` | 注入皮肤 CSS |
| `setDataSources(sources)` | `(Array<{id}>) => void` | 注册局部 DataSource（覆盖协调器级） |
| `rehydrateFromSources()` | `() => void` | 重新解析 ref-display 字段 |

### 1.2 validate() 返回

```javascript
const { valid, errors } = form.validate()
// errors: [{ key, label, message }]
// valid === (errors.length === 0)
// 失败时同步派发 cmx-ui5-form-invalid；字段标红（UI5 value-state=Negative）
```

支持的字段校验属性：`required` / `requiredWhen`（条件必填表达式）/ `validate`（函数\|表达式\|规则数组）/ `validateWhen`（条件校验闸门）/ `requiredMessage` / `validateMessage`。表达式经 `formula-eval` 求值，scope = 当前整行。

### 1.3 事件

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-ui5-form-changed` | `{ key, value, row }` | 字段值提交（input/change） |
| `cmx-ui5-form-invalid` | `{ errors, row }` | `validate()` 校验失败时 |

### 1.4 声明式属性

| 属性 | 形式 | 说明 |
|------|------|------|
| `data-cmx-model-id` | 字符串 | CmxColumnModel 实例 id（`init-page-models` 注入调 `setColumnModel`） |
| `data-cmx-master-slave-id` | 字符串 | CmxMasterSlave 实例 id（协调器绑定） |
| `data-cmx-dataset-id` | 字符串 | CmxDataSet 实例 id |
| `data-cmx-kind` | 字符串 | 节点 kind（`single`/`list`，协调器用） |
| `data-cmx-layout` | 字符串 | 布局，如 `S1 M2 L3 XL3` |
| `data-cmx-header` | 字符串 | 标题文字 |
| `data-cmx-row` | JSON | 单行初始数据 |
| `data-cmx-sources` | JSON | DataSource 数组 |
| `data-cmx-density` | `compact` | 紧凑模式（收紧间距、固定 label 列宽） |
| `data-cmx-skin` | `neo`\|`plain`\|`default`\|`none` | 皮肤；未设默认 `neo`（`globalThis.__cmxDefaultFormSkin` 可覆盖） |
| `data-cmx-skin-tone` | `mint` 等 | Neo 强调色 |
| `data-cmx-style-id` | 字符串 | 同页 `<template>` id，注入覆盖样式 |

### 1.5 字段类型 → 编辑器映射

由 `field.type`（源自 `CmxColumnModel` 的 `edit.mode` 经适配器转换）决定：

| field.type | 编辑器 | 说明 |
|------------|--------|------|
| `text`（默认） | `<ui5-input>` | 文本输入 |
| `number` | `<ui5-input type="Number">` | 数字输入 |
| `select` | `<ui5-select>` + `<ui5-option>` | 本地选项 |
| `date` | `<ui5-date-picker>` | 日期（`format-pattern` 默认 `yyyy-MM-dd`） |
| `textarea` | `<ui5-textarea>` | 多行文本（`rows` 可配） |
| `checkbox` | `<ui5-checkbox>` | 布尔 |
| `readonly` | `<span class="readonly-display">` | 只读展示（支持 `formatter` preset） |
| `ref-display` | `<span class="readonly-display">` | 引用字段展示（按 source+from 查关联值） |
| `ref` | `<ui5-select>` / `<ui5-combobox>` / `<ui5-input>` | 按 `helper`：`dropdown`（默认）/ `combo-search` / `remote-search` |
| 外挂注册类型 | `cmx-form-field-registry` | `getFieldType(type).form.create` 优先于内置 switch |

> 字段支持 `colspan`/`columnSpan`（跨多列）、`dependents`（联动刷新）、分组（`{type:'group', caption, children}` 渲染为 `<ui5-form-group>`）。

---

## 二、cmx-master-slave-config（声明式主从协调器）

声明式自启动元素：在 HTML 中放一个本元素，textContent 为 JSON 配置，`connectedCallback` 时自动 `new CmxMasterSlave(...)` 并按 selector 绑定页面的 form/grid 组件。

- **tag**：`<cmx-master-slave-config>`
- **暴露**：`element.ms`（`CmxMasterSlave` 实例）

### 2.1 配置结构（textContent JSON）

```json
{
  "schema":       [{ "id": "master", "kind": "single", "selector": "#form" },
                   { "id": "detail", "kind": "list",   "selector": "#grid" }],
  "aggregations": [{ "from": "detail", "agg": "sum", "field": "amount",
                     "to": "master", "toField": "totalAmount" }],
  "relations":    [{ "parent": "master", "child": "detail", "childKey": "masterId" }],
  "dataSources":  [{ "id": "cust", "keyField": "code", "items": [], "helper": "dropdown" }],
  "initialData":  { "master": { "id": "M1" }, "detail": [{ "id": "D1", "amount": 100 }] }
}
```

### 2.2 schema 结构

`[{ id, kind, selector?, children? }]`，递归嵌套。

| 字段 | 说明 |
|------|------|
| `id` | 节点 id（path 拼接为 `parent.child`） |
| `kind` | `'single'`（表单，`bindForm`）\| `'list'`（表格，`bindTable`） |
| `selector` | CSS 选择器，定位页面对应 `cmx-ui5-form` / grid 组件 |
| `children` | 子节点数组（递归） |

> `selector` 仅 `cmx-master-slave-config` 用（自动绑定），进协调器时被剥离。`data-scope` 属性可指定查找 root（默认 document）。

### 2.3 aggregations 结构

`[{ from, agg, field?, to, toField, scope? }]`

| 字段 | 说明 |
|------|------|
| `from` | 源节点 path（聚合数据来源） |
| `agg` | `'sum'` \| `'count'` \| `'avg'` \| `'min'` \| `'max'`（或自定义函数） |
| `field` | 聚合字段（`count` 时可省略） |
| `to` | 目标节点 path |
| `toField` | 写入目标行的字段名 |
| `scope` | 默认 `'siblings'` |

必填：`from` / `to` / `toField`。

触发时机：`setData` 后整体重算；`cmx-cell-changed` / `cmx-ui5-form-changed` 命中 `rule.from`；`cmx-row-added` / `cmx-row-removed`（path 命中或为其前缀）。

### 2.4 relations 结构

`[{ parent, child, parentKey?, childKey }]`

| 字段 | 说明 |
|------|------|
| `parent` | 父节点 path |
| `child` | 子节点 path |
| `parentKey` | 父关联键，默认 `'id'` |
| `childKey` | 子行外键字段（必填） |

必填：`parent` / `child` / `childKey`。

### 2.5 事件

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-ms-ready` | `{ ms }` | 协调器创建并绑定完成、初始数据加载后 |

### 2.6 dataSources 结构

`[{ id, keyField, labelField, items, helper, search?, loadByKeys? }]`。注册后 form/grid 可通过 `_setDataSourceProvider` 解析（`ref` / `ref-display` 字段引用 `source` id）。

---

## 三、列模型绑定元数据

`CmxColumnModel` 可通过 `metaModelId` + `metaTable` 引用已声明的元数据模型实例，由 `init-page-models` 在阶段 1.5 自动填充字段。

### 3.1 三种元数据形态

| 形态 | 类 | metaTable 含义 | 取表方法 |
|------|----|----------------|----------|
| **DOC**（单据） | `CmxDOCMeta`（`kind === 'DOC'`） | 表名 tableName | `meta.getTable(metaTable)` |
| **DCT**（字典） | `CmxDCTMeta`（`kind === 'DCT'`） | 字典编码 dictCode | `meta.getDictionary(metaTable)` |
| **FLC**（弹性组合） | `CmxFlexibleCombination` | scenario 坐标 | `loadByAnchor(anchorValues)` 动态出列 |

### 3.2 metaModelId 引用流程

1. 页面 `__designer_meta__.models` 声明 `CmxColumnModel`，带 `metaModelId` + `metaTable`。
2. `init-page-models` 阶段 1 创建 `CmxColumnModel` 实例，记入 `pendingMetaBinds` 队列。
3. 阶段 1.5：元数据模型实例就绪后，取指定表/字典的字段（`table.listFields()`）。
4. 经 `metaTableFieldsToColumns(fields, kind, opts)` 归一为 `CmxColumn[]`，`model.setMembers(...)` 填充。
5. `backfillColumnCoord(model, globalCoord)` 用全局坐标兜底字典列坐标。

```javascript
// init-page-models.js 核心逻辑（简化）
const table = meta.kind === 'DCT'
  ? meta.getDictionary(metaTable)
  : meta.getTable(metaTable)
model.setMembers(metaTableFieldsToColumns(table.listFields(), meta.kind, {
  respectOrder: Array.isArray(table.raw?.fieldSetOrder) && table.raw.fieldSetOrder.length > 0,
}))
backfillColumnCoord(model, globalCoord)
```

### 3.3 metaTableFieldsToColumns 归一函数

`init-page-models.js` 导出。把元数据字段（`fieldName`/`id`/`name` 标识、`caption` 是 i18n 对象 `{zh_CN,...}`、无 `isPrimaryKey`）归一为 `CmxColumn` 构造所需形态，再复用 `orderColumns` 出列。

### 3.4 backfillColumnCoord 字典列坐标兜底

元数据字段不保证带齐全字典坐标（dbId / dictCode 等）。`backfillColumnCoord(model, globalCoord)` 遍历 `model.members`，对缺坐标的字典列用页面全局坐标补全，确保 `enableDictEcho` / `cmx-dict-select` 能正确请求字典数据。

### 3.5 enableDictEcho 字典外键回显

表格组件的方法（`cmx-revo-grid.enableDictEcho`）。扫描列模型 `refDict`，预加载全量字典条目，给列 `display` 挂 resolver（id->名称）。详见 `grid-components.md` 1.5 节。

### 3.6 FlexibleCombination scenario 坐标

`CmxFlexibleCombination` 通过 `domain` / `app` / `module` / `scenario` 四维坐标定位弹性组合配置，`loadByAnchor(anchorValues)` 拉取默认 rule（`isDefault:true`）直接出列，动态改变 `CmxColumnModel` 成员并派发 `columns-changed`，已绑定的 form/grid 自动重渲染。

---

## 四、典型用法

### 4.1 完整 form + master-slave-config 示例

```html
<!-- 主表单 -->
<cmx-ui5-form
  id="orderForm"
  data-cmx-model-id="orderColumns"
  data-cmx-master-slave-id="orderMs"
  data-cmx-dataset-id="orderDs"
  data-cmx-kind="single"
  data-cmx-layout="S1 M2 L3 XL3"
  data-cmx-header="销售订单"
></cmx-ui5-form>

<!-- 明细表格 -->
<cmx-revo-grid
  id="detailGrid"
  data-cmx-model-id="detailColumns"
  data-cmx-master-slave-id="orderMs"
  data-cmx-dataset-id="detailDs"
  data-cmx-fill-height
  data-cmx-options='{"selectionMode":"single","editable":true,"showTotals":true}'
></cmx-revo-grid>

<!-- 主从协调器：声明式配置 -->
<cmx-master-slave-config data-scope="pageRoot">
{
  "schema": [
    { "id": "master", "kind": "single", "selector": "#orderForm" },
    { "id": "detail", "kind": "list",   "selector": "#detailGrid" }
  ],
  "aggregations": [
    { "from": "detail", "agg": "sum", "field": "amount",
      "to": "master", "toField": "totalAmount" },
    { "from": "detail", "agg": "count",
      "to": "master", "toField": "lineCount" }
  ],
  "relations": [
    { "parent": "master", "child": "detail", "childKey": "orderId" }
  ],
  "dataSources": [
    { "id": "customer", "keyField": "code", "labelField": "name",
      "items": [], "helper": "combo-search" }
  ],
  "initialData": {
    "master": { "id": "ORD-001", "orderId": "ORD-001", "customer": "C01" },
    "detail": [
      { "id": "D1", "orderId": "ORD-001", "product": "P1", "amount": 100 },
      { "id": "D2", "orderId": "ORD-001", "product": "P2", "amount": 200 }
    ]
  }
}
</cmx-master-slave-config>
```

### 4.2 监听协调器就绪 + 表单校验

```javascript
document.addEventListener('cmx-ms-ready', (e) => {
  const { ms } = e.detail
  // ms 即 CmxMasterSlave 实例，也可通过 element.ms 访问
  console.log('协调器就绪', ms)

  // 提交前校验主表单
  const form = document.querySelector('#orderForm')
  const { valid, errors } = form.validate()
  if (!valid) {
    console.warn('校验失败', errors)
    return
  }
  // 导出数据
  const ds = window.__pageModels.orderDs
  const payload = ds.toJSON()
})
```

### 4.3 元数据驱动的列模型（声明式）

```html
<!-- __designer_meta__.models 声明（简化） -->
<!-- CmxDOCMeta 实例 docMeta + CmxColumnModel 引用 -->
<cmx-ui5-form
  data-cmx-model-id="orderColumns"
  data-cmx-density="compact"
></cmx-ui5-form>

<!-- init-page-models 阶段 1.5 自动：
     orderColumns.metaModelId = 'docMeta'
     orderColumns.metaTable   = 'sale_order'
     -> docMeta.getTable('sale_order').listFields()
     -> metaTableFieldsToColumns -> setMembers
     -> backfillColumnCoord(globalCoord)
-->
```
