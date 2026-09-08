# 工作区区域联动（content ↔ property）

> 何时读：任何工作区节点（menu-node）配置了 content + property 两个区域、需要它们联动时必读。
> 典型场景：content 切换 tab 时自动隐藏/显示 property 栏，或自动切换 property 内部子 tab。
> 源码：`../../../../cmx-portal-manager` + `../../../../cmx-portal-manager`

---

## 零、适用范围（重要）

**仅适用于前端硬编码的 menu-node**（JS 对象，如 `../../../../cmx-portal-manager`）。

**不适用于 menu-pages JSON 文件**（`backend/cmx-container/assets/model/data/menu-pages/**/*.json`）——`gen_menu_migration.mjs` 不处理这两个字段，写了会被丢弃。如需在 menu-pages 中使用，需先扩展 `gen_menu_migration.mjs` 把字段映射到 `cmx_menu.definition` JSONB。

典型适用场景：
- 系统级工作台（集群数据源、DAM 注册中心、菜单管理、帮助中心、通知中心）
- 这些菜单节点都是前端 JS 硬编码的 `PORTAL_XXX_MENU_NODE` 常量

---

## 一、能力概览

框架内置两种联动，通过 menu-node 的 view spec 字段声明，**业务页代码无需处理**：

| 字段 | 作用 | 典型场景 |
|------|------|---------|
| `hideProperty: true` | 切到此 content view 时**隐藏整个 property 栏** | 概览页/仪表盘（不需要属性详情） |
| `syncPropertyView: '<viewId>'` | 切到此 content view 时**切换 property 栏内部 tab**到指定 viewId | 多视图工作台（content 的「数据字典」↔ property 的「数据字典详情」） |

> 两个字段可同时声明（但通常 `hideProperty: true` 时不需要 `syncPropertyView`）。
> 仅 content region 的 view spec 生效（其他区域不影响 property 栏）。

---

## 二、配置示例

### 2.1 单工作台完整配置（含 content + property）

```js
// CMXPortalManager/src/lib/<xxx>-menu-node.js
export const PORTAL_XXX_MENU_NODE = Object.freeze({
  id: 'portal-xxx',
  caption: 'XXX 工作台',
  type: 'workspace-node',
  workspace: {
    content: {
      caption: '主内容',
      views: [
        // 概览：隐藏 property 栏
        { tabLabel: '概览', view: 'content-overview', hideProperty: true },
        // 三视图：显示 property 栏并联动到对应子 tab
        { tabLabel: '数据字典', view: 'content-dct', syncPropertyView: 'property-dct' },
        { tabLabel: '业务单据', view: 'content-doc', syncPropertyView: 'property-doc' },
      ],
    },
    property: {
      caption: '详情',
      views: [
        // ★ property views 必须声明 id 字段，作为 syncPropertyView 的匹配键
        { id: 'property-dct', tabLabel: '数据字典', view: 'property-dct' },
        { id: 'property-doc', tabLabel: '业务单据', view: 'property-doc' },
      ],
    },
  },
})
```

### 2.2 仅隐藏 property 栏（最简）

```js
content: {
  views: [
    { tabLabel: '仪表盘', view: 'content-dashboard', hideProperty: true },
  ],
},
// property 区域可不配置
```

### 2.3 仅联动 property 内部 tab

```js
content: {
  views: [
    { tabLabel: '列表', view: 'content-list', syncPropertyView: 'property-detail' },
  ],
},
property: {
  views: [
    { id: 'property-detail', tabLabel: '详情', view: 'property-detail' },
  ],
},
```

---

## 三、关键规则

### 3.1 `syncPropertyView` 必须匹配 property view 的 `id`

```js
// ✅ 正确：syncPropertyView 值 == property view 的 id
{ view: 'content-foo', syncPropertyView: 'property-foo' }
// ...
{ id: 'property-foo', view: 'property-foo' }
```

```js
// ❌ 错误：property view 没声明 id，框架无法匹配
{ view: 'content-foo', syncPropertyView: 'property-foo' }
// ...
{ view: 'property-foo' }  // 缺 id 字段
```

> property view 的 `id` 缺省时由 `resolveWorkspaceViewId` 自动生成（`<region>.<index>`，如 `property.0`），
> 但**建议显式声明 id**，避免视图顺序变化导致匹配失败。

### 3.2 仅 content region 生效

`hideProperty` / `syncPropertyView` 只在 content region 的 view spec 上生效。
explorer / property / bottom 区域的 view spec 声明这两个字段会被忽略。

### 3.3 联动是单向的

content → property（content 切换 tab 时联动 property）。
property 内部切换 tab **不会反向联动 content**。

### 3.4 首次进入工作台的初始态

