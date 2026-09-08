# CmxMasterSlave（主从协调器）

> 何时读：L1+ 需要主从联动 + 自动聚合（凭证头/分录、订单/明细、BOM 展开）。
> 源码：`packages/cmx-data-comp/src/lib/cmx-master-slave.js`

---

## 一句话

CmxMasterSlave = **多张表的管家**。不存业务数据，做的事是：把主表 + 子表 + 孙表绑在一起，让**选主表行 → 自动刷子表 → 改子表值 → 自动汇总到主表**。

---

## 四大职责（生成时心里有数）

| 职责 | 说明 |
| --- | --- |
| 1. 持有递归主从数据树 | 每个 row 可挂 `_children: { tableId: CmxDataSet }` |
| 2. 视图按 path 注册 | `ms.bindForm('head', formEl)` / `ms.bindTable('head.items', gridEl)` |
| 3. 维护"当前选中行" | 上级选中变 → 下级视图自动重算（联动） |
| 4. 自动跑聚合规则 | 监听 cell-changed / row-added → 跑 sum/avg/min/max/count → 回写目标字段 |

---

## 字段表（props）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `schema` | array | 是（L1） | `[]` | **路径树**——定义有哪些表、父子关系 |
| `aggregations` | array | 否 | `[]` | 聚合规则——子表改了写回主表 |
| `relations` | array | 否 | （兜底读 dataFlow.relations） | 平铺数据主外键关系 |
| `editable` | boolean | 否 | （默认） | 全局可编辑标志 |

**默认 props**（源码 `page-data-panel-models.js`）：
```js
{ schema: [], aggregations: [] }
```

> 注意：`relations` 在 `initPageModels` 里**从 `dataFlow.relations` 兜底读取**（源码 `init-page-models.js`）。如果 models[i].props 里没写 relations，务必把 relations 写到顶层 `__designer_meta__.dataFlow.relations`。

---

## Schema（路径树）—— 核心配置

Schema 是一棵"表树"，每个节点 = 一张表。

### 写法

```jsonc
{
  "schema": [
    { "id": "head" },
    { "id": "items", "children": [
      { "id": "taxes" }
    ]},
    { "id": "shippings" }
  ]
}
```

### 展开规则（点分隔完整路径）

| 节点 | 完整路径 | 含义 |
| --- | --- | --- |
| `head` | `head` | 表头（顶级） |
| `items`（head 的 child） | `head.items` | 头下面的"分录"子表 |
| `taxes`（items 的 child） | `head.items.taxes` | 分录下面的"税行"孙表 |
| `shippings`（head 的 child） | `head.shippings` | 头下面的"物流"子表 |

**关键规则**：
1. **所有 path 用 `.` 分隔的完整路径**（如 `head.items`，不是 `items`）——协调器靠完整 path 定位父级
2. **每个 id 必须唯一**——重复抛 `duplicate path`
3. 子表通过父节点的 `children` 数组声明

### schema 节点字段

| 字段 | 含义 |
| --- | --- |
| `id` | 节点编码（表名，单层） |
| `children` | 子节点数组（可选） |

> `initPageModels` 会调 `stripSelectors(schema)` 只保留 `{id, children}`，所以节点上的其它字段会被忽略——业务字段写在 aggregations / ColumnModel 里。

---

## Aggregations（聚合规则）—— 自动汇总

### 写法

```jsonc
{
  "aggregations": [
    {
      "from":     "head.items",        // 从哪收集（路径）
      "agg":      "sum",               // sum / avg / min / max / count
      "field":    "debit",             // 收集哪个字段
      "to":       "head",              // 写回到哪（路径）
      "toField":  "totalDebit"         // 写到哪个字段
    },
    {
      "from":     "head.items",
      "agg":      "sum",
      "field":    "credit",
      "to":       "head",
      "toField":  "totalCredit"
    },
    {
      "from":     "head.items.taxes",
      "agg":      "sum",
      "field":    "tax",
      "to":       "head.items",
      "toField":  "totalTax"
    }
  ]
}
```

### aggregation 字段

| 字段 | 含义 |
| --- | --- |
| `from` | 从哪收集（schema 路径） |
| `agg` | sum / avg / min / max / count |
| `field` | 收集哪个字段 |
| `to` | 写回到哪（schema 路径） |
| `toField` | 写到哪个字段 |
| `scope` | `siblings`（默认）/ `all` |

### 聚合语义（决定收集范围）

| 情形 | 行为 |
| --- | --- |
| `to` 是 single（与 `from` 共同祖先是 single 或 root） | 在整树里收集 from → 写到 to 那一行 |
| `to` 是 list（与 `from` 有共同 list 祖先） | 对 to 列表中**每一行 t**，把 source 限定在 t 的子树 |
| `scope: 'all'` | 强制忽略上下文，整树聚合 |

### 触发时机

- `setData` / `setFlatData` 之后整体跑一次（"预热"）
- `cmx-cell-changed`（某字段值变）→ 跑命中 from 的规则
- `cmx-row-added` / `cmx-row-removed` → 跑 `from === X` 或 `from` 以 `X` 为前缀的规则

