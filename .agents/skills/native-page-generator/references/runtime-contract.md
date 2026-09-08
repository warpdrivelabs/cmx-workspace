# 运行时契约（native-page 装载链路 + 宿主 CE + 后端）

> 何时读：所有 native-page 形态都建议读——理解页面是怎么被加载和渲染的。
> 源码：`../../../../cmx-portal-manager` + `cmx-container/crates/libs/cmx-form/src/pages/native.rs`

---

## 一、完整装载链路

```
用户点击菜单节点（type: 'native_pages', native_page: '<id>', view?: 'content', props?: {...}）
   ↓
registerNativePagesWorkspaceViewType() 注册 'native_pages' 视图类型
   ↓
渲染 <cmx-native-pages-host native-page="..." view="..." props="...">
   ↓
CE connectedCallback → _load()
   ↓
fetch('/api/native-pages/<id>') → { sourceType:'js'|'html', source:'源码字符串' }
   ↓
materializeNativePage 按 sourceType 分流：
   ├─ js  → importNativePageModule（Blob + import()）→ 取 mod.render / mod.default / mod.nativePage / mod.page
   └─ html → 直接当 HTML 字符串
   ↓
调用 render(ctx) 得到 HTML 字符串（js 模块页）或 source 本身（html 页）
   ↓
按返回 HTML 形态分流渲染：
   ├─ 完整文档（<!doctype>/<html>）→ _renderIframe（iframe srcdoc 沙箱）
   └─ 片段 → _renderHtml（挂 shadowRoot 的 .native-page-root）
   ↓
片段里的 <script> 由 _runScripts 用 new Function('workspace','host','ctx', code) 执行
```

源码位置：
- 视图类型注册：`workspace-native-pages.js`
- `_load`：`workspace-native-pages.js`
- `materializeNativePage`：`workspace-native-pages.js`
- `importNativePageModule`：`workspace-native-pages.js`
- 渲染分流：`workspace-native-pages.js, 198-202`
- script 执行：`workspace-native-pages.js`

---

## 二、宿主 CE 属性（cmx-native-pages-host）

```html
<cmx-native-pages-host
  native-page="portal.doc.doc-loader"   <!-- ★ native-page id（来自 index.json）-->
  view="content"                         <!-- view 名（对应 views 映射的 key）-->
  region="content"                       <!-- 工作区区域 -->
  props='{"file":"cmxfico_doc_meta_v1.json","dbId":"fico-db","apiPath":"/api/doc/data/sqlx-dataset-json"}'  <!-- ★ 业务参数（DAM 不在这里，走 workspace.context）-->
  native='{}'>                           <!-- native 配置 -->
</cmx-native-pages-host>
```

> DAM（domain/application/module）不进 `props` 属性：框架 openNode 时自动注入到 `workspace.context`，页面用 `ctx.host.workspace.context.get('domain')` 读取。`props` 只放业务参数（file/dbId/apiPath 等）。

| 属性 | 含义 | 来源 |
| --- | --- | --- |
| `native-page` | native-page id | 菜单节点 `native_page` 字段 |
| `view` | 视图名 | 菜单节点 `view` 字段（缺省用 defaultView） |
| `region` | 工作区区域 | 菜单节点位置 |
| `props` | JSON 字符串，注入到 `ctx.props` | 菜单节点 `props` 字段（`parseJsonAttr` 解析） |
| `native` | JSON 字符串，注入到 `ctx.native` | 菜单节点 `native` 字段 |

> 这些属性由菜单节点配置决定——这是与 `menu-generator` 的衔接点。

### props 解析（parseJsonAttr）

`workspace-native-pages.js` 用 `parseJsonAttr` 解析 props 字符串：
- 合法 JSON → 解析为对象
- 空字符串 / null → `null`
- 解析失败 → 容错处理

生成菜单节点时 props 必须是**合法 JSON 字符串**。

---

## 三、ctx 对象完整结构

```js
// render(ctx) 或 <script> 里注入的 ctx
{
  pageId: 'portal.doc.doc-loader',       // native-page id
  view: 'content',                        // 当前 view（来自 CE view 属性）
  region: 'content',                      // 区域（来自 CE region 属性）
  props: { file, dbId, apiPath, ... },    // 业务参数（来自 CE props 属性）；DAM 不走这里
  native: { ... },                        // 来自 CE native 属性
  host: <cmx-native-pages-host CE>        // 宿主元素
}
```

> **DAM（domain/application/module）不在 ctx.props 里**。框架 openNode 时把当前菜单节点的 DAM 注入到 `ctx.host.workspace.context`（短名 `domain/application/module`）。取值：
> `const wctx = ctx.host && ctx.host.workspace && ctx.host.workspace.context`
> `const domain = (wctx && wctx.get && wctx.get('domain')) || ctx.props.domain || ''`
> 详见 `SKILL.md §2.1`。

### ctx.host 的关键成员

| 成员 | 含义 |
| --- | --- |
| `host.renderRoot` | shadowRoot（渲染目标，等同 `host.shadowRoot`） |
| `host.workspace` | 工作区 scope（跨区域联动 `workspace.context.set/get/on`） |
| `host.getAttribute(name)` | 读宿主属性（native-page/view/region/props/native） |
| `host._seq` | 内部加载序号（防并发竞态） |

---

## 四、后端契约

### 4.1 native-page 存储

native-page 存储分两部分（源码 `cmx-form/src/pages/native.rs`）：

