# CmxColumnModel + CmxColumn + ColumnGroup（列模型）

> 何时读：任何需要表格列 / 表单字段的场景（L0 起）。
> 源码：`packages/cmx-data-comp/src/lib/cmx-column-model.js` + `cmx-column.js` + `cmx-column-group.js`

---

## 一句话

CmxColumnModel = 表格 / 表单的**列配方**。定义有哪些列、每列怎么显示 / 编辑 / 聚合。可被 FlexibleCombination 在运行时动态改写。

---

## CmxColumnModel 字段表（props）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `datasetId` | string | 否 | `''` | 关联的 CmxDataSet 实例名（**单层名**，不是路径） |
| `columns` | array | 否 | `[]` | 列定义数组（每项 = 一个 CmxColumn） |
| `columnGroups` | array | 否 | `[]` | 列组定义数组（每项 = 一个 CmxColumnGroup） |
| `columnsSource` | string | 否 | `''` | 列定义的 pageService 名（动态从后端拿列） |

**默认 props**（来自源码 `page-data-panel-models.js`）：
```js
{ datasetId: '', columns: [], columnGroups: [], columnsSource: '' }
```

### 关键陷阱：datasetId 写单层名

CmxColumnModel 的 `datasetId` 写**单层表名**（如 `items`），**不是 schema 路径**（不要写 `head.items`）。

> 原因：`initPageModels` 把 ColumnModel 注册到 MS 时，用 `ms._schemaById.has(p.datasetId)` 匹配，按单层 id 查。

但 **DOM 的 `data-cmx-dataset-id`** 要写**完整路径**（如 `head.items`）。两者不要搞混。

---

## CmxColumn 字段表（columns[] 每一项）

### 基础字段

| 字段 | 含义 | 常用值 |
| --- | --- | --- |
| `id` | 列唯一编码（运行时数据行的字段名） | `code` / `amount` |
| `caption` | 显示标题；字符串或多语言对象 | `"编码"` 或 `{ "zh_CN": "编码", "en": "Code" }` |
| `dataType` | 数据类型 | 见下表 |
| `width` | 列宽 | `"140px"` / `"20%"` |
| `frozen` | 是否冻结列 | `true` / `false` |
| `visible` | 是否可见 | `true` / `false` |
| `align` | 对齐 | `"left"` / `"right"` / `"center"` |
| `agg` | 聚合方式 | `"sum"` / `"avg"` / `"min"` / `"max"` / `"count"` |

### dataType 枚举

| 值 | 含义 |
| --- | --- |
| `VARCHAR` | 字符串 |
| `TEXT` | 长文本 |
| `BIGINT` / `INT` | 整数 |
| `NUMBER` / `DECIMAL` | 数值 |
| `DATE` | 日期 |
| `DATETIME` / `TIMESTAMP` | 日期时间 |
| `BOOLEAN` | 布尔 |
| `JSON` | JSON 对象 |

### edit（编辑配置）

```jsonc
{
  "id": "qty",
  "edit": {
    "mode": "cmx-number-input",  // ★ 录入控件——必须用 EDIT_MODES 规范值（见 ../../cmx-components-guide/references/field-edit-display-modes.md）
    "required": true,            // 是否必填
    "options": [],               // select 的可选项 [{value,label}]
    "validate": "...",            // 校验规则
    "readonlyWhen": "...",       // 只读条件（表达式）
    "requiredWhen": "..."        // 必填条件（表达式）
  }
}
```

> ⚠️ **`edit.mode` 必须用 `cmx-field-uicontrol.js` 的 `EDIT_MODES` 规范值域（16 个值），完整清单见 `../../cmx-components-guide/references/field-edit-display-modes.md`**。不要自创短名 `text`/`number`/`date`（运行时会被收敛成默认 `cmx-text-input`）；`tree-ref`/`computed` 不在值域里（树形用 `combo`+parent，计算列用 `calcFormula`）。

**edit.mode 常用规范值**（完整 16 值见 `../../cmx-components-guide/references/field-edit-display-modes.md`）：

