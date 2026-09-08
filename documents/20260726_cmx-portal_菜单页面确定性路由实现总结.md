# CMX Portal 菜单页面确定性路由实现总结

> 适用于 `cmx-portal-manager`。本文档总结当前代码实现的菜单页面路由方案（URL 设计、双向同步机制、参数传递规则），不涉及多方案比较。

---

## 一、背景与目标

CMX Portal 的菜单从后端 `cmx_menu` 表动态加载，**早期实现存在两个问题**：

1. **刷新即丢**：所有"页面"都是 content-tab，URL 始终是 `/`。刷新页面后无法回到当前业务视图，必回到首页。
2. **链接不可分享**：业务视图没有独立 URL，无法通过链接直接打开某个菜单页。

**目标**：为每个菜单页定义**确定性 URL**，满足：
- 直接访问 URL 能打开对应菜单页
- 刷新页面保持当前菜单页不丢失
- 浏览器前进/后退语义正确
- 业务方可控的参数传递（代码打开走内存，深链走 URL query）
- 纯前端实现，零后端改动

---

## 二、URL 设计

基于 `cmx_menu.code`（业务唯一稳定编码，UNIQUE INDEX）的确定性路径：

| URL | 含义 |
| --- | --- |
| `/` | 首页（欢迎页或空状态） |
| `/view/<code>` | 业务视图（`code = cmx_menu.code`） |
| `/view/<code>?<query>` | 带上下文参数的视图（深链传参） |
| `/view/portal-welcome` | 欢迎页（与 `/` 等价） |
| `/view/portal-dam-registry` | DAM 注册表（shellbar 内置入口） |
| `/view/portal-help-center` | 帮助中心 |
| `/view/portal-menu-manager` | 菜单管理 |
| `/view/portal-cluster-datasource` | 集群数据源 |
| `/view/portal-notify-<id>` | 通知中心 |

### 前缀选 `/view/` 的理由

- **语义准确**：URL 表达"打开某个业务视图"而非"菜单项"（菜单只是入口，URL 描述目标）
- **企业级惯例**：与 SAP Fiori 的 view 概念一致
- **路径安全**：已避开 `/api/` `/shared/` `/rpc/` `/trpc/` `/sse/` `/ws/` `/login/` `/portal/` 等已用路径
- **`code` 校验**：`cmx_menu.code` 数据库校验规则 `^[a-zA-Z0-9._-]{1,64}$` 已禁止 `/?&` 等特殊字符，URL 安全

---

## 三、核心模块

### 3.1 文件清单

| 文件 | 角色 |
| --- | --- |
| [src/lib/portal-router.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js) | 路由器单例：URL ↔ 当前激活 tab 双向同步 |
| [src/lib/menu-cache.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/menu-cache.js) | 全量菜单树共享缓存（一次加载、多处复用） |
| [src/components/portal-app.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app.js) | 桥接 router 与 side-nav、tab 切换、菜单选中同步 |
| [src/components/portal-side-nav-menu.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-side-nav-menu.js) | 菜单渲染与 `syncMenuSelection` 选中同步 |

### 3.2 关键类与函数

#### `PortalRouter`（单例）

通过 `getPortalRouter()` 获取。关键方法：

| 方法 | 作用 |
| --- | --- |
| `attach(host)` | 绑定到 `cmx-portal-app`，注册 popstate 监听并后台预拉菜单缓存 |
| `handleInitialLocation()` | 启动时按 URL 决定首屏（`/view/<code>` 打开对应菜单；`/` 走默认欢迎页） |
| `pushMenu(code, params?)` | 同步 URL（菜单点击 / shellbar 入口 / 业务方主动调） |
| `pushTab(tabId)` | tab 切换时同步 URL（tabId 即菜单 code） |
| `_handleLocationChange()` | popstate 处理：浏览器前进/后退 → 找菜单 → openNode |

#### URL 工具（导出）

```js
// 解析 URL pathname 为 { code, params } 或 null
parseMenuUrl(pathname, search?)

// 构造菜单 URL（如 /view/gl?docId=123）
buildMenuUrl(code, params?)
```

---

## 四、工作机制

### 4.1 启动流程

