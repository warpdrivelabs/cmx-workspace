# 字段属性权威 Schema（edit.mode / display / 三元字段全集）

> ⚠️ **本文件是 `html-page-generator` 与 `native-page-generator` 的共享参考**。两处内容必须保持一致，改动需同步另一份。
> 何时读：**定义 CmxColumn 或三元定义（DCT/DOC/FLC）字段时必读**——这是字段所有可设属性的权威清单和值域。
> 权威源：`packages/cmx-data-comp/src/lib/cmx-field-schema.js`（FIELD_SCHEMA + EDITOR_PROPERTY_SCHEMA）+ `cmx-field-uicontrol.js`（EDIT_MODES）

> 本文记录的是**字段 schema 层**的 edit.mode 值域与专属属性。若需将某编辑器作为**独立组件元素**使用（如直接 `<cmx-dict-select>` 的 DOM 属性 / slot / 方法 / 事件），见 `cmx-components-guide` 技能。

---

## 核心原则

`cmx-field-schema.js` 是三端（DCT/DOC/FLC）字段定义的**单一事实来源**。它定义了：

1. **`edit.mode`** 录入控件值域——来自 `cmx-field-uicontrol.js` 的 `EDIT_MODES`（16 个规范值）
2. **`display.*`** 显示属性全集——含 `display.mode`（7 个值）+ 数值精度/格式/对齐等
3. **每个 edit.mode 的专属属性**——`EDITOR_PROPERTY_SCHEMA`（如 `cmx-number-input` 的 `intDigits`/`decimalDigits`/`min`/`max`）
4. **三元分区 SECTIONS**（10 个语义分区）+ **三端差异 appliesTo**（哪些属性在 DCT/DOC/FLC 可用）

**❌ 错误做法**：自创短名 `text`/`number`/`date`/`input`/`computed`/`tree-ref` —— 不在值域里，运行时被收敛成默认值或失效。
**✅ 正确做法**：严格用本文的规范值。

---

## 一、edit.mode 完整值域（16 个规范值）

来自 `cmx-field-uicontrol.js` 的 `EDIT_MODES`，三端共用：

| mode（规范存储值） | 中文 | runtime kind | 说明 |
| --- | --- | --- | --- |
| `cmx-text-input` | 输入 | input | 单行文本，**默认 fallback** |
| `cmx-textarea-input` | 多行文本 | textarea | ⚠️ 声明了但无编辑器，退化文本 |
| `cmx-richtext-input` | 富文本 | rich-text | ⚠️ 退化文本 |
| `cmx-number-input` | 数字 | number | 数字输入 |
| `cmx-date-input` | 日期 | date | 日期选择 |
| `cmx-datetime-input` | 日期时间 | datetime | 日期时间选择 |
| `checkbox` | 复选框 | checkbox | 布尔（BOOLEAN 自动推断） |
| `select` | 枚举下拉 | select | 静态枚举（配 `edit.options` 或字段 `enumValues`） |
| `ref` | 外键引用 | ref | ⚠️ 合法但无编辑器，业务配成 combo/dict-select |
| `combo` | 组合框 | combo | 远端搜索（list/tree/grid 三态） |
| `ignite-combo` | Ignite 组合框 | ignite-combo | Ignite 风格 |
| `cmx-dict-select` | 字典选择 | dict-select | 规范值；配 refDict + editSettings |
| `image` | 图片 | image | ⚠️ 退化文本 |
| `video` | 视频 | video | ⚠️ 退化文本 |
| `readonly` | 只读 | readonly | 不可编辑 |
| `none` | 不可编辑 | none | 完全不可编辑 |

### 常见误用对照

| 需求 | ❌ 错误 | ✅ 正确 |
| --- | --- | --- |
| 文本 | `'text'` | `'cmx-text-input'` |
| 数字 | `'number'` | `'cmx-number-input'` |
| 日期 | `'date'` | `'cmx-date-input'` |
| 日期时间 | `'datetime'` | `'cmx-datetime-input'` |
| 字典选择 | `'dict-select'` | `'cmx-dict-select'` |
| 树形引用 | `'tree-ref'`（不在值域） | `'combo'` + `edit.parent` |
| 计算列 | `'computed'`（不在值域） | `calcFormula` + `dependsOn`，edit.mode 设 `readonly` |

> 合法的无前缀短名只有：`select` / `combo` / `ref` / `checkbox` / `readonly` / `none` / `ignite-combo`。

---

## 二、每个 edit.mode 的专属属性（EDITOR_PROPERTY_SCHEMA）

