# dicttree-ws 四区联动与字典加载逻辑

> 范围：`fi-gl-dicttree-ws` 菜单节点（"总账科目维护·自分级"）的页面装配、跨页交互协议、字典加载现状。
>
> 目的：把这套页面的联动机制写清楚，作为后续"完善字典加载"（元数据驱动列 + 引用字典下拉 + DCT 版本升级）的事实依据和回归基线。
>
> 涉及文件：`cmx-container/data/html-pages/sources/fi/cmxfico/gl/dicttree-{model,explorer,content,prop-detail}.html`

---

## 目录

- [一、菜单与页面装配](#一菜单与页面装配)
  - [1.1 workspace-node 节点结构](#11-workspace-node-节点结构)
  - [1.2 四区视图清单](#12-四区视图清单)
  - [1.3 三处同步登记](#13-三处同步登记)
- [二、页面间交互协议（三层叠加，无传统消息总线）](#二页面间交互协议三层叠加无传统消息总线)
  - [2.1 协议总览](#21-协议总览)
  - [2.2 第一层：workspace.pageview 直接方法调用](#22-第一层workspacepageview-直接方法调用)
  - [2.3 第二层：workspace.context KV 总线](#23-第二层workspacecontext-kv-总线)
  - [2.4 第三层：window CustomEvent 广播](#24-第三层window-customevent-广播)
  - [2.5 onModelReady 三重回退解决加载竞态](#25-onmodelready-三重回退解决加载竞态)
- [三、完整联动链路](#三完整联动链路)
  - [3.1 选中树节点的链路](#31-选中树节点的链路)
  - [3.2 表格选行的链路](#32-表格选行的链路)
  - [3.3 新增 / 删除 / 保存链路](#33-新增--删除--保存链路)
- [四、字典加载现状（核心问题区）](#四字典加载现状核心问题区)
  - [4.1 元数据层（meta）—— 硬编码，未接通](#41-元数据层meta--硬编码未接通)
  - [4.2 数据层（data）—— 完整接通 /api/dct/*](#42-数据层data--完整接通-apidct)
  - [4.3 对照 glacct-* 标准模板](#43-对照-glacct--标准模板)
- [五、模型实例与数据流](#五模型实例与数据流)
  - [5.1 model 页的 4 个模型实例](#51-model-页的-4-个模型实例)
  - [5.2 ChangeSetCollector 增删改跟踪](#52-changesetcollector-增删改跟踪)
  - [5.3 视图层（grid/tree/form）的DataSet 绑定](#53-视图层gridtreeform的dataset-绑定)
- [六、关键文件索引](#六关键文件索引)
- [七、当前缺陷清单（为完善字典加载做准备）](#七当前缺陷清单为完善字典加载做准备)

---

## 一、菜单与页面装配

### 1.1 workspace-node 节点结构

`fi-gl-dicttree-ws` 在 `cmx-container/data/menu-pages/fi/cmxfico/gl/explorer-menu.json` 第 1566–1620 行登记为 `type: "workspace-node"`：

```jsonc
{
  "id": "fi-gl-dicttree-ws",
  "name": "dicttree-ws",
  "caption": "总账科目维护(自分级)",
  "icon": "tree",
  "type": "workspace-node",
  "workspace": {
    "id": "dicttree_ws",
    "explorerWidth": 280,
    "propertyWidth": 320,
    "model":    { "type": "html_pages", "id": "dicttree-model",       "html_page": "fi.cmxfico.gl.dicttree-model" },
    "explorer": { "caption": "科目树",   "icon": "tree",
                  "views": [{ "type":"html_pages", "id":"dicttree-explorer",    "tabLabel":"科目树",     "html_page":"fi.cmxfico.gl.dicttree-explorer" }] },
    "content":  { "caption": "子科目",   "icon": "table-view",
                  "views": [{ "type":"html_pages", "id":"dicttree-content",     "tabLabel":"子科目表格", "html_page":"fi.cmxfico.gl.dicttree-content" }] },
    "property": { "caption": "详情",     "icon": "detail-view",
                  "views": [{ "type":"html_pages", "id":"dicttree-prop-detail", "tabLabel":"详情",       "html_page":"fi.cmxfico.gl.dicttree-prop-detail" }] }
  }
}
```

> 用户给的 JSON 片段是去除了 `type/caption/icon/width` 的简化版，上面是源文件里的完整节点。

Portal 运行时由 `Workspace` 类（`../cmx-portal-manager`）托管，每个 view 挂到一个区域（region）。

### 1.2 四区视图清单

| 区域 | viewId | html_page | 角色 | 可视组件 |
|---|---|---|---|---|
| `explorer`（左 280px） | `dicttree-explorer` | `fi.cmxfico.gl.dicttree-explorer` | 科目树（左面板） | `<cmx-web-treeview>` |
| `content`（中） | `dicttree-content` | `fi.cmxfico.gl.dicttree-content` | 子科目表格 | `<cmx-revo-grid>` |
| `property`（右 320px） | `dicttree-prop-detail` | `fi.cmxfico.gl.dicttree-prop-detail` | 科目详情表单 | `<cmx-ui5-form>` |
| `model`（隐藏） | `dicttree-model` | `fi.cmxfico.gl.dicttree-model` | 共享数据大脑 | 无（纯逻辑） |

**架构关键**：四页中**只有 model 页持有数据与协调器**，其余三页 `pageData/models/dataSources` 全空，是"瘦视图"。这是同模块 `glacct-*` 的同款模式——隐藏页当数据中心。

### 1.3 三处同步登记

按 menu-generator 规范，菜单节点需在三处保持一致：

| 文件 | 位置 | dicttree 条目 |
|---|---|---|
| menu-pages JSON | `cmx-container/data/menu-pages/fi/cmxfico/gl/explorer-menu.json` | 第 1566–1620 行 |
| init_menu.sql | `cmx-container/docs/sql/init/init_menu.sql` | 第 44 行（单行 INSERT，code=`fi-gl-dicttree-ws`） |
| 迁移 SQL | `cmx-container/docs/sql/migrations/20260716_001_menu_pages_to_cmx_menu.up.sql` | 第 41 行 |

修改菜单结构时三处必须同步，否则文件与数据库脱节。

---

## 二、页面间交互协议（三层叠加，无传统消息总线）

### 2.1 协议总览

CMX 跨页交互**不用** `postMessage` / `BroadcastChannel` / `EventBus`。dicttree-* 叠用三种原生机制，每一层职责不同：

| 层 | 通道 | 语义 | 典型场景 |
|---|---|---|---|
| ① 直接方法调用 | `host.workspace.pageview['dicttree-model']` | 同步、命令式 | 调 `m.loadChildren()`、`m.setGridFilter()`、`m.saveChanges()` |
| ② KV 总线 | `host.workspace.context.set/get/on('change')` | 异步、广播 | `currentDictRow` 变更通知详情区 |
| ③ window 事件 | `window.dispatchEvent('cmx-dicttree-model', {detail:{kind}})` | 同窗口、分类广播 | `meta` / `data` / `gridfilter` 三类状态广播 |

### 2.2 第一层：workspace.pageview 直接方法调用

每个页面（包括 model 页自己）都通过这把 Proxy 拿到 model 页 CE 实例：

```js
// 4 个页面 initPage / pageFns 里反复出现的标准片段
function modelHost(){
  try {
    return host.workspace
        && host.workspace.pageview
        && host.workspace.pageview['dicttree-model']
        || null;
  } catch(e){ return null; }
}
```

model 页的 `getPageApi()` 把协调器、列模型、CRUD 方法冻结成对外 API（`dicttree-model.html` body 末尾）：

```js
return {
  // 模型实例（视图层据此 setColumnModel / setDataSet）
  dictMS, colGrid, colTree, colDetail,
  // 数据查询
  getRows,                       // () => Row[]，返回整树当前所有行
  gridView,                      // () => CmxDataSetView|null，按当前 gridParent 过滤的视图
  // 视图过滤
  setGridFilter,                 // (id) => void，切换 content 表格的父级
  setSelected,                   // (id) => void，整树行 is_selected 标记
  // 树懒加载
  loadChildren,                  // (rowData, opts) => Promise<Row[]>
  isChildrenLoaded,              // (rowData) => boolean
  reloadRoot, reload,            // () => Promise<Row[]>
  // CRUD
  newRow,                        // (parentId) => Row，本地铸临时 id
  saveRow,                       // (obj) => Promise，单行 upsert + 重载下级
  saveChanges,                   // () => Promise，批量 changeset 保存
  deleteRow,                     // (id) => Promise
  // 辅助
  collector,                     // () => ChangeSetCollector
  isReady,                       // () => boolean，数据是否就绪
  isMetaReady                    // () => boolean，列模型是否就绪
};
```

视图层都是**直接调这些方法**，不走事件。例如 explorer 点击树节点时调 `m.loadChildren(rd, {refresh:false})`、`m.setGridFilter(id)`。

### 2.3 第二层：workspace.context KV 总线

`ContextHost`（`../cmx-portal-manager`）：

```js
class ContextHost {
  constructor() { this._m = new Map(); this._changeHandlers = new Set() }
  get(key) { return this._m.get(String(key)) }
  set(key, value) {
    const k = String(key);
    const oldValue = this._m.get(k);
    if (oldValue === value) return;          // ← 同值不通知
    this._m.set(k, value);
    this._emitChange(k, value, oldValue);
  }
  on(evt, handler) { if (evt === 'change') this._changeHandlers.add(handler) }
  // ... delete / off / snapshot
}
```

**关键约束**：只有 `ctx.set/delete` 触发 change；裸赋值（`ctx.foo = 1`）不通知。

dicttree-* 共用的键只有一个：

| 键 | 写入方 | 读取方 | 用途 |
|---|---|---|---|
| `currentDictRow` | explorer（树点节点）、content（表格选行）、explorer/content（新增空行） | prop-detail | 驱动右侧详情表单 `moveToId` |

prop-detail 的订阅（`dicttree-prop-detail.html` initPage）：

```js
var c = ctx();
if (c && !host.__ctxWired) {
  host.__ctxWired = true;
  c.on('change', function(e){
    if (e.key === 'currentDictRow' && e.value != null) {
      moveDs(e.value);       // ds.moveToId(id)，详情表单移到该行
      setTimeout(showCur, 30);
    }
  });
}
```

> **坑位**：`ContextHost` 同值不通知。若要强制触发（如"再次点同一个节点"场景），需用 `Date.now()` 脏值技巧——dicttree-* 目前不依赖此场景。

### 2.4 第三层：window CustomEvent 广播

model 页定义了两个广播函数（`dicttree-model.html` initPage）：

```js
function fireModelReady(kind) {
  window.dispatchEvent(new CustomEvent('cmx-dicttree-model', { detail: { kind: kind } }));
}
function fireModelEvent(kind, extra) {
  var d = { kind: kind };
  for (var k in (extra || {})) d[k] = extra[k];
  window.dispatchEvent(new CustomEvent('cmx-dicttree-model', { detail: d }));
}
```

广播三类事件：

| kind | 触发位置 | 含义 | 订阅方 |
|---|---|---|---|
| `meta` | initPage 末尾，列模型 `setMembers` 完成后（`host.__metaReady=true`） | "列模型可用了" | 各页 `onModelReady('meta', cb)` |
| `data` | `applyData()` / `reloadRoot()` 完成后 | "数据装载完毕" | 各页 `onModelReady('data')` + `onModelEvent('data')` |
| `gridfilter` | `setGridFilter(id)` 内 | "grid 父级切了" | content 重绑 `gridView` |

订阅侧封装：

```js
function onModelEvent(kind, cb) {
  window.addEventListener('cmx-dicttree-model', function(ev){
    if (ev && ev.detail && ev.detail.kind === kind) cb(modelHost(), ev.detail);
  });
}
```

### 2.5 onModelReady 三重回退解决加载竞态

四页加载顺序不保证（model 页可能晚于视图页就绪），`onModelReady(kind, cb)` 用三重回退兜底：

```js
function onModelReady(kind, cb) {
  function hit(m) {
    if (!m) return false;
    return kind === 'meta' ? m.__metaReady : m.__ready;
  }
  // ① 已经就绪，立即回调
  var m = modelHost();
  if (hit(m)) { cb(m); return; }
  // ② 监听 window 事件，命中后注销
  function h() {
    var mm = modelHost();
    if (hit(mm)) {
      window.removeEventListener('cmx-dicttree-model', h);
      cb(mm);
    }
  }
  window.addEventListener('cmx-dicttree-model', h);
  // ③ 80ms 轮询 12 秒兜底（150 × 80ms = 12000ms）
  var n = 0, t = setInterval(function(){
    var mm = modelHost();
    if (hit(mm)) {
      clearInterval(t);
      window.removeEventListener('cmx-dicttree-model', h);
      cb(mm);
    }
    if (++n > 150) clearInterval(t);
  }, 80);
}
```

**含义**：无论 model 页先就绪还是后就绪，视图页都能拿到回调。这是 dicttree-* 联动可靠性的关键。

---

## 三、完整联动链路

### 3.1 选中树节点的链路

```
用户点树节点"1001 库存现金"
   │
   ▼ tree.addEventListener('node-clicked', ...)
explorer.selectNode(id, node):
   │
   ├─ m.setSelected(id)              → model 页整树该行 is_selected=1（ds.rows.forEach）
   │
   ├─ m.setGridFilter(id)            → model 页：
   │                                     host.__gridParent = id
   │                                     master.fillView(__gridView, parentPred(id))
   │                                     fireModelEvent('gridfilter')  ──┐
   │                                                                    │
   ├─ m.loadChildren(rd, {refresh:false})                              │
   │     ├─ 已加载过 / is_leaf → resolve([])                           │
   │     └─ 未加载：POST /api/dct/data/tokio-zmc-msgpack                │
   │                body: { parentId: id, page: 1, pageSize: 300 }     │
   │                → upsertRows(...) → applyData(...)                 │
   │                → fireModelEvent('data', {parent: id})  ──┐        │
   │                                                          │        │
   └─ ctx.set('currentDictRow', id)                           │        │
       → context 广播 'change'                                │        │
                                                             │        │
   ╔═══════════════════════════════════════════════════════ │ ═══════╪ ═══╗
   ║ content 订阅：                                          │        │   ║
   ║   onModelEvent('gridfilter', mm => {                    │        │   ║
   ║     grid.setDataSet(mm.gridView())  ←───────────────────┼────────┼───╜
   ║     setText('gridInfo', '直接下级:' + v.rows.length)     │        │
   ║     setText('nodeTitle', mm.__selectedNode.title)       │        │
   ║   })                                                    │        │
   ║   onModelEvent('data', mm => {                          │        │
   ║     grid.setDataSet(mm.gridView())  ←───────────────────┼────────┘
   ║   })                                                    │
   ║                                                         │
   ║ prop-detail 订阅：                                      │
   ║   ctx.on('change', e => {                               │
   ║     if (e.key === 'currentDictRow') {                   │
   ║       ds.moveToId(e.value)                              │
   ║       df.setDataSet(ds, {currentRowId: id})             │
   ║       setTimeout(showCur, 30)                           │
   ║     }                                                   │
   ║   })                                                    │
   ╚═══════════════════════════════════════════════════════════
```

### 3.2 表格选行的链路

```
用户在 content 表格点击某行
   │
   ▼ grid.addEventListener('cmx-row-selected', ev => ...)
content:
   ├─ ds2.moveToId(ev.detail.id)       → model 页整树 currentRow 移到该行
   │                                      （model 页的 dictMS 是同一份）
   └─ ctx.set('currentDictRow', id)    → 广播给 prop-detail
                                          prop-detail.on('change') → moveDs + setDataSet
```

> 注意：content 表格选行**不触发 `gridfilter` 事件**，也不重新 setGridFilter——只是把 currentRow 移过去，让详情区跟随。grid 内容不变。

### 3.3 新增 / 删除 / 保存链路

#### 新增子科目（content 的 doAddChild）

```
doAddChild():
   ├─ m.newRow(pid)                    → 本地铸临时 id 't{n}'，构造空行
   │                                     parent_id=pid, full_path=parent.full_path+'.'+id
   ├─ ds.addRow(nr)                    → 加到 model 页 dictMS 根 DataSet
   └─ ctx.set('currentDictRow', nr.id) → 详情区跟随到新空行
```

#### 新增根科目（explorer 的 doAddRoot）

同 doAddChild，但 `parentId=null`，`full_path=String(id)`，`level_no=1`。

#### 删除（content 的 doDel）

```
doDel():
   ├─ commitGridEdits(cb)              → 提交 revo-grid 当前编辑态（blur activeElement）
   └─ cb:
       ├─ ds.currentRow                → 拿当前行
       ├─ confirm('确定删除 ' + code + ' ?')
       └─ m.deleteRow(id):
           ├─ id 不匹配 /^[0-9]+$/（临时 t 开头）→ 本地移除，resolve({temp:true})
           └─ 数字 id → DELETE /api/dct/entries/{id}?...&dict=gl_account
                         → 从 host.__rows 过滤
                         → applyData(...) + fireModelEvent('data')
```

#### 保存（content 的 doSave）

```
doSave():
   ├─ commitGridEdits(cb)
   └─ cb:
       └─ m.saveChanges():
           ├─ ensureCollector()        → ChangeSetCollector.attach() 到 dictMS
           ├─ cs = cleanChanges(collector.export())
           │     过滤 UI 列：is_selected / children_loading / displayValue / hasChildren
           ├─ if (!Object.keys(cs).length) → resolve({noop:true})
           ├─ POST /api/dct/save?...&dict=gl_account
           │   body: { saveMode:'merge', changes: cs }
           ├─ 409 → e.conflict=true，提示"数据已被他人修改，请刷新"
           ├─ 422 → e.violations，控制台/状态栏展示校验错误
           └─ 成功 → collector.reset() → host.reload() → fireModelReady('data')
```

---

## 四、字典加载现状（核心问题区）

dicttree-model.html 把字典加载**拆成两半**：元数据层硬编码（没接通），数据层完整接通 `/api/dct/*`。

### 4.1 元数据层（meta）—— 硬编码，未接通

`dicttree-model.html` initPage：

```js
var GRID_COLS = [
  { id: "code",          caption: "科目编码", dataType: "VARCHAR", width: "140px" },
  { id: "name",          caption: "科目名称", dataType: "VARCHAR", width: "200px" },
  { id: "account_type",  caption: "账户类型", dataType: "VARCHAR", width: "110px" },  // ← 应是 refDict=account_type
  { id: "balance_dir",   caption: "余额方向", dataType: "VARCHAR", width: "100px" },  // ← 应是枚举 借/贷
  { id: "is_leaf",       caption: "末级",     dataType: "INT",    width: "70px"  },  // ← hierarchyFieldSet 系统列
  { id: "status",        caption: "状态",     dataType: "INT",    width: "70px"  }   // ← systemFieldSet + 枚举
];
var DETAIL_COLS = [
  { id:"code",         caption:"科目编码",       dataType:"VARCHAR" },
  { id:"name",         caption:"科目名称",       dataType:"VARCHAR" },
  { id:"parent_id",    caption:"上级科目ID",     dataType:"VARCHAR" },
  { id:"account_type", caption:"账户类型",       dataType:"VARCHAR" },
  { id:"balance_dir",  caption:"余额方向",       dataType:"VARCHAR" },
  { id:"is_leaf",      caption:"是否末级",       dataType:"INT" },
  { id:"sort_no",      caption:"排序号",         dataType:"INT" },
  { id:"status",       caption:"状态(1启用0停用)", dataType:"INT" }
];

// 直接用 setMembers 装到 colGrid/colDetail
host.colGrid.setMembers(GRID_COLS.map(mkCol));
host.colDetail.setMembers(DETAIL_COLS.map(mkCol));
host.colTree.setMembers([ /* code/name 两列 */ ]);

host.__metaReady = true;
fireModelReady('meta');
```

**问题**：

1. **字段清单与后端 DCT 元数据脱钩**——后端 `cmxfico_dct_meta_v3.json` 里 `gl_account` 字典有 `coa_id`（科目表）、`acct_group_code`（科目组）、`account_type_code`、`pl_bs_flag`、`open_item_mgmt`、`account_currency_code`、`post_period` 等引用字典字段，前端完全不感知。
2. **引用字典字段没有 ref_dict**——`account_type`、`coa_id` 等列在表格/表单里只能裸输文本，没有 `<cmx-dict-select>` 下拉。
3. **系统列是手抄的**——`is_leaf`/`full_path`/`level_no` 属 `hierarchyFieldSet`，`status`/`sort_no` 属 `systemFieldSet`，本应由元数据合并而来。
4. **DCT 坐标写死 v1**——`file=cmxfico_dct_meta_v1.json` 是旧版本，后端最新定义在 `cmxfico_dct_meta_v3.json`（`isDefault:true`），v1 缺很多字段。

### 4.2 数据层（data）—— 完整接通 /api/dct/*

`dicttree-model.html`：

```js
var DCT_BASE  = '/api/dct';
var DCT_COORD = 'domain=fi&application=cmxfico&module=gl&file=cmxfico_dct_meta_v1.json';
var DB        = 'fico-db';

function dctHdr() {
  return { 'Content-Type': 'application/json', 'db_id': DB };
}

// 二进制 msgpack 主通道，JSON search 兜底
function dctSearch(dict, body) {
  var url = DCT_BASE + '/data/tokio-zmc-msgpack?' + DCT_COORD + '&dict=' + dict;
  var hdr = dctHdr(); hdr['Accept'] = 'application/x-msgpack';
  return fetch(url, { method:'POST', headers:hdr, body:JSON.stringify(body||{}) })
    .then(function(r){
      var ct = r.headers.get('content-type') || '';
      if (ct.indexOf('msgpack') >= 0) {
        return r.arrayBuffer().then(function(buf){
          var dec = __lib().decodeMsgpack;
          var m = dec ? dec(new Uint8Array(buf)) : null;
          var pkg = (m && m.data !== undefined) ? m.data : m;
          return { rows: pkgToRows(pkg), total: (pkg && pkg.rows && pkg.rows.length) || 0 };
        });
      }
      return r.json().then(...);
    })
    .catch(function(e){
      // 二进制/解码失败兜底走 JSON search
      return fetch(DCT_BASE + '/data/search?' + DCT_COORD + '&dict=' + dict, ...)
        .then(r => r.json()).then(...);
    });
}
```

数据层端点完整覆盖后端 `cmx-dct-api`（`crates/libs/cmx-dct/cmx-dct-api/src/handlers.rs`）：

| 前端调用 | 后端端点 | 用途 |
|---|---|---|
| `dctSearch(dict, body)` | `POST /api/dct/data/tokio-zmc-msgpack` | 分页查（msgpack 二进制） |
| （兜底） | `POST /api/dct/data/search` | 同查（JSON） |
| `dctUpsert(dict, arr)` | `POST /api/dct/entries` | 单行 upsert（merge） |
| `dctDelete(dict, id)` | `DELETE /api/dct/entries/{id}` | 删除 |
| `dctSaveChanges(dict, cs)` | `POST /api/dct/save` | 批量 changeset，`saveMode:'merge'` |

特点：
- **msgpack 二进制主通道**（性能优），失败自动降级 JSON search。
- **`db_id: fico-db` header**——字典数据建在业务库，前端显式指定。
- **409 冲突 / 422 校验**——`saveChanges` 捕获后抛 `e.conflict` / `e.violations`，由调用方（content 的 doSave）用 `presentDocError` 展示。
- **懒加载**——树点开父节点才拉直接下级（pageSize 300）。
- **ChangeSetCollector**——`__attachCollector()` 跟踪 dictMS 的增删改，`cleanChanges` 过滤 UI 列后批量回存。

### 4.3 对照 glacct-* 标准模板

同模块的 `glacct-*`（"总账科目维护"生产模板）是元数据驱动，两套对比：

| 能力 | glacct-model（生产模板） | dicttree-model（当前页） | 差距 |
|---|---|---|---|
| 元数据来源 | `POST /api/definitions/batch` 拉 DCT（refs `kind:DCT, id:gl_account`） | 硬编码 GRID_COLS/DETAIL_COLS | ❌ 没接通 |
| base fieldSet 合并 | `mergedDictFields` 合 own + baseFieldSet + hierarchyFieldSet + auditFieldSet | 无 | ❌ |
| 列模型派生 | `buildCols(meta)` 从 meta 出列 | `mkCol(c)` 一层包装 | ❌ |
| ref_dict 字段 | 字段带 `refDict`/`refField`/`displayField`，自动驱动 `<cmx-dict-select>` | 全 VARCHAR 文本输入 | ❌ |
| DCT 版本 | 走默认 `isDefault`（v3） | 写死 v1 | ⚠️ |
| 数据接口 | `/api/dict/cf_gl_account/search`（旧 JSON） | `/api/dct/data/tokio-zmc-msgpack`（新二进制） | dicttree 反而更先进 |
| 树懒加载 | ✅ | ✅ | — |
| ChangeSetCollector | ✅ | ✅ | — |

**结论**：dicttree-* 的**数据通道比 glacct 更先进**（msgpack + `/api/dct/*`），但**元数据通道缺失**（glacct 是元数据驱动，dicttree 是硬编码列）。这是"完善字典加载"的核心缺口。

---

## 五、模型实例与数据流

### 5.1 model 页的 4 个模型实例

`dicttree-model.html` 的 `__designer_meta__.models`：

```jsonc
[
  {
    "modelType": "CmxMasterSlave",
    "instanceId": "dictMS",
    "props": {
      "schema": [ { "id": "dict" } ],     // 单层 schema，只有一个根 dataset "dict"
      "relations": [],
      "aggregations": []
    }
  },
  {
    "modelType": "CmxColumnModel",
    "instanceId": "colGrid",               // content 表格用
    "props": { "datasetId": "dict", "columns": [] }
  },
  {
    "modelType": "CmxColumnModel",
    "instanceId": "colTree",               // explorer 树用
    "props": { "datasetId": "dict", "toTitleCols": "code,name", "columns": [] }
  },
  {
    "modelType": "CmxColumnModel",
    "instanceId": "colDetail",             // property 表单用
    "props": { "datasetId": "dict", "columns": [] }
  }
]
```

**注意**：`columns` 在配置里都是空数组，真正的列定义在 initPage 里用 `setMembers(GRID_COLS.map(mkCol))` 动态填充——这就是硬编码的根源。

**为什么 schema 只有一层 `dict`？** 因为自分级字典（`selfHierarchy:true`）整棵树都在一张物理表（`cf_gl_account`），靠 `parent_id` 自关联，不需要主从两层 schema。父子关系靠 `full_path`/`level_no` 在 normalizeRow 里计算。

### 5.2 ChangeSetCollector 增删改跟踪

`dicttree-model.html`：

```js
host.__collector = null;
host.__attachCollector = function() { return ensureCollector(); };

function ensureCollector() {
  var lib2 = globalThis.__cmxDataComp || host.__cmxClasses || {};
  if (!host.__collector && lib2.ChangeSetCollector && host.dictMS) {
    try { host.__collector = new lib2.ChangeSetCollector(host.dictMS); } catch(e){}
  }
  if (host.__collector) {
    try { host.__collector.attach(); } catch(e){}
  }
}

// 保存前过滤 UI 列
function cleanChanges(cs) {
  var UI = { is_selected:1, children_loading:1, displayValue:1, hasChildren:1 };
  var out = {};
  for (var path in cs) {
    var bkt = cs[path] || {};
    var nb = {};
    if (bkt.updated) {
      var up = bkt.updated
        .filter(function(u){
          var f = u.fields || {};
          return Object.keys(f).filter(function(k){ return !UI[k]; }).length > 0;
        })
        .map(function(u){
          var f = {};
          for (var k in u.fields) { if (!UI[k]) f[k] = u.fields[k]; }
          return { id: u.id, fields: f, baseline: u.baseline };
        });
      if (up.length) nb.updated = up;
    }
    if (bkt.inserted && bkt.inserted.length) nb.inserted = bkt.inserted;
    if (bkt.deleted && bkt.deleted.length) nb.deleted = bkt.deleted;
    if (Object.keys(nb).length) out[path] = nb;
  }
  return out;
}
```

**触发时机**：content 页 initPage 末尾——`onModelReady('data', m => m.__attachCollector())` + `onModelEvent('data', m => m.__attachCollector())`，保证每次数据重载后 collector 重新 attach。

### 5.3 视图层（grid/tree/form）的 DataSet 绑定

**三页都不在 `__designer_meta__.models` 里声明模型**，而是拿到 model 页的 `colXxx` / `dictMS` 后**手动调 setColumnModel + setDataSet**：

| 视图 | 绑定代码（initPage 里） |
|---|---|
| explorer 的 `<cmx-web-treeview>` | `tree.setColumnModel(m.colTree); tree.setDataSet(ds)` —— ds 是 `m.dictMS.getRootDataSet('dict')` |
| content 的 `<cmx-revo-grid>` | `grid.setColumnModel(m.colGrid); grid.setDataSet(m.gridView())` —— 注意是 `gridView()` 返回的过滤视图，不是根 ds |
| prop-detail 的 `<cmx-ui5-form>` | `df.setColumnModel(m.colDetail); df.setDataSet(ds, {currentRowId})` |

> 这违反了 html-page-generator skill 推荐的 `data-cmx-master-slave-id` / `data-cmx-dataset-id` / `data-cmx-model-id` 声明式绑定，但因为 model 页和视图页是不同 CE 实例（跨 ShadowRoot），声明式绑定扫描不到跨 host 的模型，所以这里用**命令式 setXxx**是合理的。

---

## 六、关键文件索引

### 6.1 dicttree-ws 自身（4 个页面 + 3 处菜单登记）

| 文件 | 角色 |
|---|---|
| `cmx-container/data/html-pages/sources/fi/cmxfico/gl/dicttree-model.html` | 隐藏数据大脑，CmxMasterSlave + 3 个 CmxColumnModel + DCT 数据接口 |
| `cmx-container/data/html-pages/sources/fi/cmxfico/gl/dicttree-explorer.html` | 科目树（左），`<cmx-web-treeview>`，doAddRoot / doRefresh |
| `cmx-container/data/html-pages/sources/fi/cmxfico/gl/dicttree-content.html` | 子科目表格（中），`<cmx-revo-grid>`，doAddChild / doDel / doSave |
| `cmx-container/data/html-pages/sources/fi/cmxfico/gl/dicttree-prop-detail.html` | 详情表单（右），`<cmx-ui5-form>`，订阅 currentDictRow |
| `cmx-container/data/menu-pages/fi/cmxfico/gl/explorer-menu.json` | 菜单 JSON（dicttree 节点在 1566–1620 行） |
| `cmx-container/docs/sql/init/init_menu.sql` | init 种子（第 44 行 INSERT） |
| `cmx-container/docs/sql/migrations/20260716_001_menu_pages_to_cmx_menu.up.sql` | 迁移 SQL（第 41 行） |

### 6.2 相关运行时与组件

| 文件 | 角色 |
|---|---|
| `../cmx-portal-manager` | `Workspace` / `ContextHost` / `pageview` Proxy / `registerView` |
| `../cmx-portal-manager` | html_pages 视图渲染、CE 注册 |
| `packages/cmx-data-comp/src/lib/cmx-master-slave.js` | `CmxMasterSlave`（页内协调器，非跨页） |
| `packages/cmx-data-comp/src/lib/cmx-dct-meta.js` | `CmxDCTMeta` 模型（dicttree 未用，但是完善方向） |
| `packages/cmx-data-comp/src/lib/cmx-meta-model.js` | `CmxBaseMeta` / `loadMetaBatch` |
| `packages/cmx-data-comp/src/lib/cmx-doc-source.js` | `ChangeSetCollector`（dicttree-model 用的就是这里导出的） |
| `packages/cmx-data-comp/src/lib/init-page-models.js` | `initPageModels`——`__designer_meta__.models` 的执行入口 |

### 6.3 后端

| 文件 | 角色 |
|---|---|
| `cmx-container/crates/libs/cmx-dct/cmx-dct-api/src/lib.rs` | `DctModule` 路由聚合 |
| `cmx-container/crates/libs/cmx-dct/cmx-dct-api/src/handlers.rs` | HTTP handler（薄层） |
| `cmx-container/crates/libs/cmx-dct/cmx-dct-model/src/lib.rs` | `DctQuery` / `DictView` / `DictColumn`（DB-free） |
| `cmx-container/crates/libs/cmx-dct/cmx-dct-store-pg/src/lib.rs` | PG 持久化 + `resolve_dict` |
| `cmx-container/crates/libs/cmx-model-center/src/lib.rs` | `compile_dct` → `cf_*` DDL |
| `cmx-container/data/meta/definitions/fi/cmxfico/gl/cmxfico_dct_meta_v3.json` | gl_account 字典定义（isDefault，最新版） |
| `cmx-container/data/meta/definitions/fi/cmxfico/gl/cmxfico_dct_meta_v1.json` | v1 旧版（dicttree 当前用的） |

### 6.4 对照模板

| 文件 | 角色 |
|---|---|
| `cmx-container/data/html-pages/sources/fi/cmxfico/gl/glacct-model.html` | glacct-* 元数据驱动列的生产模板（buildCols / mergedDictFields） |
| `CMXPortalManager+CMXHTMLDesigner-模型体系文档/04-字典模型-CmxDCTMeta.md` | DCT 字段权威文档（522 行） |
| `.agents/skills/html-page-generator/SKILL.md` | 设计器业务页面生成技能 |

---

## 七、当前缺陷清单（为完善字典加载做准备）

按影响优先级排序：

| # | 缺陷 | 位置 | 影响 |
|---|---|---|---|
| 1 | 列定义硬编码，不接 DCT 元数据 | `dicttree-model.html` initPage 的 `GRID_COLS` / `DETAIL_COLS` | 后端加字段前端不感知；无法启用引用字典下拉 |
| 2 | 引用字典字段没有 `ref_dict` | 同上 | `account_type` / `coa_id` 等字段在表格/表单里裸输文本，无下拉 |
| 3 | 系统列手抄，不走 fieldSet 合并 | 同上 | `is_leaf` / `status` / `sort_no` / `parent_id` 维护重复，容易漂移 |
| 4 | DCT 坐标写死 v1 | `DCT_COORD` 常量 | 后端最新定义在 v3，前端用的字段集不全 |
| 5 | 系统列编辑器不正确 | 硬编码 | `is_leaf` 应是 checkbox，`status` 应是 switch，`balance_dir` 应是枚举单选 |
| 6 | 视图层命令式绑定 | 4 页 initPage | 跨页 ShadowRoot 限制下是合理的，但偏离 skill 推荐的声明式绑定 |

**完善方向**（推荐方案 A）：

- **范围**：只改 `dicttree-model.html` 一个文件，explorer/content/prop-detail 不动（它们通过 `colGrid`/`colDetail` 间接消费，model 改完自动生效）。
- **改动**：
  1. DCT 坐标升级（去 `file=...v1`，让后端 `resolve_dict_file` 走 `isDefault` → v3）。
  2. 新增 `loadDictMeta()`：`GET /api/dct/meta?domain=fi&application=cmxfico&module=gl&dict=gl_account` 拿元数据。
  3. `buildCols(meta, scope)` 派生：保留 GRID_COLS/DETAIL_COLS 作白名单+顺序+宽度，按 id 与 meta.columns 交集合并富信息（refDict / edit / dataType / caption）。
  4. `mkCol(c)` 升级：透传 `refDict`/`refField`/`displayField`/`edit`/`editSettings` 给 `CmxColumn`，让 `<cmx-dict-select>` 自动接管引用字典列。
  5. `loadDictMeta()` 完成后再 `fireModelReady('meta')`，保留 `onModelReady('meta')` 协议不变。
  6. 兜底：`/api/dct/meta` 失败回退当前硬编码 GRID_COLS，保证页面不崩。

---

**附：联动时序一图流**

```
用户操作              explorer              content              prop-detail         model 页（隐藏）
─────────────────────────────────────────────────────────────────────────────────────────────────────
initPage              等 modelReady         等 modelReady         等 modelReady        reloadRoot()
                       ↓                    ↓                     ↓                   fetch /api/dct/.../msgpack
                                                                                      upsertRows → applyData
                                                                                      __ready=true
                                                                                      fireModelReady('data')
                      tree.setDataSet       grid.setDataSet       form.setDataSet
                        (ds)                  (gridView)            (ds, currentRowId)

点树节点 1001         selectNode(id):
                       m.setSelected(id)
                       m.setGridFilter(id) ──────────────────── fireModelEvent('gridfilter') ──────→ grid.setDataSet(gridView)
                       m.loadChildren(rd) ── fetch /api/dct ── fireModelEvent('data') ─────────────→ grid.setDataSet(gridView)
                       ctx.set('currentDictRow', id) ───────────────────────────────────────────→ ds.moveToId + form 渲染

表格选行                                     cmx-row-selected:
                                              ds.moveToId(id)
                                              ctx.set('currentDictRow', id) ─────────────────→ ds.moveToId + form 渲染

新增子科目            doAddRoot:            doAddChild:
                       m.newRow(null)        m.newRow(pid)
                       ds.addRow(nr)
                       ctx.set('currentDictRow', nr.id) ──────────────────────────────────────→ form 跟到新空行

保存                                          doSave:
                                              m.saveChanges()
                                              POST /api/dct/save
                                              ↓ 成功
                                              collector.reset()
                                              m.reload() ──────── fireModelReady('data') ───→ 三页重绑 DataSet
                                              ↓ 失败
                                              presentDocError(e)
```

---

**文档版本**：2026-07-21 · 基于 `cmx-rpt-flow` 分支当前 `dicttree-*.html` 源码与 `glacct-*` 对照分析。