> 规则按 `from` 反向索引，无关规则不跑，性能可控。

---

## Relations（平铺数据主外键）—— setFlatData 必备

当用 `setFlatData`（推荐，简单）喂数据时，需要 relations 告诉 MS 怎么把平铺数组组装成树。

### 写法（注意：放在 dataFlow.relations）

```jsonc
// __designer_meta__.dataFlow
{
  "dataFlow": {
    "schema": [],           // 可空，schema 在 models 里写
    "aggregations": [],     // 可空
    "relations": [
      { "parent": "head",       "child": "items",  "parentKey": "id", "childKey": "headId"  },
      { "parent": "items",      "child": "taxes",  "parentKey": "id", "childKey": "itemId" }
    ]
  }
}
```

### relation 字段

| 字段 | 含义 |
| --- | --- |
| `parent` | 父表名（schema 单层 id） |
| `child` | 子表名（schema 单层 id） |
| `parentKey` | 父表关联字段（通常 `id`） |
| `childKey` | 子表指向父的外键字段 |

> 子表行必须有 `<childKey>` 字段指向父表 `<parentKey>`，MS 据此自动建树。

---

## 视图绑定（DOM + pageFn）

### DOM 声明式（推荐）

```html
<!-- 表头表单（single） -->
<cmx-ui5-form id="headForm"
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head"
  data-cmx-kind="single"
  data-cmx-model-id="headModel">
</cmx-ui5-form>

<!-- 分录表格（list） -->
<cmx-revo-grid id="itemsGrid"
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head.items"
  data-cmx-kind="list"
  data-cmx-model-id="itemModel">
</cmx-revo-grid>

<!-- 税行表格（孙层） -->
<cmx-revo-grid id="taxGrid"
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head.items.taxes"
  data-cmx-kind="list"
  data-cmx-model-id="taxModel">
</cmx-revo-grid>
```

**DOM 属性含义**（`initPageModels` 扫描时）：
- `data-cmx-master-slave-id`：MS 的 instanceId
- `data-cmx-dataset-id`：schema **完整路径**
- `data-cmx-kind`：`single`（表单，调 bindForm）/ `list`（表格，调 bindTable）
- `data-cmx-model-id`：CmxColumnModel 的 instanceId（调 setColumnModel）

> `data-cmx-kind` 缺省时：`cmx-ui5-form` 默认 `single`，其它默认 `list`。但建议显式写。

### pageFn 命令式（手动绑，用于动态/复杂场景）

```js
const ms = host.ms
ms.bindForm('head', host.shadowRoot.querySelector('#headForm'))
ms.bindTable('head.items', host.shadowRoot.querySelector('#itemsGrid'))
ms.bindTable('head.items.taxes', host.shadowRoot.querySelector('#taxGrid'))
```

> 真实样例 `erp-voucher-cnpc-ms.html` 会检查 `ms._bindings` 避免重复绑（initPageModels 已绑过的不重复）。

---

## 数据装载：setFlatData vs setData

### setFlatData（推荐，简单场景）

平铺数组 + relations，MS 自动建树：

```js
// pageFn 里
host.ms.setFlatData({
  head: [
    { id: 'h1', voucherNo: 'V001', totalDebit: 0, totalCredit: 0 }
  ],
  items: [
    { id: 'i1', headId: 'h1', acctCode: '1001', debit: 50000, credit: 0 },
    { id: 'i2', headId: 'h1', acctCode: '1122', debit: 0, credit: 50000 }
  ],
  taxes: [
    { id: 't1', itemId: 'i1', tax: 0 }
  ]
})
// relations 从 dataFlow.relations 读取，自动建 head→items→taxes 树
```

> `setFlatData` 内部自动定位各根首行并自上而下级联（`_primeCursors`），无需手动 moveFirst。

### setData（复杂场景，自己管 CmxDataSet）

```js
host.ms.setData({
  tables: {
    head: headDs,      // CmxDataSet 实例
    items: itemsDs,
    taxes: taxesDs
  }
})
```

---

## 事件清单

| 事件名 | 何时触发 | event.detail |
| --- | --- | --- |
| `change` | 某行某字段值变化 | `{ path, id, key, value, row }` |
| `select` | 某行被选中 | `{ path, id }` |
| `aggregate` | 聚合规则触发 | `{ rule, value, targetId }` |

**示例**：监听聚合结果
```jsonc
{
  "modelType": "CmxMasterSlave",
  "instanceId": "ms",
  "props": { "schema": [...], "aggregations": [...] },
  "events": {
    "aggregate": "console.log('规则', event.detail.rule.from, '→', event.detail.targetId + '.' + event.detail.rule.toField, '=', event.detail.value)"
  }
}
```

---

## 完整凭证主从协调器模板（三层 head.items.taxes）

