# 页面组装（HTML + __designer_meta__ + pageFns + DOM 绑定）

> 何时读：L1+ 组装完整 HTML 页面时（除 L0 纯展示外都建议读）。
> 真实样例：`backend/cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/erp-voucher-cnpc-ms.html`

---

## HTML 页面整体结构

一个 CMX 设计器页面 = **HTML 布局** + **`<script id="__designer_meta__">` JSON 块**。

```html
<!-- ① HTML 布局：可视组件 + UI5 标签 + style，组件带 DOM 绑定属性 -->
<div style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;">
  <cmx-revo-grid id="grid"
    data-cmx-master-slave-id="ms"
    data-cmx-dataset-id="head.items"
    data-cmx-kind="list"
    data-cmx-model-id="itemModel"
    style="height:200px;">
  </cmx-revo-grid>
  <!-- ...更多组件... -->
  <style>
    /* 可选：页面级样式 */
  </style>
</div>

<!-- ② __designer_meta__：JSON 块（核心） -->
<script type="application/json" id="__designer_meta__">
{
  "pageData": [],
  "pageFns": [],
  "pageServices": [],
  "pageDeps": [],
  "pageInterfaces": [],
  "dataSources": [],
  "dataFlow": { "schema": [], "aggregations": [], "relations": [] },
  "models": []
}
</script>
```

> 运行时：Portal 加载 HTML → 把 `__designer_meta__` 交给 `initPageModels(meta, host, root, $data)` → 编译 pageFns / pageServices → 按 modelType 实例化 → 扫 DOM 绑定 → 调 initPage。

---

## __designer_meta__ 七段速查

| 段 | 类型 | 作用 |
| --- | --- | --- |
| `pageData` | array | 页面变量（`$data.xxx`） |
| `pageFns` | array | 页面函数（`host.<fnName>`） |
| `pageServices` | array | 页面服务调用（REST 等，`host.<svcName>`） |
| `pageDeps` | array | import 声明 |
| `pageInterfaces` | array | 钩子：`initPage` / `onActivate` / `isDirty` / `getState` / `validate` |
| `dataSources` | array | 数据源 |
| `dataFlow` | object | 兼容旧位置：`schema` / `aggregations` / **`relations`**（relations 仍用） |
| `models` | array | **6 大模型实例数组**（本技能核心产物） |

---

## pageFns 写法

每个 pageFn 是一个对象，`body` 是**字符串形式的函数体**：

```jsonc
{
  "name": "loadVoucher",
  "params": "",
  "body": "var ms = host.ms;\nhost.ms.setFlatData({head:[...], items:[...]}, {relations:[...]});",
  "readsVars": [],
  "writesVars": []
}
```

运行时包装为 `function(params) { with(host){ ...body... } }`，挂到 `host.<name>`。

### 关键模式：取模型类 + waitForLib

pageFn 里要用 `CmxColumn` / `CmxColumnModel` 等类时，从 `globalThis.__cmxDataComp` 取（设计期注入）：

```js
var lib = globalThis.__cmxDataComp || host.__cmxClasses;

// 等待 cmx-data-comp 就绪（异步场景必备）
function waitForLib() {
  return new Promise(function(res, rej) {
    var n = 0, t = setInterval(function() {
      var L = globalThis.__cmxDataComp;
      if (L && L.CmxColumn && L.CmxColumnModel && L.CmxDataSet) {
        clearInterval(t); res(L); return;
      }
      if (++n > 120) { clearInterval(t); rej(new Error('cmx-data-comp 未就绪')); }
    }, 50);
  });
}
```

### 转义：只用共享 escHtml，禁止内联自定义变体

pageFn 里拼接 HTML（含 `<option value="...">` 等**属性插值**）必须转义。运行环境 `globalThis.__cmxDataComp.escHtml` 即可（最严格五字符集合 `& < > " '`，文本/属性上下文皆安全）：

```js
var esc = (globalThis.__cmxDataComp || {}).escHtml;
```

**禁止**在 body 里内联 `function esc(s){...}` 自制变体——历史存量里弱变体（只转 `&<>` 不转引号）被用在属性插值处，值含 `"` 时破坏 DOM（2026-09-01 审查 A-02 同款缺陷）。共享库不可用时的兜底也必须五字符全转。

### 多 pageFn 共享 helper：挂 host，不逐 body 复制

同页多个 pageFn 需要同一组 helper（$ / setText / waitForLib / 数据装载等）时，**不要在每个 body 里整段复制**——由首个执行的 pageFn 把闭包挂到 host，其余 body 幂等取用：

```js
var H = host.__myPageHelpers || (host.__myPageHelpers = (function(){
  function $(id){ return host.shadowRoot.querySelector('#'+id); }
  // ...其余 helper；需页面运行时全局的类走懒解析：globalThis.__cmxDataComp || host.__cmxClasses
  return { $: $ /* , ... */ };
})());
var $ = H.$;
```

反面教材：`dict-grid-meta.html` 曾在 4 个 pageFn body 里各带一整套相同样板（每份 ~3.3KB），2026-09-01 已收敛为 `host.__dictHelpers` 单实例。

