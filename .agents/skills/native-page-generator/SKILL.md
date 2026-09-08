---
name: native-page-generator
description: 指导生成 CMX 原生页面（native-pages，代码即页面）——JS 模块（导出 render(ctx) 函数）或 HTML 片段，不走设计器、不用 __designer_meta__。当用户要求生成 / 创建原生页面、native 页、纯代码业务页、管理类页面、元数据驱动通用页，或提到 native-pages、cmx-native-pages-host、globalThis.__cmxDataComp、render(ctx)、不走设计器的页面时必用。与 html-page-generator（设计器页面）成对存在——页面需走设计器 / 用 6 大模型 / 配置化时用 html-page-generator。
---

# native-page-generator（原生页面生成器）

指导你为 CMX 门户生成**原生页面**（native-pages）：产出 JS 模块（导出 `render(ctx)` 函数）或 HTML 片段，**不走设计器、不用 `__designer_meta__`**。

> **范围**：本技能专管"代码即页面"。若页面要走设计器配置 / 用 6 大数据模型（CmxMasterSlave / FlexibleCombination 等）/ 配置化，用 `html-page-generator` 技能。

---

## 一、与 html-page-generator 的边界（先判断用哪个）

| 维度 | html-page-generator（设计器页） | native-page-generator（本技能） |
| --- | --- | --- |
| 技术路线 | 配置即页面（`__designer_meta__.models`） | 代码即页面（JS 模块 `render(ctx)`） |
| 走不走设计器 | 走（Page Data / Models 面板配置） | **不走**（纯手写/生成代码） |
| 用不用 6 大模型 | 用（CmxDataSet / CmxMasterSlave / FC 等） | 不用（可选程序化调用 cmx 助手） |
| 运行时 | CE 模板编译（`cmx-html-pages-<slug>`） | `cmx-native-pages-host` + Blob import |
| 取 cmx 类 | importmap + 标签 | **`globalThis.__cmxDataComp`**（不能 import） |
| 典型场景 | 凭证录入、主从协调 + 弹性组合、固定结构表单 | 元数据驱动通用页、管理类页面、列表中心、不走设计器的定制页 |

**选择规则**：
- 需 6 大模型驱动 / 主从协调 + 弹性组合 / 走设计器配置 → **html-page-generator**
- 需纯代码控制 / 元数据动态驱动 / 管理类页面 / 不走设计器 → **本技能（native-page-generator）**

---

## 二、native-page 的两种形态

| 形态 | sourceType | 何时选 | 复用 cmx 组件 |
| --- | --- | --- | --- |
| **JS 模块页**（推荐） | `js` | 需复用 cmx 组件/助手 / 多状态 / 后端动态 / 元数据驱动 | 可（经 `globalThis.__cmxDataComp`） |
| **HTML 片段页** | `html` | 纯静态展示 / 简单交互 / 跨区域联动 demo | 不推荐（无 importmap） |

> 本技能**重点支持 JS 模块页**（生产级形态）。HTML 片段页只做轻量引导。

---

## 三、核心契约（JS 模块页，必记）

### 1. 导出格式（4 种形态均可识别，源码 `workspace-native-pages.js`）

```js
// 形态 1（推荐）：对象 + views 映射
export default {
  defaultView: 'content',
  views: {
    async content(ctx) { /* ... */ return htmlString }
  }
}

// 形态 2：默认导出函数
export default function render(ctx) { /* ... */ return htmlString }

// 形态 3：命名导出 nativePage
export const nativePage = { defaultView: 'content', views: { content(ctx) {...} } }

// 形态 4：命名导出 page
export const page = { defaultView: 'content', views: { content(ctx) {...} } }
```

> `views` 是 view 名 → 渲染函数的映射；`defaultView` 指定默认 view。宿主按菜单节点配置的 `view` 属性选对应 view 函数。

### 2. ctx 对象（render 函数接收）

```js
{
  pageId: 'portal.doc.doc-loader',   // native-page id
  view: 'content',                    // 当前 view 名
  region: 'content',                  // 工作区区域
  props: { file, dbId, apiPath, ... },  // 来自菜单节点（非 DAM 的业务参数）
  native: {...},                      // 菜单节点的 native 配置
  host: <cmx-native-pages-host CE>    // 宿主元素
}
```

