# JS 模块页深度指南（native-page 重点形态）

> 何时读：生成 JS 模块形态的 native-page（生产级、可复用 cmx 组件/助手）。
> 最佳真实范例：`cmx-container/assets/model/web/ui-native/portal/doc/doc-loader.js`（445 行，元数据驱动）

---

## 一、导出契约（4 种形态）

源码识别逻辑：`workspace-native-pages.js`

```js
// 形态 1（推荐）：对象 + views 映射
export default {
  defaultView: 'content',
  views: {
    async content(ctx) { /* ... */ return htmlString }
  }
}

// 形态 2：默认导出函数（等价 views.default）
export default async function render(ctx) { /* ... */ return htmlString }

// 形态 3：命名导出 nativePage
export const nativePage = { defaultView: 'content', views: { async content(ctx) {...} } }

// 形态 4：命名导出 page
export const page = { defaultView: 'content', views: { async content(ctx) {...} } }
```

**识别优先级**：
1. `mod.render` 是函数 → 包装为 `{ defaultView:'default', views:{ default: mod.render } }`
2. 否则取 `mod.default || mod.nativePage || mod.page` 作为页面定义对象

> 推荐形态 1：最清晰，支持多 view（一个 native 页可提供多个视图，菜单节点配 `view` 属性切换）。

### views 多视图模式

```js
export default {
  defaultView: 'list',
  views: {
    async list(ctx) { return 列表HTML },
    async detail(ctx) { return 详情HTML }
  }
}
```

菜单节点配置 `view: 'detail'` 则进入 detail 视图。

---

## 二、ctx 对象详解

```js
{
  pageId: 'portal.doc.doc-loader',   // native-page id（来自 index.json）
  view: 'content',                    // 当前 view 名（来自菜单节点 view 属性）
  region: 'content',                  // 工作区区域（content/explorer/property/bottom/floatview）
  props: { ... },                     // ★ 来自菜单节点 props 属性（parseJsonAttr）
  native: { ... },                    // 菜单节点的 native 属性
  host: <cmx-native-pages-host CE>    // 宿主元素实例
}
```

### ctx.props（关键，来自菜单注入）

native 页的"参数"全靠菜单节点的 `props` 注入。典型 props（见 `doc-loader.js` 的 `readDef`）：

```js
props = {
  domain: 'fi',           // 业务域
  application: 'cmxfico', // 应用
  module: 'gl',           // 模块
  file: 'cmxfico_doc_meta_v1.json',  // 单据/字典定义文件
  dbId: 'fico-db',        // 可选：数据源
  apiPath: '/api/doc/data/sqlx-dataset-json',  // 可选：自定义装载端点
  binary: false,          // 可选：是否走二进制通道
  limit: 50               // 可选：根层限制
}
```

> props 内容自由定义，由菜单节点配置。这是与 `menu-generator` 的核心衔接点。

### ctx.host（宿主 CE）

- `ctx.host.renderRoot` —— 指向 shadowRoot（渲染目标），等同 `ctx.host.shadowRoot`
- `ctx.host.workspace` —— 当前工作区 scope 对象（跨区域联动用）
- `ctx.host` 上还有 `getAttribute('native-page'/'view'/'region'/'props'/'native')` 等宿主属性

---

## 三、取 cmx 类与助手（铁律）

### 禁止 import，用 globalThis

```js
// ❌ Blob import 解析不了裸模块名
import { CmxMasterSlave } from 'cmx-data-comp'

// ✅ 从全局取（Portal 在 import-ui5-and-app.js 预挂）
const cmx = () => (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}
const C = cmx()
```

### 可用 API 清单（cmx-data-comp 导出，源码 `packages/cmx-data-comp/src/index.js`）

**模型类（程序化实例化，不经 __designer_meta__）**：
- `C.CmxMasterSlave` —— 主从协调器
- `C.CmxDataSet` —— 数据集（含 `C.CmxDataSet.fromJSON(pkg)` 反序列化列式包）
- `C.CmxColumnModel` / `C.CmxColumn` / `C.CmxColumnGroup` —— 列模型
- `C.CmxDCTMeta` / `C.CmxDOCMeta` —— 字典/单据元数据模型（程序化 loadById）

