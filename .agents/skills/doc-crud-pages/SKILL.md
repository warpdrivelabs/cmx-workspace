---
name: doc-crud-pages
description: 指导开发 CMX 单据管理页面（列表 + 详情 + 新建三页一体的 CRUD）。当用户要求开发单据管理、订单录入、出入库单、凭证管理、报销单、采购单、销售单等业务单据的"列表查询/查看详情/新建录入"页面时必用。覆盖跨页跳转、列表过滤分页、详情四层主从、新建态预建根行、保存收拢编辑、铸号/idMap、字典引用列配置等完整链路。生成设计器页面（html-pages）时与 html-page-generator 配合——本技能负责三页一体的业务编排与跨页协作，html-page-generator 负责单页的 6 大模型配置细节。
---

# 单据管理页面开发指南（列表 + 详情 + 新建三页一体）

指导你为 CMX 平台开发**业务单据的 CRUD 三页**：单据列表（查询/分页/跳详情）+ 单据详情（查看态，多层数据）+ 单据新建（录入态，保存落库）。三页共享同一业务实体，通过跨页跳转协作。

> **与其他技能的分工**：
> - **本技能**：三页一体的业务编排（跨页传 id、列表查询、新建态初始化、保存链路、铸号/回显）。
> - **html-page-generator**：单页的 6 大模型配置细节（CmxMasterSlave/CmxColumnModel/`__designer_meta__` 结构）。生成每张页面前先读它的复杂度决策树和模型详解。
> - **menu-generator**：列表页挂载到门户菜单。
> - **cmx-components-guide**：组件 API 细节（cmx-revo-grid / cmx-ui5-form / cmx-dict-select / cmxInfo / cmxConfirm）。

---

## 一、何时用本技能（三页一体 vs 单页）

| 场景 | 用本技能（三页一体） | 用 html-page-generator（单页） |
| --- | --- | --- |
| 业务实体 | 需要列表浏览 + 详情查看 + 新建录入的完整管理 | 只展示/录入一张表 |
| 典型例子 | 订单管理、凭证管理、出入库单、报销单 | 员工信息卡、基础参数配置 |
| 页面数 | 2 张（列表页 + 详情页，详情页兼新建） | 1 张 |

**关键判断**：业务实体有"列表 + 详情/录入"两个视角 → 用本技能。详情页和新建页通常是**同一张页面**（详情页根据 URL 是否带 id 区分查看/新建态），所以实际产出的页面是 **列表页 + 详情页（含新建态）= 2 张**。

---

## 二、三页架构与跨页协作（核心心智模型）

```
┌─────────────┐   点"查看"(带 id)    ┌─────────────────────────────┐
│  列表页     │ ───────────────────▶ │  详情页（查看态：按 id 装载）│
│  (list)     │                      │                             │
│             │   点"新增"(不带 id)   │  详情页（新建态：空装载+预建)│
│  查询/分页  │ ───────────────────▶ │                             │
└─────────────┘                      │  保存 → 后端铸号 → idMap 回写│
                                     └─────────────────────────────┘
```

### 跨页传参机制（列表 → 详情）

列表页点"查看/新增"时，调用门户 `openNode` 打开详情页节点，通过 `initialContext` 传 id：

```js
// 列表页 pageFn: openDetail
var nodeSpec = {
  id: '<domain>-<app>-<doc>-detail' + (id ? ('-' + id) : '-new'),  // 节点 id（带 id 复用 tab）
  caption: '<单据名>详情',
  type: 'workspace-node',
  workspace: { content: { caption: '<单据名>详情', icon: 'table-view',
    views: [{ tabLabel: '详情', icon: 'table-view', type: 'html_pages',
      html_page: '<domain>.<app>.<module>.<detail-page-key>', view: 'content' }] } }
};
var extras = { initialContext: id ? { id: id } : {} };  // 有 id=查看，无 id=新建
document.querySelector('cmx-portal-app').openNode(nodeSpec, extras);
```

详情页 `initPage` 从工作区上下文读 id 区分态：

```js
var ws = host.workspace;
var id = (ws && ws.context && ws.context.get) ? (ws.context.get("id") || "") : "";
id = String(id || "").trim();
if (id) {
  // 查看态：按 id 装载
  ms.loadDoc({ ..., filter: "id:" + id });
} else {
  // 新建态：空装载 + 预建根行（见 §五）
  ms.loadDoc({ ..., filter: "id:-1" });
}
```

> **为什么用 `initialContext` 而非 URL query**：详情页是 workspace-node，id 经 context 传递最可靠；URL 的节点 id 主要用于 tab 复用（带同一 id 的二次点击会切到已打开的 tab）。