首次打开工作台时，框架会读 content 第一个 view（默认激活的 view）的配置：
- 若声明 `hideProperty: true` → 强制隐藏 property 栏（覆盖 tab 的 dock 偏好）
- 若声明 `syncPropertyView` → 切到 property 对应子 tab

---

## 四、实现原理（框架层）

### 4.1 渲染时输出 data 属性

`workspace-view-renderer.js` 的 `renderWorkspaceRegionViewsHtml`：
- content region 的 tab-btn 渲染时，若 view spec 声明 `hideProperty`，输出 `data-hide-property="1"`
- 若声明 `syncPropertyView`，输出 `data-sync-property-view="<viewId>"`

```html
<!-- 渲染后的 tab-btn 示例 -->
<button class="cmx-ws-tab-btn" data-pane-index="0" data-hide-property="1">概览</button>
<button class="cmx-ws-tab-btn" data-pane-index="1" data-sync-property-view="property-dct">数据字典</button>
```

### 4.2 切换 tab 时派发事件

`workspace-view-renderer.js` 的 `handleWorkspaceRegionTabBarClick`：
- content region 的 view（子 tab）切换时，读取目标 tab-btn 的 data 属性
- 派发 `portal-content-view-change` 事件（bubbles + composed 跨 shadow DOM）

```js
region.dispatchEvent(new CustomEvent('portal-content-view-change', {
  bubbles: true,
  composed: true,
  detail: { viewIndex: idx, hideProperty, syncPropertyView },
}))
```

### 4.3 portal-app 监听事件联动

`portal-app.js` 的 `portal-content-view-change` 监听器：
- 按 `detail.hideProperty` 调整 `_propertyVisible` + 调 `Layout.applyLayout`
- 按 `detail.syncPropertyView` 调 `propertyPanel.activateWorkspaceRegionViewByViewId(viewId)`

### 4.4 首次进入 / 切回 tab 的初始态

`portal-app.js` 的 `portal-content-tab-activate` 监听器：
- 读 `content.getTabContentSpec(tabId)` 拿 content views 配置（content region 在 portal-content-area shadowRoot 内，跨 shadow 查不到；workspaceShell 不含 content）
- 取第一个 view（默认激活的 view）的配置
- 按 `hideProperty` / `syncPropertyView` 处理初始态

---

## 五、调试技巧

### 5.1 确认 data 属性已输出

在浏览器控制台检查 content region 的 tab-btn：
```js
// 跨 shadow DOM 查找（content region 在 portal-content-area 的 shadowRoot 内）
document.querySelector('cmx-portal-app').shadowRoot
  .querySelector('portal-content-area').shadowRoot
  .querySelectorAll('.cmx-ws-tab-btn')
```

### 5.2 确认事件已派发

切换 content tab 时，控制台应看到 `portal-content-view-change` 事件。
可在 portal-app.js 的监听器加 `console.log` 验证。

### 5.3 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 切到 content tab 但 property 没变化 | property view 没声明 `id`，或 `syncPropertyView` 值不匹配 | 给 property view 加 `id` 字段，值与 `syncPropertyView` 一致 |
| 首次进入 property 栏仍显示 | 旧代码缓存 / contentSpec 未读到 | 刷新页面；确认 menu-node 的 content views 配置正确 |
| 切回其他工作台 tab 后 property 状态异常 | dock 偏好被覆盖 | 切回 tab 时框架按该 tab 的 dock 偏好恢复，再按 content 首个 view 的 `hideProperty` 覆盖 |

---

## 六、关键文件索引

| 用途 | 路径 |
|------|------|
| 渲染 data 属性 | `../../../../cmx-portal-manager` 的 `renderWorkspaceRegionViewsHtml` |
| 派发事件 | `../../../../cmx-portal-manager` 的 `handleWorkspaceRegionTabBarClick` |
| 监听事件联动 | `../../../../cmx-portal-manager` 的 `portal-content-view-change` 监听器 |
| 首次进入处理 | `../../../../cmx-portal-manager` 的 `portal-content-tab-activate` 监听器 |
| property 内部 tab 切换 | `../../../../cmx-portal-manager` 的 `activateWorkspaceRegionViewByViewId` |
| 配置示例 | `../../../../cmx-portal-manager` |
| view spec 类型定义 | `../../../../cmx-portal-manager` 的 `WorkspaceViewSpec` |

---

## 七、相关技能

- **`native-page-generator`** —— native-page 业务代码**不需要**处理 property 联动（框架自动完成）。native-page 只需关心自己的 view 渲染。但 native-page 经常配套**前端硬编码的 menu-node**（如 `cluster-datasource-menu-node.js`），在 menu-node 的 workspace spec 中声明这两个字段。
- **`menu-generator`** —— 本文档的配置方式**不适用于** menu-pages JSON 文件（`gen_menu_migration.mjs` 不处理这两个字段）。如需在 menu-pages 中使用，需先扩展迁移脚本。