**关键**：
- `ctx.props` 来自菜单节点 `parseJsonAttr(getAttribute('props'))`——这是与 `menu-generator` 的衔接点。props 只放**业务参数**（如 `{ file, dbId, apiPath, dict }`）。
- **DAM（domain/application/module）不要写进 props**，改从 `ctx.host.workspace.context` 读取（框架 openNode 时自动注入）。详见下文「2.1 取 DAM 坐标」。

### 2.1 取 DAM 坐标（domain/application/module）—— 必读

门户框架在 `openNode` 打开页面时，把当前菜单节点所属的 DAM 注入到 `workspace.context`（短名 `domain/application/module`）。页面统一用 `ctx.host.workspace.context.get(...)` 读取，**禁止**在菜单 props 里写死 DAM。

```js
// ✅ 正确：从 workspace.context 取 DAM（框架注入），fallback props（向后兼容）
const wctx = ctx.host && ctx.host.workspace && ctx.host.workspace.context
const get = (k) => (wctx && typeof wctx.get === 'function' ? wctx.get(k) : undefined)
const domain = get('domain') || ctx.props.domain || ''
const application = get('application') || ctx.props.application || ''
const module = get('module') || ctx.props.module || ''
// file/dbId/apiPath 等业务参数仍在 props
const file = ctx.props.file
```

> 为什么这样设计：DAM 是菜单节点的归属维度（数据库 `cmx_menu` 一等列 `domain_code/application_code/module_code`），应由框架统一注入，而非每个页面在 props 里重复写死。这避免了页面里写死 dam、迁移困难的问题。`fallback ctx.props` 仅为向后兼容旧菜单文件，新菜单不要在 props 写 dam。

### 3. render 返回值 → 渲染分流

| 返回内容 | 渲染方式 |
| --- | --- |
| 完整 HTML 文档（含 `<!doctype>` / `<html>`） | **iframe srcdoc** 沙箱（脚本/样式隔离） |
| HTML 片段 | 挂进 `cmx-native-pages-host` 的 shadowRoot |

源码：`workspace-native-pages.js 渲染分流, 198-202`

### 4. 铁律：禁止 import cmx-data-comp

```js
// ❌ 错误：Blob import 解析不了裸模块名
import { CmxMasterSlave } from 'cmx-data-comp'

// ✅ 正确：从全局取
const cmx = () => (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}
const { CmxMasterSlave, buildColumnModel } = cmx()
```

> native JS 页源码经 Blob + `import()` 加载，**无法解析裸模块名**。cmx-data-comp 由 Portal 在 `import-ui5-and-app.js` 预挂到 `globalThis.__cmxDataComp`。UI5 已由 Portal `cmx-ui5-runtime` boot 完成，`ui5-*` 标签可直接用。

### 5. 铁律：时间显示转当前时区（硬性要求）

后端时间一律 UTC ISO（如 `2026-09-03T16:43:38.238813+00:00`）。**显示前必须转浏览器当前时区，禁止 `slice`/`replace('T')`/`substr` 截取**——截出来是 UTC，用户看到的时间差一个时区（评审一票否决）：

```js
// ❌ 错误：UTC 串直接截取冒充本地时间
const fmtTime = (t) => String(t || '').slice(0, 19).replace('T', ' ')

// ✅ 正确：globalThis.cmx.datetime（cmx-shared 共享时间域；解析/格式化/指定时区/相对时间全套见真源 §二.6）
const __CMX_DT = (typeof globalThis !== 'undefined' && globalThis.cmx && globalThis.cmx.datetime) || null
const fmtT = (t) => (__CMX_DT ? __CMX_DT.fmtDateTime(t) : (t ? String(t) : ''))
```

函数清单（`fmtDateTime`/`fmtDate`/`fmtMinute`/`fmtRelative`/`fmtDuration`…）与 4 行标准接入片段见共享真源 `../cmx-components-guide/references/frontend-conventions.md` §二.6；不要往 `__cmxDataComp` 上挂工具（纯工具统一挂 `globalThis.cmx.{domain}`）。