---

## 三、列表页配方

列表页三块结构：工具栏（新增/刷新）+ 查询条件区 + 列表区（表格 + 分页）。

### 3.1 模型组成（4 个）

| 模型 | instanceId | 职责 |
| --- | --- | --- |
| CmxDOCMeta | docMeta | 加载单据元数据（提供列定义 + 后端坐标） |
| CmxMasterSlave | ms | 协调器：loadKind=`list`，autoLoad，分页 |
| CmxColumnModel | batchModel（或 `<根层>`）| 列表表格列：**引用模式**（metaModelId+metaTable）+ 手写操作列合并 |
| CmxColumnModel | searchFormModel | 查询表单列：手写查询字段 |

### 3.2 列表表格的操作列（"查看"按钮，冻结右侧）

**纯模型配置**（不要手动注入 DOM）。列模型用手写 `_action` 列 + 元数据自动列合并：

```jsonc
// batchModel：引用模式（metaModelId）+ 手写操作列
{
  "modelType": "CmxColumnModel", "instanceId": "batchModel",
  "props": {
    "datasetId": "cv_batch",              // 根层 datasetId
    "metaModelId": "docMeta",             // 引用模式：元数据自动生成业务列
    "metaTable": "cv_batch",              // 元数据里的表名
    "columns": [                          // 手写列（与元数据列自动合并，追加到末尾）
      { "id": "_action", "caption": "操作", "width": "120px", "frozen": "right",
        "edit": { "mode": "readonly" },
        "display": { "mode": "actions", "actions": [
          { "text": "查看", "actionRef": "viewDetail", "icon": "display" }
        ]}}
    ]
  }
}
```

initPage 监听 `cmx-cell-link-click`，按 `actionRef` 分发。**注意 rowId 是 revo 行索引，要反查真实 id**：

```js
// initPage 里绑一次
var grid = host.gBatch;
if (grid && !grid.__linkWired) {
  grid.__linkWired = true;
  grid.addEventListener("cmx-cell-link-click", function (e) {
    var d = e.detail;
    if (d.actionRef !== "viewDetail") return;
    var rowIdx = parseInt(d.rowId, 10);        // revo 行索引（data-rgRow）
    var ds = grid._ds;
    var row = (ds && ds.rows && !isNaN(rowIdx)) ? ds.rows[rowIdx] : null;
    var realId = row ? row.id : null;          // 反查真实业务 id
    if (realId != null) host.openDetail(String(realId));
  });
}
```

### 3.3 查询：POST body 丰富查询（不是 GET filter 字符串）

列表查询用 `loadDoc` 的 `def.query.layers.<根层>.filter` 传丰富查询条件（`$contains`/`$gte`/`$lte`/`$or`/`$in`），**不要用** 简单的 `def.filter` 字符串（那只支持单列相等）：

```js
// pageFn: doSearch
var form = host.searchForm;
var d = form.getData() || {};
var filter = {};
var kw = (d.keyword || "").trim();
if (kw) filter.$or = [ { doc_no: { $contains: kw } }, { batch_name: { $contains: kw } } ];
if (d.batch_status) filter.batch_status = d.batch_status;
if (d.posting_from || d.posting_to) {
  var rng = {};
  if (d.posting_from) rng.$gte = d.posting_from;
  if (d.posting_to) rng.$lte = d.posting_to;
  filter.posting_date = rng;
}
var def = {
  domain: "...", application: "...", module: "...", doc: "...",
  dbId: "...", binary: true, apiPath: "/api/doc/data/sqlx-zmc-msgpack",
  depth: 1,
  query: { countTotal: true, layers: { cv_batch: { filter: filter } } }  // 丰富查询
};
if (ms._paging) ms._paging.page = 1;   // 查询时回到第 1 页
ms.loadDoc(def);
```

### 3.4 分页：cmx-pager 绑 ms

```html
<cmx-pager id="xPager" master-slave-id="ms" layer="cv_batch" page-sizes="10,20,50"></cmx-pager>
```

ms 模型 props 配 `paging: { layer: "cv_batch", pageSize: 10, page: 1, orderBy: ["!create_time"] }`。pager 与 ms 协作：翻页时 ms 自动带当前 query 重新装载（query 存在 `ms._def` 里，reload 时复用）。

### 3.5 重置查询：用 cmx-ui5-form.reset()

```js
// pageFn: resetSearch
var form = host.searchForm;
if (form && typeof form.reset === "function") form.reset();  // 组件库公共方法，清空所有字段
host.doSearch();
```

> 不要手写 DOM 遍历清空控件（`querySelectorAll` 各种 input 类型 + clear/value），脆弱且组件升级就漏。`cmx-ui5-form` 已提供 `reset()`。

