# FlexibleCombination（弹性组合 / 动态列）

> 何时读：L2 需要上下文驱动的动态列（选科目后列变化、选交易类型后字段不同）。
> 别名 **ContextProfile**（早期设计稿用名，指同一个类）。
> 源码：`packages/cmx-data-comp/src/lib/cmx-flexible-combination.js` + `flexible-combination-engine.js`

---

## 一句话

FlexibleCombination = **"上下文变化 → 列模型跟着变"的自动化**。选了"应收账款"科目，凭证分录的列就变成"客户+部门+金额"；选了"原材料"，列变成"仓库+数量+单价"。

---

## 完整流程（锚点 → 引擎 → 改写列）

```
用户操作（选主行某维度值）
   ↓
锚点变化（如 account=1122）
   ↓
查缓存 / 调 serviceFn / fetch apiPath / 用 inlineData
   ↓
得到 rule + dimensions
   ↓
FlexibleCombinationEngine.resolveMergedRule → buildColumns
   ↓
得到 CmxColumn 数组
   ↓
columnModel.setMembers(columns)  ← 改写目标列模型
   ↓
派发 columns-changed → 可视组件重渲染
```

---

## 字段表（props）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `domain` | string | 否 | `''` | DAM 第 1 段（业务域），如 `fi` |
| `app` | string | 否 | `''` | DAM 第 2 段（应用），如 `gl` |
| `module` | string | 否 | `''` | DAM 第 3 段（模块），如 `fi_gl_base_data` |
| `scenario` | string | 否 | `''` | 业务场景，如 `account` / `trade` |
| `columnModelId` | string \| `Record<表名,string>` | **是** | `''` | **目标列模型 instanceId**；对象形态为按表多绑定（见下节） |
| `serviceFn` | string | 否 | `''` | 自定义取数服务（pageService 名） |
| `apiPath` | string | 否 | `/api/flexible-combination/rule` | 默认 API |
| `anchorDimensions` | array | ⚠️ 已废弃 | `[]` | 模型侧从未消费（死配置）；锚点维度在**档案级** anchorDimensions 配置（管理页维护），后端用它识别 query 里的锚点键 |
| `inlineData` | object | 否 | （无） | **直接内联**的规则 JSON（开页生效，不请求后端；仅 inline fields 方言；设计器中收在"高级"折叠里） |

**默认 props**（源码 `page-data-panel-models.js`）：
```js
{ domain: '', app: '', module: '', scenario: '',
  columnModelId: '', serviceFn: '', apiPath: '/api/flexible-combination/rule',
  anchorDimensions: [] }
```

> **注意 app vs application**：FlexibleCombination 真实字段名是 **`app`**（不是 `application`）。这与 DCT/DOC 相反——见 SKILL.md 陷阱清单。

### 关键：columnModelId 必须对齐

`columnModelId` 必须指向**已存在**的 CmxColumnModel 的 instanceId。拼错会**静默失败**（控制台 warn，列保持原状）。

### 多绑定（按表路由字段集，2026-08 起）

`columnModelId` 支持两种形态：

- **string（单绑定）**：命中的**字段集0**（`rule.detail`）写入该列模型——旧行为完全不变。
- **`{ 表名: 列模型ID }`（多绑定）**：规则的**每个字段集**按 `table` 路由到对应列模型；
  `'*'` 键为未命中表的兜底。字段集定义：index 0 = `rule.detail`（table = `detail.table`），
  index ≥ 1 = `detail.fieldTabs[]`（每项自带 `table`，管理页"字段集 Tab"编辑的就是它们）。
  未匹配且无兜底的字段集 `console.warn` 跳过（不静默丢弃）。

```jsonc
{ "modelType": "FlexibleCombination", "instanceId": "fc", "props": {
    "scenario": "cmxfico",
    "columnModelId": { "cv_acc_line": "accModel", "cv_aux_line": "auxModel" }
} }
```

> 多规则命中时后端 `/rule` 返回的合并规则会**保留 `detail.table` 并按表聚合 `fieldTabs`**
> （同名表字段"首现定序、高分覆盖"合并，与 detail 同策略；overlay 读时展开已覆盖 fieldTabs）。
> 单绑定模式下多字段集仅字段集0 生效并 `console.info` 提示。

---

## DAM 三段定位 + scenario

`domain` / `app` / `module` / `scenario` 组合告诉系统"去哪取这个弹性组合的规则"：