来自 `cmx-field-schema.js`。选了某 mode 后，这些属性在"录入控件属性"分区可设，key 统一落到 `edit.*`（dict-select 落 `editSettings.*`）：

### cmx-text-input
| key | label | 类型 |
| --- | --- | --- |
| `edit.inputType` | 输入类型 | select：''/text/phone/email/idcard |
| `edit.pattern` | 校验正则 | text |
| `edit.maxlength` | 最大长度 | number |
| `edit.i18n` | 多语言 | checkbox |
| `edit.locale` | 当前语言 | text（如 zh_CN） |
| `edit.placeholder` | 占位符 | text |
| `edit.readonly` | 只读 | checkbox |

### cmx-textarea-input
`edit.rows`（行数）/ `edit.maxlength` / `edit.placeholder` / `edit.readonly`

### cmx-richtext-input
`edit.height`（如 240px）/ `edit.toolbar`（''/basic/full/none）/ `edit.placeholder` / `edit.readonly`

### cmx-number-input
| key | label | 类型 |
| --- | --- | --- |
| `edit.intDigits` | 整数位 | number |
| `edit.decimalDigits` | 小数位 | number |
| `edit.min` | 最小值 | number |
| `edit.max` | 最大值 | number |
| `edit.thousandSeparator` | 千分位 | checkbox |
| `edit.placeholder` | 占位符 | text |
| `edit.readonly` | 只读 | checkbox |

### cmx-date-input
`edit.formatPattern`（如 yyyy-MM-dd）/ `edit.minDate` / `edit.maxDate` / `edit.placeholder` / `edit.readonly`

### cmx-datetime-input
`edit.formatPattern`（如 yyyy-MM-dd HH:mm:ss）/ `edit.minDate` / `edit.maxDate` / `edit.placeholder` / `edit.readonly`

### cmx-dict-select（字典选择，属性落 editSettings.*）
| key | label | 说明 |
| --- | --- | --- |
| `editSettings.helpLayout` | 帮助布局 | select：**grid**（自分级 treegrid）/ **classify**（左分类树+右 grid）/ **group**（左分组树+右 grid） |
| `editSettings.hierarchical` | 分级字典 | checkbox |
| `editSettings.idCol` | ID 列 | 默认 id |
| `editSettings.codeCol` | 编码列 | 默认 code |
| `editSettings.labelCol` | 名称列 | 默认 name |
| `editSettings.parentCol` | 父级列 | 默认 parent_id |
| `editSettings.valueField` | 值字段 | 写回行字段，默认 idCol |
| `editSettings.displayField` | 显示字段 | 默认 name |
| `editSettings.displayMode` | 显示模式 | select：**auto**/value/code/label/code-label/field |
| `editSettings.displayTemplate` | 显示模板 | 如 `${code} - ${name}` |
| `editSettings.dictTitle` | 帮助标题 | 如"选择会计科目" |
| `editSettings.showClear` | 显示清除按钮 | checkbox |
| `editSettings.mruMax` | 最近选择条数 | 默认 10 |
| `editSettings.dropdownWidth` | 下拉宽度 | 如 480px |
| `editSettings.dropdownMaxHeight` | 下拉最大高度 | 如 360px |
| `editSettings.placeholder` | 占位符 | text |

> **dict-select 的字典编码不在这里配**——自动跟随字段的"引用字典"（`refDict`）。用户只在 reference 区选一次 refDict，录入控件自动用同一本。

---

## 三、display.* 显示属性全集（来自 FIELD_SCHEMA display 分区）

来自 `cmx-field-schema.js`。三端共享（DCT/DOC/FLC 都可设）：

| key | label | 类型 | 值域/说明 | 显隐条件 |
| --- | --- | --- | --- | --- |
| `display.align` | 对齐 | select | `''`/`left`/`center`/`right` | 总显示 |
| `display.mode` | 显示模式 | select | `''`/`text`/`number`/`badge`/`link`/`icon`/`actions`（7 值） | 总显示 |
| `display.format` | 格式 | select-text | **下拉+文本框**复合控件，按 `display.mode` 分组：number/缺省→`无`/`thousands`(千分位)/`percent`(百分比)/`currency:¥`(货币)；text→`无`/各档日期时间格式（`date:YYYY`/`date:YYYY-MM`/`date:YYYY-MM-DD`/`datetime:YYYY-MM-DD HH:mm:ss`/`datetime:HH:mm` 等）。下拉选高频预设，文本框可手改任意值（如 `currency:$`、`date:YYYY年MM月`），两者同值。label 后有问号图标点击弹配置说明 | mode ∈ `['', 'number', 'text']` |
| `display.decimalDigits` | 显示小数位 | number | | mode ∈ `['', 'number']` |
| `display.thousandSeparator` | 千分位 | checkbox | | mode ∈ `['', 'number']` |
| `display.zeroAsBlank` | 0 显示空 | checkbox | 数值列默认 true | mode ∈ `['', 'number']` |
| `display.negativeColor` | 负数红字 | **checkbox（布尔开关）** | ⚠️ 不是颜色值，是"是否负数标红"开关 | mode ∈ `['', 'number']` |