---

## 四、详情页配方（查看态：四层主从）

详情页 = 表头表单（L1，只读概要）+ N 层可编辑表格（L2/L3/L4）。**查看态**用 initPage 传的 id 装载。

### 4.1 模型组成

| 模型 | 用途 |
| --- | --- |
| CmxDOCMeta (docMeta) | 元数据 |
| CmxMasterSlave (ms) | loadKind=`detail`，depth=50（深装载所有层），**无 autoLoad**（initPage 手动 loadDoc 带 filter） |
| CmxColumnModel (batchModel) | L1 表头表单列：**手写**（含字典列配置） |
| CmxColumnModel (headerModel/accModel/...) | L2+ 表格列：**引用模式**（metaModelId+metaTable，元数据自动生成） |

### 4.2 数据流 schema（relations 决定级联）

`dataFlow.relations` 定义父子层级，`childKey` 通常是 `upper_id`：

```jsonc
"dataFlow": {
  "schema": [
    { "id": "cv_batch", "kind": "list", "children": [
      { "id": "cv_header", "kind": "list", "children": [
        { "id": "cv_acc_line", "kind": "list", "children": [
          { "id": "cv_aux_line", "kind": "list", "children": [] }
        ]}
      ]}
    ]}
  ],
  "relations": [
    { "parent": "cv_batch", "child": "cv_header", "parentKey": "id", "childKey": "upper_id" },
    { "parent": "cv_header", "child": "cv_acc_line", "parentKey": "id", "childKey": "upper_id" },
    { "parent": "cv_acc_line", "child": "cv_aux_line", "parentKey": "id", "childKey": "upper_id" }
  ]
}
```

### 4.3 HTML 结构（flex 纵向，每层一个可固定高度的卡片）

详情页容器 `overflow: auto`；每层卡片用 `flex: 0 0 <高度>` 固定（如 `280px`/`300px`），让多层在视口内可滚动。表头层 `flex: 0 0 auto`（自适应高度）。

### 4.4 行选中联动（父表选行 → 子表过滤）

父表 grid 绑 `data-eventcmx-row-selected="onXxxSelected(event);"`，回调里刷新计数/触发弹性组合（如有）：

```js
// pageFn: onHeaderSelected
Promise.resolve().then(function(){ host.refreshCounts(); });
```

---

## 五、新建态配方（详情页的 id 为空分支）

完整配方（空装载+预建根行 / `ensureBatchRow` 合并用户输入 / `_ensureChildDs` 新增子行并继承父字段 / 删除子行二次确认）见 [references/new-mode-and-save.md](references/new-mode-and-save.md)。**要点**：新建态 = `filter:"id:-1"` 分支 + 预建根行（`ensureBatchRow`）+ 子行经 `_ensureChildDs` 注册子数据集后追加；删除子行需选中 + `cmxConfirm` 二次确认。

## 六、保存链路（最易出错的环节）

完整链路（保存前 `commitEdit` 收拢编辑中的单元格 / 后端铸号 `mint_ids_for_changeset` + `SaveResult.idMap` 回写临时 id / `doc_no` 单据号前端生成与后端铸号）见 [references/new-mode-and-save.md](references/new-mode-and-save.md)。**铁律**：不 commitEdit 就保存会丢最后一格编辑；idMap 不回写则新建后界面仍是临时 id。

## 七、字典引用列配置（极易配错）

完整配置（`refField` 存 id 还是 code 的字段名语义 / `displayField` / `dictCode` / `helpLayout` 仅真分级字典可用 classify / 字典回显）见 [references/dict-ref-columns.md](references/dict-ref-columns.md)。**速记**：`*_id` 存 id、`*_code` 存 code；回显靠 `displayField`，不要手拼名称列。


## 八、平台规范（pageFn 必须遵守）

### 8.1 用 cmxInfo/cmxConfirm，不要 alert/confirm

```js
// initPage 注入一次（从 globalThis.__cmxDataComp 取组件库导出）
var lib = globalThis.__cmxDataComp || {};
host._cmxNotify = function(kind, msg){        // kind: 'ok'/'warn'/'error'
  var fn = lib[kind === 'ok' ? 'cmxInfo' : (kind === 'warn' ? 'cmxWarn' : 'cmxError')];
  if (typeof fn === 'function') { try { fn(msg); } catch(_) {} }
};
host._libConfirm = function(message, title){  // 返回 Promise<boolean>
  if (lib && typeof lib.cmxConfirm === 'function') return lib.cmxConfirm({ message: message, title: title || '请确认' });
  return Promise.resolve(window.confirm(message));   // 兜底
};
```

