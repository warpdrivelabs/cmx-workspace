# 推导规则详细说明

> 本文件配套 [enrich-meta.mjs](../scripts/enrich-meta.mjs)，列出所有推导规则与覆盖优先级。权威值域来源：
> - **edit.mode 16 规范值**：[`packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js`](../../../../packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js)（`EDIT_MODES`）
> - **display.mode 值域**：`packages/cmx-data-comp/src/lib/cmx-field-schema.js` 中 `display.mode` 控件 options（7 个含空串：''/text/number/badge/link/icon/actions；`actions` 操作列属页面级配置，元数据补全不涉及）
> - **CmxColumn display 域结构**：[`packages/cmx-data-comp/src/lib/cmx-column.js`（badge 推断逻辑）](../../../../packages/cmx-data-comp/src/lib/cmx-column.js)

---

## 一、edit.mode 推导（按代码顺序匹配）

| 优先级 | 条件 | 输出 | 备注 |
|---|---|---|---|
| 1 | `dataType='TINYINT'` 且 caption 含「是否/启用/允许/标记」 | `checkbox` | |
| 2 | `isPrimaryKey=1` 或 `id='id'` | `readonly` | 主键永远只读 |
| 3 | `id` 匹配审计字段 (`create_by|create_time|update_by|update_time|delete_flag|row_version|timestamp`) | `none` | 系统字段不可编辑 |
| 4 | `id` 匹配 `*_id\|parent_id\|upper_id\|ancestor_id\|descendant_id` 且**无 refDict** | `readonly` | 内部关系 ID |
| 5 | 有 `refDict` 且 `id` 匹配多值字段 (`*_types?\|required_fields\|optional_fields\|suppressed_fields\|allowed_*`) | `cmx-dict-select` + `multiple: true` | |
| 6 | 有 `refDict` 且 `id='parent_id'` 且是自分级字典 | `cmx-dict-select` + `parent: 'parent_id'` | 弹树选 |
| 7 | 有 `refDict` 且引用的是自分级字典（segment/fs_version/cons_org） | `cmx-dict-select` + `parent: 'parent_id'` | |
| 8 | 有 `refDict`（普通外键） | `cmx-dict-select` | ref 缺编辑器，按缺口分析用 dict-select |
| 9 | `dataType='DATE'` | `cmx-date-input` | |
| 10 | `dataType='DATETIME'` | `cmx-datetime-input` | |
| 11 | `dataType ∈ {INT, BIGINT, TINYINT, DECIMAL, NUMBER}` | `cmx-number-input` | |
| 12 | `dataType='TEXT'` | `cmx-textarea-input` | |
| 13 | `enumValues` 数组非空 | `select` + `options` | |
| 14 | 默认 | `cmx-text-input` | |

> 自分级字典的识别：表层级 `dictMeta.selfHierarchy=true` → 自身和引用自己的字段都走 tree-ref。

## 二、display.mode 推导

| dataType / 特征 | mode | 配套属性 |
|---|---|---|
| 主键 / 内部关系 ID | `text` | 顶层 `visible:false`（不放 display 内） |
| **非 TINYINT** 的 `doc_status` / `*_status` / `batch_status` / `state` | `badge` | `badgeMap`（草稿/过账/冲销等）+ `align:center` |
| **TINYINT** 的 `status` 等字段（0/1 布尔） | `text` | `align:center`（不套业务 badgeMap） |
| `DATE` | `text` | `format:'date:YYYY-MM-DD'` + `align:center` |
| `DATETIME` | `text` | `format:'datetime:YYYY-MM-DD HH:mm:ss'` + `align:center` |
| `DECIMAL` 金额 | `number` | 2 位 + thousands + 零空 + 负红 + 右对齐（**不写 format**） |
| `DECIMAL` 汇率 | `number` | 5 位 + 负红 + 右对齐（无千分位，**不写 format**） |
| `DECIMAL` 百分比 | `number` | N 位 + 右对齐（**不写 format**，用户下拉选 `percent`，小数位由 `decimalDigits` 控） |
| `DECIMAL` 数量/件数/天数 | `number` | 0 位 + 千分位 + 右对齐（**不写 format**，千分位走 `thousandSeparator`） |
| 整数序号（line_no/sort_no/...） | `number` | 0 位 + 千分位 + 右对齐（**不写 format**，千分位走 `thousandSeparator`） |
| `BIGINT` 非 ID | `text` | `align:left` |
| `INT` | `text` | `align:left` |
| `TINYINT`（0/1） | `text` | `align:center` |
| `TEXT` | `text` | `align:left` |
| 其他 VARCHAR | `text` | `align:left` |