---

## 四、统一生成工作流（5 步）

### Step 0：组件选型（前置，必做）

**生成任何 UI 前，先读 `../cmx-components-guide/references/component-catalog.md`**——选型优先级（cmx-data-comp 组件 → cmx lib 助手 → UI5 → div 白名单 → 自研须与用户确认）、常见误自研清单、自研判断流程**全部以该共享真源为准**，不在此复述。native 特有取用方式：JS 模块页经 `globalThis.__cmxDataComp` 取组件类后程序化渲染。

### Step 0·5：换肤与 Neo 主题（硬性要求，新增页面默认遵循）

**所有新建页面必须支持换肤，并默认采用 Neo 主题**——用 Neo 就用 cmx 组件（原生 `<table>`/`<ul>`/`<input>` 不会自动套 Neo），骨架层一律 `var(--sap*)`/`var(--neo-*)` 派生禁止硬编码。换肤机制全貌（`data-cmx-skin` 三级优先级 / `data-cmx-skin-tone` / `data-cmx-style-id` / 多主题共存 / 运行时改属性换肤）见共享真源 `../cmx-components-guide/references/page-style-guide.md` 第二、五、六节，本技能不重复维护。

### Step 1：判断形态
- 需复用 cmx 组件 / 多状态 / 后端动态 → **JS 模块页**
- 纯静态 / 简单交互 → HTML 片段页（但如需任何 cmx 组件，转 JS 模块页）

### Step 2：读对应 reference
- **必读 `../cmx-components-guide/references/component-catalog.md`**（组件选型清单，查有没有现成组件）
- JS 模块页 → 读 `references/js-module-page.md` + `references/runtime-contract.md`
- HTML 片段页 → 读 `references/html-fragment-page.md` + `references/runtime-contract.md`
- **任何形态都读 `../cmx-components-guide/references/page-style-guide.md`**（统一骨架 + 颜色 + 约定 class）

### Step 3：生成源码
- JS 模块页：`.js` 文件，4 种导出形态之一，`render(ctx)` 返回 HTML 字符串
- HTML 片段：`.html` 文件，含可选 `<script>`（由宿主包函数作用域执行）

### Step 4：登记 index.json
native-page 需在 `cmx-container/assets/portal/data/native-pages/index.json` 登记：
```jsonc
{ "id":"portal.xxx.xxx", "name":"页面名", "details":"说明", "sourceType":"js", "relPath":"portal/xxx/xxx.js" }
```
（或经 `POST /api/native-pages` 自动 upsert）

---

## 五、最小 JS 模块页骨架（可直接复制改）