| 规范值 | 含义 |
| --- | --- |
| `cmx-text-input` | 文本输入（默认） |
| `cmx-number-input` | 数字输入 |
| `cmx-date-input` | 日期选择 |
| `cmx-datetime-input` | 日期时间 |
| `checkbox` | 复选框/布尔 |
| `select` | 静态枚举下拉（配合 `edit.options`） |
| `combo` | 组合框（远端搜索，list/tree/grid 三态） |
| `cmx-dict-select` | 数据字典选择（规范值；配 dictCode 等） |
| `readonly` | 只读 |
| `none` | 不可编辑 |

> `ref` 合法但无编辑器实现，业务上配成 `combo`/`cmx-dict-select`。`cmx-textarea-input`/`cmx-richtext-input`/`image`/`video` 声明了但注册表无编辑器，会退化为文本输入。

### display（显示配置）

> `display.mode` 权威值 7 个：`''`（空，数值默认）/ `text` / `number` / `badge` / `link` / `icon` / `actions`（操作列按钮组，配 `display.actions`，点击派发 `cmx-cell-link-click`）。**纯数值类属性（decimalDigits/thousandSeparator/zeroAsBlank/negativeColor）只在 mode 为空或 `number` 时生效**（`visibleWhen` 联动）。**`display.format` 是「下拉+文本框」复合控件（select-text），在 `''`/`number`/`text` 三种模式都可用，且按 mode 给不同选项**（number→千分位/百分比/货币，text→各档日期时间格式）。完整说明见 `../../cmx-components-guide/references/field-edit-display-modes.md`。

```jsonc
{
  "id": "amount",
  "display": {
    "mode": "number",            // ★ 数值列用 '' 或 'number'；'text'/'badge'/'link'/'icon' 见下
    "format": "thousands",       // 格式化预设「下拉+文本框」复合控件（select-text，按 mode 分组）：number→无/thousands/percent/currency:¥；text→无/date:YYYY-MM-DD/datetime:YYYY-MM-DD HH:mm:ss。下拉选预设，文本框手改任意值（如 currency:$）
    "decimalDigits": 2,          // 显示小数位（仅 mode 空/number）
    "thousandSeparator": true,   // 千分位开关（boolean，仅 mode 空/number）
    "zeroAsBlank": true,         // 0 显示空（boolean，数值列默认 true，仅 mode 空/number）
    "negativeColor": true,       // ★ 负数红字开关（boolean，不是颜色值；仅 mode 空/number）
    "align": "right",            // left/center/right（总生效）
    "badgeMap": {},              // mode=badge：{值:{text,color,icon}}（运行时支持，三元 schema 无录入入口）
    "link": {},                  // mode=link：{actionRef} 或 {href}
    "icon": "",                  // mode=icon：图标名或映射
    "cellStyle": [],             // 条件样式 [{when,class,style}]
    "emptyText": "—"             // 空值占位符
  }
}
```

> **display.mode 权威值域 7 个**：`''`/`number`（数值列默认）/ `text`（原样文本）/ `badge`（徽章，配 `badgeMap`）/ `link`（链接，配 `link`）/ `icon`（图标，配 `icon`）/ `actions`（操作列按钮组，配 `actions`，点击派发 `cmx-cell-link-click`）。完整字段见 `../../cmx-components-guide/references/field-edit-display-modes.md`。注意 `display.format` 才管数值/日期格式化（number 模式：`thousands`/`percent`/`currency:¥`；text 模式：`date:YYYY-MM-DD`/`datetime:YYYY-MM-DD HH:mm:ss`），`display.mode` 只管"单元格渲染成什么样"。

### 计算列（calcFormula + dependsOn）

> **`computed` 不是 edit.mode 值**。计算列通过 `calcFormula` + `dependsOn` 实现（edit.mode 设 `readonly`）。

```jsonc
{
  "id": "subtotal",
  "caption": { "zh_CN": "小计" },
  "dataType": "NUMBER",
  "edit": { "mode": "readonly" },
  "calcFormula": "r.subtotal = r.qty * r.unitPrice",
  "dependsOn": ["qty", "unitPrice"]
}
```