```
1. 用户访问 /view/gl
2. main.js：requireAuthOrRedirect → 登录门
3. bootstrapPortalShell：
   a. ensureCmxUi5Runtime
   b. import ui5-and-app（注册 cmx-portal-app）
   c. router.attach(portalApp)
      · 后台预拉 /api/menu/tree → 缓存到 menu-cache 单例
   d. 等待 cmx-portal-app connectedCallback
   e. router.handleInitialLocation()
      · 解析 URL → 找到 gl 节点 → openNode
   f. 若 URL 是 /：让应用走默认欢迎页逻辑
```

### 4.2 URL ↔ tab 双向同步

#### 代码 → URL（push 路径）

| 触发源 | 调用 | URL 行为 |
| --- | --- | --- |
| 点菜单 → `nav-selection` 事件 | `pushMenu(code)` | `/view/gl` |
| 切 tab → `portal-content-tab-activate` 事件 | `pushTab(tabId)` → `pushMenu(tabId)` | `/view/gl` |
| 业务方主动暴露参数到 URL | `pushMenu(code, {docId: 123})` | `/view/gl?docId=123` |

#### URL → 代码（pop 路径）

| 触发源 | 行为 |
| --- | --- |
| 浏览器前进/后退 → popstate | `_handleLocationChange` → 解析 URL → `openNode` |
| 直接访问深链 `/view/gl?docId=123` | `handleInitialLocation` → 解析 URL → `openNode` |
| 刷新页面 | 同上 |

### 4.3 自稳定（无反馈环）

- `pushState` 前检查 URL 是否已等于目标值（避免 router 驱动打开后 tab-activate 反馈时反复 push）
- `popstate` 仅浏览器前进/后退触发，`pushState`/`replaceState` 不会触发，故无反馈环

### 4.4 内置页面与 404

| 场景 | 行为 |
| --- | --- |
| shellbar 内置入口（welcome / dam-registry / help-center / menu-manager / cluster-datasource / notify） | `getBuiltinMenuNode(code)` 内置映射，不依赖后端菜单树 |
| URL 中 code 不存在（如 `/view/__non_existent__`） | 显示"页面不存在"占位页，URL 保持不变 |

---

## 五、菜单缓存共享

### 5.1 问题背景

早期 side-nav 每个 module 都调一次 `/api/menu/tree?domain_code=...`，N 个模块就是 N 次请求；router 还要再调一次全量加载，导致首屏请求数为 `N + 1`。

### 5.2 解决方案

`src/lib/menu-cache.js` 提供**单例缓存**：

```js
const cache = getMenuCache()
await cache.loadAll()                 // 一次 /api/menu/tree，幂等
const nodes = await cache.getModuleNodes({ domain, application, module })  // 前端过滤
const node = await cache.findByCode(code)  // router 按 code 查找
```

#### 关键设计

| 设计点 | 选择 | 理由 |
| --- | --- | --- |
| 加载策略 | 一次加载，多处复用 | side-nav 和 router 共享同一份缓存 |
| 模块过滤位置 | 前端 | `filterRawTreeByModule` 按 domain/application/module 过滤扁平列表 + 用 `parent_id` 重建树，语义等价于后端过滤 |
| 失败兜底 | 缓存空数组，不重试 | 避免反复打挂掉的后端 |

#### 性能对比

| 场景 | 优化前 | 优化后 |
| --- | --- | --- |
| 登录首屏 | `N + 1` 次 `/api/menu/tree`（N 个模块 + 1 次 router） | **1 次** |
| 切换 activity | 1 + N 次（DAM doc + 每模块 tree） | **0 次**（全缓存命中） |
| 全程（多 activity 切换） | 持续累积 | **1 次** |

---

## 六、参数传递规则

### 6.1 核心规则

> **URL 是页面身份的标识（`/view/<code>`），不是参数载体。**  
> **代码打开 → 内存传值（`initialContext` → `workspace.context`）；**  
> **直接访问 → URL query 是唯一的参数来源（只读输入）。**

### 6.2 数据流

#### 6.2.1 代码打开（点菜单 / openNode）

```js
// 业务方打开详情页，传 docId
host.openNode(detailMenuNode, { initialContext: { docId: row.id } })
getPortalRouter().pushMenu('voucher')   // 不传 params → URL 无 query

// 数据流：
//   initialContext → addTab({initialContext})
//                 → renderTabs 创建 ws 时 ws.context.set('docId', row.id)
//                 → 详情页 initPage 中 host.workspace.context.get('docId') 同步可读
//
// URL 行为：/view/voucher（无 query）
// 刷新后：URL 无 query → initialContext 为空（业务方需自行按业务场景处理）
```