### 8.2 initPage 绑定元素引用 + 事件

```js
var root = host.shadowRoot;
if (root) { root.querySelectorAll("[id]").forEach(function (el) {
  if (el.id && host[el.id] == null) host[el.id] = el;   // host.gBatch / host.batchForm / ...
}); }
```

### 8.3 行计数实时刷新

父表/子表行数变化（新增/删除/装载）后调 `refreshCounts` 更新标题旁的 `(N 条)`：

```js
// pageFn: refreshCounts
function countAt(path){
  try { var rows = host.ms._collectRows(host.ms._data, path); return (rows && rows.length) || 0; }
  catch(e){ return 0; }
}
var hl = root.querySelector('#xxx-count');
if (hl) hl.textContent = '(' + countAt('cv_batch.cv_header') + ' 条)';
```

---

## 九、生成流程（按顺序执行）

生成一个单据管理三页一体，按以下步骤：

1. **确认业务实体与层级**：根层 + 几层子表？每层哪些字段？哪些是字典引用列（走 cmx-dict-select）？
2. **确认元数据**：`cmxfico_doc_meta_v*.json` 里是否已有 `voucherTables` 定义？字段 edit/display 配置是否完整？**先修元数据再生成页面**（详情/列表的引用模式列来自元数据）。
3. **生成详情页**（含新建态）：读 html-page-generator 的 model-master-slave + page-assembly。按本技能 §四/§五/§六 配置模型与 pageFn。**重点**：initPage 区分查看/新建态、ensureBatchRow 预建根行、saveVoucher 用 commitEdit。
4. **生成列表页**：按本技能 §三 配置 4 个模型 + 查询/分页/操作列。
5. **挂菜单**：用 menu-generator 把列表页挂到门户菜单。
6. **注册页面索引**：详情页/列表页需在 html-pages 索引注册（设计器识别）。
7. **浏览器实测**：列表查询→分页→查看跳转→新建→填写→保存→二次保存（验证 idMap 不断链）。用 cmx-portal（通常 `http://localhost:5174`，admin/cmxadmin）。

---

## 十、参考文件索引（按需读取）

本技能聚焦三页一体业务编排。单页的模型配置细节、组件 API、字段属性全集，按需读这些：

| 需要什么 | 读哪个 |
| --- | --- |
| 新建态完整配方（ensureBatchRow/_ensureChildDs/删行确认） | 本技能 `references/new-mode-and-save.md` |
| 保存链路细节（commitEdit/铸号 idMap/doc_no） | 本技能 `references/new-mode-and-save.md` |
| 字典引用列完整配置（refField/displayField/dictCode/helpLayout/回显） | 本技能 `references/dict-ref-columns.md` |
| 单页 6 大模型配置（CmxMasterSlave/CmxColumnModel/...） | html-page-generator 的 references/model-*.md |
| 页面 HTML 结构与 DOM 绑定 | html-page-generator 的 references/page-assembly.md |
| 字段 edit.mode/display 全集（cmx-dict-select 配置项） | cmx-components-guide 的 references/field-edit-display-modes.md |
| cmx-revo-grid / cmx-ui5-form / cmx-dict-select 组件 API | cmx-components-guide |
| 菜单挂载 | menu-generator |
| dct/doc 后端接口 | html-page-generator 的 references/dct-doc-api.md |

---

## 十一、自检清单（提交前）

- [ ] 列表页操作列通过列模型配置（display.mode=actions），非手动 DOM 注入
- [ ] 列表查询用 def.query.layers POST body（丰富查询），非 def.filter 字符串
- [ ] 列表重置用 form.reset()，非 DOM 遍历
- [ ] 详情页 initPage 区分查看（filter=id:X）/新建（filter=id:-1 + ensureBatchRow）
- [ ] 新建态 loadDoc 后立即预建根行（ensureBatchRow）
- [ ] ensureBatchRow 合并 batchForm.getData() 用户输入
- [ ] 新增子行设 upper_id + 继承父字段 + _ensureChildDs 注册监听
- [ ] 删除子行有 _libConfirm 二次确认
- [ ] saveVoucher 前对所有可编辑 grid 调 commitEdit()
- [ ] 全程 cmxInfo/cmxConfirm（initPage 注入），无 alert/confirm
- [ ] 字典引用列：_id 字段 refField=id，_code 字段 refField=code，表头子表一致
- [ ] 字典引用列：editSettings 含 dictCode/idCol/valueField/labelCol/coord
- [ ] 仅真分级字典配 helpLayout=classify（平级字典用默认 grid）
- [ ] 详情/列表页 __designer_meta__ JSON 结构完整（python json.loads 校验）