### 典型 pageFn：用 DOC 元数据动态构造列

```js
// pageFns[0].body 节选（来自真实凭证）
waitForLib().then(function(L) {
  // 1. 拉取 DOC 元数据（通过 pageService）
  return Promise.all([
    host.loadDocMeta({ refs: [{ domain:'fi', application:'cmxfico', module:'gl', kind:'DOC', id:'cmxfico' }] }),
    host.loadFactVoucher()
  ]);
}).then(function(rr) {
  var batch = rr[0], fact = rr[1];
  var docJson = (batch && batch.items && batch.items[0] && batch.items[0].doc) || null;

  // 2. 用 DOC voucherTable.fields 构造 CmxColumn[]
  var CmxColumn = lib.CmxColumn;
  function buildColumns(table) {
    var fields = (table && table.fields) || [];
    return fields.map(function(f) {
      return new CmxColumn({
        id: f.id,
        caption: (f.caption != null ? f.caption : f.id),
        dataType: (f.dataType || 'VARCHAR'),
        width: '130px'
      });
    });
  }

  // 3. 灌进对应 CmxColumnModel
  var cm = host.itemModel;
  var cols = buildColumns(docJson.voucherTables[1]);  // 分录层
  if (typeof cm.setMembers === 'function') cm.setMembers(cols);

  // 4. 装载数据
  host.ms.setFlatData({ head:[...], items:[...] });
});
```

### 给 host 挂载自定义函数

pageFn 里可以给 host 挂额外函数，供 pageInterface 或其它 pageFn 调用：

```js
host.showBatch = function() {
  var vsel = host.shadowRoot.querySelector('#voucherSel');
  var idx = vsel ? (+vsel.value || 0) : 0;
  var b = (host.__batches || [])[idx];
  host.ms.setFlatData({ batch:[b.batch], headers:b.headers, /* ... */ });
};
```

---

## pageServices 写法

```jsonc
{
  "name": "loadDocMeta",
  "type": "rest",
  "url": "/api/definitions/batch",
  "method": "POST",
  "rpcMethod": "",
  "gqlOperationName": "",
  "gqlQuery": "",
  "headers": "",
  "bodyTemplate": "",
  "responseTo": "",
  "responseTransform": ""
}
```

运行时 `host.<name>(params, _opts)` 触发请求，返回 Promise。`AbortSignal` 通过 `_opts.signal` 自动传入。

常用类型：
- `rest`：标准 REST 调用（`url` + `method`）
- GraphQL：`gqlOperationName` + `gqlQuery`

**示例**：
```jsonc
{ "name": "loadCustomers", "type": "rest", "url": "/api/dct/data/search", "method": "GET" }
{ "name": "resolveFC", "type": "rest", "url": "/api/flexible-combination/resolve", "method": "GET" }
```

---

## pageInterfaces（页面钩子）

```jsonc
"pageInterfaces": [
  { "name": "initPage",   "enabled": true, "body": "if (host.loadVoucher) host.loadVoucher();" },
  { "name": "onActivate", "enabled": true, "body": "if (!host.__loaded && host.loadVoucher) host.loadVoucher();" },
  { "name": "isDirty",    "enabled": true, "body": "return false;" },
  { "name": "getState",   "enabled": true, "body": "return { app: 'cmxfico' };" },
  { "name": "validate",   "enabled": true, "body": "return { valid: true };" }
]
```

| 钩子 | 何时触发 |
| --- | --- |
| `initPage` | 模型实例化 + DOM 绑定之后（首次加载） |
| `onActivate` | 页面被激活（如切 Tab 回来） |
| `isDirty` | 询问是否有未保存改动 |
| `getState` | 获取页面状态 |
| `validate` | 保存前校验 |

**L1+ 页面务必配 `initPage`** 触发数据装载。

---

## dataFlow（兼容字段，relations 仍用）

```jsonc
"dataFlow": {
  "schema": [],           // 旧位置；新代码 schema 写在 models[i].props
  "aggregations": [],     // 旧位置；新代码写在 models[i].props
  "relations": [          // ★ 仍用！setFlatData 时 initPageModels 从这里读
    { "parent": "head", "child": "items", "parentKey": "id", "childKey": "headId" }
  ]
}
```

> 即使 schema/aggregations 写在 models 里，**relations 仍要写到 dataFlow.relations**（initPageModels 兜底读取）。

---

## DOM 绑定完整速查

### 主从协调器绑定（L1+ 最常用）

```html
<!-- 表单（single → bindForm） -->
<cmx-ui5-form id="headForm"
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head"
  data-cmx-kind="single"
  data-cmx-model-id="headModel">
</cmx-ui5-form>

<!-- 表格（list → bindTable） -->
<cmx-revo-grid id="itemsGrid"
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head.items"
  data-cmx-kind="list"
  data-cmx-model-id="itemModel"
  style="height:200px;">
</cmx-revo-grid>
```

四属性齐全时 `initPageModels` 自动绑定。`data-cmx-kind` 缺省：`cmx-ui5-form` 默认 `single`，其它默认 `list`。

### 纯 DataSet 绑定（L0）