```jsonc
// __designer_meta__ 关键片段
{
  "dataFlow": {
    "relations": [
      { "parent": "head",  "child": "items", "parentKey": "id", "childKey": "headId" },
      { "parent": "items", "child": "taxes", "parentKey": "id", "childKey": "itemId" }
    ]
  },
  "models": [
    {
      "modelType": "CmxMasterSlave",
      "instanceId": "ms",
      "props": {
        "schema": [
          { "id": "head", "children": [
            { "id": "items", "children": [
              { "id": "taxes" }
            ]}
          ]}
        ],
        "aggregations": [
          { "from": "head.items",        "agg": "sum", "field": "debit",  "to": "head",       "toField": "totalDebit"  },
          { "from": "head.items",        "agg": "sum", "field": "credit", "to": "head",       "toField": "totalCredit" },
          { "from": "head.items.taxes",  "agg": "sum", "field": "tax",    "to": "head.items", "toField": "totalTax"    }
        ]
      }
    },
    {
      "modelType": "CmxColumnModel",
      "instanceId": "headModel",
      "props": {
        "datasetId": "head",
        "columns": [
          { "id": "voucherNo",     "caption": "凭证号",   "dataType": "VARCHAR", "width": "140px", "edit": { "mode": "cmx-text-input" } },
          { "id": "totalDebit",    "caption": "借方合计", "dataType": "NUMBER",  "width": "120px", "edit": { "mode": "readonly" } },
          { "id": "totalCredit",   "caption": "贷方合计", "dataType": "NUMBER",  "width": "120px", "edit": { "mode": "readonly" } }
        ]
      }
    },
    {
      "modelType": "CmxColumnModel",
      "instanceId": "itemModel",
      "props": {
        "datasetId": "items",
        "columns": [
          { "id": "acctCode", "caption": "科目编号", "dataType": "VARCHAR", "width": "110px" },
          { "id": "summary",  "caption": "摘要",     "dataType": "VARCHAR", "width": "220px" },
          { "id": "debit",    "caption": "借方",     "dataType": "NUMBER",  "width": "130px", "agg": "sum" },
          { "id": "credit",   "caption": "贷方",     "dataType": "NUMBER",  "width": "130px", "agg": "sum" }
        ]
      }
    },
    {
      "modelType": "CmxColumnModel",
      "instanceId": "taxModel",
      "props": {
        "datasetId": "taxes",
        "columns": [
          { "id": "taxName", "caption": "税种", "dataType": "VARCHAR", "width": "120px" },
          { "id": "tax",     "caption": "税额", "dataType": "NUMBER",  "width": "120px", "agg": "sum" }
        ]
      }
    }
  ]
}
```

HTML 绑定（三层 grid）：
```html
<cmx-ui5-form id="headForm"
  data-cmx-master-slave-id="ms" data-cmx-dataset-id="head"
  data-cmx-kind="single" data-cmx-model-id="headModel">
</cmx-ui5-form>

<cmx-revo-grid id="itemsGrid"
  data-cmx-master-slave-id="ms" data-cmx-dataset-id="head.items"
  data-cmx-kind="list" data-cmx-model-id="itemModel" style="height:200px;">
</cmx-revo-grid>

<cmx-revo-grid id="taxGrid"
  data-cmx-master-slave-id="ms" data-cmx-dataset-id="head.items.taxes"
  data-cmx-kind="list" data-cmx-model-id="taxModel" style="height:150px;">
</cmx-revo-grid>
```

pageFn 装载：
```js
// pageFns[0].body
host.ms.setFlatData({
  head:  [{ id: 'h1', voucherNo: 'V001', totalDebit: 0, totalCredit: 0 }],
  items: [
    { id: 'i1', headId: 'h1', acctCode: '1001', summary: '收到回款', debit: 50000, credit: 0 },
    { id: 'i2', headId: 'h1', acctCode: '1122', summary: '冲销应收', debit: 0, credit: 50000 }
  ],
  taxes: [{ id: 't1', itemId: 'i1', taxName: '增值税', tax: 0 }]
})
```

---

## 容易踩的坑

| 坑 | 正确做法 |
| --- | --- |
| 路径写 `items` 而非 `head.items` | 写完整路径，MS 靠 path 找父级 |
| schema 里同名 id | 每个 id 唯一，否则抛 `duplicate path` |
| aggregations 的 `to` 指向不存在的 path | 只用 schema 定义过的 path |
| 没绑视图就调 setCurrentId | 业务无影响但视图不刷新 |
| 用 setFlatData 但忘写 relations | relations 写到 `dataFlow.relations` |
| ColumnModel 的 datasetId 写成路径 | 写单层名（如 `items`），DOM 才写路径 |
| SPA 切页忘 destroy() | pageFn 里在适当时机调 `ms.destroy()` 防内存泄漏 |

---

## 业务无感知（重要心智）

**CmxMasterSlave 完全不认任何业务术语**——不认"凭证""客户""订单"，只认 schema 路径、字段名、聚合规则。

含义：同一份 MS 代码可用于会计、库存、订单、CRM。业务逻辑全靠**配置**驱动。"凭证"只是个 `schema: [{id:head, children:[{id:items}]}]` 的业务术语解释。