> **关键**：纯数值属性（`decimalDigits` / `thousandSeparator` / `zeroAsBlank` / `negativeColor`）**只在 display.mode 为空或 `number` 时生效**（参考 `cmx-field-schema.js` 的 `_displayModeIn(row, ['', 'number'])`）。`display.format` 是「下拉+文本框」复合控件（select-text），**在 `''`/`number`/`text` 三种模式都可用**，按 mode 给不同选项（number→千分位/百分比/货币，text→日期/日期时间）。

## 三、number 列的 5 个数值属性（脚本只补 4 个，format 留给用户）

来自 [cmx-field-schema.js](../../../../packages/cmx-data-comp/src/lib/cmx-field-schema.js)：

| 属性 | 类型 | 说明 | 脚本行为 |
|---|---|---|---|
| `display.format` | select-text（下拉+文本框） | 复合控件按 `display.mode` 分组：number/缺省→`无`/`thousands`/`percent`/`currency:¥`；text→`无`/`date:YYYY-MM-DD`/`datetime:YYYY-MM-DD HH:mm:ss`。下拉选预设，文本框可手改任意值 | **不主动写**（用户手动配，避免重跑脚本时与已配置的值冲突） |
| `display.decimalDigits` | number | 显示小数位 | ✅ 脚本写（取字段 `decimalDigits ?? 2`，整数列写 0） |
| `display.thousandSeparator` | boolean | 千分位 | ✅ 脚本写（金额/数量 `true`，汇率 `false`） |
| `display.zeroAsBlank` | boolean | 0 显示空 | ✅ 脚本写（金额 `true`，其它类型按需） |
| `display.negativeColor` | **boolean**（开关） | 负数标红 | ✅ 脚本写（金额/汇率 `true`） |

⚠️ **`negativeColor` 是 boolean 开关，不是颜色值**。早期误写成字符串 `"red"`，校对时发现 schema 里它是 `control: 'checkbox', valueType: 'boolean'`，已修正为 `true`。