```js
/**
 * xxx-loader —— 简单列表 native 页（native_pages，JS 模块）。
 * 契约：export default { defaultView, views:{ <view>(ctx) } }；ctx.props 来自菜单。
 * CMX 类经 globalThis.__cmxDataComp 取用。
 */
const cmx = () => (typeof globalThis !== 'undefined' && globalThis.__cmxDataComp) || {}

export default {
  defaultView: 'content',
  views: {
    async content(ctx) {
      const props = (ctx && ctx.props) || {}
      const host = ctx && ctx.host
      // 1. 取 DAM 坐标：优先 workspace.context（框架注入），fallback props（见 §2.1）
      const wctx = host && host.workspace && host.workspace.context
      const get = (k) => (wctx && typeof wctx.get === 'function' ? wctx.get(k) : undefined)
      const domain = get('domain') || props.domain || ''
      const application = get('application') || props.application || ''
      const module = get('module') || props.module || ''
      // 2. 拉数据
      const q = new URLSearchParams({ domain, application, module, dict: props.dict || '' })
      const res = await fetch('/api/dct/data/search?' + q.toString(), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
        body: JSON.stringify({ page: 1, pageSize: 50 })
      })
      const body = await res.json()
      const pkg = (body && typeof body.code === 'number') ? body.data : body
      const rows = (pkg && pkg.rows) || []

      // 2. 渲染后异步绑组件
      if (host) whenRendered(host, '.xxx-root', (root) => bindGrid(root, rows))

      // 3. 返回 HTML 片段（套用统一骨架，见 ../cmx-components-guide/references/page-style-guide.md）
      return `
        <div class="xxx-root" style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;background:var(--sapBackgroundColor,#f7f7f7);color:var(--sapTextColor,#1d2d3e);">
          <ui5-bar design="Header">
            <ui5-label slot="startContent" style="font-weight:800;">${props.title || '列表'}</ui5-label>
          </ui5-bar>
          <cmx-revo-grid id="grid" style="flex:1 1 auto;min-height:0;"></cmx-revo-grid>
        </div>
      `
    }
  }
}

// 等待元素渲染到 shadowRoot（ctx.host.renderRoot）
function whenRendered(host, selector, cb) {
  const root = host.renderRoot || host.shadowRoot
  const el = root && root.querySelector(selector)
  if (el) { cb(el); return }
  const obs = new MutationObserver(() => {
    const el2 = (host.renderRoot || host.shadowRoot).querySelector(selector)
    if (el2) { obs.disconnect(); cb(el2) }
  })
  if (root) obs.observe(root, { childList: true, subtree: true })
}

function bindGrid(rootEl, rows) {
  const C = cmx()
  const grid = rootEl.querySelector('#grid')
  if (!grid || !C || !C.CmxColumnModel || !C.CmxColumn) return
  grid.setColumnModel(new C.CmxColumnModel({ members: [
    new C.CmxColumn({ id: 'code', caption: '编码', dataType: 'VARCHAR', width: '140px' }),
    new C.CmxColumn({ id: 'name', caption: '名称', dataType: 'VARCHAR', width: '200px' })
  ]}))
  if (C.CmxDataSet) {
    const ds = new C.CmxDataSet({})
    ds.setRows(rows)
    grid.setDataSet(ds)
  }
}
```

> 完整元数据驱动范例见 `references/js-module-page.md`（仿 `doc-loader.js`）。

---

## 六、高频陷阱

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| `import ... from 'cmx-data-comp'` | 用 `globalThis.__cmxDataComp` | Blob import 解析不了裸模块名 |
| 用 `__designer_meta__` / 6 大模型配置 | 不要用——这是 html-page 的机制 | native 页不走设计器 |
| render 返回的 HTML 里写 `host.shadowRoot` | 用 `ctx.host.renderRoot`（指向 shadowRoot） | 宿主提供 renderRoot 别名 |
| 同步操作返回的 DOM | 用 `whenRendered` / `MutationObserver` 等渲染 | render 返回后 DOM 才被注入 shadowRoot |
| sourceType 写 `javascript` | 只能是 `js` 或 `html` | 后端严格校验（`native.rs`） |
| relPath 扩展名与 sourceType 不符 | `.js` ↔ js，`.html` ↔ html | 后端校验 |
| 硬编码色值 | `var(--sap*)` / `var(--neo*)` | 见 ../cmx-components-guide/references/page-style-guide.md |
| 用 `alert()` | `cmxInfo` / `cmxWarn` / `cmxError` | AGENTS.md 七.6 红线 |
| 用 `style="background:#fff"` 给卡片 | 用 `class="neo-panel"` / `var(--sapList_Background)` | 切 UI5 dark 主题时白底闪烁；与系统脱节 |
| 在 JS 模块页里手写 `:host { background: #xxx }` 复写皮肤 | 用 `data-cmx-skin` / `data-cmx-skin-tone` 走 Neo | 双重样式源、组件升级必坏 |
| 用户切到 dark 主题后页面不变 | 全程 `var(--sap*)` + `color-mix(... var(--sapList_Background) ...)` | Neo 公式自动适配，详见 ../cmx-components-guide/references/page-style-guide.md 七 |

---

## 六·五、生成物自检清单

交付前核对：

- [ ] **UI 优先用 cmx-data-comp 组件**（cmx-revo-grid/cmx-ui5-form/cmx-dict-select/cmx-floating-dialog/cmx-pager 等）；任何自研组件均已与用户沟通确认
- [ ] 不写 `import ... from 'cmx-data-comp'`，用 `globalThis.__cmxDataComp`
- [ ] `ctx.props` 字段与菜单节点 props 配置一致（**DAM 走 workspace.context，不写进 props**，见 §2.1）
- [ ] DOM 操作用 `ctx.host.renderRoot` + `whenRendered` 等渲染
- [ ] sourceType 与 relPath 扩展名匹配（js↔.js / html↔.html）
- [ ] index.json 登记项齐全（id/name/details/sourceType/relPath）
- [ ] 根 div 套用标准骨架（flex column + var(--sap*)）
- [ ] 无 `alert()`/`confirm()`/硬编码色值
- [ ] **换肤**：未显式关 Neo 的组件保持默认（`data-cmx-skin` 不写或写 `neo`）；要换色用 `data-cmx-skin-tone`，不要复制皮肤源到页内重写
- [ ] **主题跟随**：所有色值走 `var(--sap*)` / `var(--neo-*)` 派生，UI5 切 light/dark 时页面**自动跟随**，无白底闪烁
- [ ] **多主题支持**：若页面要响应用户换肤（URL `?skin=`、偏好、菜单），监听器通过改 `data-cmx-skin` / `data-cmx-skin-tone` 触发 attributeChangedCallback，**不要**直接 `setAttribute('style', ...)`
- [ ] **时间显示**：所有时间列/徽标/详情经 `globalThis.cmx.datetime` 转当前时区（§三.5），全页无 `slice(0,10/16/19)` / `replace('T',' ')` 时间截取

> 完整运行时自检见 `references/runtime-contract.md` 第八节。

---

## 七、references 索引

| 文件 | 何时读 | 核心内容 |
| --- | --- | --- |
| `../cmx-components-guide/references/component-catalog.md` | **生成任何 UI 前必读** | cmx-data-comp 组件选型清单（表格/表单/输入/布局/树/对话框/ignite）+ 自研判断流程 |
| `../cmx-components-guide/references/field-edit-display-modes.md` | **构造 CmxColumn / 定义字段时必读** | edit.mode 16 规范值 + 每个 mode 专属属性 + display.mode 7 值（含 actions 操作列 + `cmx-cell-link-click` 事件）+ 数值类属性显隐 + 三元字段全集 + 三端差异 |
| `references/js-module-page.md` | **JS 模块页必读** | 4 种导出形态 / globalThis.__cmxDataComp 助手清单 / DOM 操作 / 2 个完整模板 |
| `references/html-fragment-page.md` | HTML 片段页 | 何时选 / script 执行环境 / workspace.context 跨区域联动 |
| `references/runtime-contract.md` | 所有形态 | 装载链路 / 宿主 CE 属性 / ctx 结构 / 后端契约（index.json + /api/native-pages） |
| `../cmx-components-guide/references/page-style-guide.md` | **生成 HTML 时必读** | 统一根 div 骨架 / var(--sap*) 颜色 / .biz-bar .lvlbox 约定 class / Neo 皮肤 |
| `references/workspace-region-linkage.md` | **配置 content ↔ property 联动时必读** | view spec 的 hideProperty / syncPropertyView 字段 / 框架级联动机制 / 配置示例 |

**读取原则**：先读 SKILL.md 决策 → **Step 0 必读 ../cmx-components-guide/references/component-catalog.md（组件选型）** → **构造 CmxColumn 时必读 ../cmx-components-guide/references/field-edit-display-modes.md（字段值域）** → 选定形态后读对应 reference（js-module 或 html-fragment）+ runtime-contract → **必读 ../cmx-components-guide/references/page-style-guide.md**。不要全读。

---

## 附：弹层 / 网格 / 作用域 实战陷阱（MDM 页面沉淀，生成前必读）

> 以下三条为 MDM 主数据页面（录入/待办/管家）实测踩坑结论，违反即出现"按钮没反应 / 弹框左侧一条线 / 表格不显示行"。

1. **弹层必须挂 `document.body` 且自带内联 `<style>`**。
   页内 DOM 在宿主 `cmx-native-pages-host` 的 shadowRoot 内：页内 `<style>` 作用不到 body；且页内 `position:fixed` 会被门户内容区的 transform 祖先"困住"，遮罩左缘从内容区起始 → 弹框左侧出现一条明暗分界线。
   正确：`document.body.appendChild(mask)`，mask 内首行 `<style>…弹层样式…</style>`，类名加前缀（如 `.mdm-mask/.mdm-dlg`）防污染。
2. **页内 DOM 查询必须用渲染根作用域，禁用 `document.getElementById`**。
   shadowRoot 隔离使 `document.getElementById` 返回 null → 读值/绑网格失败、按钮"没反应"。
   正确：`rootEl = ctx.host.renderRoot || ctx.host.shadowRoot; const q = (id) => rootEl.querySelector('#' + id)`。
3. **弹层内的 `cmx-revo-grid` 行可能不渲染**（初始化时序：`setDataSet/addRow` 后数据集有行但可视网格空白）。
   对策：① 弹层入 DOM 且可见后再绑数据并调 `refreshLayout()`；② **小型可编辑/只读明细（如银行账户行）直接用普通 `<table>` + 状态数组驱动**，增删即时可见、取值可靠，规避时序问题。

---

## 附二：页内打开并列标签页（openNode + initialContext + 单例/多开）

> 详情/新增/编辑应为**并列门户标签页**（关闭一个不影响另一个），不用弹框。机制 = `cmx-portal-app.openNode(node, { initialContext })`，与设计师页"列表→详情"同一模式。

**打开方**（native 模块脚本在主 realm 执行，可直达 portal-app）：

```js
function openTab (host, caption, nativePage, context, opts = {}) {
  let app = document.querySelector('cmx-portal-app')          // 直达，最稳
  if (!app?.openNode) { /* 兜底：从 host 逐层 getRootNode().host 找 openNode */ }
  const ctxKey = (context && (context.crId || context.supplier?.id)) || ''
  const key = opts.single ? 'single' : (ctxKey || Date.now())  // 单例 vs 多开
  app.openNode({
    id: `${nativePage}-${key}`, name: nativePage, caption, type: 'workspace-node',
    workspace: { content: { caption, views: [{ type: 'native_pages', native_page: nativePage, view: 'content' }] } },
  }, { initialContext: context })
}
```

**单例/多开控制**（addTab 按 `id` 去重）：
- `opts.single=true` → 固定 id（`...-single`），重复点击**复用/聚焦同一 tab**（如「新增」只开一个）。
- 默认 → id 含行 id（crId/supplier.id），**不同行开多个 tab**（如「详情」）。同 id 再开则复用并同步 context。

**目标页读参**：`const crId = ctx.host?.workspace?.context?.get?.('crId')`（initialContext 注入 workspace.context）。

**目标页须注册**：在 `data/native-pages/index.json` 登记 nativePage（可不在菜单展示）。

**范例**：MDM `cr-editor.js`（列表，新增 single / 详情多开）→ `cr-form.js` / `supplier-detail.js` / `cr-detail.js`（读 context）。

---

## 八、相关技能

- **`html-page-generator`** —— 页面需走设计器 / 用 6 大数据模型 / 配置化（`__designer_meta__`）时用。典型：凭证录入（主从协调 + 弹性组合）、固定结构表单。
- **`menu-generator`** —— 页面要**挂到门户菜单** / 配置工作区节点 / 给页面注入 `ctx.props`（业务参数，如 `{ file, dbId, apiPath, dict }`）时用。**DAM 不走 props**：框架 openNode 时自动把当前菜单节点的 domain/application/module 注入 `workspace.context`，页面用 `ctx.host.workspace.context.get('domain')` 读取（见 §2.1）。
- **`cmx-components-guide`** —— cmx-data-comp 组件使用手册（96 个自定义元素的配置项 / API / 事件 / slot / 使用配方）。本技能负责"页面怎么生成、组件怎么取（`globalThis.__cmxDataComp`）"，组件**具体用法**转交该技能。

> 用户说"加个菜单""配置工作区节点""让 native 页能从菜单打开并传 props"→ `menu-generator`；说"凭证录入""主从协调""弹性组合""走设计器"→ `html-page-generator`；说"cmx-revo-grid 怎么配列""cmx-dict-select 有哪些参数""cmx-pager 事件"→ `cmx-components-guide`。直接调用对应技能，不在本技能里复制其逻辑。