### display.mode 权威值域（7 个）

来自 `cmx-field-schema.js` + `cmx-column-adapter.js`（actions 渲染源）：

| display.mode | 含义 | 配套属性 | 说明 |
| --- | --- | --- | --- |
| `''`（空，未选） | 数值默认 | 数值类属性可设（小数位/千分位/0显空/负数红字） | 数值列推荐留空或显式 number |
| `text` | 原样文本 | `display.format`（日期/日期时间预设，不可编辑时间字段走这里） | 字符串列默认 |
| `number` | 数值模式 | 数值类属性可设 | 数值列显式标注 |
| `badge` | 徽章 | `display.badgeMap`（CmxColumn 运行时支持，三元 schema 暂无录入入口） | 状态列 |
| `link` | 链接 | `display.link`（运行时支持，三元暂无入口） | 可点击列 |
| `icon` | 图标 | `display.icon`（运行时支持，三元暂无入口） | 图标列 |
| `actions` | **操作列（按钮组）** | `display.actions`（运行时支持，三元暂无入口） | 一列多按钮，点击派发 `cmx-cell-link-click`。**属页面级配置，不是元数据字段属性——DCT/DOC 定义里不要写 actions，meta-enricher 会判非法；仅在页面 CmxColumnModel / 程序化 CmxColumn 里用** |

> **关键**：纯数值属性（`decimalDigits` / `thousandSeparator` / `zeroAsBlank` / `negativeColor`）只在 `display.mode` 为空或 `number` 时显示（`visibleWhen: _displayModeIn(row, ['', 'number'])`）。`display.format` 是「下拉+文本框」复合控件（select-text），**在 `''`/`number`/`text` 三种模式都显示**，且**按 mode 给不同选项**：number/缺省给数值预设（千分位/百分比/货币），text 给日期预设（各档日期时间格式）。下拉选预设、文本框手改任意值，两者同值。设成 `badge`/`link`/`icon` 时 format 不显示。label 后有问号图标（tips），点击弹配置说明。

### ⚠️ negativeColor 是布尔开关不是颜色值

```jsonc
// ✅ 正确（来自 FIELD_SCHEMA :217，control: 'checkbox', valueType: 'boolean'）
{ "display": { "mode": "number", "negativeColor": true } }   // 负数标红开

// ❌ 错误（旧文档误导）
{ "display": { "negativeColor": "#bb0000" } }   // 不是颜色值
```

### badge/link/icon 的运行时配置（CmxColumn 支持，三元 schema 暂无录入入口）

三元定义设计器目前录不了 badgeMap/link/icon，但 CmxColumn 运行时支持（见 `cmx-column.js`）。在 pageFn 里手动构造 CmxColumn 时可用：

```jsonc
// 状态徽章列
{ "display": { "mode": "badge", "badgeMap": {
  "active": {"text":"启用","color":"#107e3e"},
  "draft":  {"text":"草稿","color":"#f59e0b"}
}}}

// 链接列
{ "display": { "mode": "link", "link": {"actionRef":"openDetail"} } }

// 图标列
{ "display": { "mode": "icon", "icon": {"high":"error","mid":"warning","low":"information"} } }

// 操作列（一列多按钮）—— 渲染源：cmx-column-adapter.js
{ "display": { "mode": "actions", "actions": [
  { "text": "编辑",  "actionRef": "edit",   "icon": "edit" },
  { "text": "审批",  "actionRef": "approve","variant": "emphasized" },
  { "text": "删除",  "actionRef": "delete", "variant": "negative" }
]}}
```

#### `display.actions[]` 单按钮字段（仅 `actions` 模式）