**索引**：`cmx-container/assets/portal/data/native-pages/index.json`
```jsonc
[
  {
    "id": "portal.doc.doc-loader",        // ★ 唯一 id
    "name": "通用业务单据加载页",            // 显示名
    "details": "纯通用：层数 N/各层列/主从关系全来自 /api/doc/meta...",  // 说明
    "sourceType": "js",                     // ★ 仅 "js" 或 "html"（严格校验）
    "relPath": "portal/doc/doc-loader.js"  // ★ 相对 sources/ 的路径，扩展名须与 sourceType 匹配
  }
]
```

**源码**：`cmx-container/assets/portal/data/native-pages/sources/<relPath>`（如 `portal/doc/doc-loader.js`）

> 索引字段定义源码：`native.rs`；sourceType / relPath 校验：`native.rs`。

### 4.2 后端 API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/native-pages?page=&pageSize=` | 分页列索引 |
| GET | `/api/native-pages/{id}` | 取单页完整内容（含 source 源码） |
| POST | `/api/native-pages` | upsert（写源文件 + 更新 index.json） |
| POST | `/api/native-pages/batch` | 批量取（body `{ ids: [...] }`） |

路由注册：`cmx-container/crates/libs/cmx-apis/cmx-common-api/src/handlers/portal/mod.rs`（native-pages 路由段）

### 4.3 单页完整返回（NativePageFull）

`GET /api/native-pages/{id}` 响应 `data`（源码 `native.rs`）：
```jsonc
{
  "id": "portal.doc.doc-loader",
  "name": "通用业务单据加载页",
  "details": "...",
  "sourceType": "js",
  "relPath": "portal/doc/doc-loader.js",
  "source": "/* 完整源码字符串 */"       // ★ 源码本体
}
```

### 4.4 upsert（POST /api/native-pages）

请求 body：`NativePageInput`（id/name/details/sourceType/relPath/source）。后端：
- 写源码到 `sources/<relPath>`
- 更新 `index.json`（按 id upsert 索引项）

源码：`native.rs`（`save_native_page`）

---

## 五、与菜单节点的衔接（关键）

native-page 本身只是源码文件，**必须通过菜单节点才能在门户打开**。菜单节点配置（`portal-workspace-node-dialog.js`）：

```jsonc
{
  "type": "native_pages",
  "native_page": "portal.doc.doc-loader",
  "view": "content",
  "props": { "file": "cmxfico_doc_meta_v1.json", "dbId": "fico-db", "apiPath": "/api/doc/data/sqlx-dataset-json" }
}
```

> **props 只放业务参数**（file/dbId/apiPath 等）。DAM（domain/application/module）不要写进 props——它由菜单文件路径决定（`menu-pages/<domain>/<app>/<module>/...`），框架 openNode 时自动注入到页面 `workspace.context`，页面用 `ctx.host.workspace.context.get('domain')` 读取。详见 `SKILL.md §2.1`。

> 菜单节点的 `type` / `native_page` / `view` / `props` 字段决定 native 页怎么被加载、收到什么 ctx.props。

**衔接点**：
- native 页生成后 → 需要挂菜单 / 配 props → 转交 `menu-generator` 技能
- native 页的 props 契约（需要哪些字段）必须与菜单节点 props 配置一致

---

## 六、缓存机制

- **模块缓存**：`importNativePageModule` 按 pageId 缓存 Blob import 结果（`_moduleCache`），同一 native 页只 import 一次
- **定义缓存**：`loadNativePageDef` 按 pageId 缓存完整定义

> 含义：修改 native 页源码后，可能需要刷新 Portal 或改 pageId 才能生效（开发期注意）。

---

## 七、sourceType / relPath 校验规则

源码 `native.rs`：

| 规则 | 说明 |
| --- | --- |
| `sourceType` 仅 `js` / `html` | 其它值拒绝 |
| `relPath` 扩展名与 sourceType 匹配 | `.js` ↔ `js`；`.html` ↔ `html` |
| `relPath` 不能含 `..` | 防路径穿越 |
| `id` 唯一 | index.json 里不能重复 |

生成 native-page 时严格按这套规则命名文件和登记 index.json。

---

## 八、生成自检清单

交付前核对：
- [ ] JS 模块页：4 种导出形态之一，`render(ctx)` 返回 HTML 字符串
- [ ] 不写 `import ... from 'cmx-data-comp'`，用 `globalThis.__cmxDataComp`
- [ ] `ctx.props` 字段与菜单节点 props 配置一致
- [ ] DOM 操作用 `ctx.host.renderRoot` + `whenRendered` 等渲染
- [ ] sourceType 与 relPath 扩展名匹配（js↔.js / html↔.html）
- [ ] index.json 登记项齐全（id/name/details/sourceType/relPath）
- [ ] 根 div 套用标准骨架（flex column + var(--sap*)）
- [ ] 无 `alert()`/`confirm()`/硬编码色值
- [ ] 模块级 state 在 content(ctx) 入口重置

---

## 九、关键文件索引

| 用途 | 路径 |
| --- | --- |
| 运行时宿主 | `../../../../cmx-portal-manager` |
| 后端存储契约 | `cmx-container/crates/libs/cmx-form/src/pages/native.rs` |
| 索引文件 | `cmx-container/assets/portal/data/native-pages/index.json` |
| 源码目录 | `cmx-container/assets/portal/data/native-pages/sources/` |
| 菜单节点配置 | `../../../../cmx-portal-manager` |
| cmx 助手预挂 | `../../../../cmx-portal-manager` |
| JS 模块页范例 | `cmx-container/assets/model/web/ui-native/portal/doc/doc-loader.js` |
| HTML 片段范例 | `cmx-container/assets/portal/data/native-pages/sources/demo/product-explorer.html` |
| 列表页范例 | `cmx-container/assets/portal/data/native-pages/sources/portal/notify/center.js` |