| 段 | 含义 | 例子 |
| --- | --- | --- |
| `domain` | 业务域 | `fi` / `ar` / `ap` / `fa` / `hr` |
| `app` | 应用 | `gl` / `ap` / `cmxfico` |
| `module` | 模块 | `fi_gl_base_data` / `cmxfico` |
| `scenario` | 业务场景 | `account`（科目辅助核算）/ `trade`（交易明细） |

后端：模型中心微服务（独立仓 `cmx-model`），规则真源 `backend/cmx-model/data/meta/flexible-combination/<domain>/<app>/<module>/<scenario>.json`，门户经反代暴露 `/api/flexible-combination/*`（`backend/cmx-container/assets/model/data/meta/` 下同名文件为迁移遗留副本，勿改）。

---

## 三种数据来源（重点）

### 1. inlineData（声明式，开页生效，最简单）

规则 JSON 直接写在 props 里，**开页立即生效**，无需后端：

```jsonc
{
  "modelType": "FlexibleCombination",
  "instanceId": "detailFC",
  "props": {
    "domain": "fi", "app": "gl", "module": "fi_gl_base_data",
    "scenario": "account",
    "columnModelId": "detailModel",
    "inlineData": {
      "rule": {
        "id": "demo",
        "detail": { "fields": [
          { "code": "customer", "kind": "dimension", "edit": { "mode": "select", "required": true } },
          { "code": "amount",   "kind": "measure",   "edit": { "mode": "cmx-number-input" } }
        ]}
      },
      "dimensions": {
        "customer": {
          "name": "客户", "valueType": "select",
          "values": [ { "code": "C-001", "name": "上海科技" } ]
        }
      }
    }
  }
}
```

> `initPageModels` 在第二轮回填 FC 时调 `fc.setCombination(p.inlineData)` 自动应用。

### 2. serviceFn（推荐：动态取数）

models 面板：
```jsonc
{
  "modelType": "FlexibleCombination",
  "instanceId": "detailFC",
  "props": {
    "domain": "fi", "app": "gl", "module": "fi_gl_base_data",
    "scenario": "account",
    "columnModelId": "detailModel",
    "serviceFn": "resolveFlexibleCombination"
  }
}
```

pageServices：
```jsonc
{ "name": "resolveFlexibleCombination", "type": "rest",
  "url": "/api/flexible-combination/rule", "method": "GET" }
```

pageFn 触发（一行）：
```js
function onEntrySelected(e) {
  var rowId = e?.detail?.id
  if (!rowId) return
  var row = host.ms.getRow('head.items', rowId)
  host.detailFC.loadByAnchor({ account: row?.acctCode || '' })
}
```

### 3. setCombination（运行时 JSON 直设）

pageFn 里直接喂 JSON：

```js
// 形态 A：单规则
host.detailFC.setCombination({ rule, dimensions })

// 形态 B：多规则 + 锚点
host.detailFC.setCombination({ rules: [...], dimensions, anchor: { account: '1122' } })

// 形态 B 简写：后端整份 /config 直接喂入
host.detailFC.setCombination({ config: backendConfig, anchor: { account: '1122' } })
```

> **不合法**（既无 `rule` 也无 `rules`）→ `console.warn` + **不写入** columnModel，目标列保持原状。

---

## 两种 JSON 形态

### 形态 A：单规则（最常见）

```jsonc
{
  "rule": {
    "id": "fi-cash",
    "detail": { "fields": [ /* 一组 FieldSpec */ ] }
  },
  "dimensions": { /* 维度定义 */ }
}
```

### 形态 B：多规则 + 锚点

```jsonc
{
  "rules": [ /* 多条规则，按 anchor 选 */ ],
  "dimensions": { /* 所有维度 */ },
  "anchor": { "account": "1122" }   // 在 rules 里按 anchor 解析一条
}
```

也接受 `{ "config": { rules, dimensions }, "anchor": {...} }` 套层形式。

---

## FieldSpec（弹性组合里一列）—— 字段三态

每个 `rule.detail.fields[]` 是一个 FieldSpec：

| 字段 | 含义 |
| --- | --- |
| `code` | 字段 id（列编码） |
| `kind` | **`dimension` / `attribute` / `measure`** |
| `caption` | 显示标题 |
| `dataType` | text / number / date / select / ref |
| `valueSourceId` | dimension：值主数据 |
| `source` | attribute：从哪带出 `{ dimension, attribute }` |
| `defaultFrom` | measure：默认值来源 |
| `edit` | 编辑配置 `{ mode, required, ... }` |
| `formula` | computed measure 计算式 |
| `dependsOn` | 计算依赖 |
| `validations` | 校验规则 |
| `display` | 显示配置 |
| `unitField` | 单位字段 |