#### 6.2.2 直接访问 / 刷新（深链）

```js
// 用户访问 /view/voucher?docId=123&mode=view
// router 内部：
const { code, params } = parseMenuUrl('/view/voucher', '?docId=123&mode=view')
//   → { code: 'voucher', params: { docId: '123', mode: 'view' } }
const extras = { initialContext: params }
host.openNode(menuNode, extras)

// 数据流：URL query → initialContext → ws.context
// URL 保持：/view/voucher?docId=123&mode=view
```

#### 6.2.3 业务方主动暴露参数到 URL（生成分享链接）

```js
// 业务方需要让 URL 携带参数（如生成可分享链接）
getPortalRouter().pushMenu('voucher', { docId: 123, mode: 'view' })
// URL：/view/voucher?docId=123&mode=view
// 后续刷新等同深链场景
```

### 6.3 API 一览

| API | 参数 | URL 结果 | 适用场景 |
| --- | --- | --- | --- |
| `pushMenu(code)` | 不传 params | `/view/<code>` | 默认：点菜单、切 tab、业务方 openNode |
| `pushMenu(code, params)` | 传 params | `/view/<code>?k=v` | 业务方主动暴露参数到 URL（如分享链接） |
| `host.openNode(node, {initialContext})` | 内存传值 | URL 不变 | 业务方内部跳转，参数不入 URL |
| 直接访问 `/view/<code>?k=v` | URL query | URL 保持 | 深链 / 刷新恢复 |

### 6.4 参数取值约定

- **类型**：URL query 解析后所有值都是字符串（`'123'`、`'true'`、`'null'`）
- **业务方读取**：`host.workspace.context.get('docId')` 拿到的是字符串，如需数字/布尔需自行转换
- **复杂对象**：不进 URL（URL 长度有限、可读性、安全性），仅传 ID 让业务方按 ID 重新查

### 6.5 prepare 对话框 result 的处理

菜单节点的 `workspace.prepare`（如选期间、组织）会让用户先在对话框确认，确认后 `resultSnap` 注入 `workspace.context`，与 `initialContext` 合并（prepare 用户确认值覆盖程序预设值）。**这部分参数不进 URL**，刷新后用户需重新选择（属业务流程，不属于页面身份）。