```html
<cmx-revo-grid id="grid"
  data-cmx-dataset-id="itemsDs"
  data-cmx-model-id="itemsModel">
</cmx-revo-grid>
```

只有 `data-cmx-dataset-id`（无 `master-slave-id`）→ 调 `grid.setDataSet(host.itemsDs)`。

### 属性对照表

| 属性 | 含义 | 取值 |
| --- | --- | --- |
| `data-cmx-master-slave-id` | MS 的 instanceId | `ms` / `voucherMS` |
| `data-cmx-dataset-id` | L0：DataSet instanceId；L1+：schema 完整路径 | `itemsDs` / `head.items` |
| `data-cmx-kind` | 视图类型 | `single`（表单）/ `list`（表格） |
| `data-cmx-model-id` | CmxColumnModel 的 instanceId | `itemModel` |

---

## setFlatData + relations 装载模式（真实凭证用法）

```js
// pageFn 里
host.ms.setFlatData({
  head:  [{ id:'h1', voucherNo:'V001', totalDebit:0, totalCredit:0 }],
  items: [
    { id:'i1', headId:'h1', acctCode:'1001', debit:50000, credit:0 },
    { id:'i2', headId:'h1', acctCode:'1122', debit:0, credit:50000 }
  ],
  details: [
    { id:'d1', itemId:'i1', amount:50000, remark:'5月预付' }
  ]
})
// relations 从 dataFlow.relations 读取，MS 自动建 head→items→details 树 + 各 grid 联动
```

> `setFlatData` 内部已自动定位各根首行并自上而下级联（`_primeCursors`），无需调用方手动 moveFirst。

---

## 后端 API 速查（6 大模型各自调哪个）

| 模型组件 | 主要调用 | 用途 |
| --- | --- | --- |
| **CmxDataSet** | `/api/doc/data/sqlx-dataset-json` 或 `/api/dct/data/search` | 装业务数据 |
| **CmxColumnModel** | 不调 API | 纯前端，列定义来自 props |
| **CmxMasterSlave** | 间接（通过 DataSet setData） | — |
| **CmxDCTMeta** | `loadById` → `/api/definitions/config?kind=DCT&id=...&domain=...&application=...&module=...` + base 字段集 | 加载字典定义 |
| **CmxDOCMeta** | `loadById` → `/api/definitions/config?kind=DOC&id=...&domain=...&application=...&module=...` + base 字段集 | 加载单据定义 |
| **FlexibleCombination** | `loadByAnchor` → `/api/flexible-combination/resolve?domain&app&module&scenario&<anchor>` | 按锚点取规则 |

### 批量加载定义（推荐）

```jsonc
// pageService
{ "name": "loadDocMeta", "type": "rest", "url": "/api/definitions/batch", "method": "POST" }
```

pageFn 调用：
```js
host.loadDocMeta({ refs: [
  { domain:'fi', application:'cmxfico', module:'gl', kind:'DOC', id:'cmxfico' }
] }).then(function(batch) {
  var docJson = batch.items[0].doc;
  // 用 docJson 构造列...
})
```

### 通用响应信封

```jsonc
// 成功
{ "code": 0, "ok": true,  "data": { ... } }
// 业务失败
{ "code": 422, "ok": false, "msg": "校验未通过" }
```

> 前端 `apiFetch` 自动拆 `data`，业务代码看到的总是 `data` 内部形状。

### 身份头

| Header | 含义 |
| --- | --- |
| `Authorization: Bearer <jwt>` | 鉴权 |
| `x-cmx-db-id: default` | 数据源（多库切换） |
| `x-cmx-trace-id: ...` | 链路追踪（缺省自动生成） |

---

## 完整页面组装清单（生成时核对）

- [ ] HTML 布局里每个可视组件都带正确的 DOM 绑定属性（四属性齐全）
- [ ] `__designer_meta__` 七段齐全（用不到的段留空数组）
- [ ] `models` 数组里每个实例 modelType + instanceId + props 齐全
- [ ] L1+ 页面把 relations 写到 `dataFlow.relations`
- [ ] L1+ 页面配 `initPage` interface 触发数据装载
- [ ] pageFns 的 body 是字符串，符合 `with(host){...}` 语义
- [ ] 用到模型类时从 `globalThis.__cmxDataComp` 取 + waitForLib
- [ ] pageServices 的 name 与 pageFns 里调用名一致
- [ ] instanceId 在 models / DOM / pageFns 引用中完全一致
- [ ] DOC/DCT 用 `application`；FC 用 `app`

---

## 调试技巧（pageFns 里）

```js
// 打印所有模型实例
console.log('host keys:', Object.keys(host).filter(k => !k.startsWith('_')))

// 检查 MS 内部状态
console.log('MS schemaById:', [...host.ms._schemaById.keys()])
console.log('MS bindings:', host.ms._bindings)

// 监听所有事件
host.ms.addEventListener('change', e => console.log('MS change:', e.detail))
host.ms.addEventListener('aggregate', e => console.log('MS aggregate:', e.detail))

// 在光标处加 debugger（设计器事件 Tab 有"插入 debugger"按钮）
debugger;
```