### 字段三态（kind）

> FLC 的 `edit.mode` 同样走 `cmx-field-uicontrol.js` 的 EDIT_MODES 规范值域（见 `../../cmx-components-guide/references/field-edit-display-modes.md`），不要用 `input`/`computed`/`tree-ref` 等非规范短名。

| 态 | 取值 | edit.mode | 典型 |
| --- | --- | --- | --- |
| **dimension**（维度） | 从某维度主数据选 | `cmx-dict-select` / `combo` / `select` | 客户、产品、币种 |
| **attribute**（属性） | 从已选维度自动带出 | `readonly` | 产品→规格、单位 |
| **measure**（度量） | 数值（输入或计算） | `cmx-number-input`（计算列配 `formula`+`dependsOn`，edit.mode 设 `readonly`） | 单价、数量、金额 |

**完整 FieldSpec 示例**：
```jsonc
{
  "code": "amount",
  "kind": "measure",
  "caption": "金额",
  "dataType": "number",
  "defaultFrom": { "dimension": "currency", "attribute": "todayRate" },
  "edit": { "mode": "cmx-number-input", "required": false },
  "formula": "unitPrice * quantity",
  "dependsOn": ["unitPrice", "quantity"],
  "validations": [ { "expr": "quantity > 0", "message": "数量须大于 0" } ],
  "display": { "decimals": 2, "thousand": ",", "zeroBlank": true },
  "unitField": "uom"
}
```

三种 kind 各一例：
```jsonc
// 维度
{ "code": "customer", "kind": "dimension", "valueSourceId": "customerMaster",
  "edit": { "mode": "cmx-dict-select", "required": true } }

// 属性（带出）
{ "code": "spec", "kind": "attribute",
  "source": { "dimension": "product", "attribute": "spec" },
  "edit": { "mode": "readonly" } }

// 度量（输入）
{ "code": "quantity", "kind": "measure", "edit": { "mode": "cmx-number-input" },
  "validations": [{ "expr": "quantity > 0", "message": "数量须大于 0" }] }

// 度量（计算）
{ "code": "amount", "kind": "measure", "edit": { "mode": "readonly" },
  "formula": "unitPrice * quantity", "dependsOn": ["unitPrice", "quantity"] }
```

---

## 匹配评分（resolveMergedRule）

多规则场景，引擎按 anchor 选规则：

| 评分来源 | score |
| --- | --- |
| `match` 全部字段精确等值（`account: '1122'`） | 3 |
| `match` 命中 `$in` / `$under` | 1.5 |
| `match` 命中维度属性（`account.category === 'receivable'`） | ~1 |
| anchor.dimensions 相同但无 match 的兜底规则 | 0 |
| 任一条件不符 | -1（淘汰） |

**最终得分**：`specificity = score * 100 + 锚点维度数`

**字段合并语义**（生产默认 `resolveMergedRule`）：
- 所有 score ≥ 0 的命中规则**全部参与**
- 同名字段取 specificity 高者胜出；同分取定义顺序靠前者
- 全部不命中 → 返回 `null`（调用方给最小列集）

### 层级泛化匹配（`$under` + `<dim>.__path`，L1 联动 L2 联动 L3）

树形维度（如会计科目）可把规则配在**祖先值**上，选中子孙值时通过祖先链联动命中：

- **锚点协议**：调用方在 anchor 里附带 `"<dim>.__path"` 键（逗号分隔的祖先链**含自身**，
  query 形态 `gl_account.__path=2,2221,222101`；服务端 handler 自动拆为数组）。
- **规则侧**：`"match": { "gl_account": { "$under": "2221" } }` —— 锚点值等于 `2221`，
  或 `__path` 里含 `2221` 时命中，得 1.5 分（介于 `$in` 与精确 3 分之间）。
- **联动语义**：选中 L3 科目 222101（path=2,2221,222101）时，配在 L1 负债类（$under 2）、
  L2 应交税费（$under 2221）、L3 进项税（精确 222101）与兜底的规则**全部命中并合并**——
  字段位置 L1 基础在前（首现序），同名字段 L3 精确（3 分）覆盖 L2/L1 泛化（1.5 分）。