- `calcFormula`：计算公式（preset 或函数体）
- `dependsOn`：依赖字段数组；这些字段变了触发重算（拓扑排序）

### 校验

```jsonc
{
  "id": "qty",
  "validations": [
    { "expr": "quantity > 0", "message": "数量必须大于 0" }
  ],
  "validateFormula": "qty > 0"
}
```

### 其它字段（按需）

| 字段 | 含义 |
| --- | --- |
| `length` / `integerDigits` / `decimalDigits` | 字段长度 / 整数位 / 小数位 |
| `defaultFrom` | 默认值来源（dimension / attribute） |
| `unitField` | 单位字段（数量挂计量单位） |
| `dimType` | 维度类型（dimension / measure） |
| `refDict` | 引用字典 |
| `displayMask` | 显示格式模板 |

---

## 字段三态（dimension / attribute / measure）

> 主要用于 FlexibleCombination 动态列；CmxColumnModel 里也可用 `dimType` 标注。详见 `model-flexible-combination.md`。

| 态 | 取值来源 | 典型 | edit.mode |
| --- | --- | --- | --- |
| **dimension**（维度） | 从某维度主数据选一个值 | 客户、产品、币种 | `cmx-dict-select` / `combo` / `select` |
| **attribute**（属性） | 从已选维度自动带出 | 产品→规格、单位 | `readonly` |
| **measure**（度量） | 数值 | 单价、数量、金额 | `cmx-number-input`（计算列用 `calcFormula`） |

---

## CmxColumnGroup（列组：合并表头 + 组内聚合）

`columnGroups[]` 每一项：

| 字段 | 含义 |
| --- | --- |
| `id` | 列组编码 |
| `caption` | 显示标题 |
| `members` | 成员（列 id 字符串，或嵌套列组对象） |
| `aggregate` | 组内聚合 `{ sum: true, avg: true, max: true, min: true, count: true }` |
| `aggregatePosition` | 聚合行位置 `"before"` / `"after"` |

**示例**：
```jsonc
{
  "modelType": "CmxColumnModel",
  "instanceId": "voucherModel",
  "props": {
    "datasetId": "items",
    "columns": [
      { "id": "debit",  "caption": "借方", "dataType": "NUMBER", "width": "120px", "agg": "sum" },
      { "id": "credit", "caption": "贷方", "dataType": "NUMBER", "width": "120px", "agg": "sum" }
    ],
    "columnGroups": [
      {
        "id": "money",
        "caption": "金额组",
        "members": ["debit", "credit"],
        "aggregate": { "sum": true },
        "aggregatePosition": "after"
      }
    ]
  }
}
```

> 当同时配置了 `columnGroups`，`initPageModels` 会用 `buildMembersFromColumnsAndGroups` 把列按组组装；没配 `columnGroups` 时直接用 `columns` 数组。

---

## 列定义模板速查

> 所有 `edit.mode` 必须用 `EDIT_MODES` 规范值（见 `../../cmx-components-guide/references/field-edit-display-modes.md`）。

### 文本列
```jsonc
{ "id": "code", "caption": { "zh_CN": "编码" }, "dataType": "VARCHAR", "width": "140px", "edit": { "mode": "cmx-text-input" } }
```

### 必填数字列（带格式化）
```jsonc
{
  "id": "qty", "caption": { "zh_CN": "数量" }, "dataType": "NUMBER", "width": "90px",
  "edit": { "mode": "cmx-number-input", "required": true },
  "display": { "mode": "number", "decimalDigits": 2, "thousandSeparator": true, "negativeColor": true }
}
```

### 计算列（readonly + calcFormula）
```jsonc
{
  "id": "subtotal", "caption": { "zh_CN": "小计" }, "dataType": "NUMBER", "width": "110px",
  "edit": { "mode": "readonly" },
  "calcFormula": "r.subtotal = r.qty * r.unitPrice",
  "dependsOn": ["qty", "unitPrice"]
}
```

### 静态下拉选择列
```jsonc
{
  "id": "status", "caption": { "zh_CN": "状态" }, "dataType": "VARCHAR", "width": "100px",
  "edit": {
    "mode": "select",
    "options": [
      { "value": "draft", "label": "草稿" },
      { "value": "posted", "label": "已过账" }
    ]
  }
}
```