**DOC 数据助手（重点，简化后端调用）**：
- `C.loadDocData(metaOrCoord, opts)` —— 装载单据数据
- `C.saveDocData(...)` / `C.saveDocDataBatch(...)` —— 回存
- `C.ChangeSetCollector` —— 变更收集器（`new C.ChangeSetCollector(ms).attach()`）
- `C.loadChildren(...)` —— 懒下钻
- `C.formatViolations` / `C.extractViolations` —— 校验诊断格式化
- `C.presentDocError(err, opts)` / `C.describeDocError(err)` —— 校验失败对话框

**DOC 元数据助手（动态构造 schema/columns）**：
- `C.buildMasterSlaveSchema(meta)` —— 由 doc/meta 构造 CmxMasterSlave schema
- `C.layerPaths(schema)` —— 计算各层 path
- `C.buildColumnModel(C, path, columns)` —— 由层列构造 CmxColumnModel
- `C.orderColumns` / `C.defaultWidth` / `C.SYSTEM_COLS`

**查询构造助手**：
- `C.OPERATORS` / `C.opsForType` / `C.coerceValue`
- `C.buildLayerFilter` / `C.buildOrderBy` / `C.buildDocQuery` / `C.encodeCursor`

**字典助手**：
- `C.CmxDictCache` / `C.collectRefDicts` / `C.makeDictResolver`
- `C.createDictDataSource` / `C.createLocalDictDataSource`

**消息/对话框**：
- `C.showCmxMessage` / `C.cmxInfo` / `C.cmxWarn` / `C.cmxError` —— **替代 alert()**
- `C.CmxFloatingDialog` —— 业务对话框

**坐标归一化**：
- `C.normalizeDocCoord` / `C.docCoordQuery` / `C.docCoordKey` / `C.resolveCoord`

**二进制/流**：
- `C.decodeMsgpack` —— msgpack 反序列化
- `C.loadDocDataStream` / `C.FrameStreamParser` —— 流式装载

> UI5 标签（`ui5-button` / `ui5-bar` / `ui5-icon` 等）已由 Portal `cmx-ui5-runtime` boot 完成，可直接在返回的 HTML 字符串里用。

---

## 四、DOM 操作规范

### 渲染目标：ctx.host.renderRoot

```js
const root = ctx.host.renderRoot   // 等同 ctx.host.shadowRoot
root.querySelector('#grid')
```

### 异步等待渲染（whenRendered 模式）

render 返回 HTML 字符串后，宿主才把它注入 shadowRoot。**同步立即 querySelector 会查不到**。用 `whenRendered` 等待（来自 `doc-loader.js`）：

```js
function whenRendered(host, selector, cb, tries) {
  const t = tries == null ? 60 : tries
  const root = host && host.renderRoot
  if (root && root.querySelector(selector)) { cb(root); return }
  if (t <= 0) return
  requestAnimationFrame(() => whenRendered(host, selector, cb, t - 1))
}

// 在 render 里：
if (host) whenRendered(host, '.my-root', (root) => bindPage(root, data))
return htmlString
```

> `requestAnimationFrame` 轮询 60 次（约 1 秒）兜底；也可用 `MutationObserver` 更精准。

### 跨区域联动（workspace.context）

native 页可跨工作区区域联动（explorer 选行 → content 刷新）：

```js
// 写：选了某行
ctx.host.workspace.context.set('selectedItem', item)

// 读（在另一个区域的 native 页里）
ctx.host.workspace.context.get('selectedItem')
```

> 真实范例见 `demo/product-explorer.html`（虽然那是 HTML 片段，但 workspace.context 机制 JS 模块页同样可用）。

---

## 五、后端 API 调用

native 页直接 `fetch`（UI5 已 boot，cmx 助手从 globalThis 取）。常用接口：

### 字典数据
```js
const q = new URLSearchParams({ domain, application, module, dict })
const res = await fetch('/api/dct/data/search?' + q, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  credentials: 'same-origin', body: JSON.stringify({ page: 1, pageSize: 50 })
})
```