| 字段 | 含义 | 取值 |
| --- | --- | --- |
| `text` | 按钮文字 | string（空则只显 icon） |
| `actionRef` | **必填**，业务路由标识，原样回传事件 detail | 任意字符串 |
| `icon` | UI5 图标名 | 如 `"edit"` / `"delete"` |
| `variant` | 视觉变体 | `""`（默认蓝文字+浅边框）/ `"emphasized"`（强调蓝填充）/ `"negative"`（红，危险/不可逆） |
| `color` | 自定义颜色（覆盖 variant） | CSS 色，建议 `var(--sap*)` |
| `visible` | **按行显隐**（程序化构造时） | `(model) => boolean`，返回假值则该行不渲染此按钮；不传则恒显示 |

> 无 `actionRef` 的 action 会被过滤掉。每按钮在 DOM 上渲染为 `<span data-cmx-link="<列id>" data-cmx-action="<actionRef>">`。
>
> **`variant` 三档语义**：默认（普通操作：提交、查看、克隆）/ `emphasized`（主操作、正向关键动作：通过、审批）/ `negative`（危险不可逆：作废、驳回、删除）。优先级：`color` > `variant` > 默认。
>
> **`visible(model)` 按行过滤**——同一列按行状态显示不同按钮。仅程序化 `new CmxColumn({...})` 可传函数，jsonc 声明式（三元 schema 暂无入口）不支持函数值。示例：
> ```js
> // 待办列表：draft 行显"提交/作废"，approving 行显"通过/驳回"，rejected 行显"修改重提"
> const is = (s) => (m) => m.doc_status === s
> new C.CmxColumn({ id: '_action', caption: '操作', dataType: 'VARCHAR', width: '180px',
>   edit: { mode: 'readonly' },
>   display: { mode: 'actions', actions: [
>     { text: '提交',     actionRef: 'submit',  visible: is('draft') },
>     { text: '作废',     actionRef: 'abort',   variant: 'negative',   visible: is('draft') },
>     { text: '通过',     actionRef: 'approve', variant: 'emphasized', visible: is('approving') },
>     { text: '驳回',     actionRef: 'reject',  variant: 'negative',   visible: is('approving') },
>     { text: '修改重提', actionRef: 'clone',   visible: is('rejected') },
>   ] } })
> ```

#### `cmx-cell-link-click` 事件（link / actions 共用）

点击 `link` 列或 `actions` 列按钮后，grid 派发（源：`revo-grid-events-mixin.js`）：

```js
grid.addEventListener('cmx-cell-link-click', (e) => {
  const { key, rowId, actionRef } = e.detail
  // key      = 列 id（如 'actions'）
  // rowId    = 行 id（data-rgRow 属性值，可能为 null）
  // actionRef= 按钮标识（actions 列每个按钮独立；link 列用 display.link.actionRef）
  if (actionRef === 'edit')   openEdit(rowId)
  if (actionRef === 'delete') confirmDelete(rowId)
})
```

> **actions 列每个按钮的 actionRef 优先**（读 `data-cmx-action`）；**link 列**用列级 `display.link.actionRef` 回退。

---

## 四、三元字段属性全集（FIELD_SCHEMA 10 个分区）

来自 `cmx-field-schema.js`。生成 DCT/DOC/FLC 定义时按需取用，`appliesTo` 标明哪些端可用：

### basic（基本）
| key | label | appliesTo | 说明 |
| --- | --- | --- | --- |
| `id` | ID | DCT/DOC/FLC | 字段唯一标识 |
| `name` | Name | DCT/DOC/FLC | 物理字段名 |
| `caption` | 标题 | DCT/DOC/FLC | 显示标题 |
| `dimType` | 维度类型 | DCT/DOC/FLC | ''/dimension/attribute/measure/relation |
| `dataType` | 数据类型 | DCT/DOC | VARCHAR/INT/BIGINT/TINYINT/DECIMAL/DATE/DATETIME/TEXT/BOOLEAN（FLC 只读） |
| `fieldLength` | 长度 | DCT/DOC | 按 typeCaps 显隐 |
| `intDigits` | 整数位 | DCT/DOC | DECIMAL 才显示 |
| `decimalDigits` | 小数位 | DCT/DOC | DECIMAL 才显示 |
| `nullable` | 可空 | DCT/DOC | checkbox |
| `isPrimaryKey` | 主键 | DCT/DOC | 存 1/0 |

### reference（引用字典）
| key | appliesTo | 说明 |
| --- | --- | --- |
| `refDict` | DCT/DOC/FLC | 引用的字典编码（FLC 仅 dimension 显示） |
| `refField` | DCT/DOC/FLC | 引用字段 |
| `displayField` | DCT/DOC/FLC | 显示字段 |