- 无 `__path` 时 `$under` 退化为值相等匹配；属性路径条件（`dim.attr`）不感知层级。
- 双引擎对称实现：Rust `engine/mod.rs`（`anchor_path_values` + `$under`）与 JS
  `flexible-combination-engine.js`（`anchorPathValues` + `$under`）。
- **管理页配置**：规则 match 行式编辑器的操作符下拉选「**属于子级($under)**」，取值控件
  为维度列的字典选择器——从树形字典里选**任意层级节点**（选大类=配 L1、选中类=配 L2、
  选叶子=配 L3）；序列化即 `{"$under": "所选节点值"}`，回显双向兼容。
- 案例参考：`cmxfico.json`（r-l1-asset / r-l1-liability / r-l2-tax / r-l3-vat-in / r-fallback）
  + `voucher-flex.html`（**行数据驱动**：点分录行 → `applyFlexByRow` 由行科目值查科目树
  推导祖先链 → `loadByAnchor` 带 `__path`，规则链随行科目层级变化）。

---

## 公式引擎（formula-eval）

- **不用裸 eval**——白名单运算符和函数
- 运算符：`+ - * / ( )`
- 字段引用（裸 code）：`amount` → 当前行的 `amount` 字段值
- 函数：`ROUND(x, n)` / `ABS(x)` / `MIN(a, b)` / `MAX(a, b)` / `IF(cond, a, b)`
- 链式计算：`dependsOn` 建有向图 → 拓扑排序后按序重算

```jsonc
{
  "code": "amount", "kind": "measure", "edit": { "mode": "readonly" },
  "formula": "unitPrice * quantity",
  "dependsOn": ["unitPrice", "quantity"],
  "display": { "decimals": 2, "thousand": "," }
}
```

> 公式保存期跑 validations + 必填检查。

---

## 运行时 API（pageFn 里可用）

```js
const fc = host.detailFC

// 走后端取规则（按 anchor）
await fc.loadByAnchor({ account: row.acctCode })
// → Promise<{ ruleId, fromCache }>

// 直接 JSON 喂入（最常用：inlineData 走的就是它）
fc.setCombination({ rule, dimensions })
fc.setCombination({ rules, dimensions, anchor: { account: '1122' } })

// 细粒度：单规则直设
fc.setRule({ rule: serverRule, dimensions, anchor })

// 清空缓存 + 还原初始列
fc.clear()

// 只清某个 anchor 的缓存
fc.invalidateCache({ account: '1122' })
```

---

## 事件（未在设计器暴露，需 pageFns 监听）

> FlexibleCombination 事件**不在 Models 面板「事件」Tab 里**。要监听，在 pageFn 里用 `addEventListener`：

| 事件名 | 含义 | event.detail |
| --- | --- | --- |
| `flexible-combination-loaded` | 规则应用成功 | `{ anchor, ruleId, fromCache }` |
| `flexible-combination-error` | 取数失败或解析失败 | `{ anchor, error }` |
| `flexible-combination-cleared` | `clear()` 调用 | （无 detail） |

**示例**（pageFn 里）：
```js
host.detailFC.addEventListener('flexible-combination-loaded', function (e) {
  console.log('规则应用成功：', e.detail.ruleId, '（缓存：' + e.detail.fromCache + '）')
})
host.detailFC.addEventListener('flexible-combination-error', function (e) {
  console.warn('弹性组合失败：', e.detail.error)
})
```

---

## 完整模板：会计科目辅助核算（L1 + L2 组合）

**场景**：选 `account = 1122`（应收账款）→ 显示客户/部门/金额；选 `account = 6601`（销售费用）→ 显示客户/项目/金额

### models 数组（含 CmxColumnModel 目标 + FlexibleCombination）

```jsonc
[
  {
    "modelType": "CmxColumnModel",
    "instanceId": "detailModel",
    "props": {
      "datasetId": "details",
      "columns": [],             // 初始为空，由 FC 填充
      "columnGroups": []
    }
  },
  {
    "modelType": "FlexibleCombination",
    "instanceId": "detailFC",
    "props": {
      "domain": "fi", "app": "gl", "module": "fi_gl_base_data",
      "scenario": "account",
      "columnModelId": "detailModel",
      "serviceFn": "resolveFlexibleCombination",
      "apiPath": "/api/flexible-combination/rule"
    }
  }
]
```

### pageService

```jsonc
{ "name": "resolveFlexibleCombination", "type": "rest",
  "url": "/api/flexible-combination/rule", "method": "GET" }
```

### pageFn 触发