### 单据数据（推荐用 cmx 助手封装）
```js
const C = cmx()
const data = await C.loadDocData(
  { domain, application, module, file },
  { apiPath: '/api/doc/data/sqlx-dataset-json', dbId: 'fico-db' }
)
```

### 单据元数据（动态构造 schema）
```js
const res = await fetch(`/api/doc/meta?domain=${domain}&application=${app}&module=${m}&file=${file}`)
const body = await res.json()
const meta = body.code != null ? body.data : body   // 兼容信封
const schema = C.buildMasterSlaveSchema(meta)
```

> 完整 DCT/DOC 接口参数见 `../../html-page-generator/references/dct-doc-api.md`（两技能共享的接口知识）。

### 响应信封兼容

手写 fetch 时要自己拆信封（Portal 的 `apiFetch` 才自动拆）：
```js
const body = await res.json()
const pkg = (body && typeof body.code === 'number') ? body.data : body
```

### 身份头
- `credentials: 'same-origin'` —— 带 cookie/jwt
- `db_id: 'fico-db'` —— 多库切换（DCT/DOC 数据接口）

---

## 六、状态管理（模块级 state）

native JS 页是 ES 模块，**模块级变量天然是单例状态**。但同一 native 页可能被多区域复用，**state 必须在 content(ctx) 入口重置**（见 `doc-loader.js`）：

```js
const state = { def: null, meta: null, ms: null, grids: {} }

export default {
  defaultView: 'content',
  views: {
    async content(ctx) {
      // ★ 每次进入重置，避免跨实例污染
      state.def = null
      state.meta = null
      state.ms = null
      state.grids = {}
      // ...继续渲染
    }
  }
}
```

---

## 七、完整模板：元数据驱动多 grid 页（仿 doc-loader.js）

**场景**：通用单据加载页——层数 N、列、主从关系全来自 `/api/doc/meta`，传入任意单据坐标即可加载。