⚠️ **`display.format` 是「用户配置区」，脚本不主动写**：
- 金额列的千分位由脚本写 `thousandSeparator: true` 表达（见上表），无需再写 `format: 'thousands'`；format 下拉虽含 thousands 预设，但金额列默认走 thousandSeparator 复选框
- format 下拉承载 number 模式的 `thousands` / `percent` / `currency:¥`，以及 text 模式的 `date:YYYY-MM-DD` / `datetime:YYYY-MM-DD HH:mm:ss`；文本框可手改任意值（如 `currency:$`）
- 交给用户通过元数据编辑器按业务挑选，一旦写入后脚本不会重写
- 这样保证幂等性：重跑脚本不会因"我猜的默认 format"覆盖用户的实际选择
- 早期版本误把 `format: 'thousands'` / `format: 'percent:N'` 写进 JSON，已用 [clean-number-display.mjs](#九一次性清理脚本) 一次性清理

## 三·补、cmx-dict-select 的 editSettings 推导（14 属性，脚本补 5 个）

当 `edit.mode === 'cmx-dict-select'` 时，配套属性落在 `editSettings.*`（不是 `edit.*`）。参考 [field-edit-display-modes.md §cmx-dict-select](../../cmx-components-guide/references/field-edit-display-modes.md#cmx-dict-select字典选择属性落-editsettings) 共 14 个属性。

### 脚本行为分类

| 属性 | 类型 | 脚本行为 | 推导规则 |
|---|---|---|---|
| `helpLayout` | select | ✅ **必补** | 自分级字典 → `'grid'`（treegrid）；普通字典 → `'classify'`（左分类树+右 grid） |
| `hierarchical` | checkbox | ✅ 自分级字典补 `true` | refDict ∈ `{segment, fs_version, cons_org}` 或表 `selfHierarchy=true` 时 |
| `dictTitle` | text | ✅ 补 | `'选择' + caption.zh_CN`（如"选择国家"） |
| `showClear` | checkbox | ✅ 补 | 非必填字段补 `true`（提升体验） |
| `idCol` | text | ✅ **条件补** | refDict 指向的字典 `baseFieldSet=dictionaryCommonNoIDFields`（无 id 列）→ 补 `'code'`；其余字典走默认 `'id'` 不写 |
| `displayMode` | select | ❌ 不写（用户配置区） | auto/value/code/label/code-label/field —— 业务自选展示样式 |
| `displayTemplate` | text | ❌ 不写 | 如 `'${code} - ${name}'`，配 displayMode=field 用 |
| `codeCol` | text | ❌ 不写（默认 `code`） | |
| `labelCol` | text | ❌ 不写（默认 `name`） | |
| `parentCol` | text | ❌ 不写（默认 `parent_id`） | 仅自分级字典需要，helpLayout=grid 时运行时自动用 |
| `valueField` | text | ❌ 不写（默认 `idCol`） | 写回行字段名 |
| `displayField` | text | ❌ 不写（默认 `name`） | |
| `mruMax` | number | ❌ 不写（默认 10） | 最近选择条数，UI 细节 |
| `dropdownWidth` / `dropdownMaxHeight` | text | ❌ 不写（默认 480px/360px） | UI 尺寸，用户按需调 |
| `placeholder` | text | ❌ 不写 | 可选，用户按需配 |

### 自分级字典识别（决定 helpLayout）

```text
refDict ∈ {'segment', 'fs_version', 'cons_org'}
  或 表 dictMeta.selfHierarchy=true 且引用自身 dictCode
→ helpLayout='grid' + hierarchical=true
否则
→ helpLayout='classify'
```

**grid vs classify 的业务语义**：
- `grid`（treegrid）：纯层级数据（会计科目树、段层级、合并组织树），数据本身就是树
- `classify`（左分类树+右 grid）：业务字典（国家、货币、客户、供应商），左侧按分类浏览，右侧平铺列表

### NoID 字典的 idCol 推导（新增）

**背景**：部分字典共享 `baseFieldSet: "dictionaryCommonNoIDFields"` 字段集，**物理表没有 id 列**，主键就是 `code`。这类字典（country / currency / doc_type / account_type 等 60 本）在被其它表通过 `refDict` 引用时，`<cmx-dict-select>` 默认按 `idCol='id'` 取值会查空，必须显式补 `idCol: 'code'`。

**识别方式**：脚本启动时构建 `baseFieldSets` 映射（`dictCode → baseFieldSet`），字段推导时查 `ctx.baseFieldSets.get(field.refDict)`。

**补全规则**：
- 字段**无** `editSettings` → 全新生成（含 idCol='code'，若 refDict 是 NoID 字典）
- 字段**已有** `editSettings` 但**缺 idCol** → 若 refDict 是 NoID 字典，补 `idCol='code'`；否则不补
- 字段**已有** `editSettings.idCol` → **不覆盖**（保留用户手工意图，即使值不是 'code'）

### 幂等保证

- 字段**无** `editSettings` → 脚本补 5 个属性（helpLayout/hierarchical/dictTitle/showClear/idCol）
- 字段**已有** `editSettings`（含运行时 `dictCode`+`coord` 定位信息）→ **不覆盖**，仅补缺失的 idCol（针对 NoID 字典的 refDict）

### 样例

```jsonc
// segment_id（自分级字典）
{
  "id": "segment_id", "refDict": "segment",
  "caption": { "zh_CN": "归属段" },
  "edit": { "mode": "cmx-dict-select" },
  "editSettings": {
    "helpLayout": "grid",      // ✅ 脚本补
    "hierarchical": true,      // ✅ 脚本补
    "dictTitle": "选择归属段",  // ✅ 脚本补
    "showClear": true          // ✅ 脚本补
  }
}

// country_code（普通字典，但 country 是 NoID 字典）
{
  "id": "country_code", "refDict": "country",
  "caption": { "zh_CN": "国家" },
  "edit": { "mode": "cmx-dict-select" },
  "editSettings": {
    "helpLayout": "classify",  // ✅ 脚本补
    "dictTitle": "选择国家",    // ✅ 脚本补
    "showClear": true,         // ✅ 脚本补
    "idCol": "code"            // ✅ 脚本补（country 是 NoID 字典）
    // 无 hierarchical（非自分级）
  }
}

// 已有运行时定位信息（仅补缺失的 idCol，不覆盖已有属性）
{
  "id": "comp_unit_id", "refDict": "comp_unit",
  "editSettings": {
    "dictCode": "cf_comp_unit",  // 运行时注入，脚本不动
    "coord": { "domain": "fi", "application": "cmxfico", "module": "gl" }
  }
}
```

## 四、dictMeta.idField 修正（NoID 字典）

**规则**：当字典 `baseFieldSet === "dictionaryCommonNoIDFields"` 时，`dictMeta.idField` 必须是 `"code"`。

**原因**：`dictionaryCommonNoIDFields` 字段集**不含 id 列**，物理表主键就是 `code`（如 country / currency / doc_type / account_type 等 60 本字典）。`idField` 写成 `"id"` 会导致运行时按不存在的列取主键，查询失败。

**修正逻辑**（`fixDictMeta` 函数）：
- `baseFieldSet === 'dictionaryCommonNoIDFields'` 且 `idField ∈ {undefined, 'id'}` → 改为 `'code'`
- 已有其它值（如 `'code'`）→ 不动（幂等）

## 五、必填（required）保守原则

满足任一即 `required: true`：
- 字段在 `uniqueKeys` 中（dict 表的复合唯一键）
- `id ∈ {code, name, doc_no, doc_status}`
- 字段 `nullable: false` 且非审计字段

始终 `required: false`：
- `isPrimaryKey=1` / `id='id'`
- `id='parent_id'` / `id='upper_id'`
- 审计字段（`create_by|create_time|update_by|update_time|delete_flag`）

`required: true` 同步写入 `edit.required: true`（保持双写一致）。

## 六、列宽（width）

```text
DATE           130px
DATETIME       160px
TINYINT         90px
BIGINT 关系ID  100px
BIGINT         120px
INT             90px
DECIMAL 汇率/百分比 110px
DECIMAL        140px
TEXT           280px
code           140px
name           180px
doc_no         160px
默认           140px
```

## 七、可见性（visible）/ 冻结（frozen）

- 主键（`isPrimaryKey=1` 或 `id='id'`）→ 顶层 `visible: false`、`frozen: 'left'`
- 内部关系 ID（`*_id|parent_id|upper_id|ancestor_id|descendant_id` 且 dt='BIGINT' 且无 refDict）→ 顶层 `visible: false`
- 其他 → 顶层 `visible` 不设（默认 true）、`frozen` 不设（默认不冻结）

> **frozen 值域**：`''`（空，不冻结）/ `'left'`（左冻结）/ `'right'`（右冻结）。旧布尔 `true` 向后兼容等价 `'left'`。

## 八、幂等保证

脚本对每个字段：
- 若 `field.edit.mode` 已是 16 规范值之一 → **不覆盖**
- 若 `field.edit.mode` 是非法值（如 `text`/`input`/`number`）→ **强制重写**
- 若 `field.display.mode` 已是 6 合法值之一 → **不覆盖**
- 若 `field.display.mode` 是非法值（如 `date`/`datetime`/`checkbox`）→ **强制重写**
- 若 `field.editSettings` 已存在 → 仅补缺失的 idCol（NoID 字典），其余属性不覆盖
- 若 `dictMeta.idField` 是 `'code'` → 不动；NoID 字典的 `'id'`/undefined → 改为 `'code'`

故可重复运行，手工微调不会被破坏。

### 8.1 验证方法

```bash
# 同一份文件跑两次，对比（除 updatedAt 之外应完全一致）
node scripts/enrich-meta.mjs in.json /tmp/run1.json
node scripts/enrich-meta.mjs /tmp/run1.json /tmp/run2.json
diff <(grep -v '"updatedAt"' /tmp/run1.json) <(grep -v '"updatedAt"' /tmp/run2.json)
# 期望：无输出
```

## 九、扩展指引

### 加一条新规则

在 `pickEdit` / `pickDisplay` 中插入匹配条件（顺序敏感），保证规则越靠前越优先。

### 加新 edit.mode 值域

修改顶部 `MODE` 字典（与 [cmx-field-uicontrol.js EDIT_MODES](../../../../packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js) 保持同步），脚本自动用新值。

### 加新 display.mode 值

修改 `DISPLAY_MODES_SET` 集合（与 `packages/cmx-data-comp/src/lib/cmx-field-schema.js` 的 `display.mode` options 保持同步）。

### 加新 status badge

修改 `DOC_STATUS_BADGE` 字典（草稿/过账/冲销/审核/驳回/关闭/预制/模拟），加新 value→{text,color}。

## 十、一次性清理脚本

### `clean-number-display.mjs`

**用途**：清理旧版本 `enrich-meta.mjs` 错误写入的值。位置：项目根的 `/tmp/cmx-meta-enrich/clean-number-display.mjs`（一次性脚本，**不入库**）。

清理规则：
- `display.mode === 'number'` 时，删除 `format` 子项（thousands / percent:N 等）
- `display.negativeColor` 值为字符串 `"red"`（或颜色字符串）→ 转 boolean `true`

```bash
node /tmp/cmx-meta-enrich/clean-number-display.mjs in.json out.json
```

⚠️ 该脚本只用于 4 份元数据的历史值清理（`cmxfico_doc_meta_v2.json` 25 处 `format:thousands` + 27 处 `negativeColor:red`，`cmxfico_dct_meta_v3.json` 4 处 `negativeColor:red`）。后续 `enrich-meta.mjs` 不会再产生这些错误值，不需要重复跑。

## 十一、校验脚本（verify-meta.mjs）

配套 [verify-meta.mjs](../scripts/verify-meta.mjs) 校验元数据合法性，与 enrich 规则一一对应：

| 校验项 | 规则 | 错误标签 |
|---|---|---|
| `edit.mode` | 必须在 16 规范值内（EDIT_MODES） | `[EDIT]` |
| `display.mode` | 必须在 6 合法值内（'' text number badge link icon）；`actions` 属页面级配置，元数据中出现视为非法 | `[DISPLAY]` |
| `dictMeta.idField` | NoID 字典（`baseFieldSet=dictionaryCommonNoIDFields`）必须是 `'code'` | `[IDFIELD]` |
| `editSettings.idCol` | refDict 指向 NoID 字典时必须是 `'code'`（缺失也算错误） | `[IDCOL]` |

```bash
node scripts/verify-meta.mjs <file1.json> [file2.json ...]
# 退出码 0=全通过，1=有错误
```
