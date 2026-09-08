# CmxDataSet（数据集）

> 何时读：需要把数据行装进表格/表单时。L0 起所有场景。
> 源码：`packages/cmx-data-comp/src/lib/cmx-data-set.js`

---

## 一句话

CmxDataSet = **多级树形数据行容器**。一个表格 + 可选子表（行里挂子行）。

---

## 字段表（props）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `dataSource` | string | 否 | `''` | 数据来源（pageService 名）；运行时由 pageFn 主动喂数则留空 |
| `dataSourceEvent` | string | 否 | `'onInit'` | 调用时机（onInit / onClick / onRowSelect ...） |
| `children` | array | 否 | `[]` | 子数据集定义（树形结构） |
| `rows` | array | 否 | `[]` | 初始数据行（一般运行时由 dataSource 填充，或测试用） |

> `instanceId` 是顶层字段（不是 props 里），运行时通过 `host.<instanceId>` 访问。

**默认 props**（来自源码 `page-data-panel-models.js`）：
```js
{ dataSource: '', dataSourceEvent: 'onInit', children: [] }
```

---

## 三种数据来源模板

### 1. 走 pageService（最常用，运行时动态拉取）

models 数组：
```jsonc
{
  "modelType": "CmxDataSet",
  "instanceId": "itemsDs",
  "props": {
    "dataSource": "loadItemsService",
    "dataSourceEvent": "onInit"
  }
}
```

pageServices 里定义同名服务：
```jsonc
{ "name": "loadItemsService", "type": "rest", "url": "/api/doc/data/sqlx-dataset-json", "method": "POST" }
```

> 这种模式下，`initPageModels` 不自动调；通常在 pageFns 的 initPage 里手动触发，或由可视组件按 `dataSourceEvent` 时机调用。

### 2. 初始静态 rows（测试/演示）

```jsonc
{
  "modelType": "CmxDataSet",
  "instanceId": "staticDs",
  "props": {
    "rows": [
      { "id": "1", "name": "A", "qty": 3 },
      { "id": "2", "name": "B", "qty": 5 }
    ]
  }
}
```

> `initPageModels` 会在创建实例后 `ds.setRows(p.rows)` 自动填充。

### 3. 空（运行时由 pageFn 主动 addRow / setRows）

```jsonc
{
  "modelType": "CmxDataSet",
  "instanceId": "emptyDs",
  "props": {}
}
```

pageFn 里手动喂数据：
```js
host.emptyDs.setRows([{ id: '1', name: 'A' }])
host.emptyDs.addRow({ id: '2', name: 'B' })
```

---

## 树形子数据集（children）

父 DataSet 的 `props.children` 里声明子数据集：

```jsonc
{
  "modelType": "CmxDataSet",
  "instanceId": "masterDs",
  "props": {
    "dataSource": "loadHeaders",
    "children": [
      {
        "instanceId": "detailDs",
        "props": { "dataSource": "loadDetails", "dataSourceEvent": "onRowSelect" }
      }
    ]
  }
}
```

> 运行时父子关系：父行 addRow 时会同时给子 DataSet 创建占位行（`row._children: { detailDs: CmxDataSet }`）。

**何时用 children vs 何时升级到 CmxMasterSlave？**
- 单纯"装数据 + 树形" → CmxDataSet 的 children 够用
- 需要"选父行 → 自动刷子表 + 改值自动聚合到父" → **升级用 CmxMasterSlave**（见 `model-master-slave.md`）

---

## 事件清单（可写进 models[i].events）

| 事件名 | 何时触发 | event.detail |
| --- | --- | --- |
| `ds-row-added` | 新增一行 | `{ row }` |
| `ds-row-removed` | 删除一行 | `{ row }` |
| `cursor-changed` | 当前选中行变化 | `{ index, prevIndex, row, id }` |
| `row-changed` | 某行某字段变化 | `{ row, key, value }` |

事件脚本运行环境（见 SKILL.md §四-2）：
```js
function(event, host) {
  with (host) {
    // event.detail = { row, key, value }  // row-changed 为例
    // this = 当前 CmxDataSet 实例
    // 可访问 $data / host.<其它instanceId>
  }
}
```

**示例**：监听行变化并改页面变量
```jsonc
{
  "modelType": "CmxDataSet",
  "instanceId": "itemsDs",
  "props": { "dataSource": "loadItems" },
  "events": {
    "row-changed": "if (event.detail.key === 'qty') { $data.totalQty = ($data.items||[]).reduce(function(s,r){return s+(+r.qty||0)},0) }"
  }
}
```

---

## 绑定可视组件

### 声明式（推荐）

**纯 DataSet 模式（不走主从协调器，L0）**——只有 `data-cmx-dataset-id`，没有 `data-cmx-master-slave-id`：
```html
<cmx-revo-grid id="itemsGrid"
  data-cmx-dataset-id="itemsDs"
  data-cmx-model-id="itemsModel">
</cmx-revo-grid>
```

> `initPageModels` 扫到这个 grid → 调 `grid.setDataSet(host.itemsDs)`。

**主从模式（L1+）**——带 `data-cmx-master-slave-id`，dataset-id 写 schema 路径：
```html
<cmx-revo-grid
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head.items"
  data-cmx-kind="list"
  data-cmx-model-id="itemModel">
</cmx-revo-grid>
```

> 主从模式下，DataSet 由 MS 内部管理，**不要**在 DOM 上再绑 `data-cmx-dataset-id="itemsDs"`，统一走 MS 的 path 绑定。

### 命令式（pageFn 里手动绑）

```js
const grid = host.shadowRoot.querySelector('#itemsGrid')
grid.setDataSet(host.itemsDs)
grid.setColumnModel(host.itemsModel)
```

---

## 运行时 API 速查（pageFn 里可用）

```js
const ds = host.itemsDs

ds.addRow({ id: 'r1', qty: 3, price: 100 })   // 加一行
ds.removeRow('r1')                              // 删一行
ds.setCell('r1', 'qty', 5)                      // 改某字段
ds.setRows([{...}, {...}])                      // 批量设行
ds.addEventListener('ds-row-added', e => {})    // 监听
ds.rows                                         // 拿所有行（数组）
```

---

## 最小完整示例（L0：客户列表）

```jsonc
// __designer_meta__.models
[
  {
    "modelType": "CmxDataSet",
    "instanceId": "customerDs",
    "props": {
      "dataSource": "loadCustomers",
      "dataSourceEvent": "onInit"
    }
  },
  {
    "modelType": "CmxColumnModel",
    "instanceId": "customerModel",
    "props": {
      "datasetId": "customerDs",
      "columns": [
        { "id": "code", "caption": { "zh_CN": "客户编码" }, "dataType": "VARCHAR", "width": "140px" },
        { "id": "name", "caption": { "zh_CN": "客户名称" }, "dataType": "VARCHAR", "width": "200px" },
        { "id": "level", "caption": { "zh_CN": "等级" }, "dataType": "VARCHAR", "width": "100px" }
      ]
    }
  }
]
```

HTML 绑定：
```html
<cmx-revo-grid id="grid"
  data-cmx-dataset-id="customerDs"
  data-cmx-model-id="customerModel"
  style="height:100%;">
</cmx-revo-grid>
```

> 列字段详见 `model-column-model.md`；pageServices 写法详见 `page-assembly.md`。