### 只读列（自动带出）
```jsonc
{ "id": "spec", "caption": "规格", "dataType": "VARCHAR", "width": "120px", "edit": { "mode": "readonly" } }
```

### 状态徽章列（display.mode=badge）
```jsonc
{
  "id": "status", "caption": "状态", "dataType": "VARCHAR", "width": "90px",
  "edit": { "mode": "readonly" },
  "display": {
    "mode": "badge",
    "badgeMap": {
      "active": {"text":"启用","color":"#107e3e"},
      "draft":  {"text":"草稿","color":"#f59e0b"}
    }
  }
}
```

### 操作列（display.mode=actions）
```jsonc
{
  "id": "_actions", "caption": "操作", "dataType": "VARCHAR", "width": "180px",
  "edit": { "mode": "readonly" },
  "display": { "mode": "actions", "actions": [
    { "text": "编辑",  "actionRef": "edit",    "icon": "edit" },
    { "text": "审批",  "actionRef": "approve", "variant": "emphasized" },
    { "text": "删除",  "actionRef": "delete",  "variant": "negative" }
  ]}
}
```

> **声明式 jsonc 只支持静态按钮组**。`variant` 取 `""`（默认蓝）/`"emphasized"`（强调填充）/`"negative"`（红）。点击派发 `cmx-cell-link-click`，监听见 `../../cmx-components-guide/references/field-edit-display-modes.md` 第三节。
>
> **按行状态显隐按钮**（如待办列表按 doc_status 显示不同操作）用 `visible(model)`，但函数值无法序列化，**只能程序化 `new CmxColumn({...})`**，不能写进 jsonc 模型声明。详见 `../../cmx-components-guide/references/field-edit-display-modes.md` 第三节「display.actions[] 单按钮字段」。

### 字典选择列（维度）
```jsonc
{
  "id": "customer", "caption": { "zh_CN": "客户" }, "dataType": "VARCHAR", "width": "160px",
  "edit": { "mode": "cmx-dict-select", "required": true, "dictCode": "bus_partner", "codeCol": "code", "labelCol": "name" },
  "dimType": "dimension"
}
```

---

## 两种列填充模式

### 1. 设计时写死 columns（最常见）

直接在 `props.columns` 写列定义数组（如上所有示例）。

### 2. 运行时 pageFn 动态设列

`columns: []` 留空，运行时由 pageFn 调 `setMembers` / `setColumns`：

```js
// pageFn 里
const lib = globalThis.__cmxDataComp
const cols = docTable.fields.map(f => new lib.CmxColumn({ id: f.id, caption: f.caption, dataType: f.dataType }))
host.itemModel.setMembers(cols)   // 或 setColumns(cols)
```

> 真实样例：`erp-voucher-cnpc-ms.html` 的 `loadVoucher` 函数——按 DOC 元数据动态构造列灌进 4 个 ColumnModel。

### 3. 被 FlexibleCombination 改写（L2）

详见 `model-flexible-combination.md`：FC 调 `columnModel.setMembers(newColumns)` 触发 `columns-changed`，可视组件重渲染。

---

## 事件

**CmxColumnModel 不继承 EventTarget——没有内置事件。**

> 写 `events` 字段不会触发。若需监听列变化，在 pageFn 里用 `host.xxxModel.addEventListener('columns-changed', ...)`（但仅当被 FC 改写时派发）。

---

## 字段类型注册表（扩展自定义字段类型）

`cmx-data-comp` 支持零代码注册新字段类型 + 编辑器：

```js
import { registerFieldType } from 'cmx-data-comp'
registerFieldType('color', {
  form: { create(field, ctx) { /* 创建 input */ } },
  grid: { editor(col, save, close) { /* 返回 {element, getValue} */ } }
})
```

- form 端未注册类型回退到内置 `cmx-text-input`
- grid 端 mount 时把已注册类型写入 `revo.editors`

> 一般生成页面用不到，除非用户明确要自定义字段类型。