### edit（编辑）
| key | appliesTo | 值域 |
| --- | --- | --- |
| `edit.mode` | DCT/DOC/FLC | EDIT_MODES 16 值（见 §一） |
| `edit.required` | DCT/DOC/FLC | checkbox |

### display（显示）
见 §三（三端共享）。

### editorProps（录入控件属性）
见 §二（按 edit.mode 动态切换）。

### compute（计算与带出）
| key | label | appliesTo | 显隐 |
| --- | --- | --- | --- |
| `formula` | 公式 | DCT/DOC/FLC | 总显示 |
| `dependsOn` | 依赖 | DCT/DOC/FLC | list |
| `source.dimension` | 来源维度 | **FLC 独有** | dimType=attribute |
| `source.attribute` | 来源属性 | **FLC 独有** | dimType=attribute |
| `defaultFrom.dimension` | 默认来源维度 | **FLC 独有** | dimType=measure |
| `defaultFrom.attribute` | 默认来源属性 | **FLC 独有** | dimType=measure |
| `unitField` | 计量单位列 | DCT/DOC/FLC | dimType=measure |

### constraint（约束校验）
| key | label | appliesTo | 说明 |
| --- | --- | --- | --- |
| `defaultValue` | 默认值 | DCT/DOC/FLC | ⚠️ CmxColumn 无此键，新建行不自动填（缺口） |
| `unique` | 唯一 | DCT/DOC/FLC | ⚠️ 不落地（缺口） |
| `pattern` | 校验正则 | DCT/DOC/FLC | 如 `^[A-Z0-9_]{2,32}$` |
| `enumValues` | 枚举值 | DCT/DOC/FLC | `[{value,label}]` 对象数组（label 可选），如 `[{"value":"open","label":"未开始"}]`；仅 edit.mode=select 时维护，运行时映射成 edit.options + 强制 select |
| `validations` | 校验规则 | **FLC 独有** | 数组 `[{expr,message}]` |
| `agg` | 合计 | DCT/DOC/FLC | ''/sum/count/avg/max/min（仅数值类型） |

### governance（数据治理）
| key | appliesTo | 说明 |
| --- | --- | --- |
| `label` | DCT/DOC/FLC | 显示标签 |
| `searchable` | DCT/DOC/FLC | ⚠️ grid 不消费（缺口） |
| `filterable` | DCT/DOC/FLC | ⚠️ grid 不消费（缺口） |
| `sensitive` | DCT/DOC/FLC | ''/public/internal/confidential/pii ⚠️ 无脱敏渲染（缺口） |
| `i18n` | DCT/DOC/FLC | checkbox |

### control（字段控制·动态条件）
| key | label | appliesTo |
| --- | --- | --- |
| `edit.requiredWhen` | 必填条件 | DCT/DOC/FLC |
| `edit.editableWhen` | 可编辑条件 | **DCT/DOC**（CmxColumn 无此键，缺口） |
| `edit.readonlyWhen` | 条件只读 | **FLC** |
| `edit.visibleWhen` | 可见条件 | **DCT/DOC**（CmxColumn 仅静态 visible，缺口） |

### flcLayout（列布局）
| key | label | appliesTo | 值域 |
| --- | --- | --- | --- |
| `width` | 列宽 | DCT/DOC/FLC | 120px / 20% / flex |
| `frozen` | 冻结列 | DCT/DOC/FLC | checkbox |
| `visible` | 可见 | DCT/DOC/FLC | checkbox |

---

## 五、三端差异速查（appliesTo）

| 能力 | DCT | DOC | FLC |
| --- | --- | --- | --- |
| `dataType` 可编辑 | ✅ | ✅ | ❌（只读） |
| `fieldLength`/`intDigits`/`decimalDigits` | ✅ | ✅ | ❌ |
| `nullable`/`isPrimaryKey` | ✅ | ✅ | ❌ |
| `source.dimension`/`source.attribute`（带出） | ❌ | ❌ | ✅ |
| `defaultFrom.dimension`/`defaultFrom.attribute` | ❌ | ❌ | ✅ |
| `validations`（校验规则数组） | ❌ | ❌ | ✅ |
| `edit.editableWhen`（可编辑条件） | ✅ | ✅ | ❌ |
| `edit.readonlyWhen`（条件只读） | ❌ | ❌ | ✅ |
| `edit.visibleWhen`（可见条件） | ✅ | ✅ | ❌ |
| `edit.mode`/`edit.required`/`display.*`/`formula`/`dependsOn`/`unitField`/`agg`/`width`/`frozen`/`visible` | ✅ | ✅ | ✅ |