参考 [portal-app-workspace-prepare.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app-workspace-prepare.js#L59-L62)。

---

## 七、菜单选中态同步

### 7.1 问题

router 驱动打开 tab（深链 / 浏览器前进后退 / 刷新）时，UI5 `side-nav` 不会自动派发 `selection-change`（只有用户鼠标点击才派发），导致侧边栏选中态与当前激活 tab 不一致。

### 7.2 解决方案

#### `syncMenuSelection(sideNavHost, menuCode)`

[src/components/portal-side-nav-menu.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-side-nav-menu.js#L93) 中导出的工具函数：

```js
// 遍历 portal-side-nav 所有 ui5-side-navigation
// 按 data-menu-id == menuCode 匹配并设 selected = true，其它清空
syncMenuSelection(sideNav, 'gl')
```

#### 双触发同步

| 触发点 | 应对场景 |
| --- | --- |
| `portal-content-tab-activate` 事件 | 菜单已渲染时立即同步 |
| `portal-menu-rendered` 事件（新增） | 菜单异步加载完成后再补一次同步（解决菜单后于 tab 加载的时序问题） |

幂等：用户点击菜单走 UI5 自身 `selection-change`；router/刷新场景走 `syncMenuSelection`。两者不会同时修改同一菜单项（事件链天然串行）。

---

## 八、刷新与浏览器历史

### 8.1 刷新保持

刷新触发完整页面重载，应用从启动流程重新走一遍：

1. URL 是 `/view/gl` → `handleInitialLocation` 解析 → 从 menu-cache 查 gl → openNode
2. menu-cache 重新拉取（页面级内存缓存随重载丢失，属正常）
3. tab 重新创建，URL 保持不变

### 8.2 浏览器前进 / 后退

`popstate` 事件触发 `_handleLocationChange`：

| 当前 URL | 后退目标 | 行为 |
| --- | --- | --- |
| `/view/gl` | `/` | 打开欢迎页（selectOnly=true，若 tab 已存在仅切换） |
| `/` | `/view/gl` | 从 menu-cache 查 gl → openNode |
| `/view/gl?docId=1` | `/view/gl?docId=2` | 解析新 query → openNode（context 更新） |

### 8.3 多 tab 不持久化

URL 只反映"当前激活 tab"，不持久化所有打开的 tab。刷新时只重新打开 URL 对应的菜单页（参考 SAP Fiori Launchpad 同款设计）。

---

## 九、限制与边界

| 场景 | 当前行为 | 备注 |
| --- | --- | --- |
| URL query 参数类型 | 全是字符串 | 业务方需自行 `parseInt` / `=== 'true'` 转换 |
| prepare 对话框 result | 仅在内存 | 刷新后用户需重新选择（属业务流程） |
| 复杂对象（如选中行） | 无法编码到 URL | 刷新后业务方需按 ID 重新查 |
| 多 tab 状态 | 不持久化 | URL 只反映当前激活 tab |
| 未授权菜单的深链 | 前端按 `permissionId` 过滤 | 不在树中 → 显示"页面不存在" |
| 用户手动改 URL 为不存在的 code | 显示 404 占位页 | URL 保持，用户可手动返回首页 |

---

## 十、测试覆盖

webapp-testing 已验证以下场景（共 14+ 项）：

1. 登录后访问 `/` 显示首页
2. 点击菜单 → URL = `/view/<code>`
3. 浏览器后退 → URL = `/`
4. 浏览器前进 → URL = `/view/<code>`
5. 直接访问 `/view/<code>`（深链）
6. 刷新 `/view/<code>` 保持
7. 不存在的 code → 显示 404
8. 深链带 query `/view/<code>?docId=123` → context 注入
9. 首屏 `/api/menu/tree` 只请求 1 次
10. 切换菜单 / 前进后退不触发新 `/api/menu/tree` 请求
11. 深链后菜单自动选中
12. 浏览器前进后退后菜单选中态同步
13. 刷新后菜单保持选中
14. 点击另一顶级菜单后选中切换

测试脚本：`/tmp/test_portal_routing.py`、`/tmp/test_menu_cache_v3.py`、`/tmp/test_menu_selection.py`、`/tmp/test_view_prefix.py`。

---

## 十一、关键代码索引

| 功能 | 文件:行 |
| --- | --- |
| URL 前缀常量 | [portal-router.js:40](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L40) |
| `parseMenuUrl` | [portal-router.js:79](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L79) |
| `buildMenuUrl` | [portal-router.js:100](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L100) |
| `PortalRouter.attach` | [portal-router.js:133](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L133) |
| `PortalRouter.handleInitialLocation` | [portal-router.js:165](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L165) |
| `PortalRouter.pushMenu` | [portal-router.js:189](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L189) |
| `PortalRouter._openNodeByCode`（query → initialContext） | [portal-router.js:274](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-router.js#L274) |
| `MenuCache` 单例 | [menu-cache.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/menu-cache.js) |
| `syncMenuSelection` | [portal-side-nav-menu.js:93](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-side-nav-menu.js#L93) |
| router 接入 `connectedCallback` | [portal-app.js:74](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app.js#L74) |
| `nav-selection` → pushMenu | [portal-app.js:381](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app.js#L381) |
| `portal-content-tab-activate` → pushTab + syncMenuSelection | [portal-app.js:231](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app.js#L231) |
| `portal-menu-rendered` 监听 | [portal-app.js:390](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app.js#L390) |
| addTab `initialContext` 注入 | [portal-content-area-tabs.js:35](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-content-area-tabs.js#L35) |
| prepare result 与 initialContext 合并 | [portal-app-workspace-prepare.js:59](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-app-workspace-prepare.js#L59) |

---

## 十二、设计原则速记

1. **确定性路由**：URL 由 `cmx_menu.code`（业务唯一稳定编码）决定，刷新不变
2. **纯前端实现**：零后端改动，仅前端新增 router + 桥接
3. **零破坏性**：保留现有 content-tab 工作区模式，URL 只是镜像激活 tab
4. **企业级**：刷新保持、深链直开、浏览器前进后退、404 提示、参数注入
5. **轻量**：~430 行自定义路由器，无 vue-router 等新依赖
6. **自稳定**：pushState 前检查 URL 是否已等于目标值，避免反馈环
7. **菜单缓存共享**：side-nav 与 router 共用一份内存缓存，全程 `/api/menu/tree` 仅 1 次请求
8. **参数语义清晰**：代码打开走内存、深链走 URL query、`pushMenu(code, params)` 是显式逃生口