```js
/**
 * universal-doc-loader —— 通用单据加载页（元数据驱动，native_pages）。
 * DAM（domain/application/module）由框架注入 workspace.context（见 SKILL §2.1），
 *   用 ctx.host.workspace.context.get('domain') 读取，不要写进菜单 props。
 * props = { file, dbId?, apiPath?, limit? }  （业务参数）
 */
const cmx = () => (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}

const state = { def: null, meta: null, ms: null, paths: [], grids: {} }

function whenRendered(host, selector, cb, tries) {
  const t = tries == null ? 60 : tries
  const root = host && host.renderRoot
  if (root && root.querySelector(selector)) { cb(root); return }
  if (t <= 0) return
  requestAnimationFrame(() => whenRendered(host, selector, cb, t - 1))
}

function readDef(ctx) {
  const p = (ctx && ctx.props) || {}
  // DAM 优先从 workspace.context 读（框架 openNode 注入），fallback props（向后兼容）
  const wctx = ctx && ctx.host && ctx.host.workspace && ctx.host.workspace.context
  const get = (k) => (wctx && typeof wctx.get === 'function' ? wctx.get(k) : undefined)
  const def = {
    domain: get('domain') || p.domain, application: get('application') || p.application,
    module: get('module') || p.module, file: p.file,
    dbId: p.dbId || p.db_id || '', apiPath: p.apiPath || '/api/doc/data/sqlx-dataset-json',
    limit: p.limit,
  }
  return (def.domain && def.application && def.module && def.file) ? def : null
}

async function loadMeta(def) {
  const q = new URLSearchParams({ domain: def.domain, application: def.application, module: def.module, file: def.file })
  const res = await fetch('/api/doc/meta?' + q.toString(), { credentials: 'same-origin' })
  const body = await res.json()
  return body.code != null ? body.data : body
}

async function loadData(def, meta) {
  const C = cmx()
  if (C && C.loadDocData) {
    return C.loadDocData(def, { apiPath: def.apiPath, dbId: def.dbId, limit: def.limit })
  }
  // 兜底：手写 fetch
  const q = new URLSearchParams(def)
  const res = await fetch(def.apiPath + '?' + q.toString(), {
    headers: { db_id: def.dbId }, credentials: 'same-origin'
  })
  const body = await res.json()
  return body.code != null ? body.data : body
}

function bindPage(root, meta, data) {
  const C = cmx()
  if (!C.CmxMasterSlave || !C.buildMasterSlaveSchema) return

  state.meta = meta
  state.ms = new C.CmxMasterSlave({
    schema: C.buildMasterSlaveSchema(meta),
    aggregations: [],
    relations: (meta.relations || []).map(r => ({ parent: r.parent, child: r.child, parentKey: r.parentKey, childKey: r.childKey }))
  })
  state.paths = C.layerPaths(state.ms.schema)

  // 为每层建 grid + columnModel
  state.paths.forEach((path, i) => {
    const grid = root.querySelector('#grid-' + i)
    if (!grid) return
    state.ms.bindTable(path, grid)
    const layer = meta.layers.find(l => l.id === path.split('.').pop()) || meta.layers[i]
    grid.setColumnModel(C.buildColumnModel(C, path, layer.columns))
    state.grids[path] = grid
  })

  // 装载数据
  if (data && C.CmxDataSet && data.datasetId != null) {
    const rootDs = C.CmxDataSet.fromJSON(data)
    const rootLayer = meta.layers[0]
    state.ms.setDataSet({ [rootLayer.id]: rootDs })
  }
}

export default {
  defaultView: 'content',
  views: {
    async content(ctx) {
      state.def = null; state.meta = null; state.ms = null; state.paths = []; state.grids = {}
      const def = readDef(ctx)
      if (!def) {
        return `<div style="padding:12px;color:#b00;">缺少坐标：workspace.context 或 props 需提供 { domain, application, module }，props 需提供 { file }</div>`
      }
      state.def = def

      const host = ctx && ctx.host
      try {
        const [meta, data] = await Promise.all([loadMeta(def), loadData(def, null).catch(() => null)])
        const layerCount = (meta.layers || []).length
        const grids = Array.from({ length: layerCount }, (_, i) =>
          `<section class="lvlbox" key="${i}" style="flex:1 1 auto;min-height:120px;">
             <div class="lvl-head"><ui5-title level="H6">${(meta.layers[i]||{}).levelName || ('L' + (i+1))}</ui5-title></div>
             <cmx-revo-grid id="grid-${i}" style="display:block;width:100%;height:100%;"></cmx-revo-grid>
           </section>`
        ).join('')

        if (host) whenRendered(host, '.udl-root', (root) => bindPage(root, meta, data))

        return `
          <div class="udl-root" style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;background:var(--sapBackgroundColor,#f7f7f7);color:var(--sapTextColor,#1d2d3e);">
            <ui5-bar design="Header">
              <ui5-label slot="startContent" style="font-weight:800;">业务单据 · ${def.module}/${def.file}</ui5-label>
            </ui5-bar>
            ${grids}
          </div>
        `
      } catch (err) {
        return `<div style="padding:12px;color:#b00;">加载失败：${err.message}</div>`
      }
    }
  }
}
```

> 这是"一份页面覆盖全部单据"的范式。完整生产版见 `doc-loader.js`（含查询条件、分页、懒下钻、msgpack 二进制、校验错误展示）。

---

## 八、完整模板：列表管理页（仿 notify/center.js）

**场景**：通知中心型——列表 + 筛选 + 操作按钮。更简单的范式。

```js
const cmx = () => (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}

function whenRendered(host, selector, cb, tries) {
  const t = tries == null ? 60 : tries
  const root = host && host.renderRoot
  if (root && root.querySelector(selector)) { cb(root); return }
  if (t <= 0) return
  requestAnimationFrame(() => whenRendered(host, selector, cb, t - 1))
}

export default {
  defaultView: 'content',
  views: {
    async content(ctx) {
      const props = (ctx && ctx.props) || {}
      const host = ctx && ctx.host

      const res = await fetch('/api/notifications?pageSize=50', { credentials: 'same-origin' })
      const body = await res.json()
      const pkg = body.code != null ? body.data : body
      const rows = (pkg && pkg.items) || []

      if (host) whenRendered(host, '.nc-root', (root) => bindList(root, rows))

      return `
        <div class="nc-root" style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;background:var(--sapBackgroundColor,#f7f7f7);color:var(--sapTextColor,#1d2d3e);">
          <ui5-bar design="Header">
            <ui5-label slot="startContent" style="font-weight:800;">${props.title || '通知中心'}</ui5-label>
          </ui5-bar>
          <div class="biz-bar">
            <ui5-label>共 ${rows.length} 条</ui5-label>
          </div>
          <cmx-revo-grid id="grid" style="flex:1 1 auto;min-height:0;"></cmx-revo-grid>
        </div>
      `
    }
  }
}

function bindList(root, rows) {
  const C = cmx()
  const grid = root.querySelector('#grid')
  if (!grid || !C.CmxColumnModel) return
  grid.setColumnModel(new C.CmxColumnModel({ members: [
    new C.CmxColumn({ id: 'title', caption: '标题', dataType: 'VARCHAR', width: '300px' }),
    new C.CmxColumn({ id: 'createdAt', caption: '时间', dataType: 'DATETIME', width: '160px' }),
    new C.CmxColumn({ id: 'status', caption: '状态', dataType: 'VARCHAR', width: '100px' }),
    // 操作列：display.mode='actions' + cmx-cell-link-click（首选，勿手写 cellTemplate）
    new C.CmxColumn({ id: '_action', caption: '操作', dataType: 'VARCHAR', width: '180px',
      edit: { mode: 'readonly' },
      display: { mode: 'actions', actions: [
        { text: '编辑', actionRef: 'edit', icon: 'edit' },
        { text: '删除', actionRef: 'delete', variant: 'negative' },
      ] } }),
  ]}))
  // 操作列点击：rowId 是 revo 行索引，反查真实行
  grid.addEventListener('cmx-cell-link-click', (e) => {
    const { rowId, actionRef } = e.detail
    const ds = grid._ds
    const row = ds?.rows?.[parseInt(rowId, 10)]
    const r = row?.toPlainObject ? row.toPlainObject() : row
    if (!r) return
    if (actionRef === 'edit') openEdit(r.id)
    else if (actionRef === 'delete') confirmDelete(r.id)
  })
  if (C.CmxDataSet) {
    const ds = new C.CmxDataSet({})
    ds.setRows(rows)
    grid.setDataSet(ds)
  }
}
```

---

## 九、调试技巧

```js
// 打印 ctx 全貌
console.log('ctx:', ctx)
console.log('props:', ctx.props)
console.log('host attrs:', ctx.host.getAttributeNames())

// 检查 cmx 助手是否就绪
const C = (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}
console.log('cmx keys:', Object.keys(C))

// 监听宿主属性变化（菜单切换 view 时）
new MutationObserver(muts => console.log('host changed:', muts)).observe(ctx.host, { attributes: true })

// 在 render 里加 debugger
async content(ctx) {
  debugger   // 浏览器 devtools 会断在这里
  ...
}
```

---

## 十、容易踩的坑

| 坑 | 正确做法 |
| --- | --- |
| `import cmx-data-comp` | 用 `globalThis.__cmxDataComp` |
| 同步 querySelector 返回 null | 用 `whenRendered` 等渲染 |
| 模块级 state 跨实例污染 | content(ctx) 入口重置 state |
| 返回整页 HTML 但想用 cmx 组件 | 整页走 iframe 沙箱，**无 globalThis.__cmxDataComp**；要复用组件就返回片段 |
| 忘 `credentials: 'same-origin'` | fetch 不带鉴权 cookie → 401 |
| 用 `alert()` | 用 `cmxInfo` / `cmxWarn` / `cmxError` |
| 硬编码色值 | 用 `var(--sap*)`（见 page-style-guide.md） |
| props 字段名和菜单配置不一致 | 与菜单节点 props 严格对齐（衔接 menu-generator） |