---

## 六、已知缺口（生成时需知）

来自 `../../../../docs/表格组件编辑渲染体系与三元定义缺口分析.md`：

1. **DOC 装载路径"裸奔"**：`cmx-doc-meta-loader.js` 的 `buildColumnModel` 只消费 6 属性（id/caption/dataType/width/align/editMode），DOC 定义里的 `decimalDigits`/`refDict`/`display` 等全部丢弃。用 `/api/doc/meta` 动态装载时需在 pageFn 手动增强。
2. **schema 可填但 CmxColumn 不消费**：`defaultValue`/`unique`/`searchable`/`filterable`/`sensitive`/`i18n` —— 搭乘顶层不建模。
3. **CmxColumn 无此键**：`edit.editableWhen`（DCT/DOC 可填）/ `edit.visibleWhen`（DCT/DOC 可填）—— 条件可编辑/可见断链。
4. **运行时无编辑器**：`cmx-textarea-input`/`cmx-richtext-input`/`image`/`video`/`ref` 退化。
5. **三元 schema 无录入入口**：`display.badgeMap`/`display.icon`/`display.link`/`display.actions`/`display.cellStyle` —— CmxColumn 运行时支持，但设计器录不了，需 pageFn 手动构造。

---

## 七、计算列（不是 edit.mode，是 calcFormula / formula）

⚠️ **`computed` 不是 edit.mode 值**。计算列用 `formula`（三元）或 `calcFormula`（CmxColumn）+ `dependsOn`：

```jsonc
// 三元定义字段
{ "code": "amount", "kind": "measure", "edit": { "mode": "readonly" },
  "formula": "unitPrice * quantity", "dependsOn": ["unitPrice", "quantity"] }

// CmxColumn（pageFn 构造）
{ "id": "subtotal", "edit": { "mode": "readonly" },
  "calcFormula": "r.subtotal = r.qty * r.unitPrice", "dependsOn": ["qty", "unitPrice"] }
```

> 三元的 `formula` 经 FLC `_fieldToColumn` 映射成 CmxColumn 的 `calcFormula`（函数式）。

---

## 八、生成自检清单

- [ ] `edit.mode` 用 EDIT_MODES 16 规范值之一（非自创短名）
- [ ] 字典选择写 `cmx-dict-select`（非 dict-select）
- [ ] 计算列用 `formula`/`calcFormula` + `dependsOn`，不用 `edit.mode: 'computed'`
- [ ] `display.mode` 用 `''`/`text`/`number`/`badge`/`link`/`icon`/`actions` 之一（7 值）
- [ ] `display.negativeColor` 是 boolean 开关（不是颜色值）
- [ ] 数值类 display 属性（format/decimalDigits/thousandSeparator/zeroAsBlank/negativeColor）只在 mode 空/number 生效
- [ ] dict-select 属性落 `editSettings.*`，字典编码跟 refDict 走
- [ ] 三元定义按 appliesTo 设字段（如 source.* 只 FLC、editableWhen 只 DCT/DOC）
- [ ] 避免选会退化的 mode（textarea/richtext/image/video）除非用户知情

---

## 九、关键文件索引

| 用途 | 路径 |
| --- | --- |
| **字段属性权威 schema**（必看） | `packages/cmx-data-comp/src/lib/cmx-field-schema.js`（FIELD_SCHEMA :178-259；EDITOR_PROPERTY_SCHEMA :87-137） |
| edit.mode 值域 | `packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js`（EDIT_MODES :9-26） |
| CmxColumn display/edit 定义 | `packages/cmx-data-comp/src/lib/cmx-column.js`（display :120-129；edit :131-142） |
| 类型判定核心 | `packages/cmx-data-comp/src/lib/cmx-column-adapter.js`（_cmxTableType :358-363） |
| dict-select 字段类型 | `packages/cmx-data-comp/src/lib/cmx-dict-field-type.js` |
| 缺口分析（权威） | `../../../../docs/表格组件编辑渲染体系与三元定义缺口分析.md` |
| FLC 字段→列映射 | `packages/cmx-data-comp/src/lib/flexible-combination-engine.js`（_fieldToColumn :424-515） |
| DOC 装载（薄弱） | `packages/cmx-data-comp/src/lib/cmx-doc-meta-loader.js`（buildColumnModel :108-122） |