```js
function onEntrySelected(e) {
  var rowId = e?.detail?.id; if (!rowId) return
  var row = host.ms.getRow('head.items', rowId)
  host.detailFC.loadByAnchor({ account: row?.acctCode || '' })
}
```

### 后端按 anchor 返回（参考）

选 account=1122 时后端返回：
```jsonc
{
  "rule": {
    "id": "fi-receivable",
    "anchor": {
      "dimensions": ["account"],
      "match": { "account": { "category": "receivable" } }
    },
    "detail": { "fields": [
      { "code": "customer",   "kind": "dimension", "edit": { "mode": "cmx-dict-select", "required": true } },
      { "code": "department", "kind": "dimension", "edit": { "mode": "combo", "parent": "parentId" } },
      { "code": "amount",     "kind": "measure",   "edit": { "mode": "cmx-number-input" } }
    ]}
  },
  "dimensions": { /* ... */ }
}
```

### inlineData 替代方案（不走后端）

把规则直接写死在页面：
```jsonc
{
  "modelType": "FlexibleCombination",
  "instanceId": "detailFC",
  "props": {
    "domain": "fi", "app": "gl", "module": "fi_gl_base_data",
    "scenario": "account",
    "columnModelId": "detailModel",
    "inlineData": {
      "rules": [
        {
          "id": "fi-receivable",
          "anchor": { "dimensions": ["account"], "match": { "account": "1122" } },
          "detail": { "fields": [
            { "code": "customer", "kind": "dimension", "edit": { "mode": "cmx-dict-select", "required": true } },
            { "code": "amount",   "kind": "measure",   "edit": { "mode": "cmx-number-input" } }
          ]}
        },
        {
          "id": "fi-default",
          "anchor": { "dimensions": ["account"] },
          "detail": { "fields": [
            { "code": "remark", "kind": "attribute", "edit": { "mode": "cmx-text-input" } },
            { "code": "amount", "kind": "measure",   "edit": { "mode": "cmx-number-input" } }
          ]}
        }
      ],
      "dimensions": {
        "customer": { "name": "客户", "valueType": "ref" }
      }
    }
  }
}
```

> 用 inlineData 时，pageFn 仍需调 `host.detailFC.loadByAnchor({account: '1122'})` 触发规则选择（或开页用 setCombination 直接喂选中结果）。

---

## Overlay 模式（引用 DOC 列，不重复定义）

> 关键设计：弹性组合**不应该重复定义**单据已有的列，而应该**引用 + 增量**。

```jsonc
// ref 字段（Overlay 模式）
{
  "ref": "voucher_detail.cost_center_id",   // 锚点：DOC 的「表.列」
  "over": { "edit": { "required": true } }  // 只写差异
}
```

现状（inline）是规则里整列深拷贝；未来 ref + over 只写差异。生成时若目标 DOC 已定义该列，优先用 ref + over。

---

## 关键特性

| 特性 | 说明 |
| --- | --- |
| 零页面胶水 | 业务页只剩一句 `loadByAnchor({...})` 或用 inlineData |
| 多消费者 | 同一 CmxColumnModel 被多个组件绑时，列变更通过事件自动广播 |
| 缓存 | 按锚点签名缓存最近结果，重复锚点不再请求后端 |
| 回退 | 服务失败或无匹配规则 → 自动还原到列模型初始 members |
| 可叠加 | 多次 setCombination 在同一 CmxColumnModel 上交替使用 |

---

## 容易踩的坑

| 坑 | 正确做法 |
| --- | --- |
| 字段名写 `application` | FC 用 **`app`** |
| `columnModelId` 写错 | 严格对齐目标 CmxColumnModel instanceId，否则静默失败 |
| 配了多字段集但用单绑定 | 单绑定只吃字段集0（有 console.info 提示）；要全用需 `{ 表名: 列模型ID }` 多绑定 |
| props 不写 module 担心不加载 | domain/app/module 可由页面坐标兜底；运行时按**解析后的坐标**判断是否自动 loadDefaultRule |
| `inlineData` 既无 `rule` 又无 `rules` | 至少要有其一，否则 warn + 不派发事件 |
| 锚点不传或传空 | 引擎给"最小列集"或回退到初始列 |
| 后端没匹配规则 | 调用方拿到 null → 列保持原状 |
| 改 scenario 后没清缓存 | 旧规则可能仍被命中，调 `clear()` 一次 |
| 监听 FC 事件写进 events Tab | 写进 pageFns 用 addEventListener（FC 事件未在设计器暴露） |
